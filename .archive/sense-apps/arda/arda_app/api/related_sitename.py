import logging


from arda_app.bll.models.payloads import RelatedSiteNamePayloadModel
from arda_app.bll.cid.site import rel_site_name_main
from arda_app.api._routers import v1_cid_router
from arda_app.common.http_auth import verify_password
from fastapi import Depends


logger = logging.getLogger(__name__)


@v1_cid_router.post("/related_sitename", summary="Get granite site name")
def related_sitename(payload: RelatedSiteNamePayloadModel, authenticated: bool = Depends(verify_password)):
    """Get granite site name"""

    payload = payload.model_dump()

    logger.info(f"v1/related_sitename payload: {payload}")

    return rel_site_name_main(payload)
