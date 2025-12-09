import logging
from typing import Dict, List, Optional, Union

from arda_app.bll.net_new.inni_matrix import find_inni
from arda_app.common.cd_utils import granite_pathUtil_get_url, granite_paths_url, region_network_mapping
from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite, get_shelf_udas, put_granite


logger = logging.getLogger(__name__)


def get_live_items(items: List[dict]) -> List[dict]:
    """
    Filter and return items with a status of "Live".

    Args:
    - items (List[dict]): List of item dictionaries.

    Returns:
    - List[dict]: List of items with status "Live".
    """
    return [item for item in items if item.get("PATH_STATUS") in ["Live", "Pending Decommission"]]


def check_circ_path_inst_id(items: List[dict]) -> bool:
    """
    Checks the uniqueness of CIRC_PATH_INST_ID in the given items.

    Args:
    - items (List[dict]): List of item dictionaries.

    Returns:
    - bool: True if there's only one unique CIRC_PATH_INST_ID, False otherwise.
    """
    if not items:
        return False

    try:
        cp_inst_id = {item["CIRC_PATH_INST_ID"] for item in items}
    except KeyError:
        abort(500, "ENNI not supported, please investigate")

    return len(cp_inst_id) == 1


def _validate_parent_paths(parent_paths: List[dict], get_granite_url: str, enni_tid: str, enni_type: str) -> List[dict]:
    """
    Validate and filter parent paths based on ENNI type.

    Args:
    - parent_paths (List[dict]): List of parent paths.
    - get_granite_url (str): URL for granite API.
    - enni_tid (str): ENNI TID.
    - enni_type (str): Type of ENNI - either "NIU" or "SWITCH".

    Returns:
    - List[dict]: Filtered list of parent paths.
    """
    if len(parent_paths) == 0:
        abort(500, f"Unable to find parent path for ENNI device: {enni_tid}")
    if enni_type == "NIU" and len(parent_paths) > 2:
        # should only have a Live path and/or a Designed path
        abort(500, f"Unexpected number of parent paths returned for ENNI device: {get_granite_url}")
    elif enni_type == "SWITCH" and len(parent_paths) > 2:
        # Switches can have multiple ENNIs on them. Filter for parent paths
        filtered_parent_paths = []
        for path in parent_paths:
            if f"{enni_tid}.{enni_tid}" in path["CIRCUIT_NAME"]:
                continue
            else:
                filtered_parent_paths.append(path)
        if len(filtered_parent_paths) > 2:
            abort(500, f"Unexpected number of parent paths returned for ENNI device: {get_granite_url}")
        return filtered_parent_paths
    return parent_paths


def _calculate_oversubscription(enni: str, cid_bw: int) -> str:
    """
    Calculate the oversubscription percentage needed to add the ENNI to the CID path.

    Args:
    - enni (str): ENNI identifier.
    - cid_bw (int): Bandwidth of the CID path.

    Returns:
    - str: Oversubscription percentage (without '%' character).
    """
    url = granite_pathUtil_get_url(enni)
    g_resp = get_granite(url)

    if isinstance(g_resp, list):
        resp = g_resp[0]
        total_bw, used_bw, available_bw = (
            int(resp.get("TOTAL_BW")),
            int(resp.get("USED_BW")),
            int(resp.get("AVAILABLE_BW")),
        )
    else:
        msg = f"No utilization data in granite for ENNI: {enni}. Please check Member BW field in granite"
        logger.error(msg)
        abort(500, msg)

    needed_bw = cid_bw + used_bw

    if available_bw > needed_bw:
        return "0"
    else:
        bw_diff = needed_bw - total_bw
        perc = 0.1
        while True:
            if (total_bw * perc) > bw_diff:
                break
            perc += 0.1
        return f"{perc:.0%}".rstrip("%")


def _edna_check(a_equip_inst_id: str, z_equip_inst_id: str = None) -> bool:
    """
    Check if either device has NETWORK of EDNA.

    Args:
    - a_equip_inst_id (str): A-side equipment instance ID.
    - z_equip_inst_id (str): Z-side equipment instance ID.

    Returns:
    - bool: True if one of the devices has the specified role, False otherwise.
    """
    roles = []
    if a_equip_inst_id:
        a_device_udas = get_shelf_udas(a_equip_inst_id)
        a_network_role = [uda.get("ATTR_VALUE") for uda in a_device_udas if uda.get("ATTR_NAME") == "NETWORK"]
        roles = a_network_role
    if z_equip_inst_id:
        z_device_udas = get_shelf_udas(z_equip_inst_id)
        z_network_role = [uda.get("ATTR_VALUE") for uda in z_device_udas if uda.get("ATTR_NAME") == "NETWORK"]
        roles = roles + z_network_role

    if "EDNA" in roles:
        return True

    return False


def _add_aside_parent_path(cid, cid_inst_id, parent_path_id, enni_sequence):
    path_payload = {
        "PATH_NAME": cid,
        "PATH_INST_ID": cid_inst_id,
        "LEG_NAME": "1",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": enni_sequence if enni_sequence else "3",
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": parent_path_id,
    }
    url = granite_paths_url()
    put_granite(url, path_payload)


def _add_enni_parent_path(cid, cid_inst_id, parent_letter, uplink_tid, enni_type):
    get_granite_url = f"/circuitSites?PATH_CLASS=P&CIRCUIT_NAME=%{parent_letter}W.{uplink_tid}&WILD_CARD_FLAG=1"
    parent_paths = get_granite(get_granite_url)
    parent_paths = _validate_parent_paths(parent_paths, get_granite_url, uplink_tid, enni_type)

    get_granite_url = f"/pathElements?CIRC_PATH_HUM_ID={cid}"
    circuit_elements = get_granite(get_granite_url)

    # sequences shift down by default if used seq # is sent
    # so if cloud is #3 and we send new path as #3, cloud will be #4
    sequence = None
    for element in circuit_elements:
        if "MPLS" in element["ELEMENT_NAME"]:
            sequence = element["SEQUENCE"]
            break

    for path in parent_paths:
        _add_aside_parent_path(cid, cid_inst_id, path["CIRC_PATH_INST_ID"], sequence)

    return parent_paths


def _put_enni_mpls(cid, cid_inst_id, enni_region, enni_state):
    enni_cloud_name = region_network_mapping(enni_region, enni_state)

    get_granite_url = f"/circuitSites?PATH_CLASS=N&CIRCUIT_NAME={enni_cloud_name}"
    cloud_network_inst_id = get_granite(get_granite_url)[0]["CIRC_PATH_INST_ID"]

    cloud_payload = {
        "PATH_NAME": cid,
        "PATH_INST_ID": cid_inst_id,
        "LEG_NAME": "1",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PARENT_NETWORK_INST_ID": cloud_network_inst_id,
        "PATH_ELEMENT_TYPE": "PARENT_NETWORK_SUBRATE",
    }

    url = granite_paths_url()
    put_granite(url, cloud_payload)


def _inni_check(
    cid_info_lvl2: List[Dict[str, Union[str, int]]],
    enni_legacy_source: str,
    enni_equip_inst_id: str,
    circit_sites_info: List[Dict[str, str]],
    cid: str,
    cid_inst_id: str,
    enni_tid: str,
) -> Optional[bool]:
    """
    Checks the INNI based on the given information.

    Parameters:
        - cid_info_lvl2: List of CID information
        - enni_legacy_source: Legacy source of ENNI
        - enni_equip_inst_id: Equipment instance ID of ENNI
        - circit_sites_info: Information on circuit sites
        - cid: CID
        - cid_inst_id: CID instance ID

    Returns:
        - True if successful, None otherwise
    """
    for element in reversed(cid_info_lvl2):
        if _is_relevant_router(element):
            if _edna_check(element.get("ELEMENT_REFERENCE"), enni_equip_inst_id):
                logger.info("ENDA device detected, no INNI needed")
                break
            elif not enni_legacy_source:
                abort(500, f"Legacy Equipment Source is blank for edge router {enni_tid}, please populate.")
            elif enni_legacy_source != element.get("LEGACY_EQUIP_SOURCE"):
                if not element.get("LEGACY_EQUIP_SOURCE"):
                    abort(
                        500, f"Missing LEGACY_EQUIP_SOURCE for Z-Side router {element.get('TID')} for INNI determination"
                    )
                elif _is_inni_unnecessary(enni_legacy_source, element.get("LEGACY_EQUIP_SOURCE")):
                    break
                else:
                    return _process_inni_determination(circit_sites_info, enni_legacy_source, element, cid, cid_inst_id)


def _is_relevant_router(element: Dict[str, str]) -> bool:
    """Checks if an element is a relevant router."""
    return element.get("ELEMENT_CATEGORY") == "ROUTER" and element.get("TID").endswith("CW")


def _is_inni_unnecessary(legacy_source_a: str, legacy_source_b: str) -> bool:
    """Checks if INNI is unnecessary based on legacy sources."""
    return (legacy_source_a, legacy_source_b) in [("L-TWC", "L-BHN"), ("L-BHN", "L-TWC")]


def _process_inni_determination(
    circit_sites_info: List[Dict[str, str]],
    enni_legacy_source: str,
    element: Dict[str, Union[str, int]],
    cid: str,
    cid_inst_id: str,
) -> Optional[bool]:
    """
    Processes INNI determination and returns True if successful.

    Parameters:
        - circit_sites_info: Information on circuit sites
        - enni_legacy_source: Legacy source of ENNI
        - element: Information element
        - cid: CID
        - cid_inst_id: CID instance ID

    Returns:
        - True if successful, None otherwise
    """
    inni_cid = find_inni(
        circit_sites_info[0]["A_STATE"],
        circit_sites_info[0]["Z_STATE"],
        enni_legacy_source,
        element.get("LEGACY_EQUIP_SOURCE"),
    )

    if inni_cid:
        logger.info(f"INNI determined: {inni_cid}")
        get_granite_url = f"/circuitSites?PATH_CLASS=P&CIRCUIT_NAME={inni_cid}"
        inni_path = get_granite(get_granite_url)

        if len(inni_path) in [1, 2]:
            _add_paths_to_inni(inni_path, cid, cid_inst_id)
            return True
        else:
            abort(500, f"Unexpected number of paths returned for INNI: {inni_cid}")
    else:
        abort(500, "Unable to determine INNI")


def _add_paths_to_inni(inni_path: List[Dict[str, Union[str, int]]], cid: str, cid_inst_id: str):
    """Adds paths to the given INNI."""
    for path in inni_path:
        path_payload = {
            "PATH_NAME": cid,
            "PATH_INST_ID": cid_inst_id,
            "LEG_NAME": "1",
            "ADD_ELEMENT": "true",
            "PATH_ELEM_SEQUENCE": "2",
            "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
            "PARENT_PATH_INST_ID": path.get("CIRC_PATH_INST_ID"),
        }
        url = granite_paths_url()
        put_granite(url, path_payload)


def remove_assoc(cid_rev_id, resp):
    # removing evc association from granite
    remove_evc = {
        "PATH_INST_ID": cid_rev_id,
        "ASSOC_NAME": resp[0]["associationName"],
        "ASSOC_INST_ID": resp[0]["assocInstId"],
    }
    resp = put_granite("/removePathAssociation?", remove_evc)

    if resp.get("retString") != "Path Association Removed":
        abort(500, "Association was not able to be removed")


def assoc_check(circuit_details, cid_rev_id):
    evc_id = set()
    cid = circuit_details[0]["PATH_NAME"]

    # look for associations
    for evc in circuit_details:
        if evc["CIRC_PATH_INST_ID"] == cid_rev_id and evc.get("EVC_ID"):
            evc_id.add(evc["EVC_ID"])

    for evc in evc_id:
        resp = get_granite(f"/pathAssociations?PATH_INST_ID={cid_rev_id}&ASSOC_INST_ID={evc}")

        if isinstance(resp, list):
            remove_assoc(cid_rev_id, resp)

            # Removing EVC ID from CID Path in granite
            put_granite_url = granite_paths_url()
            payload = {"PATH_NAME": cid, "PATH_REVISION": "1", "UDA": {"ADDITIONAL ETHERNET INFO": {"EVC ID": ""}}}
            put_granite(put_granite_url, payload)


def loc_switch_check(cid_inst_id, epl=False):
    # checking circuit to see if its locally switch and deleting cloud element
    get_granite_url = f"/pathElements?CIRC_PATH_INST_ID={cid_inst_id}&LVL=1"
    circuit_data = get_granite(get_granite_url)

    cw_list = []
    qw_list = []
    cloud_inst = ""
    seq = ""

    if isinstance(circuit_data, list):
        for data in circuit_data:
            if data["ELEMENT_CATEGORY"] == "ETHERNET TRANSPORT":
                if data["ELEMENT_NAME"].split(".")[2].endswith("CW"):
                    cw_name = data["ELEMENT_NAME"].split(".")[2]
                    cw_list.append(cw_name)

                if data["ELEMENT_NAME"].split(".")[-1].endswith("QW"):
                    qw_inst_id = data["ELEMENT_REFERENCE"]
                    qw_list.append(qw_inst_id)

            if data["ELEMENT_TYPE"] == "CLOUD":
                cloud_inst = data["ELEMENT_REFERENCE"]
                seq = data["SEQUENCE"]

    if len(cw_list) == 2:
        if cw_list[0] == cw_list[1]:
            # delete cloud element
            if cloud_inst and seq:
                cloud_remove = {
                    "PATH_INST_ID": cid_inst_id,
                    "LEG_NAME": "1",
                    "REMOVE_ELEMENT": "true",
                    "ELEMENTS_TO_REMOVE": seq,
                }

                resp = put_granite(f"/paths?CIRC_PATH_INST_ID={cid_inst_id}", cloud_remove)

                if resp.get("retString") != "Path Updated":
                    msg = "Unable to remove cloud object in granite from locally switched circuit"
                    logger.error(msg)
                    abort(500, msg)

            # checking for association and remove from path
            assoc_check(circuit_data, cid_inst_id)

            if len(qw_list) == 2 and epl:
                # checking element reference(inst_id) for same QFX which would require a vlan swap
                if qw_list[0] == qw_list[1]:
                    msg = "The circuit is locally switched to the same QFX. This will require a VLAN swap"
                    abort(500, msg)
