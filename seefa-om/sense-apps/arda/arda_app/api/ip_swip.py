import logging

from fastapi import Depends, Query, Request, status

from arda_app.bll.models.payloads import IPSWIPPayloadModel
from arda_app.bll.net_new.ip_swip import ip_swip_main, ip_unswip_main
from arda_app.dll.arin import get_arin_records, whois_check
from common_sense.common.errors import abort
from arda_app.common import app_config
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from arda_app.dll.granite import get_ip_subnets
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.post("/ip_swip", summary="[Build_Circuit_Design] IP SWIP", status_code=status.HTTP_201_CREATED)
def ip_swip(request: Request, payload: IPSWIPPayloadModel, authenticated: bool = Depends(verify_password)):
    """
    Perform IP SWIP for a circuit
    """
    logger.info("Initializing IP SWIP process")
    logger.info(f"v1/ip_swip payload: {payload.model_dump()}")

    customer_info = {
        "customer_id": payload.customer_id,
        "z_address": payload.z_address,
        "z_city": payload.z_city,
        "z_state": payload.z_state,
        "z_zip": payload.z_zip,
    }

    if payload.service_type in (
        "net_new",
        "quick_connect",
        "net_new_cj",
        "net_new_qc",
        "net_new_serviceable",
        "net_new_no_cj",
        "add",
    ):
        # return response for QA regression testing
        if "STAGE" in app_config.USAGE_DESIGNATION:
            url_path = request.url.path
            fixed_part = "/".join(url_path.split("/")[:3])
            test_response = regression_testing_check(fixed_part, payload.cid)
            if test_response != "pass":
                return test_response

        # TEST CASES for regression testing
        if payload.cid == "51.L4XX.FAIL_SWIP..CHTR":
            abort(500, "IP SWIP Test Failure Message")

        if payload.cid in ("51.L5XX.FAIL_PthUpdate..CHTR", "51.L6XX.FAIL_LTC..CHTR", "51.L7XX.PASS_ALL..CHTR"):
            return {
                "message": "IP SWIP operation completed",
                "IPs Assigned": "[{'ip': '98.123.148.56/29', 'status': 'success'}, \
                    {'ip': '2600:5c01:4a27::/48', 'status': 'success'}]",
            }

        return ip_swip_main(payload.ipv4_lan, payload.ipv6_route, customer_info)
    else:
        logger.info(f"Unsupported service type {payload.service_type}")
        abort(500, f"Unsupported service type {payload.service_type}")


@v1_design_new_router.post("/ip_swip/unswip", summary="[Build_Circuit_Design] IP UNSWIP")
def ip_unswip(cid: str, authenticated: bool = Depends(verify_password)):
    """
    Perform IP un-SWIP for a circuit to release its IPs
    """
    logger.info("Initializing IP un-SWIP release process")

    if not cid:
        abort(500, "CID parameter missing")
    else:
        return ip_unswip_main(cid)


@v1_design_new_router.get("/ip_swip/whois", summary="WHOIS IP Lookup")
def whois(ip: str):
    """
    Perform IP WHOIS lookup
    """
    if not ip:
        abort(500, "IP parameter missing")
    else:
        return whois_check(ip)


@v1_design_new_router.get("/ip_swip/subnets", summary="Granite IP Lookup")
def subnets(cid: str):
    """
    Retrieve a circuit's IPv4 and IPv6 subnets from Granite
    """

    if not cid:
        abort(500, "Invalid CID parameter")
    else:
        return get_ip_subnets(cid)


@v1_design_new_router.get("/ip_swip/records", summary="ARIN Records Lookup")
def records(
    customer_id: str = Query(..., description="The organization's customerHandle", examples=["C12345678"]),
    handle: str = Query(..., description="The organization's netHandle", examples=["NET-12-34-56-78-9"]),
):
    """Retrieve an organization's net and customer records from ARIN"""

    return get_arin_records(customer_id, handle)
