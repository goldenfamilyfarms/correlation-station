from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.serviceMapper.common import Device
from scripts.deviceReset.base import ResetBase


class JuniperReset(ResetBase):
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
        self.lan_ipv6 = self.get_ipv6()
        self.logger.info(f"self.lan_ipv6: {self.lan_ipv6}")
        self.logger.info(f"self.bw: {self.bw}")
        self.service_type = self.circuit_details["properties"]["serviceType"].upper()
        self.reset_juniper()

    def reset_juniper(self):
        parameters = {}
        if self.device_values.vendor == "JUNIPER" and self.device_values.role == "PE":
            parameters["port"] = self.device_values.handoff_port.lower()
            parameters["unit"] = self.svlan
            parameters["lan_ipv6"] = self.lan_ipv6[0] if self.lan_ipv6 else ""
        if self.device_values.vendor == "JUNIPER" and self.device_values.role == "AGG":
            parameters["port"] = self.device_values.handoff_port.lower()
            parameters["service_type"] = self.service_type
            parameters["vlan"] = self.svlan
        command = "regression-delete-service"
        self.ra_cutthrough_command(parameters, command)

    def get_ipv6(self):
        lan_ipv6 = ""
        if self.circuit_details["properties"]["service"][0]["data"].get("fia"):
            lan_ipv6 = self.circuit_details["properties"]["service"][0]["data"]["fia"][0]["endPoints"][0].get("lanIpv6Addresses", "")
        return lan_ipv6
