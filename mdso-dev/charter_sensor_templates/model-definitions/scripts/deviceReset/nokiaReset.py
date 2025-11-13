from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.serviceMapper.common import Device
from scripts.deviceReset.base import ResetBase


class NokiaReset(ResetBase):
    def __init__(
        self,
        plan,
        device_values: Device,
        circuit_id: str,
        circuit_details_id: str,
    ):
        self.plan = plan
        self.device_values = device_values
        self.circuit_id = circuit_id
        self.cutthrough = RaCutThrough()
        super().__init__(self.device_values)
        self.circuit_details = self.bpo.resources.get(circuit_details_id)
        self.bw = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evc-ingress-bwp", None)
        self.svlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("sVlan", "")
        self.evc_id = self.get_evc_id()
        self.neighbor_mgmt_ip = self.get_neighbor_mgmt_ip()
        self.sdp_id = self.get_sdp_id()["SdpId"]
        self.logger.info(f"self.sdp_id: type: {type(self.sdp_id)} return: {self.sdp_id}")
        self.service_type = self.circuit_details["properties"]["serviceType"].upper()
        self.reset_nokia()

    def reset_nokia(self):
        parameters = {}
        if self.device_values.vendor in ["NOKIA", "ALCATEL"] and self.device_values.role == "PE":
            parameters["port"] = self.device_values.handoff_port.lower()
            parameters["vlan"] = self.svlan
            parameters["evcid"] = self.evc_id
            parameters["sdp_id"] = self.sdp_id
        else:
            return
        command = "regression-delete-service"
        self.ra_cutthrough_command(parameters, command)

    def get_evc_id(self):
        evc_id = ""
        if self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evcId"):
            evc_id = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["evcId"]
        return evc_id

    def get_sdp_id(self):
        parameters = {"ip": self.neighbor_mgmt_ip}
        command = "show-service-sdp"
        device_prid = self.nf_resource["providerResourceId"]
        response = self.execute_ra_command_file(
            device_prid,
            f"{command}.json",
            parameters,
        ).json()
        return response["result"]

    def get_neighbor_mgmt_ip(self):
        """Retrieves Neighbor Router IP"""
        topology = self.circuit_details["properties"]["topology"]
        a_side_pe = topology[0]["data"]["node"][-1]
        z_side_pe = topology[-1]["data"]["node"][0]
        if self.device_values.role == "PE":
            return a_side_pe["name"][4].get("value", "") if self.device_values.location == "Z_SIDE" else z_side_pe["name"][4].get("value", "")
        return ""
