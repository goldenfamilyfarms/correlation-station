import logging

from common_sense.common.errors import (
    abort,
    error_formatter,
    get_standard_error_summary,
    GRANITE,
    INCORRECT_DATA,
    SENSE,
    AUTOMATION_UNSUPPORTED,
)
from palantir_app.common.constants import UNSUPPORTED_DDOS_PRODUCTS, DDOS_ALWAYS_ON_PROTECTION, DDOS_PROTECTION
from palantir_app.dll import granite

logger = logging.getLogger(__name__)


def ddos_validation_process(cid, product_name, path_instance_id):
    if product_name in UNSUPPORTED_DDOS_PRODUCTS:
        msg = error_formatter(SENSE, AUTOMATION_UNSUPPORTED, "Product Name", product_name)
        abort(501, msg, summary=get_standard_error_summary(msg))

    udas = granite.get_uda(path_instance_id, cid)

    # validate ddos protection uda
    protection = find_uda_value(udas, "DDoS PROTECTION")
    logger.debug(f"{protection = }")
    if "ALWAYS ON" in product_name.upper() and protection not in DDOS_ALWAYS_ON_PROTECTION:
        msg = error_formatter(GRANITE, INCORRECT_DATA, "DDOS ALWAYS ON PROTECTION", protection)
        abort(501, msg, summary=get_standard_error_summary(msg))
    elif protection not in DDOS_PROTECTION:
        msg = error_formatter(GRANITE, INCORRECT_DATA, "DDOS PROTECTION", protection)
        abort(501, msg, summary=get_standard_error_summary(msg))
    # validate managed service uda
    managed_service = find_uda_value(udas, "MANAGED SERVICE")
    logger.debug(f"{managed_service = }")
    # if not valid, update
    if managed_service != "YES":
        parameters = {
            "PATH_NAME": cid,
            "PATH_INST_ID": path_instance_id,
            "UDA": {"SERVICE TYPE": {"MANAGED SERVICE": "YES"}},
        }
        updated = granite.update_path_by_parameters(parameters)
        if updated != "Successful":
            msg = error_formatter(GRANITE, INCORRECT_DATA, "MANAGED SERVICE", managed_service)
            abort(501, msg, summary=get_standard_error_summary(msg))


def find_uda_value(udas, attr_name):
    """
    Searches for a specific attribute in a list of Granite UDAs.

    Args:
        udas (list of dict): A list of UDA attributes.
        attr_name (str): The name of the attribute to search for.

    Returns:
        str or None: The attribute value if found, otherwise None.
    """
    uda = next((item for item in udas if item.get("ATTR_NAME") == attr_name), None)
    return uda.get("ATTR_VALUE") if uda else None
