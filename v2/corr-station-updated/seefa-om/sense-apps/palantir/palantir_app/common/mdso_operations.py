import datetime
import json
import logging
import time

import requests
import urllib3

import palantir_app
from common_sense.common.errors import abort

# from palantir_app.common.mdso_auth import create_token, delete_token
from palantir_app.dll.mdso import _create_token, _delete_token

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


codes = {
    400: "Bad Request",
    401: "Not authorized",
    404: "Resource not found",
    403: "Access not authorized",
    500: "Server error",
}

mdso_base_url = palantir_app.url_config.MDSO_BASE_URL
RESOURCES_PATH = "/bpocore/market/api/v1/resources"


def get_existing_resource(headers, target, port_id):
    """Call to MDSO to check if there's an existing resource ID based on port id"""
    url = (
        f"{mdso_base_url}{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes."
        f"PortActivation&q=properties.deviceName:{target},properties.portname:{port_id}&limit=1000"
    )
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=300)
        data = json.loads(r.content.decode("utf-8"))
        if r.status_code == 200:
            if data.get("items") and data["items"]:
                found_something_maybe = False
                for record in data["items"]:
                    if record["properties"]["deviceName"] == target and record["properties"]["portname"] == port_id:
                        found_something_maybe = True
                        if record["properties"].get("status") and record["properties"]["status"] == "Ready to configure":
                            logger.debug(f"Existing resource found for {target}_{port_id} - {record['id']}")
                            return None, record["id"]
                        elif (
                            record["properties"].get("status")
                            and record["properties"]["status"] == "Port not present on the device"
                        ):
                            return {
                                "status": "failed",
                                "message": f"port not present on the device -- record: {record}",
                            }, None
                else:
                    if found_something_maybe:
                        # TODO maybe one day have better reporting here
                        return None, "still working"
            else:
                logger.info(f"No record was found for {target}_{port_id}")
                return None, None
        else:
            logger.error(f"{r.status_code} error - MDSO failed to process the get existing resource request")
            return {
                "status": "error",
                "message": f"MDSO failed to process the get existing resource request. Reponse: {r.status_code}",
            }, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def get_product(headers, res_type):
    """Get ID for Port Activation product from MDSO"""
    url = (
        f"{mdso_base_url}/bpocore/market/api/v1/products?includeInactive=false&q=resource"
        f"TypeId%3A{res_type}&offset=0&limit=1000"
    )
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=300)
        if r.status_code == 200:
            data = json.loads(r.content.decode("utf-8"))
            if data.get("items") and data["items"]:
                return None, data["items"][0]["id"]
            else:
                return {
                    "status": "error",
                    "message": "MDSO failed to process the get product request. No products found.",
                }, None
        else:
            return {
                "status": "error",
                "message": f"MDSO failed to process the get product request. Response: {r.status_code}",
            }, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError) as err:
        logger.exception(f"Can't connect to MDSO -- {err}")
        return 504, f"Can't connect to MDSO -- {err}"


def delete_resource(headers, resource_id):
    """Delete a resource, used only in testing"""
    url = f"{mdso_base_url}{RESOURCES_PATH}/{resource_id}?validate=true"
    r = requests.delete(url, headers=headers, verify=False, timeout=300)
    if r.status_code == 204:
        logger.debug(f"JUST DELETED THIS DUDE - {resource_id}")
        r = requests.get(url, headers, verify=False, timeout=300)
        timeout = 0
        while r.status_code == 200 and timeout < 15:
            time.sleep(2)
            timeout += 1
            r = requests.get(url, headers, verify=False, timeout=300)
        if timeout >= 15:
            return False
    elif r.status_code == 404:
        logger.debug(f"COULDN'T FIND THIS GUY TO DELETE? - {resource_id}")
    else:
        abort(
            f"MDSO failed to process the delete resource request. Response: {r.status_code}",
            {r.status_code in (204, 404)},
        )


def create_resource(headers, tid, target, vendor, timer, port_id, product_id):
    """Create a new resource using a POST call to MDSO"""
    data = {
        "desiredOrchState": "active",
        "label": f"{tid}_{port_id}",
        "autoClean": False,
        "reason": "string",
        "discovered": False,
        "properties": {"portname": port_id, "deviceName": target, "vendor": vendor, "terminationTime": timer},
        "productId": product_id,
    }

    try:
        r = requests.post(
            f"{mdso_base_url}{RESOURCES_PATH}?validate=false", headers=headers, json=data, verify=False, timeout=300
        )
        if r.status_code == 201:
            data = json.loads(r.content.decode("utf-8"))
            if data:
                # TODO not sure if this will be a list if more than one record is returned...
                if isinstance(data, list):
                    for record in data:
                        if record["properties"]["deviceName"] == target and record["properties"]["portname"] == port_id:
                            logger.debug(f"JUST CREATED THIS GUY - {record['id']}")
                            return None, record["id"]
                    else:
                        return {"status": "failed", "message": "device not found"}, None
                else:
                    logger.debug(f"JUST CREATED THIS GUY - {data['id']}")
                    return None, data["id"]
            else:
                logger.debug("MDSO didn't return any data")
                return {
                    "status": "error",
                    "message": "MDSO failed to process the create resource request. No data found.",
                }, None
        else:
            logger.debug(f"MDSO errored! Status code {r.status_code} - {r.content}")
            return {
                "status": "error",
                "message": f"MDSO failed to process the create resource request. Response: {r.status_code}",
            }, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def generate_op_id(headers, resource_id, status):
    """Call to activate the port, returns operation_id"""
    # payload = {"activate": "true"}  # true for up, false for down
    payload = {"interface": "setPortStatus", "inputs": {"reqdstate": "up" if status == "true" else "down"}}
    try:
        r = requests.post(
            f"{mdso_base_url}{RESOURCES_PATH}/{resource_id}/operations",
            headers=headers,
            json=payload,
            verify=False,
            timeout=300,
        )
        if r.status_code == 201:
            data = json.loads(r.content.decode("utf-8"))
            output = {"resourceId": data["resourceId"], "operationId": data["id"]}
            return None, output
        else:
            return 504, "Can't connect to MDSO"
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def generate_status_op_id(headers, resource_id):
    """Call to MDSO to generate operations id for checking status"""
    err_msg, existing_op_id = get_existing_status_op_id(headers, resource_id)
    if existing_op_id:
        return None, existing_op_id
    if err_msg:
        return err_msg, None

    payload = {"description": "string", "interface": "getPortStatus", "title": "string"}

    try:
        r = requests.post(
            f"{mdso_base_url}{RESOURCES_PATH}/{resource_id}/operations",
            headers=headers,
            json=payload,
            verify=False,
            timeout=300,
        )
        if r.status_code == 201:
            data = json.loads(r.content.decode("utf-8"))
            return None, data["id"]
        else:
            return {
                "status": "error",
                "message": f"MDSO failed to process the generate status op request. Response: {r.status_code}",
            }, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def status_call(headers, resource_id, op_id):
    """Call to MDSO to get status on port."""
    try:
        r = requests.get(
            f"{mdso_base_url}{RESOURCES_PATH}/{resource_id}/operations/{op_id}",
            headers=headers,
            verify=False,
            timeout=300,
        )
        if r.status_code == 200:
            data = json.loads(r.content.decode("utf-8"))
            if data.get("state"):
                return None, data
            else:
                return {
                    "status": "error",
                    "message": "MDSO failed to process the get status request. No state found.",
                }, None
        elif r.status_code == 404 and "not found" in json.loads(r.content.decode("utf-8"))["failureInfo"]["reason"]:
            return {"status": "failed", "message": "resourceId/operationId not found"}, None
        else:
            return {
                "status": "error",
                "message": f"MDSO failed to process the get status request. Response: {r.status_code}",
            }, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def resource_status(headers, resource_id):
    try:
        r = requests.get(f"{mdso_base_url}{RESOURCES_PATH}/{resource_id}", headers=headers, verify=False, timeout=300)
        if r.status_code == 200:
            return None, r.json()
        elif r.status_code == 404:
            abort(404, f"No MDSO resource found...with resource ID =  {resource_id}")
        else:
            return f"MDSO failed to process the resource status request. Response: {r.status_code}", None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def get_existing_status_op_id(headers, resource_id):
    """Finds all existing operation ids, sorts them by timestamp"""
    try:
        r = requests.get(
            f"{mdso_base_url}{RESOURCES_PATH}/{resource_id}/operations?offset=0&limit=1000",
            headers=headers,
            verify=False,
            timeout=300,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("items") and data["items"]:
                # List of all ids, timestamp, and what the operation was for (i.e. "getPortStatus")
                op_ids = [
                    (x["id"], datetime.datetime.strptime(x["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ"), x["interface"])
                    for x in data["items"]
                ]
                # Sort by timestamp
                op_ids.sort(key=lambda x: x[1])
                if op_ids[-1][2] != "getPortStatus":
                    # if last operation was some other action, we'll need to create a new op id
                    return None, None
                else:
                    # otherwise, we need to reuse the latest op id
                    return None, op_ids[-1][0]
            else:
                return None, None
        else:
            return {
                "status": "error",
                "message": f"MDSO failed to process the get existing status op request. {r.status_code}",
            }, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def service_id_lookup(cid, token):
    """GET call to find the service id based on CID"""
    querystring = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.Network"
        f"Service&offset=0&limit=1000&q=properties.circuit_id:{cid}"
    )
    headers = {"Accept": "application/json", "Authorization": token}
    # pdb.set_trace()
    r = requests.get(f"{mdso_base_url}{querystring}", headers=headers, verify=False, timeout=30)

    if r.status_code != 200:
        logger.exception(f"Error - {codes[r.status_code]} when trying to look up the service id for CID {cid}")
        return None
    items = json.loads(r.content.decode("utf-8"))["items"]
    if len(items) == 0:
        return None
    else:
        return json.loads(r.content.decode("utf-8"))["items"][0]["id"]


def network_call(cid, token):
    """Get Network Resources"""

    # service_id = service_id_lookup(cid, token)
    # if service_id is None:
    #     logger.debug("FAIL - can't find a service.")
    #     return None

    headers = {"Accept": "application/json", "Authorization": token}

    querystring = (
        f"{RESOURCES_PATH}?resourceTypeId=charter.resourceTypes.CircuitDetails&q=label:{cid}.cd&offset=0&limit=1000"
    )

    # this has circuit topology which is handy, but no differences field
    try:
        r = requests.get(f"{mdso_base_url}{querystring}", headers=headers, verify=False, timeout=30)
        if r.status_code == 200:
            return r.json()["items"]
        else:
            return None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        abort(504, "MDSO Not responding to request")


def device_lookup(device, token):
    headers = {"Accept": "application/json", "Authorization": token}

    querystring = (
        f"{RESOURCES_PATH}?resourceTypeId=tosca.resourceTypes.NetworkFunction&q=label:{device}&offset=0&limit=1000"
    )
    try:
        r = requests.get(f"{mdso_base_url}{querystring}", headers=headers, verify=False, timeout=30)
        if r.status_code == 200:
            return r.json()["items"]
        else:
            return None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        abort(504, "MDSO Not responding to request")


# query_criteria is a json dictionary of elements necessary to be included in the info
def get_resource_type_resource_list(resource_type, headers=None, query_criteria=None):
    """Call to MDSO for all resource instances of a resource type ...with optional mdso_filters"""
    cleanup_token = False

    if headers is None:
        token = _create_token()
        cleanup_token = True
        headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"token {token}"}

    if query_criteria is None:
        url = f"{mdso_base_url}{RESOURCES_PATH}?resourceTypeId={resource_type}&offset=0&limit=1000"
    # TODO - This else belongs in a util function to clean_json_item_list( delimiter )
    else:
        q_string = clean_name_value_mdso_filter(query_criteria)

        url = f"{mdso_base_url}{RESOURCES_PATH}?resourceTypeId={resource_type}&q={q_string}&offset=0&limit=1000"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=300)
        if cleanup_token is True:
            _delete_token(token)
        data = json.loads(r.content.decode("utf-8"))
        if r.status_code == 200:
            return 200, data
        else:
            return r.status_code, None
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        return 504, "Can't connect to MDSO"


def clean_name_value_mdso_filter(mdso_filter):
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
