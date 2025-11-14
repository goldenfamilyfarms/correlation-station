""" -*- coding: utf-8 -*-

Disconnect Mapper Plans

Versions:
    0.1 Oct 10, 2022
        Initial check in of disconnectMapper plans
"""
import sys

sys.path.append("model-definitions")
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.serviceMapper.common import Common, Device
from scripts.slm.slmServiceFinder import SLMServiceFinder
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.configmodeler.utils import NetworkCheckUtils


class Activate(Common):
    MODELED_CONFIG_TYPES = {
        "service": "FRE",
        "port": "Client TPE",
    }

    ELINE_TOPOLOGY = {"a_side": 0, "z_side": 1}

    def process(self):
        properties = self.resource["properties"]
        self.circuit_id = properties["circuit_id"]
        self.slm_eligible = properties.get("slm_eligible")
        self.origin_cid = None  # will be updated in ELAN process if needed
        self.configuration_found = {}
        self.cutthrough = RaCutThrough()
        self.utils = NetworkCheckUtils()
        self.set_circuit_details_properties()
        self.network_service = self.get_network_service()
        if self.network_service:
            self.patch_discovered_data_to_properties({"network_service_id": self.network_service["id"]})
        self.service_type = self.get_network_service_type()

        if self.is_unsupported_topology():
            self.log_unsupported()
            return

        service_type_process = {
            "FIA": self.process_ip_based_service,
            "ELINE": self.process_eline,
            "VOICE": self.process_ip_based_service,
            "ELAN": self.process_elan,
        }

        service_type_process[self.service_type]()

        if self.configuration_found:
            self.patch_discovered_data_to_properties({"configuration_found": self.configuration_found})

    def set_circuit_details_properties(self):
        circuit_details = CircuitDetailsHandler(plan=self, circuit_id=self.circuit_id, operation="DISCONNECT_MAPPER")
        circuit_details.device_onboarding_process()
        self.circuit_details_id = circuit_details.circuit_details_id
        self.circuit_details = circuit_details.circuit_details

    def get_network_service_type(self):
        return self.circuit_details["properties"]["serviceType"]

    def is_unsupported_topology(self):
        return self.service_type == "ELINE" and self.is_locally_switched(self.circuit_details)

    def log_unsupported(self):
        self.logger.info(f"Locally Switched Circuit: {self.circuit_id}")
        self.patch_discovered_data_to_properties(
            {"failure_status": "Unsupported service type: locally switched ELINE."}
        )

    def process_ip_based_service(self):
        self.set_ip_addresses()
        topology_devices = self.get_devices_from_circuit_details(self.circuit_details)
        self.logger.info(f"topology_devices {topology_devices}")
        disconnect_type = self.properties["z_side_disconnect"]
        self.check_device_configs(topology_devices, disconnect_type)
        if disconnect_type == "FULL":
            self.is_optic_slotted(topology_devices, side="z_side")

    def set_ip_addresses(self):
        self.lan_ipv4 = self.get_lan_ip_addresses("lanIpv4Addresses")
        self.lan_ipv6 = self.get_lan_ip_addresses("lanIpv6Addresses")

    def get_lan_ip_addresses(self, ip_version: str) -> str:
        try:
            lan_ips = self.circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0][ip_version][0]
        except IndexError:
            lan_ips = None
        return lan_ips

    def process_eline(self):
        self.process_eline_side("a_side")
        self.process_eline_side("z_side")
        if self.slm_eligible:
            self.set_slm_service_finder()
            slm_found, slm_device = self.verify_slm_configs()
            if any(slm_found.values()):
                self.update_configuration_found(slm_device, slm_found)

    def process_eline_side(self, side: str):
        disconnect_type_by_side = {
            "a_side": self.properties["a_side_disconnect"],
            "z_side": self.properties["z_side_disconnect"],
        }
        topology_side = self.circuit_details["properties"]["topology"][self.ELINE_TOPOLOGY[side]]
        topology_side_devices = self.get_topology_devices_by_side(topology_side)
        side_disconnect_type = disconnect_type_by_side[side]
        self.check_device_configs(topology_side_devices, side_disconnect_type)
        if side_disconnect_type == "FULL":
            self.is_optic_slotted(topology_side_devices, side)

    def get_topology_devices_by_side(self, topology_side: dict) -> list:
        return [node for node in topology_side["data"]["node"]]

    def process_elan(self):
        topology_devices = self.get_devices_from_circuit_details(self.circuit_details)
        self.logger.info(f"topology_devices {topology_devices}")
        disconnect_type = self.properties["z_side_disconnect"]
        self.check_device_configs(topology_devices, disconnect_type)
        if disconnect_type == "FULL":
            self.is_optic_slotted(topology_devices, side="z_side")
        if self.slm_eligible:
            self.determine_origin_site()
            self.set_slm_service_finder()
            slm_found, slm_device = self.verify_slm_configs()
            if any(slm_found.values()):
                self.update_configuration_found(slm_device, slm_found)

    def check_device_configs(self, topology_devices: list, disconnect_type: str):
        for device_data in topology_devices:
            device = Device(device_data, disconnect_type)
            if self.device_verification_not_required(device):
                continue
            network_config_model = self.get_network_config(device, self.service_type)

            network_config_model = self.validate_network_model(device, network_config_model)

            configs_found = self.verify_configs_are_removed(network_config_model, device)
            if any(configs_found.values()):
                unremoved_config_data = self.get_unremoved_config_data(network_config_model, configs_found)
                self.create_configuration_found(device, unremoved_config_data)
            if self.remnant_config_check_required(device.vendor):
                self.logger.info(f"Performing checks beyond Granite configuration comparison on device {device.tid}.")
                remnant_configs_found = self.verify_remnant_configs(device)
                if any(remnant_configs_found.values()):
                    self.update_configuration_found(device.tid, remnant_configs_found)

    def validate_network_model(self, device: Device, network_config_model):
        model_type = "network_config"
        for model in network_config_model[model_type]:
            if (model == "Client TPE" or (model == "FRE" and device.vendor == "CISCO")) and device.port_check_required:
                network_config_model[model_type][model] = self.verify_admin_state_and_port_description(
                    network_config_model[model_type][model], device.vendor
                )
            else:
                network_config_model[model_type][model] = {}
            if network_config_model[model_type][model]:
                network_config_model[model_type][model] = self.add_data_id(
                    device.handoff_port, network_config_model[model_type][model]
                )
        self.logger.info(f"Validated network model: {network_config_model}")
        return network_config_model

    def verify_admin_state_and_port_description(self, model_data, vendor):
        if vendor == "CISCO":
            model_data = self.sanitize_cisco(model_data)
        model_data = self.verify_admin_state(model_data, vendor)
        model_data = self.verify_port_description(model_data)
        return model_data

    def verify_admin_state(self, model_data, vendor):
        if vendor == "JUNIPER" and model_data.get("apply-groups"):
            if "DISABLEIF" in model_data["apply-groups"]:
                del model_data["apply-groups"]
        if vendor in ["ADVA", "RAD"] and model_data.get("state"):
            if "OOS_AUMA" in model_data["state"]:
                del model_data["state"]
        if vendor == "CISCO" and model_data.get("state"):
            if "OOS" == model_data["state"]:
                del model_data["state"]
        return model_data

    def verify_port_description(self, model_data):
        if "userLabel" in model_data and model_data["userLabel"] in [None, "None", "none", ""]:
            del model_data["userLabel"]
        if "portDescription" in model_data and model_data["portDescription"] in [None, "None", "none", ""]:
            del model_data["portDescription"]
        return model_data

    def sanitize_cisco(self, fre):
        sanitized_fre = {}
        keys = ["state", "portDescription"]
        for key in keys:
            if fre.get(key):
                sanitized_fre[key] = fre.get(key)
        return sanitized_fre

    def update_configuration_found(self, device: str, remnant_configs_found: dict):
        for config_found in remnant_configs_found:
            if remnant_configs_found[config_found] is True:
                if device not in self.configuration_found:
                    self.configuration_found[device] = {}
                    self.configuration_found[device][config_found] = True
                else:
                    self.configuration_found[device].update({config_found: True})

    def device_verification_not_required(self, device: Device) -> bool:
        self.logger.info(f"{device.tid} equipment status: {device.equipment_status}")
        if device.equipment_status == "PENDING DECOMMISSION":
            return True
        admin_down_mgmt = False
        if device.role == "CPE" and self.is_admin_down(
            device.details["Network Neighbor"], device.details["Network Neighbor Interface"]
        ):
            admin_down_mgmt = True
        return True if admin_down_mgmt else False

    def is_admin_down(self, device_tid, interface):
        self.logger.info(f"Checking admin state of {device_tid} {interface}")
        try:
            provider_resource_id = self.get_provider_resource_id(device_tid, is_hostname_tid=True)
        except NoNetworkFunction:
            self.logger.warning(f"No network function for {device_tid}")
            return False
        try:
            response = self.cutthrough.execute_ra_command_file(
                device=provider_resource_id,
                command_file="get-interface-admin-state.json",
                parameters={"name": interface.lower()},
            )
        except Exception as e:
            self.logger.info(f"Exception raised during get interface admin state: {e}")
            self.logger.info(f"Card is not slotted for CPE-facing interface {interface}")
            return True
        admin_state = response.json()["result"]
        if isinstance(admin_state, dict):
            admin_state = admin_state["admin_state"]
        admin_down_states = ["down", "unassigned", "admin-down"]
        return True if admin_state.lower() in admin_down_states else False

    def verify_configs_are_removed(self, network_config_model: dict, device: Device) -> dict:
        """
        builds dictionary of configuration type: evaluation of network config presence
        :param network_config_model: dict, modeled device config from network data
        :param device: object, Device class object containing device attributes necessary for mapping decisions
        :return configs_found: dict, holds each sub-type of configuration verified for removal
        :rtype: dict
        """
        configs_found = {
            "service": self.is_config_present(network_config_model["network_config"]["FRE"]),
        }
        if device.port_check_required:
            configs_found["port"] = self.is_config_present(network_config_model["network_config"].get("Client TPE"))
        self.logger.info(f"Config removal verification: {configs_found}")
        return configs_found

    def is_config_present(self, config: dict) -> bool:
        return bool(config)

    def get_unremoved_config_data(self, network_config_model: dict, configs_found: dict) -> dict:
        """
        :param network_config_model: dict, model of config containing data discovered on network
        :param configs_found: dict, contains verification of removal (True | False) per config section (Service, Port)
        :return: unremoved config data, config type (Service, Port) and discovered network config data if any was found
        :rtype: dict
        """
        return {
            config_type: network_config_model["network_config"][self.MODELED_CONFIG_TYPES[config_type]]
            for config_type, config_found in configs_found.items()
            if config_found is True
        }

    def create_configuration_found(self, device: Device, unremoved_config_data: dict):
        """
        populates configuration_found attribute with any unremoved config data per device
        :param device: Device object
        :param unremoved_config_data: dict
        """
        self.configuration_found[device.tid] = {
            "vendor": device.vendor,
        }
        for config_type in unremoved_config_data:
            self.configuration_found[device.tid][config_type] = unremoved_config_data[config_type]

    def remnant_config_check_required(self, vendor: str) -> bool:
        return vendor in ("JUNIPER",)

    def verify_remnant_configs(self, device: Device) -> dict:
        """
        verify presence of circuit id on device and if ip block is routing if required
        :param fqdn: str, device fqdn
        :param device_role: str, device role
        :return: dict, remnant_configs_found
        """
        try:
            provider_resource_id = self.get_provider_resource_id(device.fqdn)
        except NoNetworkFunction:
            return {"unable_to_verify": True}
        if device.role == "PE":
            remnant_configs_found = self.verify_remaining_pe_configs(provider_resource_id, device)
        else:
            remnant_configs_found = self.verify_remaining_agg_mtu_configs(provider_resource_id, device)

        return remnant_configs_found

    def get_provider_resource_id(self, device: str, is_hostname_tid: bool = False) -> str:
        network_function = self.get_network_function_by_host(device, is_hostname_tid)
        if not network_function:
            self.logger.error(f"No network function, unable to send command to device {device}.")
            raise NoNetworkFunction
        return network_function["providerResourceId"]

    def verify_remaining_pe_configs(self, provider_resource_id: str, device: Device) -> dict:
        remnant_configs_found = {}
        subinterfaces = self.get_device_subinterfaces(provider_resource_id)
        remnant_configs_found["circuit_id_discovered"] = self.is_circuit_id_in_pe_descriptions(
            subinterfaces, provider_resource_id
        )
        if device.port_check_required:
            remnant_configs_found["subinterface_configurations_discovered"] = self.are_subinterfaces_configured(
                subinterfaces, device.handoff_port
            )
            if remnant_configs_found["subinterface_configurations_discovered"]:
                self.add_data_id(device.handoff_port, remnant_configs_found)
        if self.service_type == "FIA":
            remnant_configs_found["ip_routing"] = self.is_ip_routing(provider_resource_id)
        return remnant_configs_found

    def get_device_subinterfaces(self, provider_resource_id: str) -> list:
        response = self.cutthrough.execute_ra_command_file(
            provider_resource_id,
            "get_all_sub_interface_descriptions.json",
            parameters={},
            headers=None,
        ).json()
        return response["result"]["interface-information"]["logical-interface"]

    def is_circuit_id_in_pe_descriptions(self, subinterfaces: dict, provider_resource_id: str) -> bool:
        if self.is_circuit_id_in_subinterface_descriptions(subinterfaces):
            return True
        if self.service_type == "ELINE":
            if self.is_circuit_id_in_l2circuit_descriptions(provider_resource_id):
                return True
        return False

    def is_circuit_id_in_subinterface_descriptions(self, subinterfaces: list) -> bool:
        for subinterface in subinterfaces:
            if self.circuit_id in subinterface.get("description", "No description"):
                return True
        return False

    def is_circuit_id_in_l2circuit_descriptions(self, provider_resource_id: str) -> bool:
        descriptions = self.cutthrough.execute_ra_command_file(
            provider_resource_id,
            "get_all_l2_circuit_descriptions.json",
            parameters={},
            headers=None,
        ).json()
        l2circuits = descriptions["result"]["data"]["configuration"]["protocols"]["l2circuit"]["neighbor"]
        for l2circuit in l2circuits:
            if isinstance(l2circuit["interface"], list):
                for description in l2circuit["interface"]:
                    if self.circuit_id in description["description"]:
                        return True
            elif self.circuit_id in l2circuit["interface"]["description"]:
                return True
        return False

    def are_subinterfaces_configured(self, subinterfaces: list, handoff_port: str) -> bool:
        for subinterface in subinterfaces:
            if subinterface["name"].split(".")[0].upper() == handoff_port:
                return True
        return False

    def is_ip_routing(self, provider_resource_id: str) -> bool:
        ipv4_route = self.get_route_config(provider_resource_id, self.lan_ipv4)
        if self.is_ip_in_route_table(ipv4_route):
            return True

        if self.lan_ipv6:
            ipv6_route = self.get_route_config(provider_resource_id, self.lan_ipv6)
            if self.is_ip_in_route_table(ipv6_route):
                return True

        return False

    def is_ip_in_route_table(self, show_route_response: dict) -> bool:
        if show_route_response is None:
            return False
        if show_route_response["route-information"].get("route-table"):
            return True
        return False

    def verify_remaining_agg_mtu_configs(self, provider_resource_id: str, device: Device) -> dict:
        remnant_configs_found = {}
        device_vlans = self.get_device_vlans(provider_resource_id)
        remnant_configs_found["circuit_id_discovered"] = self.is_circuit_id_in_agg_mtu_descriptions(device_vlans)
        if device.port_check_required:
            port_vlans = self.get_port_vlans(provider_resource_id, device.handoff_port)
            remnant_configs_found["port_vlans_discovered"] = self.are_vlans_configured(port_vlans)

        return remnant_configs_found

    def get_device_vlans(self, provider_resource_id: str) -> list:
        response = self.cutthrough.execute_ra_command_file(
            provider_resource_id,
            "qfx5100/get_all_vlan_descriptions.json",
            parameters={},
            headers=None,
        ).json()
        return response["result"]["data"]["configuration"]["vlans"]["vlan"]

    def is_circuit_id_in_agg_mtu_descriptions(self, vlans: list) -> bool:
        for vlan in vlans:
            if vlan.get("description") and self.circuit_id in vlan["description"]:
                return True
        return False

    def get_port_vlans(self, provider_resource_id: str, port) -> list:
        response = self.cutthrough.execute_ra_command_file(
            provider_resource_id,
            "seefa-cd-show-interface-config.json",
            parameters={"interface": port.lower()},
            headers=None,
        ).json()
        response = response["result"]["data"]["configuration"]["interfaces"]["interface"]
        if response.get("unit"):
            response = response["unit"]["family"]["ethernet-switching"]["vlan"]["members"]
            if isinstance(response, list):
                return response
            return [response]
        return []

    def are_vlans_configured(self, port_vlans):
        if port_vlans:
            return True
        return False

    def set_slm_service_finder(self):
        self.slm_service_finder = SLMServiceFinder(
            self,
            self.circuit_id,
            self.circuit_details_id,
            onboarding_complete=True,
            core_only=True,
            origin_cid=self.origin_cid
        )

    def verify_slm_configs(self):
        """
        verify presence of slm configurations on required model (reflector, probe, y1731)
        :return: slm_found, required_model
        :rtype: dict, str | None
        """
        slm_found = {}

        required_model = self.determine_required_slm_model()
        if not required_model:
            self.logger.info("SLM check not required for probe/reflector vendors.")
            return slm_found, required_model

        slm_modeler = self.create_slm_modeler(required_model)
        if not slm_modeler:
            slm_found["unable_to_verify"] = True
            return slm_found, required_model

        slm_model = self.get_normalized_slm_model(slm_modeler)
        slm_found["slm"] = self.is_config_present(slm_model)

        return slm_found, required_model

    def determine_required_slm_model(self):
        """
        use slm service finder to determine if reflector, probe, both, or neither slm devices are required
        return required slm model
        :return required_model: str, required slm model (reflector, probe, y1731, None)
        :rtype: str or None
        """
        vendors = self.get_slm_device_vendors()
        reflector_model_required = self.remnant_config_check_required(vendors["reflector"])
        probe_model_required = self.remnant_config_check_required(vendors.get("probe", "No probe detected"))

        if reflector_model_required and not probe_model_required:
            model = "reflector"
        elif probe_model_required and not reflector_model_required:
            model = "probe"
        elif reflector_model_required and probe_model_required:
            model = "y1731"
        else:
            # no slm check required if no Juniper slm devices
            model = None

        return model

    def get_slm_device_vendors(self):
        slm_devices = iter(self.slm_service_finder.slm_devices)
        reflector_tid = next(slm_devices)
        probe_tid = None  # ELAN origin circuit will only have reflector
        reflector_vendor = self.slm_service_finder.slm_devices[reflector_tid]["vendor"]
        vendors = {"reflector": reflector_vendor}
        try:
            probe_tid = next(slm_devices)
        except StopIteration:
            self.logger.info("No probe device detected.")
        if probe_tid:
            probe_vendor = self.slm_service_finder.slm_devices[probe_tid]["vendor"]
            vendors["probe"] = probe_vendor
        return vendors

    def create_slm_modeler(self, required_model: str):
        slm_modeler = None
        slm_details = self.slm_service_finder.determine_circuit_slm_configuration(
            self.slm_service_finder.all_slm_configurations
        )
        try:
            slm_modeler = self.bpo.resources.create(
                self.resource_id,
                {
                    "label": f"{self.circuit_id}.disconnectMapper",
                    "productId": self.get_built_in_product(self.BUILT_IN_SLM_MODELER_TYPE)["id"],
                    "properties": {
                        "circuit_id": self.circuit_id,
                        "model_type": "network_config",
                        "requested_model": required_model,
                        "circuit_details_id": self.circuit_details_id,
                        "onboarding_complete": True,
                        "core_only": True,
                        "slm_details": slm_details,
                    },
                },
            )
        except RuntimeError:
            self.logger.info("Failed to create SLM Modeler resource, unable to verify SLM configurations.")
            slm_modeler = None
        return slm_modeler

    def get_normalized_slm_model(self, slm_modeler) -> dict:
        """
        get slm model from slm modeler resource; transform to standard empty dict if no configs found
        :param slm_modeler: slmModeler resource
        :type slm_modeler: resource
        :return: slm config modeled from network data, represented as empty dict if all values are None
        :rtype: dict
        """
        slm_model = self.bpo.resources.get(slm_modeler.resource["id"])["properties"]["y1731_model"]
        slm_model = self.utils.transform_null_values_dict_to_empty_dict(self.utils.flatten_complex_dict(slm_model))
        return slm_model

    def is_optic_slotted(self, topology: list, side):
        self.get_ports_to_check_for_optic(topology, side)

    def get_ports_to_check_for_optic(self, topology: list, side):
        """
        get ports that need to be checked for an optic
        logic looks for an AGG port first, if N/A
        then looks for a PE port
        """
        disconnect_type = "FULL"
        upstream_device = self.get_upstream_device(topology, disconnect_type)
        if not upstream_device:
            # this should never happen, but just in case
            self.logger.info(f"No {side}-side PE or AGG port found")
            return
        self.logger.info(f"Found {side}-side {upstream_device.role} Port with Optic: {upstream_device.tid},{upstream_device.handoff_port}")
        port_sfp_props = self.get_port_sfp_props(upstream_device)
        data_to_patch = {
            f"{side}_optic_slotted": self.is_port_optic_slotted(port_sfp_props, f"{upstream_device.tid} {upstream_device.handoff_port}"),
            f"{side}_target_wavelength": port_sfp_props["sfp-wavelength"] if port_sfp_props else "",
            f"{side}_sfp_vendor_name": port_sfp_props["sfp-vendor-name"] if port_sfp_props else "",
            f"{side}_sfp_part_number": port_sfp_props["sfp-vendor-part-number"] if port_sfp_props else "",
        }
        self.logger.info(f"SFP data being patched: {data_to_patch}")
        self.patch_discovered_data_to_properties(data_to_patch)

    def get_upstream_device(self, topology, disconnect_type):
        for device_role in ["AGG", "PE"]:
            for device_data in topology:
                device = Device(device_data, disconnect_type)
                if device.role == device_role:
                    return device

    def get_port_sfp_props(self, device):
        device_tid, interface = device.tid, device.handoff_port
        if device.vendor == "JUNIPER":
            port_sfp_props = self.get_port_sfp_props_juniper(device_tid, interface)
        elif device.vendor == "CISCO":
            port_sfp_props = self.get_port_sfp_props_cisco(device_tid, interface)
        return port_sfp_props

    def get_port_sfp_props_juniper(self, device_tid, interface):
        try:
            provider_resource_id = self.get_provider_resource_id(device_tid, is_hostname_tid=True)
        except NoNetworkFunction:
            self.logger.warning(f"No network function for {device_tid}")
            return None
        try:
            # fpp : fpc|pic|port-slot
            self.logger.info(f"Interface being split: {interface}")
            port_fpp = interface.split("-", 1)[1]
            self.logger.info("********** FINDING fpc-slot, pic-slot and port-slot VALUES **************** ")
            fpc_slot = port_fpp.split("/", 2)[0]
            pic_slot = port_fpp.split("/", 2)[1]
            port_slot = port_fpp.split("/", 2)[2]
        except Exception as ex:
            self.logger.exception(ex)
            return None
        try:
            port_sfp_props = self.execute_ra_command_file(
                provider_resource_id,
                "show-interface-sfp-props.json",
                parameters={"fpc-slot": fpc_slot, "pic-slot": pic_slot, "port-slot": port_slot},
                headers=None,
            )
            port_sfp_props = port_sfp_props.json()["result"]
            self.logger.info(f"SFP properties for {device_tid} & {interface}: {port_sfp_props}")
            return port_sfp_props
        except Exception:
            self.logger.info(f"Card is not slotted for CPE-facing interface {interface}")
            return None

    def get_port_sfp_props_cisco(self, device_tid, interface):
        try:
            provider_resource_id = self.get_provider_resource_id(device_tid, is_hostname_tid=True)
        except NoNetworkFunction:
            self.logger.warning(f"No network function for {device_tid}")
            return None
        try:
            port_sfp_props = self.execute_ra_command_file(
                provider_resource_id,
                "show-interface-sfp-props.json",
                parameters={"name": interface},
                headers=None,
            )
            port_sfp_props = port_sfp_props.json()["result"]
            self.logger.info(f"SFP properties for {device_tid} & {interface}: {port_sfp_props}")
            return port_sfp_props
        except Exception:
            self.logger.info(f"Card is not slotted for CPE-facing interface {interface}")
            return None

    def is_port_optic_slotted(self, port_sfp_props, device_tid_port):
        if not port_sfp_props:
            self.logger.info(f"No Optic Found for: {device_tid_port}")
            return False
        port_sfp_wavelength = port_sfp_props["sfp-wavelength"]
        self.logger.info(f"SFP PROPS: {port_sfp_props}")
        if port_sfp_wavelength == "N/A" or port_sfp_wavelength == "NA":
            return False
        else:
            return True


class NoNetworkFunction(Exception):
    pass


class Terminate(Common):
    pass
