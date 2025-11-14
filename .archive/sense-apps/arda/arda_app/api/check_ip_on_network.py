import logging

from common_sense.common.errors import abort
from arda_app.api._routers import v1_tools_router
from arda_app.bll.net_new.ip_reservation.utils.mdso_utils import mdso_static_validation
from arda_app.common.http_auth import verify_password
from fastapi import Query, Depends
from typing import Optional

logger = logging.getLogger(__name__)


@v1_tools_router.get("/check_ip_on_network", summary="Check if the IP is in use on the network")
def check_ip_on_network_endpoint(
    ip: str = Query(description="The IP to check for", examples=["24.197.12.48/29"]),
    mx: Optional[str] = Query(default=None, description="The MX in question", examples=["AUSDTX121CW"]),
    authenticated: bool = Depends(verify_password),
):
    logger.info("Initializing the IP on network lookup")
    logger.info(f"v1/check_ip_on_network: IP - {ip}, MX - {mx}")

    if "/" not in ip:
        abort(500, f"IP value in unexpected format. IP string requires CIDR notation {ip}")

    # Check if IP is in use
    ip_in_use = mdso_static_validation(ip.split("/")[0], ip, mx, attempt_onboarding=False)

    return {"ip_in_use": True if ip_in_use else False}
