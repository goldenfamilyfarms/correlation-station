import logging
import requests
import time
import json

from arda_app.common import url_config, auth_config, app_config
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)

sense_usr = (
    auth_config.SENSE_TEST_SWAGGER_USER if app_config.USAGE_DESIGNATION == "STAGE" else auth_config.SENSE_SWAGGER_USER
)
sense_pass = (
    auth_config.SENSE_TEST_SWAGGER_PASS if app_config.USAGE_DESIGNATION == "STAGE" else auth_config.SENSE_SWAGGER_PASS
)


def _handle_sense_resp(url, method, resp=None, payload=None, timeout=False):
    payload_message = f"- PAYLOAD: {payload}"
    if not payload:
        payload_message = ""

    if timeout:
        logger.exception(f"ARDA - SENSE timeout - METHOD: {method} - URL: {url} {payload_message}")
        abort(500, f"SENSE timeout - METHOD: {method} - URL: {url} {payload_message}")
    else:
        if resp.status_code in (200, 201):
            try:
                return resp.json()
            except (ValueError, AttributeError):
                message = (
                    f"Failed to decode JSON for SENSE response. Status Code: {resp.status_code} "
                    f"METHOD: {method} URL: {url} RESPONSE: {resp.text}"
                )
                logger.exception(message)
                abort(500, message)
        else:
            message = (
                f"SENSE unexpected status code: {resp.status_code} METHOD: {method} "
                f"URL: {url} {payload_message} RESPONSE: {resp.text}"
            )
            logger.error(message)
            abort(500, message)


def get_sense(endpoint, payload=None, timeout=300, return_resp=False):
    """Send a GET call to the Sense API and return
    the JSON-formatted response"""
    url = f"{url_config.SENSE_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        resp = requests.get(url, headers=headers, params=payload, verify=False, timeout=timeout)
        if return_resp:
            return resp
        return _handle_sense_resp(url, "GET", resp=resp)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_sense_resp(url, "GET", timeout=True)


def put_sense(endpoint, payload, timeout=300, return_resp=False):
    """Send a PUT call to the Sense API and return
    the JSON-formatted response"""
    url = f"{url_config.SENSE_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        resp = requests.put(
            url, headers=headers, json=payload, verify=False, timeout=timeout, auth=(sense_usr, sense_pass)
        )
        if return_resp:
            return resp
        return _handle_sense_resp(url, "PUT", resp=resp)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_sense_resp(url, "PUT", timeout=True)


def post_sense(endpoint, payload, timeout=300, return_resp=False):
    """Send a POST call to the Sense API and return
    the JSON-formatted response"""
    url = f"{url_config.SENSE_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        resp = requests.post(
            url, headers=headers, json=payload, verify=False, timeout=timeout, auth=(sense_usr, sense_pass)
        )
        if return_resp:
            return resp
        return _handle_sense_resp(url, "POST", resp=resp)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_sense_resp(url, "POST", timeout=True)


def get_thor(endpoint, payload=None, timeout=300, return_resp=False):
    """Send a GET THORcall to the Sense API and return the JSON-formatted response"""
    sense_url_thor = "https://sense.chtrse.com"

    url = f"{sense_url_thor}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}

    try:
        retries = 4
        error_code = ""

        for retry in range(1, retries):
            logger.info(f"Thor check - try # {retry} of 3")
            resp = requests.get(url, headers=headers, params=payload, verify=False, timeout=timeout)

            resp_dict = json.loads(resp.text)

            # Resolving sense bug issue with None type for resp_dict
            if not isinstance(resp_dict, dict):
                msg = "No compliance data returned from Thor"
                abort(500, msg)

            if resp_dict.get("compliance") == "Fail":
                error_code = resp_dict["records"][0]["error_code"]

            if "No circuit was found with status" in error_code:
                # adding pause to help dataguard sync issues
                time.sleep(15)
            else:
                if return_resp:
                    return resp
                return _handle_sense_resp(url, "GET", resp=resp)

            if retry >= retries - 1:
                msg = (
                    f"Thor checked failed after trying multiple times, with error message: {error_code}. "
                    "Possible Dataguard issue please investigate"
                )
                logger.error(msg)
                abort(500, msg)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_sense_resp(url, "GET", timeout=True)


def get_optic_info(hostname, pe_port_number):
    """Getting light level info from optic"""
    endpoint = f"/beorn/v1/cpe/PostInstallLightLevel?device_tid={hostname}&device_port={pe_port_number}"
    beorn_response = post_sense(endpoint, payload={})
    if isinstance(beorn_response, dict):
        return beorn_response
    else:
        abort(500, f"Unable to recieve optic port information for hostname: {hostname}")
