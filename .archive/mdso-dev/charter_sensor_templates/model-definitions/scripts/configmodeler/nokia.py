import json
import sys
import bisect

from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.configmodeler.base import ConfigBase

sys.path.append("model-definitions")


class Nokia(ConfigBase):
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
        self.nf_resource = self.get_network_function_by_host_or_ip(self.device["FQDN"], self.device["Management IP"], require_active=True)
        if not self.nf_resource:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Cannot generate Nokia config model without active network function for device: {self.device['FQDN']}."
            )
            self.categorized_error = msg
            self.exit_error(msg)
        self.device_prid = self.nf_resource["providerResourceId"]
        self.client_port = self.device["Client Interface"].lower()
        self.network_port = self.device["Network Interface"].lower()
        self.port_type = self.get_port_role(
            self.circuit_details, self.device["Host Name"] + "-" + self.device["Client Interface"]
        )
        self.evc_id = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evcId")
        self.svlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("sVlan", "")
        self.user_label = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0].get(
            "userLabel"
        )
        self.evc_ingress_bwp = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evc-ingress-bwp")
        self.policy_id, self.qos_description, self.rate, self.cir, self.cbs = self.generate_qos_properties()
        self.core_router_mgmt_ip = self.get_core_mgmt_ip()
        self.port_properties_from_device = self.get_port_properties()
        self.sdp_properties_from_device = self.show_service_sdp()

    def _generate_base_model(self):
        design_model = {
            "customer_name": self.evc_id,
            "customer_description": self.user_label,
            "service_type": "epipe",
            "service_id": self.evc_id,
            "service_name": self.evc_id,
            "service_description": self.user_label,
            "service_mtu": self.determine_service_mtu(),
            "sap": self.client_port + ":" + self.svlan,
            "sdp": self.sdp_properties_from_device['SdpId'] + ":" + self.evc_id,
            "vlan": self.svlan,
            "qos_policy_id": self.policy_id,
            "qos_description": self.qos_description,
            "rate": self.rate,
            "cir": self.cir,
            "cbs": self.cbs,
            "port": self.client_port,
            "port_description": self.device["Client Interface Description"],
            "port_speed": self.determine_port_speed()
        }
        self.base_model = {"FRE": design_model}
        return self.base_model

    def generate_design_model(self):
        """
        Main function to generate the service design model
        Parameters:
            None
        Returns:
            self.service_modeler() (function): The service design model for Nokia devices (calls service specific modeler)
        """
        self.logger.info(f"Adding {self.service_type} config details to base model")
        base_model = self._generate_base_model()
        self.logger.info(f"DESIGN MODEL:\n{base_model}")
        return base_model

    def generate_network_model(self):
        """Generates the network model for Nokia devices"""
        self.logger.info("=== Generating Nokia Network Model ===")
        customer_properties = self.get_customer_properties()
        service_properties = self.get_service_properties()
        qos_properties = self.get_qos_properties()
        port_properties = self.port_properties_from_device
        self.network_config = {
            "customer_name": customer_properties['CustomerName'],
            "customer_description": customer_properties['CustomerDescription'],
            "service_type": service_properties['ServiceType'].lower(),
            "service_id": service_properties['ServiceID'],
            "service_name": service_properties['ServiceName'],
            "service_description": service_properties['ServiceDescription'],
            "service_mtu": service_properties['ServiceMTU'],
            "sap": service_properties['SAP'],
            "sdp": service_properties['SDP'],
            "vlan": service_properties['SAP'].split(":")[-1],
            "qos_policy_id": qos_properties['PolicyId'],
            "qos_description": qos_properties['Description'],
            "rate": qos_properties['Rate'],
            "cir": qos_properties['CIR'],
            "cbs": qos_properties['CBS'].split(" ")[0],
            "port": service_properties['SAP'].split(":")[0],
            "port_description": port_properties['Description'],
            "port_speed": port_properties['Speed']
        }
        network_model = {"FRE": self.network_config}
        return network_model

    def get_service_properties(self):
        service_info = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "show-service-id-base.json",
            parameters={'evcid': self.evc_id},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} results from show-service-id-base.json: {json.dumps(service_info, indent=4)}")
        return service_info

    def get_port_properties(self):
        port_info = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "show-port.json",
            parameters={'port': self.client_port},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} results from show-port.json: {json.dumps(port_info, indent=4)}")
        return port_info

    def get_customer_properties(self):
        customer_info = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "show-service-customer.json",
            parameters={'evcid': self.evc_id},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} results from show-service-customer.json: {json.dumps(customer_info, indent=4)}")
        return customer_info

    def get_qos_properties(self):
        policy_id = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "show-service-sap-using.json",
            parameters={'port_id': self.client_port + ":" + self.svlan},
            headers=None,
        ).json()["result"]['IngQos']
        qos_configs = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "show-qos-sap-ingress.json",
            parameters={'policy_id': policy_id},
            headers=None,
        ).json()["result"]
        self.logger.info(f"{self.device['Host Name']} results from show-qos-sap-ingress.json: {json.dumps(qos_configs, indent=4)}")
        return qos_configs

    def convert_bw_to_mb(self, bw):
        if not bw:
            return 0
        if bw.upper().endswith('G'):
            return int(bw[:-1]) * 1000
        else:
            return int(bw[:-1])

    def determine_cbs(self, bw):
        bw_value = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        cbs_value = [128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280]
        index = bisect.bisect_left(bw_value, bw)
        cbs = cbs_value[index] if index < len(bw_value) else cbs_value[-1]
        return cbs * 8 if "7210" in self.device['Model'] else cbs

    def generate_qos_properties(self):
        bw = self.convert_bw_to_mb(self.evc_ingress_bwp)
        policy_id = str(bw)
        qos_description = self.evc_ingress_bwp.upper() + " Rate Limit"
        rate = str(bw * 1000)
        cir = str(rate)
        cbs = str(self.determine_cbs(bw))
        return policy_id, qos_description, rate, cir, cbs

    def determine_service_mtu(self):
        mtu_options = [9186, 9164, 9114, 2048]
        port_mtu = int(self.port_properties_from_device['MTU']) if self.port_properties_from_device['MTU'] else 0
        sdp_mtu = int(self.sdp_properties_from_device['AdmMTU']) if self.sdp_properties_from_device['AdmMTU'] else 0
        admin_mtu = min([port_mtu, sdp_mtu])
        for mtu in mtu_options:
            if admin_mtu > mtu:
                return str(mtu)

    def get_core_mgmt_ip(self):
        """Retreives Core Router IP"""
        a_side_pe = self.circuit_details["properties"]["topology"][0]["data"]["node"][-1]
        z_side_pe = self.circuit_details["properties"]["topology"][-1]["data"]["node"][0]
        if self.device['Role'] == "PE":
            # Nokia is PE and is l2circuit neighbor of core router on the other side
            core_router = a_side_pe if self.device['location'] == "Z_SIDE" else z_side_pe
        else:
            # Nokia is CPE and core router is on the same side upstream from the device
            core_router = a_side_pe if self.device['location'] == "A_SIDE" else z_side_pe
        core_mgmt_ip = [pair["value"] for pair in core_router["name"] if pair["name"] == "Management IP"][0]
        return core_mgmt_ip

    def show_service_sdp(self):
        sdp_info = self.cutthrough.execute_ra_command_file(
            self.device_prid,
            "show-service-sdp.json",
            parameters={'ip': self.core_router_mgmt_ip},
            headers=None,
        ).json()["result"]
        return sdp_info

    def determine_port_speed(self):
        port_speed = "100 Gbps"
        if int(self.evc_ingress_bwp[:-1]) < 10:
            port_speed = "10 Gbps"
        elif self.evc_ingress_bwp.upper().endswith('M'):
            port_speed = "1 Gbps"
        return port_speed
