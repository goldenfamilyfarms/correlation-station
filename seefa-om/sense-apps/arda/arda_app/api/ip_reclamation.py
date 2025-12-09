import logging
from typing import Optional

from fastapi import Depends, Query

from arda_app.bll.models.payloads import IPReclamationPayloadModel
from arda_app.bll.net_new.ip_reclamation import delete_ip_subnet_block_by_cid, get_subnet_block_by_cid
from common_sense.common.errors import abort
from arda_app.common.http_auth import verify_password
from arda_app.dll.ipc import create_subnet_block
from ._routers import v1_tools_router


logger = logging.getLogger(__name__)


@v1_tools_router.post("/ip_reclamation", summary="Return a Reserved IP to IP Control (IPC)")
def ip_reclamation(
    container: Optional[str] = Query(
        None, description="The name of the subnet block's container", examples=["C0555555"]
    ),
    cid: str = Query(
        ..., description="Circuit ID whose IPv4/IPv6 subnet blocks you want from IPC", examples=["51.L1XX.054855..CHTR"]
    ),
    authenticated: bool = Depends(verify_password),
):
    """Reclaim a Subnet Block by deleting it from IP Control (IPC)"""

    return delete_ip_subnet_block_by_cid(cid, container)


@v1_tools_router.get("/ip_reclamation/subnet", summary="Return a Reserved IP to IP Control (IPC)")
def get_subnet_block(
    cid: str = Query(
        ..., description="Circuit ID whose IPv4/IPv6 subnet blocks you want from IPC", examples=["51.L1XX.054855..CHTR"]
    ),
):
    """Retrieve Subnet Block Data from IP Control (IPC)"""
    if cid:
        return get_subnet_block_by_cid(cid)
    else:
        abort(500, "Invalid CID parameter")


@v1_tools_router.post("/ip_reclamation/subnet", summary="Return a Reserved IP to IP Control (IPC)")
def post_subnet_block(payload: IPReclamationPayloadModel, authenticated: bool = Depends(verify_password)):
    """Add a new subnet child block to a specific container in IP Control (IPC)"""
    return create_subnet_block(payload.model_dump())
