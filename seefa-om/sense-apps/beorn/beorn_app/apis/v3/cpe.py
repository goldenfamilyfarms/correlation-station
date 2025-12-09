import json

from flask import request
from flask_restx import Namespace, Resource, fields

from beorn_app.bll.cpe import activate_cpe, cpe_activation_state
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth

api = Namespace("v3/cpe", description="CRUD operations for a CPE")


@api.route("")
@api.response(400, "Bad Request")
@api.response(404, "Service Not Found")
@api.response(500, "Application Error")
@api.response(502, "Bad Gateway")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
class CPE(Resource):
    """CPE CRUD Endpoints"""

    @api.doc(params={"cid": "CID"})
    @api.response(
        200,
        "Success",
        api.model(
            "circuit details success",
            {
                "cid": fields.String(example="51.L1XX.008486..TWCC"),
                "serviceType": fields.String(example="FIA"),
                "tid": fields.String(example="AUSDTXIR2QW"),
                "portid": fields.String(example="GE-1/0/2"),
                "physicalAddress": fields.String(example="11921 N MOPAC EXPY"),
                "networkServiceState": fields.String(example="READY_FOR_SERVICE"),
                "cpeState": fields.String(example="NOT_STARTED"),
                "cpeActivationStatus": fields.String(example="3. Checking CPE activation eligibility"),
                "cpeActivationError": fields.String(example="CPE is of unexpected model - expecting: RAD"),
                "resourceId": fields.String(example="5cf939bd-728d-4858-a8f7-be36f7afd30a"),
                "customer": fields.String(example="Andromeda"),
            },
        ),
    )
    def get(self):
        """
        Get the CPE Activation State
        """
        if "cid" not in request.args:
            abort(400, message="Bad request - missing CID")
        cid = request.args["cid"]
        return cpe_activation_state(cid), 200

    @api.expect(
        api.model(
            "cpe_post_fields",
            {
                "cid": fields.String(example="51.L1XX.802185..TWCC"),
                "tid": fields.String(example="AUSDTXIR5CW"),
                "port_id": fields.String(example="ge-2/1/4"),
                "ip": fields.String(example="10.10.10.10"),
            },
        )
    )
    @api.response(
        201,
        "Success",
        api.model(
            "CPE_Activate_success",
            {
                "operationId": fields.String(example="5cf939bd-728d-4858-a8f7-be75f5dfd21e"),
                "resourceId": fields.String(example="5cf939bd-728d-4858-a8f7-be36f7afd30a"),
                "uni_port": fields.String(example="3"),
            },
        ),
    )
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self):
        """
        Activate A CPE
        """
        body = json.loads(request.data.decode("utf-8"))
        required_fields = ["cid", "tid", "port_id"]
        for f, k in zip(body, required_fields):
            if f in required_fields and not body[f]:
                abort(400, f"Missing {f} value")
            if k not in body:
                abort(400, f"Missing {k}")
        return activate_cpe(body), 201
