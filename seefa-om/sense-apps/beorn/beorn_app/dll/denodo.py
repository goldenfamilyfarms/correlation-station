import logging
from time import sleep

import requests

import beorn_app
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def denodo_hydra_get(endpoint):
    hydra_base_url = beorn_app.url_config.HYDRA_BASE_URL
    url = f"{hydra_base_url}{endpoint}"
    retrycount = 0
    for _ in range(2):
        if retrycount > 0:
            sleep(3)
        try:
            r = requests.get(url, verify=False, timeout=60)
            if r.status_code in [200, 201, 202, 204]:
                return r.json()
            else:
                if retrycount > 0:
                    abort(502, f"Bad response code from Hydra returned for URL: {url[: len(url) - 40]}<key>")
                else:
                    retrycount = retrycount + 1
        except (ConnectionError, requests.Timeout, requests.ConnectionError):
            if retrycount > 0:
                logger.exception("Can't connect to Hydra")
                abort(504, f"Timed out getting data from Hydra for URL: {url[: len(url) - 40]}<key>")
            else:
                retrycount = retrycount + 1


def denodo_get(endpoint, **kwargs):
    beorn_hydra_key = beorn_app.auth_config.BEORN_HYDRA_KEY
    hydra_base_url = (
        beorn_app.url_config.HYDRA_BASE_URL.removesuffix("/qa")
        if beorn_app.app_config.USAGE_DESIGNATION == "STAGE"
        else beorn_app.url_config.HYDRA_BASE_URL.removesuffix("/prod")
    )
    url = f"{hydra_base_url}{endpoint}&api_key={beorn_hydra_key}"
    retrycount = 0
    for _ in range(2):
        if retrycount > 0:
            sleep(3)
        try:
            r = requests.get(url, verify=False, timeout=60)
            if r.status_code // 100 == 2:
                return r.json()
            else:
                if retrycount > 0:
                    abort(502, f"Bad response code from Hydra returned for URL: {url[: len(url) - 40]}<key>")
                else:
                    retrycount = retrycount + 1
        except (ConnectionError, requests.Timeout, requests.ConnectionError):
            if retrycount > 0:
                logger.exception("Can't connect to Hydra")
                abort(504, f"Timed out getting data from Hydra for URL: {url[: len(url) - 40]}<key>")
            else:
                retrycount = retrycount + 1
