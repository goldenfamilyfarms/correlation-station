import logging
import json
import requests
import urllib3

import palantir_app
from common_sense.common.errors import abort

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

RESOURCES_PATH = "/bpocore/market/api/v1/resources"


def _env_check(production, need_auth=False):
    if production:
        auth_info = {
            "user": palantir_app.auth_config.MDSO_USER_PROD,
            "password": palantir_app.auth_config.MDSO_PASS_PROD,
        }
        url = palantir_app.url_config.MDSO_PROD_URL
    else:
        auth_info = {"user": palantir_app.auth_config.MDSO_USER, "password": palantir_app.auth_config.MDSO_PASS}
        url = palantir_app.url_config.MDSO_BASE_URL
    if need_auth:
        return auth_info, url
    else:
        return url


def _create_token(production=False):
    """get a token to authenticate calls to MDSO"""

    headers = {"Content-type": "application/json"}
    auth_info, url = _env_check(production, need_auth=True)

    data = {
        "username": auth_info["user"],
        "password": auth_info["password"],
        "tenant": "master",
        "expires_in": 60,
        "grant_type": "password",
    }

    try:
        r = requests.post(f"{url}/tron/api/v1/oauth2/tokens", headers=headers, json=data, verify=False, timeout=30)
        if r.status_code in [200, 201]:
            token = r.json()["accessToken"]
            return token
        else:
            abort(502, f"Error Code: M001 - Unexpected status code: {r.status_code} at authentication with MDSO")
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        abort(504, "Error Code: M002 - Connection Timeout at authentication with MDSO")
    except requests.ReadTimeout:
        abort(504, "Error Code: M002 - Read timeout during authentication with MDSO")


def _delete_token(token, production=False):
    if token:
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"token {token}"}
        requests.delete(
            f"{_env_check(production)}/tron/api/v1/oauth2/tokens/{token}", headers=headers, verify=False, timeout=300
        )


def mdso_get(endpoint, params=None, calling_function="None given", production=False, return_response=False):
    """
    - Accepts an MDSO endpoint and optional data then performs a GET request
        ex: /bpocore/market/api/v1/resources?validate=false
    - (Optional parameter) The name of the function where mdso_get is being called from
        ex: calling_function="get_resource_type_resource_list"
    """
    token = _create_token(production)
    headers = {"Accept": "application/json", "Authorization": f"token {token}"}

    try:
        logger.info(f"Calling mdso_get() via {calling_function}()")
        r = requests.get(f"{_env_check(production)}{endpoint}", headers=headers, params=params, timeout=60, verify=False)
        if return_response:
            return r
        elif r.status_code in [200, 201]:
            return r.json()
        else:
            logger.error(
                f"{r.status_code} status code returned from MDSO endpoint {endpoint}  | "
                f"Function that called mdso_get(): {calling_function}  | Response: {r.json()}"
            )
            abort(
                502,
                f"Error Code: M003 - {r.status_code} status code returned from MDSO endpoint {endpoint}  | "
                f"Function that called mdso_get(): {calling_function}  | Response: {r.json()}",
            )
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error(
            f"Couldn't connect to MDSO for request  | Endpoint: {endpoint}  | "
            f"Function that called mdso_get(): {calling_function}"
        )
        abort(
            504,
            f"Error Code: M004 - Couldn't connect to MDSO for request  | Endpoint: {endpoint}  | "
            f"Function that called mdso_get(): {calling_function}",
        )
    except requests.ReadTimeout:
        logger.error(
            f"Timeout error - Connected to MDSO and timed out for request: {endpoint}  | "
            f"Function that called mdso_get(): {calling_function}"
        )
        abort(
            504,
            f"Error Code: M004 - Timeout error - Connected to MDSO and timed out for request: {endpoint}  | "
            f"Function that called mdso_get(): {calling_function}",
        )
    finally:
        _delete_token(token)


def mdso_post(endpoint, data, calling_function=None, production=False):
    """
    - Accepts an MDSO endpoint and data then performs a POST request
        ex: /bpocore/market/api/v1/resources?validate=false
    - (Optional parameter) The name of the function where mdso_post is being called from
        ex: calling_function="_create_port_resource"
    """
    token = _create_token(production)
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    try:
        logger.info(f"Calling mdso_post() via {calling_function}()")
        r = requests.post(f"{_env_check(production)}{endpoint}", headers=headers, verify=False, json=data, timeout=30)
        if r.status_code == 201:
            try:
                return r.json()
            except Exception:
                return {"statusCode": 201, "StatusMessage": "Success"}
        else:
            logger.error(
                f"Error Code: M005 - {r.status_code} status code returned from MDSO endpoint: {endpoint}  | "
                f"Function that called mdso_post(): {calling_function}  | Payload Data: {data} | "
                f"Response: {r.json()}"
            )
            abort(
                502,
                f"{r.status_code} status code returned from MDSO endpoint: {endpoint}  | "
                f"Function that called mdso_post(): {calling_function}  | Payload Data: {data} | "
                f"Response: {r.json()}",
            )
    except (ConnectionError, requests.ConnectionError):
        logger.error(
            f"Couldn't connect to MDSO for request  | Endpoint: {endpoint}  | "
            f"Function that called mdso_post(): {calling_function}  | Payload Data: {data}"
        )
        abort(
            504,
            f"Error Code: M006 - Couldn't connect to MDSO for request  | Endpoint: {endpoint}  | "
            f"Function that called mdso_post(): {calling_function}  | Payload Data: {data}",
        )
    except requests.ReadTimeout:
        logger.error(
            f"Timeout error - Connected to MDSO and timed out for request: {endpoint}  | "
            f"Function that called mdso_post(): {calling_function}  | Payload Data: {data}"
        )
        abort(
            504,
            f"Error Code: M006 - Timeout error - Connected to MDSO and timed out for request: {endpoint}  | "
            f"Function that called mdso_post(): {calling_function}  | Payload Data: {data}",
        )
    finally:
        _delete_token(token)


def mdso_patch(resource_id, payload, calling_function=None, production=False):
    """
    Patches a resource with data provided in payload

    REQUIRED POSITIONAL ARGS:
        1) resource_id (Value of "id" key in resource JSON)
        2) payload (dictionary of data to patch)

    RETURNS:
        <class 'list'> (Containing dictionaries for each resource found)

    EXAMPLE USAGE:
    tool = mdso_tools.Tools('https://austx-lab-dev-mdso-06.dev.chtrse.com/', 'admin', 'adminpw')
    resource_id = "5dcd924f-75ac-4834-9d81-516129b46064"
    payload = {
        "desiredOrchState": "terminated",
        "orchState": "terminated"
    }
    tool.patch_resource(resource_id, payload)
    """
    token = _create_token(production)
    header = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        url = _env_check(production)
        payload = json.dumps(payload)
        patch_url = f"{url}{RESOURCES_PATH}/{resource_id}?validate=false&obfuscate=true"
        r = requests.patch(patch_url, data=payload, headers=header, verify=False, timeout=300)

        return r
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error(
            f"Couldn't connect to MDSO for request  | Endpoint: {url}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {payload}"
        )
        abort(
            504,
            f"Couldn't connect to MDSO for request  | Endpoint: {url}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {payload}",
        )
    except requests.ReadTimeout:
        logger.error(
            f"Timeout error - Connected to MDSO and timed out for request: {url}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {payload}"
        )
        abort(
            504,
            f"Error Code: M006 - Timeout error - Connected to MDSO and timed out for request: {url}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {payload}",
        )
    finally:
        _delete_token(token)


def mdso_delete(resource_id, data=None, calling_function=None, production=False, best_effort=True):
    """
    perform a DELETE request to MDSO endpoint
    :param endpoint: str, an MDSO endpoint and data
        ex: /bpocore/market/api/v1/resources/{resource_id}?validate=false
    :param data: dict, payload for delete request
    :param calling_function: str, optional; The name of the function where mdso_delete is being called from
        ex: calling_function="_delete_network_service_resource"
    :param production: bool, indicates if production server should be used
    :param best_effort: bool, if true do not fallout even if response is not success
    """
    endpoint = f"{RESOURCES_PATH}/{resource_id}?validate=false"
    token = _create_token(production)
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    try:
        logger.info(f"Calling mdso_delete() via {calling_function}()")
        r = requests.delete(f"{_env_check(production)}{endpoint}", headers=headers, verify=False, json=data, timeout=30)
        if best_effort or r.status_code == 204:
            try:
                return r.json()
            except Exception as error:
                return {"statusCode": r.status_code, "statusMessage": error, "error": "best effort failed"}
        else:
            logger.error(
                f"{r.status_code} status code returned from MDSO endpoint: {endpoint}  | "
                f"Function that called mdso_delete(): {calling_function}  | Payload Data: {data} | "
                f"Response: {r.json()}"
            )
            abort(
                502,
                f"{r.status_code} status code returned from MDSO endpoint: {endpoint}  | "
                f"Function that called mdso_delete(): {calling_function}  | Payload Data: {data} | "
                f"Response: {r.json()}",
            )
    except (ConnectionError, requests.ConnectionError):
        logger.error(
            f"Couldn't connect to MDSO for request  | Endpoint: {endpoint}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {data}"
        )
        abort(
            504,
            f"Couldn't connect to MDSO for request  | Endpoint: {endpoint}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {data}",
        )
    except requests.ReadTimeout:
        logger.error(
            f"Timeout error - Connected to MDSO and timed out for request: {endpoint}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {data}"
        )
        abort(
            504,
            f"Error Code: M006 - Timeout error - Connected to MDSO and timed out for request: {endpoint}  | "
            f"Function that called mdso_delete(): {calling_function}  | Payload Data: {data}",
        )
    finally:
        _delete_token(token)


def service_id_lookup(cid):
    query = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.Network"
        f"Service&offset=0&limit=1000&q=properties.circuit_id:{cid}"
    )
    return mdso_get(query, calling_function="service_id_lookup")["items"][0]["id"]


def service_details(cid, resource_type, production=False):
    query = f"{RESOURCES_PATH}?resourceTypeId={resource_type}&q=properties.circuit_id:{cid}&offset=0&limit=1000"
    return mdso_get(query, calling_function="service_details", production=production)


def product_query(product_name, production=False):
    """GET call for the product id."""
    endpoint = "/bpocore/market/api/v1/products"
    query = f"{endpoint}?includeInactive=false&q=resourceTypeId%3Acharter.resourceTypes.{product_name}&limit=1000"
    logger.info(f"Attempting to return the product ID for {product_name}")
    return mdso_get(query, calling_function="product_query", production=production)["items"][0]["id"]


def device_lookup(device):
    endpoint = (
        f"{RESOURCES_PATH}?resourceTypeId=tosca.resourceTypes.NetworkFunction&q=label:{device}&offset=0&limit=1000"
    )
    return mdso_get(endpoint, calling_function="device_lookup")["items"]


def get_resource_type_resource_list(resource_type, query_criteria=None):
    """Call to MDSO for all resource instances of a resource type ...with optional mdso_filters"""

    if query_criteria is None:
        url = f"{RESOURCES_PATH}?resourceTypeId={resource_type}&offset=0&limit=1000"
    # TODO - This else belongs in a util function to clean_json_item_list( delimiter )
    else:
        q_string = _clean_name_value_mdso_filter(query_criteria)
        url = f"{RESOURCES_PATH}?resourceTypeId={resource_type}&q={q_string}&offset=0&limit=1000"
    return mdso_get(url, calling_function="get_resource_type_resource_list")


def _clean_name_value_mdso_filter(mdso_filter):
    """This may be specific to how MDSO wants to see a name-val mdso_filter; so here instead of util"""
    if mdso_filter is None:
        return mdso_filter
    else:
        cleaned = str(mdso_filter)
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


def get_resources_by_type_and_properties(resource_type, properties, production):
    endpoint = f"{RESOURCES_PATH}?resourceTypeId={resource_type}"
    for key, value in properties.items():
        endpoint += f"&q=properties.{str(key)}:{str(value)},"
    response = mdso_get(
        endpoint, calling_function="get_resources_by_type_and_properties", production=production, return_response=True
    )
    return response


def delete_inactive_nf_resources(fqdn, ip=None, production=False):
    hostnames = []
    hostnames.append(fqdn)
    if ip and ip.upper() != "DHCP":
        hostnames.append(ip)

    for hostname in hostnames:
        response = get_resources_by_type_and_properties(
            "tosca.resourceTypes.NetworkFunction", {"ipAddress": hostname}, production
        )
        network_functions = response.json().get("items", [])
        if len(network_functions) == 0:
            logger.info(f"No NetworkFunction resources found for {hostname}")
        else:
            for resource in network_functions:
                if resource["orchState"] != "active":
                    resource_id = resource["id"]
                    patch_nf_resource_dependents_terminate(resource_id, production)
                    logger.debug(f"Terminating NetworkFunction resource {resource_id}")
                    terminate_nf = mdso_patch(
                        resource["id"],
                        payload={"desiredOrchState": "terminated", "orchState": "terminated"},
                        calling_function="delete_inactive_nf_resources",
                        production=production,
                    )
                    if terminate_nf.status_code != 200:
                        msg = f"Error deleting inactive device {hostname} Status Code: {terminate_nf.status_code}"
                        abort(502, msg)


def patch_nf_resource_dependents_terminate(resource_id, production=False):
    dependents = get_network_functions_dependents(resource_id)
    logger.debug(f"Found {len(dependents.get('items', 0))} dependents for {resource_id}")
    if dependents.get("items"):
        logger.debug(f"Patch Terminating all dependents for {resource_id}")
        for dependent in dependents["items"]:
            mdso_patch(
                dependent["id"],
                payload={"desiredOrchState": "terminated", "orchState": "terminated"},
                calling_function="patch_nf_resource_dependents_terminate",
                production=production,
            )


def get_network_functions_dependents(resource_id):
    endpoint = f"{RESOURCES_PATH}/{resource_id}/dependents?recursive=true&obfuscate=true&offset=0&limit=1000"
    response = mdso_get(endpoint, return_response=True)
    return response.json()


def onboard_nf_resource(hostname, device_ip="", device_model="", device_vendor="", timeout=30):
    if device_ip == "DHCP":
        abort(502, f"MDSO onboarding error - DHCP is not a valid IP Address. Unable to get IP from IPC for {hostname}")
    onboarder_product_id = product_query("DeviceOnboarder", True)
    payload = {
        "productId": onboarder_product_id,
        "resourceTypeId": "charter.resourceTypes.DeviceOnboarder",
        "label": f"{hostname}.acceptance_device_onboarder",
        "properties": {
            "device_name": f"{hostname}",
            "device_ip": f"{device_ip}",
            "device_vendor": f"{device_vendor}",
            "device_model": f"{device_model}",
            "operation": "NETWORK_SERVICE_ACTIVATION",
        },
    }
    onboard_device_res_id = mdso_post(f"{RESOURCES_PATH}?validate=false", payload, timeout).get("id")
    return onboard_device_res_id


def get_all_product_resources(product_id, next_page_token=None):
    """
    Gets all resources from a provided product id.
    When the product contains >= 1000 resources (api limit), this function will recursively get the next batch
    and return the total list of all resources to the initial caller.
    :param token: API token
    :param product_id: id of the product holding the resources
    :param next_page_token: used for recursive calls to offset the next batch
    :return: list of all resources from the product
    """
    limit = 1000
    resource_get = f"/bpocore/market/api/v1/resources?productId={product_id}&obfuscate=true&limit={limit}"
    if next_page_token:
        resource_get = f"{resource_get}&pageToken={next_page_token}"

    response = mdso_get(endpoint=resource_get, calling_function="get_all_product_resources")
    if response:
        items = response["items"]
    else:
        return False, f"failed to get resources from mdso product {product_id}"
    if len(items) == limit:
        status, next_batch = get_all_product_resources(product_id, next_page_token=response["nextPageToken"])
        if not status:
            return False, next_batch  # next_batch will be the string error message in this case
        else:
            return True, items + next_batch
    else:
        return True, items
