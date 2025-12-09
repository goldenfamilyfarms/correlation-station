import requests
import logging

import beorn_app

from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def get_eset(url, endpoint, params, timeout, best_effort=False):
    access_token = get_eset_access_token(best_effort=best_effort)
    if best_effort and not access_token:
        logger.debug("unable to use eset currently, skipping due to best effort")
        return
    headers = {"Authorization": access_token.get("accessToken"), "Accept": "application/json"}
    eset_url = f"{url}/{endpoint}"
    try:
        r = requests.get(eset_url, params=params, timeout=timeout, headers=headers, verify=False)
        if r.status_code == 200:
            return r.json()
        else:
            msg = f"Unexpected status code: {r.status_code} for URL: {eset_url}"
            if best_effort:
                logger.debug(msg)
                return
            abort(502, msg)
    except requests.ConnectTimeout:
        msg = f"Could not connect after 1 attempt for URL: {eset_url}"
        if best_effort:
            logger.debug(msg)
            return
        abort(504, msg)
    except (ConnectionError, requests.ConnectionError):
        msg = f"Failed connecting for URL: {eset_url}"
        if best_effort:
            logger.debug(msg)
            return
        abort(504, msg)
    except requests.ReadTimeout:
        msg = f"Connected but timed out waiting for data for URL: {eset_url}"
        if best_effort:
            logger.debug(msg)
            return
        abort(504, msg)


def get_eset_access_token(best_effort=False):
    endpoint = "login"
    url = f"{beorn_app.url_config.ESET_BASE_URL}/{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {"username": beorn_app.auth_config.ESET_USER, "password": beorn_app.auth_config.ESET_PASS}
    try:
        r = requests.post(url, timeout=60, json=payload, headers=headers, verify=False)
        if r.status_code == 200:
            return r.json()
        else:
            if best_effort:
                logger.debug("unable to get access token for eset")
                return
            abort(502, f"Unexpected status code: {r.status_code} for URL: {url}")
    except requests.ConnectTimeout:
        if best_effort:
            logger.debug("timed out connecting to eset for access token")
            return
        abort(504, f"Could not connect after 1 attempt for URL: {url}")
    except (ConnectionError, requests.ConnectionError):
        if best_effort:
            logger.debug("connection error while trying to get eset access token")
            return
        abort(504, f"Failed connecting to URL: {url}")
    except requests.ReadTimeout:
        if best_effort:
            logger.debug("read timeout error while trying to get eset access token")
            return
        abort(504, f"Connected but timed out waiting for data for URL: {url}")
