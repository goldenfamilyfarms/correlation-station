import ipaddress

from copy import deepcopy

from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.configmodeler.utils import NetworkCheckUtils
from scripts.serviceMapper.common import Common, Device


ADVA_PROS_LIST = ["FSP 150-XG116PRO", "FSP 150-XG116PROH", "FSP 150-XG118PRO", "FSP 150-XG120PRO"]
MANAGEMENT_IP = "Management IP"


class Activate(Common):
    UPDATE_TYPES = {
        "bandwidth_update": [
            "committedInformationRate",
            "policerName",
            "epAccessA2NFlowCir",
            "epAccessA2NFlowEir",
            "eir",
            "cir",
            "bandwidth",
            "servicePolicyInput",
            "policer_name",
        ],
        "description_update": ["serviceName", "userLabel", "portDescription", "serviceDescription", "name"],
        "pbit_update": ["egressCosPbit", "epAccessFlowCVlanTag", "c_tag_pbit"],
    }

    def process(self):
        self.initialize()

        topology_devices = [node for node in self.circuit_details["properties"]["topology"][0]["data"]["node"]]
        if self.service_type in ["ELINE", "CTBH 4G"]:
            topology_devices.extend(node for node in self.circuit_details["properties"]["topology"][1]["data"]["node"])

        for device_data in topology_devices:
            skip_rem = False
            device = Device(device_data)

            self.get_service_differences(device, adva_pro=device.adva_pro)

            skip_rem = self.validate_network_data(device)

            if self.remediation_flag and not skip_rem:
                self.remediate_network(device)
            else:
                self.patch_resource_with_diffs(device, False)

        if self.slm_eligible:
            skip_msg = None
            if self.slm_eligible:
                skip_msg = self.slm_configuration_process()
            if not skip_msg:
                self.slm_verification_process()

    def initialize(self):
        self.utils = NetworkCheckUtils()
        self.resource_id = self.resource["id"]
        properties = self.resource["properties"]
        self.circuit_id = properties["circuit_id"]
        self.device_properties = properties.get("device_properties", {})
        self.order_type = properties.get("order_type", "")
        self.slm_eligible = properties.get("slm_eligible", False)
        self.bpo.resources.patch_observed(self.resource_id, data={"properties": {"slm_eligible": self.slm_eligible}})
        self.remediation_flag = properties["remediation_flag"]
        self.cutthrough = RaCutThrough()
        self.circuit_details_id = self.properties["circuit_details_id"]
        self.circuit_details = self.bpo.resources.get(self.circuit_details_id)
        self.update_circuit_details()  # update cpe mgmt IPs, validate devices, onboard devices
        self.bw = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evc-ingress-bwp", None)
        self.logger.info(f"self.bw: {self.bw}")
        self.service_type = self.circuit_details["properties"]["serviceType"].upper()
        if self.service_type == "ELAN":
            self.determine_origin_site()

    def update_circuit_details(self):
        # update circuit details with CPE mgmt IPs if they are provided
        if self.management_ips_provided():
            self.circuit_details = self.update_circuit_details_with_device_mgmt_ip()
        # circuit details handler will handle onboarding details now
        # detail 1 - create service device validator to check connectivity
        # detail 2 - create service device onboarder to onboard any devices not in bpo
        CircuitDetailsHandler(
            self, self.circuit_id, operation="SERVICE_MAPPER", circuit_details_id=self.circuit_details_id
        ).device_onboarding_process()
        # grab updated circuit details
        self.circuit_details = self.bpo.resources.get(self.circuit_details_id)

    def management_ips_provided(self):
        for device in self.device_properties:
            if self.device_properties[device].get(MANAGEMENT_IP):
                return True

    def update_circuit_details_with_device_mgmt_ip(self):
        circuit_details_props = self.circuit_details["properties"]
        for topology in circuit_details_props["topology"]:
            for node in topology["data"]["node"]:
                for cd_device in node["name"]:
                    if self.device_management_ip_provided(cd_device):
                        self.get_updated_management_ip(node, cd_device)

        self.bpo.resources.patch(self.circuit_details_id, {"properties": circuit_details_props})
        self.circuit_details["properties"] = circuit_details_props

        return self.circuit_details

    def device_management_ip_provided(self, cd_device):
        # make sure the circuit details device is the device properties device
        # make sure the device properties has a management IP to update circuit details
        return (
            cd_device["name"] == "Host Name"
            and self.device_properties.get(cd_device["value"])
            and self.device_properties[cd_device["value"]].get(MANAGEMENT_IP)
        )

    def get_updated_management_ip(self, node, cd_device):
        for cd_device_detail in node["name"]:
            update_ip = self.get_ip_from_device_properties(cd_device_detail, cd_device)
            if update_ip:
                cd_device_detail["value"] = update_ip
                self.logger.info(f"Updated device management IP {cd_device_detail['value']}")

    def get_ip_from_device_properties(self, cd_device_detail, cd_device):
        # only return IP if circuit details IP differs from provided IP
        provided_management_ip = self.device_properties[cd_device["value"]][MANAGEMENT_IP]
        if cd_device_detail["name"] == MANAGEMENT_IP and self.management_ip_update_required(
            cd_device_detail["value"], provided_management_ip
        ):
            self.logger.info("Updating documented management IP value to provided management IP")
            self.logger.info(f"Original circuit details management IP: {cd_device_detail['value']}")
            self.logger.info(f"Provided management IP: {provided_management_ip}")
            return self.device_properties[cd_device["value"]][MANAGEMENT_IP]

    def management_ip_update_required(self, cd_management_ip, provided_management_ip):
        return cd_management_ip != provided_management_ip

    def get_service_differences(self, device: Device, adva_pro=False):
        self.network_config = self.get_network_config(device, self.service_type, remove_irr_data=False, full_path=True)[
            "network_config"
        ]
        self.modeled_config = self.get_designed_config(device)
        self.full_modeled_config = deepcopy(self.modeled_config)["designed_config"]
        stripped_modeled_config = self.remove_irrelevant_data(
            self.modeled_config, device, self.service_type, "designed", full_path=True, adva_pro=adva_pro
        )["designed_config"]
        self.network_diff, self.design_diff = self.utils.compare_complex_dicts(
            self.network_config, stripped_modeled_config
        )

        self.logger.info(f"Full Network config: {self.network_config}")
        self.logger.info(f"Full Design config: {self.full_modeled_config}")
        self.logger.info(f"Stripped Design config: {stripped_modeled_config}")
        self.logger.info(f"Network Diff: {self.network_diff}")
        self.logger.info(f"Design Diff: {self.design_diff}")

        if device.vendor == "RAD":
            self.check_duplex_against_bw(self.network_config, self.circuit_details)

        # Remove the slight diffs but still acceptable
        if self.network_diff:
            self.remove_acceptable_diffs(device)
            self.logger.info(f"Network Diff after remove_acceptable_diffs: {self.network_diff}")
            self.logger.info(f"Design Diff after remove_acceptable_diffs: {self.design_diff}")

    def remove_acceptable_diffs(self, device: Device):
        if self.order_type == "CHANGE":
            self.remove_non_bw_values(device)
        if self.service_type == "FIA" or self.service_type == "VOICE":
            self.remove_fia_acceptable_diffs(device)
        elif self.service_type == "ELINE":
            self.remove_eline_acceptable_diffs(device)
        elif self.service_type == "CTBH 4G":
            self.remove_eline_acceptable_diffs(device)
        elif self.service_type == "ELAN":
            self.remove_elan_acceptable_diffs(device)
        elif self.service_type == "NNI":
            self.remove_nni_acceptable_diffs(device)

    def remove_nni_acceptable_diffs(self, device: Device):
        pass

    def remove_fia_acceptable_diffs(self, device: Device):
        if device.vendor == "RAD":
            self.remove_rad_native_names()
        if device.vendor == "ADVA":
            self.remove_adva_service_names()
            self.remove_adva_pro_names()
            self.remove_adva_bw_if_meets_acceptable_value(device)
        if device.vendor == "JUNIPER":
            if self.service_type == "VOICE":
                self.allow_none_voice_values()
            self.remove_juniper_user_label()
            self.remove_juniper_ipv6()

    def remove_adva_bw_if_meets_acceptable_value(self, device: Device):
        network_model_bw = self.get_bandwidth_directly_from_model(self.network_config, device)
        design_model_bw = self.get_bandwidth_directly_from_model(self.full_modeled_config, device)
        self.logger.info(f"network_model_bw: {network_model_bw}")
        self.logger.info(f"design_model_bw: {design_model_bw}")
        design_bw_total, network_bw_total = self.get_total_bw_per_model(device.model, design_model_bw, network_model_bw)
        acceptable_bw_tolerance = self.maximum_allowed_bw_difference(design_bw_total)
        if self.is_bw_within_acceptable_range(network_bw_total, design_bw_total, acceptable_bw_tolerance):
            self.logger.info(
                f"bandwidth is within acceptable range and will not be remediated for model: {device.model}"
            )
            self.remove_bw_diff_keys(device)
        else:
            self.logger.info(f"bandwidth is not within acceptable range for model: {device.model}")

    def get_bandwidth_directly_from_model(self, config_model, device: Device) -> dict:
        if device.model in ADVA_PROS_LIST:
            client_side = config_model["Client TPE"]["properties"]["data"]["attributes"]["additionalAttributes"]
            network_side = config_model["Network TPE"]["properties"]["data"]["attributes"]["additionalAttributes"]

            cir = [
                client_side["queueProfile"]["cir"],
                client_side["policerProfile"]["cir"],
                network_side["queueProfile"]["cir"],
                network_side["policerProfile"]["cir"],
            ]
            eir = [
                client_side["queueProfile"]["eir"],
                client_side["policerProfile"]["eir"],
                network_side["queueProfile"]["eir"],
                network_side["policerProfile"]["eir"],
            ]

            return {"cir": cir, "eir": eir}
        else:
            client_side = config_model["FRE"]["properties"]["included"][device.handoff_port.upper()]["attributes"][
                "additionalAttributes"
            ]
            ep_access_a2n_flow_cir = client_side.get("epAccessA2NFlowCir", 0)
            ep_access_a2n_flow_eir = client_side.get("epAccessA2NFlowEir", 0)
            return {"epAccessA2NFlowCir": ep_access_a2n_flow_cir, "epAccessA2NFlowEir": ep_access_a2n_flow_eir}

    def get_total_bw_per_model(self, device_model, design_model_bw, network_model_bw):
        if device_model in ADVA_PROS_LIST:
            design_bw_total = sum(design_model_bw["cir"]) + sum(design_model_bw["eir"])
            network_bw_total = sum(network_model_bw["cir"]) + sum(network_model_bw["eir"])
        else:
            design_bw_total = sum(
                [design_model_bw.get("epAccessA2NFlowCir", 0), design_model_bw.get("epAccessA2NFlowEir", 0)]
            )
            network_bw_total = sum(
                [network_model_bw.get("epAccessA2NFlowCir", 0), network_model_bw.get("epAccessA2NFlowEir", 0)]
            )

        return design_bw_total, network_bw_total

    def maximum_allowed_bw_difference(self, design_bw_total):
        """returns percentage of the minimum design diff value acceptable compare."""
        return int(1 / 100 * design_bw_total)

    def is_bw_within_acceptable_range(self, network_bw_total, design_bw_total, acceptable_bw_tolerance) -> bool:
        """checks if network_bw is it within the range design_bw +/- acceptable_bw_tolerance. return true / false"""
        return (
            design_bw_total - acceptable_bw_tolerance <= network_bw_total <= design_bw_total + acceptable_bw_tolerance
        )

    def remove_bw_diff_keys(self, device: Device):
        if device.model in ADVA_PROS_LIST:
            self.network_diff.pop("cir", None)
            self.design_diff.pop("cir", None)
            self.network_diff.pop("eir", None)
            self.design_diff.pop("eir", None)
        else:
            self.network_diff.pop("epAccessA2NFlowCir", None)
            self.design_diff.pop("epAccessA2NFlowCir", None)
            self.network_diff.pop("epAccessA2NFlowEir", None)
            self.design_diff.pop("epAccessA2NFlowEir", None)

    def allow_none_voice_values(self):
        if self.network_diff.get("ipv6") == "None":
            self.network_diff.pop("ipv6")
            self.design_diff.pop("ipv6")
        if not self.network_diff.get("nextipv4hop", "True"):
            self.network_diff.pop("nextipv4hop")
            self.design_diff.pop("nextipv4hop")
        if not self.network_diff.get("nextipv6hop", "True"):
            self.network_diff.pop("nextipv6hop")
            self.design_diff.pop("nextipv6hop")
        if self.network_diff.get("in_bwProfileFlowParameters") == "None":
            self.network_diff.pop("in_bwProfileFlowParameters")
            self.design_diff.pop("in_bwProfileFlowParameters")

    def remove_eline_acceptable_diffs(self, device: Device):
        if device.vendor == "NOKIA":
            self.check_nokia_port_speed()
            self.check_nokia_cir()
        if device.vendor == "RAD":
            self.remove_rad_native_names()
        if device.vendor == "ADVA":
            self.remove_adva_bw_if_meets_acceptable_value(device)
            self.remove_adva_service_names()
            self.remove_adva_pro_names()
        if device.vendor == "JUNIPER":
            self.remove_juniper_user_label()

    def remove_elan_acceptable_diffs(self, device: Device):
        if device.vendor == "RAD":
            self.remove_rad_native_names()
        if device.vendor == "ADVA":
            self.remove_adva_bw_if_meets_acceptable_value(device)
            self.remove_adva_service_names()
            self.remove_adva_pro_names()

    def remove_adva_pro_names(self):
        if self.network_diff.get("circuitName") and self.circuit_id in self.network_diff["circuitName"]:
            self.network_diff.pop("circuitName")
            self.design_diff.pop("circuitName")
        if isinstance(self.network_diff.get("userLabel"), list):
            self.clean_user_label(self.network_diff)
        if isinstance(self.design_diff.get("userLabel"), list):
            self.clean_user_label(self.design_diff)
        if self.network_diff.get("userLabel") and self.circuit_id in self.network_diff["userLabel"]:
            self.network_diff.pop("userLabel")
            self.design_diff.pop("userLabel")

    def check_nokia_port_speed(self):
        if self.network_diff.get("port_speed"):
            if self.network_diff["port_speed"] >= self.full_modeled_config["FRE"]["cir"]:
                self.network_diff.pop("port_speed")
                self.design_diff.pop("port_speed")

    def check_nokia_cir(self):
        if self.network_diff.get("cir"):
            net_cir = self.network_diff.get("cir")
            des_cir = self.design_diff.get("cir")
            # Grab the absolute remainder of the diff and if it is within 10% of the design spec
            # allow the circuit to passs otherwise report out
            cir_difference = abs(int(net_cir) - int(des_cir))
            cir_tolerance = int(des_cir) * 0.1
            if cir_difference <= cir_tolerance:
                self.network_diff.pop("cir")
                self.design_diff.pop("cir")

    def clean_user_label(self, diff):
        for label in diff["userLabel"]:
            if self.circuit_id in label:
                diff["userLabel"].remove(label)
        if not diff["userLabel"]:
            diff.pop("userLabel")

    def remove_juniper_ipv6(self):
        if self.network_diff.get("ipv6") and self.network_diff["ipv6"] != "None":
            ipv6_net, ipv6_net_cidr = (
                ipaddress.IPv6Address(self.network_diff["ipv6"].split("/")[0]),
                self.network_diff["ipv6"].split("/")[1],
            )
            ipv6_des, ipv6_des_cidr = (
                ipaddress.IPv6Address(self.design_diff["ipv6"].split("/")[0]),
                self.design_diff["ipv6"].split("/")[1],
            )
            if ipv6_net.exploded == ipv6_des.exploded and ipv6_net_cidr == ipv6_des_cidr:
                self.network_diff.pop("ipv6")
                self.design_diff.pop("ipv6")
        if self.order_type == "CHANGE" and self.network_diff.get("ipv6") == "None":
            self.network_diff.pop("ipv6")
            if self.design_diff.get("ipv6"):
                self.design_diff.pop("ipv6")

    def remove_juniper_user_label(self):
        if self.network_diff.get("userLabel") and self.circuit_id in self.network_diff["userLabel"]:
            self.network_diff.pop("userLabel")
            self.design_diff.pop("userLabel")

    def remove_adva_service_names(self):
        if isinstance(self.network_diff.get("serviceName"), list):
            for label in self.network_diff["serviceName"]:
                if self.circuit_id in label:
                    self.network_diff["serviceName"].remove(label)
            if not self.network_diff["serviceName"]:
                self.network_diff.pop("serviceName")
        if isinstance(self.design_diff.get("serviceName"), list):
            for label in self.design_diff["serviceName"]:
                if self.circuit_id in label:
                    self.design_diff["serviceName"].remove(label)
            if not self.design_diff["serviceName"]:
                self.design_diff.pop("serviceName")
        if self.network_diff.get("serviceName") and self.circuit_id in self.network_diff["serviceName"]:
            self.network_diff.pop("serviceName")
            self.design_diff.pop("serviceName")

    def remove_rad_native_names(self):
        """Checks the nativeNames by changing case, sort and if list and removes if match is found"""
        if self.network_diff.get("service_name_IN") and self.design_diff.get("service_name_IN"):
            if self.network_diff["service_name_IN"].upper() == self.design_diff["service_name_IN"]:
                self.network_diff.pop("service_name_IN")
                self.design_diff.pop("service_name_IN")
        if self.network_diff.get("service_name_OUT") and self.design_diff.get("service_name_OUT"):
            if self.network_diff["service_name_OUT"].upper() == self.design_diff["service_name_OUT"]:
                self.network_diff.pop("service_name_OUT")
                self.design_diff.pop("service_name_OUT")

    def remove_non_bw_values(self, device):
        bw_keys = {
            "NOKIA": ["cir"],
            "RAD": ["policer_name", "admin_speed"],
            "ADVA": ["epAccessA2NFlowCir", "epAccessA2NFlowEir", "eir", "cir"],
            "JUNIPER": ["bandwidth_description", "bwProfileFlowParameters", "in_bwProfileFlowParameters", "bandwidth"],
            "CISCO": ["bandwidth"],
        }
        if device.vendor == "NOKIA":
            self.filter_by_key_list(bw_keys["NOKIA"])
        if device.vendor == "RAD":
            self.filter_by_key_list(bw_keys["RAD"])
        if device.vendor == "ADVA":
            self.filter_by_key_list(bw_keys["ADVA"])
        if device.vendor == "JUNIPER":
            self.filter_by_key_list(bw_keys["JUNIPER"])
        if device.vendor == "CISCO":
            self.filter_by_key_list(bw_keys["CISCO"])

    def filter_by_key_list(self, keys):
        """Removes all data except for specific keys passed"""
        filtered_network_diff = {}
        filtered_design_diff = {}
        for key in keys:
            if self.network_diff.get(key) and self.design_diff.get(key):
                filtered_network_diff[key] = self.network_diff.get(key)
                filtered_design_diff[key] = self.design_diff.get(key)
        self.network_diff = filtered_network_diff
        self.design_diff = filtered_design_diff

    def validate_network_data(self, device: Device) -> bool:
        self.logger.info(f" ======= SERVICE TYPE: {self.service_type} =======")
        status = False
        if self.service_type == "ELAN":
            status = self.validate_elan_network_data(device)
        elif self.service_type == "FIA":
            status = self.validate_fia_or_eline_network_data(device)
        elif self.service_type == "ELINE":
            status = self.validate_fia_or_eline_network_data(device)
        elif self.service_type == "VOICE":
            status = self.validate_voice_network_data(device)
        elif self.service_type == "NNI":
            status = self.validate_nni_network_data(device)
        else:
            status = True
        return status

    def validate_nni_network_data(self, device: Device) -> bool:
        skip_rem = True
        return skip_rem

    def validate_voice_network_data(self, device: Device) -> bool:
        skip_rem = False
        for key, value in self.network_config.items():
            if device.role == "PE":
                if key == "ARP" and not value:
                    self.network_diff.update({"voice_ip_in_arp_table": False})
                    self.patch_resource_with_diffs(device, False)
                    skip_rem = True
                if not value and key != "ARP":
                    skip_rem = self.validate_missing_config(device, key, value)
            else:
                skip_rem = self.validate_missing_config(device, key, value)
        return skip_rem

    def validate_fia_or_eline_network_data(self, device: Device) -> bool:
        skip_rem = False
        for key, value in self.network_config.items():
            skip_rem = self.validate_missing_config(device, key, value)
        return skip_rem

    def validate_missing_config(self, device: Device, key, value):
        if key == "FRE_ERROR":
            self.network_diff.update({f"{key}": value})
            self.patch_resource_with_diffs(device, False)
        if key == "FRE":
            if not value:
                self.network_diff.update({f"{key} Config Error": "Device is missing circuit config"})
                self.patch_resource_with_diffs(device, False)
                return True
        else:
            if not value:
                self.network_diff.update({f"{key} Config Error": "Device is missing interface config"})
                self.patch_resource_with_diffs(device, False)
                return True

    def validate_elan_network_data(self, device: Device) -> bool:
        skip_rem = False
        # If no network config found then we have errors and must fail this device
        for key, value in self.network_config.items():
            if device.role == "PE":
                if device.vendor == "CISCO":
                    return skip_rem
                else:
                    for key, value in self.network_config[key].items():
                        if key == "VPLS" and not value["Connection Active"] and not self.is_first_circuit():
                            self.network_diff.update({"VPLS_Connected": value["Connection Active"]})
                            self.patch_resource_with_diffs(device, False)
                        if key == "COS CONFIG":
                            continue
                        if not value:
                            self.network_diff.update({f"{key} Config Error": "Device is missing network config"})
                            self.patch_resource_with_diffs(device, False)
                            skip_rem = True
            if device.role == "CPE":
                for key, value in self.network_config[key].items():
                    if key == "FRE_ERROR":
                        self.network_diff.update({f"{key}": value})
                        self.patch_resource_with_diffs(device, False)
            elif not value:
                self.network_diff.update({f"{key} Config Error": "Device is missing network config"})
                self.patch_resource_with_diffs(device, False)
                skip_rem = True

        if device.adva_pro:
            found_cid = (
                self.network_config["FRE"]
                .get("properties", dict())
                .get("data", dict())
                .get("attributes", dict())
                .get("additionalAttributes", dict())
                .get("circuitName")
            )
            if found_cid:
                if self.circuit_id not in found_cid:
                    self.network_diff.update({"Flow Config Error": "mp_flow is not configured for this circuit"})
                    self.patch_resource_with_diffs(device, False)
                    skip_rem = True
            else:
                self.network_diff.update({"Config Error": "Device is missing mp_flow"})
                self.patch_resource_with_diffs(device, False)
                skip_rem = True
        return skip_rem

    def remediate_network(self, device: Device):
        if self.network_diff:
            self.vlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"]
            nf_resource = self.get_network_function_by_host_or_ip(device.fqdn, device.management_ip)
            self.device_prid = nf_resource["providerResourceId"]
            self.check_device_for_eligible_remediation(device)
            if device.required_remediation:
                self.logger.info(f"REQUIRED REMEDIATION::::: {device.required_remediation}")
                self.bpo.resources.patch_observed(
                    self.resource_id,
                    {"properties": {"remediation_attempted": True}},
                )
                self.patch_resource_with_diffs(device, True)
                if device.vendor == "CISCO":
                    self.remediate_cisco(device)
                if device.vendor == "RAD":
                    self.remediate_rad(device)
                if device.vendor == "ADVA":
                    self.remediate_adva(device)
                self.get_service_differences(device, adva_pro=device.adva_pro)
                self.patch_resource_with_diffs(device, False)
            else:
                self.patch_resource_with_diffs(device, False)

    def patch_resource_with_diffs(self, device: Device, initial_diff: bool, error_msg: dict = None):
        if error_msg:
            if isinstance(error_msg, str):
                error_msg = {"error": error_msg}
            self.patch_error_msg(f"{device.tid.upper()}_{device.location}", initial_diff, error_msg)
        else:
            self.patch_service_diffs(
                self.network_diff,
                self.design_diff,
                f"{device.tid.upper()}_{device.location}",
                initial_diff,
            )

    def check_device_for_eligible_remediation(self, device: Device):
        # Bandwidth Check
        self.check_network_diff_for_eligible_keys(
            "bandwidth_update",
            device,
        )
        # Desciption Checks
        self.check_network_diff_for_eligible_keys(
            "description_update",
            device,
        )
        # Pbit Check
        self.check_network_diff_for_eligible_keys(
            "pbit_update",
            device,
        )

    def check_network_diff_for_eligible_keys(self, update_type, device: Device):
        if any(key in self.network_diff.keys() for key in self.UPDATE_TYPES[update_type]):
            device.required_remediation[update_type] = device.tid

    def remediate_juniper(self, device: Device):
        if device.required_remediation.get("description_update"):
            self.remediate_juniper_description(device)
        if device.required_remediation.get("bandwidth_update"):
            self.remediate_juniper_bandwidth(device)
        return device.required_remediation

    def remediate_adva(self, device: Device):
        if device.adva_pro:
            self.remediate_adva_pro(device)
        else:
            flow_id = self.network_config.get("FRE", dict()).get("properties", dict()).get("data", dict()).get("id", "")
            if flow_id:
                parameters = {"port": device.handoff_port.lower(), "flow_id": flow_id}
                if device.required_remediation.get("description_update"):
                    parameters["description_update"] = "true"
                    parameters["alias"] = device.handoff_port_description
                    parameters["circuit-name"] = self.circuit_id
                if device.required_remediation.get("bandwidth_update"):
                    # all adva mtus are pros, so bw conversions below are for cpe standards
                    parameters["bandwidth_update"] = "true"
                    parameters["cir"] = self.path_to_adva_design_model_additional_attributes(
                        device.handoff_port.upper(), "epAccessA2NFlowCir"
                    )
                    parameters["cbs"] = self.path_to_adva_design_model_additional_attributes(
                        device.handoff_port.upper(), "epAccessA2NFlowCbs"
                    )
                    parameters["eir"] = self.path_to_adva_design_model_additional_attributes(
                        device.handoff_port.upper(), "epAccessA2NFlowEir"
                    )
                    parameters["ebs"] = self.path_to_adva_design_model_additional_attributes(
                        device.handoff_port.upper(), "epAccessA2NFlowEbs"
                    )
                if device.required_remediation.get("pbit_update") and self.check_if_pbit_vlan_matches():
                    parameters["pbit_update"] = "true"
                    parameters["ctag"] = self.design_diff.get("epAccessFlowCVlanTag")[0]
                self.logger.info(f" ======= parameter values before racutthrough is launched: {parameters} =======")
                try:
                    self.execute_ra_command_file(
                        self.device_prid,
                        "remediation.json",
                        parameters,
                    )
                except Exception as e:
                    self.logger.info(f"Failed to remediate ADVA device {device.tid} with error {e}")

    def path_to_adva_design_model_additional_attributes(self, handoff_port, key_value):
        return self.full_modeled_config["FRE"]["properties"]["included"][handoff_port]["attributes"][
            "additionalAttributes"
        ][key_value]

    def check_if_pbit_vlan_matches(self):
        designed_vlan_tag = self.design_diff.get("epAccessFlowCVlanTag")[0].split("-")[0]
        network_vlan_tag = self.network_diff.get("epAccessFlowCVlanTag")[0].split("-")[0]
        if designed_vlan_tag != network_vlan_tag:
            self.logger.info("Pbit not remediated due to vlan mismatch")
            return False
        return True

    def remediate_adva_pro(self, device: Device):
        parameters = {
            "flowpoint_id_client": self.path_to_flowpoint_id("Client TPE"),
            "flowpoint_id_network": self.path_to_flowpoint_id("Network TPE"),
            "client_port": device.handoff_port.lower().split("-")[-1],
        }
        if device.required_remediation.get("description_update"):
            parameters["description_update"] = "true"
            parameters["client_desc"] = device.handoff_port_description
        if device.required_remediation.get("bandwidth_update"):
            parameters["bandwidth_update"] = "true"
            parameters["cir"] = self.path_to_adva_design_model_policer_profile().get("cir", 0)
            parameters["eir"] = self.path_to_adva_design_model_policer_profile().get("eir", 0)
            parameters["cbs"] = self.path_to_adva_design_model_policer_profile().get("cbs", "512")
            parameters["ebs"] = self.path_to_adva_design_model_policer_profile().get("ebs", "512")
            parameters["is_elephant_flow"] = (
                "true" if self.path_to_adva_design_model_policer_profile().get("cir", 0) >= 2000000000 else "false"
            )
        if device.required_remediation.get("pbit_update") and not self.design_diff.get("vlanId"):
            parameters["pbit_update"] = "true"
            parameters["ctag"] = f"{self.vlan}-{self.design_diff.get('c_tag_pbit')}"

        self.logger.debug(f"Remediation paramaters: {parameters}")
        model_path = self.get_device_model_dir_name(device.model)

        try:
            self.execute_ra_command_file(
                self.device_prid,
                f"ge/{model_path}/remediation.json",
                parameters,
            )
        except Exception as e:
            self.logger.info(f"Failed to remediate ADVA device {device.tid} with error {e}")

    def path_to_flowpoint_id(self, tpe):
        """Param Client TPE or Network TPE"""
        return self.network_config[tpe]["properties"]["data"]["id"].split("-")[-1]

    def path_to_adva_design_model_policer_profile(self):
        return self.full_modeled_config["Client TPE"]["properties"]["data"]["attributes"]["additionalAttributes"][
            "policerProfile"
        ]

    def remediate_rad(self, device: Device):
        parameters = {}
        native_name = self.get_verfied_native_name()
        if device.required_remediation.get("description_update"):
            parameters["description_update"] = "true"
            parameters["desc"] = device.handoff_port_description
            parameters["port"] = device.handoff_port.replace("-", " ").lower()
        if device.required_remediation.get("bandwidth_update") and native_name:
            parameters["bandwidth_update"] = "true"
            parameters["bw"] = self.design_diff["policer_name"]
            parameters["native_name"] = native_name
            parameters["cid"] = self.circuit_id
        if device.required_remediation.get("pbit_update") and not self.design_diff.get("vlan"):
            if native_name:
                parameters["pbit_update"] = "true"
                parameters["native_name"] = native_name
                parameters["vlan"] = self.vlan
                parameters["pbit"] = self.design_diff.get("egressCosPbit")
        try:
            self.execute_ra_command_file(
                self.device_prid,
                "remediation.json",
                parameters,
            )
        except Exception as e:
            self.logger.info(f"Failed to remediate RAD device {device.tid} with error {e}")

    def get_verfied_native_name(self):
        native_name_in = self.network_config.get("FRE", dict()).get("service_name_IN", "")
        self.logger.info(f"NATIVE NAMES LIST: {native_name_in}")
        if native_name_in:
            return native_name_in
        return False

    def remediate_juniper_description(self, device: Device):
        service_decr = self.get_service_userLabel(self.circuit_details)
        if self.service_type == "ELAN":
            elan_ri_descr = self.get_elan_ri_description()
        try:
            self.execute_ra_command_file(
                self.device_prid,
                "set-physical-interface-params.json",
                {
                    "interface": device.handoff_port.lower(),
                    "param": "description",
                    "description": device.handoff_port_description,
                    "commit": False,
                },
            )
            if device.role == "PE":
                self.execute_ra_command_file(
                    self.device_prid,
                    "update-logical-tpe.json",
                    {
                        "interface": device.handoff_port.lower(),
                        "unit": self.vlan,
                        "description": service_decr,
                        "commit": False if self.service_type == "ELAN" else True,
                    },
                )
                if self.service_type == "ELAN":
                    label = (
                        self.network_config["FRE"].get("ROUTING INSTANCE", dict()).get("properties", dict()).get("name")
                    )
                    self.execute_ra_command_file(
                        self.device_prid,
                        "update-routing-instance-direct.json",
                        {
                            "name": label,
                            "description": elan_ri_descr,
                            "commit": True,
                        },
                    )
            else:
                self.execute_ra_command_file(
                    self.device_prid,
                    "update-logical-tpe-vlans-description.json",
                    {
                        "vlan_name": self.network_config["FRE"]["vlan_name"],
                        "description": service_decr,
                        "commit": True,
                    },
                )

        except Exception as e:
            self.logger.info(f"Failed to remediate JUNIPER device {device.tid} with error {e}")

    def get_elan_ri_description(self):
        vrfid = self.circuit_details["properties"]["service"][0]["data"]["elan"][0]["vrfId"]
        return f"VC{vrfid}:TRANS:ELAN::"

    def remediate_juniper_bandwidth(self, device: Device):
        policers_on_interface = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "get-logical-tpe.json",
            parameters={"interface": device.handoff_port.lower(), "unit": self.vlan},
            headers=None,
        )
        is_edna = self.check_is_edna(self.device_prid)

        for each in self.modeled_config["FRE"]:
            if "bandwidth" in each:
                bw_full = self.modeled_config["FRE"][each]
                break
        bw = self.get_bw_in_kbps(bw_full)

        egress_policer = ingress_policer = self.get_bandwidth_formatted(bw_full, is_edna)

        try:
            if "input_policer" in policers_on_interface.json()["result"] and ingress_policer is not None:
                self.execute_ra_command_file(
                    self.device_prid,
                    "update-logical-tpe.json",
                    parameters={
                        "interface": device.handoff_port.lower(),
                        "unit": self.vlan,
                        "bandwidth": bw,
                        "input_policer": ingress_policer,
                        "output_policer": egress_policer,
                        "service_type": self.service_type,
                        "commit": True,
                    },
                    headers=None,
                )
            else:
                self.execute_ra_command_file(
                    self.device_prid,
                    "update-logical-tpe.json",
                    parameters={
                        "interface": device.handoff_port.lower(),
                        "unit": self.vlan,
                        "bandwidth": bw,
                        "output_policer": egress_policer,
                        "service_type": self.service_type,
                        "commit": True,
                    },
                    headers=None,
                )
        except Exception as e:
            self.logger.info(f"Failed to remediate JUNIPER device {device.tid} with error {e}")

    def get_bandwidth_formatted(self, bw, edna=False):
        return f"RL_{bw}" if edna else bw

    def get_bw_in_kbps(self, bw):
        if bw is None:
            return "None"
        else:
            self.logger.info("creds are correct")

    def check_duplex_against_bw(self, network_config_model, circuit_details):
        admin_speed = 0
        self.logger.info(f"network AdminSpeed: {network_config_model}")
        admin_speed = int(network_config_model["FRE"].get("admin_speed", ""))
        bandwidth = circuit_details["properties"]["service"][0]["data"]["evc"][0]["evc-egress-bwp"]
        bw_in_kbps = self.get_bandwidth_in_kbps(bandwidth)
        if admin_speed < bw_in_kbps:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Unsupported AdminSpeed for Bandwidth",
                f"admin speed: {admin_speed} bandwidth: {bw_in_kbps}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.logger.info("Unsupported admin speed for specified bandwidth")
            self.network_diff["adminSpeed"] = msg
        self.logger.info(f"AdminSpeed: {admin_speed},  Bandwidth: {bw_in_kbps}")

    def remediate_cisco(self, device: Device):
        self.network_interface_id = device.network_port.replace("-", "/") if device.network_port else ""
        self.client_interface_id = device.handoff_port.replace("-", "/") if device.handoff_port else ""
        self.interface_service_instances = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "cm-get-service-policies.json",
            {
                "network_interface_id": self.network_interface_id,
                "client_interface_id": self.client_interface_id,
                "vlan": self.vlan,
            },
        ).json()["result"]
        parameters = {
            "portRole": device.port_role,
            "serviceType": self.service_type,
            "pbit": int(self.get_pbit()),
            "cid": self.circuit_id,
            "vlan": self.vlan,
            "network_interface": self.network_interface_id,
            "client_interface": self.client_interface_id,
        }
        self.add_cisco_remediation_params(parameters, device)
        try:
            self.cutthrough.execute_ra_command_file(self.device_prid, "remediation.json", parameters, headers=None)
        except Exception as e:
            self.logger.info(f"Failed to remediate Cisco {device.model} device {device.tid} with error {e}")

    def add_cisco_remediation_params(self, parameters, device: Device):
        client_service_policy = self.get_service_policy_instance_for(self.client_interface_id)
        network_service_policy = self.get_service_policy_instance_for(self.network_interface_id)
        if device.required_remediation.get("bandwidth_update"):
            parameters.update(
                {
                    "bandwidth_update": "true",
                    "old_client_service_policy_input": client_service_policy["input"],
                    "old_client_service_policy_output": client_service_policy["output"],
                    "old_network_service_policy_input": network_service_policy["input"],
                    "old_network_service_policy_output": network_service_policy["output"],
                    "bandwidth_bps": self.design_diff.get("bandwidth", ""),
                    "bandwidth_kbps": self.convert_to_kbits(),
                    "bandwidth": self.bw,
                    "qos_description": f"{device.port_role}:{self.service_type}:::{self.vlan}",
                    "new_network_service_policy_input": f"QCP-{self.service_type}{self.bw}-HFP-IN-SUBMAP",
                    "new_client_service_policy_input": f"QSP-{self.service_type}{self.bw}-CFP-IN-MAP",
                }
            )
        if device.required_remediation.get("description_update"):
            parameters.update(
                {
                    "description_update": "true",
                    "port_description": self.design_diff.get("portDescription", ""),
                    "client_interface_description": self.design_diff.get("serviceDescription", ""),
                }
            )
        if network_service_policy["input"] or network_service_policy["output"]:
            parameters["is_network_interface_policed"] = "True"

    def get_service_policy_instance_for(self, interface) -> dict:
        service_policy_input = ""
        service_policy_output = ""
        for instance in self.interface_service_instances:
            if (
                instance["interface"] == interface
                and instance["instance_id"] == str(self.vlan)
                and instance["instance_tag"] == self.circuit_id
            ):
                return {
                    "input": instance.get("service_policy_input", ""),
                    "output": instance.get("service_policy_output", ""),
                }
        return {"input": service_policy_input, "output": service_policy_output}

    def get_pbit(self):
        pbit = {"GOLD": "5", "SILVER": "3", "BRONZE": "1"}
        return pbit[self.get_cos()]

    def get_cos(self):
        return (
            self.circuit_details.get("properties", dict())
            .get("service", dict())[0]
            .get("data", dict())
            .get("evc", dict())[0]
            .get("cosNames", dict())[0]
            .get("name", "none")
        )

    def convert_to_kbits(self):
        if self.bw[-1] == "g":
            return self.bw[:-1] + "000000"
        elif self.bw[-1] == "m":
            return self.bw[:-1] + "000"
        return ""


class Terminate(Common):
    def process(self):
        resource_dependents = self.get_dependencies(self.resource["id"])
        for resource_dependent in resource_dependents:
            self.logger.info("existing resource_dependent id found: {}".format(resource_dependent["id"]))
            self.bpo.resources.patch(
                resource_dependent["id"],
                {"desiredOrchState": "terminated", "orchState": "terminated"},
            )
