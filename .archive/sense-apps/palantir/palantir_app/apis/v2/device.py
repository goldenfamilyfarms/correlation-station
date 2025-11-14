import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.bll.device_validator_deprecated import validate_device_circuit
from common_sense.common.errors import abort
from palantir_app.dll.granite import update_granite_shelf

api = Namespace("v2/device", description="NAC CRUD operations on Device")

logger = logging.getLogger(__name__)


# Swagger API modeling
bad_request = api.model(
    "bad_request",
    {"message": fields.String(example="Please submit a valid circuit id", description="Reason for exception")},
)

not_found = api.model(
    "not_found",
    {
        "message": fields.String(
            example="Device attributes not found", description="No records matching the specified criteria were found"
        )
    },
)

precondition_fail = api.model(
    "precondition_fail",
    {
        "message": fields.String(
            example="Device in CID is not in ISE", description="Expected precondition was not satisfied"
        )
    },
)

app_error = api.model(
    "application_error", {"error": fields.String(example="Issue with API request", description="Issue within the API")}
)

not_implemented = api.model(
    "not_implemented",
    {"error": fields.String(example="Use case <x> not implemented", description="Identify missing business logic")},
)

data_error = api.model(
    "data_error",
    {
        "error": fields.String(
            example="Issue with data from upstream server", description="Issue with upstream data source"
        )
    },
)

processing_error = api.model(
    "processing_error",
    {
        "error": fields.String(
            example="Issue with processing upstream request", description="Issue with processing upstream server request"
        )
    },
)

connection_error = api.model(
    "connection_error",
    {
        "error": fields.String(
            example="Issue with server connection", description="Connection issue with upstream data source"
        )
    },
)


@api.route("")
@api.response(504, "Connection Error", connection_error)
@api.response(503, "Processing Error", processing_error)
@api.response(502, "Data Error", data_error)
@api.response(501, "Not Implemented", not_implemented)
@api.response(500, "Application Error", app_error)
@api.response(412, "Precondition Failure", precondition_fail)
@api.response(404, "Resource Not Found", not_found)
@api.response(400, "Bad Request", bad_request)
@api.response(200, "OK")
class Device(Resource):
    @api.doc("device_check")
    @api.param("cid", "The circuit ID for the service")
    def get(self):
        """Determines if all devices for a CID or individual devices are login accessible"""
        cid = request.args.get("cid", "")

        # Validate arguments
        if not cid:
            abort(400, "Please submit required parameters.")

        if "test" in cid:
            return {"message": {"FAKETID": ["Config Remediation Success", "ISIN Success", "CA Spectrum Success"]}}, 200

        logger.debug(f"== cid {cid} ==")
        cid = cid.strip()
        return validate_device_circuit(cid)


@api.route("/ip_update")
@api.response(200, "OK")
@api.response(400, "Bad Request")
@api.response(404, "Not Found")
@api.response(500, "Application Error")
class DeviceIPUpdate(Resource):
    @api.param("TID", "The TID of the device - Example: DANEWCPE1ZW")
    @api.param("IP", "IP to update device management to in Granite - Example: 127.0.0.1/24")
    def post(self):
        """Updates Granite with IP address as Management IP of the device"""
        tid = request.args.get("TID")
        ip_addy = request.args.get("IP")

        # Validate arguments
        if len(request.args) != 2:
            missing = ""
            for in_arg in ["TID", "IP"]:
                if request.args.get(in_arg) is None:
                    missing = in_arg if missing == "" else missing + (", " + in_arg)
            abort(400, f"Please submit required parameters. Missing: {missing}")

        result = update_granite_shelf(tid=tid, ip=ip_addy)
        msg = {"TID": tid, "IP": ip_addy, "granite_update_success": result}

        return msg, 200
