from scripts.common_plan import CommonPlan


class Device(CommonPlan):
    def __init__(self, device, disconnect_type=None):
        self.details = self.get_device_details(device)
        self.netconf_devicelist = ["FSP 150-XG116PRO", "FSP 150-XG116PROH", "FSP 150-XG118PRO (SH)", "FSP 150-XG120PRO"]
        self.required_remediation = {}
        self.tid = self.details["Host Name"]
        self.vendor = self.details["Vendor"]
        self.model = self.details["Model"]
        self.role = self.details["Role"]
        self.network_port = self.details["Network Interface"]
        self.handoff_port = self.details["Client Interface"]
        self.handoff_port_description = self.details["Client Interface Description"]
        self.client_neighbor = self.details["Client Neighbor"]
        self.handoff_port_type = self.get_port_service_type()
        self.equipment_status = self.details["Equipment Status"]
        self.fqdn = self.details["FQDN"]
        self.port_role = self.details["Node Edge Point"]["Role"]
        self.port_check_required = False
        self.management_ip = self.details["Management IP"]
        self.location = self.details["location"]
        if disconnect_type:
            self.port_check_required = self.is_port_check_required(disconnect_type)
        self.adva_pro = True if self.model in self.netconf_devicelist else False

    def get_port_service_type(self) -> str:
        """
        Determine if port service type is virtual (EVP-UNI) or private (EP-UNI)
        :return: str service_type EP-UNI or EVP-UNI
        :rtype: str
        """
        port_type_descriptions = []
        try:
            # most naming standards define port type after the first : in description
            port_type_descriptions.append(self.handoff_port.split(":")[1])
            # except CPE facing, which is defined before the first :
            port_type_descriptions.append(self.handoff_port.split(":")[0])
        except IndexError:
            # this means the interface is incorrectly configured
            # defaults to EVP-UNI to avoid breaking anything existing
            pass
        return "EP-UNI" if "EP-UNI" in port_type_descriptions else "EVP-UNI"

    def get_device_details(self, device: dict) -> dict:
        spoke_list = self.get_device_details_from_circuit_details_device(device)
        device_edge_point_details = device["ownedNodeEdgePoint"][-1]["name"]
        spoke_list["Node Edge Point"] = {detail["name"]: detail["value"] for detail in device_edge_point_details}
        self.logger.info(f"Device Details {spoke_list}")
        return spoke_list

    def is_port_check_required(self, disconnect_type: str) -> bool:
        # ENNI not checked at port level
        if self.is_port_role_enni():
            return False
        if disconnect_type == "FULL":
            # CPE facing port should be cleared
            if self.is_downstream_device_cpe():
                return True
            # if no CPE, core handoff port should be cleared
            if self.is_core_handoff_device():
                return True
        else:
            # CPE handoff port should be cleared
            if self.is_cpe_handoff_device():
                return True
        return False

    def is_port_role_enni(self):
        return self.port_role == "ENNI"

    def is_downstream_device_cpe(self):
        return self.client_neighbor[-2:] in ["ZW", "WW", "XW", "YW"]

    def is_core_handoff_device(self):
        return self.client_neighbor == "None" and self.role != "CPE"

    def is_cpe_handoff_device(self):
        return self.client_neighbor == "None" and self.role == "CPE"
