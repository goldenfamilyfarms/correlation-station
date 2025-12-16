import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.bll.resource_status import get_resource_status
from palantir_app.common.constants import PASS_THROUGH
from common_sense.common.errors import abort
from palantir_app.common.regres_testing import mock_resource_status_response
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from sense_common.observability.mdso_patterns import ErrorCategorizer


api = Namespace("v4/resourcestatus", description="Status of MDSO resources")

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


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
        resource_id = request.args.get("resourceId")
        
        with tracer.start_as_current_span("palantir.resource_status.get") as span:
            set_mdso_correlation(resource_id=resource_id)
            span.set_attribute("resource_status.operation", "get_status")
            
            if not resource_id:
                abort(400, "Missing resource ID")

            # no mdso resource was created
            if resource_id == PASS_THROUGH:
                span.set_attribute("resource_status.pass_through", True)
                return {"status": "Completed"}

            if "test" in resource_id:
                span.set_attribute("resource_status.test_mode", True)
                return mock_resource_status_response("/v4/resourcestatus", resource_id)

            poll_counter = request.args.get("poll_counter")
            poll_sleep = request.args.get("poll_sleep")
            
            if poll_counter and poll_sleep:
                span.set_attribute("resource_status.polling", True)
                span.set_attribute("resource_status.poll_counter", int(poll_counter))
                span.set_attribute("resource_status.poll_sleep", int(poll_sleep))
                add_span_event("resource_status.polling.start", resource_id=resource_id, counter=poll_counter)
            
            try:
                add_span_event("resource_status.query.start", resource_id=resource_id)
                result = get_resource_status(
                    resource_id,
                    poll=(poll_counter is not None and poll_sleep is not None),
                    poll_counter=int(poll_counter) if poll_counter else 0,
                    poll_sleep=int(poll_sleep) if poll_sleep else 0
                )
                
                # Extract status information
                if isinstance(result, dict):
                    status = result.get("status", "unknown")
                    span.set_attribute("resource_status.status", status)
                    if "summary" in result:
                        span.set_attribute("resource_status.summary", result["summary"])
                    if "message" in result:
                        span.set_attribute("resource_status.message", result["message"][:200])  # Truncate long messages
                    
                    # Extract circuit_id from label if available
                    if "data" in result and isinstance(result["data"], dict):
                        label = result["data"].get("label")
                        if label:
                            set_mdso_correlation(circuit_id=label)
                            span.set_attribute("mdso.circuit_id", label)
                
                add_span_event("resource_status.query.complete", resource_id=resource_id, status=result.get("status", "unknown"))
                return result
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise
