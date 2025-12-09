import logging

from arda_app.bll.transport_path import get_transport_path_data
from arda_app.bll.type_two_segment_ops import get_existing_segment_inst_id, get_new_segment_inst_id
from arda_app.common.cd_utils import granite_paths_url, get_circuit_site_url
from arda_app.dll.granite import (
    find_nni_device,
    get_path_elements,
    get_next_zw_shelf,
    post_granite,
    put_granite,
    get_circuit_site_info,
    get_granite,
)
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def create_transport_path(payload: dict):
    cid = payload.get("cid")
    spectrum_buy_nni_circuit_id = payload.get("spectrum_buy_nni_circuit_id")
    transport_path_name = ""
    # site data collection
    z_side_details = get_z_side_details_from_service_path_cid(cid)
    a_side_details = get_a_side_details_from_buy_nni_cid(spectrum_buy_nni_circuit_id)
    a_side_router = find_nni_device(spectrum_buy_nni_circuit_id)
    transport_paths = get_list_of_cpe_transport_paths_with_a_side_router(a_side_router, z_side_details["Z_SITE_NAME"])
    # determine how cpe transport path is created
    if len(transport_paths) > 1:
        cpe_tid = transport_paths[0].split(".")[-1]
        msg = f"Multiple transport paths found for CPE device: {cpe_tid}"
        logger.error(msg)
        abort(500, msg)
    elif len(transport_paths) == 1:
        # cpe transport path increment
        start_transport_path = int(transport_paths[0].split(".")[0]) + 1
        transport_path_name = str(start_transport_path) + "." + (transport_paths[0].split(".", 1)[1])
        bandwidth = transport_path_name.split(".")[1]
        if "10" in bandwidth:
            bandwidth_string = "10 Gbps"
        else:
            bandwidth_string = "1 Gbps"
    else:
        # new cpe transport path
        transport_path_name, bandwidth_string = build_transport_path(cid, a_side_details["A_CLLI"])
    # make sure a transport path name to create is defined
    if not transport_path_name:
        msg = f"Unable to create transport path for Type 2 circuit {cid}"
        logger.error(msg)
        abort(500, msg)
    # create cpe transport path
    _create_transport_path_at_granite(
        transport_path_name, bandwidth_string, a_side_details["A_SITE_NAME"], z_side_details["Z_SITE_NAME"]
    )
    transport_path_data = get_transport_path_data(transport_path_name)
    transport_path_data["transport_path_name"] = transport_path_name
    # retrieve segment and add it to transport path
    segment_inst_id = get_existing_segment_inst_id(payload)
    if not segment_inst_id:
        segment_inst_id = get_new_segment_inst_id(payload, bandwidth_string)
    try:
        _reserve_segment_on_granite(transport_path_data, segment_inst_id)
    except Exception:
        msg = "Segment found but it could be assigned to another path"
        logger.error(msg)
        abort(500, msg)
    # add completed transport path with segment to service path CID
    transport_path_inst_id = transport_path_data.get("path_inst_id")
    new_sequence_number = sequence_number_for_new_service_path_element(cid)
    _add_transport_channel_to_ethernet_path(cid, transport_path_inst_id, new_sequence_number)
    resp = {"cpe_transport_path": transport_path_name}
    return resp


def get_z_side_details_from_service_path_cid(service_path_cid: str) -> dict:
    z_side_details = {}
    url = f"/circuitSites?CIRCUIT_NAME={service_path_cid}&PATH_CLASS=P"
    data = get_granite(url)
    if data and isinstance(data, list):
        try:
            z_clli = data[0]["Z_CLLI"]
            z_site_name = data[0]["Z_SITE_NAME"]
        except Exception:
            msg = f"Unable to obtain Z-side site details for {service_path_cid}"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = f"Unable to pull circuit sites data for {service_path_cid}"
        logger.error(msg)
        abort(500, msg)
    if not all([z_clli, z_site_name]):
        msg = f"Z-side site information is missing for {service_path_cid}"
        logger.error(msg)
        abort(500, msg)
    z_side_details["Z_CLLI"] = z_clli
    z_side_details["Z_SITE_NAME"] = z_site_name
    return z_side_details


def get_a_side_details_from_buy_nni_cid(buy_nni_cid: str) -> dict:
    a_side_details = {}
    url = f"/circuitSites?CIRCUIT_NAME={buy_nni_cid}&PATH_CLASS=P"
    data = get_granite(url)
    if data and isinstance(data, list):
        try:
            a_clli = data[0]["A_CLLI"]
            a_site_name = data[0]["A_SITE_NAME"]
        except Exception:
            msg = f"Unable to obtain A-side site details for {buy_nni_cid}"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = f"Unable to pull circuit sites data for {buy_nni_cid}"
        logger.error(msg)
        abort(500, msg)
    if not all([a_clli, a_site_name]):
        msg = f"A-side site information is missing for {buy_nni_cid}"
        logger.error(msg)
        abort(500, msg)
    a_side_details["A_CLLI"] = a_clli
    a_side_details["A_SITE_NAME"] = a_site_name
    return a_side_details


def get_list_of_cpe_transport_paths_with_a_side_router(a_side_router: str, z_site_name: str) -> list:
    transport_paths = []
    url = f"/paths?CIRC_PATH_HUM_ID=%{a_side_router}.%ZW"
    paths = get_granite(url)

    if isinstance(paths, list):
        for path in paths:
            if path.get("zSideSiteName", "").upper() == z_site_name.upper():
                if path.get("pathId"):
                    transport_paths.append(path["pathId"])
    else:
        msg = "Unable to pull transport path data"
        logger.error(msg)
        abort(500, msg)

    return transport_paths


def build_transport_path(cid, a_clli):
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={cid}"
    path_elements = get_granite(endpoint)
    if path_elements and isinstance(path_elements, dict) and "retString" in path_elements.keys():
        path_elements = []
    parent_site_info = get_circuit_site_info(cid)
    npa_nxx = cid[:2]
    shelf = get_next_zw_shelf(parent_site_info[0].get("Z_CLLI"))
    bandwidth = parent_site_info[0].get("CIRCUIT_BANDWIDTH")
    bandwidth_string = bandwidth_conversion(bandwidth)
    if not path_elements:
        aside = ""
        url = f"/uplinkPorts?CLLI={a_clli}&BANDWIDTH={bandwidth_string}"
        resp = get_granite(url)
        if resp and isinstance(resp, list):
            try:
                aside = resp[0]["EQUIP_NAME"]
            except Exception:
                msg = f"Unable to determine A-side router at {a_clli}"
                logger.error(msg)
                abort(500, msg)
        else:
            msg = f"Unable to determine A-side router at {a_clli}"
            logger.error(msg)
            abort(500, msg)
    else:
        for element in path_elements:
            if element.get("ELEMENT_CATEGORY") == "ROUTER":
                aside = element.get("ELEMENT_NAME")
                break
    equip_name = aside.split("/")[0]
    return f"{npa_nxx}001.GE{bandwidth_string.split(' ')[0]}.{equip_name}.{shelf}", bandwidth_string


def bandwidth_conversion(bandwidth):
    bw_value = bandwidth.split(" ")[0]
    bw_type = bandwidth.split(" ")[1]
    bandwidth_in_mbps = get_bandwidth_in_mbps(bw_type, bw_value)

    if bandwidth_in_mbps <= 1000:
        bandwidth_string = "1 Gbps"
    else:
        bandwidth_string = "10 Gbps"
    return bandwidth_string


def get_bandwidth_in_mbps(bw_type, bw_value):
    if bw_type.lower() == "mbps":
        bandwidth_in_mbps = float(bw_value)
    elif bw_type.lower() == "gbps":
        bandwidth_in_mbps = float(bw_value) * 1000
    else:
        abort(500, "invalid bandwidth_type - must be Mbps or Gbps.")
    return bandwidth_in_mbps


def _create_transport_path_at_granite(
    transport_path_name, bandwidth_string, a_site_name, z_site_name, build_type_mtu=False
):
    if (not a_site_name) and (not z_site_name):
        msg = "Unable to create transport path due to unknown site names"
        logger.error(msg)
        abort(500, msg)

    # post new transport path to Granite
    granite_url = granite_paths_url()
    if build_type_mtu:
        uda_product_service = "INT-EDGE TRANSPORT"
    else:
        uda_product_service = "INT-ACCESS TO PREM TRANSPORT"

    params = {
        "PATH_NAME": transport_path_name,
        "PATH_TEMPLATE_NAME": "WS ETHERNET TRANSPORT",
        "PATH_BANDWIDTH": bandwidth_string,
        "TOPOLOGY": "Point to point",
        "A_SITE_NAME": a_site_name,
        "Z_SITE_NAME": z_site_name,
        "PATH_STATUS": "Planned",
        "PATH_MAX_OVER_SUB": "0",
        "UDA": {"SERVICE TYPE": {"PRODUCT/SERVICE": uda_product_service, "SERVICE MEDIA": "FIBER"}},
        "UPDATE_LEG": "true",
        "LEG_NAME": "1",
        "LEG_A_SITE_NAME": a_site_name,
        "LEG_Z_SITE_NAME": z_site_name,
        "SET_CONFIRMED": "TRUE",
    }
    return post_granite(granite_url, params, timeout=90)


def _reserve_segment_on_granite(transport_path_data, segment_inst_id):
    granite_url = granite_paths_url()

    payload = {
        "PATH_NAME": transport_path_data["transport_path_name"],
        "PATH_REV_NBR": "1",
        "PATH_INST_ID": transport_path_data["path_inst_id"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PATH_ELEMENT_TYPE": "CIRCUIT_SEGMENT",
        "SEGMENT_INST_ID": segment_inst_id,
        "LEG_NAME": transport_path_data["leg_name"],
        "PATH_LEG_INST_ID": transport_path_data["leg_inst_id"],
    }
    return put_granite(granite_url, payload, timeout=90)


def _add_transport_channel_to_ethernet_path(cid, transport_inst_id, new_sequence_number):
    url = get_circuit_site_url(cid)
    res = get_granite(url)
    data = res[0]

    channel_path_params = {
        "PATH_NAME": data["CIRCUIT_NAME"],
        "PATH_INST_ID": data["CIRC_PATH_INST_ID"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": str(new_sequence_number),
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": transport_inst_id,
        "LEG_NAME": "1",
        "SET_CONFIRMED": "true",
        "BREAK_LOCK": "true",
    }

    url = granite_paths_url()
    granite_response_data = put_granite(url, channel_path_params, timeout=90)

    if not granite_response_data:
        logger.error(
            f"No response from Granite assigning transport path {data['path_name']} to circuit."
            f"\nURL: {url} \nResponse: \n{granite_response_data}"
        )
        abort(
            500,
            message=f"Issue assigning transport path {data['path_name']} to circuit in Granite.",
            url=url,
            response=granite_response_data,
        )

    try:
        if granite_response_data["retString"].lower() != "path updated":
            logger.error(
                f"Granite error {granite_response_data['httpCode']} returned when assigning transport path "
                f"{data['path_name']} to circuit. \nURL: {url} \nResponse: \n{granite_response_data}"
            )
            abort(
                500,
                message=f"Granite error {granite_response_data['httpCode']} returned when assigning transport path "
                f"{data['path_name']} to circuit.",
                url=url,
                response=granite_response_data,
            )
    except (AttributeError, KeyError, TypeError):
        logger.exception(
            f"Invalid response from Granite assigning transport path {data['path_name']} "
            f"to circuit. \nURL: {url} \nResponse: \n{granite_response_data}"
        )
        abort(
            500,
            message=f"Invalid response from Granite assigning transport path {data['path_name']} "
            f"to circuit. \nURL: {url} \nResponse: \n{granite_response_data}",
        )
    return data


def sequence_number_for_new_service_path_element(cid: str) -> int:
    try:
        path_elements = get_path_elements(cid)
    except Exception:
        path_elements = []
    next_seq = 0
    if path_elements and isinstance(path_elements, list):
        for element in path_elements:
            try:
                seq = element["SEQUENCE"]
            except Exception:
                logger.info("Unable to find sequence number for path element")
            if seq.isnumeric() and (int(seq) > next_seq):
                next_seq = int(seq)
    return next_seq + 1
