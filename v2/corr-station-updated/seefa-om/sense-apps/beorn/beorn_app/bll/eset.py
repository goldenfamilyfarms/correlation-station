import logging
import beorn_app
from common_sense.common.errors import abort
from beorn_app.dll.eset import get_eset
from beorn_app.common.endpoints import ESET_VENDOR_MODEL

logger = logging.getLogger(__name__)


def get_device_data_from_eset_ui(snmp_isolated_model, best_effort=False):
    if not snmp_isolated_model:
        msg = f"Invalid Model Input provided to ESET UI: {snmp_isolated_model}"
        if best_effort:
            logger.debug(msg)
            return
        abort(502, msg)
    params = {"filter": f"snmp_isolated_model={snmp_isolated_model}"}
    timeout = 60
    return get_eset(beorn_app.url_config.ESET_BASE_URL, ESET_VENDOR_MODEL, params, timeout, best_effort=best_effort)
