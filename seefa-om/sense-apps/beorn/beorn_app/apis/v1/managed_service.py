import json
import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from beorn_app.bll.managed_service import create_managed_service, get_existing_managed_service
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth

api = Namespace("v1/managed_service", description="Create a managed service for orchestration in MDSO")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(400, "Bad Request")
@api.response(404, "Resource Not Found")
@api.response(500, "Internal Server Error")
@api.response(
    501,
    "Not Implemented",
    api.model("not_implemented", {"message": fields.String(example="Use case <> not supported in this release")}),
)
@api.response(
    502, "Bad Gateway", api.model("app_error", {"message": fields.String(example="Unexpected data received from <>")})
)
@api.response(503, "Service Unavailable")
@api.response(
    504,
    "Gateway Timeout",
    api.model("gateway_timeout", {"message": fields.String(example="Timed out requesting data from <>")}),
)
class ManagedService(Resource):
    """Create operation for Managed services."""

    @api.doc(params={"fqdn": "fqdn"})
    @api.response(
        200,
        "Found",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(404, "Not Found")
    def get(self):
        """Get an existing managed service"""
        try:
            fqdn = request.args.get("fqdn")
        except Exception:
            abort(400, f"Corrupt payload: {request.args}")

        existing_resource_id = get_existing_managed_service(fqdn)
        if existing_resource_id:
            return existing_resource_id
        else:
            abort(404, "Resource was not found.")

    @api.response(
        200,
        "Found",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(
        201,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.expect(
        api.model(
            "ms_post_fields",
            {
                "ipAddress": fields.String(example="71.42.150.174", description="IP of device"),
                "vendor": fields.String(example="CISCO", description="Device Vendor"),
                "model": fields.String(example="C1111-8P ISR", description="Device Model"),
                "fqdn": fields.String(
                    example="AUSLTXABM1W.DEV.CHTRSE.COM", description="FQDN Address of TID to be provisioned"
                ),
                "configuration": fields.List(
                    fields.String,
                    example=["command 1", "command 2", "command 3"],
                    description="Device config in the form of a list that will be sent to the device",
                ),
                # 'firmwareVersion': fields.List(fields.String,
                # example='c1100-universalk9_ias.16.09.04.SPA.bin', description=''),
            },
        )
    )
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self):
        """Create a new managed service"""
        try:
            body = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, f"Corrupt payload: {request.data}")

        required_fields = ["ipAddress", "vendor", "model", "fqdn", "configuration"]
        for field in required_fields:
            if field not in body:
                abort(400, f"Missing {field}")

        resource_id = create_managed_service(body)
        return {"resource_id": resource_id}, 201
