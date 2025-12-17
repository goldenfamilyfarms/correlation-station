import logging

from fastapi import Depends
from arda_app.bll.models.payloads import BuildCircuitDesignPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.data.mock_circuits.mc_build_circuit_design import bcd_test_case_response
from arda_app.common.build_circuit_design_template import build_circuit_design_main
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from opentelemetry.trace import Status, StatusCode
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode

from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v1_design_router.post("/build_circuit_design", summary="SEnSE intake service to build a circuit")
def build_circuit_design(payload: BuildCircuitDesignPayloadModel, authenticated: bool = Depends(verify_password)):
    """
    Checks eligibility of service and product ordered and runs Design automation process if successful
    """
    payload_dict = payload.model_dump(exclude_none=True)
    logger.info(f"v1/build_circuit_design payload: {payload_dict}")

    zcid = payload_dict.get("z_side_info", {}).get("cid")
    product_name = payload_dict.get("z_side_info", {}).get("product_name")
    service_type = payload_dict.get("z_side_info", {}).get("service_type")

    with tracer.start_as_current_span("arda.build_circuit_design") as span:
        set_mdso_correlation(
            circuit_id=zcid,
            product_id=product_name,
            service_type=service_type,
        )
        span.set_attribute("design.operation", "build_circuit_design")
        span.set_attribute("design.product_name", product_name or "unknown")
        span.set_attribute("design.service_type", service_type or "unknown")
        
        try:
            # TEST CASES for regression testing
            if payload_dict.get("z_side_info") is not None:
                span.set_attribute("design.test_mode", True)
                bcd_test_case_response(payload_dict)

            add_span_event("design.build.start", circuit_id=zcid)
            result = build_circuit_design_main(payload_dict)
            
            # Extract circ_path_inst_id from result if available
            if isinstance(result, dict) and "circ_path_inst_id" in result:
                span.set_attribute("design.circ_path_inst_id", result["circ_path_inst_id"])
            elif isinstance(result, list) and len(result) > 0:
                first_item = result[0] if isinstance(result[0], dict) else {}
                if "circ_path_inst_id" in first_item:
                    span.set_attribute("design.circ_path_inst_id", first_item["circ_path_inst_id"])
            
            add_span_event("design.build.complete", circuit_id=zcid)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
