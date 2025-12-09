import logging

from fastapi import Depends
from arda_app.bll.models.payloads import BuildCircuitDesignPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.data.mock_circuits.mc_build_circuit_design import bcd_test_case_response
from arda_app.common.build_circuit_design_template import build_circuit_design_main

from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.post("/build_circuit_design", summary="SEnSE intake service to build a circuit")
def build_circuit_design(payload: BuildCircuitDesignPayloadModel, authenticated: bool = Depends(verify_password)):
    """
    Checks eligibility of service and product ordered and runs Design automation process if successful
    """
    payload_dict = payload.model_dump(exclude_none=True)
    logger.info(f"v1/build_circuit_design payload: {payload_dict}")

    # TEST CASES for regression testing
    if payload_dict.get("z_side_info") is not None:
        bcd_test_case_response(payload_dict)

    return build_circuit_design_main(payload_dict)
