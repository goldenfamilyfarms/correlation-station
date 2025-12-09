import ipaddress
import logging
import re
import socket

from common_sense.common.errors import abort
from palantir_app.bll import circuit_test
from palantir_app.bll.ipc import get_ip_from_tid
from palantir_app.dll.denodo import denodo_get
from palantir_app.dll.granite import call_granite_for_circuit_devices, granite_get
from palantir_app.common.endpoints import (
    GRANITE_ELEMENTS,
    GRANITE_CIRCUIT_SITES,
    DENODO_SPIRENT_VTA,
    DENODO_SPIRENT_PORT,
)

logger = logging.getLogger(__name__)


VTA_TYPE = "vw-vta-y1564-l"
BLANK_CPE = {
    "Vendor": None,
    "Model": None,
    "Hostname": None,
    "TestAccessPort": None,
    "Interface": None,
    "InterfaceInfo": None,
    "Description": None,
    "PortType": None,
    "VLANOperation": None,
    "ServiceVLANID": None,
    "CustomerVLANID": None,
    "EVCType": None,
}


def circuit_test_model_v3(cid):
    # Obtain devices from CID
    records = circuit_test.device_inventory_call(cid)
    if not records:
        abort(404, "no record found")
    logger.debug(f"{records = }")

    if "CTBH" in records[0]["service_type"]:
        return _ctbh_model(cid, records)

    return circuit_test.circuit_test_model(cid, records)


def _ctbh_model(cid, records):
    filtered_records = _filter_records_by_status(records)
    if not filtered_records:
        abort(404, "no live or design records were found")

    circuit_devices = _get_circuit_devices(cid)
    circuit_sites = _get_circuit_sites(cid)

    ctbh_model = {
        "CustomerName": filtered_records[0]["customer_id"],
        "CircuitID": cid,
        "Bandwidth": filtered_records[0]["bandwidth"],
        "ServiceLevel": filtered_records[0]["cos"],
        "Status": filtered_records[0]["status"],
        "Legs": [],
    }

    for num, record in enumerate(filtered_records):
        devices = record["data"]
        if not devices:
            abort(404, "no record found")

        # Identify A Side and Z Side devices
        a_side_devices = _get_single_side_devices(devices)
        logger.debug(f"{a_side_devices = }")

        reversed_devices = list(reversed(devices))
        z_side_devices = _get_single_side_devices(reversed_devices)
        logger.debug(f"{z_side_devices = }")

        # Get CPE and PE devices, obtain NFX details from PE
        a_side_cpe = _get_cpe_device(a_side_devices, circuit_devices, is_ctbh=True)
        logger.debug(f"{a_side_cpe = }")

        a_side_pe = _get_pe_device(a_side_devices, circuit_devices, is_ctbh=True)
        logger.debug(f"{a_side_pe = }")

        a_nfx_details = None
        if a_side_pe:
            a_nfx_details = _get_feasible_nfx_details(a_side_pe)
        logger.debug("== A side PE details ==")
        logger.debug(a_nfx_details)

        z_side_cpe = _get_cpe_device(z_side_devices, circuit_devices, is_ctbh=True)
        logger.debug(f"{z_side_cpe = }")

        z_side_pe = _get_pe_device(z_side_devices, circuit_devices, is_ctbh=True)
        logger.debug(f"{z_side_pe = }")

        z_nfx_details = None
        if z_side_pe:
            z_nfx_details = _get_feasible_nfx_details(z_side_pe)
        logger.debug("== Z side PE details ==")
        logger.debug(z_nfx_details)

        service_type = record["service_type"]
        logger.debug(f"{service_type = }")
        validate_nfx = _is_nfx_validation_required(service_type)
        if validate_nfx:
            # TODO fix me! we already check this in feasible nfx available,
            # but need to fall out if none is available for some circumstances only?
            _check_nfx_feasibility(z_side_pe, z_nfx_details)

        # add test port details
        if a_nfx_details:
            a_vta_details = _get_base_spirent_vta_details(a_side_pe, a_nfx_details)
        else:
            a_vta_details = {}
        if z_nfx_details:
            z_vta_details = _get_base_spirent_vta_details(z_side_pe, z_nfx_details)
        else:
            z_vta_details = {}

        # NID
        nid = _is_nid_circuit(a_side_pe, z_side_pe)
        if not nid:
            ctbh_model["UnitType"] = None

        for site in circuit_sites:
            if site["LEG_INST_ID"] == str(record["leg_inst_id"]):
                break

        a_side_data = _combine_side_data(a_side_pe, a_side_cpe, a_nfx_details, a_vta_details, a_side_devices)
        z_side_data = _combine_side_data(z_side_pe, z_side_cpe, z_nfx_details, z_vta_details, z_side_devices)

        data = _build_leg_data(num, record, a_side_data, z_side_data)
        ctbh_model["Legs"].append(data)

    return ctbh_model


def _filter_records_by_status(records):
    live_records = []
    designed_records = []
    # if there live records
    for record in records:
        status = record.get("status")
        if isinstance(status, str) and status.lower() == "live":
            live_records.append(record)
            continue
        if isinstance(status, str) and status.lower() == "designed":
            designed_records.append(record)
    if live_records:
        return live_records

    # if no live records - choose designed records or return empty list
    return designed_records


def _get_circuit_devices(cid):
    granite_resp = call_granite_for_circuit_devices(cid, GRANITE_ELEMENTS)
    logger.debug(f"GRANITE_PathElement_RESPONSE: {granite_resp}")
    return granite_resp


def _get_circuit_sites(cid: str) -> dict:
    # TODO: Circuit test v4 that I borrowed this from did not have th wild card flag but the original did.
    endpoint = f"{GRANITE_CIRCUIT_SITES}?CIRCUIT_NAME={cid}&WILD_CARD_FLAG=1&WILD_CARD_FLAG=1&PATH_CLASS=P"
    granite_resp = granite_get(endpoint, operation="general")
    logger.debug(f"GRANITE_PathElement_RESPONSE: {granite_resp}")
    return granite_resp


def _get_single_side_devices(devices):
    side_devices = []
    for index, device in enumerate(devices):
        topology = device.get("topology", "")
        if device["split_id"] or "CLOUD" in topology.upper():
            side_devices = devices[:index]
            break
    if not side_devices:
        side_devices = split_on_cloud(devices)
    if not side_devices:
        side_devices = split_on_pe(devices)
    if not side_devices:
        side_devices = devices
        logger.warning("Unable to find any indication of side index. Using outer bounds.")
    return side_devices


def split_on_cloud(devices):
    for index, device in enumerate(devices):
        topology = device.get("topology", "")
        if not topology:
            continue
        if (
            topology.upper() == "POINT TO POINT"
            and not device.get("model")
            and not device.get("tid")
            and not device.get("chan_name")
        ):
            return devices[:index]


def split_on_pe(devices):
    found_pe = False
    for index, device in enumerate(devices):
        device_role = device.get("device_role", "")
        if not device_role:
            tid = device.get("tid", "")
            if not tid or len(tid) < 4:
                continue
            device_role = tid[-2]
        if device_role and isinstance(device_role, str):
            device_role = device_role.upper()
        if device_role == "C" and not found_pe:
            found_pe = device.get("tid")
        if device.get("eq_type") == "ROUTER" and not found_pe:
            found_pe = device.get("tid")
        elif found_pe and device.get("tid") != found_pe:
            return devices[:index]


def _get_cpe_device(devices, circuit_devices, is_ctbh: bool = False):
    cpe = {}
    for device in devices:
        # because of the order of devices, the first with TID is the CPE
        tid = device.get("tid")
        if not tid and not isinstance(tid, str):
            continue
        else:
            tid = tid.split("-")[0]  # Strip out suffix e.x. PEWTWICI2TW-ESR02
        if tid and tid[-1] == "W" and (not is_ctbh or tid[-3] == "7"):
            cpe = device
            break
        if is_ctbh and tid and tid[-2:] == "TW":
            logger.debug(f"Detected CTBH PE - {tid}")
            break
        if tid and tid[-2] == "C" and device["site_type"] == "HUB":
            logger.debug(f"Detected PE - {tid}")
            break
        if tid[-1] == "W" and (tid[-2] in ["2", "A", "Z"]):
            cpe = device
            break
    if cpe:
        cpe = _add_status(cpe, circuit_devices)
    return cpe


def _add_status(device, circuit_devices):
    device["status"] = None
    path_inst_id = str(device["path_inst_id"])
    for x in circuit_devices:
        if str(x["CIRC_PATH_INST_ID"]) == path_inst_id:
            logger.debug(f"Found Inst_Id match {path_inst_id}")
            device["status"] = x["PATH_STATUS"]
            break
    return device


def _get_pe_device(devices, circuit_devices, is_ctbh: bool = False) -> dict:
    logger.debug("Get PE - Device devices")  # '{devices}' circuit_devices '{circuit_devices}'")
    pe = None
    for device in devices:
        tid = device.get("tid")
        if not tid and not isinstance(tid, str):
            continue
        else:
            tid = tid.split("-")[0]  # Strip out suffix e.x. PEWTWICI2TW-ESR02
        if is_ctbh:
            if tid and tid[-2:] == "TW":
                logger.debug(f"Detected CTBH PE - {tid}")
                pe = device
                break
        if tid[-2] == "C" and (is_ctbh or device.get("site_type") == "HUB"):
            logger.debug(f"Detected PE - {tid}")
            pe = device
            break
    if not pe:
        for device in devices:
            if device.get("eq_type") == "ROUTER":
                pe = device
                break
    if pe:
        logger.debug(f"Found PE Adding status - PE '{pe}'")
        pe = _add_status(pe, circuit_devices)
    return pe


def _get_feasible_nfx_details(pe) -> list[dict]:
    """get target details on a valid PE"""
    logger.debug(f"Get Feasible NFX Details PE - '{pe}'")
    hostname = pe.get("tid")
    if not hostname:
        return []

    required_properties = ["test_fqdn", "test_circ_inst", "test_equip_model", "test_equip_status"]
    optional_properties = ["test_tid", "test_equip_vendor", "test_circ_status"]

    tid = hostname if "-" not in hostname else hostname.split("-")[0]
    vta_data = _get_vta_from_pe(tid)
    if not vta_data:
        logger.debug("No VTA Data")
        return []

    pe_nfx_indexes = []
    for i, testing_details in enumerate(vta_data):
        if _is_feasible_nfx_available(testing_details, tid):
            pe_nfx_indexes.append(i)
    logger.debug(f"FOUND! {len(pe_nfx_indexes)} device(s)")
    if not pe_nfx_indexes:
        logger.debug("No PE NFX Indices")
        return []

    # Mine data from each PE record
    feasible_nfx_data = []
    for tid_nfx_index in pe_nfx_indexes:
        nfx = {}
        for required_property in required_properties:
            vta_property = vta_data[tid_nfx_index].get(required_property, None)
            if not vta_property:
                return abort(502, f"Unable to determine {required_property} for PE {hostname}")
            nfx[required_property] = vta_property
        for optional_property in optional_properties:
            nfx[optional_property] = vta_data[tid_nfx_index].get(optional_property)
        feasible_nfx_data.append(nfx)
    return feasible_nfx_data


def _get_vta_from_pe(tid):
    """
    get vta information
    vta example {
        "name":"dv_spirent_vta_lookup"
        "elements":[
            {
                "test_circ_inst":2175025,
                "test_circ_id":"31001.GE10.CHCGILDT4CW.CHCGILDTS6W",
                "test_circ_status":"Live",
                "test_equip_inst":1558393,
                "pe_tid":"CHCGILDT4CW",
                "test_tid":"CHCGILDTS6W",
                "test_fqdn":"CHCGILDTS6W.CHTRSE.COM",
                "test_ip":"10.10.148.3/24",
                "test_equip_status":"Live",
                "test_equip_vendor":"JUNIPER",
                "test_equip_model":"NFX250-S1"},
            {
                "test_circ_inst":2175027,
                "test_circ_id":"31001.GE1.CHCGILDT4CW.CHCGILDTS6W",
                "test_circ_status":"Live",
                "test_equip_inst":1558393,
                "pe_tid":"CHCGILDT4CW",
                "test_tid":"CHCGILDTS6W",
                "test_fqdn":"CHCGILDTS6W.CHTRSE.COM",
                "test_ip":"10.10.148.3/24",
                "test_equip_status":"Live",
                "test_equip_vendor":"JUNIPER",
                "test_equip_model":"NFX250-S1"
            }
        ]
    }
    no vta example: {"name":"dv_spirent_vta_lookup","elements":[]}
    """
    if "-" in tid:
        logger.warning(f"Extended Tid Used to request vta data {tid}")
    endpoint = f"{DENODO_SPIRENT_VTA}?pe_tid={tid}"
    return denodo_get(endpoint)["elements"]


def _is_feasible_nfx_available(testing_details: dict, hostname: str) -> bool:
    # Spirent requirements: PE with Live test circuit + test equip status, FQDN is not NULL,
    # and NFX model for E-Access Fiber
    if testing_details["test_circ_status"].upper() != "LIVE":
        logger.debug(f"Test Circuit Status for PE {hostname}-{testing_details['test_circ_inst']} is inactive")
        return False
    if testing_details["test_equip_status"].upper() != "LIVE":
        logger.debug(f"Test Equipment Status for PE {hostname}-{testing_details['test_circ_inst']} is inactive")
        return False
    if not testing_details["test_fqdn"]:
        logger.debug(f"Test fqdn for PE {hostname} is not found.")
        return False
    if not testing_details:
        logger.debug("No testing details found")
        return False
    return True


def _get_base_spirent_vta_details(pe, nfx_details):
    """build base details model and obtain spirent test port info"""
    # TODO should we remove vta rid and mac addres since we aren't getting that anywhere?
    vta_details = {}

    if not nfx_details:
        logger.warning("Could not extract vta mac address and test port info")
        return vta_details

    for detail in nfx_details:
        if detail.get("test_tid"):
            # Retrieve the test port info
            if detail["test_equip_model"] != "VISIONWORKS VTP 1G":
                test_port = _get_spirent_port(pe.get("tid").split("-")[0], detail["test_circ_inst"])
                if test_port:
                    vta_details["port_access_id"] = test_port[0]["pe_port_access_id"]

    if test_tid := detail.get("test_tid"):
        wbox_test_port = _get_spirent_port(test_tid, detail["test_circ_inst"])
        if wbox_test_port:
            vta_details["wbox_port_access_id"] = wbox_test_port[0]["pe_port_access_id"]
    logger.debug(f"vta_details - {vta_details}")
    return vta_details


def _get_spirent_port(tid, test_circ_inst):
    """get port access id"""
    endpoint = f"{DENODO_SPIRENT_PORT}?pe_tid={tid}&test_circ_inst={test_circ_inst}"
    return denodo_get(endpoint, operation="spirent")["elements"]


def _is_nid_circuit(a_side_pe, z_side_pe):
    # Circuit with no PEs
    if (not a_side_pe) and (not z_side_pe):
        return True
    return False


def _is_nfx_validation_required(service_type):
    validation_required = ["EPLAN", "NNI", "UNI"]  # TODO what??
    if service_type in validation_required:
        return True
    return False


def _check_nfx_feasibility(pe, nfx_details):
    """check test device"""
    # TODO why hardcode to 0 index instead of checking if any are feasible?
    if not nfx_details:
        abort(502, description="Unable to find any PE")
    if not nfx_details[0]["test_equip_model"]:
        return
    if "NFX" not in nfx_details[0]["test_equip_model"]:
        logger.debug("== check_test_device call ==")
        logger.debug(f"No valid test device (NFX) at this location - {pe['tid']}")
        return
    if nfx_details[0]["test_circ_status"] != "Live":
        abort(502, f"Test circuit status is {nfx_details[0]['test_circ_status']}, instead of Live")
    if nfx_details[0]["test_equip_status"] != "Live":
        abort(502, f"NFX {nfx_details[0]['test_fqdn']} equipment status is {nfx_details[0]['test_equip_status']}")


def _combine_side_data(pe, cpe, nfx_details, vta_details, devices):
    return {"pe": pe, "cpe": cpe, "nfx": nfx_details, "vta": vta_details, "devices": devices}


def _build_leg_data(num, record, a_side_data, z_side_data):
    data = {}

    svlan = ""
    for side in (a_side_data["pe"], a_side_data["cpe"], z_side_data["pe"], z_side_data["cpe"]):
        if side and side.get("svlan"):
            svlan = side["svlan"]

    data["LegName"] = f"{record.get('cid')}-{svlan}"
    data["VCID"] = None
    if record["evc_id"]:
        data["VCID"] = record["evc_id"].split(",")[num]

    # Z side
    z_side = {"CustomerAddr": None}
    if z_side_data.get("pe"):
        z_side["PE"] = _build_pe_data(z_side_data, is_z_side=True)
        if z_side_data.get("cpe"):
            z_side["CustomerAddr"] = z_side_data["cpe"]["full_address"]
    if z_side_cpe := z_side_data.get("cpe"):
        z_side["CPE"] = _build_cpe_data(z_side_cpe)
    # A side
    a_side = {"CustomerAddr": None}  # TODO you are missing the customer address
    if a_side_data.get("pe"):
        a_side["PE"] = _build_pe_data(a_side_data)
        if a_side_data.get("cpe"):
            a_side["CustomerAddr"] = a_side_data["cpe"].get("full_address")
    if a_side_cpe := a_side_data.get("cpe"):
        a_side["CPE"] = _build_cpe_data(a_side_cpe)
    data.update({"ZSide": z_side, "ASide": a_side})
    return data


def _build_pe_data(side_data, is_z_side=False):
    test_access_port = None if not side_data.get("vta") else side_data["vta"].get("port_access_id", "").lower()
    wbox_test_access_port = None if not side_data.get("vta") else side_data["vta"].get("wbox_port_access_id", "").lower()
    pe = {
        "Vendor": side_data["pe"]["vendor"],
        "Model": side_data["pe"]["model"],
        "Hostname": side_data["pe"]["tid"],
        "IpAddress": _get_ip_address(side_data),
        "VLANOperation": side_data["pe"]["vlan_operation"],
        "ServiceVLANID": side_data["pe"]["svlan"],
        "TestAccessPort": test_access_port,
        "WBoxTestAccessPort": wbox_test_access_port,
        "Interface": side_data["pe"].get("port_access_id", "").lower(),
        "InterfaceInfo": None,
        "Description": None,
    }
    if is_z_side:
        pe["EVCType"] = None
        _update_type_2_svlan(side_data)  # not all are type 2, but if they are they need normalizing

    if side_data["pe"]["svlan"]:
        _update_svlan(side_data, pe, is_z_side)
        if is_z_side:
            pe["CustomerVLANID"] = side_data["pe"]["cevlan"]
    else:
        # If PE service vlan is null, use the CPE service vlan id
        _update_with_cpe_svlan(side_data, pe)
    pe["CustomerVLANID"] = side_data["pe"]["cevlan"]
    # If PE customer vlan is null, use the CPE customer vlan id
    if not side_data["pe"]["cevlan"] and side_data.get("cpe") and side_data["cpe"].get("cevlan"):
        pe["CustomerVLANID"] = side_data["cpe"]["cevlan"]

    pe["WBox"] = _get_white_box_data(side_data)

    return pe


def _get_ip_address(side_data):
    ip_address = side_data["pe"].get("management_ip", "").split("/")[0]
    if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
        ip_address = _get_cpe_ip_address(side_data["pe"].get("tid"))
    return ip_address


def _get_cpe_ip_address(tid):
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
        return _get_ip_from_ipc(tid)
    except socket.gaierror as error:
        logger.warning(f"Unable to retrieve ip from tid '{tid}' Error - {error}")
        return _get_ip_from_ipc(tid)
    except Exception:
        logger.error(f"Unknown Exception while SNMP tid '{tid}'")
        return


def _get_ip_from_ipc(tid):
    hostname = tid.split(".")[0]
    ip = get_ip_from_tid(hostname)
    logger.info(f"Ip from tid '{ip}'")
    if ip:
        return ip


def _update_type_2_svlan(side_data):
    # Service is outer vlan; customer is inner vlan
    # Case where Type II ('CUST-OFFNET') circuit:
    for device in list(reversed(side_data["devices"])):
        if device["chan_name"] and "IV-" in device["chan_name"] and "OV-" in device["chan_name"]:
            side_data["pe"]["svlan"] = device["chan_name"]


def _update_svlan(side_data, pe, is_z_side):
    # Handle case where delimiter '//' separates a combined service/customer VLAN id
    if "//" in side_data["pe"]["svlan"]:
        vlan_id, side_data["pe"]["cevlan"] = side_data["pe"]["svlan"].split("//")
        if is_z_side:
            if "OV-" in vlan_id:
                vlan_id = vlan_id[vlan_id.find("OV-") + 3 :]
            if "IV-" in side_data["pe"]["cevlan"]:
                side_data["pe"]["cevlan"] = side_data["pe"]["cevlan"][side_data["pe"]["cevlan"].find("IV-") + 3 :]
    else:
        # Remove all alpha characters, leave digits alone
        vlan_id = re.sub("[^0-9]", "", side_data["pe"]["svlan"])
    pe["ServiceVLANID"] = vlan_id


def _update_with_cpe_svlan(side_data, pe):
    cpe = side_data.get("cpe")
    if not cpe:
        return False
    logger.debug(" == # If PE service vlan is null, use the CPE service vlan id == ")
    if side_data["cpe"] and side_data["cpe"]["svlan"]:
        pe["ServiceVLANID"] = side_data["cpe"]["svlan"]
    return True


def _get_white_box_data(side_data) -> list:
    if not side_data.get("nfx"):
        # no test circuit data found on PE
        return []

    first_nfx = side_data["nfx"][0]
    if "VTP" in first_nfx.get("test_equip_model"):
        # invalid model
        return []

    white_box = {
        "Name": first_nfx.get("test_tid"),
        "Vendor": first_nfx.get("test_equip_vendor"),
        "Model": first_nfx.get("test_equip_model"),
        "VTA": _add_vta_details(side_data),
    }

    return [white_box]


def _add_vta_details(side_data) -> list:
    if side_data.get("vta") and side_data["vta"].get("vta_mac_address"):  # TODO right now this condition is never met
        return [{"MacAddress": side_data["vta"]["vta_mac_address"]}]
    return []


def _build_cpe_data(side_cpe):  # TODO you are missing the customer address
    cpe = {
        "Vendor": side_cpe.get("vendor"),
        "Model": side_cpe.get("model"),
        "Hostname": side_cpe.get("tid"),
        "TestAccessPort": None,
        "InterfaceInfo": None,
        "Description": None,
        "PortType": None,
        "Interface": side_cpe.get("port_access_id", "").lower(),
        "VLANOperation": side_cpe.get("vlan_operation"),
        "ServiceVLANID": side_cpe.get("svlan"),
        "EVCType": None,
    }
    ip_address = side_cpe.get("management_ip")
    if not ip_address or ip_address.upper() in ["DHCP", "TRUE", "FALSE"]:
        ip_address = _get_cpe_ip_address(side_cpe.get("tid"))
    if not ip_address:
        abort(502, "No management IP given for CPE: {}".format(side_cpe["tid"]))
    cpe["IpAddress"] = side_cpe["management_ip"].split("/")[0]
    if side_cpe["svlan"]:
        # Handle case where delimiter '//' separates a combined service/customer VLAN id
        if "//" in side_cpe["svlan"]:
            vlan_id = side_cpe["svlan"].split("//")[0]
            side_cpe["cevlan"] = side_cpe["svlan"].split("//")[1]
        else:
            # Remove all alpha characters, leave digits alone
            vlan_id = re.sub("[^0-9]", "", side_cpe["svlan"])
        cpe["ServiceVLANID"] = vlan_id
    cpe["CustomerVLANID"] = side_cpe["cevlan"]
    return cpe
