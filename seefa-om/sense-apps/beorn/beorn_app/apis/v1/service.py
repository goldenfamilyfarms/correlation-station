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

api = Namespace("v1/service", description="Create, delete, update, and check status of a service")

logger = logging.getLogger(__name__)


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
        if "cid" not in request.args:
            abort(400, "Missing CID")

        cid = request.args["cid"]
        token = create_token()

        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        err_msg, items = service_details(headers, cid, "charter.resourceTypes.NetworkService")
        if err_msg:
            abort(500, err_msg)

        msg = ""
        if items:
            for i in items:
                site_msgs = []
                if "site_status" in i["properties"]:
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
        else:
            abort(404, "No service found")
        delete_token(token)
        return msg

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
        if "cid" not in request.args:
            abort(400, "Missing CID")

        cid = request.args["cid"]
        token = create_token()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "token {}".format(token),
        }

        err_msg, service_id = service_id_lookup(headers, cid)
        if err_msg:
            abort(500, err_msg)
        if service_id is not None:
            return {"resource_id": service_id}, 200

        err_msg, product = product_query(headers, "NetworkService")
        if err_msg:
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
            abort(500, err_msg)
        delete_token(token)

        return {"resource_id": resource_id}, 201

    @api.response(
        200,
        "Deletion in progress",
        api.model("resource_id", {"resource_id": fields.String(example="5ce6bdc1-8176-417c-88fc-07931c7528d6")}),
    )
    @api.response(204, "No service found to delete")
    def delete(self):
        """Delete a service"""
        if "cid" not in request.args:
            abort(400, "Missing CID")

        cid = request.args["cid"]
        token = create_token()
        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        err_msg, service_id = service_id_lookup(headers, cid)
        if err_msg:
            abort(500, err_msg)

        if service_id is None:
            return "", 204

        logger.debug("Deleting service for {}".format(cid))
        err_msg = delete_service(headers, service_id)
        if err_msg:
            abort(500, err_msg)
        delete_token(token)
        return {"resource_id": service_id}, 200

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
        if "cid" not in request.args:
            abort(400, "Missing CID")
        cid = request.args["cid"]

        body = json.loads(request.data.decode("utf-8"))

        bw = True if body.get("bw") and body["bw"] == "true" else False
        ip = True if body.get("ip") and body["ip"] == "true" else False
        dsc = True if body.get("dsc") and body["dsc"] == "true" else False

        if not bw and not ip and not dsc:
            abort(400, "Select at least one option to update.")

        token = create_token()
        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        err_msg, prod_id = product_query(headers, "NetworkServiceUpdate")
        if err_msg:
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
            successes["ip_resource_id"] = resource_id
        if bw:
            data["properties"]["ip"] = False
            data["properties"]["description"] = False
            data["properties"]["bandwidth"] = True
            err_msg, resource_id = post_to_service(headers, data, cid)
            if err_msg:
                errors.append("Bandwidth error: {}".format(err_msg))
            successes["bw_resource_id"] = resource_id
        if dsc:
            data["properties"]["bandwidth"] = False
            data["properties"]["ip"] = False
            data["properties"]["description"] = True
            err_msg, resource_id = post_to_service(headers, data, cid)
            if err_msg:
                errors.append("Description error: {}".format(err_msg))
            successes["dsc_resource_id"] = resource_id
        if errors:
            abort(500, ", ".join(errors))
        delete_token(token)
        return successes, 201
