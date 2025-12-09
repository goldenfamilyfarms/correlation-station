import json
import logging
import pysnmp
import re
import traceback

from beorn_app.common.generic import ADVA, CIENA, CISCO, JUNIPER, RAD, SUMITOMO
from beorn_app.dll.snmp import snmp_get, get_system_info
from beorn_app.bll.eset import get_device_data_from_eset_ui

logger = logging.getLogger(__name__)


VENDOR_MODEL_MAP = {
    ADVA: [
        "FSP150CC-825:3.3.3",
        "FSP 150-GE114PRO",
        "FSP 150-XG108",
        "FSP 150-XO106",
        "FSP150CC-XG116PRO",
        "FSP150CC-GE114",
        "FSP150CC-GE206",
        "FSP150CC-XG116PRO (H)",
        "FSP150-XG118PRO (SH)",
        "FSP150CC-XG120PRO",
    ],
    "ALCATEL": ["7210SASD"],
    CIENA: ["5171 PACKETWAVE PLATFORM", "CIENA3931"],
    CISCO: [
        "ASR 9006",
        "ASR 9001",
        "ASR 9010",
        "ASR920",
        "ASR9204SZA",
        "ME340X",
        "ME340012CS",
        "ME34002CS",
        "ME3600X24FSM",
        "NCS2006M6",
    ],
    JUNIPER: ["ACX5448", "EX4200-24F", "EX4200-24T", "QFX5100-96S-8Q", "MX240", "MX480", "MX960"],
    RAD: [
        "ETX-203AX",
        "ETX-203AX/N",
        "ETX-2I-10G-B-8SFPP",
        "ETX-2I-10G-LC",
        "ETX-2I-10G",
        "ETX-220A",
        "ETX-220A-4XFP-10X1G",
    ],
    SUMITOMO: ["FSU7100", "FSU7101", "FTE6083WALLMOUNT"],
}


GRANITE_MODEL_MAP = {
    "FSP 150-GE114Pro": "FSP 150-GE114PRO-C",
    "FSP150CC-GE114": "FSP 150-GE114PRO-C",
    "FSP150CC-XG116PRO": "FSP 150-XG116PRO",
    "ETX-203AX": "ETX203AX/2SFP/2UTP2SFP",
    "ETX-2i-10G-B-8SFPP": "ETX-2I-10G-B/8.5/8SFPP",
    "FSP150CC-XG116PRO (H)": "FSP 150-XG116PROH",
    "FSP150CC-XG120PRO": "FSP 150-XG120PRO",
    "ETX-220A": "ETX-220A",
    "ETX-2I-10G-LC": "ETX-2I-10G/4SFPP/4SFP4UTP",
    "ETX-2I-10G": "ETX-2I-10G/4SFPP/24SFP",
    "FSP 150-XG108": "FSP 150-XG108",
}


def _get_vendor_by_model(model: str) -> str:
    for vendor, models in VENDOR_MODEL_MAP.items():
        if model.upper() in models:
            return vendor
    else:
        logger.warning(f"Cannot find vendor for model '{model}'")


def _convert_snmp_model_to_granite_model(model):
    return GRANITE_MODEL_MAP.get(model, model)


def _isolate_model(model):
    specialized_model_finders = {
        "ETX": _rad_etx_model_finder,
        JUNIPER: _juniper_model_regex,
        CISCO: _cisco_model_regex,
        "ASR920": _cisco_model_regex,
        SUMITOMO: _sumitomo_model_regex,
    }
    for trigger in specialized_model_finders:
        if trigger in model.upper():
            return specialized_model_finders[trigger](model)
    return model


def isolate_firmware(snmp_response, vendor):
    firmware_regex = {ADVA: adva_firmware_finder, RAD: rad_firmware_finder, SUMITOMO: sumitomo_firmware_finder}
    return firmware_regex[vendor.upper()](snmp_response)


def _rad_etx_model_finder(model):
    return model.split(" ")[0] if "ETX" in model else model


def _juniper_model_regex(model):
    # hunt for MX, EX, QFX
    juniper_model = re.search(r"(m|e|q)(f|x)\S*", model)
    return juniper_model[0].upper() if juniper_model else model


def _cisco_model_regex(model):
    # hunt for cisco models
    cisco_model = re.search(r"(ME)(\S*)", model)
    logger.debug(f"Cisco model {cisco_model}")
    if cisco_model:
        return cisco_model[0].upper()
    cisco_model = re.search(r"(ASR)\s(\S*)", model)
    logger.debug(f"Cisco model {cisco_model}")
    if cisco_model:
        return cisco_model[0].upper()
    logger.debug(f"Cisco model {model}")
    cisco_model = re.search(r"Cisco IOS Software, (\w+) Software", model)
    logger.debug(cisco_model)
    if cisco_model:
        return cisco_model.group(1).upper()
    return model


def _sumitomo_model_regex(model):
    # hunt for sumitomo models
    sumitomo_model = re.search(r"(?<=HWType=)[0-Z]*", model)
    logger.debug(f"Sumitomo model {sumitomo_model}")
    return sumitomo_model[0].upper() if sumitomo_model else model


def adva_firmware_finder(snmp_response):
    return snmp_response


def rad_firmware_finder(snmp_response):
    juniper_firmware = snmp_response.split(" Sw: ")[-1]
    return juniper_firmware


def sumitomo_firmware_finder(snmp_response):
    sumitomo_firmware = re.search(r"(?<=FWVersion=)[.-Z]*", snmp_response)
    logger.debug(f"Sumitomo model {sumitomo_firmware}")
    return sumitomo_firmware[0].upper() if sumitomo_firmware else False


def get_model(ip, best_effort=False, public=False):
    model = snmp_get(ip, "sysDescr", best_effort=best_effort, public=public)
    if not model:
        return None

    model = _isolate_model(model)
    return model


def get_firmware(ip: str, vendor=None, best_effort=True, public=False):
    try:
        obj_indentifier = {ADVA: ".1.3.6.1.2.1.16.19.2.0", RAD: "sysDescr"}
        obj_id = obj_indentifier[vendor.upper()]
        logger.info(f"Object Identifier '{obj_id}'")
        firmware = snmp_get(ip, obj_id, best_effort=best_effort, public=public)
        if not firmware or firmware.upper() == "NONE":
            logger.warning(f"Firmware not received for IP '{ip}' Obj Identifier '{obj_id}'")
            obj_attempt = obj_indentifier
            obj_attempt.pop(vendor)
            for obj_id in obj_attempt.values():
                logger.info(f"Attempting firmware retrieval. IP '{ip}' Vendor '{vendor}' Object Identifier '{obj_id}'")
                firmware = snmp_get(ip, obj_id, best_effort=best_effort)
                if firmware:
                    break
        logger.info(f"Firmware '{firmware}' for IP '{ip}'")
        if not firmware:
            logger.warning(f"No firmware returned on IP '{ip}' | Make '{vendor}'")
            return
        elif isinstance(firmware, dict):
            logger.warning(
                f"Error getting firmware on IP '{ip} | Make '{vendor}'" + f" | Message '{firmware.get('message')}'"
            )
            return
        firmware = isolate_firmware(firmware, vendor)
        logger.info(f"Isolated Firmware '{firmware}'")
    except pysnmp.error.PySnmpError:
        logger.warning(f"Hostname '{ip}' is not reachable")
        return
    except json.decoder.JSONDecodeError as e:
        print(traceback.format_exc())
        logger.warning(f"bad ipv4/udp transport address - Exception {e}'")
        return
    except Exception as e:
        print(traceback.format_exc())
        logger.error(
            f"Failed to get firmware version from Device IP '{ip}' Make '{vendor}' "
            + f"Model '{vendor}' - Exception {e}"
        )
        return
    return firmware


def get_device_vendor_and_model(ip, best_effort=False, return_ise_values=False, public=False):
    snmp_isolated_model = get_model(ip, best_effort, public=public)
    if not snmp_isolated_model:
        return {"vendor": None, "model": None}

    ui_vendor, ui_model, ise_model, ise_role = None, None, None, None
    eset_device_data_response = get_device_data_from_eset_ui(snmp_isolated_model, best_effort=True)

    if eset_device_data_response and eset_device_data_response.get("data"):
        device_date_from_eset_ui = eset_device_data_response["data"][0]
        ui_vendor, ui_model = device_date_from_eset_ui.get("snmp_vendor"), device_date_from_eset_ui.get("granite_model")
        ise_model, ise_role = device_date_from_eset_ui.get("ise_model"), device_date_from_eset_ui.get("role_access_type")

    vendor = ui_vendor if ui_vendor else _get_vendor_by_model(snmp_isolated_model)
    model = ui_model if ui_model else _convert_snmp_model_to_granite_model(snmp_isolated_model)
    ise_model = ise_model if ise_model else model

    if not return_ise_values:
        return {"vendor": vendor, "model": model}
    else:
        return {"vendor": vendor, "model": ise_model, "role": ise_role}


def get_snmp_system_info(device_id):
    system_info = get_system_info(device_id)
    model = _isolate_model(system_info[1])
    return {
        "name": system_info[0],
        "vendor": _get_vendor_by_model(model),
        "model": model,
        "uptime": system_info[2],
        "location": system_info[3],
    }


def get_snmp_data_by_oid_or_symbolic_name(device_id, object_id):
    data = snmp_get(device_id, object_id)
    return {"data": data}


def normalize_firmware(firmware: str, last_call=False) -> list:
    if isinstance(firmware, int):
        return [firmware]
    firmware = firmware.strip()
    firmware = re.sub(r"[(\-]", " ", firmware)
    firmware = re.sub(r"[\)\+]", "", firmware)
    firmware = re.sub(r"B", "0.", firmware)  # 6.4.0(B86) in the chalk documentation is treated as 6.4.0(0.86)
    firmware = firmware.split(" ")
    vendor_version = [int(n) for n in firmware[0].strip().split(".")]
    if len(firmware) > 1 and not last_call:
        vendor_version.append(normalize_firmware(firmware[1], last_call=True))
    return vendor_version


def compare_version(firmware: list, minimum: list, last_call=False):
    logger.info(f"Compare Version Firmware '{firmware}' Minimum '{minimum}'")
    if not isinstance(firmware, list):
        firmware = normalize_firmware(firmware)
    if not isinstance(minimum, list):
        minimum = normalize_firmware(minimum)
    # logger.info("Compare Vendor Version")
    for i in range(min(len(minimum), len(firmware))):
        if isinstance(firmware[i], list) or isinstance(minimum[i], list):
            return compare_version(firmware[i], minimum[i], last_call=True)
        if firmware[i] > minimum[i]:
            logger.info(f"Eligible firmware '{firmware}' > minimum '{minimum}'")
            return "GREATER"
        elif firmware[i] < minimum[i]:
            logger.warning(f"Ineligible firmware '{firmware}' < minimum '{minimum}'")
            return "LESSER"
    # Check last element of firmware version. Assume longer version is greater. Might break RAD.
    logger.debug(f"Checking last version segment firmware '{firmware}' minimum '{minimum}'")
    if len(firmware) < len(minimum):
        logger.warning(f"Ineligible firmware '{firmware}' < minimum '{minimum}'")
        return "LESSER"
    elif len(firmware) > len(minimum):
        logger.info(f"Eligible firmware '{firmware}' > minimum '{minimum}'")
        return "GREATER"
    else:
        logger.info(f"Version match firmware '{firmware}' == minimum '{minimum}'")
        return "EQUALS"
