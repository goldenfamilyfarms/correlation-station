""" -*- coding: utf-8 -*-

SLM Config Variables Plans

Versions:
   0.1 Aug 19, 2021
       Initial check in of SLM plans

"""

import json
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from time import strftime, gmtime
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.slm.slmServiceFinder import SLMServiceFinder
import re


class Activate(CommonPlan):
    DOMAIN_LEVELS = {"UNI-UNI": "3", "UNI-ENNI": "2"}
    STANDARD_REMOTE_MEP = {"reflector": "2", "probe": "1"}

    def process(self):
        self.cutthrough = RaCutThrough()
        self.properties = self.resource["properties"]
        self.circuit_id = self.properties["circuit_id"]
        self.circuit_details_id = self.properties.get("circuit_details_id")
        self.origin_cid = self.properties.get("origin_cid", "")
        self.origin_circuit_details_id = self.properties.get("origin_cd_id", "")
        self.onboarding_complete = self.properties.get("onboarding_complete", False)
        self.slm_service_finder = SLMServiceFinder(
            plan=self,
            circuit_id=self.circuit_id,
            circuit_details_id=self.circuit_details_id,
            onboarding_complete=self.onboarding_complete,
            core_only=self.properties.get("core_only", False),
            origin_cid=self.origin_cid,
            origin_circuit_details_id=self.origin_circuit_details_id,
        )
        self.circuit_details = self.slm_service_finder.circuit_details
        self.origin_circuit_details = self.slm_service_finder.origin_circuit_details
        self.is_elan = True if self.origin_cid else False
        self.customer_type = self.circuit_details["properties"]["customerType"]
        self.service_type = self.circuit_details["properties"]["serviceType"]
        self.all_slm_configurations = self.slm_service_finder.all_slm_configurations
        circuit_slm_configuration = self.slm_service_finder.determine_circuit_slm_configuration(
            self.all_slm_configurations
        )
        self.endpoint_roles = self.slm_service_finder.endpoint_roles
        self.slm_devices = self.slm_service_finder.slm_devices
        slm_configuration_variables = {}
        self.evcid = (
            self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["vrfId"] if self.is_elan else None
        )
        self.logger.info(f"SERVICE TYPE {json.dumps(self.service_type)}")
        if self.service_type == "CTBH 4G":
            self.evcid = (
                self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["evcId"]
            )
        for device in self.all_slm_configurations:
            slm_role = self.all_slm_configurations[device]["slm_role"]
            already_configured = False
            if circuit_slm_configuration.get(slm_role, {}).get("maintenance_association"):
                already_configured = True
                slm_configuration_variables = self.add_configured_details(
                    slm_configuration_variables,
                    device,
                    circuit_slm_configuration,
                    slm_role,
                )

            if not already_configured:
                if self.slm_devices[device]["onboarded"]:
                    self.logger.info(
                        "Creating SLM config variables from {}".format(self.all_slm_configurations[device])
                    )
                    slm_configuration_variables[self.slm_devices[device]["slm_role"]] = (
                        self.determine_slm_configuration_variables(device, self.all_slm_configurations[device])
                    )
                    slm_configuration_variables[self.slm_devices[device]["slm_role"]][
                        "network_function_resource_id"
                    ] = self.slm_devices[device]["network_function_resource_id"]

                else:
                    self.exit_error("Onboarding failure for device {}".format(self.all_slm_configurations[device]))
        self.bpo.resources.patch_observed(
            self.resource["id"],
            data={"properties": {"slm_configuration_variables": slm_configuration_variables}},
        )

    def add_configured_details(self, slm_configuration_variables, device, circuit_slm_configuration, slm_role):
        # universal (probe + reflector)
        slm_configuration_variables[self.slm_devices[device]["slm_role"]] = circuit_slm_configuration[slm_role]
        slm_configuration_variables[self.slm_devices[device]["slm_role"]]["existing_configuration_details"] = True
        # below will only have values populated for Juniper devices at this time
        # (see slmServiceFinder get_additional_configured_data)
        slm_configuration_variables[self.slm_devices[device]["slm_role"]]["cos"] = circuit_slm_configuration[slm_role][
            "additional_data"
        ].get("cos")
        slm_configuration_variables[self.slm_devices[device]["slm_role"]]["vlan"] = circuit_slm_configuration[slm_role][
            "additional_data"
        ].get("vlan")

        # probe specific extras, may not exist
        slm_configuration_variables[self.slm_devices[device]["slm_role"]]["performance_tier"] = (
            circuit_slm_configuration[slm_role]["additional_data"].get("performance_tier")
        )
        slm_configuration_variables[self.slm_devices[device]["slm_role"]]["cos_name"] = circuit_slm_configuration[
            slm_role
        ]["additional_data"].get("cos_name")

        return slm_configuration_variables

    def maintenance_domain(self, slm_device):
        self.logger.info("Determining correct maintenance domain")
        maintenance_domain_name = self.determine_maintenance_domain_name(self.endpoint_roles)
        self.logger.info("Maintenance domain name: {}".format(maintenance_domain_name))
        return {
            "maintenance_domain_name": maintenance_domain_name,
            "maintenance_domain_level": self.DOMAIN_LEVELS[maintenance_domain_name],
        }

    def determine_maintenance_domain_name(self, endpoint_roles):
        nni = [role for role in endpoint_roles.values() if "NNI" in role]
        return "UNI-ENNI" if nni else "UNI-UNI"

    def maintenance_association(self, slm_device, maintenance_domain_level):
        self.logger.info("Determining next available maintenance association")
        if slm_device["vendor"] == "JUNIPER":
            return (
                "-".join([self.circuit_id.split("-")[0], self.vlan()])
                if self.service_type == "CTBH 4G"
                else self.circuit_id
            )

        configured_maintenance_associations = self.separate_maintenance_association_data(
            slm_device, maintenance_domain_level
        )
        return str(self.get_last_configured_maintenance_association(configured_maintenance_associations) + 1)

    def separate_maintenance_association_data(self, slm_configurations, maintenance_domain_level):
        self.logger.info("Parsing: {}".format(slm_configurations))
        try:
            sorted_maintenance_associations = sorted(
                [
                    maintenance_association["id"]
                    for maintenance_association in slm_configurations["maintenance_associations"]
                    if slm_configurations["maintenance_domain_id"] == maintenance_domain_level
                ]
            )
        except KeyError:
            sorted_maintenance_associations = sorted(
                [
                    maintenance_association["id"].split("-")[-1]
                    for config in slm_configurations["cfm_configured"]
                    for maintenance_association in config["maintenance_associations"]
                    if config["maintenance_domain_id"].split("-")[-1] == maintenance_domain_level
                ]
            )
        if slm_configurations["vendor"] == "ADVA":
            sorted_maintenance_associations = (
                sorted(
                    [
                        maintenance_association["id"].split("-")[-1]
                        for maintenance_association in slm_configurations["maintenance_associations"]
                        if slm_configurations["maintenance_domain_id"].split("-")[-1] == maintenance_domain_level
                    ]
                )
                if not IndexError
                else sorted_maintenance_associations
            )
        return sorted_maintenance_associations

    def get_last_configured_maintenance_association(self, maintenance_associations):
        return 0 if len(maintenance_associations) == 0 else int(maintenance_associations[-1])

    def vlan(self, slm_role=""):
        service_data = self.get_service_data(self.slm_service_finder.circuit_details)
        if self.is_elan:
            if not slm_role:
                return "Device SLM role must be provided to determine correct VLAN"
            if slm_role == "probe":
                return service_data["evc"][0]["sVlan"]
            else:
                return self.origin_circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"]
        else:
            return service_data["evc"][0]["sVlan"]

    def macomp(self, slm_device, handoff_port):
        if slm_device["connection_type"] == "netconf":
            model = slm_device["device_model_type"][2:]  # slice off the xg from netconf models
            flowpoint = self.cutthrough.execute_ra_command_file(
                slm_device["device_prid"],
                f'ge/{model}/netconf-get-slm-flowpoint.json',
                {"handoff_port": handoff_port},
                headers=None,
            ).json()["result"]["data"]["sub-network"]["network-element"]["shelf"]["slot"]["card"]["ethernet-card"][
                "ethernet-port"]["flowpoint"]
            return self.get_magic_adva_component_id(self.get_flowpoint_id(flowpoint))
        else:
            return "1"

    def get_flowpoint_id(self, flowpoint):
        if isinstance(flowpoint, list):
            for flow_id in flowpoint:
                if self.circuit_id in flow_id['alias']:
                    return flow_id['flowpoint-id']
        else:
            return flowpoint["flowpoint-id"]

    def get_magic_adva_component_id(self, flowpoint_id):
        # netconf adva component id = flowpoint id + magic number
        return str(int(flowpoint_id) + 100945920)

    def normalize_port_data(self, port, vendor):
        return port.lower() if vendor == "JUNIPER" else port.split("-")[-1]

    def normalize_adva_model(self, device_model_type: str) -> str:
        """Modifies Adva device model to device command expectation.

        Parameters
        ----------
            device_model_type: str (lower)

        """
        return device_model_type.replace("ge", "")

    def get_existing_probe_list(self, existing_device_probes_found: str) -> list:
        """
        parses the return result values of the show_slm_probe_list.json ra command and returns
            a list of all the esa_probe-1-1-1-X coordinates of each probe found.

        Parameters
        ----------
        existing_device_probes_found : str
            is the result value from the racutthrough command show_slm_probe_list.json

        logic
        -----
        searches for a esa_probe pattern then strips off the last
            digit and adds it to a list. example return ['1', '2'].
        """

        pattern = re.compile(r"esa_probe-1-1-1-(\d+)")
        matches = pattern.findall(existing_device_probes_found)
        if len(matches) < 1:
            pattern = re.compile(r"esa_schedule-1-1-1-(\d+)")
            matches = pattern.findall(existing_device_probes_found)

        return matches

    def get_existing_netconf_probe_list(self, data: str) -> list:
        """
        parses the return result values of the netconf_how_slm_probe_list.json ra command and returns
            a list of all the esa-probe-entry coordinates of each probe found.

        Parameters
        ----------
        existing_device_probes_found : str
            is the result value from the racutthrough command netconf_show_slm_probe_list.json

        """
        self.logger.info("DATA::: {}".format(data))
        probe_path = (
            data.get("data", dict())
            .get("sub-network", dict())
            .get("network-element", dict())
            .get("shelf", dict())
            .get("slot", dict())
            .get("card", dict())
            .get("ethernet-card", dict())
            .get("esa-probe", False)
        )
        probe_list = []
        if isinstance(data, dict):
            if probe_path and probe_path.get("esa-probe-entry"):
                if isinstance(probe_path.get("esa-probe-entry"), list):
                    for probe_item in probe_path.get("esa-probe-entry"):
                        probe_list.append(probe_item["probe-id"])
                    return probe_list
                elif probe_path.get("esa-probe-entry", dict()).get("probe-id"):
                    probe_list.append(probe_path.get("esa-probe-entry", dict()).get("probe-id"))
                    return probe_list
            return probe_list

    def esa_probe_select(self, existing_probe_list: list, port: str) -> str:
        """
        To determine the next available esa_probe-1-1-1-X and esa_schedule-1-1-1-X
             based on port value or next available if port number not available to use

         Parameters
         ----------
         existing_probe_list : list
             a list of probes found on the device. example ["1", "2"]

         port : str
              customer handoff on the device

         logic
         -----
         By default the esa_probe_number will be equal to port. If port number not in list
         then esa_probe will equal the lowest available number to assign
         to esa_probe / esa_schedule.
        """

        if len(existing_probe_list) < 1:
            esa_probe_number = port
        else:
            # svi maximum potential range for esa_prob port number int converted to str
            svi_probe_max_range_list = [str(x) for x in list(range(1, 71))]
            # the probe_numbers_availabe = svi_probe_max_range_list minus what was found on the device
            probe_numbers_availabe = [i for i in svi_probe_max_range_list if i not in existing_probe_list]
            esa_probe_number = port
            if port not in probe_numbers_availabe:
                esa_probe_number = int(probe_numbers_availabe[0])

        return esa_probe_number

    def determine_probe_number(self, device: str, slm_configurations: dict) -> str:
        """
        Checks device and determines the slm probe number.

        Parameters
        ----------
        slm_configurations: dict
            self.all_slm_configurations[device]

        device: str
            this is the device tid
        """
        self.logger.info("DEVICE:::: {}".format(slm_configurations))
        if (slm_configurations["connection_type"]) == "netconf":
            existing_netconf_device_probes_found = self.cutthrough.execute_ra_command_file(
                slm_configurations["device_prid"],
                "netconf_show_slm_probe_list.json",
                headers=None,
            ).json()["result"]
            existing_probe_list = self.get_existing_netconf_probe_list(existing_netconf_device_probes_found)
        else:
            existing_device_probes_found = self.cutthrough.execute_ra_command_file(
                slm_configurations["device_prid"],
                "show_slm_probe_list.json",
                {"device_model_type": slm_configurations["device_model_type"]},
                headers=None,
            ).json()["result"]
            self.logger.info("existing_device_probes: {}".format(existing_device_probes_found))
            existing_probe_list = self.get_existing_probe_list(existing_device_probes_found)
        self.logger.info("existing_probe_list: {}".format(existing_probe_list))

        probe_number = self.esa_probe_select(
            existing_probe_list,
            self.slm_devices[device]["port"][-1],
        )
        return probe_number

    def determine_mep(self, slm_configurations):
        if self.is_elan:
            if slm_configurations["slm_role"] == "probe":
                return self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["elanSlm"][0][
                    "sourceMepId"
                ].split("::")[-1]
            else:
                return 10
        else:
            return self.slm_service_finder.STANDARD_MEP[slm_configurations["slm_role"]]

    def determine_remote_mep(self, slm_configurations):
        if self.is_elan:
            if slm_configurations["slm_role"] == "probe":
                return 10
            else:
                return None
        else:
            return self.slm_service_finder.STANDARD_MEP[slm_configurations["slm_role"]]

    def get_elan_mep_list(self, slm_configurations):
        leg_mep = int(
            self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["elanSlm"][0]["sourceMepId"].split("::")[
                -1
            ]
        )
        if slm_configurations["vendor"] == "ADVA":
            mep_list = [num for num in range(10, leg_mep + 6)]
            return ",".join((map(str, mep_list)))
        elif slm_configurations["vendor"] == "RAD":
            return [num for num in range(11, leg_mep + 6)]

    def determine_slm_configuration_variables(self, device, slm_configurations):
        self.logger.info("Determining SLM configuration variables for device: {}".format(device))
        maintenance_domain_variables = self.maintenance_domain(self.slm_devices[device])
        service_data = self.get_service_data(self.circuit_details)
        if self.is_elan and slm_configurations["slm_role"] == "reflector":
            circuit_id = self.origin_cid
            self.meps = self.get_elan_mep_list(slm_configurations)
        else:
            self.meps = None
            circuit_id = self.circuit_id
        slm_configuration_variables = {
            "circuit_id": circuit_id,
            "is_elan": self.is_elan,
            "is_reflector": True if slm_configurations["slm_role"] == "reflector" else False,
            "tid": device,
            "maintenance_domain_level": maintenance_domain_variables["maintenance_domain_level"],
            "maintenance_domain_name": maintenance_domain_variables["maintenance_domain_name"],
            "maintenance_association": self.maintenance_association(
                slm_configurations,
                maintenance_domain_variables["maintenance_domain_level"],
            ),
            "mep": self.determine_mep(slm_configurations),
            "evcid": self.evcid,
            "mep_list": self.meps if self.meps else False,
            "remote_mep": self.determine_remote_mep(slm_configurations),
            "cos": self.determine_pbit(service_data),
            "cos_name": self.get_cos_name(service_data),
            "performance_tier": self.performance_tier(service_data),
            "handoff_port": self.normalize_port_data(
                self.slm_devices[device]["port"], self.slm_devices[device]["vendor"]
            ),
            "vlan": self.vlan(slm_configurations["slm_role"]),
            "vendor": self.slm_devices[device]["vendor"],
        }

        if slm_configurations["vendor"] == "ADVA":
            slm_configuration_variables = self.add_adva_specific_variables(
                slm_configurations, device, slm_configuration_variables
            )
        if slm_configurations["vendor"] == "RAD":
            slm_configuration_variables = self.add_rad_specific_variables(
                maintenance_domain_variables, slm_configuration_variables
            )
        self.logger.info("slm_configuration_variables: {}".format(slm_configuration_variables))
        return slm_configuration_variables

    def get_cos_name(self, service_data):
        default_standard = "GOLD" if self.customer_type == "CARR" else "SILVER"
        return service_data["evc"][0].get("cosNames", [{}])[0].get("name", default_standard).lower()

    def performance_tier(self, service_data):
        return service_data["evc"][0].get("perfTier", [{}])[0].get("name", "METRO").lower()

    def add_adva_specific_variables(self, slm_configurations, device, slm_configuration_variables):
        slm_configurations["device_model_type"] = self.normalize_adva_model(slm_configurations["device_model_type"])
        if slm_configurations["slm_role"] == "probe":
            slm_configuration_variables["probe_number"] = self.determine_probe_number(device, slm_configurations)
        slm_configuration_variables["time"] = strftime("%Y-%m-%dT%H:%M:%S+00:00", gmtime())
        slm_configuration_variables["macomp"] = self.macomp(
            slm_configurations, slm_configuration_variables["handoff_port"]
        )
        slm_configuration_variables["device_model_type"] = slm_configurations["device_model_type"]
        return slm_configuration_variables

    def add_rad_specific_variables(self, maintenance_domain_variables, slm_configuration_variables):
        slm_configuration_variables["client_md_level"] = str(
            int(maintenance_domain_variables["maintenance_domain_level"]) + 1
        )
        return slm_configuration_variables


class Terminate(CommonPlan):
    def process(self):
        pass
