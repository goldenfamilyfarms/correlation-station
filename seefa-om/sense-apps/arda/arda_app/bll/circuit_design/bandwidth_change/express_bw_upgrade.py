import logging

from arda_app.bll.circuit_design import common as cmn
from arda_app.bll.circuit_status import update_circuit_status
from arda_app.dll.granite import get_path_association, assign_association
from arda_app.bll.circuit_design.circuit_design_main import bw_upgrade_assign_gsip
from common_sense.common.errors import abort


logger = logging.getLogger(__name__)


def express_bw_upgrade_main(body):
    """Main express bandwidth upgrade logic"""
    pathid = body.get("cid")
    engineering_name = body.get("engineering_name")
    prod_name = body["product_name"]
    logger.info(f"Intake validation completed successfully, executing BW Upgrade for {pathid}")

    # checking whitelist of products we support
    if prod_name not in (
        "Carrier E-Access (Fiber)",
        "Carrier Fiber Internet Access",
        "EP-LAN (Fiber)",
        "EPL (Fiber)",
        "Fiber Internet Access",
    ):
        abort(500, f"Unsupported Product for Express BW Upgrade :: {prod_name}")

    # Validate the intake
    req_bw_val, req_bw_unit, mbps_req_bw_val = cmn.validate_payload_express_bw_upgrade(body)

    # Obtain current BW and Instance ID in Granite
    (main_bw_val, main_bw_unit, mbps_main_bw_val, main_inst, main_rev) = cmn._check_granite_bandwidth(pathid)

    # Compare the requested upgrade data against current Granite data
    if mbps_main_bw_val == mbps_req_bw_val:
        abort_bw = f"{main_bw_val}{main_bw_unit}"

        logger.error(f"No change required for {pathid} - requested bandwidth {abort_bw} matches current bandwidth")
        abort(500, f"No change required for {pathid} - requested bandwidth {abort_bw} matches current bandwidth")

    # downgrade
    if mbps_req_bw_val < mbps_main_bw_val:
        res = (
            f"Requested bandwidth {mbps_req_bw_val} {main_bw_unit} "
            f"is less than current bandwidth {mbps_main_bw_val} {main_bw_unit}"
        )
        logger.error(res)
        abort(500, res)

    # upgrade
    if mbps_req_bw_val > mbps_main_bw_val:
        mbps_delta_bw_val = mbps_req_bw_val - mbps_main_bw_val
        logger.info(f"Requested bandwidth delta value is {mbps_delta_bw_val}")

    # Create circuit revision
    rev_result, rev_instance, rev_path = cmn._granite_create_circuit_revision(pathid, main_rev)

    if not rev_result:
        logger.error(f"Unable to create revision for {pathid}, Granite operation failed")
        abort(500, f"Unable to create new revision in Granite for {pathid}")

    logger.info(f"Revision Create Result: {rev_result} \nRevision Instance ID: {rev_instance}")

    # Make sure revision has new instance ID
    if rev_instance == main_inst:
        logger.error(f"New revision instance ID {rev_instance} matches current revision Instance ID {main_inst}")
        abort(500, f"Revision Instance ID {rev_instance} matches current Instance ID {main_inst}")

    # checking for path associations
    association = None

    if prod_name in ("EP-LAN (Fiber)", "EPL (Fiber)", "Carrier E-Access (Fiber)"):
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

        # add VRFID link to revision
        if prod_name == "EP-LAN (Fiber)":
            cmn.add_vrfid_link(pathid, rev_instance)

    # This actually runs the update against Granite
    update_result = cmn.express_update_circuit_bw(
        pathid, rev_instance, rev_path, req_bw_val, req_bw_unit, engineering_name
    )

    # Set circuit to 'Planned' status
    update_circuit_status(pathid, rev_instance, rev_path, "Planned")

    # assign gsip
    bw_upgrade_assign_gsip(pathid, rev_instance, prod_name, body.get("class_of_service_type", ""))

    logger.info(f"Bandwidth Upgrade operation completed successfully, returning payload: \n{update_result}")

    return update_result
