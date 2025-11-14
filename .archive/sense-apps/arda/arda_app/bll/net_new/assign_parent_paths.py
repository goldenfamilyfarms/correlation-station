import logging

from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite, put_granite, edna_mpls_in_path, get_path_elements
from arda_app.bll.assign.enni_utils import _edna_check, loc_switch_check
from arda_app.bll.assign.gsip import cos_check
from arda_app.dll.mdso import onboard_and_exe_cmd
from arda_app.common.cd_utils import (
    validate_values,
    get_l1_url,
    get_circuit_site_url,
    granite_paths_url,
    region_network_mapping,
    validate_hub_clli,
    get_l2_url,
)

logger = logging.getLogger(__name__)


def _get_circuit_info(cid, side="z_side"):
    # get l1 data object
    l1_url = get_l1_url(cid)
    l1_resp = get_granite(l1_url)
    l1_data = None

    # l1_data will use the A or Z CLLi to determine correct transport based on which side is being processed
    if isinstance(l1_resp, list):
        l1_data = [
            e
            for e in l1_resp
            if e["ELEMENT_CATEGORY"] == "ETHERNET TRANSPORT"
            and e["Z_CLLI" if side == "z_side" else "A_CLLI"] in e["Z_SITE_NAME"]
        ][0 if side == "z_side" else -1]
    else:
        msg = f"No data in Granite response for {cid}."
        abort(500, msg)

    # validate response for expected values
    expected = ["PATH_NAME", "PATH_REV", "CIRC_PATH_INST_ID", "LEG_NAME", "LEG_INST_ID", "ELEMENT_NAME", "PATH_Z_SITE"]
    missing = validate_values(l1_data, expected)

    if missing:
        msg = f"Missing required fields: {missing} in response from Granite get path elements."
        logger.error(f"{msg}\nURL: {l1_url} \nResponse: \n{l1_resp}")
        abort(500, message=msg, url=l1_url, response=l1_resp)

    # parse element name to get root location for container and cloud address, and validate expected values
    l1_data["CW_CID"] = None
    start, element, end = None, None, None

    try:
        element = l1_data["ELEMENT_NAME"].split(".")
        start, end = element[-2][-2:], element[-1][-2:]
    except Exception:
        msg = f"Unsupported CPE uplink topology in Granite for {cid} - {l1_data['ELEMENT_NAME']}"
        logger.exception(f"{msg}\nURL: {l1_url} \nResponse: \n{l1_resp}")
        abort(500, message=msg, url=l1_url, response=l1_resp)

    if start not in {"AW", "CW", "QW"} or end not in {"AW", "ZW"}:
        msg = f"Unsupported CPE uplink topology in Granite for {cid} - {l1_data['ELEMENT_NAME']}."
        logger.error(f"{msg}\nURL: {l1_url} \nResponse: \n{l1_resp}")
        abort(500, message=msg, url=l1_url, response=l1_resp)

    if start in "AW":
        _, _, aw_tid, _ = l1_data["ELEMENT_NAME"].split(".")
        get_url = get_circuit_site_url(cid=f"W.{aw_tid}", full_info=False)
        paths_data = get_granite(get_url)

        if len(paths_data) > 1:
            msg = f"Multiple paths found for {cid} - {l1_data['ELEMENT_NAME']}."
            logger.error(f"{msg}\nURL: {get_url} \nResponse: \n{paths_data}")
            abort(500, message=msg, url=get_url, response=paths_data)

        if paths_data[0]["CIRCUIT_STATUS"] == "Live":
            l1_data["AW_CIRCUIT_NAME"] = paths_data[0]["CIRCUIT_NAME"]

    # if we have a QW -> ZW ELEMENT_NAME: format QW substring and add to return object (used as CID for next call)
    if start in "QW":
        l1_data["CW_CID"] = "CW." + element[-2]

    return l1_data


def circuit_site_info_path(cid, full_info=True):
    """
    Get site information for path
        -full_info parameter determines whether we are making the call on the CID or on transport via wildcard
        -full_info=True means we are using the CID (calling circuitSite on the parent)
        -full_info=False means we are using a wildcard to check elements.
        -full_info=False requires additional validation:
            1) circuitSite response must contain only one entry
            2) circuitSite response entry must contain CIRCUIT_STATUS=Live
    """
    # Set up and make the call
    url = get_circuit_site_url(cid=cid, full_info=full_info)
    res = get_granite(url)

    # Filter out invalid service types
    if isinstance(res, list):
        res = [x for x in res if x.get("SERVICE_TYPE") != "INT-CUSTOMER HANDOFF"]

    # Validate that a list (and not a dict) of results are returned; assign the one and only expected entry to a var
    data = None

    try:
        data = res[0]
    except Exception:
        logger.exception(f"No records found in Granite circuitSites call for {cid}. \nURL: {url} \nResponse: \n{res}")
        abort(500, message=f"No circuit site data found in Granite for {cid}", url=url, response=res)

    if not full_info:
        # Validate that there is only one entry in result
        if len(res) > 2:
            logger.error(
                f"{len(res)} results found in circuitSites lookup for {cid}, only one result is supported. "
                f"\nURL: {url} \nResponse: \n{res}"
            )
            abort(
                500,
                f"Unsupported scenario - {len(res)} results found in transport path "
                f"lookup for {cid}. Only one result supported",
                url=url,
                response=res,
            )

    if data["CIRCUIT_BANDWIDTH"] == "RF":
        data["A_SITE_REGION"] = data["Z_SITE_REGION"]
        data["A_STATE"] = data["Z_STATE"]
        data["A_SITE_NAME"] = data["Z_SITE_NAME"]
        data["A_CLLI"] = data["Z_CLLI"]

    # Validate other expected values
    expected = [
        "CIRC_PATH_INST_ID",
        "A_SITE_REGION",
        "A_STATE",
        "A_SITE_NAME",
        "Z_SITE_REGION",
        "Z_ADDRESS",
        "Z_CITY",
        "Z_STATE",
        "Z_ZIP",
    ]

    missing = validate_values(data, expected)

    if missing:
        msg = f"circuitSites response for {cid} missing {missing}"
        logger.error(f"{msg}\nURL: {url} \nResponse: \n{res}")
        abort(500, msg, url=url, response=res)

    # Prepare return object
    csip_resp = []

    for circuit in res:
        if circuit["CIRCUIT_STATUS"] == "DO NOT USE" or circuit["CIRCUIT_STATUS"] == "DO-NOT-USE":
            continue

        csip_values = {
            "CIRC_PATH_INST_ID": circuit["CIRC_PATH_INST_ID"],
            "A_SITE_REGION": circuit["A_SITE_REGION"],
            "Z_SITE_REGION": circuit["Z_SITE_REGION"],
            "Z_ADDRESS": circuit["Z_ADDRESS"],
            "Z_CITY": circuit["Z_CITY"],
            "Z_STATE": circuit["Z_STATE"],
            "Z_ZIP": circuit["Z_ZIP"],
            "A_STATE": circuit["A_STATE"],
            "A_SITE_NAME": circuit["A_SITE_NAME"],
            "A_CLLI": circuit["A_CLLI"],
            "Z_CLLI": circuit["Z_CLLI"],
        }
        csip_resp.append(csip_values)

    if csip_resp:
        return csip_resp
    else:
        msg = f"Could not determine the next path to use by using this partial string {cid}. \
            Please check transports manually"
        logger.error(f"{msg}\nURL: {url} \nResponse: \n{res}")
        abort(500, msg, url=url, response=res)


def _add_parent_path_element(appe_params, sequence="1"):
    payload = {
        "PATH_NAME": appe_params["PATH_NAME"],
        "PATH_INST_ID": appe_params["CIRC_PATH_INST_ID"],
        "PATH_REV_NBR": appe_params["PATH_REV"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": sequence,
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": appe_params["PARENT_PATH_INST_ID"],
        "LEG_NAME": appe_params["LEG_NAME"],
        "PATH_LEG_INST_ID": appe_params["LEG_INST_ID"],
    }

    url = granite_paths_url()
    data = put_granite(url, payload)

    if not isinstance(data, dict):
        msg = "Granite returned an unexpected response"
        logger.error(msg)
        abort(500, msg)

    if data["retString"].lower() != "path updated":
        msg = f"Granite error returned when assigning transport path: {appe_params['path_name']} to circuit."
        logger.error(msg)
        abort(500, msg)


def circuit_site_info_network(csin_input):
    # Get network info
    url = get_circuit_site_url(cid=csin_input, path_class="N")
    res = get_granite(url)

    if not res:
        msg = f"Invalid response from Granite for {csin_input}. Unable to determine parent network."
        logger.error(msg)
        abort(500, msg)

    csin_data = None

    try:
        csin_data = res[0]["CIRC_PATH_INST_ID"]
    except Exception:
        msg = f"Issue discerning parent network from Granite data for {csin_input}."
        logger.error(msg)
        abort(500, msg)

    return csin_data


def _add_parent_network_element(apne_params, sequence="1", a_site=False):
    component: str = ""
    payload: dict = {}

    if not a_site:
        if apne_params.get("PATH_ELEMENT_TYPE") == "CLOUD":
            payload = apne_params
        else:
            component = "parent network element"
            payload = {
                "PATH_NAME": apne_params["PATH_NAME"],
                "PATH_INST_ID": apne_params["CIRC_PATH_INST_ID"],
                "PATH_REV_NBR": apne_params["PATH_REV"],
                "LEG_NAME": apne_params["LEG_NAME"],
                "ADD_ELEMENT": "true",
                "PATH_ELEM_SEQUENCE": sequence,
                "PATH_ELEMENT_TYPE": "PARENT_NETWORK_SUBRATE",
                "PARENT_NETWORK_INST_ID": apne_params["PARENT_NETWORK_INST_ID"],
            }

            if apne_params.get("LEG_INST_ID"):
                payload["PATH_LEG_INST_ID"] = apne_params["LEG_INST_ID"]
    else:
        component = "A_SITE_NAME"
        payload = {
            "PATH_NAME": apne_params["PATH_NAME"],
            "PATH_REVISION": apne_params["PATH_REV"],
            "A_SITE_NAME": apne_params["A_SITE_NAME"],
            "Z_SITE_NAME": apne_params["Z_SITE_NAME"],
            "UPDATE_LEG": "true",
            "LEG_A_SITE_NAME": apne_params["A_SITE_NAME"],
            "LEG_NAME": apne_params["LEG_NAME"],
            "LEG_Z_SITE_NAME": apne_params["Z_SITE_NAME"],
        }

    logger.info(f"Adding {component} to circuit in Granite")
    url = granite_paths_url()
    data = put_granite(url, payload)

    if not isinstance(data, dict):
        msg = f"No data returned from Granite, unable to assign {component}"
        logger.error(msg)
        abort(500, msg)

    if data["retString"].lower() != "path updated":
        msg = f"Add {component} failed, Granite error {data['httpCode']}."
        logger.error(msg)
        abort(500, msg)

    logger.info(f"Assignment of {component} completed successfully")


def _put_parent_path(cid, path_rev, path_leg, parent_path_id, sequence):
    payload = {
        "PATH_NAME": cid,
        "PATH_REV": path_rev,
        "LEG_NAME": path_leg,
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": sequence,
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": parent_path_id,
    }
    url = granite_paths_url()
    put_granite(url, payload)


def _add_serviceable_shelf_uplink_path(cid, epl, side):
    path_elements = get_path_elements(cid, "&LVL=1&ELEMENT_TYPE=PORT")[0]

    shelf_tid = path_elements["TID"]
    path_rev = path_elements["PATH_REV"]
    path_leg = path_elements["LEG_NAME"]
    sequence = "1"

    if epl:
        if side == "z_side":
            # if epl and a_side has net new cj transport path (correct sequence)
            sequence = "2" if path_elements["SEQUENCE"] == "2" else "1"
        else:
            # if epl and a_side (sequence should always be 2 for epl a side)
            sequence = "2"

    parent_paths = get_granite(f"/circuitSites?CIRCUIT_NAME=%.{shelf_tid}&PATH_CLASS=P&WILD_CARD_FLAG=1")

    if isinstance(parent_paths, dict):
        abort(500, f"No parent path found for TID: {shelf_tid}")

    # Filter out trunked paths and overlay paths
    parent_paths = [
        path
        for path in parent_paths
        if path.get("SERVICE_TYPE") == "INT-ACCESS TO PREM TRANSPORT" and path.get("CIRCUIT_NAME").endswith(shelf_tid)
    ]

    if len(parent_paths) > 2:
        abort(500, f"Unexpected number of parent paths returned for TID: {shelf_tid}")
    elif len(parent_paths) == 2:
        parent_path_id_live = None
        parent_path_id_designed = None

        if parent_paths[0]["CIRCUIT_STATUS"] == "Live":
            parent_path_id_live = parent_paths[0]["CIRC_PATH_INST_ID"]

            if parent_paths[1]["CIRCUIT_STATUS"] == "Designed":
                parent_path_id_designed = parent_paths[1]["CIRC_PATH_INST_ID"]
        elif parent_paths[1]["CIRCUIT_STATUS"] == "Live":
            parent_path_id_live = parent_paths[1]["CIRC_PATH_INST_ID"]

            if parent_paths[0]["CIRCUIT_STATUS"] == "Designed":
                parent_path_id_designed = parent_paths[0]["CIRC_PATH_INST_ID"]

        if parent_path_id_live and parent_path_id_designed:
            _put_parent_path(cid, path_rev, path_leg, parent_path_id_designed, sequence)
            _put_parent_path(cid, path_rev, path_leg, parent_path_id_live, sequence)
        else:
            abort(500, f"Parent path for TID: {shelf_tid} is not in Live or Designed status")
    elif len(parent_paths) == 1:
        parent_path_id = parent_paths[0]["CIRC_PATH_INST_ID"]
        _put_parent_path(cid, path_rev, path_leg, parent_path_id, sequence)
    else:
        abort(500, f"No parent path with product service of INT-ACCESS TO PREM TRANSPORT for: {shelf_tid}")


def _add_parent_for_each_child(cid, parent_path_inst_id, num_of_circuits):
    for x in range(1, num_of_circuits + 1):
        circuit_id = f"{cid}.00{x}"

        # Set up and make the call
        url = get_circuit_site_url(cid=circuit_id)
        res = get_granite(url)

        # Validate that a list (and not a dict) of results are returned; assign the one and only expected entry to a var
        data = None

        try:
            data = res[0]
        except Exception:
            logger.exception(
                f"No records found in Granite circuitSites call for {circuit_id}. \nURL: {url} \nResponse: \n{res}"
            )
            abort(500, f"No circuit site data found in Granite for {circuit_id}", url=url, response=res)

        appe_params = {
            "PATH_NAME": data["CIRCUIT_NAME"],
            "CIRC_PATH_INST_ID": data["CIRC_PATH_INST_ID"],
            "PATH_REV": 1,
            "PARENT_PATH_INST_ID": parent_path_inst_id,
            "LEG_NAME": data["LEG_NAME"],
            "LEG_INST_ID": data["LEG_INST_ID"],
        }
        _add_parent_path_element(appe_params)


def clli_check(circuits: list) -> None:
    for circuit in circuits:
        for clli in "A_CLLI", "Z_CLLI":
            valid, reason = validate_hub_clli(circuit[clli])

            if not valid:
                logger.error(reason)
                abort(500, reason)


def _validate_and_add_parent_paths(
    cid: str,
    csip: list,
    l1: dict,
    product_name: str,
    side: str = "z_side",
    is_cw_cid: bool = False,
    is_aw_cid: bool = False,
    num_of_circuits: int = 0,
) -> None:
    circuits = []
    csip_dict = {}

    # finding sequence of transport path to make sure parent path and cloud are added correctly
    if side == "a_side":
        int_seq = int(l1.get("SEQUENCE")) + 1
        sequence = str(int_seq)
    else:
        sequence = l1.get("SEQUENCE")

    if len(csip) > 1:
        clli_check(csip)

        for circuit in csip:
            parent_path_inst_id = circuit["CIRC_PATH_INST_ID"]

            if parent_path_inst_id not in circuits:
                circuits.append(parent_path_inst_id)

        circuits.reverse()

        for path in circuits:
            if is_cw_cid or is_aw_cid:
                appe_params = {
                    "PATH_NAME": l1["PATH_NAME"],
                    "CIRC_PATH_INST_ID": l1["CIRC_PATH_INST_ID"],
                    "PATH_REV": l1["PATH_REV"],
                    "PARENT_PATH_INST_ID": path,
                    "LEG_NAME": l1["LEG_NAME"],
                    "LEG_INST_ID": l1["LEG_INST_ID"],
                }
                _add_parent_path_element(appe_params, sequence)

        csip_dict = csip[0]
    elif len(csip) == 1:
        clli_check(csip)
        csip_dict = csip[0]

        # get inst id for parent element to be assigned (and validate)
        parent_path_inst_id = csip_dict["CIRC_PATH_INST_ID"]

        # if parent element needs assignment we need to add parent path
        if is_cw_cid or is_aw_cid:
            appe_params = {
                "PATH_NAME": l1["PATH_NAME"],
                "CIRC_PATH_INST_ID": l1["CIRC_PATH_INST_ID"],
                "PATH_REV": l1["PATH_REV"],
                "PARENT_PATH_INST_ID": parent_path_inst_id,
                "LEG_NAME": l1["LEG_NAME"],
                "LEG_INST_ID": l1["LEG_INST_ID"],
            }

            _add_parent_path_element(appe_params, sequence)

    if num_of_circuits > 0 and product_name in {"PRI Trunk (Fiber)", "PRI Trunk(Fiber) Analog", "PRI Trunk (DOCSIS)"}:
        _add_parent_for_each_child(l1["PATH_NAME"], l1["CIRC_PATH_INST_ID"], num_of_circuits)

    # QW to AW transport added
    # Stop here and let next section of assign_parent_paths() finish the CW to QW transport and MPLS elements
    if is_aw_cid:
        return

    # use region mapping to get correct input for next call
    z_site_region, z_state, a_site_name = (csip_dict["Z_SITE_REGION"], csip_dict["Z_STATE"], csip_dict["A_SITE_NAME"])

    if "Wireless Internet Access" in product_name:
        if not is_aw_cid:
            apne_params = {
                "LEG_NAME": "1",
                "PATH_NAME": l1["PATH_NAME"],
                "PATH_INST_ID": l1["CIRC_PATH_INST_ID"],
                "ADD_ELEMENT": "true",
                "PATH_ELEM_SEQUENCE": "1",
                "PATH_ELEMENT_TYPE": "CLOUD",
                "CLOUD_INST_ID": "1220" if l1["MODEL"] == "W1850" else "1001",
            }
            _add_parent_network_element(apne_params)
    else:
        hub_clli = ""

        if product_name == "Carrier E-Access (Fiber)":
            # Get Z-side hub router CLLI since it can be different from the Z_CLLI
            l2_url = get_l2_url(cid)
            l2_resp = get_granite(l2_url)

            for element in reversed(l2_resp):
                if element["ELEMENT_CATEGORY"] == "ROUTER" and element["TID"].endswith("CW"):
                    hub_clli = element["A_CLLI"]
                    legacy_region = element["LEGACY_EQUIP_SOURCE"]
                    break

        if not hub_clli:
            hub_clli = csip_dict["A_CLLI"]
            legacy_region = None

        try:
            cw_path_elements = get_path_elements(cid, "&LVL=2&ELEMENT_CATEGORY=ROUTER")
            element_reference = cw_path_elements[0].get("ELEMENT_REFERENCE")
            tid = cw_path_elements[0].get("TID")
            vendor = cw_path_elements[0].get("VENDOR")
            legacy_region = cw_path_elements[0].get("LEGACY_EQUIP_SOURCE")
        except Exception:
            abort(500, f"No CW Path Elements found for cid: {cid}")

        if not edna_mpls_in_path(cid):
            edna_device = _edna_check(element_reference)

            if not edna_device and vendor == "JUNIPER":
                edna_device = onboard_and_exe_cmd(command="is_edna", hostname=tid, attempt_onboarding=False).get(
                    "result"
                )

            if not edna_device:
                cloud_address = region_network_mapping(z_site_region, z_state, hub_clli, legacy=legacy_region)
                # get inst id for parent network to be assigned
                parent_network_inst_id = circuit_site_info_network(cloud_address)

            if not is_aw_cid:
                if edna_device:
                    apne_params = {
                        "LEG_NAME": "1",
                        "PATH_NAME": l1["PATH_NAME"],
                        "PATH_INST_ID": l1["CIRC_PATH_INST_ID"],
                        "ADD_ELEMENT": "true",
                        "PATH_ELEM_SEQUENCE": sequence,
                        "PATH_ELEMENT_TYPE": "CLOUD",
                        "CLOUD_INST_ID": "1180",
                    }
                else:
                    apne_params = {
                        "PATH_NAME": l1["PATH_NAME"],
                        "CIRC_PATH_INST_ID": l1["CIRC_PATH_INST_ID"],
                        "PARENT_NETWORK_INST_ID": parent_network_inst_id,
                        "PATH_REV": l1["PATH_REV"],
                        "LEG_NAME": l1["LEG_NAME"],
                        "LEG_INST_ID": l1["LEG_INST_ID"],
                    }

                if side == "z_side":
                    _add_parent_network_element(apne_params, sequence)

                if product_name not in ("Carrier E-Access (Fiber)", "EPL (Fiber)"):
                    # populate A_SITE information for later retrieval during IP assignment (nn4)
                    a_site_params = {
                        "A_SITE_NAME": a_site_name,
                        "Z_SITE_NAME": l1["PATH_Z_SITE"],
                        "PATH_NAME": l1["PATH_NAME"],
                        "CIRC_PATH_INST_ID": l1["CIRC_PATH_INST_ID"],
                        "PATH_REV": l1["PATH_REV"],
                        "LEG_NAME": l1["LEG_NAME"],
                        "LEG_INST_ID": l1["LEG_INST_ID"],
                    }

                    _add_parent_network_element(a_site_params, a_site=True)


def assign_parent_paths_main(payload: dict) -> dict:
    cid = payload.get("cid")
    product_name = payload.get("product_name")
    service_type = payload.get("service_type")
    side = payload.get("side")
    type2 = payload.get("third_party_provided_circuit")
    number_of_circuits_in_group = 0
    if payload.get("number_of_circuits_in_group"):
        number_of_circuits_in_group = int(payload["number_of_circuits_in_group"])

    logger.debug(f"starting PE Creation on {cid}")

    if "Wireless Internet Access" in product_name or type2 == "Y":
        l1_url = get_l1_url(cid)
        l1_resp = get_granite(l1_url)

        try:
            l1 = l1_resp[0]
        except Exception:
            msg = f"No data in Granite response for {cid}."
            logger.exception(f"{msg}\nURL: {l1_url} \nResponse: \n{l1_resp}")
            abort(500, message=msg, url=l1_url, response=l1_resp)
        csip = circuit_site_info_path(cid, full_info=False)

        # changing region to NNI region for type II circuits if Z region is offnet
        if type2 == "Y" and product_name == "Fiber Internet Access":
            if csip[0]["Z_SITE_REGION"] == "OFF-NET" and csip[0].get("A_SITE_REGION"):
                nni = l1["ELEMENT_NAME"]
                url = get_circuit_site_url(nni)
                res = get_granite(url)
                csip[0]["Z_SITE_REGION"] = res[0]["A_SITE_REGION"]

                # changing A site name from CID to a site name from ENNI if OFFNET(type II)
                csip[0]["A_SITE_NAME"] = res[0]["A_SITE_NAME"]

        _validate_and_add_parent_paths(cid, csip, l1, product_name, is_aw_cid=False)
    else:
        epl = True if product_name == "EPL (Fiber)" else False

        if service_type in ["net_new_no_cj", "net_new_serviceable"]:
            # add shelf uplink parent path for serviceable shelf orders
            _add_serviceable_shelf_uplink_path(cid, epl, side)

        l1 = _get_circuit_info(cid, side)  # get initial circuit data

        # check whether cid parameter needs to be updated (which is if we only have partial QW -> ZW info)
        csip = None

        if l1.get("AW_CIRCUIT_NAME"):
            aw_cid = l1["AW_CIRCUIT_NAME"]
            csip = circuit_site_info_path(aw_cid, full_info=False)
            _validate_and_add_parent_paths(
                cid, csip, l1, product_name, side, is_aw_cid=True, num_of_circuits=number_of_circuits_in_group
            )

            # call get circuit info again to get updated data if AW circuit
            l1 = _get_circuit_info(cid, side)

        if l1.get("CW_CID"):
            cw_cid = l1["CW_CID"]
            csip = circuit_site_info_path(cw_cid, full_info=False)
            _validate_and_add_parent_paths(
                cid, csip, l1, product_name, side, is_cw_cid=True, num_of_circuits=number_of_circuits_in_group
            )
        else:
            cw_no_qw_cid = l1["ELEMENT_NAME"]
            csip = circuit_site_info_path(cw_no_qw_cid)
            _validate_and_add_parent_paths(
                cid, csip, l1, product_name, side, num_of_circuits=number_of_circuits_in_group
            )

        # checking to see if path is locally switched and cloud needs to be removed
        if epl and side == "a_side":
            loc_switch_check(l1["CIRC_PATH_INST_ID"], epl)

            area = cos_check(cid, "GOLD")

            if area.split()[-1] != "METRO":
                abort(500, "The EPL (Fiber) circuit is outside of the Metro area which is currently unsupported")

    msg = "Parent Paths & Cloud has been successfully added."
    response_payload = {"message": msg}

    logger.info(f"{msg} Response payload: \n{response_payload}")
    return response_payload
