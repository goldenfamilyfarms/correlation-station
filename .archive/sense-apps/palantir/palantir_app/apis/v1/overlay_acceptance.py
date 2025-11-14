import logging

from flask import request
from flask_restx import Namespace, Resource, fields
from common_sense.common.errors import abort
from palantir_app.bll.route_overlay import route_acceptance


api = Namespace("v1/overlay_acceptance", description="Overlay Managed Services Acceptance")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(200, "Overlay Compliance Success")
@api.response(400, "Bad Request")
@api.response(404, "Not Found")
@api.response(500, "Application Error")
class OverlayAcceptance(Resource):
    overlay_acceptance_example = api.model(
        "Overlay Acceptance",
        {
            "cid": fields.String(required=False, example="81.L1XX.006522..TWCC"),
            "device_mapping": fields.String(example="false"),
            "order_type": fields.String(required=True, example="New"),
            "product_name": fields.String(required=True, example="Managed Network Edge - Spectrum Provided"),
            "product_family": fields.String(required=True, example="Managed Network WiFi"),
            "eng_id": fields.String(required=True, example="ENG-03573212"),
        },
    )

    @api.expect(api.model("OverlayAcceptance", overlay_acceptance_example))
    def post(self):
        """
        Starts Overlay Acceptance automation
        """

        body = request.json if isinstance(request.json, dict) else {}
        if not body:
            logger.exception("overlay_acceptance json payload invalid.")
            abort(400, "Invalid overlay_acceptance payload.")

        req_fields = ["eng_id", "order_type", "cid", "product_name", "product_family"]
        for field in req_fields:
            if not body.get(field):
                abort(400, f"Missing {field}")

        prod_fam = body.get("product_family")

        return route_acceptance(body, prod_fam)
