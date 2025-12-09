import logging
from typing import Tuple

from common_sense.common.errors import abort
from arda_app.common.cd_utils import granite_paths_url, granite_ports_put_url
from arda_app.dll.granite import get_path_elements, put_granite, get_circuit_site_info, get_path_elements_l1


logger = logging.getLogger(__name__)


def assign_uplinks_and_handoffs_main(payload: dict) -> dict:
    """Assign uplinks and handoffs."""
    put_payload = {}
    port_type = ""
    cid = payload.get("cid")
    port_role = payload.get("port_role")
    mtu_pe_path = payload.get("mtu_pe_path")
    mtu_uplink = payload.get("mtu_uplink")
    zw_path = payload.get("zw_path")
    cpe_uplink = payload.get("cpe_uplink")
    build_type = payload.get("build_type")
    product_name = payload.get("product_name")
    circ_path_inst_id = payload.get("circ_path_inst_id")
    cpe_handoff = payload.get("cpe_handoff")
    cpe_trunked_path = payload.get("cpe_trunked_path")
    side = payload.get("side")
    third_party_provided_circuit = payload.get("third_party_provided_circuit")
    cpe_handoff_paid = payload.get("cpe_handoff_paid")
    number_of_circuits_in_group = 0

    if payload.get("number_of_circuits_in_group"):
        number_of_circuits_in_group = int(payload["number_of_circuits_in_group"])

    if port_role == "uplink":
        # Assign Uplink
        put_payload, port_type = _uplink_payload(
            cid, mtu_pe_path, mtu_uplink, zw_path, cpe_uplink, build_type, product_name
        )

    elif port_role == "handoff":
        # Assign CPE Handoff
        put_payload, port_type = _handoff_payload(
            cid,
            circ_path_inst_id,
            cpe_handoff,
            cpe_trunked_path,
            build_type,
            side,
            product_name,
            third_party_provided_circuit,
        )

    if not put_payload:
        logger.error("Incorrect payload information. Cannot assign uplinks and handoffs.")
        abort(500, "Assignment failed, incorrect payload information.")

    paths_url = granite_paths_url()

    if (
        port_role == "handoff"
        and number_of_circuits_in_group > 0
        and product_name in {"PRI Trunk (Fiber)", "PRI Trunk(Fiber) Analog", "PRI Trunk (DOCSIS)"}
    ):
        for x in range(1, number_of_circuits_in_group + 1):
            circuit_id = f"{cid}.00{x}"
            circ_path_inst_id = _get_path_inst_id(circuit_id)
            put_child_payload, port_type = _handoff_payload(
                circuit_id, circ_path_inst_id, cpe_handoff, cpe_trunked_path, build_type, side, product_name
            )
            put_granite(paths_url, put_child_payload)
    else:
        put_granite(paths_url, put_payload)

    if port_role == "handoff" and cpe_trunked_path:
        _update_trunked_dynamic_port(cid, cpe_handoff_paid, put_payload["PATH_ELEM_SEQUENCE"])

    return {"message": f"{port_type} has been added successfully."}


def _uplink_payload(
    cid: str, mtu_pe_path: str, mtu_uplink: str, zw_path: str, cpe_uplink: str, build_type: str, product_name: str
) -> Tuple[dict, str]:
    """Assign Uplink payload."""

    put_payload = {
        "LEG_NAME": "1",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "2",
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
    }

    # MTU or CPE
    if build_type == "MTU New Build":
        put_payload["PATH_INST_ID"] = mtu_pe_path
        put_payload["PORT_INST_ID"] = mtu_uplink
        port_type = "MTU Uplink"
    else:
        put_payload["PATH_INST_ID"] = zw_path
        put_payload["PORT_INST_ID"] = cpe_uplink
        port_type = "CPE Uplink"

    # SIP
    if product_name in {
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
    }:
        put_payload["PATH_ELEM_SEQUENCE"] = _get_next_element_sequence(cid)

    return put_payload, port_type


def _handoff_payload(
    cid: str,
    circ_path_inst_id: str,
    cpe_handoff: str,
    cpe_trunked_path: str,
    build_type: str,
    side: str,
    product_name: str,
    third_party_provided_circuit="N",
) -> Tuple[dict, str]:
    """Assign CPE Handoff payload."""

    put_payload = {"PATH_NAME": cid, "PATH_INST_ID": circ_path_inst_id, "LEG_NAME": "1", "ADD_ELEMENT": "true"}

    # A Side or Z Side
    if side == "z_side":
        if third_party_provided_circuit == "Y":
            put_payload["PATH_ELEM_SEQUENCE"] = "4"
        else:
            put_payload["PATH_ELEM_SEQUENCE"] = "3" if build_type == "MTU New Build" else "2"
    else:
        put_payload["PATH_ELEM_SEQUENCE"] = "1"

    # Access or Trunked
    if cpe_trunked_path:
        put_payload["PATH_ELEMENT_TYPE"] = "CIRC_PATH_CHANNEL"
        put_payload["PARENT_PATH_INST_ID"] = cpe_trunked_path
        put_payload["PARENT_PORT_INST_ID"] = cpe_handoff
    else:
        put_payload["PATH_ELEMENT_TYPE"] = "EQUIPMENT_PORT"
        put_payload["PORT_INST_ID"] = cpe_handoff

    if (
        product_name in {"SIP - Trunk (Fiber)", "SIP Trunk(Fiber) Analog", "EPL (Fiber)", "Hosted Voice - (Fiber)"}
        and side != "a_side"
    ):
        put_payload["PATH_ELEM_SEQUENCE"] = _get_next_element_sequence(cid)

    return put_payload, "CPE Handoff"


def _get_next_element_sequence(cid: str):
    """Get the next path element sequence."""
    path_elements = get_path_elements_l1(cid)

    # net_new_no_cj & net_new_servicable logic no existing transport next sequence = 1
    if isinstance(path_elements, dict):
        return "1"

    highest_sequence = 0

    for element in path_elements:
        if int(element["SEQUENCE"]) > highest_sequence:
            highest_sequence = int(element["SEQUENCE"])

    return str(highest_sequence + 1)


def _get_path_inst_id(cid: str):
    resp = get_circuit_site_info(cid)
    path_elements = resp[0]
    return path_elements.get("CIRC_PATH_INST_ID")


def _update_trunked_dynamic_port(cid: str, cpe_handoff_paid: str, sequence: str) -> None:
    """Update trunked dynamic port."""
    dynamic_port_sequence = str(int(sequence) + 1)
    path_elements = get_path_elements(cid, url_params=f"&LVL=1&SEQUENCE={dynamic_port_sequence}")[0]

    # Update dynamic port with trunked info
    trunked_payload = {
        "PORT_INST_ID": path_elements["PORT_INST_ID"],
        "PORT_ACCESS_ID": cpe_handoff_paid,
        "UDA": {"VLAN INFO": {"PORT-ROLE": "UNI-EVP"}},
        "SET_CONFIRMED": "TRUE",
    }
    ports_url = granite_ports_put_url()
    put_granite(ports_url, trunked_payload)
