import ipaddress
import logging
import paramiko
import re
import socket

import beorn_app

from beorn_app.common.generic import (
    ADVA,
    ALCATEL,
    CISCO,
    RAD,
    JUNIPER,
    NOKIA,
    FIA,
    ELAN,
    ELINE,
    ELINE_SEGMENT,
    CTBH,
    BIT,
    KILOBIT,
    MEGABIT,
    GIGABIT,
    TERABIT,
    PETABIT,
)
from common_sense.common.errors import abort
from beorn_app.bll.ip_finder import ip_finder
from beorn_app.bll.snmp import (
    get_firmware,
    get_device_vendor_and_model,
    get_system_info,
    compare_version,
    _isolate_model,
    _get_vendor_by_model,
)
from beorn_app.dll.granite import granite_get
from beorn_app.dll.ipc import get_ip_from_tid
from beorn_app.bll.eligibility.circuit_test import PalantirConnector
from beorn_app.common.endpoints import DICE_CIRCUIT_TOPOLOGY
from beorn_app.bll.eligibility.circuit_test import get_pe_details

PALANTIR_URL = f"{beorn_app.url_config.SENSE_BASE_URL}/palantir"

logger = logging.getLogger(__name__)

FIRMWARE = "Firmware"
BANDWIDTHLIMIT = "BANDWIDTHLIMIT"

# Circuit Tests Supported Firmware
L2YG = "L2 Y.1564 Generator"
L2LB = "L2 Loopback Function"
L3LB = "L3 Loopback Function"
MFLG = "Multi-flow Generation"
MFLR = "Multi-flow Reflection"

SERVICE_TYPE_PATH = {
    FIA: ["DIA", "MSS DIA", "SECURE INT", "FIA"],
    ELAN: ["EPLAN", "EVPLAN"],
    ELINE: ["EPL", "EVPL", "ELINE"],
    ELINE_SEGMENT: ["E-ACCESS F"],
    CTBH: ["CTBH", "CTBH 4G"],
}

ELIGIBLE_SERVICE_TYPES = ["DIA", "MSS DIA", "SECURE INT", "EPL", "E-ACCESS F"]

# Circuits like TWCC have a cpe with device role A
CPE_ROLES = ["A", "Z"]
PE_ROLES = ["C"]
QFX_ROLES = ["Q"]

# This is the model format that visionworks is expecting.
NORMALIZE_MODEL = {
    ADVA: [
        "GE114",
        "GE114PRO",
        "GE116PRO",
        "XG116PRO",
        "XG108",
        "XG118PRO",  # Not confirmed by visionworks team
        "XO106",
    ],
    RAD: ["220", "203", "2I"],
    CISCO: ["920"],
    JUNIPER: ["MX240", "MX480", "MX960"],  # MX480 and MX960 naming convention not confirmed
}

# https://chalk.charter.com/display/public/SLM/Spirent+VisionWorks+Conductor
SUPPORTED_VISIONWORKS_DEVICES = {
    ADVA: {
        "GE114": {
            BANDWIDTHLIMIT: 1 * GIGABIT,
            FIRMWARE: {ELINE: {L2YG: "10.5.2", L2LB: "7.1.4+"}, FIA: {L3LB: "11.1.2-123"}},
        },  # "TWAMP": {TWPG: "11.1.2 0.123", TWPR: "11.1.2 0.123"}
        "GE114PRO": {
            BANDWIDTHLIMIT: 1 * GIGABIT,
            FIRMWARE: {ELINE: {L2YG: "10.5.3", L2LB: "10.5.3"}, FIA: {L3LB: "11.6.1"}},
        },  # "TWAMP": {TWPG: "11.6.1+", TWPR: "11.6.1+"}
        "GE116PRO": {
            BANDWIDTHLIMIT: 10 * GIGABIT,
            FIRMWARE: {
                ELINE: {L2YG: "10.5.3", L2LB: "10.5.3", MFLG: "13.7.1", MFLR: "11.6.1"},
                FIA: {L3LB: "11.6.1", MFLG: "13.7.1", MFLR: "11.6.1"},
            },
        },  # "TWAMP": {TWPG: "11.6.1+", TWPR: "11.6.1+"}
        "XG116PRO": {
            BANDWIDTHLIMIT: 10 * GIGABIT,
            FIRMWARE: {
                ELINE: {L2YG: "10.5.3", L2LB: "10.5.3", MFLG: "13.7.1", MFLR: "11.6.1"},
                FIA: {L3LB: "11.6.1", MFLG: "13.7.1", MFLR: "11.6.1"},
            },
        },  # "TWAMP": {TWPG: "11.6.1+", TWPR: "11.6.1+"}
        "XG108": {
            BANDWIDTHLIMIT: 10 * GIGABIT,
            FIRMWARE: {ELINE: {L2YG: "11.6.1", L2LB: "11.6.1"}, FIA: {L3LB: "11.6.1"}},
        },  # "TWAMP": {TWPG: "11.6.1", TWPR: "11.6.1"}
        "XO106": {
            BANDWIDTHLIMIT: 10 * GIGABIT,
            FIRMWARE: {ELINE: {L2YG: "11.6.1", L2LB: "11.6.1"}, FIA: {L3LB: "11.6.1"}},
        },  # "TWAMP": {TWPG: "11.6.1", TWPR: "11.6.1"}
    },
    RAD: {
        "220": {
            BANDWIDTHLIMIT: 10 * GIGABIT,
            FIRMWARE: {
                ELINE: {L2YG: "6.4.0 0.86", L2LB: "6.4.0 0.86", MFLR: "6.4.0 0.91"},
                FIA: {L3LB: "6.4.0(0.86)", MFLR: "6.4.0(0.91)"},
            },
        },  # "TWAMP": {TWPG: "6.4.0 0.86", TWPR: "6.4.0 0.86"}
        "203": {
            BANDWIDTHLIMIT: 1 * GIGABIT,
            FIRMWARE: {ELINE: {L2YG: "6.4.0 0.86", L2LB: "6.4.0 0.86"}, FIA: {L3LB: "6.4.0(0.86)"}},
        },  # "TWAMP": {TWPG: "6.4.0 0.86", TWPR: "6.4.0 0.86"}
        "2I": {
            BANDWIDTHLIMIT: 10 * GIGABIT,
            FIRMWARE: {
                ELINE: {L2YG: "6.4.0 0.86", L2LB: "6.4.0 0.86", MFLR: "6.4.0 0.91"},
                FIA: {L3LB: "6.4.0(0.86)", MFLR: "6.4.0(0.91)"},
            },
        },  # "TWAMP": {TWPG: "6.4.00.86", TWPR: "6.4.0 0.86"}
    },
    CISCO: {
        # "920": {BANDWIDTHLIMIT: 1 * GIGABIT, FIRMWARE: {ELINE: {L2LB: "16.05.01"}}}
    },
}

E_ACCESS_FIBER_SUPPORTED_PE = {JUNIPER: {"MX204": {}, "MX240": {}, "MX480": {}, "MX960": {}}}

CTBH_SUPPORTED_PE = {ALCATEL: {"7750SR": {}}, NOKIA: {"7750SR": {}}}

# These names keep the splunk logging consistent
ELIGIBLE = "Eligible"
INELIGIBLE = "Ineligible"
UNDETERMINED = "Failed"

FAILED_RETRIEVAL = "Failed to retrieve"
FAILED_DETERMINATION = "Failed to determine eligibility"


class Eligibility:
    def __init__(
        self,
        circuit_id,
        cpe_ip_address=False,
        allow_ctbh=False,
        cap_eline_bandwidth=True,
        check_ssh="",
        username="",
        fastpath_only: bool = False,
        cpe_planned_ineligible: bool = False,
    ):
        self.circuit_id = circuit_id
        self.cpe_ip_address = cpe_ip_address
        self.allow_ctbh = allow_ctbh
        self.cap_eline_bandwidth = cap_eline_bandwidth
        self.check_ssh = check_ssh
        self.username = username
        self.fastpath_only = fastpath_only
        self.cpe_planned_ineligible = cpe_planned_ineligible
        self.common_eligible_tests = []
        self._log_initialization()
        self._set_base_response()

    def _log_initialization(self):
        logger.info(
            f"method=GET | Beorn_Endpoint=Eligibility Circuit Testing | {f'Username={self.username} | '}"
            + f"Circuit_ID={self.circuit_id} | CPE_IP_Address={self.cpe_ip_address} | "
            + f"Allow_CTBH={self.allow_ctbh} | Cap_ELINE_Bandwidth={self.cap_eline_bandwidth} | "
            + f"Check_SSH={self.check_ssh} | Username={self.username} | State=Started"
        )

    def _set_base_response(self):
        self.response = {"circuit_test_eligible": False, "warning": [], "failure_reason": ""}

    def check_automation_eligibility(self):
        # Fetch Granite Data
        granite_data_elements = self.get_granite_data()
        if not granite_data_elements:
            return self.response, 500

        if "CTBH" in granite_data_elements[0].get("service_type", ""):
            return self.check_automation_eligibility_ctbh(granite_data_elements)
        # In the event of an upgrade there will be two elements. The old 'Live' circuit and the new
        # 'Designed' circuit. The 'Designed' circuit is what should be deployed on the network.
        # It will be set to 'Live' once it has completed compliance testing.
        eligibility_attempts = []
        for index, element in enumerate(granite_data_elements):
            eligible, status_code = self._is_eligible(element)
            if eligible:
                if index > 0:
                    self.response["warning"].append(
                        f"Topology Element '{index}' {element.get('status')} used for eligibility."
                    )
                    self.response["warning"].append({"element_attempts": eligibility_attempts})
                return self.response, status_code
            else:
                eligibility_attempts.append(self.response.get("failure_reason"))
        if len(granite_data_elements) > 1:
            self.response["warning"].append({"element_attempts": eligibility_attempts[:-1]})
        return self.response, status_code

    def check_automation_eligibility_by_leg(self, granite_data_elements) -> list[dict]:
        eligibility_by_leg = []

        # In the event of an upgrade there will be two elements. The old 'Live' circuit and the new
        # 'Designed' circuit. The 'Designed' circuit is what should be deployed on the network.
        # It will be set to 'Live' once it has completed compliance testing.
        for element in granite_data_elements:
            _, status_code = self._is_eligible(element)
            self.response["status_code"] = status_code
            eligibility_by_leg.append(self.response)
            self._set_base_response()
            self.common_eligible_tests = []
        return eligibility_by_leg

    def check_automation_eligibility_ctbh(self, elements: dict):
        # In the event of an upgrade there will be two elements. The old 'Live' circuit and the new
        # 'Designed' circuit. The 'Designed' circuit is what should be deployed on the network.
        # It will be set to 'Live' once it has completed compliance testing.
        eligibility_list = self.check_automation_eligibility_by_leg(elements)
        required_eligible_legs = 2
        eligible_legs = 0
        for index, leg_eligibility in enumerate(eligibility_list):
            status_code = leg_eligibility.get("status_code")
            leg_eligibility.pop("status_code", None)
            if status_code // 100 != 2 or not leg_eligibility.get("circuit_test_eligible"):
                self.response.update(leg_eligibility)
                return self.response, status_code
            else:
                eligible_legs += 1
                for w in leg_eligibility.get("warning", []):
                    if w not in self.response.get("warning"):
                        self.response["warning"].append(w)
                self.response["warning"].append(
                    f"Topology Element '{index}' {elements[index].get('status')} used for eligibility."
                )
                self.update_eligible_tests(leg_eligibility.get("tests"), "")
                if eligible_legs >= required_eligible_legs:
                    leg_eligibility.pop("warning", None)
                    self.response.update(leg_eligibility)
                    self.response["tests"] = self.common_eligible_tests
                    return self.response, status_code
        return self.response, 500

    def get_granite_data(self):
        granite_data = granite_get(
            endpoint=DICE_CIRCUIT_TOPOLOGY, params={"cid": self.circuit_id, "$format": "json"}, retry=3
        )
        if not granite_data:
            granite_data = {}
        granite_data = granite_data.get("elements")
        if not granite_data:
            abort(500, "Circuit Topology contains no elements")
        return granite_data

    def _is_eligible(self, element):
        # 200 status code indicates compliance checks were performed, regardless of eligibility
        # 500 status code indicates compliance checks could not be performed
        service_type = element.get("service_type")
        logger.info(f"Granite service type {service_type}")
        self.response["service_type"] = service_type
        granite_bandwidth = element.get("bandwidth")
        self._set_log_preamble(service_type, granite_bandwidth)

        # service checks
        if not self.is_supported_service_type(service_type):
            return False, 200

        # design database status checks
        if not self.is_supported_path_status(element.get("status", "")):
            return False, 200
        for entry in list(reversed(element["data"])):
            if not self.is_supported_equipment_status(entry):
                return False, 200

        bandwidth = self._normalize_bandwidth(granite_bandwidth)
        logger.info(f"{self.log_preamble} | Log_Message=Bandwidth '{granite_bandwidth}' normalized to '{bandwidth}'")
        service_type_path = self._get_service_type_path(service_type)

        # optional eline bw limitation check
        if self.cap_eline_bandwidth and service_type_path == ELINE:
            if not self.is_supported_eline_bandwidth(bandwidth, granite_bandwidth):
                return False, 200

        # ensure we have devices to evaluate
        if "CTBH" in service_type:
            devices_to_check = self._get_ctbh_device_to_check(element["data"])
        else:
            devices_to_check = self._get_device_to_check(element["data"])
            if service_type_path in [ELINE, ELINE_SEGMENT]:
                devices_to_check, insufficient_device_count = self._add_device_to_check(
                    devices_to_check, element.get("data", {}), service_type_path
                )
                if insufficient_device_count:
                    segment_test_msg = "ELINE Segment Testing Not Supported. Detected only one CPE on Circuit."
                    self.response["failure_reason"] = segment_test_msg
                    logger.info(
                        f"{self.log_preamble} | Status=Ineligible | "
                        + "Ineligible_Category=ELINE Segment | "
                        + f"Log_Message={self.response['failure_reason']}"
                    )
                    return False, 200
        if not self.is_cpe_found(devices_to_check, service_type):
            return False, 200

        # carrier e-access checks
        if service_type in SERVICE_TYPE_PATH[ELINE_SEGMENT]:
            # NID NNI no thanks
            if self.is_nid_enni(devices_to_check):
                return False, 200
            # Detect if the PE is not supported for ELINE Segment
            if not self.is_supported_pe(element["data"]):  # Check A-Side First
                return False, 200
            # Mark a service as ineligible if we can't detect a wbox.
            # According to Simon Perez, There needs to be an A side nfx.
            found_wbox = self.is_pe_wbox(element["data"])
            if not found_wbox:
                found_wbox = self.is_qfx_wbox(element["data"])
            if not found_wbox:
                self.response["failure_reason"] = "No Whitebox Discovered"
                logger.error(
                    f"{self.log_preamble} | Status=Ineligible | "
                    + "Ineligible_Category=Topology | "
                    + "Ineligible_Sub_Category=Missing Whitebox | "
                    + f"Log_Message={self.response.get('failure_reason')}"
                )
                return False, 200
        if service_type in SERVICE_TYPE_PATH[CTBH]:
            pe = {}
            for entry in element["data"]:
                tid = entry.get("tid")
                if not tid and not isinstance(tid, str):
                    continue
                else:
                    tid = tid.split("-")[0]  # Strip out suffix e.x. PEWTWICI2TW-ESR02
                if tid and tid.endswith("TW") or (tid and tid[-2] == "C" and (entry.get("site_type") == "HUB")):
                    pe = entry
                    break
                if self.is_cloud(entry):
                    break
            if not pe:
                logger.info(f"No PE detected - {pe}")
                self.response["failure_reason"] = "Missing PE"
                return False, 200
            try:
                model = pe.get("model", "").split("-")[0]
                model = re.sub(r"[^a-zA-Z0-9]", "", model.upper())
                pe["model"] = model
            except Exception as e:
                logger.error(f"{self.log_preamble} | Log_Message={e}")
            if not self.is_supported_pe_vendor_and_model(pe, CTBH_SUPPORTED_PE):
                logger.info(f"Unsupported PE detected - {pe}")
                self.response["failure_reason"] = "Unsupported PE"
                return False, 200
            found_wbox = self.is_pe_ctbh_wbox(pe)
            if not found_wbox:
                logger.info("No whitebox detected")
                self.response["failure_reason"] = "No Whitebox Discovered"
                return False, 200

        # checks for all service types
        if self.is_behind_jumphost(element, service_type):
            return False, 200
        logger.debug(f"Devices to check - {devices_to_check}")
        if not devices_to_check:
            logger.error("Failed to detect loopback device")
            self.response["failure_reason"] = "Failed to detect loopback device"
            return False, 500
        make_model = ""
        for index, data in enumerate(devices_to_check):
            logger.debug(data)
            make_model, sd_make, sd_model = self.get_formatted_make_model(data)
            ips_to_check = self.get_ips_to_check(data, make_model)

            if not self.fastpath_only:
                ips_to_check = self.add_ip_finder_ip(ips_to_check, data.get("tid", ""), make_model)
                # TODO should ip validation be part of fastpath too?
                if not self.valid_ips_to_check(ips_to_check, make_model):
                    return False, 500

            if self.check_ssh in ["OPTIONAL", "YES"]:
                ssh_reachable = self.check_ssh_process(make_model, ips_to_check, data.get("device_id", ""))
                # do not halt process on optional check even if not reachable
                if not ssh_reachable and self.check_ssh == "YES":
                    return False, 200

            device_info, device_ip, discovered_ip = self.get_device_info(
                ips_to_check, make_model, data.get("tid", ""), devices_to_check, index
            )
            if not device_ip:
                if self.is_cpe_planned(data, make_model, ips_to_check, sd_model, sd_make):
                    return False, 200
                else:
                    return False, 502

            if not self.is_device_model_found(device_info, make_model, device_ip):
                return False, 200
            if not self.is_device_vendor_found(device_info, make_model, device_ip):
                return False, 200

            sd_make, sd_model = self.check_network_device_against_designed_device(
                device_info, device_ip, data, discovered_ip, devices_to_check, index, sd_make, sd_model
            )
            normalized_model = self.normalize_model(sd_model, vendor=sd_make, best_effort=True)
            logger.info(
                f"{self.log_preamble} | {sd_model} | Log_Message=Model '{sd_model}' normalized to '{normalized_model}'"
            )
            if not self.is_device_supported(sd_make, normalized_model, make_model):
                return False, 200

            if not self.is_supported_bandwidth(bandwidth, sd_make, normalized_model, make_model):
                return False, 200

            firmware = self.check_firmware(data, service_type)
            if firmware == FAILED_RETRIEVAL or firmware == FAILED_DETERMINATION:
                return False, 500
            elif firmware == INELIGIBLE:
                return False, 200
        self.response["tests"] = self.common_eligible_tests
        # You made it through all the checks!
        self.response["circuit_test_eligible"] = len(self.response["tests"]) > 0
        logger.info(f"{self.log_preamble} | Status=Eligible | State=Complete | Log_Message={self.response}")
        return True, 200

    def _set_log_preamble(self, service_type, granite_bandwidth):
        self.log_preamble = (
            f"method=GET | Beorn_Endpoint=Eligibility Circuit Testing | {f'Username={self.username} | '}"
            f"Circuit_ID={self.circuit_id} | Service_Type={service_type} | Bandwidth={granite_bandwidth}"
        )

    def is_supported_service_type(self, service_type):
        if not (service_type in ELIGIBLE_SERVICE_TYPES or (self.allow_ctbh and "CTBH" in service_type)):
            self.response["failure_reason"] = f"Service Type '{service_type}' Not Supported"
            logger.error(f"{self.log_preamble} | Status=Failed | Failure_Category=Service Type Not Supported")
            return False
        logger.info(f"{self.log_preamble} | Log_Message=Service Type Supported")
        return True

    def is_supported_path_status(self, status):
        # Deny Status -  DO-NOT-USE, Pending Commission
        supported_statuses = [
            "LIVE",
            "DESIGNED",
            "AVAILABLE",
            "PLANNED",
            "AUTO-ACCEPTED",
            "AUTO-DESIGNED",
            "AUTO-PROVISIONED",
            "AUTO-PLANNED",
        ]
        if beorn_app.app_config.USAGE_DESIGNATION == "STAGE":
            supported_statuses.append("TESTING")
        if status.upper() not in supported_statuses:
            self.response["failure_reason"] = f"Element Status '{status}' Not Supported"
            logger.error(f"{self.log_preamble} | Status=Failed | Failure_Category=Element Status Not Supported")
            return False
        if status.upper() == "LIVE":
            self.response["warning"].append("Live Circuit")
            logger.warning(f"{self.log_preamble} | Log_Message=Live Circuit Detected")
        return True

    def is_supported_equipment_status(self, entry):
        # we only care about reserved status for PEs
        if entry["device_role"] not in PE_ROLES:
            return True
        logger.debug(entry.get("equip_status", ""))
        if "RESERVED" in entry.get("equip_status", "").upper():
            self.response["failure_reason"] = "PE Reserved on Circuit"
            logger.info(
                f"{self.log_preamble} | Reserved_PE={entry.get('tid')} | Status=Ineligible | "
                + "Ineligible_Category=PE Reserved | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return False
        return True

    def _normalize_bandwidth(self, bandwidth: str) -> int:
        try:
            bandwidth = re.sub("bps", "", bandwidth.strip())
            unit = bandwidth[-1].upper()
            lookup = {"B": BIT, "K": KILOBIT, "M": MEGABIT, "G": GIGABIT, "T": TERABIT, "P": PETABIT}
            if unit not in lookup.keys():
                return int(bandwidth)

            unit_value = int(bandwidth[:-1])
            xbit = lookup[unit]
            return unit_value * xbit
        except ValueError:
            logger.warning(f"Bandwidth value is not an integer - '{bandwidth}'")
            return 0

    def _get_service_type_path(self, service_type):
        pattern = re.compile(r"\b" + service_type + r"\b")
        service_type_path = next((k for k, v in SERVICE_TYPE_PATH.items() if pattern.search(str(v))), None)
        logger.info(f"Service Type Path: {service_type_path}")
        return service_type_path

    def is_supported_eline_bandwidth(self, bandwidth, granite_bandwidth):
        eline_bandwidth_limit = 2 * GIGABIT
        if bandwidth > eline_bandwidth_limit:
            limit_exceeded_msg = (
                f"Bandwidth '{granite_bandwidth}' exceeds the bandwidth limit of 2Gbps on ELINE Circuits"
            )
            self.response["failure_reason"] = limit_exceeded_msg
            logger.error(
                f"{self.log_preamble} | Status=Failed | Failure_Category=Eline Bandwidth Cap Exceeded | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return False
        logger.info(f"{self.log_preamble} | Log_Message=Eline Bandwidth Cap Not Exceeded")
        return True

    def _get_device_to_check(self, element_data):
        devices_to_check = []
        for entry in list(reversed(element_data)):
            if entry["device_role"] in CPE_ROLES:
                devices_to_check.append(entry)
                logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
                break
            if entry.get("device_role", "") in PE_ROLES:
                break
        return devices_to_check

    def _get_ctbh_device_to_check(self, element_data):
        devices_to_check = []
        for entry in list(reversed(element_data)):
            tid = entry.get("tid")
            if tid and tid[-3] == "7" and tid[-1] == "W":
                devices_to_check.append(entry)
                logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
                break
            if entry.get("device_role", "") in PE_ROLES:
                break
        if not devices_to_check:
            for entry in list(reversed(element_data)):
                tid = entry.get("tid")
                model = self.normalize_model(entry.get("model"))
                make = entry.get("vendor")
                is_supported_device = (
                    make in SUPPORTED_VISIONWORKS_DEVICES and model in SUPPORTED_VISIONWORKS_DEVICES[make]
                )
                if tid and tid[-1] == "W" and is_supported_device:
                    devices_to_check.append(entry)
                    logger.debug(f"Topology Device Role [A, Z] Data:{entry}")
                    break
                if entry.get("device_role", "") in PE_ROLES:
                    break
        return devices_to_check

    def _add_device_to_check(self, devices_to_check, data, service_type_path):
        insufficient_device_count = False
        for entry in data:
            if entry["device_role"] in CPE_ROLES:
                if len(entry.get("path_name")) > 24:
                    # Check that the entry is a device and not a path before checking if it already exists in the list.
                    continue
                if self._is_duplicate_cpe(entry, devices_to_check):
                    two_cpes_expected = self._check_for_unsupported_eline_segment(service_type_path)
                    if two_cpes_expected:
                        insufficient_device_count = True
                        return devices_to_check, insufficient_device_count
                    else:
                        break
                devices_to_check.append(entry)
                logger.debug(f"CPE Data:\n{entry}")
                break
            if entry.get("device_role", "") in PE_ROLES:
                break
        return devices_to_check, insufficient_device_count

    def _is_duplicate_cpe(self, entry, devices_to_check):
        return any(
            device.get("tid") == entry.get("tid") and device.get("sequence") == entry.get("sequence")
            for device in devices_to_check
        )

    def _check_for_unsupported_eline_segment(self, service_type_path):
        if service_type_path in [ELINE]:
            return True
        else:
            logger.info("TID already in sequence")
            return False

    def is_cpe_found(self, devices_to_check, service_type):
        if (
            not devices_to_check and service_type in ELIGIBLE_SERVICE_TYPES
        ):  # TODO isn't this redundant to the service type supported check?
            self.response["failure_reason"] = "No device with role ['A', 'Z']"
            logger.error(
                f"{self.log_preamble} | Status=Failed | Failure_Category=No device with role ['A', 'Z'] | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return False
        # TODO i swear this is redundant to the check made in _add_device_to_check?
        if service_type in SERVICE_TYPE_PATH[ELINE]:
            # gotta have *two* handoff devices if you're an eline!
            return self.check_expected_cpes_found(devices_to_check)
        return True

    def check_expected_cpes_found(self, devices_to_check):
        if len(devices_to_check) < 2:
            self.response["failure_reason"] = "No device with role ['A', 'Z']"  # Doesn't support segments at the moment
            logger.error(
                f"{self.log_preamble} | Status=Failed | Failure_Category=Invalid Topology | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return False
        return True

    def is_nid_enni(self, devices_to_check):
        logger.debug(f"Checking for NID ENNI - {devices_to_check} - {len(devices_to_check)}")
        if len([device for device in devices_to_check if device.get("vendor") != JUNIPER]) > 1:
            self.response["failure_reason"] = "NID ENNI Detected"
            logger.error(
                f"{self.log_preamble} | Status=Ineligible | "
                + "Ineligible_Category=NID ENNI Detected | "
                + f"Log_Message={self.response.get('failure_reason')}"
            )
            return True
        return False

    def is_supported_pe(self, data):
        for entry in data:
            if entry["device_role"] in CPE_ROLES:
                if self.is_mx_cpe(entry):
                    return False
            elif entry["device_role"] in PE_ROLES:
                if not self.is_supported_pe_vendor_and_model(entry, E_ACCESS_FIBER_SUPPORTED_PE):
                    return False
            elif self.is_cloud(entry):
                break
        return True

    def is_mx_cpe(self, entry):
        logger.info(f"MX CPE check - vendor {entry.get('vendor', '').upper()}")
        if entry.get("vendor", "").upper() == "JUNIPER":
            self.response["failure_reason"] = "MX CPE"
            logger.error(
                f"{self.log_preamble} | Status=Ineligible | "
                + "Ineligible_Category=Topology | "
                + "Ineligible_Sub_Category=MX CPE | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return True
        return False

    def is_supported_pe_vendor_and_model(self, entry, supported_devices):
        vendor = entry.get("vendor")
        model = entry.get("model")
        if vendor in supported_devices and model in supported_devices.get(vendor):
            # green light
            return True
        else:
            self.response["failure_reason"] = "Unsupported PE"
            logger.error(
                f"{self.log_preamble} | Status=Ineligible | "
                + "Ineligible_Category=Topology | "
                + "Ineligible_Sub_Category=Unsupported PE | "
                + f"Log_Message={self.response.get('failure_reason')}"
            )
            return False

    def is_pe_wbox(self, data):
        for entry in data:
            if entry["device_role"] in PE_ROLES:
                pe_details = get_pe_details(entry)
                logger.warning(pe_details)
                for pe in pe_details:
                    if pe.get("test_equip_vendor") == JUNIPER and "VTP" not in pe.get("test_equip_model", "VTP"):
                        logger.warning(f"Valid whitebox on PE - {pe}")
                        return True
            elif self.is_cloud(entry):
                break
        return False

    def is_qfx_wbox(self, data):
        for entry in data:
            if entry["device_role"] in QFX_ROLES:
                pe_details = get_pe_details(entry)
                logger.warning(pe_details)
                for pe in pe_details:
                    if "VTP" not in pe.get("test_equip_model", "VTP"):
                        logger.warning(f"Valid whitebox on QFX {pe}")
                        return True
            elif self.is_cloud(entry):
                break
        else:
            self.response["failure_reason"] = "No Whitebox Discovered"
            logger.error(
                f"{self.log_preamble} | Status=Ineligible | "
                + "Ineligible_Category=Topology | "
                + "Ineligible_Sub_Category=Missing Whitebox | "
                + f"Log_Message={self.response.get('failure_reason')}"
            )
        return False

    def is_pe_ctbh_wbox(self, pe):
        tid = pe.get("tid")
        if not tid and not isinstance(tid, str):
            return False
        else:
            tid = tid.split("-")[0]  # Strip out suffix e.x. PEWTWICI2TW-ESR02
        pe_details = get_pe_details(pe, is_ctbh=True)
        logger.debug(f"pe_details - {pe_details}")
        for pe in pe_details:
            if pe.get("test_equip_vendor") == ADVA and "VTA" in pe.get("test_equip_model", ""):
                logger.warning(f"Valid whitebox on PE - {pe}")
                return True
        logger.warning("Could not detect ctbh wbox")
        return False

    def is_behind_jumphost(self, element, service_type):
        if service_type in SERVICE_TYPE_PATH[ELINE_SEGMENT] or "CTBH" in service_type:
            if self.is_side_behind_jumphost(element.get("data", {})):  # Check A-Side
                return True
            return False
        if self.is_side_behind_jumphost(list(reversed(element.get("data", {})))):  # Check Z-Side
            return True
        if service_type in SERVICE_TYPE_PATH[ELINE]:
            if self.is_side_behind_jumphost(element.get("data", {})):  # Check A-Side
                return True
        return False

    def is_side_behind_jumphost(self, devices):
        last_pe_before_cloud_index = False
        first_pe = {}
        for entry in devices:
            if entry.get("device_role", "") in PE_ROLES:
                if not first_pe:
                    first_pe = entry
                last_pe_before_cloud_index = entry
            elif self.is_cloud(entry):
                break
        logger.debug(f"{last_pe_before_cloud_index = }")  # noqa: E251, E202
        if last_pe_before_cloud_index:
            if not last_pe_before_cloud_index.get("management_ip"):
                logger.debug("No management IP on last PE before cloud")
                return False
            ip = last_pe_before_cloud_index.get("management_ip", "").split("/")[0]
            # PE ip addresses that start with 96 and don't respond to ssh are
            # behind a jumphost and are not supported by circuit testing.
            potentially_jumphosty = self.is_acr(last_pe_before_cloud_index) or self.is_96dot_pe(ip)
            if not potentially_jumphosty:
                return False  # no chance we're behind a jumphost
            if not self.is_96dot_sshable(first_pe):
                jumphost = last_pe_before_cloud_index.get("tid", True)
                self.response["failure_reason"] = "Jumphost Detected on Circuit"
                logger.error(
                    f"{self.log_preamble} | Jumphost={jumphost} | Status=Ineligible | "
                    + "Ineligible_Category=Jumphost Detected | "
                    + f"Log_Message={self.response.get('failure_reason')}"
                )
                return True
        return False

    def is_96dot_sshable(self, first_pe):
        if first_pe and first_pe.get("management_ip"):
            logger.info("PE may be behind jumphost.")
            pe_ip = first_pe["management_ip"]
            if not self.is_reachable_ssh(host=pe_ip):
                logger.info(f"Jumphost Detected. IP {pe_ip} not reachable via SSH")
                return False
            else:
                logger.info(f"IP {pe_ip} is reachable via SSH")
                return True
        return True  # if none of the criteria are met, we don't care to check here

    def is_acr(self, last_pe):
        return "ACR" in last_pe.get("owned_edge_point", "").upper() or "ACR" in last_pe.get("equip_descr", "").upper()

    def is_96dot_pe(self, ip: str):
        behind_jumphost_check = "96"
        return ip.split(".")[0] == behind_jumphost_check

    def is_reachable_ssh(self, host, port=22):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                host, username="test", password="test123", port=port, timeout=10, allow_agent=False, look_for_keys=False
            )
            client.close()
            return True
        except paramiko.AuthenticationException as e:
            logger.info(f"Reached authentication for SSH connection to {host}. {e}")
            return True
        except paramiko.SSHException as sshexception:
            logger.info(f"Unable to establich an SSH connection to {host}. {sshexception}")
            return False
        except Exception as e:
            logger.info(f"Error connecting to {host}: {str(e)}")
            return False

    def get_formatted_make_model(self, data):
        make = re.sub(r"[^a-zA-Z0-9]", "", data["vendor"]).upper()
        model = re.sub(r"[^a-zA-Z0-9]", "", data["model"]).upper()
        # Sanitize model string by striping out all non-alphanumeric characters for effective result
        sd_model = re.sub(r"[^A-Z0-9]", "", model.upper())
        sd_make = make.upper()
        return f"Make={sd_make} | Model={sd_model}", sd_make, sd_model

    def get_ips_to_check(self, data, make_model):
        device_id = data.get("device_id", "")
        device_tid = data.get("tid", "")
        raw_ips = [self.cpe_ip_address, data.get("management_ip"), self.get_cpe_ip_address(device_id, device_tid)]
        ips_to_check = []
        for ip in raw_ips:
            logger.info(f"ip {ip} type {type(ip)}")
            if not ip or not isinstance(ip, str) or ip.upper() in ["DHCP", "TRUE", "FALSE"]:
                logger.warning(
                    f"{self.log_preamble} | {make_model} | "
                    + f"Log_Message=CPE Management IP '{ip}' cannot be used for IP checks."
                )
            else:
                ip = ip.split("/")[0]
                if ip not in ips_to_check:
                    ips_to_check.append(ip)
        logger.info(
            f"{self.log_preamble} | {make_model} | " + f"Log_Message=Discovered CPE Management IP '{ips_to_check}'"
        )
        return ips_to_check

    def get_cpe_ip_address(self, device_id: str, hostname: str = "") -> str | None:
        # TODO make sure the latest fixes made their way here
        logger.info(f"Device tid: '{device_id}'")
        if not hostname:
            hostname = device_id.split(".")[0]
        try:
            ip = socket.gethostbyname(device_id)
            ipaddress.ip_address(ip)
            if ip:
                return ip
        except ValueError as error:
            # IPControl can take 12-24 hours to update tid to ip mapping
            logger.warning(f"Failed to get ipaddress with device_id '{device_id}' Error - {error}")
        except socket.gaierror as error:
            logger.warning(f"Unable to retrieve ip from device_id '{device_id}' Error - {error}")
        except Exception:
            logger.error(f"Unknown Exception while SNMP device_id '{device_id}'")
        ip = get_ip_from_tid(hostname, failout=False)
        logger.info(f"Ip from tid '{ip}'")
        if ip:
            return ip

    def add_ip_finder_ip(self, ips_to_check, tid, make_model):
        if not ips_to_check:
            ip_finder_response, _ = ip_finder(self.circuit_id, tid)
            ip_address = ip_finder_response.get("CPE_IP", "")
            if ip_address == "no ip found":
                ip_address = ""
            else:
                # Update CPE Management IP in granite to prevent duplicate lookups. Best Effort.
                status = self.palantir_ip_update(ip_address, tid)
                logger.info(
                    f"{self.log_preamble} | {make_model} | "
                    + f"Log_Message=Best Effort to update granite cpe management ip '{status}'"
                )
            ips_to_check = [ip_address]
            logger.info(
                f"{self.log_preamble} | {make_model} | "
                + f"Log_Message=Discovered CPE Management IP with IP Finder '{ips_to_check}'"
            )
        return ips_to_check

    def valid_ips_to_check(self, ips_to_check, make_model):
        if not any(ip for ip in ips_to_check):
            self.response["failure_reason"] = f"Could not discover cpe management ip '{ips_to_check}'"
            logger.error(
                f"{self.log_preamble} | {make_model} | Status=Failed | Failure_Category=No CPE IP DISCOVERED | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return False
        return True

    def palantir_ip_update(self, ip_address: str, tid: str) -> dict:
        palantir = PalantirConnector(PALANTIR_URL)
        status = palantir.ip_update(ip_address, tid)
        return status

    def check_ssh_process(self, make_model, ips_to_check, device_id):
        logger.info(
            f"{self.log_preamble} | {make_model} | "
            + f"Log_Message=Checking for SSH reply with enforcement '{self.check_ssh.upper()}'"
        )
        for ip in ips_to_check:
            if self.is_reachable_ssh(host=ip):
                logger.info(f"Device '{device_id}' is reacheable via SSH on IP address '{ip}'.")
                return True

        if self.check_ssh == "YES":
            self.response["failure_reason"] = f"Device '{device_id}' is not reacheable via SSH."
            logger.error(
                f"{self.log_preamble} | {make_model} | Status=Failed | Failure_Category=Unreacheable SSH | "
                + f"Log_Message={self.response['failure_reason']}"
            )
        else:
            # check is informational, not required
            msg = f"Device '{device_id}' is not reacheable via SSH."
            self.response["warning"].append(msg)
            logger.error(f"{self.log_preamble} | {make_model} | " + f"Log_Message={msg}")
        return False

    def get_device_info(self, check_ips, make_model, tid, devices_to_check, index):
        discovered_ip = False
        device_info = {}
        device_ip = ""
        for ip in check_ips:
            try:
                if not ip:
                    logger.warning(f"Log_Message=Invalid ip attempted '{ip}'")
                    continue
                info = get_system_info(ip)
                logger.info(
                    f"{self.log_preamble} | {make_model} | " + f"Log_Message=Device IP '{ip}' Device info '{info}'"
                )
                device_info = {"tid": info[0], "description": info[1], "uptime": info[2], "address": info[3]}
                if not device_info.get("description"):
                    continue
                logger.info(f"Ip {ip} CPE IP {self.cpe_ip_address}")
                tid_mismatch = self.hostname_compare(device_info.get("tid"), tid) not in ["MATCH", "CLOSEENOUGH"]
                if tid_mismatch and ip == self.cpe_ip_address:
                    self.response["warning"].append(
                        f"Discovered device '{device_info.get('tid')}' does not match design '{tid}'."
                    )
                    logger.warning(
                        f"{self.log_preamble} | {make_model} | IP_Address={ip} | "
                        + f"Log_Message={self.response['failure_reason']}"
                    )
                    continue
                if ip not in devices_to_check[index].get("management_ip", ""):
                    logger.error(f"Management IP '{devices_to_check[index].get('management_ip')}' Discovered IP '{ip}'")
                    discovered_ip = True
                # clean up management ip address
                devices_to_check[index].update({"management_ip": ip})
                device_ip = ip
                logger.info(
                    f"{self.log_preamble} | {make_model} | "
                    + f"Log_Message=Device IP '{device_ip}' returned an SNMP response."
                )
                break
            except Exception as e:
                logger.error(
                    f"{self.log_preamble} | {make_model} | Log_Message=Device IP '{ip}' SNMP threw an Exception - {e}",
                    exc_info=True,
                )
        logger.debug(f"{device_info = } {device_ip = } {discovered_ip = }")  # noqa: E251, E202
        return device_info, device_ip, discovered_ip

    def is_cpe_planned(self, data, make_model, check_ips, sd_model, sd_make):
        # This is a workaround until we can determine how many standalone planned circuits failed.
        logger.info(f"cpe_planned_ineligible - {self.cpe_planned_ineligible}")
        status = data.get("equip_status", "").upper()
        if self.cpe_planned_ineligible and status in ["PLANNED", "AUTO-PLANNED"]:
            self.response["failure_reason"] = f"Element Status '{status}' Not Supported"
            logger.error(
                f"{self.log_preamble} | {make_model} | Status=Ineligible | Failure_Category=No CPE for Planned Status |"
                + " Log_Message=Planned Circuit No valid SNMP response from IP Attempt List"
                + f"'{check_ips}'"
            )
            return True
        else:
            self.response["failure_reason"] = f"No valid IP to SNMP for device '{data.get('device_id')}'"
            normalized_model = self.normalize_model(sd_model, vendor=sd_make, best_effort=True)
            logger.info(
                f"{self.log_preamble} | {make_model} | "
                + f"Log_Message=Model '{sd_model}' normalized to '{normalized_model}'"
            )
            if not normalized_model:
                self.response["warning"].append(f"Unsupported Make '{sd_make}' Model '{sd_model}' reported by granite")
            logger.error(
                f"{self.log_preamble} | {make_model} | Status=Failed | Failure_Category=No valid IP to SNMP | "
                + f"Log_Message=No valid SNMP response from IP Attempt List'{check_ips}'"
            )
            return False

    def normalize_model(self, long_model: str, vendor=None, best_effort=False) -> str:
        longest_substring = ""
        if vendor and vendor in NORMALIZE_MODEL.keys():
            if not NORMALIZE_MODEL.get(vendor):
                return long_model if best_effort else ""
            for key in NORMALIZE_MODEL[vendor]:
                if key in long_model and len(key) > len(longest_substring):
                    longest_substring = key
        else:
            for models in NORMALIZE_MODEL.values():
                for key in models:
                    if key in long_model and len(key) > len(longest_substring):
                        longest_substring = key
        if not longest_substring and best_effort:
            return long_model
        return longest_substring

    def is_device_model_found(self, device_info, make_model, device_ip):
        device_info["model"] = _isolate_model(device_info.get("description", ""))
        device_info["vendor"] = _get_vendor_by_model(device_info.get("model"))
        logger.debug(f"{device_info['model'] = } {device_info['vendor'] = }")  # noqa: E251, E202
        if not device_info.get("vendor") and device_info.get("model"):
            self.response["failure_reason"] = f"Ineligible Device Model '{device_info.get('model')}'"
            logger.error(
                f"{self.log_preamble} | {make_model} | IP_Address={device_ip} | Status=Ineligible | "
                + "Ineligible_Category=Ineligible Device | "
                + f"Log_Message={self.response['failure_reason']} - Device Info {device_info}"
            )
            return False
        return True

    def is_device_vendor_found(self, device_info, make_model, device_ip):
        if not device_info and device_info["vendor"]:
            self.response["failure_reason"] = f"Ineligible Device Model '{device_info['model']}'"
            logger.error(
                f"{self.log_preamble} | {make_model} | IP_Address={device_ip} | Status=Ineligible | "
                + "Ineligible_Category=Ineligible Device | "
                + f"Log_Message=Couldn't find vendor from {self.response['failure_reason']}"
            )
            return False
        return True

    def check_network_device_against_designed_device(
        self, device_info, device_ip, data, discovered_ip, devices_to_check, index, sd_make, sd_model
    ):
        # Check if make/model for cpe in granite matches the make/model discovered by snmp
        discovered_vendor = re.sub(r"[^a-zA-Z0-9]", "", device_info.get("vendor")).upper()
        discovered_model = re.sub(r"[^a-zA-Z0-9]", "", device_info.get("model")).upper()
        normalized_sd_model = self.normalize_model(sd_model)
        normalized_discovered_model = self.normalize_model(discovered_model)
        logger.info(f"Device IP '{device_ip}' Management IP '{data.get('management_ip')}'")
        vendor_mismatch = self.is_vendor_match(sd_make, discovered_vendor)
        model_mismatch = self.is_model_match(normalized_sd_model, normalized_discovered_model)
        circuit_unreachable = any("Circuit Not Reachable" in warning for warning in self.response.get("warning", []))
        logger.info([vendor_mismatch, model_mismatch, circuit_unreachable, discovered_ip])
        if vendor_mismatch or model_mismatch or circuit_unreachable or discovered_ip:
            device_mismatch = (
                f"Mismatch in device vendor/model. TID '{device_info.get('tid')}'. "
                f"IP '{device_ip}'. "
                f"Discovered '{discovered_vendor}'/'{discovered_model}'. "
                f"Expected '{sd_make}'/'{sd_model}'"
            )
            self.response["warning"].append(device_mismatch)
            sd_make = discovered_vendor
            sd_model = discovered_model
            make_model = f"Make={sd_make} | Model={sd_model}"
            self.log_preamble += make_model
            logger.warning(f"{self.log_preamble} | {make_model} | " + f"Log_Message={device_mismatch}")
            devices_to_check[index].update({"vendor": sd_make, "model": sd_model})
        if not (vendor_mismatch or model_mismatch or circuit_unreachable) and discovered_ip:
            different_ip = f"Override Management IP. TID '{device_info.get('tid')}'. IP '{device_ip}'."
            self.response["warning"].append(different_ip)
        return sd_make, sd_model

    def is_vendor_match(self, sd_make, discovered_vendor):
        return sd_make != discovered_vendor

    def is_model_match(self, sd_model, discovered_model):
        return sd_model != discovered_model

    def is_device_supported(self, make, model, make_model):
        if not (make in SUPPORTED_VISIONWORKS_DEVICES and model in SUPPORTED_VISIONWORKS_DEVICES[make]):
            failure_reason = f"Device Make '{make}' or Model '{model}' Not Supported"
            failure_category = "Unsupported Device"
            logger.error(
                f"{self.log_preamble} | {make_model} | Status={INELIGIBLE} | "
                + f"{INELIGIBLE}_Category={failure_category}"
                + f"Log_Message={failure_reason}"
            )
            self.response["failure_reason"] = failure_reason
            return False
        return True

    def is_supported_bandwidth(self, bandwidth, make, model, make_model):
        eligibility = INELIGIBLE
        bandwidth_limit = SUPPORTED_VISIONWORKS_DEVICES[make][model].get(BANDWIDTHLIMIT)
        if not bandwidth_limit:
            failure_reason = f"Failed to find bandwidth limit for make '{make}' model '{model}'"
            failure_category = "Unknown Bandwidth Limit"
        elif bandwidth > int(bandwidth_limit) or bandwidth < 0:
            failure_reason = f"Bandwidth '{bandwidth}' exceeds bandwidth limit {bandwidth_limit} on '{make}' '{model}'"
            failure_category = "Ineligible Bandwidth"
        else:
            eligibility = ELIGIBLE
        if eligibility != ELIGIBLE:
            logger.error(
                f"{self.log_preamble} | {make_model} | Status={eligibility} | "
                + f"{eligibility}_Category={failure_category} | "
                + f"Log_Message={failure_reason}"
            )
            self.response["failure_reason"] = failure_reason
            return False
        logger.info(f"{self.log_preamble} | {make_model} | " + "Log_Message=Bandwidth Supported")
        return True

    def check_firmware(self, data, service_type):
        ip = data.get("management_ip")
        make = data.get("vendor")
        model = data.get("model")
        device_preamble = f"Vendor={make} | Model={model} | IP_Address={ip}"
        firmware = self.get_device_firmware(ip, make, model, device_preamble)
        if firmware == FAILED_RETRIEVAL:
            return firmware
        eligible_tests = []
        normalized_model = self.normalize_model(data.get("model"), vendor=data.get("vendor"), best_effort=True)
        try:
            clean_service_type = self.normalize_service_type(service_type)
            if clean_service_type == ELINE_SEGMENT:
                clean_service_type = ELINE
            if clean_service_type == CTBH:
                clean_service_type = ELINE
            logger.info(f"{data.get('vendor')} {normalized_model} {clean_service_type}")
            test_eligibility = SUPPORTED_VISIONWORKS_DEVICES[data["vendor"]][normalized_model][FIRMWARE].get(
                clean_service_type
            )
            for test, test_min_version in test_eligibility.items():
                if compare_version(firmware, test_min_version) != "LESSER":
                    eligible_tests.append(test)
            if eligible_tests:
                logger.info(
                    f"{self.log_preamble} | {device_preamble} | "
                    + f"Log_Message=Firmware {firmware} is eligible to run Tests '{eligible_tests}' "
                    + f"on Make '{make}' Model '{model}'."
                )
        except Exception as e:
            error_msg = (
                f"Failed to determine if firmware '{firmware}' is eligible. "
                f"Make '{make}' Model '{model}. - Exception {e}"
            )
            logger.error(f"{self.log_preamble} | {device_preamble} | " + f"Log_Message={error_msg}", exc_info=True)
            self.response["failure_reason"] = error_msg
            return FAILED_DETERMINATION
        if not eligible_tests:
            self.response["failure_reason"] = f"Ineligible Firmware '{firmware}' on Device Make '{make}' Model '{model}'"
            logger.error(
                f"{self.log_preamble} | {device_preamble} | Status=Ineligible | "
                + "Ineligible_Category=No Eligible Tests | "
                + f"Log_Message={self.response['failure_reason']}"
            )
            return INELIGIBLE
        else:
            self.update_eligible_tests(eligible_tests, device_preamble)
        logger.info(
            f"{self.log_preamble} | {device_preamble} | Log_Message=Common Eligible Tests "
            + f"'{self.common_eligible_tests}'"
        )

    def get_device_firmware(self, ip, make, model, device_preamble):
        firmware = get_firmware(ip, make)
        if not firmware:
            self.response["failure_reason"] = (
                f"Unable to retrieve Device firmware from Device IP '{ip}' Make '{make}' Model '{model}'"
            )
            logger.error(
                f"{self.log_preamble} | {device_preamble} | Status=Failed | Failure_Category=No Firmware Retrieved"
            )
            return FAILED_RETRIEVAL
        return firmware

    def normalize_service_type(self, service_type: str) -> str:
        if "CTBH" in service_type:
            return CTBH
        for k, v in SERVICE_TYPE_PATH.items():
            if service_type.upper() in v:
                return k

    def update_eligible_tests(self, eligible_tests, device_preamble):
        if not self.common_eligible_tests:
            self.common_eligible_tests = eligible_tests
        else:
            logger.info(
                f"{self.log_preamble} | {device_preamble} | "
                + f"Log_Message=Comparing eligible tests. Common '{self.common_eligible_tests}'.\n"
                + f"Device eligible test '{eligible_tests}'"
            )
            self.common_eligible_tests = [test for test in eligible_tests if test in self.common_eligible_tests]

    def hostname_compare(self, hostname1: str, hostname2: str):
        if not hostname1 or not hostname2 or not isinstance(hostname1, str) or not isinstance(hostname2, str):
            logger.warning(f"Invalid hostname in compare {hostname1}/{hostname2}")
            return False
        h1 = hostname1.strip().upper()
        h2 = hostname2.strip().upper()
        if h1 == h2:
            return "MATCH"
        # Detect Common Typos when entering text
        h1 = h1.replace("0", "O").replace("1", "I").replace("l", "I")
        h2 = h2.replace("0", "O").replace("1", "I").replace("l", "I")
        if h1 == h2:
            return "CLOSEENOUGH"
        try:
            h1 = h1[:-3] + "X" + h1[-2:]
            h2 = h2[:-3] + "X" + h2[-2:]
            if h1 == h2:
                return "DEVICEREPLACEMENT"
        except IndexError:
            logger.warning(f"Hostname length is not long enough {h1}/{h2}")
        return False

    def check_ip_snmp(self, ip_list: dict, best_effort=False):
        for ip in ip_list:
            if not ip:
                continue
            device_info = get_device_vendor_and_model(ip, best_effort)
            if device_info["vendor"]:
                return ip, device_info
        return False, False

    def is_cloud(self, device: dict) -> bool:
        topology = device.get("topology", "").upper()
        if topology == "CLOUD":
            return True
        return (
            topology == "POINT TO POINT"
            and not device.get("model")
            and not device.get("tid")
            and not device.get("chan_name")
        )
