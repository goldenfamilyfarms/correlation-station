import logging

from arda_app.dll.granite import get_path_elements, get_granite, put_granite, get_attributes_for_path
from arda_app.bll.net_new.ip_reservation.utils.granite_utils import get_circuit_site_url
from arda_app.common.cd_utils import granite_paths_url
from arda_app.common.bw_operations import normalize_bandwidth_values
from common_sense.common.errors import abort


logger = logging.getLogger(__name__)


def add_buy_nni(payload: dict) -> bool:
    cid = payload.get("cid")
    spectrum_buy_nni_circuit_id = payload.get("spectrum_buy_nni_circuit_id")
    try:
        path_elements = get_path_elements(spectrum_buy_nni_circuit_id)
        buy_nni_path_inst_id = path_elements[0].get("CIRC_PATH_INST_ID")
        nni_name = path_elements[0].get("PATH_NAME")
    except Exception:
        logger.exception(f"Unable to find path elements for Buy NNI {spectrum_buy_nni_circuit_id}")
        abort(500, f"Unable to find path elements for Buy NNI {spectrum_buy_nni_circuit_id}")

    try:
        path_elements_parent = get_path_elements(cid)
    except Exception:
        path_elements_parent = []

    if path_elements_parent:
        msg = f"Path elements were unexpectedly found for {cid}"
        logger.error(msg)
        abort(500, msg)

    if not does_buy_nni_exist(path_elements):
        msg = "Buy NNI does not exist"
        logger.error(msg)
        abort(500, msg)

    oversubscribe_check(nni_name, buy_nni_path_inst_id, cid)

    vendor = buy_nni_device_vendor(path_elements)

    if vendor:
        logger.info(f"{vendor} is currently not supported for Type 2 circuit")
        abort(500, f"{vendor} is currently not supported for Type 2 circuit")
    else:
        granite_response_data = _add_buy_nni_path(cid, buy_nni_path_inst_id, path_elements_parent, path_elements)
        granite_response_data_2 = _resequence_dynamic_router_port(granite_response_data, cid, path_elements_parent)

    return True if (granite_response_data and granite_response_data_2) else False


def _add_buy_nni_path(cid, buy_nni_path_inst_id, path_elements_parent, buy_nni_path_elements):
    url = get_circuit_site_url(cid)
    res = get_granite(url)
    data = res[0]
    buy_nni_sequence_number = get_buy_nni_sequence_number(path_elements_parent)
    buy_nni_port_inst_id = get_buy_nni_port_inst_id(buy_nni_path_elements)

    buy_nni_path_params = {
        "PATH_NAME": data["CIRCUIT_NAME"],
        "PATH_INST_ID": data["CIRC_PATH_INST_ID"],
        "PATH_REV": "1",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": buy_nni_sequence_number,
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": buy_nni_path_inst_id,
        "PARENT_PORT_INST_ID": buy_nni_port_inst_id,
        "LEG_NAME": data["LEG_NAME"],
        "PATH_LEG_INST_ID": data["LEG_INST_ID"],
        "SET_CONFIRMED": "true",
        "BREAK_LOCK": "true",
    }

    url = granite_paths_url()
    granite_response_data = put_granite(url, buy_nni_path_params)

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


def does_buy_nni_exist(buy_nni_path_elements: list) -> bool:
    return True if buy_nni_path_elements else False


def buy_nni_device_vendor(buy_nni_path_elements: list) -> str:
    vendor = ""
    vendors = ("ADVA", "RAD")
    for elem in buy_nni_path_elements:
        if elem.get("VENDOR") and (elem.get("VENDOR").upper() in vendors):
            vendor = elem.get("VENDOR")
            break
    return vendor


def get_cloud_sequence_number(path_elements_parent: list) -> str:
    sequence = "0"
    element_type = ("CLOUD", "NETWORK", "NETWORK LINK")
    for elem in path_elements_parent:
        if elem["ELEMENT_TYPE"].upper() in element_type:
            sequence = elem["SEQUENCE"]
            break
    return sequence


def get_buy_nni_sequence_number(path_elements_parent: list) -> str:
    cloud_sequence_number = get_cloud_sequence_number(path_elements_parent)
    return str(int(cloud_sequence_number) + 1) if cloud_sequence_number else ""


def get_dynamic_router_port_sequence_number(path_elements_parent: list) -> str:
    buy_nni_sequence_number = get_buy_nni_sequence_number(path_elements_parent)
    return str(int(buy_nni_sequence_number) + 1) if buy_nni_sequence_number else ""


def get_buy_nni_port_inst_id(buy_nni_path_elements: list) -> str:
    buy_nni_port_inst_id = ""
    # find port instance ID of dynamic port on the router
    for elem in buy_nni_path_elements:
        if (elem["ELEMENT_TYPE"].upper() == "PORT") and (elem["SEQUENCE"] == "1"):
            buy_nni_port_inst_id = elem["PORT_INST_ID"]
            break
    return buy_nni_port_inst_id


def get_dynamic_router_port_location(parent_cid: str) -> str:
    # after adding buy nni element, run get to search for element_type=port & LVL=1
    # and look for greatest sequence number
    path_elements_after_adding_buy_nni = get_path_elements(parent_cid, "&LVL=1&ELEMENT_TYPE=PORT")
    # the greatest sequence number should be the dynamic router port to resequence
    element_to_move = ""
    for elem in path_elements_after_adding_buy_nni:
        if element_to_move < str(elem["SEQUENCE"]):
            element_to_move = elem["SEQUENCE"]
    return element_to_move


def _resequence_dynamic_router_port(data: list, parent_cid: str, path_elements_parent: list) -> dict:
    # get dynamic router port info
    element_to_move = get_dynamic_router_port_location(parent_cid)
    sequence_number_to_move_to = get_dynamic_router_port_sequence_number(path_elements_parent)
    # build payload
    if element_to_move and sequence_number_to_move_to:
        resequence_payload = {
            "PATH_INST_ID": data["CIRC_PATH_INST_ID"],
            "PATH_LEG_INST_ID": data["LEG_INST_ID"],
            "ELEMENT_TO_MOVE": element_to_move,
            "NEW_SEQUENCE": sequence_number_to_move_to,
            "SET_CONFIRMED": "true",
            "BREAK_LOCK": "true",
        }
    else:
        msg = "Unable to resequence dynamic router port for buy NNI"
        logger.error(msg)
        abort(500, msg)
    logger.debug(f"resequence_payload - {resequence_payload}")
    # update Granite
    url = granite_paths_url()
    resp = put_granite(url, resequence_payload)
    return resp


def oversubscribe_check(nni_name, buy_nni_path_inst_id, cid):
    url = f"/pathUtilization?CIRC_PATH_HUM_ID={nni_name}&CIRC_PATH_INST_ID={buy_nni_path_inst_id}"

    data = get_granite(url, 60, False, 3)
    logger.debug(f"data - {data}")

    # checking if Path bandwidth will oversubscribe NNI
    # get path BW from granite
    path_data = get_attributes_for_path(cid)

    # split BW to value and unit (10 , Mbps)
    bw_value = path_data[0]["bandwidth"].split()[0]
    bw_unit = path_data[0]["bandwidth"].split()[1]

    path_bw_mbps = normalize_bandwidth_values(bw_value, bw_unit)

    # convert NNI available BW from bytes to Mbps
    nni_value = int(data[0]["AVAILABLE_BW"])
    available_bw_mbps = nni_value / 1000000  # Convert from bytes to Mb

    # then compare and abort if path bandwidth is greater than available bw
    if path_bw_mbps > available_bw_mbps:
        msg = f"The cid bandwidth of {bw_value} {bw_unit} will oversubscribe ENNI: {nni_name}. Please investigate"
        logger.error(msg)
        abort(500, msg)
