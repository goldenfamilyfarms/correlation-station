import json

from flask import request
from flask_restx import Namespace, Resource, fields

from beorn_app.bll.cpe import activate_cpe, cpe_activation_state
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth
from beorn_app.common.otel import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from beorn_app.common.otel.mdso_patterns import ErrorCategorizer

api = Namespace("v3/cpe", description="CRUD operations for a CPE")
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@api.route("")
@api.response(400, "Bad Request")
@api.response(404, "Service Not Found")
@api.response(500, "Application Error")
@api.response(502, "Bad Gateway")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
class CPE(Resource):
    """CPE CRUD Endpoints"""

    @api.doc(params={"cid": "CID"})
    @api.response(
        200,
        "Success",
        api.model(
            "circuit details success",
            {
                "cid": fields.String(example="51.L1XX.008486..TWCC"),
                "serviceType": fields.String(example="FIA"),
                "tid": fields.String(example="AUSDTXIR2QW"),
                "portid": fields.String(example="GE-1/0/2"),
                "physicalAddress": fields.String(example="11921 N MOPAC EXPY"),
                "networkServiceState": fields.String(example="READY_FOR_SERVICE"),
                "cpeState": fields.String(example="NOT_STARTED"),
                "cpeActivationStatus": fields.String(example="3. Checking CPE activation eligibility"),
                "cpeActivationError": fields.String(example="CPE is of unexpected model - expecting: RAD"),
                "resourceId": fields.String(example="5cf939bd-728d-4858-a8f7-be36f7afd30a"),
                "customer": fields.String(example="Andromeda"),
            },
        ),
    )
    def get(self):
        """
        Get the CPE Activation State
        """
        cid = request.args.get("cid")
        if not cid:
            abort(400, message="Bad request - missing CID")
        
        with tracer.start_as_current_span("beorn.cpe.get_activation_state") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("cpe.operation", "get_activation_state")
            
            try:
                add_span_event("cpe.activation_state.query.start", circuit_id=cid)
                result = cpe_activation_state(cid)
                
                # Extract CPE metadata from result
                if isinstance(result, dict):
                    if "tid" in result:
                        span.set_attribute("network.device.tid", result["tid"])
                    if "serviceType" in result:
                        span.set_attribute("cpe.service_type", result["serviceType"])
                    if "cpeState" in result:
                        span.set_attribute("cpe.state", result["cpeState"])
                    if "networkServiceState" in result:
                        span.set_attribute("cpe.network_service_state", result["networkServiceState"])
                    if "resourceId" in result:
                        span.set_attribute("mdso.resource_id", result["resourceId"])
                    if "cpeActivationError" in result:
                        error_context = error_categorizer.extract_error_context(result["cpeActivationError"])
                        span.set_attribute("error.category", error_context.get("category", "CPE_ERROR"))
                        span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                
                add_span_event("cpe.activation_state.query.complete", circuit_id=cid)
                return result, 200
            except Exception as e:
                set_span_error(e)
                raise

    @api.expect(
        api.model(
            "cpe_post_fields",
            {
                "cid": fields.String(example="51.L1XX.802185..TWCC"),
                "tid": fields.String(example="AUSDTXIR5CW"),
                "port_id": fields.String(example="ge-2/1/4"),
                "ip": fields.String(example="10.10.10.10"),
            },
        )
    )
    @api.response(
        201,
        "Success",
        api.model(
            "CPE_Activate_success",
            {
                "operationId": fields.String(example="5cf939bd-728d-4858-a8f7-be75f5dfd21e"),
                "resourceId": fields.String(example="5cf939bd-728d-4858-a8f7-be36f7afd30a"),
                "uni_port": fields.String(example="3"),
            },
        ),
    )
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self):
        """
        Activate A CPE
        """
        body = json.loads(request.data.decode("utf-8"))
        cid = body.get("cid")
        tid = body.get("tid")
        port_id = body.get("port_id")
        
        with tracer.start_as_current_span("beorn.cpe.activate") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("cpe.operation", "activate")
            span.set_attribute("network.device.tid", tid or "unknown")
            span.set_attribute("cpe.port_id", port_id or "unknown")
            if "ip" in body:
                span.set_attribute("cpe.ip_address", body["ip"])
            
            required_fields = ["cid", "tid", "port_id"]
            for f, k in zip(body, required_fields):
                if f in required_fields and not body[f]:
                    abort(400, f"Missing {f} value")
                if k not in body:
                    abort(400, f"Missing {k}")
            
            try:
                add_span_event("cpe.activation.start", circuit_id=cid, tid=tid, port_id=port_id)
                result = activate_cpe(body)
                
                # Extract activation result metadata
                if isinstance(result, dict):
                    if "operationId" in result:
                        span.set_attribute("cpe.operation_id", result["operationId"])
                    if "resourceId" in result:
                        span.set_attribute("mdso.resource_id", result["resourceId"])
                    if "uni_port" in result:
                        span.set_attribute("cpe.uni_port", result["uni_port"])
                
                add_span_event("cpe.activation.complete", circuit_id=cid, resource_id=result.get("resourceId"))
                return result, 201
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "CPE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise
