import logging

from fastapi import Depends, status

from arda_app.bll.assign.vpls import assign_vpls_main
from arda_app.bll.models.payloads import ElanAddVplsPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_new_router


logger = logging.getLogger(__name__)


@v1_design_new_router.post(
    "/elan_add_vpls", summary="[Build_Circuit_Design] Assign VPLS", status_code=status.HTTP_201_CREATED
)
def elan_add_vpls(payload: ElanAddVplsPayloadModel, authenticated: bool = Depends(verify_password)):
    """Perform Assign VPLS and return status."""
    logger.info("Initializing Assign VPLS")
    body = payload.model_dump()

    return assign_vpls_main(body)
