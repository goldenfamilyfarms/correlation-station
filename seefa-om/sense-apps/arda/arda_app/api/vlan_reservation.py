import logging

from fastapi import Depends
from fastapi.responses import JSONResponse

from arda_app.bll.models.payloads import VLANReservationPayloadModel
from arda_app.common.utils import path_regex_match
from arda_app.bll.net_new.vlan_reservation.vlan_reservation_main import vlan_reservation_main
from arda_app.common.http_auth import verify_password
from arda_app.data.mock_circuits.mc_vlan_reservation import vr_test_case_responses
from arda_app.api._routers import v1_design_new_router
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/vlan_reservation", summary="[Build Circuit Design] VLAN Reservation")
def vlan_reservation(payload: VLANReservationPayloadModel, authenticated: bool = Depends(verify_password)):
    """[Build Circuit Design] VLAN Reservation"""
    # TEST CASES for regression testing
    vr_test_case_responses(payload.cid)

    logger.info(f"v1/vlan_reservation payload: {payload.model_dump()}")

    # Sanitize NNI string
    if payload.spectrum_buy_nni_circuit_id:
        sanitized_nni_cid = path_regex_match(payload.spectrum_buy_nni_circuit_id, match_type="path_name")
        if sanitized_nni_cid:
            payload.spectrum_buy_nni_circuit_id = sanitized_nni_cid[0]
        else:
            abort(500, f"Unable to parse Buy NNI {payload.spectrum_buy_nni_circuit_id}")

    vlan_reservation_main(payload)

    logger.info("VLAN reservation completed successfully")
    return JSONResponse({"message": "Successful VLAN Reservation"})
