import logging
import re
from typing import Dict, List, Tuple, Any, Union, Type

from common_sense.common.errors import abort
from arda_app.bll.models.device_topology.underlay import UnderlayDeviceTopologyModel
from arda_app.bll.circuit_design.common import _granite_create_circuit_revision
from arda_app.bll.cpe_swap.cpe_swap_constants import SUPPORTED_VENDORS, SUPPORTED_MODELS
from arda_app.common.cd_utils import (
    granite_cards_url,
    granite_paths_get_url,
    granite_paths_url,
    granite_ports_put_url,
    granite_shelves_post_url,
)
from arda_app.dll.granite import (
    get_path_elements,
    get_granite,
    put_granite,
    delete_granite,
    post_granite,
    get_equipment_buildout,
)
from arda_app.dll.mdso import (
    get_resource_id_from_tid,
    _show_10g_adva_flows,
    _show_1g_adva_ports,
    _show_rad_ports,
    get_active_device,
)


logger = logging.getLogger(__name__)


def _initial_validations(args):
    # Fallout for non-CPE device
    if not args["device_tid"].endswith("ZW"):
        logging.error("ARDA - Non-CPE device detected. Only CPEs can be swapped")
        abort(500, "Non-CPE device detected. Only CPEs can be swapped")

    # Fallout for unsupported vendors or models
    if args["new_vendor"] not in SUPPORTED_VENDORS:
        err_msg = f"Provided vendor: {args['new_vendor']} is not eligible to be swapped at this time"
        logging.error(err_msg)
        abort(500, err_msg)
    elif args["new_model"] not in SUPPORTED_MODELS.keys():
        logging.error(f"ARDA - Provided model: {args['new_model']} is not currently supported")
        abort(500, f"Provided model: {args['new_model']} is not currently supported")

    # Fallout for invalid vendor/model combination
    if args["new_vendor"] != SUPPORTED_MODELS[args["new_model"]][1]:
        logging.error("ARDA - Invalid vendor and model combination")
        abort(500, "Invalid vendor and model combination")


def _cid_revision_check(cid: str) -> None:
    """Fallout if more than one path found (Ex. Live and Designed)"""
    url = granite_paths_get_url(cid)
    get_paths_resp = get_granite(url)
    if len(get_paths_resp) > 1:
        logging.error(f"ARDA - More than one path found for {cid}")
        abort(500, f"More than one path found for {cid}")


def _l1_l2_evp_check(cpe_path_elements: List[Dict[str, str]], tid: str) -> None:
    """Fallout for missing LVL1 or LVL2 or if trunked handoff detected"""
    if len(cpe_path_elements) != 2:
        if cpe_path_elements[0]["PORT_ROLE"] == "UNI-EVP":
            err_msg = "Handoff port with PORT_ROLE EVP-UNI detected. Trunked handoffs are not supported at this time"
            logging.error(err_msg)
            abort(500, err_msg)
        logging.error(f"ARDA - Circuit path missing LVL1 or LVL2 element for {tid}")
        abort(500, f"Circuit path missing LVL1 or LVL2 element for {tid}")
    elif cpe_path_elements[0]["LVL"] != "1" and cpe_path_elements[1]["LVL"] != "2":
        logging.error(f"ARDA - Circuit path missing LVL1 or LVL2 element for {tid}")
        abort(500, f"Circuit path missing LVL1 or LVL2 element for {tid}")


def _get_mdso_resource_id(tid: str) -> Union[str, None]:
    """Check for existing resource ID in MDSO"""
    resource_id = get_resource_id_from_tid(tid)
    if len(resource_id) != 0:
        for item in resource_id:
            if item["orchState"] == "active" and item["properties"]["communicationState"] == "AVAILABLE":
                return item["providerResourceId"]
    return None


def _get_interface_descriptions_from_network(vendor: str, model: str, resource_id: str) -> Dict[str, Any]:
    if vendor == "ADVA":
        if "114" in model or "108" in model:
            return _show_1g_adva_ports(resource_id, timeout=60)
        else:
            return _show_10g_adva_flows(resource_id, timeout=60)
    elif vendor == "RAD":
        return _show_rad_ports(resource_id, timeout=60)


def _transport_channel_validation(
    transport_id: str,
    chan_inst_id: str,
    cid: str,
    tid: str,
    vendor: str,
    model: str,
    before_install: bool,
    path_inst_id: str,
) -> Union[Tuple[Dict[str, Any], str], Tuple[None, None]]:
    """Check if more than one channel is built on the transport path to the CPE"""
    endpoint = "/pathChanAvailability"
    params = f"?PATH_NAME={transport_id}&CHAN_AVAILABILITY=IN USE&MIN_VLAN=1"
    channel_availability_resp = get_granite(f"{endpoint}{params}")

    # Multi path check not supported for bw upgrades so adding bypass logic
    if path_inst_id:
        before_install = True

    if len(channel_availability_resp) > 1:
        related_cid_info = {}
        # Check all CIDs for ones with revisions first
        for channel in channel_availability_resp:
            # add and statment to if statement
            if channel["CHAN_INST_ID"] == chan_inst_id:
                continue
            _cid_revision_check(channel.get("MEMBER_PATH", channel.get("NEXT_PATH", None)))
        # Check all CIDs for correct L1/L2 elements and UNI-EVP port role
        for channel in channel_availability_resp:
            if channel["CHAN_INST_ID"] == chan_inst_id:
                continue
            cpe_path_elements = get_path_elements(
                channel.get("MEMBER_PATH", channel.get("NEXT_PATH", None)), f"&TID={tid}"
            )

            if not path_inst_id:
                _l1_l2_evp_check(cpe_path_elements, tid)

            # Store needed info for later
            related_cid_info[channel.get("MEMBER_PATH", channel.get("NEXT_PATH", None))] = [
                _uplink_handoff_values(cpe_path_elements, before_install, is_related_cid=True),
                cpe_path_elements,
            ]
            if before_install:
                related_cid_info[channel.get("MEMBER_PATH", channel.get("NEXT_PATH", None))].append(
                    cpe_path_elements[0]["PORT_ACCESS_ID"]
                )
        # Check network for which circuit is on which interface
        if not before_install:
            # Attempt to pull interface descriptions
            resource_id = _get_mdso_resource_id(tid)
            if resource_id:
                interface_status = _get_interface_descriptions_from_network(vendor, model, resource_id)
            else:
                # If no resource ID found, attempt onboarding and try again
                _, device = get_active_device(tid, timeout=30, polling=True, model=model, device_vendor=vendor)
                if device:
                    resource_id = device["providerResourceId"]
                    interface_status = _get_interface_descriptions_from_network(vendor, model, resource_id)

            # Parse interface return
            interfaces = {}
            if interface_status and len(interface_status["result"]) > 0:
                if vendor == "ADVA":
                    if "114" in model or "108" in model:
                        for interface in interface_status["result"]:
                            interfaces[interface["label"].upper()] = {"alias": interface["properties"]["alias"]}
                        """
                        'interfaces' ends up looking like:
                            {
                                "ACCESS-1-1-1-3": {"alias": ":EP-UNI:78759:NETWORK AUTOMATION TEAM:"},
                                "ACCESS-1-1-1-4": {"alias": "EP-UNI:ELINE:TEST ACCT DEV:51.L1XX.010216..TWCC:"},
                                "ACCESS-1-1-1-5": {"alias": ""},
                                "ACCESS-1-1-1-6": {"alias": ""},
                            }
                        """
                    else:
                        for flow in interface_status["result"]:
                            for port in flow["properties"]["data"]["relationships"]["endPoints"]["data"]:
                                if ("fp-1-1-1-8" in port["id"] and "116" in model) or (
                                    "fp-1-1-1-26" in port["id"] and "120" in model
                                ):
                                    continue
                                flow_name = port["id"]
                                flow_name = flow_name[0:10]
                                interface_name = re.sub("fp", "ETH_PORT", flow_name)
                                interfaces[interface_name] = {
                                    "alias": flow["properties"]["data"]["attributes"]["additionalAttributes"][
                                        "circuitName"
                                    ]
                                }
                        """
                        'interfaces' ends up looking like:
                            {
                                "ETH_PORT-1-1-1-1": {"alias": "51.L1XX.019875..CHTR"},
                                "ETH_PORT-1-1-1-2": {"alias": "61.L1XX.007185..CHTR"}
                            }
                        """
                elif vendor == "RAD":
                    for interface in interface_status["result"]:
                        if interface["type"] != "SVI":
                            interfaces[interface["id"]] = {"alias": interface["details"]["name"]}
                    """
                    'interfaces' ends up looking like:
                        {
                            "1": {"alias": "ETH-1"},
                            "2": {"alias": "ETH-2"},
                            "3": {"alias": "ETH-3"},
                            "4": {"alias": ":EP-UNI:78759:TEST ACCT DEV:"},
                            "5": {"alias": "EP-UNI:FIA:TEST ACCT DEV@11921 N MOPAC EXPY:51.L1XX.009701..TWCC:"},
                            "6": {"alias": ":EP-UNI:78759:TEST ACCT DEV:"},
                            "101": {"alias": "MNG-ETH"},
                        }
                    """
            else:
                abort(500, "Unable to retrieve interface descriptions from the network")

        # Check that each related circuit can be mapped to an interface
        main_cid_int = None
        if not before_install:
            for related_cid in related_cid_info.keys():
                matched = False
                for interface in interfaces.keys():
                    if related_cid in interfaces[interface]["alias"]:
                        matched = True
                        related_cid_info[related_cid].append(interface.upper())
                    elif cid in interfaces[interface]["alias"]:
                        main_cid_int = interface
                if not matched:
                    abort(500, f"Unable to swap multi-circuit CPE. Related CID {related_cid} not found on the device")
                elif not main_cid_int:
                    abort(500, "Unable to swap multi-circuit CPE. Provided CID not found on the device")

        # Related CIDs passed validations, proceed with removing shelf from their paths
        for related_cid in related_cid_info:
            if path_inst_id:
                logger.info("Creating revisions for related paths and removing handoff ports")

                _, rev_instance, _ = _granite_create_circuit_revision(
                    cpe_path_elements[0]["PATH_NAME"], cpe_path_elements[0]["PATH_REV"]
                )

                cid_put_payload_remove_lvl1 = {
                    "PATH_NAME": related_cid,
                    "PATH_INST_ID": rev_instance,
                    "LEG_NAME": cpe_path_elements[0]["LEG_NAME"],
                    "REMOVE_ELEMENT": "true",
                    "ELEMENTS_TO_REMOVE": cpe_path_elements[0]["SEQUENCE"],
                }

            else:
                cid_put_payload_remove_lvl1, _ = _create_path_put_payloads(
                    related_cid_info[related_cid][1], before_install, vendor, is_related_cid=True
                )

            url = granite_paths_url()
            put_granite(url, cid_put_payload_remove_lvl1)

        return related_cid_info, main_cid_int

    else:
        return None, None


def _uplink_handoff_values(
    cpe_path_elements: List[Dict[str, str]], before_install: bool, is_related_cid: bool = False
) -> Tuple[str, str, Dict[Any, Any], Dict[Any, Any]]:
    existing_model = cpe_path_elements[0]["MODEL"]
    existing_vendor = cpe_path_elements[0]["VENDOR"]
    if before_install and not is_related_cid:
        existing_handoff_vlan_info = None
        existing_uplink_vlan_info = _existing_port_vlan_info(cpe_path_elements[0])
    else:
        existing_handoff_vlan_info = _existing_port_vlan_info(cpe_path_elements[0])
        existing_uplink_vlan_info = _existing_port_vlan_info(cpe_path_elements[1])

    return (existing_model, existing_vendor, existing_handoff_vlan_info, existing_uplink_vlan_info)


def _handoff_get_equipment_buildout(
    device_topology: Type[UnderlayDeviceTopologyModel], tid: str, path_inst_id: bool = False
) -> Tuple[Dict[str, str], str, str]:
    # For BW upgrades we need to use the SLOT to get correct card template
    if device_topology.device_bw == "10 Gbps" or path_inst_id:
        equipment_buildout_handoff_param = f"SLOT={device_topology.handoff.slot}"
    else:
        equipment_buildout_handoff_param = f"PORT_ACCESS_ID={device_topology.handoff.port_access_id}"

    get_handoff_equip_buildout_resp = get_equipment_buildout(f"{tid}&{equipment_buildout_handoff_param}")
    handoff_card_template = get_handoff_equip_buildout_resp[0].get("CARD_TEMPLATE", None)

    return (get_handoff_equip_buildout_resp, handoff_card_template, equipment_buildout_handoff_param)


def _set_handoff_card_template(
    create_shelf_payload,
    device_topology: Type[UnderlayDeviceTopologyModel],
    tid: str,
    equipment_buildout_handoff_param: str,
    get_handoff_equip_buildout_resp: Dict[str, str],
) -> Dict[str, str]:
    handoff_template_cards_post_payload = {
        "SHELF_NAME": create_shelf_payload["SHELF_NAME"],
        "SLOT_INST_ID": get_handoff_equip_buildout_resp[0]["SLOT_INST_ID"],
        "CARD_TEMPLATE_NAME": device_topology.handoff.template,
    }
    url = granite_cards_url()
    post_granite(url, handoff_template_cards_post_payload)

    # GET /equipmentBuildouts again for port inst IDs after loading card template
    return get_equipment_buildout(f"{tid}&{equipment_buildout_handoff_param}")


def _set_handoff_paid(
    get_handoff_equip_buildout_resp: Dict[str, str],
    device_topology: Type[UnderlayDeviceTopologyModel],
    existing_handoff_vlan_info: Dict[Any, Any],
) -> None:
    handoff_put_ports_payload = _build_ports_put_payload(
        get_handoff_equip_buildout_resp[0]["PORT_INST_ID"],
        device_topology.handoff.port_access_id,
        existing_handoff_vlan_info,
    )
    url = granite_ports_put_url()
    put_granite(url, handoff_put_ports_payload)


def _create_path_put_payloads(
    cpe_path_elements: List[Dict[str, str]], before_install: bool, vendor: str, is_related_cid: bool = False
) -> Tuple[Dict[str, str], Dict[str, str]]:
    if before_install and not is_related_cid:
        path_put_payload_lvl1 = None
        index = 0
    else:
        index = 1
        path_put_payload_lvl1 = {
            "PATH_NAME": cpe_path_elements[0]["PATH_NAME"],
            "PATH_INST_ID": cpe_path_elements[0]["CIRC_PATH_INST_ID"],
            "LEG_NAME": cpe_path_elements[0]["LEG_NAME"],
            "REMOVE_ELEMENT": "true",
            "ELEMENTS_TO_REMOVE": cpe_path_elements[0]["SEQUENCE"],
        }

    path_put_payload_lvl2 = {
        "PATH_NAME": cpe_path_elements[index]["PATH_NAME"],
        "PATH_INST_ID": cpe_path_elements[index]["CIRC_PATH_INST_ID"],
        "LEG_NAME": cpe_path_elements[index]["LEG_NAME"],
        "REMOVE_ELEMENT": "true",
        "ELEMENTS_TO_REMOVE": "2" if vendor == "CRADLEPOINT" else cpe_path_elements[index]["SEQUENCE"],
    }

    return path_put_payload_lvl1, path_put_payload_lvl2


def _build_create_shelf_post_payload(
    cpe_path_elements: Dict[str, str], payload: Dict[str, str], template: str
) -> Dict[str, Any]:
    shelf_suffix = {"ADVA": "SWT", "RAD": "NIU", "CRADLEPOINT": "RTR"}
    shelf_type = shelf_suffix[payload["new_vendor"]]

    # for BW upgrades we will need grab the next ZW cpe from the upgraded transport path
    if payload.get("path_inst_id"):
        payload["device_tid"] = payload["transport_10G"].split(".")[-1]

    return {
        "SHELF_NAME": f"{payload['device_tid']}/999.9999.999.99/{shelf_type}",
        "SHELF_TEMPLATE": template,
        "SITE_NAME": cpe_path_elements["A_SITE_NAME"],
        "SHELF_FQDN": f"{payload['device_tid']}.CML.CHTRSE.COM",
        "UDA": {
            "Purchase Info": {"PURCHASING GROUP": "ENTERPRISE", "TRANSPORT MEDIA TYPE": "FIBER"},
            "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            "Device Info": {"NETWORK ROLE": "CUSTOMER PREMISE EQUIPMENT"},
            "Device Config-Equipment": {
                "TARGET ID (TID)": payload["device_tid"],
                "IPv4 ADDRESS": cpe_path_elements["IPV4_ADDRESS"],
                "IP MGMT": "ENTERPRISE",
                "IP MGMT TYPE": "DHCP",
                "OAM PROTOCOL": "y.1731",
            },
        },
    }


def _build_put_add_payload(
    cpe_path_elements: Dict[str, str],
    get_equip_buildout_resp: List[Dict[str, str]],
    sequence: str = "",
    new_inst_id: str = "",
) -> Dict[str, str]:
    return {
        "PATH_NAME": cpe_path_elements["PATH_NAME"],
        "PATH_INST_ID": new_inst_id if new_inst_id else cpe_path_elements["CIRC_PATH_INST_ID"],
        "LEG_NAME": "INTERNET" if cpe_path_elements["LEG_NAME"] == "INTERNET" else "1",
        "PATH_LEG_INST_ID": cpe_path_elements["LEG_INST_ID"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": sequence if sequence else cpe_path_elements["SEQUENCE"],
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "PORT_INST_ID": get_equip_buildout_resp[0]["PORT_INST_ID"],
    }


def _build_ports_put_payload(port_inst_id: str, port_access_id: str, vlan_info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "PORT_INST_ID": port_inst_id,
        "PORT_ACCESS_ID": port_access_id,
        "PORT_STATUS": "Assigned",
        "UDA": {
            "VLAN INFO": {
                k: v
                for k, v in (
                    ("BUNDLED C-VLAN", vlan_info.get("c_vlan", None)),
                    ("CUSTOMER S-VLAN", vlan_info.get("cust_s_vlan", None)),
                    ("INCOMING VLAN OPERATION", vlan_info.get("vlan_operation", None)),
                    ("S-VLAN", vlan_info.get("s_vlan", None)),
                    ("PORT-ROLE", vlan_info.get("port_role", None)),
                )
                if v
            }
        },
    }


def _existing_port_vlan_info(cpe_path_elements: Dict[str, str]) -> Dict[str, Any]:
    return {
        k: v
        for k, v in (
            ("c_vlan", cpe_path_elements["C_VLAN"]),
            ("cust_s_vlan", cpe_path_elements["CUST_S_VLAN"]),
            ("s_vlan", cpe_path_elements["S_VLAN"]),
            ("vlan_operation", cpe_path_elements["VLAN_OPERATION"]),
            ("port_role", cpe_path_elements["PORT_ROLE"]),
        )
        if v
    }


def _remove_ports_from_path(cpe_path_elements: Dict[str, str], before_install: bool, vendor: str):
    (cid_put_payload_remove_lvl1, transport_put_payload_remove_lvl2) = _create_path_put_payloads(
        cpe_path_elements, before_install, vendor
    )

    url = granite_paths_url()
    if not before_install:
        put_granite(url, cid_put_payload_remove_lvl1)
    put_granite(url, transport_put_payload_remove_lvl2)


def _delete_shelf(cpe_path_elements: Dict[str, str]):
    shelf_delete_payload = {
        "SHELF_INST_ID": cpe_path_elements[0]["ELEMENT_REFERENCE"],
        "ARCHIVE_STATUS": "Decommisioned" if cpe_path_elements[0]["ELEMENT_STATUS"] == "Live" else "Canceled",
    }

    url = granite_shelves_post_url()
    delete_granite(url, shelf_delete_payload)


def _create_shelf(args: Dict[str, str], cpe_path_elements: Dict[str, str], new_model_template: str):
    create_shelf_payload = _build_create_shelf_post_payload(cpe_path_elements[0], args, new_model_template)
    url = granite_shelves_post_url()
    create_shelf_resp = post_granite(url, create_shelf_payload)
    return create_shelf_payload, create_shelf_resp


def _uplink_card_and_paid(
    args: Dict[str, str],
    equipment_buildout_uplink_param: str,
    create_shelf_payload: Dict[str, Any],
    device_topology: Type[UnderlayDeviceTopologyModel],
    existing_uplink_vlan_info: Dict[str, Any],
):
    get_uplink_equip_buildout_resp = get_equipment_buildout(f"{args['device_tid']}&{equipment_buildout_uplink_param}")
    uplink_card_template = get_uplink_equip_buildout_resp[0].get("CARD_TEMPLATE", None)

    # Load card templates, if needed
    if not uplink_card_template:
        uplink_template_cards_post_payload = {
            "SHELF_NAME": create_shelf_payload["SHELF_NAME"],
            "SLOT_INST_ID": get_uplink_equip_buildout_resp[0]["SLOT_INST_ID"],
            "CARD_TEMPLATE_NAME": device_topology.uplink.template,
        }

        url = granite_cards_url()
        post_granite(url, uplink_template_cards_post_payload)

        # GET /equipmentBuildouts again for port inst IDs after loading card template
        get_uplink_equip_buildout_resp = get_equipment_buildout(
            f"{args['device_tid']}&{equipment_buildout_uplink_param}"
        )

    # Update port_access_ids and port VLAN INFO
    uplink_put_ports_payload = _build_ports_put_payload(
        get_uplink_equip_buildout_resp[0]["PORT_INST_ID"],
        device_topology.uplink.port_access_id,
        existing_uplink_vlan_info,
    )
    url = granite_ports_put_url()
    put_granite(url, uplink_put_ports_payload)

    return get_uplink_equip_buildout_resp
