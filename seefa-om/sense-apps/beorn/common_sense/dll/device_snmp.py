import logging
from common.network_devices import ADVA, CIENA, CISCO, JUNIPER, RAD, SUMITOMO
from dll.snmp import snmp_get_wrapper

logger = logging.getLogger(__name__)

VENDOR_MODEL_MAP = {
    ADVA: [
        "FSP150CC-825:3.3.3",
        "FSP150-GE114PRO",
        "FSP150-XG108",
        "FSP150-XO106",
        "FSP150CC-XG116PRO",
        "FSP150CC-GE114",
        "FSP150CC-GE206",
        "FSP150CC-XG116PRO(H)",
        "FSP150-XG118PRO(SH)",
        "FSP150CC-XG120PRO",
    ],
    "ALCATEL": [
        "7210SASD",
    ],
    CIENA: [
        "5171PACKETWAVEPLATFORM",
        "CIENA3931",
    ],
    CISCO: [
        "ASR9006",
        "ASR9001",
        "ASR9010",
        "ASR920",
        "ASR9204SZA",
        "ME340X",
        "ME340012CS",
        "ME34002CS",
        "ME3600X24FSM",
        "NCS2006M6",
    ],
    JUNIPER: [
        "ACX5448",
        "EX4200-24F",
        "EX4200-24T",
        "QFX5100-96S-8Q",
        "MX240",
        "MX480",
        "MX960",
    ],
    RAD: [
        "ETX-203AX",
        "ETX-2I-10G-B-8SFPP",
        "ETX-2I-10G-LC",
        "ETX-2I-10G",
        "ETX-220A",
    ],
    SUMITOMO: [
        "FSU7100",
        "FSU7101",
        "FTE6083WALLMOUNT",
    ],
}


class DeviceSNMP:
    def __init__(
        self,
        ip_address: str,
        snmp_tokens: list,
    ):
        """Attempt to connect to the device over SNMP. It will attempt to connect with the public token by default.
        It's recommended you use the public token and then the community token."""
        self.ip_address = ip_address
        if not isinstance(snmp_tokens, list):
            snmp_tokens = [snmp_tokens]
        self.snmp_tokens = snmp_tokens

    def discover_device(self) -> dict:
        description = self.get("description")
        device = self.parse_description(description)
        if "model" in device and "vendor" not in device:
            vendor = self._get_vendor_by_model(device.get("model"))
            if vendor:
                device["vendor"] = vendor
        if "software_version" not in device:
            firmware = self.discover_firmware(device.get("vendor"), device.get("model"))
            if not firmware:
                logger.warning(f"Failed to retrieve firmware from device '{device}'")
            else:
                device["software_version"] = firmware
        return device

    def parse_description(self, description: str) -> dict:
        detectors_parsers = {
            self.etx_detector: self.etx_parser,
            self.adva_detector: self.adva_parser,
            self.juniper_detector: self.juniper_parser,
            self.cisco_detector: self.cisco_parser,
            self.asr920_detector: self.asr920_parser,
            self.packetwave_detector: self.packetwave_parser,
            self.sumitomo_detector: self.sumitomo_parser,
        }
        device_details = {}
        for detector, parser in detectors_parsers.items():
            if detector(description):
                device_details = parser(description)
        return device_details

    def get(self, key):
        object_id_mapping = {
            "name": "sysName",
            "description": "sysDescr",
            "uptime": "sysUpTime",
            "location": "sysLocation",
        }
        if key in object_id_mapping:
            return snmp_get_wrapper(self.snmp_tokens, self.ip_address, object_id_mapping.get(key))
        return

    def uptime(self):
        return snmp_get_wrapper(self.snmp_tokens, self.ip_address, "sysUpTime")

    def _get_vendor_by_model(self, model: str):
        for vendor, models in VENDOR_MODEL_MAP.items():
            if model.upper() in models:
                return vendor
        return

    def etx_detector(self, sysDescr: str) -> bool:
        return "ETX" in sysDescr

    def etx_parser(self, sysDescr: str) -> dict:
        values = sysDescr.split(" ")
        details = {
            "vendor": RAD,
            "model": values[0],
            "hardware_revision": values[2].rstrip(","),
            "software_version": values[4].rstrip(","),
        }
        return details

    def adva_detector(self, sysDescr: str) -> dict:
        return "FSP" in sysDescr

    def adva_parser(self, sysDescr: str) -> dict:
        return {"vendor": ADVA, "model": sysDescr}

    def juniper_detector(self, sysDescr: str) -> bool:
        return JUNIPER in sysDescr.upper()

    def juniper_parser(self, sysDescr: str) -> dict:
        values = sysDescr.split(",")
        details = {
            "vendor": JUNIPER,
            "model": values[1].lstrip(" Inc. ").rstrip(" Ethernet Switch").rstrip(" internal router"),
            "software_version": values[2].lstrip(" kernel "),
        }
        return details

    def cisco_detector(self, sysDescr: str) -> bool:
        return CISCO in sysDescr.upper()

    def cisco_parser(self, sysDescr: str) -> dict:
        values = sysDescr.split(",")
        details = {"vendor": CISCO}
        try:
            details.update(
                {
                    "model": values[0].lstrip("Cisco IOS XR Software (Cisco ").rstrip(")"),
                    "software_version": values[1].split("\r")[0].lstrip("  Version ").rstrip("[Default]"),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to parse sysDescr for CISCO parser '{sysDescr}' - {e}")
        return details

    def asr920_detector(self, sysDescr: str) -> bool:
        return "ASR920" in sysDescr

    def asr920_parser(self, sysDescr: str) -> dict:
        values = sysDescr.split(",")
        details = {"vendor": CISCO, "model": values[1].split(" ")[1], "software_version": values[2].lstrip("Version ")}
        return details

    def sumitomo_detector(self, sysDescr: str) -> bool:
        return SUMITOMO in sysDescr.upper()

    def sumitomo_parser(self, sysDescr: str) -> dict:
        values = sysDescr.split(",")
        details = {
            "vendor": SUMITOMO,
            "model": values[1].strip().lstrip("HWType="),
            "hardware_revision": values[2].strip().lstrip("HWVersion="),
            "software_version": values[3].strip().lstrip("FWVersion="),
        }
        return details

    def packetwave_detector(self, sysDescr: str) -> dict:
        return "Packetwave" in sysDescr

    def packetwave_parser(self, sysDescr: str) -> dict:
        return {"vendor": SUMITOMO, "model": sysDescr}

    def discover_firmware(self, vendor: str, model: str) -> str:
        vendor_u = vendor.upper()
        if vendor_u == ADVA:
            adva_firmware_obj_identifier = ".1.3.6.1.2.1.16.19.2.0"
            firmware_response = snmp_get_wrapper(adva_firmware_obj_identifier, self.ip_address, self.snmp_tokens)
            return firmware_response
        return
