import json
import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from beorn_app.bll.managed_rphy import expected_payloads, response_models, validate_rphy_payload

from common_sense.common.errors import abort
from beorn_app.dll.mdso import create_service, get_existing_resource_by_query, product_query


logger = logging.getLogger(__name__)
api = Namespace("v1/rphy", description="Extract Product ID")
_response_models = response_models(api)
_expected_models = expected_payloads(api)


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
class ManagedRPHY(Resource):
    @api.doc(params={"cid": "Circuit-Path ID"})
    @api.doc(params={"cid": "cid"})
    @api.response(
        200,
        "Found",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(404, "Not Found")
    def get(self):
        """Get Resource ID"""
        if not request.args.get("cid"):
            abort(400, "Please provide a cid")
        cid = request.args.get("cid")
        resource_type = "charter.resourceTypes.ManagedRPHY"
        query_property = "label"
        existing_resource_id = get_existing_resource_by_query(resource_type, query_property, cid)
        if not existing_resource_id or not existing_resource_id.get("id"):
            return f"Resource ID for {cid} not found", 404

        return existing_resource_id.get("id")

    @api.response(200, "OK", _response_models["rphy_get_ok"])
    @api.response(201, "Created", _response_models["created"])
    @api.response(400, "Bad Request", _response_models["bad_request"])
    @api.response(404, "Not Found", _response_models["bad_request"])
    @api.response(500, "Internal Server Error", _response_models["server_error"])
    @api.response(501, "Not Implemented", _response_models["server_error"])
    @api.response(502, "Bad Gateway", _response_models["server_error"])
    @api.response(503, "Service Unavailable", _response_models["server_error"])
    @api.response(504, "Gateway Timeout", _response_models["server_error"])
    @api.doc(security="Basic Auth")
    @api.expect(_expected_models["rphy"])
    def post(self):
        """Create new RPHY service"""
        # convert given payload to json
        try:
            rphy_payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Invalid payload, could not load as json")

        # check required fields are in payload
        missing_fields = validate_rphy_payload(rphy_payload)
        if len(missing_fields) > 0:
            abort(400, "Invalid Payload - Missing Required Field(s): {}".format(", ".join(missing_fields)))

        # begin provisioning
        rphy_payload["productId"] = product_query("ManagedRPHY")
        rphy_payload["label"] = rphy_payload["properties"]["cid"]
        logger.info(f"Rphy Payload: {rphy_payload}")
        try:
            resource_id = create_service(rphy_payload)
        except Exception:
            abort(400, "Unable to Get RPHY Resource ID")

        return {"resource_id": resource_id}, 201


@api.route("/rphy_firmware_upgrade")
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
class RphyFirmwareUpgrade(Resource):
    @api.doc(params={"cid": "Circuit-Path ID"})
    @api.doc(params={"cid": "cid"})
    @api.response(
        200,
        "Found",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(404, "Not Found")
    def get(self):
        """Get Resource ID"""
        if not request.args.get("cid"):
            abort(400, "Please provide a cid")

        cid = request.args.get("cid")

        resource_type = "charter.resourceTypes.RPHYFWupgrade"
        query_property = "label"

        existing_resource_id = get_existing_resource_by_query(resource_type, query_property, cid)["id"]

        return existing_resource_id

    @api.response(200, "OK", _response_models["rphy_get_ok"])
    @api.response(201, "Created", _response_models["created"])
    @api.response(400, "Bad Request", _response_models["bad_request"])
    @api.response(404, "Not Found", _response_models["bad_request"])
    @api.response(500, "Internal Server Error", _response_models["server_error"])
    @api.response(501, "Not Implemented", _response_models["server_error"])
    @api.response(502, "Bad Gateway", _response_models["server_error"])
    @api.response(503, "Service Unavailable", _response_models["server_error"])
    @api.response(504, "Gateway Timeout", _response_models["server_error"])
    @api.doc(security="Basic Auth")
    @api.expect(
        api.model(
            "rphy_firmware_upgrade",
            {
                "cid": fields.String(required=True, example="81.L1XX.006522..TWCC"),
                "rpd": fields.String(required=True, example="16:0"),
                "vendor": fields.String(required=True, example="harmonic"),
                "cmtsipAddress": fields.String(required=True, example="170.151.0.68"),
            },
        )
    )
    def post(self):
        """Create new RPHY Firmware Upgrade"""
        # convert given payload to json
        try:
            fw_payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Invalid payload, could not load as json")
        # Begin RPHY FW upgrade process
        fw_payload["vendor"] = fw_payload["vendor"].lower()
        rphy_fw_payload = {
            "label": fw_payload.get("cid"),
            "properties": fw_payload,
            "productId": product_query("RPHYFWupgrade"),
        }
        logger.info(f"Rphy firmware Payload: {rphy_fw_payload}")
        try:
            resource_id = create_service(rphy_fw_payload)
        except Exception as e:
            abort(400, f"Unable to Get RPHY Resource ID: {e}")

        return {"resource_id": resource_id}, 201
