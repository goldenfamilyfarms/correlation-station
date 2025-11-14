from typing import Union

from common_sense.common.errors import abort


def ltc_test_case_responses(circuit_id: str) -> Union[dict, None]:
    """Mock response for Light Test Check"""
    if circuit_id == "51.L6XX.FAIL_LTC..CHTR":
        abort(500, "Light Test Check Test Failure Message")

    if circuit_id == "51.L7XX.PASS_ALL..CHTR":
        return {"port_activation_link": "https://light-test.seek.chtrse.com/light_test/TEST0QW/9999999/GE-9/9/9"}
