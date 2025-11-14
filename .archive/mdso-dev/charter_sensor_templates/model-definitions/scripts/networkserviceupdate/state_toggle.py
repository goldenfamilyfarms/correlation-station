""" -*- coding: utf-8 -*-

BandwidthUpdate Plans

Versions:
   0.1 Dec 03, 2018
       Initial check in of CircuitDataCollection plans

"""

import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """this is the class that is called for the initial updation of the
    Network Service bandwidth. The only input it requires is the circuit_id
    associated with the service.
    """

    def process(self):
        self.circuit_id = self.properties["circuit_id"]
        self.circuit_res_id = self.properties["circuit_details_resource_id"]
        self.required_state = "ENABLED" if self.properties["required_state"] == "enable" else "DISABLED"

        self.circuit_details = self.get_resource(self.circuit_res_id)
        evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
        svlan = "0" if evc["sVlan"] in ["untagged", "Untagged"] else evc["sVlan"]

        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)

        for spoke in spoke_list:
            ordered_spoke_list = self.get_ordered_topology(spoke)
            terminating_node = ordered_spoke_list[-1]

            for device, values in terminating_node.items():
                if values["Role"] == "CPE" or (
                    values["Role"] == "MTU"
                    and str(values["Client Neighbor Interface"].lower()) == "none"
                    and ("EX" not in values["Model"])
                ):
                    cvlan = self.get_cvlans_for_uni_ep(
                        self.circuit_details, values["Host Name"] + "-" + values["Client Interface"]
                    )
                    self.toggle_service_CPE(values["Host Name"], self.required_state, svlan, cvlan)
                else:
                    self.toggle_service(self.circuit_details, values, self.required_state, svlan)

    def toggle_service(self, circuit_details, device, adminstate, svlan):
        """toggles service state on PE/AGG/MTU Juniper devices"""
        try:
            self.create_mef_segment_for_toggle_service(circuit_details, device, adminstate, svlan)
        except Exception as err:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Error- {err} raised while doing service-toggle for {device['Role']} - {device['Host Name']}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

    def create_mef_segment_for_toggle_service(self, circuit_details, device_info, adminstate, svlan):
        """
        Creates mef segment resource for service toggle
        :param circuit_details: circuit details resource
        :param device_info: device info of pe/agg/mtu devices from the spoke list
        :adminstate: adminstate to toggle(either ENABLED/DISABLED)
        :param svlan: svlan
        :return: None
        """
        self.logger.info(f"Service toggle for {device_info['Role']} Device {device_info['Host Name']}")

        # Getting the NF by using fqdn as well as ip #
        nf = self.get_network_function_for_spoke_device(device_info)

        # Get MEF plugin product
        package = nf["resourceTypeId"].split(".")[0]
        product_id = self.get_mef_plugin_product(package)
        self.logger.info(f"product_id for package: {package} is {product_id}")

        segment_properties = self.get_toggle_service_properties(circuit_details, device_info, adminstate, svlan)
        self.logger.info(
            f"segment properties for update operation of {device_info['Host Name']} device is {segment_properties}"
        )

        # Creating MEF segment to update description on PE/AGG/MTU device
        self.create_and_delete_segment_resource(self.resource["id"], product_id, segment_properties, self.circuit_id)

    def get_toggle_service_properties(self, circuit_details, device_info, adminstate, svlan):
        """
        Forms the service toggle properties for mef segment creation
        :param circuit_details: circuit details resource
        :param device_info: device info of pe/agg/mtu devices from the spoke list
        :adminstate: adminstate to toggle(either ENABLED/DISABLED)
        :param svlan: svlan
        :return: None
        """
        device_nf = self.get_network_function_for_spoke_device(device_info)
        client_port = device_info["Client Interface"]
        cvlan = self.get_cvlans_for_uni_ep(circuit_details, device_info["Host Name"] + "-" + client_port)

        package = device_nf["resourceTypeId"].split(".")[0]
        port_res_id = self.get_port_id_from_port_name_and_device_id_retry(client_port, device_nf["id"])
        port_res = self.bpo.resources.get(port_res_id)
        service_type = circuit_details["properties"]["serviceType"]

        if port_res is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Unable to find port {client_port} on node {device_info['Host Name']}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        mef_products = self.bpo.products.get_by_domain_and_type(
            self.BUILT_IN_DOMAIN_ID, "mef.resourceTypes.LegatoSegment"
        )

        product_id = None

        for product in mef_products:
            if product["providerData"]["template"].startswith(device_nf["resourceTypeId"].split(".")[0] + "."):
                product_id = product["id"]

        if not product_id:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"No Mef Service Template found for domain {package}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        segment_properties = {
            "operation": "UPDATE",
            "update_properties": [{"adminState": True}],
            "segment_info": {
                "name": self.circuit_id,
                "type": service_type,
                "adminState": adminstate,
                "endpoints": [
                    {"node_id": device_nf["id"], "port_id": port_res["id"], "svlan": int(svlan), "cvlan": cvlan}
                ],
            },
        }

        return segment_properties

    def toggle_service_CPE(self, node_name, adminstate, svlan, cvlan):
        """toggles the service state on CPE devices"""
        client_interface = self.get_node_client_interface(self.circuit_details, node_name)
        fqdn = self.get_node_fqdn(self.circuit_details, node_name)
        mgmt_ip = self.get_node_management_ip(self.circuit_details, node_name)
        nf = self.get_network_function_by_host(fqdn)

        if nf is None:
            nf = self.get_network_function_by_host(mgmt_ip)

            if nf is None:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"Node with FQDN {fqdn} and ip {mgmt_ip} not found",
                )
                self.categorized_error = msg
                self.exit_error(msg)

        package = nf["resourceTypeId"].split(".")[0]
        nf_prid = nf["providerResourceId"]
        port_prid = nf_prid + "::TPE_" + client_interface.upper() + "_PTP"
        domain = nf_prid.split("_")[1]
        port_res = self.bpo.resources.get_by_provider_resource_id(domain, port_prid)

        if port_res is None:
            client_interface = client_interface.replace("ETH-PORT", "ETH_PORT")
            port_prid = nf_prid + "::TPE_" + client_interface.upper() + "_PTP"
            port_res = self.bpo.resources.get_by_provider_resource_id(domain, port_prid)

        if port_res is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Unable to find port {client_interface} on node {fqdn}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        mef_products = self.bpo.products.get_by_domain_and_type(
            self.BUILT_IN_DOMAIN_ID, "mef.resourceTypes.LegatoSegment"
        )

        product_id = None

        for product in mef_products:
            if product["providerData"]["template"].startswith(nf["resourceTypeId"].split(".")[0] + "."):
                product_id = product["id"]

        if not product_id:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"No Mef Service Template found for domain {package}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        segment_properties = {
            "operation": "UPDATE",
            "update_properties": [{"adminState": True}],
            "segment_info": {
                "name": self.circuit_id,
                "adminState": adminstate,
                "endpoints": [
                    {
                        "node_id": nf["id"],
                        "port_id": port_res["id"],
                        "svlan": int(svlan),
                        "cvlan": cvlan,
                    }
                ],
            },
        }
        # self.create_and_delete_segment_resource(self.resource['id'], product_id, segment_properties,
        #                                         self.circuit_id, wait_active=False)
        segment_res_obj = {
            "label": self.circuit_id + segment_properties["operation"],
            "productId": product_id,
            "properties": segment_properties,
        }
        segment_res = self.bpo.resources.create(self.resource["id"], segment_res_obj, wait_active=False)
        reason = self.get_reason(segment_res.resource_id, interval=5, max=300)

        if reason == "active":
            self.bpo.relationships.delete_relationships(segment_res.resource_id)
            self.bpo.resources.delete(segment_res.resource_id)
        elif "Device Type Does not support shutting down Flows" in str(reason):
            pe_device = self.get_pe_in_spoke(node_name)
            self.toggle_service(self.circuit_details, pe_device, self.required_state, svlan)
            # self.bpo.resources.delete_dependencies(self.resource['id'])
        else:
            self.logger.info(str(reason))
            msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(reason))
            self.categorized_error = msg
            self.exit_error(msg)

    def get_reason(self, resource_id, interval=1.0, max=90.0):
        """Getting the state of the resource."""
        import time

        t0 = time.time()

        while True:
            resource = self.bpo.market.get(f"/resources/{resource_id}")
            status = resource["orchState"]

            if status == "active":
                return "active"
            elif status == "failed":
                return resource["reason"]

            remaining = (t0 + max) - time.time()

            if remaining < 0:
                return f"Timed out while waiting for resource {resource_id} to come active or failed state"

            time.sleep(interval)

    def get_pe_in_spoke(self, node_name):
        """
        finds the PE device host name
        in Spoke where this device is present
        """
        return_value = None
        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)
        required_spoke = None

        for spoke in spoke_list:
            if node_name in spoke.keys():
                required_spoke = spoke
                break

        if required_spoke is not None:
            for device, values in required_spoke.items():
                if values["Role"] == "PE":
                    return_value = values
                    break

        if return_value is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Could Not Find PE device in spoke for node {node_name}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return return_value
