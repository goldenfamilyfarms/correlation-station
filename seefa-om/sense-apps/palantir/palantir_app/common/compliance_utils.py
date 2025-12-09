import copy
import logging
import re

from requests import JSONDecodeError

from common_sense.common.errors import abort, format_unsupported_service_error, format_unsupported_equipment_error
from palantir_app.common.constants import (
    CHANGE_ORDER_TYPE,
    DESIGN_COMPLIANCE_STAGE,
    DOCSIS_CHANGE_ORDER_TYPE,
    DOCSIS_NEW_ORDER_TYPE,
    DOCSIS_PREFIX,
    ELIGIBLE_SLM_SERVICES,
    ENGINEERING_JOB_TYPES,
    FIA_PRODUCTS,
    FULL_DISCO_ORDER_TYPE,
    IP_DISCONNECT_STAGE,
    ISP_STAGE,
    NETWORK_COMPLIANCE_STAGE,
    NEW_ORDER_TYPE,
    ORDER_TYPES,
    PARTIAL_DISCO_ORDER_TYPE,
    PASS_THROUGH,
    PATH_STATUS_STAGE,
    REQUIRED_ORDER_DATA,
    SALESFORCE_PRODUCT_NAMES,
    SITE_STATUS_STAGE,
    STATE_ABBREVIATIONS,
    WIA_ORDER_TYPE,
)
from palantir_app.dll.granite import granite_get
from palantir_app.dll.sense import sense_get
from palantir_app.common.endpoints import GRANITE_PATH_CHAN_AVAILABILITY

logger = logging.getLogger(__name__)


class ComplianceStages:
    NOT_PERFORMED_STATUS = "Not Performed"
    READY_STATUS = "Ready to Initiate"
    SUCCESS_STATUS = "Successful"
    PASS_THROUGH_STATUS = "Passed Through"  # noqa: S105

    def __init__(self, order_type, product_name="", housekeeping_only=False):
        self.order_type = order_type
        self.product_name = product_name
        self.housekeeping_only = housekeeping_only
        self.set_status()

    COMPLIANCE_STAGES = {
        NEW_ORDER_TYPE: {
            DESIGN_COMPLIANCE_STAGE: READY_STATUS,
            NETWORK_COMPLIANCE_STAGE: NOT_PERFORMED_STATUS,
            PATH_STATUS_STAGE: NOT_PERFORMED_STATUS,
        },
        CHANGE_ORDER_TYPE: {NETWORK_COMPLIANCE_STAGE: READY_STATUS, PATH_STATUS_STAGE: NOT_PERFORMED_STATUS},
        PARTIAL_DISCO_ORDER_TYPE: {
            NETWORK_COMPLIANCE_STAGE: READY_STATUS,
            IP_DISCONNECT_STAGE: NOT_PERFORMED_STATUS,
            PATH_STATUS_STAGE: NOT_PERFORMED_STATUS,
        },
        FULL_DISCO_ORDER_TYPE: {
            NETWORK_COMPLIANCE_STAGE: READY_STATUS,
            IP_DISCONNECT_STAGE: NOT_PERFORMED_STATUS,
            ISP_STAGE: NOT_PERFORMED_STATUS,
            PATH_STATUS_STAGE: NOT_PERFORMED_STATUS,
            SITE_STATUS_STAGE: NOT_PERFORMED_STATUS,
        },
        DOCSIS_NEW_ORDER_TYPE: {PATH_STATUS_STAGE: READY_STATUS},
        DOCSIS_CHANGE_ORDER_TYPE: {PATH_STATUS_STAGE: READY_STATUS},
        WIA_ORDER_TYPE: {DESIGN_COMPLIANCE_STAGE: READY_STATUS, NETWORK_COMPLIANCE_STAGE: NOT_PERFORMED_STATUS},
    }

    HOUSEKEEPING_STAGES = {
        NEW_ORDER_TYPE: {PATH_STATUS_STAGE: READY_STATUS},
        CHANGE_ORDER_TYPE: {PATH_STATUS_STAGE: READY_STATUS},
        PARTIAL_DISCO_ORDER_TYPE: {IP_DISCONNECT_STAGE: READY_STATUS, PATH_STATUS_STAGE: NOT_PERFORMED_STATUS},
        FULL_DISCO_ORDER_TYPE: {
            IP_DISCONNECT_STAGE: READY_STATUS,
            ISP_STAGE: NOT_PERFORMED_STATUS,
            PATH_STATUS_STAGE: NOT_PERFORMED_STATUS,
            SITE_STATUS_STAGE: NOT_PERFORMED_STATUS,
        },
        DOCSIS_NEW_ORDER_TYPE: {PATH_STATUS_STAGE: READY_STATUS},
        DOCSIS_CHANGE_ORDER_TYPE: {PATH_STATUS_STAGE: READY_STATUS},
    }

    def set_status(self):
        compliance_stages = self.HOUSEKEEPING_STAGES if self.housekeeping_only else self.COMPLIANCE_STAGES
        compliance_status = copy.deepcopy(compliance_stages[self.order_type])
        if (
            "DISCONNECT" in self.order_type
            and self.product_name not in FIA_PRODUCTS
            and compliance_status.get(IP_DISCONNECT_STAGE)
        ):
            del compliance_status[IP_DISCONNECT_STAGE]
        self.status = compliance_status

    def set_next_stage_to_ready(self):
        for state in self.status:
            if self.status[state] == self.NOT_PERFORMED_STATUS:
                self.status[state] = self.READY_STATUS
                break

    def set_pass_through_status(self):
        last_stage = list(self.status)[-1]
        for state in self.status:
            if state == last_stage:
                self.status[state] = self.READY_STATUS
            else:
                self.status[state] = self.PASS_THROUGH_STATUS


class NetworkCompliance:
    def __init__(self, cid, request, order_type):
        self.request = request
        self.cid = self.check_multiple_cids(cid)
        if order_type in (DOCSIS_NEW_ORDER_TYPE, DOCSIS_CHANGE_ORDER_TYPE):
            order_type = order_type.lstrip(DOCSIS_PREFIX).strip()
        self.order_type = order_type
        logger.debug(f"{self.order_type = }")

    def check_automation_eligibility(self, eligibility_endpoint):
        eligibility = sense_get(eligibility_endpoint, params={"circuit_id": self.cid}, return_response=True)
        try:
            eligibility = eligibility.json()
        except JSONDecodeError:
            msg = f"Eligibility JSON Decode Error. Response: {eligibility} {eligibility.text}"
            logger.debug(msg)
            abort(501, msg)
        if isinstance(eligibility, dict):
            error_key = None
            if eligibility.get("error"):
                error_key = "error"
            if eligibility.get("message"):
                error_key = "message"
            msg = eligibility[error_key] if error_key else eligibility
            logger.debug(f"Issue Determining Automation Eligibility: {msg}")
            abort(501, msg, summary=eligibility.get("summary"))
        for evaluation in eligibility:
            if not evaluation["eligible"]:
                data = evaluation["data"]
                workstream = f"Compliance {self.order_type.capitalize()}"
                if data.get("unsupportedService"):
                    msg = format_unsupported_service_error(data["unsupportedService"], workstream)
                    abort(501, msg)
                elif data.get("unsupportedEquipment"):
                    msg = format_unsupported_equipment_error(data["unsupportedEquipment"], workstream)
                    abort(501, msg)
                logger.debug(f"MDSO Automation Unsupported - {data}")
                abort(501, data)

    def is_valid_cpe_tid(self, tid):
        if len(tid) != 11:
            return False
        state_abbreviation = tid[4:6]
        if state_abbreviation not in STATE_ABBREVIATIONS:
            return False
        if not re.match("[WXYZ]W", tid[9:11]):
            return False
        else:
            return True

    def is_valid_ctbh_cpe_tid(self, tid):
        non_cpe_tids = ["TW", "QW", "CW", "AW", "LT"]
        if len(tid) != 11:
            return False
        state_abbreviation = tid[4:6]
        if state_abbreviation not in STATE_ABBREVIATIONS:
            return False
        if tid[9:11] in non_cpe_tids:
            return False
        else:
            return True

    def is_service_slm_eligible(self, service_type):
        # service type should be either from Granite or beorn/v3/topologies
        return service_type in ELIGIBLE_SLM_SERVICES

    def check_multiple_cids(self, cid):
        cid_regex = r"(\d{2}\.[A-Z0-9]{4}\.\d{6}\.[A-Z0-9]{0,3}\.[TWCC|CHTR]{4})"
        if len(cid) > 23 and " " in cid:
            try:
                cid = re.findall(cid_regex, cid)[0]
            except IndexError:
                logger.debug(f"No valid CID found in {cid}")
        return cid


def translate_sf_order_type(sf_order, product_name):
    for order_type in ORDER_TYPES:
        if sf_order.upper() in ORDER_TYPES[order_type]:
            return f"{DOCSIS_PREFIX}{order_type}" if "DOCSIS" in product_name else order_type
    return sf_order


def translate_eng_job_type(eng_job_type, product_name=""):
    for order_type, job_types in ENGINEERING_JOB_TYPES.items():
        if eng_job_type in job_types:
            return f"{DOCSIS_PREFIX}{order_type}" if "DOCSIS" in product_name else order_type
    return eng_job_type


def is_compliance_required(resource_id):
    # we have no visibility to DOCSIS network, skip compliance
    return resource_id != PASS_THROUGH


def get_required_order_details(product_name, order_data, order_type=NEW_ORDER_TYPE):
    # determine salesforce values required for processing compliance
    # based on order type and product type
    product = translate_sf_product_name(product_name)
    required_data = {"product_name": product}
    if REQUIRED_ORDER_DATA.get(order_type):
        required_data = copy.deepcopy(REQUIRED_ORDER_DATA[order_type].get(product, required_data))
    return add_data_from_order(required_data, order_data)


def translate_sf_product_name(product_name):
    for product_family in SALESFORCE_PRODUCT_NAMES:
        if product_name in product_family:
            return SALESFORCE_PRODUCT_NAMES[product_family]
    return product_name


def add_data_from_order(required_data, order_data):
    retain_ip_address = False
    if "retain_ip_address" in order_data and order_data["retain_ip_address"] is not None:
        retain_ip_address = order_data["retain_ip_address"].lower() == "yes"

    for service_detail in required_data.keys():
        if not retain_ip_address:
            if service_detail not in order_data:
                abort(400, f"Bad request - Missing Input Data - {service_detail}")
            else:
                required_data[service_detail] = order_data[service_detail]
        else:
            if service_detail != "ipv4" and service_detail not in order_data:
                abort(400, f"Bad request - Missing Input Data - {service_detail}")
            elif service_detail == "ipv4" and "ip_address" not in order_data:
                abort(400, f"Bad request - Missing Input Data - {service_detail}")
            elif service_detail == "ipv4" and "ip_address" in order_data:
                required_data[service_detail] = order_data["ip_address"]
            else:
                required_data[service_detail] = order_data[service_detail]

    return required_data


def validate_network_data_exists(compliance_status, resource_id=None, network_data=None):
    if not resource_id and not network_data:
        abort(400, "Unable to retrieve network data. No resource ID provided.")
    if not network_data:
        msg = f"Invalid MDSO resource - Resource ID: {resource_id}"
        compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
        abort(502, compliance_status)
    if "properties" not in network_data:
        compliance_status.update({NETWORK_COMPLIANCE_STAGE: "Unable to retreive network data from MDSO"})
        abort(502, compliance_status)


def is_shelf_swap(ip, granite_vendor):
    """Returns info for a device based on ip or tid"""
    if not ip:
        return None, None
    installed_device = sense_get("beorn/v1/device", params={"ip": ip}, best_effort=True)

    # if model or vendor is none, skip swap effort and let MDSO try
    if not installed_device.get("model"):
        logger.error("CPE Swap Verification Error: Unable to obtain installed device's model from SNMP")
        return False, None
    if not installed_device.get("vendor"):
        logger.error(
            f"CPE Swap Verification Error: Installed device {ip} {installed_device['model']} \
            is not mapped to a vendor yet"
        )
        return False, None

    if installed_device["vendor"] != granite_vendor:
        return True, installed_device
    else:
        return False, installed_device


def get_pri_trunks(cid: str, live_only: bool = True):
    data = []
    payload = {"PATH_NAME": cid}
    pri_trunks = granite_get(GRANITE_PATH_CHAN_AVAILABILITY, params=payload, return_response_obj=True)
    if pri_trunks.status_code == 200:
        pri_trunks = pri_trunks.json()
        if "retString" in pri_trunks:
            return {}
        else:
            for trunk in pri_trunks:
                if live_only and trunk.get("NEXT_PATH"):
                    data.append((trunk["NEXT_PATH"], trunk["PATH_REV"]))
                elif not live_only and trunk.get("MEMBER_PATH"):
                    data.append((trunk["MEMBER_PATH"], trunk["PATH_REV"]))
            return data
    else:
        return {}


def is_coax_voice(path_data):
    return "COAX" in path_data[0]["serviceMedia"] and "VOICE" in path_data[0]["product_Service_UDA"]


def is_coax_voice_model(path_data):
    if path_data[0].get("service_media") and path_data[0].get("service_type"):
        if path_data[0]["service_media"] == "COAX" and path_data[0]["service_type"] == "VOICE-HOST":
            return False
        return "COAX" in path_data[0]["service_media"] and "VOICE" in path_data[0]["service_type"]
    else:
        return False


def pass_through_service_type(path_data):
    if path_data[0].get("service_media") and path_data[0].get("service_type"):
        if "INTERNET A" in path_data[0]["service_type"]:
            return "5G" in path_data[0]["service_media"] or "LTE" in path_data[0]["service_media"]
        if "VOICE" in path_data[0]["service_type"]:
            return "COAX" in path_data[0]["service_media"]
    else:
        return False


def is_live_voice_change_order(path_data, order_type):
    logger.debug(f"Path status: {path_data[0]['status']} Order Type: {order_type}")
    return (
        path_data[0]["status"] == "Live"
        and "VOICE" in path_data[0]["product_Service_UDA"]
        and CHANGE_ORDER_TYPE in order_type
    )


def is_live(path_status):
    logger.debug(f"path STATUSSS {path_status}")
    return path_status == "Live"
