from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.serviceMapper.common import Device
from scripts.deviceReset.base import ResetBase


class RadReset(ResetBase):
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
        self.logger.info(f"self.bw: {self.bw}")
        self.service_type = self.circuit_details["properties"]["serviceType"].upper()
        self.reset_rad()

    def reset_rad(self):
        parameters = {}
        self.logger.info(f"(1)self.device_tid = {self.device_values.tid}")
        self.logger.info(f"(2)self.device_values.vendor = {self.device_values.vendor}")
        self.logger.info(f"(3)self.device_values.role = {self.device_values.role}")
        if self.device_values.vendor == "RAD" and self.device_values.role == "MTU":
            return
        elif self.device_values.vendor == "RAD" and self.device_values.role == "CPE":
            parameters["port"] = self.device_values.handoff_port.split("-")[1]
            parameters["cid"] = self.circuit_id
            parameters["bw"] = self.bw
        command = "regression-delete-service"
        self.ra_cutthrough_command(parameters, command)
