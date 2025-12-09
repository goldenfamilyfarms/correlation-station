import logging
from typing import Dict, Any

from common_sense.common.errors import abort
from arda_app.common.cd_utils import granite_paths_url
from arda_app.dll.granite import get_path_elements, get_granite, put_granite
from arda_app.bll.models.device_topology.underlay import UnderlayDeviceTopologyModel
from arda_app.bll.net_new.utils.shelf_utils import get_device_bw
from arda_app.bll.cpe_swap.cpe_swap_utils import (
    _initial_validations,
    _cid_revision_check,
    _l1_l2_evp_check,
    _transport_channel_validation,
    _uplink_handoff_values,
    _handoff_get_equipment_buildout,
    _set_handoff_card_template,
    _set_handoff_paid,
    _build_put_add_payload,
    _remove_ports_from_path,
    _delete_shelf,
    _create_shelf,
    _uplink_card_and_paid,
)
from arda_app.bll.cpe_swap.cpe_swap_constants import (
    SUPPORTED_VENDORS,
    SUPPORTED_MODELS,
    RAD_TO_10G_ADVA_HANDOFF_PAID_MATRIX,
    RAD_TO_1G_ADVA_HANDOFF_PAID_MATRIX,
)

logger = logging.getLogger(__name__)


def cpe_swap_main(args: Dict[str, str], before_install: bool = False) -> Dict[str, Any]:
    """Main function for the /v1/cpe_swap endpoint.

    Validates payload values and existing Granite design,
    removes CPE ports from paths, deletes CPE shelf, creates new CPE shelf,
    updates cards and ports, adds new ports to paths.

    Args:
        args (dict)::
            {
                "cid": (string),
                "device_tid": (string),
                "new_model": (string),
                "new_vendor": (string),
                "path_inst_id": (string) (optional),
                "trans_inst_id": (string) (optional),
                "transport_10G": (string) (optional)
            },
        before_install (bool): Optional param for swaps during design

    path_inst_id, trans_inst_id, transport_10G - These are optional and used for bandwidth upgrade swaps

    Returns:
        dict::
            {
                "status": "successful",
                "new_equip_inst_id": new_equip_inst_id (string),
                "new_handoff_port_inst_id": new_handoff_port_inst_id (string),
                "multiple_paths_changed": [multiple_paths_changed (bool), related_cids (list)],
            }

    """
    # Prelim payload checks
    _initial_validations(args)

    # Fallout if more than one path found (Ex. Live and Designed)
    # skip this check for BW upgrades
    if not args.get("path_inst_id"):
        _cid_revision_check(args["cid"])

    # Gather existing path element info
    cpe_path_elements = get_path_elements(args["cid"], f"&TID={args['device_tid']}")

    # remove live path related elements if it is a BW upgrade
    if args.get("path_inst_id"):
        path_elements = cpe_path_elements
        cpe_path_elements = [
            x
            for x in path_elements
            if args["path_inst_id"] == x["INITIAL_CIRCUIT_ID"]
            and x["CIRC_PATH_INST_ID"] in (args["path_inst_id"], args["trans_inst_id"])
        ]
        # Change Bandwidth to 10 Gbps for CPE swaps related to BW upgrades
        if "BASET" in cpe_path_elements[0]["ELEMENT_BANDWIDTH"]:
            cpe_path_elements[0]["ELEMENT_BANDWIDTH"] = "10 Gbps"
            cpe_path_elements[0]["CONNECTOR_TYPE"] = "LC"
            cpe_path_elements[0]["BANDWIDTH"] = "10 Gbps"
            cpe_path_elements[1]["ELEMENT_BANDWIDTH"] = "10 Gbps"
            cpe_path_elements[1]["CONNECTOR_TYPE"] = "LC"
            cpe_path_elements[1]["BANDWIDTH"] = "10 Gbps"

    # Fallout for missing LVL1 or LVL2 or if trunked handoff detected
    if not before_install:
        _l1_l2_evp_check(cpe_path_elements, args["device_tid"])

    # Store existing design values needed later
    (existing_model, existing_vendor, existing_handoff_vlan_info, existing_uplink_vlan_info) = _uplink_handoff_values(
        cpe_path_elements, before_install
    )

    # Fallout if same model detected or existing device vendor is not supported
    if existing_model == args["new_model"]:
        logging.error("ARDA - Requested model is the same as the existing model")
        abort(500, "Requested model is the same as the existing model")

    if existing_vendor not in SUPPORTED_VENDORS:
        err_msg = f"Existing vendor {existing_vendor} is not eligible to be swapped at this time"
        logging.error(err_msg)
        abort(500, err_msg)

    # Additional fallout check for non-CPE devices
    if cpe_path_elements[0]["PATH_Z_SITE_TYPE"] not in ["LOCAL", "CUST_OFFNET"]:
        logging.error("ARDA - Non-CPE device detected. Only CPEs can be swapped")
        abort(500, "Non-CPE device detected. Only CPEs can be swapped")

    # Fallout for Live CPE shelf (bypassed for BW upgrades)
    if cpe_path_elements[0]["ELEMENT_STATUS"] == "Live" and not args.get("path_inst_id"):
        logging.error("ARDA - CPE shelf has Live status. Only Planned and Designed are eligible at this time")
        abort(500, "CPE shelf has Live status. Only Planned and Designed are eligible at this time")

    # Transport path channel validation to check for other circuits designed to the CPE
    if args["new_vendor"] == "CRADLEPOINT":
        related_cids = []
        main_cid_int = None
    else:
        related_cids, main_cid_int = _transport_channel_validation(
            cpe_path_elements[1]["PATH_NAME"] if len(cpe_path_elements) == 2 else cpe_path_elements[0]["PATH_NAME"],
            (
                cpe_path_elements[1]["CHAN_INST_ID"]
                if len(cpe_path_elements) == 2
                else cpe_path_elements[0]["CHAN_INST_ID"]
            ),
            args["cid"],
            args["device_tid"],
            args["new_vendor"],
            args["new_model"],
            before_install,
            args.get("path_inst_id"),
        )

    # Map payload new_model to shelf templates, create UnderlayDeviceTopologyModel, and set uplink params
    new_model_template = args["new_model"]

    if args["new_model"] not in ["FSP 150-GE114PRO-C", "ETX203AX/2SFP/2UTP2SFP", "ETX-220A", "ARC CBA850"]:
        new_model_template = f"{args['new_vendor']} {args['new_model']}"

    if args["new_vendor"] == "CRADLEPOINT":
        device_bw = "RF"
    else:
        device_bw = (
            cpe_path_elements[1]["ELEMENT_BANDWIDTH"]
            if len(cpe_path_elements) == 2
            else cpe_path_elements[0]["ELEMENT_BANDWIDTH"]
        )

    handoff_connector = (
        cpe_path_elements[1]["CONNECTOR_TYPE"]
        if args["new_vendor"] == "CRADLEPOINT"
        else cpe_path_elements[0]["CONNECTOR_TYPE"]
    )

    device_topology = UnderlayDeviceTopologyModel(
        role="cpe",
        vendor=args["new_vendor"],
        connector_type=handoff_connector,
        device_bw=device_bw,
        device_template=new_model_template,
    )

    if new_model_template not in ["FSP 150-GE114PRO-C", "ARC CBA850", "CRADLEPOINT E100 C4D/C7C"]:
        equipment_buildout_uplink_param = f"SLOT={device_topology.uplink.slot}"
    else:
        equipment_buildout_uplink_param = f"PORT_ACCESS_ID={device_topology.uplink.port_access_id}"

    if not before_install:
        # Fallout for attempts to swap 1G for 10G and vise versa (bypassed for BW upgrades)
        if cpe_path_elements[1]["ELEMENT_BANDWIDTH"] != SUPPORTED_MODELS[args["new_model"]][0] and not args.get(
            "path_inst_id"
        ):
            err_msg = (
                f"Provided model is {SUPPORTED_MODELS[args['new_model']][0]} "
                f"but existing model is {cpe_path_elements[1]['ELEMENT_BANDWIDTH']}. "
                "Only 1G -> 1G or 10G -> 10G model swaps are supported"
            )
            logging.error(err_msg)
            abort(500, err_msg)

        # Set UnderlayDeviceTopologyModel handoff
        if args["new_vendor"] == "CRADLEPOINT":
            handoff_bw = "1 Gbps"
        else:
            handoff_bw = cpe_path_elements[0]["BANDWIDTH"]
        device_topology.set_handoff(handoff_bw)

        if main_cid_int and main_cid_int.upper() != device_topology.handoff.port_access_id:
            device_topology.set_known_slot(cpe_path_elements[0]["ELEMENT_BANDWIDTH"], port_access_id=main_cid_int)

        # Create and send LVL1/LVL2 payloads for PUTs that remove CPE from circuit path and transport path
        _remove_ports_from_path(cpe_path_elements, before_install, args["new_vendor"])

        # Delete existing CPE shelf and create new shelf (bypassed for BW upgrades)
        if not args.get("path_inst_id"):
            _delete_shelf(cpe_path_elements)

        create_shelf_payload, create_shelf_resp = _create_shelf(args, cpe_path_elements, new_model_template)

        # Set uplink card and port access ID
        get_uplink_equip_buildout_resp = _uplink_card_and_paid(
            args, equipment_buildout_uplink_param, create_shelf_payload, device_topology, existing_uplink_vlan_info
        )

        (get_handoff_equip_buildout_resp, handoff_card_template, equipment_buildout_handoff_param) = (
            _handoff_get_equipment_buildout(device_topology, args["device_tid"], args.get("path_inst_id"))
        )

        if not handoff_card_template:
            get_handoff_equip_buildout_resp = _set_handoff_card_template(
                create_shelf_payload,
                device_topology,
                args["device_tid"],
                equipment_buildout_handoff_param,
                get_handoff_equip_buildout_resp,
            )

        _set_handoff_paid(get_handoff_equip_buildout_resp, device_topology, existing_handoff_vlan_info)

        # /paths PUTs to add new ports to transport and circuit paths
        transport_put_add_uplink_payload = _build_put_add_payload(cpe_path_elements[1], get_uplink_equip_buildout_resp)
        url = granite_paths_url()
        put_granite(url, transport_put_add_uplink_payload)

        sequence = None
        if args["new_vendor"] == "CRADLEPOINT":
            sequence = "3"
        cid_put_add_handoff_payload = _build_put_add_payload(
            cpe_path_elements[0], get_handoff_equip_buildout_resp, sequence=sequence
        )
        url = granite_paths_url()
        put_granite(url, cid_put_add_handoff_payload)
    else:
        get_handoff_equip_buildout_resp = None
        # Create and send LVL2 payload for PUT that removes CPE port from transport path
        _remove_ports_from_path(cpe_path_elements, before_install, args["new_vendor"])

        # Delete existing CPE shelf and create new shelf
        if not args.get("path_inst_id"):
            _delete_shelf(cpe_path_elements)

        create_shelf_payload, create_shelf_resp = _create_shelf(args, cpe_path_elements, new_model_template)

        # Set uplink card and port access ID
        get_uplink_equip_buildout_resp = _uplink_card_and_paid(
            args, equipment_buildout_uplink_param, create_shelf_payload, device_topology, existing_uplink_vlan_info
        )

        # /paths PUT to add new port to transport
        transport_put_add_uplink_payload = _build_put_add_payload(cpe_path_elements[0], get_uplink_equip_buildout_resp)
        url = granite_paths_url()
        put_granite(url, transport_put_add_uplink_payload)

    multiple_paths_changed = False

    if related_cids:
        for related_cid in related_cids.keys():
            logger.info(f"Adding handoff port on {related_cid}")

            # Extract existing info
            handoff_path_elements = (
                related_cids[related_cid][1][1]
                if related_cids[related_cid][1][1]["LVL"] != "2"
                else related_cids[related_cid][1][0]
            )
            existing_handoff_vlan_info = related_cids[related_cid][0][2]
            existing_port_access_id = related_cids[related_cid][-1]

            # create instance of UnderlayDeviceTopologyModel
            device_topology = UnderlayDeviceTopologyModel(
                role="cpe",
                vendor=args["new_vendor"],
                connector_type=handoff_path_elements["CONNECTOR_TYPE"],
                device_bw=SUPPORTED_MODELS[args["new_model"]][0],
                device_template=new_model_template,
            )
            # Checking for revisions on Related CID to update correct path
            new_inst_id = None
            if args.get("path_inst_id"):
                url = granite_paths_url() + f"?CIRC_PATH_HUM_ID={related_cid}"
                resp = get_granite(url)

                if isinstance(resp, list):
                    if len(resp) > 2:
                        logger.error("Too many revisions for this path")
                        abort(500, f"Too many revisions for {related_cid}")
                    elif int(resp[0].get("pathRev")) < int(resp[1].get("pathRev")):
                        new_inst_id = resp[1]["pathInstanceId"]
                    else:
                        new_inst_id = resp[0]["pathInstanceId"]

                # Set UnderlayDeviceTopologyModel handoff
                device_topology.set_handoff(device_topology.device_bw)

            # translate RAD to ADVA port access IDs and update UnderlayDeviceTopologyModel accordingly
            if before_install:
                # Handoff bandwidth based on CID bandwidth
                element_bandwidth_speed, element_bandwidth_unit = handoff_path_elements["BANDWIDTH"].split()
                handoff_bw = get_device_bw(element_bandwidth_speed, element_bandwidth_unit)
                device_topology.set_known_slot(handoff_bw, port_access_id=existing_port_access_id)

                if existing_model == "ETX-2I-10G-B/8.5/8SFPP" and args["new_model"] == "FSP 150-XG116PRO":
                    for port in RAD_TO_10G_ADVA_HANDOFF_PAID_MATRIX[handoff_path_elements["CONNECTOR_TYPE"]]:
                        if existing_port_access_id == port["RAD"]:
                            device_topology.set_known_slot(handoff_bw, port_access_id=port["ADVA"])
                            break
                elif existing_model == "ETX203AX/2SFP/2UTP2SFP" and args["new_model"] == "FSP 150-GE114PRO-C":
                    for port in RAD_TO_1G_ADVA_HANDOFF_PAID_MATRIX[handoff_path_elements["CONNECTOR_TYPE"]]:
                        if existing_port_access_id == port["RAD"]:
                            device_topology.set_known_slot(handoff_bw, port_access_id=port["ADVA"])
                            break

            if not device_topology.handoff:
                bw = handoff_path_elements["ELEMENT_BANDWIDTH"]
                if handoff_path_elements["ELEMENT_BANDWIDTH"] not in ["1 Gbps", "10 Gbps"]:
                    bw = "1 Gbps"
                device_topology.set_known_slot(bw, port_access_id=existing_port_access_id)

            (get_handoff_equip_buildout_resp, handoff_card_template, equipment_buildout_handoff_param) = (
                _handoff_get_equipment_buildout(device_topology, args["device_tid"], args.get("path_inst_id"))
            )

            # Set handoff card, if needed
            if not handoff_card_template:
                get_handoff_equip_buildout_resp = _set_handoff_card_template(
                    create_shelf_payload,
                    device_topology,
                    args["device_tid"],
                    equipment_buildout_handoff_param,
                    get_handoff_equip_buildout_resp,
                )

            # Update port_access_id
            _set_handoff_paid(get_handoff_equip_buildout_resp, device_topology, existing_handoff_vlan_info)

            # PUT port back in path
            cid_put_add_handoff_payload = _build_put_add_payload(
                handoff_path_elements, get_handoff_equip_buildout_resp, new_inst_id=new_inst_id
            )
            url = granite_paths_url()
            put_granite(url, cid_put_add_handoff_payload)

            multiple_paths_changed = True

    return {
        "status": "successful",
        "new_equip_inst_id": create_shelf_resp["equipInstId"],
        "new_handoff_port_inst_id": (
            get_handoff_equip_buildout_resp[0]["PORT_INST_ID"] if isinstance(create_shelf_resp, dict) else None
        ),
        "multiple_paths_changed": (
            [multiple_paths_changed, list(related_cids.keys())]
            if multiple_paths_changed
            else [multiple_paths_changed, []]
        ),
    }
