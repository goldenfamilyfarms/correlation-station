import json
import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.bll.port import check_port_status, get_ports, update_port, _clear_all_port_activation_mdso_resources
from common_sense.common.errors import abort
from palantir_app.common.http_auth import auth

api = Namespace("v2/port", description="CRUD operations for a core router port")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(400, "Bad Request")
@api.response(404, "Port Not Found")
@api.response(501, "Not Implemented")
@api.response(502, "Gateway Error")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
class Port(Resource):
    @api.response(
        200,
        "OK",
        api.model(
            "put_success",
            {
                "TID": fields.String(example="TID"),
                "Port": fields.String(example="Port ID"),
                "Activated": fields.Boolean(example="True"),
            },
        ),
    )
    @api.expect(
        api.model(
            "put_port_payload",
            {
                "activate": fields.Boolean(description="true or false", required=True, example=""),
                "tid": fields.String(description="TID", required=True, example=""),
                "port_id": fields.String(description="Port ID", required=True, example=""),
                "timer": fields.Integer(description="Timer to keep active", required=True, example=""),
            },
        )
    )
    def put(self):
        """Activate or deactivate a port."""
        try:
            body = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Could not read payload")
        tid = body.get("tid").upper()
        port_id = body.get("port_id").lower()
        timer = body.get("timer")
        activate = body.get("activate")
        if None in (tid, port_id, timer, activate):
            abort(400, "Missing field. Required fields are tid, port_id, timer, and activate.")

        try:
            timer = int(timer)
        except ValueError:
            abort(400, "timer is not an integer")
        if timer > 60:
            timer = 60

        return update_port(tid, port_id, timer, activate=activate), 200

    @api.response(
        200,
        "OK",
        api.model(
            "get_success",
            {
                "adminstate": fields.String(example="up"),
                "operstate": fields.String(example="up"),
                "transmitting_optical_power": fields.String(example="N/A"),
                "receiving_optical_power": fields.String(example="N/A"),
                "portSFPvendorPartNumber": fields.String(example="N/A"),
                "portSFPwavelength": fields.String(example="N/A"),
                "portSFPvendorName": fields.String(example="N/A"),
                "status_info": fields.String(example="N/A"),
            },
        ),
    )
    @api.doc(params={"tid": "TID", "port_id": "Port ID", "production": "false", "timer": "timer"})
    def get(self):
        """Get the port status"""
        if "port_id" not in request.args:
            abort(400, message="bad request")
        if "tid" not in request.args:
            abort(400, message="bad request")

        tid = request.args.get("tid").upper()
        port_id = request.args.get("port_id").lower()
        production = request.args.get("production", False)
        if production:
            production = True
        timer = request.args.get("timer")
        if "timer" not in request.args:
            timer = 60
        try:
            timer = int(timer)
        except ValueError:
            abort(400, "timer is not an integer")
        if timer > 60:
            timer = 60

        return check_port_status(tid, port_id, production, timer), 200


port_fields = {"tid": fields.String(example="TID"), "port_id": fields.String(example="Port ID")}


@api.route("/<cid>")
@api.response(400, "Bad Request")
@api.response(404, "Port Not Found")
@api.response(501, "Not Implemented")
@api.response(502, "Gateway Error")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
class PortCid(Resource):
    @api.response(
        200,
        "OK",
        api.model(
            "success",
            {
                "ports": fields.List(
                    fields.Nested(
                        api.model(
                            "nested", {"tid": fields.String(example="TID"), "port_id": fields.String(example="Port ID")}
                        )
                    )
                )
            },
        ),
    )
    @api.doc(params={"cid": "Specify the cid you want to the get ports to activate for"})
    def get(self, cid):
        """Get ports to activate on a cid"""
        if cid == "" or cid is None:
            abort(400, message="bad request")

        return get_ports(cid), 200


@api.route("/mdso")
@api.response(400, "Bad Request")
@api.response(501, "Not Implemented")
@api.response(502, "Gateway Error")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
class PortActivationMDSO(Resource):
    @auth.login_required
    @api.doc(security="Basic Auth")
    def delete(self):
        "Delete all Port Activation Resources from MDSO"
        return _clear_all_port_activation_mdso_resources()
