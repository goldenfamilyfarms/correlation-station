import logging

from fastapi import Depends

from arda_app.bll.cid.site import find_or_create_a_site_v5
from arda_app.bll.models.payloads import SitePayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v5_cid_router

logger = logging.getLogger(__name__)


@v5_cid_router.put("/site", summary="Find or Create a Site")
def site(payload: SitePayloadModel, authenticated: bool = Depends(verify_password)):
    """Find existing site or create a new site"""
    site_payload = payload.model_dump()

    logger.info(f"v5/site payload: {site_payload}")

    response = find_or_create_a_site_v5(site_payload)

    return response
