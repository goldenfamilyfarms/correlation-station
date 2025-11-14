import logging
import re
from copy import deepcopy
from thefuzz import fuzz

from arda_app.bll.disconnect import mne_service_check
from arda_app.bll.disconnect_utils import get_job_type
from arda_app.bll.net_new.utils.shelf_utils import (
    get_circuit_side_info,
    get_vgw_shelf_info,
    get_zsite_voice,
    switch_sites_for_each_side,
)
from arda_app.dll.thor import thor_gsip_check
from common_sense.common.errors import abort
from arda_app.common.utils import path_regex_match
from arda_app.common.cd_utils import (
    validate_values,
    get_l1_url,
    granite_paths_url,
    granite_sites_put_url,
    granite_mne_url,
)
from arda_app.dll.granite import (
    put_granite,
    get_circuit_site_info,
    get_existing_shelf,
    get_equipid,
    get_granite,
    get_site_data,
    get_path_elements_l1,
    get_network_elements,
    update_network_status,
    get_path_elements,
    paths_from_site,
)

logger = logging.getLogger(__name__)


def update_circuit_status(
    pathid, path_instance=None, path_rev=None, status=None, service=None, leg=False, uda=False, product=""
):
    """Update the status of a circuit in Granite"""
    logger.debug(f"Executing circuit status change to {status} for {pathid}")

    url = granite_paths_url()
    get_url = f"{url}?CIRC_PATH_HUM_ID={pathid}"
    first_entry = {}

    if path_instance is None:
        logger.info(f"Obtaining circuit info for {pathid} using GET call to Granite paths endpoint")
        get_data = get_granite(get_url)

        if "retString" in get_data:
            logger.error(f"No records found in Granite for {pathid}")
            abort(500, f"Unable to locate circuit {pathid} in Granite")

        if len(get_data) > 1 and service not in ("bw_change", "change_logical"):
            logger.error(f"Existing revision found for {pathid}")
            abort(500, "Existing revision found for this circuit")
        elif len(get_data) > 2 and service in ("bw_change", "change_logical"):
            logger.error(f"There are 3 or more revisions for {pathid}")
            abort(500, f"There are 3 or more revisions for {pathid}")

        try:
            if len(get_data) > 1 and int(get_data[0].get("pathRev")) < int(get_data[1].get("pathRev")):
                first_entry = get_data[1]
            else:
                first_entry = get_data[0]
        except (IndexError, KeyError, AttributeError):
            logger.exception(f"Empty Granite response payload for {pathid}")
            abort(500, f"No records returned from Granite for Path ID: {pathid}")

        # Validate and assign required values
        missing = validate_values(first_entry, ["pathInstanceId", "pathRev"])

        if missing:
            logger.error(f"Granite response for GET call to paths endpoint missing {missing}")
            abort(500, f"Required data missing from Granite response for path validation: {missing}")

        path_instance, path_rev = first_entry["pathInstanceId"], first_entry["pathRev"]

    update_parameters = {
        "PATH_NAME": pathid,
        "PATH_INST_ID": path_instance,
        "PATH_REVISION": path_rev,
        "PATH_STATUS": status,
    }

    # Crossing logic with assign gsip
    if uda:
        slm_eligibility = "ELIGIBLE DESIGN"

        if service:
            if service in "quick_connect":
                slm_eligibility = "unsupported DESIGN"

        update_parameters["UDA"] = {
            "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
            "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
            "SERVICE TYPE": {"MANAGED SERVICE": "NO", "SERVICE MEDIA": "FIBER"},
            "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": slm_eligibility},
        }

    # Change status in Granite
    logger.info(
        "Executing circuit update via PUT call to Granite paths endpoint. "
        f"\nPayload sent to Granite: \n{update_parameters}"
    )
    data = put_granite(url, update_parameters)

    missing = validate_values(data, ["pathId", "status"])

    if missing:
        logger.error(f"Granite status update response payload missing {missing}")
        abort(
            500, f"Missing the following values in Granite response while attempting to update circuit status: {missing}"
        )

    # If nothing else required return values
    if not leg:
        resp = {"cid": data["pathId"], "status": data["status"]}
        logger.info(f"Status update operation completed successfully. \nResponse payload: \n{resp}")
        return resp

    """ If a leg value was passed in, get new circuit info from Granite and continue updating """
    # Get path data (again)
    logger.info(f"Updating Granite records for {leg}")
    get_url = get_l1_url(pathid)
    circuit_info_data = get_granite(get_url)

    if "retString" in circuit_info_data:
        logger.error(f"No Granite records returned for {pathid} during update for {leg}")
        abort(500, f"No Granite records found for {pathid}")

    # Set up put params
    path, elem_ref, path_rev = None, None, None

    for element in circuit_info_data:
        if element["ELEMENT_NAME"].endswith("ZW"):
            path = element["ELEMENT_NAME"]
            elem_ref = element["ELEMENT_REFERENCE"]
            path_rev = element["PATH_REV"]

            # we should not update the status of a path that is already live
            if element["ELEMENT_STATUS"] == "Live":
                resp = {"cid": data["pathId"], "status": data["status"]}
                return resp

    # Added for circuits with no ZW transports
    if not path:
        resp = {"cid": data["pathId"], "status": data["status"]}
        return resp

    update_parameters = {
        "PATH_NAME": path,
        "PATH_INST_ID": elem_ref,
        "PATH_REVISION": path_rev,
        "PATH_STATUS": status,
        "UDA": {"SERVICE TYPE": {"SERVICE MEDIA": "FIBER"}},
    }

    # Change circuit status in Granite
    logger.info(
        f"Executing PUT to granite paths endpoint for circuit data update for {pathid} and {leg}."
        f"\nPayload sent to Granite: \n{update_parameters}"
    )
    second_data = put_granite(url, update_parameters)

    if not second_data.get("pathId"):
        logger.error(f"Missing value: 'pathId' in Granite response while updating status for Path ID: {pathid}")
        abort(500, f"Missing value: 'pathId' in Granite response while updating status for Path ID: {pathid}")

    resp = {"cid": data["pathId"], "ethernet_transport": second_data["pathId"], "status": data["status"]}

    logger.info(f"Granite Status and UDA update operation completed successfully. \nResponse sent: \n{resp}")
    return resp


def disco_path_update(pathid, body, switch_sides=False):
    # Extract CID from SF string
    cid = path_regex_match(pathid)
    if isinstance(cid, list):
        if len(set(cid)) == 1:
            pathid = cid[0]
        else:
            abort(500, f"Multiple different CIDs detected within: {pathid}")
    else:
        abort(500, f"Unable to determine CID from: {pathid}")

    url = granite_paths_url()
    get_url = f"{url}?CIRC_PATH_HUM_ID={pathid}"
    resp = get_granite(get_url)
    if not isinstance(resp, list) and resp.get("retString") and "No records found" in resp["retString"]:
        abort(500, f"No path info found for CID: {pathid}")
    elif len(resp) > 1:
        for path in resp:
            if path.get("status") == "Live":
                disco_data = path
                break
    else:
        disco_data = resp[0]

    skip_setting_circuit_status = False
    site_name = disco_data["zSideSiteName"]
    product_name = body["product_name"]

    # grab service type to determine if we can skip setting the circuit status to pending decommission
    if "Managed Network Edge" in product_name:
        service_type = disco_data["serviceMedia"]
        body["engineering_job_type"] = "Full Disconnect"

        if service_type not in ("BYO", "COAX"):
            skip_setting_circuit_status = True

    # for EPL (Fiber) circuits, if needed, reassign Z-side site name based on service location address
    if product_name.upper() in ("EPL (FIBER)"):
        service_loc = (
            body.get("service_location_address")
            if body.get("service_location_address")
            else abort(500, "Service location address is missing")
        )
        if str(service_loc).isspace():
            abort(500, "Missing service location address")
        # check circuit status
        circuit_data = get_circuit_side_info(pathid)
        if circuit_data["status"].upper() == "PENDING DECOMMISSION":
            skip_setting_circuit_status = True

    path_order_num = ""

    if len(f"{disco_data.get('orderNumber', '')},D-{body['engineering_name']}") > 50:
        path_order_num = disco_data.get("orderNumber", "").split(",")
        path_order_num = f"{','.join(path_order_num[1:])},D-{body['engineering_name']}"
    else:
        path_order_num = f"{disco_data.get('orderNumber', '')},D-{body['engineering_name']}"

    # update circuit status
    status = body["status"]
    disco_cid_data = None
    if not skip_setting_circuit_status:
        update_parameters = {
            "PATH_NAME": pathid,
            "PATH_INST_ID": disco_data["pathInstanceId"],
            "PATH_REVISION": disco_data["pathRev"],
            "PATH_STATUS": status,
            "PATH_DECOMM_DATE": body["due_date"],
            "PATH_ORDER_NUM": path_order_num,
        }

        logger.info(
            "Executing circuit update via PUT call to Granite paths endpoint. "
            f"\nPayload sent to Granite: \n{update_parameters}"
        )

        disco_cid_data = put_granite(url, update_parameters)
    elif body["product_name"].upper() in ("EPL (FIBER)"):
        disco_cid_data = {}
        data = get_granite(get_url)
        if data and isinstance(data, list):
            disco_cid_data["pathId"] = data[0].get("pathId", "")
            disco_cid_data["pathRev"] = data[0].get("pathRev", "")
            disco_cid_data["status"] = data[0].get("status", "")
            disco_cid_data["pathInstanceId"] = data[0].get("pathInstanceId", "")

    logger.info(f"Granite Path Status and Decommission Date updated successfully. \nResponse sent: \n{disco_cid_data}")

    if "EP-LAN (Fiber)" in body["product_name"]:
        path_elements = get_path_elements(pathid)
        network_inst_id = ""
        try:
            for element in path_elements:
                if element["ELEMENT_CATEGORY"] == "VPLS SVC":
                    network_inst_id = element.get("ELEMENT_REFERENCE")
                    break
        except Exception:
            logger.error("Unable to find network instant ID")

        if network_inst_id:
            network_elements = get_network_elements(network_inst_id)
        else:
            abort(500, f"Network instance ID for {body.get('cid')} not found")
        decom_status = get_decom_status(network_elements)

        if decom_status:
            logger.debug(" ---> call update_network_status <---")
            update_network_status_resp = update_network_status(network_inst_id, "Pending Decommission")
            logger.debug(f"update_network_status_resp - {update_network_status_resp}")

    voice_product_found = is_voice_product(body["product_name"])
    if voice_product_found:
        if is_pri_service(pathid):
            # set .00n child circuits to pending decom
            z_site_info = get_zsite_voice(pathid)
            for i in z_site_info:
                if i["CIRCUIT_NAME"] == pathid:
                    continue  # parent voice circuit's status was set earlier
                circ_name = i["CIRCUIT_NAME"]
                set_circuit_status(circ_name, body)

        # set VGW shelf to pending decom
        vgw_shelf = get_vgw_shelf_info(pathid)
        if not is_supported_vgw_shelf(vgw_shelf["SHELF_NAME"]):
            msg = f"Unsupported VGW shelf {vgw_shelf} found"
            logger.info(msg)
        path_elements = get_path_elements_l1(pathid)
        disco_vgw_data = disco_vgw_update(path_elements, vgw_shelf["SHELF_NAME"], site_name, status)
        # for hosted voice, update network elements to pending decom
        if "HOSTED VOICE" in body["product_name"].upper():
            disco_hosted_voice_update(pathid, path_elements, body)

    if body["engineering_job_type"].lower() == "partial disconnect":
        return {"message": "Partial Disconnect complete", "data": disco_cid_data, "status": "Pending Decommission"}
    elif body["engineering_job_type"].lower() == "full disconnect":
        site_info = get_zsite_voice(pathid)

        # for EPL (Fiber) circuits
        if switch_sides:
            # call helper method to swap A-side and Z-side site names in site_info
            switch_site_info = deepcopy(site_info)
            site_info = switch_sites_for_each_side(switch_site_info)
            site_name = site_info[0]["Z_SITE_NAME"]

        circuit_names = [info["CIRCUIT_NAME"] for info in site_info]
        # call paths_from_sites to get all paths for the site
        paths = paths_from_site(site_info[0]["Z_SITE_NAME"])
        live_paths = [path["PATH_NAME"] for path in paths if path["SITE_STATUS"] == "Live"]
        filtered_paths = [
            path
            for path in live_paths
            if path not in circuit_names and (path.upper().endswith("CHTR") or path.upper().endswith("TWCC"))
        ]

        # update site status
        if len(filtered_paths) == 0:
            disco_site_data = disco_site_update(site_name, status)
        else:
            disco_site_data = "Multiple live paths found. Did not disconnect site"

        path_elements = get_path_elements_l1(pathid)

        if len(path_elements) == 0:
            abort(500, f"No elements found for pathid: {pathid}")

        # update transport path and cpe status
        disco_transport_data = ""
        disco_cpe_data = ""
        if "DOCSIS" not in product_name.upper():
            if "Managed Network Edge" in product_name:
                url = granite_mne_url(disco_data["pathInstanceId"])
                resp = get_granite(url)
                cpe_installer, _, tid = mne_service_check(resp, path_elements, True)
                if cpe_installer == "Yes":
                    disco_cpe_data = disco_cpe_update(path_elements, tid, site_name, status, switch_sides=switch_sides)
            else:
                disco_transport_data = disco_transport_update(
                    path_elements, site_name, status, switch_sides=switch_sides
                )
                tid = disco_transport_data["pathId"].split(".")[3]
                disco_cpe_data = disco_cpe_update(path_elements, tid, site_name, status, switch_sides=switch_sides)

        resp = {
            "message": "Full Disconnect complete",
            "cid_disconnect_data": disco_cid_data,
            "site_disconnect_data": disco_site_data,
            "transport_disconnect_data": disco_transport_data,
            "cpe_disconnect_data": disco_cpe_data,
            "status": "Pending Decommission",
        }

        if voice_product_found:
            resp["cpe_disconnect_data"] = disco_vgw_data

        return resp


def disco_site_update(site_name, status):
    site_data = get_site_data(site_name)

    try:
        site_type = site_data[0]["siteType"]
    except (IndexError, KeyError):
        abort(500, f"No site data found for site: {site_name}")

    update_parameters = {"SITE_NAME": site_name, "SITE_TYPE": site_type, "SITE_STATUS": status}

    logger.info(
        f"Executing site update via PUT call to Granite sites endpoint. \nPayload sent to Granite: \n{update_parameters}"
    )

    try:
        data = put_granite(granite_sites_put_url(), update_parameters, timeout=90)
    except Exception:
        abort(500, f"Issue updating site in granite. Update parameters: {update_parameters}")

    logger.info(f"Granite Site Status updated successfully. \nResponse sent: \n{data}")

    return data


def disco_transport_update(path_elements, site_name, status, switch_sides=False):
    zw_paths = []

    path_site = "PATH_Z_SITE" if not switch_sides else "PATH_A_SITE"
    try:
        for element in path_elements:
            if (
                (element["ELEMENT_NAME"].endswith("ZW"))
                and (element[path_site] == site_name)
                and ("MGMT" not in element["LEG_NAME"])
            ):
                zw_paths.append(element)
    except (KeyError, IndexError):
        abort(500, "No elements found for CID")

    if len(zw_paths) == 0:
        abort(500, "No path elements ending in ZW found")
    elif len(zw_paths) > 1:
        # determine the transport path for the Z-side ZW device
        for elem in zw_paths:
            if site_name and (site_name == elem["Z_SITE_NAME"]) and (elem["ELEMENT_STATUS"] in ["Live"]):
                zw_paths = [elem]
                break
        else:
            msg = f"Transport path for ZW device at {site_name} is not found or not Live"
            abort(500, msg)

    transport_path = zw_paths[0]["ELEMENT_NAME"]
    url = granite_paths_url()
    get_url = f"{url}?CIRC_PATH_HUM_ID={transport_path}"
    granite_resp = get_granite(get_url)

    try:
        disco_data = granite_resp[0]
        update_parameters = {
            "PATH_NAME": transport_path,
            "PATH_INST_ID": disco_data["pathInstanceId"],
            "PATH_REVISION": disco_data["pathRev"],
            "PATH_STATUS": status,
        }
    except (IndexError, KeyError):
        abort(500, f"No path info found for transport path: {transport_path}")

    logger.info(
        "Executing circuit update via PUT call to Granite paths endpoint. "
        f"\nPayload sent to Granite: \n{update_parameters}"
    )

    try:
        data = put_granite(url, update_parameters)

        if data["pathId"] is None:
            abort(500, f"Issue updating transport path in granite. Update parameters: {update_parameters}")
    except Exception:
        abort(500, f"Issue updating transport path in granite. Update parameters: {update_parameters}")

    logger.info(f"Granite Transport Status updated successfully. \nResponse sent: \n{data}")

    return data


def disco_vgw_update(path_elements, tid, site_name, status):
    vgw = []

    for element in path_elements:
        if tid and element["TID"]:
            if (tid in element["TID"]) and (element["PATH_Z_SITE"] == site_name):
                vgw.append(element)

    if len(vgw) == 0:
        abort(500, "No VGW found")
    elif len(vgw) > 1:
        # check if VGW has same element name and reference
        element_name = vgw[0]["ELEMENT_NAME"]
        element_reference = vgw[0]["ELEMENT_REFERENCE"]
        for element in vgw:
            if element["ELEMENT_NAME"] == element_name and element["ELEMENT_REFERENCE"] == element_reference:
                continue
            else:
                abort(500, "More than 1 VGW found")
        update_parameters = {
            "SHELF_NAME": vgw[0]["ELEMENT_NAME"],
            "SHELF_INST_ID": vgw[0]["ELEMENT_REFERENCE"],
            "SHELF_STATUS": status,
        }
    else:
        update_parameters = {
            "SHELF_NAME": vgw[0]["ELEMENT_NAME"],
            "SHELF_INST_ID": vgw[0]["ELEMENT_REFERENCE"],
            "SHELF_STATUS": status,
        }

    logger.info(
        "Executing vgw update via PUT call to Granite shelves endpoint. "
        f"\nPayload sent to Granite: \n{update_parameters}"
    )

    try:
        data = put_granite("/shelves", update_parameters)

        if data["retString"] != "Shelf Updated":
            abort(500, f"Issue updating vgw in granite. Update parameters: {update_parameters}")
    except Exception:
        abort(500, f"Issue updating vgw in granite. Update parameters: {update_parameters}")

    logger.info(f"Granite VGW Status updated successfully. \nResponse sent: \n{data}")

    return data


def disco_cpe_update(path_elements, tid, site_name, status, switch_sides=False):
    cpe = []

    path_site = "PATH_Z_SITE" if not switch_sides else "PATH_A_SITE"
    for element in path_elements:
        if element["TID"] == tid and element[path_site] == site_name:
            cpe.append(element)

    if len(cpe) == 0:
        abort(500, "No CPE found")
    elif len(cpe) > 1 and (cpe[0].get("TID", "") != cpe[1].get("TID", "")):
        abort(500, "More than 1 CPE found")
    else:
        update_parameters = {
            "SHELF_NAME": cpe[0]["ELEMENT_NAME"],
            "SHELF_INST_ID": cpe[0]["ELEMENT_REFERENCE"],
            "SHELF_STATUS": status,
        }

    logger.info(
        "Executing cpe update via PUT call to Granite shelves endpoint. "
        f"\nPayload sent to Granite: \n{update_parameters}"
    )

    try:
        data = put_granite("/shelves", update_parameters)

        if data["retString"] != "Shelf Updated":
            abort(500, f"Issue updating cpe in granite. Update parameters: {update_parameters}")
    except Exception:
        abort(500, f"Issue updating cpe in granite. Update parameters: {update_parameters}")

    logger.info(f"Granite CPE Status updated successfully. \nResponse sent: \n{data}")

    return data


def get_decom_status(network_elements):
    for element in network_elements:
        if element.get("ELEMENT_STATUS") != "Pending Decommission" and element.get("ELEMENT_STATUS") != "Decommissioned":
            return False
    return True


def is_voice_product(product_name: str) -> bool:
    """
    Determine if a circuit is a voice product

    Arg:
        product_name (str): product name of a circuit

    Returns:
        True: circuit is a voice product
        False: circuit is a non-voice product
    """
    hosted = ["Hosted Voice - (Fiber)", "Hosted Voice - (DOCSIS)", "Hosted Voice - (Overlay)"]
    pri = ["PRI Trunk (Fiber)", "PRI Trunk (DOCSIS)", "PRI Trunk(Fiber) Analog"]
    sip = ["SIP - Trunk (Fiber)", "SIP - Trunk (DOCSIS)", "SIP Trunk(Fiber) Analog"]
    for prod in hosted + pri + sip:
        if product_name == prod:
            return True

    return False


def is_pri_service(cid: str) -> bool:
    """
    Determine if a voice circuit is a PRI service

    Arg:
        cid (str): circuit ID

    Returns:
        True: if circuit is a PRI service
        False: if circuit is a not a PRI service
    """
    pri_service = "CUS-VOICE-PRI"
    resp = get_circuit_site_info(cid)
    if resp:
        if isinstance(resp, list):
            try:
                if resp[0]["SERVICE_TYPE"] == pri_service:
                    return True
            except (KeyError, IndexError, AttributeError):
                msg = f"Unable to determine service type of circuit site at {cid}"
                logger.error(msg)
                abort(500, msg)

    return False


def is_supported_vgw_shelf(shelf_name: str) -> bool:
    """
    Calculate whether a VGW device is supported or not

    Arg:
        shelf_name (str): TID of the VGW device

    Returns:
        True: if VGW shelf is on the supported list
        False: if VGW shelf is not on the supported list
    """
    resp = False

    # legacy Cisco voice models requiring support
    cisco = ["IAD2431", "ISR 2901", "ISR2821", "ISR (G2) 2921"]
    # please keep these voice gateway device models current with https://eset.chtrse.com/voice_gateway_picker
    adtran = ["908E Gen 3", "924 Gen 3", "3430 V Gen2", "4430 V", "NV644", "NV3430", "NV4430", "TA904 Gen 2"]
    audiocodes = ["M500B", "M800B", "M800C", "M1000B", "M3000B", "M4000B", "MP114", "MP118", "MP124E"]
    innomedia = ["9378-4B", "10K-MDX"]

    # verify format of vgw device tid is in alignment
    # with https://chalk.charter.com/display/public/NPD/Equipment+Naming+Standards
    # e.g. G(n)1	Line/Access Gateway
    #      G(n)W	Router
    #      where (n)	Numeric between 0-9
    vgw_regex = r"([A-Z0-9-]{8}[G][0-9]{1}[1|W])"
    if not re.findall(vgw_regex, shelf_name):
        msg = f"{shelf_name} is an unsupported VGW device TID format"
        logger.error(msg)

    # check vgw device model against supported ones
    data = get_equipid(shelf_name)
    if data:
        if isinstance(data, list):
            try:
                equip_model = data[0]["EQUIP_MODEL"]
            except (KeyError, IndexError, AttributeError):
                msg = f"Unable to find equipment model for VGW shelf {shelf_name}"
                logger.error(msg)
                abort(500, msg)
            for model_id in cisco + adtran + audiocodes + innomedia:
                if model_id in equip_model:
                    resp = True
                    break

    return resp


def set_circuit_status(pathid: str, body: dict):
    """
    Update circuit with status passed-in via body parameter

    Args:
        pathid (str): circuit ID
        body (dict): payload data

    Returns:
        None
    """
    url = granite_paths_url()
    get_url = f"{url}?CIRC_PATH_HUM_ID={pathid}"
    granite_resp = get_granite(get_url)

    try:
        disco_data = granite_resp[0]
        # zsite_name = disco_data["zSideSiteName"]
    except IndexError:
        abort(500, f"No path info found for CID: {pathid}")

    path_order_num = ""

    if len(f"{disco_data['orderNumber']},D-{body['engineering_name']}") > 50:
        path_order_num = disco_data["orderNumber"].split(",")
        path_order_num = f"{','.join(path_order_num[1:])},D-{body['engineering_name']}"
    else:
        path_order_num = f"{disco_data['orderNumber']},D-{body['engineering_name']}"

    status = body["status"]
    update_parameters = {
        "PATH_NAME": pathid,
        "PATH_INST_ID": disco_data["pathInstanceId"],
        "PATH_REVISION": disco_data["pathRev"],
        "PATH_STATUS": status,
        "PATH_DECOMM_DATE": body["due_date"],
        "PATH_ORDER_NUM": path_order_num,
    }

    logger.info(
        "Executing circuit update via PUT call to Granite paths endpoint. "
        f"\nPayload sent to Granite: \n{update_parameters}"
    )

    disco_cid_data = put_granite(url, update_parameters)

    logger.info(f"Granite Path Status and Decommission Date updated successfully. \nResponse sent: \n{disco_cid_data}")
    return


def disco_hosted_voice_update(pathid: str, path_elements: list, body: dict):
    """
    Update the status of switches on a hosted voice network

    Args:
        path_id (str): circuit ID
        path_elements (list): network elements of hosted voice circuit
        body (dict): payload data

    Returns:
        None
    """
    hosted_voice_network_id = None
    hosted_voice_transport_paths = []
    hosted_voice_shelf = None
    hosted_voice_shelf_id = None

    # from path elements, retrieve network ID of managed voice ethernet transport path
    for elem in path_elements:
        if (elem.get("ELEMENT_CATEGORY").upper() == "ETHERNET TRANSPORT") and (
            "NETWORK LINK" in elem.get("ELEMENT_TYPE").upper()
        ):
            hosted_voice_network_id = elem.get("ELEMENT_REFERENCE")
            break
    if not hosted_voice_network_id:
        msg = f"Unable to find hosted voice network ID for {pathid}"
        logger.error(msg)
        abort(500, msg)

    # from network elements, get vgw shelf and ethernet transport path(s) from vgw shelf to switch(es)
    network_elements = get_network_elements(hosted_voice_network_id)
    if isinstance(network_elements, list):
        for elem in network_elements:
            if (elem.get("ELEMENT_TYPE").upper() == "PATH") and (
                elem.get("ELEMENT_CATEGORY").upper() == "ETHERNET TRANSPORT"
            ):
                hosted_voice_transport_paths.append(elem.get("ELEMENT_NAME"))
            elif (elem.get("ELEMENT_TYPE").upper() == "PORT") and (elem.get("ELEMENT_CATEGORY").upper() == "ROUTER"):
                hosted_voice_shelf = elem.get("ELEMENT_NAME")
                hosted_voice_shelf_id = elem.get("ELEMENT_REFERENCE")

        if not hosted_voice_transport_paths:
            msg = f"Unable to find hosted voice transport paths for {pathid}"
            logger.error(msg)
            abort(500, msg)
        if (not hosted_voice_shelf) and (not hosted_voice_shelf_id):
            msg = f"Unable to find hosted voice shelf for {pathid}"
            logger.error(msg)
            abort(500, msg)

    # for each ethernet transport path, update hosted voice switch status (to pending decom)
    for path in hosted_voice_transport_paths:
        hosted_voice_path_elements = get_path_elements_l1(path)
        for elem in hosted_voice_path_elements:
            if (elem.get("ELEMENT_TYPE").upper() == "PORT") and (elem.get("ELEMENT_CATEGORY").upper() == "SWITCH"):
                switch = elem.get("ELEMENT_NAME")
                switch_id = elem.get("ELEMENT_REFERENCE")
                element_category = elem.get("ELEMENT_CATEGORY")
                logger.info(f"Hosted voice {element_category} found: {switch} / {element_category} ID: {switch_id}")
                update_parameters = {"SHELF_NAME": switch, "SHELF_INST_ID": switch_id, "SHELF_STATUS": body["status"]}
                logger.info(
                    "Executing hosted voice switch update via PUT call to Granite shelves endpoint. "
                    f"\nPayload sent to Granite: \n{update_parameters}"
                )
                try:
                    data = put_granite("/shelves", update_parameters)

                    if data["retString"] != "Shelf Updated":
                        abort(
                            500,
                            f"Issue updating hosted voice {element_category} in granite."
                            f" Update parameters: {update_parameters}",
                        )
                except Exception:
                    abort(500, f"Issue updating hosted voice switch in granite. Update parameters: {update_parameters}")
                logger.info(f"Granite Hosted Voice Switch Status updated successfully. \nResponse sent: \n{data}")
                break

        # for the current ethernet transport path from vgw shelf to switch, set its status (to pending decom)
        url = granite_paths_url()
        get_url = f"{url}?CIRC_PATH_HUM_ID={path}"
        granite_resp = get_granite(get_url)
        try:
            disco_data = granite_resp[0]
            update_parameters = {
                "PATH_NAME": path,
                "PATH_INST_ID": disco_data["pathInstanceId"],
                "PATH_REVISION": disco_data["pathRev"],
                "PATH_STATUS": body["status"],
            }
        except (IndexError, KeyError):
            abort(500, f"No path info found for hosted voice transport path: {path}")
        logger.info(
            "Executing circuit update via PUT call to Granite paths endpoint. "
            f"\nPayload sent to Granite: \n{update_parameters}"
        )

        try:
            data = put_granite(url, update_parameters)
            if data["pathId"] is None:
                abort(
                    500, f"Issue updating hosted voice transport path in granite. Update parameters: {update_parameters}"
                )
        except Exception:
            abort(500, f"Issue updating hosted voice transport path in granite. Update parameters: {update_parameters}")
        logger.info(f"Granite Hosted Voice Transport Status updated successfully. \nResponse sent: \n{data}")
        break

    for elem in path_elements:
        if elem.get("ELEMENT_CATEGORY").upper() == "CABLE MODEM":
            modem = elem.get("ELEMENT_NAME")
            modem_id = elem.get("ELEMENT_REFERENCE")
            element_category = elem.get("ELEMENT_CATEGORY")
            logger.info(f"Hosted voice {element_category} found: {modem} / {element_category} ID: {modem_id}")
            update_parameters = {"SHELF_NAME": modem, "SHELF_INST_ID": modem_id, "SHELF_STATUS": body["status"]}
            logger.info(
                "Executing hosted voice modem update via PUT call to Granite shelves endpoint. "
                f"\nPayload sent to Granite: \n{update_parameters}"
            )
            try:
                data = put_granite("/shelves", update_parameters)

                if data["retString"] != "Shelf Updated":
                    abort(
                        500,
                        f"Issue updating hosted voice {element_category} in granite."
                        f" Update parameters: {update_parameters}",
                    )
            except Exception:
                abort(500, f"Issue updating hosted voice Modem in granite. Update parameters: {update_parameters}")
            logger.info(f"Granite Hosted Voice Modem Status updated successfully. \nResponse sent: \n{data}")
            break
    # update hosted voice network status (to pending decom)
    logger.debug(" ---> call update_network_status <---")
    update_network_status_resp = update_network_status(hosted_voice_network_id, body["status"])
    logger.debug(f"hosted voice update_network_status_resp - {update_network_status_resp}")
    return


def check_thor(pathid, product_name, designed):
    """GSIP check for live and designed circuits"""

    compliant, data = thor_gsip_check(pathid, product_name, designed)
    logger.debug(f"THOR GSIP Compliance result: {compliant} \nTHOR GSIP Compliance data: \n{data}")

    if not compliant:
        logger.error(f"THOR GSIP compliance check failed for {pathid}")
        abort(500, f"GSIP compliance check failed for {pathid}. \nTHOR results: \n{data}")


def disco_epl(pathid: str, body: dict) -> list:
    responses = []
    service_location_address = body.get("service_location_address")
    circuit_info = get_circuit_side_info(pathid)
    a_side_site_name = circuit_info.get("aSideSiteName", "")
    z_side_site_name = circuit_info.get("zSideSiteName", "")
    a_side_site_addr = a_side_site_name.split("/")[-1] if a_side_site_name else ""
    z_side_site_addr = z_side_site_name.split("/")[-1] if z_side_site_name else ""
    a_side_clli = a_side_site_name.split("-")[0] if a_side_site_name else ""
    z_side_clli = z_side_site_name.split("-")[0] if z_side_site_name else ""

    # determine current side of the circuit the service location address is pointing to
    # as well as identifying the service location address on the opposite side of the circuit
    a_side_ratio = fuzz.partial_ratio(service_location_address, a_side_site_name)
    z_side_ratio = fuzz.partial_ratio(service_location_address, z_side_site_name)
    switch_sides = False
    if a_side_ratio > z_side_ratio:
        clli = a_side_clli
        site_name = a_side_site_name
        opposite_clli = z_side_clli
        opposite_site_name = z_side_site_name
        switch_sides = True
    elif z_side_ratio > a_side_ratio:
        clli = z_side_clli
        site_name = z_side_site_name
        opposite_clli = a_side_clli
        opposite_site_name = a_side_site_name
    else:
        abort(
            500,
            f"Unable to determine which side of the circuit is being referenced by "
            f"service location address {service_location_address}",
        )

    # retrieve ZW device at specified service location address of circuit
    zw = get_zw_device_tid(pathid, clli, site_name)

    # calculate job type at original service location address of circuit
    job_type = get_job_type(pathid, zw, switch_sides=switch_sides)
    if job_type:
        body["engineering_job_type"] = f"{job_type} disconnect"
    else:
        abort(500, f"Unable to determine job type of {pathid} at {zw}")

    # process original side of circuit
    resp = disco_path_update(pathid, body, switch_sides=switch_sides)
    responses.append(resp)

    # prep to process opposite side of circuit
    new_body = deepcopy(body)
    switch_sides = False if switch_sides else True

    # retrieve ZW device at opposite side of circuit
    zw = get_zw_device_tid(pathid, opposite_clli, opposite_site_name)

    # calculate job type at opposite side of circuit
    job_type = get_job_type(pathid, zw, switch_sides=switch_sides)
    if job_type:
        new_body["engineering_job_type"] = f"{job_type} disconnect"
    else:
        abort(500, f"Unable to determine job type of {pathid} at {zw}")

    # make sure to define the opposite side's service location address
    new_body["service_location_address"] = (
        a_side_site_addr if opposite_site_name == a_side_site_name else z_side_site_addr
    )

    # process opposite side of disconnect order
    resp = disco_path_update(pathid, new_body, switch_sides=switch_sides)
    responses.append(resp)
    return responses


def get_zw_device_tid(pathid: str, clli: str, site_name: str) -> str:
    zw = ""
    data = get_existing_shelf(clli, site_name)
    if data and isinstance(data, list):
        if len(data) == 1:
            zw = data[0].get("TARGET_ID", "")
        elif len(data) > 1:
            params = "&LVL=1&ELEMENT_TYPE=PORT"
            path_elements_resp = get_path_elements(pathid, params)
            if path_elements_resp and isinstance(path_elements_resp, list):
                for elem in path_elements_resp:
                    if elem.get("A_SITE_NAME", "") == site_name:
                        zw = elem.get("TID", "")
                        break
                else:
                    abort(500, f"Unable to retrieve tid of ZW device at {site_name}")
                if not zw:
                    abort(500, f"Missing TID of ZW device at {site_name}")
        else:
            abort(500, f"No existing ZW shelf at {site_name}")
    else:
        abort(500, f"Unable to retrieve ZW device of circuit at {site_name}")
    return zw
