import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.bll.resource_status import get_resource_status
from palantir_app.common.constants import PASS_THROUGH
from common_sense.common.errors import abort
from palantir_app.common.regres_testing import mock_resource_status_response


api = Namespace("v4/resourcestatus", description="Status of MDSO resources")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(
    200,
    "OK",
    api.model(
        "resource_status",
        {
            "id": fields.String(example="5ce47efe-c165-4795-8952-313b5c67d98b"),
            "status": fields.String(example="Enum(Processing, Completed, Failed)"),
            "summary": fields.String(example="Generalized Summary"),
            "message": fields.String(example="Failed Reason or Error Code"),
        },
    ),
)
@api.response(
    400, "Bad request", api.model("bad request 1", {"message": fields.String(example="Bad or Unsupported Request.")})
)
@api.response(
    404, "Resource ID Not Found", api.model("bad request 2", {"message": fields.String(example="Missing resourceId.")})
)
@api.response(
    500,
    "Application Error",
    api.model("app error 1", {"message": fields.String(example="SEnSE failed to process the request")}),
)
@api.response(
    501,
    "Unexpected Response",
    api.model("app error 2", {"message": fields.String(example="MDSO returned unexpected or unparsable response")}),
)
@api.response(
    502,
    "Downstream Missing or Invalid Response",
    api.model("app error 3", {"message": fields.String(example="MDSO returned invalid or missing information")}),
)
@api.response(
    504,
    "Gateway Timeout",
    api.model(
        "app error 4", {"message": fields.String(example="Timed Out Waiting on MDSO Response or Erroneous Connection")}
    ),
)
class ResourceStatus(Resource):
    @api.doc(
        params={
            "resourceId": "resourceId",
            "poll_counter": "int for num of iters",
            "poll_sleep": "int for seconds to sleep between iters",
        }
    )
    def get(self):
        """Takes resourceID and returns status."""

        if "resourceId" not in request.args:
            abort(400, "Missing resource ID")
        resource_id = request.args["resourceId"]

        # no mdso resource was created
        if resource_id == PASS_THROUGH:
            return {"status": "Completed"}

        if "test" in resource_id:
            return mock_resource_status_response("/v4/resourcestatus", resource_id)

        if "poll_counter" in request.args and "poll_sleep" in request.args:
            counter = request.args["poll_counter"]
            sleep = request.args["poll_sleep"]
            get_resource_status(resource_id, poll=True, poll_counter=counter, poll_sleep=sleep)
        return get_resource_status(resource_id)
