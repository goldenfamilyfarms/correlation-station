import logging

from arda_app.dll.granite import get_circuit_site_info, get_segments, post_granite, put_granite, get_vendor
from common_sense.common.errors import abort


logger = logging.getLogger(__name__)


def get_number_of_segments(cid: str) -> int:
    params = "?SEGMENT_NAME="
    segments_data = get_segments(cid, params=params)
    return len(segments_data) if (segments_data and isinstance(segments_data, list)) else 0


def get_segment_inst_id(cid: str) -> str:
    params = "?SEGMENT_NAME="
    segments_data = get_segments(cid, params=params)
    if segments_data and isinstance(segments_data, list):
        try:
            segment_inst_id = segments_data[0]["CIRC_INST_ID"]
        except Exception:
            msg = f"Unable to obtain segment instance ID for {cid}"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = f"Unable to obtain segment instance ID for {cid}"
        logger.error(msg)
        abort(500, msg)
    return segment_inst_id


def get_existing_segment_inst_id(payload: dict) -> str:
    # search for an existing segment
    cid = payload.get("service_provider_cid")
    segments_found = get_number_of_segments(cid)
    if segments_found == 0:
        # second search attempt
        cid = payload.get("service_provider_uni_cid")
        segments_found = get_number_of_segments(cid)
        if segments_found == 0:
            # both search attempts did not find existing segment, assign empty string
            segment_inst_id = ""
        elif segments_found == 1:
            segment_inst_id = get_segment_inst_id(cid)
        else:
            msg = f"More than 1 segment was found for {cid}"
            logger.error(msg)
            abort(500, msg)
    elif segments_found == 1:
        segment_inst_id = get_segment_inst_id(cid)
    else:
        msg = f"More than 1 segment was found for {cid}"
        logger.error(msg)
        abort(500, msg)
    # segment exists and is ready to be updated with site info
    if segment_inst_id and isinstance(segment_inst_id, str):
        url = "/segments"
        put_payload = {
            "SEGMENT_INST_ID": segment_inst_id,
            "A_SIDE_SITE_NAME": get_a_side_site_name_for_segment(payload.get("spectrum_buy_nni_circuit_id")),
            "Z_SIDE_SITE_NAME": get_z_side_site_name_for_segment(payload.get("cid")),
        }
        resp = put_granite(url, put_payload, timeout=90)
        if isinstance(resp, dict) and ("Segment Updated" not in resp["retString"]):
            msg = "Unable to update segment"
            logger.error(msg)
            abort(500, msg)
    return segment_inst_id


def payload_constructor_for_create_segment(payload: dict, bandwidth_string: str) -> bool:
    payload_list = []

    # construct payload to create segment
    segment_vendor = vendor_check(payload.get("service_provider"))
    service_provider_cid = payload.get("service_provider_cid").upper()

    post_payload = {
        "SEGMENT_NAME": service_provider_cid,
        "SEGMENT_BANDWIDTH": bandwidth_string,
        "SEGMENT_TYPE": "CUSTOMER",
        "SEGMENT_VENDOR": segment_vendor,
        "SEGMENT_STATUS": "Designed",
    }
    missing_data = []
    if all(post_payload.values()):
        # if all payload keys have values, then payload is correctly constructed and ready for use
        payload_list.append(post_payload)
    else:
        # keep track of payload keys missing values
        for x, y in post_payload.items():
            if not y:
                missing_data.append(x)
    # create payload to update segment
    put_payload = {
        "SEGMENT_NAME": service_provider_cid,
        "A_SIDE_SITE_NAME": get_a_side_site_name_for_segment(payload.get("spectrum_buy_nni_circuit_id")),
        "Z_SIDE_SITE_NAME": get_z_side_site_name_for_segment(payload.get("cid")),
    }
    if all(put_payload.values()):
        payload_list.append(put_payload)
    else:
        for x, y in put_payload.items():
            if not y:
                missing_data.append(x)
    # check if any required data is missing and fall-out if needed
    if missing_data:
        msg = f"Missing values when creating segment: {missing_data}"
        logger.error(msg)
        abort(500, msg)
    return payload_list


def get_a_side_site_name_for_segment(buy_nni_cid: str) -> str:
    a_side_site_name = ""
    try:
        data = get_circuit_site_info(buy_nni_cid)
    except Exception:
        return a_side_site_name
    if data and isinstance(data, list):
        try:
            a_side_site_name = data[0]["A_SITE_NAME"]
        except KeyError:
            msg = "Can't find A-side site name for segment"
            logger.error(msg)
    return a_side_site_name


def get_z_side_site_name_for_segment(service_path_cid: str) -> str:
    z_side_site_name = ""
    try:
        data = get_circuit_site_info(service_path_cid)
    except Exception:
        return z_side_site_name
    if data and isinstance(data, list):
        try:
            z_side_site_name = data[0]["Z_SITE_NAME"]
        except KeyError:
            msg = "Can't find Z-side site name for segment"
            logger.error(msg)
    return z_side_site_name


def get_new_segment_inst_id(payload, bandwidth_string: str) -> str:
    # prep work for Granite calls
    payloads = payload_constructor_for_create_segment(payload, bandwidth_string)
    if not payloads:
        msg = "Required data to create segment unavailable"
        logger.error(msg)
        abort(500, msg)
    url = "/segments"

    # create segment with POST segments call
    resp = post_granite(url, payloads[0], timeout=90)

    if isinstance(resp, dict) and ("Segment Added" not in resp["retString"]):
        msg = "Unable to create segment"
        logger.error(msg)
        abort(500, msg)

    # update same segment using PUT segments call with site terminations
    resp = put_granite(url, payloads[1], timeout=90)
    msg = "Unable to update segment"

    if isinstance(resp, dict) and ("Segment Updated" not in resp["retString"]):
        logger.error(msg)
        abort(500, msg)

    try:
        segment_inst_id = resp["CIRC_INST_ID"]
    except Exception:
        msg = "Unable to obtain an instance ID for the new segment"
        logger.error(msg)
        abort(500, msg)

    return segment_inst_id


def vendor_check(vendor):
    """
    Looking up vendor in granite to ensure we can create a segment
    """
    vendor = vendor.upper()

    # removing vendor on right side of '/'
    if "/" in vendor:
        vendor = vendor.split("/")[0].strip()

    if "AT&T" in vendor or "ATT" in vendor:
        # fixing & issue
        vendor = "AT%26T"
    elif "C SPIRE" in vendor:
        vendor = "CSPIRE"
    elif vendor == "CONSOLIDATED":
        msg = f"The vendor: {vendor} has multiple results when searching in granite. Please investigate"
        logger.error(msg)
        abort(500, msg)

    resp = get_vendor(vendor)

    if isinstance(resp, list):
        # returning the first result (not many vendors with same name)
        return resp[0]["VENDOR_NAME"]

    msg = f"No results in granite when looking up vendor: {vendor}"
    logger.error(msg)
    abort(500, msg)
