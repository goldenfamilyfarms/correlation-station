import logging
import requests

from json import JSONDecodeError

import palantir_app
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)

sense_usr = palantir_app.auth_config.SENSE_SWAGGER_USER
sense_pass = palantir_app.auth_config.SENSE_SWAGGER_PASS
base_url = palantir_app.url_config.SENSE_BASE_URL

RETRY_MAX = 2


def sense_get(endpoint, params=None, timeout=120, best_effort=False, return_response=False):
    url = f"{base_url}/{endpoint}"
    retry = 0
    while retry <= RETRY_MAX:
        try:
            retry += 1
            r = requests.get(url, params=params, timeout=timeout, auth=(sense_usr, sense_pass))
            if return_response:
                return r
            if r.status_code == 200:
                return r.json()
            elif "SEnSE Bug" in r.text:
                return {"error": f"{r.text}"}
            elif "message" in r.json().keys():
                return {"error": f"{r.json()['message']}"}
            else:
                message = f"Unexpected response: {r.status_code} {r.text} URL: {url} and params: {params}"
                handle_request_error(retry, message, best_effort)
        # intersense calls should always respond with json and servers should be available
        # these exceptions are intermittent glitches try again while retry max allows
        except JSONDecodeError:
            message = f"{r.status_code} {r.text} {endpoint}"
            handle_request_error(retry, message, best_effort)
        except requests.ConnectTimeout:
            message = f"Could not connect to Sense after {retry} attempts for URL: {url} and params :{params}"
            handle_request_error(retry, message, best_effort)
        except (ConnectionError, requests.ConnectionError):
            message = f"Failed connecting to Sense for URL: {url} and params :{params}"
            handle_request_error(retry, message, best_effort)
        except requests.ReadTimeout:
            message = f"Connected to Sense and timed out waiting for data for URL: {url} and params :{params}"
            handle_request_error(retry, message, best_effort)


def handle_request_error(retry, message, best_effort):
    if retry >= RETRY_MAX:
        if best_effort:
            return {"error": message}
        else:
            abort(502, message)


def beorn_get(endpoint, params=None, timeout=30):
    url = f"{base_url}/beorn{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=timeout, auth=(sense_usr, sense_pass))
        if r.status_code == 200:
            return r.json()
        elif "message" in r.json().keys():
            return {"error": f"{r.json()['message']}"}
        elif "BEORN -" in r.text or "SEnSE Bug" in r.text:
            return {"error": f"{r.text}"}
        else:
            abort(502, f"Unexpected status code: {r.status_code} for URL: {url}")
    except (ConnectionError, requests.ConnectionError):
        abort(504, f"Failed connecting to Beorn for URL: {url}")
    except requests.ConnectTimeout:
        abort(504, f"Could not connect to Beorn after 1 attempt for URL: {url}")
    except requests.ReadTimeout:
        abort(504, f"Connected to Beorn and timed out waiting for data for URL: {url}")


def post_sense(endpoint, payload=None, timeout=300):
    url = f"{base_url}/{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        return requests.post(url, json=payload, headers=headers, timeout=timeout, auth=(sense_usr, sense_pass))
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, f"Timed out posting data to url: {url}")
