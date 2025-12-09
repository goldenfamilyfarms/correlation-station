import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from common_sense.common.errors import abort
from beorn_app.bll.eligibility import circuit_test_eligibility
from beorn_app.bll.eligibility.rphy_activation_eligibility import RPHYActivationEligibilityChecker
from beorn_app.bll.eligibility.automation_eligibility import (
    Provisioning,
    ProvisioningChange,
    ComplianceNew,
    ComplianceChange,
    ComplianceDisconnect,
)
from beorn_app.common.generic import ENG_ID_REGEX, MAC_ADDR_REGEX
from beorn_app.bll.topologies import Topologies


api = Namespace("v1/eligibility", description="Automation Eligibility Checks")
logger = logging.getLogger(__name__)


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
        return circuit_test.check_automation_eligibility()


@api.route("/provisioning_new")
@api.response(404, "Page Not Found")
class ProvisioningNewEligibility(Resource):
    @api.response(
        418, "Unsupported for automation", api.model("unsupported", {"eligible": fields.Boolean(example=False)})
    )
    @api.response(200, "Eligible for automation", api.model("eligible", {"eligible": fields.Boolean(example=True)}))
    @api.doc(params={"circuit_id": {"description": "Circuit ID", "type": "string", "default": None}})
    def get(self):
        # new provisioning orders
        circuit_id = request.args.get("circuit_id").strip()
        if not circuit_id:
            abort(400, "Bad request - missing CID")

        topology_data = Topologies(circuit_id)
        topology = topology_data.create_topology()
        circuit_elements = topology_data.circuit_elements
        multi_leg = True if topology.get("PRIMARY") else False
        if multi_leg:
            primary_leg = Provisioning(topology["PRIMARY"], topology_data.primary_leg_elements)
            primary_eligibility, primary_status = primary_leg.check_automation_eligibility()
            primary_eligibility["leg"] = "primary"
            secondary_leg = Provisioning(topology["SECONDARY"], topology_data.secondary_leg_elements)
            secondary_eligibility, secondary_status = secondary_leg.check_automation_eligibility()
            secondary_eligibility["leg"] = "secondary"
            status = 200
            if primary_status != 200 or secondary_status != 200:
                status = 418
            provisioning_eligibility = [primary_eligibility, secondary_eligibility], status
        else:
            eligibility, status = Provisioning(topology, circuit_elements).check_automation_eligibility()
            provisioning_eligibility = [eligibility], status
        return provisioning_eligibility


@api.route("/provisioning_change")
@api.response(418, "Unsupported for automation")  # TODO add documentation for unsupported elements model
@api.response(404, "Page Not Found")
@api.response(200, "Eligible for automation")
@api.doc(params={"circuit_id": {"description": "circuit_id", "type": "string", "default": None}})
class ProvisioningChangeEligibility(Resource):
    def get(self):
        # change provisioning orders
        circuit_id = request.args.get("circuit_id").strip()
        if not circuit_id:
            abort(400, "Bad request - missing CID")

        topology_data = Topologies(circuit_id)
        topology = topology_data.create_topology()
        circuit_elements = topology_data.circuit_elements
        multi_leg = True if topology.get("PRIMARY") else False
        if multi_leg:
            primary_leg = ProvisioningChange(topology["PRIMARY"], topology_data.primary_leg_elements)
            primary_eligibility, primary_status = primary_leg.check_automation_eligibility()
            primary_eligibility["leg"] = "primary"
            secondary_leg = ProvisioningChange(topology["SECONDARY"], topology_data.secondary_leg_elements)
            secondary_eligibility, secondary_status = secondary_leg.check_automation_eligibility()
            secondary_eligibility["leg"] = "secondary"
            status = 200
            if primary_status != 200 or secondary_status != 200:
                status = 418
            provisioning_eligibility = [primary_eligibility, secondary_eligibility], status
        else:
            eligibility, status = ProvisioningChange(topology, circuit_elements).check_automation_eligibility()
            provisioning_eligibility = [eligibility], status
        return provisioning_eligibility


@api.route("/compliance_new")
@api.response(418, "Unsupported for automation")  # TODO add documentation for unsupported elements model
@api.response(404, "Page Not Found")
@api.response(200, "Eligible for automation")
@api.doc(params={"circuit_id": {"description": "circuit_id", "type": "string", "default": None}})
class ComplianceNewEligibility(Resource):
    def get(self):
        # new and change compliance orders
        circuit_id = request.args.get("circuit_id").strip()
        if not circuit_id:
            abort(400, "Bad request - missing CID")

        topology_data = Topologies(circuit_id)
        topology = topology_data.create_topology()
        circuit_elements = topology_data.circuit_elements
        multi_leg = True if topology.get("PRIMARY") else False
        if multi_leg:
            primary_leg = ComplianceNew(topology["PRIMARY"], topology_data.primary_leg_elements)
            primary_eligibility, primary_status = primary_leg.check_automation_eligibility()
            primary_eligibility["leg"] = "primary"
            secondary_leg = ComplianceNew(topology["SECONDARY"], topology_data.secondary_leg_elements)
            secondary_eligibility, secondary_status = secondary_leg.check_automation_eligibility()
            secondary_eligibility["leg"] = "secondary"
            status = 200
            if primary_status != 200 or secondary_status != 200:
                status = 418
            compliance_eligibility = [primary_eligibility, secondary_eligibility], status
        else:
            eligibility, status = ComplianceNew(topology, circuit_elements).check_automation_eligibility()
            compliance_eligibility = [eligibility], status
        return compliance_eligibility


@api.route("/compliance_change")
@api.response(418, "Unsupported for automation")  # TODO add documentation for unsupported elements model
@api.response(404, "Page Not Found")
@api.response(200, "Eligible for automation")
@api.doc(params={"circuit_id": {"description": "circuit_id", "type": "string", "default": None}})
class ComplianceChangeEligibility(Resource):
    def get(self):
        # new and change compliance orders
        circuit_id = request.args.get("circuit_id").strip()
        if not circuit_id:
            abort(400, "Bad request - missing CID")

        topology_data = Topologies(circuit_id)
        topology = topology_data.create_topology()
        circuit_elements = topology_data.circuit_elements
        multi_leg = True if topology.get("PRIMARY") else False
        if multi_leg:
            primary_leg = ComplianceChange(topology["PRIMARY"], topology_data.primary_leg_elements)
            primary_eligibility, primary_status = primary_leg.check_automation_eligibility()
            primary_eligibility["leg"] = "primary"
            secondary_leg = ComplianceChange(topology["SECONDARY"], topology_data.secondary_leg_elements)
            secondary_eligibility, secondary_status = secondary_leg.check_automation_eligibility()
            secondary_eligibility["leg"] = "secondary"
            status = 200
            if primary_status != 200 or secondary_status != 200:
                status = 418
            compliance_eligibility = [primary_eligibility, secondary_eligibility], status
        else:
            eligibility, status = ComplianceChange(topology, circuit_elements).check_automation_eligibility()
            compliance_eligibility = [eligibility], status
        return compliance_eligibility


@api.route("/compliance_disconnect")
@api.response(418, "Unsupported for automation")  # TODO add documentation for unsupported elements model
@api.response(404, "Page Not Found")
@api.response(200, "Eligible for automation")
@api.doc(params={"circuit_id": {"description": "circuit_id", "type": "string", "default": None}})
class ComplianceDisconnectEligibility(Resource):
    def get(self):
        # new and change compliance orders
        circuit_id = request.args.get("circuit_id").strip()
        if not circuit_id:
            abort(400, "Bad request - missing CID")

        topology_data = Topologies(circuit_id)
        topology = topology_data.create_topology()
        circuit_elements = topology_data.circuit_elements
        multi_leg = True if topology.get("PRIMARY") else False
        if multi_leg:
            primary_leg = ComplianceDisconnect(topology["PRIMARY"], topology_data.primary_leg_elements)
            primary_eligibility, primary_status = primary_leg.check_automation_eligibility()
            primary_eligibility["leg"] = "primary"
            secondary_leg = ComplianceDisconnect(topology["SECONDARY"], topology_data.secondary_leg_elements)
            secondary_eligibility, secondary_status = secondary_leg.check_automation_eligibility()
            secondary_eligibility["leg"] = "secondary"
            status = 200
            if primary_status != 200 or secondary_status != 200:
                status = 418
            compliance_eligibility = [primary_eligibility, secondary_eligibility], status
        else:
            eligibility, status = ComplianceDisconnect(topology, circuit_elements).check_automation_eligibility()
            compliance_eligibility = [eligibility], status
        return compliance_eligibility


@api.route("/rphy_activation")
@api.response(418, "Unsupported for automation")
@api.response(404, "Page Not Found")
@api.response(200, "Eligible for automation")
@api.doc(
    params={
        "eng_id": {"description": "Engineering ID", "type": "string", "default": None},
        "mac_address": {"description": "Mac Address", "type": "string", "default": None},
    }
)
class RPHYActivationEligibility(Resource):
    def get(self):
        eng_id = request.args.get("eng_id").strip()
        if not eng_id or not bool(ENG_ID_REGEX.match(eng_id)):
            abort(400, "Bad request - Invalid ENG ID")

        mac_address = request.args.get("mac_address").strip()
        if not mac_address or not bool(MAC_ADDR_REGEX.match(mac_address)):
            abort(400, "Bad request - Invalid Mac Address")

        eligibility_status = RPHYActivationEligibilityChecker(eng_id, mac_address)
        eligibility_status = eligibility_status.check_eligibility()

        return eligibility_status
