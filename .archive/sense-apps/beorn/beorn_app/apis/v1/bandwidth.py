import logging
import re

from flask import request
from flask_restx import Namespace, Resource, fields

import beorn_app.common.mdso_auth
from common_sense.common.errors import abort
from beorn_app.common.granite_operations import path_update_by_parameters
from beorn_app.common.mdso_operations import product_query, update_by_parameters
from beorn_app.dll.hydra import get_headers

logger = logging.getLogger(__name__)

# globals used in this module for field trial available-bandwidth options
mbps_value_check_list = [25, 50, 100, 200, 300, 500, 1000]
gbps_value_check_list = [1]
example_available_bwdth = ["25 Mbps", "50 Mbps", "100 Mbps", "200 Mbps", "300 Mbps", "500 Mbps", "1 Gbps"]

api = Namespace("v1/bandwidth", description="MACD (i.e. CRUD) Operations on a Specified Service Bandwidth")


@api.route("/available")
@api.response(
    200, "OK", api.model("get_success", {"available_bandwidth": fields.String(example=example_available_bwdth)})
)
@api.response(
    400, "Bad Request", api.model("bad request", {"message": fields.String(example="Missing Mandatory Parameter")})
)
@api.response(500, "Service or Orchestrator Systems Error")
class BandwidthAvailable(Resource):
    @api.doc(params={"CID": "Circuit ID"})
    def get(self):
        """determine viable bandwidth(s) that can be assigned to a given service (using CID)"""
        circuit_id = request.args.get("CID", None)
        if circuit_id is None:
            abort(400, message="Missing CID (Circuit ID)")

        # if not request.args.get('cid'):
        #    abort(400, message='Missing Mandatory "circuit_id" Parameter')

        available_bandwidths_str = ""
        mbps_value_check_list.sort()
        gbps_value_check_list.sort()
        for val in mbps_value_check_list:
            available_bandwidths_str = "{}{} Mbps,".format(available_bandwidths_str, val)

        for val in gbps_value_check_list:
            available_bandwidths_str = "{}{} Gbps,".format(available_bandwidths_str, val)

        # remove final comma from the presented string
        available_bandwidths_str = available_bandwidths_str[:-1]
        available_bandwidths_str = available_bandwidths_str.strip().split(",")

        # TODO: This is a place holder for a much more complex algorithm to determine
        # how much bandwidth is actually available to this service
        # if 'circuit_id' not in request.args:
        # error_message = "Service ID (circuit_id) Parameter Is Mandatory"
        # abort(400, message=error_message)

        return {"available_bw": available_bandwidths_str}

    # TODO Need to Pull Current Granite or Network Bandwidth Setting from Topology Call to
    # Denodo or MDSO Call ( async)
    # Currently, Portal is calling Topologies for this info
    # @api.route('/configured')
    # @api.doc(params={'circuit_id': 'CID'})
    # class BandwidthConfigured:


@api.route("")
@api.response(
    201,
    "OK",
    api.model("bw_status_success", {"resource_id": fields.String(example="5cddb068-4206-4cd8-95f3-889a9989cff2")}),
)
@api.response(
    400, "Bad Request", api.model("Bad Request", {"message": fields.String(example="Missing Mandatory Parameter")})
)
@api.response(
    500,
    "System Error",
    api.model("System Error", {"message": fields.String(example="Service or Orchestrator Systems Error")}),
)
# Updates BOTH : Granite FIRST (record), THEN Network Bandwidth
@api.doc(params={"CID": "Circuit ID", "bw_value": "Bandwidth Value", "bw_unit": "Bandwidth Unit"})
class BandwidthUpdate(Resource):
    def put(self):
        """Update Network and Provisioning Database with Specifie Bandwidth Setting"""
        circuit_id = request.args.get("CID", None)
        bandwidth_units = request.args.get("bw_unit", None)
        bandwidth_value = request.args.get("bw_value", None)

        if not len(request.args):
            abort(400, message=("Circuit ID, Bandwidth Unit and Value are all mandatory to complete this Update"))

        if circuit_id is None:
            abort(400, message="Missing CID (Circuit ID)")
        if bandwidth_units is None:
            abort(400, message="Empty bw_unit (Bandwidth Unit)")
        if bandwidth_value is None:
            abort(400, message="Empty bw_value (Bandwidth Value)")

        test_regex = re.search("GBPS|MBPS", bandwidth_units.upper())
        if test_regex is None:
            abort(400, message="Units Must Be Specified as MBPS or GBPS")

        try:
            bandwidth_value = int(bandwidth_value)

        except ValueError:
            abort(400, message="Bandwidth value is not an integer")
        bandwidth_suffix = ""
        found_value = False

        if re.search("MBPS", bandwidth_units.upper()):
            bandwidth_suffix = "Mbps"
            for val in mbps_value_check_list:
                if val == bandwidth_value:
                    found_value = True
                    break
        if re.search("GBPS", bandwidth_units.upper()):
            bandwidth_suffix = "Gbps"
            for val in gbps_value_check_list:
                if val == bandwidth_value:
                    found_value = True
                    break

        if not found_value:
            abort(400, message="Updating Bandwidth to {} {} Not Available".format(bandwidth_value, bandwidth_units))

        # We are updating Granite ( out of sequence ) before updating the Network
        # Attempt to update the provisioning dbase (i.e. Granite)
        # TODO: This sequence is a little intereting; but will suffice for field trial
        headers = get_headers()

        update_parameters = {
            "procType": "update",
            "GRANITE_USER": "ws-mulesoft",
            "PATH_NAME": circuit_id,
            "PATH_BANDWIDTH": "{} {}".format(bandwidth_value, bandwidth_suffix),
        }

        prov_status, prov_response = path_update_by_parameters(headers, update_parameters)

        if prov_status == 400:
            abort(prov_status, "Target or CID {} is malformed or otherwise invalid".format(circuit_id))

        if prov_status != 200:
            abort(prov_status, "GRANITE ERROR RESPONSE")

        orchestrator_token = beorn_app.common.mdso_auth.create_token()

        if orchestrator_token is None:
            abort(500, "Orchestrator Is Not Returning Expected Auth Token")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "keep-alive",
            "Authorization": "token {}".format(orchestrator_token),
        }

        product_name = "NetworkServiceUpdate"

        error_message, product = product_query(headers, product_name)
        if error_message:
            beorn_app.common.mdso_auth.delete_token(orchestrator_token)
            abort(500, error_message)
        if product is None:
            beorn_app.common.mdso_auth.delete_token(orchestrator_token)
            abort(500, "Product Returned by Orchestrator is Malformed or Missing")

        update_parameters = {
            "autoClean": "false",
            "desiredOrchState": "active",
            "discovered": "false",
            "productId": product,
            "properties": {
                "bandwidth": True,
                "bandwidthValue": "{}{}".format(bandwidth_value, bandwidth_suffix),
                "circuit_id": circuit_id,
            },
            "label": circuit_id,
        }

        error_message, orchestrator_response = update_by_parameters(headers, update_parameters)
        if error_message:
            beorn_app.common.mdso_auth.delete_token(orchestrator_token)
            abort(500, error_message)

        if orchestrator_response and error_message is None:
            beorn_app.common.mdso_auth.delete_token(orchestrator_token)
            return {"resource_id": orchestrator_response["id"]}, 201

        beorn_app.common.mdso_auth.delete_token(orchestrator_token)
        abort(500, "Orchestrator Response Does Not Contain Mandatory Asynchronous-Operation Resource Identifier")
