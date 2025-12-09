import logging

from fastapi import Body, Depends, Path, Request

from arda_app.bll.circuit_status import disco_epl, disco_path_update, update_circuit_status, check_thor
from arda_app.bll.models.payloads import UpdatePathStatusPayloadModel
from arda_app.common import app_config
from common_sense.common.errors import abort
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from arda_app.data.mock_circuits.mc_update_path_status import ups_test_case_responses
from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.put("/update_path_status/{pathid}/status", summary="[Build_Circuit_Design] Update Path Status")
def update_path_status(
    request: Request,
    pathid: str = Path(..., title="Path ID", description="The pathid in the path"),
    payload: UpdatePathStatusPayloadModel = Body(
        ..., title="Update Path Status", description="The payload in the request body"
    ),
    authenticated: bool = Depends(verify_password),
    # status_update: StatusUpdate = Body(
    #     ..., title="Status Update", description="The status update in the request body"
    # ),
):
    """Update the status of a circuit, write GSIP standard UDA values to circuit"""
    logger.info("Initializing Status and UDA update process.")
    logger.info(f"v1/update_path_status/{pathid}/status payload: {payload}")

    status_put_vals = ("service_type", "status", "product_name")
    missing = [key for key in status_put_vals if key not in payload.model_dump()]

    if not all(key in payload.model_dump() for key in status_put_vals):
        logger.error(f"Payload missing field(s): {missing}")
        abort(500, f"Payload missing field(s): {missing}")

    # TEST CASES for regression testing
    ups_test_case_responses(pathid)

    # Unpacking payload values for logging and handle unpredictable cases on intake
    # SEnSE-defined values should be cast to lower, Granite-based values to upper, static SF values left as-is
    service, status = (payload.service_type.lower(), payload.status)

    if "Decom" in status and "Disconnect" in payload.engineering_job_type:
        if not payload.due_date:
            abort(500, "due_date is required for disconnect.")
        if payload.product_name.upper() == "EPL (FIBER)":
            return disco_epl(pathid.upper(), payload.model_dump())
        else:
            return disco_path_update(pathid.upper(), payload.model_dump())
    elif service in (
        "bw_change",
        "change_logical",
        "net_new",
        "net_new_cj",
        "net_new_no_cj",
        "net_new_serviceable",
        "quick_connect",
        "add",
    ):
        # return response for QA regression testing
        if "STAGE" in app_config.USAGE_DESIGNATION:
            url_path = request.url.path
            fixed_part = "/".join(url_path.split("/")[:3])
            test_response = regression_testing_check(fixed_part, pathid)

            if test_response != "pass":
                return test_response

        product_name = payload.product_name

        if status == "Auto-Designed":
            status = "Designed"

        if "Wireless Internet Access" in product_name or "Express" in payload.engineering_job_type:
            leg = False
        else:
            leg = True

        if product_name == "Hosted Voice - (Fiber)" and payload.service_type == "change_logical":
            resp = {"cid": pathid, "status": "Live"}
            designed = "N"
        else:
            resp = update_circuit_status(pathid.upper(), status=status, service=service, leg=leg, product=product_name)
            designed = "Y"

        # thor check only for Logical and bandwidth changes
        if service in ("bw_change", "change_logical"):
            check_thor(pathid, product_name, designed)

        return resp
    else:
        logger.error(f"Unsupported service type: {service}.")
        abort(500, f"Unsupported service type: {service}.")
