import logging

from fastapi import Depends, Query

from arda_app.bll.net_new.ip_reclamation import reclaim_mgmt_ip_main
from arda_app.common.http_auth import verify_password
from arda_app.api._routers import v1_tools_router

logger = logging.getLogger(__name__)


@v1_tools_router.post("/reclaim_cpe_mgmt_ip", summary="Reclaim a CPE's MGMT IP from IPControl (IPC)")
def reclaim_mgmt_ip(
    tid: str = Query(
        ..., description="The hostname whose management IP you want to reclaim from IPC", examples=["AMDAOH031ZW"]
    ),
    mgmt_ip: str = Query(..., description="The management IP you'll be reclaiming from IPC", examples=["147.0.218.64"]),
    authenticated: bool = Depends(verify_password),
):
    """Reclaim static Management IPs from IPControl (IPC)"""

    return reclaim_mgmt_ip_main(tid, mgmt_ip)
