import logging

import requests
from common_sense.common.errors import abort

try:
    from arda_app.common import url_config

    app_name = "ARDA"
    new_way = True
except ImportError:
    try:
        import beorn_app as app

        app_name = "BEORN"
        new_way = False
    except ImportError:
        import palantir_app as app

        app_name = "Palantir"
        new_way = False


logger = logging.getLogger(__name__)


def pull_creds():
    # creds = get_creds("sense")

    # sense_user = creds["un"]
    # sense_pass = creds["pw"]
    sense_user = app.auth_config.SENSE_SWAGGER_USER
    sense_pass = app.auth_config.SENSE_SWAGGER_PASS
    return sense_user, sense_pass


"""
FROM ARDA
"""


def _handle_sense_resp(url, method, resp=None, payload=None, timeout=False):
    payload_message = f"- PAYLOAD: {payload}"
    if not payload:
        payload_message = ""

    if timeout:
        logger.exception(f"{app_name} - SENSE timeout - METHOD: {method} - URL: {url} {payload_message}")
        abort(504, f"{app_name} - SENSE timeout - METHOD: {method} - URL: {url} {payload_message}")
    else:
        if resp.status_code in (200, 201):
            try:
                return resp.json()
            except (ValueError, AttributeError):
                message = (
                    f"{app_name} - Failed to decode JSON for SENSE response. Status Code: {resp.status_code} "
                    f"METHOD: {method} URL: {url} RESPONSE: {resp.text}"
                )
                logger.exception(message)
                abort(502, message)
        else:
            message = (
                f"{app_name} - SENSE unexpected status code: {resp.status_code} METHOD: {method} "
                f"URL: {url} {payload_message} RESPONSE: {resp.text}"
            )
            logger.error(message)
            abort(502, message)


def get_sense(endpoint, payload=None, timeout=300, return_resp=False):
    """Send a GET call to the Sense API and return
    the JSON-formatted response"""
    if new_way:
        url = f"{url_config.SENSE_BASE_URL}{endpoint}"
    else:
        url = f"{app.url_config.SENSE_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        resp = requests.get(url, headers=headers, params=payload, verify=False, timeout=timeout)
        if return_resp:
            return resp
        return _handle_sense_resp(url, "GET", resp=resp)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        return _handle_sense_resp(url, "GET", timeout=True)


def put_sense(endpoint, payload, timeout=300, return_resp=False):
    """Send a PUT call to the Sense API and return
    the JSON-formatted response"""
    url = f"{app.app.config['SENSE_BASE_URL']}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    sense_user, sense_pass = pull_creds()
    try:
        resp = requests.put(
            url,
            headers=headers,
            json=payload,
            verify=False,
            timeout=timeout,
            auth=(sense_user, sense_pass),
        )
        if return_resp:
            return resp
        return _handle_sense_resp(url, "PUT", resp=resp)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_sense_resp(url, "PUT", timeout=True)


def post_sense(endpoint, payload, timeout=300, return_resp=False):
    """Send a POST call to the Sense API and return
    the JSON-formatted response"""
    url = f"{app.url_config.SENSE_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    sense_user, sense_pass = pull_creds()
    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=False,
            timeout=timeout,
            auth=(sense_user, sense_pass),
        )
        if return_resp:
            return resp
        return _handle_sense_resp(url, "POST", resp=resp)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_sense_resp(url, "POST", timeout=True)


"""
FROM BEORN
"""


def sense_get(service, endpoint, params=None, timeout=30):
    base_url = app.url_config.SENSE_BASE_URL
    url = f"{base_url}/{service}/{endpoint}"
    sense_user, sense_pass = pull_creds()
    try:
        r = requests.get(url, params=params, timeout=timeout, auth=(sense_user, sense_pass))
        if r.status_code == 200:
            return r.json()
        else:
            abort(502, f"{app_name} - Unexpected status code: {r.status_code} for URL: {url}")
    except (ConnectionError, requests.ConnectionError):
        abort(504, f"{app_name} - Failed connecting to {service} for URL: {url}")
    except requests.ConnectTimeout:
        abort(504, f"{app_name} - Could not connect to {service} after 1 attempt for URL: {url}")
    except requests.ReadTimeout:
        abort(504, f"{app_name} - Connected to {service} and timed out waiting for data for URL: {url}")


def sense_post(service, endpoint, timeout=60, best_effort=False, **payload_data):
    base_url = app.url_config.SENSE_BASE_URL
    url = f"{base_url}/{service}/{endpoint}"
    sense_user, sense_pass = pull_creds()
    try:
        r = requests.post(url=url, **payload_data, timeout=timeout, auth=(sense_user, sense_pass))
        if best_effort or r.status_code in (200, 201, 202):
            return r
        else:
            abort(502, f"BEORN - Unexpected status code: {r.status_code} for URL: {url}", f"Response: {r.json()}")
    except (ConnectionError, requests.ConnectionError):
        error = f"BEORN - Failed connecting to {service} for URL: {url}"
        return error if best_effort else abort(504, error)
    except requests.ConnectTimeout:
        error = f"BEORN - Could not connect to {service} after 1 attempt for URL: {url}"
        return error if best_effort else abort(504, error)
    except requests.ReadTimeout:
        error = f"BEORN - Connected to {service} and timed out waiting for data for URL: {url}"
        return error if best_effort else abort(504, error)


"""
FROM Palantir
"""


def beorn_get(endpoint, params=None, timeout=30):
    base_url = app.url_config.SENSE_BASE_URL
    url = f"{base_url}/beorn{endpoint}"
    sense_user, sense_pass = pull_creds()
    try:
        r = requests.get(url, params=params, timeout=timeout, auth=(sense_user, sense_pass))
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 501 and "message" in r.json().keys():
            return {"error": f'{r.json()["message"]}'}
        else:
            abort(502, f"{app_name} - Unexpected status code: {r.status_code} for URL: {url}")
    except (ConnectionError, requests.ConnectionError):
        abort(504, f"{app_name} - Failed connecting to Beorn for URL: {url}")
    except requests.ConnectTimeout:
        abort(504, f"{app_name} - Could not connect to Beorn after 1 attempt for URL: {url}")
    except requests.ReadTimeout:
        abort(504, f"{app_name} - Connected to Beorn and timed out waiting for data for URL: {url}")
