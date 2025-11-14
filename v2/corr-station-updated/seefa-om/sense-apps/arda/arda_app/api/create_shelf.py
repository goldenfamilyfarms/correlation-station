import logging

from fastapi import Depends, status

from arda_app.bll.models.payloads import CreateShelfPayloadModel
from arda_app.bll.net_new.create_shelf import create_shelf_main
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/create_shelf", summary="Create device shelf", status_code=status.HTTP_201_CREATED)
def create_shelf(payload: CreateShelfPayloadModel, authenticated: bool = Depends(verify_password)):
    """Create device shelf"""
    logger.info(f"v1/create_shelf payload: {payload.model_dump()}")

    return create_shelf_main(payload.model_dump())
