import json
import logging
from flask import request
from flask_restx import Namespace, Resource
from beorn_app.bll.ene import expected_payloads, response_models
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth
from beorn_app.dll.mdso import create_resource

api = Namespace("v1/ENE", description="CRUD operation for ENE automation")
logger = logging.getLogger(__name__)
_response_models = response_models(api)
_expected_models = expected_payloads(api)


@api.route("/automate")
@api.response(400, "Bad Request", _response_models["bad_request"])
@api.response(201, "OK", _response_models["ene_post_ok"])
@api.response(401, "Unauthorized")
class Claim(Resource):
    @api.doc(security="Basic Auth")
    @auth.login_required
    @api.expect(_expected_models["ene_claim_device"])
    def post(self):
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Invalid payload, could not load as json")
        try:
            resource_id = create_resource(payload, product="ENE")
            if resource_id is None:
                abort(400, "problem sending payload to MDSO")
            return {"resource_id": resource_id}
        except Exception:
            abort(400, "problem sending payload to MDSO")
