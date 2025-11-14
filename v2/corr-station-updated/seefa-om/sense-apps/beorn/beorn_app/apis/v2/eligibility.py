from flask import request
from flask_restx import Namespace, Resource
from common_sense.common.errors import abort
from beorn_app.bll.eligibility import circuit_test_eligibility

api = Namespace("v2/eligibility", description="Automation Eligibility Checks")


@api.route("/circuit_testing")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
@api.doc(
    params={
        "circuit_id": {"description": "Circuit ID", "type": "string"},
        "cpe_ip_address": {"description": "CPE IP Address Override", "type": "string", "default": None},
        "allow_ctbh": {"description": "Allow CTBH Service Types", "type": "boolean", "default": False},
        "cap_eline_bandwidth": {
            "description": "Mark eline bandwidth greater than 2Gbps as ineligible",
            "type": "boolean",
            "default": True,
        },
        "check_ssh": {
            "description": "Check that device is reachable via SSH. "
            + "'Optional' returns a warning. 'Yes' will return a failure.",
            "type": "string",
            "default": None,
        },
        "username": {
            "description": "Username of the person or service calling this endpoint.",
            "type": "string",
            "default": None,
        },
        "fastpath_only": {
            "description": "Failout instead of running slow fallbacks.",
            "type": "boolean",
            "default": False,
        },
        "cpe_planned_ineligible": {
            "description": "Mark No CPE Planned Status Ineligible",
            "type": "boolean",
            "default": False,
        },
    }
)
class CircuitTestingEligibility(Resource):
    """
    Checks if the Circuit is eligible for testing by performing the following operations:
    1. Checks if the Service Type is FIA
    3. Checks if the Device Model is in the list of Supported Devices
    2. Checks if bandwidth is <= the bandwidth limit for the device
    4. Checks which tests are compatible with the current version
    :return: circuit_eligible - boolean
    """

    def get(self):
        circuit_id = request.args.get("circuit_id", "").strip()
        cpe_ip_address = request.args.get("cpe_ip_address", "").strip()
        allow_ctbh = request.args.get("allow_ctbh", False)
        cap_eline_bandwidth = request.args.get("cap_eline_bandwidth", True)
        check_ssh = request.args.get("check_ssh", "NO").strip().upper()
        username = request.args.get("username", "").strip().upper()
        fastpath_only = request.args.get("fastpath_only", False)
        cpe_planned_ineligible = request.args.get("cpe_planned_ineligible", False)
        if isinstance(allow_ctbh, str):
            allow_ctbh = allow_ctbh.upper() == "TRUE"
        if isinstance(cap_eline_bandwidth, str):
            cap_eline_bandwidth = cap_eline_bandwidth.upper() != "FALSE"
        if isinstance(fastpath_only, str):
            fastpath_only = fastpath_only.upper() != "FALSE"
        if isinstance(cpe_planned_ineligible, str):
            cpe_planned_ineligible = cpe_planned_ineligible.upper() != "FALSE"

        if not circuit_id:
            abort(400, "Bad request - missing CID")

        circuit_test = circuit_test_eligibility.Eligibility(
            circuit_id,
            cpe_ip_address,
            allow_ctbh,
            cap_eline_bandwidth,
            check_ssh,
            username,
            fastpath_only,
            cpe_planned_ineligible,
        )
        return circuit_test.check_automation_eligibility_by_leg()
