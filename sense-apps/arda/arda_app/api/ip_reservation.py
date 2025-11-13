import logging

from fastapi import Depends

from arda_app.bll.models.payloads import IPReservationPayloadModel
from arda_app.bll.net_new.ip_reservation.ip_reservation_main import ip_delegation
from arda_app.common.http_auth import verify_password
from arda_app.data.mock_circuits.mc_ip_reservation import ipr_test_case_responses
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/ip_reservation", summary="Reserve an IP from IP Control (IPC)")
def ip_reservation_endpoint(payload: IPReservationPayloadModel, authenticated: bool = Depends(verify_password)):
    """Reserve an IP from IP Control (IPC)"""
    logger.info("Initializing IP Reservation")
    logger.info(f"v1/ip_reservation payload: {payload.model_dump()}")

    # TEST CASES for regression testing
    ipr_test_case_responses(payload)

    return ip_delegation(payload)
