import logging

from fastapi import Depends, status

from arda_app.bll.models.payloads import QCTransportPayloadModel
from arda_app.bll.transport_path import qc_transport_path_main
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post(
    "/qc_transport_path", summary="Quick Connect Transport Path", status_code=status.HTTP_201_CREATED
)
def qc_transport_path(payload: QCTransportPayloadModel, authenticated: bool = Depends(verify_password)):
    """
    Construct Transport path for a given Circuit and post in Granite
    """
    payload_dict = payload.model_dump()
    logger.info(f"v1/qc_transport_path payload: {payload_dict}")

    return qc_transport_path_main(payload_dict)
