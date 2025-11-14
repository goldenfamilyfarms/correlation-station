import logging
import re
from thefuzz import fuzz
from typing import Tuple
from typing import Literal

from common_sense.common.errors import abort
from arda_app.common.cd_utils import granite_paths_url
from arda_app.dll.granite import (
    get_circuit_site_info,
    get_granite,
    get_network_path,
    get_path_elements,
    get_shelf_used_ports,
    put_granite,
)
from arda_app.dll.mdso import onboard_and_exe_cmd

logger = logging.getLogger(__name__)


def get_device_bw(
    speed: str, unit: str, for_path_name=False
) -> Literal[Literal["1 Gbps", "10 Gbps", "RF"], Literal["GE10", "GE1"]]:
    """Get device bandwidth. Can be used with circuit, element, and device bandwidths."""
    speed_in_gbps = float(speed)
    if unit and unit.lower() == "mbps":
        speed_in_gbps = float(speed) / 1000

    if speed_in_gbps > 1:
        return "GE10" if for_path_name else "10 Gbps"

    return "GE1" if for_path_name else "1 Gbps"


def get_shelf_names(element_name: str, vendor: str, tid: str = "") -> Tuple[str, str]:
    """
    Get shelf name and tid based on the element name and vendor.
    """
    if not tid:
        _, _, _, tid = element_name.split(".")

    # Vendor is RAD
    if vendor == "RAD":
        return f"{tid}/999.9999.999.99/NIU", tid

    # Vendor is AUDIOCODES or CRADLEPOINT
    if vendor in {"AUDIOCODES", "CRADLEPOINT"}:
        return f"{tid}/999.9999.999.99/RTR", tid

    # Vendor is ADVA or JUNIPER
    return f"{tid}/999.9999.999.99/SWT", tid


def get_path_elements_data(cid: str, side: str) -> Tuple[dict, dict]:
    """Get LVL1 and LVL2 path elements data based on cid."""
    # GET all Path Elements
    path_elements_data = get_path_elements(cid)

    # GET level 1 path elements
    lvl1 = [e for e in path_elements_data if e["LVL"] == "1"][-1 if side == "z_side" else 0]

    # GET level 2 path elements
    lvl2 = [e for e in path_elements_data if e["LVL"] == "2"][0]

    return lvl1, lvl2


def check_and_add_existing_transport(cid: str) -> None:
    path_elements_data = get_granite(f"/pathElements?CIRC_PATH_HUM_ID={cid}")

    if isinstance(path_elements_data, list):
        return

    # no elements found on cid so will search for existing transports
    circuit_path_data = get_circuit_site_info(cid)[0]
    transport_path_template = f"{circuit_path_data['Z_CLLI']}_ZW"
    elements_data = get_circuit_site_info(transport_path_template, 1)
    if isinstance(elements_data, dict):
        abort(500, "No existing transport paths found that matches the customer's site")

    # finding transport paths that match customer z side site
    existing_transport = []
    for element in elements_data:
        if element["Z_SITE_NAME"] == circuit_path_data["Z_SITE_NAME"]:
            existing_transport.append(element)

    if len(existing_transport) == 1:
        status = existing_transport[0]["CIRCUIT_STATUS"]

        if status == "Live":
            msg = f"Found existing customer transport with status of {status}, which is currently unsupported"
            logger.error(msg)
            abort(500, msg)
        else:
            # add missing path transport path
            resp = _granite_add_path_elements(cid, circuit_path_data["CIRC_PATH_INST_ID"], existing_transport[0])

            if resp.get("retString") != "Path Updated":
                msg = f"Error while adding existing transport path to {cid}"
                logger.error(msg)
                abort(500, msg)
    elif len(existing_transport) > 1:
        msg = "Multiple transport paths found that matches the customer's site"
        logger.error(msg)
        abort(500, msg)
    else:
        msg = "No existing transport paths found that matches the customer's site"
        logger.error(msg)
        abort(500, msg)


def _granite_add_path_elements(
    cid: str, circ_path_inst_id: str, path_elements_data: dict, path_elem_sequence: str = "1"
):
    granite_url = granite_paths_url()

    payload = {
        "PATH_NAME": cid,
        "PATH_REV_NBR": "1",
        "PATH_INST_ID": circ_path_inst_id,
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": path_elem_sequence,
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": path_elements_data["CIRC_PATH_INST_ID"],
        "LEG_NAME": path_elements_data["LEG_NAME"],
        "PATH_LEG_INST_ID": path_elements_data["LEG_INST_ID"],
    }
    return put_granite(granite_url, payload)


def cpe_service_check(shelf_info, cids):
    """check Granite CID data associated with the network flows data"""

    if shelf_info[1].upper() == "RAD":
        data = get_rad_flows_data(shelf_info[0])
    elif shelf_info[1].upper() == "ADVA":
        data = get_adva_flows_data(shelf_info[0], shelf_info[2])
    else:
        abort(500, f"Unsupported CPE Vendor :: {shelf_info[1].upper()}")
    try:
        result_data = data.get("result")
    except Exception:
        abort(500, f"Unable to parse network data for {shelf_info[0]}")

    cid_found = False
    # ADVA 114
    if (shelf_info[1].upper() == "ADVA") and ("114" in shelf_info[2]):
        for cid in cids:
            for flow in result_data:
                try:
                    properties_data = flow.get("properties")
                except Exception:
                    logger.info(f"Unable to find properties for flow {flow}")
                if cid in properties_data.get("epAccessFlowEVCName", ""):
                    cid_found = True
                    break
            if cid_found:
                break
        else:
            abort(500, f"Unable to find any CIDs associated with the shelf in the flows data for {shelf_info[0]}")
    # ADVA 116
    if (shelf_info[1].upper() == "ADVA") and ("116" in shelf_info[2]):
        for cid in cids:
            for flow in result_data:
                try:
                    properties_data = flow.get("properties")
                except Exception:
                    logger.info(f"Unable to find properties for flow {flow}")
                try:
                    if cid in properties_data.get("data").get("attributes").get("additionalAttributes").get(
                        "circuitName", ""
                    ):
                        cid_found = True
                        break
                except Exception:
                    logger.info(f"Unable to find properties for flow {flow}")
            if cid_found:
                break
        else:
            abort(500, f"Unable to find any CIDs associated with the shelf in the flows data for {shelf_info[0]}")
    # RAD
    if shelf_info[1].upper() == "RAD":
        for cid in cids:
            for flow in result_data:
                try:
                    properties_data = flow.get("properties")
                except Exception:
                    logger.info(f"Unable to find properties for flow {flow}")
                if cid in properties_data.get("serviceName", ""):
                    cid_found = True
                    break
            if cid_found:
                break
        else:
            abort(500, f"Unable to find any CIDs associated with the shelf in the flows data for {shelf_info[0]}")


def get_rad_flows_data(tid):
    """
    Get the network flows data for a RAD device

    Args:
        tid (str): device hostname

    Returns:
        dict: device config info of RAD device
    """
    command = "rad_flows"
    try:
        device_config = onboard_and_exe_cmd(command=command, hostname=tid, timeout=120, attempt_onboarding=False)
    except Exception:
        abort(500, f"Unable to retrieve network data for {tid} - command - {command}")
    return device_config


def get_adva_flows_data(tid, model):
    """
    Get the network flows data for an ADVA device

    Args:
        tid (str): device hostname
        model (str): model of device

    Returns:
        dict: device config info of ADVA device
    """
    try:
        command = "1g_adva_flows" if "114" in model.upper() else "10g_adva_flows"
        device_config = onboard_and_exe_cmd(command=command, hostname=tid, timeout=120, attempt_onboarding=False)
    except Exception:
        abort(500, f"Unable to retrieve network data for {tid} - command - {command}")
    return device_config


def get_zsite(cid: str):
    """
    Get the Z-side CPE site info

    Args:
        cid (str): Circuit ID

    Returns:
        dict: Z-side CPE site info (or None, None tuple)
    """
    endpoint = f"/circuitSites?CIRCUIT_NAME={cid}&WILD_CARD_FLAG=1&PATH_CLASS=P"
    try:
        granite_resp = get_granite(endpoint)
        site_info = granite_resp[0]
        if "Z_SITE_NAME" not in site_info:
            return None, None
        return site_info  # return full site info
    except (IndexError, KeyError):
        return None, None


def get_zsite_voice(cid: str):
    """
    Get Z-site voice to return all Granite site info instead of just first element
    """
    endpoint = f"/circuitSites?CIRCUIT_NAME={cid}&WILD_CARD_FLAG=1&PATH_CLASS=P"
    try:
        granite_resp = get_granite(endpoint)
        site_info = granite_resp
        return site_info
    except (IndexError, KeyError):
        return None


def get_cpe_transport_paths(device: str, z_site_info: dict) -> dict:
    """
    Get the transport paths associated with a CPE

    Args:
        device (str): hostname of CPE shelf
        z_site_info (dict): Z-side CPE site info

    Returns:
        dict: transport paths and/or services running through a CPE shelf
        shelf_dict = {
            "BFLRNYZV3ZW": [
                [
                    "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW",
                    "ADVA",
                    "FSP 150-GE114PRO-C"
                ],
                [
                    "71.L1XX.013079..CHTR",
                    "ADVA",
                    "FSP 150-GE114PRO-C"
                ]
            ]
        }
    """
    shelf_dict = {}
    device_name = device.split("/")[0]
    shelf_info = get_shelf_used_ports(z_site_info["Z_CLLI"], device_name)
    try:
        shelf_dict[device_name] = [
            [
                path.get("CURRENT_PATH_NAME") if path.get("CURRENT_PATH_NAME") else path.get("NEXT_PATH_NAME"),
                path.get("EQUIP_VENDOR"),
                path.get("EQUIP_MODEL"),
            ]
            for path in shelf_info
        ]
    except (KeyError, IndexError, AttributeError):
        if "No records" in shelf_info.get("retString"):
            shelf_dict[device_name] = None

    return shelf_dict


def get_cpe_services(shelf_dict: dict) -> tuple:
    """
    Get the services linked with a CPE

    Args:
        shelf_dict (dict): transport paths and/or services running through a CPE shelf

    Returns:
        tuple: first element is shelf hostname and second element is list of CIDs tied in with shelf
        shelf_info, cids = ("BFLRNYZV3ZW", "ADVA", "FSP 150-GE114PRO-C"), ["71.L1XX.013079..CHTR"]
    """
    # network pre-check
    shelf_info = ()
    cids = []
    # for each shelf, generate list of CIDs to search for in flows call to RAD or ADVA CPE devices
    cid_regex = r"(\d{2}\.[A-Z0-9]{4}\.\d{6}\.[A-Z0-9]{0,3}\.[TWCC|CHTR]{4})"
    cid_list = []
    cid_dict = {}
    shelf, paths = next(iter(shelf_dict.items()))
    for path_info in paths:
        # distinguish between a cid and a transport path; save only cids
        if re.findall(cid_regex, path_info[0]):
            cid_list.append(path_info[0])
            cid_dict[(shelf, path_info[1], path_info[2])] = cid_list
    logger.debug(f"cid_dict - {cid_dict}")
    # check CIDs in network flows call
    shelf_info, cids = next(iter(cid_dict.items()))

    return shelf_info, cids


def get_type2_path_elements_data(cid: str, role: str = "") -> Tuple[dict, dict]:
    """Get LVL1 and LVL2 path elements data based on cid."""
    # GET all Path Elements
    path_elements_data = get_path_elements(cid)

    # GET level 1 path elements
    lvl1 = [e for e in path_elements_data if e["LVL"] == "1" and e["ELEMENT_NAME"].endswith("ZW")][0]

    # GET level 2 path elements
    lvl2 = [e for e in path_elements_data if e["LVL"] == "2"][0]

    return lvl1, lvl2


def get_circuit_side_info(cid: str) -> dict:
    """Collect a subset of circuit data\n
    :param cid: "77.L1XX.002735..CHTR"
    :return: circuit_data: {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD"
    }
    """
    cid_data = get_network_path(cid)
    # build return dictionary with select circuit info
    circuit_data = {}
    if cid_data and isinstance(cid_data, list):
        circuit_data["cid"] = cid
        circuit_data["status"] = cid_data[0].get("status", "")
        circuit_data["aSideSiteName"] = cid_data[0].get("aSideSiteName", "")
        circuit_data["zSideSiteName"] = cid_data[0].get("zSideSiteName", "")
        return circuit_data
    else:
        msg = f"Unable to retrieve circuit data for {cid}"
        abort(500, msg)


def get_cpe_side_info(devices: dict, path_elements: list, circuit_data: dict) -> dict:
    """Retrieve ZW devices info on both sides of circuit
    :param devices: {
        "RENRNVYB1ZW": "ETH PORT 4",
        "STEDNVRR3ZW": "ETH PORT 3",
        "RENQNVLX1QW": "GE-0/0/49",
        "RENQNVLX1CW": "AE17",
        "RENQNVLX0QW": "GE-0/0/34"
    }
    :param path_elements: /pathElements response (list of dicts) (truncated example)
        [{
            "PATH_NAME": "77.L1XX.002735..CHTR",
            "A_SITE_NAME":
            "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "ELEMENT_NAME": "RENRNVYB1ZW/999.9999.999.99/NIU",
            "PORT_ACCESS_ID": "ETH PORT 4",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "TID": "RENRNVYB1ZW",
        },
        {
            "PATH_NAME": "77.L1XX.002735..CHTR",
            "A_SITE_NAME":
            "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "ELEMENT_NAME": "STEDNVRR3ZW/999.9999.999.99/NIU",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "TID": "STEDNVRR3ZW",
        }]
    :param circuit_data: {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD"
    }
    :return: cpe_per_side: {
        "a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP"),
        "z_side_cpe": ("STEDNVRR3ZW", "ETX203AX/2SFP/2UTP2SFP")
    }
    """
    cpe_per_side = {}
    a_side_site_name = circuit_data.get("aSideSiteName", "")
    z_side_site_name = circuit_data.get("zSideSiteName", "")
    # find ZW device(s)
    zw_devices = {tid: devices[tid] for tid in devices.keys() if tid.endswith("ZW")}
    # loop through each ZW device to determine which side it's on
    for tid in zw_devices:
        for elem in path_elements:
            if (
                (elem.get("TID") == tid)
                and (elem.get("PORT_ACCESS_ID") == zw_devices[tid])
                and (tid in elem.get("ELEMENT_NAME"))
                and (circuit_data.get("cid") in elem.get("PATH_NAME"))
            ):
                if elem.get("A_SITE_NAME") == z_side_site_name:
                    cpe_tid = elem.get("ELEMENT_NAME").split("/")[0]
                    cpe_per_side["z_side_cpe"] = (cpe_tid, elem.get("MODEL"))
                    break
                elif elem.get("A_SITE_NAME") == a_side_site_name:
                    cpe_tid = elem.get("ELEMENT_NAME").split("/")[0]
                    cpe_per_side["a_side_cpe"] = (cpe_tid, elem.get("MODEL"))
                    break
    if not cpe_per_side:
        msg = f"Unable to designate which side a ZW device belongs to on {circuit_data['cid']}"
        abort(500, msg)
    return cpe_per_side


def get_cpe_at_service_location(service_location_address: str, circuit_data: dict, cpe_per_side: dict) -> dict:
    """Identify the ZW device at the service location address
    :param service_location_address: "4615 ECHO AVE"
    :param circuit_data: {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD"
    :param cpe_per_side: {
        "a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP"),
        "z_side_cpe": ("STEDNVRR3ZW", "ETX203AX/2SFP/2UTP2SFP")
    }
    :return: cpe: {
        "a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP")
    }
    """
    cpe = {}
    if str(service_location_address).isspace():
        abort(500, "Undefined service location address")
    selected = None
    if service_location_address:
        a_side_site_address = circuit_data.get("aSideSiteName", "").split("/")[-1]
        z_side_site_address = circuit_data.get("zSideSiteName", "").split("/")[-1]
        a_side_ratio = fuzz.partial_ratio(service_location_address, a_side_site_address)
        z_side_ratio = fuzz.partial_ratio(service_location_address, z_side_site_address)
        match_threshold = 80
        if match_threshold <= a_side_ratio > z_side_ratio:
            selected = "a_side_cpe"
        elif match_threshold <= z_side_ratio > a_side_ratio:
            selected = "z_side_cpe"
        elif a_side_ratio < match_threshold > z_side_ratio:
            abort(500, f"Unable to determine ZW device at {service_location_address}")
        elif a_side_ratio == z_side_ratio:
            abort(500, f"Unable to distinguish which ZW device services {service_location_address}")
    if selected:
        cpe[selected] = cpe_per_side.get(selected, ())
    else:
        abort(500, "Unable to match service location address with ZW device")
    return cpe


def switch_sites_for_each_side(switch_site_info: list) -> list:
    """Switches a subset of A-side site data with corresponding Z-side site data.
       This is needed due to current BAU logic which handles only the Z-side of a disco order.
       To process the A-side of an order, we need to make it look like it's the Z-side.
    :param switch_site_info: /pathElements response (list of dicts) (truncated example)
        [{
            "A_SITE_NAME":
            "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "A_SITE_REGION": "NORTHWEST",
            "A_ADDRESS": "4615 ECHO AVE",
            "A_CITY": "RENO",
            "A_STATE": "NV",
            "A_ZIP": "89506",
            "A_COMMENTS":
            "= Inserted via REST Web Service ==  CPE: RAD 203 1.Floor: 1st  2.Suite/RM: electrical room",
            "A_CLLI": "RENRNVYB",
            "A_NPA": "775",
            "A_LONGITUDE": "-119.87078",
            "A_LATITUDE": "39.653391",
            "Z_SITE_NAME":
            "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "Z_SITE_REGION": "NORTHWEST",
            "Z_ADDRESS": "14100 LEAR BLVD",
            "Z_CITY": "STEAD",
            "Z_STATE": "NV",
            "Z_ZIP": "89506",
            "Z_CLLI": "STEDNVRR",
            "Z_NPA": "775",
            "Z_LONGITUDE": "-119.893003",
            "Z_LATITUDE": "39.642515",
        }]
    :return: switch_site_info: (list of dicts) (truncated example)
        [{
            "A_SITE_NAME":
            "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "A_SITE_REGION": "NORTHWEST",
            "A_ADDRESS": "14100 LEAR BLVD",
            "A_CITY": "STEAD",
            "A_STATE": "NV",
            "A_ZIP": "89506",
            "A_COMMENTS": "",
            "A_CLLI": "STEDNVRR",
            "A_NPA": "775",
            "A_LONGITUDE": "-119.893003",
            "A_LATITUDE": "39.642515",
            "Z_SITE_NAME":
            "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "Z_SITE_REGION": "NORTHWEST",
            "Z_ADDRESS": "4615 ECHO AVE",
            "Z_CITY": "RENO",
            "Z_STATE": "NV",
            "Z_ZIP": "89506",
            "Z_CLLI": "RENRNVYB",
            "Z_NPA": "775",
            "Z_LONGITUDE": "-119.87078",
            "Z_LATITUDE": "39.653391",
            "Z_COMMENTS":
            "= Inserted via REST Web Service ==  CPE: RAD 203 1.Floor: 1st  2.Suite/RM: electrical room",
        }]
    """
    site_keys = [
        "SITE_NAME",
        "SITE_TYPE",
        "SITE_MARKET",
        "SITE_REGION",
        "ADDRESS",
        "CITY",
        "STATE",
        "ZIP",
        "CLLI",
        "NPA",
        "LONGITUDE",
        "LATITUDE",
        "COMMENTS",
    ]
    paired = {f"A_{key}": f"Z_{key}" for key in site_keys}
    for key in paired:
        temp = switch_site_info[0].get(key, "")
        switch_site_info[0][key] = switch_site_info[0].get(paired[key], "")
        switch_site_info[0][paired[key]] = temp
    return switch_site_info


def get_vgw_shelf_info(cid: str) -> dict:
    """
    Collect data on a VGW shelf for a voice circuit

    Arg:
        cid (str): circuit ID

    Returns:
        dictionary object with VGW shelf attributes
        ex. vgw_shelf = {
                "SHELF_NAME": "WRHGOHETG1W",
                "VENDOR": "AUDIOCODES",
                "MODEL": "M500",
                "CIRC_PATH_INST_ID": "2184672"
            }
    """
    vgw_shelf = {}
    params = "&LVL=1&ELEMENT_TYPE=PORT"
    data = get_path_elements(cid, params)
    if data:
        if isinstance(data, list):
            sequence = 0
            high_sequence_element = {}
            try:
                for element in data:
                    if int(element["SEQUENCE"]) > sequence:
                        sequence = int(element["SEQUENCE"])
                        high_sequence_element = element
                vgw_shelf["SHELF_NAME"] = high_sequence_element["ELEMENT_NAME"].split("/")[0]
                vgw_shelf["VENDOR"] = high_sequence_element["VENDOR"]
                vgw_shelf["MODEL"] = high_sequence_element["MODEL"]
                vgw_shelf["CIRC_PATH_INST_ID"] = high_sequence_element["CIRC_PATH_INST_ID"]
                vgw_shelf["IPV4_ADDRESS"] = high_sequence_element["IPV4_ADDRESS"]
            except (KeyError, IndexError, AttributeError):
                msg = f"Unable to acquire VGW shelf info on {cid}"
                logger.error(msg)
                abort(500, msg)
        else:
            msg = f"Unable to acquire VGW shelf info on {cid}"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = f"Unable to acquire VGW shelf info on {cid}"
        logger.error(msg)
        abort(500, msg)

    return vgw_shelf
