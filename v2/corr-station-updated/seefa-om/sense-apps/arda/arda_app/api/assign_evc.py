import logging

from arda_app.bll.assign.evc import assign_evc_main
from arda_app.bll.models.payloads import AssignEvcPayloadModel
from arda_app.api._routers import v1_design_new_router
from arda_app.common.http_auth import verify_password
from fastapi import Depends

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/assign_evc", summary="[Build_Circuit_Design] Assign EVC")
def assign_evc(payload: AssignEvcPayloadModel, authenticated: bool = Depends(verify_password)):
    """Perform Assign EVC and return status"""

    logger.info("Initializing Assign EVC")
    logger.info(f"v1/assign_evc payload: {payload.model_dump()}")

    return assign_evc_main(payload.model_dump())
