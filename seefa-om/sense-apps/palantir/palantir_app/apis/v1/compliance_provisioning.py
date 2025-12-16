import logging
from werkzeug.exceptions import HTTPException

from flask import request
from flask_restx import Namespace, Resource, fields

from common_sense.common.errors import abort
from palantir_app.bll import compliance_provisioning, compliance_provisioning_housekeeping, compliance_wia
from palantir_app.bll.device_validator import validation_process
from palantir_app.common import compliance_utils
from palantir_app.common.constants import (
    COMPLIANT,
    DESIGN_COMPLIANCE_STAGE,
    FIBER_INTERNET_ACCESS,
    NETWORK_COMPLIANCE_STAGE,
    PASS_THROUGH,
    PATH_STATUS_STAGE,
    WIA_PRIMARY,
)
from palantir_app.common.http_auth import auth
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
api = Namespace("v1/compliance", description="Circuit Compliance API")
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()

UNSUPPORTED_ERROR = api.model("unsupported", {"message": fields.String(example="Use case unsupported")})

PROCESS_ERROR = api.model("unable_to_proceed", {"message": fields.String(example="Unable to proceed with automation")})


@api.route("/provisioning/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class ProvisioningCompliance(Resource):
    @api.response(
        201,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce4794b-6a0d-4855-84e7-2223e489ae40")}),
    )
    @api.expect(
        api.model(
            "post_compliance_fields",
            {
                "service_request_order_type": fields.String(
                    example="New Install",
                    default="New Install",
                    required=True,
                    description="Service Request Order Type provided from SF order",
                ),
                "order_type": fields.String(
                    example="New",
                    default="New",
                    required=True,
                    description="Engineering Job Type provided from SF order",
                ),
                "remediation_flag": fields.Boolean(
                    default=True,
                    required=False,
                    description="Optional parameter to enable/disable remediation of non-service impacting \
                        discrepancies between design and network",
                ),
                "duplex_setting": fields.String(
                    default="FULL", example="FULL", required=False, description="Duplex setting"
                ),
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self, cid):
        """Create service mapper resource to map discrepancies between network and design for circuit"""
        body = request.get_json()
        
        with tracer.start_as_current_span("palantir.compliance.provisioning.create") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("compliance.operation", "provisioning_create")
            span.set_attribute("compliance.order_type", body.get("order_type", "unknown"))
            span.set_attribute("compliance.service_request_order_type", body.get("service_request_order_type", "unknown"))
            span.set_attribute("compliance.product_name", body.get("product_name", "unknown"))
            span.set_attribute("compliance.remediation_flag", body.get("remediation_flag", True))
            
            try:
                add_span_event("compliance.provisioning.create.start", circuit_id=cid)
                compliance_provisioning.validate_request(body)  # abort if request is not feasible
                order_type = compliance_utils.translate_sf_order_type(
                    body["service_request_order_type"], body.get("product_name", "")
                )
                span.set_attribute("compliance.order_type_translated", order_type)
                
                network_compliance = compliance_provisioning.Initialize(cid, body, order_type)
                if network_compliance.is_pass_through():
                    span.set_attribute("compliance.pass_through", True)
                    add_span_event("compliance.provisioning.pass_through", circuit_id=cid)
                    span.set_status(Status(StatusCode.OK))
                    return {"resource_id": PASS_THROUGH}, 211
                
                span.set_attribute("compliance.pass_through", False)
                try:
                    add_span_event("compliance.device_validation.start", circuit_id=cid)
                    validation_process(cid, acceptance=False)
                    add_span_event("compliance.device_validation.complete", circuit_id=cid)
                except HTTPException as error:
                    logger.info(f"Validate Failed for {cid}: {error}")
                    error_context = error_categorizer.extract_error_context(str(error))
                    span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                    span.set_attribute("error.severity", error_context.get("severity", "WARN"))
                    add_span_event("compliance.device_validation.failed", circuit_id=cid, error=str(error))
                except Exception as error:
                    logger.info(f"Validate Failed for {cid} Exception: {error}")
                    error_context = error_categorizer.extract_error_context(str(error))
                    span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                    span.set_attribute("error.severity", error_context.get("severity", "WARN"))
                    add_span_event("compliance.device_validation.failed", circuit_id=cid, error=str(error))

                add_span_event("compliance.service_mapper.create.start", circuit_id=cid)
                response = network_compliance.create_service_mapper()
                
                if isinstance(response, dict) and "resource_id" in response:
                    span.set_attribute("mdso.resource_id", response["resource_id"])
                
                add_span_event("compliance.provisioning.create.complete", circuit_id=cid, resource_id=response.get("resource_id") if isinstance(response, dict) else None)
                span.set_status(Status(StatusCode.OK))
                return response, 201
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "COMPLIANCE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


@api.route("/provisioning/status/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class ProvisioningComplianceStatus(Resource):
    @api.response(
        200,
        "New/MAC Compliance Status",
        api.model(
            "compliance_status",
            {
                DESIGN_COMPLIANCE_STAGE: fields.String(example=compliance_utils.ComplianceStages.SUCCESS_STATUS),
                NETWORK_COMPLIANCE_STAGE: fields.String(example=compliance_utils.ComplianceStages.SUCCESS_STATUS),
                PATH_STATUS_STAGE: fields.String(example=compliance_utils.ComplianceStages.READY_STATUS),
                COMPLIANT: fields.Boolean(default=True),
            },
        ),
    )
    @api.expect(
        api.model(
            "get_compliance_fields",
            {
                "resource_id": fields.String(
                    example="625575e8-xxxx-yyyy-zzzz-c1bf8ae5fe19", required=True, description="MDSO Resource ID"
                ),
                "order_type": fields.String(example="NEW", required=True, description="Order Type"),
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
                "connector_type": fields.String(example="RJ45", required=False, description="connector_type"),
                "dia_svc_type": fields.String(example="LAN", required=False, description="dia_svc_type"),
                "ipv4": fields.String(example="/29=5", required=False, description="ipv4"),
                "uni_type": fields.String(example="Access", required=False, description="uni_type"),
                "bandwidth": fields.String(example="50 Mbps", required=False, description="Bandwidth"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self, cid):
        """
        Evaluate compliance status of new network service or network service update
        :param cid: circuit ID
        :type cid: str
        :return: compliance status
        :rtype: dict
        """
        body = request.get_json()
        resource_id = body.get("resource_id")
        
        with tracer.start_as_current_span("palantir.compliance.provisioning.status") as span:
            set_mdso_correlation(circuit_id=cid, resource_id=resource_id)
            span.set_attribute("compliance.operation", "provisioning_status")
            span.set_attribute("compliance.product_name", body.get("product_name", "unknown"))
            span.set_attribute("compliance.order_type", body.get("order_type", "unknown"))
            
            try:
                add_span_event("compliance.provisioning.status.check.start", circuit_id=cid, resource_id=resource_id)
                compliance_required = compliance_utils.is_compliance_required(resource_id)
                span.set_attribute("compliance.required", compliance_required)

                # get required details from request
                product_name = body["product_name"]
                order_type = compliance_utils.translate_eng_job_type(body["order_type"])
                span.set_attribute("compliance.order_type_translated", order_type)

                # make sure the right endpoint was called for the order type
                if not compliance_provisioning.is_valid_request(order_type):
                    error_msg = f"Incorrect order type submitted for provisioning compliance request: {body['order_type']}"
                    error_context = error_categorizer.extract_error_context(error_msg)
                    span.set_attribute("error.category", error_context.get("category", "VALIDATION_ERROR"))
                    abort(400, error_msg)

                # initialize compliance stages for order type
                compliance_stages = compliance_utils.ComplianceStages(order_type)
                logger.debug(f"{cid} Initial Compliance Stages: {compliance_stages.status}")

                # allow pass through orders to flow directly to housekeeping
                if not compliance_required:
                    compliance_stages.set_pass_through_status()
                    span.set_attribute("compliance.pass_through", True)
                    add_span_event("compliance.provisioning.pass_through", circuit_id=cid)
                    return compliance_stages.status, 200

                span.set_attribute("compliance.pass_through", False)
                order_details = compliance_utils.get_required_order_details(product_name, body, order_type)
                logger.debug(f"CID: {cid} Required data: {order_details}")

                # check compliance
                add_span_event("compliance.check.start", circuit_id=cid, order_type=order_type)
                compliance_provisioning.check_compliance(
                    order_details, cid, order_type, compliance_stages.status, resource_id=resource_id
                )
                add_span_event("compliance.check.complete", circuit_id=cid)

                compliance_stages.set_next_stage_to_ready()
                
                # Extract compliance status
                if isinstance(compliance_stages.status, dict):
                    compliant = compliance_stages.status.get(COMPLIANT, False)
                    span.set_attribute("compliance.compliant", compliant)
                
                add_span_event("compliance.provisioning.status.check.complete", circuit_id=cid)
                return compliance_stages.status, 200
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "COMPLIANCE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise


@api.route("/provisioning/housekeeping/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class ProvisioningComplianceHousekeeping(Resource):
    @api.response(
        200,
        "New/MAC Compliance Housekeeping Status",
        api.model(
            "compliance_housekeeping_status",
            {PATH_STATUS_STAGE: fields.String(example=compliance_utils.ComplianceStages.SUCCESS_STATUS)},
        ),
    )
    @api.expect(
        api.model(
            "path_status_update_fields",
            {
                "order_type": fields.String(example="NEW", required=False, description="Order Type"),
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self, cid):
        """
        Update path status to LIVE in design database

        :param cid: circuit ID
        :type cid: str
        :return: set to live status
        :rtype: dict
        """
        body = request.get_json()
        product_name = body["product_name"]
        order_type = compliance_utils.translate_eng_job_type(body["order_type"], product_name)
        # make sure the right endpoint was called for the order type
        if not compliance_provisioning.is_valid_request(order_type):
            abort(400, f"Incorrect order type submitted for set to live request: {body['order_type']}")

        set_to_live_status = compliance_utils.ComplianceStages(order_type, housekeeping_only=True).status

        compliance_provisioning_housekeeping.set_to_live(
            cid, order_type=order_type, compliance_status=set_to_live_status, product_name=product_name
        )

        return set_to_live_status, 200


@api.route("/provisioning/wia/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class ProvisioningComplianceWIA(Resource):
    @api.response(
        201,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce4794b-6a0d-4855-84e7-2223e489ae40")}),
    )
    @api.expect(
        api.model(
            "wia_compliance_post_fields",
            {
                "order_type": fields.String(example="NEW", required=False, description="Order Type"),
                "product_name": fields.String(example=WIA_PRIMARY, required=True, description="product_name"),
                "service_data": fields.List(
                    fields.Nested(
                        api.model(
                            "wia_service_data",
                            {
                                "name": fields.String(
                                    example="Wireless Internet Unlimited Premium", required=True, description="Rate Plan"
                                ),
                                "family": fields.String(
                                    example="Wireless Internet Access", required=False, description="Product Family Name"
                                ),
                                "serviceCode": fields.String(
                                    example="RW604", required=False, description="Ntl ICOMS Service Code"
                                ),
                                "quantity": fields.String(example="1", required=False, description="Quantity"),
                                "orderType": fields.String(example="New", required=False, description="Order Type"),
                            },
                        )
                    )
                ),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self, cid):
        """Create WIA mapper resource to identify any remnant configurations on network"""
        body = request.get_json()
        product_name = body["product_name"]
        order_type = compliance_utils.translate_eng_job_type(body["order_type"], product_name)
        if not compliance_wia.is_valid_request(order_type):
            abort(400, f"Incorrect order type submitted for WIA provisioning compliance request: {body['order_type']}")
        network_compliance = compliance_wia.Initialize(cid, body, order_type)
        response = network_compliance.create_wia_mapper()
        return response, 201


@api.route("/provisioning/wia/status/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class ProvisioningComplianceWIAStatus(Resource):
    @api.response(
        200,
        "WIA Compliance Status",
        api.model(
            "wia_compliance_status",
            {
                DESIGN_COMPLIANCE_STAGE: fields.String(example=compliance_utils.ComplianceStages.SUCCESS_STATUS),
                NETWORK_COMPLIANCE_STAGE: fields.String(example=compliance_utils.ComplianceStages.SUCCESS_STATUS),
                COMPLIANT: fields.Boolean(default=True),
            },
        ),
    )
    @api.expect(
        api.model(
            "wia_compliance_status_fields",
            {
                "resource_id": fields.String(
                    example="625575e8-xxxx-yyyy-zzzz-c1bf8ae5fe19", required=True, description="MDSO Resource ID"
                )
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self, cid):
        compliance_stages = compliance_utils.ComplianceStages(order_type="WIA")
        logger.debug(f"{cid} Initial Compliance Stages: {compliance_stages.status}")
        body = request.get_json()
        resource_id = body.get("resource_id")
        compliance_wia.check_compliance_wia(compliance_stages.status, resource_id=resource_id)

        return compliance_stages.status, 200
