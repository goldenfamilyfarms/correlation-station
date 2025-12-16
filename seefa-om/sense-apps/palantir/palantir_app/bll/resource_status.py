import logging
import re
import time

from common_sense.common.errors import (
    ERROR_CATEGORIES,
    SUMMARY_DETAILS_DELIMITER,
    get_standard_error_details,
    get_standard_error_summary,
    clean_details,
)
from palantir_app.common.constants import PROCESSING_STATUSES
from palantir_app.dll.mdso import mdso_get
from palantir_app.common.otel import (
    get_tracer,
    set_mdso_correlation,
    add_span_event,
    set_span_error,
)
from palantir_app.common.otel.mdso_patterns import ErrorCategorizer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


MDSO_REASON_SUMMARY_REGEX = r"(\w*\s\|.*?\-)(.*?:)"
MDSO_REASON_DETAILS_REGEX = r"\w*\s\|.*?\-(.*?:)(.*?)(?=\.)"


def get_resource_status(resource_id, map_responses=True, poll=False, poll_counter=0, poll_sleep=0, production=False):
    """
    Gets the status of a resource from MDSO
    map_responses gets human readable responses in 'message'
    poll will have this method poll MDSO
    poll counter is the number of times to loop
    poll sleep is the time to sleep between each loop in seconds

    returns
    dict {id, status, message}
    """
    with tracer.start_as_current_span("palantir.resource_status.get_resource_status") as span:
        set_mdso_correlation(resource_id=resource_id)
        span.set_attribute("resource_status.operation", "get_status")
        span.set_attribute("resource_status.polling", poll)
        span.set_attribute("resource_status.poll_counter", poll_counter)
        span.set_attribute("resource_status.poll_sleep", poll_sleep)
        span.set_attribute("resource_status.map_responses", map_responses)
        
        logger.info(f"Retrieving resource status via mdso_get for ID: {resource_id}")
        response = {"id": resource_id, "status": "", "summary": "", "message": "", "data": ""}
        
        try:
            add_span_event("resource_status.mdso.query.start", resource_id=resource_id)
            data = get_resource(resource_id, production)
            if not data:
                span.set_attribute("resource_status.found", False)
                return response

            response["data"] = data
            span.set_attribute("resource_status.found", True)
            
            # Extract circuit_id from label if available
            if "label" in data:
                set_mdso_correlation(circuit_id=data["label"])
                span.set_attribute("mdso.circuit_id", data["label"])
            
            if "orchState" not in data:
                return response

            orch_state = data["orchState"]
            span.set_attribute("mdso.orch_state", orch_state)
            
            if orch_state in PROCESSING_STATUSES:
                response["status"] = "Processing"
                span.set_attribute("resource_status.status", "Processing")
                logger.info(f"Processing resource status for {data.get('label', resource_id)}\n")
                if poll:
                    add_span_event("resource_status.polling.start", resource_id=resource_id, counter=poll_counter)
                    result = _poll_response(resource_id, poll_counter, poll_sleep, production, response, map_responses)
                    add_span_event("resource_status.polling.complete", resource_id=resource_id)
                    return result

            elif orch_state == "active":
                result = _active_response(data, response)
                span.set_attribute("resource_status.status", result.get("status", "Completed"))
                add_span_event("resource_status.active", resource_id=resource_id)
                return result
            else:
                result = _failed_response(data, response, map_responses)
                span.set_attribute("resource_status.status", "Failed")
                error_context = error_categorizer.extract_error_context(data.get("reason", ""))
                span.set_attribute("error.category", error_context.get("category", "MDSO_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                add_span_event("resource_status.failed", resource_id=resource_id, reason=data.get("reason", "unknown"))
                return result

            return response
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise


def get_resource(resource_id, production):
    url = f"/bpocore/market/api/v1/resources/{resource_id}"
    return mdso_get(url, calling_function="get_resource_status (inside activation loop)", production=production)


def _poll_response(resource_id, poll_counter, poll_sleep, production, response, map_responses):
    for i in range(int(poll_counter)):
        time.sleep(int(poll_sleep))

        data = get_resource(resource_id, production)

        if data["orchState"] in PROCESSING_STATUSES:
            logger.info(f"Continuing orchState check for {data['label']}  | poll attempt: {i}")
            continue
        elif data["orchState"] == "active":
            response = _active_response(data, response)
        else:
            response = _failed_response(data, response, map_responses)
        return response
    return response


def _active_response(data, response):
    logger.info(f"The orchState for {data['label']} returned an ACTIVE response")
    response["status"] = "Completed"
    if data["properties"].get("report"):
        response["message"] = data["properties"]["report"]
        response["status"] = "Failed"
    return response


def _failed_response(data, response, map_responses):
    response["status"] = "Failed"
    logger.info(f"The orchState for {data['label']} returned a FAILED response  | Data: {data}")
    if map_responses and "reason" in data:
        mdso_reason = str(data["reason"]).upper()
        response = _handle_failure_reason(response, mdso_reason)
        if response["message"] is not None:
            return response
        else:
            response["message"] = f"Unrecognized MDSO reason: {mdso_reason}"
    return response


def _handle_failure_reason(response: object, mdso_reason: str):
    mdso_reason = _clean_data(mdso_reason)
    failure_point = _get_failure_point(response["data"], mdso_reason)
    error, specialized = _get_error(response["data"], mdso_reason)
    error, summary = _split_summary_and_error(error, specialized)
    response["message"] = "{} - {}".format(failure_point, error)
    response["summary"] = summary
    if "data" in response:
        del response["data"]
    return response


def _clean_data(mdso_reason: str):
    mdso_reason = mdso_reason.replace("\\N", "")
    mdso_reason = mdso_reason.replace(r"\N", "")
    mdso_reason = mdso_reason.replace("\\n", "")
    mdso_reason = mdso_reason.replace("\n", "")
    mdso_reason = mdso_reason.replace("\\", "")
    mdso_reason = mdso_reason.replace("'", "")
    mdso_reason = mdso_reason.replace('"', "")
    mdso_reason = mdso_reason.replace("\t", "")
    mdso_reason = mdso_reason.replace("   ", "")
    return mdso_reason


def _get_failure_point(resource_data, mdso_reason: str) -> str:
    files = _get_files_with_errors(mdso_reason)
    # the last script in the tuple is the mdso script that caused failure
    # the 2nd to last str in the script name split on . is the relevant file name
    try:
        return files[-1].split(".")[-2] if files else resource_data["properties"].get("state", "UNKNOWN")
    except IndexError:
        return files[-1] if files else resource_data["properties"].get("state", "UNKNOWN")


def _get_files_with_errors(mdso_reason: str) -> tuple:
    # find all the scripts called out in the reason for failure
    failed_files = tuple(re.findall(r"SCRIPTS.\S*", mdso_reason))
    failed_files = tuple([x[8:-1].replace(" ", "") for x in failed_files if len(x) > 3])
    if not failed_files:
        failed_files = tuple(re.findall(r"\S*\.ACTIVATE", mdso_reason))
    return failed_files


def _get_error(mdso_resource, mdso_reason):
    error = None
    specialized = False
    if "cpe" in mdso_resource["resourceTypeId"]:
        error = mdso_resource["properties"].get("cpe_activation_error")
        specialized = True
    elif "NetworkService" in mdso_resource["resourceTypeId"]:
        error = mdso_resource["properties"].get("network_service_error")
        specialized = True
    elif _error_isolation_required(mdso_reason):
        error = _isolate_error_message(mdso_reason)
    if not error:
        error = mdso_reason
    return error, specialized


def _error_isolation_required(error):
    # no error calls for regex hunt
    # semantic errors are formatted in an unruly way in mdso network service error
    return not error or error and "SEMANTIC ERRORS" in error


def _isolate_error_message(mdso_reason: str) -> str:
    # attempt to isolate relevant data between ERROR: and PLEASE CHECK FILE delimiters
    initial_isolation = re.search(r"(?<=ERROR:)(.*?)(?=FILE)", mdso_reason)
    if initial_isolation is None:
        # if no match, attempt to isolate with EXCEPTION, RAISED delimiters
        exception_isolation = re.search(r"(?<=EXCEPTION)(.*?)(?=RAISED)", mdso_reason)
        if exception_isolation is None:
            # if no exception raised in error, send for more granular regex refinement
            refined_reason = _refine_isolated_error(mdso_reason)
            return refined_reason[0] if refined_reason else mdso_reason
        else:
            return f"PLEASE INVESTIGATE EXCEPTION RAISED{exception_isolation[0]}"
    # attempt to further isolate relevant data, removing extra noise
    further_isolation = _refine_isolated_error(initial_isolation[0])
    if further_isolation and further_isolation[0] == " ":
        further_isolation = None
    return initial_isolation[0] if further_isolation is None else further_isolation[0]


def _refine_isolated_error(error: str):
    error_handlers = {
        "SCRIPTS.NETWORKSERVICE.SERVICEDEVICECVALIDATOR.ACTIVATE": _service_device_validator_error,
        "SCRIPTS.NETWORKSERVICE.CIRCUITDETAILSCOLLECTOR.ACTIVATE": _circuit_details_collector_error,
        "SCRIPTS.NETWORKSERVICE.SERVICEPROVISIONER.ACTIVATE": _service_provisioner_error,
        "PE_SERVICE_PROVISIONER": _pe_service_provisioner_error,
        "RA_PLUGINS": _ra_plugins_error,
    }
    for script in error_handlers:
        if script in error:
            return error_handlers[script](error)
    # if no specific error handling exists
    # attempt to isolate data between ERROR and PLEASE CHECK FILE
    return re.search(r"(?<=ERROR:)(.*?)(?=PLEASE)", error)


def _service_device_validator_error(error):
    # relevant data found between script name and PLEASE CHECK FILE
    return re.search(r"(?<=SCRIPTS.NETWORKSERVICE.SERVICEDEVICECVALIDATOR.ACTIVATE,)(.*?)(?=PLEASE)", error)


def _circuit_details_collector_error(error):
    # relevant data found between script name and PLEASE CHECK FILE
    return re.search(r"(?<=SCRIPTS.NETWORKSERVICE.CIRCUITDETAILSCOLLECTOR.ACTIVATE,)(.*?)(?=PLEASE)", error)


def _service_provisioner_error(error):
    # relevant data found between script name and PLEASE CHECK FILE
    return re.search(r"(?<=SCRIPTS.NETWORKSERVICE.SERVICEPROVISIONER.ACTIVATE,)(.*?)(?=PLEASE)", error)


def _pe_service_provisioner_error(error):
    # look for data between ERROR ON <port>, ---
    refinement = re.search(r"(?<=ERROR ON)((\sA|\sG|\sX)(E).*?)(?=---)", error)
    if not refinement:
        if "SEMANTIC ERRORS" in error:
            refinement = _semantic_error(error)
        else:
            # if not semantic error or error on port, isolate between 400 BAD REQUEST and FILE
            refinement = re.search(r"(?<=400 BAD REQUEST:)(.*?)(?=FILE)", error)
    if refinement and len(refinement[0]) > 301:
        # truncate if overly verbose
        return re.search(r"(?<=400 BAD REQUEST:)(.*?)(?=PLEASE)", error)
    return refinement if refinement else error


def _semantic_error(error):
    # relevant data found between SEMANTIC ERRORS and END
    return re.search(r"(?<=SEMANTIC ERRORS: )(.*?)(?=END)", error)


def _ra_plugins_error(error):
    # relevant data found between script name and PLEASE CHECK FILE
    return re.search(r"(?<=.ACTIVATE,)(.*?)(?=PLEASE)", error)


def _split_summary_and_error(error, specialized=False):
    logger.debug(f"{error = }")
    logger.debug(f"{specialized = }")
    category_found = any(category.upper() in error.upper() for category in ERROR_CATEGORIES)
    logger.debug(f"{category_found = }")
    if category_found:
        if specialized:
            details = get_standard_error_details(error)
            summary = get_standard_error_summary(error)
            return details, summary
        else:
            summary = re.search(MDSO_REASON_SUMMARY_REGEX, error)[0].split(SUMMARY_DETAILS_DELIMITER)[0].strip()
            logger.debug(f"{summary = }")
            details = re.search(MDSO_REASON_DETAILS_REGEX, error)[0].strip()
            logger.debug(f"{details = }")
            details = clean_details(details.split(f"{summary}{SUMMARY_DETAILS_DELIMITER} ")[-1].split(":"))
            return details, summary
    return error, "MDSO | Process Error"


def stand_alone_config_removal(data):
    """
    Remove the CPE configuration (cpe_config)
    from the resource_status.py return
    for stand_alone_config when called
    returns modified dictionary (data)
    """
    if "cpe_config" in data["properties"].keys():
        del data["properties"]["cpe_config"]
    return data
