import logging
import requests
import re

from requests import JSONDecodeError

import palantir_app
from common_sense.common.errors import abort, error_formatter, get_standard_error_summary, GRANITE, MISSING_DATA
from palantir_app.common.utils import get_hydra_headers, is_ctbh
from palantir_app.common.endpoints import (
    GRANITE_ELEMENTS,
    GRANITE_EQUIPMENTS,
    GRANITE_PATHS,
    GRANITE_PATHS_FROM_SITE,
    GRANITE_SHELVES,
    GRANITE_SITES,
    GRANITE_UDA,
    GRANITE_ASSOCIATIONS_GET,
    GRANITE_ASSOCIATIONS_REMOVE,
    SHELF_UDAS,
    ELAN_SLM,
    GRANITE_PATH_RELATIONSHIPS,
)

logger = logging.getLogger(__name__)

granite_base_url = palantir_app.url_config.GRANITE_BASE_URL


NO_RECORDS_FOUND = "No records found with the specified search criteria..."


def granite_get(endpoint, params=None, timeout=60, return_response_obj=False, handle_not_found=False, operation=""):
    headers = get_hydra_headers(operation)
    url = f"{granite_base_url}{endpoint}"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout, verify=False)
        if return_response_obj:
            return resp
        if resp.status_code == 200:
            granite_resp = resp.json()
            # Check for CID not found
            if "retString" in granite_resp and "No records" in granite_resp["retString"]:
                if handle_not_found:
                    return granite_resp["retString"]
                msg = f"No records found for URL: {url}"
                logger.error(msg)
                abort(502, msg)
            else:
                return granite_resp
        else:
            msg = f"Unexpected error from Granite for URL: {url} Status Code: {resp.status_code}"
            logger.error(msg)
            abort(502, msg)
    except (ConnectionError, requests.ConnectionError) as exception:
        msg = f"Failed connecting to Granite for URL: {url} Error: {exception}"
        logger.error(msg)
        abort(504, msg)
    except requests.ReadTimeout as exception:
        msg = f"Connected to Granite and timed out waiting for data for URL: {url}  Error: {exception}"
        logger.error(msg)
        abort(504, msg)


def granite_put(endpoint, payload, best_effort=False, calling_function="not specified"):
    """Send a PUT call to the Granite API and return
    the JSON-formatted response"""
    headers = get_hydra_headers()
    url = f"{granite_base_url}{endpoint}"

    try:
        r = requests.put(url, headers=headers, json=payload, verify=False, timeout=60)
        if r.status_code in [200, 204]:
            return r.json()

        granite_resp = r.json()
        if "retString" in granite_resp:
            error_msg = f"Granite response: {granite_resp['retString']}; \
                calling function: {calling_function}; payload: {payload}"
        else:
            error_msg = (
                f"Unexpected error from Granite for url: {url}: Headers = {clean_headers(headers)}, Payload = {payload}"
            )
        if best_effort:
            return {"errorStatusCode": r.status_code, "errorStatusMessage": error_msg}
        else:
            abort(502, error_msg)
    except (ConnectionError, requests.ConnectionError) as exception:
        abort(
            504,
            f"Connection timed out updating data to Granite for url: {url}:"
            f" Headers = {clean_headers(headers)}, Payload = {payload} Error = {exception}",
        )
    except requests.ReadTimeout as exception:
        abort(
            504,
            f"Connection timed out updating data to Granite for url: {url}:"
            f" Headers = {clean_headers(headers)}, Payload = {payload} Error = {exception}",
        )


def delete_with_query(endpoint, payload=None, query=None, timeout=60):
    headers = get_hydra_headers()
    url = f"{granite_base_url}{endpoint}"
    try:
        resp = requests.delete(url, headers=headers, json=payload, params=query, verify=False, timeout=timeout)
        return resp.json()
    except (ConnectionError, requests.ConnectionError, requests.ReadTimeout) as exception:
        abort(
            (
                504,
                f"Connection Error While Deleting data from Granite for\
                url: {url}, Error = {exception}",
            )
        )


def granite_delete(endpoint, payload, timeout=60):
    headers = get_hydra_headers()
    url = f"{granite_base_url}{endpoint}"
    max_retries = 3
    if "CIRC_PATH_INST_ID" in payload:
        CIRC_PATH_INST_ID = payload["CIRC_PATH_INST_ID"]
    elif "PATH_INST_ID" in payload:
        CIRC_PATH_INST_ID = payload["PATH_INST_ID"]
    else:
        CIRC_PATH_INST_ID = ""
    CID = payload["PATH_NAME"]

    retry_count = 0
    while retry_count <= max_retries:
        try:
            resp = requests.delete(url, headers=headers, json=payload, verify=False, timeout=timeout)
            if resp.status_code in [200, 202, 204]:
                return (200, f"Live Revision Deleted: CID = {CID} , CIRC_PATH_INST_ID = {CIRC_PATH_INST_ID}")
            else:
                retry_count = retry_count + 1
                if retry_count > max_retries:
                    return (
                        502,
                        f"Unexpected error from Granite for url: {url}:"
                        f" Headers = {clean_headers(headers)}, Payload = {payload}, Response = {resp.text}",
                    )
        except (ConnectionError, requests.ConnectionError, requests.ReadTimeout) as exception:
            if retry_count > max_retries:
                return (
                    504,
                    f"Connection Error While Deleting data from Granite for\
                         url: {url}, Headers = {clean_headers(headers)}, Payload = {payload} Error = {exception}",
                )
            else:
                retry_count = retry_count + 1


def get_circuit_devices(cid):
    """Granite API to retrieve device list of a CID"""
    params = {
        "CIRC_PATH_HUM_ID": f"{cid}",
        "ELEMENT_TYPE": "PORT",
        "ELEMENT_CATEGORY": "SWITCH,NIU,ROUTER,OPTICAL NETWORK UNIT,CABLE MODEM,"
        "ONS,DIGITAL CONTENT MANAGER,WIFI AP,OPTICAL LINE TERMINAL,"
        "MEDIA CONVERTER,QAM,LINE/ACCESS GATEWAY,VIDEO ENCODER,"
        "SERVER,WIFI CONTROLLER,SESSION BORDER CONTROLLER,"
        "VIDEO MODULATOR,DACS,MICROWAVE,CMTS,SMART PDU,"
        "OPTICAL NETWORK TERMINAL",
    }
    timeout = 60  # secs
    return granite_get(GRANITE_ELEMENTS, params, timeout)


def get_path_elements(cid, level=1):
    """Granite synchronous GET path elements using service path-circuit id (cid)"""
    params = {"CIRC_PATH_HUM_ID": cid, "LVL": level}
    path_elements = granite_get(GRANITE_ELEMENTS, params=params)

    if not path_elements:
        abort(502, f"No path elements found for CID: {cid}: {GRANITE_ELEMENTS}")

    return path_elements


def get_path_details_by_cid(cid, return_response=False):
    """Granite synchronous GET path info using service path-circuit id (cid)"""
    params = {"CIRC_PATH_HUM_ID": cid}
    return granite_get(GRANITE_PATHS, params=params, return_response_obj=return_response)


def call_granite_for_circuit_devices(cid, url_version, operation="general"):
    """Granite API to retrieve device list of a CID"""
    headers = get_hydra_headers(operation, accept_text_html_xml=True)
    payload = {
        "ELEMENT_TYPE": "PORT",
        "ELEMENT_CATEGORY": "SWITCH,NIU,ROUTER,OPTICAL NETWORK UNIT,CABLE MODEM,"
        "ONS,DIGITAL CONTENT MANAGER,WIFI AP,OPTICAL LINE TERMINAL,"
        "MEDIA CONVERTER,QAM,LINE/ACCESS GATEWAY,VIDEO ENCODER,"
        "SERVER,WIFI CONTROLLER,SESSION BORDER CONTROLLER,"
        "VIDEO MODULATOR,DACS,MICROWAVE,CMTS,SMART PDU,"
        "OPTICAL NETWORK TERMINAL",
    }
    granite_elements = None
    try:
        r = requests.get(
            f"{granite_base_url}{url_version}?CIRC_PATH_HUM_ID={cid}",
            params=payload,
            headers=headers,
            verify=False,
            timeout=30,
        )
        if r.status_code != 200:
            logger.exception(f"Received {r.status_code} status from granite")
            if r.status_code == 404:
                abort(404, f"No records found for {cid}")
            else:
                abort(502, "Received unexpected data from GRANITE")
        else:
            if isinstance(r.json(), list):
                granite_elements = r.json()
            else:
                key = "retString"
                value = NO_RECORDS_FOUND
                if key in r.json().keys() and value in r.json().values():
                    abort(404, f"No records found for {cid}")
                else:
                    abort(502, f"Received unexpected data from GRANITE {r.json()}")

        if not granite_elements:
            abort(404, f"No records found for {cid}")
        return granite_elements

    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to GRANITE")
        abort(504, "Timed out getting data from GRANITE")


def get_path_elements_from_filter(cid, level: str, operation: str = "mne"):
    # TODO deprecate this, replace with get_path_elements
    """
    Granite synchronous GET path elements using service path-circuit id (cid)
    returns latest PATH_REV
    """
    headers = get_hydra_headers(operation, accept_text_html_xml=True)
    params = {"CIRC_PATH_HUM_ID": cid, "LVL": level}
    try:
        r = requests.get(
            f"{granite_base_url}{GRANITE_ELEMENTS}", params=params, headers=headers, verify=False, timeout=30
        )
        if r.status_code != 200:
            logger.exception(f"Received {r.status_code} status from granite")
            if r.status_code == 404:
                return 404, f"No records found for {cid}"
            else:
                return 503, "GRANITE failed to process the request"
        else:
            if isinstance(r.json(), list):
                granite_elements = r.json()
            else:
                key = "retString"
                value = NO_RECORDS_FOUND
                if key in r.json().keys() and value in r.json().values():
                    return 404, f"No records found for {cid}"
                else:
                    return 503, "GRANITE failed to process the request"

        if not granite_elements:
            return 404, f"No records found for {cid}"
        logger.info(f"granite_elements: {granite_elements}")
        return 200, granite_elements

    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to GRANITE")
        return 504, "Timed out getting data from GRANITE"


def get_udas(path_name, revision, operation="mne"):
    headers = get_hydra_headers(operation, accept_text_html_xml=True)
    params = {"PATH_NAME": path_name, "REV_NBR": revision}
    try:
        r = requests.get(f"{granite_base_url}{GRANITE_UDA}", params=params, headers=headers, verify=False, timeout=30)
        if r.status_code != 200:
            logger.exception(f"Received {r.status_code} status from granite")
            if r.status_code == 404:
                return 404, f"No records found for {path_name} revision: {revision}"
            else:
                return 503, "GRANITE failed to process the request"
        else:
            if isinstance(r.json(), list):
                granite_elements = r.json()
            else:
                key = "retString"
                value = NO_RECORDS_FOUND
                if key in r.json().keys() and value in r.json().values():
                    return 404, f"No records found for {path_name} revision: {revision}"
                else:
                    return 503, "GRANITE failed to process the request"
        if not granite_elements:
            return 404, f"No records found for {path_name} revision: {revision}"
        return 200, granite_elements

    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to GRANITE")
        return 504, "Timed out getting data from GRANITE"


def get_fqdn_ip_vendor_from_tid(tid: str):
    response = granite_get(f"{GRANITE_EQUIPMENTS}?OBJECT_TYPE=SHELF&WILD_CARD_FLAG=1&EQUIP_NAME={tid}")
    return_info = {
        "FQDN": response[0]["FQDN"],
        "IPV4_ADDRESS": response[0]["IPV4_ADDRESS"],
        "VENDOR": response[0]["EQUIP_VENDOR"],
    }
    return return_info


def get_ip_subnets(cid):
    """Gets a circuit's IPv4 & IPv6 subnets from Granite"""
    resp = granite_get(f"/granite/ise/pathElements?CIRC_PATH_HUM_ID={cid}")
    vgw_ipv4 = get_vgw_data(resp, cid)
    if vgw_ipv4:
        return {
            "ipv4_assigned_subnets": vgw_ipv4,
            "ipv6_assigned_subnets": None,
            "ipv4_glue_subnet": None,
            "ipv6_glue_subnet": None,
        }
    data = resp[0]
    return {
        "ipv4_assigned_subnets": data.get("IPV4_ASSIGNED_SUBNETS"),
        "ipv6_assigned_subnets": data.get("IPV6_ASSIGNED_SUBNETS"),
        "ipv4_glue_subnet": data.get("IPV4_GLUE_SUBNET"),
        "ipv6_glue_subnet": data.get("IPV6_GLUE_SUBNET"),
    }


def get_vgw_data(resp, cid):
    vgw_ipv4 = None
    if isinstance(resp, dict):
        if resp.get("retString") and "No records found" in resp.get("retString"):
            abort(500, f"{cid} does not have an existing record in Granite")
    elif isinstance(resp, list) and resp:
        data = resp[0]
        if data["SERVICE_TYPE"] in ["CUS-VOICE-PRI", "CUS-VOICE-SIP"]:
            vgw_data = get_vgw_shelf_info(resp, cid)
            if vgw_data:
                vgw_ipv4 = vgw_data.get("IPV4_ADDRESS")
            if vgw_ipv4 is None:
                abort(500, f"VGW Circuit {cid} did not have any IPv4 in Granite")
    return vgw_ipv4


def get_vgw_shelf_info(data, cid: str) -> dict:
    """
    Collect data on a VGW shelf for a voice circuit

    Arg:
        cid (str): circuit ID

    Returns:
        dictionary object with VGW shelf attributes
        ex. vgw_shelf = {
                "SHELF_NAME": "WRHGOHETG1W",
                "VENDOR": "AUDIOCODES",
                "MODEL": "M500",
                "CIRC_PATH_INST_ID": "2184672"
            }
    """
    if not data:
        msg = f"Unable to acquire VGW shelf info on {cid}, missing data."
        logger.error(msg)
        abort(500, msg)
    if not isinstance(data, list):
        msg = f"Unable to acquire VGW shelf info on {cid}, no list available."
        logger.error(msg)
        abort(500, msg)
    vgw_shelf = {}
    sequence = 0
    high_sequence_element = {}
    try:
        for element in data:
            if int(element["SEQUENCE"]) > sequence:
                sequence = int(element["SEQUENCE"])
                high_sequence_element = element
        vgw_shelf["SHELF_NAME"] = high_sequence_element["ELEMENT_NAME"].split("/")[0]
        vgw_shelf["VENDOR"] = high_sequence_element["VENDOR"]
        vgw_shelf["MODEL"] = high_sequence_element["MODEL"]
        vgw_shelf["CIRC_PATH_INST_ID"] = high_sequence_element["CIRC_PATH_INST_ID"]
        vgw_shelf["IPV4_ADDRESS"] = high_sequence_element["IPV4_ADDRESS"]
    except (KeyError, IndexError, AttributeError):
        msg = f"Unable to acquire VGW shelf info on {cid}"
        logger.error(msg)
        abort(500, msg)
    return vgw_shelf


def get_devices_from_cid(cid):
    params = {"CIRC_PATH_HUM_ID": cid}
    resp = granite_get(GRANITE_ELEMENTS, params=params)
    if not isinstance(resp, list):
        return
    tid_list = []
    granite_data_non_null_tids = [x for x in resp if (x["TID"] is not None) and (x["LVL"] == "1")]
    if not granite_data_non_null_tids:
        return
    for x in granite_data_non_null_tids:
        if x["TID"].upper() not in tid_list:
            tid_list.append(x)
    return tid_list


def get_uda(circ_path_inst_id, cid=""):
    params = {"CIRC_PATH_INST_ID": circ_path_inst_id}
    if cid:
        params["PATH_NAME"] = cid
    uda_elements = granite_get(GRANITE_UDA, params=params)
    if not uda_elements:
        abort(502, "No records found for {}".format(params))
    return uda_elements


def get_inferred_slm_data(circ_path_inst_id, cid):
    source_mep_id = _get_source_mep(circ_path_inst_id)
    if source_mep_id and source_mep_id.split("::")[1] == "10":
        elan_slm_data = [
            {
                "sourceCid": cid,
                "sourceMepId": source_mep_id,
                "destinationMepId": source_mep_id,
                "destinationCid": cid,
                "sourceId": cid,
            }
        ]
        return elan_slm_data


def _get_source_mep(path_id):
    attribute_name = "SOURCE MEP ID"
    return _get_uda_value(path_id, attribute_name)


def _get_uda_value(circ_path_inst_id, attribute_name):
    uda_elements = get_uda(circ_path_inst_id)
    for uda in uda_elements:
        if uda.get("ATTR_NAME") == attribute_name:
            return uda.get("ATTR_VALUE")


def get_elan_slm_data(cid, circ_path_inst_id):
    params = {"CIRC_PATH_HUM_ID": cid}
    elan_slm_data = granite_get(ELAN_SLM, params, return_response_obj=True)
    if elan_slm_data.status_code == 200:
        elan_slm_data = elan_slm_data.json()
        if isinstance(elan_slm_data, dict) and "retString" in elan_slm_data:
            return get_inferred_slm_data(circ_path_inst_id, cid)
    else:
        return get_inferred_slm_data(circ_path_inst_id, cid)
    camel_keys = {
        "SOURCE_CID": "sourceCid",
        "SOURCE_MEP_ID": "sourceMepId",
        "DESTINATION_MEP_ID": "destinationMepId",
        "DESTINATION_CID": "destinationCid",
        "SOURCE_ID": "sourceId",
    }
    elan_slm_data = [{camel_keys[k]: v for k, v in elan_slm_data[0].items()}]
    return elan_slm_data


def create_granite_slm_data(granite_element):
    """Update Granite with ELAN SLM Data"""
    cid = granite_element["PATH_NAME"]
    evc_id = granite_element["EVC_ID"]
    path_inst_id = granite_element["CIRC_PATH_INST_ID"]
    json_content = get_path_details_by_cid(cid)
    if json_content:
        latest_revision = get_latest_revision(get_all_revisions(json_content)[0])
    else:
        abort(502, "Granite Update - Mandatory Granite Circuit Information Missing")

    payload = {
        "PATH_NAME": cid,
        "PATH_REVISION": latest_revision,
        "PATH_INST_ID": path_inst_id,
        "UDA": {"CIRCUIT SOAM PM": {"SOURCE MEP ID": f"{evc_id}::10"}},
    }
    return granite_put(GRANITE_PATHS, payload)


def get_all_revisions(path_data):
    revisions = []
    count = 0
    for _ in path_data:
        revisions.append(path_data[count]["pathRev"])
        count = count + 1
    return sorted(revisions), count


def get_latest_revision(all_revisions):
    return all_revisions[-1]


def get_paths_from_site(site_inst_id):
    paths_on_site = []
    site_path_data = granite_get(GRANITE_PATHS_FROM_SITE, params={"SITE_INST_ID": site_inst_id})
    if not site_path_data:
        msg = error_formatter(GRANITE, MISSING_DATA, "No paths found on site", site_inst_id)
        abort(502, msg, summary=get_standard_error_summary(msg))
    else:
        paths_on_site = [path["PATH_NAME"] for path in site_path_data if path.get("PATH_NAME")]
    return paths_on_site


def get_equipment_count(tid):
    clli = tid[:-3]
    params = {"CLLI": clli, "EQUIP_NAME": tid, "OBJECT_TYPE": "PORT", "USED": "IN_USE", "WILD_CARD_FLAG": "1"}
    equipments_granite_response = granite_get(GRANITE_EQUIPMENTS, params=params)
    if not equipments_granite_response:
        return 0
    else:
        unique_curr_path_name = {
            equipment["CURRENT_PATH_NAME"]
            for equipment in equipments_granite_response
            if "CURRENT_PATH_NAME" in equipment
        }
        unique_next_path_name = {
            equipment["NEXT_PATH_NAME"] for equipment in equipments_granite_response if "NEXT_PATH_NAME" in equipment
        }
        return len(unique_curr_path_name) + len(unique_next_path_name)


def get_shelf_status_data(tid, site_name=""):
    if site_name:
        url = f"{GRANITE_EQUIPMENTS}?CLLI={tid[:8]}&EQUIP_NAME={tid}&OBJECT_TYPE=SHELF&WILD_CARD_FLAG=1&SITE_NAME={site_name}"  # noqa
    else:
        url = f"{GRANITE_EQUIPMENTS}?CLLI={tid[:8]}&EQUIP_NAME={tid}&OBJECT_TYPE=SHELF&WILD_CARD_FLAG=1"
    data = granite_get(url)
    return data[0]


def get_transport_path(granite_elements: list, tid: str):
    path_name = None
    for element in granite_elements:
        if "TRANSPORT" in element["ELEMENT_CATEGORY"]:
            path_name = element["ELEMENT_NAME"]
            if tid in path_name:
                break
    if not path_name:
        return []
    transport_data = granite_get(GRANITE_PATHS, params={"CIRC_PATH_HUM_ID": path_name})
    return transport_data


def get_device_vendor_model_site_category(equipment_name: str) -> dict:
    """
    Get the vendor and model of a network device from Granite.

    :param equipment_name: The TID of the network device.
    :type equipment_name: str
    :return: The vendor of the network device.
    :rtype: str
    """
    clli = equipment_name[0:8]

    granite_url = f"/granite/ise/equipments?CLLI={clli}&OBJECT_TYPE=SHELF&EQUIP_NAME={equipment_name}&WILD_CARD_FLAG=1"
    response = granite_get(granite_url)
    try:
        data = response[0]
        vendor = data.get("EQUIP_VENDOR")
        model = data.get("EQUIP_MODEL")
        site_category = data.get("SITE_CATEGORY")
        return {"vendor": vendor, "model": model, "site_category": site_category}
    except IndexError:
        abort(
            502,
            "Error Code: M015 - The network device required onboarding but no device vendor was provided by Granite.",
        )


def delete_path(path_data, cid, status, skip_associations=False):
    """Deletes Granite Path and Associations by default.

    :param path_data: Payload from get granite paths call
    :type path_data: dict
    :param cid: Circuit ID
    :type cid: str
    :param status: Status used to delete the PATH (Canceled, Decommissioned)
    :type status: str
    :param skip_associations: Skip deletion of assiociations necessary for transport path removal, defaults to False
    :type skip_associations: bool, optional
    :param circuit_side: Circuit side to delete, defaults to "Z"
    :type circuit_side: str, optional
    """
    if not skip_associations:
        delete_associations_error = delete_path_associations(path_data, cid)
        if delete_associations_error:
            return delete_associations_error

    for path in path_data:
        if status == "Canceled":
            update_parameters = {
                "PATH_NAME": cid,
                "CIRC_PATH_INST_ID": path["pathInstanceId"],
                "PATH_REV": path["pathRev"],
                "ARCHIVE_STATUS": status,
            }
        else:
            update_parameters = {"PATH_NAME": cid, "PATH_INST_ID": path["pathInstanceId"], "ARCHIVE_STATUS": status}
        path_delete_error = delete_path_by_parameters(update_parameters)
        if path_delete_error:
            return path_delete_error


def delete_path_associations(path_data: list, cid: str):
    """Delete Granite Path Associations"""
    for path in path_data:
        path_instance_id = path.get("pathInstanceId")
        path_associations = get_path_associations(cid, path_instance_id)
        if isinstance(path_associations, str):  # error occurred while getting path associations
            return path_associations

        for association in path_associations:
            association_name = association.get("associationName")
            update_parameters = {
                "PATH_INST_ID": association.get("pathInstId"),
                "PATH_NAME": cid,
                "PATH_REV": association.get("pathRevNbr"),
                "ASSOCIATION_NAME": association_name,
                "ASSOC_INST_ID": association.get("assocInstId"),
            }
            association_del_resp = granite_put(GRANITE_ASSOCIATIONS_REMOVE, payload=update_parameters, best_effort=True)
            if "errorStatusCode" in association_del_resp:
                granite_err_resp = association_del_resp["errorStatusMessage"]
                return f"Path Association Delete Failed for CID : {cid} and Association : {association_name}.\
                     Error {granite_err_resp}"

            if "retString" not in association_del_resp or (
                "retString" in association_del_resp
                and "Path Association Removed" not in association_del_resp["retString"]
            ):
                return f"Path Association Delete Failed for CID : {cid} and Association :\
                     {association_name} -  {str(association_del_resp)}"


def get_path_associations(circ_path_num_id, path_inst_id):
    params = {"CIRC_PATH_HUM_ID": circ_path_num_id, "PATH_INST_ID": path_inst_id}
    response = granite_get(GRANITE_ASSOCIATIONS_GET, params, return_response_obj=True)

    try:
        path_associations = response.json()
    except JSONDecodeError as exp:
        return "Granite Path Association Get returned invalid format: " + exp

    if response.status_code == 200:
        if isinstance(path_associations, dict):
            if _no_associations_found(path_associations):
                return []
            return [path_associations]
        if isinstance(path_associations, list):
            return path_associations

        return f"Path Association Get Failed for CID : {circ_path_num_id} and Path Instance ID : {path_inst_id}\
            . Error {response.text}"

    if "retString" in path_associations:
        return path_associations["retString"]
    else:
        return f"Unexpected error from Granite for endpoint: {GRANITE_ASSOCIATIONS_GET}: , Parameters: {params}"


def _no_associations_found(granite_resp):
    return "assocInstId" not in granite_resp or (
        "retString" in granite_resp and "No Associations found" in granite_resp["retString"]
    )


def delete_path_by_parameters(update_parameters: dict):
    """Granite synchronous path delete using granite-defined paramters"""
    delete_code, delete_msg = granite_delete(GRANITE_PATHS, update_parameters)
    if delete_code != 200:
        return f"Granite-Delete Path Errored {delete_msg}"


def update_path_by_parameters(update_parameters: dict):
    """Granite synchronous path update using granite-defined paramters"""
    response_dictionary = granite_put(f"{GRANITE_PATHS}?validate=false", update_parameters)
    target_status = update_parameters["PATH_STATUS"]

    if "retCode" in response_dictionary:
        return f"Granite-specified Return Code error {response_dictionary['retCode']}"
    if "status" not in response_dictionary:
        return "Granite failed to provide mandatory status from circuit live update"
    else:
        status = response_dictionary["status"]
        status = status.upper()
        target_status = target_status.upper()
        if status == target_status:
            return "Successful"
        else:
            return f"Granite failed to set circuit to '{target_status}' status"


def get_path_elements_for_cid(cid):
    """Granite synchronous GET path elements using service path-circuit id (cid)"""
    endpoint = GRANITE_ELEMENTS
    params = {"CIRC_PATH_HUM_ID": cid}
    path_elements_all = granite_get(endpoint, params=params)

    if not path_elements_all:
        abort(502, f"Missing Information from Granite : Endpoint = {endpoint}")

    path_elements_notnulls = [x for x in path_elements_all if (x["TID"] is not None) and (x["LVL"] == "1")]
    if not path_elements_notnulls:
        abort(502, f"Expected values in Granite fields are null : Endpoint = {endpoint}")

    path_elements_filtered = [x for x in path_elements_notnulls if re.match(".{9}[ACTQWXYZ0-9]W", x["TID"].upper())]

    if not path_elements_filtered:
        abort(502, "TIDS ending in CW,QW,ZW,AW are not found")

    path_elements_ip_missing = [
        x for x in path_elements_filtered if (x["IPV4_ADDRESS"] is None) and (x["IPV4_ASSIGNED_SUBNETS"] is None)
    ]

    path_elements_cidr_missing_in_ipv4address = [
        x
        for x in path_elements_filtered
        if (x["IPV4_ADDRESS"] is not None)
        and (x["IPV4_ADDRESS"].upper() != "DHCP")
        and (not re.search("/", x["IPV4_ADDRESS"]))
    ]

    path_elements_cidr_missing_in_ipv4assignedsubnets = [
        x
        for x in path_elements_filtered
        if ((x["IPV4_ASSIGNED_SUBNETS"] is not None) and (not re.search("/", x["IPV4_ASSIGNED_SUBNETS"])))
    ]

    if (
        path_elements_cidr_missing_in_ipv4assignedsubnets and path_elements_cidr_missing_in_ipv4address
    ) or path_elements_ip_missing:
        abort(502, f"Granite Missing IP and or CIDR Data : Endpoint = {endpoint}")

    path_elements = _filter_path_entries(path_elements_filtered)
    if not path_elements:
        abort(502, f"No valid/expected records found in Granite : Endpoint = {endpoint}")

    path_elements_zw = [x for x in path_elements if re.match(".{9}[WXYZ]W", x["TID"].upper())]

    if not path_elements_zw and not is_ctbh(path_elements_all):
        abort(502, f"ZW TID not found : Endpoint = {endpoint}")

    return path_elements


def _filter_path_entries(granite_data):
    unique_tids = {}
    granite_data_filtered = []

    for record in granite_data:
        tid = record["TID"]
        if unique_tids.get(tid):
            if record["LVL"] > unique_tids[tid]["LVL"]:
                unique_tids[tid]["LVL"] = record["LVL"]
                unique_tids[tid]["RECORD"] = record
                unique_tids[tid]["IPV4_ASSIGNED_SUBNETS"] = record["IPV4_ASSIGNED_SUBNETS"]
            elif record["LVL"] == unique_tids[tid]["LVL"]:
                if unique_tids[tid]["IPV4_ASSIGNED_SUBNETS"] in (None, "null", "None") and record[
                    "IPV4_ASSIGNED_SUBNETS"
                ] not in (None, "null", "None"):
                    unique_tids[tid]["LVL"] = record["LVL"]
                    unique_tids[tid]["RECORD"] = record
                    unique_tids[tid]["IPV4_ASSIGNED_SUBNETS"] = record["IPV4_ASSIGNED_SUBNETS"]
        else:
            unique_tids[tid] = {}
            unique_tids[tid]["LVL"] = record["LVL"]
            unique_tids[tid]["RECORD"] = record
            unique_tids[tid]["IPV4_ASSIGNED_SUBNETS"] = record["IPV4_ASSIGNED_SUBNETS"]

    for tid in unique_tids:
        granite_data_filtered.append(unique_tids[tid]["RECORD"])

    return granite_data_filtered


def delete_shelf(shelf_equip_id: str):
    delete_params = {"SHELF_INST_ID": shelf_equip_id, "ARCHIVE_STATUS": "Decommissioned"}
    resp = delete_with_query(GRANITE_SHELVES, delete_params)

    logger.info(f"Granite Shelf Delete Response: {resp}")
    if resp["retString"] != "Shelf Deleted":
        return f"Granite Delete Shelf Errored {resp['retString']}"


def delete_site(site_inst_id: str):
    delete_params = {"SITE_INST_ID": site_inst_id, "ARCHIVE_STATUS": "Decommissioned"}
    resp = delete_with_query(GRANITE_SITES, delete_params)

    logger.info(f"Granite Site Delete Response: {resp}")
    if resp["retString"] != "Site Deleted":
        return f"Granite Delete Site Errored {resp['retString']}"


def update_granite_shelf(tid: str, ip: str, cid: str = None) -> bool:
    """Update IP for TID in Granite

    :param tid: TID of the device to Update
    :type tid: str
    :param ip: IP to update TID to
    :type ip: str
    :param cid: CID of circuit(optional)
    :type cid: str, optional
    :return: True if successful, False
    :rtype: bool
    """
    params = None
    if cid:
        params = get_tid_params_by_cid(cid, tid, ip)
    else:
        params = get_tid_params_by_tid(tid, ip)
    if not params:
        return False
    response = granite_put(GRANITE_SHELVES, params, calling_function="update_granite_shelf")
    if response is not None and "retString" in response:
        if "SHELF UPDATED" in str(response["retString"]).upper():
            return True
    return False


def get_tid_params_by_cid(cid, tid, ip):
    records = get_circuit_devices(cid)
    for record in records:
        if record["TID"] == tid:
            return {
                "SHELF_INST_ID": record["ELEMENT_REFERENCE"],
                "SHELF_NAME": record["ELEMENT_NAME"],
                "SITE_NAME": record["A_SITE_NAME"],
                "SHELF_STATUS": record["ELEMENT_STATUS"],
                "SHELF_FQDN": record["FQDN"],
                "UDA": {"Device Config-Equipment": {"IPv4 ADDRESS": f"{ip}"}},
            }


def get_tid_params_by_tid(tid, ip):
    clli = tid[:8]
    records = granite_get(f"/granite/ise/equipments?CLLI={clli}&OBJECT_TYPE=SHELF&EQUIP_NAME={tid}&WILD_CARD_FLAG=1")
    for record in records:
        if record["TARGET_ID"] == tid:
            return {
                "SHELF_INST_ID": record["EQUIP_INST_ID"],
                "SHELF_NAME": record["EQUIP_NAME"],
                "SITE_NAME": record["SITE_NAME"],
                "SHELF_STATUS": record["EQUIP_STATUS"],
                "SHELF_FQDN": record["FQDN"],
                "UDA": {"Device Config-Equipment": {"IPv4 ADDRESS": f"{ip}"}},
            }


def clean_headers(headers):
    headers["X-Api-Key"] = "<API Key>"
    return headers


def get_transport_media_type_by_equipment_id(equipment_id):
    params = {"EQUIP_INST_ID": equipment_id}
    shelf_info = granite_get(SHELF_UDAS, params)
    transport_media_type = None
    for shelf in shelf_info:
        if shelf.get("ATTR_NAME") == "TRANSPORT MEDIA TYPE":
            transport_media_type = shelf.get("ATTR_VALUE")
            break
    return transport_media_type


def get_path_relationships(circuit_id, path_inst_id):
    """Returns a list of any and all path relationships for a given circuit and its path instance ID
        Path instance ID can be found by calling get_path_elements_for_cid()
    :param circuit_id: CID
    :type circuit_id: str
    :param path_inst_id: CIRC_PATH_INST_ID for a circuit
    :type path_inst_id: str (ex. "2633735")
    :return: returns a list of any path relationships the circuit may have and who/how they're connected
    :rtype: list of dicts
    """
    params = {"CIRC_PATH_HUM_ID": circuit_id, "PATH_INST_ID": path_inst_id}
    response = granite_get(GRANITE_PATH_RELATIONSHIPS, params)
    logger.info(f"Granite Path Relationships for {circuit_id}: {response}")
    return response


def delete_path_relationships(circuit_id, path_inst_id, relationship_type="Backup"):
    """Removes any and all path relationships for a given circuit and its path instance id
    :param circuit_id: CID
    :type circuit_id: str
    :param path_inst_id: CIRC_PATH_INST_ID for a circuit
    :type path_inst_id: str (ex. "2633735")
    :param relationship_type: what type of connection two paths may have, defaults to "Backup" for WIA
    :type relationship_type: str, optional
    """
    relationships = get_path_relationships(circuit_id, path_inst_id)  # Retrieves the necessary RELATED_PATH_INST_ID
    failed_to_delete = []
    for relationship in relationships:
        if relationship.get("RELATIONSHIP") != relationship_type:
            continue
        params = {
            "PATH_INST_ID": path_inst_id,
            "RELATED_PATH_INST_ID": relationship.get("RELATED_PATH_INST_ID"),
            "RELATIONSHIP": relationship_type,
            "REMOVE_RELATIONSHIP": "SINGLE",
        }
        response = granite_put(GRANITE_PATH_RELATIONSHIPS, params)
        logger.info(f"Path Relationship Deletion Response for {circuit_id}: {response}")
        if response["retString"] != "Path Relationship Removed":
            failed_to_delete.append({circuit_id: relationship.get("RELATED_PATH_INST_ID")})

    if failed_to_delete:
        return f"Granite Delete Path Relationships Failure(s): {failed_to_delete}"
