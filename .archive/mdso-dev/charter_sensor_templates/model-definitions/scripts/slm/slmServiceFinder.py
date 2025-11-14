""" -*- coding: utf-8 -*-

SLM Service Finder Plans

Versions:
   0.1 Aug 19, 2021
       Initial check in of SLM plans

"""
import json
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.circuitDetailsHandler import CircuitDetailsHandler


class SLMServiceFinder(object):
    STANDARD_MEP = {"reflector": "1", "probe": "2"}

    def __init__(
        self,
        plan,
        circuit_id,
        circuit_details_id=None,
        origin_cid=None,
        origin_circuit_details_id=None,
        onboarding_complete=False,
        core_only=False,
    ):
        self.plan = plan
        self.circuit_id = circuit_id
        self.circuit_details_id = circuit_details_id
        self.core_only = core_only
        self.origin_cid = origin_cid
        self.origin_circuit_details_id = origin_circuit_details_id
        self.origin_circuit_details = None
        self.cutthrough = RaCutThrough()
        self.is_elan = True if self.origin_cid else False
        self.is_elan_origin_circuit = self.circuit_id == self.origin_cid  # only relevant for ELAN

        # if we already have circuit details resource id, get circuit details from it
        if self.circuit_details_id:
            self.circuit_details = self.bpo.resources.get(self.circuit_details_id)
        # if we don't already have circuit details resource id or if we need to onboard additional devices into circuit details
        # we need to generate our own circuit details
        elif not self.circuit_details_id or not onboarding_complete:
            self.circuit_details = self.create_circuit_details_resource(circuit_id=self.circuit_id)
        # if elan, we need to generate our own ORIGIN circuit details if we don't already have them
        # or if we need to onboard additional devices into ORIGIN circuit details
        if self.is_elan:
            if not self.origin_circuit_details_id or not onboarding_complete:
                self.origin_circuit_details = self.create_circuit_details_resource(circuit_id=self.origin_cid)
            else:
                self.origin_circuit_details = self.bpo.resources.get(self.origin_circuit_details_id)

        # determine reflector and probe device TIDs and ports
        topology_indexes = self.determine_slm_role_topology_index()
        reflector = self.determine_slm_device_details(topology_indexes["reflector"], "reflector")
        probe = self.determine_slm_device_details(topology_indexes["probe"], "probe")
        self.logger.info("Reflector: {}\nProbe: {}".format(reflector, probe))
        self.endpoint_roles = self.determine_endpoint_roles([reflector["uuid"], probe.get("uuid", "")])
        if self.is_elan_origin_circuit:
            # the first ELAN circuit will only have a reflector; probes come later with additional legs
            self.slm_devices = {reflector["tid"]: reflector}
        else:
            self.slm_devices = {reflector["tid"]: reflector, probe["tid"]: probe}
        self.logger.info(f"SLM devices: {json.dumps(self.slm_devices)}")
        self.all_slm_configurations = self.get_all_slm_configurations(self.slm_devices)

    def create_circuit_details_resource(self, circuit_id):
        handler = CircuitDetailsHandler(plan=self, circuit_id=circuit_id, operation="SLM")
        handler.device_onboarding_process()
        return handler.circuit_details

    def device_count_per_side(self, topology_index):
        device_count = 0
        for _ in self.circuit_details["properties"]["topology"][topology_index]["data"]["node"]:
            device_count += 1
        return device_count

    def determine_slm_role_topology_index(self):
        """
        determine which side is reflector and which is probe on based on device count
        if z side only has 1 device: A side CPE/probe, Z side MX/reflector
        if both a and z sides only have 1 device: A side MX/reflector, Z side MX/probe
        otherwise: A side CPE/reflector, Z side CPE/probe
        """
        if self.is_elan:
            return {"probe": 0, "reflector": 0}

        a_side_device_count = self.device_count_per_side(0)
        z_side_device_count = self.device_count_per_side(1)
        self.logger.info("A side count: {}".format(a_side_device_count))
        self.logger.info("Z side count: {}".format(z_side_device_count))
        if z_side_device_count == 1 and a_side_device_count > 1:
            reflector = 1
            probe = 0
        else:
            reflector = 0
            probe = 1
        return {"probe": probe, "reflector": reflector}

    def determine_slm_device_details(self, topology_index, slm_role):
        self.logger.info("Determining SLM device details for {} device".format(slm_role))
        slm_device = {}
        if self.is_elan_origin_circuit and slm_role == "probe":
            # ELAN origin circuit will not contain probe, no details to populate
            return slm_device
        if self.is_elan and slm_role == "reflector":
            topology = self.origin_circuit_details
        else:
            topology = self.circuit_details

        target_tid = topology["properties"]["service"][0]["data"]["evc"][0]["endPoints"][topology_index]["uniId"].split("-")[0]

        for device in topology["properties"]["topology"][topology_index]["data"]["node"]:
            device_data = device["name"]
            device_info = {detail["name"]: detail["value"] for detail in device_data}
            if device_info["Host Name"] == target_tid:
                slm_device = self.add_slm_device_details(device_info)
                slm_device["onboarded"] = (
                    False
                    if slm_device.get("network_function_resource_id") is None
                    else self.determine_onboard_status(
                        self.bpo.resources.get(slm_device["network_function_resource_id"])["orchState"]
                    )
                )
                slm_device["slm_role"] = slm_role
                return slm_device
        return slm_device

    def add_slm_device_details(self, device_info):
        return {
            "tid": device_info["Host Name"],
            "port": device_info["Client Interface"],
            "uuid": "{}-{}".format(
                device_info["Host Name"],
                device_info["Client Interface"],
            ),
            "model": device_info["Model"],
            "mgmt_ip": device_info["Management IP"],
            "fqdn": device_info["FQDN"],
            "role": device_info["Role"],
            "vendor": device_info["Vendor"],
            "network_function_resource_id": self.get_network_function_resource_id(device_info),
        }

    def get_network_function_resource_id(self, device_info):
        network_function = self.get_network_function_by_host_or_ip(device_info["FQDN"], device_info["Management IP"])
        return None if not network_function else network_function["id"]

    def determine_endpoint_roles(self, endpoint_ports):
        self.logger.info("endpoint ports: {}".format(endpoint_ports))
        endpoint_roles = {edgenode: "UNI-UNI" for edgenode in endpoint_ports}
        self.logger.info("endpoint roles from granite: {}".format(str(endpoint_roles)))
        return endpoint_roles

    def maintenance_association_command_required(self, vendor, connection_type):
        maintenance_association_vendors = ["RAD", "ADVA"]
        return True if vendor in maintenance_association_vendors and connection_type == "cli" else False

    def parse_for_maintenance_domain(self, command_output, vendor, connection_type):
        maintenance_domain_parser_by_vendor = {
            "JUNIPER": self.juniper_maintenance_domains,
            "RAD": self.rad_maintenance_domains,
            "ADVA": self.adva_maintenance_domains,
            "NOKIA": self.nokia_maintenance_domains,
        }
        cfm_config_data = command_output.json()["result"]
        return maintenance_domain_parser_by_vendor[vendor](cfm_config_data, connection_type)

    def juniper_maintenance_domains(self, cfm_config_data, connection_type=None):
        maintenance_domain_list = []
        if isinstance(cfm_config_data, list):
            for maintenance_domain in cfm_config_data:
                if maintenance_domain.get("level") is None:
                    return maintenance_domain_list
                maintenance_domain_list.append(self._create_juniper_maintenance_domain_dict(maintenance_domain))
        else:
            if cfm_config_data.get("level") is None:
                return maintenance_domain_list
            maintenance_domain_list.append(self._create_juniper_maintenance_domain_dict(cfm_config_data))
        return maintenance_domain_list

    def _create_juniper_maintenance_domain_dict(self, iterable_config_data):
        return {
            "name": iterable_config_data["name"],
            "level": iterable_config_data["level"],
            "maintenance_associations": iterable_config_data.get("maintenance-association", []),
        }

    def rad_maintenance_domains(self, cfm_config_data, connection_type=None):
        maintenance_domain_list = []
        for maintenance_domain in cfm_config_data:
            if maintenance_domain["properties"].get("md-level") is None:
                return maintenance_domain_list
            maintenance_domains = {
                "maintenance_associations": [],
                "name": maintenance_domain["properties"]["name"],
                "level": maintenance_domain["properties"]["md-level"],
                "maintenance_domain_id": maintenance_domain["properties"]["md-id"],
            }
            maintenance_domain_list.append(maintenance_domains)
        return maintenance_domain_list

    def adva_maintenance_domains(self, cfm_config_data, connection_type):
        # netconf data shape
        if connection_type == "netconf":
            if cfm_config_data["data"].get("maintenance-domain") is None:
                return []
            maintenance_domain_data = cfm_config_data["data"]["maintenance-domain"]
            if isinstance(cfm_config_data["data"]["maintenance-domain"], dict):
                maintenance_domain_data = [maintenance_domain_data]
        # cli data shape
        if connection_type == "cli":
            maintenance_domain_data = cfm_config_data["output"]
        return self.normalize_adva_maintenance_domains(maintenance_domain_data, connection_type)

    def normalize_adva_maintenance_domains(self, maintenance_domain_data, connection_type):
        maintenance_domain_list = []
        if not maintenance_domain_data:
            return maintenance_domain_list
        device_response = {
            "cli": {
                "name": "mdName",
                "level": "mdLevel",
                "maintenance_domain_id": "mdId",
            },
            "netconf": {
                "name": "name",
                "level": "md-level",
                "maintenance_domain_id": "id",
            },
        }
        for maintenance_domain in maintenance_domain_data:
            if connection_type == "cli" and maintenance_domain.get("mdLevel") is None:
                return maintenance_domain_list
            maintenance_domains = {
                "name": maintenance_domain[device_response[connection_type]["name"]],
                "level": maintenance_domain[device_response[connection_type]["level"]],
                "maintenance_domain_id": maintenance_domain[device_response[connection_type]["maintenance_domain_id"]],
                "maintenance_associations": []
                if connection_type == "cli"
                else self.normalize_adva_netconf_maintenance_associations(
                    maintenance_domain.get("maintenance-association")
                ),
            }
            maintenance_domain_list.append(maintenance_domains)
        return maintenance_domain_list

    def normalize_adva_netconf_maintenance_associations(self, maintenance_association_data):
        normalized_maintenance_associations = []
        if maintenance_association_data:
            if isinstance(maintenance_association_data, dict):
                maintenance_association_data = [maintenance_association_data]
            for maintenance_association in maintenance_association_data:
                normalized_maintenance_associations.append(maintenance_association)
        return normalized_maintenance_associations

    def get_maintenance_association_info(self, maintenance_association_return, maintenance_domains, vendor):
        maintenance_association_data = {
            "RAD": self.rad_maintenance_associations,
            "ADVA": self.adva_maintenance_associations,
        }
        return maintenance_association_data[vendor](maintenance_association_return, maintenance_domains)

    def adva_maintenance_associations(self, maintenance_association_return, maintenance_domains):
        maintenance_association_return = maintenance_association_return.json()["result"]
        self.logger.info("adva maintenance association command return: {}".format(maintenance_association_return))
        for maintenance_domain in maintenance_domains:
            for maintenance_association in maintenance_association_return:
                maintenance_association_zip = zip(
                    maintenance_association["manetId"], maintenance_association["manetName"]
                )
                for maintenance_association_data in maintenance_association_zip:
                    if (
                        maintenance_domain["maintenance_domain_id"].split("-")[1]
                        == maintenance_association_data[0].split("-")[1]
                    ):
                        maintenance_domain["maintenance_associations"].append(
                            {"id": maintenance_association_data[0], "name": maintenance_association_data[1]}
                        )
        return maintenance_domains

    def rad_maintenance_associations(self, maintenance_association_return, maintenance_domains):
        maintenance_association_return = maintenance_association_return.json()["result"]
        self.logger.info("rad maintenance association command return: {}".format(maintenance_association_return))
        for maintenance_domain in maintenance_domains:
            for maintenance_association in maintenance_association_return:
                if maintenance_association["properties"]["md-id"] == maintenance_domain["maintenance_domain_id"]:
                    maintenance_domain["maintenance_associations"].append(
                        {
                            "id": maintenance_association["properties"]["ma-id"],
                            "name": maintenance_association["properties"]["name"],
                        }
                    )
        return maintenance_domains

    def nokia_maintenance_domains(self, cfm_config_data, connection_type=None):
        self.logger.info(f"NOKIA MD LIST:: {json.dumps(cfm_config_data)}")
        maintenance_domain_list = []
        for maintenance_domain in cfm_config_data:
            if maintenance_domain.get("Level") is None:
                return maintenance_domain_list
            maintenance_domains = {
                "maintenance_associations": [],
                "name": maintenance_domain["Name"],
                "level": maintenance_domain["Level"],
                "maintenance_domain_id": maintenance_domain["Md-index"],
            }
            maintenance_domain_list.append(maintenance_domains)
        self.logger.info(f"MD LIST:: {json.dumps(maintenance_domain_list)}")
        return maintenance_domain_list

    def get_all_slm_configurations(self, slm_devices):
        all_slm_configurations = {}
        for device in slm_devices:
            self.logger.info("SLM Device: {}".format(device))
            if self.skip_device_requested(slm_devices[device]["role"]):
                continue
            if slm_devices[device]["onboarded"] is False:
                self.exit_error(
                    "Unable to retreive configuration data. Device not onboarded in MDSO {}".format(slm_devices[device])
                )
            network_function = (
                self.bpo.resources.get(slm_devices[device]["network_function_resource_id"])
                if slm_devices[device]["network_function_resource_id"] is not None
                else self.get_network_function_by_host_or_ip(
                    slm_devices[device]["fqdn"], slm_devices[device]["mgmt_ip"]
                )
            )
            device_prid = network_function["providerResourceId"]
            device_model_type = network_function["properties"]["resourceType"].lower()
            # issue racutthrough to get CFM configuration
            vendor = slm_devices[device]["vendor"]
            connection_type = self.get_network_function_connection_type(network_function)
            cfm_command = (
                "get-cfm-configuration.json"
                if connection_type == "cli" or vendor == "JUNIPER"
                else "get-cfm-configuration-netconf.json"
            )
            cfm_config_data = self.cutthrough.execute_ra_command_file(device_prid, cfm_command)
            maintenance_domains = self.parse_for_maintenance_domain(cfm_config_data, vendor, connection_type)
            if not maintenance_domains:
                all_slm_configurations[device] = {
                    "cfm_configured": False,
                    "slm_role": slm_devices[device]["slm_role"],
                    "vendor": vendor,
                    "maintenance_associations": [],
                    "device_prid": device_prid,
                    "connection_type": connection_type,
                    "device_model_type": device_model_type,
                }
            if maintenance_domains:
                if self.maintenance_association_command_required(vendor, connection_type):
                    maintenance_association_return = self.cutthrough.execute_ra_command_file(
                        device_prid, "list-oam-mas.json"
                    )
                    maintenance_domains = self.get_maintenance_association_info(
                        maintenance_association_return, maintenance_domains, vendor
                    )
                all_slm_configurations[device] = {
                    "cfm_configured": maintenance_domains,
                    "slm_role": slm_devices[device]["slm_role"],
                    "vendor": vendor,
                    "device_prid": device_prid,
                    "connection_type": connection_type,
                    "device_model_type": device_model_type,
                }
        return all_slm_configurations

    def skip_device_requested(self, device_role):
        return self.core_only and device_role != "PE"

    def get_maintenance_domain_name(self, slm_config, vendor):
        return slm_config["name"] if vendor == "JUNIPER" else slm_config["maintenance_domain_id"].split("-")[-1]

    def get_maintenance_association_id(self, maintenance_association, vendor):
        return maintenance_association["name"] if vendor == "JUNIPER" else maintenance_association["id"].split("-")[-1]

    def get_mep(self, maintenance_association, vendor, slm_role):
        if self.is_elan:
            if slm_role.lower() == "probe":
                return self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["elanSlm"][0][
                    "sourceMepId"
                ].split("::")[-1]
            else:
                return 10
        else:
            return maintenance_association["mep"]["name"] if vendor == "JUNIPER" else self.STANDARD_MEP[slm_role]

    def determine_circuit_slm_configuration(self, all_slm_configurations):
        if self.is_elan:
            ma_match = "VPLS" + self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["vrfId"]
        else:
            ma_match = self.circuit_id
        circuit_slm_configuration = {}
        for slm_device in all_slm_configurations:
            maintenance_association_match = {}
            slm_service_configured = False
            slm_role = all_slm_configurations[slm_device]["slm_role"]
            vendor = all_slm_configurations[slm_device]["vendor"]
            if all_slm_configurations[slm_device]["cfm_configured"]:
                for slm_config in all_slm_configurations[slm_device]["cfm_configured"]:
                    if not self.is_empty(slm_config["maintenance_associations"]):
                        self.logger.info(f"Evaluating SLM Config for Device {slm_device}: {slm_config}")
                        if isinstance(slm_config["maintenance_associations"], list):
                            for maintenance_association in slm_config["maintenance_associations"]:
                                if maintenance_association.get("name") == ma_match:
                                    slm_service_configured = True
                                    maintenance_association_match = maintenance_association
                                    break
                        else:
                            if slm_config["maintenance_associations"].get("name") == ma_match:
                                slm_service_configured = True
                                maintenance_association_match = slm_config["maintenance_associations"]
                        if slm_service_configured:
                            circuit_slm_configuration[slm_role] = self.build_circuit_slm_configuration_data(
                                self.slm_devices[slm_device],
                                self.get_maintenance_domain_name(slm_config, vendor),
                                self.get_maintenance_association_id(maintenance_association_match, vendor),
                                self.get_mep(maintenance_association_match, vendor, slm_role),
                                self.get_additional_configured_data(
                                    slm_config, maintenance_association_match, vendor, slm_role
                                ),
                            )
                            break
            if not slm_service_configured:
                circuit_slm_configuration[slm_role] = self.build_circuit_slm_configuration_data(
                    self.slm_devices[slm_device], None, None, None, self.add_empty_configurations(vendor, slm_role)
                )

        self.logger.info("Circuit SLM configuration: {}".format(circuit_slm_configuration))
        return circuit_slm_configuration

    def get_additional_configured_data(self, slm_config, maintenance_association, vendor, slm_role):
        configured_data_by_vendor = {
            "JUNIPER": self.juniper_configured_data,
            "RAD": self.rad_configured_data,
            "ADVA": self.adva_configured_data,
            "NOKIA": self.nokia_configured_data,
        }
        return configured_data_by_vendor[vendor](slm_config, maintenance_association, slm_role)

    def juniper_configured_data(self, slm_config, maintenance_association, slm_role):
        configured_data = {
            "vlan": maintenance_association["primary-vid"],
            "cos": maintenance_association["mep"]["priority"],
            "maintenance_domain_level": slm_config["level"],
            "continuity_check": {
                "interval": maintenance_association["continuity-check"].get("interval"),
                "interface_status_tlv": maintenance_association["continuity-check"].get("interface-status-tlv"),
            },
            "mep_direction": maintenance_association["mep"].get("direction"),
            "mep_discovery": maintenance_association["mep"].get("auto-discovery"),
            "mep_lowest_priority_defect": maintenance_association["mep"].get("lowest-priority-defect"),
        }
        if slm_role == "probe":
            remote_mep = maintenance_association["mep"].get("remote-mep")
            configured_data["remote_mep"] = remote_mep["name"]
            configured_data["sla_iterator_profile_slm"] = self.get_sla_iterator_profile(remote_mep, "slm")
            configured_data["sla_iterator_profile_delay"] = self.get_sla_iterator_profile(remote_mep, "delay")
            configured_data["cos_name"] = self.get_data_from_sla_iterator_profiles(
                configured_data["sla_iterator_profile_slm"], configured_data["sla_iterator_profile_delay"], "cos_name"
            )
            configured_data["performance_tier"] = self.get_data_from_sla_iterator_profiles(
                configured_data["sla_iterator_profile_slm"],
                configured_data["sla_iterator_profile_delay"],
                "performance_tier",
            )
            configured_data["continuity_check"]["hold_interval"] = maintenance_association["continuity-check"].get(
                "hold-interval"
            )

        return configured_data

    def get_sla_iterator_profile(self, remote_mep, profile_name):
        sla_iterator_profiles = remote_mep.get("sla-iterator-profile")
        if not sla_iterator_profiles:
            return None
        for profile in sla_iterator_profiles:
            if profile_name in profile["name"]:
                return profile["name"]

    def get_data_from_sla_iterator_profiles(self, slm_profile, delay_profile, requested_data):
        data_indexes = {
            "performance_tier": -1,
            "cos_name": -2,
        }
        data_index = data_indexes[requested_data]

        if slm_profile:
            return slm_profile.split("-")[data_index]
        if delay_profile:
            return delay_profile.split("-")[data_index]
        return

    def rad_configured_data(self, slm_config, maintenance_association, slm_role):
        return {}

    def adva_configured_data(self, slm_config, maintenance_association, slm_role):
        return {}

    def nokia_configured_data(self, slm_config, maintenance_association, slm_role):
        return {}

    def add_empty_configurations(self, vendor, slm_role):
        empty_data = {
            "vlan": None,
            "cos": None,
            "maintenance_domain_level": None,
        }
        data_by_vendor = {
            "JUNIPER": self.juniper_empty_data,
            "RAD": self.rad_empty_data,
            "ADVA": self.adva_empty_data,
            "NOKIA": self.nokia_empty_data,
        }
        return data_by_vendor[vendor](empty_data, slm_role)

    def juniper_empty_data(self, empty_data, slm_role):
        empty_data["continuity_check"] = {"interval": None, "interface_status_tlv": None}
        empty_data["mep_lowest_priority_defect"] = None
        empty_data["mep_direction"] = None
        empty_data["mep_discovery"] = None

        if slm_role == "probe":
            empty_data["remote_mep"] = None
            empty_data["sla_iterator_profile_slm"] = None
            empty_data["sla_iterator_profile_delay"] = None
            empty_data["cos_name"] = None
            empty_data["performance_tier"] = None
            empty_data["continuity_check"]["hold_interval"] = None

        return empty_data

    def rad_empty_data(self, empty_data, slm_role):
        return empty_data

    def adva_empty_data(self, empty_data, slm_role):
        return empty_data

    def nokia_empty_data(self, empty_data, slm_role):
        return empty_data

    def build_circuit_slm_configuration_data(
        self, device_details, maintenance_domain, maintenance_association, mep, additional_data
    ):
        return {
            "device_details": device_details,
            "maintenance_domain": maintenance_domain,
            "maintenance_association": maintenance_association,
            "mep": mep,
            "vendor": device_details["vendor"],
            "additional_data": additional_data,
        }

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class Activate(CommonPlan):
    def process(self):
        slm_service_finder = SLMServiceFinder(
            plan=self,
            circuit_id=self.properties["circuit_id"],
            circuit_details_id=self.properties.get("circuit_details_id"),
            origin_cid=self.properties.get("origin_cid"),
            origin_circuit_details_id=self.properties.get("origin_cd_id"),
            onboarding_complete=self.properties.get("onboarding_complete", False),
            core_only=self.properties.get("core_only", False),
        )
        all_slm_configurations = slm_service_finder.all_slm_configurations
        self.bpo.resources.patch_observed(
            self.resource["id"],
            data={
                "properties": {
                    "slm_configuration": slm_service_finder.determine_circuit_slm_configuration(all_slm_configurations)
                }
            },
        )


class Terminate(CommonPlan):
    def process(self):
        pass
