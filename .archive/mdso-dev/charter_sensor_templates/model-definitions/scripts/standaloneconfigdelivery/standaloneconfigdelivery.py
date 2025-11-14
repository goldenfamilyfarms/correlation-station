import json
import time
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from ra_plugins.ra_cutthrough import RaCutThrough
import ipaddress
from ping3 import verbose_ping


class Activate(CommonPlan):
    """
    Activation Class for Standalone Configuration Delivery (CPEA Phase3)
    """

    def process(self):
        # STEP 1. Build Equipment Dictionaries Based on Input
        self.cpe_ip = None
        self.status_update("Step 1: Preparing Data for Standalone Config Delivery")
        self.logger.info("Step 1: Preparing Data for Standalone Config Delivery")

        try:
            cpe = {}
            cpe["fqdn"] = self.properties["target_device"].upper()
            cpe["vendor"] = self.properties["target_vendor"].upper()
            cpe["model"] = self.properties["target_model"].upper()
            cpe["tid"] = cpe["fqdn"].split(".")[0].upper()
            self.cpe_tid = cpe["tid"]

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
            self.status_update("Unable to Process Provided Data", True, "10100")
            self.exit_error("Unable to Process Provided Data: %s" % self.properties)

        # STEP 2. Onboard or Resync Upstream Equipment, Offboard CPE
        self.status_update("Step 2: Obtaining, Onboarding, and Offboarding Equipment as Needed")
        self.logger.info("Step 2: Obtaining, Onboarding, and Offboarding Equipment as Needed")

        # Check for Onboard CPE and Delete if There
        nf_resource_type = self.get_network_function_resource_type_by_vendor(cpe["vendor"])
        if cpe["vendor"].upper() not in ["RAD", "ADVA"]:
            self.status_update("CPE Vendor Unsupported", True, "10200")
            self.exit_error("CPE Vendor Unsupported: %s" % cpe["vendor"])

        try:
            cpe_net_func = self.get_resource_by_type_and_label(nf_resource_type, cpe["tid"], no_fail=True)
            self.logger.info("&&&&&&&&&&&& Step 2. CPE Network Function &&&&&&&&&&&&&&&&&")
            self.logger.info(cpe_net_func)

            if cpe_net_func:
                self.delete_resource(cpe_net_func["id"])

            # Check for Upstream Equipment, Resync or Onboard as Needed
            devices_to_onboard = []

            pe_router_nf = self.get_onboard_device(pe_router["fqdn"])
            upst_device_nf = self.get_onboard_device(upst_device["fqdn"])

            self.logger.info("================= pe_router_nf: ============================")
            self.logger.info(pe_router_nf)
            self.logger.info("================= upst_device_nf: ============================")
            self.logger.info(upst_device_nf)

            if pe_router_nf is None:
                devices_to_onboard.append(pe_router)
                self.logger.info("I will be onboarding %s" % pe_router["tid"])
            else:
                self.logger.info("Resyncing %s" % pe_router["tid"])
                self.bpo.market.post("/resources/{}/resync".format(pe_router_nf["id"]))

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
                    pe_router_nf = self.get_onboard_device(pe_router["fqdn"])
                    if upst_device["pe"]:
                        upst_device_nf = pe_router_nf
                else:
                    upst_device_nf = self.get_onboard_device(upst_device["fqdn"])

            self.logger.info("I should be done onboarding stuff now")
            pe_router["model"] = pe_router_nf["properties"]["type"]
            upst_device["model"] = upst_device_nf["properties"]["type"]
            self.pe_prid = pe_router_nf["providerResourceId"]
            self.upst_nfid = upst_device_nf["id"]

        except Exception:
            self.status_update("Unable to Obtain, Onboard, and/or Offboard Equipment", True, "10201")
            self.exit_error(
                "Unable to Obtain, Onboard, and/or Offboard Equipment: %s, %s" % (pe_router["tid"], upst_device["tid"])
            )

        # STEP 3a. Check Upstream Port Status and Activate if Needed
        self.status_update("Step 3a: Check Port Status and Activate Port if Needed")
        self.logger.info("Step 3a: Check Port Status and Activate Port if Needed")

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
                            self.status_update(status_mesg, True, "10301")
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
            self.status_update(status_mesg, True, "10301")
            self.exit_error(status_mesg)

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
                self.status_update(status_mesg, True, "10302")
                self.exit_error(status_mesg)

        except Exception:
            status_mesg = "Unable to Turn Up Port: " + upst_device["tid"] + " " + upst_device["port"]
            self.status_update(status_mesg, True, "10302")
            self.exit_error(status_mesg)

        # STEP 3b. Check Upstream Port Status and Activate if Needed
        self.status_update("Step 3b: Check Port Status and Activate Port if Needed")
        self.logger.info("Step 3b: Check Port Status and Activate Port if Needed")

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
            self.status_update(status_mesg, True, "10303")
            self.exit_error("CPE-Facing port UP DOWN - Layer 1 Issue")

        # STEP 4. Get MAC Address and IP Address for CPE
        self.status_update("Step 4: Get MAC Address and IP Address for CPE")
        self.logger.info("Step 4: Get MAC Address and IP Address for CPE")

        try:
            if upst_device["pe"] is False:
                mac_address = self.get_mac(upst_device)
                self.cpe_ip = self.find_ip(pe_rtr=pe_router_nf, mac=mac_address)
            else:
                self.cpe_ip = self.find_ip(pe_rtr=pe_router_nf, port=upst_device["port"])

            # Update Standalone Resource with CPE IP
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip": self.cpe_ip}})

        except Exception:
            status_mesg = (
                "Unable to Get Mac Address or IP Address for CPE - Ensure device is connected,"
                " light is verified, and CPE is defaulted (with pre-config applied if appropriate)."
                " Then select 'Try Again'. After a second failed attempt, call Service"
                " Activation Support Team for assistance at 844.896.5784 - Option 1, 2  Monday"
                " through Friday from 7am to 7pm CST."
            )
            self.status_update(status_mesg, True, "10400")
            self.exit_error(status_mesg)

        # STEP 5. Onboard CPE
        self.status_update("Step 5: Onboarding CPE - %s - %s - %s" % (cpe["tid"], cpe["vendor"], cpe["model"]))
        self.logger.info("Step 5: Onboarding CPE - %s - %s - %s" % (cpe["tid"], cpe["vendor"], cpe["model"]))

        # Check for CPE Already and STILL Onboard (After Step 2 Deletion)
        try:
            cpe_net_func = self.get_resource_by_type_and_label(nf_resource_type, cpe["tid"], no_fail=True)
            self.logger.info("&&&&&&&&&&&& Step 5. CPE Network Function &&&&&&&&&&&&&&&&&")
            self.logger.info(cpe_net_func)

        except Exception:
            status_mesg = "Failed During PreOnboarding Check for " + cpe["tid"]
            self.status_update(status_mesg, True, "10500")
            self.exit_error(status_mesg)

        if cpe_net_func:
            status_mesg = f"{cpe['tid']} Already Onboard and Unable to Delete"
            self.status_update(status_mesg, True, "10501")
            self.exit_error(status_mesg)

        # Onboard CPE
        self.onboard_cpe(cpe)

        # STEP 5a. Best Effort Attempt To Obtain Light Levels
        self.status_update("Step 5a: Best Effort Attempt To Obtain Light Levels")
        self.logger.info("Step 5a: Best Effort Attempt To Obtain Light Levels")

        try:
            self.get_light_levels(self.upst_nfid, self.target_nfid)
        except Exception:
            pass

        # STEP 6. Implementing Secret Passwords for Configuration
        self.status_update("Step 6: Decrypting Configuration")
        self.logger.info("Step 6: Decrypting Configuration")

        try:
            creds = {}

            # Grabbing Credentials From Resource
            cpea_creds = self.bpo.market.get(
                "/resources?resourceTypeId={}&p=label%3A{}&obfuscate=false&offset=0&limit=1000".format(
                    "charter.resourceTypes.CPEACreds", "default"
                )
            )["items"][0]
            creds["snmp"] = cpea_creds["properties"]["SNMPstring"]
            creds["NOC"] = cpea_creds["properties"]["credentials"]["NOC_password"]
            creds["comm_engineer"] = cpea_creds["properties"]["credentials"]["comm_engineer_password"]
            creds["comm_support"] = cpea_creds["properties"]["credentials"]["comm_support_password"]
            creds["secret"] = cpea_creds["properties"]["credentials"]["ACS_secret"]

            self.config = []
            ise_per_command = "command-authorization 1st-method tacacsplus 2nd-method local netconf-include"
            exit_all = "exit all"
            end_add_required = False
            add_to_end = [
                exit_all,
                f"configure management access {ise_per_command}",
            ]

            for conf_line in self.properties["cpe_config"]:
                if "$$$" in conf_line:
                    self.config.append(self.crypt_keeper(conf_line, creds))
                elif ise_per_command in conf_line:
                    self.logger.info(
                        f"Found ISE per command config line: {conf_line} - will be adding it to end of config"
                    )
                    self.config.append(exit_all)
                    end_add_required = True
                elif conf_line == "save" and end_add_required:
                    add_to_end.append(conf_line)
                    self.config.append(exit_all)
                else:
                    self.config.append(conf_line)

            if end_add_required:
                self.config.extend(add_to_end)

        except Exception:
            status_mesg = "Failed During Configuration Decryption"
            self.status_update(status_mesg, True, "10600")
            self.exit_error("Failed During Configuration Decryption - %s" % "charter.resourceTypes.CPEACreds ISSUE")

        # STEP 7. Implementation of Configuration on Target CPE
        self.status_update("Step 7: Delivering Configuration to Target CPE")
        self.logger.info("Step 7: Delivering Configuration to Target CPE")
        cpe_nf = self.get_network_function_by_host_or_ip(self.cpe_ip)

        try:
            # 116 PRO Uses Netconf, Different Configuration Delivery Method
            if "116PRO" not in cpe["model"]:
                if cpe["vendor"] == "RAD":
                    time.sleep(30)
                cli_result = self.create_cli_manager()
                if cli_result:
                    self.logger.info(f"=-=-=-=-=-= cli_result: {cli_result}")
                    # This section can be utilized when error catching/handling is enhanced
                    # for result in cli_result["properties"]["output_results"]["command_results"]:
                    #     if "ERROR" in result["result"].upper():
                    #         self.logger.info(f"Failed Command: {result['command']}")
                    #         self.logger.info(f"Failed Command Response: {result['result']}")
                    #         status_mesg = "Unable to Deliver Configuration to " + cpe["tid"]
                    #         self.status_update(status_mesg, True, "10700")
                    #         self.exit_error(f"Failed Command Response: {result['result']}")

            else:
                self.netconf_config(cpe_nf["providerResourceId"])

            # $$$$$$$$$$$$$$$ Standalone Config Delivery Complete $$$$$$$$$$$$$$$
            self.status_update("CPE AUTO-ACTIVATION IS NOW COMPLETE")
            time.sleep(10)
        except Exception:
            status_mesg = "Unable to Deliver Configuration to " + cpe["tid"]
            self.status_update(status_mesg, True, "10700")
            self.exit_error(status_mesg)

        # POST DELIVERY 1. Best Effort ISE Push
        self.status_update("Post Delivery 1. Good faith effort to push CPE into ISE")

        self.logger.info("Pushing CPE to ISE")
        self.best_effort_ise(cpe)

        # POST DELIVERY 2. Best Effort Attempt to Update Management IP in Granite
        self.status_update("Post Delivery 2. Best Effort Attempt to Update Management IP in Granite")
        self.logger.info("=== UPDATING CPE MGMT IP IN GRANITE - BEST EFFORT ===")
        ip_update_response = self.update_granite_ip()
        self.logger.info(f"ip_update_response: {ip_update_response}")

        # POST DELIVERY 3: Best Effort Remove Default Credential CPE Network Function
        self.status_update("Post Delivery 3. Best Effort Removal of CPE NF with Default Credentials")
        try:
            self.delete_resource(cpe_nf["id"])
        except Exception as e:
            self.logger.info(
                f"Failed during best-effort removal of CPE NF w default credentials. Function designed to pass. Exception:{e}"
            )

        # $$$$$$$$$$$$$$$ Fully Complete $$$$$$$$$$$$$$$
        self.status_update("Standalone Config Completed Including Post Delivery")

    def status_update(self, status_msg, err_msg=False, err_code=None):
        """
        Updates the cpe_activation, cpe_activation_error and scod_error_code
        :param status_msg: String to update cpe_activation/cpe_activation_error
        :param err_msg: Boolean to identify when failing
        :param err_code: String for error reporting
        """
        props = {}
        if err_msg:
            props["cpe_activation_error"] = status_msg
            props["scod_error_code"] = err_code
        else:
            props["cpe_activation"] = status_msg

        self.bpo.resources.patch_observed(self.resource["id"], {"properties": props})
        if err_msg and self.cpe_ip:
            try:
                self.logger.info("=== UPDATING CPE MGMT IP IN GRANITE - BEST EFFORT ===")
                ip_update_response = self.update_granite_ip()
                self.logger.info(f"ip_update_response: {ip_update_response}")
            except Exception as e:
                self.logger.info(
                    f"Failed during best-effort Mgmt IP update in Granite. Function designed to pass. Exception:{e}"
                )

    def netconf_config(self, nf_provider_resource_id):
        """
        Deliver configuration to 116PRO via netconf
        :param nf_provider_resource_id: String to providerResourceId of the network function
        """
        self.cutthrough = RaCutThrough()
        self.logger.info(self.config)

        data = ""
        for config_portion in self.config:
            data = data + config_portion

        self.logger.info("===DATA (from self.config): %s" % data)

        self.logger.info("ATTEMPTING TO SEND 116PRO COMMANDS")
        self.cutthrough.execute_ra_command_file(
            nf_provider_resource_id, "cutthrough-standalone-config.json", parameters=data, headers=None
        )

    def get_onboard_device(self, fqdn):
        """
        Find onboard equipment in MDSO
        :param fqdn: String to use actual FQDN or IP address
        :return: device's network function resource
        """
        device_resource = self.get_network_function_by_host_or_ip(fqdn)

        return device_resource

    def onboard_device(self, dvc, fqdn=True, CPE_NID=False):
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

        if CPE_NID:
            onboard_details["properties"]["operation"] = "CPE_ACTIVATION"

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
                self.status_update(status_mesg, True, "10302")
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

                    self.status_update(status_mesg, True, "10412")
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
                self.status_messages("Timed out waiting for CPE to show up in MAC table", True, "10411")
                self.exit_error("Timed out waiting for Mac to be learned on {}".format(up_dev["tid"]))

            self.logger.debug("Returning MAC ADDRESS: %s" % mac_address)
            return mac_address

        except Exception:
            status_mesg = (
                "Unable to Get Mac Address for CPE - Ensure device is connected,"
                " light is verified, and CPE is defaulted (with pre-config applied"
                " if appropriate). Then select 'Try Again'. After a second failed"
                " attempt, call Service Activation Support Team for assistance at"
                " 844.896.5784 - Option 1, 2  Monday through Friday from 7am to 7pm CST."
            )
            self.status_update(status_mesg, True, "10410")
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
                status_mesg = "Timed Out Waiting for IP Address to Show in ARP Table"
                self.status_update(status_mesg, True, "10421")
                self.exit_error(status_mesg)

            return ip

        except Exception:
            status_mesg = "Unable to Get IP Address for CPE"
            self.status_update(status_mesg, True, "10420")
            self.exit_error(status_mesg)

    def ping_irb_blocks(self, prid, arping_ips=[]):
        block_ping_responses = []
        mgmt_blocks = self.get_mgmt_blocks(prid)
        self.logger.info(f"MANAGEMENT BLOCKS (irb.99): {mgmt_blocks}")

        for ip_block in mgmt_blocks:
            block_ping_responses.append(self.block_ping(ip_block, arping_ips))

        self.logger.info(f"BLOCK_PING_RESPONSES: {block_ping_responses}")
        return block_ping_responses

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

    def update_granite_ip(self):
        try:
            mgmt_blocks = self.get_mgmt_blocks(self.pe_prid)
            self.logger.info(f"MANAGEMENT BLOCKS (irb.99): {mgmt_blocks}")
            self.logger.info(f"CPE_IP: {self.cpe_ip}")

            mgmt_subnet = self.get_mgmt_subnet(mgmt_blocks)
            self.logger.info(f"mgmt_subnet: {mgmt_subnet}")

            ip_w_cidr = "/".join([str(self.cpe_ip), str(mgmt_subnet).split("/")[-1]])
            ip_updated = False
            ip_updated = self.ip_update(self.cpe_tid, ip_w_cidr)
            self.logger.info("=========== RESULT OF GRANITE CPE IP UPDATE ============")
            self.logger.info(f"ip_updated: {ip_updated.json()}")

            return ip_updated.json()

        except Exception as e:
            self.logger.info(
                f"Failed during best-effort Mgmt IP update in Granite. Function designed to pass. Exception:{e}"
            )

        return "Mgmt IP update in Granite failed"

    def get_mgmt_subnet(self, mgmt_blocks):
        for block in mgmt_blocks:
            network_ip = ipaddress.ip_address(block.split("/")[0]) - 1
            cidr = block.split("/")[-1]
            nu_block = "/".join([str(network_ip), str(cidr)])
            if ipaddress.ip_address(self.cpe_ip) in ipaddress.ip_network(nu_block):
                return str(block)

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

    def create_cli_manager(self):
        """
        Create CLI manager object which delivers configuration
        """
        cli_manager_product = self.get_built_in_product(self.BUILT_IN_CLI_MANAGER_TYPE)
        label = self.cpe_ip + ".cli_manager"
        cli_manager_details = {
            "label": label,
            "productId": cli_manager_product["id"],
            "properties": {
                "configuration": self.config,
                "ipAddress": self.cpe_ip,
                "operation": "CPE_ACTIVATION",
                "ignore_errors": True,
            },
        }
        self.logger.debug("Sending following commands: " + str(self.config))
        delivery_result = self.bpo.resources.create(self.params["resourceId"], cli_manager_details)
        self.logger.info(f"delivery_result: {delivery_result.resource}")

        return delivery_result.resource

    def crypt_keeper(self, conf_line, creds):
        """
        Replaces generic strings with secure strings maintained internally in MDSO
        :param conf_line: String line of configuration destined for device
        :param creds: Dictionary of secure strings maintained internally in MDSO
        :return: configuration_line with generic string replaced with secure string
        """
        try:
            for cred in creds.keys():
                if cred in conf_line:
                    repl = "$$$" + cred
                    return conf_line.replace(repl, creds[cred])
        except Exception:
            self.status_update("Invalid Data Provided in Configuration", True)
            self.exit_error("Invalid CPEACreds Object $$$ in Configuration: %s" % conf_line)

    def best_effort_ise(self, cpe):
        """
        Calls functions to update CPE to utilise TACACS logins and add CPE to ISE
        :param cpe_model: String identifying model of CPE
        """
        try:
            # Push Update to ISE/ISIN
            self.iseupdate(cpe, self.cpe_ip)
        except Exception as e:
            self.logger.info("Failed during good faith CPE to ISE. Function designed to pass. Exception:{}".format(e))

    def onboard_cpe(self, cpe):
        try:
            cpe["ip"] = self.cpe_ip
            cpe_onboard_result = self.onboard_device(cpe, False, True)
            self.logger.info("=========== dvc_onboard_result for %s ===========" % cpe["tid"])
            self.logger.info(cpe_onboard_result)
            nf_resource_type = self.get_network_function_resource_type_by_vendor(cpe["vendor"])
            status_checks = 12
            wait_secs = 5

            for status_check in range(1, status_checks + 1):
                cpe_nf = self.get_resource_by_type_and_label(nf_resource_type, cpe["tid"], no_fail=True)
                self.target_nfid = cpe_nf["id"]
                orchstate = cpe_nf["orchState"].upper()
                commstate = cpe_nf["properties"]["communicationState"].upper()
                if orchstate == "ACTIVE" and commstate == "AVAILABLE":
                    self.logger.info("===== ACTIVE & AVAILABLE - CARRY ON =====")
                    break
                elif status_check == status_checks:
                    self.logger.info("CPE Network Function Must Be Active and Available, but is not.")
                    self.logger.info(f"CPE orchState: {orchstate}, communicationState: {commstate}")
                    status_mesg = "Unable to Onboard " + cpe["tid"]
                    self.status_update(status_mesg, True, "10502")
                    self.exit_error(status_mesg)
                self.logger.info(
                    f"Waiting {wait_secs} seconds for CPE NF to be ACTIVE and AVAILABLE - Attempt {status_check} of {status_checks}"
                )
                self.logger.info(f"Current orchstate: {orchstate} | Current commstate: {commstate}")
                time.sleep(wait_secs)

        except Exception:
            status_mesg = "Unable to Onboard " + cpe["tid"]
            self.status_update(status_mesg, True, "10502")
            self.exit_error(status_mesg)

    def get_light_levels(self, upst_nfid, target_nfid):
        upstream_tid = self.properties["upstream_device_FQDN"].split(".")[0].upper()
        upstream_port = self.properties["upstream_port"].upper()

        target_tid = self.properties["target_device"].split(".")[0].upper()
        if self.properties.get("target_uplink"):
            target_port = self.properties["target_uplink"]
        else:
            target_port = "default_uplink"

        self.logger.info(f"Upstream Device: {upstream_tid}, port: {upstream_port}")
        self.logger.info(f"Target Device: {target_tid}, port: {target_port}")
        try:
            upstream_pill_details = self.create_pill_resource(upstream_tid, upst_nfid, upstream_port)
        except Exception:
            upstream_pill_details = {}
            dependencies = self.bpo.resources.get_dependencies(self.params["resourceId"])
            for dep in dependencies:
                if dep["label"] == f"{upstream_tid}_{upstream_port}-SCOD":
                    upstream_pill_details["pill_error"] = (
                        dep["properties"]["pill_error"] if dep["properties"].get("pill_error") else "NA"
                    )
                    upstream_pill_details["pill_error_code"] = (
                        dep["properties"]["pill_error_code"] if dep["properties"].get("pill_error_code") else "NA"
                    )

        try:
            target_pill_details = self.create_pill_resource(target_tid, target_nfid, target_port)
        except Exception:
            target_pill_details = {}
            dependencies = self.bpo.resources.get_dependencies(self.params["resourceId"])
            for dep in dependencies:
                if dep["label"] == f"{target_tid}_{target_port}-SCOD":
                    target_pill_details["pill_error"] = (
                        dep["properties"]["pill_error"] if dep["properties"].get("pill_error") else "NA"
                    )
                    target_pill_details["pill_error_code"] = (
                        dep["properties"]["pill_error_code"] if dep["properties"].get("pill_error_code") else "NA"
                    )

        self.bpo.resources.patch_observed(
            self.resource["id"], {"properties": {"upstream_pill_details": upstream_pill_details}}
        )
        self.bpo.resources.patch_observed(
            self.resource["id"], {"properties": {"target_pill_details": target_pill_details}}
        )

    def create_pill_resource(self, tid, nf_id, port):

        pill_prod_id = self.get_products_by_type_and_domain("charter.resourceTypes.postInstallLightLevels", "built-in")[
            0
        ]["id"]

        pill_label = f"{tid}_{port}-SCOD"
        pill_data = {
            "label": pill_label,
            "productId": pill_prod_id,
            "properties": {"device_tid": tid, "device_id": nf_id, "port": port},
        }

        cpe_pill = self.create_active_resource(pill_label, self.resource_id, pill_data, True, 30, 5, True)
        self.logger.info(f"Post Install Light Level Result: {cpe_pill}")
        pill_details = cpe_pill.resource["properties"]["pill_details"]
        return pill_details


class Terminate(CommonPlan):
    """
    placeholder for now
    """
