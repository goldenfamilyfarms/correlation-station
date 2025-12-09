import logging

from common_sense.common.errors import (
    GRANITE,
    INCORRECT_DATA,
    MISSING_DATA,
    abort,
    error_formatter,
    get_standard_error_summary,
)
from palantir_app.bll.mdso import delete_mdso_resources, get_activating_resource_id_by_type_and_filters
from palantir_app.common.compliance_utils import ComplianceStages, NetworkCompliance, pass_through_service_type, is_coax_voice_model
from palantir_app.common.constants import (
    DISCO_FAILURES_WITH_PORT,
    DISCONNECT_IP_PRODUCTS,
    ELIGIBILITY_ENDPOINT_BASE,
    ELINE_TOPOLOGY_INDEXES,
    FIA,
    FIA_TOPOLOGY_INDEXES,
    FULL_DISCO_ORDER_TYPE,
    NETWORK_COMPLIANCE_STAGE,
    PARTIAL_DISCO_ORDER_TYPE,
    WIA_MODEL_TO_MEDIA_TYPE_MAP,
)
from palantir_app.common.endpoints import DENODO_CIRCUIT_DEVICES
from palantir_app.common.system_cmds_util import fping_ip
from palantir_app.dll import granite
from palantir_app.dll.denodo import denodo_get
from palantir_app.dll.mdso import mdso_post, product_query
from palantir_app.dll.sense import sense_get

logger = logging.getLogger(__name__)


class Initialize(NetworkCompliance):
    def __init__(self, cid, request, order_type):
        super().__init__(cid, request, order_type)

    def is_pass_through(self):
        path_data = denodo_get(DENODO_CIRCUIT_DEVICES, params={"cid": self.cid})
        if path_data.get("elements"):
            path_data = path_data["elements"]
            for data in path_data[0]["data"]:
                if data.get("model"):
                    for model in WIA_MODEL_TO_MEDIA_TYPE_MAP.keys():
                        if model in data["model"] and "WAN" in data.get("port_access_id"):
                            return True
        else:
            msg = error_formatter(GRANITE, MISSING_DATA, "Path Elements", path_data)
            abort(502, f"{msg}. Response: {path_data}", summary=get_standard_error_summary(msg))
        if path_data and len(path_data) == 1 and is_coax_voice_model(path_data):
            return True
        return False

    def create_disconnect_mapper(self):
        # validate MDSO eligibility
        eligibility_endpoint = f"{ELIGIBILITY_ENDPOINT_BASE}/compliance_disconnect"
        self.check_automation_eligibility(eligibility_endpoint)
        # if there is already a compliance request processing for the same circuit, no need to recreate
        activating_resource_id = get_activating_resource_id_by_type_and_filters(
            "charter.resourceTypes.DisconnectMapper", filters={"label": self.cid, "properties.circuit_id": self.cid}
        )
        if activating_resource_id:
            return {"resource_id": activating_resource_id}

        endpoint_data = self.get_endpoint_data_from_design()
        service_type = endpoint_data.pop("service_type")
        payload = self._create_payload(endpoint_data, service_type)
        resource = mdso_post("/bpocore/market/api/v1/resources?validate=false&obfuscate=true", payload)
        return {"resource_id": resource["id"]}

    def get_endpoint_data_from_design(self, passthrough=False):
        # DOCSIS endpoint data cannot be obtained from topologies
        if passthrough:
            return self._get_docsis_endpoint_data()
        topology = sense_get(endpoint=f"beorn/v3/topologies?cid={self.cid}")
        if "error" in topology:
            abort(502, f"{topology['error']} - Unable to get endpoint data")
        maximum_endpoints = topology["service"][0]["data"]["evc"][0]["maxNumOfEvcEndPoint"]
        # 1 EVC endpoint signifies FIA, only Z side present
        if maximum_endpoints == 1:
            endpoint_data = self._get_endpoint_by_side(topology=topology, side="z_side", topology_index_type=FIA)
        # multiple EVC endpoints signifies ELINE, A + Z sides present
        else:
            # a side
            endpoint_data = self._get_endpoint_by_side(topology=topology, side="a_side", topology_index_type="ELINE")
            # z side
            endpoint_data = self._get_endpoint_by_side(
                topology=topology, side="z_side", topology_index_type="ELINE", endpoint_data=endpoint_data
            )

        return endpoint_data

    def _get_docsis_endpoint_data(self):
        circuit_data = denodo_get(DENODO_CIRCUIT_DEVICES, params={"cid": self.cid})
        site_id = self._get_docsis_site_id(circuit_data)
        endpoint_data = {
            "z_side_endpoint": self._get_docsis_tid(circuit_data),
            "z_side_address": self._get_docsis_address(circuit_data),
            "docsis_service_name": self._get_docsis_product_name(circuit_data),
            "z_side_disconnect": self._get_impact_analysis_from_site(site_id),
        }

        return endpoint_data

    def _get_docsis_site_id(self, circuit_data):
        return circuit_data["elements"][-1]["z_side_site_id"]

    def _get_docsis_tid(self, circuit_data):
        # hardcoded to grab the last data object for reasons:
        # docsis sip the 2 elements are identical, docsis pri the 1st element is a cloud
        return circuit_data["elements"][0]["data"][-1]["tid"]

    def _get_docsis_address(self, circuit_data):
        # this isn't really a full address, but docsis doesn't require ISP so we're ok
        return circuit_data["elements"][0]["data"][-1]["full_address"]

    def _get_docsis_product_name(self, circuit_data):
        elements = circuit_data["elements"]
        if not pass_through_service_type(elements):
            msg = error_formatter(
                GRANITE,
                INCORRECT_DATA,
                "DOCSIS Passthrough Incorrectly Requested",
                f"Design Data: {elements[0]['service_media']} {elements[0]['service_type']}",
            )
            abort(502, msg)
        return f"{elements[0]['service_media']} {elements[0]['service_type']}"

    def _get_impact_analysis_from_site(self, site_id):
        paths_on_site = granite.get_paths_from_site(site_id)
        if self.cid not in paths_on_site:
            msg = error_formatter(
                GRANITE, INCORRECT_DATA, "Circuit ID not found on site", f"Circuit: {self.cid} Site: {site_id}"
            )
            abort(502, msg, summary=get_standard_error_summary(msg))
        if len(paths_on_site) == 1:
            return "FULL"
        else:
            return "PARTIAL"

    def _get_endpoint_by_side(self, topology, side, topology_index_type, endpoint_data=None):
        indexes = FIA_TOPOLOGY_INDEXES if topology_index_type == FIA else ELINE_TOPOLOGY_INDEXES
        topology_index = indexes[side]["topology_index"]
        endpoint_index = indexes[side]["endpoint_index"]
        address_index = indexes[side]["address_index"]

        if not endpoint_data:
            endpoint_data = {
                f"{side}_endpoint": "",
                f"{side}_address": "",
                f"{side}_disconnect": "",
                "service_type": topology["serviceType"],
            }

        topology_side = topology["topology"][topology_index]["data"]["node"]

        tid = topology_side[endpoint_index]["uuid"]
        endpoint_data[f"{side}_endpoint"] = tid

        address = topology["service"][0]["data"]["evc"][0]["endPoints"][address_index].get("address")
        if not address:
            abort(502, "Missing Valid Granite Elements - Endpoint Address")
        endpoint_data[f"{side}_address"] = address

        equipment_count = granite.get_equipment_count(tid)
        if equipment_count > 2:
            endpoint_data[f"{side}_disconnect"] = "PARTIAL"
        else:
            endpoint_data[f"{side}_disconnect"] = "FULL"

        return endpoint_data

    def _create_payload(self, endpoint_data, service_type):
        post_info = {
            "label": self.cid,
            "resourceTypeId": "charter.resourceTypes.DisconnectMapper",
            "productId": product_query("DisconnectMapper"),
            "properties": {
                "circuit_id": self.cid,
                "use_alternate_circuit_details_server": False,
                "z_side_disconnect": endpoint_data["z_side_disconnect"],
                "z_side_endpoint": endpoint_data["z_side_endpoint"],
                "z_side_address": endpoint_data["z_side_address"],
            },
        }
        if endpoint_data.get("a_side_disconnect"):
            post_info["properties"]["a_side_disconnect"] = endpoint_data["a_side_disconnect"]
            post_info["properties"]["a_side_endpoint"] = endpoint_data["a_side_endpoint"]
            post_info["properties"]["a_side_address"] = endpoint_data["a_side_address"]
        if self.is_service_slm_eligible(service_type):
            post_info["properties"]["slm_eligible"] = True
        return post_info


def check_compliance(cid: str, product_name: str, network_data: dict, compliance_status: dict):
    design_data = granite.get_path_elements_for_cid(cid)
    network_compliance = NetworkDesignCompliance(cid, design_data, network_data)
    network_compliance.check_network_against_design(product_name, compliance_status)
    compliance_status.update({NETWORK_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS})


def is_valid_request(order_type):
    return "DISCONNECT" in order_type.upper()


def get_endpoint_data(network_data):
    return {
        "z_side_disconnect": network_data["properties"]["z_side_disconnect"],
        "z_side_endpoint": network_data["properties"]["z_side_endpoint"],
        "z_side_address": network_data["properties"]["z_side_address"],
        "z_side_optic_slotted": network_data["properties"].get("z_side_optic_slotted"),
        "z_side_target_wavelength": network_data["properties"].get("z_side_target_wavelength"),
        "a_side_disconnect": network_data["properties"].get("a_side_disconnect"),
        "a_side_endpoint": network_data["properties"].get("a_side_endpoint"),
        "a_side_address": network_data["properties"].get("a_side_address"),
        "a_side_optic_slotted": network_data["properties"].get("a_side_optic_slotted"),
        "a_side_target_wavelength": network_data["properties"].get("a_side_target_wavelength"),
    }


def get_order_type_by_impact_analysis(endpoint_data, order_type):
    is_full = is_full_type_present(endpoint_data)
    granite_order_type = FULL_DISCO_ORDER_TYPE if is_full else PARTIAL_DISCO_ORDER_TYPE
    # design database order type is trusted over request order type
    if granite_order_type != order_type:
        order_type = granite_order_type
    return order_type


def is_full_type_present(endpoint_data):
    return True if "FULL" in endpoint_data.values() else False


def format_response(compliance_status, order_type, legacy=False, passthrough=False):
    """
    :param compliance_status: all compliance processes + statuses
    {
    "Network Granite Compliance": "Successful",
    "IP Release Process": "Successful",
    "Path Status Update": "Successful"
    }
    :type compliance_status: dict
    :param order_type: order type
    :type order_type: str
    :return: response, status code
    :rtype: str, requests status code
    """
    if order_type == FULL_DISCO_ORDER_TYPE:
        return _full_disconnect_success_response(compliance_status, legacy, passthrough), 200
    return wrap_response_as_message(compliance_status, legacy), 200


def _full_disconnect_success_response(compliance_status, legacy, passthrough):
    """
    :param compliance_status: all compliance processes + statuses
    :type compliance_status: dict
    :return: response
    :rtype: list
    example return
    {
        "message": "PALANTIR -
        {"Network Granite Compliance": "Successful",
        "IP Release Process": "Successful",
        "Path Status Update": "Successful",
        "Site Status Update": "Successful",
        "ISP Disconnect Process": "Successful"}
        "ispRequired":
        [
            {
                'ispDisconnectTicket': 'WO1253536',
                'site': '123 Unicorn Way',
                'engineeringPage': 'ENG-4839333'},
            {
                'ispDisconnectTicket': 'WO32355288',
                'site': '334 Misty Mountain Cove',
                'engineeringPage': 'ENG-2352555'
            }
        ]
    }
    """
    if passthrough:  # no ISP in the data model if we're passing through housekeeping
        return wrap_response_as_message(compliance_status, legacy)
    isp_information = compliance_status.pop("ISP Information")
    response = wrap_response_as_message(compliance_status, legacy)
    response["ispRequired"] = isp_information
    return response


def wrap_response_as_message(compliance_status, legacy=False):
    """
    :param compliance_status: all compliance processes + statuses
    :type compliance_status: dict
    :return: response
    :rtype: dict
    """
    # 200 success: all required processes completed
    if legacy:
        compliance_status = str(compliance_status)
    response = {"message": compliance_status}
    return response


class NetworkDesignCompliance:
    def __init__(self, cid, design_data, network_data):
        self.cid = cid
        self.design_data = design_data
        self.network_data = network_data

    def check_network_against_design(self, product_name, compliance_status):
        if product_name in DISCONNECT_IP_PRODUCTS:
            # fping safety net to be super sure IP is not routing
            self._verify_fping_response(compliance_status)
        if "properties" in self.network_data:
            # fall out if key(s) present that indicate unwanted config elements remain on network
            if "configuration_found" in self.network_data["properties"]:
                resource_properties = self.network_data["properties"]
                self._abort_with_disconnect_compliance_issue(
                    resource_properties["configuration_found"], compliance_status
                )
            # if resource failed during mdso process
            if "failure_status" in self.network_data["properties"]:
                msg = f"Network: Disconnect Validation Process failed on\
                        {self.cid}: {self.network_data['properties']['failure_status']}"
                compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
                abort(502, compliance_status)
        # if we make it here, config removal is verified; delete network service in mdso if existing
        if self.network_data["properties"].get("network_service_id"):
            network_resource_id = self.network_data["properties"].get("network_service_id")
            delete_mdso_resources(self.cid, network_resource_id)

    def _verify_fping_response(self, compliance_status):
        subnets = granite.get_ip_subnets(self.cid)
        if not subnets["ipv4_assigned_subnets"] and not subnets["ipv6_assigned_subnets"]:
            err_msg = f"{self.cid} did not have any IPv4 or IPv6 addresses shown in Granite"
            compliance_status.update({"IP Release Process": err_msg})
            abort(502, compliance_status)
        ipv4_block = subnets["ipv4_assigned_subnets"]
        ipv4_glue = subnets["ipv4_glue_subnet"]
        fping_ip(ipv4_block, compliance_status)
        if ipv4_glue:
            fping_ip(ipv4_glue, compliance_status)

    def _abort_with_disconnect_compliance_issue(self, configuration_found: dict, compliance_status: dict):
        msg = "Disconnect Validation Failed"
        validation_fails = {
            "service": " - Service config",
            "port": " - Interface config",
            "slm": " - SLM config",
            "ip_routing": " - IP routing",
            "circuit_id_discovered": " - Circuit ID",
            "subinterface_configurations_discovered": " - Subinterface configurations",
            "unable_to_verify": " - Unable to verify remnant configs",
        }
        for device in configuration_found:
            config = configuration_found[device]
            for validation in validation_fails:
                if config.get(validation):
                    port = self._get_port(config[validation])
                    msg += validation_fails[validation] + f" found on {device}"
                    if port:
                        msg += f":{port}"
                    compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
                    abort(502, compliance_status)
        compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
        abort(502, compliance_status)

    def _get_port(self, port_resource):
        if port_resource not in DISCO_FAILURES_WITH_PORT:
            return
        try:
            if port_resource.get("properties"):
                port = port_resource["properties"]["data"]["id"]
            else:
                port = port_resource["data"]["id"]
            return port
        except KeyError:
            return
