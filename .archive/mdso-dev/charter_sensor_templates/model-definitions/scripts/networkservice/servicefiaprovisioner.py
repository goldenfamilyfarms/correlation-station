""" -*- coding: utf-8 -*-

ServiceDeviceOnboarder Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of Servicefiaprovisioner plans

"""

import sys
import re

sys.path.append("model-definitions")
from scripts.networkservice.peprovisioner import PeProvisioner
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan, PeProvisioner):
    """
    this is the class used for initial activation of service fia service provisioner
    """

    COS_LOOKUP = {
        "PE": {
            "NONE": "SERVICEPORT_UNCLASSIFIED_COS",
            "BRONZE": "SERVICEPORT_BRONZE_COS",
            "SILVER": "SERVICEPORT_SILVER_COS",
            "GOLD": "SERVICEPORT_GOLD_COS",
        },
        "CPE": {"NONE": "PBIT-0", "BRONZE": "PBIT-1", "SILVER": "PBIT-3", "GOLD": "PBIT-5"},
    }

    def process(self):
        self.operation = self.properties.get("operation", self.ACTIVATE_OPERATION_STRING)
        circuit_details_id = self.properties["circuit_details_id"]
        context = self.properties["context"]
        stage = self.properties["stage"]
        self.normalized_designed_model = None

        if not stage == "PRODUCTION":
            return

        # Get the circuit details and network service
        self.circuit_details = self.get_resource(circuit_details_id)
        self.service_type = self.circuit_details["properties"]["serviceType"]

        # return without doing anything if service is not FIA
        if not self.service_type == "FIA" or not context == "PE":
            if not self.service_type == "VOICE":
                return

        self.service_type = self.circuit_details["properties"]["serviceType"]
        self.circuit_id = self.circuit_details["properties"]["circuit_id"]
        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)

        if len(spoke_list) > 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                "FIA service should only have one spoke",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        # Get the PE from topology
        all_devices = []
        pe = None
        pe_id = None

        for spoke in spoke_list:
            for device, values in spoke.items():
                if (
                    values["Role"] == "PE"
                    and self.get_node_bpo_state(self.circuit_details, device) == self.BPO_STATES["AVAILABLE"]["state"]
                ):
                    pe_id = device
                    self.device_tid = device
                    pe = values
                    all_devices.append(values["Host Name"])

        if pe is None:
            if pe_id is not None:
                msg = self.error_formatter(
                    self.CONNECTIVITY_ERROR_TYPE,
                    self.RESOURCE_GET_SUBCATEGORY,
                    f"PE ({pe_id}) device not in active state, Please check RA logs and Device State",
                )
                self.categorized_error = msg
                self.exit_error(msg)
            else:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    "No PE provided in circuit path, please check Mulesoft details for the circuit.",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

        nf_resource = self.get_network_function_by_host_or_ip(pe["FQDN"], pe["Management IP"])
        fia_object = self.get_fia_service_object_from_details(pe, self.circuit_details)

        if self.operation == "MAP":
            fia_object["properties"]["service_mapper"] = True

        package = nf_resource["resourceTypeId"].split(".")[0]
        self.logger.info(f"package is {package}")
        fia_plugin_product = self.get_plugin_product(package, "charter.resourceTypes.FIAendpoint")
        self.logger.info(f"fia plugin product is {fia_plugin_product}")

        if self.operation == "MAP":
            self.logger.info("Service Mapper Processing")
            network_config_data = self.get_network_config_data(
                self.circuit_details,
                "FIA",
                self.device_tid,
                device_provider_resource_id=nf_resource["providerResourceId"],
                is_service_mapper=True,
            )
            self.service_mapper_process(fia_object, network_config_data, nf_resource, pe)
            return

        if self.operation == self.ACTIVATE_OPERATION_STRING:
            self.do_activate(pe, fia_object, fia_plugin_product)
            self.update_devices_prop_value([pe["Host Name"]], circuit_details_id, "Provisioned", "True")
        elif self.operation == self.UPDATE_OPERATION_STRING:
            self.do_update(pe, fia_object, fia_plugin_product)
        elif self.operation == self.TERMINATE_OPERATION_STRING:
            self.do_terminate(pe, nf_resource, self.circuit_details, fia_object, fia_plugin_product)
        else:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Invalid command received {self.operation}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

    def service_mapper_process(self, designed_model, network_config_data, nf_resource, pe):
        ipv4_address = self.get_ipv4()
        service_mapper = self.bpo.resources.get_one_by_filters(
            resource_type="charter.resourceTypes.ServiceMapper",
            q_params={"label": self.circuit_id},
        )
        network_model = self.model_network_data(network_config_data, nf_resource, ipv4_address)

        if network_model.get("error"):
            self.bpo.resources.patch_observed(
                service_mapper["id"],
                data={"properties": {"service_differences": {self.device_tid: network_model}}},
            )
        else:
            if self.service_type == "VOICE":
                voice_ip_in_arp_table = self.check_if_ip_in_arp_table(
                    nf_resource["providerResourceId"], designed_model, pe, ipv4_address
                )
                if not voice_ip_in_arp_table:
                    self.bpo.resources.patch_observed(
                        service_mapper["id"],
                        data={
                            "properties": {
                                "service_differences": {
                                    self.device_tid: {"voice_ip_in_arp_table": voice_ip_in_arp_table}
                                }
                            }
                        },
                    )

            self.normalized_designed_model = self.normalize_designed_model(designed_model)
            self.logger.info(
                f"IPv4 blocks:\nDesign_IPv4_block:\n{self.normalized_designed_model['ipv4']}\n"
                f"Network_IPv4_block:\n{network_model['ipv4']}",
            )
            network_model_ipv4_list = self.convert_ipv4_block_to_list(network_model["ipv4"])
            self.compare_design_ips_to_network(
                self.normalized_designed_model["ipv4"], network_model_ipv4_list, service_mapper["id"], self.device_tid
            )
            self.logger.info(
                f"final ipv4 diffies:\nDesign_IPv4_block:\n{self.normalized_designed_model['ipv4']}\n"
                f"Network_IPv4_block:\n{network_model['ipv4']}",
            )
            self.remove_ipv4_keys_from_network_and_design_models(network_model, self.normalized_designed_model)

            self.logger.info("Comparing modeled network data to modeled design data")
            self.logger.info(f"Network:\n{network_model}\nDesign:\n{self.normalized_designed_model}")
            network_diff, design_diff = self.resource_comparison_pe(network_model, self.normalized_designed_model)

            if design_diff:
                self.patch_service_mapper_diffs_tpe(
                    service_mapper["id"], self.device_tid, network_diff, design_diff, is_core=True
                )

    def convert_ipv4_block_to_list(self, ipv4_item) -> list:
        """makes sure that single items are in a list for later comparison"""
        if isinstance(ipv4_item, list):
            return ipv4_item

        return [ipv4_item]

    def remove_ipv4_keys_from_network_and_design_models(self, network_model, normalized_designed_model):
        """
        Removing ipv4 keys which will be compared seperately
        and convert / default network_model nextipv4hop value to list
        """
        network_model.pop("ipv4", None)
        normalized_designed_model.pop("ipv4", None)
        network_model["nextipv4hop"] = self.convert_ipv4_block_to_list(network_model["nextipv4hop"])

    def get_voice_arp_table(self, provider_resource_id, port, vlan) -> dict:
        """gets dictionary containing arp table info

        :param str provider_resource_id: _description_
        :param str port: device port (e.g. ge-1/1/1)
        :param str vlan: service vlan
        :return dict: the dictionary only contains arp info associated
        to port.vlan
        """
        port_vlan = f"|{port.lower()}.{vlan}"
        arp_response = self.execute_ra_command_file(
            provider_resource_id,
            "get-arp-query.json",
            parameters={"uniqueid": port_vlan},
            headers=None,
        ).json()["result"]
        return arp_response

    def calculate_ipv4_for_voice_device(self, ip_block) -> str:
        """
        Logically manipulates the ip/cidr to get the ip associated with the voice device
        Param: ip_block = ip/cidr
        """
        return ip_block[:-3].rstrip(ip_block[:-3].split(".")[3]) + str(int(ip_block[:-3].split(".")[3]) + 1)

    def iterate_arp_table_for_ip(self, arp_response, ip) -> bool:
        if arp_response.get("properties", dict()).get("result"):
            if isinstance(arp_response["properties"]["result"], list):
                return bool([arp for arp in arp_response["properties"]["result"] if ip in arp["ip-address"]])

            return bool(arp_response["properties"]["result"]["ip-address"] == ip)

        return False

    def check_if_ip_in_arp_table(self, prid, designed_model, pe, ipv4_address) -> bool:
        ip = self.calculate_ipv4_for_voice_device(ipv4_address[0])
        arp_response = self.get_voice_arp_table(
            prid, pe["Client Interface"].lower(), designed_model["properties"]["vlan"]
        )
        self.logger.info(f"arp_response: {arp_response}")
        voice_ip_in_arp_table = self.iterate_arp_table_for_ip(arp_response, ip)
        self.logger.info(f"Ip:\n{ip}\narp_response:\n{arp_response}\nvoice_ip_in_arp_table:\n{voice_ip_in_arp_table}")
        return voice_ip_in_arp_table

    def normalize_designed_model(self, designed_model):
        """
        This method normalizes the MDSO designed model to currently supported attributes for comparison
        Parameters:
            designed_model (dict): MDSO designed model
        Returns:
            normalized_designed_model (dict): Normalized designed model
        """
        output_policer = designed_model["properties"]["e_bwProfileFlowParameters"]

        if "RL" in output_policer:
            output_policer = output_policer.split("_")[1]

        normalized_model = {
            "userLabel": self.circuit_id,
            "e_bwProfileFlowParameters": output_policer,
            "in_bwProfileFlowParameters": designed_model["properties"].get("in_bwProfileFlowParameters"),
            "bandwidth_description": designed_model["properties"][
                "e_bwProfileFlowParameters"
            ],  # This should match on device to e_bwProfileFlowParameters
            "vlan": designed_model["properties"]["vlan"],
            "ipv6": designed_model["properties"].get("wanIpv6Address", "").lower(),
            "ipv4": designed_model["properties"]["lanIpv4Addresses"],
            "port_name": designed_model["properties"]["port_name"],
            "nextipv4hop": designed_model["properties"].get("nextIpv4Hop"),
        }
        normalized_model["nextipv4hop"] = self.convert_ipv4_block_to_list(normalized_model["nextipv4hop"])

        return normalized_model

    def model_network_data(self, network_config_data, nf_resource, ipv4_address):
        """
        This method models the network data to currently supported attributes for comparison
        Parameters:
            network_config_data (dict): Network config data
        Returns:
            network_model (dict): Network model
        """
        # Checks to see if device is actually configured or not before trying everything
        try:
            interface_name = list(network_config_data["subinterface_config"]["configuration"]["interfaces"].keys())[0]
        except Exception as ex:
            return {"error": f"Logical interface not configured on device:{self.device_tid}. Exception: {ex}"}

        network_config_data_sub = network_config_data["subinterface_config"]["configuration"]["interfaces"][
            interface_name
        ]["unit"][0]

        new_userlabel = self.check_network_userlabel(network_config_data_sub)
        output_policer = network_config_data_sub.get("layer2-policer", dict()).get("output-policer")
        get_ipv4_data = self.get_ipv4_next_hop_data(
            network_config_data, nf_resource["providerResourceId"], ipv4_address
        )
        self.logger.info(f"get_ipv4_data is: {get_ipv4_data}")

        if output_policer:
            if "RL" in output_policer:
                output_policer = output_policer.split("_")[1]

        return {
            "userLabel": new_userlabel,
            "e_bwProfileFlowParameters": output_policer,
            "in_bwProfileFlowParameters": network_config_data_sub.get("layer2-policer", dict()).get("input-policer"),
            "bandwidth_description": network_config_data_sub.get("bandwidth"),
            "vlan": network_config_data_sub.get("vlan-id"),
            "ipv6": network_config_data_sub["family"].get("inet6", dict()).get("address", dict()).get("name", ""),
            "ipv4": get_ipv4_data.get("name", "None"),
            "port_name": interface_name.upper(),
            "nextipv4hop": get_ipv4_data.get("next-hop", "None"),
        }

    def check_network_userlabel(self, network_config_data_sub):
        """
        As of 6/27/2023 we are only comparing the CID in the description
        """
        description = network_config_data_sub.get("description")

        if self.circuit_id in description:
            new_userlabel = self.circuit_id
        else:
            new_userlabel = network_config_data_sub.get("description")

        return new_userlabel

    def get_ipv4(self):
        """Gets lanIpv4Addresses from circuit details"""
        return self.circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"]

    def do_activate(self, pe, fia_object, fia_plugin_product):
        """Process activate of the PE resources"""
        # Get PE related FIA attributes
        if fia_plugin_product:
            fia_object["productId"] = fia_plugin_product
            network_service = self.get_associated_network_service(self.resource["id"])
            self.logger.info("==============FIA_OBJECT IS:==============")
            self.logger.info(fia_object)
            self.logger.info("====PE VALUES=====")

            if pe:
                self.logger.info(pe)
            else:
                self.logger.info("There is no pe, sorry")

            bpo_r_c_fia_object = fia_object

            if pe["Vendor"] == "CISCO":
                del bpo_r_c_fia_object["properties"]["firewallFilters"]

            self.logger.info("====THE bpo_r_c_fia_object IS===")
            self.logger.info(bpo_r_c_fia_object)

            self.bpo.resources.create(network_service["id"], bpo_r_c_fia_object)
            # Juniper doesn't currently support FIA service using plugin
        else:
            # Create logical Interface
            try:
                tpe = self.create_pe_tpe(fia_object["properties"])
            except Exception as ex:
                self.logger.exception(ex)
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, "Unable to create Logical TPE on PE device"
                )
                self.categorized_error = msg
                self.exit_error(msg)

            # Add Static Routes
            try:
                self.add_static_routes(fia_object)
            except Exception as ex:
                self.logger.info("Unable to Add Static Routes while Configuring PE Device")
                self.logger.error(str(ex), exc_info=True)
                msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                self.categorized_error = msg
                self.exit_error(msg)

            # check if the device is_edna, determine if firewall policer, bridge domain and apply group has been built and build if needed for unified communication/hosted voice.
            if self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0].get("msVlan"):
                interface = fia_object["properties"]["port_name"].lower()
                device_prid = self.get_network_function_by_host(pe["FQDN"])["providerResourceId"]
                downstream_dev_role = self.circuit_details["properties"]["topology"][0]["data"]["node"][1]["name"][1]["value"]
                downstream_dev_vendor = self.circuit_details["properties"]["topology"][0]["data"]["node"][1]["name"][2]["value"]
                required_apply_group = ""
                required_bandwidth = ""
                is_edna = self.check_is_edna(device_prid)

                if is_edna:
                    if downstream_dev_role == "AGG" and downstream_dev_vendor == "JUNIPER":
                        required_apply_group = "TP_SERVICEPORT-MS_CES"
                        required_bandwidth = "RL_CML_100M"
                    elif downstream_dev_role == "AGG" and downstream_dev_vendor['RAD', 'ADVA']:
                        required_apply_group = "TP_SERVICEPORT-MS_MTU"
                        required_bandwidth = "RL_CML_50M"
                    elif downstream_dev_role == "CPE":
                        required_apply_group = "TP_SERVICEPORT-MS_NID"
                        required_bandwidth = "RL_CML_10M"
                else:
                    if downstream_dev_role == "AGG" and downstream_dev_vendor == "JUNIPER":
                        required_apply_group = "SERVICEPORT-MS_CES"
                        required_bandwidth = "100M"
                    elif downstream_dev_role == "AGG" and downstream_dev_vendor['RAD', 'ADVA']:
                        required_apply_group = "SERVICEPORT-MS_MTU"
                        required_bandwidth = "50M"
                    elif downstream_dev_role == "CPE":
                        required_apply_group = "SERVICEPORT-MS_NID"
                        required_bandwidth = "10M"

                check_firewall_policer_present = self.execute_ra_command_file(
                    device_prid,
                    "confirm-firewall-policers.json",
                    parameters={
                        "bandwidth": required_bandwidth,
                    },
                    headers=None,
                ).json()["result"]

                if not check_firewall_policer_present:
                    try:
                        self.execute_ra_command_file(
                            device_prid,
                            "set-firewall-policer.json",
                            parameters={
                                "bandwidth": required_bandwidth,
                            }
                        )
                    except Exception as ex:
                        self.logger.info("Unable to Add Firewall Policy while Configuring PE Device")
                        self.logger.info(str(ex))
                        msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                        self.categorized_error = msg
                        self.exit_error(msg)

                is_ms_bridge_domain_present = self.execute_ra_command_file(
                    device_prid,
                    "get-bridge-domains.json",
                    parameters={
                        "interface": interface,
                        "unit": "88",
                        "bridge_domain": "CPEMGMT",
                    },
                    headers=None,
                )

                if is_ms_bridge_domain_present.json()["result"].lower() == "not present":
                    try:
                        self.execute_ra_command_file(
                            device_prid,
                            "set-bridge-domain-inner.json",
                            parameters={
                                "interface": interface,
                                "unit": "88",
                                "bridge_domain": "CPEMGMT",
                            },
                            headers=None,
                        )
                    except Exception as ex:
                        self.logger.info("Unable to Add MS Bridge Domain while Configuring PE Device")
                        self.logger.info(str(ex))
                        msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                        self.categorized_error = msg
                        self.exit_error(msg)

                is_ms_apply_group_present = self.execute_ra_command_file(
                    device_prid,
                    "get-apply-groups.json",
                    parameters={
                        "interface": interface,
                        "group": required_apply_group,
                    },
                    headers=None,
                ).json()["result"]

                if not is_ms_apply_group_present:
                    self.execute_ra_command_file(
                        device_prid,
                        "create-ms-apply-groups.json",
                        parameters={
                            "group": required_apply_group,
                            "bandwidth": required_bandwidth,
                        },
                        headers=None,
                    )
                    try:
                        self.execute_ra_command_file(
                            device_prid,
                            "set-apply-groups-inner.json",
                            parameters={
                                "group": required_apply_group,
                                "interface": interface,
                            },
                            headers=None,
                        )
                    except Exception as ex:
                        self.logger.info("Unable to Add MS Apply Group while Configuring PE Device")
                        self.logger.info(str(ex))
                        msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                        self.categorized_error = msg
                        self.exit_error(msg)
            try:
                self.commit_and_close(pe)
                self.await_active_collect_timing([str(tpe)], interval=3.0, tmax=300.0)
            except RuntimeError as e:
                resource_info = self.bpo.resources.get(tpe)
                self.logger.info(
                    f"Upon Failure Resource Status for {tpe} - Resource Type: {resource_info['resourceTypeId']}, ",
                    f"Resource Label: {resource_info['label']}, Orch State: {resource_info['orchState']}",
                )
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, f"TPE creation failed with reason: {e}"
                )
                self.categorized_error = msg
                self.exit_error(msg)
            except Exception as x:
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE,
                    self.RESOURCE_GET_SUBCATEGORY,
                    f"Failed to commit fia service hit exception: {x}",
                )
                self.categorized_error = msg
                self.exit_error(msg)

            # Build CPEMGMT for Type II Circuits
            if fia_object["properties"]["type_2"]:
                # check if cpe mgmt is built already
                device_prid = self.get_network_function_by_host(pe["FQDN"])["providerResourceId"]
                interface_config = self.execute_ra_command_file(
                    device_prid,
                    "get-interface-config.json",
                    parameters={"name": fia_object["properties"]["port_name"].lower()},
                    headers=None,
                ).json()["result"]
                outer_vlan = fia_object["properties"]["outer_vlan"]

                if not self.is_typeii_cpe_mgmt_built(interface_config, outer_vlan):
                    try:
                        is_edna = self.check_is_edna(device_prid)
                        self.logger.info(f"is_edna = {is_edna}")
                        cpegmt_cos_apply_group = "TP_SERVICEPORT_QF_MGMT" if is_edna else "SERVICEPORT_FC_MGMT"
                        cpe_tid = self.circuit_details["properties"]["topology"][0]["data"]["link"][0]["nodeEdgePoint"][
                            -1
                        ].split("-")[0]

                        cpemgmt_parameters = {
                            "interface": fia_object["properties"]["port_name"].lower(),
                            "outer_vlan": outer_vlan,
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
                        msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                        self.categorized_error = msg
                        self.exit_error(msg)

            try:
                self.commit_and_close(pe)
                self.await_active_collect_timing([str(tpe)], interval=3.0, tmax=300.0)
            except RuntimeError as e:
                resource_info = self.bpo.resources.get(tpe)
                self.logger.info(
                    f"Upon Failure Resource Status for {tpe} - Resource Type: {resource_info['resourceTypeId']}, ",
                    f"Resource Label: {resource_info['label']}, Orch State: {resource_info['orchState']}",
                )
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, f"TPE creation failed with reason: {e}"
                )
                self.categorized_error = msg
                self.exit_error(msg)
            except Exception as x:
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE,
                    self.RESOURCE_GET_SUBCATEGORY,
                    f"Failed to commit fia service hit exception: {x}",
                )
                self.categorized_error = msg
                self.exit_error(msg)

    def do_update(self, pe, fia_object, fia_plugin_product):
        """Process updates of the PE resources"""
        fia_object["properties"]["operation"] = self.UPDATE_OPERATION_STRING
        update_property = self.properties.get("update_property")

        if "bandwidth" in update_property:
            fia_object["properties"]["update_property"] = "bandwidth"
            self.bandwidth_update(pe, fia_object, fia_plugin_product)

        if "description" in update_property:
            fia_object["properties"]["update_property"] = "description"
            self.description_update(pe, fia_object, fia_plugin_product)

        if "adminState" in update_property:
            self.adminstate_update()

    def get_cir(self):
        bw = self.properties["bandwidthValue"]
        cir = int(re.findall(r"\d+", bw)[0]) * (
            1000000000 if "g" in bw.lower() else 1000000 if "m" in bw.lower() else 1000 if "k" in bw.lower() else 1
        )
        return cir

    def bandwidth_update(self, pe, fia_object, fia_plugin_product):
        """
        Method to update bandwidth for FIA service
        :param pe: pe device info from the spoke list
        :param fia_object: formed FIA propeties
        :param fia_plugin_product: FIA plugin product id
        :return: None
        """
        self.logger.info("Bandwidth update")
        self.logger.info("======= PE info from Circuit Details: =======")
        self.logger.info(pe)
        self.logger.info(f"FIA_OBJECT: {fia_object}")
        self.logger.info(f"FIA_PLUGIN_PRODUCT: {fia_plugin_product}")

        cid = fia_object["properties"]["userLabel"].split(":")[0]
        network_service = self.get_network_service_by_label(cid)
        self.logger.info(f"FOUND ACTIVE NETWORK SERVICE RESOURCE: {network_service}")

        if pe["Vendor"] == "CISCO":
            # If network service and fia plugin product already exist for circuit,
            #  create new plugin product w/ updated bw info
            if fia_plugin_product and network_service:
                self.logger.info("Creating FIA plugin resource for bandwidth update")
                fia_object["productId"] = fia_plugin_product
                fia_object["properties"]["firewallFilters"][0]["type"] = "ipv4"
                fia_object["properties"]["firewallFilters"][1]["type"] = "ipv6"
                fia_object["properties"]["e_bwProfileFlowParameters"] = self.properties["bandwidthValue"]

                # Create new Cisco FIA PE Endpoint Resource with updated bw value
                self.bpo.resources.create(network_service["id"], fia_object)

            interface = fia_object["properties"]["port_name"].replace("-", "/")

            # Define subinterface based on whether circuit is Type 2 or not
            if not fia_object["properties"]["type_2"]:
                subinterface = f"{interface}.{fia_object['properties']['vlan']}"
            else:
                evc_endpoints = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"]

                for endpoint in evc_endpoints:
                    if endpoint.get("unit"):
                        unit = endpoint["unit"]

                subinterface = f"{interface}.{unit}"

            # Get current subinterface configs
            pe_device = self.get_network_function_by_host(pe["FQDN"])
            self.logger.info("======= pe_device AKA network_function of the PE =======")
            self.logger.info(pe_device)

            device_prid = pe_device["providerResourceId"]
            subinterface_config = self.execute_ra_command_file(
                device_prid, "me3400/show-running-config-interface.json", parameters={"interface": subinterface}
            ).json()["result"]

            input_service_policy = subinterface_config["service_policy_input"]
            output_service_policy = subinterface_config["service_policy_output"]

            # Define parameters for updating bandwidth
            cos = fia_object["properties"]["cos"]
            pbit = self.get_pbit(cos)
            cir = int(re.findall(r"\d+", self.properties["bandwidthValue"])[0]) * (
                1000000000
                if "g" in self.properties["bandwidthValue"].lower()
                else (
                    1000000
                    if "m" in self.properties["bandwidthValue"].lower()
                    else 1000 if "k" in self.properties["bandwidthValue"].lower() else 1
                )
            )
            port_role = fia_object["properties"]["port_role"]
            bw_update_params = {
                "subinterface": subinterface,
                "oldInPolicy": input_service_policy,
                "oldOutPolicy": output_service_policy,
                "bandwidth": self.properties["bandwidthValue"],
                "cir": cir,
                "p-bit": pbit,
                "portRole": port_role,
            }
            # Remove current service policy(s) from the subinterface,
            #  build and assign new service policy(s) in its place
            self.execute_ra_command_file(device_prid, "update-bandwidth.json", parameters=bw_update_params)
        elif pe["Vendor"] == "JUNIPER":
            # Juniper doesn't currently support FIA service using plugin
            self.logger.info("Juniper does not currently support FIA service using plugin")
            self.logger.info(f"Updating bandwidth on device {pe['Host Name']}")

            # fetching interface values required to update PE device
            pe_device = self.get_network_function_by_host(pe["FQDN"])

            self.logger.info("======= pe_device AKA network_function of the PE =======")
            self.logger.info(pe_device)

            device_prid = pe_device["providerResourceId"]
            interface_name = pe["Client Interface"].lower()

            # fetching service values required to update PE device
            evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
            unit = "0" if evc["sVlan"].lower() == "untagged" else evc["sVlan"]

            try:
                egress_bw = self.properties["bandwidthValue"]
                ingress_bw = self.properties["bandwidthValue"]
            except Exception:
                egress_bw = evc.get("evc-egress-bwp")
                ingress_bw = evc.get("evc-ingress-bwp")

            service_type = self.circuit_details["properties"]["serviceType"]

            if egress_bw is None:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    "Egress Policer details missing in mulesoft response",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

            # Converting Bandwidths to standard format
            # Check if MX PE converted to EDNA/C3 & requires "RL_" in policer profile name
            is_edna = self.check_is_edna(device_prid)

            self.logger.info(f"is_edna = {is_edna}")

            egress_policer = self.get_bandwidth_formatted(egress_bw)
            ingress_policer = None if ingress_bw is None else self.get_bandwidth_formatted(ingress_bw)

            # Modify policer profile to use "RL_[in/egress_policer]"if MX converted to EDNA
            if is_edna:
                egress_policer = f"RL_{egress_policer}"
                ingress_policer = None if ingress_policer is None else f"RL_{ingress_policer}"

            bw = self.get_bw_in_kbps(egress_bw) if egress_bw is not None else self.get_bw_in_kbps(ingress_bw)

            # Check which policers are already present on interface
            policers_on_interface = self.execute_ra_command_file(
                device_prid,
                "get-logical-tpe.json",
                parameters={"interface": interface_name, "unit": unit},
                headers=None,
            )

            # Update the device
            params = {
                "interface": interface_name,
                "unit": unit,
                "bandwidth": bw,
                "output_policer": egress_policer,
                "service_type": service_type,
                "commit": True,
            }

            if "input-policer" in policers_on_interface.json()["result"] and ingress_policer:
                params["input_policer"] = ingress_policer

            self.execute_ra_command_file(device_prid, "update-logical-tpe.json", parameters=params, headers=None)

    def description_update(self, pe, fia_object, fia_plugin_product):
        """
        Method to update description for FIA service
        :param pe: pe device info from the spoke list
        :param fia_object: formed FIA propeties
        :param fia_plugin_product: FIA plugin product id
        :return: None
        """
        cid = fia_object["properties"]["userLabel"].split(":")[0]
        network_service = self.get_network_service_by_label(cid)
        self.logger.info(f"FOUND ACTIVE NETWORK SERVICE RESOURCE: {network_service}")
        self.logger.info("Description update")

        if fia_plugin_product and network_service:
            self.logger.info("Creating FIA plugin resource for description update")
            fia_object["productId"] = fia_plugin_product
            self.bpo.resources.create(network_service["id"], fia_object)
        else:
            # Juniper doesn't currently supports FIA service using plugin
            self.logger.info("Juniper does not currently support FIA service using plugin")
            self.logger.info(f"Updating description on device {pe['Host Name']}")

            # fetching interface values required to update PE device
            pe_device = self.get_network_function_by_host(pe["FQDN"])
            device_prid = pe_device["providerResourceId"]
            interface_name = pe["Client Interface"]
            client_port_decr = pe["Client Interface Description"]

            # Determine new or old logicial interface
            service_decr = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0][
                "userLabel"
            ]
            self.logger.info(f"service_decr using circuit_details as reference {service_decr}")

            # fetching service values required to update PE device
            evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
            unit = "0" if evc["sVlan"].lower() == "untagged" else evc["sVlan"]

            try:
                self.execute_ra_command_file(
                    device_prid,
                    "set-physical-interface-params-inner.json",
                    {"interface": interface_name.lower(), "param": "description", "description": client_port_decr},
                )

                self.execute_ra_command_file(
                    device_prid,
                    "update-logical-tpe-cmd.json",
                    {"interface": interface_name.lower(), "unit": str(unit), "description": service_decr},
                )
            except Exception as e:
                msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(e))
                self.categorized_error = msg
                self.exit_error(msg)

    def do_terminate(self, pe, nf_resource, circuit_details, fia_object, fia_plugin_product):
        """Terminate FIA service on PE"""
        cid = fia_object["properties"]["userLabel"].split(":")[0]
        network_service = self.get_network_service_by_label(cid)
        self.logger.info(f"FOUND ACTIVE NETWORK SERVICE RESOURCE: {network_service}")

        if fia_plugin_product and network_service:
            fia_object["productId"] = fia_plugin_product
            fia_object["properties"]["operation"] = self.TERMINATE_OPERATION_STRING
            nw_service_delete_res = self.bpo.resources.get_dependent_by_type(
                self.resource["id"], self.BUILT_IN_NETWORK_SERVICE_DELETE_TYPE
            )
            self.bpo.resources.create(nw_service_delete_res["id"], fia_object)
        else:
            # Juniper doesn't currently supports FIA service using plugin
            evc_data = circuit_details["properties"]["service"][0]["data"]["evc"][0]

            # remove the logical interface
            try:
                PeProvisioner.delete_pe_logical_ctp(
                    self, nf_resource, pe["Client Interface"].lower(), str(evc_data["sVlan"])
                )
            except Exception as ex:
                self.logger.info("Failure while deleting Interface from PE device")
                msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                self.categorized_error = msg
                self.exit_error(msg)

            # remove static routes
            try:
                self.delete_static_routes(nf_resource, fia_object)
            except Exception as ex:
                self.logger.info("Failure while deleting routes from PE device")
                msg = self.error_formatter(self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, str(ex))
                self.categorized_error = msg
                self.exit_error(msg)

    def add_static_routes(self, fia_object):
        device_rid = fia_object["properties"]["pe_device_rid"]
        device_pid = self.bpo.resources.get(device_rid)["productId"]
        device_prid = self.bpo.resources.get(device_rid)["providerResourceId"]
        domain_id = self.bpo.market.get(f"/products/{device_pid}")["domainId"]

        ipv4_res = self.bpo.resources.get_by_provider_resource_id(domain_id, f"{device_prid}::RIB::GlobalRouter")
        ipv6_res = self.bpo.resources.get_by_provider_resource_id(domain_id, f"{device_prid}::RIB::inet6.0")

        ipv4_data = self.execute_ra_command_file(
            device_prid, "get-fre.json", parameters={"data.id": "RIB::GlobalRouter"}, headers=None
        )
        ipv6_data = self.execute_ra_command_file(
            device_prid, "get-fre.json", parameters={"data.id": "RIB::inet6.0"}, headers=None
        )

        # Don't need to create any FIA FRE for FIA DIRECT
        if fia_object["properties"]["fia_type"] == "DIRECT":
            if "lanIpv6Addresses" in fia_object["properties"].keys():
                if not ipv6_res:
                    self.create_fia_static_fre(device_prid, fia_object["properties"], "ipv6")
                else:
                    self.update_fia_static_fre(ipv6_data.json()["result"], ipv6_res, fia_object["properties"], "ipv6")

        # Find if routing FREs already exist and update them, create if they do not exist
        if fia_object["properties"]["fia_type"] == "STATIC":
            if "lanIpv4Addresses" in fia_object["properties"].keys():
                if not ipv4_res:
                    self.create_fia_static_fre(device_prid, fia_object["properties"], "ipv4")
                else:
                    self.update_fia_static_fre(ipv4_data.json()["result"], ipv4_res, fia_object["properties"], "ipv4")

            if "lanIpv6Addresses" in fia_object["properties"].keys():
                if not ipv6_res:
                    self.create_fia_static_fre(device_prid, fia_object["properties"], "ipv6")
                else:
                    self.update_fia_static_fre(ipv6_data.json()["result"], ipv6_res, fia_object["properties"], "ipv6")

    def create_fia_static_fre(self, device_prid, properties, route_type):
        """creates the FRE object for FIA-STATIC"""
        fre_pid = self.get_product_id_by_type_domain("tosca.resourceTypes.FRE", self.domain_id)
        fre_properties = self.create_fre_properties(properties, route_type)
        fre_label = "RIB::" + ("GlobalRouter" if route_type == "ipv4" else "inet6.0")
        fre_object = {
            "id": fre_label,
            "resourceTypeId": "tosca.resourceTypes.FRE",
            "productId": fre_pid,
            "properties": fre_properties,
        }

        self.execute_ra_command_file(device_prid, "create-fre-routingInstance.json", fre_object, headers=None)

    def update_fia_static_fre(self, route_data, fre_res, properties, route_type):
        """Updates the fre for static route"""
        looper = properties["lanIpv4Addresses"] if route_type == "ipv4" else properties["lanIpv6Addresses"]

        for ip in looper:
            route_list_object = {
                "match": {
                    "routeType": {
                        route_type: {"destIpv4Address" if route_type == "ipv4" else "destIpv6Address": ip.lower()}
                    }
                },
                "nexthop": {
                    "nexthopType": {
                        "nexthopBase": {
                            "ipv4AddressNexthop" if route_type == "ipv4" else "ipv6AddressNexthop": (
                                properties["nextIpv4Hop"] if route_type == "ipv4" else properties["nextIpv6Hop"].lower()
                            )
                        }
                    }
                },
            }
            route_data["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"].append(
                route_list_object
            )
        """
        patch = {
            "properties": {
                "data": {
                    "attributes": {
                        "routingInstance": {
                            "ribList": route_data["properties"]["data"]["attributes"]["routingInstance"]["ribList"]
                        }
                    }
                }
            }
        }
        """
        device_prid = fre_res["providerResourceId"].split(":")[0]
        self.execute_ra_command_file(device_prid, "create-fre-routingInstance.json", route_data, headers=None)
        self.bpo.market.post(f"/resources/{fre_res['id']}/resync")

    def delete_static_routes(self, pe_device, fia_object):
        """Deletes the static routes created for FIA service"""
        device_prid = pe_device["providerResourceId"]

        # Getting required domain
        device_pid = pe_device["productId"]
        self.domain_id = self.bpo.market.get(f"/products/{device_pid}")["domainId"]

        ipv6_res = self.bpo.resources.get_by_provider_resource_id(self.domain_id, f"{device_prid}::RIB::inet6.0")
        fia_obj_properties = fia_object["properties"]

        if "lanIpv6Addresses" in fia_obj_properties.keys():
            if ipv6_res is None:
                pass
            else:
                self.delete_created_routes(ipv6_res, fia_obj_properties)

        if fia_obj_properties["fia_type"] == "STATIC":
            ipv4_res = self.bpo.resources.get_by_provider_resource_id(
                self.domain_id, f"{device_prid}::RIB::GlobalRouter"
            )

            if "lanIpv4Addresses" in fia_obj_properties.keys():
                if ipv4_res is None:
                    pass
                else:
                    self.delete_created_routes(ipv4_res, fia_obj_properties)

        self.logger.info("Done Deleting Routes")
        return {}

    def delete_created_routes(self, fre_res, properties):
        """deletes the routes added by this fia service from fre"""
        try:
            is_discovered = False
            route_type = "ipv6" if fre_res["label"].endswith("inet6.0") else "ipv4"
            looper = properties["lanIpv4Addresses"] if route_type == "ipv4" else properties["lanIpv6Addresses"]

            route_list = fre_res["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"]
            new_route_list = route_list

            for dest_ip in looper:
                for route in route_list:
                    existing_dest_ip = (
                        route["match"]["routeType"]["ipv4"]["destIpv4Address"]
                        if route_type == "ipv4"
                        else route["match"]["routeType"]["ipv6"]["destIpv6Address"]
                    )
                    if dest_ip.lower() == existing_dest_ip:
                        new_route_list.remove(route)

            fre_res["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"] = new_route_list
            patch = {"properties": fre_res["properties"]}

            if fre_res["discovered"] is True:
                is_discovered = True
                self.bpo.resources.patch(fre_res["id"], {"discovered": False})

            self.bpo.resources.patch(fre_res["id"], patch)

            if is_discovered is True:
                self.bpo.resources.patch(fre_res["id"], {"discovered": True})
        except Exception as err:
            self.logger.info(f"Error- {err}, while doing terminate")

            if is_discovered:
                self.bpo.resources.patch(fre_res["id"], {"discovered": True})

            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, f"Error- {err}, while doing terminate"
            )
            self.categorized_error = msg
            raise Exception(msg)

    def commit_and_close(self, pe):
        pe_device = self.get_network_function_by_host(pe["FQDN"])
        device_prid = pe_device["providerResourceId"]
        status = self.execute_ra_command_file(device_prid, "commit-close.json", retry=0)
        self.logger.info(f"THIS IS MY STATUS {status}")

        if status.status_code > 400:
            self.logger.info(f"Error committing in device. please see RA log for {device_prid}")
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_GET_SUBCATEGORY, f"Error commiting in device {pe['FQDN']}"
            )
            self.categorized_error = msg
            raise Exception(msg)

    def get_product_id_by_type_domain(self, resource_type, domain_id):
        """
        returns the product id based on resource type and
        domain (this needs to be moved to common.py)
        """
        product_list = self.bpo.market.get_products_by_resource_type(resource_type)

        if len(product_list) == 0:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"Unable to Find any products for type {resource_type}, make sure the products are on-boarded",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            raise Exception(msg)

        for product in product_list:
            if product["domainId"] == domain_id:
                required_pid = product["id"]

        if not required_pid:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"unable to find product for {resource_type} in domain {domain_id}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            raise Exception(msg)

        return required_pid

    def create_fre_properties(self, properties, route_type):
        """generate FRE object for FIA service"""
        fre_properties = {
            "device": self.bpo.resources.get(properties["pe_device_rid"])["providerResourceId"],
            "data": {
                "id": "RIB::" + ("GlobalRouter" if route_type == "ipv4" else "inet6.0"),
                "type": "fres",
                "attributes": {
                    "serviceClass": "IP",
                    "networkRole": "IFRE",
                    "adminState": "enabled",
                    "active": True,
                    "routingInstance": {
                        "name": "GlobalRouter" if route_type == "ipv4" else "inet6.0",
                        "ribList": [
                            {
                                "name": "GlobalRouter" if route_type == "ipv4" else "inet6.0",
                                "addressFamily": route_type,
                                "routeList": [],
                            }
                        ],
                    },
                },
            },
        }

        looper = properties["lanIpv4Addresses"] if route_type == "ipv4" else properties["lanIpv6Addresses"]

        for ip in looper:
            route_list_element = {
                "match": {
                    "routeType": {
                        route_type: {"destIpv4Address" if route_type == "ipv4" else "destIpv6Address": ip.lower()}
                    }
                },
                "nexthop": {
                    "nexthopType": {
                        "nexthopBase": {
                            "ipv4AddressNexthop" if route_type == "ipv4" else "ipv6AddressNexthop": (
                                properties["nextIpv4Hop"] if route_type == "ipv4" else properties["nextIpv6Hop"].lower()
                            )
                        }
                    }
                },
            }

            fre_properties["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"].append(
                route_list_element
            )

        return fre_properties

    def get_network_service_by_label(self, label):
        """
        return active Network Service resource that matches the provided label
          or None if active resource does not exist

        :param label: label of network service resource (usually CID)

        :return: Network Service resource object or None

        :rtype: dict or None
        """
        network_service_resource = self.bpo.resources.get_by_filters(
            "charter.resourceTypes.NetworkService", q_params={"label": label, "orchState": "active"}
        )
        self.logger.info(f"GET BY FILTERS RESPONSE: {network_service_resource}")

        if network_service_resource:
            return network_service_resource[0]

        self.logger.info(f"Unable to get Network Service resource for label: {label}")
        return None

    def get_pbit(self, cos):
        pbit = 5

        if "SILVER" in cos:
            pbit = 3

        if "BRONZE" in cos:
            pbit = 1

        if "UNCLASSIFIED" in cos:
            pbit = 0

        return pbit
