import logging

from fastapi import Depends

from arda_app.bll.disconnect import disconnect
from arda_app.bll.models.payloads import DisconnectPayloadModel
from arda_app.common.http_auth import verify_password
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from opentelemetry.trace import Status, StatusCode
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode
from arda_app.api._routers import v1_design_mac_router

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v1_design_mac_router.post("/disconnect", summary="Circuit Design Disconnect Validation")
def disconnect_endpoint(payload: DisconnectPayloadModel, authenticated: bool = Depends(verify_password)):
    """Validate properties and return back success or a failure"""
    logger.info("Initializing Design Disconnect")
    payload_dict = payload.model_dump()
    logger.info(f"v1/disconnect payload: {payload_dict}")
    
    cid = payload_dict.get("cid")
    product_name = payload_dict.get("product_name")
    product_family = payload_dict.get("product_family")
    
    with tracer.start_as_current_span("arda.disconnect") as span:
        set_mdso_correlation(
            circuit_id=cid,
            product_id=product_name,
            service_type="disconnect",
        )
        span.set_attribute("design.operation", "disconnect")
        span.set_attribute("design.product_name", product_name or "unknown")
        span.set_attribute("design.product_family", product_family or "unknown")
        
        try:
            add_span_event("disconnect.start", circuit_id=cid)
            result = disconnect(payload)
            
            # Extract relevant information from result
            if isinstance(result, dict):
                if "circ_path_inst_id" in result:
                    span.set_attribute("design.circ_path_inst_id", result["circ_path_inst_id"])
                if "engineering_job_type" in result:
                    span.set_attribute("design.engineering_job_type", result["engineering_job_type"])
                if "blacklist" in result:
                    span.set_attribute("disconnect.blacklist", result["blacklist"])
                if "hub_work_required" in result:
                    span.set_attribute("disconnect.hub_work_required", result["hub_work_required"])
            
            add_span_event("disconnect.complete", circuit_id=cid)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
