import logging

from fastapi import Depends, status
from arda_app.bll.models.payloads import AssignHandoffsAndUplinksPayloadModel
from arda_app.bll.net_new.assign_uplinks_and_handoffs import assign_uplinks_and_handoffs_main
from arda_app.common.http_auth import verify_password

from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post(
    "/assign_handoffs_and_uplinks",
    summary="[Build_Circuit_Design] Assign handoffs and uplinks",
    status_code=status.HTTP_201_CREATED,
)
def assign_uplinks_and_handoffs(
    payload: AssignHandoffsAndUplinksPayloadModel, authenticated: bool = Depends(verify_password)
):
    """Assign handoffs and uplinks"""

    logger.info("Initializing Assign handoffs and uplinks")
    logger.info(f"v1/assign_handoffs_and_uplinks payload: {payload.model_dump()}")

    return assign_uplinks_and_handoffs_main(payload.model_dump())
