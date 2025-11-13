import logging
import re

from common_sense.common.errors import (
    abort,
    error_formatter,
    get_standard_error_summary,
    AUTOMATION_UNSUPPORTED,
    GRANITE,
    MISSING_DATA,
    SENSE,
    INCORRECT_DATA,
)
from palantir_app.bll.device import Device
from palantir_app.common.constants import (
    UNSUPPORTED_ACCEPTANCE_SERVICE_TYPES,
    DEVICE_STATUS_CHECK_SERVICES,
    DEVICE_STATUS_CHECK_VENDORS,
    SERVICE_TYPES,
)
from palantir_app.dll.sense import sense_get
from palantir_app.dll.granite import get_circuit_devices, get_fqdn_ip_vendor_from_tid
from palantir_app.dll.tacacs import get_tacacs_status


logger = logging.getLogger(__name__)


def validation_process(cid: str = "", tid: str = "", acceptance: bool = False):
    l2circuit_error = None
    service_type, devices = _get_validation_data(cid=cid, tid=tid)
    devices_to_validate = [Device(device, cid) for device in devices]
    if any(device.is_err_state for device in devices_to_validate):
        msg = get_combined_message(devices_to_validate)
        abort(
            501, msg, summary="NETWORK | CONNECTIVITY ERROR - PREREQUISITE DEVICE VALIDATION FAILED", pretty_format=True
        )
    for device in devices_to_validate:
        validate_device(device)
        if acceptance and _is_l2circuit_service_eligible(service_type):
            l2circuit_error = validate_l2_connection(device)
            if l2circuit_error:
                device.msg["additional"] = {"l2circuit": l2circuit_error}
    if any(device.is_err_state for device in devices_to_validate) or l2circuit_error:
        msg = get_combined_message(devices_to_validate)
        abort(501, msg, summary="NETWORK | CONNECTIVITY ERROR - TACACS DEVICE VALIDATION FAILED", pretty_format=True)
    return {"message": get_combined_message(devices_to_validate)}


def _get_validation_data(cid: str = "", tid: str = "") -> tuple[str, list]:
    devices = []
    service_type = ""
    if not cid and not tid:
        msg = error_formatter(SENSE, MISSING_DATA, "Device Validation Process", "Must provide either TID or CID")
        abort(502, msg, summary=get_standard_error_summary(msg))
    # gather device data either by TID or CID
    if cid:
        logger.info("---------------STARTING CID DEVICE CHECK---------------")
        service_type, devices = _get_cid_data(cid)
    elif tid and not cid:
        logger.info("---------------STARTING SINGLE DEVICE CHECK---------------")
        devices = [_get_tid_data(tid)]  # we don't need service type for single device checks
    if not devices:
        msg = error_formatter(GRANITE, MISSING_DATA, "No devices found", detail=cid)
        abort(502, msg, summary=get_standard_error_summary(msg))
    return service_type, devices


def _get_cid_data(cid):
    """Returns list of dictionaries containing device IPs and TIDs for CID from Granite"""
    records = get_circuit_devices(cid)
    for element in records:
        if element["PATH_NAME"] == cid:
            break
    else:
        msg = error_formatter(GRANITE, INCORRECT_DATA, "Circuit ID Path Name", f"{cid}")
        abort(502, msg, summary=get_standard_error_summary(msg))
    service_type = records[0]["SERVICE_TYPE"]
    if service_type in UNSUPPORTED_ACCEPTANCE_SERVICE_TYPES:
        msg = error_formatter(SENSE, AUTOMATION_UNSUPPORTED, "Service Type", f"{service_type}")
        abort(502, msg, summary=get_standard_error_summary(msg))
    if not service_type:
        msg = error_formatter(GRANITE, MISSING_DATA, "Service Type", f"{cid}")
        abort(502, msg, summary=get_standard_error_summary(msg))
    devices = records
    latest_rev_id = _get_latest_revision_id(devices)
    circuit_devices = _get_circuit_devices(devices, latest_rev_id)
    if not circuit_devices:
        msg = error_formatter(GRANITE, MISSING_DATA, "Circuit Devices", f"{cid}")
        abort(502, msg, summary=get_standard_error_summary(msg))

    logger.info(f"GRANITE CALL - SERVICE TYPE: {service_type}")
    logger.info(f"GRANITE CALL - Device List: {circuit_devices}")
    return service_type, circuit_devices


def _get_latest_revision_id(devices):
    # Determine the latest revision of the CID
    latest_rev_id = ""
    for dev in devices:
        if dev["INITIAL_CIRCUIT_ID"] is None:
            abort(502, "GRANITE CALL - INITIAL CID NOT FOUND")
        elif dev["INITIAL_CIRCUIT_ID"] == "":
            abort(502, "GRANITE CALL - REVISION ID UNDEFINED")
        elif dev["INITIAL_CIRCUIT_ID"] > latest_rev_id:
            latest_rev_id = dev["INITIAL_CIRCUIT_ID"]
    return latest_rev_id


def _get_circuit_devices(devices, latest_rev_id):
    # Skip devices with no equipment type and save device IP & TID if it isn't on the list already
    circuit_devices = []

    def _skip_tid(device_tid: str):
        if not re.match(".{9}[ACTQWXYZ0-9]W", device_tid.upper()):
            logger.info(f"Skipping TID: {device_tid}")
            return True
        return False

    for dev in devices:
        # Due to Granite changes, determine which key refers to the device's management IP address
        dev_ip = _get_device_ip_from_granite(dev)
        if dev["INITIAL_CIRCUIT_ID"] == latest_rev_id:
            if not dev["ELEMENT_CATEGORY"]:
                continue
            elif dev["TID"] and dev["TID"] not in [x["tid"] for x in circuit_devices] and not _skip_tid(dev["TID"]):
                if len(dev["TID"][0:11]) != 11:
                    msg = error_formatter(GRANITE, INCORRECT_DATA, "TID", f"{dev['TID']}")
                    abort(502, msg)
                circuit_devices.append(
                    {
                        "ip": dev_ip,
                        "tid": dev["TID"],
                        "fqdn": dev["FQDN"],
                        "port": dev.get("PORT_ACCESS_ID"),
                        "vlan": dev.get("S_VLAN"),
                        "vendor": dev.get("VENDOR"),
                        "channel": dev.get("CHAN_NAME"),
                        "category": dev.get("ELEMENT_CATEGORY"),
                        "leg": dev.get("LEG_NAME"),
                    }
                )
    return circuit_devices


def _get_device_ip_from_granite(device):
    if "MANAGEMENT_IP" in device.keys():
        return device["MANAGEMENT_IP"]
    elif "IPV4_ADDRESS" in device.keys() and device["IPV4_ADDRESS"]:
        return device["IPV4_ADDRESS"]
    elif "IPV6_ADDRESS" in device.keys() and device["IPV6_ADDRESS"]:
        return device["IPV6_ADDRESS"]


def _get_tid_data(tid):
    # single device validation only requires IP, TID, FQDN, and vendor from Granite
    # remaining properties are required only for circuit level validations
    granite_data = get_fqdn_ip_vendor_from_tid(tid)
    return {
        "ip": granite_data["IPV4_ADDRESS"],
        "tid": tid,
        "fqdn": granite_data["FQDN"],
        "port": None,
        "vlan": None,
        "vendor": granite_data["VENDOR"],
        "channel": None,
        "category": None,
        "leg": None,
    }


def validate_device(device: Device):
    logger.info("---------------STARTING VALIDATIONS---------------")
    device.determine_vendor_and_model()
    device.determine_tacacs()
    if device.tacacs_remediation_required:
        device.remediate_tacacs()
        device.ise_check()
        if device.ise_success:
            device.determine_tacacs()
    if device.granite_remediation_required:
        # align databases with usable IP value
        device.update_granite_ip()
    # set device error state based on validation process results
    device.set_is_err_state()


def _is_l2circuit_service_eligible(service_type):
    svc = _convert_service_type(service_type)
    logger.debug(f"converted service type: {svc}")
    if svc in DEVICE_STATUS_CHECK_SERVICES:
        return True
    else:
        return False


def _convert_service_type(service_type):
    logger.debug(f"service type: {service_type}")
    for svc, product_names in SERVICE_TYPES.items():
        if service_type in product_names:
            return svc
    return "Service type not mapped"


def validate_l2_connection(device: Device):
    if not is_l2circuit_eq_type_eligible(device.eq_type):
        logger.debug(f"equipment type does not support l2circuit: {device.eq_type}")
        return

    if not is_l2circuit_vendor_eligible(device.vendor):
        logger.debug(f"vendor does not support l2circuit: {device.vendor}")
        return

    port = _get_l2circuit_check_port(device.port, device.leg_name)

    vlan = _get_l2circuit_check_vlan(device.vlan, device.chan_name)

    if not is_l2circuit_vlan_valid(vlan):
        logger.debug(f"invalid vlan: {vlan}")
        return

    if not is_l2circuit_port_valid(port):
        logger.debug(f"invalid port: {port}")
        return

    interface = _get_l2circuit_check_interface(port, vlan)

    l2circuit_data_check(device.tid, port)

    valid_response, response_data = _get_l2circuit_status_arda(device.tid, interface)

    if not valid_response:
        logger.debug("invalid response")
        return  # TODO does this need to return something to trigger fall out?

    connection_status = _get_l2_connection_status(device.tid, interface, response_data)

    if connection_status and connection_status != "Up":
        return {
            "status": "failed",
            "reason": "l2circuit status",
            "data": {"interface": interface, "connection": connection_status},
        }


def is_l2circuit_eq_type_eligible(eq_type):
    if not eq_type or eq_type != "ROUTER":
        return False
    else:
        return True


def is_l2circuit_vendor_eligible(vendor):
    if vendor not in DEVICE_STATUS_CHECK_VENDORS:
        return False
    else:
        return True


def _get_l2circuit_check_port(port, leg_name):
    if "/" in leg_name:
        port = leg_name.split("/")[0]
    return port


def _get_l2circuit_check_vlan(vlan, chan_name):
    if chan_name and not vlan:
        vlan = str(re.search(r"\d+", chan_name).group(0))
    return vlan


def is_l2circuit_port_valid(port):
    if not port or port == "":
        return False
    else:
        return True


def is_l2circuit_vlan_valid(vlan):
    if not vlan:
        return False
    else:
        return True


def _get_l2circuit_check_interface(port, vlan):
    if port and vlan:
        interface = port + "." + vlan
        interface = interface.lower()
        return interface


def l2circuit_data_check(tid, port):
    if not tid or not port:
        error_message = (
            "Failure Deriving Mandatory Device information for L2 Status Check (TID (Host), Port (Interface))"
        )
        abort(502, error_message)


def _get_l2circuit_status_arda(tid, interface):
    sense_response = sense_get(
        f"arda/v1/device?hostname={tid}",
        params={"cmd": "show_l2circuit_status", "args": interface, "attempt onboarding": "true"},
        timeout=120,
        best_effort=True,
    )
    logger.debug(f"Sense response: {sense_response}")

    if "error" in sense_response:
        error_message = sense_response["error"]
        error_message = _parse_l2_error_message(tid, interface, error_message)
        logger.warning(error_message)
        return False, error_message
    else:
        return True, sense_response


def _parse_l2_error_message(tid, interface, error_message):
    error_message = f"Failure Checking L2circuit Connection Status for TID: {tid} and Interface: {interface}\
, Message : {error_message}"
    return error_message


def _get_l2_connection_status(tid, interface, response_data):
    connection_status = None
    result = response_data.get("result")
    if result and result.get("l2circuit-connection-information"):
        l2circuit_information = result["l2circuit-connection-information"]
        l2circuit_neighbor = l2circuit_information.get("l2circuit-neighbor")
        if l2circuit_neighbor and l2circuit_neighbor.get("connection"):
            connection = l2circuit_information["l2circuit-neighbor"]["connection"]
            if isinstance(connection, dict) and connection.get("connection-status"):
                connection_status = connection["connection-status"]
            elif (
                isinstance(connection, list)
                and connection[0]
                and isinstance(connection[0], dict)
                and connection[0].get("connection-status")
            ):
                connection_status = connection[0]["connection-status"]
            else:
                logger.error(f"Arda L2 Status Api response format error - connection {connection}")
    logger.debug(f"TID: {tid}, Interface: {interface}, connection_status : {connection_status}")
    return connection_status


def get_combined_message(devices: "list[Device]"):
    combined_msg = {}
    for device in devices:
        combined_msg[device.tid] = device.msg
    return combined_msg


def validate_tacacs(ip):
    status = get_tacacs_status(ip)
    return {"status": status}
