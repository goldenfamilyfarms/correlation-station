import json
import logging
import time
from flask import request
from flask_restx import Namespace, Resource
from beorn_app.bll.mne import clean_message, expected_payloads, response_models, parse_payload
from common_sense.common.errors import abort
from beorn_app.common.http_auth import auth
from beorn_app.dll.granite import get_mne_network_id, update_mne_network_id
from beorn_app.dll.mdso import get_existing_resource_by_query, create_resource

api = Namespace("v1/MNE", description="CRUD operation for MNE")
logger = logging.getLogger(__name__)
_response_models = response_models(api)
_expected_models = expected_payloads(api)


@api.route("/")
@api.response(200, "OK", _response_models["mne_get_ok"])
@api.response(400, "Bad Request", _response_models["bad_request"])
@api.response(404, "Not Found", _response_models["bad_request"])
@api.response(500, "Internal Server Error", _response_models["server_error"])
@api.response(501, "Not Implemented", _response_models["server_error"])
@api.response(502, "Bad Gateway", _response_models["server_error"])
@api.response(503, "Service Unavailable", _response_models["server_error"])
@api.response(504, "Gateway Timeout", _response_models["server_error"])
class ResourceData(Resource):
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(params={"resource_id": "Resource ID", "label": "Hostname / TID"})
    def get(self):
        """Get information about a meraki organization and network after day 0 was performed"""
        # get the query parameter we will use to get the resource
        q_param = ""
        q_value = ""
        mne_rid = ""
        if request.args.get("resource_id"):
            q_param = "id"
            q_value = request.args.get("resource_id")
        elif request.args.get("label"):
            q_param = "label"
            q_value = request.args.get("label")
        else:
            abort(400, "Please provide a resource id or a resource label")

        dt = 5  # seconds
        max_wait = 60 * 10  # 10 min (does not include each get request time)

        # get the mne resource from the label and wait for it to finish processing
        timed_out = True
        mne_resource = None
        for _i in range(max_wait // dt):
            mne_resource = get_existing_resource_by_query(
                resource_type="charter.resourceTypes.merakiServices", q_param=q_param, q_value=q_value
            )
            if mne_resource is None:
                abort(400, f"Failed to find resource with query parameter and value ({q_param}: {q_value})")
            mne_rid = mne_resource["id"]
            if mne_resource["orchState"] != "activating":
                timed_out = False
                break
            time.sleep(dt)
        # did we end the loop because the resource finished, or we timed out
        if timed_out:
            abort(502, f"MNE resource {q_value} has timed out")

        properties = mne_resource["properties"]
        fail_reason = clean_message(mne_resource.get("reason", "")).strip()
        response = {
            "resource_id": mne_rid,
            "network_name": properties.get("networkName", None),
            "network_id": properties.get("networkID", None),
            "org_name": properties.get("orgName", None),
            "org_id": properties.get("orgID", None),
        }
        if fail_reason is not None and fail_reason != "":
            response["reason"] = fail_reason
        return response


@api.route("/claimDevice")
@api.response(200, "OK", _response_models["claim_ok"])
@api.response(400, "Bad Request", _response_models["bad_request"])
@api.response(404, "Not Found", _response_models["bad_request"])
@api.response(500, "Internal Server Error", _response_models["server_error"])
@api.response(501, "Not Implemented", _response_models["server_error"])
@api.response(502, "Bad Gateway", _response_models["server_error"])
@api.response(503, "Service Unavailable", _response_models["server_error"])
@api.response(504, "Gateway Timeout", _response_models["server_error"])
class Claim(Resource):
    @api.expect(_expected_models["claim_device"])
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self):
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Invalid payload, could not load as json")

        # create the payload to send to MDSO
        try:
            claim_payload = parse_payload(payload)
            if claim_payload in [None, {}]:
                abort(400, "Error occurred when attempting to create payload for MDSO")
        except Exception:
            abort(400, "Error occurred when attempting to create payload for MDSO")

        # send the payload to MDSO
        try:
            resource_id = create_resource(claim_payload, product="merakiClaim")
            if resource_id is None:
                abort(400, "problem sending payload to MDSO")
        except Exception:
            abort(400, "problem sending payload to MDSO")
        response = {"resource_id": resource_id}
        return response


@api.route("/NetID")
@api.response(400, "Bad Request", _response_models["bad_request"])
@api.response(404, "Not Found", _response_models["bad_request"])
@api.response(500, "Internal Server Error", _response_models["server_error"])
@api.response(501, "Not Implemented", _response_models["server_error"])
@api.response(502, "Bad Gateway", _response_models["server_error"])
@api.response(503, "Service Unavailable", _response_models["server_error"])
@api.response(504, "Gateway Timeout", _response_models["server_error"])
class MneNetIdAPI(Resource):
    @api.doc(params={"cid": "A cid"})
    @api.response(200, "OK", _response_models["netid_get_ok"])
    def get(self):
        """Get the Managed Network Edge (MNE) network ID from Granite"""
        if "cid" not in request.args:
            abort(400, message="Bad request - missing CID")
        cid = request.args.get("cid")
        return get_mne_network_id(cid)

    @api.expect(_expected_models["net_id_put"])
    @api.response(200, "OK", _response_models["netid_put_ok"])
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def put(self):
        """Update a Managed Network Edge (MNE) network ID in Granite"""
        body = json.loads(request.data.decode("utf-8"))
        required_fields = ["cid", "network_id"]
        for f, k in zip(body, required_fields):
            if f in required_fields and not body[f]:
                abort(400, f"Missing {f} value")
            if k not in body:
                abort(400, f"Missing {k}")
        return update_mne_network_id(body["cid"], body["network_id"]), 200


@api.route("/PerRoom")
@api.response(200, "OK", _response_models["claim_ok"])
@api.response(400, "Bad Request", _response_models["bad_request"])
@api.response(404, "Not Found", _response_models["bad_request"])
@api.response(500, "Internal Server Error", _response_models["server_error"])
@api.response(501, "Not Implemented", _response_models["server_error"])
@api.response(502, "Bad Gateway", _response_models["server_error"])
@api.response(503, "Service Unavailable", _response_models["server_error"])
@api.response(504, "Gateway Timeout", _response_models["server_error"])
class locationUpdate(Resource):
    @api.expect(_expected_models["mne_pr"])
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self):
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Invalid payload, could not load as json")

        # check the payload and send it to mdso
        try:
            required_fields = ["orgID", "networkID", "orgName", "networkName", "devices"]
            for rf in required_fields:
                if rf not in payload:
                    abort(400, f"Payload must contain {rf}")
            payload = {"label": f"{payload['networkName']}", "properties": payload}
            resource_id = create_resource(payload, product="merakiLocationUpdate")
            if resource_id is None:
                abort(400, "problem sending payload to MDSO")
            else:
                response = {"resource_id": resource_id}
                return response
        except Exception as e:
            abort(400, f"problem sending payload to MDSO: {e.args}")


@api.route("/template")
@api.response(200, "OK", _response_models["claim_ok"])
@api.response(400, "Bad Request", _response_models["bad_request"])
@api.response(404, "Not Found", _response_models["bad_request"])
@api.response(500, "Internal Server Error", _response_models["server_error"])
@api.response(501, "Not Implemented", _response_models["server_error"])
@api.response(502, "Bad Gateway", _response_models["server_error"])
@api.response(503, "Service Unavailable", _response_models["server_error"])
@api.response(504, "Gateway Timeout", _response_models["server_error"])
class Template(Resource):
    @api.expect(_expected_models["template"])
    @api.response(401, "Unauthorized")
    @auth.login_required
    @api.doc(security="Basic Auth")
    def post(self):
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            abort(400, "Invalid payload, could not load as json")
        try:
            required_fields = ["orgName", "template_name"]
            for rf in required_fields:
                if rf not in payload:
                    abort(400, f"Payload must contain {rf}")
            payload = {"label": f"{payload['orgName']} - {payload['template_name']}", "properties": payload}
            resource_id = create_resource(payload, product="merakiTemplate")

            if resource_id is None:
                abort(400, "problem sending payload to MDSO")
            else:
                response = {"resource_id": resource_id}
                return response
        except Exception as e:
            abort(400, f"problem sending payload to MDSO: {e.args}")
