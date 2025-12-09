import logging

from fastapi import Depends
from arda_app.bll.models.payloads import BuildCircuitDesignPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.common.srvc_prod_eligibility_template import SrvcProdEligibilityTemplate
from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.post("/service_product_eligibility", summary="[Build_Circuit_Design] Service Product Eligibility")
def service_product_eligibility(payload: BuildCircuitDesignPayloadModel, authenticated: bool = Depends(verify_password)):
    """Service to determine the eligibility of the chosen service and product to build a circuit"""
    # Check if service type and product name are eligible
    order = SrvcProdEligibilityTemplate(payload.model_dump())
    order.check_service_and_product_eligibility()

    # If eligibility check passes successfully, call SEnSE supported_product endpoint
    return order.call_supported_product_endpoint()
