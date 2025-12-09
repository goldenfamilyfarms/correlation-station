from typing import Literal

from arda_app.bll.net_new.utils.shelf_utils import get_device_bw, get_path_elements_data
from arda_app.common.cd_utils import granite_paths_url
from arda_app.dll.granite import get_site, post_granite, put_granite


def create_mtu_new_build_transport_main(payload: dict) -> dict:
    """Create MTU new build transport"""
    cid = payload.get("cid")
    side = payload.get("side")
    mtu_tid = payload.get("mtu_tid")
    cpe_tid = payload.get("cpe_tid")
    mtu_handoff = payload.get("mtu_handoff")
    cpe_uplink = payload.get("cpe_uplink")
    product_name = payload.get("product_name")
    # GET Path Elements LVL1 and LVL2
    lvl1, _ = get_path_elements_data(cid, side)

    # Get first two digits in npa_nxx to use in the trunked path name
    npa_nxx = get_site(site_hum_id=lvl1["Z_SITE_NAME"])[0]["npaNxx"][:2]

    # GET bandwidth speed and unit for path name and post payload
    bw_speed, bw_unit = lvl1["BANDWIDTH"].split()

    if bw_unit == "Gbps" or (bw_unit == "Mbps" and int(bw_speed) >= 1000):
        bw_speed, bw_unit = "10", "Gbps"

    bw_path_name = get_device_bw(bw_speed, bw_unit, for_path_name=True)
    bw = get_device_bw(bw_speed, bw_unit)

    # GET mtu & cpe site name
    # TODO: Need to factor in A side logic
    mtu_site_name = lvl1["Z_SITE_NAME"]
    cpe_site_name = lvl1["PATH_Z_SITE"]

    # Create mtu path name
    path_name = f"{npa_nxx}001.{bw_path_name}.{mtu_tid}.{cpe_tid}"

    post_payload = {
        "PATH_NAME": path_name,
        "PATH_TEMPLATE_NAME": "WS ETHERNET TRANSPORT",
        "PATH_BANDWIDTH": bw,
        "UPDATE_LEG": "true",
        "LEG_NAME": "1",
        "LEG_A_SITE_NAME": mtu_site_name,
        "LEG_Z_SITE_NAME": cpe_site_name,
        "TOPOLOGY": "Point to Point",
        "A_SITE_NAME": mtu_site_name,
        "Z_SITE_NAME": cpe_site_name,
        "PATH_STATUS": "Planned",
        "UDA": {"SERVICE TYPE": {"PRODUCT/SERVICE": "INT-ACCESS TO PREM TRANSPORT", "SERVICE MEDIA": "FIBER"}},
    }

    paths_url = granite_paths_url()
    post_resp = post_granite(paths_url, post_payload)

    # Create mtu new build transport and name from pathIntanceId and pathId
    transport = post_resp["pathInstanceId"] if isinstance(post_resp, dict) else ""
    transport_name = post_resp["pathId"] if isinstance(post_resp, dict) else ""

    # Assign MTU handoff to MTU path
    _assign_handoff_to_path(transport_name, transport, mtu_handoff, paths_url)

    # Assign MTU uplink to MTU path
    _assign_uplink_to_path(transport_name, transport, cpe_uplink, paths_url)

    # Add MTU transport to circuit path
    _add_transport_to_path(cid, transport, product_name, side, paths_url)

    return {
        "mtu_new_build_transport_name": transport_name,
        "mtu_new_build_transport": transport,
        "message": f"{path_name} has been successfully created and added to {cid}",
    }


def _assign_handoff_to_path(transport_name: str, transport: str, mtu_handoff: str, paths_url: str) -> None:
    """Assign MTU handoff to MTU path."""
    put_granite(
        paths_url,
        {
            "PATH_NAME": transport_name,
            "PATH_INST_ID": transport,
            "PATH_LEG_INST_ID": "1",
            "ADD_ELEMENT": "true",
            "PATH_ELEM_SEQUENCE": "1",
            "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
            "PORT_INST_ID": mtu_handoff,
        },
    )


def _assign_uplink_to_path(transport_name: str, transport: str, cpe_uplink: str, paths_url: str) -> None:
    """Assign MTU uplink to MTU path."""
    put_granite(
        paths_url,
        {
            "PATH_NAME": transport_name,
            "PATH_INST_ID": transport,
            "PATH_LEG_INST_ID": "1",
            "ADD_ELEMENT": "true",
            "PATH_ELEM_SEQUENCE": "2",
            "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
            "PORT_INST_ID": cpe_uplink,
        },
    )


def _add_transport_to_path(
    cid: str, transport: str, product_name: str, side: Literal["a_side", "z_side"], paths_url: str
) -> None:
    """Add MTU transport to circuit path."""
    # Set path element sequence
    sequence = "2"
    if product_name == "EPL (Fiber)":
        sequence = "1" if side == "a_side" else "3"

    put_granite(
        paths_url,
        {
            "PATH_NAME": cid,
            "PATH_REVISION": "1",
            "PATH_LEG_INST_ID": "1",
            "ADD_ELEMENT": "true",
            "PATH_ELEM_SEQUENCE": sequence,
            "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
            "PARENT_PATH_INST_ID": transport,
        },
    )
