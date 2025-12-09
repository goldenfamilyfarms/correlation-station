import logging

from fastapi import Depends
from arda_app.common.utils import validate_required_parameters
from arda_app.bll.cid.customer import find_or_create_a_customer_v3, cid_entrance_criteria
from arda_app.bll.models.payloads import CustomerPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v4_cid_router

logger = logging.getLogger(__name__)

required_customer_values = ["name", "type", "country", "sf_id"]


@v4_cid_router.put("/customer", summary="Find or Create a Customer")
def customer(payload: CustomerPayloadModel, authenticated: bool = Depends(verify_password)):
    """Find existing customer or create a new customer"""
    logger.info(f"v4/customer payload: {payload.model_dump()}")

    cid_entrance_criteria(payload.model_dump())

    validate_required_parameters(required_customer_values, payload.model_dump())
    return find_or_create_a_customer_v3(payload.model_dump())
