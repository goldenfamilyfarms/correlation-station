import logging

from fastapi import Depends

from arda_app.bll.models.payloads import IPReservationPayloadModel
from arda_app.bll.net_new.ip_reservation.ip_reservation_main import ip_delegation
from arda_app.common.http_auth import verify_password
from arda_app.data.mock_circuits.mc_ip_reservation import ipr_test_case_responses
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from opentelemetry.trace import Status, StatusCode
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v1_design_new_router.post("/ip_reservation", summary="Reserve an IP from IP Control (IPC)")
def ip_reservation_endpoint(payload: IPReservationPayloadModel, authenticated: bool = Depends(verify_password)):
    """Reserve an IP from IP Control (IPC)"""
    logger.info("Initializing IP Reservation")
    payload_dict = payload.model_dump()
    logger.info(f"v1/ip_reservation payload: {payload_dict}")

    cid = payload_dict.get("cid")
    ip_address = payload_dict.get("ip_address")
    subnet = payload_dict.get("subnet")

    with tracer.start_as_current_span("arda.ip_reservation") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("ip.operation", "reservation")
        span.set_attribute("ip.address", ip_address or "unknown")
        span.set_attribute("ip.subnet", subnet or "unknown")
        if "ip_type" in payload_dict:
            span.set_attribute("ip.type", payload_dict["ip_type"])
        
        try:
            # TEST CASES for regression testing
            ipr_test_case_responses(payload)
            span.set_attribute("ip.test_mode", True)

            add_span_event("ip.reservation.start", circuit_id=cid, ip_address=ip_address)
            result = ip_delegation(payload)
            
            # Extract IP reservation result metadata
            if isinstance(result, dict):
                if "ip_address" in result:
                    span.set_attribute("ip.reserved_address", result["ip_address"])
                if "subnet" in result:
                    span.set_attribute("ip.reserved_subnet", result["subnet"])
                if "resource_id" in result:
                    span.set_attribute("mdso.resource_id", result["resource_id"])
            
            add_span_event("ip.reservation.complete", circuit_id=cid, ip_address=result.get("ip_address") if isinstance(result, dict) else None)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "IP_RESERVATION_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
