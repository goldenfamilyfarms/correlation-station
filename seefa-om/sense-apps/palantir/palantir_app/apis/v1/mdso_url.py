import logging
from flask_restx import Namespace, Resource
from common_sense.common.errors import abort
from palantir_app.dll.mdso import _env_check

api = Namespace("v1/mdso_url", description="Returns MDSO Production URL")
logger = logging.getLogger(__name__)


@api.route("")
@api.response(200, "OK")
@api.response(400, "Bad Request")
@api.response(404, "Not Found")
@api.response(500, "Application Error")
class MDSOSwivelUrl(Resource):
    def get(self):
        """
        Returns the active production URL for MDSO
        """
        try:
            # Use the _env_check method with production=True and need_auth=False
            url = _env_check(production=True, need_auth=False)
            return {"mdso_prod_url": url}, 200
        except Exception as e:
            logger.error(f"Error retrieving MDSO production URL: {str(e)}")
            abort(500, "Unable to retrieve MDSO production URL")
