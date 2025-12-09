import logging

from arda_app.bll.circuit_design.common import (
    _check_granite_bandwidth,
    _granite_create_circuit_revision,
    validate_payload_express_bw_upgrade,
    express_update_circuit_bw,
    fia_ipv6_check,
    add_vrfid_link,
    get_cpe_info,
)
from arda_app.bll.circuit_status import update_circuit_status
from common_sense.common.errors import abort
from arda_app.dll.mdso import get_active_device
from arda_app.dll.granite import get_path_association, assign_association
from arda_app.bll.circuit_design.circuit_design_main import bw_upgrade_assign_gsip


from arda_app.bll.net_new.utils.shelf_utils import (
    cpe_service_check,
    get_cpe_services,
    get_cpe_transport_paths,
    get_zsite,
)

logger = logging.getLogger(__name__)


def bw_downgrade_main(body):
    """Main bandwidth downgrade logic"""
    pathid = body.get("cid")
    engineering_name = body.get("engineering_name")
    logger.info(f"Intake validation completed successfully, executing BW Downgrade for {pathid}")

    # checking whitelist of products we support
    if body["product_name"] not in ("Fiber Internet Access", "Carrier Fiber Internet Access", "EP-LAN (Fiber)"):
        abort(500, f"Unsupported Product for BW Downgrade :: {body['product_name']}")

    # Validate the intake
    req_bw_val, req_bw_unit, mbps_req_bw_val = validate_payload_express_bw_upgrade(body)

    # Obtain current BW and Instance ID in Granite
    (main_bw_val, main_bw_unit, mbps_main_bw_val, main_inst, main_rev) = _check_granite_bandwidth(pathid)

    # Compare the requested downgrade data against current Granite data
    if mbps_main_bw_val == mbps_req_bw_val:
        abort_bw = f"{main_bw_val}{main_bw_unit}"

        logger.error(f"No change required for {pathid} - requested bandwidth {abort_bw} matches current bandwidth")
        abort(500, f"No change required for {pathid} - requested bandwidth {abort_bw} matches current bandwidth")

    if mbps_req_bw_val > mbps_main_bw_val:
        logger.error(
            f"Requested bandwidth {mbps_req_bw_val} {main_bw_unit} "
            f"is greater than current bandwidth {mbps_main_bw_val} {main_bw_unit}"
        )
        abort(
            500,
            f"Requested bandwidth {mbps_req_bw_val} {main_bw_unit} "
            f"is greater than current bandwidth {mbps_main_bw_val} {main_bw_unit}",
        )

    cpe_installer = False
    mw_needed = "No"
    hub_work_required = False

    supported_cpe = ("ADVA", "RAD")

    tid, vendor, model = get_cpe_info(pathid)

    # cpe vendor check
    if vendor not in supported_cpe:
        logger.error("Unsupported vendor")
        abort(500, f"Unsupported CPE vendor :: {vendor}")

    # verifying the device is active on the network to perform BW change later
    try:
        _, _ = get_active_device(tid)
    except Exception:
        logger.error("Unable to login into the device please investigate")
        abort(500, f"Unable to login into the device: {tid} - {vendor} - {model}")

    z_site_info = get_zsite(pathid)
    shelf_dict = get_cpe_transport_paths(tid, z_site_info)
    shelf_info, cids = get_cpe_services(shelf_dict)
    cpe_service_check(shelf_info, cids)

    # Create circuit revision
    rev_result, rev_instance, rev_path = _granite_create_circuit_revision(pathid, main_rev)

    if not rev_result:
        logger.error(f"Unable to create revision for {pathid}, Granite operation failed")
        abort(500, f"Unable to create new revision in Granite for {pathid}")
    logger.info(f"Revision Create Result: {rev_result} \nRevision Instance ID: {rev_instance}")

    # Make sure revision has new instance ID
    if rev_instance == main_inst:
        logger.error(f"New revision instance ID {rev_instance} matches current revision Instance ID {main_inst}")
        abort(500, f"Revision Instance ID {rev_instance} matches current Instance ID {main_inst}")

    association = None

    if body["product_name"] == "EP-LAN (Fiber)":
        association = get_path_association(main_inst)

        if isinstance(association, dict):
            if association.get("retString"):
                logger.error("Missing association in granite for CID")
                abort(500, f"Missing association in granite for {pathid}")

        # adding path association to revision
        evcid = association[0]["associationValue"]
        association_name = association[0]["associationName"]
        range_name = association[0]["numberRangeName"]

        assoc_result = assign_association(rev_instance, evcid, association_name, range_name)

        if not assoc_result:
            logger.error("Unable to add path association, Granite operation failed")
            abort(500, f"Unable to add path association {evcid} to new revision in Granite for {pathid}")

        # link revision to VRFID network link
        add_vrfid_link(pathid, rev_instance)

    # This actually runs the update against Granite
    update_result = express_update_circuit_bw(pathid, rev_instance, rev_path, req_bw_val, req_bw_unit, engineering_name)

    # Set the circuit to 'Planned' status
    update_circuit_status(pathid, rev_instance, rev_path, "Planned")

    if "Fiber Internet Access" in body["product_name"]:
        fia_ipv6_check(pathid, mw_needed=False)

    # assign gsip
    bw_upgrade_assign_gsip(pathid, rev_instance, body["product_name"], body.get("class_of_service_type", ""))

    update_result["cpe_installer"] = cpe_installer
    update_result["mw_needed"] = mw_needed
    update_result["hub_work_required"] = hub_work_required
    logger.info(f"Bandwidth Downgrade operation completed successfully, returning payload: \n{update_result}")

    return update_result
