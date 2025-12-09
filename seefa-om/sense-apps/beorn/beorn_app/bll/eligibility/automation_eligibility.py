import logging
import re

from copy import deepcopy

from beorn_app.bll import snmp
from beorn_app.bll.eligibility.provisioning import new_provisioning, change_provisioning
from beorn_app.bll.eligibility.compliance import new_compliance, change_compliance, disco_compliance
from beorn_app.bll.topologies import TopologyUtils
from beorn_app.bll.eligibility import mdso_eligible
from beorn_app.common.utils import anthropomorphize_the_camel, flatten_list
from common_sense.common.errors import abort, granite_msg, MISSING_DATA

logger = logging.getLogger(__name__)


class DeviceEligibility:
    VERIFY_EQUIPMENT_STATUS = ["VIDEO"]

    def __init__(self, topology):
        self.topology = topology
        self.supported_vendors = []
        self.supported_models = []
        self.supported_port_roles = {}
        self.service_type = topology["serviceType"]
        self.utils = TopologyUtils()
        self.linked_interfaces = self.utils.get_linked_interfaces(topology)
        self.topology_devices = self.utils.get_topology_devices(topology, self.linked_interfaces)
        self.unsupported_equipment = {}

    def check_devices(self):
        for device in self.topology_devices:
            # we don't need to do remaining checks if we hit one that is not supported, move on to the next device
            if not self._is_supported_vendor(device["vendor"]):
                self._update_unsupported_equipment(device, "vendor", additional_data=self.service_type)
                continue
            if not self._is_supported_model(device["model"]):
                self._update_unsupported_equipment(device, "model", additional_data=self.service_type)
                continue
            if not self._is_supported_port_role(device["portRole"], device["vendor"], device["model"]):
                generalized_device = self._generalize_device(device["vendor"], device["model"])
                self._update_unsupported_equipment(
                    device, "portRole", additional_data=f"{self.service_type} {device['vendor']} {generalized_device}"
                )
                continue
            if not self._is_supported_equipment_status(device["deviceRole"], device["equipmentStatus"]):
                self._update_unsupported_equipment(
                    device, "equipmentStatus", additional_data=f"{device['deviceRole']} - {self.service_type}"
                )
                continue
            if not self._is_valid_fqdn(device["fqdn"], device["hostName"]):
                self._update_unsupported_equipment(device, "fqdn", additional_data=device["hostName"])
                continue
            unsupported_lag, lag_data = self._is_unsupported_lag(device["hostName"])
            if unsupported_lag:
                logger.debug(f"CID: {self.topology['serviceName']} Invalid Lag Link: {lag_data}")
                self._update_unsupported_equipment(device, "portRole", additional_data="Invalid Lag Link")

    def _is_supported_vendor(self, vendor):
        logger.debug(f"Checking vendor: {vendor}")
        if vendor not in self.supported_vendors:
            return False
        return True

    def _is_supported_model(self, model):
        logger.debug(f"Checking model: {model}")

        if model not in self.supported_models:
            return False
        return True

    def _is_supported_port_role(self, port_role, vendor, model):
        logger.debug(f"Checking port role: {port_role} on {model}")
        if not self.supported_port_roles:
            # no port roles supported for this service type on this device in this workstream
            return False
        model = self._generalize_model(vendor, model)
        if port_role not in self.supported_port_roles.get(model, []):
            logger.debug(f"{port_role} not supported on {vendor} {model} device for {self.service_type}")
            return False
        return True

    def _generalize_model(self, vendor, device_model):
        for model in mdso_eligible.DEVICES[vendor]:
            if device_model in mdso_eligible.DEVICES[vendor][model]:
                return model
        return device_model

    def _generalize_device(self, vendor, model):
        # special request generalizations for reporting
        if vendor == "JUNIPER":
            for generalized_model, models in mdso_eligible.DEVICES["JUNIPER"].items():
                if model in models:
                    return generalized_model
        if vendor == "ALCATEL":
            return "ALU"
        if model in mdso_eligible.CISCO_9K_MODELS:
            return "9K"
        return model

    def _is_supported_equipment_status(self, device_role, equipment_status):
        if self.service_type not in self.VERIFY_EQUIPMENT_STATUS:
            return True
        device_statuses = {"VIDEO": {"live_status_required": ["PE", "AGG"], "live_status_unsupported": ["CPE", "MTU"]}}
        live_status_required = device_statuses[self.service_type]["live_status_required"]
        live_status_unsupported = device_statuses[self.service_type]["live_status_unsupported"]
        if device_role in live_status_required and equipment_status != "LIVE":
            return False
        if device_role in live_status_unsupported and equipment_status == "LIVE":
            return False
        return True

    def _is_valid_fqdn(self, fqdn, host_name):
        if not fqdn or not host_name:
            return False
        fqdn_host_name = fqdn.split(".")[0]
        if fqdn_host_name != host_name:
            return False
        return True

    def _is_unsupported_lag(self, host_name):
        if not self.linked_interfaces:
            return False, ""
        for link in self.linked_interfaces:  # link "MILZWIFT1CW-XE-9/0/11_MILZWIFT1CW-XE-9/0/10
            if host_name in link:
                break
        first_linked_tid = link.split("_")[0].split("-")[0]
        second_linked_tid = link.split("_")[1].split("-")[0]
        if first_linked_tid == second_linked_tid:
            return True, link
        return False, ""

    def _update_unsupported_equipment(self, device, unsupported_element, additional_data=None):
        if self.unsupported_equipment.get(device["hostName"]):
            self.unsupported_equipment[device["hostName"]]["details"]["ports"].append(
                {"name": device["name"], "portRole": device["portRole"]}
            )
        else:
            self.unsupported_equipment[device["hostName"]] = {
                "reason": {
                    "category": anthropomorphize_the_camel(unsupported_element),
                    unsupported_element: device[unsupported_element],
                    "message": build_message(
                        "device", device[unsupported_element], additional_data, translate_for_humans=unsupported_element
                    ),
                },
                "details": {
                    "serviceType": self.service_type,
                    "vendor": device["vendor"],
                    "model": device["model"],
                    "role": device["deviceRole"],
                    "ports": [{"name": device["name"], "portRole": device["portRole"]}],
                },
            }


def build_message(message_type, reason, additional_data=None, translate_for_humans=""):
    human_friendly = {"equipmentStatus": f"Status {reason}", "fqdn": f"FQDN TID Mismatch -- {reason}"}
    if human_friendly.get(translate_for_humans):
        message = f"Automation Unsupported: {human_friendly[translate_for_humans]}"
        if additional_data:
            message += f" - {additional_data}"
        return message

    message = "Automation Unsupported: "
    if additional_data and message_type == "service":
        message += f"{additional_data} -"
    message += f" {reason}"
    if additional_data and message_type == "device":
        message += f" - {additional_data}"
    return message


class ServiceEligibility:
    UNI_VLAN = "0"
    SUPPORTED_UNI_VLAN_MODELS = mdso_eligible.JUNIPER_MX_MODELS

    def __init__(self, circuit_elements):
        self.utils = TopologyUtils()
        self.circuit_data = self.utils.get_circuit_data(circuit_elements)
        self.consolidated_data = self.utils.consolidate_clouds(self.circuit_data["data"])
        self.service_type = circuit_elements[0]["service_type_full"]
        if "CTBH" in self.service_type:
            self.service_type = "CTBH 4G"
        self._set_service_attributes()
        self.eligible_products = "No service type products instantiated"
        self.unsupported_service = {}

    def _set_service_attributes(self):
        # set all service nuances as booly attributes
        self.bgp_fia = self._is_bgp_fia()
        self.vlan_swapping = self._is_swap_operation()
        self.cevlan = self._is_cevlan()
        self.trunked = self._is_trunked_service()
        self.multiple_vlans = self._are_multiple_vlans()
        self.inner_outer_vlan_swap = self._is_inner_outer_vlan_swap()
        self.legacy_vpls_vlan_id = None

    def _is_bgp_fia(self):
        return True if self.circuit_data["cust_bgp_asn"] else False

    def _is_swap_operation(self):
        for element in self.circuit_data["data"]:
            if element["vlan_operation"] == "SWAP":
                return True
        return False

    def _is_cevlan(self):
        for element in self.circuit_data["data"]:
            if element["cevlan"] and element["cevlan"] != element["svlan"]:
                return True
        return False

    def _are_multiple_vlans(self):
        # isolate valid equipment
        equipment = [data for data in self.circuit_data["data"] if data.get("eq_type") in mdso_eligible.EQUIPMENT_TYPES]
        # isolate unique vlan id(s) from channel name
        vlans_from_channel = self._get_vlans_from_channel(equipment)
        # isolate unique vlan id(s) from svlan
        vlans_from_svlan = self._get_svlans(equipment)
        # invalid multiple vlans if more than one vlan id exists in channel names or svlans
        if len(vlans_from_channel) > 1 or len(vlans_from_svlan) > 1:
            return True
        # invalid multiple vlans if vlans from channel names differ from vlans from svlans
        if vlans_from_channel == vlans_from_svlan:
            return False
        # router handoffs will not have any channel names, should only have 1 svlan
        if len(vlans_from_channel) == 0 and len(vlans_from_svlan) == 1:
            return False
        return True

    def _get_vlans_from_channel(self, equipment):
        return {
            data["chan_name"][4:].split("-")[0]
            for data in equipment
            if data["chan_name"]
            and data["chan_name"][:4].upper() == "VLAN"
            and data["chan_name"][4:].split("-")[0].isnumeric()
        }

    def _get_svlans(self, equipment):
        svlans = []
        for data in equipment:
            if data["svlan"]:
                svlans.append({"svlan": data["svlan"], "model": data["model"]})
        exclude_supported_uni_vlans = deepcopy(svlans)
        for data in svlans:
            if data["svlan"] == self.UNI_VLAN and data["model"] in self.SUPPORTED_UNI_VLAN_MODELS:
                exclude_supported_uni_vlans.remove(data)
        return {data["svlan"] for data in exclude_supported_uni_vlans}

    def _is_inner_outer_vlan_swap(self):
        inner_outer_pattern = r"(\d{5}:)?OV-\d{2,4}\/\/IV-\d{2,4}"
        if bool(re.search(inner_outer_pattern, str(self.consolidated_data))):
            logger.debug("Inner/Outer VLAN Swap Occurs in Circuit")
            return True
        return False

    def set_legacy_vpls_vlan_id(self, vpls_vlan_id):
        if vpls_vlan_id == "0":
            self.legacy_vpls_vlan_id = True
        else:
            self.legacy_vpls_vlan_id = False

    def check_service_type(self):
        if not self._is_supported_service_type():
            service_type = self._generalize_service_type()
            self._update_unsupported_service(service_type, additional_data="Service Type")

    def _is_supported_service_type(self):
        is_supported = True
        if self.service_type not in self.eligible_products:
            is_supported = False
        return is_supported

    def _is_trunked_service(self):
        if self.service_type in mdso_eligible.TRUNKED_SERVICES:
            return True

    def _generalize_service_type(self):
        generalized_service_type = self.service_type.replace("CAR-", "")
        generalized_service_type = generalized_service_type.replace("COM-", "")
        return generalized_service_type

    def check_service_attributes(self):
        if self.bgp_fia:
            self._update_unsupported_service("BGP")
        if self.vlan_swapping:
            self._update_unsupported_service("VLAN swap operation")
        if self.cevlan and self.service_type not in mdso_eligible.CEVLAN_SERVICES:
            self._update_unsupported_service("CEVLAN")
        if self.multiple_vlans:
            self._update_unsupported_service("Multiple VLANs Designed")
        if self.legacy_vpls_vlan_id:
            self._update_unsupported_service("VPLS VLAN ID None (legacy)")

    def _update_unsupported_service(self, reason, additional_data=None):
        if self.unsupported_service.get("reason"):
            self.unsupported_service["reason"]["additionalUnsupported"] = reason
        else:
            self.unsupported_service = {
                "reason": {"service": reason, "message": build_message("service", reason, additional_data)},
                "details": {"serviceType": self.service_type},
            }

    def check_inner_outer_vlan(self):
        if self.inner_outer_vlan_swap:
            self._update_unsupported_service("Inner/Outer Vlan Swap")

    def check_vpls_vlan_id(self, vpls_vlan_id):
        if not vpls_vlan_id:
            msg = granite_msg(MISSING_DATA, "VPLS VLAN ID", "not populated")
            self._update_unsupported_service(msg)

    def check_for_locally_switched(self, evcid):
        if evcid == "LOCALLY SWITCHED":
            self._update_unsupported_service("Locally Switched Circuit")


class Eligibility:
    # eligibility is comprised of service eligibility and device eligibility
    def __init__(self, topology, circuit_elements):
        self.service_type = topology["serviceType"]
        self.device_eligibility = DeviceEligibility(topology)
        self.service_eligibility = ServiceEligibility(circuit_elements)
        if self.service_type == "ELAN":
            self.service_eligibility.set_legacy_vpls_vlan_id(topology["service"][0]["data"]["evc"][0]["vplsVlanId"])
        self.unsupported_elements = {}
        logger.debug(f"Evaluating eligibility for {self.device_eligibility.topology['serviceName']}")

    def check_automation_eligibility(self):
        # validate service and service attributes are supported
        self.service_eligibility.check_service_type()
        self.service_eligibility.check_service_attributes()
        if self.service_eligibility.unsupported_service:
            self.unsupported_elements["unsupportedService"] = self.service_eligibility.unsupported_service
        # validate all topology devices are supported
        self.device_eligibility.check_devices()
        if self.device_eligibility.unsupported_equipment:
            self.unsupported_elements["unsupportedEquipment"] = self.device_eligibility.unsupported_equipment
        if self.unsupported_elements:
            return {"eligible": False, "data": self.unsupported_elements}, 418
        return {"eligible": True, "data": {}}, 200


class Provisioning(Eligibility):
    def __init__(self, topology, circuit_elements):
        super().__init__(topology, circuit_elements)
        self.service_eligibility.eligible_products = mdso_eligible.PROVISIONING_SERVICES
        if self.service_type == "FIA" and not getattr(self, "_skip_colo_check", False):
            self._check_for_unsupported_colo(topology)
        if self.service_type == "ELAN":
            self.service_eligibility.check_vpls_vlan_id(topology["service"][0]["data"]["evc"][0]["vplsVlanId"])
        if self.service_type == "ELINE":
            self.service_eligibility.check_for_locally_switched(topology["service"][0]["data"]["evc"][0]["evcId"])
        supported_devices = self._get_supported_devices()
        if supported_devices:
            self.device_eligibility.supported_vendors = supported_devices.VENDORS
            self.device_eligibility.supported_models = flatten_list(supported_devices.MODELS)
            self.device_eligibility.supported_port_roles = supported_devices.PORT_ROLES

    def _check_for_unsupported_colo(self, topology):
        forbidden_devices = ["SNJUCACL1CW"]
        for device in forbidden_devices:
            if device in str(topology):
                abort(502, f"Unsupported COLO : {device}", summary="MDSO | Automation Unsupported | Unsupported COLO")

    def _get_supported_devices(self):
        supported_devices = {
            "CTBH 4G": new_provisioning.CTBH,
            "ELAN": new_provisioning.ELAN,
            "ELINE": new_provisioning.ELINE,
            "FIA": new_provisioning.FIA,
            "NNI": new_provisioning.NNI,
            "VIDEO": new_provisioning.VIDEO,
            "VOICE": new_provisioning.VOICE,
        }
        if not supported_devices.get(self.service_type):
            return
        return supported_devices[self.service_type]()


class ProvisioningChange(Provisioning):
    def __init__(self, topology, circuit_elements):
        self._skip_colo_check = True
        super().__init__(topology, circuit_elements)
        supported_devices = self._get_supported_devices()
        if supported_devices:
            self.device_eligibility.supported_vendors = supported_devices.VENDORS
            self.device_eligibility.supported_models = flatten_list(supported_devices.MODELS)
            self.device_eligibility.supported_port_roles = supported_devices.PORT_ROLES

    def _get_supported_devices(self):
        supported = {
            "CTBH 4G": change_provisioning.CTBH,
            "ELAN": change_provisioning.ELAN,
            "ELINE": change_provisioning.ELINE,
            "FIA": change_provisioning.FIA,
            "VIDEO": change_provisioning.VIDEO,
            "VOICE": change_provisioning.VOICE,
        }
        if not supported.get(self.service_type):
            return
        return supported[self.service_type]()

    def _check_for_unsupported_colo(self, topology):
        return


class ComplianceNew(Eligibility):
    def __init__(self, topology, circuit_elements):
        super().__init__(topology, circuit_elements)
        self.service_eligibility.eligible_products = mdso_eligible.NEW_COMPLIANCE_SERVICES
        self.service_eligibility.check_inner_outer_vlan()
        if self.service_type == "ELAN":
            self.service_eligibility.check_vpls_vlan_id(topology["service"][0]["data"]["evc"][0]["vplsVlanId"])
        supported_devices = self._get_supported_devices()
        if supported_devices:
            self.device_eligibility.supported_vendors = supported_devices.VENDORS
            self.device_eligibility.supported_models = flatten_list(supported_devices.MODELS)
            self.device_eligibility.supported_port_roles = supported_devices.PORT_ROLES

    def _get_supported_devices(self):
        supported = {
            "CTBH 4G": new_compliance.CTBH,
            "ELAN": new_compliance.ELAN,
            "ELINE": new_compliance.ELINE,
            "FIA": new_compliance.FIA,
            "NNI": new_compliance.NNI,
            "VOICE": new_compliance.VOICE,
        }
        if not supported.get(self.service_type):
            return
        return supported[self.service_type]()


class ComplianceChange(Eligibility):
    def __init__(self, topology, circuit_elements):
        super().__init__(topology, circuit_elements)
        self.service_eligibility.eligible_products = mdso_eligible.MAC_COMPLIANCE_SERVICES
        self.service_eligibility.check_inner_outer_vlan()
        supported_devices = self._get_supported_devices()
        if supported_devices:
            self.device_eligibility.supported_vendors = supported_devices.VENDORS
            self.device_eligibility.supported_models = flatten_list(supported_devices.MODELS)
            self.device_eligibility.supported_port_roles = supported_devices.PORT_ROLES

    def _get_supported_devices(self):
        supported = {
            "CTBH 4G": change_compliance.CTBH,
            "ELAN": change_compliance.ELAN,
            "ELINE": change_compliance.ELINE,
            "FIA": change_compliance.FIA,
            "VOICE": change_compliance.VOICE,
        }
        if not supported.get(self.service_type):
            return
        return supported[self.service_type]()


class ComplianceDisconnect(Eligibility):
    def __init__(self, topology, circuit_elements):
        super().__init__(topology, circuit_elements)
        self.service_eligibility.eligible_products = mdso_eligible.DISCONNECT_COMPLIANCE_SERVICES
        self.service_eligibility.check_inner_outer_vlan()
        if self.service_type == "ELAN":
            self.service_eligibility.check_vpls_vlan_id(topology["service"][0]["data"]["evc"][0]["vplsVlanId"])
        if self.service_type == "ELINE":
            self.service_eligibility.check_for_locally_switched(topology["service"][0]["data"]["evc"][0]["evcId"])
        supported_devices = self._get_supported_devices()
        if supported_devices:
            self.device_eligibility.supported_vendors = supported_devices.VENDORS
            self.device_eligibility.supported_models = flatten_list(supported_devices.MODELS)
            self.device_eligibility.supported_port_roles = supported_devices.PORT_ROLES

    def _get_supported_devices(self):
        supported = {
            "ELINE": disco_compliance.ELINE,
            "FIA": disco_compliance.FIA,
            "VOICE": disco_compliance.VOICE,
            "ELAN": disco_compliance.ELAN,
        }
        if not supported.get(self.service_type):
            return
        return supported[self.service_type]()


def cpe_swap_eligibility(cpe_model):
    """verify installed device is swappable with arda endpoint"""
    if cpe_model not in snmp.GRANITE_MODEL_MAP.values():
        abort(
            502,
            f"CPE Swap Process Error: Installed device {cpe_model} \
                is not eligible for shelf swap",
        )
