import logging
from time import sleep
from urllib.parse import urlencode

import requests
import urllib3

import beorn_app
from common_sense.common.errors import abort
from beorn_app.common.endpoints import DENODO_UDA, GRANITE_ELEMENTS, GRANITE_JSON_PATH, DENODO_CIRCUIT_DEVICES
from beorn_app.dll.hydra import get_headers

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

codes = {
    400: "Bad Request",
    401: "Not authorized",
    404: "Resource not found",
    403: "Access not authorized",
    500: "Server error",
}

hydra_base_url = beorn_app.url_config.HYDRA_BASE_URL


def path_update_by_parameters(headers_info, update_parameters):
    """MDSO asynchronous update using the resource API with specified json-formatted parameters"""
    try:
        response = requests.post(
            f"{hydra_base_url}{GRANITE_JSON_PATH}?validate=false",
            headers=headers_info,
            json=update_parameters,
            verify=False,
            timeout=30,
        )
        if response.json()["retCode"] != 0:
            return 400, response.json()

        return response.status_code, response.json()

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on GRANITE to process the request")
        abort(504, "Timeout waiting on GRANITE to process the request")


def call_denodo_for_circuit_devices(cid):
    headers = get_headers(override=True)
    retrycount = 0
    for _ in range(2):
        if retrycount > 0:
            sleep(3)
        try:
            r = requests.get(
                url=f"{beorn_app.url_config.HYDRA_BASE_URL}{DENODO_CIRCUIT_DEVICES}",
                headers=headers,
                params={"cid": cid},
                verify=False,
                timeout=60,
            )
            if r.status_code != 200:
                if retrycount > 0:
                    logger.exception(f"Received {r.status_code} status from granite")
                    if r.status_code == 404:
                        abort(500, "Granite Call - No records in Granite found for {}".format(cid))
                    else:
                        abort(504, "Granite Call - GRANITE failed to process the request")
                else:
                    retrycount = retrycount + 1
            else:
                denodo_elements = r.json()["elements"]

                if not denodo_elements:
                    if retrycount > 0:
                        abort(404, "Granite Call - No records in Granite found for {}".format(cid))
                    else:
                        retrycount = retrycount + 1
                else:
                    return denodo_elements

        except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError, requests.ReadTimeout):
            if retrycount > 0:
                logger.error("Timeout waiting on GRANITE to process the request")
                abort(504, "Granite Call - Timeout waiting on GRANITE to process the request")
            else:
                retrycount = retrycount + 1


def call_denodo_for_uda(**kwargs):
    params = ""

    if kwargs:
        params = urlencode(kwargs["params"])
    denodo_uda_url = (
        f"{hydra_base_url}{DENODO_UDA}?{params}&$format=json&api_key={beorn_app.auth_config.BEORN_HYDRA_KEY}"
    )
    retrycount = 0
    for _ in range(2):
        if retrycount > 0:
            sleep(3)
        try:
            r = requests.get(denodo_uda_url, verify=False, timeout=60)
            if r.status_code != 200:
                if retrycount > 0:
                    logger.exception(f"Received {r.status_code} status from granite")
                    if r.status_code == 404:
                        abort(404, "No records found for {}".format(params))
                    else:
                        abort(504, "GRANITE failed to process the request")
                else:
                    retrycount = retrycount + 1
            else:
                uda_elements = r.json()["elements"]
                if not uda_elements:
                    if retrycount > 0:
                        abort(404, "No records found for {}".format(params))
                    else:
                        retrycount = retrycount + 1
                else:
                    return uda_elements

        except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError, requests.ReadTimeout):
            if retrycount > 0:
                logger.error("Timeout waiting on GRANITE to process")
                abort(504, "Timeout waiting on GRANITE to process")
            else:
                retrycount = retrycount + 1


def get_granite_devices_from_cid(cid):
    headers = get_headers()
    if not cid:
        return None

    params = {"CIRC_PATH_HUM_ID": cid}

    try:
        r = requests.get(
            f"{beorn_app.url_config.GRANITE_BASE_URL}{GRANITE_ELEMENTS}",
            params=params,
            headers=headers,
            verify=False,
            timeout=30,
        )

        if r.status_code != 200:
            return None
        else:
            if isinstance(r.json(), list):
                granite_elements = r.json()
            else:
                return None

        if not granite_elements:
            return None

    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        return None

    tid_list = []

    granite_data_non_null_tids = [x for x in granite_elements if (x["TID"] is not None) and (x["LVL"] == "1")]
    if not granite_data_non_null_tids:
        return None

    for x in granite_data_non_null_tids:
        if x["TID"].upper()[-2:] in ["ZW", "WW", "XW", "YW"]:
            if x["TID"].upper() not in tid_list:
                tid_list.append(x["TID"].upper())
    return tid_list
