import logging

from fastapi import Depends
from arda_app.bll.circuit_design.bandwidth_change.bw_change_main import bandwidth_change_main
from arda_app.bll.models.payloads import BandwidthChangePayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_mac_router

logger = logging.getLogger(__name__)


@v1_design_mac_router.put("/bandwidth_change", summary="Upgrade or Downgrade Bandwidth")
def bandwidth_change(payload: BandwidthChangePayloadModel, authenticated: bool = Depends(verify_password)):
    """Upgrade or Downgrade Bandwidth"""
    logger.info("Initializing Express Bandwidth Upgrade.")
    logger.info(f"v1/bandwidth_change payload: {payload.model_dump()}")

    return bandwidth_change_main(payload)
