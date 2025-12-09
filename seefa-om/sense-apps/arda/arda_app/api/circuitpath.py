import logging

from fastapi import Depends, status

from arda_app.bll.cid.pathid import (
    create_path_v4,
    create_sister_path,
    create_sub_paths,
    generate_cid_v3,
    get_suffix,
    product_service_validation_v2,
    unitless_bandwidths,
)
from arda_app.bll.net_new.assign_parent_paths import _add_parent_network_element
from arda_app.common.http_auth import verify_password
from arda_app.common.npa_operations import get_npa_and_site_type_with_site
from arda_app.common.utils import validate_required_parameters
from arda_app.bll.models.payloads import CircuitPathPayloadModel
from common_sense.common.errors import abort
from arda_app.api._routers import v4_cid_router

logger = logging.getLogger(__name__)

required_path_values = ["bw_value", "path_order_num", "customer_type", "product_service", "z_side_site", "service_media"]


@v4_cid_router.post("/circuitpath", summary="Create a path", status_code=status.HTTP_201_CREATED)
def circuit_path(payload: CircuitPathPayloadModel, authenticated: bool = Depends(verify_password)):
    """Create a path"""

    logger.info(f"v4/circuitpath payload: {payload.model_dump()}")

    validate_required_parameters(required_path_values, payload.model_dump())

    body = unitless_bandwidths(payload.model_dump())

    try:
        npa, site_type = get_npa_and_site_type_with_site(body["z_side_site"]["site"])
    except KeyError:
        logger.error("Z side site is missing the site name in payload")
        abort(500, "Z side site is missing the site name in payload")

    body["site_type"] = site_type
    service_type = body["product_service"]

    new_cid = generate_cid_v3(body, npa, service_type)
    product_service_validation_v2(body)
    suffix = get_suffix(service_type)

    if suffix:
        path = create_path_v4(new_cid, body, suffix)
    else:
        path = create_path_v4(new_cid, body)

    if "OL-UC" in body["path_order_num"]:
        path_inst_id = path["instId"]

        apne_params = {
            "LEG_NAME": "1",
            "PATH_NAME": path["pathId"],
            "PATH_INST_ID": path_inst_id,
            "ADD_ELEMENT": "true",
            "PATH_ELEM_SEQUENCE": "1",
            "PATH_ELEMENT_TYPE": "CLOUD",
            "CLOUD_INST_ID": "1003",
        }
        _add_parent_network_element(apne_params)

    if service_type == "CUS-VOICE-PRI":
        sub_paths = create_sub_paths(body, path["pathId"])
        return {"path": path["pathId"], "circuit_inst_id": path["instId"], "relatedCircuitId": sub_paths}
    elif service_type == "CAR-E-ACCESS FIBER/DOCSIS EPL":
        sister_path = create_sister_path(new_cid, body)

        return {
            "path": path["pathId"],
            "circuit_inst_id": path["instId"],
            "relatedCircuitId": {"path": sister_path["pathId"]},
        }

    return {"path": path["pathId"], "circuit_inst_id": path["instId"]}
