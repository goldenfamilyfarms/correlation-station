import re
import requests
import logging

from arda_app.common import url_config
from arda_app.common.endpoints import CARS_ISP_GROUPS
from arda_app.dll.utils import get_hydra_headers
from common_sense.common.errors import abort


logger = logging.getLogger(__name__)

REMEDY_BASE_URL = url_config.REMEDY_BASE_URL
REMEDY_SERVER = url_config.REMEDY_SERVER


def remedy_post(endpoint, headers, payload, timeout=120):
    headers["Content-Type"] = "text/xml;charset=UTF-8"
    headers["Connection"] = "Keep-Alive"
    headers["Host"] = REMEDY_BASE_URL.split("https://")[1]

    server_param = f"server={REMEDY_SERVER}"
    url = f"{REMEDY_BASE_URL}/arsys/services/ARService?{server_param}&webService={endpoint}"

    try:
        return requests.post(url, data=payload, headers=headers, timeout=timeout, verify=False)
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(500, f"Timed out posting data to url: {url}")


def create_workorder(payload):
    headers = {"SOAPAction": "urn:SRM_RequestInterface_Create_WS/Request_Submit_Service"}
    endpoint = "CreateWorkOrder"
    return remedy_post(endpoint, headers, payload)


def get_workorder_info(payload):
    headers = {"SOAPAction": "CHR_WOI_WorkOrder_WS/WorkOrder_GetInfo"}
    endpoint = "CHR_WOI_WorkOrder_WS"
    return remedy_post(endpoint, headers, payload)


def create_crq(payload):
    headers = {"SOAPAction": "CHG_ChangeInterface_Create_WS_v2_2"}
    endpoint = "CHG_ChangeInterface_Create_WS_v2_2"
    return remedy_post(endpoint, headers, payload)


def update_crq(payload):
    headers = {"SOAPAction": "CHG_ChangeInterface_WS_v3"}
    endpoint = "CHG_ChangeInterface_WS_v3"
    return remedy_post(endpoint, headers, payload)


def create_crq_task(payload):
    headers = {"SOAPAction": "CHR_TMS_TaskInterface_Create_IN"}
    endpoint = "CHR_TMS_TaskInterface_Create_IN"
    resp = remedy_post(endpoint, headers, payload)
    # Parse XML response and return task ID
    task_id = re.findall(r"<ns0:Task_ID>(\w+)</ns0:Task_ID>", str(resp.content))
    if isinstance(task_id, list):
        return task_id[0]
    else:
        if "faultstring" in str(resp.content):
            fault = re.findall(r"<faultstring>(.*)</faultstring>", str(resp.content))
            if len(fault) > 0:
                abort(500, f"ARDA - Unexpected Remedy error. Task was not created because: {fault[0]}")
        abort(500, "ARDA - Unexpected Remedy error. Task was not created.")


def create_inc(payload):
    headers = {"SOAPAction": "WS_Charter_Incident_Interface_Stage"}
    endpoint = "WS_Charter_Incident_Interface_Stage"
    return remedy_post(endpoint, headers, payload)


def get_isp_group_cars(clli):
    """Pulls ISP info directly from the CARS Remedy db.
    Hydra -> Helios -> CARS ARADMIN.T3944 table\n
    :param clli: "WTVLOHAP"
    :return: {
            "isp_group": "ISP-GLR-NOH-West",
            "x_matters_group": "ISP-Ohio-Waterville",
            "site_type": "Primary Hub",
            "common_name": "Waterville",
            "common_id": "Waterville : 49",
            "clli": "WTVLOHAP",
            "site_group": "Northern Ohio",
            "address": "1295 Waterville Monclova Rd.",
            "city": "Waterville",
            "state": "OH",
            "zip": "43566",
            "region": "Great Lakes"
        }
    """
    headers = get_hydra_headers()
    endpoint = f"{CARS_ISP_GROUPS}?$filter=clli='{clli}'"
    resp = requests.get(f"{url_config.HYDRA_BASE_URL}{endpoint}", headers=headers, verify=False, timeout=300)
    if resp.status_code == 200:
        resp = resp.json()
        if resp.get("elements") and len(resp.get("elements")) > 0:
            logger.info(resp["elements"][0])
            return resp["elements"][0]
        else:
            abort(500, f"CARS Remedy empty response for CLLI: {clli}")
    else:
        abort(500, f"Unexpected response from Helios for CARS Remedy ISP group lookup with endpoint: {endpoint}")
