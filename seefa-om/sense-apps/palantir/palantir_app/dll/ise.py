import requests
import xmltodict
import json
import logging


import palantir_app
from palantir_app.common import endpoints
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def _ise_get(base_url, endpoint, params=None, abort_mode=True):
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    url = f"{base_url}{endpoint}"
    try:
        resp = requests.get(
            url,
            headers=headers,
            params=params,
            verify=False,
            auth=(palantir_app.auth_config.ISE_USER, palantir_app.auth_config.ISE_PASS),
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"Unexpected data received from ISE: {resp.content}")
            if abort_mode:
                abort(502, f"Unexpected data received from ISE: {resp.content}")
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, f"Timed out getting data from ISE for URL: {url}")


def _ise_put(base_url, endpoint, device, timeout=30):
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    url = f"{base_url}{endpoint}"
    try:
        r = requests.put(
            url,
            json=device,
            headers=headers,
            verify=False,
            timeout=timeout,
            auth=(palantir_app.auth_config.ISE_USER, palantir_app.auth_config.ISE_PASS),
        )
        return r
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, f"Timed out putting data to ISE for URL: {url}")


def _ise_post(base_url, endpoint, device, timeout=30):
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    url = f"{base_url}{endpoint}"
    try:
        r = requests.post(
            url,
            json=device,
            headers=headers,
            verify=False,
            timeout=timeout,
            auth=(palantir_app.auth_config.ISE_USER, palantir_app.auth_config.ISE_PASS),
        )
        return r
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, f"Timed out posting data to ISE for URL: {url} and device: {device}")


def ise_west_get_cluster(endpoint, params=None, delete_device=False):
    west_cubes = palantir_app.url_config.ISE_CUBES_WEST
    west_results = []
    for cube in west_cubes:
        try:
            response = _ise_get(west_cubes[cube], endpoint, params, False)
        except (ConnectionError, requests.Timeout, requests.ConnectionError):
            abort(504, f"Timed out Getting data from ISE for URL: {west_cubes[cube]} and endpoint: {endpoint}")
        if response and response.get("SearchResult") and response["SearchResult"]["total"] != 0:
            west_results.append(response)
            if delete_device:
                _delete_ise_device(west_cubes[cube], response["SearchResult"]["resources"][0]["id"])
        if response and response.get("NetworkDevice") and response["NetworkDevice"]["id"]:
            west_results.append(response.get("NetworkDevice"))
            if delete_device:
                _delete_ise_device(west_cubes[cube], response["NetworkDevice"]["id"])
    return west_results


def ise_east_get_cluster(endpoint, params=None, delete_device=False):
    east_cubes = palantir_app.url_config.ISE_CUBES_EAST
    east_results = []
    for cube in east_cubes:
        try:
            response = _ise_get(east_cubes[cube], endpoint, params, False)
        except (ConnectionError, requests.Timeout, requests.ConnectionError):
            abort(504, f"Timed out Getting data from ISE for URL: {east_cubes[cube]} and endpoint: {endpoint}")
        if response and response.get("SearchResult") and response["SearchResult"]["total"] != 0:
            east_results.append(response)
            if delete_device:
                _delete_ise_device(east_cubes[cube], response["SearchResult"]["resources"][0]["id"])
        if response and response.get("NetworkDevice") and response["NetworkDevice"]["id"]:
            east_results.append(response.get("NetworkDevice"))
            if delete_device:
                _delete_ise_device(east_cubes[cube], response["NetworkDevice"]["id"])
    return east_results


def ise_south_get_cluster(endpoint, params=None, delete_device=False):
    south_cubes = palantir_app.url_config.ISE_CUBES_SOUTH
    south_results = []
    for cube in south_cubes:
        try:
            response = _ise_get(south_cubes[cube], endpoint, params, False)
        except (ConnectionError, requests.Timeout, requests.ConnectionError):
            abort(504, f"Timed out Getting data from ISE for URL: {south_cubes[cube]} and endpoint: {endpoint}")
        if response and response.get("SearchResult") and response["SearchResult"]["total"] != 0:
            south_results.append(response)
            if delete_device:
                _delete_ise_device(south_cubes[cube], response["SearchResult"]["resources"][0]["id"])
        if response and response.get("NetworkDevice") and response["NetworkDevice"]["id"]:
            south_results.append(response.get("NetworkDevice"))
            if delete_device:
                _delete_ise_device(south_cubes[cube], response["NetworkDevice"]["id"])
    return south_results


def _delete_ise_device(ise_url, ise_host_id):
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    endpoint = f"{endpoints.ISE_NETWORK_DEVICE}/{ise_host_id}"
    url = f"{ise_url}{endpoint}"
    timeout = 30
    try:
        r = requests.delete(
            url,
            headers=headers,
            verify=False,
            timeout=timeout,
            auth=(palantir_app.auth_config.ISE_USER, palantir_app.auth_config.ISE_PASS),
        )

        if r.status_code == 400:
            abort(400, r.json()["ERSResponse"]["messages"][0]["title"])
        return 200, "Success"
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, f"Timed out deleting device from ISE for URL: {url} and Host ID: {ise_host_id}")


def get_host_id(ise_url, hostname):
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    endpoint = "ers/config/networkdevice"
    url = f"{ise_url}{endpoint}"
    timeout = 30
    params = {"filter": "name.EQ." + hostname}
    try:
        resp = requests.get(
            url,
            headers=headers,
            params=params,
            verify=False,
            timeout=timeout,
            auth=(palantir_app.auth_config.ISE_USER, palantir_app.auth_config.ISE_PASS),
        )
        if resp.status_code == 200:
            data_dict = xmltodict.parse(resp.text)
            resp_json = json.dumps(data_dict)
            return resp_json["SearchResult"]["resources"][0]["id"]
        else:
            abort(502, f"Unexpected data received from ISE: {resp.content}")
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, f"Timed out getting data from ISE for URL: {url}")
