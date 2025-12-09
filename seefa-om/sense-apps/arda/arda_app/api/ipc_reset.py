import logging

from arda_app.api._routers import v1_tools_router
from arda_app.bll.models.payloads.ipc_reclaim import IPCPayloadModel
from arda_app.bll.smart.ipc_reclaim import ipc_reclaim
from arda_app.common.http_auth import verify_password
from fastapi import Depends

logger = logging.getLogger(__name__)


@v1_tools_router.post("/ipc_reset", summary="Reclaim IP(s) from IP Control (IPC)")
def ipc_reset_endpoint(params: IPCPayloadModel, authenticated: bool = Depends(verify_password)):
    """Reclaim IP(s) from IP Control (IPC)"""
    logger.info("Initializing IPC Reset")
    logger.info(f"v1/ipc_reset: {params.ip}")

    return ipc_reclaim(params)
