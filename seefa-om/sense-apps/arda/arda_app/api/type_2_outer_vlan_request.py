import logging

from fastapi import Depends
from fastapi.responses import JSONResponse

from arda_app.bll.models.payloads.vlan_reservation import Type2OuterVLANRequestPayloadModel
from arda_app.bll.net_new.vlan_reservation.vlan_reservation_main import type_2_outer_vlan_request
from arda_app.common.http_auth import verify_password

# from common_sense.common.errors import abort
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/type_2_outer_vlan_request", summary="[Build Circuit Design] Type II Outer VLAN Request")
def vlan_request(payload: Type2OuterVLANRequestPayloadModel, authenticated: bool = Depends(verify_password)):
    """[Build Circuit Design] Type II Outer VLAN Request"""

    logger.info(f"v1/type_2_outer_vlan_request payload: {payload.model_dump()}")
    resp = type_2_outer_vlan_request(payload)

    logger.info("Type II Outer VLAN request completed successfully")
    return JSONResponse(resp)
