import logging

from fastapi import Depends, status
from arda_app.bll.models.payloads import CreateMTUTransportPayloadModel
from arda_app.bll.net_new.create_mtu_transport import create_mtu_new_build_transport_main
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_new_router


logger = logging.getLogger(__name__)


@v1_design_new_router.post(
    "/create_mtu_transport", summary="Create MTU new build transport", status_code=status.HTTP_201_CREATED
)
def create_mtu_transport(payload: CreateMTUTransportPayloadModel, authenticated: bool = Depends(verify_password)):
    """Create MTU new build transport"""

    logger.info("Initializing Create MTU transport")
    logger.info(f"v1/create_mtu_transport payload: {payload.model_dump()}")

    return create_mtu_new_build_transport_main(payload.model_dump())
