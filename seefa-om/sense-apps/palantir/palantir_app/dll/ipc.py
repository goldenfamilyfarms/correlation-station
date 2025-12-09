import logging
import requests

from time import sleep

import palantir_app

from common_sense.common.errors import abort, error_formatter, get_standard_error_summary
from palantir_app.common.utils import get_hydra_headers
from palantir_app.common.endpoints import CROSSWALK_IPADDRESS

logger = logging.getLogger(__name__)

content_type = "application/json"


def _create_token():
    try:
        r = requests.post(
            f"{palantir_app.url_config.IPC_BASE_URL}/inc-rest/api/v1/login",
            data={"username": palantir_app.auth_config.IPC_USER, "password": palantir_app.auth_config.IPC_PASS},
            verify=False,
            timeout=30,
        )
        if r.status_code == 200:
            response = r.json()
            if response:
                if "access_token" in response.keys():
                    return response["access_token"]
                else:
                    abort(502, "Unable to retrieve IPControl auth token")
            else:
                abort(502, "Unable to retrieve IPControl auth token")
        else:
            abort(r.status_code)
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.error("Timed out getting token from IPControl")
        abort(504, "Timed out getting token from IPControl")


def ipc_get(url, params, timeout=30):
    """Send a GET call to the CrossWalk IPC API and return the JSON-formatted response"""
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            r = requests.get(
                f"{palantir_app.url_config.HYDRA_BASE_URL}{url}",
                headers=get_hydra_headers(operation="ipc"),
                params=params,
                verify=False,
                timeout=timeout,
            )
            if r.status_code == 200:
                return r.json()
            else:
                logger.error(f"Unexpected response from CrossWalk IPC API for URL: {url}")
                none_found_response = _check_for_abort_scenario(r, count)
                if none_found_response:
                    return
        except (ConnectionError, requests.Timeout, requests.ConnectionError):
            logger.exception(f"Can't connect to Crosswalk: {url} raised requests connection error")

    logger.error(f"Timed out getting data from Crosswalk for url: {url}")
    abort(504, f"Timed out getting data from Crosswalk for URL: {url} after {count} tries")


def _check_for_abort_scenario(response, count):
    if response.status_code == 409:
        logger.warning(f"Nothing found in Crosswalk IPC response: {response.text}")
        return "409 not found message"
    elif "message" in response.json().keys():
        error = error_formatter("Crosswalk", "IPC", "Unexpected Response", f"{response.json()['message']}")
        abort(502, message=error, summary=get_standard_error_summary(error))
    else:
        if count == 2:
            abort(502, f"CrossWalk IPC API responded with an unexpected status code: {response.status_code}")


def ipc_post(url, payload, timeout=30):
    """Send a post call to the IPControl API and return the JSON-formatted response"""
    try:
        r = requests.post(
            f"{palantir_app.url_config.HYDRA_BASE_URL}{url}",
            headers=get_hydra_headers(operation="ipc"),
            json=payload,
            verify=False,
            timeout=timeout,
        )

        if r.status_code == 200:
            return r.json()
        else:
            logger.error(f"Unexpected response from IPControl for URL: {url}")
            if "faultString" in r.json().keys():
                abort(502, f"IPControl responded with an unexpected message: {r.json()['faultString']}")
            else:
                abort(502, f"IPControl responded with an unexpected status code: {r.status_code}")
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.error(f"Timed out getting data from IPControl for url: {url}")
        abort(504, "Timed out getting data from IPControl")


def get_device_by_hostname(tid):
    params = {"name": tid}
    ipc_entry = ipc_get(CROSSWALK_IPADDRESS, params)
    if isinstance(ipc_entry, list):
        for device in ipc_entry:
            if device.get("hostName") and tid == device["hostName"]:
                return device
        return f"No device found for {tid} in CrossWalk IPC"
    if not ipc_entry or ipc_entry.get("message") and "Device not found" in ipc_entry.get("message"):
        return f"No device found for {tid} in CrossWalk IPC"
    return ipc_entry
