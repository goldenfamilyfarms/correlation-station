from time import sleep
from typing import Union

from arda_app.bll.models.payloads.ip_reservation import IPReservationPayloadModel
from common_sense.common.errors import abort


def ipr_test_case_responses(payload: IPReservationPayloadModel) -> Union[dict, None]:
    """Mock response for IP Reservation"""
    if payload.z_side_info.cid == "51.L3XX.FAIL_IP..CHTR":
        abort(500, "IP Reservation Test Failure Message")
    elif payload.z_side_info.cid == "51.L3XX.FAIL_IP_TIMEOUT..CHTR":
        sleep(300)
        abort(500, "IP Reservation Test Failure Message")

    if payload.z_side_info.cid in (
        "51.L4XX.FAIL_SWIP..CHTR",
        "51.L5XX.FAIL_PthUpdate..CHTR",
        "51.L6XX.FAIL_LTC..CHTR",
        "51.L7XX.PASS_ALL..CHTR",
    ):
        return {
            "ipv4_service_type": "LAN",
            "ipv4_glue_subnet": "",
            "ipv4_assigned_subnets": "98.123.148.56/29",
            "ipv4_assigned_gateway": "98.123.148.57/29",
            "ipv6_service_type": "ROUTED",
            "ipv6_glue_subnet": "2600:5c01:4860:5::/64",
            "ipv6_assigned_subnet": "2600:5c01:4a27::/48",
        }
