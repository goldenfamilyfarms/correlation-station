import logging
import requests

from fastapi import Query, status, Request

from arda_app.common import url_config, auth_config
from common_sense.common.errors import abort
from arda_app.dll.granite import post_granite
from arda_app.api._routers import v1_tools_router

logger = logging.getLogger(__name__)


@v1_tools_router.get("/noc_analysis", summary="Granite Circuit Lookup")
def noc_analysis(
    request: Request,
    cid: str = Query(None, description="The Circuit ID of the service", examples=["32.L1XX.990440..CHTR"]),
    tid: str = Query(None, description="The Target ID of the device", examples=["AMDAOH031ZW"]),
):
    """
    Returns service details for a given Circuit ID or device TID
    """

    if len(request.query_params) > 1:
        abort(500, "more than one parameter provided, please use either 'tid' or 'cid'")

    if cid and tid:
        abort(500, "more than one parameter provided, please use either 'tid' or 'cid'")

    if cid is not None:
        if cid == "":
            abort(500, "nothing specified for parameter 'cid'")
        else:
            return service_check("cid", cid)
    elif tid is not None:
        if tid == "":
            abort(500, "nothing specified for parameter 'tid'")
        else:
            return service_check("tid", tid)
    else:
        abort(500, "invalid parameter provided - please use either 'tid' or 'cid'")


@v1_tools_router.post("/noc_analysis", summary="Granite Circuit Create", status_code=status.HTTP_204_NO_CONTENT)
def noc_analysis_depr(
    cid: str = Query(..., description="The Circuit ID of the service", examples=["32.L1XX.990440..CHTR"]),
    bandwidth: str = Query(..., examples=["1 Gbps"]),
):
    """Creates a new circuit in Granite"""
    # I don't think this is used... or at least it shouldn't be

    if not cid:
        abort(500, "Bad request - missing parameter cid")
    if not bandwidth:
        abort(500, "Bad request - missing parameter bandwidth")

    update_parameters = {
        "procType": "new",
        "GRANITE_USER": "ws-mulesoft",
        "PATH_NAME": cid,
        "PATH_TOPOLOGY": "Point to Point",
        "PATH_BANDWIDTH": bandwidth,
        "PATH_TYPE": "ETHERNET",
        "PATH_STATUS": "Designed",
    }

    # check for errors that it doesn't like status, or bw, or locked by user

    url = "/gateKeeper/resources/json/GkJsonService/processPath?validate=false"

    post_granite(url, update_parameters)
    return ""


def service_check(call_type: str, value: str):
    """
    call_type = device_tid or cid
    value = the CID or TID to be searched
    Pulls device info from granite.
    """
    api_key = auth_config.ARDA_NOC_HYDRA_KEY

    headers = {"APPLICATION": "SENSE-ARDA"}
    hydra_base_url = url_config.HYDRA_BASE_URL

    if call_type == "tid":
        api_path = "/server/nsm_deo/dv_cans2_tid_impact/views/dv_cans2_tid_impact"
        url = f"{hydra_base_url}{api_path}?eq_tid={value.upper()}&api_key={api_key}"

        r = requests.get(url=url, headers=headers, verify=False, timeout=300)
        data = r.json()

        if "elements" not in data:
            abort(500, "issue with upstream data source.")
        elif len(data["elements"]) == 0:
            abort(500, "no records found")
        else:
            return data["elements"][0]["port_data"]

    elif call_type == "cid":
        api_path = "/server/app_dev/bv_cans2_cid_lookup/views/bv_cans2_cid_lookup"
        url = f"{hydra_base_url}{api_path}?circuit_id={value.upper()}&api_key={api_key}"

        r = requests.get(url, verify=False, timeout=300)
        data = r.json()

        if data.get("elements") is None:
            abort(500, "issue with upstream data source.")
        elif len(data["elements"]) == 0:
            abort(500, "no records found")
        return data["elements"]

    else:
        abort(500, "issue with upstream data source.")
