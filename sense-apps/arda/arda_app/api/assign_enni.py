import logging

from arda_app.bll.assign.enni import assign_enni_main
from arda_app.bll.models.payloads import AssignEnniPayloadModel
from arda_app.api._routers import v1_design_new_router
from arda_app.common.http_auth import verify_password
from fastapi import Depends

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/assign_enni", summary="[Build_Circuit_Design] Assign ENNI")
def assign_enni(payload: AssignEnniPayloadModel, authenticated: bool = Depends(verify_password)):
    """Perform Assign ENNI and return status"""

    logger.info("Initializing Assign ENNI")
    logger.info(f"v1/assign_enni payload: {payload.model_dump()}")

    return assign_enni_main(payload.model_dump())
