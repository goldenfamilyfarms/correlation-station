import logging

from fastapi import Query

from arda_app.bll import optic_check as oc
from arda_app.bll.light_test_check import check_port, get_path_elements_data, qfx_paid_check
from arda_app.common import url_config
from arda_app.data.mock_circuits.mc_light_test_check import ltc_test_case_responses
from common_sense.common.errors import abort
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.get("/light_test_check", summary="Light Test Check")
def light_test_check(
    circuit_id: str = Query(..., examples=["27.L1XX.000002.GSO.TWCC"]), prism_id: str = Query(..., examples=["2232045"])
):
    """Perform light test check and return port activation link"""

    # TEST CASES for regression testing
    ltc_test_case_responses(circuit_id)

    path_elements_data = get_path_elements_data(circuit_id)

    if not isinstance(path_elements_data, dict):
        abort(500, f"Path Elements data not found: {path_elements_data}")
        return

    tid = path_elements_data["TID"]
    hostname = tid
    vendor = path_elements_data["VENDOR"]
    hub_model = path_elements_data["MODEL"]
    hub_paid = path_elements_data["PORT_ACCESS_ID"]
    hub_inst_id = path_elements_data["PORT_INST_ID"]

    qfx_paid_check(hub_inst_id, hub_model, hub_paid)

    palantir_resp = False
    try:
        palantir_resp = check_port(tid, hub_paid)
    except Exception as e:
        logger.debug(f"No records found in Palantir for {tid}: {e}")

    if isinstance(palantir_resp, dict) and palantir_resp.get("status_info") == "Port Status Retrieved":
        palantir_resp = True

    pat_link = f"{url_config.LIGHT_TEST_URL}{hostname}/{prism_id}/{hub_paid}"

    if vendor == "JUNIPER":
        ports_info = oc.get_port_from_mdso_juniper(hostname, hub_paid)
        if isinstance(ports_info, dict) and ports_info.get("scenario") == 4:
            return ports_info
    elif vendor == "CISCO":
        return oc.get_port_from_mdso_cisco(hostname, hub_paid)
    else:
        logger.error("Vendor must be either CISCO or JUNIPER")
        abort(500, f"Vendor must be either CISCO or JUNIPER. Vendor found for cid in Granite was: {vendor}")

    """optic comparision check"""
    pat_link = f"{url_config.LIGHT_TEST_URL}{hostname}/{prism_id}/{hub_paid}"

    return {"port_activation_link": pat_link}
