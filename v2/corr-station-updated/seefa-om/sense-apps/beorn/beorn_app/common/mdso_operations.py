import json
import logging

import requests
import urllib3

import beorn_app
from common_sense.common.errors import abort
from beorn_app.common.mdso_auth import create_token, delete_token

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

codes = {
    400: "Bad Request",
    401: "Not authorized",
    404: "Resource not found",
    403: "Access not authorized",
    412: "Precondition error",
    500: "Server error",
    502: "Bad Gateway",
    504: "Server Unavailable",
}

MDSO_BASE_URL = beorn_app.url_config.MDSO_BASE_URL
RESOURCES_PATH = "/bpocore/market/api/v1/resources"


def service_id_lookup(headers, cid):
    """GET call to find the service id based on CID"""
    querystring = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.Network"
        f"Service&offset=0&limit=1000&q=properties.circuit_id:{cid}"
    )
    try:
        r = requests.get(f"{MDSO_BASE_URL}{querystring}", headers=headers, verify=False, timeout=30)

        if r.status_code == 200:
            if r.json()["items"]:
                return None, r.json()["items"][0]["id"]
            else:
                return None, None
        else:
            return f"MDSO Error - {codes[r.status_code]}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def dependency_thing(headers, resource_id, cid):
    querystring = f"{RESOURCES_PATH}/{resource_id}/dependencies?recursive=true&q=label:{cid}.cd&offset=0&limit=1000"
    try:
        r = requests.get(f"{MDSO_BASE_URL}{querystring}", headers=headers, verify=False, timeout=30)

        if r.status_code == 200:
            if r.json()["items"]:
                return None, r.json()["items"]
            else:
                return None, None
        else:
            return f"MDSO Error - {codes[r.status_code]}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def product_query(headers, product_name):
    """GET call for the product id."""
    querystring = (
        "/bpocore/market/api/v1/products?includeInactive=false&q=resourceTypeId%3"
        f"Acharter.resourceTypes.{product_name}&offset=0&limit=1000"
    )
    try:
        r = requests.get(f"{MDSO_BASE_URL}{querystring}", headers=headers, verify=False, timeout=30)
        if r.status_code != 200:
            return f"MDSO Error - {codes[r.status_code]}", None
        try:
            product = json.loads(r.content.decode("utf-8"))["items"][0]["id"]
            return None, product
        except IndexError:
            return f"The MDSO product id for {product_name} does not exist.", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def post_to_service(headers, data, cid, ok_200=False):
    """Used to update or create a service. Returns success or failure reason."""

    good_responses = [200, 201] if ok_200 else [201]
    try:
        r = requests.post(
            f"{MDSO_BASE_URL}{RESOURCES_PATH}?validate=false", headers=headers, json=data, timeout=30, verify=False
        )
        if r.status_code in good_responses:
            return None, r.json()["id"]
        else:
            return f"MDSO Error - {cid} - {codes[r.status_code]}", None

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def delete_service(headers, service_id):
    """Delete a service using service id"""
    try:
        response = requests.delete(
            f"{MDSO_BASE_URL}{RESOURCES_PATH}/{service_id}", headers=headers, verify=False, timeout=30
        )
        if response.status_code != 204:
            return f"MDSO Error - {codes[response.status_code]}"
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def update_by_parameters(headers_info, update_parameters):
    """MDSO asynchronous update using json-formatted parameters"""
    try:
        response = requests.post(
            f"{MDSO_BASE_URL}{RESOURCES_PATH}?validate=false",
            headers=headers_info,
            json=update_parameters,
            verify=False,
            timeout=30,
        )
        if response.status_code != 201:
            return f"MDSO Error - {codes[response.status_code]}", None
        else:
            return None, response.json()

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def service_details(headers, cid, resource_type):
    url = (
        f"{MDSO_BASE_URL}{RESOURCES_PATH}?resourceTypeId={resource_type}"
        f"&q=properties.circuit_id:{cid}&offset=0&limit=1000"
    )
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=30)
        if r.status_code == 200:
            return None, r.json()["items"]
        elif r.status_code == 404 and "not found" in json.loads(r.content.decode("utf-8"))["failureInfo"]["reason"]:
            return "Resource not found", None
        else:
            return f"MDSO failed to process the request {r.json()}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def find_resource_by_circuit(headers, cid):
    url = (
        f"{MDSO_BASE_URL}{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes."
        f"NetworkService&q=properties.circuit_id:{cid}&offset=0&limit=1000"
    )
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=30)
        if r.status_code == 200:
            if r.json()["items"]:
                return None, r.json()["items"][0]["id"]
            else:
                return "Resource not found", None
        else:
            return f"MDSO failed to process the request {r.json()}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def create_activate_op_id(headers, resource_id, data):
    try:
        r = requests.post(
            f"{MDSO_BASE_URL}{RESOURCES_PATH}/{resource_id}/operations",
            headers=headers,
            json=data,
            verify=False,
            timeout=30,
        )
        if r.status_code == 201:
            data = {"operationId": r.json()["id"], "resourceId": r.json()["resourceId"]}
            return None, data
        else:
            return f"MDSO failed to process the request {r.json()}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def dependencies_by_resource(headers, resource_id, cid):
    querystring = f"{RESOURCES_PATH}/{resource_id}/dependencies?recursive=true&q=label:{cid}.cd&offset=0&limit=1000"
    try:
        r = requests.get(f"{MDSO_BASE_URL}{querystring}", headers=headers, verify=False, timeout=30)

        if r.status_code == 200:
            if r.json()["items"]:
                return None, r.json()["items"]
            else:
                return None, None
        else:
            return f"MDSO Error - {codes[r.status_code]}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


def lookup_dependencies(headers, resource_id):
    url = f"{MDSO_BASE_URL}{RESOURCES_PATH}/{resource_id}/dependencies?recursive=true&offset=0&limit=1000"

    try:
        r = requests.get(url, headers=headers, verify=False, timeout=30)
        if r.status_code == 200:
            if not r.json()["items"]:
                return "No data", None
            for i in r.json()["items"]:
                if i["resourceTypeId"] == "charter.resourceTypes.CircuitDetails":
                    try:
                        for top in i["properties"]["topology"]:
                            for node in top["data"]["node"]:
                                device = {x["name"]: x["value"] for x in node["name"]}
                                if device["Role"] == "CPE":
                                    for d in node["ownedNodeEdgePoint"]:
                                        edge = {}
                                        for z in d["name"]:
                                            edge[z["name"]] = z["value"]
                                        if edge["Role"] == "UNI":
                                            return None, edge["Name"]
                    except KeyError:
                        continue
            return None, "No UNI Port found"
        else:
            return f"MDSO failed to process the request {r.json()}", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on MDSO to process the request")
        abort(504, "Timeout waiting on MDSO to process the request")


# query_criteria is a json dictionary of elements necessary to be included in the info
def get_resource_type_resource_list(resource_type, headers=None, query_criteria=None):
    """Call to MDSO for all resource instances of a resource type ...with optional filters"""
    cleanup_token = False

    if headers is None:
        token = create_token()
        cleanup_token = True

        headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    if query_criteria is None:
        url = (f"{MDSO_BASE_URL}{RESOURCES_PATH}?resourceTypeId={resource_type}&offset=0&limit=1000",)
    else:
        q_string = clean_name_value_filter(query_criteria)

        url = f"{MDSO_BASE_URL}{RESOURCES_PATH}?resourceTypeId={resource_type}&q={q_string}&offset=0&limit=1000"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=300)
        data = json.loads(r.content.decode("utf-8"))
        if r.status_code == 200:
            if cleanup_token:
                delete_token(token)
            return 200, data
        else:
            if cleanup_token:
                delete_token(token)
            return r.status_code, None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        delete_token(token)
        logger.exception("Can't connect to MDSO")
        if cleanup_token:
            delete_token(token)
        return {"status": "error", "message": "MDSO failed to process the request"}, None
    finally:
        if cleanup_token:
            delete_token(token)


def create_service_mapper(service_id, device_ips=None):
    """POST call to instantiate a ServiceMapper actor resource"""
    # Pass CID as body parameter
    if service_id is None:
        http_code = 412
        return http_code, None, None

    token = create_token()

    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    filters = {"label": service_id, "properties.circuit_id": service_id}
    http_code, resource_list = get_resource_type_resource_list("charter.resourceTypes.ServiceMapper", headers, filters)

    if http_code == 200:  # This implies a ServiceMapper has already been run
        # iterate through items[] array and look for an orchState == active
        for item in resource_list["items"]:
            if "orchState" in item:
                if item["orchState"] in ("active", "requested", "activating"):
                    # already a mapping resource instantiated and either in process or completed
                    # good! just return the resource id of this entry
                    if len(item["id"]) > 0:
                        # there is a resource that can already be queried for status and diffs
                        delete_token(token)
                        return 201, item, "Mapper Invoked"
    else:
        error_message = f"Failed to retireve ServiceMapper info from MDSO with code: {http_code}"
        delete_token(token)
        return 502, error_message, None

    # The above query resulted in a 200 but there was no ServiceMapper info OR
    # the entries for the ServiceMapper were all failed... this would require a new Mapper
    query_response, product = product_query(headers, "ServiceMapper")

    if query_response:
        error_message = "Failed to retireve Product ID associated with MDSO charter.resourceIdType.ServiceMapper"
        delete_token(token)
        return 502, error_message, None

    post_info = {
        "label": "",
        "resourceTypeId": "",
        "productId": "",
        "properties": {"circuit_id": "", "use_alternate_circuit_details_server": False},
    }

    post_info["label"] = service_id
    post_info["productId"] = product
    post_info["resourceTypeId"] = "charter.resourceTypes.ServiceMapper"
    post_info["properties"]["circuit_id"] = service_id

    if device_ips is not None:
        post_info["properties"]["device_ips"] = device_ips

    querystring = f"{RESOURCES_PATH}?validate=false&obfuscate=true"
    try:
        r = requests.post(f"{MDSO_BASE_URL}{querystring}", headers=headers, json=post_info, verify=False, timeout=30)
        delete_token(token)

        if r.status_code != 201:
            error_message = f"Unexpected HTTP Code:{codes[r.status_code]},Service Mapper Instantiation Error:{post_info}"
            if r.status_code >= 500:
                return 504, None, error_message
            else:
                return 502, None, error_message
        else:
            # return 201, response, None
            response_content = json.loads(r.content.decode("utf-8"))
            return 201, response_content, "Mapper Invoked"
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        error_message = "Timeout waiting on MDSO to process Service Mapper POST request"
        logger.exception(error_message)
        delete_token(token)
        return 504, None, error_message
    finally:
        delete_token(token)


def resource_status(headers, resource_id):
    try:
        r = requests.get(f"{MDSO_BASE_URL}{RESOURCES_PATH}/{resource_id}", headers=headers, verify=False, timeout=300)
        if r.status_code == 200:
            return None, r.json()
        elif r.status_code == 404 and "not found" in json.loads(r.content.decode("utf-8"))["failureInfo"]["reason"]:
            return "Resource not found", None
        else:
            return "MDSO failed to process the request", None
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return "MDSO failed to process the request", None


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
