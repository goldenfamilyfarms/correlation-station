import logging

from fastapi import Depends

from arda_app.bll.disconnect import disconnect
from arda_app.bll.models.payloads import DisconnectPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_mac_router

logger = logging.getLogger(__name__)


@v1_design_mac_router.post("/disconnect", summary="Circuit Design Disconnect Validation")
def disconnect_endpoint(payload: DisconnectPayloadModel, authenticated: bool = Depends(verify_password)):
    """Validate properties and return back success or a failure"""
    logger.info("Initializing Design Disconnect")
    logger.info(f"v1/disconnect payload: {payload.model_dump()}")
    return disconnect(payload)
