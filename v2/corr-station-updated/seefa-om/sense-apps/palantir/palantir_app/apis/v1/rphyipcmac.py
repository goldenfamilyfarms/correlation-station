import logging
import re
import json

import requests
from flask import request
from flask_restx import Namespace, Resource, fields

import palantir_app
from common_sense.common.errors import abort, error_formatter, SENSE, AUTOMATION_UNSUPPORTED
from palantir_app.common.utils import get_hydra_headers
from palantir_app.dll.ipc import ipc_get, ipc_post
from palantir_app.dll.sales_force import SalesforceConnection
from palantir_app.dll.denodo import denodo_get
from palantir_app.common.endpoints import DENODO_CIRCUIT_DEVICES, CROSSWALK_DHCP

api = Namespace("v1/rphyipcmac", description="updates the Mac Address for RPHY")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(200, "OK")
@api.response(400, "Bad Request")
@api.response(404, "Not Found")
@api.response(500, "Application Error")
class MacAdd(Resource):
    @api.doc(params={"CID": "CID", "mac_address": "MAC Address"})
    def get(self):
        """Retrieves MAC Address from given circuit id and validates Correct MAC Association"""

        self.validate_args(request)

        cid = request.args.get("CID", "").strip()

        response = denodo_get(DENODO_CIRCUIT_DEVICES, params={"cid": cid}, operation="mne")

        device_uid = self.check_device_uid(response.get("elements", [])[0])

        params = {"name": f"RPD-{device_uid}"}
        ipc_response = ipc_get(CROSSWALK_DHCP, params)

        return self.validate_mac(request.args.get("mac_address", ""), ipc_response)

    mac_RPHY_example = api.model(
        "MacIPC",
        {
            "CID": fields.String(required=False, example="81.L1XX.006522..TWCC"),
            "mac_address": fields.String(required=True, example="00:20:a3:3e:10:1b"),
        },
    )

    @api.doc(params={"CID": "CID", "mac_address": "MAC Address"})
    def post(self):
        """Appends MAC Address to DHCP Client Class in IPControl"""

        body = {}

        if isinstance(request.json, dict):
            body = request.json
        elif request.args:
            body = {"CID": request.args["CID"], "mac_address": request.args["mac_address"]}

        if not body:
            logger.exception("RPHY Mac Add json payload invalid.")
            abort(400, "Invalid RPHY Mac Add payload.")

        mac = body.get("mac_address")
        if not mac:
            abort(400, "Missing mac_address")

        cid = body.get("CID")
        if not cid:
            abort(400, "Missing CID")
        mac = mac.strip()
        cid = cid.strip()

        if not re.match("^([0-9a-fA-F][0-9a-fA-F]:){5}([0-9a-fA-F][0-9a-fA-F])$", mac):
            abort(400, "Invalid MAC Address")
        # TODO: Remove denodo api key from source
        headers = get_hydra_headers("mne")
        r = requests.get(
            f"{palantir_app.url_config.HYDRA_BASE_URL}{DENODO_CIRCUIT_DEVICES}?cid={cid}",
            verify=False,
            headers=headers,
            timeout=300,
        )
        response = r.json()

        if r.status_code // 100 != 2:
            abort(500, "Unable to retrieve data from Hydra")
        response = response["elements"][0]
        if len(response) == 0:
            abort(500, f"No results found for CID {cid}")
        try:
            device_uid = self.check_device_uid(response)
        except (KeyError, IndexError):
            abort(500, "UID does not exist for CID")

        params = {"name": f"RPD-{device_uid}"}
        ipc_response = ipc_get(CROSSWALK_DHCP, params)

        if any(key not in ipc_response.keys() for key in ["name"]):
            abort(502, "IPControl DHCP Client Class does contain necessary key values.")

        params["macAddress"] = [mac]
        ipc_post(CROSSWALK_DHCP, payload=params)

        return f"Successfully added MAC Address {mac} for CID {cid}", 200

    def validate_args(self, request):
        # check CID in args
        if "CID" not in request.args:
            abort(400, "Missing CID")

        # check mac address in args
        if "mac_address" not in request.args:
            abort(400, "Missing Mac Address ")

        # check formatting of mac address
        if not re.match("^([0-9a-fA-F][0-9a-fA-F]:){5}([0-9a-fA-F][0-9a-fA-F])$", request.args["mac_address"]):
            abort(400, "Invalid MAC Address")

    def check_device_uid(self, response):
        """
        checks that the device uid is present in the
        """
        try:
            for elem in response["data"]:
                if elem["sequence"].split(".")[0][-1] == "1" and elem["sequence"][-1] == "1":
                    return elem["path_name"].split(".")[-1]
        except (KeyError, IndexError):
            abort(500, "UID does not exist for CID")

    def validate_mac(self, mac_address, ipc_response):
        items = ipc_response.get("items", [])

        mac_matches_found = [
            items[x].get("value") for x in range(len(items)) if items[x].get("value", "") == mac_address
        ]

        if not mac_matches_found or not any(mac_matches_found):
            return {"match": False, "client_class": " "}, 200

        client_class = ipc_response.get("name", "")

        mac_validation_response = {"match": True, "client_class": client_class}

        return mac_validation_response, 200


@api.route("/clu_zip_codes")
@api.response(200, "OK")
@api.response(400, "Bad Request")
@api.response(404, "Resource Not Found")
@api.response(500, "Application Error")
class CLUZipCodes(Resource):
    @api.doc(params={"CID": "CID", "ENG_ID": "ENG_ID"})
    def get(self):
        """Retrieves Zip Code to be used for CLU given a CID"""
        sf = SalesforceConnection()
        payload_data = {}

        if "CID" in request.args.keys():
            query_params = "Name, Service_Location_Zip_Code__c"
            query_response = json.loads(
                json.dumps(
                    (
                        sf.query_sf(
                            f"SELECT {query_params} FROM Engineering__c WHERE Circuit_ID2__c = '{request.args['CID']}'"
                        )
                    )
                )
            )
            payload_data = {
                "eng_id": query_response[0]["Name"],
                "zip_code": query_response[0]["Service_Location_Zip_Code__c"],
            }

        elif "ENG_ID" in request.args.keys():
            query_params = "Service_Location_Zip_Code__c, Product_Family__c, Circuit_ID2__c FROM Engineering__c"
            query_response = json.loads(
                json.dumps((sf.query_sf(f"SELECT {query_params} WHERE Name = '{request.args['ENG_ID']}'")))
            )
            if len(query_response) > 0 and query_response[0].get("Product_Family__c") != "Fiber Connect Plus":
                subcategory = "Product Family Not Listed as FC+."
                error_detail = f"ENG ID: {request.args.get('ENG_ID')} - {query_response[0].get('Product_Family__c')}"
                error = error_formatter(SENSE, AUTOMATION_UNSUPPORTED, subcategory, error_detail)
                abort(404, error)
            payload_data = {
                "zip_code": query_response[0]["Service_Location_Zip_Code__c"],
                "cid": query_response[0]["Circuit_ID2__c"],
            }
        else:
            abort(500, "CID or ENG_ID Not Provided")

        return payload_data, 200
