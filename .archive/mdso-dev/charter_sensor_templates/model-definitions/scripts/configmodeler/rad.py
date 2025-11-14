import json
import sys

from ra_plugins.ra_cutthrough import RaCutThrough

sys.path.append("model-definitions")
from scripts.configmodeler.base import ConfigBase


class RAD(ConfigBase):
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
        self.service_type = self.circuit_details["properties"]["serviceType"]
        super().__init__(self.service_type)
        self.device = self._get_device_details(device_tid=device.upper(), location=location)
        self.nf_resource = self.get_network_function_by_host_or_ip(
            self.device["FQDN"], self.device["Management IP"], require_active=True
        )
        if not self.nf_resource:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Cannot generate RAD config model without active network function for device: {self.device['FQDN']}."
            )
            self.categorized_error = msg
            self.exit_error(msg)
        self.device_prid = self.nf_resource["providerResourceId"]
        self.client_port = self.device["Client Interface"].split("-")[1]
        self.network_port = self._check_lagged()
        self.port_type = self.get_port_role(
            self.circuit_details, self.device["Host Name"] + "-" + self.device["Client Interface"]
        )
        self.evc_id = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evcId")
        self.svlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("sVlan", "")
        self.ms_vlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("msVlan", "")
        self.ce_vlans = self.get_ce_vlans()
        self.user_label = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0].get(
            "userLabel"
        )
        self.evc_ingress_bwp = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evc-ingress-bwp")
        self.pbit = self._get_pbit()

    def _check_lagged(self):
        """Sets the expected network interface or if lagged defaults to 4/1"""
        port = ""
        if "LAG" in self.device["Network Interface"].upper():
            port = "4/1"
        else:
            port = self.device["Network Interface"].split("-")[1]

        return port

    def _model_nni_config(self):
        """
        Generates the service design model for NNI services
        Parameters:
            None
        Returns:
            self.base_model (dict): The service design model with additional NNI model
        """
        self.logger.info("=== Generating RAD NNI Specific Model ===")
        nni_model = {}
        self.base_model.update(nni_model)

    def _generate_base_model(self):
        """
        Example:
        self.base_model: {
            "mtu": "12000",
            "name": "51001.GE1.CNI2TXR26AW.CNI2TXR3MZW:CPE:CNI2TXR3MZW:ETHERNET-1:97.77.67.125",
            "vlan": "1103",
            "p_bit": "",
            "ms_vlan": "88",
            "mac_l2cp": "network",
            "admin_state": "Up",
            "policer_name": "",
            "operation_state": "Up",
            "service_name_IN": "51.YSMS.009859..TWCC-IN",
            "service_name_OUT": "51.YSMS.009859..TWCC-OUT",
            "egress_port_id_IN": "4/1",
            "egress_port_id_OUT": "1/3",
            "ingress_port_id_IN": "1/3",
            "ingress_port_id_OUT": "4/1",
            "ms_egress_port_id_IN": "4/1",
            "ms_mgmt88_service_IN": "MGMT88-IN",
            "ms_egress_port_id_OUT": "1/3",
            "ms_ingress_port_id_IN": "1/3",
            "ms_mgmt88_service_OUT": "MGMT88-OUT",
            "ms_ingress_port_id_OUT": "4/1",
        }
        """

        self.logger.info("Placeholder for RAD base config modeling")

        self.design_model = {
            "mtu": "12000",
            "name": self.device["Client Interface Description"],
            "vlan": self.svlan,
            "p_bit": self.pbit if self.pbit else "",
            # "ms_vlan": self.ms_vlan,
            # "mac_l2cp": "network" if self.device['Role'] == "MTU" else "",
            "admin_state": "Up",
            "policer_name": self.evc_ingress_bwp,
            # "operation_state": "Up",
            "service_name_IN": f"{self.circuit_id}-IN",
            "service_name_OUT": f"{self.circuit_id}-OUT",
            "egress_port_id_IN": self.network_port,
            "egress_port_id_OUT": self.client_port,
            "ingress_port_id_IN": self.client_port,
            "ingress_port_id_OUT": self.network_port,
            # "ms_egress_port_id_IN": self.network_port if "88" in self.get_ms_vlan() else "",
            # "ms_egress_port_id_OUT": self.client_port if "88" in self.get_ms_vlan() else "",
            # "ms_ingress_port_id_IN": self.client_port if "88" in self.get_ms_vlan() else "",
            # "ms_ingress_port_id_OUT": self.network_port if "88" in self.get_ms_vlan() else "",
        }

        self.base_model = {
            "FRE": self.design_model,
        }
        return self.base_model

    def generate_design_model(self):
        """
        Main function to generate the service design model
        Parameters:
            None
        Returns:
            self.service_modeler() (function): The service design model for RAD devices(calls service specific modeler)
        """
        self.logger.info(f"Adding {self.service_type} config details to base model")
        return self._generate_base_model()

    def generate_network_model(self):
        """Generates the network model for RAD devices"""
        self.logger.info("=== Generating RAD Network Model ===")
        self.classifiers = self.get_all_classifiers_for_network_model()
        self.flows = self.get_all_flows_for_network_model()
        self.port_info = self.get_port_info_for_network_model()

        self.network_config = {
            "vlan": self.get_classifier_service_vlan(),
            "service_name_IN": "",
            "ingress_port_id_IN": "",
            "egress_port_id_IN": "",
            "service_name_OUT": "",
            "ingress_port_id_OUT": "",
            "egress_port_id_OUT": "",
            "p_bit": "",
            "policer_name": "",
            # "ms_vlan": "",
            # "ms_ingress_port_id_IN": "",
            # "ms_egress_port_id_IN": "",
            # "ms_ingress_port_id_OUT": "",
            # "ms_egress_port_id_OUT": "",
            "admin_speed": self.port_info.get("rate", ""),
            "name": self.port_info["details"].get("name", ""),
            "admin_state": self.port_info["details"].get("admin", ""),
            # "operation_state": self.port_info["details"].get("oper", ""),
            "mtu": self.port_info["details"].get("mac_egressMtu", ""),
            # "mac_l2cp": self.port_info["details"].get("mac_l2cp", ""),
        }
        self.get_service_flow_values()
        self.get_all_ms_mgmt_flow_values()

        network_model = {
            "FRE": self.network_config,
        }
        return network_model

    def _get_pbit(self) -> int:
        cos = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["cosNames"][0].get("name", None)
        egress_cos = {
            "UNCLASSIFIED": 0,
            "BRONZE": 1,
            "SILVER": 3,
            "GOLD": 5,
            "PBIT-0": 0,
            "PBIT-1": 1,
            "PBIT-3": 3,
            "PBIT-5": 5,
        }
        pbit = egress_cos.get(cos)

        return pbit

    def get_ms_vlan(self):
        return "88" if "88" in self.ce_vlans or self.device["Role"] == "MTU" and self.ms_vlan else ""

    def get_all_ms_mgmt_flow_values(self):
        if "88" in self.get_ms_vlan():
            ms_mgmt_classifier_labels = self.get_ms_mgmt_classifier_labels()
            if ms_mgmt_classifier_labels:
                for label in ms_mgmt_classifier_labels:
                    self.get_ms_mgmt_flow_values(label)

    def get_ms_mgmt_classifier_labels(self) -> list:
        ms_mgmt_classifiers = []
        for classifier in self.classifiers:
            if "match vlan 88" in classifier["properties"]["match"]:
                ms_mgmt_classifiers.append(classifier["label"])
        self.logger.info(f"{self.device['Host Name']} all ms_mgmt_classifiers: {ms_mgmt_classifiers}")
        return ms_mgmt_classifiers

    def get_all_classifiers_for_network_model(self):
        classifiers = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "list-classifiers.json",
            parameters={},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} all classifiers: {json.dumps(classifiers, indent=4)}")
        return classifiers

    def get_ms_mgmt_flow_values(self, label):
        flow_direction = label.split("-")[2]
        self.network_config["ms_vlan"] = "88" if label else ""
        for flow in self.flows:
            if label in flow["properties"]["classifierProfile"]:
                self.network_config[f"ms_mgmt88_service_{flow_direction}"] = flow["label"]
                self.network_config[f"ms_ingress_port_id_{flow_direction}"] = flow["properties"]["ingressPortId"]
                self.network_config[f"ms_egress_port_id_{flow_direction}"] = flow["properties"]["egressPortId"]

    def get_all_flows_for_network_model(self):
        flows = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "list-flows.json",
            parameters={},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} all flows: {json.dumps(flows, indent=4)}")
        return flows

    def get_port_info_for_network_model(self):
        port_info = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "get-port.json",
            parameters={"type": "ethernet", "id": self.client_port},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} port info: {json.dumps(port_info, indent=4)}")
        return port_info

    def get_classifier_service_vlan(self) -> list:
        s_vlan = ""
        for classifier in self.classifiers:
            if f"CP-{self.circuit_id}-OUT" in classifier["properties"]["name"].upper():
                s_vlan = classifier["properties"]["match"][0].split(" ")[2]
        return s_vlan

    def get_service_flow_values(self):
        classifier_check_list = [
            f"CP-{self.circuit_id}-IN",
            f"CP-{self.circuit_id}-OUT",
        ]
        for flow in self.flows:
            if self.circuit_id in flow["label"] and self.circuit_id:
                for classifier in classifier_check_list:
                    flow_direction = classifier.split("-")[2]
                    if classifier in flow.get("properties", dict()).get("classifierProfile", dict()):
                        self.network_config[f"service_name_{flow_direction}"] = flow.get("label", "")
                        self.network_config[f"ingress_port_id_{flow_direction}"] = flow.get("properties", dict()).get(
                            "ingressPortId", ""
                        )
                        self.network_config[f"egress_port_id_{flow_direction}"] = flow.get("properties", dict()).get(
                            "egressPortId", ""
                        )
                        if "IN" in classifier.upper():
                            self.network_config["policer_name"] = flow.get("properties", dict()).get("policerName", "")
                            if flow["properties"].get("vlanTag"):
                                self.network_config["p_bit"] = (
                                    flow.get("properties", dict()).get("vlanTag", dict()).get("outerPbit", "")
                                )
