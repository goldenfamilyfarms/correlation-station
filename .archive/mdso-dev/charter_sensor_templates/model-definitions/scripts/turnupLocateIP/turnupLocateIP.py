import json
import time
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
import ipaddress
from ra_plugins.ra_cutthrough import RaCutThrough
from ping3 import verbose_ping


class Activate(CommonPlan):
    """
    Activation Class for TurnUp Locate IP
    """

    def process(self):
        self.enter_exit_log(message="Turnup Locate IP")
        # STEP 1. Build Equipment Dictionaries Based on Input
        self.status_update("Step 1: Preparing Data for port turn up and IP location")

        try:
            pe_router = {}
            pe_router["fqdn"] = self.properties["pe_router_FQDN"].upper()
            pe_router["vendor"] = self.properties["pe_router_vendor"].upper()
            pe_router["tid"] = pe_router["fqdn"].split(".")[0].upper()

            upst_device = {}
            upst_device["fqdn"] = self.properties["upstream_device_FQDN"].upper()
            upst_device["vendor"] = self.properties["upstream_device_vendor"].upper()
            upst_device["port"] = self.properties["upstream_port"].upper()
            upst_device["tid"] = upst_device["fqdn"].split(".")[0].upper()
            upst_device["pe"] = True if upst_device["tid"] == pe_router["tid"] else False

        except Exception:
            self.status_update("Unable to Process Provided Data", True, "TULIP10100")
            self.exit_error("Unable to Process Provided Data: %s" % self.properties)

        # STEP 2. Onboard or Resync Upstream Equipment, Offboard CPE
        self.status_update("Step 2: Obtaining, Onboarding, and Offboarding Equipment as Needed")

        try:

            # Check for Upstream Equipment, Resync or Onboard as Needed
            devices_to_onboard = []

            self.pe_router_nf = self.get_onboard_device(pe_router["fqdn"])
            upst_device_nf = self.get_onboard_device(upst_device["fqdn"])

            self.logger.info("================= self.pe_router_nf: ============================")
            self.logger.info(self.pe_router_nf)
            self.logger.info("================= upst_device_nf: ============================")
            self.logger.info(upst_device_nf)

            if self.pe_router_nf is None:
                devices_to_onboard.append(pe_router)
                self.logger.info("I will be onboarding %s" % pe_router["tid"])
            else:
                self.logger.info("Resyncing %s" % pe_router["tid"])
                self.bpo.market.post("/resources/{}/resync".format(self.pe_router_nf["id"]))

            if upst_device_nf is None and upst_device["pe"] is False:
                devices_to_onboard.append(upst_device)
                self.logger.info("I will be onboarding %s" % upst_device["tid"])
            elif upst_device["pe"] is False:
                self.logger.info("Resyncing %s" % upst_device["tid"])
                self.bpo.market.post("/resources/{}/resync".format(upst_device_nf["id"]))

            # Time allowance for resync if onboarding not needed
            if len(devices_to_onboard) == 0:
                time.sleep(20)

            self.logger.info("=== devices_to_onboard: %s" % devices_to_onboard)

            for dvc in devices_to_onboard:
                dvc_onboard_result = self.onboard_device(dvc)
                self.logger.info("=========== dvc_onboard_result for %s ===========" % dvc["tid"])
                self.logger.info(dvc_onboard_result)

                if dvc["tid"] == pe_router["tid"]:
                    self.pe_router_nf = self.get_onboard_device(pe_router["fqdn"])
                    if upst_device["pe"]:
                        upst_device_nf = self.pe_router_nf
                else:
                    upst_device_nf = self.get_onboard_device(upst_device["fqdn"])

            self.logger.info("I should be done onboarding stuff now")
            pe_router["model"] = self.pe_router_nf["properties"]["type"]
            upst_device["model"] = upst_device_nf["properties"]["type"]

        except Exception:
            self.status_update("Unable to Obtain, Onboard, and/or Offboard Equipment", True, "TULIP10200")
            self.exit_error(
                "Unable to Obtain, Onboard, and/or Offboard Equipment: %s, %s" % (pe_router["tid"], upst_device["tid"])
            )

        # STEP 3. Check Upstream Port Status
        self.status_update("Step 3: Check Upstream Port Status")
        try:
            # Determine Proper TPE(Port) Name
            if upst_device["vendor"] == "JUNIPER":
                upst_port = upst_device["port"].lower()
            elif upst_device["vendor"] == "RAD":
                upst_port = "TPE_ETHERNET-" + upst_device["port"].replace("ETH PORT ", "") + "_PTP"

            self.logger.info("upst_port: %s" % upst_port)

            self.tpe_resource = self.get_tpe_by_name_and_host_return_errors(upst_device["fqdn"], upst_port)
            self.logger.info(f"tpe_resource: {self.tpe_resource}")
            if "status" in self.tpe_resource.keys() and "not present" in self.tpe_resource["status"]:
                max_tpe_checks = 12
                for wait_step in range(1, max_tpe_checks + 1):
                    self.logger.info(
                        f"TPE not ACTIVE yet. Waiting 10 seconds and checking again - Attempt# {wait_step} of {max_tpe_checks}"
                    )
                    if "status" in self.tpe_resource.keys() and "not present" in self.tpe_resource["status"]:
                        time.sleep(10)
                        self.tpe_resource = self.get_tpe_by_name_and_host_return_errors(upst_device["fqdn"], upst_port)
                        self.logger.info(f"tpe_resource: {self.tpe_resource}")
                        if (
                            wait_step == 12
                            and "status" in self.tpe_resource.keys()
                            and "not present" in self.tpe_resource["status"]
                        ):
                            fail_reason = f"TPE not active after {str(wait_step * 10)} seconds. Activation failed."
                            status_mesg = (
                                "Unable to Verify Port Status: " + upst_device["tid"] + " " + upst_device["port"]
                            )
                            self.status_update(status_mesg, True, "TULIP10300")
                            self.exit_error(status_mesg + " - " + fail_reason)
                    else:
                        break

            self.logger.info("tpe_resource: %s" % self.tpe_resource)

            # Check Port Status
            upst_port_state = self.check_port_status(upst_port, upst_device)
            self.logger.info("Upstream Port Adminstate: %s" % upst_port_state["admin"])
            self.logger.info("Upstream Port Operational-state: %s" % upst_port_state["oper"])

        except Exception:
            status_mesg = "Unable to Verify Port Status: " + upst_device["tid"] + " " + upst_device["port"]
            self.status_update(status_mesg, True, "TULIP10300")
            self.exit_error(status_mesg)

        # STEP 4. Activate Upstream Port if Needed
        self.status_update("Step 4: Activate upstream port if needed")
        try:
            # Now that we've got the port's status, we will determine if it needs activating
            if upst_port_state["admin"].upper() != "UP":
                self.logger.info("ACTIVATING PORT")
                self.logger.info("UPSTREAM DEVICE VENDOR: %s" % upst_device["vendor"])

                if upst_device["vendor"] == "RAD":
                    self.logger.info("************ RAD TPE DATA ************")
                    self.logger.info("TPE DATA: %s" % self.tpe_resource)
                    # Setting the STATE to IS aka IN SERVICE
                    self.tpe_resource["properties"]["data"]["attributes"]["state"] = "IS"

                    # Set discovered to FALSE if it's true so we can modify the TPE
                    was_discovered = False
                    if self.tpe_resource["discovered"] is True:
                        self.bpo.resources.patch(self.tpe_resource["id"], {"discovered": False})
                        was_discovered = True

                    # Update the TPE / turn up the port
                    self.bpo.resources.patch(self.tpe_resource["id"], {"properties": self.tpe_resource["properties"]})
                    self.await_differences_cleared_collect_timing(
                        "Differences clear on TPE:{}", format(self.tpe_resource["id"])
                    )

                    # Set discovered back to True like we found it
                    if was_discovered:
                        self.bpo.resources.patch(self.tpe_resource["id"], {"discovered": True})

                elif upst_device["vendor"] == "JUNIPER":
                    self.activate_port(upst_device)

            upst_port_state = self.check_port_status(upst_port, upst_device)
            if upst_port_state["admin"].upper() != "UP":
                status_mesg = "Unable to Turn Up Port: " + upst_device["tid"] + " " + upst_device["port"]
                self.status_update(status_mesg, True, "TULIP10400")
                self.exit_error(status_mesg)

        except Exception:
            status_mesg = "Unable to Turn Up Port: " + upst_device["tid"] + " " + upst_device["port"]
            self.status_update(status_mesg, True, "TULIP10400")
            self.exit_error(status_mesg)

        # STEP 5. Confirm upstream port is both adminstratively and operationally up
        self.status_update("Step 5: Confirm upstream port is both adminstratively and operationally up")

        # Port Admin Up, but Operationally Down = No Layer 1 Connection
        if upst_port_state["oper"].upper() != "UP":
            status_mesg = (
                "CPE-Facing Port is administratively up, but operationally down"
                " - Ensure device is connected, light is verified, and CPE is defaulted (with"
                " pre-config applied if appropriate). Then select 'Try Again'. After"
                " a second failed attempt, call Service Activation Support Team for"
                " assistance at 844.896.5784 - Option 1, 2  Monday through Friday"
                " from 7am to 7pm CST."
            )
            self.status_update(status_mesg, True, "TULIP10500")
            self.exit_error("CPE-Facing port UP DOWN - Layer 1 Issue")

        # STEP 6. Get MAC Address for CPE if needed
        self.status_update("Step 6: Get MAC Address for CPE if needed")

        try:
            if upst_device["pe"] is False:
                mac_address = self.get_mac(upst_device)

        except Exception:
            status_mesg = (
                "Unable to get MAC Address for CPE - Ensure device is connected, light"
                " is verified, and CPE is defaulted (with pre-config applied if"
                " appropriate), then select 'Try Again'. After a second failed attempt,"
                " call Service Activation Support Team for assistance at 844.896.5784 -"
                " Option 1, 2  Monday through Friday from 7am to 7pm CST."
            )
            self.status_update(status_mesg, True, "TULIP10600")
            self.exit_error(status_mesg)

        # STEP 7. Get IP address for CPE
        self.status_update("Step 7: Get IP address for CPE")

        try:
            if upst_device["pe"] is False:
                self.cpe_ip = self.find_ip(pe_rtr=self.pe_router_nf, mac=mac_address)
            else:
                self.cpe_ip = self.find_ip(pe_rtr=self.pe_router_nf, port=upst_device["port"])

            # Update Standalone Resource with CPE IP
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip": self.cpe_ip}})
        except Exception:
            status_mesg = (
                "Unable to get IP Address for CPE - Ensure device is connected, light is"
                " verified, and CPE is defaulted (with pre-config applied if appropriate),"
                " then select 'Try Again'. After a second failed attempt, call Service"
                " Activation Support Team for assistance at 844.896.5784 - Option 1, 2"
                " Monday through Friday from 7am to 7pm CST."
            )
            self.status_update(status_mesg, True, "TULIP10700")
            self.exit_error(status_mesg)

    def status_update(self, status_msg, err_msg=False, err_code=None):
        """
        Updates tulip_status, tulip_error and tulip_error_code
        :param status_msg: String to update tulip_status/tulip_error
        :param err_msg: Boolean to identify when failing
        :param err_code: String for error reporting
        """
        props = {}
        if err_msg:
            props["tulip_error"] = status_msg
            props["tulip_error_code"] = err_code
        else:
            props["tulip_status"] = status_msg

        self.bpo.resources.patch_observed(self.resource["id"], {"properties": props})

    def get_onboard_device(self, fqdn):
        """
        Find onboard equipment in MDSO
        :param fqdn: String to use actual FQDN or IP address
        :return: device's network function resource
        """
        device_resource = self.get_network_function_by_host_or_ip(fqdn)

        return device_resource

    def onboard_device(self, dvc, fqdn=True):
        """
        Onboards device
        :param dvc: Dictionary containing device details
        :param fqdn: Boolean to identify contact method
        :return: Onboarding results
        """

        device_name = dvc["tid"].upper()
        device_fqdn = dvc["fqdn"].upper()
        contact_method = device_fqdn if fqdn else dvc["ip"]
        created_onboarded_res = []
        devices_deployed = {}
        vendor_name = dvc["vendor"].upper()
        onboard_product = self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)

        label = device_fqdn + ".device_onboarder"
        devices_deployed[device_fqdn] = False
        onboard_details = {
            "label": label,
            "productId": onboard_product["id"],
            "properties": {
                "device_ip": contact_method,
                "device_name": device_name,
                "device_vendor": vendor_name,
                "device_already_active": True,
            },
        }

        if "model" in dvc.keys():
            onboard_details["properties"]["device_model"] = dvc["model"]

        self.logger.debug("On-boarding device: " + device_fqdn)
        device_res = self.add("Resource", "/resources", onboard_details)
        created_onboarded_res.append(device_res)
        # NOW WAIT FOR THEM ALL TO FINISH
        for resp in created_onboarded_res:
            resp_id = resp["id"]
            # Wait for relationships to be built
            try:
                self.await_resource_states_collect_timing("Waiting for " + resp_id, resp_id, interval=5, tmax=300)
                devices_deployed[resp["properties"]["device_ip"]] = True
            except Exception:
                try:
                    r = self.bpo.resources.get(resp_id)
                    if r is not None:
                        devices_deployed[resp["properties"]["device_ip"]] = r["orchState"] == "active"
                except Exception as ex:
                    devices_deployed[resp["properties"]["device_ip"]] = True
                    self.logger.debug("On-boarder %s already on-boarding so no need to check." % resp_id)
                    self.logger.debug("Exception: " + str(ex))

                # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
                self.delete_resource(resp_id)

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        output = {"status": "Device deployed successfully"}
        self.logger.info("Output: " + json.dumps(output))

        return json.dumps(output)

    def check_port_status(self, upst_port, upst_device):
        """
        Gets state of port (TPE)
        :param upst_port: String of port name
        :param upst_device: Dictionary with upstream device details
        :return: Return dictionary port state
        """
        self.logger.info("********* GET ADMIN STATUS *********")

        if upst_device["vendor"] == "JUNIPER":
            admin_json = "get-interface.json"
            admin_params = {"name": upst_port}

        elif upst_device["vendor"] == "RAD":
            admin_json = "get-port-details.json"
            nu_port = upst_port.split("_")[1].split("-")
            admin_params = {"type": nu_port[0], "id": nu_port[1]}

        self.logger.info("THE UPST_PORT IS: %s" % upst_port)

        get_admin_state = self.execute_ra_command_file(
            self.tpe_resource["properties"]["device"], admin_json, admin_params, headers=None
        )

        self.logger.info("GET ADMIN STATE RESPONSE: %s" % get_admin_state)
        get_admin_state = get_admin_state.json()["result"]
        self.logger.info("GET ADMIN STATE JSON: %s" % get_admin_state)

        portstate = {}
        if upst_device["vendor"] == "JUNIPER":
            portstate["admin"] = get_admin_state["interface-information"]["physical-interface"]["admin-status"]["#text"]
            portstate["oper"] = get_admin_state["interface-information"]["physical-interface"]["oper-status"]
        elif upst_device["vendor"] == "RAD":
            portstate["admin"] = get_admin_state["admin"]
            portstate["oper"] = get_admin_state["oper"]
        self.logger.info("PORTSTATE: %s" % portstate)

        return portstate

    def activate_port(self, upst_dvc):
        """
        Activates Upstream Port
        :param upst_dvc: Dictionary with upstream device details
        """

        self.logger.info("ACTIVATING PORT in activate_port")
        self.logger.info("upst_dvc - port: %s" % upst_dvc["port"])
        self.logger.info("upst_dvc - vendor: %s" % upst_dvc["vendor"])
        port_activation_resource_id = self.check_port_activation_resources(
            upst_dvc["fqdn"], upst_dvc["port"].lower(), "custom"
        )

        if port_activation_resource_id is not None:
            self.bpo.resources.delete(port_activation_resource_id["resourceId"])

        self.logger.info("PORT ACTIVATION CREATION")
        rtype = self.get_built_in_product(self.BUILT_IN_RESOURCE_PORT_ACTIVATION_TYPE)
        self.logger.info(rtype)
        self.logger.info("RTYPE: %s" % rtype)
        activator_details = {
            "label": upst_dvc["tid"] + ".cpe_activator",
            "productId": rtype["id"],
            "properties": {
                "deviceName": upst_dvc["fqdn"],
                "portname": upst_dvc["port"].lower(),
                "terminationTime": 0,
                "vendor": upst_dvc["vendor"],
            },
        }
        self.logger.info("SELF.RESOURCE - ID: %s" % self.resource["id"])
        port_activator = self.create_active_resource(
            rtype, self.resource["id"], activator_details, create_relationship=False
        )

        self.logger.info("=====PORT ACTIVATOR=====")
        self.logger.info(port_activator)
        set_port_up = self.bpo.resources.post_operation(
            port_activator.resource_id, "setPortStatus", {"reqdstate": "up"}
        )
        try:
            self.await_operation_successful_collect_timing(set_port_up["resourceId"], set_port_up["id"])
        except Exception:
            try:
                time.sleep(30)
                self.await_operation_successful_collect_timing(set_port_up["resourceId"], set_port_up["id"])
            except RuntimeError:
                status_mesg = "Unable to Turn Up Port: " + upst_dvc["tid"] + " " + upst_dvc["port"]
                self.status_update(status_mesg, True, "TULIP10400")
                self.exit_error(status_mesg)

        self.logger.info("**PORT UP OPERATION**")
        self.logger.info("{}".format(set_port_up))

    def get_mac(self, up_dev):
        """
        Obtain MAC Address
        :param up_dev: Dictionary with upstream device details
        :return: String mac_address
        """
        try:
            self.logger.info("********* UPLINK INFORMATION *********")
            self.logger.info("CPE_UPLINK_DEVICE: %s" % up_dev["tid"])
            self.logger.info("UPLINK_PORT: %s" % up_dev["port"])
            self.logger.debug("Getting MAC ADDRESS")
            model = up_dev["model"]
            vendor = up_dev["vendor"]
            self.logger.info("Device directly upstream from CPE MODEL IS {}".format(model))
            self.logger.info("Device directly upstream from CPE VENDOR IS {}".format(vendor))
            mac_repopulated = False

            t = 30
            mac_address = "*"

            if vendor == "RAD":
                MTU_TPE = None
                TPE_LBL = up_dev["tid"] + "::TPE_ETHERNET-" + up_dev["port"].replace("ETH PORT ", "") + "_IN_0"
                mgmt_flow_tpes = self.get_resources_by_type_and_query(
                    "tosca.resourceTypes.TPE", None, f"label:{TPE_LBL}"
                )
                self.logger.info("mgmt_flow_tpes: {}".format(mgmt_flow_tpes))

                for tpe in mgmt_flow_tpes:
                    tpe_dependencies = self.get_dependencies(
                        tpe["id"], resource_type="radra.resourceTypes.NetworkFunction", recursive=True
                    )
                    self.logger.info(
                        f"TPE_DEPENDENCIES for TPE {tpe['id']} has {len(tpe_dependencies)} dependencies: {tpe_dependencies}"
                    )
                    if len(tpe_dependencies) == 1:
                        MTU_TPE = tpe
                        self.logger.info(f"MTU_TPE: {MTU_TPE}")
                        break

                if not MTU_TPE:
                    self.logger.info("No TPE for Management Flow tied to Network Function for RAD MTU")
                    status_mesg = (
                        f"Unable to find management flow for port {up_dev['port']} on Rad MTU {up_dev['tid']}."
                        " Please contact the Service Activation Support Team to confirm/correct the MTU"
                        " configuration. Once corrected, please reboot the CPE and then select 'Try Again'."
                        " Service Activation Support Team: 844.896.5784 - Option 1, 2  Monday through"
                        " Friday from 7am to 7pm CST."
                    )
                    self.status_update(status_mesg, True, "TULIP10620")
                    self.exit_error("Timed out waiting for Mac to be learned on {}".format(up_dev["tid"]))

                self.logger.info("********* THE MTU_TPE FOR BRIDGE *********")
                self.logger.info("MTU_TPE: {}".format(MTU_TPE))

                bridge_flow_native_name = MTU_TPE["properties"]["data"]["attributes"]["nativeName"]
                self.logger.info("bridge_flow_native_name: %s" % bridge_flow_native_name)
                my_bridge_port = bridge_flow_native_name.rsplit("p")[-1]
                self.logger.info("bridge_port: %s" % my_bridge_port)

                while mac_address == "*" and t > 0:
                    self.logger.info(
                        "********* T-MINUS {} SECONDS BEFORE I GIVE UP ON THE MAC ADDRESS *********".format(t)
                    )
                    mac_response = self.execute_ra_command_file(
                        self.tpe_resource["properties"]["device"], "get-mac-table.json"
                    )
                    self.logger.info("********* MAC RESPONSE IN RAW FORM *********")
                    self.logger.info("mac_response: {}".format(mac_response))
                    response = mac_response.json()["result"]
                    self.logger.info("********* MAC RESPONSE IN JSON FORM *********")
                    self.logger.info("response: {}".format(response))

                    bad_macs = ["33-33", "FF-FF"]
                    for mac_entry in response:
                        if mac_entry["VLAN"] == "99" and mac_entry["Port"] == my_bridge_port:
                            if mac_entry["Mac"][0:5] not in bad_macs:
                                mac_address = mac_entry["Mac"]
                            self.logger.info("MAC ADDRESS FROM RAD: {}".format(mac_address))

                    if mac_address != "*":
                        mac_address = ":".join(mac_address.split("-")).lower()
                        self.logger.info("FORMATTED MAC ADDRESS: {}".format(mac_address))

                    t -= 5
                    time.sleep(5)

            elif vendor == "JUNIPER":
                mgmt_vlans = ["MGMT", "CPEMGMT"]
                juniper_aggs = ["EX", "QFX", "ACX"]

                for device in juniper_aggs:
                    if device in model:
                        model = device

                while mac_address == "*" and t > 0:
                    mac_response = self.execute_ra_command_file(
                        self.tpe_resource["properties"]["device"],
                        "get-etherswitching-table.json",
                        parameters={"id": up_dev["port"].lower(), "model": model},
                        headers=None,
                    )
                    response = mac_response.json()["result"]

                    if model == "EX":
                        self.logger.debug("***EX RESPONSE***")
                        self.logger.debug(response)
                        try:
                            entries = response["ethernet-switching-table-information"]["ethernet-switching-table"][
                                "mac-table-entry"
                            ]
                            for entry in entries:
                                if entry["mac-vlan"] in mgmt_vlans:
                                    mac_address = entry["mac-address"]

                        except KeyError as err:
                            self.logger.debug("**EX ENTRY RESPONSE ERROR: {}".format(err))
                            mac_address = "*"

                    elif model in ["QFX", "ACX"]:
                        self.logger.debug("***HUB AGG RESPONSE***")
                        self.logger.debug(response)
                        try:
                            entries = response["l2ng-l2ald-interface-macdb-vlan"]["l2ng-l2ald-mac-entry-vlan"][
                                "l2ng-mac-entry"
                            ]
                            for entry in entries:
                                if entries[entry] in mgmt_vlans:
                                    mac_address = entries["l2ng-l2-mac-address"]

                        except KeyError as err:
                            self.logger.debug("**HUB AGG ENTRY RESPONSE ERROR: {}".format(err))
                            mac_address = "*"

                    t -= 5
                    if t == 20 and not mac_repopulated:
                        try:
                            # Best Effort attempt to ping possible CPE IPs to repopulate MAC address
                            mac_repopulated = self.repopulate_mac()
                        except Exception as ex:
                            self.logger.info(f"Exception during mac repopulation attempt: {ex}")

                    time.sleep(5)

            if t == 0:
                self.status_messages("Timed out waiting for CPE to show up in MAC table", True, "TULIP10611")
                self.exit_error("Timed out waiting for Mac to be learned on {}".format(up_dev["tid"]))

            self.logger.debug("Returning MAC ADDRESS: %s" % mac_address)
            return mac_address

        except Exception:
            status_mesg = (
                "Unable to get MAC Address for CPE - Ensure device is connected, light"
                " is verified, and CPE is defaulted (with pre-config applied if"
                " appropriate), then select 'Try Again'. After a second failed attempt,"
                " call Service Activation Support Team for assistance at 844.896.5784 -"
                " Option 1, 2  Monday through Friday from 7am to 7pm CST."
            )
            self.status_update(status_mesg, True, "TULIP10610")
            self.exit_error(status_mesg)

    def repopulate_mac(self):
        """
        Process to attempt traffic generation to repopulate a mac address that has aged out of the switching table
        :return: Boolean used to ensure this process is attempted only once during an activation
        """
        all_mgmt_macs = self.get_all_mgmt_macs()
        self.logger.info(f"MGMT_MACS: {all_mgmt_macs}")
        if len(all_mgmt_macs) == 0:
            self.logger.info(
                "NO MAC ADDRESS FOUND ON UPSTREAM DEVICE ASSOCIATED TO STANDARD MANAGEMENT VLAN NAMES - CANNOT REPOPULATE MAC ADDRESS"
            )
            return True

        mgmt_arp_table = self.get_arp_table()
        self.logger.info(f"mgmt_arp_table: {mgmt_arp_table}")
        if len(mgmt_arp_table) == 0:
            self.logger.info("NO IPS ARPING ON IRB INTERFACES - CANNOT REPOPULATE MAC ADDRESS")
            return True

        rtr_int = self.find_router_interface(mgmt_arp_table, all_mgmt_macs)
        self.logger.info(f"router interface: {rtr_int}")
        if not rtr_int:
            self.logger.info(
                "NO MANAGEMENT IPS ARPING ON PE ROUTER INTERFACE TO UPSTREAM DEVICE - CANNOT REPOPULATE MAC ADDRESS"
            )
            return True

        mgmt_arp_on_int = self.narrow_arp_by_interface(mgmt_arp_table, rtr_int)
        self.logger.info(f"mgmt_arp_on_int: {mgmt_arp_on_int}")

        orphaned_ips = self.find_orphaned_ips(mgmt_arp_on_int, all_mgmt_macs)
        self.logger.info(f"orphaned_ips: {orphaned_ips}")
        if len(orphaned_ips) == 0:
            self.logger.info("NO UNASSOCIATED IPS ARPING - CANNOT REPOPULATE MAC ADDRESS")
            return True

        ping_results = self.ping_ip_list(orphaned_ips)
        self.logger.info(f"PING_RESULTS: {ping_results}")

        return True

    def ping_ip_list(self, orphaned_ips):
        """
        Ping each IP in a list one time to generate traffic and hopefully repopulate the mac address in switching table
        :param orphaned_ips: List - IPs ARPing on PE_Router but not tied to MAC on Upstream Device
        :return ping_responses: List - Dictionaries with IP address and any response to ping received
        """
        ping_responses = []
        for ip_addy in orphaned_ips:
            response = verbose_ping(ip_addy, unit="ms", count=1, timeout=0.1)
            if response is not None:
                mod_resp = str(int(response)) + "ms"
                ping_responses.append({ip_addy: mod_resp})
            else:
                ping_responses.append({ip_addy: "unreachable"})

        return ping_responses

    def find_orphaned_ips(self, arp_table, mac_addresses):
        """
        Identify and IPs in the arp_table that are not aligned with mac_addresses in list
        :param arp_table: Dictionary - ARP Table details from PE Router
        :param mac_addresses: List - mac addresses on upstream device connected to management vlan
        :return orphaned_ips: List - IPs in ARP table or PE Router that are not aligned with MAC address from mac table on Upstream Device
        """
        orphaned_ips = []
        for entry in arp_table:
            if entry["mac-address"] not in mac_addresses:
                orphaned_ips.append(entry["ip-address"])

        return orphaned_ips

    def narrow_arp_by_interface(self, arp_table, interface):
        """
        Narrow down the ARP Table to only those tied to the provided interface
        :param arp_table: Dictionary - ARP Table details from PE Router
        :param interface: String - Interface to cross reference with arp_table
        :return arp_on_interface: Dictionary - ARP Entries aligned with interface
        """
        arp_on_interface = []
        for arp_entry in arp_table:
            if arp_entry["interface-name"] == interface:
                arp_on_interface.append(arp_entry)

        return arp_on_interface

    def find_router_interface(self, arp_table, mac_table):
        """
        Determine the interface on PE Router facing the Upstream Device
        :param arp_table: Dictionary - ARP Table details from PE Router
        :param mac_table: List - mac addresses on upstream device
        :return rtr_interface: String - Iterface on PE Router facing the Upstream Device
        """
        rtr_interface = False
        for mac in mac_table:
            for arp_entry in arp_table:
                if arp_entry["mac-address"] == mac:
                    rtr_interface = arp_entry["interface-name"]
                    break

        return rtr_interface

    def get_arp_table(self, interface="|irb.99"):
        """
        Obtain ARP Table for specified interface (default is irb.99 - management IPs on that router)
        :param interface: Default to management IPs, but specific phyical interface can also be used
        :return: arp_response - Dictionary of arp query response
        """
        router_session = self.pe_router_nf["providerResourceId"]
        arp_response = self.execute_ra_command_file(
            router_session, "get-arp-query.json", parameters={"uniqueid": interface}, headers=None
        )
        arp_response = arp_response.json()["result"]["properties"]["result"]
        self.logger.info(f"ARP_RESPONSE: {arp_response}")

        return arp_response

    def get_all_mgmt_macs(self):
        """
        Obtain all mac addresses tied to one of the management vlan names on the upstream device
        :return: mgmt_macs - List of mac addresses tied to management vlan
        """
        mgmt_vlans = ["MGMT", "CPEMGMT"]
        full_switching_table = self.execute_ra_command_file(
            self.tpe_resource["properties"]["device"],
            "get-etherswitching-table.json",
            parameters=None,
            headers=None,
        )

        switching_table = full_switching_table.json()["result"]
        self.logger.info(f"switching_table: {switching_table}")
        mgmt_macs = []

        if switching_table.get("ethernet-switching-table-information"):
            all_learned_macs = switching_table["ethernet-switching-table-information"]["ethernet-switching-table"][
                "mac-table-entry"
            ]
            vlan_name = "mac-vlan"
            mac_address = "mac-address"

        else:
            all_learned_macs = switching_table["l2ng-l2ald-rtb-macdb"]["l2ng-l2ald-mac-entry-vlan"]["l2ng-mac-entry"]
            vlan_name = "l2ng-l2-mac-vlan-name"
            mac_address = "l2ng-l2-mac-address"

        for mac in all_learned_macs:
            self.logger.info(f"Loop mac: {mac}")
            if mac[vlan_name] in mgmt_vlans and mac[mac_address] != "*":
                mgmt_macs.append(mac[mac_address])

        return mgmt_macs

    def find_ip(self, pe_rtr, port=None, mac=None):
        """
        Obtain IP Address
        :param pe_rtr: Dictionary with PE router details
        :param port: String required when CPE connects directly to PE router
        :param mac: String required when CPE does not connect directly to PE router
        :return: String ip
        """
        err_status_mesg = (
            "Unable to get IP Address for CPE - Ensure device is connected, light is"
            " verified, and CPE is defaulted (with pre-config applied if appropriate),"
            " then select 'Try Again'. After a second failed attempt, call Service"
            " Activation Support Team for assistance at 844.896.5784 - Option 1, 2"
            " Monday through Friday from 7am to 7pm CST."
        )
        try:
            irb_interface = "|irb.99"
            ip = None
            t = 30
            block_ping_performed = False
            router_session = pe_rtr["providerResourceId"]
            arping_ips = []

            if mac:

                while ip is None and t > 0:
                    arp_response = self.execute_ra_command_file(
                        router_session, "get-arp-query.json", parameters={"uniqueid": irb_interface}, headers=None
                    )

                    arp_response = arp_response.json()["result"]["properties"]["result"]
                    arp_response = arp_response if isinstance(arp_response, list) else [arp_response]
                    for arp_entry in arp_response:
                        arping_ips.append(arp_entry["ip-address"])
                        if arp_entry["mac-address"] == mac:
                            ip = arp_entry["ip-address"]
                    self.logger.info(ip)
                    t -= 5
                    if t < 20 and not block_ping_performed and ip is None:
                        self.ping_irb_blocks(router_session, arping_ips)
                        block_ping_performed = True
                    time.sleep(5)
            else:
                mgmt_interface = port.lower() + ".99"
                while ip is None and t > 0:
                    arp_response = self.execute_ra_command_file(
                        self.tpe_resource["properties"]["device"],
                        "get-arp-query.json",
                        parameters={"uniqueid": irb_interface},
                        headers=None,
                    )

                    arp_response = arp_response.json()["result"]["properties"]["result"]
                    arp_response = arp_response if isinstance(arp_response, list) else [arp_response]
                    for arp_entry in arp_response:
                        arping_ips.append(arp_entry["ip-address"])
                        if mgmt_interface in arp_entry["interface-name"]:
                            ip = arp_entry["ip-address"]

                    t -= 5
                    if t < 20 and not block_ping_performed and ip is None:
                        self.ping_irb_blocks(router_session, arping_ips)
                        block_ping_performed = True
                    time.sleep(5)

            if t == 0:
                self.status_update(err_status_mesg, True, "TULIP10710")
                self.exit_error(err_status_mesg)

            return ip

        except Exception:
            self.status_update(err_status_mesg, True, "TULIP10720")
            self.exit_error(err_status_mesg)

    def get_mgmt_blocks(self, prid):
        ra = RaCutThrough()
        mgmt_blocks = []
        irbs = []
        data = {}
        data["name"] = "irb.99"

        irb_99 = ra.execute_ra_command_file(prid, "get-interfaces-config.json", parameters=data, headers=None).json()[
            "result"
        ]

        for interface in irb_99["configuration"]["interfaces"]:
            if interface == "irb":
                irbs.append(irb_99["configuration"]["interfaces"][interface])

        for irb in irbs[0]["unit"]:
            if irb["name"] == "99":
                for addy in irb["family"]["inet"]["address"]:
                    mgmt_blocks.append(addy["name"])

        return mgmt_blocks

    def block_ping(self, subnet, arping_ips=[]):
        network = ipaddress.ip_network(subnet, strict=False)
        responses = {subnet: []}
        avoid_ips = arping_ips
        self.logger.info(f"IN BLOCK PING - THE IP NETWORK: {network}")
        # No need to ping the subnet, gateway, or broadcast IPs)
        subnet_ip = str(ipaddress.ip_address(str(network).split("/")[0]))
        gateway_ip = str(ipaddress.ip_address(str(network).split("/")[0]) + 1)
        broadcast_ip = str(ipaddress.ip_network(network).broadcast_address)
        sgb_ips = [subnet_ip, gateway_ip, broadcast_ip]
        avoid_ips.extend(sgb_ips)
        self.logger.info(f"I WILL BE AVOIDING the subnet, gateway, and broadcast IPs: {sgb_ips}")
        self.logger.info(f"FULL AVOID LIST: {avoid_ips}")

        for ip in network.hosts():
            if str(ip) not in avoid_ips:
                response = verbose_ping(str(ip), unit="ms", count=1, timeout=0.1)
                if response is not None:
                    mod_resp = str(int(response)) + "ms"
                    responses[subnet].append({str(ip): mod_resp})
                else:
                    responses[subnet].append({str(ip): "unreachable"})

        return responses

    def ping_irb_blocks(self, prid, arping_ips=[]):
        block_ping_responses = []
        mgmt_blocks = self.get_mgmt_blocks(prid)
        self.logger.info(f"MANAGEMENT BLOCKS (irb.99): {mgmt_blocks}")

        for ip_block in mgmt_blocks:
            block_ping_responses.append(self.block_ping(ip_block, arping_ips))

        self.logger.info(f"BLOCK_PING_RESPONSES: {block_ping_responses}")
        return block_ping_responses


class Terminate(CommonPlan):
    """This is the class that is called for the termination of a TULIP resource."""

    """
        Disable the enter_exit_log behavior to prevent creating a new instance of TraceLog that would
        not be terminated automatically after the TULIP terminates. Unless this is disabled,
        TraceLog resources will accumulate for each TULIP that we terminate.
    """
    EnableEnterExitLog = False
    all_dependencies_ids = []

    def process(self):

        self.soft_terminate_process()

        try:
            dependencies = self.bpo.resources.get_dependencies(self.resource["id"])

            self.logger.debug("Deleting resources. " + str(len(dependencies)))
            self.bpo.resources.delete_dependencies(
                self.resource["id"], None, dependencies, force_delete_relationship=True
            )

        except Exception as ex:
            self.logger.exception(ex)
            raise Exception(ex)
        pass
