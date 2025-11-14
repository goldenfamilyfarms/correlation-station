import json
import logging
import os
import re

# determine framework to guide custom abort logic
try:
    from flask import abort as flask_abort
    from werkzeug.exceptions import HTTPException

    FRAMEWORK = "flask"
except ImportError:
    FRAMEWORK = "fast_api"

from common_sense.common.summary_mapping_tables import ID_TABLE, REGEX_TABLE

app_name = os.environ.get("MS_NAME", "SEnSE")
logger = logging.getLogger(__name__)

RETRY_TRIGGER_STATUS_CODES = [401, 404, 503, 504]

SUMMARY_DETAILS_DELIMITER = ":"
DETAILS_REGEX = r"\:(.*)"

SENSE = "SEnSE"
MDSO = "MDSO"
GRANITE = "Granite"
NETWORK = "Network"
SYSTEM_CATEGORIES = [
    SENSE,
    MDSO,
    GRANITE,
    NETWORK,
]

AUTOMATION_UNSUPPORTED = "Automation Unsupported"
CONNECTIVITY = "Connectivity Error"
SYSTEM = "System Error"
INCORRECT_DATA = "Incorrect Data"
MISSING_DATA = "Missing Data"
TOPOLOGIES_UNSUPPORTED = "Topology Unsupported"
PROCESS = "Process Error"

ERROR_CATEGORIES = [
    AUTOMATION_UNSUPPORTED,
    CONNECTIVITY,
    SYSTEM,
    INCORRECT_DATA,
    MISSING_DATA,
    PROCESS,
]


# AbortException class for fastapi custom abort exception
class AbortException(Exception):
    def __init__(self, status_code: int, data: dict):
        self.code = status_code
        self.status_code = status_code
        self.data = data
        logger.error(data)


def abort(status_code, message="", **kwargs):
    custom_aborts = {"flask": custom_flask_abort, "fast_api": custom_fast_api_abort}
    return custom_aborts[FRAMEWORK](status_code, message, **kwargs)


def custom_flask_abort(status_code, message="", **kwargs):
    """
    Custom abort to add the name of the application.
    """
    if status_code in RETRY_TRIGGER_STATUS_CODES:
        status_code = 500
    try:
        flask_abort(status_code)
    except HTTPException as e:
        if message:
            if kwargs and kwargs.get("pretty_format"):
                kwargs["message"] = message
            else:
                kwargs["message"] = f"{app_name} - {str(message)}"
        if kwargs:
            e.data = kwargs
            if not kwargs.get("pretty_format"):  # not json obj, make it pretty the hard way
                e.data["message"] = clean_message(e.data["message"])
            # generate integration error summary if not provided
            if not kwargs.get("summary"):
                e.data["summary"] = generate_error_summary(e.data["message"])
            logger.error(kwargs)
        raise


def custom_fast_api_abort(status_code=500, message="Unknown error", **kwargs):
    try:
        message = json.loads(message)
        message = message.get("message", "Unknown error")
    except json.decoder.JSONDecodeError:
        message = f"{app_name} - {str(message)}"
    except Exception:
        message = f"{app_name} - {str(message)}"

    message = clean_message(message)

    # generate integration error summary if not provided
    if not kwargs.get("summary"):
        summary = generate_error_summary(message)

    data = {"message": message, "summary": summary}
    raise AbortException(status_code=status_code, data=data)


def clean_message(message):
    message = re.sub(r"\\|\n", "", message)
    # convert escaped double quotes to single quotes
    message = re.sub('"', "'", message)
    # remove the random n at the end of nested dicts converted to strings
    message = re.sub(r"n(?='})", "", message)
    # convert u003d symbol to '='
    message = message.replace("u003d", "=")
    return message


def remove_api_key(string: str) -> str:
    """Clean API keys from strings so they don't return in aborts"""
    return re.sub(r"api_key=\S{40}", "api_key=<key>", string)


def clean_internal_endpoint_fallout(err_data: dict, endpoint: str) -> dict:
    """Remove extra messaging from internal endpoint calls and return just the dict with message and summary keys"""
    if "SENSE timeout - METHOD:" in err_data["message"]:
        return {"message": f"Timeout calling {endpoint}", "summary": "SENSE | Timeout"}
    else:
        if "{'message':'ARDA" in err_data["message"]:
            # fastAPI
            err_data["message"] = err_data["message"].split("message':'")[-1]  # grab value of last message key
        else:
            # Flask
            err_data["message"] = err_data["message"].split("message': '")[-1]  # grab value of last message key
        err_data["message"] = re.sub(r"'summary':(.*)", "", err_data["message"])  # remove summary key/value from string
        err_data["message"] = err_data["message"].rstrip()[:-2]
        if "'summary':" in err_data["summary"]:
            err_data["summary"] = re.sub(r"'summary':(.*)", "", err_data["summary"])
            err_data["summary"] = err_data["summary"].rstrip()[:-2]
        return err_data


def error_id_lookup(error: str) -> str:
    for id in ID_TABLE:
        if re.search(id, error):
            return ID_TABLE[id]
    return ""


def regex_lookup(error: str) -> str:
    for summary in REGEX_TABLE:
        if re.search(summary["rule"], error):
            return summary["summary"]
    return "Uncategorized | Not Yet Mapped"


def generate_error_summary(error: str) -> str:
    microservice = "PALANTIR - " if "PALANTIR" in error else "BEORN - "
    error = error.split(microservice)[-1]
    if AUTOMATION_UNSUPPORTED in error:
        return parse_mdso_unsupported(error)
    return get_unstandardized_error_summary(error)


def get_unstandardized_error_summary(error):
    if "unsupported" in error.lower() and "::" in error:
        return unsupported_summary(error)
    summary = error_id_lookup(error)
    if not summary:
        summary = regex_lookup(error)
    return summary


def parse_mdso_unsupported(error: str) -> str:
    if "MDSO | Automation Unsupported" in error:
        if "Equipment Issue" in error and "," in error:
            return error.split(",")[0]
        return error.split(" -- ")[0].split(" Workstream: ")[0]
    return error


def unsupported_summary(error: str) -> str:
    unsupported_value = error.split("::")[-1].strip()
    if "product" in error.lower():
        return f"Unsupported | Product - {unsupported_value}"
    elif "cpe vendor" in error.lower():
        return f"Unsupported | CPE Vendor - {unsupported_value}"
    elif "Logical Change" in error:
        return f"Unsupported | Logical Change Reason - {unsupported_value}"


def format_unsupported_service_error(unsupported_service, workstream):
    detail = unsupported_service["reason"]["message"].split("Automation Unsupported:")[-1].strip()
    return f"MDSO | Automation Unsupported - Service Issue: {detail} Workstream: {workstream}"


def format_unsupported_equipment_error(unsupported_equipment, workstream):
    msg = "MDSO | Automation Unsupported - Equipment Issue:"
    device_count = 0
    for device in unsupported_equipment:
        if device_count > 0:
            msg += ","
        category = unsupported_equipment[device]["reason"]["category"]
        element = unsupported_equipment[device]["reason"]["message"].split("Automation Unsupported:")[-1]
        msg += f" {category}: {element}"
        device_count += 1
    msg = f"{msg} Workstream: {workstream}"
    return msg


def error_formatter(system, category, subcategory, detail):
    return f"{system} | {category} - {subcategory}: {detail}"


def granite_msg(category, subcategory, detail=""):
    return error_formatter("Granite", category, subcategory, detail)


def topologies_msg(subcategory, detail=""):
    return error_formatter("SEnSE", TOPOLOGIES_UNSUPPORTED, subcategory, detail)


def mdso_msg(error):
    # this is a legacy message, only called as a fallback if normal automation unsupported process fails
    return error_formatter("MDSO", AUTOMATION_UNSUPPORTED, "Uncategorized", error)


def get_standard_error_summary(error):
    return error.split(SUMMARY_DETAILS_DELIMITER)[0].upper()


def get_standard_error_details(error):
    isolated_details = re.search(DETAILS_REGEX, error)[0].upper().split(SUMMARY_DETAILS_DELIMITER)
    return clean_details(isolated_details)


def clean_details(split_details: list):
    details = " ".join(split_details).strip()
    details = details.replace("  ", " ")
    return details
