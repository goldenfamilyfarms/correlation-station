import ipaddress
import logging
import re
import socket

import palantir_app

from common_sense.common.errors import abort
from common_sense.dll.hydra import HydraConnector
from common_sense.dll.snmp import snmp_get_wrapper
from palantir_app.bll.ipc import get_ip_from_tid
from palantir_app.dll.granite import call_granite_for_circuit_devices
from palantir_app.dll.denodo import denodo_get
from palantir_app.dll.granite import granite_get
from palantir_app.common.utils import get_hydra_key
from palantir_app.common.endpoints import (
    GRANITE_ELEMENTS,
    GRANITE_CIRCUIT_SITES,
    DENODO_CIRCUIT_DEVICES,
    DENODO_SPIRENT_PORT,
    DENODO_SPIRENT_VTA,
)

logger = logging.getLogger(__name__)

"""This file is not deprecated. It is still used for v3 circuit test if the service type isn't CTBH."""

CIRCUIT_ID_REGEX = r"^([A-Z0-9]){2}\.([A-Z0-9]){4}\.([A-Z0-9]){6}\..*?\..{4}$"

SRVC_TYPE = ["EPL", "EVPL", "ETHERNET", "E-ACCESS F", "EPLAN", "NNI", "UNI", "DIA", "MSS DIA", "SECURE INT"]
FIA_TYPE_SERVICE = ["DIA", "MSS DIA", "SECURE INT", "FIA", "E-ACCESS F"]
ELINE_TYPE_SERVICE = ["EPL", "EVPL", "ELINE"]


def circuit_test_model(cid, records=None, detect_active_element=False):
    # Obtain device list
    if not records:
        records = device_inventory_call(cid)
    if len(records) == 0:
        abort(404, "no record found")
    logger.debug("== device inventory call ==")
    logger.debug(records)
    element_index = 0
    if detect_active_element:
        active_index = active_element_index(records)
        logger.info("Detected active element index ")
        if active_index:
            element_index = active_index
    element = records[element_index]
    return process_circuit_test_model(cid, element)


def process_circuit_test_model(cid: str, element: dict) -> dict:
    devices = element["data"]
    if len(devices) == 0:
        abort(404, "no record found")
    # Check for supported topologies
    service_type = element["service_type"]
    if service_type not in SRVC_TYPE:
        abort(501, "Topology {} unsupported".format(service_type))

    logger.debug(f"service_type - {service_type}")

    # Identify ASide and ZSide devices
    a_side_devices = []
    z_side_devices = []
    for index, device in enumerate(devices):
        if device["split_id"]:
            a_side_devices = devices[:index]
            break
    else:
        a_side_devices = devices
    logger.debug(f"== A side devices: {a_side_devices} ==")

    rdevices = list(reversed(devices))
    for index, device in enumerate(rdevices):
        if device["split_id"]:
            z_side_devices = rdevices[:index]
            break
    if not z_side_devices:
        z_side_devices = rdevices
    logger.debug(f"== Z side devices: {z_side_devices} ==")
    statuses = devices_statuses(cid)
    cid_info = get_additional_cid_info(cid)
    region_and_market = get_region_and_market(cid_info)
    # Identify CPE and PE devices
    a_side = _get_cpe_pe(cid, a_side_devices)
    a_side_cpe = a_side["cpe"]
    if a_side_cpe:
        a_side_cpe = add_status(a_side_cpe, statuses)
    a_side_pe = a_side["pe"]
    logger.debug(f"a_side - {a_side}")
    logger.debug(f"== A side PE ==\n{a_side_pe}")
    logger.debug(f"== A side CPE ==\n{a_side_cpe}")

    z_side = _get_cpe_pe(cid, z_side_devices)
    z_side_cpe = z_side["cpe"]
    if z_side_cpe:
        z_side_cpe = add_status(z_side_cpe, statuses)
    z_side_pe = z_side["pe"]
    logger.debug(f"z_side - {z_side}")
    logger.debug("== Z side CPE ==")
    logger.debug(z_side_cpe)
    logger.debug("== Z side PE ==")
    logger.debug(z_side_pe)

    # Obtain PE details
    a_pe_details = None
    if a_side_pe:
        a_side_pe = add_status(a_side_pe, statuses)
        a_pe_details = _get_pe_details(a_side_pe)
    logger.debug("== A side PE details ==")
    logger.debug(a_pe_details)
    z_pe_details = None
    if z_side_pe:
        z_side_pe = add_status(z_side_pe, statuses)
        z_pe_details = _get_pe_details(z_side_pe)
    logger.debug("== Z side PE details ==")
    logger.debug(z_pe_details)

    a_side_qfx = a_side.get("qfx", {})
    a_qfx_details = None
    if a_side_qfx:
        a_side_qfx = add_status(a_side_qfx, statuses)
        a_qfx_details = _get_pe_details(a_side_qfx)
    logger.debug("== A side QFX details ==")
    logger.debug(a_qfx_details)
    z_side_qfx = z_side.get("qfx", {})
    z_qfx_details = None
    if z_side_qfx:
        z_side_qfx = add_status(z_side_qfx, statuses)
        z_qfx_details = _get_pe_details(z_side_qfx)
    logger.debug("== Z side QFX details ==")
    logger.debug(z_qfx_details)

    # Search for VTA and test port details
    vta_type = "vw-vta-y1564-l"
    nid_detected = False
    a_vta_details = _get_vta_and_port_info(a_side_pe, a_pe_details, vta_type)
    logger.debug(f"get vta and port info - {a_vta_details} - {a_side_qfx} - {a_qfx_details}")
    if not a_vta_details.get("vta_rid") and a_side_qfx.get("tid"):
        a_vta_details = _get_vta_and_port_info(a_side_qfx, a_qfx_details, vta_type)
    logger.debug("== A side VTA details ==")
    logger.debug(a_vta_details)
    z_vta_details = _get_vta_and_port_info(z_side_pe, z_pe_details, vta_type)
    logger.debug("== Z side VTA details ==")
    logger.debug(z_vta_details)

    # Circuit with no PEs
    if (not a_side_pe) and (not z_side_pe):
        nid_detected = True

    # ELAN circuit requirements
    elan = False
    elan_types = ["EPLAN", "NNI", "UNI"]
    if service_type in elan_types:
        elan = True
    if elan:
        _check_test_device(z_side_pe, z_pe_details)

    return _data_transformation(
        element,
        a_side_pe,
        a_side_cpe,
        a_pe_details,
        a_vta_details,
        z_side_pe,
        z_side_cpe,
        z_pe_details,
        z_vta_details,
        a_side_devices,
        z_side_devices,
        region_and_market,
        nid_detected,
        a_qfx_details,
        z_qfx_details,
    )


def check_valid_circuit_id(circuit_id):
    return re.match(CIRCUIT_ID_REGEX, circuit_id)


def device_inventory_call(cid):
    """get initial circuit details"""
    return denodo_get(DENODO_CIRCUIT_DEVICES, params={"cid": cid}, operation="spirent")["elements"]


def _tid_data_search(tid):
    """get tid information"""
    return denodo_get(f"{DENODO_SPIRENT_VTA}?pe_tid={tid}", operation="spirent")["elements"]


def _port_access_search(tid, test_circ_inst):
    """get port access id"""
    endpoint = f"{DENODO_SPIRENT_PORT}?pe_tid={tid}&test_circ_inst={test_circ_inst}"
    return denodo_get(endpoint, operation="spirent")["elements"]


def devices_statuses(cid):
    granite_resp = call_granite_for_circuit_devices(cid, GRANITE_ELEMENTS)
    logger.debug(f"GRANITE_PathElement_RESPONSE: {granite_resp}")
    return granite_resp


def get_additional_cid_info(cid):
    endpoint = f"{GRANITE_CIRCUIT_SITES}?CIRCUIT_NAME={cid}&WILD_CARD_FLAG=1&PATH_CLASS=P"
    granite_resp = granite_get(endpoint, operation="general")
    logger.debug(f"GRANITE_PathElement_RESPONSE: {granite_resp}")
    return granite_resp


def get_region_and_market(data):
    result = {}
    try:
        result["a_site_market"] = data[0].get("A_SITE_MARKET")
        result["a_site_region"] = data[0].get("A_SITE_REGION")
        result["z_site_market"] = data[0].get("Z_SITE_MARKET")
        result["z_site_region"] = data[0].get("Z_SITE_REGION")
    except (IndexError, KeyError):
        pass
    return result


def add_status(device, data):
    device["status"] = None
    path_inst_id = str(device["path_inst_id"])
    for x in data:
        if x["CIRC_PATH_INST_ID"] == path_inst_id:
            device["status"] = x["PATH_STATUS"]
            break
    return device


def _get_cpe_pe(cid: str, device_list: dict) -> dict:
    """retrieve the CPE and PE from a device list"""
    cpe = {}
    qfx = {}
    pe = {}
    cpe_not_found = True
    qfx_not_found = True
    pe_not_found = True
    path_search = ["TRANSPORT", "EPL", "EVPL"]
    if device_list:
        for device in device_list:
            if cpe_not_found:
                if device["device_role"] in ("A", "Z", "2"):
                    cpe = device
                    if ("HANDOFF" in device["path_type"]) or (device["path_name"] == cid):
                        cpe = device
                        cpe_not_found = False
            if pe_not_found:
                if device["device_role"] == "C":
                    pe = device
                    if [x for x in path_search if (x in device["path_type"])]:
                        pe = device
                        pe_not_found = False
            if qfx_not_found:  # Only used for e access fiber vta fallback.
                if device["device_role"] in ["Q"]:
                    qfx = device
                    qfx_not_found = False
            if (not cpe_not_found) and (not pe_not_found):
                break
    return {"cpe": cpe, "qfx": qfx, "pe": pe}


def _get_pe_details(pe: dict):
    """get target details on a valid PE"""
    hostname = pe.get("tid")
    if not hostname:
        return None, None
    tid_data = _tid_data_search(hostname)

    """Add Circuit OAM TESTING for Y.1564 on eligible circuits. This is required for E ACCESS Fiber circuit testing
    (DICE ELINE Service Activation Test in Visionworks)."""
    circ_path_inst_id_list = [k.get("test_circ_inst") for k in tid_data]
    env = palantir_app.app_config.USAGE_DESIGNATION
    hc = HydraConnector(
        palantir_app.url_config.HYDRA_BASE_URL, get_hydra_key(), environment="dev" if env == "STAGE" else "prd"
    )
    logger.debug(f"list - {circ_path_inst_id_list}")
    if circ_path_inst_id_list:
        circ_path_inst_id_list_str = ", ".join([str(k) for k in circ_path_inst_id_list])
        dv_circ_path_attr_settings = hc.dv_circ_path_attr_settings(
            filter=f"(circ_path_inst_id in ({circ_path_inst_id_list_str})and val_attr_inst_id=3821)"
        )
        logger.debug(f"return - {dv_circ_path_attr_settings}")
        for k in dv_circ_path_attr_settings.get("elements", {}):
            if k.get("attr_value") in ["Y.1564"]:
                for i, data in enumerate(tid_data):
                    if k.get("circ_path_inst_id") == data.get("test_circ_inst"):
                        tid_data[i].update({"Circuit_OAM_TESTING": k.get("attr_value")})
                        break

    logger.debug(f"tid_data - {tid_data}")
    keys = [
        "test_circ_inst",
        "test_tid",
        "test_fqdn",
        "test_circ_status",
        "test_equip_status",
        "test_equip_vendor",
        "test_equip_model",
        "Circuit_OAM_TESTING",
    ]
    data = []
    if not tid_data:
        return [dict.fromkeys(keys)]

    # Search each PE record with a Live status and fqdn is not NULL
    # and equipment model includes "NFX" per Spirent requirements
    # then adds each id to the tid_nfx_list
    tid_nfx_list = []
    for id, device in enumerate(tid_data):
        # conditions for a valid test circuit
        if device.get("test_circ_status", "").upper() != "LIVE":
            continue
        logger.debug(f"Test Circuit Status for PE {hostname}-{device['test_circ_inst']} is inactive")
        if device.get("test_equip_status", "").upper() != "LIVE":
            continue
        logger.debug(f"Test Equipment Status for PE {hostname}-{device['test_circ_inst']} is inactive")
        if device.get("test_fqdn", "") is None:
            continue
        logger.debug(f"Test fqdn for PE {hostname} is not found.")
        if device.get("test_equip_model", "").upper().find("NFX") == -1:
            continue
        logger.debug(f"Test Equipment Model for PE {hostname} is invalid.")
        tid_nfx_list.append(id)
    logger.debug(f"FOUND! {len(tid_nfx_list)} device(s)")
    if not tid_nfx_list:
        return [dict.fromkeys(keys)]
    # Mine data from each PE record
    for entry in tid_nfx_list:
        nfx = {}
        for key in keys:
            if key not in tid_data[entry].keys():
                nfx[key] = None
            elif key not in ("test_fqdn", "test_circ_inst", "test_equip_model", "test_equip_status"):
                nfx[key] = tid_data[entry].get(key, None)
            elif tid_data[entry][key]:
                nfx[key] = tid_data[entry].get(key, None)
            else:
                return abort(502, "Unable to determine {} for PE {}".format(key, hostname))
        data.append(nfx)
    return data


def _get_vta_and_port_info(pe, pe_details, vta_type) -> dict:
    """obtain vta mac address and test port info"""
    vta_details = {"vta_rid": None, "vta_mac_address": None, "port_access_id": None}
    if not pe_details:
        return vta_details
    for entry in pe_details:
        try:
            test_tid = entry.get("test_tid")
        except TypeError:
            test_tid = None
        # Search for MDSO resource info for VTA device
        vta_info = {"vta_rid": None, "vta_mac_address": None}
        if not test_tid:
            return vta_details
        # Retrieve the test port info
        test_port = None
        if entry.get("test_equip_model", "") != "VISIONWORKS VTP 1G":
            test_port = _port_access_search(pe.get("tid"), entry.get("test_circ_inst"))
        vta_details["vta_rid"] = vta_info["vta_rid"]
        vta_details["vta_mac_address"] = vta_info["vta_mac_address"]
        if test_port:
            vta_details["port_access_id"] = test_port[0]["pe_port_access_id"]
        if vta_details["vta_mac_address"] is not None or entry.get("Circuit_OAM_TESTING") == "Y.1564":
            break
    return vta_details


def _check_test_device(pe, pe_details):
    """check test device"""
    if not pe_details:
        abort(502, "Unable to find any PE")
    # Focus on NFX's for now
    if pe_details[0]["test_equip_model"] is None:
        return
    elif "NFX" not in pe_details[0]["test_equip_model"]:
        logger.debug("== check_test_device call ==")
        logger.debug("No valid test device (NFX) at this location - {}".format(pe["tid"]))
    elif pe_details[0]["test_circ_status"] != "Live":
        abort(502, "Test circuit status is {}, instead of Live".format(pe_details[0]["test_circ_status"]))
    elif pe_details[0]["test_equip_status"] != "Live":
        abort(
            502, "NFX {} equipment status is {}".format(pe_details[0]["test_fqdn"], pe_details[0]["test_equip_status"])
        )


def _data_transformation(
    element,
    a_side_pe,
    a_side_cpe,
    a_pe_details,
    a_vta_details,
    z_side_pe,
    z_side_cpe,
    z_pe_details,
    z_vta_details,
    a_side_devices,
    z_side_devices,
    region_and_market,
    NID,
    a_qfx_details=None,
    z_qfx_details=None,
):
    if a_qfx_details is None:
        a_qfx_details = []
    if z_qfx_details is None:
        z_qfx_details = []
    """create the data object to return"""
    record = element
    # Circuit info
    data = {
        "CustomerName": record.get("customer_id"),
        "CircuitID": record.get("cid"),
        "Bandwidth": record.get("bandwidth"),
        "ServiceLevel": record.get("cos"),
        "CustomerType": record.get("customer_type"),
        "ServiceType": record.get("service_type"),
        "Status": record.get("status"),
        "VCID": record.get("evc_id"),
    }
    if not NID:
        data["UnitType"] = None

    z_side = {
        "CustomerAddr": None if not z_side_cpe else z_side_cpe.get("full_address"),
        "Market": None if not region_and_market else region_and_market.get("z_site_market"),
        "Region": None if not region_and_market else region_and_market.get("z_site_region"),
    }
    if z_side_pe:
        pe = extract_pe(z_side_devices, z_side_pe, z_side_cpe, z_pe_details, z_vta_details, is_zside=True)
        if not pe.get("wbox") and z_qfx_details and isinstance(z_qfx_details, list):
            wbox = extract_wbox(z_qfx_details[0], z_vta_details)
            pe["WBox"] = [wbox] if (isinstance(wbox, dict) and wbox) else []
        z_side["PE"] = pe
    z_side["CPE"] = BLANK_CPE if not z_side_cpe else extract_cpe(z_side_cpe)

    # A side
    a_side = {
        "CustomerAddr": None if not a_side_cpe else a_side_cpe.get("full_address"),
        "Market": None if not region_and_market else region_and_market.get("a_site_market"),
        "Region": None if not region_and_market else region_and_market.get("a_site_region"),
    }
    if a_side_pe:
        pe = extract_pe(a_side_devices, a_side_pe, a_side_cpe, a_pe_details, a_vta_details)
        if not pe.get("wbox") and a_qfx_details and isinstance(a_qfx_details, list):
            wbox = extract_wbox(a_qfx_details[0], a_vta_details)
            pe["WBox"] = [wbox] if (isinstance(wbox, dict) and wbox) else []
        a_side["PE"] = pe
    a_side["CPE"] = BLANK_CPE if not a_side_cpe else extract_cpe(a_side_cpe)
    data.update({"ZSide": z_side, "ASide": a_side})
    return data


def active_element_index(elements: dict) -> int:
    for index, element in enumerate(elements):
        if element.get("service_type") not in SRVC_TYPE:
            continue
        if element_active(element):
            return index
    return 0


def element_active(element: dict) -> bool:
    """Detects which element of a multi element topology is active out in the wild"""
    cpe_role_list = ["A", "Z"]
    device_check = []
    for entry in list(reversed(element["data"])):
        if entry["device_role"] in cpe_role_list:
            device_check.append(entry)
            logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
            break
    for entry in element["data"]:
        if entry["device_role"] in cpe_role_list:
            device_check.append(entry)
            logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
            break
    if not device_check:
        return False
    for device in device_check:
        ip_address = device.get("management_ip", "")
        if not ip_address or isinstance(ip_address, bool) or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
            ip_address = get_cpe_ip_address(device.get("tid"))
        ip_address = ip_address.split("/")[0]
        device_info = snmp_get_wrapper(
            [palantir_app.auth_config.SNMP_COMMUNITY_STRING, palantir_app.auth_config.SNMP_PUBLIC_STRING],
            ip_address,
            "sysDescr",
        )
        if device_info and isinstance(device_info, dict) and device_info.get("model"):
            return True
    return False


def extract_pe(side_devices, side_pe, side_cpe, pe_details, vta_details, is_zside=False):
    ip_address = side_pe.get("management_ip", "").split("/")[0]
    if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
        ip_address = get_cpe_ip_address(side_pe.get("tid"))
    leg_name = side_pe.get("leg_name", "")
    if leg_name and "AE" in leg_name:
        try:
            leg_name = leg_name.split("/")[0]
            leg_name = leg_name.lower()
        except Exception as e:
            logger.error(f"Failed to extract agg port - {leg_name} - {e}")
    else:
        leg_name = ""
    pe = {
        "Status": side_pe.get("status", None),
        "Vendor": side_pe["vendor"],
        "Model": side_pe["model"],
        "Hostname": side_pe["tid"],
        "IpAddress": ip_address,
        "VLANOperation": side_pe["vlan_operation"],
        "ServiceVLANID": side_pe["svlan"],
        "TestAccessPort": (
            leg_name
            if leg_name
            else (
                vta_details.get("port_access_id")
                if not vta_details.get("port_access_id")
                else str(vta_details.get("port_access_id", "")).lower()
            )
        ),
        "Interface": (
            side_pe.get("port_access_id")
            if not side_pe.get("port_access_id")
            else side_pe.get("port_access_id", "").lower()
        ),
        "InterfaceInfo": None,
        "Description": None,
        "EVCType": None,
    }
    if side_pe["svlan"]:
        if is_zside:
            # Service is outer vlan; customer is inner vlan
            # Case where Type II ('CUST-OFFNET') circuit:
            for device in list(reversed(side_devices)):
                if device["chan_name"] and "IV-" in device["chan_name"] and "OV-" in device["chan_name"]:
                    side_pe["svlan"] = device["chan_name"]
        # Handle case where delimiter '//' separates a combined service/customer VLAN id
        if "//" in side_pe["svlan"]:
            vlan_id, side_pe["cevlan"] = side_pe["svlan"].split("//")
            if is_zside:
                if "OV-" in vlan_id:
                    vlan_id = vlan_id[(vlan_id.find("OV-") + 3) :]
                if "IV-" in side_pe["cevlan"]:
                    side_pe["cevlan"] = side_pe["cevlan"][(side_pe["cevlan"].find("IV-") + 3) :]
        else:
            # Remove all alpha characters, leave digits alone
            vlan_id = re.sub("[^0-9]", "", side_pe["svlan"])
        pe["ServiceVLANID"] = vlan_id
        if is_zside:
            pe["CustomerVLANID"] = side_pe["cevlan"]
    else:
        # If PE service vlan is null, use the CPE service vlan id
        logger.debug(" == # If PE service vlan is null, use the CPE service vlan id == ")
        if side_cpe:
            if side_cpe["svlan"]:
                pe["ServiceVLANID"] = side_cpe["svlan"]
    pe["CustomerVLANID"] = side_pe["cevlan"]
    # If PE customer vlan is null, use the CPE customer vlan id
    if not side_pe.get("cevlan") and side_cpe and side_cpe.get("cevlan"):
        pe["CustomerVLANID"] = side_cpe["cevlan"]
    pe["WBox"] = []
    if pe_details:
        wbox = extract_wbox(pe_details[0], vta_details)
        pe["WBox"] = [wbox]
    return pe


def extract_wbox(device_details: dict, vta_details) -> dict:
    logger.debug(f"Extracting wbox - {device_details} - {vta_details}")
    if device_details.get("test_equip_vendor") == "JUNIPER":
        if "VTP" not in device_details["test_equip_model"]:
            wbox = {
                "Name": device_details["test_tid"],
                "Vendor": device_details["test_equip_vendor"],
                "Model": device_details["test_equip_model"],
            }
            vta = []
            if vta_details["vta_mac_address"]:
                vta = [{"Vendor": None, "Model": None, "MacAddress": vta_details.get("vta_mac_address")}]
            wbox.update({"VTA": vta})
            logger.debug(f"wbox - {wbox}")
            return wbox
    return {}


BLANK_CPE = dict.fromkeys(
    [
        "Status",
        "Vendor",
        "Model",
        "Hostname",
        "IpAddress",
        "TestAccessPort",
        "Interface",
        "InterfaceInfo",
        "Description",
        "PortType",
        "VLANOperation",
        "ServiceVLANID",
        "CustomerVLANID",
        "EVCType",
    ]
)


def get_cpe_ip_address(tid: str) -> str:
    logger.info(f"Device tid: '{tid}'")
    try:
        ip = socket.gethostbyname(tid)
        ipaddress.ip_address(ip)
        if ip:
            return ip
    except ValueError as error:
        # IPControl can take 12-24 hours to update tid to ip mapping
        # TODO: Check that hostname in fqdn matches the tid used in the ip lookup.
        logger.warning(f"Failed to get ipaddress with tid '{tid}' Error - {error}")
        hostname = tid.split(".")[0]
        ip = get_ip_from_tid(hostname)
        logger.info(f"Ip from tid '{ip}'")
        if ip is not None:
            return ip
    except socket.gaierror as error:
        logger.warning(f"Unable to retrieve ip from tid '{tid}' Error - {error}")
        hostname = tid.split(".")[0]
        ip = get_ip_from_tid(hostname)
        logger.info(f"Ip from tid '{ip}'")
        if ip is not None:
            return ip
    except Exception:
        logger.error(f"Unknown Exception while SNMP tid '{tid}'")
        return False
    return False


def extract_cpe(side_cpe):
    if not side_cpe:
        return False
    cpe = {
        "Status": side_cpe.get("status", None),
        "Vendor": side_cpe.get("vendor"),
        "Model": side_cpe.get("model"),
        "Hostname": side_cpe.get("tid"),
        "TestAccessPort": None,
        "InterfaceInfo": None,
        "Description": None,
        "PortType": None,
        "Interface": (
            side_cpe.get("port_access_id")
            if not side_cpe.get("port_access_id")
            else str(side_cpe.get("port_access_id", "")).lower()
        ),
        "VLANOperation": side_cpe.get("vlan_operation"),
        "ServiceVLANID": side_cpe.get("svlan"),
        "EVCType": None,
    }
    ip_address = side_cpe.get("management_ip", "")
    if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
        ip_address = get_cpe_ip_address(side_cpe.get("tid"))
    if not ip_address:
        abort(502, "No management IP given for CPE: {}".format(side_cpe["tid"]))
    cpe["IpAddress"] = ip_address.split("/")[0]
    if side_cpe["svlan"]:
        # Handle case where delimiter '//' separates a combined service/customer VLAN id
        if "//" in side_cpe["svlan"]:
            vlan_id = side_cpe.get("svlan", "").split("//")[0]
            side_cpe["cevlan"] = side_cpe.get("svlan", "").split("//")[1]
        else:
            # Remove all alpha characters, leave digits alone
            vlan_id = re.sub("[^0-9]", "", side_cpe["svlan"])
        cpe["ServiceVLANID"] = vlan_id
    cpe["CustomerVLANID"] = side_cpe["cevlan"]
    return cpe
