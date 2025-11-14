import logging

from flask import request
from flask_restx import Namespace, Resource, reqparse

from common_sense.common.errors import abort
from palantir_app.bll.device_validator import validation_process, validate_tacacs

api = Namespace("v2/device_validator", description="Validate and Remediate Device Connectivity Problems")

logger = logging.getLogger(__name__)


parser = reqparse.RequestParser()
parser.add_argument("cid", type=str, help="The circuit ID for the service")
parser.add_argument("tid", type=str, help="The TID for the device")


@api.route("")
@api.response(200, "OK")
@api.response(400, "Missing Input Parameter")
@api.response(502, "Step in process is in FAILED state, check the return message for details")
class Device(Resource):
    @api.doc("Validations for device IP, FQDN, TACACS access")
    @api.expect(parser, validate=True)
    def get(self):
        """Validates and remediates the device for connectivity issues"""
        cid = request.args.get("cid")
        tid = request.args.get("tid")

        if cid:
            cid = cid.strip()
            return validation_process(cid=cid), 200
        elif tid:
            tid = tid.strip()
            return validation_process(tid=tid), 200
        else:
            abort(400, "Please submit required parameters.")


@api.route("/tacacs")
@api.response(200, "OK")
@api.response(400, "Missing Input Parameter")
@api.response(502, "Step in process is in FAILED state, check the return message for details")
class DeviceTACACS(Resource):
    @api.doc(params={"ip": "Device management IP"})
    def get(self):
        """Validates TACACS access"""
        ip = request.args["ip"]
        return validate_tacacs(ip), 200
