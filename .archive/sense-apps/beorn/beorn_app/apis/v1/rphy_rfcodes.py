import logging

from flask import request
from flask_restx import Namespace, Resource

from common_sense.common.errors import abort
from beorn_app.dll.sales_force import get_codes

logger = logging.getLogger(__name__)
api = Namespace("v1/rphy", description="Extract RF codes")


@api.route("/rf_codes")
@api.response(200, "OK")
@api.response(404, "Not Found")
@api.response(400, "Bad Request")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented")
@api.response(502, "Bad Gateway")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
@api.doc(params={"eng_id": "An engineering ID", "prefix": "Prefix of Service Codes"})
class RFcodes(Resource):
    def get(self):
        if not request.args.get("eng_id"):
            abort(404, "Provide Engineering ID to Retrieve RF Codes")

        return get_codes(request.args.get("eng_id"), request.args.get("prefix", "RF"))
