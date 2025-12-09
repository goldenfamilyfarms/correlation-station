import logging

from fastapi import Depends

from arda_app.api._routers import v1_design_new_router
from arda_app.bll.models.payloads.type_2_hub_work import Type2HubWorkPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.bll.type_2_hub_work import type_2_hub_work_main


logger = logging.getLogger(__name__)


@v1_design_new_router.put("/type_2_hub_work", summary="Type II Buy NNI and Transport")
def type_ii_hub_work(payload: Type2HubWorkPayloadModel, authenticated: bool = Depends(verify_password)):
    """Find and Add Buy NNI and Hub Transport paths"""
    logger.info("Initializing Type II hub work")
    logger.info(f"v1/type_2_hub_work payload: {payload.model_dump()}")

    return type_2_hub_work_main(payload.model_dump())
