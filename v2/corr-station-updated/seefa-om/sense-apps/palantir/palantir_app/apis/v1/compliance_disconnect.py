import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.common.constants import (
    COMPLIANT,
    FIBER_INTERNET_ACCESS,
    IP_DISCONNECT_STAGE,
    ISP_STAGE,
    PATH_STATUS_STAGE,
    SITE_STATUS_STAGE,
    NETWORK_COMPLIANCE_STAGE,
    FULL_DISCO_ORDER_TYPE,
    DISCONNECT_IP_PRODUCTS,
    PARTIAL_DISCO_ORDER_TYPE,
    IP_RECLAIM_STAGE,
    IP_UNSWIP_STAGE,
    CPE_IP_RELEASE_STAGE,
    ISP_REQUIRED,
    PASS_THROUGH,
)
from palantir_app.common.compliance_utils import (
    is_compliance_required,
    ComplianceStages,
    validate_network_data_exists,
    translate_sf_order_type,
    translate_eng_job_type,
)
from palantir_app.bll import compliance_disconnect
from palantir_app.bll.compliance_disconnect_housekeeping import DisconnectHousekeeping, DisconnectServiceIPs
from palantir_app.bll.mdso import get_active_resource, get_resource_by_type_and_label
from common_sense.common.errors import abort
from palantir_app.common.http_auth import auth

logger = logging.getLogger(__name__)
api = Namespace("v1/compliance", description="Circuit Compliance API")

UNSUPPORTED_ERROR = api.model("unsupported", {"message": fields.String(example="Use case unsupported")})

PROCESS_ERROR = api.model("unable_to_proceed", {"message": fields.String(example="Unable to proceed with automation")})


# Disconnect Compliance Mapping
@api.route("/disconnect/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectCompliance(Resource):
    @api.response(
        201,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce4794b-6a0d-4855-84e7-2223e489ae40")}),
    )
    @api.expect(
        api.model(
            "post_disconnect_compliance_fields",
            {"order_type": fields.String(example="Partial Disconnect", description="Order Type provided from SF order")},
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self, cid):
        """Create disconnect mapper resource to identify any remnant configurations on network"""
        body = request.get_json()

        compliance = compliance_disconnect.Initialize(cid, body, body["order_type"].upper())
        if compliance.is_pass_through():
            return {"resource_id": PASS_THROUGH}, 211

        response = compliance.create_disconnect_mapper()
        return response, 201


# Disconnect Compliance Evaluation of Mapping
@api.route("/disconnect/status/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectComplianceStatus(Resource):
    @api.response(
        200,
        "Disconnect Compliance Status",
        api.model(
            "post_disconnect_compliance_status",
            {
                "message": fields.Nested(
                    api.model(
                        "status_message",
                        {
                            NETWORK_COMPLIANCE_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS),
                            IP_DISCONNECT_STAGE: fields.String(example=ComplianceStages.READY_STATUS),
                            ISP_STAGE: fields.String(example=ComplianceStages.NOT_PERFORMED_STATUS),
                            PATH_STATUS_STAGE: fields.String(example=ComplianceStages.NOT_PERFORMED_STATUS),
                            SITE_STATUS_STAGE: fields.String(example=ComplianceStages.NOT_PERFORMED_STATUS),
                        },
                    )
                ),
                COMPLIANT: fields.Boolean(default=True),
            },
        ),
    )
    @api.expect(
        api.model(
            "get_disconnect_compliance_fields",
            {
                "resource_id": fields.String(
                    example="625575e8-xxxx-yyyy-zzzz-c1bf8ae5fe19", required=True, description="MDSO Resource ID"
                ),
                "order_type": fields.String(example="FULL DISCONNECT", required=True, description="Order Type"),
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self, cid):
        """
        Evaluate compliance status of disconnect network service

        :param cid: circuit ID
        :type cid: str
        :return: compliance status
        :rtype: dict
        """
        body = request.get_json()
        resource_id = body["resource_id"]
        product_name = body["product_name"]
        order_type = translate_eng_job_type(body["order_type"])
        # make sure the right endpoint was called for the order type
        if not compliance_disconnect.is_valid_request(order_type):
            abort(400, f"Incorrect order type submitted for disconnect compliance request: {body['order_type']}")

        compliance_required = is_compliance_required(resource_id)
        # allow pass through orders to flow directly to housekeeping
        if not compliance_required:
            compliance_stages = ComplianceStages(order_type, product_name=product_name)
            compliance_stages.set_pass_through_status()
            return compliance_stages.status, 200

        network_data = get_active_resource(resource_id)
        if not network_data:
            abort(400, "Unable to get required network data for evaluation, no active DisconnectMapper resource found")
        endpoint_data = compliance_disconnect.get_endpoint_data(network_data)

        # get true order type by evaluating designed paths
        order_type = compliance_disconnect.get_order_type_by_impact_analysis(endpoint_data, order_type)

        # initialize compliance stages for order type
        compliance_stages = ComplianceStages(order_type, product_name=product_name)
        logger.debug(f"{cid} Initial Compliance Stages: {compliance_stages.status}")

        validate_network_data_exists(compliance_stages.status, resource_id, network_data)

        # check compliance
        compliance_disconnect.check_compliance(cid, product_name, network_data, compliance_stages.status)

        compliance_stages.set_next_stage_to_ready()
        return {"message": compliance_stages.status, COMPLIANT: True}, 200


# Disconnect Compliance Housekeeping Tasks (only called if /disconnect/status/<cid> response status 200)
@api.route("/disconnect/housekeeping/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectComplianceHousekeeping(Resource):
    @api.response(
        200,
        "Disconnect Compliance Housekeeping Status",
        api.model(
            "disconnect_compliance_housekeeping_status",
            {
                "message": fields.Nested(
                    api.model(
                        "message",
                        {
                            IP_DISCONNECT_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS),
                            ISP_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS),
                            PATH_STATUS_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS),
                            SITE_STATUS_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS),
                        },
                    )
                ),
                ISP_REQUIRED: fields.List(
                    fields.Nested(
                        api.model(
                            "isp_required",
                            {
                                "ispDisconnectTicket": fields.String(example="WO1253536"),
                                "site": fields.String(example="123 Unicorn Way"),
                                "engineeringPage": fields.String(example="ENG-4839333"),
                            },
                        )
                    )
                ),
            },
        ),
    )
    @api.expect(
        api.model(
            "disconnect_housekeeping_fields",
            {
                "resource_id": fields.String(
                    example="625575e8-xxxx-yyyy-zzzz-c1bf8ae5fe19", required=False, description="MDSO Resource ID"
                ),
                "order_type": fields.String(example="FULL DISCONNECT", required=True, description="Order Type"),
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
                "site_order_data": fields.List(
                    fields.Nested(
                        api.model(
                            "site_order_data",
                            {
                                "engineering_page": fields.String(
                                    example="ENG-01234567",
                                    required=False,
                                    description="Engineering Page Number, only required for disconnect orders",
                                ),
                                "service_location_address": fields.String(
                                    example="1234 Alden Marshall Pkwy Austin TX 78759",
                                    required=False,
                                    description="Service Location Address from engineering page, \
                                        only required for disconnect orders",
                                ),
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
    def put(self, cid):
        """
        Perform disconnect compliance housekeeping

        :param cid: circuit ID
        :type cid: str
        :return: disconnect compliance housekeeping status
        :rtype: dict
        """
        body = request.get_json()
        product_name = body["product_name"]
        site_order_data = body.get("site_order_data")
        resource_id = body.get("resource_id")
        network_data = None
        endpoint_data = None
        passthrough = True if resource_id == PASS_THROUGH else False
        order_type = translate_eng_job_type(body["order_type"], product_name)
        # make sure the right endpoint was called for the order type
        if not compliance_disconnect.is_valid_request(order_type):
            abort(400, f"Incorrect order type submitted for disconnect compliance request: {body['order_type']}")

        disconnect = compliance_disconnect.Initialize(cid, request=body, order_type=order_type)
        if not passthrough:
            if resource_id:
                network_data = get_active_resource(resource_id)
            else:
                network_data = get_resource_by_type_and_label(resource_type="DisconnectMapper", label=cid)
            if not network_data:
                abort(400, "Unable to get required network data, please provide MDSO DisconnectMapper resource ID")
            endpoint_data = compliance_disconnect.get_endpoint_data(network_data)
        else:
            endpoint_data = disconnect.get_endpoint_data_from_design(passthrough=True)
            # request product name cannot be trusted
            # so we harvest service data from Granite to ensure DOCSIS behavior throughout process
            product_name = endpoint_data["docsis_service_name"]

        # get true order type by evaluating designed paths
        order_type = compliance_disconnect.get_order_type_by_impact_analysis(endpoint_data, order_type)

        # now that we are sure of the order type, if it is full we need site order data from the request
        if order_type == FULL_DISCO_ORDER_TYPE and not site_order_data:
            abort(400, "Full disconnect detected. Site order data is required.")

        # initialize compliance stages for order type
        housekeeping_stages = ComplianceStages(order_type, product_name=product_name, housekeeping_only=True)
        logger.debug(f"{cid} Initial Compliance Stages: {housekeeping_stages.status}")
        # both full and partial FIA products require IP release process
        housekeeping = DisconnectHousekeeping(cid, product_name, endpoint_data)
        if product_name in DISCONNECT_IP_PRODUCTS:
            disconnect_ip = DisconnectServiceIPs()
            disconnect_ip.ip_release_process(cid, product_name, housekeeping_stages.status)
        # partial disconnect requires the path set to decom
        if order_type == PARTIAL_DISCO_ORDER_TYPE:
            housekeeping.set_path_to_decom(housekeeping_stages.status)
        # full disconnect requires ISP work order, path set to decom, and site set to decom
        if order_type == FULL_DISCO_ORDER_TYPE:
            if not passthrough:  # DOCSIS does not require IP reclaim or ISP
                housekeeping.reclaim_cpe_mgmt_ip(housekeeping_stages.status)
                housekeeping.isp_work_order_process(site_order_data, housekeeping_stages.status)
            housekeeping.set_path_to_decom(housekeeping_stages.status)
            housekeeping.set_site_to_decom(housekeeping_stages.status)
        return compliance_disconnect.format_response(housekeeping_stages.status, order_type, passthrough=passthrough)


# Disconnect Compliance Housekeeping Discrete Phases Below
@api.route("/disconnect/housekeeping/ip_unswip/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectIPUnSWIP(Resource):
    @api.response(
        200,
        "IP UnSWIP Status",
        api.model("ip_unswip_status", {IP_UNSWIP_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS)}),
    )
    @api.expect(
        api.model(
            "ip_unswip_fields",
            {
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
                "order_type": fields.String(example="Full Disconnect", required=True, description="order type"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self, cid):
        body = request.get_json()
        product_name = body["product_name"]
        order_type = translate_sf_order_type(body["order_type"].upper(), product_name)
        if product_name not in DISCONNECT_IP_PRODUCTS:
            abort(400, f"IP unSWIP Process unsupported for {product_name}. Supported: {DISCONNECT_IP_PRODUCTS}")
        if not compliance_disconnect.is_valid_request(order_type):
            abort(400, f"Invalid order type for IP unSWIP process request: {order_type}")
        disconnect_ip = DisconnectServiceIPs()
        status = {IP_UNSWIP_STAGE: ComplianceStages.READY_STATUS}
        unswipped, msg = disconnect_ip.release_ips(cid, f"arda/v1/ip_swip/unswip?cid={cid}")
        status[IP_UNSWIP_STAGE] = msg
        if not unswipped:
            abort(502, status)
        return status, 200


@api.route("/disconnect/housekeeping/ip_reclaim/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectIPReclaim(Resource):
    @api.response(
        200,
        "IP Reclaim Status",
        api.model("ip_reclaim_status", {IP_RECLAIM_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS)}),
    )
    @api.expect(
        api.model(
            "ip_reclaim_fields",
            {
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
                "order_type": fields.String(example="Full Disconnect", required=True, description="order type"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self, cid):
        body = request.get_json()
        product_name = body["product_name"]
        order_type = translate_sf_order_type(body["order_type"].upper(), product_name)
        if product_name not in DISCONNECT_IP_PRODUCTS:
            abort(400, f"IP Reclaim Process unsupported for {product_name}. Supported: {DISCONNECT_IP_PRODUCTS}")
        if not compliance_disconnect.is_valid_request(order_type):
            abort(400, f"Invalid order type for IP reclaim process request: {order_type}")
        disconnect_ip = DisconnectServiceIPs()
        status = {IP_RECLAIM_STAGE: ComplianceStages.READY_STATUS}
        released, msg = disconnect_ip.release_ips(cid, f"arda/v1/ip_reclamation?cid={cid}")
        status[IP_RECLAIM_STAGE] = msg
        if not released:
            abort(502, status)
        return status, 200


@api.route("/disconnect/housekeeping/mgmt_ip_reclaim/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectMgmtIPReclaim(Resource):
    @api.response(
        200,
        "MGMT IP Reclaim Status",
        api.model(
            "mgmt_ip_reclaim_status", {CPE_IP_RELEASE_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS)}
        ),
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self, cid):
        disconnect_impact_analysis = compliance_disconnect.Initialize(
            cid, request=None, order_type=None
        ).get_endpoint_data_from_design()
        full_disconnect = compliance_disconnect.is_full_type_present(disconnect_impact_analysis)
        if not full_disconnect:
            abort(400, "Full disconnect required for management IP reclaim process")
        status = DisconnectHousekeeping(cid, product_name="N/A").reclaim_cpe_mgmt_ip()
        return status, 200


@api.route("/disconnect/housekeeping/isp_work_order/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectISP(Resource):
    @api.response(
        200,
        "ISP Work Order Create Status",
        api.model("isp_stage_status", {ISP_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS)}),
    )
    @api.expect(
        api.model(
            "disconnect_isp_fields",
            {
                "order_type": fields.String(example="FULL DISCONNECT", required=True, description="Order Type"),
                "site_order_data": fields.List(
                    fields.Nested(
                        api.model(
                            "site_order_data",
                            {
                                "engineering_page": fields.String(
                                    example="ENG-01234567",
                                    required=False,
                                    description="Engineering Page Number, only required for disconnect orders",
                                ),
                                "service_location_address": fields.String(
                                    example="1234 Alden Marshall Pkwy Austin TX 78759",
                                    required=False,
                                    description="Service Location Address from engineering page, \
                                        only required for disconnect orders",
                                ),
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
    def put(self, cid):
        body = request.get_json()
        site_order_data = body["site_order_data"]
        disconnect_impact_analysis = compliance_disconnect.Initialize(
            cid, request=None, order_type=None
        ).get_endpoint_data_from_design()
        full_disconnect = compliance_disconnect.is_full_type_present(disconnect_impact_analysis)
        if not full_disconnect:
            abort(400, "Full disconnect required for ISP work order creation request")
        housekeeping = DisconnectHousekeeping(cid, product_name="N/A")
        status = housekeeping.isp_work_order_process(site_order_data)
        return status, 200


@api.route("/disconnect/housekeeping/decom_path/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectDecomPath(Resource):
    @api.response(
        200,
        "Path Decom Status",
        api.model("path_decom_status", {PATH_STATUS_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS)}),
    )
    @api.expect(
        api.model(
            "decom_path_fields",
            {
                "order_type": fields.String(example="Full Disconnect", required=True, description="order type"),
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self, cid):
        body = request.get_json()
        order_type = body["order_type"].upper()
        product_name = body["product_name"]
        if not compliance_disconnect.is_valid_request(order_type):
            abort(400, f"Invalid order type path decom process request: {order_type}")
        housekeeping = DisconnectHousekeeping(cid, product_name)
        status = housekeeping.set_path_to_decom()
        return status, 200


@api.route("/disconnect/housekeeping/decom_site/<cid>")
@api.response(400, "Bad Request")
@api.response(401, "Unauthorized")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", UNSUPPORTED_ERROR)
@api.response(502, "Bad Gateway", PROCESS_ERROR)
class DisconnectDecomSite(Resource):
    @api.response(
        200,
        "Site Decom Status",
        api.model("site_decom_status", {SITE_STATUS_STAGE: fields.String(example=ComplianceStages.SUCCESS_STATUS)}),
    )
    @api.expect(
        api.model(
            "decom_site_fields",
            {
                "product_name": fields.String(example=FIBER_INTERNET_ACCESS, required=True, description="product_name"),
                "skip_preliminary_process": fields.Boolean(
                    example=True,
                    default=True,
                    required=True,
                    description="Skip required preliminary processes: decom circuit path, decom transport path, delete equipment shelf.  Set True if preliminary decoms already handled and only site decom remains.",  # noqa
                ),
                "site_id": fields.String(
                    example="349367",
                    required=False,
                    description="Site ID to decom.  Value must be provided if skipping preliminary process.",
                ),
            },
        ),
        validate=True,
    )
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self, cid):
        body = request.get_json()
        disconnect_impact_analysis = compliance_disconnect.Initialize(
            cid, request=body, order_type=None
        ).get_endpoint_data_from_design()
        full_disconnect = compliance_disconnect.is_full_type_present(disconnect_impact_analysis)
        if not full_disconnect:
            abort(400, "Full disconnect required for site decom process request")
        product_name = body["product_name"]
        housekeeping = DisconnectHousekeeping(cid, product_name, endpoint_data=disconnect_impact_analysis)
        # if the preliminary decom processes are all complete, we'll fail if we repeat those deletes
        # this bypasses ALL preliminary validations as well, USE WITH CAUTION
        if body["skip_preliminary_process"]:
            if not body.get("site_id"):
                abort(400, "Site ID required if skipping preliminary processes.")
            status = housekeeping.no_guardrails_set_site_to_decom(body["site_id"])
            return status, 200
        status = housekeeping.set_site_to_decom()
        return status, 200
