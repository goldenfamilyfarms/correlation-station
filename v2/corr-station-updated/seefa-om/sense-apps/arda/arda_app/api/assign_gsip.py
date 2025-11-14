import logging

from fastapi import Depends, status

from arda_app.bll.assign.gsip import assign_gsip_main
from arda_app.bll.models.payloads import AssignGsipPayloadModel
from arda_app.common.http_auth import verify_password

from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post(
    "/assign_gsip", summary="[Build_Circuit_Design] Assign GSIP", status_code=status.HTTP_201_CREATED
)
def assigngsip(payload: AssignGsipPayloadModel, authenticated: bool = Depends(verify_password)):
    """Perform Assign GSIP and return status."""
    logger.info("Initializing Assign GSIP")
    logger.info(f"v1/assign_gsip payload: {payload.model_dump()}")

    return assign_gsip_main(payload.model_dump())
