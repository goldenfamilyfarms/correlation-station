from typing import Any, Union

import logging
import requests

from time import sleep

from arda_app.common import url_config, auth_config, app_config
from arda_app.common.utils import sanitize_site_string
from arda_app.common.endpoints import GRANITE_COMMON_PATH
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def get_headers(api_key=None):
    if not api_key:
        if app_config.USAGE_DESIGNATION == "PRODUCTION":
            api_key = auth_config.ARDA_HYDRA_KEY
        else:
            api_key = auth_config.ARDA_HYDRA_STAGIUS_KEY

    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "X-Api-Key": api_key,
        "APPLICATION": "SENSE-ARDA",
    }
    return headers


def _handle_granite_resp(url, method, resp=None, payload=None, timeout=False):
    payload_message = f"PAYLOAD: {payload}"
    if not payload:
        payload_message = ""

    if timeout:
        message = f"Granite timeout - METHOD: {method} URL: {url} {payload_message}"
        logger.exception(message)
        abort(500, message)
    elif "<!DOCTYPE" in resp.text:
        message = (
            f"Hydra Invalid HTML Response - Status Code: {resp.status_code} "
            f"METHOD: {method} URL: {url} RESPONSE: {resp.text}"
        )
        logger.exception(message)
        abort(500, message)
    else:
        if resp.status_code == 200:
            try:
                if method in ["POST", "PUT"]:
                    sleep(2)
                return resp.json()
            except (ValueError, AttributeError):
                message = (
                    f"Failed to decode JSON for Granite response. Status Code: {resp.status_code} "
                    f"METHOD: {method} URL: {url} {payload_message} RESPONSE: {resp.text}"
                )
                logger.exception(message)
                abort(500, message)
        else:
            message = (
                f"Granite unexpected status code: {resp.status_code} METHOD: {method} "
                f"URL: {url} {payload_message} RESPONSE: {resp.text}"
            )
            logger.error(message)
            abort(500, message)


def get_granite(endpoint, timeout=60, return_resp=False, retry=0, key="") -> Any:
    """Send a GET call to the Granite API and return
    the JSON-formatted response"""

    url = f"{url_config.GRANITE_BASE_URL}{GRANITE_COMMON_PATH}{endpoint}"
    headers = get_headers() if not key else get_headers(api_key=key)

    # At least 1 try and N "retry" times to query and read data from Granite (default 1-shot)
    for _ in range(retry + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if resp.text.startswith("<!DOCTYPE"):
                sleep(60)
                continue

            if return_resp and "<!DOCTYPE" not in resp.text:
                # Return the response immediately without further check or logging
                return resp

            return _handle_granite_resp(url, "GET", resp=resp)
        except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
            _handle_granite_resp(url, "GET", timeout=True)


def post_granite(endpoint, payload, timeout=60, return_resp=False) -> Any:
    """Send a POST call to the Granite API and return
    the JSON-formatted response"""

    url = f"{url_config.GRANITE_BASE_URL}{GRANITE_COMMON_PATH}{endpoint}"
    headers = get_headers()
    try:
        resp = requests.post(url, headers=headers, json=payload, verify=False, timeout=timeout)

        if return_resp and "<!DOCTYPE" not in resp.text:
            return resp
        return _handle_granite_resp(url, "POST", resp=resp, payload=payload)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_granite_resp(url, "POST", payload=payload, timeout=True)


def put_granite(endpoint, payload, timeout=60, return_resp=False):
    """Send a PUT call to the Granite API and return
    the JSON-formatted response"""

    url = f"{url_config.GRANITE_BASE_URL}{GRANITE_COMMON_PATH}{endpoint}"
    headers = get_headers()
    try:
        payload["BREAK_LOCK"] = "TRUE"  # Prevent lock errors
        resp = requests.put(url, headers=headers, json=payload, verify=False, timeout=timeout)

        if return_resp and "<!DOCTYPE" not in resp.text:
            return resp
        return _handle_granite_resp(url, "PUT", resp=resp, payload=payload)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_granite_resp(url, "PUT", payload=payload, timeout=True)


def delete_granite(endpoint, payload, timeout=60, return_resp=False) -> Any:
    """Send a DELETE call to the Granite API and return
    the JSON-formatted response"""

    url = f"{url_config.GRANITE_BASE_URL}{GRANITE_COMMON_PATH}{endpoint}"
    headers = get_headers()
    try:
        resp = requests.delete(url, headers=headers, json=payload, verify=False, timeout=timeout)

        if return_resp and "<!DOCTYPE" not in resp.text:
            return resp
        return _handle_granite_resp(url, "DELETE", resp=resp, payload=payload)
    except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout, requests.ReadTimeout):
        _handle_granite_resp(url, "DELETE", payload=payload, timeout=True)


def get_equipment_buildout(tid):
    """GET to /equipmentBuildouts using device TID"""
    equipment_build_url = f"/equipmentBuildouts?EQUIP_NAME={tid}"
    equipment_build_data = get_granite(equipment_build_url)
    if "retString" in equipment_build_data:
        logger.error(
            f"Unable to locate CPE shelf record created for {tid} in Granite \n"
            f"URL: {equipment_build_url} \nResponse: {equipment_build_data}"
        )
        abort(
            500,
            message=f"Unable to locate the CPE Shelf record created for {tid} in Granite",
            url=equipment_build_url,
            response=equipment_build_data,
        )
    return equipment_build_data


def get_equipment_buildout_slot(tid, slot):
    """GET to /equipmentBuildouts using device TID"""
    equipment_build_url = f"/equipmentBuildouts?EQUIP_NAME={tid}&SLOT={slot}"
    equipment_build_data = get_granite(equipment_build_url)
    if "retString" in equipment_build_data:
        logger.error(
            f"Unable to locate CPE shelf record created for {tid} in Granite \n"
            f"URL: {equipment_build_url} \nResponse: {equipment_build_data}"
        )
        abort(
            500,
            message=f"Unable to locate the CPE Shelf record created for {tid} in Granite",
            url=equipment_build_url,
            response=equipment_build_data,
        )
    return equipment_build_data


def get_device_vendor(equipment_name) -> str:
    clli = equipment_name[0:8]

    granite_url = f"/equipments?CLLI={clli}&OBJECT_TYPE=SHELF&EQUIP_NAME={equipment_name}&WILD_CARD_FLAG=1"
    response = get_granite(granite_url)
    try:
        data = response[0]
        vendor = data.get("EQUIP_VENDOR", "") if isinstance(data, dict) else ""
        return vendor
    except (IndexError, KeyError):
        abort(
            500,
            "Error Code: M015 - The network device required onboarding "
            f"but no device vendor for {equipment_name} was provided by Granite.",
        )


def get_selected_vendor(source="internal"):
    """get selected vendor (ARDA or RAD) from randomizer"""
    try:
        api_key = auth_config.ARDA_ADVA_RAD_HYDRA_KEY
        resp = (
            get_granite("/aDVAvsRAD?DATE=60") if source == "internal" else get_granite("/aDVAvsRAD?DATE=60", key=api_key)
        )
        return resp[0]
    except Exception:
        # Default to RAD if issue with endpoint
        return {"VENDOR": "RAD"}


def get_device_fqdn(equipment_name):
    clli = equipment_name[0:8]
    granite_url = f"/equipments?CLLI={clli}&OBJECT_TYPE=SHELF&EQUIP_NAME={equipment_name}&WILD_CARD_FLAG=1"
    response = get_granite(granite_url)
    try:
        data = response[0]
        host = data.get("FQDN")
        if host is None:
            abort(500, f"No FQDN Address found for {equipment_name} in Granite")
        return host
    except (IndexError, KeyError):
        abort(500, "Error Code: M014 - The network device required onboarding but no FQDN was found in granite.")


def get_device_model(equipment_name):
    # Replace dash with space in clli's that are not 8 characters (LEE-MA04 -> LEE MA04)
    clli = equipment_name[0:8].replace("-", " ")
    granite_url = f"/equipments?CLLI={clli}&OBJECT_TYPE=SHELF&EQUIP_NAME={equipment_name}&WILD_CARD_FLAG=1"
    response = get_granite(granite_url)

    if isinstance(response, list):
        data = response[0]
        model = data.get("EQUIP_MODEL")
        if model is None:
            abort(500, f"No device model found for {equipment_name} in Granite")
        return model

    abort(500, "Error Code: M014 - The network device model was not found in Granite.")


def insert_card_template(uplink_port, card_template):
    payload = {
        "SHELF_NAME": uplink_port["EQUIP_NAME"],
        "CARD_TEMPLATE_NAME": card_template,
        "SLOT_INST_ID": uplink_port["SLOT_INST_ID"],
    }
    return post_granite("/cards", payload)


def get_available_uplink_ports(hub_clli_code, bandwidth_string):
    """returns a list of available uplink ports from Granite"""
    granite_url = f"/uplinkPorts?CLLI={hub_clli_code}&BANDWIDTH={bandwidth_string}"

    granite_resp = get_granite(granite_url)
    # logger.debug(f'GRANITE_UPLINK_PORT_RESPONSE: {granite_resp}')
    if isinstance(granite_resp, dict) and granite_resp.get("retString"):
        if "JUNIPER" in granite_resp["retString"].upper():
            abort(
                500,
                f"Error code: G022 - No Juniper devices found for Hub CLLI: {hub_clli_code}. "
                f"Bandwidth: {bandwidth_string}",
            )
        else:
            abort(
                500,
                f"Error code: G019 - No ports found in Granite for Hub CLLI: {hub_clli_code}. "
                f"Bandwidth: {bandwidth_string}",
            )
    return filter_out_ports(granite_resp)


def filter_out_ports(ports):
    filtered_ports = []
    acx_port_slots = ("48", "49", "50", "51")

    for port in ports:
        if (
            "FAN" in port["SLOT"]
            or "POWER" in port["SLOT"]
            or "JPSU" in port["SLOT"]
            or "CONSOLE" in port["SLOT"]
            or ("ACX5448" in port["MODEL"] and port["SLOT"] in acx_port_slots)
        ):
            continue
        else:
            filtered_ports.append(port)

    return filtered_ports


def get_qc_available_uplink_ports(z_clli_code, bandwidth_string):
    granite_url = f"/mtuHandoffPort?CLLI={z_clli_code}&PORT_BW={bandwidth_string}"

    granite_resp = get_granite(granite_url)

    if isinstance(granite_resp, dict):
        abort(500, f"Error Code: G005 - No ports found in Granite for z CLLI {z_clli_code}")

    # multi MTU check
    equip_name = granite_resp[0]["EQUIP_NAME"]

    for port in granite_resp:
        if port["EQUIP_NAME"] != equip_name:
            msg = "Multiple MTU's at this location. Unable to determine which MTU to use. Please investigate"
            logger.error(msg)
            abort(500, msg)

    # updating expected_paid for rad 220A
    for index, port in enumerate(granite_resp):
        if port.get("MODEL") == "ETX-220A":
            if "ETH PORT" in port.get("EXPECTED_PAID"):
                granite_resp[index]["EXPECTED_PAID"] = granite_resp[index]["EXPECTED_PAID"].replace("ETH PORT ", "")

    return granite_resp


def put_port_access_id(port_inst_id, port_access_id):
    payload = {"PORT_INST_ID": port_inst_id, "PORT_ACCESS_ID": port_access_id}
    granite_resp = put_granite("/ports", payload)
    return granite_resp


def get_available_equipment_ports(equipment_name):
    """returns a list of available equipment ports"""
    equipment_name = equipment_name.replace("#", "%23")
    url = f"/equipments?CLLI={equipment_name[0:8]}&OBJECT_TYPE=PORT&USED=AVAILABLE&EQUIP_NAME={equipment_name}"
    granite_resp = get_granite(url)
    if isinstance(granite_resp, dict) and "No records found" in granite_resp.get("retString"):  # type: ignore
        abort(
            500,
            f"Granite: No records found in available equipment ports for {equipment_name} "
            f"GET url: {url} "
            f"Granite Response: {granite_resp}",
        )
    return granite_resp


def get_used_equipment_ports(equipment_name):
    """returns a list of used equipment ports"""
    url = (
        f"/equipments?CLLI={equipment_name[0:8]}&EQUIP_NAME={equipment_name}"
        "&OBJECT_TYPE=PORT&USED=IN%20USE&WILD_CARD_FLAG=1"
    )

    granite_resp = get_granite(url)
    if isinstance(granite_resp, dict) and "No records found" in granite_resp.get("retString"):  # type: ignore
        abort(
            500,
            f"Granite: No records found in used equipment ports for {equipment_name} "
            f"GET url: {url} "
            f"Granite Response: {granite_resp}",
        )
    return granite_resp


def get_existing_shelf(z_clli, z_site_name):
    """returns correct z-side shelf to use for the transport path given the z-side site name"""
    endpoint = f"/equipments?SITE_NAME={z_site_name}&OBJECT_TYPE=SHELF&EQUIP_NAME={z_clli}%ZW&WILD_CARD_FLAG=1"

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_EXISTING_SHELF_RESPONSE: {granite_resp}")
        return granite_resp
    except (IndexError, KeyError):
        return None


def get_next_available_zw_shelf(z_clli: str, z_site_name: str) -> str:
    """returns next available ZW shelf at Z CLLI"""

    # use existing gatekeeper call to find next ZW shelf
    zw_candidate = get_next_zw_shelf(z_site_name)

    # check to see if ZW shelf exists at Z CLLI
    url = f"/equipments?OBJECT_TYPE=SHELF&CLLI={z_clli}&EQUIP_NAME={zw_candidate}&WILD_CARD_FLAG=1"
    try:
        resp = get_granite(url)
        logger.debug(f"GRANITE_SHELF_EXISTS_RESPONSE: {resp}")
    except Exception:
        return None

    # if no response, return ZW shelf TID name
    if (isinstance(resp, dict)) and ("retString" in resp) and ("No records found" in resp.get("retString", "")):
        return zw_candidate

    # if ZW exists, find the next available ZW
    available_zw = identify_available_zw_shelf(z_clli, zw_candidate)

    # return next available ZW if found
    if available_zw:
        return available_zw
    else:
        msg = f"Unable to identify the next available ZW shelf for {z_site_name}"
        logger.error(msg)
        abort(500, msg)


def identify_available_zw_shelf(z_clli: str, zw_candidate: str) -> str:
    """search logic for next available ZW shelf at Z CLLI"""

    # search for next available shelf after ZW candidate
    shelf_designator = zw_candidate.split(z_clli)[1].split("ZW")[0]
    zw_increments = [str(c) for c in range(1, 10)] + ["0"] + list(map(chr, range(65, 91)))
    try:
        zw_increments = [zw_increments[i] for i in range(zw_increments.index(shelf_designator) + 1, len(zw_increments))]
    except ValueError:
        msg = f"Unable to determine the next available ZW shelf after {zw_candidate} at {z_clli}"
        logger.error(msg)
        abort(500, msg)
    if not zw_increments:
        msg = f"No ZW shelves available at {z_clli}"
        logger.error(msg)
        abort(500, msg)

    # iterate over possible ZW shelf names bounded by search threshold
    try_count = 0
    max_tries = 3
    while try_count < max_tries:
        next_zw = f"{z_clli}{zw_increments[try_count]}ZW"
        url = f"/equipments?OBJECT_TYPE=SHELF&CLLI={z_clli}&EQUIP_NAME={next_zw}&WILD_CARD_FLAG=1"
        try:
            resp = get_granite(url)
            logger.debug(f"GRANITE_SHELF_EXISTS_RESPONSE: {resp}")
        except Exception:
            return None
        # if no response, return ZW shelf TID name
        if (isinstance(resp, dict)) and ("retString" in resp) and ("No records found" in resp.get("retString", "")):
            return next_zw
        try_count += 1

    # search threshold reached
    if try_count == max_tries:
        msg = f"Unable to find next available ZW shelf at {z_clli} after {max_tries} search attempts"
        logger.error(msg)
        abort(500, msg)


def get_shelves_at_site(z_clli, z_site_name):
    """returns correct z-side shelf to use for the transport path given the z-side site name"""
    z_site_name = sanitize_site_string(z_site_name)
    endpoint = f"/equipments?CLLI={z_clli}&OBJECT_TYPE=SHELF&SITE_NAME={z_site_name}"

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_EXISTING_SHELF_RESPONSE: {granite_resp}")
        return granite_resp
    except (IndexError, KeyError):
        return None


def get_site_available_ports(site_name):
    site_name = sanitize_site_string(site_name)
    endpoint = f"/customerPortAvailability?SITE_NAME={site_name}"
    granite_resp = get_granite(endpoint)
    return granite_resp


def get_existing_ctbh_cpe_shelf(clli, site_name):
    """Returns found shelves at site based on CTBH CPE naming convention 7%W"""
    endpoint = f"/equipments?SITE_NAME={site_name}&OBJECT_TYPE=SHELF&EQUIP_NAME={clli}7%W&WILD_CARD_FLAG=1"
    granite_resp = get_granite(endpoint)
    return granite_resp


def get_aw_shelf(hub_clli):
    """returns correct a-side shelf to use for the transport path given the hub clli"""
    endpoint = f"/awShelfs?SITE_HUM_ID={hub_clli}"

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_EXISTING_AW_SHELF_RESPONSE: {granite_resp}")
        return granite_resp[0].get("SHELF")
    except (IndexError, KeyError):
        return


def get_correct_npa(data, npa_type):
    hub_type = ("HE-HUB", "HUB", "XHUB", "HEAD END")
    mtu_type = "ACTIVE MTU"
    npa_nxxs = []
    for npa in data:
        npa_nxxs.append(npa.get("NPA_NXX"))
        if npa_type == "HUB":
            if npa.get("TYPE") in hub_type:
                return npa["NPA_NXX"]
        elif npa_type == "MTU":
            if npa.get("TYPE") in mtu_type:
                return npa["NPA_NXX"]

    if npa_nxxs:
        # if HUB doesn't exist - return the most common NPA_NXX
        return max(set(npa_nxxs), key=npa_nxxs.count)

    raise KeyError


def get_npa(hub_clli_code, npa_type="HUB"):
    """returns the npa-nxx for a given clli code"""
    endpoint = f"/npaNxxs?CLLI={hub_clli_code}"
    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_NPA_RESPONSE: {granite_resp}")
        npa_nxx = get_correct_npa(granite_resp, npa_type)
        return npa_nxx
    except (IndexError, KeyError):
        abort(500, f"Error Code: G011 - NPA not found in Granite for hub CLLI {hub_clli_code}")


def get_npa_qa(z_clli_code):
    """returns the npa-nxx for a given z_clli code"""
    endpoint = f"/npaNxxs?CLLI={z_clli_code}"
    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_NPA_RESPONSE: {granite_resp}")
        return granite_resp[0]["NPA_NXX"]
    except (IndexError, KeyError):
        abort(500, f"ARDA - Error Code: G011 - NPA not found in Granite for z CLLI {z_clli_code}")


def get_path_elements_l1(path_id):
    """Returns lvl1 path element only"""
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={path_id}&LVL=1"
    return get_granite(endpoint)


def get_path_elements_inst_l1(path_instid):
    """Returns lvl1 path element only"""
    endpoint = f"/pathElements?CIRC_PATH_INST_ID={path_instid}&LVL=1"
    return get_granite(endpoint)


def get_path_elements_l2(path_id):
    """Returns lvl2 path element only"""
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={path_id}&LVL=2"
    return get_granite(endpoint)


def get_path_elements(path_id, url_params=""):
    """Returns all path elements"""
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={path_id}{url_params}"
    resp = get_granite(endpoint)
    if "retString" in resp:
        logger.error(f"No circuit data found in Granite for {path_id}\nResponse:\n{resp}\n")
        abort(500, message=f"Granite endpoint {endpoint} error: {resp}")
    return resp


def get_circuit_site_info(cid, wild_card_flag=0, path_class="P"):
    endpoint = f"/circuitSites?CIRCUIT_NAME={cid}&PATH_CLASS={path_class}&WILD_CARD_FLAG={wild_card_flag}"
    return get_granite(endpoint)


def get_shelf_used_ports(clli, device, object_type="PORT", wild_card_flag=1):
    endpoint = (
        f"/equipments?CLLI={clli}&EQUIP_NAME={device}&OBJECT_TYPE={object_type}"
        f"&USED=IN%20USE&WILD_CARD_FLAG={wild_card_flag}"
    )
    return get_granite(endpoint)


def get_circuit_uda_info(cid):
    endpoint = f"/circuitUDAs?CIRC_PATH_INST_ID={cid}"
    return get_granite(endpoint)


def get_path_uda(cid):
    endpoint = f"/circuitUDAs?PATH_NAME={cid}&REV_NBR=1"
    return get_granite(endpoint)


def get_sites(clli: str):
    """returns the npa-nxx for a given clli code"""
    endpoint = f"/sites?CLLI={clli}"
    return get_granite(endpoint)


def get_site(site_hum_id: str) -> dict:
    """returns the npa-nxx for a given SITE_HUM_ID"""
    endpoint = f"/sites?SITE_HUM_ID={site_hum_id}"
    return get_granite(endpoint)


def get_result_as_list(url, timeout=60, retry=0):
    result = get_granite(url, timeout=timeout, retry=retry)
    if isinstance(result, dict) and result.get("retCode"):
        if "no records found" in result["retString"].lower():
            return []
        else:
            logger.error("Granite responded with a failure message: ", result["retString"])
            abort(500, f"{result['retString']}")
    else:
        return result


def get_next_zw_shelf(z_site_name, length: int = 11):
    """Gets the next available shelf for the given z site name"""
    endpoint = f"/nextZWshelf?SITE_HUM_ID={z_site_name}"
    shelf_data = get_granite(endpoint)
    if isinstance(shelf_data, list):
        for shelf in shelf_data:
            if isinstance(shelf, dict):
                result = shelf.get("SHELF", "")
                if len(result) == length:
                    return result
    elif isinstance(shelf_data, dict):
        result = shelf_data.get("SHELF", "")
        if len(result) == length:
            return result
    abort(500, f"Incorrect shelf in Granite for Z Site Name {z_site_name}: {shelf_data}")


def get_ip_subnets(cid):
    """Gets a circuit's IPv4 & IPv6 subnets from Granite"""
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={cid}"
    resp = get_granite(endpoint)
    if isinstance(resp, dict):
        if resp.get("retString") and "No records found" in resp["retString"]:
            abort(500, f"{cid} does not have an existing record in Granite")
    elif isinstance(resp, list):
        data = resp[0]

    ipv4_lan = data.get("IPV4_ASSIGNED_SUBNETS")
    ipv6_route = data.get("IPV6_ASSIGNED_SUBNETS")
    ipv4_glue = data.get("IPV4_GLUE_SUBNET")
    ipv6_glue = data.get("IPV6_GLUE_SUBNET")

    if ipv4_lan is None and ipv6_route is None:
        abort(500, f"{cid} did not have any IPv4 or IPv6 addresses shown in Granite")
    else:
        return {
            "IPV4_ASSIGNED_SUBNETS": ipv4_lan,
            "IPV6_ASSIGNED_SUBNETS": ipv6_route,
            "IPV4_GLUE_SUBNET": ipv4_glue,
            "IPV6_GLUE_SUBNET": ipv6_glue,
        }


def assign_relationship(path_inst_id, related_path_inst_id):
    granite_url = "/pathRelationship"
    payload = {
        "PATH_INST_ID": path_inst_id,
        "RELATED_PATH_INST_ID": related_path_inst_id,
        "RELATIONSHIP": "BACKUP-WIRELESS",
    }
    granite_resp = put_granite(granite_url, payload)
    return granite_resp


def get_equipment_buildout_v2(tid):
    """GET to /equipmentBuildouts using device TID"""
    equipment_build_url = f"/equipmentBuildouts?EQUIP_NAME={tid}"
    return get_granite(equipment_build_url)


def get_vgw_id(cid: str):
    path_elements = get_path_elements_l1(cid)
    # Find TIDs with "G01" ... "G91", "G1W" ... "G9W"
    tid_suffix = [f"G{i}W" for i in range(1, 10)] + [f"G{j}1" for j in range(0, 10)]
    element_reference = ""
    for element in path_elements:
        tid: str = element["TID"] if element.get("TID") else ""
        if any(suffix in tid for suffix in tid_suffix):
            element_reference = element["ELEMENT_REFERENCE"]
            break
    return element_reference


def get_existing_shelf_v2(z_clli):
    """returns correct existing shelf equipment to be use for the transport path given a existing CLLI"""
    endpoint = f"/equipments?OBJECT_TYPE=SHELF&EQUIP_NAME={z_clli}_ZW&WILD_CARD_FLAG=1"

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_NEW_SHELF_RESPONSE: {granite_resp}")
        return granite_resp
    except IndexError:
        abort(500, f"Error Code: Shelf not found in Granite with CLLI {z_clli}")


def get_site_data(site_name: str):
    """returns the site information for a given site name"""
    site_name = site_name.replace("&", "%26")
    endpoint = f"/sites?SITE_HUM_ID={site_name}"
    return get_granite(endpoint)


def get_shelf_udas(equip_inst_id: str):
    """returns the UDAs for a given equipment inst id"""
    endpoint = f"/shelfUDAs?EQUIP_INST_ID={equip_inst_id}"
    return get_granite(endpoint)


def get_equipid(equip_name: str):
    """returns the equipment inst id"""
    endpoint = f"/equipments?OBJECT_TYPE=SHELF&EQUIP_NAME={equip_name}&WILD_CARD_FLAG=1"
    return get_granite(endpoint)


def get_hub_site(query: str):
    """Search for hub site based on SITE_ID partial match and return CLLI"""
    endpoint = f"/sites?SITE_HUM_ID={query}&SITE_TYPE=HUB%2CHEAD%20END%2CHE-HUB%2CMDC&wildCardFlag=1&STATUS=Live"
    response = get_granite(endpoint)

    if isinstance(response, dict) and "retString" in response:
        return False
    if isinstance(response, list) and len(response) > 1:
        npa_code = response[0]["npaNxx"]
        clli = response[0]["clli"]
        for site in response:
            if site["npaNxx"] != npa_code or site["clli"] != clli:
                return False
    return response[0].get("clli")


def get_network_association(network_inst_id: str) -> Union[str, list]:
    """Returns the association data of a network instance ID"""
    endpoint = f"/ntwkAssociations?NETWORK_INST_ID={network_inst_id}"
    return get_granite(endpoint)


def get_path_association(path_inst: str):
    endpoint = f"/pathAssociations?PATH_INST_ID={path_inst}"
    return get_granite(endpoint)


def assign_association(path_inst_id, evcid, association_name, range_name):
    """Adds association to provided CID revision"""
    granite_url = "/pathAssociation"
    payload = {
        "PATH_INST_ID": path_inst_id,
        "RANGE_NAME": range_name,
        "ASSOCIATION_NAME": association_name,
        "NUMBER_TYPE": "EVC ID",
        "STATUS": "Reserved",
        "NUMBER": evcid,
    }
    granite_resp = put_granite(granite_url, payload)
    return granite_resp


def assign_network_association(network_id, evcid, range_name):
    granite_url = "/ntwkAssociation"

    payload = {
        "NETWORK_INST_ID": network_id,
        "RANGE_NAME": range_name,
        "ASSOC_NAME": "EVC ID NUMBER/NETWORK",
        "NUMBER_TYPE": "EVC ID",
        "NUMBER": evcid,
    }

    granite_resp = put_granite(granite_url, payload)
    return granite_resp


def edna_mpls_in_path(cid):
    """Return True if the CHTRSE.EDNA.MPLS cloud element is in the path"""
    url = f"/pathElements?CIRC_PATH_HUM_ID={cid}&LVL=1"
    resp = get_granite(url)
    if isinstance(resp, list):
        for element in resp:
            if element["ELEMENT_NAME"] == "CHTRSE.EDNA.MPLS":
                return True
    return False


def update_port_paid(port_inst_id, paid):
    granite_url = "/ports"
    payload = {"PORT_INST_ID": port_inst_id, "PORT_ACCESS_ID": paid}
    granite_resp = put_granite(granite_url, payload)
    return granite_resp


def get_network_elements(network_inst_id: str) -> dict:
    """Retrieve the elements of the network"""
    url = f"/networkElements?CIRC_PATH_INST_ID={network_inst_id}"
    resp = get_granite(url)
    return resp


def get_network(network_name: str) -> dict:
    """Retrieve the elements of the network"""
    url = f"/network?NETWORK_NAME={network_name}&NETWORK_REV=1"
    resp = get_granite(url)
    return resp


def update_network_status(network_inst_id: str, status: str):
    """Update network with a passed-in status"""
    payload = {
        "NETWORK_INST_ID": network_inst_id,
        "NETWORK_BANDWIDTH": "VPLS",
        "NETWORK_TOPOLOGY": "Mesh",
        "NETWORK_STATUS": status,
    }
    return put_granite("/networks", payload)


def update_network_vlan(network_inst_id: str, network_vlan_list: list, granite_vlan):
    """Compares the granite and network VLANS and updates granite network with GSIP values"""
    network_vlan = ""

    if network_vlan_list:
        # live circuit with network vlans
        if all(i == network_vlan_list[0] for i in network_vlan_list):
            network_vlan = network_vlan_list[0]
        else:
            msg = "Network VLANs do not match. Please investigate"
            logger.error(msg)
            abort(500, msg)

    if not granite_vlan and not network_vlan:
        network_vlan = "1200"
    elif granite_vlan and not network_vlan:
        network_vlan = granite_vlan

    payload = {
        "NETWORK_INST_ID": network_inst_id,
        "NETWORK_BANDWIDTH": "VPLS",
        "NETWORK_TOPOLOGY": "Cloud",
        "UDA": {"EVC ATTRIBUTES": {"NETWORK VLAN-ID": network_vlan}},
    }

    return put_granite("/networks", payload)


def create_vpls_network(new_vrfid):
    """Creates a new VPLS element"""
    payload = {
        "NETWORK_NAME": new_vrfid,
        "NETWORK_TEMPLATE_NAME": "WS ELAN VPLS",
        "NETWORK_BANDWIDTH": "VPLS",
        "NETWORK_TOPOLOGY": "Cloud",
        "NETWORK_STATUS": "Planned",
        "UDA": {"EVC ATTRIBUTES": {"NETWORK VLAN-ID": "1200"}},
    }

    granite_resp = post_granite("/networks", payload)
    return granite_resp


def get_attributes_for_path(cid: str) -> dict:
    """returns a list of summary attributes for queried path"""
    url = f"/paths?CIRC_PATH_HUM_ID={cid}"
    granite_resp = get_granite(url)
    if isinstance(granite_resp, dict) and "No records found" in granite_resp.get("retString"):  # type: ignore
        abort(
            500,
            f"Granite: No records found in path attributes for {cid} GET url: {url} Granite Response: {granite_resp}",
        )

    return granite_resp


def get_source_mep(evcid: str):
    endpoint = f"/nextSourceMEP?MEP_ID={evcid}"
    return get_granite(endpoint)


def get_network_path(network_name: str) -> dict:
    """Retrieve the list of related Networks"""
    url = f"/paths?CIRC_PATH_HUM_ID={network_name}&wildCardFlag=1"
    resp = get_granite(url)
    return resp


def update_vgw_shelf_ipv4_address(cid: str, shelf_ipv4: str):
    """Update IPv4 address of a VGW shelf"""
    url = "/shelves"
    granite_payload = {
        "SHELF_INST_ID": get_vgw_id(cid),
        "UDA": {"Device Config-Equipment": {"IPv4 ADDRESS": shelf_ipv4}},
    }
    return put_granite(url, granite_payload)


def get_segments(inst_id: str, params: str = None) -> list:
    """Retrieve a list of segments associated with instance ID"""
    url = f"/segments{params}{inst_id}"
    resp = get_granite(url, timeout=90)
    return resp


def get_transport_channels(transport: str) -> list:
    url = f"/pathChanAvailability?PATH_NAME={transport}"
    resp = get_granite(url)
    if isinstance(resp, dict) and "No records found" in resp.get("retString"):
        abort(500, f"No records found for transport: {transport}")
    return resp


def get_a_side_router(a_clli: str, a_site_name: str) -> str:
    a_side_router = ""
    url = f"/equipments?CLLI={a_clli}&OBJECT_TYPE=SHELF&SITE_NAME={a_site_name}"
    data = get_granite(url)
    if data and isinstance(data, list):
        for dev in data:
            try:
                equip_category = dev["EQUIP_CATEGORY"]
            except Exception:
                logger.info("Unable to find equipment category of A-side router")
            if equip_category.upper() == "ROUTER":
                try:
                    equip_name = dev["EQUIP_NAME"]
                except Exception:
                    msg = "Unable to find equipment name of A-side router"
                    logger.error(msg)
                    abort(500, msg)
                a_side_router = equip_name.split("/")[0]
                break
        else:
            msg = "Unable to find A-side router"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = "Unable to pull equipments data for A-side router"
        logger.error(msg)
        abort(500, msg)
    if not a_side_router:
        msg = "Undefined A-side router"
        logger.error(msg)
        abort(500, msg)
    return a_side_router


def paths_from_site(site_name):
    # replace any occurence of "&"" with "%26" in site name
    site_name = site_name.replace("&", "%26")
    # uses sitename to get related paths
    url = f"/pathsFromSite?SITE_NAME={site_name}"
    data = get_granite(url)
    if isinstance(data, dict):
        msg = f"Unable to find any path for site name: {site_name}"
        abort(500, msg)
    else:
        return data


def find_nni_device(nni):
    url = f"/pathElements?CIRC_PATH_HUM_ID={nni}&LVL=1"
    resp = get_granite(url)

    if isinstance(resp, list):
        for element in resp:
            if element["ELEMENT_TYPE"] == "PORT":
                a_side_router = element["TID"]
                return a_side_router

    msg = "Unable to find A-side router"
    logger.error(msg)
    abort(500, msg)


def get_vendor(vendor):
    url = f"/segmentVendors?VENDOR_NAME={vendor}&wildCardFlag=TRUE"
    resp = get_granite(url)

    return resp


def get_paths_from_ip(ip: str) -> list:
    url = f"/pathsFromIp?IP_ADDRESS={ip}"
    resp = get_granite(url)
    return resp


def get_port_udas(port_inst_id):
    """returns a list of port udas from Granite"""
    granite_url = f"/portUDAs?PORT_INST_ID={port_inst_id}"

    granite_resp = get_granite(granite_url)
    if isinstance(granite_resp, list):
        return granite_resp
    else:
        abort(500, "No port UDAs found")
