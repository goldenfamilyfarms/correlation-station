import logging

from arda_app.bll.all_products import get_original_transport_path, update_related_circuits
from arda_app.bll.models.payloads import ISPUpdateRelatedCircuitsPayloadModel
from arda_app.common import app_config
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from fastapi import Depends, Request, status

from arda_app.api._routers import v1_isp_router

logger = logging.getLogger(__name__)


@v1_isp_router.put(
    "/isp_update_related_circuits", summary="Assigns Transport Path to List of CIDs", status_code=status.HTTP_201_CREATED
)
def isp_update_related_circuits(
    request: Request, payload: ISPUpdateRelatedCircuitsPayloadModel, authenticated: bool = Depends(verify_password)
):
    """Assign Transports to a List of Circuit IDs"""
    body = payload.model_dump()
    logger.info(f"v1/isp_update_related_circuits payload: {body}")

    # return response for QA regression testing
    if "STAGE" in app_config.USAGE_DESIGNATION:
        circuit_id = body["related_circuit_ids"][0]["circuit_id"]
        url_path = request.url.path
        test_response = regression_testing_check(url_path, circuit_id)
        if test_response != "pass":
            return test_response

    transport_path = body.get("transport_path", None)
    main_circuit_id = body.get("main_circuit_id", None)

    if main_circuit_id is None and transport_path is not None:
        cid_statuses = update_related_circuits(
            body["related_circuit_ids"], transport_path, body.get("service_location_address")
        )
        return {"relatedCircuitStatus": cid_statuses}
    elif main_circuit_id is not None:
        circuit_id = body["related_circuit_ids"][0].get("circuit_id")
        transport_path = get_original_transport_path(circuit_id)
        circuit_id_list = []
        circuit_id_list.append(main_circuit_id)
        cid_statuses = update_related_circuits(circuit_id_list, transport_path, body.get("service_location_address"))
        return {"relatedCircuitStatus": cid_statuses}
