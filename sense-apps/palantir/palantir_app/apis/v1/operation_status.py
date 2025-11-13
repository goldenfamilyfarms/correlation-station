import logging

from flask import request
from flask_restx import Namespace, Resource, fields

# from palantir_app.common.mdso_auth import create_token, delete_token
from common_sense.common.errors import abort
from palantir_app.common.mdso_operations import status_call
from palantir_app.dll.mdso import _create_token, _delete_token

api = Namespace("v1/operationstatus", description="Status of MDSO operations")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(
    200,
    "OK",
    api.model(
        "op_status_success",
        {
            "adminstate": fields.String(example="up", description="up or down"),
            "transmitting_optical_power": fields.String(example="0.0 dBm", description="light level"),
            "receiving_optical_power": fields.String(example="0.0 dBm", description="light level"),
            "status": fields.String(
                example="failed", description="requested, scheduled, executing, successful, or failed"
            ),
            "portSFPvendorPartNumber": fields.String(example="N/A"),
            "portSFPwavelength": fields.String(example="N/A"),
            "portSFPvendorName": fields.String(example="N/A"),
            "status_info": fields.String(example="Successfully able to retrieve port state"),
            "message": fields.String(
                example="MDSO failure reason", description="If not failed, message does not appear"
            ),
        },
    ),
)
@api.response(
    400,
    "Bad Request",
    api.model(
        "bad request", {"status": fields.String(example="failed"), "message": fields.String(example="bad request")}
    ),
)
@api.response(404, "Page Not Found")
@api.response(500, "Application Error")
class PortStatus(Resource):
    @api.doc(params={"resourceId": "resourceId", "operationId": "operationId"})
    def get(self):
        """Takes resourceID and operationID and returns status.

        ### 200 - Possible MDSO status values: ###

        “requested”, “scheduled”, “executing”, “successful”, “failed”

        Communication problems with MDSO -
        ```
        {
            "status": "error",
            "message": "MDSO failed to process the operation status request"
        }
        ```
        Bad resourceID / operationID -
        ```
        {
            "status": "failed",
            "message": "resourceId/operationId not found"
        }
        ```
        """
        # TODO make these not case sensitive

        if "resourceId" not in request.args:
            abort(400, status="failed", message="bad request")
        if "operationId" not in request.args:
            abort(400, status="failed", message="bad request")
        if "operationType" in request.args and request.args["operationType"] != "portStatus":
            abort(400, status="failed", message="bad request")
        token = _create_token()
        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        error_msg, data = status_call(headers, request.args["resourceId"], request.args["operationId"])
        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            abort(500, error_msg)

        if data["state"] == "failed":
            logger.debug(data["reason"])
            abort(500, status="failed", message="{}".format(data["reason"]))
        payload = {"status": data["state"]}

        try:
            payload["adminstate"] = data["outputs"]["adminstate"]
            payload["transmitting_optical_power"] = data["outputs"]["portTxAvgOpticalPower"]
            payload["receiving_optical_power"] = data["outputs"]["portRxAvgOpticalPower"]
            payload["status_info"] = data["outputs"]["status"]
            payload["operstate"] = data["outputs"]["operstate"]
            payload["portSFPvendorPartNumber"] = data["outputs"]["portSFPvendorPartNumber"]
            payload["portSFPwavelength"] = data["outputs"]["portSFPwavelength"]
            payload["portSFPvendorName"] = data["outputs"]["portSFPvendorName"]

        except KeyError:
            if data["outputs"].get("status"):
                payload["status_info"] = data["outputs"]["status"]
            else:
                pass

        _delete_token(token)

        return payload
