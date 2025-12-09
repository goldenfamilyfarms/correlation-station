import logging

from fastapi import Depends, status

from arda_app.bll.models.payloads import ServiceableShelfPayloadModel
from arda_app.bll.serviceable_shelf import serviceable_shelf_main
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post(
    "/serviceable_shelf", summary="Existing CPE Handoff Port", status_code=status.HTTP_201_CREATED
)
def serviceable_shelf(payload: ServiceableShelfPayloadModel, authenticated: bool = Depends(verify_password)):
    """Serviceable shelf - select the available handoff from CPE"""
    payload = payload.model_dump()
    logger.info(f"v1/serviceable_shelf payload: {payload}")

    return serviceable_shelf_main(payload)
