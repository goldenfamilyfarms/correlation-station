import ipaddress
import sys

from ra_plugins.ra_cutthrough import RaCutThrough

sys.path.append("model-definitions")
from scripts.configmodeler.base import ConfigBase


class Cisco(ConfigBase):
    CISCO_9K = [
        "ASR 9001",
        "ASR 9006",
        "ASR 9010",
    ]

    def __init__(
        self,
        plan,
        circuit_id: str,
        device: str,
        location: str,
        circuit_details_id: str,
    ):
        self.plan = plan
        self.circuit_id = circuit_id
        self.cutthrough = RaCutThrough()
        self.circuit_details = self.bpo.resources.get(circuit_details_id)
        self.logger.info(f"self.circuit_details = {self.circuit_details}")
        self.service_type = self.circuit_details["properties"]["serviceType"]
        super().__init__(self.service_type)
        self.device = self._get_device_details(device_tid=device.upper(), location=location)
        self.logger.info(f"self.device = {self.device}")
        self.device_port_role = self.device["Client Interface Description"].split(":")[1]
        self.logger.info(f"self.device_port_role = {self.device_port_role}")
        self.device_model = self.device["Model"]
        self.device_role = self.device["Role"]
        self.device_model_dir_name = self.get_device_model_dir_name(self.device_model)
        self.nf_resource = self.get_network_function_by_host_or_ip(
            self.device["FQDN"], self.device["Management IP"], require_active=True
        )
        if not self.nf_resource:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Cannot generate Cisco config model without active network function for device: {self.device['FQDN']}."
            )
            self.categorized_error = msg
            self.exit_error(msg)
        self.client_interface = self.device["Client Interface"]
        self.svlan = self.get_svlan()
        self.device_prid = self.nf_resource["providerResourceId"]
        self.ipv4, self.mask, self.ipv6 = self.get_ips_and_subnet_for_design_model()
        self.port_role = self.get_port_role(
            self.circuit_details, self.device["Host Name"] + "-" + self.client_interface
        )
        self.bw = self.get_bw()
        self.cos = self.get_cos()
        self.service_policy_input, self.service_policy_output = self.get_service_policy()
        self.endpoints = self.get_endpoints()

    def _model_nni_config(self):
        """
        Generates the service design model for NNI services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional NNI model
        """
        self.logger.info("=== Generating CISCO NNI Specific Model ===")
        nni_model = {}
        self.base_model.update(nni_model)

    def generate_design_model(self):
        self.logger.info(f"Adding {self.service_type} config details to base model")
        self._generate_base_model()
        return self.base_model

    def _generate_base_model(self) -> dict:
        """
        Example:
        {
        "id": "GigabitEthernet0-1-0-3",
        "mtu": "9172",
        "ipv4": "192.168.2.5",
        "ipv6": "",
        "port": "GigabitEthernet0-1-0-3",
        "type": "tpes",
        "vlan": "1100",
        "label": "GigabitEthernet0/1/0/3",
        "state": "IS",
        "active": true,
        "subnet": "255.255.255.252",
        "dampening": "",
        "layerRate": "DSR_1GE",
        "orchState": "active",
        "adminState": "up",
        "discovered": true,
        "nativeName": "GigabitEthernet0-1-0-3",
        "ipv4Address": "Unknown",
        "displayAlias": "GigabitEthernet 0/1/0/3",
        "structureType": "PTP",
        "managementType": "cli",
        "stackDirection": "bidirectional",
        "ipv4AccessGroup": "FIA-FILTER-IN",
        "ipv6AccessGroup": "IPV6-FIA-FILTER-IN",
        "portDescription": "CPE:AUT1TXC41ZW,ME3400E:ge-0/0/0::CPE:cali-1.5.6",
        "operationalState": "up",
        "terminationState": "terminated bidirectional",
        "serviceDescription": "51.L1XX.008967..TWCC:CUST:FIA:78759:",
        "servicePolicyInput": "QSP-FIA-UNI-500m-IN",
        "subportInformation": false,
        "servicePolicyOutput": "QSP-FIA-UNI-500m-OUT"
        }
        """
        design_model = {
            "id": self.client_interface,
            "mtu": "",
            "ipv4": str(self.ipv4),
            "ipv6": str(self.ipv6),
            "port": self.client_interface,
            "type": "tpes",
            "vlan": self.svlan,
            "label": self.client_interface.replace("-", "/"),
            "state": "IS",
            "active": True,
            "subnet": str(self.mask),
            "dampening": "",
            "layerRate": "DSR_1GE",
            "bandwidth": str(self.bw_to_bytes()),
            "orchState": "active",
            "adminState": "up",
            "discovered": True,
            "nativeName": self.client_interface,
            "ipv4Address": "Unknown",
            "displayAlias": self.client_interface.replace("-", "/"),
            "structureType": "PTP",
            "managementType": "cli",
            "stackDirection": "bidirectional",
            "ipv4AccessGroup": "FIA-FILTER-IN" if self.ipv4 and self.device_model in self.CISCO_9K else "",
            "ipv6AccessGroup": "IPV6-FIA-FILTER-IN" if self.ipv6 and self.device_model in self.CISCO_9K else "",
            "portDescription": self.device["Client Interface Description"],
            "operationalState": "up",
            "terminationState": "terminated bidirectional",
            "serviceDescription": self.get_service_description(),
            "servicePolicyInput": self.service_policy_input,
            "subportInformation": False,
            "servicePolicyOutput": self.service_policy_output,
            "evc": self.get_evc_id(),
            "neighborIp": self.get_l2circuit_neighbor_ip(),
            "l2vpnLocalSegment1": "UP" if self.service_type == "ELINE" else "",
            "l2vpnRemoteSegment2": "UP" if self.service_type == "ELINE" else "",
            "bridgeGroup": "",
            "bridgeDomain": "",
            "bridgeDomainState": "up",
        }
        self.base_model = {
            "FRE": design_model,
        }
        return self.base_model

    def generate_network_model(self) -> dict:
        """Example {"port": "GigabitEthernet0/1/0/1, "vlan": "1100"}"""
        self.logger.info("Generating CISCO Network Model")

        try:
            network_values = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "cm-get-network-values.json",
                parameters={"port": self.client_interface_formatted(), "vlan": self.svlan},
                headers=None,
            ).json()["result"][0]
        except Exception as e:
            self.logger.info(f"Failed to gather network values {self.device['Host Name']} with error {e}")
            return {"FRE": {}}
        service_policy_input, service_policy_output = self.get_service_policy_instance_for(
            self.client_interface_formatted()
        )
        network_values["service_policy_input"] = service_policy_input
        network_values["service_policy_output"] = service_policy_output
        network_values["police_cir"] = self.get_police_cir(service_policy_input, service_policy_output)

        network_model = self.network_template_create(network_values)
        return network_model

    def get_service_policy_instance_for(self, interface):
        service_policies = self.get_network_model_service_policies_from_device()
        for instance in service_policies:
            if (
                interface in instance["interface"]
                and instance["instance_id"] == str(self.svlan)
                and instance["instance_tag"] == self.circuit_id
                and instance["encapsulation"] != "untagged"
            ):
                return instance.get("service_policy_input", ""), instance.get("service_policy_output", "")
            if interface in instance["interface"] and instance["encapsulation"] != "untagged":
                return instance.get("service_policy_input", ""), instance.get("service_policy_output", "")
        return "", ""

    def get_network_model_service_policies_from_device(self):
        try:
            service_policies = self.cutthrough.execute_ra_command_file(
                self.device_prid,
                "cm-get-service-policies.json",
                parameters={"client_interface_id": self.client_interface_formatted(), "vlan": self.svlan},
                headers=None,
            ).json()["result"]
        except Exception as e:
            self.logger.info(f"Failed to gather network values {self.device['Host Name']} with error {e}")
        return service_policies

    def get_police_cir(self, service_policy_input, service_policy_output):
        service_policy_name = service_policy_input
        if self.device_model in self.CISCO_9K and self.service_type in ["FIA", "VOICE"]:
            service_policy_name = service_policy_output
        if service_policy_name:
            try:
                police_cir = self.cutthrough.execute_ra_command_file(
                    self.device_prid,
                    "cm-get-police-cir.json",
                    parameters={"service_policy_name": service_policy_name},
                    headers=None,
                ).json()["result"][0]
                self.logger.info(f"get_police_cir: {police_cir}")
            except Exception as e:
                self.logger.info(f"Failed to gather police cir {self.device['Host Name']} with error {e}")
                return ""
            return police_cir["police_cir"]
        return ""

    def network_template_create(self, network_values) -> dict:
        network_config = {
            "label": self.get_network_alias_label(network_values),
            "orchState": "active",
            "discovered": True,
            "id": self.get_network_formated_port_id(network_values),
            "type": "tpes",
            "state": self.get_network_state(network_values),
            "active": True,
            "port": self.get_network_formated_port_id(network_values),
            "managementType": "cli",
            "nativeName": self.get_network_formated_port_id(network_values),
            "displayAlias": self.get_network_alias_label(network_values),
            "structureType": "PTP",
            "stackDirection": "bidirectional",
            "layerRate": "DSR_1GE",
            "adminState": self.get_network_admin_state(network_values),
            "operationalState": self.get_network_operational_state(network_values),
            "terminationState": "terminated bidirectional",
            "mtu": network_values.get("Mtu", ""),
            "bandwidth": network_values.get("police_cir", ""),
            "bandwidthUnits": network_values.get("BwUnits", ""),
            "ipv4": network_values.get("ipv4", ""),
            "ipv6": network_values.get("ipv6", ""),
            "vlan": network_values.get("vlan", ""),
            "subnet": network_values.get("subnet", ""),
            "dampening": network_values.get("dampening", ""),
            "ipv4Address": network_values.get("IpInfo", ""),
            "ipv4AccessGroup": network_values.get("ipv4_access_group", ""),
            "ipv6AccessGroup": network_values.get("ipv6_access_group", ""),
            "portDescription": network_values.get("port_description", ""),
            "serviceDescription": network_values.get("service_description", ""),
            "servicePolicyInput": network_values.get("service_policy_input", ""),
            "subportInformation": True if network_values.get("layer2", "") else False,
            "servicePolicyOutput": network_values.get("service_policy_output", ""),
            "evc": network_values.get("evc_id", ""),
            "neighborIp": network_values.get("neighbor_ip", ""),
            "l2vpnLocalSegment1": network_values.get("l2vpn_local_segment1", ""),
            "l2vpnRemoteSegment2": network_values.get("l2vpn_remote_segment2", ""),
            "bridgeGroup": network_values.get("bridge_group", ""),
            "bridgeDomain": network_values.get("bridge_domain", ""),
            "bridgeDomainState": network_values.get("bridge_domain_state", ""),
        }
        network_model = {
            "FRE": network_config,
        }
        return network_model

    def client_interface_formatted(self):
        """Example return GigabitEthernet0/1/0/1"""
        return self.client_interface.replace("-", "/")

    def get_ips_and_subnet_for_design_model(self):
        ipv4, mask, ipv6 = "", "", ""
        if self.service_type in ["FIA", "VOICE"]:
            fia = self.circuit_details.get("properties", {}).get("service", [])[0].get("data", {}).get("fia", False)
            if fia:
                endpoints = fia[0]["endPoints"][0]
                ipv4_scope = (
                    endpoints["wanIpv4Address"] if fia[0]["type"] == "STATIC" else endpoints["lanIpv4Addresses"][0]
                )
                network_ip_scope = ipaddress.IPv4Interface(ipv4_scope)
                ipv4 = network_ip_scope.ip
                if self.service_type == "VOICE":
                    ipv4 = network_ip_scope.ip + 1
                mask = network_ip_scope.with_netmask.split("/")[1]
                ipv6 = endpoints.get("wanIpv6Address", "")
        return ipv4, mask, ipv6

    def get_l2circuit_neighbor_ip(self):
        ip = ""
        if self.service_type == "ELINE":
            topology_check = self.get_index()
            topology_index = 1 if topology_check == 0 else 0
            node_index = int("-1" if topology_check == 1 else 0)
            ip = self.circuit_details["properties"]["topology"][topology_index]["data"]["node"][node_index]["name"][4][
                "value"
            ]
        return ip

    def get_supported_device_name(self, model):
        directory = {
            "ASR 9001": "asr9k",
            "ASR 9006": "asr9k",
            "ASR 9010": "asr9k",
            "ME-3400E-24TS-M": "me3400",
            "ME-3400-EG-12CS-M": "me3400",
            "ME-3400-2CS": "me3400",
            "ASR-920-12CZ": "asr920",
            "ASR-920-24SZ": "asr920",
            "ASR-920-4SZ-A": "asr920",
        }
        return directory[model]

    def get_service_policy(self):
        get_supported_device = self.get_supported_device_name(self.device_model)
        return {
            "asr9k": self.get_service_policy_asr9k,
            "asr920": self.get_service_policy_asr920,
            "me3400": self.get_service_policy_me3400,
        }[get_supported_device]()

    def get_service_policy_asr9k(self):
        """Generates IN and OUT policey_maps for PE"""

        cos_policy = {
            "GOLD": {"input": f"QSP-CS-G-{self.bw}-IN", "output": f"QSP-CS-{self.bw}-OUT"},
            "SILVER": {"input": f"QSP-CS-S-{self.bw}-IN", "output": f"QSP-CS-{self.bw}-OUT"},
            "BRONZE": {"input": f"QSP-BE-CS-B-{self.bw}-IN", "output": f"QSP-CS-{self.bw}-OUT"},
        }
        service_policy_input = ""
        service_policy_output = ""
        if self.service_type in ["FIA", "VOICE"]:
            if "UNI" in self.port_role:
                service_policy_input = f"QSP-{self.service_type}-UNI-{self.bw}-IN"
                service_policy_output = f"QSP-{self.service_type}-UNI-{self.bw}-OUT"
            elif "INNI" in self.port_role:
                service_policy_input = ""
                service_policy_output = f"QSP-{self.service_type}-CPE-{self.bw}-OUT"
        else:
            if "UNI" in self.port_role:
                service_policy_input = cos_policy[self.cos]["input"]
                service_policy_output = cos_policy[self.cos]["output"]
            elif "INNI" in self.port_role:
                service_policy_input = cos_policy[self.cos]["input"]
                service_policy_output = ""
        return service_policy_input, service_policy_output

    def get_service_policy_asr920(self):
        service_policy_input = f"QSP-Policer-{self.bw}-CFP-IN-MAP"
        service_policy_output = ""
        return service_policy_input, service_policy_output

    def get_service_policy_me3400(self):
        service_policy_input = self.circuit_id
        service_policy_output = ""
        return service_policy_input, service_policy_output

    def bw_to_bytes(self):
        bytes_size = 1000000000 if self.bw[-1] == "g" else 1000000
        bw_to_bytes = (int(self.bw[:-1]) * 1.1) * bytes_size
        if self.device_role == "PE":
            bw_to_bytes = int(self.bw[:-1]) * bytes_size
        return int(bw_to_bytes)

    def get_service_description(self):
        service_description = ""
        if self.device_role == "PE":
            service_description = self.endpoints[0]["userLabel"]
            if self.service_type == "ELINE":
                service_description = self.endpoints[self.get_index()]["userLabel"]
        return service_description

    def get_evc_id(self):
        return (
            self.circuit_details.get("properties", dict())
            .get("service", dict())[0]
            .get("data", dict())
            .get("evc", dict())[0]
            .get("evcId", "")
        )

    def get_bw(self):
        return (
            self.circuit_details.get("properties", dict())
            .get("service", dict())[0]
            .get("data", dict())
            .get("evc", dict())[0]
            .get("evc-egress-bwp", "none")
        )

    def get_cos(self):
        return (
            self.circuit_details.get("properties", dict())
            .get("service", dict())[0]
            .get("data", dict())
            .get("evc", dict())[0]
            .get("cosNames", dict())[0]
            .get("name", "none")
        )

    def get_svlan(self):
        return self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0].get("sVlan")

    def get_endpoints(self):
        return (
            self.circuit_details.get("properties", dict())
            .get("service", dict())[0]
            .get("data", dict())
            .get("evc", dict())[0]
            .get("endPoints", "")
        )

    def get_index(self):
        """this can determine a and z loc as well if needed"""
        return (
            0
            if self.device["Host Name"]
            not in self.circuit_details["properties"]["topology"][-1]["data"]["link"][0]["uuid"]
            else 1
        )

    def get_network_operational_state(self, network_values):
        return "up" if network_values.get("lineStatus", "").lower() in ["up", "administratively up"] else "down"

    def get_network_admin_state(self, network_values):
        return "up" if network_values.get("status", "").lower() in ["up", "administratively up"] else "down"

    def get_network_state(self, network_values):
        return "IS" if network_values.get("status", "").lower() in ["up", "administratively up"] else "OOS"

    def get_network_alias_label(self, network_values):
        return f"{network_values.get('intfType', '')}{network_values.get('port', '')}"

    def get_network_formated_port_id(self, network_values):
        return (
            f"{network_values.get('intfType', '')}{network_values.get('port', '').replace('/', '-').replace(' ', '')}"
        )
