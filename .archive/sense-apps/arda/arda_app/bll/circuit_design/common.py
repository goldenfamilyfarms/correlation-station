import logging
import datetime
from json import JSONDecodeError

from arda_app.common.bw_operations import normalize_bandwidth_values
from arda_app.common.cd_utils import granite_paths_get_url, granite_paths_url, granite_networks_url
from common_sense.common.errors import abort
from arda_app.dll.granite import (
    get_granite,
    put_granite,
    get_ip_subnets,
    get_path_elements,
    get_attributes_for_path,
    get_circuit_site_info,
)

logger = logging.getLogger(__name__)


def _validate_payload(body, pathid):
    """Validate and format the data sent through intake"""
    logger.info(f"Normalizing intake bandwidth for {pathid}")

    # TODO: Move this to circuitpath intake, adapt to standard used for other endpoints
    if not all((k in body for k in ("bw_unit", "bw_value"))):
        logger.error("Required value missing from intake payload")
        abort(500, message="Circuit ID, Bandwidth Unit, and Value are all mandatory to complete this Update")

    bw_value = body["bw_value"]
    bw_unit = body["bw_unit"].upper()

    # Assigned the normalized value to its own var so we don't lose the request
    mbps_bw_val = normalize_bandwidth_values(bw_value, bw_unit)

    if "M" in bw_unit[0]:
        bw_unit = "Mbps"
    elif "G" in bw_unit[0]:
        bw_unit = "Gbps"
    else:
        logger.error(f"Unsupported bandwidth unit {bw_unit}, must be either Mbps or Gbps")
        abort(500, f"Unsupported bandwidth unit {bw_unit}, must be either Mbps or Gbps")

    logger.info(
        f"Bandwidth normalization complete \n'bw_value': {bw_value} "
        f"\n'bw_unit': {bw_unit} \n'mbps_bw_val': {mbps_bw_val}"
    )
    return bw_value, bw_unit, mbps_bw_val


def validate_payload_express_bw_upgrade(body):
    """Validate and format the data sent through intake"""

    if not all((k in body for k in ("bw_speed", "bw_unit", "cid", "engineering_name"))):
        logger.error("Required values missing from intake payload")
        abort(
            500, message="Bandwidth Speed and Unit, CID, and Engineering Name are all mandatory to complete this Update"
        )

    bw_speed = body.get("bw_speed")
    bw_unit = body.get("bw_unit")

    if bw_unit.upper() == "MBPS" and int(bw_speed) > 999:
        abort(500, "Bandwith speed is greater than 999 Mbps please convert to Gbps")
    elif bw_unit.upper() == "GBPS" and int(bw_speed) > 800:
        abort(500, "Bandwith speed is greater than 800 Gbps please check bandwidth conversion")

    # Assign the normalized value to its own var so we don't lose the request
    mbps_bw_val = normalize_bandwidth_values(bw_speed, bw_unit.upper())

    logger.info(
        f"Bandwidth normalization complete \n'bw_speed': {bw_speed} "
        f"\n'bw_unit': {bw_unit} \n'mbps_bw_val': {mbps_bw_val}"
    )
    return bw_speed, bw_unit, mbps_bw_val


def _check_granite_bandwidth(pathid):
    """Obtain the current circuit bandwidth from Granite"""

    logger.info(f"Validating existing circuit revision in Granite for {pathid}")

    url = granite_paths_get_url(pathid)
    # This will get the circuit bandwidth from Granite
    data = get_granite(url)
    if "retString" in data or not data:
        logger.error(f"No circuit found in Granite for {pathid} \nURL: {url}")
        abort(500, f"No circuit found in Granite for {pathid}")

    # Check for existing revisions
    if len(data) > 1:
        logger.error(f"Existing revision found for {pathid} in Granite. \nRevisions found: {len(data)}")
        abort(
            500, f"Existing revision found for {pathid} Circuits with an existing revision are currently not supported"
        )

    # Verify the circuit is currently in 'Live' status, kick out otherwise
    if "Live" not in data[0]["status"]:
        abort(500, f"Unsupported circuit status {data[0]['status']} for {pathid}.Circuit must be in 'Live' status")

    # Pull the bandwidth value from the Granite call for formatting
    current_bw = data[0]["bandwidth"]

    # Split the bandwidth value and unit for the processing logic
    bw_val, bw_unit = current_bw.split(" ")

    # Normalize the bandwidth value into MBPS
    mbps_bw_val = normalize_bandwidth_values(bw_val, bw_unit)

    logger.info(
        f"Validations for {pathid} performed successfully: "
        f"\nCurrent Bandwidth: {bw_val}{bw_unit} \nNormalized Bandwidth: {mbps_bw_val} "
        f"\nPath Inst ID: {data[0]['pathInstanceId']} \nCircuit Revision: {data[0]['pathRev']}"
    )
    return bw_val, bw_unit, mbps_bw_val, data[0]["pathInstanceId"], data[0]["pathRev"]


def _granite_create_circuit_revision(pathid, main_rev, status="Planned"):
    """Create a new revision in Granite on a qualified Circuit"""

    logger.info(f"Creating Granite circuit revision for {pathid}")
    url = granite_paths_url()
    # Standard go-live date for revision should be 30 days from current date
    live_date = (datetime.datetime.today() + datetime.timedelta(days=30)).strftime("%m/%d/%Y")

    # payload to be sent to Granite to create the revision
    payload = {
        "PATH_NAME": pathid,
        "PATH_REVISION": main_rev,
        "PATH_STATUS": status,
        "SCHEDULED_DATE": live_date,
        "COPY": "true",
        "CREATE_REVISION": "true",
    }

    try:
        data = put_granite(url, payload)

        new_rev = data["pathRev"]
        path_inst = data["pathInstanceId"]
        # Check to ensure that that the 'pathRev' has incremented by one
        if int(data["pathRev"]) <= int(main_rev):
            logger.error(
                f"Granite revision creation issue - revsion number {new_rev} of new revision "
                f"is greater than original circuit record revision {main_rev}"
            )
            abort(
                500,
                f"Granite revision creation issue, 'pathRev' value {new_rev}of new "
                f"revision is not greater than original circuit record revision {main_rev}",
            )
        logger.info(f"New revision for {pathid} created successfully \nRevision: {new_rev} \nPath Inst ID: {path_inst}")
        return True, data["pathInstanceId"], data["pathRev"]
    except (JSONDecodeError, Exception) as e:
        logger.exception(
            f"Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to create circuit revision. Exception while processing Granite response", url=url)


def update_circuit_bw(pathid, rev_instance, rev_path, bw_value, bw_suffix):
    """Apply the new bandwidth to the circuit in Granite"""

    logger.info(
        f"Applying bandwidth update to {bw_value} {bw_suffix} for {pathid} "
        f"on revision {rev_path}, Instance ID {rev_instance}"
    )

    update_parameters = {
        "PATH_NAME": pathid,
        "PATH_INST_ID": rev_instance,
        "PATH_REVISION": rev_path,
        "PATH_BANDWIDTH": f"{bw_value} {bw_suffix}",
        "PATH_START_CHAN_NBR": "1",
        "PATH_END_CHAN_NBR": "9999",
        "PATH_CHANNEL_ASSIGN": "DYNAMIC",
    }

    url = granite_paths_url()

    resp_data = put_granite(url, update_parameters)
    logger.info(f"Bandwidth update compete \nGranite response: \n{resp_data}")
    # return resp_data
    return {
        "circuitId": resp_data["pathId"],
        "circuit_inst_id": resp_data["pathInstanceId"],
        "bw_unit": bw_suffix,
        "bw_value": bw_value,
    }


def express_update_circuit_bw(pathid, rev_instance, rev_path, bw_speed, bw_unit, engineering_name):
    """Apply the new bandwidth to the circuit in Granite"""

    logger.info(
        f"Applying bandwidth update to {bw_speed} {bw_unit} for {pathid} "
        f"on revision {rev_path}, Instance ID {rev_instance}"
    )

    update_parameters = {
        "PATH_NAME": pathid,
        "PATH_INST_ID": rev_instance,
        "PATH_REVISION": rev_path,
        "PATH_BANDWIDTH": f"{bw_speed} {bw_unit}",
        "PATH_START_CHAN_NBR": "1",
        "PATH_END_CHAN_NBR": "9999",
        "PATH_CHANNEL_ASSIGN": "DYNAMIC",
    }

    # only update order number if engineering name is not None
    if engineering_name:
        update_parameters["PATH_ORDER_NUM"] = engineering_name

    url = granite_paths_url()

    resp_data = put_granite(url, update_parameters)
    logger.info(f"Bandwidth update complete \nGranite response: \n{resp_data}")
    return {
        "circuitId": resp_data["pathId"],
        "circ_path_inst_id": resp_data["pathInstanceId"],
        "bw_speed": bw_speed,
        "bw_unit": bw_unit,
    }


def create_transport_revision(trans_name, transport_id):
    """Create a new revision in Granite on a qualified Transport paths"""

    logger.info(f"Creating Granite transport path revision for {trans_name}")
    url = granite_paths_url()
    # Standard go-live date for revision should be 30 days from current date
    live_date = (datetime.datetime.today() + datetime.timedelta(days=30)).strftime("%m/%d/%Y")

    # payload to be sent to Granite to create the revision
    payload = {
        "PATH_NAME": trans_name,
        "PATH_INST_ID": transport_id,
        "PATH_STATUS": "Planned",
        "SCHEDULED_DATE": live_date,
        "COPY": "true",
        "CREATE_REVISION": "true",
    }

    try:
        data = put_granite(url, payload)
        new_rev = data["pathRev"]
        path_inst = data["pathInstanceId"]

        # Check to ensure that that the 'pathRev' has incremented by one

        if path_inst <= transport_id:
            logger.error(
                f"Granite revision creation issue - new path instance id {path_inst}"
                f"is greater than original path instance id: {transport_id}"
            )
            abort(
                500,
                f"Granite revision creation issue - new path instance id {path_inst}"
                f"is greater than original path instance id: {transport_id}",
            )

        logger.info(
            f"New revision for {data['pathId']} created successfully \nRevision: {new_rev} \nPath Inst ID: {path_inst}"
        )
        return data

    except (JSONDecodeError, Exception) as e:
        logger.exception(
            f"Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to create transport revision. Exception while processing Granite response", url=url)


def update_transport_bw(pathid, rev_instance, new_shelf):
    """Apply the new bandwidth to the transport path in Granite"""
    logger.info(f"Applying bandwidth update to 10 Gbps for {pathid}: Instance ID {rev_instance}")

    if new_shelf:
        replace_tid = pathid.split(".")[-1]
        pathid = pathid.replace(replace_tid, new_shelf)

    update_parameters = {
        "PATH_NAME": pathid.replace(".GE1.", ".GE10."),
        "PATH_INST_ID": rev_instance,
        "PATH_BANDWIDTH": "10 Gbps",
        "PATH_START_CHAN_NBR": "1",
        "PATH_END_CHAN_NBR": "9999",
        "PATH_CHANNEL_ASSIGN": "DYNAMIC",
        "SET_CONFIRMED": "TRUE",
    }

    url = granite_paths_url()

    try:
        resp_data = put_granite(url, update_parameters)
        logger.info(f"Bandwidth update complete \nGranite response: \n{resp_data}")
    except Exception:
        logger.error("Granite call to update transport path encountered an error")
        abort(500, "Granite call to update transport path encountered an error")

    return resp_data


def get_cpe_info(cid):
    granite_resp = get_path_elements(cid, "&LVL=1&ELEMENT_TYPE=PORT")

    if isinstance(granite_resp, list):
        granite_resp.reverse()
        tid, vendor, model = "", "", ""

        for port in granite_resp:
            if (
                port.get("PURCHASING_GROUP") == "ENTERPRISE"
                and port.get("TID")
                and port.get("TID").upper().endswith("ZW")
            ):
                tid = port.get("TID")
                vendor = port.get("VENDOR")
                model = port.get("MODEL")
                break
        return tid, vendor, model

    else:
        abort(500, f"No port elements found for cid: {cid}")


def add_vrfid_link(path_name, path_instid):
    """
    Adding revision path to network link

    Input:
    path_name = "71.L1XX.013079..CHTR"
    path_instid = "1234567"

    Output:
    None
    or
    abort
    """
    logger.info(f"Adding new path revision {path_name} to vrfid network link")

    url = f"/pathElements?CIRC_PATH_INST_ID={path_instid}&LVL=1&"

    # Collect raw data from Granite
    try:
        data = get_granite(url, 60, False, 3)
        logger.debug(f"data - {data}")
    except Exception as e:
        logger.exception(
            f"Exception while retrieving circuit info from Granite pathElements "
            f"API \nURL: {url} \nPayload: None \nResponse {e}"
        )
        abort(500, f"Unable to retrieve circuit info. Exception while processing Granite response from {url}")

    if "retString" in data:
        logger.error(f"No circuit found in Granite for {path_name} \nURL: {url}")
        abort(500, f"No circuit found in Granite for {path_name} \nURL: {url}")

    # Storing vrfid elements info to add revision CID
    network_link = []
    path_id = data[0]["CIRC_PATH_INST_ID"]

    for item in data:
        element_bandwidth = item.get("ELEMENT_BANDWIDTH").upper() if item.get("ELEMENT_BANDWIDTH") else ""
        element_type = item.get("ELEMENT_TYPE").upper() if item.get("ELEMENT_TYPE") else ""

        if element_bandwidth == "VPLS":
            if element_type == "NETWORK LINK":
                network_link.append(item)

    if len(network_link) > 1:
        logger.error("There are more than one vrfid elements in revision")
        abort(500, "There are more than one vrfid elements in revision")
    elif len(network_link) == 0:
        logger.error("There are no vrfid elements in revision")
        abort(500, "There are no vrfid elements in revision")

    url = granite_networks_url()
    payload = {
        "NETWORK_NAME": network_link[0]["ELEMENT_NAME"],
        "NETWORK_INST_ID": network_link[0]["ELEMENT_REFERENCE"],
        "LEG_NAME": "1",
        "ADD_ELEMENT": "true",
        "NETWORK_ELEM_SEQUENCE": "1",
        "NETWORK_ELEMENT_TYPE": "CIRCUIT_PATH_LINK",
        "PARENT_PATH_INST_ID": path_instid if path_instid else path_id,
    }

    try:
        put_granite(url, payload)
    except Exception as e:
        logger.exception(
            f"Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to remove vrfid elements. Exception while processing Granite response", url=url)


def fia_ipv6_check(pathid, mw_needed):
    """
    This function checks the IPv6 subnet values

    Input:
    pathid = 71.L1XX.013079..CHTR

    Output:
    None
    or
    Abort
    """
    ips = get_ip_subnets(pathid)

    if ips.get("IPV6_GLUE_SUBNET"):
        if ips["IPV6_GLUE_SUBNET"].split("/")[-1] != "64" and mw_needed:
            logger.error("An update to IPv6 is required. Maintenance window needed due to transport/duplex update")
            abort(500, "An update to IPv6 is required. Maintenance window needed due to transport/duplex update")


def bw_check(cid, bw_speed, bw_unit):
    logger.info("Checking circuit bandwidth against salesforce data")

    url = granite_paths_get_url(cid)
    resp = get_granite(url)

    if isinstance(resp, list):
        # converting bw thats over 999 Mbps to Gbps
        if bw_unit == "Mbps":
            if int(bw_speed) >= 1000:
                bw_speed = str(int(bw_speed) // 1000)
                bw_unit = "Gbps"

        # checking if bandwidth speed and unit matches
        if int(resp[0]["bandwidth"].split()[0]) != int(bw_speed) or resp[0]["bandwidth"].split()[1] != bw_unit:
            bw = f"{bw_speed} {bw_unit}"

            update_parameters = {
                "PATH_INST_ID": resp[0]["pathInstanceId"],
                "PATH_BANDWIDTH": bw,
                "SET_CONFIRMED": "TRUE",
            }

            url = granite_paths_url()
            resp_data = put_granite(url, update_parameters)

            if resp_data["retString"] != "Path Updated":
                msg = f"Error updating circuit bandwidth in granite for {cid}"
                abort(500, msg)

    else:
        msg = f"Error getting bandwidth information from granite for {cid}"
        logger.error(msg)
        abort(500, msg)


def add_job_validation(payload: dict, z_side: bool, a_side: bool) -> dict:
    paths = get_attributes_for_path(payload["z_side_info"]["cid"])
    if isinstance(paths, list):
        if len(paths) > 1:
            abort(500, f"More than one revision found for Add EJT CID: {payload['z_side_info']['cid']}")
        path_status = paths[0]["status"]

    if path_status == "Live":
        payload["z_side_info"]["service_type"] = "change_logical"
    elif "Planned" not in path_status:
        abort(500, f"Add EJT and {path_status} Circuit Found in Granite")
    else:
        if z_side:
            payload["z_side_info"]["service_type"] = "net_new_serviceable"
            payload["z_side_info"]["engineering_job_type"] = "New"

        if a_side:
            payload["a_side_info"]["service_type"] = "net_new_serviceable"
            payload["a_side_info"]["engineering_job_type"] = "New"

    return payload


def colo_site_check(cid: str):
    """Fall out if the provided Z-side site is a COLO"""
    resp = get_circuit_site_info(cid)
    if isinstance(resp, dict):
        abort(500, f"Error retrieving /circuitSites data for {cid}")
    if isinstance(resp, list) and len(resp) > 1:
        abort(500, f"Multiple revisions found for cid: {cid}")
    if "COLO" in resp[0].get("Z_SITE_TYPE"):
        abort(500, f"Unsupported Z-side Site Type COLO for {resp[0].get('Z_SITE_NAME')}")


def entrance_criteria_check(payload):
    # Grabbing z side payload first
    payload_list = [payload.get("z_side_info")]

    # Adding a side if it exist
    if payload.get("a_side_info"):
        payload_list.append(payload.get("a_side_info"))

    for side_info in payload_list:
        # might have None values so checking and converting to .upper() or .lower()
        const_job_type = (
            ""
            if not side_info.get("primary_construction_job_fiber_type")
            else side_info["primary_construction_job_fiber_type"].upper()
        )

        complex = "" if not side_info.get("complex") else side_info["complex"].lower()
        physical_diversity_needed = (
            "" if not side_info.get("physical_diversity_needed") else side_info["physical_diversity_needed"].lower()
        )
        secondary_fia_service_type = (
            "" if not side_info.get("secondary_fia_service_type") else side_info["secondary_fia_service_type"].lower()
        )

        # payload checks
        if side_info.get("build_type") in ("Colocation", "Network Expansion", "Passive MTU"):
            abort(500, f"Unsupported build type of {side_info.get('build_type')}")

        if side_info.get("assigned_cd_team") in (
            "Colocation",
            "Complex",
            "Managed Services – BAU",
            "Managed Services - Complex",
        ):
            abort(500, f"Unsupported assigned circuit design team of {side_info.get('assigned_cd_team')}")

        if const_job_type == "EPON":
            abort(500, f"Unsupported primary construction job fiber type of {const_job_type}")

        if side_info.get("protection_notes"):
            abort(500, f"Unsupported protection notes type of {side_info.get('protection_notes')}")

        if side_info.get("type_of_protection_needed"):
            abort(500, f"Unsupported type of protection needed of {side_info.get('type_of_protection_needed')}")

        if complex == "yes":
            abort(500, f"Unsupported complex type of {side_info.get('complex')}")

        if physical_diversity_needed == "yes":
            abort(500, f"Unsupported physical diversity type of {side_info.get('physical_diversity_needed')}")

        if secondary_fia_service_type == "bgp":
            abort(500, f"Unsupported secondary FIA service type of {side_info.get('secondary_fia_service_type')}")


def epl_circuit_check(payload):
    """
    Checks A side and Z side info for 2 sided circuits to ensure:
    Both uni types are equal to Access
    Transport path and cjs are aligned
    Granite site name field matches information in Granite
    """

    if len(payload) == 2:
        invalid = ("Trunked", None)
        pid_list = []

        cid = payload["z_side_info"].get("cid", "")
        a_side_sitename = payload["a_side_info"].get("granite_site_name", "")
        z_side_sitename = payload["z_side_info"].get("granite_site_name", "")
        a_side_uni = payload["a_side_info"].get("uni_type", "")
        z_side_uni = payload["z_side_info"].get("uni_type", "")
        a_side_pid = payload["a_side_info"].get("pid", "")
        z_side_pid = payload["z_side_info"].get("pid", "")

        if a_side_pid:
            pid_list.append(a_side_pid)

        if z_side_pid:
            pid_list.append(z_side_pid)

        cj = len(pid_list)

        # Check if both sides are access ports, if not then fallout because it wouldn't match the product
        if a_side_uni in invalid or z_side_uni in invalid:
            msg = f"SF uni type combo of: {a_side_uni} & {z_side_uni} not valid for EPL. Both should be Access"
            abort(500, msg)

        # Evaluate for 0, 1, or 2 transports. If not equal to the # of CJs on the order, fallout
        try:
            granite_resp = get_path_elements(cid, "&LVL=1&ELEMENT_TYPE=PATH")

            if isinstance(granite_resp, list):
                transports = len(granite_resp)
        except Exception:
            transports = 0

        # transport paths must equal CJ or fallout
        if transports != cj:
            msg = "The number of transport paths & CJ's are not equal. Please investigate"
            abort(500, msg)

        # Matching SF granite site name to Granite A-side site & Z-side site info
        url = granite_paths_get_url(cid)
        data = get_granite(url)

        if "retString" in data or not data:
            msg = f"No circuit found in Granite for {cid}"
            abort(500, msg)

        g_asitename = data[0].get("aSideSiteName", "")
        g_zsitename = data[0].get("zSideSiteName", "")

        if g_asitename != a_side_sitename or g_zsitename != z_side_sitename:
            msg = "Granite site name information between salesforce and granite does not match. Please investigate"
            abort(500, msg)
    else:
        msg = "Missing A side payload information for EPL. Please investigate"
        abort(500, msg)
