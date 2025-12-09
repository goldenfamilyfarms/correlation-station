from time import sleep
import requests
import logging
import json


from arda_app.common import url_config, endpoints
from arda_app.dll.utils import get_hydra_headers
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)

DEPLOYED_STATUS = "deployed"


def _handle_ipc_resp(url, method, resp=None, payload=None, timeout=False) -> dict:
    payload_message = f"- PAYLOAD: {payload}"
    if not payload:
        payload_message = ""

    if timeout:
        logger.exception(f"IPControl timeout - METHOD: {method} - URL: {url} {payload_message}")
        abort(500, f"IPControl timeout - METHOD: {method} - URL: {url} {payload_message}")
    else:
        if resp.status_code == 200:
            return resp.json()
        else:
            message = ()
            try:
                if "message" in resp.json().keys():
                    if "Device not found" in resp.json()["message"]:
                        message = resp.json()["message"]
                    else:
                        message = (
                            f"IPControl unexpected response - METHOD: {method} - URL: {url} "
                            f"{payload_message} - message: {resp.json()['message']}"
                        )
            except json.JSONDecodeError as e:
                message = (
                    f"IPControl unexpected status code 1: {resp.status_code}, response: {resp.text} error {e} "
                    f"- METHOD: {method} - URL: {url} {payload_message}"
                )
            if not message:
                message = (
                    f"IPControl unexpected status code 2: {resp.status_code}, response: {resp.text}"
                    f"- METHOD: {method} - URL: {url} {payload_message}"
                )

            logger.error(message)
            abort(500, message)


def get_ipc(url, params=None, timeout=30, return_resp=False):
    """Send a GET call to the IPControl API and return the JSON-formatted response"""
    url = f"{url_config.HYDRA_BASE_URL}{url}"
    headers = get_hydra_headers()
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            resp = requests.get(url=url, headers=headers, params=params, verify=False, timeout=timeout)
            if return_resp:
                return resp.json()
            return _handle_ipc_resp(url, "GET", resp=resp)
        except (ConnectionError, requests.ConnectionError, requests.Timeout):
            _handle_ipc_resp(url, "GET", timeout=True)

    logger.error(f"Timed out getting data from IPControl for url: {url}")
    abort(500, f"Timed out getting data from IPControl for URL: {url} after {count} tries")


def post_ipc(url, payload, timeout=30):
    """Send a post call to the IPControl API and return the JSON-formatted response"""
    url = f"{url_config.HYDRA_BASE_URL}{url}"
    headers = get_hydra_headers()

    try:
        resp = requests.post(url=url, headers=headers, json=payload, verify=False, timeout=timeout)
        return _handle_ipc_resp(url, "POST", resp=resp, payload=payload)
    except (ConnectionError, requests.ConnectionError, requests.Timeout):
        _handle_ipc_resp(url, "POST", timeout=True)

    logger.error(f"Timed out getting data from IPControl for URL: {url}")
    abort(500, f"Timed out getting data from IPControl for URL: {url}")


def put_ipc(url, payload, timeout=30):
    """Send a post call to the IPControl API and return the JSON-formatted response"""
    url = f"{url_config.HYDRA_BASE_URL}{url}"
    headers = get_hydra_headers()
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            resp = requests.put(url=url, headers=headers, json=payload, verify=False, timeout=timeout)
            return _handle_ipc_resp(url, "PUT", resp=resp, payload=payload)
        except (ConnectionError, requests.ConnectionError, requests.Timeout):
            _handle_ipc_resp(url, "PUT", timeout=True)

    logger.error(f"Timed out getting data from IPControl for URL: {url}")
    abort(500, f"Timed out getting data from IPControl for URL: {url} after {count} tries")


def delete_ipc(url, payload, timeout=30, return_resp=False):
    """Send a DELETE call to the IPControl API and return the JSON-formatted response"""
    url = f"{url_config.HYDRA_BASE_URL}{url}"
    headers = get_hydra_headers()
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            resp = requests.delete(url=url, headers=headers, json=payload, verify=False, timeout=timeout)
            if return_resp:
                return resp.json()
            return _handle_ipc_resp(url, "DELETE", resp=resp)
        except (ConnectionError, requests.ConnectionError, requests.Timeout):
            _handle_ipc_resp(url, "DELETE", timeout=True)

    logger.error(f"Timed out getting data from IPControl for URL: {url}")
    abort(500, f"Timed out getting data from IPControl for URL: {url} after {count} tries")


def get_subnet_block_by_blockname(block_name, container_name=None, get_message=False):
    """
    Retrieves a subnet block from IPControl using its blockName (aka IP + its subnet)    Ex: 70.92.49.160/29
    This is separate from get_ipc in order to retrieve the 502 info when a block does not exist.
        (If you try and delete a block that doesn't exist, it just returns None -
        the exact same thing it returns if the block DOES exist and gets successfully deleted)

    NOTE: You must include the container name holding the block if the block name is not unique

    """
    if block_name is None:
        return None

    container = f"&container={container_name}" if container_name is not None else ""
    url = f"{endpoints.CROSSWALK_IPBLOCK_V1}?blockName={block_name}{container}"
    result = get_ipc(url, return_resp=get_message)
    if get_message and isinstance(result, dict) and result.get("message"):
        return result["message"]
    for item in result:
        if item["childBlock"]["blockStatus"].lower() == DEPLOYED_STATUS:
            return item["childBlock"]


def get_subnet_block_by_ip(ip, status=None, get_message=False):
    """Retrieves a subnet block from IPC using an IP address (no subnet needed)"""
    status = status if status else DEPLOYED_STATUS
    url = f"{endpoints.CROSSWALK_IPBLOCK_V1}?ipAddress={ip}"
    result = get_ipc(url, return_resp=get_message)
    if get_message and isinstance(result, dict) and result.get("message"):
        return result["message"]
    for item in result:
        if item["childBlock"]["blockStatus"].lower() == status.lower():
            return item["childBlock"]


def get_device_by_hostname(hostname):
    """Send a GET call to the IPControl API and return the JSON-formatted response"""

    result = get_ipc(url=f"{endpoints.CROSSWALK_IPADDRESS}?name={hostname}")
    if len(result) == 1:
        return result[0]["interfaces"][0]["ipAddress"][0]


def get_container_by_block(cidr_block):
    """Take the network address of a CIDR notation IP block (ex. '47.44.16.200/29')
    and return the container it comes from in IPC (ex. 'Commercial/LCHTR/SanLuisObispo/Customer')
    """
    url = f"{endpoints.CROSSWALK_IPBLOCK_V1}?blockName={cidr_block}"
    result = get_ipc(url, timeout=300)
    for item in result:
        if item["childBlock"]["blockStatus"].lower() == DEPLOYED_STATUS:
            container = item["childBlock"]["container"]
            return container[0] if isinstance(container, list) else container


def create_static_iprecord(class_type, params, block_type, block_size):
    # compose the remaining parameters for the IPC payload
    ipv6_bool = True if class_type in ["v6_route", "v6_glue"] else False
    block_type = block_type if block_type else "RIP-DIA"

    payload = {
        "accountNumber": params["Account_Number"],
        "blockType": block_type,
        "blockSize": block_size,
        "container": params["container"],
        "description": "",
        "ipv6": ipv6_bool,
        "notes": params["Notes"],
        "notes_2": "",
        "serviceType": "Fiber",
    }

    if block_type == "RIP-DIA":
        url = endpoints.CROSSWALK_IPBLOCK_V2
        payload["companyName"] = params["companyName"]
    else:  # VOIP block type
        url = endpoints.CROSSWALK_IPBLOCK_V3
        payload["zipCode"] = params["Zip_Code"]
        payload["mso"] = "CHTR"

    logger.info(f"Reserving customer IPs: {json.dumps(payload)}")
    res = post_ipc(url=url, payload=payload, timeout=300)
    logger.info(f"Response after reserving customer IPs: {json.dumps(res)}")

    if block_type == "RIP-DIA":
        # if res[0].get("blockSize") in ["48", "64", "128"] and not ipv6_bool:
        #     abort(500, f"IPv4 requested and IPv6 in first index of Crosswalk response: {res[0]}")
        # elif ipv6_bool and res[0].get("blockSize") not in ["48", "64", "128"]:
        #     abort(500, f"IPv6 requested and IPv4 in first index of Crosswalk response: {res[0]}")

        # res = res[0]
        # res["result"] = res["blockName"]

        if res.get("result") and isinstance(res["result"], str):
            return res
        elif res.get("blockName") and isinstance(res["blockName"], str):
            res["result"] = res["blockName"]
            return res
        else:
            abort(500, f"IPControl Unexpected Response - {res}")
        return res
    else:  # VOIP block type
        if res[0]["childBlock"].get("blockSize") in ["48", "64", "128"] and not ipv6_bool:
            abort(500, f"IPv4 requested and IPv6 in first index of Crosswalk response: {res[0]}")
        elif ipv6_bool and res[0]["childBlock"].get("blockSize") not in ["48", "64", "128"]:
            abort(500, f"IPv6 requested and IPv4 in first index of Crosswalk response: {res[0]}")

        res = res[0]
        res["result"] = res["childBlock"]["blockName"]
        return res


def modify_block(data, retain_ip_logic=False):
    url = endpoints.CROSSWALK_IPBLOCK_V2

    if retain_ip_logic:
        notes = data["userDefinedFields"]
        updateReason = "Retaining IPs"
    else:
        notes = ""
        updateReason = "Potential IP Conflict. IP in use on Network. Please investigate."

    payload = {
        "subnet": data["blockName"],
        "updateReason": updateReason,
        "description": "",
        "notes": notes,
        "notes_2": "",
    }

    return put_ipc(url, payload, timeout=300)


def delete_block(block, container, cid, return_resp=False):
    url = f"{endpoints.CROSSWALK_IPBLOCK_V1_DELETE}/delete"

    payload = {"subnet": block, "deleteReason": f"Disconnect 'EPR' {cid}"}
    res = delete_ipc(url, payload, return_resp=return_resp)
    logger.info(f"Delete Block sent, Block: {block} Container: {container} Response: {res}")
    return res


def delete_device(ip):
    """Removes the entry for an IP from IPC"""
    url = endpoints.CROSSWALK_IPADDRESS

    payload = {"ipAddress": ip, "deleteReason": f"Disconnect: IP {ip}"}
    delete_resp = delete_ipc(url=url, payload=payload)

    return delete_resp[0] if isinstance(delete_resp, list) else delete_resp


def get_engineering_info(epr, timeout=30, return_resp=False):  # deprecated
    url = endpoints.CROSSWALK_ENGINEERING
    headers = get_hydra_headers()
    for count in range(3):
        if count > 0:
            sleep(5)
        try:
            resp = requests.get(url=url, headers=headers, params={"query": epr}, verify=False, timeout=timeout)
            if return_resp:
                return resp.json()
            return _handle_ipc_resp(url, "GET", resp=resp)
        except (ConnectionError, requests.ConnectionError, requests.Timeout):
            _handle_ipc_resp(url, "GET", timeout=True)

    logger.error(f"Timed out getting data from IPControl for URL: {url}")
    abort(500, f"Timed out getting data from IPControl for URL: {url} after {count} tries")


def get_billing_id(account_number):  # deprecated
    url = endpoints.CROSSWALK_ACCOUNT
    params = {"query": account_number}
    result = get_ipc(url=url, params=params)
    return result["billingSystemCode"]


def create_subnet_block(body):  # deprecated
    """Creates a subnet block in IPC"""
    url = endpoints.CROSSWALK_IPBLOCK_V2
    account_number = get_engineering_info(body["epr"])
    billing_id = get_billing_id(account_number)
    payload = {
        "accountNumber": account_number,
        "blockType": body["inpChildBlock"]["blockType"],
        "blockSize": str(body["inpChildBlock"]["blockSize"]),
        "companyName": "",
        "billingID": billing_id,
        "ipcContainer": body["inpChildBlock"]["container"],
        "ipv6": body["inpChildBlock"]["ipv6"],
    }

    return post_ipc(url=url, payload=payload)


def get_block_by_blockname(block):
    """GET IP Block details from network address"""
    return get_ipc(f"{endpoints.CROSSWALK_IPBLOCK_V4}?blockName={block}")
