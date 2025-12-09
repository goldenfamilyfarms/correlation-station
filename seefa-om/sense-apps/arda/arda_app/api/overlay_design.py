import logging
from fastapi import Depends, status

from arda_app.bll.models.payloads import OverlayDesignPayloadModel

from arda_app.common.http_auth import verify_password
from common_sense.common.errors import abort
from arda_app.api._routers import v1_design_router
from arda_app.bll.net_new.create_sbb import create_SBB_shelves, check_for_pillow_speakers

logger = logging.getLogger(__name__)

OVERLAY_DESIGN_WHITELIST = ["SBB 1-19 Outlets", "SBB-Hospitality"]


@v1_design_router.post("/overlay_design", description="Overlay Circuit Design.", status_code=status.HTTP_201_CREATED)
async def overlaydesign(payload: OverlayDesignPayloadModel, authenticated: bool = Depends(verify_password)):
    """Overlay Circuit Design."""
    prod_fam = payload.product_family
    # Determine which direction the payload will be sent
    if prod_fam in OVERLAY_DESIGN_WHITELIST:
        # TODO: Enhance when products become eligible for automated Design
        # Service Codes for Pillow speakers
        check_for_pillow_speakers(payload.model_dump())
        resp = create_SBB_shelves(payload.model_dump())
        return resp
    else:
        abort(500, f"Product Family {prod_fam} is not supported by Automation at this time.")
