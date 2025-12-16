import logging

from fastapi import Depends
from fastapi.responses import JSONResponse

from arda_app.bll.models.payloads import VLANReservationPayloadModel
from arda_app.common.utils import path_regex_match
from arda_app.bll.net_new.vlan_reservation.vlan_reservation_main import vlan_reservation_main
from arda_app.common.http_auth import verify_password
from arda_app.data.mock_circuits.mc_vlan_reservation import vr_test_case_responses
from arda_app.common.otel import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from arda_app.common.otel.mdso_patterns import ErrorCategorizer
from arda_app.api._routers import v1_design_new_router
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v1_design_new_router.post("/vlan_reservation", summary="[Build Circuit Design] VLAN Reservation")
def vlan_reservation(payload: VLANReservationPayloadModel, authenticated: bool = Depends(verify_password)):
    """[Build Circuit Design] VLAN Reservation"""
    payload_dict = payload.model_dump()
    cid = payload.cid
    
    with tracer.start_as_current_span("arda.vlan_reservation") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("vlan.operation", "reservation")
        if hasattr(payload, "spectrum_buy_nni_circuit_id") and payload.spectrum_buy_nni_circuit_id:
            span.set_attribute("vlan.buy_nni_cid", payload.spectrum_buy_nni_circuit_id)
        
        try:
            # TEST CASES for regression testing
            vr_test_case_responses(cid)
            span.set_attribute("vlan.test_mode", True)

            logger.info(f"v1/vlan_reservation payload: {payload_dict}")

            # Sanitize NNI string
            if payload.spectrum_buy_nni_circuit_id:
                add_span_event("vlan.nni_sanitization.start", circuit_id=cid)
                sanitized_nni_cid = path_regex_match(payload.spectrum_buy_nni_circuit_id, match_type="path_name")
                if sanitized_nni_cid:
                    payload.spectrum_buy_nni_circuit_id = sanitized_nni_cid[0]
                    span.set_attribute("vlan.buy_nni_cid_sanitized", sanitized_nni_cid[0])
                    add_span_event("vlan.nni_sanitization.complete", circuit_id=cid)
                else:
                    error_msg = f"Unable to parse Buy NNI {payload.spectrum_buy_nni_circuit_id}"
                    error_context = error_categorizer.extract_error_context(error_msg)
                    span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                    abort(500, error_msg)

            add_span_event("vlan.reservation.start", circuit_id=cid)
            vlan_reservation_main(payload)
            add_span_event("vlan.reservation.complete", circuit_id=cid)

            logger.info("VLAN reservation completed successfully")
            return JSONResponse({"message": "Successful VLAN Reservation"})
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "VLAN_RESERVATION_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
