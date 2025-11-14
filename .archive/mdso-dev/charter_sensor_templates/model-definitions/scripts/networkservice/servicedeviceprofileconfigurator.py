""" -*- coding: utf-8 -*-

ServiceDeviceProfileConfigurator Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of ServiceDeviceProfileConfigurator plans

"""

import sys

sys.path.append("model-definitions")
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """
    This is the class that is called for the initial activation of the
    ServiceDeviceProfileConfigurator.
    """

    def process(self):
        # Get network service if exists
        self.network_service = self.get_associated_network_service_for_resource(self.params["resourceId"])

        circuit_details_id = self.properties["circuit_details_id"]
        context = self.properties["context"]
        operation = self.properties["operation"]

        # Get the circuit details
        self.circuit_details = self.get_resource(circuit_details_id)
        self.circuit_id = self.circuit_details["properties"]["serviceName"]

        evc = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]
        self.logger.info(f"EVC details are {evc}")

        if operation == "NETWORK_SERVICE_UPDATE":
            devices = self.get_all_circuit_devices(self.circuit_details)
        elif operation == "CPE_ACTIVATION":
            devices = self.get_affected_devices_from_circuit(self.params["resourceId"], self.circuit_details, operation)
        elif "SERVICE_MAPPER" in operation:
            service_mapper = self.get_associated_resource(self.resource["id"], self.BUILT_IN_SERVICE_MAPPER_TYPE)
            service_mapper_remediation = self.is_service_mapper_remediation(service_mapper)

            if context == "CPE":
                devices = self.get_tids_from_circuit_details(self.circuit_details, role="CPE")
            else:
                devices = self.get_all_circuit_devices(self.circuit_details)
        else:  # TODO this whole section can probably use some scrubbing
            self.network_service = self.get_associated_network_service_for_resource(self.params["resourceId"])
            devices = self.get_all_circuit_devices(self.circuit_details)

        # building list of devices with bw needed on them from services
        exclude_list = ["CPE_ACTIVATION", "SERVICE_MAPPER", "SERVICE_MAPPER_FIX"]
        device_list = []

        for device in devices:
            device_vendor = self.get_node_vendor(self.circuit_details, device)
            device_role = self.get_node_role(self.circuit_details, device)
            device_bpo_state = self.get_node_bpo_state(self.circuit_details, device)
            device_equipment_status = self.get_node_property(self.circuit_details, device, "Equipment Status")

            if self.bw_inclusion_required(device_vendor, device_role, context, device_bpo_state):
                if operation not in exclude_list and device_equipment_status == "LIVE" or operation in exclude_list:
                    if "evc-ingress-bwp" in evc.keys():
                        device_list.append({"name": device, "in_bw": evc["evc-ingress-bwp"]})

                    if "evc-egress-bwp" in evc.keys():
                        device_list.append({"name": device, "e_bw": evc["evc-egress-bwp"]})

                self.logger.info(f"Device list is {device_list}")

        for device in device_list:
            node_name = device["name"]
            node_vendor = self.get_node_vendor(self.circuit_details, node_name)
            node_fqdn = self.get_node_fqdn(self.circuit_details, node_name)
            device_role = self.get_node_role(self.circuit_details, node_name)

            node_ip = self.get_node_management_ip(self.circuit_details, node_name)
            node_model = self.get_node_model(self.circuit_details, node_name)
            self.logger.debug(f"Checking BW Profiles on device: {node_name}")
            self.logger.info(f"Node Vendor: {node_vendor}")

            # check if we need to skip applying policer to particular device role
            self.logger.debug("Checking BW skip policer")

            if self.is_skip_bw_policer(context, node_vendor, device_role, node_model):
                self.logger.debug(f"skip vendor {node_vendor}, role {device_role}, model {node_model}")
                continue

            network_function = self.get_network_function_by_host(node_fqdn)

            if network_function is None:
                network_function = self.get_network_function_by_host(node_ip)

            if network_function is None:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"No network function found for fqdn {node_fqdn} or ip {node_ip}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

            network_construct = None if node_vendor in ["NOKIA", "ALCATEL"] else self.get_network_construct_by_device_id(network_function["id"])
            # Calling plugin for devices which support device profile configurator
            # via plugin, Evenetually all devices shall move to plugin
            package = network_function["resourceTypeId"].split(".")[0]
            self.logger.info(f"Package from Network Function: {package}")
            profile_plugin_product = self.get_plugin_product(package, "charter.resourceTypes.ProfileConfigurator")
            self.logger.info(f"Profile Plugin Product: {profile_plugin_product}")

            if (
                profile_plugin_product
                and self.network_service
                or profile_plugin_product
                and self.is_standalone_service_mapper(operation)
            ):
                profile_object = {
                    "label": f"{node_name}-Profile-configurator",
                    "productId": profile_plugin_product,
                    "properties": {
                        "device_id": network_function["id"],
                        "nc_id": network_construct["id"],
                        "service_level": self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["cosNames"][
                            0
                        ]["name"],
                        "service_type": self.circuit_details["properties"]["serviceType"],
                        "port_role": self.get_node_client_interface_role(self.circuit_details, node_name),
                        "bandwidth": device["in_bw"] if "in_bw" in device.keys() else device["e_bw"],
                    },
                }
                parent_resource_id = (
                    service_mapper["id"] if self.is_standalone_service_mapper(operation) else self.network_service["id"]
                )
                profile_plugin_resource = self.bpo.resources.create(parent_resource_id, profile_object)
                self.bpo.relationships.delete_by_source_and_target(
                    parent_resource_id, profile_plugin_resource.resource_id
                )
                self.bpo.resources.delete(profile_plugin_resource.resource_id)
            else:
                # Get device dependents associated with BW_POLICER_TYPE
                lookup = self.COMMON_TYPE_LOOKUP[node_vendor]
                self.logger.info(f"LookUp: {lookup}")

                # not all devices may have bandwidth profiles supported, hence checking if it exists
                profile_resource_type = lookup.get("BW_POLICER_TYPE")
                self.logger.info(f"Profile Resource Type: {profile_resource_type}")

                if profile_resource_type is None:
                    self.logger.debug(
                        "skipping looking for bw profile as we don't have a bw profile product for this device"
                    )
                    continue

                bw_list = []

                for key in ["in_bw", "e_bw"]:
                    if key in device.keys():
                        bw_list.append(device[key])

                self.logger.info(f"Bandwidth List: {bw_list}")

                for bw in bw_list:
                    bandwidth_list = self.get_bandwidth_int_and_units(bw)
                    packet_bw_id = f"{bandwidth_list[0]}{bandwidth_list[1]}"
                    device_prid = network_function["providerResourceId"]
                    bw_profile_res_prid = (
                        f"{device_prid}::{('BWP2' if node_vendor.lower() == 'juniper' else 'BWP')}::{packet_bw_id}"
                    )

                    if node_vendor == "JUNIPER":
                        # Check if MX has been converted to EDNA to determine appropriate
                        # names to use for apply-groups, filters, and policers.
                        is_edna = self.check_is_edna(device_prid)
                        self.logger.info(f"IS_EDNA: {is_edna}")

                        if is_edna:
                            bw_profile_res_prid = "::RL_".join(bw_profile_res_prid.rsplit("::", 1))

                    self.logger.info(f"=======bw_profile_res_prid: {bw_profile_res_prid}")
                    domain_id = device_prid.split("_")[1]
                    packet_bw_profile_res = self.get_resource_by_provider_resource_id(
                        domain_id, bw_profile_res_prid, no_fail=True
                    )
                    self.logger.info(f"=======packet_bw_profile_res: {packet_bw_profile_res}")

                    if packet_bw_profile_res is None and operation == "SERVICE_MAPPER":
                        packet_bw_profile = self.get_packet_bw_profile_by_id(packet_bw_id, node_vendor)
                        packet_bw_profile["properties"]["id"] = f"BWP::{packet_bw_id}"
                        packet_bw_profile["properties"]["device"] = device_prid

                        # if statement wiil catch when BW profile doesn't exist on the device and patch SM
                        error_statement = (
                            f"Unable to find Packet Bw resource on Device {node_name} for BW {packet_bw_id}"
                        )
                        self.logger.info(error_statement)
                        tid = network_function["label"]

                        # patching differences to a seperate dictionary before remediation occurs
                        if service_mapper_remediation:
                            self.logger.info("PATCH to initial_differences")
                            self.bpo.resources.patch_observed(
                                service_mapper["id"],
                                data={
                                    "properties": {
                                        "initial_differences": {
                                            tid: {
                                                "bw_profile": {
                                                    "Network": "No matching BW profile on the device",
                                                    "Design": packet_bw_profile["properties"],
                                                }
                                            }
                                        }
                                    }
                                },
                            )
                        else:
                            self.logger.info("PATCH to service_differences")
                            self.bpo.resources.patch_observed(
                                service_mapper["id"],
                                data={
                                    "properties": {
                                        "service_differences": {
                                            tid: {
                                                "bw_profile": {
                                                    "Network": "No matching BW profile on the device",
                                                    "Design": packet_bw_profile["properties"],
                                                }
                                            }
                                        }
                                    }
                                },
                            )
                    elif packet_bw_profile_res and operation == "SERVICE_MAPPER":
                        # Getting Design BW profile
                        packet_bw_profile = self.get_packet_bw_profile_by_id(packet_bw_id, node_vendor)

                        # modifying design bw profile with additonal properties to compare against network
                        # props are for RAD vendor
                        packet_bw_profile["properties"]["id"] = f"BWP::{packet_bw_id}"

                        # converting design/ market resource to color blind
                        packet_bw_profile_res["properties"]["colorMode"] = "color-blind"

                        # removing properties that are hard coded by MDSO during a resync and do not need to be compared
                        additional_properties = [
                            "peakBurstSize",
                            "excessInformationRate",
                            "compensation",
                            "trafficType",
                        ]

                        for property in additional_properties:
                            packet_bw_profile_res["properties"].pop(property, None)
                            packet_bw_profile["properties"].pop(property, None)

                        packet_bw_profile_res["properties"].pop("device")
                        self.logger.info("bw profile found on device and service mapper exists")
                        self.logger.info(
                            f"packet_bw_profile, design: {packet_bw_profile} and packet_bw_profile_res, "
                            f"network: {packet_bw_profile_res}"
                        )

                        design_tupel_dict, network_tupel_dict = self.compare_bw_profile(
                            packet_bw_profile, packet_bw_profile_res
                        )

                        self.logger.info(
                            f"network_tupel_dict: {network_tupel_dict} and design_tupel_dict: {design_tupel_dict}"
                        )

                        if design_tupel_dict or network_tupel_dict:
                            tid = network_function["label"]

                            # patching differences to a seperate dictionary before remediation occurs
                            if service_mapper_remediation:
                                self.logger.info("PATCH to initial_differences")
                                self.bpo.resources.patch_observed(
                                    service_mapper["id"],
                                    data={
                                        "properties": {
                                            "initial_differences": {
                                                tid: {
                                                    "bw_profile": {
                                                        "Network": network_tupel_dict,
                                                        "Design": design_tupel_dict,
                                                    }
                                                }
                                            }
                                        }
                                    },
                                )
                            else:
                                self.logger.info("PATCH to service_differences")
                                self.bpo.resources.patch_observed(
                                    service_mapper["id"],
                                    data={
                                        "properties": {
                                            "service_differences": {
                                                tid: {
                                                    "bw_profile": {
                                                        "Network": network_tupel_dict,
                                                        "Design": design_tupel_dict,
                                                    }
                                                }
                                            }
                                        }
                                    },
                                )
                        return
                    elif packet_bw_profile_res is None:
                        self.logger.info(
                            f"Unable to find Packet BW resource on Device {node_name} for BW {packet_bw_id}"
                        )
                        self.logger.info("trying to find Packet BW resource in Planet Orchestrate domain")
                        # search bandwidth profile not restricted to one domain

                        # Build the RL_ policer if not already on device
                        if node_vendor.upper() == "JUNIPER" and is_edna:
                            packet_bw_id = f"RL_{packet_bw_id}"

                        packet_bw_profile = self.get_packet_bw_profile_by_id(packet_bw_id, node_vendor)

                        if packet_bw_profile is None:
                            msg = self.error_formatter(
                                self.MISSING_DATA_ERROR_TYPE,
                                self.TOPOLOGIES_DATA_SUBCATEGORY,
                                (
                                    f"BW profile for {packet_bw_id} neither exist on Device {node_name} "
                                    "or planet orchestrate domain"
                                ),
                                system=self.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            self.exit_error(msg)
                        else:
                            self.logger.info(f"Creating Bandwidth Profile {packet_bw_id} on the device {node_name}")
                            self.bw_profile_builder(
                                node_name,
                                packet_bw_profile,
                                network_function["id"],
                                network_function["providerResourceId"],
                                profile_resource_type,
                            )

    def is_standalone_service_mapper(self, operation):
        return operation == "SERVICE_MAPPER" and not self.network_service

    def bw_profile_builder(
        self, device, packet_bw_profile, networkfunction_id, providerResourceId, profile_resource_type
    ):
        """
        :param device:
        :param packet_bw_profile:
        :param networkfunction_id:
        :param profile_resource_type:
        :return:
        """
        domain_id = self.get_domain_id(networkfunction_id)
        index = 0

        while index < 6:
            device_profile_product_id = None

            try:
                device_profile_product_id = self.get_products_by_type_and_domain(profile_resource_type, domain_id)[0][
                    "id"
                ]
            except Exception:
                self.logger.warning(
                    f"Unable to get the product id {profile_resource_type} for domain {domain_id}, "
                    "waiting 10sec and trying again"
                )

            index += 1

        if device_profile_product_id is None:
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                (
                    f"Unable to get the product id {profile_resource_type} for domain {domain_id}, "
                    "waiting 10sec and trying again",
                ),
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        resource_body = self.create_pe_profile_body(
            device, networkfunction_id, packet_bw_profile, providerResourceId, device_profile_product_id
        )
        self.logger.info(f"Packet Bandwidth to add: {resource_body}")

        try:
            bw_resource = self.create_active_resource("test_profile", None, resource_body).resource
        except Exception as ex:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Unable to build BW profile/policer on device {device}, error {ex}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        # NOW SET THE RESOURCE TO DISCOVERED is True to act like it was from the network
        self.bpo.resources.patch(bw_resource["id"], {"discovered": True})

    def create_pe_profile_body(
        self, device, network_function_id, packet_bw_profile, providerResourceId, device_profile_product_id
    ):
        """
        :param device:
        :param packet_bw_profile:
        :param device_profile_product_id:
        :return:
        """

        """
            {
                "label": "troy1",
                "productId": "5a657f85-0b7c-4049-a103-ab69161553cc",
                "properties": {
                    "name": "troy1",
                    "excessBurstSize": {
                        "units": "bytes",
                        "value": 2000000
                    },
                    "committedBurstSize": {
                        "units": "bytes",
                        "value": 2000000
                    },
                    "committedInformationRate": {
                        "units": "bps",
                        "value": 20000000
                    },
                    "peakInformationRate": {
                        "units": "bps",
                        "value": 20000000
                    },
                    "peakBurstSize": {
                        "units": "bytes",
                        "value": 2000000
                    },
                    "device": "bpo_5a56c396-45e4-4122-a62b-89d9c49d9d14_5a657fe3-0b29-4dd3-a4a1-0c865887d959",
                    "colorMode": "color-aware"
                }
            }
        """
        profile_resource_body = {
            "label": f"{device}:{packet_bw_profile['label'].split(':')[-1]}",
            "productId": device_profile_product_id,
            "properties": {
                "device": network_function_id,
                "name": packet_bw_profile["properties"]["name"],
                "policerType": packet_bw_profile["properties"].get("policerType", "profile"),
            },
        }
        excess_burst_size = packet_bw_profile["properties"].get("excessBurstSize")

        if excess_burst_size:
            profile_resource_body["properties"]["excessBurstSize"] = excess_burst_size

        committed_burst_size = packet_bw_profile["properties"].get("committedBurstSize")

        if committed_burst_size:
            profile_resource_body["properties"]["committedBurstSize"] = committed_burst_size

        committed_information_rate = packet_bw_profile["properties"].get("committedInformationRate")

        if committed_information_rate:
            profile_resource_body["properties"]["committedInformationRate"] = committed_information_rate

        peak_information_rate = packet_bw_profile["properties"].get("peakInformationRate")

        if peak_information_rate:
            profile_resource_body["properties"]["peakInformationRate"] = peak_information_rate

        peak_burst_size = packet_bw_profile["properties"].get("peakBurstSize")

        if peak_burst_size:
            profile_resource_body["properties"]["peakBurstSize"] = peak_burst_size

        color_mode = packet_bw_profile["properties"].get("colorMode")

        if color_mode:
            profile_resource_body["properties"]["colorMode"] = color_mode

        additional_data = packet_bw_profile["properties"].get("additionalData")

        if additional_data:
            profile_resource_body["properties"]["additionalData"] = additional_data

        return profile_resource_body

    def bw_inclusion_required(self, device_vendor, device_role, context, device_bpo_state):
        if self.device_is_pe(context, device_role):
            return True

        if self.device_is_reachable_cpe(context, device_role, device_bpo_state):
            return True

        if self.device_is_bw_required_mtu(device_vendor, device_role, context):
            return True

        return False

    def device_is_pe(self, context, device_role):
        return device_role == "PE" or context == "PE" and device_role == "AGGREGATE"

    def device_is_reachable_cpe(self, context, device_role, device_bpo_state):
        return context == "CPE" and device_role in ["CPE"] and device_bpo_state == self.BPO_STATES["AVAILABLE"]["state"]

    def device_is_bw_required_mtu(self, device_vendor, device_role, context):
        if device_vendor.upper() in ["JUNIPER", "CIENA", "CISCO"]:
            return False

        inclusions = {
            "RAD": "BW_POLICER_INCLUSION_LIST",
            "ADVA": "MTU_BW_INCLUSION",
        }
        include_bw = inclusions[device_vendor]

        return (
            self.COMMON_TYPE_LOOKUP[device_vendor].get(include_bw)
            and self.COMMON_TYPE_LOOKUP[device_vendor][include_bw]["deviceRole"] == device_role
            and self.COMMON_TYPE_LOOKUP[device_vendor][include_bw]["context"] == context
        )
