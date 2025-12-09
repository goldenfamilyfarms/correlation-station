import logging

from arda_app.bll.models.payloads import PickSovaWoPayloadModel
from arda_app.bll.nova_to_sova import wo_main
from arda_app.api._routers import v1_isp_router
from arda_app.common.http_auth import verify_password
from fastapi import Depends

logger = logging.getLogger(__name__)


@v1_isp_router.post("/pick_sova_wo", summary="Find Remedy Workorder")
def pick_sova_wo(payload: PickSovaWoPayloadModel, authenticated: bool = Depends(verify_password)):
    """Picking remedy work order"""
    return wo_main(payload.model_dump())
