import json
import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from common_sense.common.errors import abort
from beorn_app.common.mdso_auth import create_token, delete_token
from beorn_app.common.mdso_operations import (
    delete_service,
    post_to_service,
    product_query,
    service_details,
    service_id_lookup,
)
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from sense_common.observability.mdso_patterns import ErrorCategorizer

api = Namespace("v1/service", description="Create, delete, update, and check status of a service")

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@api.route("")
@api.response(400, "Bad Request", api.model("bad_request", {"message": fields.String(example="Missing CID")}))
@api.response(
    500,
    "Application Error",
    api.model("app_error", {"message": fields.String(example="MDSO failed to process the request")}),
)
@api.doc(params={"cid": "CID"})
class Service(Resource):
    """CRUD operations for services. No validation is being performed on the CID."""

    @api.response(404, "No service found", api.model("no_data", {"message": fields.String(example="No service found")}))
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
    def get(self):
        """Check status of a service"""
        cid = request.args.get("cid")
        if not cid:
            abort(400, "Missing CID")

        with tracer.start_as_current_span("beorn.service.v1.get_status") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "get_status")
            span.set_attribute("service.api_version", "v1")
            
            try:
                add_span_event("service.status.query.start", circuit_id=cid)
                token = create_token()

                headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

                err_msg, items = service_details(headers, cid, "charter.resourceTypes.NetworkService")
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                    abort(500, err_msg)

                msg = ""
                if items:
                    for i in items:
                        span.set_attribute("mdso.resource_id", i["id"])
                        span.set_attribute("service.stage", i["properties"]["stage"])
                        span.set_attribute("service.state", i["properties"]["state"])
                        span.set_attribute("service.orch_state", i["orchState"])
                        span.set_attribute("service.desired_state", i["desiredOrchState"])
                        
                        site_msgs = []
                        if "site_status" in i["properties"]:
                            span.set_attribute("service.sites_count", len(i["properties"]["site_status"]))
                            for site in i["properties"]["site_status"]:
                                site_msgs.append({"Host": site["host"], "Site": site["site"], "State": site["state"]})
                        msg = {
                            "MDSO service ID": i["id"],
                            "Stage": i["properties"]["stage"],
                            "Site state": i["properties"]["state"],
                            "Site status": site_msgs,
                            "Current service state": i["orchState"],
                            "Desired service state": i["desiredOrchState"],
                            "Reason": i["reason"],
                        }
                        if i.get("reason"):
                            error_context = error_categorizer.extract_error_context(i["reason"])
                            span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                else:
                    span.set_attribute("service.found", False)
                    abort(404, "No service found")
                
                span.set_attribute("service.found", True)
                add_span_event("service.status.query.complete", circuit_id=cid)
                delete_token(token)
                return msg
            except Exception as e:
                set_span_error(e)
                raise

    @api.response(
        200,
        "Service already exists",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(
        201,
        "Created",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(404, "Resource Not Found")
    def post(self):
        """Create a new service"""
        cid = request.args.get("cid")
        if not cid:
            abort(400, "Missing CID")

        with tracer.start_as_current_span("beorn.service.v1.create") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "create")
            span.set_attribute("service.api_version", "v1")
            
            try:
                add_span_event("service.create.start", circuit_id=cid)
                token = create_token()

                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": "token {}".format(token),
                }

                err_msg, service_id = service_id_lookup(headers, cid)
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    abort(500, err_msg)
                if service_id is not None:
                    span.set_attribute("service.existing", True)
                    span.set_attribute("mdso.resource_id", service_id)
                    add_span_event("service.create.existing_found", circuit_id=cid, resource_id=service_id)
                    return {"resource_id": service_id}, 200

                span.set_attribute("service.existing", False)
                err_msg, product = product_query(headers, "NetworkService")
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    abort(500, err_msg)

                data = {
                    "label": cid,
                    "description": "CID from sense CLI",
                    "productId": product,
                    "properties": {"circuit_id": cid},
                    "autoclean": True,
                }

                logger.debug("Creating a service for {}".format(cid))
                err_msg, resource_id = post_to_service(headers, data, cid)
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    abort(500, err_msg)
                
                span.set_attribute("mdso.resource_id", resource_id)
                add_span_event("service.create.complete", circuit_id=cid, resource_id=resource_id)
                delete_token(token)

                return {"resource_id": resource_id}, 201
            except Exception as e:
                set_span_error(e)
                raise

    @api.response(
        200,
        "Deletion in progress",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(204, "No service found to delete")
    def delete(self):
        """Delete a service"""
        cid = request.args.get("cid")
        if not cid:
            abort(400, "Missing CID")

        with tracer.start_as_current_span("beorn.service.v1.delete") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "delete")
            span.set_attribute("service.api_version", "v1")
            
            try:
                add_span_event("service.delete.start", circuit_id=cid)
                token = create_token()
                headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

                err_msg, service_id = service_id_lookup(headers, cid)
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    abort(500, err_msg)

                if service_id is None:
                    span.set_attribute("service.found", False)
                    add_span_event("service.delete.not_found", circuit_id=cid)
                    return "", 204

                span.set_attribute("service.found", True)
                span.set_attribute("mdso.resource_id", service_id)
                logger.debug("Deleting service for {}".format(cid))
                err_msg = delete_service(headers, service_id)
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    abort(500, err_msg)
                
                add_span_event("service.delete.complete", circuit_id=cid, resource_id=service_id)
                delete_token(token)
                return {"resource_id": service_id}, 200
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
                "bw": fields.String(example="false", description="true or false"),
                "ip": fields.String(example="false", description="true or false"),
                "dsc": fields.String(example="false", description="true or false"),
            },
        )
    )
    @api.response(404, "Resource Not Found")
    def put(self):
        """Update a service
        This relies on Granite already having the updated data.

        Provide at least one option to update using the body payload."""
        cid = request.args.get("cid")
        if not cid:
            abort(400, "Missing CID")

        body = json.loads(request.data.decode("utf-8"))

        bw = True if body.get("bw") and body["bw"] == "true" else False
        ip = True if body.get("ip") and body["ip"] == "true" else False
        dsc = True if body.get("dsc") and body["dsc"] == "true" else False

        if not bw and not ip and not dsc:
            abort(400, "Select at least one option to update.")

        with tracer.start_as_current_span("beorn.service.v1.update") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("service.operation", "update")
            span.set_attribute("service.api_version", "v1")
            span.set_attribute("service.update.bandwidth", bw)
            span.set_attribute("service.update.ip", ip)
            span.set_attribute("service.update.description", dsc)
            
            try:
                add_span_event("service.update.start", circuit_id=cid, updates={"bw": bw, "ip": ip, "dsc": dsc})
                token = create_token()
                headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

                err_msg, prod_id = product_query(headers, "NetworkServiceUpdate")
                if err_msg:
                    error_context = error_categorizer.extract_error_context(err_msg)
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    abort(500, err_msg)

                # only one property can be updated at a time

                data = {
                    "label": cid,
                    "resourceTypeId": "charter.resourceTypes.NetworkServiceUpdate",
                    "productId": prod_id,
                    "properties": {
                        "ip": False,
                        "description": False,
                        "bandwidth": False,
                        "serviceStateenable": False,
                        "circuit_id": cid,
                        "serviceStatedisable": False,
                    },
                    "desiredOrchState": "active",
                }
                successes = {}
                errors = []

                if ip:
                    data["properties"]["bandwidth"] = False
                    data["properties"]["description"] = False
                    data["properties"]["ip"] = True
                    err_msg, resource_id = post_to_service(headers, data, cid)
                    if err_msg:
                        errors.append("IP error: {}".format(err_msg))
                    else:
                        successes["ip_resource_id"] = resource_id
                        span.set_attribute("service.update.ip.resource_id", resource_id)
                if bw:
                    data["properties"]["ip"] = False
                    data["properties"]["description"] = False
                    data["properties"]["bandwidth"] = True
                    err_msg, resource_id = post_to_service(headers, data, cid)
                    if err_msg:
                        errors.append("Bandwidth error: {}".format(err_msg))
                    else:
                        successes["bw_resource_id"] = resource_id
                        span.set_attribute("service.update.bw.resource_id", resource_id)
                if dsc:
                    data["properties"]["bandwidth"] = False
                    data["properties"]["ip"] = False
                    data["properties"]["description"] = True
                    err_msg, resource_id = post_to_service(headers, data, cid)
                    if err_msg:
                        errors.append("Description error: {}".format(err_msg))
                    else:
                        successes["dsc_resource_id"] = resource_id
                        span.set_attribute("service.update.dsc.resource_id", resource_id)
                
                if errors:
                    error_context = error_categorizer.extract_error_context(", ".join(errors))
                    span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                    span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                    abort(500, ", ".join(errors))
                
                add_span_event("service.update.complete", circuit_id=cid, updates_count=len(successes))
                delete_token(token)
                return successes, 201
            except Exception as e:
                set_span_error(e)
                raise
