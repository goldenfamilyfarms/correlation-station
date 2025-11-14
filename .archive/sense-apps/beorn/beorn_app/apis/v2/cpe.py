import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from beorn_app.bll.cpe import input_parameter_validation, stand_alone_eligibility
from common_sense.common.errors import abort
from beorn_app.common.mdso_auth import create_token, delete_token
from beorn_app.common.mdso_operations import (
    create_activate_op_id,
    dependencies_by_resource,
    lookup_dependencies,
    service_details,
    service_id_lookup,
)

api = Namespace("v2/cpe", description="CRUD operations for a CPE")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(
    400, "Bad Request", api.model("bad request", {"message": fields.String(example="Bad Request  - missing CID")})
)
@api.response(503, "Service Unavailable")
@api.response(500, "Application Error")
class CPE(Resource):
    @api.doc(params={"cid": "CID"})
    @api.response(404, "Service Not Found")
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
        Network Service Details
        """
        if "cid" not in request.args:
            abort(400, message="Bad request - missing CID")

        token = create_token()
        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        err_msg, service_data = service_details(headers, request.args["cid"], "charter.resourceTypes.NetworkService")

        if not service_data:
            abort(404, message="Service Not Found")
        if err_msg:
            abort(503, err_msg)

        resource_id = service_data[0]["id"]
        cpe_state = (
            service_data[0]["properties"]["site_status"][0]["state"]
            if service_data[0]["properties"].get("site_status")
            else "unavailable"
        )

        err_msg, dependencies = dependencies_by_resource(headers, resource_id, request.args["cid"])
        if err_msg:
            abort(503, err_msg)
        elif dependencies:
            service_type = dependencies[0]["properties"]["serviceType"]
            customer = dependencies[0]["properties"]["customerName"]
        else:
            service_type = "unavailable"
            customer = "unavailable"

        data = {
            "resourceId": resource_id,
            "serviceType": service_type,
            "networkServiceState": service_data[0]["properties"].get("state", "unavailable"),
            "cpeState": cpe_state,
            "cid": request.args["cid"],
            "customer": customer,
        }

        if dependencies:
            for link in dependencies[0]["properties"]["topology"][0]["data"]["link"]:
                uuid = link["uuid"].split("_")
                uuid_a = uuid[0].split("-")
                uuid_b = uuid[1].split("-")
                cpe = uuid_b[0]
                if cpe.lower()[-2:] in ["zw", "ww", "xw", "yw"]:
                    data["tid"] = uuid_a[0]
                    data["portid"] = "-".join(uuid_a[1:])
                    break
            for node in dependencies[0]["properties"]["topology"][0]["data"]["node"]:
                name = {}
                for pair in node["name"]:
                    name[pair["name"]] = pair["value"]
                if name["Role"] == "CPE":
                    data["physicalAddress"] = name["Address"]
                    break
        else:
            data["tid"] = "unavailable"
            data["portid"] = "unavailable"
            data["physicalAddress"] = "unavailable"

        if "cpe_activation" in service_data[0]["properties"]:
            data["cpeActivationStatus"] = service_data[0]["properties"]["cpe_activation"]
        if "cpe_activation_error" in service_data[0]["properties"]:
            data["cpeActivationError"] = service_data[0]["properties"]["cpe_activation_error"]

        delete_token(token)
        return data

    @api.doc(params={"cid": "CID", "ip": "ip - OPTIONAL", "tid": "TID", "port_id": "port ID"})
    @api.response(404, "Service Not Found")
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
    def put(self):
        """
        Activate the CPE
        """
        if "cid" not in request.args:
            abort(400, message="Bad request - missing CID")
        if "tid" not in request.args:
            abort(400, message="Bad request - missing TID")
        if "port_id" not in request.args:
            abort(400, message="Bad request - missing port_id")

        ip = request.args["ip"] if request.args.get("ip") else ""

        token = create_token()
        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        err_msg, resource_id = service_id_lookup(headers, request.args["cid"])
        if err_msg:
            abort(503, err_msg)
        if resource_id is None:
            abort(404, "Resource not found")

        payload = {
            "interface": "activateSite",
            "inputs": {"ip": ip, "site": request.args["tid"], "port": request.args["port_id"]},
        }

        err_msg, data = create_activate_op_id(headers, resource_id, payload)
        if err_msg:
            abort(503, err_msg)

        err_msg, uni_port = lookup_dependencies(headers, resource_id)
        if err_msg:
            abort(503, err_msg)

        delete_token(token)

        data["uni_port"] = uni_port
        return data, 201


@api.route("/scod_eligibility")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
@api.doc(
    params={
        "pe_router_fqdn": "pe_router_fqdn",
        "pe_router_vendor": "pe_router_vendor",
        "pe_router_model": "pe_router_model",
        "upstream_device_fqdn": "upstream_device_fqdn",
        "upstream_device_vendor": "upstream_device_vendor",
        "upstream_device_model": "upstream_device_model",
        "upstream_device_port": "upstream_device_port",
        "target_device_fqdn": "target_device_fqdn",
        "target_device_vendor": "target_device_vendor",
        "target_device_model": "target_device_model",
        "target_device_uplink": {"description": "target_device_uplink - optional", "type": "string", "default": None},
        "update_cpe": {"description": "CID Required if updating CPE", "type": "boolean", "default": "false"},
        "circuit_id": {"description": "CID Required if updating CPE", "type": "string", "default": None},
    }
)
class StandaloneConfigDeliveryEligibility(Resource):
    @api.doc(responses={200: "Ok", 400: "Bad Request"})
    def get(self):
        """
        Standalone Config Delivery Eligibility Check
        """
        parm_criteria = [
            "pe_router_fqdn",
            "pe_router_vendor",
            "pe_router_model",
            "upstream_device_fqdn",
            "upstream_device_vendor",
            "upstream_device_model",
            "upstream_device_port",
            "target_device_fqdn",
            "target_device_vendor",
            "target_device_model",
        ]

        input_parms = request.args
        logger.info("input_parms: {}".format(input_parms))

        # Validate input
        try:
            parm_error, validated_params = input_parameter_validation(input_parms, parm_criteria)
            if parm_error:
                # If input validation fails, abort the port
                return parm_error, 200
        except Exception:
            abort(500, "Failed to perform input parameter validation")

        try:
            eligibility_status = stand_alone_eligibility(validated_params)
            if not eligibility_status["eligible"]:
                return eligibility_status, 200
        except Exception:
            abort(500, "Failed to perform eligibility validation")

        return eligibility_status
