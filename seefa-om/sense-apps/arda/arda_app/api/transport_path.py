import logging

from fastapi import Depends, Request, status
from arda_app.bll.transport_path import (
    get_existing_path_elements,
    get_existing_transports,
    create_transport_path_main,
    lookup_hub_clli,
)
from arda_app.bll.models.payloads import TransportPathPayloadModel
from arda_app.common import app_config
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from common_sense.common.errors import abort
from arda_app.api._routers import v3_isp_router

logger = logging.getLogger(__name__)


@v3_isp_router.post("/transport_path", summary="Transport Path Services", status_code=status.HTTP_201_CREATED)
def create_transport_path(
    request: Request, payload: TransportPathPayloadModel, authenticated: bool = Depends(verify_password)
):
    """Create Transport Path"""

    logger.info(f"v3/transport_path payload: {payload.model_dump()}")

    missing = {"circuit_id", "hub_clli_code", "bandwidth_value", "bandwidth_type", "build_type"}.difference(
        payload.model_dump().keys()
    )
    args = request.query_params
    attempt_onboarding = args.get("attempt onboarding", False)

    if len(missing) > 0:
        abort(500, "Required query parameter(s) not specified: {}".format(", ".join(missing)))
    if not payload.circuit_id:
        abort(500, "invalid circuitID")
    payload.circuit_id = payload.circuit_id.strip()
    if not payload.hub_clli_code:
        abort(500, "invalid hub_clli_code")
    payload.hub_clli_code = lookup_hub_clli(payload.hub_clli_code.strip())
    if payload.hub_clli_code == "PLBGNYHK":
        abort(500, f"Unsupported dual legacy company hub: {payload.hub_clli_code}")
    if not payload.bandwidth_value:
        abort(500, "invalid bandwidth_value")
    if not payload.bandwidth_type:
        abort(500, "invalid bandwidth_type")

    """ unsupported_product_families = {'EPL', 'epl', 'EVPL', 'evpl', 'CTBH', 'ctbh'} """
    unsupported_product_families = {"Carrier CTBH - Dark Fiber"}
    if payload.product_name_order_info in unsupported_product_families:
        abort(500, f"Product family {payload.product_name_order_info} not supported in this release")

    # All carrier orders need to be created witha 10G transport
    if payload.product_name_order_info == "Carrier CTBH":
        payload.bandwidth_value = "10"
        payload.bandwidth_type = "Gbps"

    # return response for QA regression testing
    if "STAGE" in app_config.USAGE_DESIGNATION:
        test_response = regression_testing_check("/v3/transport_path", payload.circuit_id)
        if test_response != "pass":
            return test_response

    existing_path_elements = get_existing_path_elements(payload.circuit_id)
    if existing_path_elements:
        abort(500, f"Circuit path already has transport element: {existing_path_elements[0].get('PATH_NAME')}")
    else:
        existing_transports = get_existing_transports(payload.model_dump())
        if not existing_transports:
            transport_id = create_transport_path_main(payload.model_dump(), attempt_onboarding)
            return {"transport_path": transport_id, "message": "Created new transport path"}
        elif existing_transports.get("transport_status") == "use_existing_transport":
            transport_id = existing_transports.get("transport_path")
            return {"transport_path": transport_id, "message": "Found existing transport"}
        elif existing_transports.get("transport_status") == "Live":
            abort(500, f"Found Live existing transport path {existing_transports['transport_path']}, please investigate")
        else:
            abort(
                500,
                f"Existing transport path {existing_transports['transport_path']} "
                f"with status {existing_transports['transport_status']} did not match the customer and site",
            )
