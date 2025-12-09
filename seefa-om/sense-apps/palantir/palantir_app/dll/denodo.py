import logging
from time import sleep

import requests

import palantir_app
from common_sense.common.errors import abort
from palantir_app.common.utils import get_hydra_headers
from palantir_app.common.endpoints import DENODO_CIRCUIT_DEVICES, DENODO_SEEK_TID

logger = logging.getLogger(__name__)


def denodo_get(endpoint, params=None, operation=""):
    headers = get_hydra_headers(operation)
    url = f"{palantir_app.url_config.HYDRA_BASE_URL}{endpoint}"
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            r = requests.get(url, headers=headers, params=params, verify=False, timeout=60)
            if 200 <= r.status_code <= 299:
                return r.json()
            else:
                logger.error(
                    f"Hydra responded with status code: {r.status_code} for URL: {url} METHOD: GET RESPONSE: {r.text}"
                )
                if count == 2:
                    abort(502, f"Bad response code {r.status_code} returned for URL: {url}")

        except Exception as arg:
            logger.exception(f"Can't connect to Hydra: {url}<key> received error: {arg}")

    abort(504, f"Timed out getting data from Hydra for URL: {url}<key> after {count} tries")


def get_target_and_vendor(tid):
    """Gets target and vendor for TID as a tuple (target, vendor)"""
    params = {"device_tid": tid}
    json_resp = denodo_get(DENODO_SEEK_TID, params=params)
    elems = json_resp["elements"]
    if len(elems) >= 1:
        if "eq_target" in elems[0] and "eq_vendor" in elems[0]:
            return elems[0]["eq_target"], elems[0]["eq_vendor"]
    else:
        abort(404, f"No device found in Hydra for TID: {tid}")
    abort(502, f"Did not receive equipment data from Hydra for TID: {tid}")


def get_circuit_devices(cid):
    circuit_devices = denodo_get(DENODO_CIRCUIT_DEVICES, params={"cid": cid})["elements"]
    if not circuit_devices:
        abort(502, f"No records found from denodo call for {cid}")
    return circuit_devices
