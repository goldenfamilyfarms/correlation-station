import requests

import beorn_app

from common_sense.common.errors import abort

sense_usr = beorn_app.auth_config.SENSE_SWAGGER_USER
sense_pass = beorn_app.auth_config.SENSE_SWAGGER_PASS


def sense_get(service, endpoint, params=None, timeout=30):
    base_url = beorn_app.url_config.SENSE_BASE_URL
    url = f"{base_url}/{service}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=timeout, auth=(sense_usr, sense_pass))
        if r.status_code == 200:
            return r.json()
        else:
            abort(502, f"Unexpected status code: {r.status_code} for URL: {url}")
    except (ConnectionError, requests.ConnectionError):
        abort(504, f"Failed connecting to {service} for URL: {url}")
    except requests.ConnectTimeout:
        abort(504, f"Could not connect to {service} after 1 attempt for URL: {url}")
    except requests.ReadTimeout:
        abort(504, f"Connected to {service} and timed out waiting for data for URL: {url}")


def sense_post(service, endpoint, timeout=60, best_effort=False, **payload_data):
    base_url = beorn_app.url_config.SENSE_BASE_URL
    url = f"{base_url}/{service}/{endpoint}"
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        r = requests.post(url=url, headers=headers, **payload_data, timeout=timeout, auth=(sense_usr, sense_pass))
        if best_effort or r.status_code in (200, 201, 202):
            return r
        else:
            abort(502, f"Unexpected status code: {r.status_code} for URL: {url} Response: {r.json()}")
    except (ConnectionError, requests.ConnectionError):
        error = f"Failed connecting to {service} for URL: {url}"
        return error if best_effort else abort(504, error)
    except requests.ReadTimeout:
        error = f"Connected to {service} and timed out waiting for data for URL: {url}"
        return error if best_effort else abort(504, error)
