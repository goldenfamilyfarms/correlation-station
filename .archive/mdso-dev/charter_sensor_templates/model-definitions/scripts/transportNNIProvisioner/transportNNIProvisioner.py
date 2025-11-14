import sys
sys.path.append('model-definitions')
from scripts.circuitDetailsHandler import CircuitDetailsHandler

from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """This product provisions NEW NNI circuits on Juniper MX's.
    Can be built on existing devices but CANNNOT be built on LAG ports.
    """

    def process(self):
        self.circuit_id = self.properties["circuit_id"]
        self.logger.info("============== CIRCUIT DETAILS HANDLER ===================")
        self.transport_circuit_details_handlder = CircuitDetailsHandler(
            plan=self,
            circuit_id=self.circuit_id,
            circuit_details_id=self.circuit_details_id,
            operation="TRANSPORT",
        )
        self.transport_circuit_details_handlder.device_onboarding_process()
        self.circuit_details_id = self.transport_circuit_details_handlder.circuit_details_id
        self.circuit_details = self.bpo.resources.get(self.circuit_details_id)

        node_uuid = self.get_pe_nodes_from_circuit_details(self.circuit_details)[0].split(".")[0]
        port_name = self.get_node_client_interface(self.circuit_details, node_uuid)
        device_model = self.get_node_model(self.circuit_details, node_uuid)
        fqdn = self.get_node_fqdn(self.circuit_details, node_uuid)
        hostname = self.get_node_management_ip(self.circuit_details, node_uuid)
        self.nodeport = node_uuid + "-" + port_name
        port_role = self.get_port_role(self.circuit_details, self.nodeport)
        port_description = self.get_port_description(self.circuit_details, self.nodeport)
        self.port_description = port_description
        self.logger.info(f"{port_role}\n port description: {port_description}")

        self.logger.info("=================== Starting Interface Check =================")
        self.get_tpe_by_name_and_host_return_errors(fqdn, port_name.lower())
        port_status = self.check_port(fqdn, port_name.lower())
        try:
            if not self.device_eligible(device_model):
                self.exit_error(f"Ineligible Device Model\nDevice Model {device_model} Not Supported at This Time")

            if port_status == "down":
                self.check_apply_groups(fqdn, hostname, port_name.lower())
                self.provision_device(port_name.lower(), fqdn)
        except Exception as ex:
            self.exit_error(f"{ex} Provisioning Failed\nManual Provisioning required")

    def check_port(self, fqdn, port_name):
        self.logger.info("=========================== Starting Port Check =============================")
        tpe = self.get_tpe_by_name_and_host_return_errors(fqdn, port_name)
        if "properties" in tpe:
            properties = tpe["properties"]
            state = properties["state"]
            if state == "OOS":
                get_admin_state = self.execute_ra_command_file(
                    tpe["properties"]["device"], "get-interface.json", parameters={"name": port_name}, headers=None
                )
                get_admin_state = get_admin_state.json()["result"]
                admin_state = get_admin_state["interface-information"]["physical-interface"]["admin-status"]["#text"]
                return admin_state
            else:
                self.exit_error("Existing Services Found on interface.\nManual Provisioning required")

    def check_apply_groups(self, fqdn, hostname, port_name):
        self.logger.info("==================CHECKING APPLY GROUPS=======================")
        device = self.get_network_function_by_host_or_ip(fqdn, hostname)
        tpe = self.get_tpe_by_name_and_host_return_errors(fqdn, port_name)
        is_edna = self.check_is_edna(device["providerResourceId"])
        disablr = "TP_NNI" if is_edna else "NNI"
        disableif = "TP_DISABLEIF" if is_edna else "DISABLEIF"
        apply_groups = tpe["properties"]["data"]["attributes"]["additionalAttributes"]["apply-groups"]
        if disableif in apply_groups:
            apply_groups.remove(disableif)

        if disablr not in apply_groups:
            apply_groups.append(disablr)

        tpe["properties"]["data"]["attributes"]["additionalAttributes"]["apply-groups"] = apply_groups
        self.bpo.resources.patch(tpe["id"], {"discovered": False})
        self.bpo.resources.patch(tpe["id"], {"properties": tpe["properties"]})
        self.bpo.resources.patch(tpe["id"], {"discovered": True})

    def provision_device(self, port_name, fqdn):
        self.logger.info("===================== Starting Device Configuration =====================================")
        tpe = self.get_tpe_by_name_and_host_return_errors(fqdn, port_name)
        if "properties" in tpe:
            user_label_description = [" ", "", "", " "]
            description = self.port_description
            if tpe["properties"]["data"]["attributes"]["userLabel"] in user_label_description:
                tpe["properties"]["data"]["attributes"]["userLabel"] = description.replace(" ", "")

                self.bpo.resources.patch(tpe["id"], {"discovered": False})
                self.bpo.resources.patch(tpe["id"], {"properties": tpe["properties"]})
                self.bpo.resources.patch(tpe["id"], {"discovered": True})
            else:
                self.exit_error("Existing Interface on Port, Manual Provisioning Required")

    def userlabel_description(self):
        index = 0
        transport_id = self.get_port_transportId(self.circuit_details, self.nodeport)
        customer_address = self.get_customer_addresses(self.circuit_details)
        customer_zipcode = customer_address[index].split(" ")[-1]
        user_label_description = (
            transport_id + ":NNI1:" + customer_zipcode + ":" + self.circuit_details["properties"]["customerName"] + ":"
        )
        return user_label_description

    def device_eligible(self, device_model):
        # models that will be added later ['MX480', 'QFX5100', '220']
        device_whitelist = ["MX960"]
        eligible = False
        for device in device_whitelist:
            if device in device_model:
                eligible = True

        data = {"properties": {"eligible": eligible}}
        if not eligible:
            data["properties"]["failure_status"] = "Ineligible PE - {}".format(device_model)

        self.bpo.resources.patch_observed(self.resource["id"], data=data)
        self.logger.info("PE {} eligible: {}".format(device_model, eligible))
        return eligible


class Terminate(CommonPlan):
    pass
