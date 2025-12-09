import logging
from arda_app.bll.models.device_topology import (
    AUDIOCODES_M500B,
    # AUDIOCODES_MEDIANT_1000B_4D38FXS,
    AUDIOCODES_MEDIANT_MP_52424FXS,
    AUDIOCODES_MEDIANT_800B,
    AUDIOCODES_MEDIANT_800C_60_SIP,
    AUDIOCODES_MEDIANT_800C_200_SIP,
)

from common_sense.common.errors import abort
from arda_app.bll.models.device_topology.overlay import OverlayDeviceTopologyModel
from arda_app.bll.net_new.utils.shelf_utils import get_shelf_names
from arda_app.common.cd_utils import granite_ports_put_url, granite_shelves_post_url
from arda_app.dll.granite import (
    get_equipment_buildout,
    insert_card_template,
    post_granite,
    put_granite,
    get_circuit_site_info,
)

logger = logging.getLogger(__name__)


def create_vgw_shelf(payload: dict):
    """Create VGW shelf."""
    cid = payload.get("cid")
    product_name = payload.get("product_name")
    number_of_circuits_in_group = payload.get("number_of_circuits_in_group")
    number_of_b_channels = payload.get("number_of_b_channels")
    service_code = payload.get("service_code")

    # GET circuit sites info
    lvl1 = get_circuit_site_info(cid)[0]

    # Update tid suffix
    tid_suffix = ""

    if product_name in {"SIP - Trunk (Fiber)", "SIP Trunk(Fiber) Analog", "SIP - Trunk (DOCSIS)"}:
        tid_suffix = "G01"
    elif product_name in {"PRI Trunk (Fiber)", "PRI Trunk(Fiber) Analog"}:
        if int(number_of_circuits_in_group) > 1:
            msg = "Multiple PRI trunks are currently unsupported"
            logger.error(msg)
            abort(500, msg)

        tid_suffix = "G1W"

    # Select device
    device_template = ""

    if product_name == "SIP - Trunk (Fiber)":
        if int(number_of_b_channels) <= 60:
            device_template = AUDIOCODES_MEDIANT_800C_60_SIP
        else:
            device_template = AUDIOCODES_MEDIANT_800C_200_SIP
    elif product_name == "PRI Trunk (Fiber)":
        if number_of_circuits_in_group == "1":
            device_template = AUDIOCODES_M500B
        elif number_of_circuits_in_group == "2":
            device_template = AUDIOCODES_MEDIANT_800B
        else:
            # will fallout before it gets here please see abort logic above
            device_template = "M800C/V/4ET8S/CH/ALU"
    elif product_name in ("SIP Trunk(Fiber) Analog", "PRI Trunk(Fiber) Analog"):
        if service_code == "RZ901":
            device_template = AUDIOCODES_MEDIANT_MP_52424FXS
        elif service_code == "RZ900":
            if product_name == "SIP Trunk(Fiber) Analog":
                if int(number_of_b_channels) <= 60:
                    device_template = AUDIOCODES_MEDIANT_800C_60_SIP
                else:
                    device_template = AUDIOCODES_MEDIANT_800C_200_SIP
            else:  # PRI Trunk(Fiber) Analog logic
                if number_of_circuits_in_group in ("1", "2"):
                    device_template = AUDIOCODES_MEDIANT_800B
                else:
                    # will fallout before it gets here please see abort logic above
                    device_template = "M800C/V/4ET8S/CH/ALU"
        else:
            abort(500, "service code was not provided and is required for SIP and PRI analog")

    # SET device topology
    device_topology = OverlayDeviceTopologyModel(role="vgw", device_template=device_template)  # type: ignore

    # GET shelf name
    tid = f"{lvl1['Z_CLLI']}{tid_suffix}"
    shelf_name, tid = get_shelf_names(element_name=tid, vendor=device_topology.vendor, tid=tid)

    # Create VGW shelf payload
    shelf_create_payload = {
        "SHELF_NAME": shelf_name,
        "SHELF_TEMPLATE": device_topology.device_template,
        "SITE_NAME": lvl1["Z_SITE_NAME"],
        "SHELF_FQDN": f"{tid}.CML.CHTRSE.COM" if "DOCSIS" in product_name else f"{tid}.CHTRSE.COM",
        "UDA": {
            "Purchase Info": {
                "PURCHASING GROUP": "ENTERPRISE",
                "TRANSPORT MEDIA TYPE": "COAX" if "DOCSIS" in product_name else "FIBER",
            },
            "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            "Device Config-Equipment": {
                "TARGET ID (TID)": tid,
                "IPv4 ADDRESS": "",
                "IP MGMT": "ENTERPRISE",
                "IP MGMT TYPE": "DHCP" if "DOCSIS" in product_name else "STATIC",
                "OAM PROTOCOL": "None",
            },
            "Device Info": {"NETWORK ROLE": "CUSTOMER PREMISE EQUIPMENT"},
        },
    }

    # POST Create VGW shelf from template to granite
    _create_shelf(shelf_create_payload)

    # PUT build uplink card
    vgw_uplink_pid, vgw_uplink_paid = _build_uplink(shelf_name, device_topology)
    vgw_handoff_pid, vgw_handoff_paid = _build_handoff(shelf_name, device_topology)

    # set response
    resp = {
        "vgw_shelf": shelf_name,
        "vgw_tid": tid,
        "vgw_uplink": vgw_uplink_pid,
        "vgw_uplink_paid": vgw_uplink_paid,
        "vgw_handoff": vgw_handoff_pid,
        "vgw_handoff_paid": vgw_handoff_paid,
        "circ_path_inst_id": lvl1["CIRC_PATH_INST_ID"],
    }

    return resp


def _create_shelf(shelf_create_payload: dict) -> None:
    """Create Voice Gateway shelf in Granite."""
    shelf_create_url = granite_shelves_post_url()
    shelf_create_data = post_granite(shelf_create_url, shelf_create_payload)

    if shelf_create_data["retString"] == "Shelf has nothing to update":
        logger.error(f"Unsupported existing shelf found.\nURL: {shelf_create_url} \nResponse: {shelf_create_data}")
        abort(
            500,
            message="Unsupported existing shelf found. Must be no prior VGW shelf at site for this customer",
            url=shelf_create_url,
            response=shelf_create_data,
        )

    if shelf_create_data["retString"] != "Shelf Added":
        logger.error(
            f"Unexpected Granite response, could not find 'Shelf Added' message. "
            f"\nURL: {shelf_create_url} \nResponse: {shelf_create_data}"
        )
        abort(500, message="Incorrect shelf data payload from Granite", url=shelf_create_url, response=shelf_create_data)

    logger.info(f"VGW shelf created \nGranite shelf create response: \n{shelf_create_data}")


def _build_uplink(shelf_name: str, device_topology: OverlayDeviceTopologyModel) -> str:
    """add uplink card"""
    equipment_data = get_equipment_buildout(shelf_name)

    if not device_topology.uplink:
        abort(500, "device topology is missing uplink port data")

    for item in equipment_data:
        if all(
            (not item.get("PORT_USE"), item.get("SLOT") == device_topology.uplink.slot, not item.get("PORT_INST_ID"))
        ):
            insert_card_template(item, device_topology.uplink.template)
            break

    # run get equipment buildout again to retrieve latest data
    equipment_data = get_equipment_buildout(shelf_name)
    port_inst_id = ""

    # different logic for M800B-V-1ET4S-4L when choosing uplink multiple port 01
    for e in equipment_data:
        if e.get("PORT_NAME", "") == device_topology.uplink.slot:
            if device_topology.model == "M800B-V-1ET4S-4L":
                if e.get("SLOT", "") == "WAN":
                    port_inst_id = e.get("PORT_INST_ID")
                    break
            else:
                port_inst_id = e.get("PORT_INST_ID")
                break

    payload = {
        "PORT_ACCESS_ID": device_topology.uplink.port_access_id,
        "PORT_INST_ID": port_inst_id,
        "PORT_STATUS": "Assigned",
    }

    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id, device_topology.uplink.port_access_id


def _build_handoff(shelf_name: str, device_topology: OverlayDeviceTopologyModel) -> str:
    """build_handoff"""
    equipment_data = get_equipment_buildout(shelf_name)

    if not device_topology.handoff:
        abort(500, "device topology is missing handoff port data")

    for item in equipment_data:
        if all(
            (not item.get("PORT_USE"), item.get("SLOT") == device_topology.handoff.slot, not item.get("PORT_INST_ID"))
        ):
            insert_card_template(item, device_topology.handoff.template)
            break

    # run get equipment buildout again to retrieve latest data
    equipment_data = get_equipment_buildout(shelf_name)
    logger.debug(f"SHELF NAME: {shelf_name}")
    logger.debug(f"EQUIP DATA: {equipment_data}")

    port_inst_id = None

    # get port_inst_id
    for e in equipment_data:
        if e.get("PORT_NAME", "") == device_topology.handoff.slot:
            port_inst_id = e.get("PORT_INST_ID")

    payload = {
        "PORT_ACCESS_ID": device_topology.handoff.port_access_id,
        "PORT_INST_ID": port_inst_id,
        "PORT_STATUS": "Assigned",
    }
    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id, device_topology.handoff.port_access_id
