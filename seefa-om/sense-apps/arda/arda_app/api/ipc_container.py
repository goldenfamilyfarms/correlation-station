import logging

from common_sense.common.errors import abort
from arda_app.api._routers import v1_tools_router
from arda_app.bll.net_new.ip_reservation.utils.granite_utils import get_circuit_info_and_map_legacy
from arda_app.common.http_auth import verify_password
from fastapi import Query, Depends

logger = logging.getLogger(__name__)


@v1_tools_router.get("/ipc_container", summary="Grabbing IPC container using the CID")
def ipc_container_endpoint(
    cid: str = Query(description="Grabbing IPC container using the CID", examples=["51.L1XX.054855..CHTR"]),
    authenticated: bool = Depends(verify_password),
):
    logger.info("Initializing IPC Container lookup")
    logger.info(f"v1/ipc_container: {cid}")

    resp = get_circuit_info_and_map_legacy(cid, attempt_onboarding=False)

    if isinstance(resp, dict):
        return {"ipam_container": resp["ipc_path"]}
    abort(500, f"No IPC container data found with {cid}")
