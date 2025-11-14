import re
import logging
from common_sense.common.errors import abort
from arda_app.common.cd_utils import get_l1_url
from arda_app.dll.granite import get_granite
from arda_app.bll.transport_path import (
    get_existing_path_elements,
    create_circuit_path_data,
    get_transport_path_data,
    granite_add_path_elements,
)

logger = logging.getLogger(__name__)
sequence = ""


def add_path_to_granite(circuit_id, circuit_path_data, transport_path_data, path_elem_sequence="1"):
    try:
        granite_add_path_elements(circuit_id, circuit_path_data, transport_path_data, path_elem_sequence)
        return {"circuit_id": circuit_id, "status": "success"}
    except Exception:
        logger.debug("exception occured while adding path elements to granite")
        return {"circuit_id": circuit_id, "status": "failure"}


def handle_epl_evpl(
    service_location_address, circuit_id, circuit_path_data, transport_path_data, existing_path_elements
):
    if len(existing_path_elements) > 2:
        logger.debug("product type is EPL or EVPL but there are more than 2 path elements")
        return {"circuit_id": circuit_id, "status": "failure"}
    else:
        if service_location_address and circuit_path_data["A_ADDRESS"] in service_location_address:
            global sequence
            sequence = "1"
            return add_path_to_granite(circuit_id, circuit_path_data, transport_path_data, "1")
        elif service_location_address and circuit_path_data["Z_ADDRESS"] in service_location_address:
            sequence = "2"
            return add_path_to_granite(circuit_id, circuit_path_data, transport_path_data, "2")
        else:
            logger.debug("product type is EPL or EVPL but address did not match")
            return {"circuit_id": circuit_id, "status": "failure"}


def update_related_circuits(circuit_ids_list, transport_path, service_location_address):
    cid_statuses = []
    epl_evpl_product_families = {"EPL (Fiber)", "EVPL (Fiber)"}
    transport_path_data = get_transport_path_data(transport_path)

    for cid in circuit_ids_list:
        circuit_id = cid.get("circuit_id")
        circuit_path_data = create_circuit_path_data(circuit_id)
        existing_path_elements = get_existing_path_elements(circuit_id)
        if existing_path_elements is not None:
            if cid["product_name_order_info"] in epl_evpl_product_families:
                cid_statuses.append(
                    handle_epl_evpl(
                        service_location_address,
                        circuit_id,
                        circuit_path_data,
                        transport_path_data,
                        existing_path_elements,
                    )
                )
            else:
                logger.debug("path elements exist and product type is not EPL or EVPL")
                cid_statuses.append({"circuit_id": circuit_id, "status": "failure"})
                continue
        else:
            cid_statuses.append(add_path_to_granite(circuit_id, circuit_path_data, transport_path_data))
    return cid_statuses


def get_original_transport_path(circuit_id):
    url = get_l1_url(circuit_id)
    related_cid_path_elements = get_granite(url)
    if (isinstance(related_cid_path_elements, list) and len(related_cid_path_elements) == 0) or (
        isinstance(related_cid_path_elements, dict) and related_cid_path_elements.get("retString")
    ):
        abort(500, f"No transport found in path for related CID: {circuit_id}")
    for element in reversed(related_cid_path_elements):
        if re.search(r".*(CW|QW)\..*(AW|ZW)", element["ELEMENT_NAME"]):
            return element["ELEMENT_NAME"]
