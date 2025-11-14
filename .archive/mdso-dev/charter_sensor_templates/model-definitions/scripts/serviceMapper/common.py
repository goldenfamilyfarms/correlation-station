""" -*- coding: utf-8 -*-

Common Mapper Plans

Versions:
   0.1 Oct 10, 2022
       Initial check in of common plan for mapper products
"""

import sys

sys.path.append("model-definitions")
from time import sleep

from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.common_plan import CommonPlan
from scripts.configmodeler.utils import NetworkCheckUtils
from scripts.serviceMapper.configDataModel import (
    REQUIRED_TPE_FRE_VALUES,
    REQUIRED_TPE_FRE_VALUES_ADVA_PRO,
)
from scripts.serviceMapper.device import Device


class Common(CommonPlan):
    """
    common functionalities utilized by mapper products
    """

    def create_modeled_config(self, payload) -> object:
        """
        create config modeler resource, either designed or network flavored
        :param payload: dict
        :param requested_model: str, either 'network' or 'designed'
        :return: config modeler resource data (modeled config)
        :rtype: object
        """
        config_modeler = self.bpo.resources.create(self.resource_id, payload)
        return config_modeler

    def create_config_modeler_payload(self, config_request_data) -> dict:
        """
        build payload needed to create config modeler resource
        :param device: dict of device data from circuit details
        :param requested_model: str, either 'network' or 'designed'
        :return: dict payload to create config modeler resource
        :rtype: dict
        """
        device = config_request_data["device"]
        payload = {
            "label": f"{device['Host Name']}.{config_request_data['requested_model']}",
            "productId": self.get_built_in_product(self.BUILT_IN_CONFIG_MODELER_TYPE)["id"],
            "properties": {
                "vendor": device["Vendor"],
                "device": device["Host Name"],
                "location": device["location"],
                "network_config": False,
                "circuit_id": config_request_data["circuit_id"],
                "circuit_details_id": config_request_data["circuit_details_id"],
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
            },
        }
        if config_request_data["requested_model"] == "network":
            payload["properties"]["network_config"] = True
        return payload

    def get_modeled_config(self, config_request_data) -> dict:
        payload = self.create_config_modeler_payload(config_request_data)
        self.logger.info(f"payload: {payload}")
        self.logger.info(f"Creating {config_request_data['requested_model']} config model")
        config_modeler = self.create_modeled_config(payload)
        # TODO add error handling for config_modeler creation fails
        return config_modeler.resource["properties"]["modeled_config"]

    def patch_discovered_data_to_properties(self, data_payload):
        self.bpo.resources.patch_observed(
            self.resource["id"],
            data={"properties": data_payload},
        )

    def get_network_service(self):
        """
        get network service resource by property: circuit id
        option to update resource with mdso_provisioned bool (True if resource, False if none)
        :param update_resource: bool, trigger to add mdso_provisioned bool to resource
        """
        network_service = self.get_resource_by_type_and_properties(
            self.BUILT_IN_NETWORK_SERVICE_TYPE,
            {"circuit_id": self.circuit_id},
            no_fail=True,
        )
        self.logger.info(f"Network Service: {network_service}")
        if network_service is None:
            self.logger.info("Network Service does not exist in MDSO. Proceeding as Standalone Mapper.")
        if network_service and network_service["orchState"] != "active":
            self.logger.info("Network Service OrchState is not active. Proceeding as Standalone Mapper.")
        return network_service

    def build_config_request_data(self, device_details: dict, model_type: str = "network") -> dict:
        """
        builds payload for config modeler resource creation
        :param device_details: contains device details required for modeling config
        :type device_details: dict
        :return: payload for config modeler resource creation
        :rtype: dict
        """
        return {
            "device": device_details,
            "circuit_id": self.circuit_id,
            "circuit_details_id": self.circuit_details_id,
            "requested_model": model_type,
        }

    def remove_irrelevant_data(self, found_config_model: dict, device: Device, service_type: str, model_type: str, full_path: bool = False, adva_pro=False) -> dict:
        utils = NetworkCheckUtils()
        model_type = model_type.lower() + "_config"
        for model in found_config_model[model_type]:
            # continue as ARP is not in required tpe/fre
            if model == "ARP":
                continue
            found_config_model[model_type][model] = utils.extract_needed_values_from_complex_dict(
                found_config_model[model_type][model],
                (
                    REQUIRED_TPE_FRE_VALUES[device.role][device.vendor][service_type][model]
                    if not adva_pro
                    else REQUIRED_TPE_FRE_VALUES_ADVA_PRO[device.role][device.vendor][service_type][model]
                ),
                full_path=full_path,
            )
        return found_config_model

    def get_network_config(self, device: Device, service_type: str, remove_irr_data: bool = True, full_path: bool = False) -> dict:
        config_request_data = self.build_config_request_data(device.details, "network")
        network_config_model = self.get_modeled_config(config_request_data)
        if remove_irr_data:
            return self.remove_irrelevant_data(
                network_config_model, device, service_type, "network", full_path=full_path
            )
        return network_config_model

    def get_designed_config(self, device: Device) -> dict:
        config_request_data = self.build_config_request_data(device.details, "designed")
        modeled_config_model = self.get_modeled_config(config_request_data)

        return modeled_config_model

    def add_data_id(self, handoff_port: str, model: dict):
        data_id_dictionary = {"data": {"id": handoff_port}}
        model.update(data_id_dictionary)
        return model

    def patch_service_diffs(self, network_resource_diff: dict, mdso_resource_diff: dict, tid: str, initial_map: bool):
        if not network_resource_diff:
            # nothing to patch
            return

        mapper = self.resource["properties"]
        if not mapper.get("service_differences"):
            mapper["service_differences"] = {}
        if not mapper["service_differences"].get(tid):
            mapper["service_differences"][tid] = {}
        if not mapper["service_differences"][tid].get("flow"):
            mapper["service_differences"][tid]["flow"] = {
                "Network": network_resource_diff,
                "Design": mdso_resource_diff,
            }
        else:
            network = mapper["service_differences"][tid]["flow"].get("Network")
            if not network:
                mapper["service_differences"][tid]["flow"].update({"Network": {}})
                network = mapper["service_differences"][tid]["flow"]["Network"]
            design = mapper["service_differences"][tid]["flow"]["Design"]
            network = network_resource_diff
            design = mdso_resource_diff
            mapper["service_differences"][tid]["flow"] = {"Network": network, "Design": design}

        if initial_map:
            try:
                self.bpo.resources.patch_observed(
                    self.resource_id, data={"properties": {"initial_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update initial differences", Exception)

        else:
            try:
                self.bpo.resources.patch_observed(
                    self.resource_id, data={"properties": {"service_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update service differences", Exception)

    def patch_error_msg(self, tid: str, initial_map: bool, error_msg: dict):
        mapper = self.resource["properties"]
        if not mapper.get("service_differences"):
            mapper["service_differences"] = {}
        if not mapper["service_differences"].get(tid):
            mapper["service_differences"][tid] = {}
        if not mapper["service_differences"][tid].get("flow"):
            mapper["service_differences"][tid]["flow"] = {"Design": error_msg}
        else:
            network = mapper["service_differences"][tid]["flow"].get("Network")
            if not network:
                mapper["service_differences"][tid]["flow"].update({"Network": {}})
                network = mapper["service_differences"][tid]["flow"]["Network"]
            design = mapper["service_differences"][tid]["flow"]["Design"]
            design.update(error_msg)
            mapper["service_differences"][tid]["flow"] = {"Network": network, "Design": design}

        if initial_map:
            try:
                self.bpo.resources.patch_observed(
                    self.resource_id, data={"properties": {"initial_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update initial differences", Exception)
        else:
            try:
                self.bpo.resources.patch_observed(
                    self.resource_id, data={"properties": {"service_differences": mapper["service_differences"]}}
                )
            except Exception:
                self.logger.error("Unable to update service differences", Exception)

    def slm_configuration_process(self):
        try:
            if self.service_type == "ELAN" and self.is_first_circuit():
                return "Origin site is the same as destination site. Skipping SLM configuration."
            self.configure_slm()
        except Exception as error:
            self.logger.error("Unable to complete SLM configuration. {}".format(error))

    def is_first_circuit(self) -> bool:
        return self.origin_cid == self.circuit_id

    def determine_origin_site(self):
        self.origin_cid = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["elanSlm"][0]["destinationCid"]
        self.origin_circuit_details_id = ""
        self.logger.info(f"Origin CID: {self.origin_cid}")
        self.logger.info(f"Origin CD ID: {self.origin_circuit_details_id}")

        try:
            self.origin_circuit_details = self._get_circuit_details(self.origin_cid)
            self.origin_circuit_details_id = self.origin_circuit_details["id"]
        except Exception as error:
            self.logger.info("Unable to get circuit details for origin circuit. {}".format(error))

    def configure_slm(self):
        data = {
            "label": f"{self.circuit_id}.slmConfigurator",
            "productId": self.get_built_in_product(self.BUILT_IN_SLM_CONFIGURATOR_TYPE)["id"],
            "properties": {
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
                "circuit_id": self.circuit_id,
                "circuit_details_id": self.circuit_details_id,
                "onboarding_complete": True,
            },
        }
        if self.service_type == "ELAN":
            data["properties"]["origin_cid"] = self.origin_cid
            data["properties"]["origin_cd_id"] = self.origin_circuit_details_id
        self.bpo.resources.create(self.resource_id, data=data)

    def slm_verification_process(self):
        self.logger.info("Beginning SLM traffic verification process")
        slm_traffic_passing = False if self.slm_eligible is False else self.slm_traffic_verification()
        # if traffic is not bidirectional, add slm traffic passing: false to differences
        if not slm_traffic_passing:
            slm_traffic_data = {"properties": {"slm_traffic_passing": False}}
            self.bpo.resources.patch_observed(self.resource["id"], slm_traffic_data)

    def slm_traffic_verification(self):
        # create slm resource
        slm_service = self.get_resource(self.create_slm_service_finder_resource().resource_id)
        # confirm slm configuration for circuit exists on probe
        if not slm_service["properties"]["slm_configuration"].get("probe"):
            return False
        # extract slm config details from resource properties
        probe_device_slm_data = slm_service["properties"]["slm_configuration"]["probe"]
        if not probe_device_slm_data["maintenance_association"]:
            return False
        self.logger.info("Probe device SLM config data: {}".format(probe_device_slm_data))
        network_function = (
            self.bpo.resources.get(probe_device_slm_data["device_details"]["network_function_resource_id"])
            if probe_device_slm_data["device_details"]["network_function_resource_id"] is not None
            else self.get_network_function_by_host_or_ip(
                probe_device_slm_data["device_details"]["fqdn"],
                probe_device_slm_data["device_details"]["mgmt_ip"],
            )
        )
        # build command data for slm traffic verification command variables
        # (maintenance domain id, maintenance association id)
        command_data = self.create_slm_command_data(probe_device_slm_data)
        # determine command file based on connection type
        command_file = self.determine_command_file_name(self.get_network_function_connection_type(network_function))
        self.logger.info(f"Sending initial slm traffic commands to {probe_device_slm_data['device_details']['fqdn']}.")
        sleep(60)  # allow time for traffic to begin passing
        try:
            initial_slm_traffic_output = self.__send_commands(
                network_function["providerResourceId"], command_file, command_data
            ).json()["result"]
        except Exception as error:
            self.logger.info(f"Error issuing traffic statistics command: {error}")
            return False
        sleep(1)
        self.logger.info("Sending secondary slm traffic commands.")
        second_slm_traffic_output = self.__send_commands(
            network_function["providerResourceId"], command_file, command_data
        ).json()["result"]
        self.logger.info("Checking for bidirectional SLM traffic.")
        return self.is_slm_traffic_passing_bidirectionally(
            initial_slm_traffic_output,
            second_slm_traffic_output,
            probe_device_slm_data["device_details"]["vendor"],
            command_data["ma"],
        )

    def create_slm_service_finder_resource(self):
        product = self.BUILT_IN_SLM_SERVICE_FINDER_TYPE
        details = {
            "label": f"{self.circuit_id}.slmServiceFinder",
            "productId": self.get_built_in_product(product)["id"],
            "properties": {
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
                "circuit_id": self.circuit_id,
                "circuit_details_id": self.circuit_details_id,
                "onboarding_complete": True,
            },
        }
        if self.service_type == "ELAN":
            details["properties"]["origin_cid"] = self.origin_cid
            details["properties"]["origin_cd_id"] = self.origin_circuit_details_id
        self.logger.info(f"Creating SLM Service Finder resource for {self.circuit_id}")
        return self.bpo.resources.create(parent_resource_id=self.resource_id, data=details)

    def create_slm_command_data(self, probe_device_slm_data):
        self.logger.info("SLM traffic statistics command variables:")
        self.logger.info(f"maintenance domain {probe_device_slm_data['maintenance_domain']}")
        self.logger.info(f"maintenance association {probe_device_slm_data['maintenance_association']}")
        return {
            "md": probe_device_slm_data["maintenance_domain"],
            "ma": probe_device_slm_data["maintenance_association"],
            "mep": probe_device_slm_data["mep"],
        }

    def determine_command_file_name(self, network_function_connection_type):
        self.logger.info(f"Probe device connection type: {network_function_connection_type}")
        command_file = {
            "cli": "show-slm-traffic-stats.json",
            "netconf": "show-slm-traffic-stats-netconf.json",
        }
        return command_file[network_function_connection_type]

    def __send_commands(self, device, commandfile, data=None):
        # intake necessary device details to be able to log in and issue commands
        self.cutthrough = RaCutThrough()
        return RaCutThrough().execute_ra_command_file(device, commandfile, parameters=data)

    def is_slm_traffic_passing_bidirectionally(self, initial_slm_traffic_output, second_slm_traffic_output, probe_vendor, maintenance_association_id):
        # verify output of slm traffic check command
        # return True if traffic is passing bidirectionally else return False
        self.logger.info(f"Initial traffic command response: {initial_slm_traffic_output} Second traffic command response: {second_slm_traffic_output}")
        if not initial_slm_traffic_output or not second_slm_traffic_output:
            return False
        is_traffic_incrementing = {
            "RAD": self.is_traffic_incrementing_rad,
            "ADVA": self.is_traffic_incrementing_adva,
        }
        # compare initial and secondary values to confirm traffic is incrementing (and therefore non-zero)
        if isinstance(initial_slm_traffic_output, list):
            incrementing_traffic = is_traffic_incrementing[probe_vendor](
                initial_slm_traffic_output[0],
                second_slm_traffic_output[0],
                maintenance_association_id,
            )
        if isinstance(initial_slm_traffic_output, dict):
            incrementing_traffic = is_traffic_incrementing[probe_vendor](
                initial_slm_traffic_output,
                second_slm_traffic_output,
                maintenance_association_id,
            )
        all_values_incrementing = all(incrementing_traffic.values())
        self.logger.info(f"Traffic incrementing comparison: {incrementing_traffic} SLM traffic passing: {all_values_incrementing}")
        return all_values_incrementing

    def is_traffic_incrementing_rad(self, initial_slm_traffic_output, second_slm_traffic_output, maintenance_association_id=None):
        return {
            "tx_forward": int(initial_slm_traffic_output["txFramesForward"]) < int(second_slm_traffic_output["txFramesForward"]),
            "tx_backward": int(initial_slm_traffic_output["txFramesBackward"]) < int(second_slm_traffic_output["txFramesBackward"]),
            "rx_forward": int(initial_slm_traffic_output["rxFramesForward"]) < int(second_slm_traffic_output["rxFramesForward"]),
            "rx_backward": int(initial_slm_traffic_output["rxFramesBackward"]) < int(second_slm_traffic_output["rxFramesBackward"]),
        }

    def is_traffic_incrementing_adva(self, initial_slm_traffic_output, second_slm_traffic_output, maintenance_association_id=None):
        if initial_slm_traffic_output.get("transmitted"):
            return {
                "probe_to_reflector": int(initial_slm_traffic_output["transmitted"]) < int(second_slm_traffic_output["transmitted"]),
                "reflector_to_probe": int(initial_slm_traffic_output["received"]) < int(second_slm_traffic_output["received"]),
            }
        else:
            normalized_initial_transmitted = self.normalize_netconf_traffic_command_response(initial_slm_traffic_output, maintenance_association_id, "out")
            normalized_second_transmitted = self.normalize_netconf_traffic_command_response(second_slm_traffic_output, maintenance_association_id, "out")
            normalized_initial_received = self.normalize_netconf_traffic_command_response(initial_slm_traffic_output, maintenance_association_id, "in")
            normalized_second_received = self.normalize_netconf_traffic_command_response(second_slm_traffic_output, maintenance_association_id, "in")
            return {
                "probe_to_reflector": normalized_initial_transmitted < normalized_second_transmitted,
                "reflector_to_probe": normalized_initial_received < normalized_second_received,
            }

    def normalize_netconf_traffic_command_response(self, traffic_command_response, maintenance_association_id, traffic_direction):
        for maintenance_association in traffic_command_response["data"]["maintenance-domain"]["maintenance-association"]:
            if maintenance_association["id"] == maintenance_association_id:
                if traffic_direction == "out":
                    return int(maintenance_association["maintenance-association-end-point"]["continuity-check"]["sent-ccms"])
                if traffic_direction == "in":
                    return int(maintenance_association["maintenance-association-end-point"]["continuity-check"]["total-ccm-in"]["#text"])

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
            "ipv4": designed_model["properties"]["lanIpv4Addresses"][0],
            "port_name": designed_model["properties"]["port_name"],
            "nextipv4hop": designed_model["properties"].get("nextIpv4Hop"),
        }
        return normalized_model
