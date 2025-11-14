from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.serviceMapper.common import Device
from scripts.deviceReset.base import ResetBase


class AdvaReset(ResetBase):
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
        self.reset_adva()

    def reset_adva(self):
        if self.device_values.model in self.device_values.netconf_devicelist:
            self.reset_adva_pro()
        else:
            self.reset_adva_114()

    def reset_adva_114(self):
        parameters = {}
        if self.device_values.vendor == "ADVA" and self.device_values.role == "MTU":
            return
        elif self.device_values.vendor == "ADVA" and self.device_values.role == "CPE":
            parameters["port"] = self.device_values.handoff_port[-1]
        command = "regression-delete-service"
        self.ra_cutthrough_command(parameters, command)

    def reset_adva_pro(self):
        parameters = {}
        flowpoint_id_client, flowpoint_id_network, mp_id = self.get_all_flow_related_ids()
        parameters["client_port"] = self.device_values.handoff_port[-1]
        parameters["network_port"] = self.device_values.network_port[-1]
        parameters["flowpoint_id_client"] = flowpoint_id_client
        parameters["flowpoint_id_network"] = flowpoint_id_network
        parameters["mp_id"] = mp_id
        self.logger.info(f"mp-flow and flowpoint parameters: {parameters}")
        command = "regression-delete-service"
        self.ra_cutthrough_command(parameters, command)

    def get_all_flow_related_ids(self):
        parameters = {"client_port": self.device_values.handoff_port[-1], "network_port": self.device_values.network_port[-1]}
        # TODO create new command that looks for both inner, outer flows and mp flows
        # TODO need to add this find all flow related ids to the ge/120 folder in the ra as well
        command = "find_all_flow_related_ids"
        response = self.ra_cutthrough_command(parameters, command)
        self.logger.info(f'client port: {self.device_values.handoff_port[-1]}')
        self.logger.info(f'network port: {self.device_values.network_port[-1]}')
        self.logger.info(f"netconf_find_flowpoints response: {response}")
        flowpoint_id_client = self.get_flowpoint_id(self.device_values.handoff_port[-1], response)
        flowpoint_id_network = self.get_flowpoint_id(self.device_values.network_port[-1], response)
        mp_id = self.get_mp_flow_id(response)
        return flowpoint_id_client, flowpoint_id_network, mp_id

    def get_flowpoint_id(self, port, response):
        ethernet_ports = response["result"]["data"]["sub-network"]["network-element"]["shelf"]["slot"]["card"]["ethernet-card"]["ethernet-port"]
        for ethernet_port in ethernet_ports:
            if ethernet_port["port-id"] == port:
                # if isinstance(ethernet_port["flowpoint"], list):
                if isinstance(ethernet_port.get("flowpoint"), list):
                    return self._find_flowpoint_id_if_in_list(ethernet_port)
                else:
                    return self._find_flowpoint_id_if_not_in_list(ethernet_port)
        return ""

    def _find_flowpoint_id_if_in_list(self, ethernet_port):
        for flowpoint in ethernet_port.get("flowpoint"):
            if self.circuit_id in flowpoint["alias"]:
                return flowpoint["flowpoint-id"]
        return ""

    def _find_flowpoint_id_if_not_in_list(self, ethernet_port):
        if ethernet_port.get("flowpoint"):
            if self.circuit_id in ethernet_port["flowpoint"].get("alias"):
                return ethernet_port["flowpoint"]["flowpoint-id"]
        return ""

    def get_mp_flow_id(self, response):
        mp_flows = response["result"]["data"]["sub-network"]["network-element"]["mp-flow"]
        if isinstance(mp_flows, list):
            for mp_flow in mp_flows:
                if self.circuit_id in mp_flow["circuit-name"]:
                    return mp_flow["mp-flow-id"]
        elif self.circuit_id in mp_flows.get("circuit-name", ""):
            return mp_flows["mp-flow-id"]
        return ""
