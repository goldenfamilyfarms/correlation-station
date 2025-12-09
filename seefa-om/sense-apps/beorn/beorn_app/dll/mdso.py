import requests
import urllib3
import logging

from time import sleep

import beorn_app

from common_sense.common.errors import abort
from beorn_app.common.mdso_operations import resource_status

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RESOURCES_PATH = "/bpocore/market/api/v1/resources"


def _create_token():
    """get a token to authenticate calls to MDSO"""
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    data = {
        "username": beorn_app.auth_config.MDSO_USER,
        "password": beorn_app.auth_config.MDSO_PASS,
        "tenant": "master",
        "expires_in": 60,
        "grant_type": "password",
    }
    try:
        logger.info(data)
        logger.info(f"{beorn_app.url_config.MDSO_BASE_URL}/tron/api/v1/oauth2/tokens")
        r = requests.post(
            f"{beorn_app.url_config.MDSO_BASE_URL}/tron/api/v1/oauth2/tokens",
            headers=headers,
            json=data,
            verify=False,
            timeout=30,
        )
        if r.status_code in [200, 201]:
            try:
                return r.json()["accessToken"]
            except ValueError:
                abort(502, "Could not parse response from MDSO for authentication")
        else:
            abort(502, f"Error Code: M001 - Unexpected status code: {r.status_code} at authentication with MDSO")
    except (ConnectionError, requests.ConnectionError):
        abort(502, "Failed to initialize connection to MDSO to complete authentication")
    except requests.ReadTimeout:
        abort(504, "Error Code: M002 - Timed out reading data from MDSO during authentication")
    except Exception:
        abort(502, "Unknown exception occurred during authentication with MDSO")


def _delete_token(token):
    if token:
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {token}"}
        requests.delete(
            f"{beorn_app.url_config.MDSO_BASE_URL}/tron/api/v1/oauth2/tokens/{token}",
            headers=headers,
            verify=False,
            timeout=300,
        )


def mdso_get(endpoint, timeout=30):
    token = _create_token()
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    try:
        r = requests.get(
            f"{beorn_app.url_config.MDSO_BASE_URL}{endpoint}", headers=headers, timeout=timeout, verify=False
        )
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                abort(502, f"Could not parse response from MDSO for endpoint: {endpoint}")
        else:
            abort(
                502,
                f"Error Code: M003 - Unexpected status code: {r.status_code} returned from MDSO endpoint: {endpoint}",
            )
    except (ConnectionError, requests.ConnectionError):
        abort(502, f"Failed to initialize connection to MDSO to complete: {endpoint}")
    except requests.ReadTimeout:
        abort(504, f"Error Code: M004 - Timed out reading data from MDSO to complete {endpoint}")
    finally:
        _delete_token(token)


def mdso_post(endpoint, data, timeout=30, resync=False):
    token = _create_token()
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        r = requests.post(
            f"{beorn_app.url_config.MDSO_BASE_URL}{endpoint}", headers=headers, json=data, verify=False, timeout=timeout
        )
        if r.status_code == 201:
            try:
                return r.json()
            except ValueError:
                abort(502, f"MDSO POST - Could not parse response from MDSO for endpoint: {endpoint} | payload: {data}")
        elif r.status_code == 202 and resync:
            try:
                return r.json()
            except ValueError:
                abort(502, f"MDSO POST - Could not parse response from MDSO for endpoint: {endpoint} | payload: {data}")
        else:
            abort(
                502,
                f"Error Code: M005 - MDSO POST - Unexpected status code: {r.status_code} "
                f"returned from MDSO endpoint: {endpoint} | payload: {data}",
            )
    except (ConnectionError, requests.ConnectionError):
        abort(502, f"MDSO POST - Failed to initialize connection to MDSO for endpoint: {endpoint} | payload: {data}")
    except requests.ReadTimeout:
        abort(
            504,
            "Error Code: M006 - MDSO POST - "
            f"Timed out reading data from MDSO for endpoint: {endpoint} | payload: {data}",
        )
    except Exception:
        abort(502, f"MDSO POST - Unknown exception occurred at MDSO for endpoint: {endpoint} | payload: {data}")
    finally:
        _delete_token(token)


def mdso_post_request(endpoint, data, timeout=30):
    token = _create_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        r = requests.post(
            f"{beorn_app.url_config.MDSO_BASE_URL}{endpoint}", headers=headers, data=data, verify=False, timeout=timeout
        )
        if r.status_code == 201:
            try:
                return r.json()
            except ValueError:
                abort(502, f"MDSO POST - Could not parse response from MDSO for endpoint: {endpoint} | payload: {data}")
        else:
            abort(
                502,
                f"Error Code: M005 - MDSO POST - Unexpected status code: {r.status_code} "
                f"returned from MDSO endpoint: {endpoint} | payload: {data}",
            )
    except (ConnectionError, requests.ConnectionError):
        abort(502, f"MDSO POST - Failed to initialize connection to MDSO for endpoint: {endpoint} | payload: {data}")
    except requests.ReadTimeout:
        abort(
            504,
            "Error Code: M006 - MDSO POST - "
            f"Timed out reading data from MDSO for endpoint: {endpoint} | payload: {data}",
        )
    except Exception:
        abort(502, f"MDSO POST - Unknown exception occurred at MDSO for endpoint: {endpoint} | payload: {data}")
    finally:
        _delete_token(token)


def service_id_lookup(cid, resource_type="NetworkService"):
    # def service_id_lookup(cid):
    query = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.{resource_type}"
        f"&offset=0&limit=1000&q=properties.circuit_id:{cid}"
    )

    resp = mdso_get(query)["items"]

    if len(resp) > 0:
        return resp[0].get("id")
    else:
        return None


# This method is added because it accommodates the complexity of doing a service id lookup for an existing
# service, in the case of polling palantir for resource id rather than EXPO calling it. (not in use)
def service_update_id_lookup(cid):
    query = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.Network"
        f"ServiceUpdate&offset=0&limit=1000&q=properties.circuit_id:{cid}"
    )
    resp = mdso_get(query)
    total = int(resp["total"])
    resp = resp["items"]
    if len(resp) > 0:
        return resp[total - 1].get("id")
    else:
        return None


def service_details(cid, resource_type):
    query = f"{RESOURCES_PATH}?resourceTypeId={resource_type}&q=properties.circuit_id:{cid}&offset=0&limit=1000"
    return mdso_get(query)


def product_query(product_name):
    """GET call for the product id."""
    url = "/bpocore/market/api/v1/products"
    query = f"{url}?includeInactive=false&q=resourceTypeId%3Acharter.resourceTypes.{product_name}&offset=0&limit=1000"
    product_items = mdso_get(query).get("items")
    if product_items:
        if isinstance(product_items, list):
            product_id = product_items[0].get("id")
            if product_id:
                return product_id
    abort(
        502, f"MDSO Product Query - Unexpected data from MDSO - could not find the product ID for product {product_name}"
    )


def create_service(payload):
    """Used to update or create a service. Returns success or failure reason."""
    resource_id = mdso_post(f"{RESOURCES_PATH}?validate=false", payload).get("id")
    if resource_id:
        return resource_id
    abort(
        502, f"MDSO Service Create - Unexpected data from MDSO - could not create the resource ID for payload {payload}"
    )


def clean_name_value_filter(afilter):
    """This may be specific to how MDSO wants to see a name-val filter; so here instead of util"""
    if afilter is None:
        return afilter
    else:
        cleaned = str(afilter)
        cleaned = cleaned.replace('"', "")
        cleaned = cleaned.replace("'", "")
        cleaned = cleaned.replace("{", "")
        cleaned = cleaned.replace("}", "")
        cleaned = cleaned.replace(")", "")
        cleaned = cleaned.replace("(", "")
        cleaned = cleaned.replace("]", "")
        cleaned = cleaned.replace("[", "")
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.strip()

    return cleaned


def get_port_status(provider_resource_id, upstream_port):
    url = f"/ractrl/api/v1/devices/{provider_resource_id}/execute"
    payload = f'{{"command": "get-interface.json", "parameters": {{"name": "{upstream_port.lower()}"}}}}'

    return mdso_post_request(url, payload)


def get_mac(provider_resource_id, upstream_port, model):
    url = f"/ractrl/api/v1/devices/{provider_resource_id}/execute"
    payload = f'{{"command": "get-etherswitching-table.json", "parameters": \
                {{"id": "{upstream_port.lower()}", "model": "{model}"}}}}'
    return mdso_post_request(url, payload)["result"]


def get_ip(provider_resource_id, irb_interface):
    url = f"/ractrl/api/v1/devices/{provider_resource_id}/execute"
    payload = f'{{"command": "get-arp-query.json", "parameters": {{"uniqueid": "{irb_interface.lower()}"}}}}'
    return mdso_post_request(url, payload)["result"]["properties"]["result"]


def poll_resource_status(resource_id):
    timer = 150
    cpe_ip = "no ip found"

    while timer >= 0:
        token = _create_token()
        headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"token {token}"}

        logger.info("TIMER = %s" % str(timer))
        timer -= 5
        sleep(5)
        try:
            err_msg, cpe_ip_resource = resource_status(headers, resource_id)
            logger.info("CPE IP RESOURCE: %s" % cpe_ip_resource)
            logger.info("ERROR MSG: %s" % err_msg)
        except Exception:
            if err_msg:
                return {"CPE_IP": cpe_ip, "FAIL_REASON": err_msg}, 404

            else:
                return {"CPE_IP": cpe_ip, "FAIL_REASON": "Unable to obtain IP Provider resource in MDSO"}, 404

        if cpe_ip_resource:
            logger.info("CONFIRMED CPE_IP_RESOURCE EXISTS")
            if cpe_ip_resource["orchState"] == "active":
                logger.info("CONFIRMED CPE_IP_RESOURCE ORCH STATE IS ACTIVE")
                cpe_ip = cpe_ip_resource["properties"]["ip"]
                _delete_token(token)
                return {"CPE_IP": cpe_ip, "FAIL_REASON": None}, 200

            elif cpe_ip_resource["orchState"] == "failed":
                if "ip_provider_error" in cpe_ip_resource["properties"].keys():
                    err_msg = cpe_ip_resource["properties"]["ip_provider_error"]
                else:
                    err_msg = "MDSO IP Provider Resource FAIL"

                _delete_token(token)
                return {"CPE_IP": cpe_ip, "FAIL_REASON": err_msg}, 400

        if timer < 0:
            _delete_token(token)
            if not err_msg:
                err_msg = "Timed out awaiting IP from MDSO"

            return {"CPE_IP": cpe_ip, "FAIL_REASON": err_msg}, 400
    return {"FAIL_REASON": "Poll_Resource_Status_Unknown"}, 500


def resync_resource(resource_id):
    return mdso_post(f"{RESOURCES_PATH}/{resource_id}/resync?full=true", None, 30, True)


def get_mne_resources_from_cid(cid):
    url = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.merakiServices&q="
        f"properties.circuitId%3A{cid}&obfuscate=true&offset=0&limit=1000"
    )
    mne_resources = mdso_get(url)
    return mne_resources


def get_existing_resource_by_query(resource_type, q_param, q_value):
    """
    Returns mdso resource.

    Parameters:
        resource_type (str): The MDSO resource type (typically charter.resourceTypes.<productName>)
        q_param (str): Query parameter key (example: label)
        q_value (str): Query parameter value (example: <circuit id>)

    Returns:
        resource_id (str) : resource id of mdso managed services resource if it exists
        else, None will be returned.
    """
    endpoint = f"{RESOURCES_PATH}?resourceTypeId={resource_type}&q={q_param}%3A{q_value}&obfuscate=true&offset=0&limit=1"
    existing_resource = mdso_get(endpoint).get("items")
    if existing_resource and len(existing_resource) > 0:
        return existing_resource[0]
    else:
        return None


def get_resource_operations(resource_id, ids_only=True, limit=1000, offset=0):
    operations = mdso_get(f"{RESOURCES_PATH}/{resource_id}/operations?offset={offset}&limit={limit}")["items"]
    if ids_only:
        operations = [o["id"] for o in operations]
    return operations


def get_resource_dependents(msa_rid):
    mne_resource = mdso_get(f"{RESOURCES_PATH}/{msa_rid}/dependencies?recursive=false&obfuscate=true")
    return mne_resource["items"]


def create_resource(body, product="merakiServices"):
    productId = product_query(product)
    body["resourceTypeId"] = f"charter.resourceTypes.{product}"
    body["productId"] = productId
    return create_service(body)


def pill_poll_resource_status(resource_id):
    for pprs_timer in range(0, 7):
        token = _create_token()
        headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"token {token}"}

        logger.info(f"pprs_timer = {pprs_timer}")
        try:
            err_msg, pill_resource = resource_status(headers, resource_id)
            logger.info(f"POST INSTALL LIGHT LEVEL RESOURCE: {pill_resource}")
            logger.info(f"ERROR MSG: {err_msg}")
        except Exception:
            if err_msg:
                return {"pill_error_code": "PILL400", "pill_error": err_msg}, 404

            else:
                return {
                    "pill_error_code": "PILL401",
                    "pill_error": "Unable to obtain light levels from resource in MDSO",
                }, 404

        if pill_resource:
            logger.info("CONFIRMED PILL_RESOURCE EXISTS")
            if pill_resource["orchState"] == "active":
                logger.info("CONFIRMED PILL_RESOURCE ORCH STATE IS ACTIVE")
                logger.info(f"pill resource: {pill_resource}")
                pill_details = pill_resource["properties"]["pill_details"]
                _delete_token(token)
                return pill_details, 200

            elif pill_resource["orchState"] != "activating":
                if "pill_error" and "pill_error_code" in pill_resource["properties"].keys():
                    err_msg = pill_resource["properties"]["pill_error"]
                    err_code = pill_resource["properties"]["pill_error_code"]
                else:
                    err_msg = "MDSO PILL RESOURCE FAILED"
                    err_code = "PILL999"
                _delete_token(token)
                return {"pill_error_code": err_code, "pill_error": err_msg}, 400

        sleep(5)

    _delete_token(token)
    err_msg = "Timed out awaiting light levels from MDSO"
    return {"pill_error_code": "PILL998", "pill_error": err_msg}, 400
