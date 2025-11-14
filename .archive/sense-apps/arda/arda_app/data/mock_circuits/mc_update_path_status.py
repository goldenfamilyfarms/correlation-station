from typing import Union

from common_sense.common.errors import abort


def ups_test_case_responses(pathid: str) -> Union[dict, None]:
    """Update path status test cases for regression testing."""
    if pathid in ["51.L5XX.FAIL_PthUpdate..CHTR", "20.L1XX.CD_PASS_UPS_FAIL..TWCC"]:
        abort(500, "Update Path Status Test Failure Message.")

    elif pathid in (
        "51.L6XX.FAIL_LTC..CHTR",
        "51.L7XX.PASS_ALL..CHTR",
        "51.L1XX.partial_pass..CHTR",
        "20.L1XX.DOWNGRADE_PASS..TWCC",
    ):
        return {"cid": pathid, "ethernet_transport": "pathId", "status": "Auto-Designed"}

    elif pathid in {"20.L1XX.001748..TWCC", "20.L1XX.001747..TWCC"}:
        return {"cid": pathid, "status": "Auto-Designed"}
