import logging
import ipaddress
from typing import Tuple, Any
from arda_app.bll.models.device_topology.overlay import OverlayDeviceTopologyModel

from arda_app.common.cd_utils import (
    granite_ports_put_url,
    granite_shelves_post_url,
    granite_paths_url,
    granite_equipments_url,
    granite_uda_get_url,
)
from common_sense.common.errors import abort
from arda_app.dll.granite import (
    get_equipment_buildout,
    insert_card_template,
    post_granite,
    put_granite,
    get_granite,
    get_path_elements_l1,
)

logger = logging.getLogger(__name__)

MODELS = {
    "MX68": "MERAKI MX68",
    "MX85": "MERAKI MX85",
    "MX105": "MERAKI MX105",
    "MX250": "MERAKI MX250",
    "MX450": "MERAKI MX450",
}


def create_mne_shelf(payload) -> dict:
    """Start process for MNE MX shelf creation"""
    cid = payload.get("cid")
    product_name = payload.get("product_name")
    related_cid = payload.get("related_cid")
    coax = payload.get("coax")
    model = None

    paths = get_granite(granite_paths_url() + f"?CIRC_PATH_HUM_ID={cid}&LVL=1")
    if isinstance(paths, dict) and "No records found with the specified search criteria..." in paths.values():
        abort(500, f"Empty Path response received. Path missing from Granite for cid: {cid}")
    else:
        paths = paths[0]
    udas = get_granite(granite_uda_get_url(paths["pathInstanceId"]))
    uda_dict = {}
    if udas:
        for e in udas:
            uda_dict[e["ATTR_NAME"]] = e["ATTR_VALUE"]
    logger.info(f"MNE Create_Shelf uda_dict for cid {cid}: {uda_dict}\n")
    lvl1 = {
        "PATH_Z_SITE": paths["zSideSiteName"],
        "CIRC_PATH_INST_ID": paths["pathInstanceId"],
        "IPV4_SERVICE_TYPE": uda_dict.get("IPv4 SERVICE TYPE", None),
        "IPV4_ASSIGNED_SUBNETS": uda_dict.get("IPv4 ASSIGNED SUBNET(s)", None),
        "SERVICE_MEDIA": uda_dict.get("SERVICE MEDIA", None),
    }
    # Commenting this out per customer request temporarily. To be removed in the future.
    # mne_serv_types = ["LAN", "ROUTED"]
    # if lvl1["IPV4_SERVICE_TYPE"] not in mne_serv_types and uda_dict.get("SERVICE MEDIA") != "BYO":
    #     abort(500, f'Incorrect IPV4 Service Type: {lvl1["IPV4_SERVICE_TYPE"]}')
    # Check for existing MX before processing.
    if product_name == "Managed Network Edge":
        existing_mx, tid, model = _check_existing_mx(cid)
        if existing_mx:
            return 200, f"Meraki MX Shelf already exists: TID: {tid}, Model: {model}"
    model = MODELS[payload.get("model")]
    # GET site name based on side
    site_name = lvl1["PATH_Z_SITE"]
    tid = site_name.split("-")[0] + "MN1"
    new_tid = _find_next_tid(tid)
    skip_media = ["BYO", "COAX"]
    if not lvl1["IPV4_ASSIGNED_SUBNETS"]:
        if lvl1["SERVICE_MEDIA"] not in skip_media:
            abort(500, "No IPV4 Information available in granite or payload")
        else:
            nw_address = cidr = gw_address = tid_ip = nw_address = ""
    elif len(lvl1["IPV4_ASSIGNED_SUBNETS"].split(",")) == 1:
        nw_address = ipaddress.IPv4Address(lvl1["IPV4_ASSIGNED_SUBNETS"].split("/")[0])
        cidr = f"/{lvl1['IPV4_ASSIGNED_SUBNETS'].split('/')[1]}"
        gw_address = nw_address + 1
        tid_ip = nw_address + 2
    else:
        abort(500, f"IPv4 ASSIGNED SUBNETS contains multiple IP blocks: {lvl1['IPV4_ASSIGNED_SUBNETS']}")

    shelf_create_payload = {
        "SHELF_NAME": f"{new_tid}/999.999.999.99/FWL",
        "SHELF_TEMPLATE": f"{model} FIREWALL",
        "SITE_NAME": site_name,
        "UDA": {
            "Purchase Info": {"PURCHASING GROUP": "MANAGED SERVICES - IP", "TRANSPORT MEDIA TYPE": "FIBER"},
            "Device Info": {"DEVICE ID": new_tid, "GNE IP ADDRESS": str(gw_address), "IP SUBNET MASK": str(cidr)},
            "Device Config-Equipment": {"IPv4 ADDRESS": str(tid_ip) + str(cidr), "TARGET ID (TID)": new_tid},
        },
    }

    logger.info(f"Creating shelf w/ payload: {shelf_create_payload}")
    # POST Create CPE shelf from template to granite
    _create_shelf(shelf_create_payload)

    if coax:
        first_tid = site_name.split("-")[0] + "1ZW"
        modem_tid = _find_next_tid(first_tid)
        _create_coax_elements(modem_tid, site_name, cid, paths["pathInstanceId"])

    # SET device topology
    device_topology = OverlayDeviceTopologyModel(role="mne", vendor="CISCO", device_template=model, model=model)
    # PUT build uplink card
    mne_uplink_pid, mne_uplink_paid = _build_uplink(new_tid, device_topology)

    # PUT build handoff card
    mne_handoff_pid, mne_handoff_paid = _build_handoff(new_tid, device_topology)

    # set response
    resp = {
        "mne_shelf": f"{new_tid}/999.999.999.99/FWL",
        "mne_tid": new_tid,
        "mne_uplink": mne_uplink_pid,
        "mne_uplink_paid": mne_uplink_paid,
        "mne_handoff": mne_handoff_pid,
        "mne_handoff_paid": mne_handoff_paid,
        "circ_path_inst_id": lvl1["CIRC_PATH_INST_ID"],
    }

    logger.info("Shelf creation complete. Adding uplink port to Path")

    if related_cid:
        _change_port_channelization(mne_uplink_pid)
        transport_response = _create_transport(cid, site_name, new_tid, paths["pathInstanceId"])
        _add_port_to_transport(transport_response, mne_uplink_pid)
    else:
        uplink_payload = {"cid": cid, "port_pid": mne_uplink_pid}
        _add_port_to_path(uplink_payload)

    logger.info("Uplink port add complete. Adding handoff port to Path")

    handoff_payload = {"cid": cid, "port_pid": mne_handoff_pid}
    _add_port_to_path(handoff_payload)

    return resp


def _add_port_to_path(add_port_payload: dict) -> None:
    """
    Add specified port to path as last element in path
    Currently utilized for MNE services/MX shelves only
    """
    path_elems = get_path_elements_l1(add_port_payload["cid"])
    if not isinstance(path_elems, dict):
        leg_inst_id = path_elems[0]["LEG_INST_ID"]
        next_sequence = sorted([int(e["SEQUENCE"]) for e in path_elems])[-1] + 1
        path_inst_id = path_elems[0]["CIRC_PATH_INST_ID"]
    else:
        paths = get_granite(granite_paths_url() + f"?CIRC_PATH_HUM_ID={add_port_payload['cid']}&LVL=1")[0]
        next_sequence = "1"
        leg_inst_id = "1"
        path_inst_id = paths["pathInstanceId"]
    logger.info(f"\n add port pl: {add_port_payload}\n")
    port_path_payload = {
        "PATH_NAME": add_port_payload["cid"],
        "PATH_INST_ID": path_inst_id,
        "LEG_INST_ID": leg_inst_id,
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": str(next_sequence),
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "PORT_INST_ID": add_port_payload["port_pid"],
    }

    path_put_url = granite_paths_url()
    logger.info(f"Port put Response:{put_granite(path_put_url, port_path_payload)}")


def _create_shelf(shelf_create_payload: dict) -> None:
    """
    Create Customer Premise Equipment shelf in Granite.

    TODO: fallout when an existing shelf with a different vendor is found (SWT vs. NIU).
    """
    shelf_create_url = granite_shelves_post_url()
    shelf_create_data = post_granite(shelf_create_url, shelf_create_payload)

    if shelf_create_data["retString"] == "Shelf has nothing to update":
        logger.error(f"Unsupported existing shelf found.\nURL: {shelf_create_url} \nResponse: {shelf_create_data}")
        abort(
            500,
            message="Unsupported existing shelf found. Must be no prior CPE shelf at site for this customer",
            url=shelf_create_url,
            response=shelf_create_data,
        )

    if shelf_create_data["retString"] != "Shelf Added":
        logger.error(
            f"Unexpected Granite response, could not find 'Shelf Added' message. "
            f"\nURL: {shelf_create_url} \nResponse: {shelf_create_data}"
        )
        abort(500, message="Incorrect shelf data payload from Granite", url=shelf_create_url, response=shelf_create_data)

    logger.info(f"MNE shelf created \nGranite shelf create response: \n{shelf_create_data}")
    return shelf_create_data


def _create_coax_elements(modem_tid, site_name, cid, path_inst_id):
    """Steps to perform for COAX underlay"""
    # TODO: Check HFC cloud existence first?? TBD on PO

    # Create Modem for COAX orders
    modem_create_payload = {
        "SHELF_NAME": f"{modem_tid}/999.999.999.99/NIU",
        "SHELF_TEMPLATE": "GENERIC DOCSIS 3.0 CABLE MODEM",
        "SITE_NAME": site_name,
        "UDA": {
            "Purchase Info": {"PURCHASING GROUP": "MANAGED SERVICES - IP", "TRANSPORT MEDIA TYPE": "COAX"},
            "Device Info": {"DEVICE ID": modem_tid, "GNE IP ADDRESS": "DHCP"},
            "Device Config-Equipment": {"IPv4 ADDRESS": "DHCP", "TARGET ID (TID)": modem_tid},
        },
    }

    modem_id = _create_shelf(modem_create_payload)["equipInstId"]
    logger.info(f"\n modem_id response: {modem_id}")
    full_tid = f"{modem_tid}/999.999.999.99/NIU"
    _add_coax_cloud_to_path(cid, path_inst_id)
    _add_modem_to_path(full_tid, cid)


def _add_coax_cloud_to_path(cid, path_inst_id):
    """Add Coax Cloud , ID/methodology to ID TBD based on SF or single generic cloud"""
    # TODO: Logic to figure out cloud id's. is it static? dynamic based on state?

    path_elems = get_path_elements_l1(cid)
    if not isinstance(path_elems, dict):
        leg_inst_id = path_elems[0]["LEG_INST_ID"]
        next_sequence = sorted([int(e["SEQUENCE"]) for e in path_elems])[-1] + 1
    else:
        next_sequence = "1"
        leg_inst_id = "1"

    path_cloud_payload = {
        "PATH_NAME": cid,
        "PATH_INST_ID": path_inst_id,
        "LEG_INST_ID": leg_inst_id,
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": str(next_sequence),
        "PATH_ELEMENT_TYPE": "CLOUD",
        "CLOUD_NAME": "CHTR-HFC-CORE-CLOUD",
    }

    path_put_url = granite_paths_url()
    logger.info(f"Port put Response:{put_granite(path_put_url, path_cloud_payload)}")


def _add_modem_to_path(modem_tid, cid):
    """Add modem uplink and UNI ports to path"""
    equipment_data = get_equipment_buildout(modem_tid)
    logger.info(f"equipment answer: \n {equipment_data}")
    uplink_id, uni_id = "", ""
    for data in equipment_data:
        if data["PORT_NAME"] == "CABLE":
            uplink_id = data["PORT_INST_ID"]
            uplink_payload = {"cid": cid, "port_pid": uplink_id}
            _add_port_to_path(uplink_payload)
        if data["PORT_NAME"] == "1":
            uni_id = data["PORT_INST_ID"]
            uni_payload = {"cid": cid, "port_pid": uni_id}
            _add_port_to_path(uni_payload)
        if uplink_id and uni_id:
            break


def _find_next_tid(tid):
    """Check site for existing MXs"""
    valid_tid = False
    suffix = 1
    while not valid_tid:
        get_url = f"?EQUIP_NAME={tid[:-1] + str(suffix)}&OBJECT_TYPE=SHELF&WILD_CARD_FLAG=true"
        tid_check = get_granite(granite_equipments_url() + get_url, 60, False)
        if isinstance(tid_check, list):
            suffix += 1
            continue
        elif tid_check["retString"] == "No records found with the specified search criteria...":
            valid_tid = True
            return tid[:-1] + str(suffix)


def _build_uplink(shelf_name: str, device_topology: OverlayDeviceTopologyModel) -> str:
    """add uplink card"""
    equipment_data = get_equipment_buildout(shelf_name)

    if not device_topology.uplink:
        abort(500, "device topology is missing uplink port data")

    for item in equipment_data:
        if all(
            (not item.get("PORT_USE"), item.get("SLOT") == device_topology.uplink.slot, not item.get("PORT_INST_ID"))
        ):
            insert_card_template(item, device_topology.uplink.template)
            break

    # run get equipment buildout again to retrieve latest data
    equipment_data = get_equipment_buildout(shelf_name)

    # get port_inst_id
    port_inst_id = "".join(
        e.get("PORT_INST_ID") for e in equipment_data if e.get("PORT_NAME", "") == device_topology.uplink.slot
    )

    payload = {
        "PORT_ACCESS_ID": device_topology.uplink.port_access_id,
        "PORT_INST_ID": port_inst_id,
        "PORT_STATUS": "Assigned",
    }

    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id, device_topology.uplink.port_access_id


def _build_handoff(shelf_name: str, device_topology: OverlayDeviceTopologyModel) -> str:
    """build_handoff"""
    equipment_data = get_equipment_buildout(shelf_name)

    if not device_topology.handoff:
        abort(500, "device topology is missing handoff port data")

    for item in equipment_data:
        if all(
            (not item.get("PORT_USE"), item.get("SLOT") == device_topology.handoff.slot, not item.get("PORT_INST_ID"))
        ):
            insert_card_template(item, device_topology.handoff.template)
            break

    # run get equipment buildout again to retrieve latest data
    equipment_data = get_equipment_buildout(shelf_name)
    logger.debug(f"SHELF NAME: {shelf_name}")
    logger.debug(f"EQUIP DATA: {equipment_data}")

    port_inst_id = None

    # get port_inst_id
    for e in equipment_data:
        if e.get("PORT_NAME", "") == device_topology.handoff.slot:
            port_inst_id = e.get("PORT_INST_ID")

    payload = {
        "PORT_ACCESS_ID": device_topology.handoff.port_access_id,
        "PORT_INST_ID": port_inst_id,
        "PORT_STATUS": "Assigned",
    }
    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id, device_topology.handoff.port_access_id


def _create_transport(cid, site_name, new_tid, inst_id):
    path_elems = get_path_elements_l1(cid)
    if isinstance(path_elems, dict):
        next_sequence = 1
        leg_name = "1"
    else:
        next_sequence = sorted([int(e["SEQUENCE"]) for e in path_elems])[-1] + 1
        leg_name = path_elems[0]["LEG_NAME"]
    payload = {
        "PATH_NAME": f"{cid[:2]}%.GE1.{new_tid}.{new_tid}",
        "PATH_TEMPLATE_NAME": "WS ETHERNET TRANSPORT",
        "BANDWIDTH": "1 Gbps",
        "TOPOLOGY": "Point to point",
        "A_SITE_NAME": site_name,
        "Z_SITE_NAME": site_name,
        "PATH_STATUS": "Designed",
        "UDA": {
            "SERVICE TYPE": {
                "PRODUCT/SERVICE": "INT-CUSTOMER HANDOFF",
                "MANAGED SERVICE": "YES",
                "SERVICE MEDIA": "FIBER",
            },
            "CHANNELS": {"ASSIGNMENTS": "Dynamic", "PATH_START_CHAN_NBR": 1, "PATH_END_CHAN_NBR": 999},
        },
    }
    paths_url = granite_paths_url()
    post_response = post_granite(paths_url, payload, 60)
    logger.info(f"transport response : {post_response}\n")

    trans_payload = {
        "PATH_INST_ID": inst_id,
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "ADD_ELEMENT": "true",
        "PARENT_PATH_INST_ID": post_response["pathInstanceId"],
        "PATH_ELEM_SEQUENCE": str(next_sequence),
        "LEG_NAME": leg_name,
    }
    ports_url = granite_paths_url()
    put_response = put_granite(ports_url, trans_payload, 60)
    logger.info(f"transport add to path response: {put_response}\n")

    return post_response


def _add_port_to_transport(transport_response, mne_handoff_pid):
    path_inst_id = transport_response["pathInstanceId"]
    payload = {
        "PATH_INST_ID": path_inst_id,
        "PORT_INST_ID": mne_handoff_pid,
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "LEG_NAME": "1",
    }
    ports_url = granite_paths_url()
    put_response = put_granite(ports_url, payload, 60)
    logger.info(f"Transport port add repsonse: {put_response}\n")

    return


def _change_port_channelization(uni_pid):
    payload = {"PORT_INST_ID": uni_pid, "PORT_CHANNEL_ASSIGN": "Dynamic", "SET_CONFIRMED": "TRUE"}
    ports_url = granite_ports_put_url()
    put_response = put_granite(ports_url, payload, 60)
    logger.info(f"channelization repsonse {put_response}\n")


def _check_existing_mx(cid: str) -> Tuple[bool, str, Any]:
    path_elements = get_path_elements_l1(cid)
    if not isinstance(path_elements, dict):
        mx_models = ["MERAKI MX68", "MERAKI MX85", "MERAKI MX105", "MERAKI MX250", "MERAKI MX450"]
        for elem in path_elements:
            if elem["MODEL"] in mx_models:
                tid = elem["ELEMENT_NAME"]
                return True, tid, elem["MODEL"]
    return False, None, None


def _check_existing_sbb(cid: str) -> Tuple[bool, str, Any]:
    tids = None
    path_elements = get_path_elements_l1(cid)
    if not isinstance(path_elements, dict):
        sbb_tid, wb_tid = None, None
        sbb_models, wb_models = ["MGT2000-SE"], ["WORLDBOX"]
        for elem in path_elements:
            if elem["MODEL"] in sbb_models:
                sbb_tid = elem["ELEMENT_NAME"]
            elif elem["MODEL"] in wb_models:
                wb_tid = elem["ELEMENT_NAME"]
        tids = [sbb_tid, wb_tid]
    return tids
