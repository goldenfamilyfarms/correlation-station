import logging
import requests
import beorn_app
from datetime import datetime, timezone

from time import sleep
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)

SEEFA_DL = "DL-SENOE-Automation-and-Orchestration-All@charter.com"


def get_headers(override=False):
    if override or beorn_app.app_config.USAGE_DESIGNATION == "PRODUCTION":
        api_key = beorn_app.auth_config.BEORN_HYDRA_KEY
    else:
        api_key = beorn_app.auth_config.BEORN_HYDRA_STAGIUS_KEY
    headers = {
        "APPLICATION": "SENSE-BEORN",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "X-Api-Key": api_key,
        "X-Requested-With": f"username=SEEFA,useremail={SEEFA_DL},sessionid=SEEFA-Automation,"
        f"exptime={datetime.now(timezone.utc)},action=SENSE-Beorn",
    }
    return headers


def hydra_get(endpoint, params=None, failout=True):
    hydra_base_url = beorn_app.url_config.HYDRA_BASE_URL
    headers = get_headers()
    url = f"{hydra_base_url}{endpoint}"
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            r = requests.get(url, headers=headers, params=params, verify=False, timeout=60)
            if r.status_code in [200, 201, 202, 204]:
                return r.json()
            else:
                logger.error(
                    f"Hydra responded with status code: {r.status_code} for URL: {url} METHOD: GET RESPONSE: {r.text}"
                )
                if count == 2:
                    if not failout:
                        return {}
                    abort(502, f"Bad response code {r.status_code} returned for URL: {url}")

        except Exception as arg:
            logger.exception(f"Can't connect to Hydra: {url} received error: {arg}")

    if not failout:
        return {}
    abort(504, f"Timed out getting data from Hydra for URL: {url} after {count} tries")
