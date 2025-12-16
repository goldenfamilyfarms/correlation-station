import logging
from time import sleep
from urllib.parse import urlencode

import requests
import urllib3

import beorn_app
from common_sense.common.errors import abort
from beorn_app.common.endpoints import DENODO_UDA, GRANITE_ELEMENTS, GRANITE_JSON_PATH, DENODO_CIRCUIT_DEVICES
from beorn_app.dll.hydra import get_headers
from beorn_app.common.otel import get_tracer, add_span_event, set_span_error
from beorn_app.common.otel.mdso_patterns import ErrorCategorizer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

codes = {
    400: "Bad Request",
    401: "Not authorized",
    404: "Resource not found",
    403: "Access not authorized",
    500: "Server error",
}

hydra_base_url = beorn_app.url_config.HYDRA_BASE_URL


def path_update_by_parameters(headers_info, update_parameters):
    """MDSO asynchronous update using the resource API with specified json-formatted parameters"""
    try:
        response = requests.post(
            f"{hydra_base_url}{GRANITE_JSON_PATH}?validate=false",
            headers=headers_info,
            json=update_parameters,
            verify=False,
            timeout=30,
        )
        if response.json()["retCode"] != 0:
            return 400, response.json()

        return response.status_code, response.json()

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.error("Timeout waiting on GRANITE to process the request")
        abort(504, "Timeout waiting on GRANITE to process the request")


def call_denodo_for_circuit_devices(cid):
    with tracer.start_as_current_span("denodo.circuit_devices.query") as span:
        span.set_attribute("denodo.operation", "get_circuit_devices")
        span.set_attribute("denodo.circuit_id", cid)
        span.set_attribute("denodo.endpoint", DENODO_CIRCUIT_DEVICES)
        
        headers = get_headers(override=True)
        retrycount = 0
        for attempt in range(2):
            if retrycount > 0:
                sleep(3)
                span.set_attribute("denodo.retry_count", retrycount)
                add_span_event("denodo.retry", circuit_id=cid, attempt=retrycount)
            
            try:
                add_span_event("denodo.query.start", circuit_id=cid, endpoint=DENODO_CIRCUIT_DEVICES)
                r = requests.get(
                    url=f"{beorn_app.url_config.HYDRA_BASE_URL}{DENODO_CIRCUIT_DEVICES}",
                    headers=headers,
                    params={"cid": cid},
                    verify=False,
                    timeout=60,
                )
                span.set_attribute("http.status_code", r.status_code)
                
                if r.status_code != 200:
                    if retrycount > 0:
                        logger.exception(f"Received {r.status_code} status from granite")
                        error_context = error_categorizer.extract_error_context(f"HTTP {r.status_code}")
                        span.set_attribute("error.category", error_context.get("category", "HTTP_ERROR"))
                        span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                        if r.status_code == 404:
                            abort(500, "Granite Call - No records in Granite found for {}".format(cid))
                        else:
                            abort(504, "Granite Call - GRANITE failed to process the request")
                    else:
                        retrycount = retrycount + 1
                else:
                    denodo_elements = r.json()["elements"]
                    span.set_attribute("denodo.elements_count", len(denodo_elements) if denodo_elements else 0)

                    if not denodo_elements:
                        if retrycount > 0:
                            abort(404, "Granite Call - No records in Granite found for {}".format(cid))
                        else:
                            retrycount = retrycount + 1
                    else:
                        add_span_event("denodo.query.complete", circuit_id=cid, elements_count=len(denodo_elements))
                        return denodo_elements

            except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError, requests.ReadTimeout) as e:
                if retrycount > 0:
                    logger.error("Timeout waiting on GRANITE to process the request")
                    set_span_error(e)
                    error_context = error_categorizer.extract_error_context(str(e))
                    span.set_attribute("error.category", error_context.get("category", "TIMEOUT_ERROR"))
                    span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                    abort(504, "Granite Call - Timeout waiting on GRANITE to process the request")
                else:
                    retrycount = retrycount + 1


def call_denodo_for_uda(**kwargs):
    with tracer.start_as_current_span("denodo.uda.query") as span:
        span.set_attribute("denodo.operation", "get_uda")
        span.set_attribute("denodo.endpoint", DENODO_UDA)
        
        params = ""
        if kwargs:
            params = urlencode(kwargs["params"])
            span.set_attribute("denodo.params", params[:200])  # Truncate long params
        
        denodo_uda_url = (
            f"{hydra_base_url}{DENODO_UDA}?{params}&$format=json&api_key={beorn_app.auth_config.BEORN_HYDRA_KEY}"
        )
        retrycount = 0
        for attempt in range(2):
            if retrycount > 0:
                sleep(3)
                span.set_attribute("denodo.retry_count", retrycount)
                add_span_event("denodo.retry", endpoint=DENODO_UDA, attempt=retrycount)
            
            try:
                add_span_event("denodo.uda.query.start", endpoint=DENODO_UDA)
                r = requests.get(denodo_uda_url, verify=False, timeout=60)
                span.set_attribute("http.status_code", r.status_code)
                
                if r.status_code != 200:
                    if retrycount > 0:
                        logger.exception(f"Received {r.status_code} status from granite")
                        error_context = error_categorizer.extract_error_context(f"HTTP {r.status_code}")
                        span.set_attribute("error.category", error_context.get("category", "HTTP_ERROR"))
                        span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                        if r.status_code == 404:
                            abort(404, "No records found for {}".format(params))
                        else:
                            abort(504, "GRANITE failed to process the request")
                    else:
                        retrycount = retrycount + 1
                else:
                    uda_elements = r.json()["elements"]
                    span.set_attribute("denodo.elements_count", len(uda_elements) if uda_elements else 0)
                    
                    if not uda_elements:
                        if retrycount > 0:
                            abort(404, "No records found for {}".format(params))
                        else:
                            retrycount = retrycount + 1
                    else:
                        add_span_event("denodo.uda.query.complete", elements_count=len(uda_elements))
                        return uda_elements

            except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError, requests.ReadTimeout) as e:
                if retrycount > 0:
                    logger.error("Timeout waiting on GRANITE to process")
                    set_span_error(e)
                    error_context = error_categorizer.extract_error_context(str(e))
                    span.set_attribute("error.category", error_context.get("category", "TIMEOUT_ERROR"))
                    span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                    abort(504, "Timeout waiting on GRANITE to process")
                else:
                    retrycount = retrycount + 1


def get_granite_devices_from_cid(cid):
    with tracer.start_as_current_span("granite.devices.query") as span:
        span.set_attribute("granite.operation", "get_devices_from_cid")
        span.set_attribute("granite.circuit_id", cid or "unknown")
        span.set_attribute("granite.endpoint", GRANITE_ELEMENTS)
        
        headers = get_headers()
        if not cid:
            span.set_attribute("granite.empty_cid", True)
            return None

        params = {"CIRC_PATH_HUM_ID": cid}

        try:
            add_span_event("granite.query.start", circuit_id=cid, endpoint=GRANITE_ELEMENTS)
            r = requests.get(
                f"{beorn_app.url_config.GRANITE_BASE_URL}{GRANITE_ELEMENTS}",
                params=params,
                headers=headers,
                verify=False,
                timeout=30,
            )
            span.set_attribute("http.status_code", r.status_code)

            if r.status_code != 200:
                span.set_attribute("granite.found", False)
                return None
            else:
                if isinstance(r.json(), list):
                    granite_elements = r.json()
                    span.set_attribute("granite.elements_count", len(granite_elements))
                else:
                    span.set_attribute("granite.found", False)
                    return None

            if not granite_elements:
                span.set_attribute("granite.found", False)
                return None

        except (ConnectionError, requests.Timeout, requests.ConnectionError) as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "CONNECTION_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            return None

        tid_list = []

        granite_data_non_null_tids = [x for x in granite_elements if (x["TID"] is not None) and (x["LVL"] == "1")]
        span.set_attribute("granite.valid_tids_count", len(granite_data_non_null_tids))
        if not granite_data_non_null_tids:
            return None

        for x in granite_data_non_null_tids:
            if x["TID"].upper()[-2:] in ["ZW", "WW", "XW", "YW"]:
                if x["TID"].upper() not in tid_list:
                    tid_list.append(x["TID"].upper())
        
        span.set_attribute("granite.tid_list_count", len(tid_list))
        add_span_event("granite.query.complete", circuit_id=cid, tids_count=len(tid_list))
        return tid_list
