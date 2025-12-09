import json
import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic_core import ValidationError

from common_sense.common.errors import remove_api_key


def error_message_handler(body: bytes, exc: Exception | RequestValidationError, request: Request) -> dict:
    """returns a general error message."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = body.decode("utf-8")

    return {
        "SEnSE Bug!!": "Sending Report to SEnSE team for investigation",
        "URL": f"{request.url}",
        "URL PARAMS": f"{request.query_params}",
        "PAYLOAD": payload,
        "REMOTE ADDR": f"{request.client.host}",
        "TRACE": remove_api_key(f"{traceback.format_exc()}"),
    }


def validation_message_handler(exc: RequestValidationError | ValidationError) -> dict:
    """returns a validation error message."""
    details = exc.errors()
    app_prefix = "SENSE"

    missing_fields = []
    literal_error = {}
    wrong_type = []
    additional_error = []

    result = {}

    for error in details:
        if error["type"] == "missing":
            missing_fields.append(error["loc"][-1])
        elif error["type"] == "literal_error":
            literal_error[error["loc"][-1]] = error["input"]
        elif error["type"] == "string_type":
            wrong_type.append(error["loc"][-1])
        else:
            message = error["msg"]
            field = error["loc"][-1]
            additional_error.append(f"{message} for field: {field}")

    if missing_fields:
        # optic check validation logic
        if error["loc"][1] in ("remedy_fields", "sales_force_fields", "prism_fields"):
            tool = error["loc"][1]
            miss_items = {", ".join(missing_fields)}
            msg = (
                "SOVA Optic Validation and Remedy Work Order monitoring can not begin "
                + "because the following required information is not provided."
            )
            if len(miss_items) > 1 and tool != "remedy_fields":
                tool = f"remedy_fields, {tool}"
            message = f"{msg} {tool} - {miss_items}"
        else:
            message = f"ARDA - Required query parameter(s) not specified: {', '.join(missing_fields)}"

        summary_message = "Missing Payload Keys"
        if not result:
            result = {"message": message, "summary": f"{app_prefix} | {summary_message}"}
        else:
            result["message"] += f". {message}"
            result["summary"] += f". {summary_message}"

    if literal_error:
        message = (
            "ARDA - Unsupported value(s): "
            f"{', '.join([value if value else 'None' for value in literal_error.values()])} "
            f"for literal field(s): {', '.join(literal_error.keys())}"
        )
        summary_message = "Literal Error"
        if not result:
            result = {"message": message, "summary": f"{app_prefix} | {summary_message}"}
        else:
            result["message"] += f". {message}"
            result["summary"] += f". {summary_message}"

    if wrong_type:
        message = f"ARDA - Incorrect field type: {', '.join(wrong_type)}"
        summary_message = "Incorrect field type"
        if not result:
            result = {"message": message, "summary": f"{app_prefix} | {summary_message}"}
        else:
            result["message"] += f". {message}"
            result["summary"] += f". {summary_message}"

    if additional_error:
        message = f"ARDA - {', '.join(additional_error)}"
        summary_message = "Validation exception"
        if not result:
            result = {"message": message, "summary": f"{app_prefix} | {summary_message}"}
        else:
            result["message"] += f". {message}"
            result["summary"] += f". {summary_message}"

    return result


async def set_body(request: Request, body: bytes):
    """Sets the body of the request."""

    async def receive() -> dict:
        return {"type": "http.request", "body": body}

    request._receive = receive


async def get_body(request: Request) -> bytes:
    """Gets the body of the request."""
    body = await request.body()
    await set_body(request, body)
    return body
