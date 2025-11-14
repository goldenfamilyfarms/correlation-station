from copy import deepcopy

from common_sense.common.errors import abort
from common_sense.dll.sense import get_sense


def verify_device_connectivity(hostname: str = "", cid: str = "", core_only: bool = False):
    """Verify device connectivity and return the status of the device
    :param hostname: the hostname of the device
    :param cid: the cid of the device
    :param core_only: if True, only return the status of core devices
    :return: pass through palantir/v1/device_validator response
    """
    response = get_device_validation(hostname, cid)
    # 200 means no issues found during device validation
    if response.status_code == 200:  # this will always be a response obj
        return response.json()
    else:
        response = response.json()
        msg = response["message"]
        if core_only:
            # do not abort for CPE fails if core only
            return validated_core_devices(msg)
        summary = response.get("summary")
        abort(502, msg, summary=summary)


def get_device_validation(hostname: str = "", cid: str = ""):
    palantir_endpoint = "/palantir/v2/device_validator"
    if cid:
        payload = {"cid": cid}
    else:
        payload = {"tid": hostname}
    return get_sense(palantir_endpoint, payload=payload, return_resp=True)


def validated_core_devices(devices_message):
    core_devices_only = deepcopy(devices_message)
    failed_core_devices = []
    for device in devices_message:
        if not _is_core_device(device):
            core_devices_only.pop(device)
            continue  # we only care about core here
        for validation in devices_message[device]:  # iterate over all for full data picture
            if devices_message[device][validation].get("status") != "validated":
                failed_core_devices.append(device)
                break
    # abort if failures, otherwise return the curated core response
    if failed_core_devices:
        abort(502, core_devices_only)
    return core_devices_only


def _is_core_device(tid):
    return tid[-2:] in ["CW", "QW"]
