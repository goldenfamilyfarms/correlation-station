import logging
import traceback

from fastapi import Depends
from fastapi.responses import JSONResponse

from arda_app.bll.models.payloads import BuildCircuitDesignPayloadModel
from arda_app.common.http_auth import verify_password
from arda_app.common.supported_prod_template import SupportedProdTemplate
from common_sense.common.errors import abort
from arda_app.api._routers import v1_design_router

logger = logging.getLogger(__name__)


@v1_design_router.post("/supported_product", summary="[Build_Circuit_Design] Supported Product")
def supported_product(payload: BuildCircuitDesignPayloadModel, authenticated: bool = Depends(verify_password)):
    """Starts processing of valid orders to build a circuit"""
    # Invoke class methods in sequence to work on Circuit Design order
    order = SupportedProdTemplate(payload.model_dump(exclude_none=True))
    # return order.product_uniqueness_identifier()
    try:
        return order.product_uniqueness_identifier()
    except Exception as e:
        response_data = traceback.format_exc()
        logger.debug(f"response_data - {response_data}")
        last_index = response_data.rfind("ARDA -")
        if last_index != -1:
            second_to_last_index = response_data.rfind("ARDA -", 0, last_index)
            if second_to_last_index != -1:
                logger.debug(
                    f"response_data[second_to_last_index:] - {response_data[second_to_last_index:]}and e.code - {e.code}"
                )
                return JSONResponse({"message": response_data[second_to_last_index:]}, e.code)
            else:
                logger.debug(f"response_data[last_index:] - {response_data[last_index:]} and e.code - {e.code}")
                return JSONResponse({"message": response_data[last_index:]}, e.code)
        else:
            abort(e.code, e.data)
