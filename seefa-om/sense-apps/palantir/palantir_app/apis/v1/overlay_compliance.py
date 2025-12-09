import logging

from flask import request
from flask_restx import Namespace, Resource, fields
from common_sense.common.errors import abort
from palantir_app.bll.route_overlay import route_compliance, route_compliance_stl

api = Namespace("v1/overlay_compliance", description="Overlay Managed Services Compliance")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(200, "Overlay Compliance Success")
@api.response(400, "Bad Request")
@api.response(404, "Not Found")
@api.response(500, "Application Error")
class OverlayCompliance(Resource):
    overlay_compliance_example = api.model(
        "Overlay Compliance",
        {
            "cid": fields.String(required=False, example="81.L1XX.006522..TWCC"),
            "device_mapping": fields.String(example="false"),
            "order_type": fields.String(required=True, example="New"),
            "product_name": fields.String(required=True, example="Managed Network Edge - Spectrum Provided"),
            "product_family": fields.String(required=True, example="Managed Network WiFi"),
            "eng_id": fields.String(required=True, example="ENG-03573212"),
        },
    )

    @api.expect(api.model("OverlayCompliance", overlay_compliance_example))
    def post(self):
        """
        Starts Overlay Compliance automation
        """

        body = request.json if isinstance(request.json, dict) else {}
        if not body:
            logger.exception("overlay_compliance json payload invalid.")
            abort(400, "Invalid overlay_compliance payload.")

        req_fields = ["eng_id", "order_type", "cid", "order_type", "product_name", "product_family"]
        for field in req_fields:
            if not body.get(field):
                abort(400, f"Missing {field}")

        return route_compliance(body)


@api.route("/stl")
@api.response(200, "Overlay Compliance STL Process Success")
@api.response(400, "Bad Request")
@api.response(404, "Not Found")
@api.response(500, "Application Error")
class OverlayComplianceSTL(Resource):
    overlay_email = api.model(
        "email_info",
        {
            "customer_name": fields.String(required=True, example="CUSTOMER"),
            "customer_poc": fields.String(required=True, example="JOHN DOE"),
            "account_number": fields.String(required=True, example="ACCT-123456"),
            "customer_email": fields.String(required=True, example="john.doe@email.com"),
            "customer_address": fields.String(required=True, example="123 Adresss"),
        },
    )
    overlay_compliance_stl_example = api.model(
        "OverlayComplianceSTL",
        {
            "cid": fields.String(required=True, example="81.L1XX.006522..TWCC"),
            "device_mapping": fields.String(example="false"),
            "order_type": fields.String(example="New"),
            "product_name": fields.String(required=True, example="Managed Network Edge - Spectrum Provided"),
            "product_family": fields.String(required=True, example="Managed Network WiFi"),
            "eng_id": fields.String(required=True, example="ENG-03573212"),
            "email_info": fields.Nested(overlay_email),
        },
    )

    @api.expect(api.model("OverlayComplianceSTL", overlay_compliance_stl_example))
    def post(self):
        """
        Starts Overlay Compliance automation
        """

        body = request.json if isinstance(request.json, dict) else {}
        if not body:
            logger.exception("overlay_compliance json payload invalid.")
            abort(400, "Invalid overlay_compliance payload.")

        req_fields = ["eng_id", "order_type", "cid", "email_info", "product_name", "product_family"]
        for field in req_fields:
            if not body.get(field):
                abort(400, f"Missing {field}")

        return route_compliance_stl(body)
