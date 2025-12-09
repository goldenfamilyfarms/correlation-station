import logging

from arda_app.bll.add_buy_nni import add_buy_nni
from arda_app.bll.type_two_transport_path import create_transport_path
from arda_app.common.utils import path_regex_match
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def type_2_hub_work_main(payload):
    # Sanitize NNI string
    spectrum_buy_nni_circuit_id = payload.get("spectrum_buy_nni_circuit_id")
    sanitized_nni_cid = path_regex_match(spectrum_buy_nni_circuit_id, match_type="path_name")
    if sanitized_nni_cid:
        payload["spectrum_buy_nni_circuit_id"] = sanitized_nni_cid[0]
    else:
        abort(500, f"Unable to parse Buy NNI {spectrum_buy_nni_circuit_id}")

    buy_nni_success = add_buy_nni(payload)
    if not buy_nni_success:
        abort(500, f"Add Buy NNI stage did not pass for {payload['cid']}")
    return create_transport_path(payload)
