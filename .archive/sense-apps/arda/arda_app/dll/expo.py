import logging
import requests

from arda_app.common import app_config
from common_sense.common.errors import abort


logger = logging.getLogger(__name__)

EXPO_BASE_URL = (
    "http://vm0dnt3brma0002.corp.chartercom.com:4201"
    if app_config.USAGE_DESIGNATION == "STAGE"
    else "https://expo.corp.chartercom.com"
)


def get_expo(endpoint):
    resp = requests.get(f"{EXPO_BASE_URL}{endpoint}", verify=False, timeout=60)
    return resp.json()


def put_expo(endpoint, payload):
    logging.info(payload)
    resp = requests.put(f"{EXPO_BASE_URL}{endpoint}", json=payload, verify=False, timeout=60)
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.info(resp)
        abort(500, f"Unexpected Response from EXPO - Status Code: {resp.status_code}")


def get_order_processing():
    "Check the status and queue of EXPO stages and substages"
    return get_expo("/cwf/expo/v1/seefa/config/orderProcessing/all")


def put_order_processing(payload):
    "Pause EXPO queue or trigger"
    endpoint = "/cwf/expo/v1/seefa/config/orderProcessing"
    resp = put_expo(endpoint, payload)
    return resp
