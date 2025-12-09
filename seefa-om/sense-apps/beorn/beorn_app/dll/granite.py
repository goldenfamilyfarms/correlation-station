import logging
import requests
from time import sleep
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

import beorn_app
from common_sense.common.errors import abort
from beorn_app.common.endpoints import GRANITE_ELEMENTS, GRANITE_PATHS, GRANITE_UDA
from beorn_app.dll.hydra import get_headers

LOGGER = logging.getLogger(__name__)


def granite_get(endpoint, params=None, timeout=60, retry=0, best_effort=False):
    headers = get_headers()
    url = f"{beorn_app.url_config.GRANITE_BASE_URL}{endpoint}"
    err_msg = ""
    for _ in range(retry + 1):
        try:
            resp = requests.get(url=url, headers=headers, params=params, timeout=timeout, verify=False)
            if resp.status_code == 200:
                granite_resp = resp.json()
                # Check for CID not found
                if "retString" in granite_resp and "No records" in granite_resp["retString"]:
                    if best_effort:
                        return []
                    else:
                        abort(
                            502, f"Granite Call - No records found for URL: {url} params: {params} RESPONSE: {resp.text}"
                        )
                return granite_resp
            else:
                err_msg = f"Granite Call - Not success status code '{resp.status_code}': {url}"
        except (ConnectionError, requests.ConnectionError, requests.ConnectTimeout):
            err_msg = f"Granite Call - Failed connecting to Granite for URL: {url}"
        except requests.ReadTimeout:
            err_msg = f"Granite Call - Connected to Granite and timed out waiting for data for URL: {url}"
        LOGGER.info(f"Granite get - {err_msg}")
        sleep(3)
    # Failed to get data from granite. Aborting
    abort(504, err_msg)


def granite_put(endpoint, payload):
    """Send a PUT call to the Granite API and return
    the JSON-formatted response"""
    headers = get_headers()
    try:
        r = requests.put(
            f"{beorn_app.url_config.GRANITE_BASE_URL}{endpoint}", headers=headers, json=payload, verify=False, timeout=60
        )
        if r.status_code != 200:
            abort(
                502,
                f"Granite Update - Unexpected status code {r.status_code} "
                f"from Granite for url: {endpoint} and payload {payload} RESPONSE: {r.text}",
            )
        return r
    except (ConnectionError, requests.ConnectionError, requests.Timeout):
        abort(504, f"Timed out putting data to Granite for url: {endpoint} and payload {payload}")


def get_granite_devices_from_cid(cid):
    params = {"CIRC_PATH_HUM_ID": cid}
    resp = granite_get(GRANITE_ELEMENTS, params)
    if not isinstance(resp, list):
        return None
    tid_list = []

    granite_data_non_null_tids = [x for x in resp if (x["TID"] is not None) and (x["LVL"] == "1")]
    if not granite_data_non_null_tids:
        return None

    for x in granite_data_non_null_tids:
        if x["TID"].upper() not in tid_list:
            tid_list.append(x)
    return tid_list


def call_granite_for_uda(circ_path_inst_id):
    params = {"CIRC_PATH_INST_ID": circ_path_inst_id}
    uda_elements = granite_get(GRANITE_UDA, params)
    if not uda_elements:
        abort(502, "No records found for {}".format(params))
    return uda_elements


def _path_details_by_cid(cid):
    """Granite synchronous GET path info using service path-circuit id (cid)"""
    params = {"CIRC_PATH_HUM_ID": cid}
    return granite_get(GRANITE_PATHS, params)


def _update_path_status(cid, status):
    """Update Granite CID path status"""
    json_content = _path_details_by_cid(cid)
    if json_content:
        latest_revision = _find_latest_revision(json_content)
    else:
        abort(502, "Granite Update - Mandatory Granite Circuit Information Missing")

    json_content_latest_revision = [x for x in json_content if x["pathRev"] == latest_revision]
    for i in json_content_latest_revision:
        if i["status"] == "Live":
            abort(501, "Granite Update - Circuit status is already set to Live")

    payload = {"PATH_NAME": cid, "PATH_REVISION": latest_revision, "PATH_STATUS": status}
    return granite_put(GRANITE_PATHS, payload)


def _find_latest_revision(json_content):
    revisions = []
    count = 0
    for _ in json_content:
        revisions.append(json_content[count]["pathRev"])
        count = count + 1
    sorted_revs = sorted(revisions)
    latest_revision = sorted_revs[-1]
    return latest_revision


def create_granite_slm_data(granite_element):
    """Update Granite with ELAN SLM Data"""
    cid = granite_element["PATH_NAME"]
    evc_id = granite_element["EVC_ID"]
    path_inst_id = granite_element["CIRC_PATH_INST_ID"]
    json_content = _path_details_by_cid(cid)
    if json_content:
        latest_revision = _find_latest_revision(json_content)
    else:
        abort(502, "Granite Update - Mandatory Granite Circuit Information Missing")

    payload = {
        "PATH_NAME": cid,
        "PATH_REVISION": latest_revision,
        "PATH_INST_ID": path_inst_id,
        "UDA": {"CIRCUIT SOAM PM": {"SOURCE MEP ID": f"{evc_id}::10"}},
    }
    return granite_put(GRANITE_PATHS, payload)


def get_mne_network_id(circuit_id, timeout=60):
    headers = get_headers()
    url_paths = f"{beorn_app.url_config.GRANITE_BASE_URL}{GRANITE_PATHS}"
    url_udas = f"{beorn_app.url_config.GRANITE_BASE_URL}{GRANITE_UDA}"
    params = {"CIRC_PATH_HUM_ID": circuit_id}

    try:
        response = requests.get(url_paths, headers=headers, params=params, timeout=timeout, verify=False)
        path_inst_id = response.json()[0]["pathInstanceId"]
        params = {"CIRC_PATH_INST_ID": path_inst_id}
    except (ConnectionError, ConnectTimeout, ReadTimeout):
        abort(504, "Timeout")
    except (IndexError, KeyError):
        abort(502, "Circuit ID not found")

    try:
        response = requests.get(url_udas, headers=headers, params=params, timeout=timeout, verify=False)
        udas = response.json()
    except (ConnectionError, ConnectTimeout, ReadTimeout):
        abort(504, "Timeout")

    for i in udas:
        if i["ATTR_NAME"] != "MERAKI NETWORK ID":
            continue
        network_id = i["ATTR_VALUE"]
        break
    else:
        network_id = None

    return {"network_id": network_id}


def update_mne_network_id(circuit_id, network_id, timeout=60):
    headers = get_headers()
    url = f"{beorn_app.url_config.GRANITE_BASE_URL}{GRANITE_PATHS}"
    params = {"CIRC_PATH_HUM_ID": circuit_id}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout, verify=False)
        path_inst_id = response.json()[0]["pathInstanceId"]
    except (ConnectionError, ConnectTimeout, ReadTimeout):
        abort(504, "Timeout")
    except (IndexError, KeyError):
        abort(502, "Circuit ID not found")

    payload = {"PATH_INST_ID": path_inst_id, "UDA": {"MERAKI SERVICES": {"MERAKI NETWORK ID": network_id}}}
    try:
        response = requests.put(url, headers=headers, json=payload, verify=False, timeout=timeout)
    except (ConnectionError, ConnectTimeout, ReadTimeout):
        abort(504, "Timeout")

    if response.ok:
        return response.json()
    else:
        abort(502, f"Granite Update - Unexpected status code {response.status_code} from Granite")
