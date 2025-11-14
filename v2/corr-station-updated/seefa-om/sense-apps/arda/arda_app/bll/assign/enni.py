import logging

from arda_app.common.cd_utils import granite_paths_url
from common_sense.common.errors import abort
from arda_app.dll.granite import (
    get_granite,
    put_granite,
    get_path_elements,
    edna_mpls_in_path,
    get_path_elements_inst_l1,
)
from arda_app.bll.assign.enni_utils import (
    _put_enni_mpls,
    _inni_check,
    _validate_parent_paths,
    check_circ_path_inst_id,
    get_live_items,
    _calculate_oversubscription,
    _add_aside_parent_path,
    _add_enni_parent_path,
    loc_switch_check,
)

logger = logging.getLogger(__name__)


def assign_enni_main(payload: dict):
    cid = payload.get("cid")
    spectrum_primary_enni = payload.get("spectrum_primary_enni")
    rev_instance = payload.get("rev_instance") if payload.get("rev_instance") else ""

    # Get info from payload CID
    if rev_instance:
        cid_info = get_path_elements_inst_l1(rev_instance)
    else:
        cid_info = get_path_elements(cid)

    # GET ENNI Info
    enni_info = get_path_elements(spectrum_primary_enni)
    cid_info_lvl2 = [element for element in cid_info if element.get("LVL") == "2"]
    cid_inst_id = cid_info[0]["CIRC_PATH_INST_ID"]
    z_site_name = cid_info[0]["PATH_Z_SITE"]
    cid_bw = cid_info[0]["BW_SIZE"]

    # Filter ENNI Info to get only Live items
    enni_info = get_live_items(enni_info)
    if not enni_info:
        abort(500, "ENNI Error: No Live items found.")
    if not check_circ_path_inst_id(enni_info):
        abort(500, "ENNI Revisions not supported at this time.")

    enni_vendor = None
    enni_equip_inst_id = None
    enni_path_rev = None
    enni_legacy_source = None
    parent_path_inst_id = None
    parent_port_inst_id = None
    parent_element_name = None
    port_acccess_id = None
    enni_type = None
    a_site_name = enni_info[0]["A_SITE_NAME"]
    for element in enni_info:
        # Ignore optical ports and gather correct ENNI device info
        if element["ELEMENT_CATEGORY"] in ["ROUTER", "NIU"] or (
            element["ELEMENT_CATEGORY"] == "SWITCH" and element["ELEMENT_TYPE"] == "PORT"
        ):
            enni_vendor = element["VENDOR"]
            enni_type = element["ELEMENT_CATEGORY"]
            enni_equip_inst_id = element["ELEMENT_REFERENCE"]
            enni_path_rev = element["PATH_REV"]
            enni_tid = element["TID"]
            enni_legacy_source = element["LEGACY_EQUIP_SOURCE"]
            parent_path_inst_id = element["CIRC_PATH_INST_ID"]
            parent_port_inst_id = element["PORT_INST_ID"]
            parent_element_name = element["ELEMENT_NAME"]
            port_acccess_id = element["PORT_ACCESS_ID"]
            break

    # Whitelist of supported ENNI device types
    if enni_vendor not in ["JUNIPER", "CISCO", "RAD", "ADVA"]:
        abort(500, f"ENNI device {enni_vendor} is not supported at this time. Only Juniper, Cisco, and RAD.")
    elif enni_vendor == "CISCO" and enni_type == "SWITCH":
        abort(500, "Cisco switches as ENNI devices are unsupported at this time")

    # Check if A-side is in different region. If so, add that cloud MPLS network element (and TBONE)
    get_granite_url = f"/circuitSites?PATH_CLASS=P&CIRCUIT_NAME={cid}"
    circit_sites_info = get_granite(get_granite_url)

    # Add MPLS if A and Z are in different regions
    if not (circit_sites_info[0].get("A_SITE_REGION") and circit_sites_info[0].get("Z_SITE_REGION")):
        missing = "A_SITE_REGION" if not circit_sites_info[0].get("A_SITE_REGION") else "Z_SITE_REGION"
        abort(500, f"No parent region found for {missing} for MPLS cloud check")
    if circit_sites_info[0]["A_SITE_REGION"] != circit_sites_info[0]["Z_SITE_REGION"]:
        if not edna_mpls_in_path(cid):
            _put_enni_mpls(cid, cid_inst_id, circit_sites_info[0]["A_SITE_REGION"], circit_sites_info[0]["A_STATE"])

    # Check if INNI is needed based on LEGACY_EQUIP_SOURCE of ENNI device and Z-side router
    inni_added = _inni_check(
        cid_info_lvl2, enni_legacy_source, enni_equip_inst_id, circit_sites_info, cid, cid_inst_id, enni_tid
    )

    # Check ENNI utilization for over-subscription % and update, if needed
    over_sub_perc = _calculate_oversubscription(spectrum_primary_enni, int(cid_bw))
    if int(over_sub_perc) > 0:
        url = granite_paths_url()
        payload = {
            "PATH_NAME": spectrum_primary_enni,
            "PATH_REVISION": enni_path_rev,
            "PATH_MAX_OVER_SUB": over_sub_perc,
        }
        put_granite(url, payload)

    # Assign ENNI
    logger.info(f"Creating Granite circuit revision for {cid}")
    put_granite_url = granite_paths_url()
    payload = {
        "PATH_NAME": cid,
        "PATH_REVISION": cid_info[0]["PATH_REV"],
        "PATH_LEG_INST_ID": cid_info[0]["LEG_INST_ID"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": parent_path_inst_id,
        "PARENT_PORT_INST_ID": parent_port_inst_id,
    }
    put_granite(put_granite_url, payload)

    # Get Dynamic Port Info
    get_granite_url = f"/pathElements?CIRC_PATH_HUM_ID={cid}&ELEMENT_NAME={parent_element_name}"
    dynamic_port_info = get_granite(get_granite_url)

    dynamic_port_inst_id, dynamic_port_sequence = (None, None)
    for item in dynamic_port_info:
        if item["PORT_INST_ID"] != parent_port_inst_id:
            dynamic_port_sequence = item["SEQUENCE"]
            dynamic_port_inst_id = item["PORT_INST_ID"]

    if not all((dynamic_port_inst_id, dynamic_port_sequence)):
        abort(500, f"Get Dynamic Port Info Faild for {cid}.")

    # PUT Dynamic Port Info
    put_granite_url = granite_paths_url()
    payload = {
        "PATH_INST_ID": cid_inst_id,
        "LEG_NAME": "1",
        "ELEMENT_TO_MOVE": dynamic_port_sequence,
        "NEW_SEQUENCE": "1",
    }
    put_granite(put_granite_url, payload)

    # PUT Add PAID to Dynamic Port:
    put_granite_url = f"/ports?PORT_INST_ID={dynamic_port_inst_id}"
    payload = {
        "PORT_INST_ID": dynamic_port_inst_id,
        "PORT_ACCESS_ID": port_acccess_id,
        "PORT_STATUS": "Assigned",
        "SET_CONFIRMED": "TRUE",
        "UDA": {"VLAN INFO": {"PORT-ROLE": "ENNI"}},
    }
    put_granite(put_granite_url, payload)

    # PUT A_SITE_NAME call
    put_granite_url = granite_paths_url()
    payload = {
        "PATH_NAME": cid,
        "PATH_INST_ID": cid_inst_id,
        "A_SITE_NAME": a_site_name,
        "UPDATE_LEG": "true",
        "LEG_NAME": "1",
        "LEG_A_SITE_NAME": a_site_name,
        "LEG_Z_SITE_NAME": z_site_name,
    }
    put_granite(put_granite_url, payload)

    # Find and add parent path
    if enni_vendor in ["RAD", "ADVA"] or (enni_vendor == "JUNIPER" and enni_type == "SWITCH"):
        get_granite_url = f"/circuitSites?PATH_CLASS=P&CIRCUIT_NAME=%W.{enni_tid}&WILD_CARD_FLAG=1"
        parent_paths = get_granite(get_granite_url)
        parent_paths = _validate_parent_paths(parent_paths, get_granite_url, enni_tid, enni_type)

        get_granite_url = f"/pathElements?CIRC_PATH_HUM_ID={cid}"
        circuit_elements = get_granite(get_granite_url)

        enni_sequence = None
        for element in circuit_elements:
            if element["ELEMENT_NAME"] == spectrum_primary_enni:
                enni_sequence = str(int(element["SEQUENCE"]) + 1)
                break

        # PUT parent path(s)
        for path in parent_paths:
            _add_aside_parent_path(cid, cid_inst_id, path["CIRC_PATH_INST_ID"], enni_sequence)

        # if AW or QFX detected, find and add parent path(s)
        uplink_tid = parent_paths[0]["CIRCUIT_NAME"].split(".")[-2]
        if uplink_tid[-2] == "A":
            parent_paths = _add_enni_parent_path(cid, cid_inst_id, "Q", uplink_tid, enni_type)
            uplink_tid = parent_paths[0]["CIRCUIT_NAME"].split(".")[-2]
            _add_enni_parent_path(cid, cid_inst_id, "C", uplink_tid, enni_type)
        elif uplink_tid[-2] == "Q":
            _add_enni_parent_path(cid, cid_inst_id, "C", uplink_tid, enni_type)

    if inni_added:
        # Manual design process is to log into the hub routers and test latency across the designed path with ping tests
        # Unable to do so currently so fall out after finishing the ENNI design
        abort(500, "INNI added but unable to perform latency testing")

    loc_switch_check(cid_inst_id)

    return {"message": "ENNI has been added successfully."}
