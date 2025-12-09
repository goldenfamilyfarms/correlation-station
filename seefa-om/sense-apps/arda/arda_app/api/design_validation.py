import logging

from fastapi import Depends

from arda_app.bll.models.payloads import DesignValidationPayloadModel
from arda_app.bll.models.responses import DesignValidationResponseModel, DesignValidationOdinResponseModel
from arda_app.bll.circuit_status import check_thor
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_mac_router
from typing import Union

logger = logging.getLogger(__name__)


@v1_design_mac_router.post(
    "/design_validation",
    summary="Design Validation",
    response_model=Union[DesignValidationResponseModel, DesignValidationOdinResponseModel],
)
def design_validation(payload: DesignValidationPayloadModel, authenticated: bool = Depends(verify_password)):
    """
    Design Validation
    """
    logger.info("Initializing Design Validation")
    logger.info(f"v1/design_validation payload: {payload.model_dump()}")

    resp = check_thor(payload.cid, payload.product_name, designed="Y", raw_response=payload.passthrough)

    if payload.passthrough:
        return resp

    compliant, data = resp
    logger.debug(f"NICE GSIP Compliance result: {compliant} \nNICE GSIP Compliance data: \n{data}")

    if compliant is True:
        return {"validation_circuit_design_notes": "No issues found with the circuit", "ODIN_verification": "Passed"}

    return {"validation_circuit_design_notes": f"Issues found with circuit {data}", "ODIN_verification": "Failed"}
