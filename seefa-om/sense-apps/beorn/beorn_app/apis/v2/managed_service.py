import json
import logging
from flask import request
from flask_restx import Namespace, Resource, fields
from beorn_app.bll.mne import validate_net_name
from common_sense.common.errors import abort
from beorn_app.dll.mdso import get_existing_resource_by_query, create_resource
from beorn_app.common.http_auth import auth

api = Namespace("v2/managed_service", description="Create a managed service for orchestration in MDSO")
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

    @api.doc(params={"label": "label"})
    @api.response(
        200,
        "Found",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(404, "Not Found")
    def get(self):
        """Get an existing managed service"""
        try:
            label = request.args.get("label")
        except Exception:
            abort(400, f"Corrupt payload: {request.args}")

        existing_resource_id = get_existing_resource_by_query(
            resource_type="charter.resourceTypes.merakiServices", q_param="label", q_value=label
        )
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
            "ms_post_fields_v2",
            {
                "label": fields.String(example="MNE_CID"),
                "service_type": fields.String(example="MNE"),
                "properties": fields.Nested(
                    api.model(
                        "properties",
                        {
                            "customerName": fields.String(example="CUSTOMER_NAME"),
                            "licenseType": fields.String(example="MX250-SEC"),
                            "circuitId": fields.String(example="CID"),
                            "address": fields.String(example="11921 N MoPac Expy, Austin, TX, 78759"),
                            "productTypes": fields.String(example="appliance"),
                            "accountNumbers": fields.String(example="ACCT-123456789"),
                            "timeZone": fields.String(example="TX"),
                            "clli": fields.String(example="HSTNTXMOCG0"),
                        },
                    )
                ),
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

        required_fields = ["label", "properties"]
        for field in required_fields:
            if field not in body:
                abort(400, f"Missing {field}")

        # check that the net name does not have invalid characters
        if not validate_net_name(body["properties"]["networkName"]):
            abort(400, "invalid network name, can only contain characters A-Z a-z 0-9 and .@#_-")

        if isinstance(body["properties"]["accountNumbers"], int):
            body["resource_properties"]["accountNumbers"] = f"ACCT-{body['resource_properties']['accountNumbers']}"

        resource_id = create_resource(body, product="merakiServices")
        return {"resource_id": resource_id}, 201
