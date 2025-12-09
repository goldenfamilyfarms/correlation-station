import logging

from flask import request
from flask_restx import Namespace, Resource

from beorn_app.bll import snmp
from beorn_app.dll.ipc import get_ip_from_tid
from common_sense.common.errors import abort
from beorn_app.common.utils import is_ip


api = Namespace("v1/device", description="Get device information using SNMP")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(200, "Success")
class Model(Resource):
    @api.doc(params={"ip": "IP", "return_ise_values": "Return ISE Vaues? (True/False) "})
    def get(self):
        """Get device vendor and model"""
        ip = _get_required_param("ip", request.args)
        return_ise_values = (
            True
            if "return_ise_values" in request.args and request.args["return_ise_values"].upper() == "TRUE"
            else False
        )
        response = snmp.get_device_vendor_and_model(ip, best_effort=False, return_ise_values=return_ise_values)
        return response, 200


@api.route("/system_info")
@api.response(200, "Success")
class SystemInfo(Resource):
    @api.doc(params={"device_id": "Device IP, FQDN, or TID"})
    def get(self):
        """Get device name, vendor, model, uptime, location"""
        device_id = _get_required_param("device_id", request.args)
        # if TID or FQDN provided instead of IP, get IP from TID
        if not is_ip(device_id):
            device_id = _get_ip_from_device_id(device_id)
        response = snmp.get_snmp_system_info(device_id)
        return response, 200


@api.route("/snmp_identifier")
@api.response(200, "Success")
class SNMPIdentifier(Resource):
    @api.doc(params={"device_id": "Device IP, FQDN, or TID", "object_id": "SNMP Object Identifier"})
    def get(self):
        """
        Get device information by provided SNMP OID (object identifier) or symbolic name
        """
        device_id = _get_required_param("device_id", request.args)
        object_id = _get_required_param("object_id", request.args)
        # if TID or FQDN provided instead of IP, get IP from TID
        if not is_ip(device_id):
            device_id = _get_ip_from_device_id(device_id)
        response = snmp.get_snmp_data_by_oid_or_symbolic_name(device_id, object_id)
        return response, 200


def _get_required_param(required_param, request_body):
    if required_param not in request_body:
        abort(400, message=f"Bad request - missing {required_param}")
    return request.args[required_param]


def _get_ip_from_device_id(device_id):
    hostname = device_id.split(".")[0]
    device_id = get_ip_from_tid(hostname)
    if device_id is None:
        abort(404, f"Unable to retrieve IP address for device: {hostname}")
    return device_id
