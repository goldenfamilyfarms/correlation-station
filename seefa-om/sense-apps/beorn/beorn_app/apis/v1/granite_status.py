import logging

from flask import request
from flask_restx import Namespace, Resource, fields

import beorn_app
from beorn_app.bll.granite import set_circuit_auto_provisioned
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth
from beorn_app.common.regres_testing import regression_testing_check

api = Namespace("v1/granite_status", description="Operations with granite circuit status")

logger = logging.getLogger(__name__)
not_found = api.model(
    "No records found", {"message": fields.String(example="No records found", description="No records found for cid")}
)


@api.route("")
@api.response(200, "OK")
@api.response(400, "Bad Request")
@api.response(404, "Not Found", not_found)
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented")
@api.response(502, "Bad Gateway")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
class GraniteStatus(Resource):
    """CRUD Operations for Granite Circuit Status"""

    @api.response(200, "Circuit status updated to Auto-Provisioned")
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth", params={"cid": "A cid"})
    def put(self):
        """Update circuit status to Auto-Provisioned"""
        if "cid" not in request.args:
            abort(400, message="Bad request - missing CID")

        cid = request.args["cid"]

        # return response for QA regression testing
        if "STAGE" in beorn_app.app_config.USAGE_DESIGNATION:
            test_response = regression_testing_check(api.path, cid, request="put")
            if test_response != "pass":
                return test_response, 200

        return ("Circuit status updated to Auto-Provisioned", set_circuit_auto_provisioned(cid).status_code)
