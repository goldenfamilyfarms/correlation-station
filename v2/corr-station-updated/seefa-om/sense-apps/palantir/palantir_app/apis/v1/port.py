import json
import logging

import requests
from flask import request
from flask_restx import Namespace, Resource, fields

import palantir_app
from common_sense.common.errors import abort
from palantir_app.common.mdso_operations import (
    create_resource,
    generate_op_id,
    generate_status_op_id,
    get_existing_resource,
    get_product,
    status_call,
)
from palantir_app.dll.mdso import _create_token, _delete_token
from palantir_app.common.utils import get_hydra_headers
from palantir_app.common.endpoints import GRANITE_EQUIPMENTS

api = Namespace("v1/port", description="CRUD operations for a core router port")

logger = logging.getLogger(__name__)


def granite_call(tid):
    """Call to Granite through mulesoft based on tid."""
    headers = get_hydra_headers("tid")
    clli = tid[:8]
    url = f"{palantir_app.url_config.GRANITE_BASE_URL}{GRANITE_EQUIPMENTS}"
    url += f"?CLLI={clli}&EQUIP_NAME={tid}&OBJECT_TYPE=SHELF&WILD_CARD_FLAG=1"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=60)
        if r.status_code == 200:
            granite_data = json.loads(r.content.decode("utf-8"))
            if len(granite_data) == 0:
                return {"message": "device not found"}, None
            else:
                return None, granite_data
        else:
            return {"message": f"Granite failed to process the request. Response: {r.status_code}"}, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to Granite")
        return {"message": "Granite failed to process the request. Connection or timeout error."}, None


@api.route("")
@api.response(400, "Bad Request", api.model("bad request", {"message": fields.String(example="bad request")}))
@api.response(404, "Page Not Found")
@api.response(500, "Application Error")
class Port(Resource):
    @api.response(
        201,
        "OK",
        api.model(
            "put_success",
            {
                "resourceId": fields.String(example="a resource id"),
                "operationId": fields.String(example="an operation id"),
            },
        ),
    )
    @api.doc(
        params={
            "tid": "TID",
            "port_id": "Port ID",
            "timer": 'How long to keep the port active in minutes. If "0" port will remain active.',
        }
    )
    @api.expect(
        api.model("activate", {"activate": fields.String(description="true or false", required=True, example="true")})
    )
    def put(self):
        """Activate or deactivate a port.

        ### 201 - Success: ###

        While we are working on activating or deactivating the port
        ```
        {
            "status": "on-boarding"
        }
        ```

        ### 500 - Application error: ###

        Bad port id -
        ```
        {
            "message": "port not present on the device"
        }
        ```

        Bad TID -
        ```
        {
            "message": "device not found"
        }
        ```

        Communication problems with MDSO -
        ```
        {
            "message": "MDSO failed to process the request"
        }
        ```
        """

        body = json.loads(request.data.decode("utf-8"))
        if not body.get("activate"):
            abort(400, message="missing activate")
        if "port_id" not in request.args:
            abort(400, message="missing port_id")
        if "timer" not in request.args:
            abort(400, message="missing timer")
        if "tid" not in request.args:
            abort(400, message="missing tid")

        tid = request.args.get("tid")
        port_id = request.args.get("port_id")
        timer = request.args.get("timer")
        try:
            timer = int(timer)
        except ValueError:
            abort(400, message="bad request")
        if timer > 60:
            timer = 60

        # POST to create token
        token = _create_token()

        # GET granite data
        error_msg, denodo_data = granite_call(tid)
        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            abort(500, message=error_msg["message"])

        target = denodo_data[0]["FQDN"]
        vendor = denodo_data[0]["EQUIP_VENDOR"]

        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        # GET on existing resourceID
        error_msg, resource_id = get_existing_resource(headers, target, port_id)
        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            abort(500, message=error_msg["message"])

        if resource_id == "still working":
            return {"status": "on-boarding"}, 201

        if not resource_id:
            # GET product
            res_type = "charter.resourceTypes.PortActivation"
            error_msg, product_id = get_product(headers, res_type)
            if error_msg:
                _delete_token(token)
                logger.debug(error_msg)
                abort(500, message=error_msg["message"])

            # POST to create resourceID
            # if timer is >= 30, you'll have to recreate this resource id
            error_msg, resource_id = create_resource(headers, tid, target, vendor, timer, port_id, product_id)
            if error_msg:
                _delete_token(token)
                logger.debug(error_msg)
                abort(500, message=error_msg["message"])

            return {"status": "on-boarding"}, 201

        # POST resourceID to get operationID
        error_msg, data = generate_op_id(headers, resource_id, body["activate"])
        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            abort(500, message=error_msg["message"])

        _delete_token(token)
        return data, 201

    @api.response(
        200,
        "OK",
        api.model(
            "get_success",
            {
                "resourceId": fields.String(example="5d9cac60-41d2-4d89-b965-1deee147af5b"),
                "operationId": fields.String(example="5d9cac6d-bad3-449d-a24c-f3113ae793a"),
            },
        ),
    )
    @api.doc(params={"tid": "TID", "port_id": "Port ID"})
    def get(self):
        """Returns on-boarding or port information.

        ### 200 - Success: ###
        While we are retrieving the port information -
        ```
        {
            "status": "on-boarding"
        }
        ```

        ### 500 - Application error: ###

        Bad port id -
        ```
        {
            "message": "port not present on the device"
        }
        ```

        Bad TID -
        ```
        {
            "message": "device not found"
        }
        ```

        Communication problems with MDSO -
        ```
        {
            "message": "MDSO failed to process the request"
        }
        ```

        Status lookup error in MDSO -
        ```
        {
            "message": "resourceId/operationId not found"
        }
        ```
        """

        if "port_id" not in request.args:
            abort(400, message="bad request")
        if "tid" not in request.args:
            abort(400, message="bad request")

        tid = request.args.get("tid")
        port_id = request.args.get("port_id")

        # POST to create token
        token = _create_token()

        # GET granite data
        error_msg, denodo_data = granite_call(tid)
        if error_msg:
            abort(500, message=error_msg["message"])

        target = denodo_data[0]["FQDN"]
        vendor = denodo_data[0]["EQUIP_VENDOR"]

        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        # GET on existing resourceID
        error_msg, resource_id = get_existing_resource(headers, target, port_id)
        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            abort(500, message=error_msg["message"])

        if resource_id == "still working":
            _delete_token(token)
            return {"status": "on-boarding"}

        if not resource_id:
            # GET product
            res_type = "charter.resourceTypes.PortActivation"
            error_msg, product_id = get_product(headers, res_type)
            if error_msg:
                _delete_token(token)
                logger.debug(error_msg)
                abort(500, message=error_msg["message"])

            # POST to create resourceID
            error_msg, resource_id = create_resource(headers, tid, target, vendor, 60, port_id, product_id)

            if error_msg:
                _delete_token(token)
                logger.debug(error_msg)
                abort(500, message=error_msg["message"])

            return {"status": "on-boarding"}

        # POST resourceID to get operationID for port status
        error_msg, op_id = generate_status_op_id(headers, resource_id)

        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            abort(500, message=error_msg["message"])

        error_msg, data = status_call(headers, resource_id, op_id)
        _delete_token(token)
        if error_msg:
            logger.debug(error_msg)
            abort(500, error_msg)

        if data["state"] == "failed":
            abort(500, message="MDSO failed to process the request")
        elif data["state"] != "successful":
            return {"status": "on-boarding"}
        else:
            try:
                payload = {"resourceId": resource_id, "operationId": op_id}
                return payload
            except KeyError:
                abort(500, message="bad request")
