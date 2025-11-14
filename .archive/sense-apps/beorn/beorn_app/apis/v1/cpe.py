import logging
import json

from flask import request
from flask_restx import Namespace, Resource, fields

from beorn_app.bll.cpe import (
    build_arda_swap_data,
    cpe_activation_eligibility,
    input_parameter_validation,
    stand_alone_eligibility,
    standalone_config,
    build_tulip,
    turnup_locate_ip_eligibility,
    build_firmware_updater,
    firm_up_eligibility,
    build_post_install_light_level,
)
from beorn_app.bll.ip_finder import ip_finder
from beorn_app.bll.topologies import Topologies
from common_sense.common.errors import abort
from beorn_app.common.mdso_auth import create_token, delete_token
from beorn_app.common.mdso_operations import (
    create_activate_op_id,
    dependencies_by_resource,
    lookup_dependencies,
    service_details,
    service_id_lookup,
)
from beorn_app.common.sense_operations import arda_cpe_swap
from beorn_app.dll.mdso import pill_poll_resource_status

from beorn_app.bll.snmp import get_firmware
from beorn_app.bll.snmp import get_device_vendor_and_model

api = Namespace("v1/cpe", description="CRUD operations for a CPE")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(
    400, "Bad Request", api.model("bad request", {"message": fields.String(example="Bad Request  - missing CID")})
)
@api.response(501, "Not Implemented")
@api.response(502, "Bad Gateway")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
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
                "tid": fields.String(example="AUSDTXIR2QW"),
                "portid": fields.String(example="GE-1/0/2"),
                "physicalAddress": fields.String(example="11921 N MOPAC EXPY"),
                "networkServiceState": fields.String(example="READY_FOR_SERVICE"),
                "cpeState": fields.String(example="NOT_STARTED"),
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

        err_msg, dependencies = dependencies_by_resource(headers, resource_id, request.args["cid"])
        if err_msg:
            abort(503, err_msg)

        data = {
            "resourceId": service_data[0]["id"],
            "networkServiceState": service_data[0]["properties"]["state"],
            "cpeState": service_data[0]["properties"]["site_status"][0]["state"],
            "cid": request.args["cid"],
            "customer": dependencies[0]["properties"]["customerName"],
        }

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


@api.route("/eligibility")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
@api.doc(params={"cid": "Circuit ID"})
class CPEEligibility(Resource):
    @api.doc(responses={200: "Ok", 400: "Bad Request"})
    def get(self):
        if not request.args.get("cid"):
            abort(400, "Please provide a cid.")

        cid = request.args.get("cid").split(" ")[0].split("\t")[0]

        topology = Topologies(cid).create_topology()
        eligibility_data = cpe_activation_eligibility(topology, cid)
        return eligibility_data


@api.route("/ip_finder")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
@api.doc(params={"cid": "Circuit ID", "tid": "TID"})
class IpFinder(Resource):
    @api.doc(responses={200: "Ok", 400: "Bad Request"})
    def get(self):
        """
        Primary function to initiate IP Provider which will obtain IP from MDSO IP Provider
        """
        if not request.args.get("cid"):
            abort(400, "Please provide a cid.")

        if not request.args.get("tid"):
            abort(400, "Please provide a tid.")

        cid = request.args.get("cid")
        tid = request.args.get("tid")
        response, status_code = ip_finder(cid, tid)
        if response and "CPE_IP" in response and not response.get("CPE_IP"):
            response["CPE_IP"] = "no ip found"
        return response, status_code


@api.route("/standalone_config_delivery")
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
        "update_cpe": {
            "description": "update_cpe - if TRUE, circuit_id required",
            "type": "boolean",
            "default": "false",
        },
        "circuit_id": {"description": "circuit_id", "type": "string", "default": None},
    }
)
class StandaloneConfigDelivery(Resource):
    @api.doc(responses={200: "Ok", 400: "Bad Request"})
    @api.expect(api.model("configuration-nation", {"configuration": fields.String()}))
    def post(self):
        """
        CID required if swapping
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

        body = json.loads(request.data.decode())

        logger.debug("=+=+=+=+=+=+=+=+=+= body (DICE-Provided configuration should be in here) =+=+=+=+=+=+=+=+=+=+=+=+")
        logger.debug(body)
        logger.debug("=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+")

        # Validate input
        try:
            parm_error, validated_params = input_parameter_validation(input_parms, parm_criteria)
            if parm_error:
                # If input validation fails, abort
                return parm_error, 200
        except Exception:
            abort(500, "Failed to perform input parameter validation")

        try:
            eligibility_status = stand_alone_eligibility(validated_params)
            if not eligibility_status["eligible"]:
                return eligibility_status, 200
        except Exception:
            abort(500, "Failed to perform eligibility validation")

        validated_params["configuration"] = body.get("configuration")

        # Call Arda to swap CPE in Granite if needed
        logger.info("++++++++++++++++++++++++++PARM_DICT++++++++++++++++++++++++++")
        logger.info(validated_params)
        swap_response = None
        if "update_cpe" in validated_params.keys() and validated_params["update_cpe"] is True:
            cid = input_parms["circuit_id"]
            device_tid = validated_params["target_device_fqdn"].split(".")[0]
            new_model = validated_params["target_device_model"]
            new_vendor = validated_params["target_device_vendor"]
            try:
                logger.info("&&&&&&&&&&&&&&&&&& SWAP_RESPONSE &&&&&&&&&&&&&&&&&&&&&&&&&&")
                swap_response = arda_cpe_swap(cid, device_tid, new_model, new_vendor, best_effort=True)
                swap_response_details = swap_response.json()
                logger.info(swap_response)
                logger.info(swap_response_details)

            except Exception:
                logger.info("Failed to successfully initiate CPE SWAP")

        # Proceed with standalone config delivery
        try:
            standalone_rid = standalone_config(validated_params)
            logger.info(standalone_rid)
        except Exception:
            abort(500, "Failed to successfully initiate CPEA stand alone config")

        if swap_response is not None:
            upd_arda_swap = build_arda_swap_data(swap_response)
            return {"StandAlone Config Resource": standalone_rid, "ARDA CPE SWAP Response": upd_arda_swap}, 201
        else:
            return {
                "StandAlone Config Resource": standalone_rid,
                "ARDA CPE SWAP Response": "CPE SWAP not requested or unsuccessful.",
            }, 201


@api.route("/TurnUpLocateIP")
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
    }
)
class TurnUpLocateIP(Resource):
    @api.doc(responses={200: "OK", 201: "Resource Created", 400: "Bad Request", 500: "Internal Server Error"})
    def post(self):
        """
        New CPE IP Gathering
        """
        parm_criteria = [
            "pe_router_fqdn",
            "pe_router_vendor",
            "pe_router_model",
            "upstream_device_fqdn",
            "upstream_device_vendor",
            "upstream_device_model",
            "upstream_device_port",
        ]

        input_parms = request.args

        # Validate input
        try:
            parm_error, validated_params = input_parameter_validation(input_parms, parm_criteria, True)
            if parm_error:
                parm_error_code = {
                    "error": str(parm_error["Error"]),
                    "error_code": "TULIP" + str(parm_error["Error Code"]),
                }
                return parm_error_code
        except Exception:
            return {"error": "Failed to perform input parameter validation", "error_code": "TULIP1099"}

        try:
            eligibility_status = turnup_locate_ip_eligibility(validated_params)
            if not eligibility_status["eligible"]:
                ineligible = "device_eligibility: " + str(eligibility_status["device_eligibility"])
                eligibility_status_code = "TULIP" + str(eligibility_status["Error Code"])
                return {"error": ineligible, "error_code": eligibility_status_code}
        except Exception:
            return {"error": "Failed to perform TULIP eligibility check", "error_code": "TULIP1299"}

        # Proceed with turnup locate ip tool
        try:
            tulip_rid = build_tulip(validated_params)
        except Exception:
            return {"error": "Failed to successfully initiate TurnUPLocateIP resource", "error_code": "TULIP1399"}

        else:
            return (tulip_rid, 200) if tulip_rid.get("error") else ({"TurnUPLocateIP Resource": tulip_rid["rid"]}, 201)


@api.route("/FirmwareFinder")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
@api.doc(params={"target_device_ip": "target_device_ip"})
class FirmwareFinder(Resource):
    @api.doc(responses={200: "OK", 201: "Resource Created", 400: "Bad Request", 500: "Internal Server Error"})
    def get(self):
        """
        New CPE Firmware Gathering
        """
        parm_criteria = ["target_device_ip"]

        input_parms = request.args

        # Validate input
        try:
            parm_error = input_parameter_validation(input_parms, parm_criteria, True)[0]
            if parm_error:
                parm_error_code = {
                    "error": str(parm_error["Error"]),
                    "error_code": "FIFI" + str(parm_error["Error Code"]),
                }
                return parm_error_code
        except Exception:
            return {"error": "Failed to perform input parameter validation", "error_code": "FIFI1099"}

        target_ip = request.args["target_device_ip"]

        try:
            device_type = get_device_vendor_and_model(target_ip, True, False, True)
            target_vendor = device_type["vendor"]
            target_model = device_type["model"]
            if not target_vendor or not target_model:
                return {
                    "error": "Unable to determine vendor, model, and current firmware version. "
                    "Default the device now and ensure preconfiguration is applied if needed, "
                    "then try again.",
                    "error_code": "FIFI1100",
                }
        except Exception:
            return {"error": "Failed while determining vendor and model", "error_code": "FIFI1199"}
        try:
            firmware = get_firmware(target_ip, target_vendor, False, True)
            if firmware:
                return {"Firmware": firmware, "Vendor": target_vendor, "Model": target_model}, 200
            else:
                return {"error": "Unable to obtain firmware version from device", "error_code": "FIFI1201"}
        except Exception:
            return {"error": "Failed while obtaining firmware", "error_code": "FIFI1299"}


@api.route("/FirmwareUpdater")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
@api.doc(
    params={
        "device_ip": "device_ip",
        "device_vendor": "device_vendor",
        "device_model": "device_model",
        "device_fqdn": "device_fqdn",
        "firmware_file": "firmware_file",
    }
)
class FirmwareUpdater(Resource):
    @api.doc(responses={200: "OK", 201: "Resource Created", 400: "Bad Request", 500: "Internal Server Error"})
    def post(self):
        """
        New CPE Firmware Updater
        """
        parm_criteria = ["device_ip", "device_vendor", "device_model", "device_fqdn", "firmware_file"]
        input_parms = request.args
        # Validate input
        parm_error, validated_params = input_parameter_validation(input_parms, parm_criteria, nonSCoD=True)
        if parm_error:
            # If input validation fails, abort
            parm_error_code = {
                "error": str(parm_error["Error"]),
                "error_code": " FIRMUP" + str(parm_error["Error Code"]),
            }
            return parm_error_code, 200
        try:
            eligibility_status = firm_up_eligibility(validated_params)
            if not eligibility_status["eligible"]:
                ineligible = "device_eligibility: " + str(eligibility_status["device_eligibility"])
                eligibility_status_code = "FIRMUP" + str(eligibility_status["Error Code"])
                return {"error": ineligible, "error_code": eligibility_status_code}, 200
        except Exception as e:
            abort(500, f"Failed to perform eligibility validation: {e}")

        # Proceed with update firmware tool
        try:
            firmware_updater_rid = build_firmware_updater(validated_params)
            logger.info(firmware_updater_rid)
        except Exception as e:
            abort(500, f"Failed to successfully initiate FirmwareUpdater resource: {e}")

        else:
            return {"Firmware Update Resource": firmware_updater_rid}, 201


@api.route("/PostInstallLightLevel")
@api.response(404, "Page Not Found")
@api.doc(
    params={
        "device_tid": "device tid",
        "device_port": "device port",
        "network_function_id": "network function resouce id - optional",
    }
)
@api.response(
    200,
    "OK",
    api.model(
        "PILL_Success",
        {
            "transmit_power": fields.String(example="-7.10"),
            "reach": fields.String(example="NOT PROVIDED"),
            "tx_high_alarm": fields.String(example="-2.21"),
            "rx_low_alarm": fields.String(example="-30.46"),
            "part_number": fields.String(example="LX-SFP-1G-C"),
            "rx_low_warn": fields.String(example="-27.21"),
            "rx_high_warn": fields.String(example="0.00"),
            "receive_power": fields.String(example="-4.63"),
            "tx_low_warn": fields.String(example="-9.51"),
            "tx_high_warn": fields.String(example="-3.00"),
            "media": fields.String(example="NOT PROVIDED"),
            "wavelength": fields.String(example="1310.00"),
            "vendor": fields.String(example="PROLABS"),
            "tx_low_alarm": fields.String(example="-10.51"),
            "rx_high_alarm": fields.String(example="3.01"),
        },
    ),
)
class PostInstallLightLevel(Resource):
    @api.doc(responses={200: "Ok", 400: "Bad Request"})
    def post(self, network_function_id=None):
        """
        Primary function is to initiate and obtain light levels from MDSO PostInstallLightLevel
        """
        input_params = request.args
        if not input_params.get("device_tid"):
            abort(400, "Please provide the device tid")
        if not input_params.get("device_port"):
            abort(400, "Please provide a device port.")

        # proceed with post install light level tool
        device_tid = input_params.get("device_tid")
        pill_rid = build_post_install_light_level(input_params, device_tid)

        logger.debug(f"THE POST INSTALL LIGHT LEVEL resource is {pill_rid}")

        data, response_code = pill_poll_resource_status(pill_rid)

        return data, response_code
