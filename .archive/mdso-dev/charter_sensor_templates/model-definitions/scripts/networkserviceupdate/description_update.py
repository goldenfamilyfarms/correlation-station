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
    """this is the class that is called for the initial updation of thes
    Network Service description.  The only input it requires is the circuit_id
    associated with the service.
    """

    def process(self):
        # added the operation flag options
        self.operation = self.properties["operation"]
        self.circuit_id = self.properties["circuit_id"]
        self.circuit_res_id = self.properties["circuit_details_resource_id"]
        circuit_details = self.get_resource(self.circuit_res_id)
        evc = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        svlan = "0" if evc["sVlan"] in ["untagged", "Untagged"] else evc["sVlan"]

        pe_list = []
        cpe_list = []
        agg__mtu_list = []

        # get all the spokes in network service
        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)

        if self.operation == "SERVICE_MAPPER":
            # dictionary of to be updated devices passed from network service update on behalf of service mapper
            # this is an optional attribute that is used for service mapper
            self.devices_to_be_updated = self.properties["devices_to_be_updated"]["description_update"]
            self.logger.info("devices_to_be_updated: {}".format(self.devices_to_be_updated))

            # service mapper removing all device that need not to be updated
            self.service_mapper_spoke_list_adjustment(self.devices_to_be_updated, spoke_list, circuit_details)

        self.logger.info("spoke_list after adjustment: {}".format(spoke_list))

        for spoke in spoke_list:
            for device, values in spoke.items():
                if not values.get("Role"):
                    msg = self.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"Device: {device} has unsupported role: {values['Role']}",
                    )
                    self.categorized_error = msg
                    self.exit_error(msg)
                elif values["Role"].upper() == "PE":
                    pe_list.append(values)
                elif values["Role"].upper() == "AGG" or values["Role"].upper() == "MTU":
                    agg__mtu_list.append(values)
                elif values["Role"].upper() == "CPE":
                    cpe_list.append(values)
                else:
                    msg = self.error_formatter(
                        self.INCORRECT_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"Device: {device} has unsupported role: {values['Role']}",
                    )
                    self.categorized_error = msg
                    self.exit_error(msg)

        # mickey added the operation flag options
        if self.operation != "SERVICE_MAPPER":
            for pe in pe_list:
                self.update_pe_descr(circuit_details, pe, svlan)

        self.logger.info("cpe_list contains: {}".format(cpe_list))

        for device in cpe_list:
            device_nf = self.get_network_function_by_host_or_ip(hostname=device["FQDN"], ip=device["Management IP"])
            if not device_nf:
                msg = self.error_formatter(
                    self.PROCESS_ERROR_TYPE,
                    self.RESOURCE_GET_SUBCATEGORY,
                    f"No Network Function Resource found with FQDN: {device['FQDN']} and/or IP: {device['Management IP']}",
                )
                self.categorized_error = msg
                self.exit_error(msg)
            self.update_description(circuit_details, device, svlan)
        # service mapper only supports CPEs
        if self.operation != "SERVICE_MAPPER":
            for device in agg__mtu_list:
                self.update_description(circuit_details, device, svlan)

    def update_pe_descr(self, circuit_details, pe, svlan):
        """
        Creates plugin resource for eline service
        Creates serviceprovisioner_FIA/ELAN resource for FIA/ELAN service
        """
        try:
            service_type = circuit_details["properties"]["serviceType"]
            self.logger.info("Updating Device %s for service type %s" % (pe["Host Name"], service_type))

            if service_type == "ELINE":
                # Creating mef legato segment resource for description update
                self.create_mef_segment_for_descr_update(circuit_details, pe, svlan)

            else:
                properties = {
                    "circuit_details_id": self.circuit_res_id,
                    "circuit_id": self.circuit_id,
                    "context": "PE",
                    "stage": "PRODUCTION",
                    "operation": self.UPDATE_OPERATION_STRING,
                    "update_property": "description",
                }
                pe_update_obj = {
                    "label": self.properties["circuit_id"] + "-" + service_type + "-Provisioner",
                    "productId": self.get_built_in_product(self.PE_SPECIFIC_RESOURCE_TYPES.get(service_type))["id"],
                    "properties": properties,
                }
                self.logger.info("pe update object %s" % str(pe_update_obj))
                self.bpo.resources.create(self.params["resourceId"], pe_update_obj)

        except Exception as err:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_CREATE_SUBCATEGORY,
                f"Failed to update description on PE Device: {pe['Host Name']} due to following error: {str(err)}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

    def update_description(self, circuit_details, device, svlan):
        """
        Method to Update Description on CPE
        devices
        """
        try:
            self.create_mef_segment_for_descr_update(circuit_details, device, svlan)

        except Exception as err:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_CREATE_SUBCATEGORY,
                f"Failed to update description on {device['Role']} Device: {device['Host Name']} due to following error: {str(err)}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

    def create_mef_segment_for_descr_update(self, circuit_details, device_info, svlan):
        """
        Creates mef segment resource for description update
        :param circuit_details: circuit details resource
        :param device_info: device info of pe/cpe devices from the spoke list
        :param svlan: svlan
        :return: None
        """
        self.logger.info("Updating %s Device %s" % (device_info["Role"], device_info["Host Name"]))

        # Getting the NF by using fqdn as well as ip #
        nf = self.get_network_function_for_spoke_device(device_info)

        # Get MEF plugin product
        package = nf["resourceTypeId"].split(".")[0]
        product_id = self.get_mef_plugin_product(package)
        self.logger.info("product_id for package: %s is %s" % (package, product_id))
        segment_properties = self.get_descr_update_properties(circuit_details, device_info, svlan)
        self.logger.info(
            "segment properties for update operation of %s device is %s"
            % (device_info["Host Name"], str(segment_properties))
        )

        # Creating MEF segment to update description on PE/CPE device
        self.create_and_delete_segment_resource(self.resource["id"], product_id, segment_properties, self.circuit_id)

    def get_descr_update_properties(self, circuit_details, device_info, svlan):
        """
        Forms the description update properties for mef segment creation
        :param circuit_details: circuit details resource
        :param device_info: device info of pe/cpe devices from the spoke list
        :param svlan: svlan
        :return: None
        """
        device_nf = self.get_network_function_for_spoke_device(device_info)
        client_port = device_info["Client Interface"]
        client_port_decr = device_info["Client Interface Description"]
        service_decr = self.get_service_userLabel(circuit_details)
        cvlan = self.get_cvlans_for_uni_ep(circuit_details, device_info["Host Name"] + "-" + client_port)
        device_rid = device_nf["id"]
        node_ip = device_nf["properties"]["ipAddress"]
        package = device_nf["resourceTypeId"].split(".")[0]
        port_res_id = self.get_port_id_from_port_name_and_device_id_retry(client_port, device_nf["id"])
        port_res = self.bpo.resources.get(port_res_id)
        service_type = circuit_details["properties"]["serviceType"]

        if port_res is None:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"No Port Resource found for Port: {client_port} on Device: {node_ip}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        mef_products = self.bpo.products.get_by_domain_and_type(
            self.BUILT_IN_DOMAIN_ID, "mef.resourceTypes.LegatoSegment"
        )
        product_id = None
        for product in mef_products:
            if product["providerData"]["template"].startswith(package + "."):
                product_id = product["id"]

        if not product_id:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"No Mef Service Template found for domain: {package}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        segment_properties = {
            "operation": "UPDATE",
            "update_properties": [{"description": True}],
            "segment_info": {
                "type": service_type,
                "name": service_decr,
                "endpoints": [
                    {
                        "node_id": device_rid,
                        "port_id": port_res["id"],
                        "svlan": int(svlan),
                        "cvlan": cvlan,
                        "description": client_port_decr,
                    }
                ],
            },
        }

        return segment_properties

    def service_mapper_spoke_list_adjustment(self, devices_to_be_updated, spoke_list, circuit_details):
        """alters the spoke_list when operation == "SERVICE_MAPPER".

        Reason:
        by default bandwidth update provisions all cpe's but for the use of service mapper
        only one cpe may be necessary so this method adjusts spoke_list as needed.

        Keyword arguments:
        devices_to_be_updated -- List of device tids that need update.

        spoke_list --

        circuit_details --

        """
        one_sided_services = (
            "FIA",
            "VOICE",
        )

        if circuit_details["properties"]["serviceType"] in one_sided_services:
            pass
        else:
            # self.spoke_list = spoke_list
            a_side = list(spoke_list[0].keys())
            z_side = list(spoke_list[1].keys())
            self.logger.info("a_side: {}".format(a_side))
            self.logger.info("z_side: {}".format(z_side))

            # empty list of device to be deleted from bandwidth update cpe_list
            cpe_to_be_excluded = []

            if len(self.devices_to_be_updated) == 1:
                for device in devices_to_be_updated:
                    if device in a_side:
                        del spoke_list[1]
                    else:
                        del spoke_list[0]
                # print(spoke_list)

                # for loop to determine what device to add to the cpe_to_be_excluded dynamic list
                for device in spoke_list[0].keys():
                    for tid in devices_to_be_updated:
                        if device != tid:
                            cpe_to_be_excluded.append(device)
                            self.logger.info("device to exclude: {}".format(device))

                # for loop to delete the key value contained in the cpe_to_be_excluded list from the spoke_list.
                # reason for doing this is that by default
                # this product will updated all cpe's regardless of it needing to be fixed.
                for device in cpe_to_be_excluded:
                    del spoke_list[0][device]
            else:
                pass
