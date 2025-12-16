import json
import logging

from flask import request
from flask_restx import Namespace, Resource, fields

import beorn_app
from beorn_app.bll.service import create_core_service, get_service_info, get_service_map_info, update_service
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth
from beorn_app.common.regres_testing import regression_testing_check
from beorn_app.dll.mdso import create_service, mdso_get, product_query
from beorn_app.common.otel import get_tracer, set_mdso_correlation, add_span_event, set_span_error

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

api = Namespace("v3/service", description="CRUD for Core Provisioning")


MISSING_CID_MSG = "Missing CID"
BASE_RESOURCE_ENDPOINT = "/bpocore/market/api/v1/resources"


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
class Service(Resource):
    """CRUD operations for services. No validation is being performed on the CID."""

    @api.response(
        200,
        "OK",
        api.model(
            "service_status_success",
            {
                "MDSO service ID": fields.String(example="5cddb068-4206-4cd8-95f3-889a9989cff2"),
                "Stage": fields.String(example="PRODUCTION"),
                "Site state": fields.String(example="PROVISIONING_PRE_CHECKS"),
                "Site status": fields.List(
                    fields.Nested(
                        api.model(
                            "site_msgs",
                            {
                                "Host": fields.String(example="AUSDTXIR2ZW"),
                                "Site": fields.String(example="1121"),
                                "State": fields.String(example="NOT_STARTED"),
                            },
                        )
                    )
                ),
                "Current service state": fields.String(example="activating"),
                "Desired service state": fields.String(example="active"),
                "Reason": fields.String(example="MDSO failure reason if any"),
            },
        ),
    )
    @api.doc(params={"cid": "Circuit-Path ID", "service_mapping_only": "optional field to view map info"})
    def get(self):
        """Check status of a service"""
        cid = request.args.get("cid")
        if not cid:
            abort(400, MISSING_CID_MSG)
        
        with tracer.start_as_current_span("beorn.service.get") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "get_status")
            span.set_attribute("service.mapping_only", "service_mapping_only" in request.args)
            
            try:
                if "service_mapping_only" in request.args:
                    result = get_service_map_info(cid)
                    span.set_attribute("service.result_type", "mapping")
                else:
                    result = get_service_info(cid)
                    span.set_attribute("service.result_type", "status")
                    if isinstance(result, dict) and "MDSO service ID" in result:
                        span.set_attribute("mdso.resource_id", result["MDSO service ID"])
                        span.set_attribute("service.stage", result.get("Stage", "unknown"))
                        span.set_attribute("service.state", result.get("Current service state", "unknown"))
                
                add_span_event("service.status.retrieved", circuit_id=cid)
                return result, 200
            except Exception as e:
                set_span_error(e)
                raise

    @api.response(
        200,
        "Ok",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(
        201,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.expect(
        api.model(
            "service_post_fields",
            {
                "product_name": fields.String(
                    example="Fiber Internet Access", description="Product Name provided from SF order"
                ),
                "cid": fields.String(example="51.L1XX.802185..TWCC", description="51.L1XX.802185..TWCC"),
                "maintenance_window": fields.Boolean(default=False),
                "service_request_order_type": fields.String(
                    example="New Install",
                    default="New",
                    description="Service Request Order Type provided from order",
                    required=False,
                ),
                "engineering_job_type": fields.String(
                    example="New", default="New", description="Engineering Job Type provided from order", required=False
                ),
            },
        )
    )
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self):
        """Create a new service"""
        body = json.loads(request.data.decode("utf-8"))
        cid = body.get("cid")
        product_name = body.get("product_name")
        
        with tracer.start_as_current_span("beorn.service.create") as span:
            set_mdso_correlation(
                circuit_id=cid,
                product_id=product_name,
                service_type=body.get("service_request_order_type"),
            )
            span.set_attribute("service.operation", "create")
            span.set_attribute("service.product_name", product_name or "unknown")
            span.set_attribute("service.maintenance_window", body.get("maintenance_window", False))
            span.set_attribute("service.order_type", body.get("service_request_order_type", "unknown"))
            span.set_attribute("service.engineering_job_type", body.get("engineering_job_type", "unknown"))
            
            required_fields = ["cid", "product_name", "maintenance_window"]
            for f, k in zip(body, required_fields):
                if f in required_fields and body[f] is None:
                    abort(400, f"Missing {f} value")
                if k not in body:
                    abort(400, f"Missing {k}")
                if body["maintenance_window"] is True:
                    add_span_event("service.maintenance_window.detected", circuit_id=cid)
                    abort(
                        400,
                        "This order requires customer coordination & is ineligible for automation",
                        summary="MDSO | Automation Unsupported | Maintenance Window Required",
                    )

            # return response for QA regression testing
            if "STAGE" in beorn_app.app_config.USAGE_DESIGNATION:
                test_response = regression_testing_check(api.path, body["cid"], request="post")
                if test_response != "pass":
                    span.set_attribute("service.test_mode", True)
                    return test_response, 201

            try:
                resource_id, http_resp_code = create_core_service(body)
                span.set_attribute("mdso.resource_id", resource_id)
                span.set_attribute("http.status_code", http_resp_code)
                add_span_event("service.created", resource_id=resource_id, circuit_id=cid)
                return {"resource_id": resource_id}, http_resp_code
            except Exception as e:
                set_span_error(e)
                raise

    @api.response(
        201,
        "Created",
        api.model(
            "update_res_id",
            {
                "ip_resource_id": fields.String(example="5ce4794b-6a0d-4855-84e7-2223e489ae40"),
                "bw_resource_id": fields.String(example="5ce4794b-6a0d-1255-84e7-2223e489ae40"),
            },
        ),
    )
    @api.expect(
        api.model(
            "update_fields",
            {
                "bw": fields.Boolean(default=False),
                "ip": fields.Boolean(default=False),
                "dsc": fields.Boolean(default=False),
                "maintenance_window": fields.Boolean(default=False, required=False),
                "product_name": fields.String(
                    example="Fiber Internet Access", description="Product Name provided from SF order"
                ),
                "cid": fields.String(example="51.L1XX.009701..TWCC", description="51.L1XX.009701..TWCC"),
                "order_type": fields.String(
                    example="New Install", default="New Install", description="Order Type provided from SF order"
                ),
                "service_request_order_type": fields.String(
                    example="Change Request",
                    default="Change Request",
                    description="Service Request Order Type provided from order",
                    required=False,
                ),
                "engineering_job_type": fields.String(
                    example="Upgrade",
                    default="Upgrade",
                    description="Engineering Job Type provided from order",
                    required=False,
                ),
            },
        )
    )
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self):
        """Update an existing service map to include devices either uninstalled or undiscovered"""
        body = json.loads(request.data.decode("utf-8"))
        cid = body.get("cid")
        
        with tracer.start_as_current_span("beorn.service.update") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "update")
            span.set_attribute("service.update_types", {
                "bandwidth": body.get("bw", False),
                "ip": body.get("ip", False),
                "description": body.get("dsc", False),
            })
            span.set_attribute("service.order_type", body.get("order_type", "unknown"))
            
            # device_mapping boolean = TRUE + a CID will default to PUT of Device Mapping
            if not cid:
                abort(400, MISSING_CID_MSG)
            
            order_type = body.get("order_type")
            if "test" in cid:
                span.set_attribute("service.test_mode", True)
                return (
                    regression_testing_check(
                        "/v3/service", cid, request="put", validate_cid=False, order_type=order_type
                    ),
                    200,
                )

            try:
                response = update_service(body)
                status = 201
                if response.get("resource_id") == "pass through":
                    status = 211
                    span.set_attribute("service.pass_through", True)
                else:
                    if "ip_resource_id" in response:
                        span.set_attribute("mdso.ip_resource_id", response["ip_resource_id"])
                    if "bw_resource_id" in response:
                        span.set_attribute("mdso.bw_resource_id", response["bw_resource_id"])
                
                span.set_attribute("http.status_code", status)
                add_span_event("service.updated", circuit_id=cid, status=status)
                return response, status
            except Exception as e:
                set_span_error(e)
                raise


@api.route("/slm/configuration_variables")
@api.doc(params={"resource_id": "Resource ID"})
@api.response(404, "Service Not Found")
@api.response(
    200,
    "Success",
    api.model(
        "slm_configuration_variables",
        {
            "probe": fields.Nested(
                api.model(
                    "probe",
                    {
                        "handoff_port": fields.String(description="handoff port"),
                        "network_function_resource_id": fields.String(description="resource id"),
                        "circuit_id": fields.String(description="circuit id"),
                        "vlan": fields.String(description="vlan"),
                        "mep": fields.String(description="mep"),
                        "performance_tier": fields.String(description="slm performance tier"),
                        "remote_mep": fields.String(description="remote mep"),
                        "cos": fields.String(description="class of service"),
                        "maintenance_association": fields.String(description="maintenance association"),
                        "tid": fields.String(description="device tid"),
                        "maintenance_domain_name": fields.String(description="maintenance domain name"),
                        "maintenance_domain_level": fields.String(description="maintenance domain level"),
                        "client_md_level": fields.String(description="client maintenance domain level"),
                    },
                )
            ),
            "reflector": fields.Nested(
                api.model(
                    "reflector",
                    {
                        "handoff_port": fields.String(description="handoff port"),
                        "network_function_resource_id": fields.String(description="resource id"),
                        "circuit_id": fields.String(description="circuit id"),
                        "vlan": fields.String(description="vlan"),
                        "mep": fields.String(description="mep"),
                        "performance_tier": fields.String(description="slm performance tier"),
                        "remote_mep": fields.String(description="remote mep"),
                        "cos": fields.String(description="class of service"),
                        "maintenance_association": fields.String(description="maintenance association"),
                        "tid": fields.String(description="device tid"),
                        "maintenance_domain_name": fields.String(description="maintenance domain name"),
                        "maintenance_domain_level": fields.String(description="maintenance domain level"),
                        "client_md_level": fields.String(description="client maintenance domain level"),
                    },
                )
            ),
        },
    ),
)
class SLMConfigVariables(Resource):
    @api.doc(responses={200: "Ok", 400: "Bad Request"})
    def get(self):
        """
        Get variables necessary for generating SLM configuration from template.
        """
        resource_id = request.args.get("resource_id")
        if not resource_id:
            abort(400, message="Bad request - missing resource ID")
        
        with tracer.start_as_current_span("beorn.service.slm_config.get") as span:
            set_mdso_correlation(resource_id=resource_id)
            span.set_attribute("service.operation", "get_slm_config")
            
            base = BASE_RESOURCE_ENDPOINT
            endpoint_url = f"{base}/{resource_id}?full=false&obfuscate=true"
            
            try:
                slm_return = mdso_get(endpoint_url)
                if not slm_return:
                    abort(404, message="Resource Not Found")
                
                cid = slm_return.get("label")
                if cid:
                    set_mdso_correlation(circuit_id=cid)
                    span.set_attribute("mdso.circuit_id", cid)
                
                data = {
                    "resource_id": slm_return["id"],
                    "slm_configuration_variables": slm_return["properties"].get(
                        "slm_configuration_variables", slm_return["reason"]
                    ),
                    "cid": cid,
                }
                add_span_event("slm.config.retrieved", resource_id=resource_id, circuit_id=cid)
                return data
            except Exception as e:
                set_span_error(e)
                raise

    @api.doc(params={"cid": "CID"})
    @api.response(
        200,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    def post(self):
        """Create new SLM Config Variables resource"""
        cid = request.args.get("cid")
        if not cid:
            abort(400, MISSING_CID_MSG)

        with tracer.start_as_current_span("beorn.service.slm_config.create") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "create_slm_config")
            
            try:
                product = product_query("slmConfigVariables")
                data = {
                    "label": cid,
                    "description": "CID from sense CLI",
                    "productId": product,
                    "properties": {"circuit_id": cid},
                }

                logger.debug("Creating a service for {}".format(cid))
                resource_id = create_service(data)
                
                if resource_id is not None:
                    span.set_attribute("mdso.resource_id", resource_id)
                    add_span_event("slm.config.created", resource_id=resource_id, circuit_id=cid)
                    return {"resource_id": resource_id}, 200

                add_span_event("slm.config.created.pending", circuit_id=cid)
                return {"resource_id": resource_id}, 201
            except Exception as e:
                set_span_error(e)
                raise
