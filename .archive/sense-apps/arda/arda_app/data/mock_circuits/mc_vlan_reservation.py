from typing import Union
from common_sense.common.errors import abort


def vr_test_case_responses(cid: str) -> Union[dict, None]:
    if cid in (
        "51.L3XX.FAIL_IP..CHTR",
        "51.L3XX.FAIL_IP_TIMEOUT..CHTR",
        "51.L4XX.FAIL_SWIP..CHTR",
        "51.L5XX.FAIL_PthUpdate..CHTR",
        "51.L6XX.FAIL_LTC..CHTR",
        "51.L7XX.PASS_ALL..CHTR",
    ):
        return {"message": "Successful VLAN Reservation"}
    elif cid == "51.L2XX.FAIL_VLAN..CHTR":
        abort(500, "Vlan Reservation Test Failure Message")
