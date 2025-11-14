from typing import Union
from common_sense.common.errors import abort


def bcd_test_case_response(payload: dict) -> Union[dict, None]:
    """Mock response for Build Circuit Design"""
    if payload["z_side_info"]["cid"] == "51.L1XX.FAIL_BCD..CHTR":
        abort(500, "Build Circuit Design Test Failure Message")

    if payload["z_side_info"]["cid"] in (
        "51.L2XX.FAIL_VLAN..CHTR",
        "51.L3XX.FAIL_IP..CHTR",
        "51.L3XX.FAIL_IP_TIMEOUT..CHTR",
        "51.L4XX.FAIL_SWIP..CHTR",
        "51.L5XX.FAIL_PthUpdate..CHTR",
        "51.L6XX.FAIL_LTC..CHTR",
        "51.L7XX.PASS_ALL..CHTR",
    ):
        return {"circ_path_inst_id": "1234"}
