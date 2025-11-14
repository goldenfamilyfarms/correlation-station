import ipaddress
import logging

from common_sense.common.errors import abort
from beorn_app.dll.hydra import hydra_get
from beorn_app.common.endpoints import CROSSWALK_DEVICE

logger = logging.getLogger(__name__)


def get_ip_from_tid(tid, vendor="", failout=True):
    """Send a GET call to the Hydra Crosswalk API and return the JSON-formatted response"""
    params = {"name": tid}
    data = hydra_get(CROSSWALK_DEVICE, params, failout=failout).get("devices")
    if data is None:
        logger.debug(f"Crosswalk data - call returned None for {tid}")
        return None
    logger.debug(f"{vendor} {tid} Crosswalk data - {data}")
    if vendor == "JUNIPER":
        return _get_ip_from_juniper(data)
    else:
        ip_data = data[-1]["interfaces"][0]  # Best effort selecting last entry if no mac address found
        if len(data) > 1:  # Check for multiple IPC entries
            for x in data:
                if "macAddress" in x["interfaces"][0].keys():  # Select entry with macAddress set by field tech
                    ip_data = x["interfaces"][0]
                    break
        if ip_data and "ipAddress" in ip_data.keys():
            ipaddr = ip_data["ipAddress"][0]
            logger.debug(f"ipaddr - {ipaddr}")
            return ipaddr
    return None


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
                logger.debug(f"ip address: {ip['ipAddress'][0]}")
                return ip["ipAddress"][0]
    except ValueError:
        abort(400, f"Invalid IP: {ip['ipAddress'][0]}")
    except KeyError as e:
        abort(400, f"Crosswalk entry does not contain requested field: {e}")
