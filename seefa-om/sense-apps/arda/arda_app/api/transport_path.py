import logging

from fastapi import Depends, Request, status
from arda_app.bll.transport_path import (
    get_existing_path_elements,
    get_existing_transports,
    create_transport_path_main,
    lookup_hub_clli,
)
from arda_app.bll.models.payloads import TransportPathPayloadModel
from arda_app.common import app_config
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from opentelemetry.trace import Status, StatusCode
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode
from common_sense.common.errors import abort
from arda_app.api._routers import v3_isp_router

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v3_isp_router.post("/transport_path", summary="Transport Path Services", status_code=status.HTTP_201_CREATED)
def create_transport_path(
    request: Request, payload: TransportPathPayloadModel, authenticated: bool = Depends(verify_password)
):
    """Create Transport Path"""
    payload_dict = payload.model_dump()
    logger.info(f"v3/transport_path payload: {payload_dict}")

    cid = payload.circuit_id
    hub_clli = payload.hub_clli_code
    bandwidth_value = payload.bandwidth_value
    bandwidth_type = payload.bandwidth_type
    build_type = payload.build_type

    with tracer.start_as_current_span("arda.transport_path.create") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("transport_path.operation", "create")
        span.set_attribute("transport_path.hub_clli", hub_clli or "unknown")
        span.set_attribute("transport_path.bandwidth_value", str(bandwidth_value) if bandwidth_value else "unknown")
        span.set_attribute("transport_path.bandwidth_type", bandwidth_type or "unknown")
        span.set_attribute("transport_path.build_type", build_type or "unknown")
        if hasattr(payload, "product_name_order_info") and payload.product_name_order_info:
            span.set_attribute("transport_path.product_family", payload.product_name_order_info)
        
        try:
            missing = {"circuit_id", "hub_clli_code", "bandwidth_value", "bandwidth_type", "build_type"}.difference(
                payload_dict.keys()
            )
            args = request.query_params
            attempt_onboarding = args.get("attempt onboarding", False)
            span.set_attribute("transport_path.attempt_onboarding", attempt_onboarding)

            if len(missing) > 0:
                error_msg = "Required query parameter(s) not specified: {}".format(", ".join(missing))
                span.set_attribute("error.missing_fields", list(missing))
                abort(500, error_msg)
            if not cid:
                abort(500, "invalid circuitID")
            payload.circuit_id = cid.strip()
            if not hub_clli:
                abort(500, "invalid hub_clli_code")
            payload.hub_clli_code = lookup_hub_clli(hub_clli.strip())
            span.set_attribute("transport_path.hub_clli_resolved", payload.hub_clli_code)
            if payload.hub_clli_code == "PLBGNYHK":
                abort(500, f"Unsupported dual legacy company hub: {payload.hub_clli_code}")
            if not bandwidth_value:
                abort(500, "invalid bandwidth_value")
            if not bandwidth_type:
                abort(500, "invalid bandwidth_type")

            """ unsupported_product_families = {'EPL', 'epl', 'EVPL', 'evpl', 'CTBH', 'ctbh'} """
            unsupported_product_families = {"Carrier CTBH - Dark Fiber"}
            if payload.product_name_order_info in unsupported_product_families:
                error_msg = f"Product family {payload.product_name_order_info} not supported in this release"
                error_context = error_categorizer.extract_error_context(error_msg)
                span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                abort(500, error_msg)

            # All carrier orders need to be created witha 10G transport
            if payload.product_name_order_info == "Carrier CTBH":
                payload.bandwidth_value = "10"
                payload.bandwidth_type = "Gbps"
                span.set_attribute("transport_path.bandwidth_override", True)

            # return response for QA regression testing
            if "STAGE" in app_config.USAGE_DESIGNATION:
                test_response = regression_testing_check("/v3/transport_path", cid)
                if test_response != "pass":
                    span.set_attribute("transport_path.test_mode", True)
                    return test_response

            add_span_event("transport_path.existing_check.start", circuit_id=cid)
            existing_path_elements = get_existing_path_elements(cid)
            if existing_path_elements:
                error_msg = f"Circuit path already has transport element: {existing_path_elements[0].get('PATH_NAME')}"
                error_context = error_categorizer.extract_error_context(error_msg)
                span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                abort(500, error_msg)
            else:
                existing_transports = get_existing_transports(payload_dict)
                if not existing_transports:
                    add_span_event("transport_path.creation.start", circuit_id=cid)
                    transport_id = create_transport_path_main(payload_dict, attempt_onboarding)
                    span.set_attribute("transport_path.id", transport_id)
                    span.set_attribute("transport_path.action", "created")
                    add_span_event("transport_path.created", circuit_id=cid, transport_id=transport_id)
                    return {"transport_path": transport_id, "message": "Created new transport path"}
                elif existing_transports.get("transport_status") == "use_existing_transport":
                    transport_id = existing_transports.get("transport_path")
                    span.set_attribute("transport_path.id", transport_id)
                    span.set_attribute("transport_path.action", "use_existing")
                    add_span_event("transport_path.existing_found", circuit_id=cid, transport_id=transport_id)
                    return {"transport_path": transport_id, "message": "Found existing transport"}
                elif existing_transports.get("transport_status") == "Live":
                    error_msg = f"Found Live existing transport path {existing_transports['transport_path']}, please investigate"
                    error_context = error_categorizer.extract_error_context(error_msg)
                    span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                    abort(500, error_msg)
                else:
                    error_msg = (
                        f"Existing transport path {existing_transports['transport_path']} "
                        f"with status {existing_transports['transport_status']} did not match the customer and site"
                    )
                    error_context = error_categorizer.extract_error_context(error_msg)
                    span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                    abort(500, error_msg)
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "TRANSPORT_PATH_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
