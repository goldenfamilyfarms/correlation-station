import logging

from common_sense.common.errors import abort
from arda_app.bll.models.device_topology.underlay import UnderlayDeviceTopologyModel
from arda_app.bll.net_new.utils.shelf_utils import get_path_elements_data, get_shelf_names
from arda_app.common.cd_utils import granite_ports_put_url, granite_shelves_post_url

from arda_app.dll.granite import get_equipment_buildout, insert_card_template, post_granite, put_granite


logger = logging.getLogger(__name__)


def create_mtu_shelf(payload: dict) -> dict:
    """
    Create an MTU aggregate shelf.

    TODO: will need to add `element_name` field to be able to assign a static
    IP address to the mtu agg shelf creation payload.

    Notes: Will always be 10 gb device. Connector type will always be LC (handoff and uplink).
    the downstream customer is the CPE.
    """
    cid = payload.get("cid")
    side = payload.get("side")

    # GET Path Elements LVL1 and LVL2
    lvl1, _ = get_path_elements_data(cid, side)

    # SET device topology
    device_topology = UnderlayDeviceTopologyModel(role="mtu", connector_type="LC", device_bw="10 Gbps")

    # GET shelf name
    shelf_name, tid = get_shelf_names(element_name=lvl1["ELEMENT_NAME"], vendor=device_topology.vendor)

    # Check for build type change since ISP
    if tid.endswith("ZW"):
        abort(
            500,
            "Manual Intervention detected at create_mtu:"
            f" Transport {lvl1['ELEMENT_NAME']} does not align with build_type MTU New Build",
        )

    # Create payload data for shelf creation
    shelf_create_payload = {
        "SHELF_NAME": shelf_name,
        "SHELF_TEMPLATE": device_topology.device_template,
        "SITE_NAME": lvl1["Z_SITE_NAME"],
        "SHELF_FQDN": f"{tid}.CML.CHTRSE.COM",
        "UDA": {
            "Purchase Info": {"PURCHASING GROUP": "ENTERPRISE", "TRANSPORT MEDIA TYPE": "FIBER"},
            "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            "Device Config-Equipment": {
                "TARGET ID (TID)": tid,
                "IPv4 ADDRESS": "DHCP",
                "IP MGMT": "ENTERPRISE",
                "IP MGMT TYPE": "DHCP",
                "OAM PROTOCOL": "None",
            },
            "Device Info": {"NETWORK ROLE": "AGGREGATION SWITCH - MTU", "MTU CLASSIFICATION": "QUICK CONNECT"},
        },
    }

    # POST shelf in Granite
    _create_shelf(shelf_create_payload)

    # Add Cards
    mtu_uplink = _build_uplink(shelf_name=shelf_name, device_topology=device_topology)
    mtu_handoff = _build_handoff(
        shelf_name=shelf_name, circuit_bandwidth=lvl1["BANDWIDTH"], device_topology=device_topology
    )

    return {
        "mtu_shelf": shelf_name,
        "mtu_tid": tid,
        "mtu_uplink": mtu_uplink,
        "mtu_handoff": mtu_handoff,
        "mtu_pe_path": lvl1["ELEMENT_REFERENCE"],
        "mtu_z_site": lvl1["Z_SITE_NAME"],
    }


def _create_shelf(shelf_create_payload: dict) -> None:
    """Create MTU Aggregate shelf in Granite."""
    shelf_create_url = granite_shelves_post_url()
    shelf_create_data = post_granite(shelf_create_url, shelf_create_payload)

    if shelf_create_data["retString"] == "Shelf has nothing to update":
        logger.error(f"Unsupported existing shelf found.\nURL: {shelf_create_url} \nResponse: {shelf_create_data}")
        abort(
            500,
            message="Unsupported existing shelf found. Must be no prior MTU shelf at site for this customer",
            url=shelf_create_url,
            response=shelf_create_data,
        )

    if shelf_create_data["retString"] != "Shelf Added":
        logger.error(
            f"Unexpected Granite response, could not find 'Shelf Added' message. "
            f"\nURL: {shelf_create_url} \nResponse: {shelf_create_data}"
        )
        abort(500, message="Incorrect shelf data payload from Granite", url=shelf_create_url, response=shelf_create_data)

    logger.info(f"MTU aggregate shelf created \nGranite shelf create response: \n{shelf_create_data}")


def _build_uplink(shelf_name: str, device_topology: UnderlayDeviceTopologyModel) -> str:
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

    # get port_inst_id
    port_inst_id = "".join(e.get("PORT_INST_ID") for e in equipment_data if e["SLOT"] == device_topology.uplink.slot)

    payload = {"PORT_ACCESS_ID": device_topology.uplink.port_access_id, "PORT_INST_ID": port_inst_id}

    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id


def _build_handoff(shelf_name: str, circuit_bandwidth: str, device_topology: UnderlayDeviceTopologyModel) -> str:
    """add hand off cards"""
    equipment_data = get_equipment_buildout(shelf_name)
    device_topology.set_handoff(circuit_bandwidth=circuit_bandwidth)

    if not device_topology.handoff:
        abort(500, "device topology is missing uplink port data")

    for item in equipment_data:
        if all(
            (not item.get("PORT_USE"), item.get("SLOT") == device_topology.handoff.slot, not item.get("PORT_INST_ID"))
        ):
            insert_card_template(item, device_topology.handoff.template)

            # run get equipment buildout again to retrieve latest data
            equipment_data = get_equipment_buildout(shelf_name)
            break

    # get port_inst_ids
    payload = [
        {"PORT_ACCESS_ID": device_topology.handoff.port_access_id, "PORT_INST_ID": e.get("PORT_INST_ID")}
        for e in equipment_data
        if e["SLOT"] == device_topology.handoff.slot
    ][0]

    put_url = granite_ports_put_url()
    put_granite(put_url, payload)

    return payload["PORT_INST_ID"]
