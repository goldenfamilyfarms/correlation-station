"""-*- coding: utf-8 -*-

ServiceProvisioner_ELAN Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of ServiceDeviceOnboarder plans

"""

import sys

sys.path.append("model-definitions")
from copy import deepcopy

from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
from scripts.networkservice.peprovisioner import PeProvisioner


class Activate(CompleteAndTerminatePlan, PeProvisioner):
    CUSTOMER_NAME_TO_VPLS_SUB_STRING = "[^0-9a-zA-Z_-]"

    """
    this is the class used for initial activation of service elan service provisioner
    """

    def process(self):
        operation = self.properties.get("operation", self.ACTIVATE_OPERATION_STRING)
        circuit_details_id = self.properties["circuit_details_id"]
        context = self.properties["context"]
        stage = self.properties["stage"]

        if not stage == "PRODUCTION":
            return

        # Get the circuit details and network service
        self.circuit_details = self.get_resource(circuit_details_id)
        # return without doing anything if service is not ELAN
        if not self.circuit_details["properties"]["serviceType"] == "ELAN" or context != "PE":
            self.logger.warning("ELAN Service provisioner called for a service it should not have been.")
            return

        pe = self.get_pe_details()
        if not pe:
            self.exit_error("No PE device found or PE Device not in active state, Please check RA logs / Device State")

        nf_resource = self.get_network_function_by_host(pe["FQDN"])
        self.pe_network_function = nf_resource
        elan_object = self.get_elan_service_object_from_details(pe)
        self.pe_tpe_agroup = elan_object["properties"]["apply_group"]
        package = nf_resource["resourceTypeId"].split(".")[0]

        #################################################
        # PLUGIN PRODUCT IS NOT IN USE FOR ELAN.
        # IF WE CHANGE TO USING PLUGIN PRODUCT,
        # DEVELOPMENT AND TESTING WILL BE REQUIRED
        #################################################

        elan_plugin_product = self.get_plugin_product(package, "charter.resourceTypes.ElanEndpoint")

        self.logger.info("======= DATA FROM serviceelanprovisioner.py =======")
        self.logger.info("pe: %s" % pe)
        self.logger.info("nf_resource: %s" % nf_resource)
        self.logger.info("elan_object: %s" % elan_object)
        self.logger.info("elan_plugin_product: %s" % elan_plugin_product)

        if operation == self.ACTIVATE_OPERATION_STRING:
            self.do_activate(pe, nf_resource, elan_object, elan_plugin_product)
            self.update_devices_prop_value([pe["Host Name"]], circuit_details_id, "Provisioned", "True")
        elif operation == self.UPDATE_OPERATION_STRING:
            self.do_update(pe, elan_object, elan_plugin_product)
        elif operation == self.TERMINATE_OPERATION_STRING:
            self.do_terminate(pe, nf_resource, self.circuit_details, elan_object, elan_plugin_product)
        else:
            self.exit_error("Invalid command received " + operation)

    def do_activate(self, pe, nf_resource, elan_object, elan_plugin_product):
        """Process activate of the PE resources"""
        # Get PE related ELAN attributes
        if elan_plugin_product is not None:
            elan_object["productId"] = elan_plugin_product
            network_service = self.get_associated_network_service(self.resource["id"])
            self.bpo.resources.create(network_service["id"], elan_object)
        else:
            # Update the network instance with this interface
            self.add_update_network_interface(
                nf_resource,
                self.get_network_instance_for_circuit_details(self.circuit_details, pe, nf_resource),
                elan_object,
            )

    def do_update(self, pe, elan_object, elan_plugin_product):
        """'
        Process updates of the PE resources
        """
        elan_object["properties"]["operation"] = self.UPDATE_OPERATION_STRING
        update_property = self.properties.get("update_property")

        if update_property == "bandwidth":
            elan_object["properties"]["update_property"] = "bandwidth"
            self.bandwidth_update(pe, elan_object, elan_plugin_product)

        if "description" in update_property:
            elan_object["properties"]["update_property"] = "description"
            self.description_update(pe, elan_object, elan_plugin_product)

        if "adminState" in update_property:
            self.adminstate_update()

    def bandwidth_update(self, pe, elan_object, elan_plugin_product):
        """
        Method to update bandwidth for ELAN service
        :param pe: pe device info from the spoke list
        :param fia_object: formed ELAN properties
        :param fia_plugin_product: ELAN plugin product id
        :return: None
        """
        self.logger.info("Bandwidth update")
        if elan_plugin_product is not None:
            self.logger.info("Creating ELAN plugin resource for bandwidth update")
            elan_object["productId"] = elan_plugin_product
            network_service = self.get_associated_network_service(self.resource["id"])
            elan_plugin_resource = self.bpo.resources.create(network_service["id"], elan_object)
            self.logger.info("elan_plugin_resource: {}".format(elan_plugin_resource))

        else:
            #  Juniper doesn't currently support ELAN service using plugin
            self.logger.info("Juniper doesn't currently support ELAN service using plugin")
            self.logger.info("Updating bandwidth on device %s" % pe["Host Name"])
            # fetching interface values required to update PE device
            pe_device = self.get_network_function_by_host(pe["FQDN"])
            device_prid = pe_device["providerResourceId"]
            interface_name = pe["Client Interface"].lower()

            # fetching interface values required to update PE device
            evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
            unit = evc["sVlan"]
            if (
                "apply_group" in elan_object["properties"]
                and elan_object["properties"]["apply_group"].upper() == "EP-UNI"
            ) or evc["sVlan"] == "untagged":
                unit = "0"
            egress_bw = evc.get("evc-egress-bwp")
            ingress_bw = evc.get("evc-ingress-bwp")
            # Override circuit details with input value if present
            if "bandwidthValue" in self.properties:
                egress_bw = self.properties["bandwidthValue"]
                ingress_bw = self.properties["bandwidthValue"]
            service_type = self.circuit_details["properties"]["serviceType"]

            if egress_bw is None:
                self.exit_error("Egress Policer details missing in Mulesoft response")

            # Converting Bandwidths to standard format
            egress_policer = self.get_bandwidth_formatted(egress_bw)
            ingress_policer = None if ingress_bw is None else self.get_bandwidth_formatted(ingress_bw)

            bw = self.get_bw_in_kbps(egress_bw) if egress_bw is not None else self.get_bw_in_kbps(ingress_bw)

            # Check which policers are already present on interface
            policers_on_interface = self.execute_ra_command_file(
                device_prid,
                "get-logical-tpe.json",
                parameters={"interface": interface_name, "unit": unit},
                headers=None,
            )

            # Update the device
            if "input_policer" in policers_on_interface.json()["result"] and ingress_policer is not None:
                self.execute_ra_command_file(
                    device_prid,
                    "update-logical-tpe.json",
                    parameters={
                        "interface": interface_name,
                        "unit": unit,
                        "bandwidth": bw,
                        "input_policer": ingress_policer,
                        "output_policer": egress_policer,
                        "service_type": service_type,
                        "commit": True,
                    },
                    headers=None,
                )
            else:
                self.execute_ra_command_file(
                    device_prid,
                    "update-logical-tpe.json",
                    parameters={
                        "interface": interface_name,
                        "unit": unit,
                        "bandwidth": bw,
                        "output_policer": egress_policer,
                        "service_type": service_type,
                        "commit": True,
                    },
                    headers=None,
                )

    def description_update(self, pe, elan_object, elan_plugin_product):
        """
        Method to update description for ELAN service
        :param pe: pe device info from the spoke list
        :param fia_object: formed ELAN properties
        :param fia_plugin_product: ELAN plugin product id
        :return: None
        """
        self.logger.info("Description update")
        if elan_plugin_product is not None:
            self.logger.info("Creating ELAN plugin resource for description update")
            elan_object["productId"] = elan_plugin_product
            network_service = self.get_associated_network_service(self.resource["id"])
            self.bpo.resources.create(network_service["id"], elan_object)

        else:
            # Juniper doesn't currently support ELAN service using plugin
            self.logger.info("Juniper doesn't currently support ELAN service using plugin")
            self.logger.info("Updating description on device %s" % pe["Host Name"])
            # fetching interface values required to update PE device
            pe_device = self.get_network_function_by_host(pe["FQDN"])
            device_prid = pe_device["providerResourceId"]
            interface_name = pe["Client Interface"]
            client_port_decr = pe["Client Interface Description"]
            service_decr = self.get_service_userLabel(self.circuit_details)

            # fetching service values required to update PE device
            evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
            unit = evc["sVlan"]
            if (
                "apply_group" in elan_object["properties"]
                and elan_object["properties"]["apply_group"].upper() == "EP-UNI"
            ) or evc["sVlan"] == "untagged":
                unit = "0"

            try:
                self.execute_ra_command_file(
                    device_prid,
                    "set-physical-interface-params.json",
                    {
                        "interface": interface_name.lower(),
                        "param": "description",
                        "description": client_port_decr,
                        "commit": False,
                    },
                )

                self.execute_ra_command_file(
                    device_prid,
                    "update-logical-tpe.json",
                    {
                        "interface": interface_name.lower(),
                        "unit": str(unit),
                        "description": service_decr,
                        "commit": True,
                    },
                )

            except Exception as e:
                self.exit_error(str(e))

    def do_terminate(self, pe, nf_resource, circuit_details, elan_object, elan_plugin_product):
        """terminate the ELAN Service on the PE"""
        if elan_plugin_product is not None:
            elan_object["productId"] = elan_plugin_product
            elan_object["properties"]["operation"] = self.TERMINATE_OPERATION_STRING
            nw_service_delete_res = self.bpo.resources.get_dependent_by_type(
                self.resource["id"], self.BUILT_IN_NETWORK_SERVICE_DELETE_TYPE
            )
            self.bpo.resources.create(nw_service_delete_res["id"], elan_object)
        else:
            #
            # NOW REMOVE THE TPE ON THE DEVICE.
            #
            evc_data = circuit_details["properties"]["service"][0]["data"]["evc"][0]
            unit_id = str(evc_data["sVlan"])
            if (
                "apply_group" in elan_object["properties"]
                and elan_object["properties"]["apply_group"].upper() == "EP-UNI"
            ):
                unit_id = "0"
            PeProvisioner.delete_pe_logical_ctp(self, nf_resource, pe["Client Interface"].lower(), unit_id)
            ni_resource = self.get_network_instance_for_circuit_details(self.circuit_details, pe, nf_resource)
            self.logger.info(ni_resource)
            network_instances = self.get_network_instances_for_device_and_type(
                nf_resource["id"], itype="vpls", group_name=ni_resource["properties"]["name"]
            )

            if len(network_instances) == 0:
                self.logger.warning("No network instance found, so nothing to terminate")
                return

            self.logger.info(network_instances)
            interface = ni_resource["properties"]["interfaces"][0]["config"]["interface"]
            self.add_remove_interface_to_network_interface(self, network_instances[0], interface, False)

    def get_pe_details(self):
        """returns the PE detail information

        None if it is not found.

        """
        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)
        if len(spoke_list) > 1:
            self.exit_error("ELAN service should only have one spoke")

        # Get the PE, AGG list and MTU list from topology
        pe = None
        for spoke in spoke_list:
            for device, values in spoke.items():
                if (
                    values["Role"] == "PE"
                    and self.get_node_bpo_state(self.circuit_details, device) == self.BPO_STATES["AVAILABLE"]["state"]
                ):
                    pe = values

        return pe

    def create_pe_tpe(self, properties, pe_uni=False):
        # Getting required domain
        device_pid = self.bpo.resources.get(properties["pe_device_rid"])["productId"]
        self.logger.info("CREATE_PE_TPE - PROPERTIES: {}".format(properties))
        self.domain_id = self.bpo.market.get("/products/%s" % device_pid)["domainId"]

        # Update PTP TPE from disable to active state
        self.update_ptp_tpe(properties["port_id"], properties["interface_userLabel"])

        # Create TPE for ELAN service
        pe_tpe_res = self.create_tpe(properties=properties, pe_uni=pe_uni)
        # Patch the TPE to discovered as a locking measure to prevent subsequent changes to device resource

        return pe_tpe_res.resource_id

    def create_tpe(self, properties, tpe_properties=None, pe_uni=False):
        """
        creates the TPE resource for service
        """
        tpe_pid = self.bpo.products.get_by_domain_and_type(self.domain_id, "tosca.resourceTypes.TPE")[0]["id"]
        if not tpe_properties:
            tpe_properties = self.get_tpe_properties(properties)
        # Define what unit we are provisioning on
        if properties.get("vlan") and properties["vlan"].lower() == "untagged":
            unit = "0"
        elif properties.get("type_2"):
            unit = properties["unit"]
        else:
            unit = tpe_properties["data"]["attributes"]["locations"][0]["vlan"]
        tpe_label = properties["port_name"].lower() + "." + unit

        self.logger.info("TPE_PROPERTIES within create_tpe: {}".format(tpe_properties))
        self.logger.info("PROPERTIES within create_tpe: {}".format(properties))

        tpe_object = {
            "label": tpe_label,
            "resourceTypeId": "tosca.resourceTypes.TPE",
            "productId": tpe_pid,
            "properties": tpe_properties,
        }

        if pe_uni:
            if tpe_object["properties"]["data"]["attributes"]["additionalAttributes"].get("intfLabel"):
                new_userLabel = tpe_object["properties"]["data"]["attributes"]["additionalAttributes"]["intfLabel"]
                tpe_object["properties"]["data"]["attributes"]["userLabel"] = new_userLabel
                tpe_object["properties"]["data"]["attributes"]["additionalAttributes"].pop("intfLabel")

        self.logger.info("TPE_OBJECT within create_tpe: {}".format(tpe_object))

        return self.bpo.resources.create(self.params["resourceId"], tpe_object, wait_active=False)

    def get_tpe_properties(self, properties):
        """
        generate TPE object on PE port for ELAN service
        """
        # Define what unit we are provisioning on
        if properties.get("vlan") and properties["vlan"].lower() == "untagged":
            unit = "0"
        elif properties.get("type_2"):
            unit = properties["unit"]
        else:
            unit = properties["vlan"]
        tpe_properties = {
            "device": self.bpo.resources.get(properties["pe_device_rid"])["providerResourceId"],
            "data": {
                "attributes": {
                    "structureType": "CTPServerToClient",
                    "bwpPerUni": [],
                    "layerTerminations": [
                        {
                            "layerRate": "ETHERNET",
                            "structureType": "exposed lone cp",
                            "terminationState": "layer termination cannot terminate",
                            "active": True,
                            "mplsPackage": {
                                "bw": {
                                    "bwKbps": self.get_bw_in_kbps(properties["e_bwProfileFlowParameters"])
                                    if "e_bwProfileFlowParameters" in properties.keys()
                                    else self.get_bw_in_kbps(properties["in_bwProfileFlowParameters"])
                                }
                            },
                            "signalIndex": {"mappingTable": [{}]},
                        }
                    ],
                    "additionalAttributes": {},
                },
                "id": properties["port_name"].lower() + "." + unit,
                "relationships": {
                    "owningServerTpe": {"data": {"id": properties["port_id"], "type": "tpes"}},
                    "networkConstruct": {
                        "data": {"id": properties["network_construct_id"], "type": "networkConstructs"}
                    },
                },
                "type": "tpes",
            },
        }

        # Set encapsulation to ethernet-vpls for UNI port, vlan-vpls for NNI port
        if "apply_group" in properties and properties["apply_group"].upper() == "EP-UNI":
            tpe_properties["data"]["attributes"]["encapsulation"] = {"encapsType": "ethernet-vpls"}
            tpe_properties["data"]["attributes"]["additionalAttributes"]["intfLabel"] = properties["userLabel"]
            tpe_properties["data"]["attributes"]["locations"] = [{"vlan": "0"}]
            tpe_properties["data"]["id"] = properties["port_name"].lower() + ".0"
            tpe_properties["data"]["attributes"]["additionalAttributes"]["intf-apply-groups"] = ["EP-UNI"]
            tpe_properties["data"]["attributes"]["userLabel"] = self.get_pe_port_desc()

            # Now we set up the vlan manipulation for ELAN circuits on PE EP-UNI's
            tpe_properties["data"]["attributes"]["additionalAttributes"]["input-vlan-map-action"] = "push"
            tpe_properties["data"]["attributes"]["additionalAttributes"]["input-vlan-map-vlan"] = str(
                properties["vplsVlanId"]
            )
            tpe_properties["data"]["attributes"]["additionalAttributes"]["output-vlan-map-action"] = "pop"

        elif "apply_group" in properties and properties["apply_group"].upper() == "EVP-UNI":
            tpe_properties["data"]["attributes"]["encapsulation"] = {"encapsType": "vlan-vpls"}
            tpe_properties["data"]["attributes"]["additionalAttributes"]["intfLabel"] = properties["userLabel"]
            tpe_properties["data"]["attributes"]["userLabel"] = self.get_pe_port_desc()
            self.logger.info("AT LINE 430 - TPE_PROPERTIES: {}".format(tpe_properties))

            # Now we set up the vlan manipulation for ELAN circuits on PE EVP-UNI's
            tpe_properties["data"]["attributes"]["locations"] = [{"vlanlist": properties["ceVlans"]}]
            tpe_properties["data"]["attributes"]["additionalAttributes"]["input-vlan-map-action"] = "push"
            tpe_properties["data"]["attributes"]["additionalAttributes"]["input-vlan-map-vlan"] = str(
                properties["vplsVlanId"]
            )
            tpe_properties["data"]["attributes"]["additionalAttributes"]["output-vlan-map-action"] = "pop"

        else:
            if properties.get("type_2"):
                tpe_properties["data"]["attributes"]["locations"] = [
                    {"vlanlist": [properties["outer_vlan"], "type 2", properties["inner_vlan"]]}
                ]
            if properties.get("vlan") and properties["vlan"].lower() != "untagged":
                tpe_properties["data"]["attributes"]["locations"] = [{"vlan": properties["vlan"]}]
            tpe_properties["data"]["attributes"]["encapsulation"] = {"encapsType": "vlan-vpls"}
            if not properties["userLabel"] == "None":
                tpe_properties["data"]["attributes"]["userLabel"] = properties["userLabel"]

        tpe_properties["data"]["attributes"]["layerTerminations"][0]["signalIndex"]["mappingTable"][0]["cos"] = (
            properties["cos"]
        )

        self.logger.info("Returning TPE_PROPERTIES from get_tpe_properties: {}".format(tpe_properties))

        return tpe_properties

    def get_pe_port_desc(self):
        """returns the description for the physical PE port

        Fail if it is not found within circuit details.

        """
        cd_node_name_list = self.circuit_details["properties"]["topology"][0]["data"]["node"][0]["name"]
        for name_value in cd_node_name_list:
            if name_value["name"] == "Client Interface Description":
                self.logger.info("Client Interface Description: {}".format(name_value["value"]))
                return name_value["value"]

        err_msg = "Client Interface Description Not Found in Circuit Details"
        self.exit_error(err_msg)

    def get_all_devices(self):
        """returns the list of devices

        None if it is not found.

        """
        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)
        if len(spoke_list) > 1:
            self.exit_error("ELAN service should only have one spoke")

        # Get the PE, AGG list and MTU list from topology
        all_devices = []
        for spoke in spoke_list:
            for device, values in spoke.items():
                if (
                    values["Role"] in ["PE", "AGG", "MTU"]
                    and self.get_node_bpo_state(self.circuit_details, device) == self.BPO_STATES["AVAILABLE"]["state"]
                ):
                    all_devices.append(values["Host Name"])

        return all_devices

    def get_elan_service_object_from_details(self, pe_details):
        """
        generates ELAN TPE Object from  PE Details

        :param pe_details: PE details generated by create_device_dict function
        :pe_details type: dict

        :return_value TPE object
        :rtype dict
        """
        evc_data = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
        elan_data = self.get_elan_service_details_from_circuit_details(self.circuit_details)
        port_name = pe_details["Client Interface"]
        port_uuid = pe_details["Host Name"] + "-" + port_name
        nf_resource = self.get_network_function_by_host(pe_details["FQDN"])
        pe_prid = nf_resource["providerResourceId"]
        type_2_endpoint = evc_data["endPoints"][0]
        is_type_2 = True if evc_data["endPoints"][0].get("type2") else False

        properties = {
            "pe_device_rid": nf_resource["id"],
            "network_construct_id": self.get_network_construct_id_by_device_id(nf_resource["id"]),
            "port_name": port_name,
            "port_id": self.get_port_id_from_port_name_and_device_id_retry(port_name, nf_resource["id"]),
            "interface_userLabel": self.get_port_description(self.circuit_details, port_uuid),
            "cos": self.COS_LOOKUP[pe_details["Role"]][evc_data["cosNames"][0]["name"]],
            "vlan": str(evc_data["sVlan"]),
            "userLabel": self.get_service_userLabel(self.circuit_details),
            "evcId": evc_data["evcId"],
            "group_name": self.get_network_instance_group_name_from_circuit_details(self.circuit_details),
            "vrf_id": str(elan_data["asNumber"]),
        }

        # Udate properties with Type II info if needed
        if is_type_2:
            properties["type_2"] = True
            properties["unit"] = str(type_2_endpoint["unit"])
            properties["outer_vlan"] = str(type_2_endpoint["outerVlan"])
            properties["inner_vlan"] = str(type_2_endpoint["innerVlan"])
            del properties["vlan"]

        is_edna = self.check_is_edna(pe_prid)
        edna_cos_group = "TP_SERVICEPORT_QF_" + properties["cos"].split("_")[1]
        properties["cos"] = edna_cos_group if is_edna else properties["cos"]

        if "vplsNetworkId" in evc_data:
            properties["vplsNetworkId"] = evc_data["vplsNetworkId"]

        if "vplsVlanId" in evc_data:
            properties["vplsVlanId"] = evc_data["vplsVlanId"]

        if "ceVlans" in evc_data["endPoints"][0]:
            properties["ceVlans"] = evc_data["endPoints"][0]["ceVlans"]

        if (
            "evc-ingress-bwp" in evc_data.keys()
            and self.get_node_client_neighbor(self.circuit_details, pe_details["Host Name"]) == "None"
        ):
            properties["in_bwProfileFlowParameters"] = evc_data["evc-ingress-bwp"]
        if "evc-egress-bwp" in evc_data.keys():
            properties["e_bwProfileFlowParameters"] = evc_data["evc-egress-bwp"]

        properties["apply_group"] = self.determine_port_apply_group(port_uuid)

        return_value = {
            "label": self.circuit_details["properties"]["circuit_id"] + ".elan_service",
            "properties": properties,
        }

        self.logger.info("======= return_value from get_elan_service_object_from_details: {}".format(return_value))

        return return_value

    def determine_port_apply_group(self, port_uuid):
        """
        Determine and return the apply group for an interface
        """
        port_apply_groups = {"INNI": "SERVICEPORT", "ENNI": "NNI", "UNI": ["EP-UNI", "EVP-UNI"]}
        a_grp = port_apply_groups[self.get_port_role(self.circuit_details, port_uuid)]
        self.logger.info("first a_grp = {}".format(a_grp))
        a_grp = self.get_service_type(self.circuit_details) if isinstance(a_grp, list) else a_grp
        self.logger.info("second a_grp = {}".format(a_grp))

        return a_grp

    def get_network_instance_for_circuit_details(self, circuit_details, pe_details, network_function):
        evc_data = circuit_details["properties"]["service"][0]["data"]["evc"][0]
        name = self.get_network_instance_group_name_from_circuit_details(circuit_details)
        port_uuid = pe_details["Host Name"] + "-" + pe_details["Client Interface"]
        is_type_2 = True if evc_data["endPoints"][0].get("type2") else False
        if self.determine_port_apply_group(port_uuid) == "EP-UNI":
            unit = "0"
        elif is_type_2:
            unit = circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0].get("unit")
        else:
            unit = str(evc_data["sVlan"])

        port_name = pe_details["Client Interface"].lower() + "." + unit
        network_instance = {
            "label": "RI::" + name,
            "resourceTypeId": self.BUILT_IN_NETWORK_INSTANCE_TYPE,
            "properties": {
                "name": name,
                "interfaces": [{"config": {"interface": port_name}}],
                "config": {
                    "additionalConfiguration": {
                        "filter": name + ".ELAN-BUM-FILTER",
                        "noTunnelServices": True,
                        "interfaceMacLimit": 512,
                    },
                    "description": self.get_network_instance_description_from_circuit_details(circuit_details),
                    "routeTarget": self.get_route_target_for_circuit_details(circuit_details),
                    "type": "vpls",
                },
                "vlans": [{"vlanId": int(evc_data["vplsVlanId"])}],
                "device": network_function["providerResourceId"],
            },
        }

        return network_instance

    def add_update_network_interface(self, network_function, network_instance, elan_object=None):
        """Will get the Network Interface from the market and determine if the interfaces
        need to be added

        :param network_function: Network Function
        :param network_instance: Network Instance
        :type network_function: dict
        :type network_instance: dict
        :return: Network Function
        :rtype: int
        """
        evc_id = network_instance["properties"]["config"]["routeTarget"].split(":")[-1]
        network_instances = self.get_network_instances_for_device_and_type(
            network_function["id"],
            itype="vpls",
            evc_id=evc_id,
        )

        cutthrough_product = self.get_ra_plugin_product(
            self.BUILT_IN_NETWORK_INSTANCE_TYPE, network_function["resourceTypeId"].split(".")[0]
        )

        if len(network_instances) > 1:
            network_instances = self.check_existing_routing_instances_on_pe(network_instances)

        self.logger.info("***** Routing Instances on PE with evc_id {}: {}".format(evc_id, network_instances))

        operation = "ACTIVATE"

        # Build CPEMGMT for Type II Circuits
        if elan_object["properties"].get("type_2"):
            # check if cpe mgmt is built already
            device_prid = network_function["providerResourceId"]
            interface_config = self.execute_ra_command_file(
                device_prid,
                "get-interface-config.json",
                parameters={"name": elan_object["properties"]["port_name"].lower()},
                headers=None,
            ).json()["result"]
            outer_vlan = elan_object["properties"]["outer_vlan"]
            if not self.is_typeii_cpe_mgmt_built(interface_config, outer_vlan):
                try:
                    is_edna = self.check_is_edna(device_prid)
                    self.logger.info("is_edna = %s" % is_edna)
                    cpegmt_cos_apply_group = "TP_SERVICEPORT_QF_MGMT" if is_edna else "SERVICEPORT_FC_MGMT"
                    cpe_tid = self.circuit_details["properties"]["topology"][0]["data"]["link"][0]["nodeEdgePoint"][
                        -1
                    ].split("-")[0]
                    cpemgmt_parameters = {
                        "interface": elan_object["properties"]["port_name"].lower(),
                        "outer_vlan": elan_object["properties"]["outer_vlan"],
                    }
                    cpemgmt_unit = self.execute_ra_command_file(
                        device_prid,
                        "get-next-available-type2-mgmt-unit.json",
                        parameters=cpemgmt_parameters,
                        headers=None,
                    ).json()["result"]
                    cpemgmt_parameters["unit"] = cpemgmt_unit
                    cpemgmt_parameters["apply-group"] = cpegmt_cos_apply_group
                    cpemgmt_parameters["description"] = f":MGMT::{cpe_tid}:"
                    self.execute_ra_command_file(
                        device_prid, "create-type2-mgmt.json", parameters=cpemgmt_parameters, headers=None
                    ).json()
                except Exception as ex:
                    self.logger.info("Unable to Add Type II CPEMGMT while Configuring PE Device")
                    self.logger.info(str(ex))
                    msg = str(ex)
                    self.categorized_error = (
                        self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                    )
                    self.exit_error(msg)

        if cutthrough_product:
            #
            # Using RA Cut Through
            #
            if len(network_instances) > 0:
                operation = "UPDATE"
                network_instance = self.__merge_network_instances(
                    network_instances[0], network_instance, operation="UPDATE"
                )

            cutthrough = {
                "label": network_instance["label"] + ".ra_cut",
                "productId": cutthrough_product["id"],
                "properties": {"operation": operation, "resource": network_instance},
            }
            if len(network_instances) == 0:
                # This is an update
                cutthrough["properties"]["operation"] = "UPDATE"
            self.bpo.resources.create(None, cutthrough)
        elif len(network_instances) > 0:
            #
            # Updating Network Instance on the device
            #
            merged_instance = self.__merge_network_instances(network_instances[0], network_instance, operation="UPDATE")
            supported = self.check_if_supported(elan_object, merged_instance)
            self.logger.info(
                "Existing Routing-Instance is {} with the designed handoff type/location".format(supported)
            )

            # Create the PE TPE
            pe_uni = True if elan_object["properties"]["apply_group"] in ["EP-UNI", "EVP-UNI"] else False
            tpe = self.create_pe_tpe(properties=elan_object["properties"], pe_uni=pe_uni)
            self.bpo.resources.patch(merged_instance["id"], {"properties": merged_instance["properties"]})

            try:
                self.await_active_collect_timing([str(tpe)], interval=3.0, tmax=300.0)

            except RuntimeError:
                resource_info = self.bpo.resources.get(tpe)
                self.logger.info(
                    "Upon Failure Resource Status for %s - Resource Type: %s, Resource Label: %s, Orch State: %s"
                    % (tpe, resource_info["resourceTypeId"], resource_info["label"], resource_info["orchState"])
                )

                self.exit_error("Timed out waiting for tpe to be created 300.0 seconds")
        else:
            #
            # Creating Network Instance
            #

            pe_uni = True if elan_object["properties"]["apply_group"] in ["EP-UNI", "EVP-UNI"] else False
            tpe = self.create_pe_tpe(properties=elan_object["properties"], pe_uni=pe_uni)
            device_domain_id = self.get_domain_id(network_function["id"])
            ni_product = self.bpo.products.get_by_domain_and_type(device_domain_id, self.BUILT_IN_NETWORK_INSTANCE_TYPE)
            network_instance["productId"] = ni_product[0]["id"]

            if self.pe_tpe_agroup in ["EP-UNI", "EVP-UNI"]:
                network_instance["properties"]["vlans"] = []

            self.logger.info("Network instance object to be created: {}".format(network_instance))
            network_instance_created = self.bpo.resources.create(None, network_instance)
            self.logger.info("Network_instance has been created: {}".format(network_instance_created))

            try:
                self.await_active_collect_timing([str(tpe)], interval=3.0, tmax=300.0)

            except RuntimeError:
                resource_info = self.bpo.resources.get(tpe)
                self.logger.info(
                    "Upon Failure Resource Status for %s - Resource Type: %s, Resource Label: %s, Orch State: %s"
                    % (tpe, resource_info["resourceTypeId"], resource_info["label"], resource_info["orchState"])
                )

                self.exit_error("Timed out waiting for tpe to be created 300.0 seconds")

            self.bpo.resources.patch(network_instance_created.resource_id, {"discovered": True})

    def remove_vplsVlanId(self, network_instance):
        new_ni = deepcopy(network_instance)
        new_ni["properties"] = {}

        for key in network_instance["properties"]:
            if key == "vlans":
                new_ni["properties"][key] = []
            else:
                new_ni["properties"][key] = network_instance["properties"][key]

        return new_ni

    def check_vpls_vlan_id_preexist(self, network_ri):
        """Check if existing routing instance contains vlan_id

        :param network_ri: Resource for existing routing instance
        :type network_ri: dict
        :rtype: Boolean
        """
        vpls_vlans = network_ri["properties"]["vlans"]

        for v in vpls_vlans:
            if v.get("vlanId"):
                return True

        return False

    def check_if_supported(self, elan_object, network_ri):
        """Check if a maintenance window is needed (EP/EVP-UNI going on MX using vlan-id in routing instance)

        :param elan_object: : Props to build Routing Instance from Circuit Details
        :param network_ri: Resource for existing routing instance
        :type elan_object: dict
        :type network_ri: dict
        :rtype: String
        """

        uni_apply_groups = ["EP-UNI", "EVP-UNI"]

        vpls_vlan = self.check_vpls_vlan_id_preexist(network_ri)
        a_group = elan_object["properties"]["apply_group"]

        if a_group in uni_apply_groups and vpls_vlan == True:
            self.exit_error("MAINTENANCE WINDOW NEEDED: EP/EVP-UNI ON ROUTER W EXISTING ROUTING-INSTANCE USING VLAN-ID")

        if a_group not in uni_apply_groups and vpls_vlan == False:
            self.exit_error("UNSUPPORTED: EXISTING ROUTING-INSTANCE WITHOUT VLAN-ID AND HANDOFF ON ENNI OR DOWNSTREAM")

        return "SUPPORTED"

    def remove_interface_from_network_interface(self, network_instance, interface):
        """Remove the interface, if the interface is the last it will delete the Network Instance

        :param interface: Interface name
        :param network_instance: Network Instance
        :type interface: str
        :type network_instance: dict
        :return: Network Function
        :rtype: int
        """
        network_function = self.get_network_function_for_resource(network_instance)
        cutthrough_product = self.get_ra_plugin_product(
            self.BUILT_IN_NETWORK_INSTANCE_TYPE, network_function["resourceTypeId"].split(".")[0]
        )
        updated_interfaces = []
        for intf in network_instance["properties"]["interfaces"]:
            if intf["config"]["interface"] != interface:
                updated_interfaces.append(intf)

        network_instance["properties"]["interfaces"] = updated_interfaces

        if cutthrough_product:
            cutthrough = {
                "label": network_instance["label"] + ".ra_cut",
                "productId": cutthrough_product["id"],
                "properties": {"operation": "UPDATE", "resource": network_instance},
            }
            if len(updated_interfaces) == 0:
                cutthrough["properties"]["operation"] = "TERMINATE"
            self.bpo.resources.create(None, cutthrough)
        else:
            if len(updated_interfaces) == 0:
                self.bpo.resources.delete(network_instance["id"])
            else:
                self.bpo.resources.patch(network_instance["id"], {"properties": network_instance["properties"]})

    def __merge_network_instances(self, ni1, ni2, operation="ACTIVATE"):
        """Merges Network Instances

        returns the merge of two Network Instances based on ni1 being
        the main one.
        """
        interfaces1 = []
        interfaces2 = []
        for intf in ni1["properties"]["interfaces"]:
            interfaces1.append(intf["config"]["interface"])
        for intf in ni2["properties"]["interfaces"]:
            interfaces2.append(intf["config"]["interface"])

        if operation in ["ACTIVATE", "UPDATE"]:
            interfaces1 = list(set(interfaces1 + interfaces2))
        else:
            interfaces1 = list(set(interfaces1 - interfaces2))

        updated_interfaces = []
        for interface in interfaces1:
            updated_interfaces.append({"config": {"interface": interface}})

        ni1["properties"]["interfaces"] = updated_interfaces

        return ni1

    def get_route_target_for_circuit_details(self, circuit_details):
        """returns the route target for the circuit_details

        if none is present it returns None

        :param circuit_details: charter.resourceTypes.CircuitDetails
        :type circuit_details: dict

        :return: route target or None
        :rtype: int
        """
        elan_data = self.get_elan_service_details_from_circuit_details(circuit_details)
        return str(elan_data["asNumber"]) + ":" + str(elan_data["vrfId"])

    def get_elan_service_details_from_circuit_details(self, circuit_details):
        """Will get the Network Interface from the market and determine it the interfaces
        need to be added
        """
        return circuit_details["properties"]["service"][0]["data"]["elan"][0]

    def get_network_instance_group_name_from_circuit_details(self, circuit_details):
        """returns the network instance group name based on the passed in Circuit Details

        :param circuit_details: CircuitDetails object
        :type circuit_details: dict

        :return_value name
        :rtype str
        """
        self.logger.info(
            "$$$ Circuit Details within get_network_instance_group_name_from_circuit_details: {}".format(
                circuit_details
            )
        )

        return circuit_details["properties"]["service"][0]["data"]["evc"][0]["evcId"] + ".ELAN"

    def get_network_instance_description_from_circuit_details(self, circuit_details):
        """returns the network instance group name based on the passed in Circuit Details

        :param circuit_details: CircuitDetails object
        :type circuit_details: dict

        :return_value name
        :rtype str
        """
        evc_id = circuit_details["properties"]["service"][0]["data"]["evc"][0]["evcId"]
        return "VC" + evc_id + ":TRANS:" + circuit_details["properties"]["serviceType"] + "::"

    def get_network_instance_name_from_circuit_details(self, circuit_details):
        """returns the network instance group name based on the passed in Circuit Details

        :param circuit_details: CircuitDetails object
        :type circuit_details: dict

        :return_value name
        :rtype str
        """
        group_name = self.get_network_instance_group_name_from_circuit_details(circuit_details)
        return group_name + "_" + str(Activate.get_vrfid_for_circuit_details(circuit_details)) + "." + "ELAN"

    def check_existing_routing_instances_on_pe(self, net_instances):
        """returns the routing instance resourceId if exists on PE"""

        network_instance_resources = []
        vpls_vlan = int(self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["vplsVlanId"])
        evc_id = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["evcId"]
        ni_name = evc_id + ".ELAN"

        self.logger.info(
            "Designed Network instance name: {}  EVC Id is: {}, and vpls Vlan is: {}".format(ni_name, evc_id, vpls_vlan)
        )

        for instance in net_instances:
            name = instance["properties"]["name"]
            vlan_id = None
            if len(instance["properties"]["vlans"]) > 0:
                for vlan_item in instance["properties"]["vlans"]:
                    if vlan_item.get("vlanId"):
                        vlan_id = instance["properties"]["vlans"][0]["vlanId"]

            if name.upper() == ni_name:
                self.logger.info(
                    "*** The instance name matched the name of the designed network instance: {} ***".format(ni_name)
                )
                return [instance]

            self.logger.info(
                "Instance properties name {} doesn't match the expected network instance name {}".format(name, ni_name)
            )
            if vlan_id == vpls_vlan:
                network_instance_resources.append(instance)

        if len(network_instance_resources) == 0:
            self.exit_error(
                "More than one instance with evc_id {} - Cannot determine correct Routing Instance".format(evc_id)
            )

        elif len(network_instance_resources) > 1:
            self.exit_error(
                "More than one instance with evc_id {} and vpls_vlan_id {} - Cannot determine correct Routing Instance".format(
                    evc_id, vpls_vlan
                )
            )

        else:
            return network_instance_resources

    @staticmethod
    def add_remove_interface_to_network_interface(self, network_instance, interface, add_interface=True):
        """adds the interface to the network instance if it is not there.

        No return

        :param network_instance: tosca.resourceTypes.NetworkInstance
        :param interface: Interface name (ge-0/0/4.200)
        :param add_interface: If true, adding interface
        :type network_instance: dict
        :type interface: str
        :type add_interface: boolean
        """
        does_interface_exist = False

        self.logger.info(
            "---- network_instance within add_remove_interface_to_network_interface: {}".format(network_instance)
        )
        interfaces = network_instance["properties"]["interfaces"]
        updated_interfaces = []
        for intf in interfaces:
            if intf["config"]["interface"] == interface:
                does_interface_exist = True
                break
            updated_interfaces.append(intf)

        if add_interface is True and does_interface_exist is False:
            self.logger.debug("Interface {} does not exist on Network Instance, so adding.".format(interface))
            updated_interfaces.append({"config": {"interface": interface}})
        elif add_interface is False and does_interface_exist is True:
            self.logger.debug("Interface {} exists on Network Instance, so removing.".format(interface))

        if len(updated_interfaces) != len(interfaces):
            patch = {"properties": {"interfaces": updated_interfaces}}
            self.bpo.resources.patch(network_instance["id"], patch)
        else:
            self.logger.debug("No changes in interfaces on Network Instance, skipping")
