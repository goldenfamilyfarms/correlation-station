import logging

from arda_app.bll.remedy.remedy_ticket import RemedyTicket
from arda_app.bll.models.payloads import (
    RemedyTicketPayloadModel,
    RemedyDisconnectTicketPayloadModel,
    RemedyChangeTicketPayloadModel,
)
from arda_app.common import app_config
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from fastapi import Depends, status
from arda_app.api._routers import v2_remedy_router

logger = logging.getLogger(__name__)


@v2_remedy_router.post(
    "/remedy_ticket",
    summary="Create Remedy Workorder (WO)",
    description="Create Remedy Workorder (WO) Ticket",
    status_code=status.HTTP_201_CREATED,
)
def remedy_workorder_ticket(payload: RemedyTicketPayloadModel, authenticated: bool = Depends(verify_password)):
    """Create Remedy Workorder (WO) Ticket"""

    logger.info(f"v2/remedy_ticket payload: {payload.model_dump()}")

    # return response for QA regression testing
    if "STAGE" in app_config.USAGE_DESIGNATION:
        test_response = regression_testing_check("/v2/remedy_ticket", payload.circuit_id)
        if test_response != "pass":
            return test_response

    rt = RemedyTicket(payload.model_dump())
    return rt.create_workorder()


@v2_remedy_router.post(
    "/remedy_ticket/disconnect_ticket",
    summary="Create Remedy Workorder (WO)",
    description="Create Remedy Workorder (WO) Ticket for Customer Disconnect",
    status_code=status.HTTP_201_CREATED,
)
def remedy_disconnect_workorder_ticket(
    payload: RemedyDisconnectTicketPayloadModel, authenticated: bool = Depends(verify_password)
):
    """Create Remedy Workorder (WO) Ticket for Customer Disconnect"""

    logger.info(f"v2/remedy_ticket/disconnect_ticket payload: {payload.model_dump()}")

    rt = RemedyTicket(payload.model_dump())
    return rt.create_disconnect_workorder()


@v2_remedy_router.post(
    "/remedy_ticket/create_crq",
    summary="Create Remedy Change Request (CRQ)",
    description="Create Remedy Change Request (CRQ) Ticket",
    status_code=status.HTTP_201_CREATED,
)
def remedy_crq_ticket(payload: RemedyChangeTicketPayloadModel, authenticated: bool = Depends(verify_password)):
    """Create Remedy Change Request (CRQ) Ticket"""

    logger.info(f"v2/remedy_ticket/create_crq payload: {payload.model_dump()}")

    rt = RemedyTicket({})
    return rt.create_crq_ticket(payload.model_dump())
