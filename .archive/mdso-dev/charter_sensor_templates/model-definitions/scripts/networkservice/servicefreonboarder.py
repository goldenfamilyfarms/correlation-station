""" -*- coding: utf-8 -*-

ServiceDeviceOnboarder Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of ServiceDeviceOnboarder plans

"""
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    def process(self):
        self.logger.info("Nothing to Dd")
        pass

    def verify_both_nodes_onboard(self, circuit_details, link):
        """
        verifies both nodes on the link are
        available in BP
        """

        return_value = True
        node_ports = link.split("_")
        for np in node_ports:
            node_name = self.get_node_port_name_from_uuid(np)[0]
            self.logger.debug(node_name)
            node_state = self.get_node_bpo_state(circuit_details, node_name)
            self.logger.debug(node_state)
            if not node_state == self.BPO_STATES["AVAILABLE"]["state"]:
                self.logger.debug(
                    "node %s isnt deployed, hence skipping creating FRE AP for link %s " % (node_name, link)
                )
                return_value = False

        self.logger.info("return value chahiye %s " % str(return_value))
        return return_value

    def get_associated_ptp(self, fqdn, vendor, interface_name, node=None, circuit_details=None):
        """returns the PTP associated with the device (form CircuitDetails)"""
        return_value = None
        is_cpe_activate = False
        connection_param = None
        if node is not None and circuit_details is not None:
            network_service = self.get_associated_network_service_for_resource(self.params["resourceId"])
            reachable_via = self.get_node_reachability(circuit_details, node)
            device_role = self.get_node_role(circuit_details, node)
            if network_service["orchState"] == "active" and device_role == "CPE":
                is_cpe_activate = True

            connection_param = "IP" if is_cpe_activate is True or reachable_via == "IP" else "FQDN"

        if is_cpe_activate is True or connection_param == "IP":
            host = self.get_node_management_ip(circuit_details, node)
        else:
            host = fqdn

        network_function = self.get_network_function_by_host(host)
        if network_function is None:
            msg = "Network Function does not exist for " + host
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
            self.exit_error(msg)

        lookup = self.COMMON_TYPE_LOOKUP[vendor]
        resource_type = lookup["INTERFACE_TYPE"]

        for dependent in self.get_dependents(
            network_function["id"], resource_type, recursive=True, exception_on_failure=True
        ):
            ptp_name = dependent["label"].upper()
            if "data" in dependent["properties"].keys() and "attributes" in dependent["properties"]["data"].keys():
                # THIS IS A TPE_FRE PTP
                ptp_name = dependent["properties"]["data"]["attributes"].get("nativeName")
                if ptp_name:
                    ptp_name = ptp_name.upper()

            if ptp_name == interface_name.upper().replace(" ", "-") or ptp_name == interface_name.replace(
                "ETH-PORT", "ETH_PORT"
            ):
                return_value = dependent
                break

        self.logger.info("Returning PTP: " + str(return_value))
        return return_value

    def is_ptp_associated_with_link(self, ptp_id):
        """returns true if the link is associated with the PTP"""
        return_value = False
        deps = self.get_dependents_by_type_and_query(
            ptp_id, self.BUILT_IN_FRE_TYPE, query="properties.networkRole:FREAP"
        )
        if len(deps) > 0:
            return_value = True

        return return_value
