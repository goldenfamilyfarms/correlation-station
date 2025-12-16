import logging

from fastapi import Depends
from arda_app.bll.circuit_design.bandwidth_change.bw_change_main import bandwidth_change_main
from arda_app.bll.models.payloads import BandwidthChangePayloadModel
from arda_app.common.http_auth import verify_password
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from opentelemetry.trace import Status, StatusCode
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode
from arda_app.api._routers import v1_design_mac_router

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v1_design_mac_router.put("/bandwidth_change", summary="Upgrade or Downgrade Bandwidth")
def bandwidth_change(payload: BandwidthChangePayloadModel, authenticated: bool = Depends(verify_password)):
    """Upgrade or Downgrade Bandwidth"""
    payload_dict = payload.model_dump()
    cid = payload_dict.get("cid")
    
    logger.info("Initializing Express Bandwidth Upgrade.")
    logger.info(f"v1/bandwidth_change payload: {payload_dict}")

    with tracer.start_as_current_span("arda.bandwidth_change") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("bandwidth_change.operation", "change")
        if "bandwidth_value" in payload_dict:
            span.set_attribute("bandwidth_change.value", str(payload_dict["bandwidth_value"]))
        if "bandwidth_type" in payload_dict:
            span.set_attribute("bandwidth_change.type", payload_dict["bandwidth_type"])
        if "change_type" in payload_dict:
            span.set_attribute("bandwidth_change.change_type", payload_dict["change_type"])
        
        try:
            add_span_event("bandwidth_change.start", circuit_id=cid)
            result = bandwidth_change_main(payload)
            
            # Extract result metadata
            if isinstance(result, dict):
                if "resource_id" in result:
                    span.set_attribute("mdso.resource_id", result["resource_id"])
            
            add_span_event("bandwidth_change.complete", circuit_id=cid)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "BANDWIDTH_CHANGE_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
