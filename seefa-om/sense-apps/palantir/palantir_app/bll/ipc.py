import ipaddress
import logging

from common_sense.common.errors import abort
from palantir_app.dll.ipc import ipc_get
from palantir_app.common.endpoints import CROSSWALK_DEVICE

logger = logging.getLogger(__name__)


def get_ip_from_tid_deprecated(tid, vendor="", verbose=False):
    """Send a GET call to the Crosswalk IPC API and return the JSON-formatted response"""
    params = {"name": tid}
    data = ipc_get(CROSSWALK_DEVICE, params)
    if not data:
        logger.info(f"Crosswalk IPC Call - No device found with TID {tid}")
        return "ERROR: NO DEVICE FOUND" if verbose else None
    logger.debug(f"{vendor} {tid} Crosswalk IPC data - {data}")
    if vendor == "JUNIPER":
        ipaddr = _get_ip_from_juniper(data["devices"])
        if ipaddr:
            return ipaddr
    ip_data = data["devices"][-1]["interfaces"][0]  # Best effort selecting last entry if no mac address found
    if len(data["devices"]) > 1:  # Check for multiple IPC entries
        for x in data["devices"]:
            if x.get("resourceRecordFlag") == "true":
                ip_data = x["interfaces"][0]
                break
    if ip_data and "ipAddress" in ip_data.keys():
        ipaddr = ip_data["ipAddress"][0]
        logger.info(f"Crosswalk IPC Call - Found IP Address - {ipaddr}")
        return ipaddr
    else:
        logger.info(f"Crosswalk IPC Call - Unable to parse IP address for {tid}")
    return "ERROR: ISSUE PARSING IP ADDRESS" if verbose else None


def get_ip_from_tid(tid, vendor="") -> str:
    """Send a GET call to the Crosswalk IPC API and return the JSON-formatted response"""
    params = {"name": tid}
    data = ipc_get(CROSSWALK_DEVICE, params)
    if not data:
        logger.info(f"Crosswalk IPC Call - No device found with TID {tid}")
        return ""
    logger.debug(f"{vendor} {tid} Crosswalk IPC data - {data}")
    if vendor == "JUNIPER":
        ipaddr = _get_ip_from_juniper(data["devices"])
        if ipaddr:
            return ipaddr
    ip_data = data["devices"][-1]["interfaces"][0]  # Best effort selecting last entry if no mac address found
    if len(data["devices"]) > 1:  # Check for multiple IPC entries
        for x in data["devices"]:
            if x.get("resourceRecordFlag") == "true":
                ip_data = x["interfaces"][0]
                break
    if ip_data and "ipAddress" in ip_data.keys():
        ipaddr = ip_data["ipAddress"][0]
        logger.info(f"Crosswalk IPC Call - Found IP Address - {ipaddr}")
        return ipaddr
    else:
        logger.info(f"Crosswalk IPC Call - Unable to parse IP address for {tid}")
    return ""


def _get_ip_from_juniper(ipc_response):
    # isolate lo0 entries
    lo0_addresses = [
        ipc_entry["interfaces"] for ipc_entry in ipc_response if "lo0" in ipc_entry["interfaces"][0]["name"]
    ]
    # flatten
    lo0_addresses = [entry for ipc_entry in lo0_addresses for entry in ipc_entry]
    try:
        for ip in lo0_addresses:
            if isinstance(ipaddress.ip_address(ip["ipAddress"][0]), ipaddress.IPv4Address):
                logger.debug(f"Juniper IP address: {ip['ipAddress'][0]}")
                return ip["ipAddress"][0]
    except ValueError:
        abort(400, f"Invalid IP: {ip['ipAddress'][0]}")
    except KeyError as e:
        abort(400, f"Crosswalk ipc entry does not contain requested field: {e}")
