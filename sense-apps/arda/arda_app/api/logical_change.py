import logging

from fastapi import Depends

from arda_app.bll.logical_change import logical_change_main
from arda_app.bll.models.payloads import LogicalChangePayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_mac_router

logger = logging.getLogger(__name__)


@v1_design_mac_router.put("/logical_change", summary="Process Logical Change Orders")
def logical_change(payload: LogicalChangePayloadModel, authenticated: bool = Depends(verify_password)):
    """Process Logical Change Orders"""
    logger.info(f"v1/logical_change payload: {payload.model_dump()}")

    return logical_change_main(payload)
