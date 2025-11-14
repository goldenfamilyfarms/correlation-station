import logging

from fastapi import Depends

from arda_app.bll.cpe_swap.cpe_swap_main import cpe_swap_main
from arda_app.bll.models.payloads import CpeSwapPayloadModel
from arda_app.common.http_auth import verify_password
from common_sense.common.errors import abort
from arda_app.api._routers import v1_tools_router

logger = logging.getLogger(__name__)


@v1_tools_router.post("/cpe_swap", summary="Performs Shelf Swap of CPE")
def cpe_swap(payload: CpeSwapPayloadModel, authenticated: bool = Depends(verify_password)):
    """Performs Shelf Swap of CPE"""

    logger.info("Initializing CPE Swap")
    logger.info(f"v1/cpe_swap payload: {payload.model_dump()}")

    body = payload.model_dump()
    for k, v in body.items():
        try:
            body.update({k: v.upper()})
        except AttributeError:
            abort(500, f"Payload issue: {v} is not a string for field {k}")

    return cpe_swap_main(body)
