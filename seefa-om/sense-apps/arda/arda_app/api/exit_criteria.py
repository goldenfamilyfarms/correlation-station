import logging

from fastapi import Depends

from arda_app.bll.circuit_design.exit_criteria import create_base_exit_criteria, create_exit_criteria
from arda_app.bll.models.payloads import ExitCriteriaPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.put("/exit_criteria", summary="EXPO Exit Criteria")
def exit_criteria(payload: ExitCriteriaPayloadModel, authenticated: bool = Depends(verify_password)):
    """Generate Exit Criteria response for EXPO"""
    logger.info("Initializing Exit Criteria")
    logger.info(f"v1/exit_criteria payload: {payload.model_dump()}")

    exit_data = create_base_exit_criteria(payload.model_dump())

    return create_exit_criteria(payload.model_dump(), exit_data)
