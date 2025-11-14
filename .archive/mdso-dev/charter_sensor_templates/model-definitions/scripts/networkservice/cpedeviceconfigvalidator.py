""" -*- coding: utf-8 -*-

CPE device config validator Plans

Versions:
   0.2 Jul 19, 2019
       Latest copy of of cpedeviceconfigvalidator plan

"""
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """
    This function will do the following:
        - for CPE it will check if port is in-service or not
        - If the port is already in in-service, it will fail the resource.
    """

    def process(self):
        circuit_details_id = self.properties["circuit_details_id"]
        self.circuit_details = self.get_resource(circuit_details_id)
        self.logger.debug("circuit_details in cpedeviceconfigvalidator: " + str(self.circuit_details))

        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)
        self.logger.debug("spoke_list in cpedeviceconfigvalidator: " + str(spoke_list))

        for spoke in spoke_list:
            for device, device_info in spoke.items():
                if device_info["Role"] == "CPE":
                    self.logger.debug("CPE device found in cpedeviceconfigvalidator: " + str(device))
                    client_interface = device_info["Client Interface"]

                    nf = self.get_network_function_by_host_or_ip(device_info["FQDN"], device_info["Management IP"])
                    self.logger.debug("Network function of CPE device found in cpedeviceconfigvalidator: " + str(nf))

                    if not nf:
                        self.logger.debug("No network function found for host name %s" % device)
                    else:
                        # todo: add NF communicatino check. it will fail below with confusing error if logic continues
                        # w/o confirming NF communication.
                        device_id = nf["id"]
                        port_id = self.get_port_id_from_port_name_and_device_id_retry(
                            client_interface, device_id, device_role="CPE"
                        )
                        self.logger.debug(
                            "Port id of CPE device's port %s found in cpedeviceconfigvalidator: %s"
                            % (client_interface, port_id)
                        )

                        port_role = self.get_port_role(self.circuit_details, device + "-" + client_interface)
                        required_service_type = "epl"
                        if "ceVlan" in self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"]:
                            required_service_type = "evpl"

                        package = nf["resourceTypeId"].split(".")[0]
                        plugin_rt = "charter.resourceTypes.CpeConfigValidator"
                        plugin_product = self.get_plugin_product(package, plugin_rt)
                        if plugin_product is not None:
                            plugin_properties = {
                                "node_id": nf["id"],
                                "pe_port_res_id": port_id,
                                "port_role": port_role,
                                "required_service_type": required_service_type,
                                "resource_name": "cpe_device_config_validator",
                            }

                            plugin_object = {
                                "label": self.circuit_details["properties"]["circuit_id"] + ".cpe_config_validator",
                                "resourceTypeId": plugin_rt,
                                "productId": plugin_product,
                                "properties": plugin_properties,
                            }

                            plugin_resource = self.bpo.resources.create(self.resource["id"], plugin_object)
                            if plugin_resource.resource["orchState"] == "active":
                                self.bpo.relationships.delete_by_source_and_target(
                                    self.resource["id"], plugin_resource.resource_id
                                )
                                self.bpo.resources.delete(plugin_resource.resource_id)
                        break
        return
