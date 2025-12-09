import logging

from fastapi import Depends, status

from arda_app.bll.net_new.meraki_services import create_meraki_services
from arda_app.bll.models.payloads import MerakiServicesPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.post("/meraki_services", summary="Meraki Services Design", status_code=status.HTTP_201_CREATED)
def meraki_services(payload: MerakiServicesPayloadModel, authenticated: bool = Depends(verify_password)):
    """Meraki Services Design"""

    body = payload.model_dump(by_alias=True)
    create_meraki_services(body)
    return "Meraki Services process Success"
