import logging

from arda_app.common.cd_utils import (
    granite_shelves_post_url,
    granite_paths_url,
    granite_equipments_url,
    granite_uda_get_url,
)
from common_sense.common.errors import abort
from arda_app.dll.granite import get_equipment_buildout, put_granite, get_granite
from arda_app.bll.net_new.create_mne import _create_shelf, _add_port_to_path
from arda_app.dll.sense import get_sense

logger = logging.getLogger(__name__)
SF_TO_LEGACY_PATH = {"Charter": "L-CHTR", "TWC": "L-TWC", "Bright House": "L-BHN"}


def create_SBB_shelves(payload) -> dict:
    """Begin SBB Process"""
    cid = payload.get("cid")
    # Paths get call and validate list return with single content.
    paths = get_granite(granite_paths_url() + f"?CIRC_PATH_HUM_ID={cid}&LVL=1")
    if isinstance(paths, list):
        if len(paths) > 1:
            abort(500, f"Unable to create SBB Shelves: 2 Revisions found for {cid}")
        paths = paths[0]
    else:
        if "No records found with the specified search criteria..." in paths.values():
            abort(500, f"Empty Path response received. Path missing from Granite for cid: {cid}")
    udas = get_granite(granite_uda_get_url(paths["pathInstanceId"]))
    uda_dict = {}
    if udas:
        for e in udas:
            uda_dict[e["ATTR_NAME"]] = e["ATTR_VALUE"]
    get_url = (
        f"?CLLI={paths['zSideSiteName'][:8]}&SITE_NAME={paths['zSideSiteName']}&OBJECT_TYPE=SHELF&WILD_CARD_FLAG=true"
    )
    site_eqp = get_granite(granite_equipments_url() + get_url, 60, False)
    # Grabbing equipments at site and fail out if either are fiound as change orders are not supported at this time
    if isinstance(site_eqp, list):
        for shelf in site_eqp:
            if shelf["EQUIP_MODEL"] == "WORLDBOX" or shelf["EQUIP_MODEL"] == "MGT2000-SE":
                abort(500, f"MNE SBB Design: Unexpected issue: shelves found at site: {shelf['EQUIP_NAME']}")

    clli = paths["zSideSiteName"][:8]

    tap_payload = {
        "SHELF_NAME": f"{clli}RF0/999.9999.999.99/TAP",
        "SHELF_TEMPLATE": "ANTRONIX TAP",
        "SITE_NAME": f"{paths['zSideSiteName']}",
        "SHELF_STATUS": "Designed",
        "UDA": {"LEGACY_EQUIPMENT": {"SOURCE": "L-CHTR"}},
    }
    logger.info(f"Creating shelf w/ payload: {tap_payload}")
    # POST Create CPE shelf from template to granite
    _create_shelf(tap_payload)

    wb_payload = {
        "SHELF_NAME": f"{clli}N00/999.9999.999.99/VCE",
        "SHELF_TEMPLATE": "ADB PHANTOM",
        "SITE_NAME": f"{paths['zSideSiteName']}",
        "SHELF_STATUS": "Designed",
        "UDA": {
            "LEGACY_EQUIPMENT": {"SOURCE": "L-CHTR"},
            "Device Info": {"DEVICE ID": f"{clli}N00"},
            "Purchase Info": {"PURCHASING GROUP": "MANAGED SERVICES - VIDEO", "TRANSPORT MEDIA TYPE": "COAX"},
        },
    }
    logger.info(f"Creating shelf w/ payload: {wb_payload}")
    # POST Create CPE shelf from template to granite
    wb_response = _create_shelf(wb_payload)
    # Changed Model to WORLDBOX
    wb_model_pl = {"SHELF_INST_ID": f"{wb_response['equipInstId']}", "SHELF_MODEL": "WORLDBOX", "SET_CONFIRMED": "TRUE"}
    put_response = put_granite(granite_shelves_post_url(), wb_model_pl, 60)
    logger.info(f"\nput_response:{put_response}\n")

    # Update path to Designed and Change Leg name to "SBB WB COAX"
    leg_payload = {
        "PATH_INST_ID": paths["pathInstanceId"],
        "LEG_NAME": "1",
        "NEW_LEG_NAME": "SBB WB COAX",
        "LEG_Z_SITE_NAME": paths["zSideSiteName"],
        "UPDATE_LEG": "true",
        "PATH_STATUS": "Designed",
    }
    if paths.get("aSideSiteName"):
        leg_payload["LEG_A_SITE_NAME"] = paths["aSideSiteName"]
    post_response = put_granite(granite_paths_url(), leg_payload)
    logger.info(f"Leg change response: {post_response}")

    # ADD TAP Uplink port to Path
    equipment_data = get_equipment_buildout(f"{clli}RF0/999.9999.999.99/TAP")
    uplink_inst_id = [port["PORT_INST_ID"] for port in equipment_data if port.get("PORT_NAME") == "RF IN"]
    if not uplink_inst_id:
        abort(500, f"Uplink port not found on shelf: {clli}RF0/999.9999.999.99/TAP")

    uplink_payload = {"cid": cid, "port_pid": uplink_inst_id[0]}
    _add_port_to_path(uplink_payload)

    # ADD WORLDBOX UNI port to Path
    equipment_data = get_equipment_buildout(f"{clli}N00/999.9999.999.99/VCE")
    handoff_inst_id = [port["PORT_INST_ID"] for port in equipment_data if port.get("PORT_NAME") == "RF INPUT"]
    if not handoff_inst_id:
        abort(500, f"Handoff port not found on shelf: {clli}N00/999.9999.999.99/VCE")

    handoff_payload = {"cid": cid, "port_pid": handoff_inst_id[0]}
    _add_port_to_path(handoff_payload)

    glink = "https://granite-ise.chartercom.com:2269/web-access/WebAccess.html"
    plink = "#HistoryToken,type=Path,mode=VIEW_MODE,instId="
    granite_link = glink + plink + paths["pathInstanceId"]

    # parse data and return exit_data
    resp = {
        "TAP_name": "HRHNLAATRF0/999.9999.999.99/TAP",
        "WB_name": "HRHNLAATN00/999.9999.999.99/VCE",
        "TAP_uplink_pid": uplink_inst_id[0],
        "WB_handoff_pid": handoff_inst_id[0],
        "circ_path_inst_id": paths["pathInstanceId"],
        "maintenance_window_needed": "No",
        "hub_work_required": "No",
        "cpe_installer_needed": "Yes",
        "granite_link": granite_link,
    }
    logger.info(f"SBB Design complete. Response: {resp}")

    return resp


def check_for_pillow_speakers(payload):
    # Reject if Pillow speakers are found
    epr = payload.get("engineering_name")
    endpoint = "/beorn/v1/rphy/rf_codes?"
    beorn_payload = {"eng_id": {epr}, "prefix": "RI"}
    beorn_response = get_sense(endpoint, beorn_payload)
    codes = beorn_response.get("svc_codes")
    if beorn_response.get("error"):
        abort(500, beorn_response.get("error"))
    if not codes:
        abort(500, f"No Svc codes returned from Salesforce for {epr}")
    elif codes and "RI713" in codes:
        abort(500, "Ineligible for automation: Pillow Speakers detected.")
