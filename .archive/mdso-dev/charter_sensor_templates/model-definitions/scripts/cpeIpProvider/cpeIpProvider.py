import time
import json
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.circuitDetailsHandler import CircuitDetailsHandler


class Activate(CommonPlan):
    """
    Process Placeholder
    """

    def process(self):
        self.logger.info("IP Provider Resource Info")
        self.logger.info(self.resource)
        cid = self.resource["properties"]["cid"]
        target_tid = self.resource["properties"]["target_device"]

        # Creating circuit details
        self.logger.info("==== ABOUT TO CALL CIRCUITDETAILSHANDLER ====")
        circuit_details_handler = CircuitDetailsHandler(plan=self, circuit_id=cid, operation="IP_GETTER")
        self.logger.info("==== TRYING TO SET CIRCUIT DETAILS ID FROM CIRCUITDETAILSHANDLER ====")
        circuit_details = circuit_details_handler.circuit_details

        cpe = {}
        cpe["tid"] = target_tid.upper()

        upst_device = {}
        pe_router = {}

        # Review and catalog topology details
        topo = 0
        if len(circuit_details["properties"]["topology"]) > 1:
            for node in circuit_details["properties"]["topology"][1]["data"]["node"]:
                if node["uuid"].upper() == cpe["tid"]:
                    topo = 1

        topo_node = circuit_details["properties"]["topology"][topo]["data"]["node"]
        topo_link = circuit_details["properties"]["topology"][topo]["data"]["link"]

        self.logger.info("TOPONODE")
        self.logger.info(topo_node)
        self.logger.info("TOPOLINK")
        self.logger.info(topo_link)

        if self.target_check(topo_node, target_tid) is False:
            cip_error = (
                "Provided CPE TID is not in Circuit Design. Please ensure that Circuit ID and Granite details are valid"
            )
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
            self.exit_error(cip_error)

        for link in topo_link:
            if link["uuid"].split("_")[-1].split("-")[0] == target_tid:
                upst_device["tid"] = link["uuid"].split("-")[0]

        for node in topo_node:
            if node["uuid"] == target_tid:
                cpe["topo_details"] = node
            elif node["uuid"] == upst_device["tid"]:
                upst_device["topo_details"] = node

            for item in node["name"]:
                if item["name"] == "Role" and item["value"] == "PE":
                    pe_router["topo_details"] = node
                    pe_router["tid"] = node["uuid"]

        # Determining if PE also == Upstream device
        upst_device["pe"] = True if upst_device["tid"] == pe_router["tid"] else False

        # Check that router an upstream device are onboarded (and if not onboard them)
        pe_router["fqdn"] = self.get_node_fqdn(circuit_details, pe_router["tid"])
        upst_device["fqdn"] = self.get_node_fqdn(circuit_details, upst_device["tid"])
        self.logger.info("PE ROUTER FQDN: %s" % pe_router["fqdn"])
        self.logger.info("UPSTREAM DEVICE FQDN %s" % upst_device["fqdn"])

        pe_router["vendor"] = self.get_node_vendor(circuit_details, pe_router["tid"]).upper()
        upst_device["vendor"] = self.get_node_vendor(circuit_details, upst_device["tid"]).upper()

        pe_router["port"] = self.get_node_client_interface(circuit_details, pe_router["tid"])
        upst_device["port"] = self.get_node_client_interface(circuit_details, upst_device["tid"])

        pe_router["model"] = self.get_node_model(circuit_details, pe_router["tid"]).upper()
        upst_device["model"] = self.get_node_model(circuit_details, upst_device["tid"]).upper()

        cip_error = self.device_el_check(pe_router, upst_device)
        self.logger.info("CIP ERROR: %s" % cip_error)

        if cip_error:
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
            self.exit_error(cip_error)

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
            self.bpo.market.post("/resources/{}/resync?full=true".format(pe_router_nf["id"]))

        if upst_device_nf is None and upst_device["pe"] is False:
            devices_to_onboard.append(upst_device)
            self.logger.info("I will be onboarding %s" % upst_device["tid"])
        elif upst_device["pe"] is False:
            self.bpo.market.post("/resources/{}/resync?full=true".format(upst_device_nf["id"]))

        self.logger.info("=== devices_to_onboard: %s" % devices_to_onboard)

        try:
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

            self.logger.info("***ONBOARDING COMPLETE***")
        except Exception:
            cip_error = "UNABLE TO SUCCESSFULLY ONBOARD DEVICES"
            self.logger.info(cip_error)
            self.logger.info(devices_to_onboard)
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
            self.exit_error(cip_error)

        time.sleep(5)
        # Identifying TPE resources for involved ports
        if upst_device["vendor"].upper() == "JUNIPER":
            upst_port = upst_device["port"].lower()
        elif upst_device["vendor"].upper() == "RAD":
            upst_port = "TPE_" + upst_device["port"] + "_PTP"

        self.logger.info("upst_port: %s" % upst_port)

        self.tpe_resource = self.get_tpe_by_name_and_host_return_errors(upst_device["fqdn"], upst_port)

        if "status" in self.tpe_resource.keys() and "not present" in self.tpe_resource["status"]:
            waiter = 30
            while waiter >= 0 and "status" in self.tpe_resource.keys() and "not present" in self.tpe_resource["status"]:
                time.sleep(5)
                self.tpe_resource = self.get_tpe_by_name_and_host_return_errors(upst_device["fqdn"], upst_port)
                waiter -= 5

        self.logger.info("************ TPE_RESOURCE *************")
        self.logger.info("tpe_resource: %s" % self.tpe_resource)

        if "status" in self.tpe_resource.keys():
            if "is not MDSO reachable" in self.tpe_resource["status"]:
                cip_error = self.tpe_resource["status"]
                self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
                self.exit_error(cip_error)

        # Checking port status
        port_status = self.check_port_status(upst_port, upst_device)

        port_status_message = "PORT STATUS: "

        port_status_fail = False

        if port_status["admin"].lower() == "down":
            port_status_message += "ADMIN DOWN"
            port_status_fail = True
        else:
            port_status_message += "ADMIN UP | "

            if port_status["oper"].lower() == "down":
                port_status_message += "OPERATIONALLY DOWN"
                port_status_fail = True
            else:
                port_status_message += "OPERATIONALLY UP"

        self.logger.info("PORT STATUS RESULTS: %s" % port_status_message)

        if port_status_fail is True:
            self.logger.info("FAILING OUT BECAUSE : %s" % port_status_message)
            cip_error = "Port NOT up/up"
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
            self.exit_error(cip_error)

        # Getting MAC and IP
        if upst_device["pe"] is False:
            mac_address = self.get_mac(upst_device)
            self.cpe_ip = self.find_ip(pe_rtr=pe_router_nf, mac=mac_address)
        else:
            self.cpe_ip = self.find_ip(pe_rtr=pe_router_nf, port=pe_router["port"])

        self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip": self.cpe_ip}})

    def onboard_device(self, dvc):
        """
        Function for onboarding equipment
        """
        device_name = dvc["tid"].upper()
        device_fqdn = dvc["fqdn"].upper()
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
                "device_ip": device_fqdn,
                "device_name": device_name,
                "device_vendor": vendor_name,
                "device_already_active": True,
            },
        }
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

    def get_onboard_device(self, fqdn):
        """
        This will be used to check if upstream device and pe router are onboard
        """
        device_resource = self.get_network_function_by_host_or_ip(fqdn)

        return device_resource

    def check_port_status(self, upst_port, upst_device):
        """
        Function to get port status (admin/oper)
        """
        self.logger.info("********* GET ADMIN STATUS *********")

        if upst_device["vendor"].upper() == "JUNIPER":
            admin_json = "get-interface.json"
            admin_params = {"name": upst_port}

        elif upst_device["vendor"].upper() == "RAD":
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

    def get_mac(self, up_dev):
        """
        Function to get MAC Address
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

            if vendor == "RAD":
                TPE_LBL = up_dev["tid"] + "::TPE_" + up_dev["port"] + "_IN_0"
                MTU_TPE = self.get_resource_by_type_and_label("tosca.resourceTypes.TPE", TPE_LBL, partial=True)
                self.logger.info("********* THE MTU_TPE FOR BRIDGE *********")
                self.logger.info("MTU_TPE: {}".format(MTU_TPE))
                bridge_flow_native_name = MTU_TPE["properties"]["data"]["attributes"]["nativeName"]
                self.logger.info("bridge_flow_native_name: %s" % bridge_flow_native_name)
                my_bridge_port = bridge_flow_native_name.rsplit("p")[-1]
                self.logger.info("bridge_port: %s" % my_bridge_port)

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

                mac_address = ":".join(mac_address.split("-")).lower()
                self.logger.info("FORMATTED MAC ADDRESS: {}".format(mac_address))

            elif vendor == "JUNIPER":
                mgmt_vlans = ["MGMT", "CPEMGMT"]
                juniper_aggs = ["EX", "QFX"]

                for device in juniper_aggs:
                    if device in model:
                        model = device

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

                elif model == "QFX":
                    self.logger.debug("***QFX RESPONSE***")
                    self.logger.debug(response)
                    try:
                        entries = response["l2ng-l2ald-interface-macdb-vlan"]["l2ng-l2ald-mac-entry-vlan"][
                            "l2ng-mac-entry"
                        ]

                        for entry in entries:
                            if entries[entry] in mgmt_vlans:
                                mac_address = entries["l2ng-l2-mac-address"]

                    except KeyError as err:
                        self.logger.debug("**QFX ENTRY RESPONSE ERROR: {}".format(err))

            if not mac_address:
                cip_error = "Issue obtaining CPE MAC Address"
                self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
                self.exit_error(cip_error)
        except Exception:
            cip_error = "Issue obtaining CPE MAC Address"
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
            self.exit_error(cip_error)

        self.logger.debug("Returning MAC ADDRESS: %s" % mac_address)
        return mac_address

    def find_ip(self, pe_rtr, port=None, mac=None):
        """
        Function to find IP Address
        """
        try:
            irb_interface = "|irb.99"
            ip = None
            t = 30

            if mac:
                router_session = pe_rtr["providerResourceId"]

                while ip is None and t > 0:
                    arp_response = self.execute_ra_command_file(
                        router_session, "get-arp-query.json", parameters={"uniqueid": irb_interface}, headers=None
                    )
                    arp_response = arp_response.json()["result"]["properties"]["result"]
                    self.logger.info("*****ARP RESPONSE*****")
                    self.logger.info(arp_response)

                    for arp_entry in arp_response:
                        if arp_entry["mac-address"] == mac:
                            ip = arp_entry["ip-address"]

                    self.logger.info("*****IP FROM ARP*****")
                    self.logger.info(ip)
                    t -= 5
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
                    self.logger.info("*****ARP RESPONSE*****")
                    self.logger.info(arp_response)

                    for arp_entry in arp_response:
                        if mgmt_interface in arp_entry["interface-name"]:
                            ip = arp_entry["ip-address"]

                    self.logger.info("*****IP FROM ARP*****")
                    self.logger.info(ip)
                    t -= 5
                    time.sleep(5)

            if t == 0:
                cip_error = "Unable to find IP in ARP table"
                self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
                self.exit_error(cip_error)
        except Exception:
            cip_error = "Issue obtaining CPE IP"
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": {"ip_provider_error": cip_error}})
            self.exit_error(cip_error)

        return ip

    def target_check(self, node_list, target_tid):
        """
        Function to validate input TID vs Circuit Details
        """
        tid_list = []
        for node in node_list:
            tid_list.append(node["uuid"])
        self.logger.info(tid_list)

        tid_in_design = True if target_tid in tid_list else False
        self.logger.info(tid_in_design)
        self.logger.info("TID IN DESIGN: %s" % tid_in_design)

        return tid_in_design

    def device_el_check(self, pe_router, upst_device):
        """
        Function to evaluate eligibility of devices on circuit
        """

        self.logger.info("PROVIDED ROUTER %s" % pe_router)
        self.logger.info("PROVIDED UPSTREAM DEVICE %s" % upst_device)

        el_pe_router_vendor = ["JUNIPER"]
        el_pe_router_model = ["MX"]
        el_upst_dev_vendor = ["JUNIPER", "RAD"]
        el_upst_dev_model = ["MX", "QFX", "EX", "2I", "220"]

        el_confirmed = []
        equip_check = {
            "rv": [pe_router["vendor"], "PE ROUTER VENDOR"],
            "rm": [pe_router["model"], "PE ROUTER MODEL"],
            "uv": [upst_device["vendor"], "UPSTREAM DEVICE VENDOR"],
            "um": [upst_device["model"], "UPSTREAM DEVICE MODEL"],
        }

        for router in el_pe_router_vendor:
            if router in pe_router["vendor"]:
                el_confirmed.append("rv")

        for model in el_pe_router_model:
            if model in pe_router["model"]:
                el_confirmed.append("rm")

        for vendor in el_upst_dev_vendor:
            if vendor in upst_device["vendor"]:
                el_confirmed.append("uv")

        for model in el_upst_dev_model:
            if model in upst_device["model"]:
                el_confirmed.append("um")

        for confirmed in el_confirmed:
            del equip_check[confirmed]

        self.logger.info("EQUIPMENT CHECK %s" % equip_check)

        el_error = None

        if len(equip_check) > 0:
            el_error = "Unsupported Device in Role: "
            for evf in equip_check:
                el_error = el_error + equip_check[evf][0] + " as " + equip_check[evf][1] + ". "

        self.logger.info("EL ERRORO %s" % el_error)

        return el_error


class Terminate(CommonPlan):
    def process(self):
        pass
