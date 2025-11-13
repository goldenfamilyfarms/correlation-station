import logging
import re

from common_sense.common.errors import abort
from palantir_app.bll.device_deprecated import Device
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


def _abort_502(device, l2error=None, verbose: bool = False):
    if verbose:
        if isinstance(device, list):
            abort(502, message=get_combined_message(device, l2error))
        else:
            abort(502, message=combine_single_device_messages(device, l2error))
    else:
        if isinstance(device, list):
            abort(502, message=device_validator_clean_abort(get_combined_message(device, l2error), core_only=False))
        else:
            abort(
                502,
                message=device_validator_clean_abort(combine_single_device_messages(device, l2error), core_only=False),
            )


def get_combined_message(devices: "list[Device]", l2error=None):
    combined_msg = {}
    for device in devices:
        combined_msg[device.tid] = device.msg
    if l2error:
        combined_msg["L2Circuit Error"] = l2error
    return combined_msg


def combine_single_device_messages(device: Device, l2error=None):
    combined_msg = {}
    combined_msg[device.tid] = device.msg
    if l2error:
        combined_msg["L2Circuit Error"] = l2error
    return combined_msg


def validate_device_single(tid: str, acceptance: bool = False, verbose: bool = False):
    # Grab FQDN and check IP in granite
    granite_data = get_fqdn_ip_vendor_from_tid(tid)
    fqdn = granite_data["FQDN"]
    granite_ip = granite_data["IPV4_ADDRESS"]
    granite_vendor = granite_data["VENDOR"]
    # Need to check provided ip and granite IP
    device = [granite_ip, tid, fqdn, None, None, granite_vendor, None, None, None]
    device = Device(device)
    if device.is_err_state:
        _abort_502(device, verbose=verbose)

    # Calls the validate
    l2error = validation_process(device, acceptance)

    if device.is_err_state or l2error:
        _abort_502(device, l2error, verbose)

    if verbose:
        return {"message": combine_single_device_messages(device)}, 200
    else:
        return {"message": device_validator_clean_abort(combine_single_device_messages(device), core_only=False)}, 200


def validate_device_circuit(cid: str = "", acceptance: bool = False, verbose: bool = False):
    logger.info("---------------STARTING CID DEVICE CHECK---------------")
    l2error = None
    # Step 1: Gather CID, TID, IP from Provided or Granite
    service_type, circuit_devices = _get_cid_data(cid)

    def _skip_tid(device_tid: str):
        if not re.match(".{9}[ACTQWXYZ0-9]W", device_tid.upper()):
            logger.info(f"Skipping TID: {device_tid}")
            return True

        return False

    if not circuit_devices:
        abort(404, message="No record found")

    devices = [
        Device(device_attributes, cid)
        for device_attributes in circuit_devices
        if not _skip_tid(device_attributes[1][0:11])
    ]
    if any(device.is_err_state for device in devices) or l2error:
        _abort_502(devices, l2error, verbose)

    l2error = [validation_process(device, service_type, acceptance) for device in devices]

    l2error = [err for err in l2error if err is not None]

    l2error = "\n".join(map(str, l2error))

    if any(device.is_err_state for device in devices) or l2error:
        _abort_502(devices, l2error, verbose)

    if verbose:
        return {"message": get_combined_message(devices)}, 200
    else:
        return {"message": device_validator_clean_abort(get_combined_message(devices), core_only=False)}, 200


def _get_cid_data(cid, old_process=False):
    """Returns list of dictionaries containing device IPs and TIDs for CID from Granite"""
    records = get_circuit_devices(cid)
    for element in records:
        if element["PATH_NAME"] == cid:
            break
    else:
        abort(404, "GRANITE CALL - PATH_NAME DOES NOT MATCH CID ENTERED")
    service_type = records[0]["SERVICE_TYPE"]
    if service_type in UNSUPPORTED_ACCEPTANCE_SERVICE_TYPES:
        abort(502, f"GRANITE CALL - SERVICE TYPE {service_type} UNSUPPORTED")
    if not service_type:
        abort(502, "GRANITE CALL - SERVICE TYPE UNDEFINED")
    devices = records
    latest_rev_id = _get_latest_revision_id(devices)
    circuit_devices = _get_circuit_devices(devices, old_process, latest_rev_id)
    if not circuit_devices:
        abort(404, "GRANITE CALL - NO DEVICE LIST FOUND")
    logger.info(f"GRANITE CALL - SERVICE TYPE: {service_type}")
    logger.info(f"GRANITE CALL - Device List: {circuit_devices}")
    return service_type, circuit_devices


def _get_latest_revision_id(devices):
    # Determine the latest revision of the CID
    latest_rev_id = ""
    for dev in devices:
        if dev["INITIAL_CIRCUIT_ID"] is None:
            abort(404, "GRANITE CALL - INITIAL CID NOT FOUND")
        elif dev["INITIAL_CIRCUIT_ID"] == "":
            abort(502, "GRANITE CALL - REVISION ID UNDEFINED")
        elif dev["INITIAL_CIRCUIT_ID"] > latest_rev_id:
            latest_rev_id = dev["INITIAL_CIRCUIT_ID"]
    return latest_rev_id


def _get_circuit_devices(devices, old_process, latest_rev_id):
    # Skip devices with no equipment type and save device IP & TID if it isn't on the list already
    circuit_devices = []
    for dev in devices:
        # Due to Granite changes, determine which key refers to the device's management IP address
        dev_ip = _get_device_ip_from_granite(dev, old_process)
        if dev["INITIAL_CIRCUIT_ID"] == latest_rev_id:
            if not dev["ELEMENT_CATEGORY"]:
                continue
            elif dev["TID"] and dev["TID"] not in [x[1] for x in circuit_devices]:
                if len(dev["TID"][0:11]) != 11:
                    abort(502, "GRANITE CALL - INVALID TID")
                circuit_devices.append(
                    (
                        dev_ip,
                        dev["TID"],
                        dev["FQDN"],
                        dev.get("PORT_ACCESS_ID"),
                        dev.get("S_VLAN"),
                        dev.get("VENDOR"),
                        dev.get("CHAN_NAME"),
                        dev.get("ELEMENT_CATEGORY"),
                        dev.get("LEG_NAME"),
                    )
                )
    return circuit_devices


def _get_device_ip_from_granite(device, old_process):
    if "MANAGEMENT_IP" in device.keys():
        return device["MANAGEMENT_IP"]
    elif "IPV4_ADDRESS" in device.keys() and device["IPV4_ADDRESS"]:
        return device["IPV4_ADDRESS"]
    elif "IPV6_ADDRESS" in device.keys() and device["IPV6_ADDRESS"]:
        return device["IPV6_ADDRESS"]
    else:
        if old_process:
            abort(502, "GRANITE CALL - UNABLE TO RETRIEVE IP")


def validation_process(device: Device, service_type=None, acceptance: bool = False):
    logger.info("---------------STARTING SINGLE DEVICE CHECK---------------")
    # If no error state then we move on to LOGIN Step
    # First Gather the Vendor and Model via SNMP
    device.determine_vendor_and_model()

    # Attempt LOGIN if failed and not CPE Mark and abort after
    device.determine_tacacs()

    # If Remediation is needed remediate
    if device.tacacs_remediation_required:
        device.remediate_tacacs()

        # New ISE Remediation Process
        device.ise_check()

        # Check TACACS Status if ISE is good
        if device.ise_success:
            device.determine_tacacs()

    # align databases with usable IP value
    device.remediate_boundary()

    # set device error state based on validation process results
    device.set_is_err_state()

    # If acceptance flow then process acceptance specific needs
    if acceptance:
        # L2 Circuit Verification Check
        if is_l2circuit_service_eligible(service_type):
            return l2circuit_connection_status_check(device)


def is_l2circuit_service_eligible(service_type):
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


def l2circuit_connection_status_check(device: Device):
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
        return

    connection_status = _get_l2_connection_status(device.tid, interface, response_data)

    if connection_status and connection_status != "Up":
        return f"l2circuit is not up, please investigate potential test loop - \
        TID : {device.tid} , Interface : {interface}, Connection Status : {connection_status}"


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
    if (not vlan or vlan == "") and (chan_name and chan_name != ""):
        vlan = str(re.search(r"\d+", chan_name).group(0))
    return vlan


def is_l2circuit_port_valid(port):
    if not port or port == "":
        return False
    else:
        return True


def is_l2circuit_vlan_valid(vlan):
    if not vlan or vlan == "":
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


def validate_tacacs(ip):
    status = get_tacacs_status(ip)
    return {"status": status}


def device_validator_clean_abort(response, core_only):
    msg = {}
    r = _flatten_dict(response)
    error_vals = ["ERROR", "FAILED", "NOT FOUND"]
    for device, validated in r.items():
        tid = device.split(".")[0].upper()
        if core_only and not _is_core_device(tid):
            continue
        # if validated is a bool, we're dealing with fqdn reachable true/false
        if isinstance(validated, bool):
            # if True or if CPE, we are unconcerned
            if validated or _is_cpe_device(tid):
                continue
            _set_msg(msg, tid, device.split(".")[-1])
        elif any(error in validated for error in error_vals):
            error_val = device.split(".")[-1] if device.split(".")[-1] != "STATUS" else device.split(".")[-2]
            _set_msg(msg, tid, error_val)
        if device == "L2Circuit Error":
            _set_msg(msg, "L2Circuit Error", validated)
    return msg


def _flatten_dict(d, parent_key="", sep="."):
    # Flatten dictionary
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _set_msg(msg, tid, error_val):
    if msg.get(tid):
        msg[tid].append(error_val)
    else:
        msg[tid] = [error_val]
    return msg


def _is_core_device(tid):
    return tid[-2:] in ["CW", "QW"]


def _is_cpe_device(tid):
    return tid.endswith("ZW")
