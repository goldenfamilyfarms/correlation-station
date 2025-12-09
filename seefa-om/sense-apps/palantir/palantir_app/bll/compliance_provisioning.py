import logging
import re
from json import JSONDecodeError

from common_sense.common.errors import abort, error_formatter, get_standard_error_summary, SENSE, AUTOMATION_UNSUPPORTED

from palantir_app.bll.ipc import get_ip_from_tid
from palantir_app.bll.mdso import get_activating_resource_id_by_type_and_filters, get_active_resource
from palantir_app.common.compliance_utils import (
    ComplianceStages,
    NetworkCompliance,
    is_coax_voice,
    is_live_voice_change_order,
    is_shelf_swap,
    validate_network_data_exists,
)
from palantir_app.common.constants import (
    CARRIER_EACCESS_FIBER,
    CARRIER_FIA,
    CARRIER_TRANSPORT_EPL,
    CTBH,
    CHANGE_ORDER_TYPE,
    COMPLIANT,
    DDOS_PRODUCTS,
    DESIGN_COMPLIANCE_STAGE,
    ELIGIBILITY_ENDPOINT_BASE,
    EPLAN_FIBER,
    EPL_FIBER,
    EVPL_FIBER,
    EVPLAN,
    FIBER_INTERNET_ACCESS,
    HOSTED_VOICE_FIBER,
    NETWORK_COMPLIANCE_STAGE,
    NETWORK_TO_GRANITE_MODEL_MAP,
    NEW_ORDER_TYPE,
    PRI_TRUNK_FIBER,
    PRI_TRUNK_FIBER_ANALOG,
    SIP_TRUNK_FIBER,
    SIP_TRUNK_FIBER_ANALOG,
)
from palantir_app.dll import granite
from palantir_app.dll.mdso import mdso_post, product_query
from palantir_app.dll.sense import post_sense

logger = logging.getLogger(__name__)


def validate_request(request_body):
    if not request_body:
        abort(400, "Missing all required params. Please refer to swagger documentation.")
    if request_body.get("diversity"):
        msg = error_formatter(SENSE, AUTOMATION_UNSUPPORTED, "Diversity Required", "see Salesforce for details")
        abort(502, msg, summary=get_standard_error_summary(msg))
    if "CTBH" in request_body["product_name"] and "Logical Change" == request_body["order_type"]:
        msg = error_formatter(SENSE, AUTOMATION_UNSUPPORTED, "CTBH Logical Change", "see Salesforce for details")
        abort(502, msg, summary=get_standard_error_summary(msg))


class Initialize(NetworkCompliance):
    def __init__(self, cid, request, order_type):
        super().__init__(cid, request, order_type)
        self.remediate = request.get("remediation_flag", True)

    def is_pass_through(self):
        """
        Change orders that are already live indicate no network compliance required,
        no set to live required: pass through
        """
        path_data = granite.get_path_details_by_cid(self.cid, return_response=True)
        if path_data.status_code == 200:
            path_data = path_data.json()
        else:
            abort(
                502, f"Unexpected error calling Granite to determine path status. Status Code: {path_data.status_code}"
            )
        if path_data and len(path_data) == 1:
            if is_coax_voice(path_data):
                return True
            if is_live_voice_change_order(path_data, self.order_type):
                return True
        return False

    def create_service_mapper(self):
        # validate MDSO eligibility
        eligibility_endpoint = f"{ELIGIBILITY_ENDPOINT_BASE}/compliance_{self.order_type.lower()}"
        self.check_automation_eligibility(eligibility_endpoint)
        circuit_devices = granite.get_devices_from_cid(self.cid)
        if not circuit_devices:
            abort(502, "Missing Valid Granite Elements - Devices")
        circuit_service_type = circuit_devices[0]["SERVICE_TYPE"].upper()
        if circuit_service_type == "CAR-CTBH 4G":
            designed_cpes = self._remove_ctbh_core_devices(circuit_devices)
        else:
            designed_cpes = self._remove_core_devices(circuit_devices)
        if not designed_cpes:
            logger.debug(f"No devices that meet valid CPE TID within Granite data for circuit: {self.cid}")

        logger.info(f"Designed CPE data: {designed_cpes}")
        cpe_ips, cpe_swap_data = self._create_cpe_payloads(designed_cpes)

        # if there is already a compliance request processing for the same circuit, no need to recreate
        activating_resource_id = get_activating_resource_id_by_type_and_filters(
            "charter.resourceTypes.ServiceMapper", filters={"label": self.cid, "properties.circuit_id": self.cid}
        )
        if activating_resource_id:
            return {"resource_id": activating_resource_id}

        slm_data_missing, element_to_update = self._is_missing_elan_slm_data(designed_cpes)
        if slm_data_missing:
            logger.info(f"Creating ELAN SLM Data for {element_to_update['PATH_NAME']}")
            granite.create_granite_slm_data(element_to_update)

        payload = self._create_payload(cpe_ips, designed_cpes, circuit_service_type, cpe_swap_data)
        resource = mdso_post("/bpocore/market/api/v1/resources?validate=false&obfuscate=true", payload)
        return {"resource_id": resource["id"]}

    def _remove_core_devices(self, circuit_devices):
        for device in circuit_devices[:]:
            if device["VENDOR"].upper() == "JUNIPER" or not self.is_valid_cpe_tid(device["TID"].upper()):
                circuit_devices.remove(device)
        return circuit_devices

    def _remove_ctbh_core_devices(self, circuit_devices):
        for device in circuit_devices[:]:
            if device["VENDOR"].upper() == "JUNIPER" or not self.is_valid_ctbh_cpe_tid(device["TID"].upper()):
                circuit_devices.remove(device)
        return circuit_devices

    def _create_cpe_payloads(self, granite_cpe_data):
        cpe_ips = {}
        cpe_swap_data = {}
        for device in granite_cpe_data:
            tid = device["TID"].upper()
            designed_vendor = device["VENDOR"].upper()
            designed_model = device["MODEL"].upper()
            ip = get_ip_from_tid(tid, vendor=designed_vendor)
            if ip:
                cpe_ips[tid] = ip
                shelf_swap, installed_device = is_shelf_swap(ip, designed_vendor)
                if shelf_swap:
                    # best effort correct the database to reflect the network
                    self._cpe_swap_process(tid, installed_device)
                    # update cpe swap data to send to mdso for expo/data tracking later
                    cpe_swap_data[tid] = self._create_cpe_swap_data(installed_device, designed_vendor, designed_model)

        return cpe_ips, cpe_swap_data

    def _cpe_swap_process(self, tid, installed_device):
        # verify cpe swap is supported for the installed device
        self._check_cpe_swap_eligibility(installed_device["model"])
        # update granite to reflect network
        payload = {
            "cid": self.cid,
            "device_tid": tid,
            "new_model": installed_device["model"],
            "new_vendor": installed_device["vendor"],
        }
        update_cpe = post_sense(endpoint="arda/v1/cpe_swap/", payload=payload)
        if isinstance(update_cpe, str):
            abort(502, f"Error connecting to Arda CPE Swap endpoint: {update_cpe}")
        if update_cpe.status_code != 200:
            try:
                abort(502, f"Unable to swap CPE in Granite. Error: {update_cpe.json()}")
            except JSONDecodeError:
                abort(502, f"Unable to swap CPE in Granite. Error: {update_cpe.text}")

    def _check_cpe_swap_eligibility(self, cpe_model):
        """verify installed device is swappable with arda endpoint"""
        if cpe_model not in NETWORK_TO_GRANITE_MODEL_MAP.values():
            abort(
                502,
                f"CPE Swap Process Error: Installed device {cpe_model} \
                    is not eligible for shelf swap",
            )

    def _create_cpe_swap_data(self, installed_device, designed_vendor, designed_model):
        return {
            "designed": {"vendor": designed_vendor, "model": designed_model},
            "installed": {"vendor": installed_device["vendor"].upper(), "model": installed_device["model"]},
        }

    def _create_payload(self, cpe_ips, designed_cpes, service_type, cpe_swap=None):
        post_info = {
            "label": self.cid,
            "productId": product_query("Compliance"),
            "resourceTypeId": "charter.resourceTypes.Compliance",
            "properties": {
                "circuit_id": self.cid,
                "remediation_flag": self.remediate,
                "device_properties": {},
                "order_type": self.order_type,
                "compliance_type": "service",
            },
        }

        if cpe_swap:
            post_info["properties"]["cpe_swap"] = cpe_swap
            post_info["properties"]["cpe_swap_note"] = self._create_cpe_swap_note(cpe_swap)
        if self.is_service_slm_eligible(service_type):
            post_info["properties"]["slm_eligible"] = True
        for device in designed_cpes:
            post_info = self._update_device_properties(post_info, device, cpe_ips)
        return post_info

    def _create_cpe_swap_note(self, cpe_swap):
        cpe_swap_note = "ENC Automation "
        for device in cpe_swap:
            logger.debug(device)
            cpe_swap_note += (
                f"CPE SHELF SWAP on {device} "
                f"FROM {cpe_swap[device]['designed']['model']} TO {cpe_swap[device]['installed']['model']}. "
            )
        logger.debug(cpe_swap_note)
        return cpe_swap_note

    def _is_missing_elan_slm_data(self, granite_info):
        for element in granite_info:
            if "EPLAN" in element["SERVICE_TYPE"] and not granite.get_elan_slm_data(
                element["PATH_NAME"], element["CIRC_PATH_INST_ID"]
            ):
                return True, element
        return False, None

    def _update_device_properties(self, post_info, device, device_ips=None):
        post_info["properties"]["device_properties"][device["TID"]] = {"MediaType": device.get("CONNECTOR_TYPE")}
        if device_ips and device_ips.get(device["TID"]):
            post_info["properties"]["device_properties"][device["TID"]]["Management IP"] = device_ips[device["TID"]]
        return post_info


def check_compliance(
    order_data: dict,
    cid: str,
    order_type: str,
    compliance_status: dict,
    resource_id: str = None,
    network_data: dict = None,
):
    design_data = granite.get_path_elements_for_cid(cid)
    order_design_compliance = OrderDesignCompliance(order_type, design_data, order_data)
    if order_design_compliance.is_required():
        logger.debug("performing order-design compliance")
        design_compliance = order_design_compliance.check_design_against_order(compliance_status)
        if design_compliance["result"] == "fail":
            compliance_status.update({DESIGN_COMPLIANCE_STAGE: design_compliance["errors"]})
        compliance_status.update({DESIGN_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS})

    network_compliance = NetworkDesignCompliance(cid, design_data, resource_id=resource_id, network_data=network_data)
    network_compliance.check_network_against_design(compliance_status)
    compliance_status.update({NETWORK_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS})
    compliance_status.update({COMPLIANT: True})


def is_valid_request(order_type):
    return NEW_ORDER_TYPE in order_type.upper() or CHANGE_ORDER_TYPE in order_type.upper()


class OrderDesignCompliance:
    def __init__(self, order_type, design_data, order_data):
        self.order_type = order_type
        self.design_data = design_data
        self.order_data = order_data

    def is_required(self):
        return self.order_type == NEW_ORDER_TYPE

    def check_design_against_order(self, compliance_status: dict):
        if not self.design_data:
            compliance_status.update({DESIGN_COMPLIANCE_STAGE: "Missing Valid Granite Elements"})
            abort(502, compliance_status)

        # convert order request data to standard for design database
        translated_product = self._translate_order_product_to_design_product()
        if not translated_product:
            msg = (
                f"Unsupported Product and Handoff Type: {self.order_data['product_name']} {self.order_data['uni_type']}"
            )
            compliance_status.update({DESIGN_COMPLIANCE_STAGE: msg})
            abort(502, compliance_status)
        self.order_data["product_name"] = translated_product

        errors = []
        for record in self.design_data:
            product_check = self._check_product_name(record["SERVICE_TYPE"])
            connector_check = self._check_connector_type(record)
            compliance_results = [product_check, connector_check]
            if self._ip_check_required():
                ipv4_check = self._check_ipv4(record)
                dia_svc_type_check = self._check_dia_svc_type(record)
                compliance_results += [ipv4_check, dia_svc_type_check]
            if self._bw_check_required():
                bandwidth_check = self._check_bandwidth(record["BANDWIDTH"])
                compliance_results += [bandwidth_check]
            error_results = [result["error"] for result in compliance_results if result["error"]]
            errors += error_results

        if errors:
            return {"result": "fail", "errors": errors}

        return {"result": "pass"}

    def _check_retain_ip_address(self):
        if "retain_ip_address" in self.order_data and self.order_data["retain_ip_address"] is not None:
            return self.order_data["retain_ip_address"].lower() == "yes"
        else:
            return False

    def _translate_order_product_to_design_product(self):
        supported_products = {
            "Access": {
                FIBER_INTERNET_ACCESS: "COM-DIA",
                EPL_FIBER: "COM-EPL",
                CARRIER_EACCESS_FIBER: "CAR-E-ACCESS FIBER/FIBER EPL",
                CARRIER_TRANSPORT_EPL: "CAR-E-TRANSPORT FIBER/FIBER EPL",
                CARRIER_FIA: "CAR-DIA",
                PRI_TRUNK_FIBER: "CUS-VOICE-PRI",
                PRI_TRUNK_FIBER_ANALOG: "CUS-VOICE-PRI",
                SIP_TRUNK_FIBER: "CUS-VOICE-SIP",
                SIP_TRUNK_FIBER_ANALOG: "CUS-VOICE-SIP",
                HOSTED_VOICE_FIBER: "CUS-VOICE-HOSTED",
                EPLAN_FIBER: "COM-EPLAN",
            },
            "Trunked": {
                CARRIER_EACCESS_FIBER: "CAR-E-ACCESS FIBER/FIBER EVPL",
                EVPL_FIBER: "COM-EVP",
                PRI_TRUNK_FIBER: "CUS-VOICE-PRI",
                PRI_TRUNK_FIBER_ANALOG: "CUS-VOICE-PRI",
                SIP_TRUNK_FIBER: "CUS-VOICE-SIP",
                SIP_TRUNK_FIBER_ANALOG: "CUS-VOICE-SIP",
                EVPLAN: "COM-EPLAN",
                CTBH: "CAR-CTBH 4G",
            },
            "N/A": {  # we don't mind not knowing the UNI type for these products
                PRI_TRUNK_FIBER: "CUS-VOICE-PRI",
                PRI_TRUNK_FIBER_ANALOG: "CUS-VOICE-PRI",
                SIP_TRUNK_FIBER: "CUS-VOICE-SIP",
                SIP_TRUNK_FIBER_ANALOG: "CUS-VOICE-SIP",
                HOSTED_VOICE_FIBER: "CUS-VOICE-HOSTED",
            },
        }
        if self.order_data["product_name"] in DDOS_PRODUCTS:
            # DDoS products get a pass on UNI type but are represented as FIA in Granite
            return "COM-DIA"
        try:
            translated_product = supported_products[self.order_data["uni_type"]][self.order_data["product_name"]]
            return translated_product
        except (KeyError, TypeError):
            return ""

    def _check_product_name(self, design_product):
        result = {"error": None}
        order_product = self.order_data["product_name"]
        if self._normalize_product_name(order_product) != self._normalize_product_name(design_product):
            result["error"] = f"product name match failed, design: {design_product} order: {order_product}"
            return result
        return result

    def _normalize_product_name(self, product_name):
        if self._is_null_value(product_name):
            return ""
        # TODO will need to update here when FIA goes back to being DIA
        pattern = re.compile(r"-{0,1}\s?DIA|-{0,1}\s?DIRECT INTERNET ACCESS|-{0,1}\s?FIBER INTERNET ACCESS")
        retstr = pattern.sub(r"FIA", str(product_name).upper())
        pattern = re.compile(r"\s?CARRIER\s?")
        retstr = pattern.sub(r"CAR", retstr.upper())

        pattern = re.compile(r"\s?COMMERCIAL\s?")
        retstr = pattern.sub(r"COM", retstr.upper())

        # if there is no qualifying network specified, it is presumed Commercial
        pattern = re.compile(r"^\s?FIA\s?$")
        retstr = pattern.sub(r"COMFIA", retstr.upper())

        return retstr.strip()

    def _is_null_value(self, data):
        return not data or len(data) == 0 or data.lower().strip() in ("none", "null")

    def _check_connector_type(self, record):
        order_connector = self.order_data["connector_type"]
        result = {"error": None}
        if self._connector_check_not_required(record["SERVICE_TYPE"]):
            return result
        design_connector = self._normalize_connector_type(record["CONNECTOR_TYPE"])
        order_connector = self._normalize_connector_type(order_connector)
        if not design_connector:
            if not order_connector:
                return result
            result["error"] = f"connector type match failed, design: None order: {order_connector}"
            return result
        if self._is_cpe_element(record["TID"], record["ELEMENT_TYPE"]) and design_connector != order_connector:
            result["error"] = f"connector type match failed, design: {design_connector} order: {order_connector}"
            return result
        return result

    def _connector_check_not_required(self, service_type):
        return "VOICE" in service_type

    def _normalize_connector_type(self, connector_type):
        if self._is_null_value(connector_type):
            return ""
        return connector_type.lower().replace("-", "")

    def _is_cpe_element(self, device_tid, element_type):
        return re.match(".{9}[WXYZ]W", device_tid.upper()) and "TRANSPORT" not in element_type

    def _ip_check_required(self):
        return "ipv4" in self.order_data or "ip_address" in self.order_data

    def _check_ipv4(self, record):
        result = {"error": None}
        retain_ip_address = self._check_retain_ip_address()
        if not self._is_cpe_element(record["TID"], record["ELEMENT_TYPE"]):
            result["error"] = f"design transport element is missing for TID: {record['TID']}"
            return result

        design_cidr = "EMPTY"
        design_ip = ""
        if re.search("/", record["IPV4_ASSIGNED_SUBNETS"]):
            design_cidr = "/" + record["IPV4_ASSIGNED_SUBNETS"].split("/")[1]
            design_ip = record["IPV4_ASSIGNED_SUBNETS"].split("/")[0]
        if design_cidr == "EMPTY" and re.search("/", record["IPV4_ADDRESS"]):
            design_cidr = "/" + record["IPV4_ADDRESS"].split("/")[1]
            design_ip = record["IPV4_ADDRESS"].split("/")[0]
        if design_cidr == "EMPTY":
            result["error"] = "design subnet CIDR notation is missing"
            return result

        order_cidr = ""
        if retain_ip_address:
            order_ip = self.order_data["ip_address"].split("/")[0]
            if re.search("/", self.order_data["ip_address"]):
                order_cidr = "/" + self.order_data["ip_address"].split("/")[1]
            if design_ip != order_ip:
                result["error"] = f"IP address match failed, design: {design_ip} order: {order_ip}"
                return result
        else:
            order_ip = self.order_data["ipv4"]
            order_cidr = order_ip.split("=")[0]

        if design_cidr != order_cidr:
            result["error"] = f"subnet CIDR notation match failed, design: {design_cidr} order: {order_cidr}"
            return result

        return result

    def _check_dia_svc_type(self, record):
        order_svc_type = self.order_data["dia_svc_type"]
        result = {"error": None}
        if self._is_cpe_element(record["TID"], record["ELEMENT_TYPE"]):
            design_svc_type = record["IPV4_SERVICE_TYPE"]
            if self._is_null_value(design_svc_type):
                result["error"] = "design missing ipv4 service type"
                return result
            design_svc_type = self._normalize_data(design_svc_type)
            order_svc_type = self._normalize_data(order_svc_type)
            if design_svc_type != order_svc_type:
                result["error"] = f"order service type match failed, design: {design_svc_type}, order: {order_svc_type}"
                return result
            ipv4_glue = record.get("IPV4_GLUE_SUBNET")
            if self._lan_service_has_routed_ips(order_svc_type, ipv4_glue):
                result["error"] = f"design has no glue IP value; order {order_svc_type} is not LAN service type"
                return result
            if self._routed_service_missing_routed_ips(order_svc_type, ipv4_glue):
                result["error"] = (
                    f"design has glue IP {record['IPV4_GLUE_SUBNET']}; "
                    "order must specify ROUTED service type,"
                    f"currently {order_svc_type}"
                )
        return result

    def _normalize_data(self, data):
        return data.lower().strip()

    def _lan_service_has_routed_ips(self, order_svc_type, ipv4_glue):
        return order_svc_type == "lan" and ipv4_glue is not None

    def _routed_service_missing_routed_ips(self, order_svc_type, ipv4_glue):
        return order_svc_type == "routed" and not ipv4_glue

    def _bw_check_required(self):
        return "bandwidth" in self.order_data and self.order_data["bandwidth"]

    def _check_bandwidth(self, design_bandwidth):
        order_bandwidth = self.order_data["bandwidth"]
        result = {"error": None}
        if self._normalize_data(design_bandwidth) != self._normalize_data(order_bandwidth):
            result["error"] = f"bandwidth match failed, design: {design_bandwidth}, order: {order_bandwidth}"
        return result


class NetworkDesignCompliance:
    NAME_DELIMITER = r"@"
    ADDRESS_DELIMITER = r":.*"

    def __init__(self, cid, design_data, resource_id=None, network_data=None):
        self.cid = cid
        self.design_data = design_data
        if resource_id and not network_data:
            network_data = get_active_resource(resource_id)
        self.network_data = network_data
        self.resource_id = resource_id

    def check_network_against_design(self, compliance_status):
        validate_network_data_exists(compliance_status, resource_id=self.resource_id, network_data=self.network_data)
        network_design_differences = self.network_data["properties"].get("service_differences")
        slm_traffic_passing = self.network_data["properties"].get("slm_traffic_passing", True)
        order_design_differences = self.are_design_order_differences(compliance_status)
        # if any compliancy issues, fall out
        if network_design_differences or slm_traffic_passing is False or order_design_differences:
            self._abort_with_compliance_issue(compliance_status, network_design_differences, slm_traffic_passing)
        if "failure_status" in self.network_data["properties"]:
            failure_status = self.network_data["properties"]["failure_status"]
            if "device_ips" in self.network_data["properties"]:
                failure_status = str(failure_status) + str(self.network_data["properties"]["device_ips"])
            msg = f"Network - Service Map Validation Failed: {failure_status} - {self.cid}"
            compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
            abort(502, compliance_status)

    def are_design_order_differences(self, compliance_status: dict):
        if compliance_status.get(DESIGN_COMPLIANCE_STAGE) == ComplianceStages.SUCCESS_STATUS:
            # order-design compliant
            return False
        if compliance_status.get(DESIGN_COMPLIANCE_STAGE) is None:
            # order-design compliance not required
            return False
        # order-design required and not compliant
        return True

    def _abort_with_compliance_issue(self, compliance_status, differences=None, slm_traffic_passing=True):
        msg = {}
        if not slm_traffic_passing:
            msg["slm_issue"] = True
        if differences:
            noncompliant_devices = differences.keys()
            if not noncompliant_devices:
                msg["compliance_issue"] = "No devices found in network design differences"
            else:
                msg["compliance_issue"] = differences
        compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
        abort(502, message=compliance_status)
