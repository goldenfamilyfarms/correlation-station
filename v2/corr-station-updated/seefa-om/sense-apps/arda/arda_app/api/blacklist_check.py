from pydantic.networks import IPvAnyNetwork

from arda_app.dll.blacklist import is_blacklisted
from arda_app.api._routers import v1_design_mac_router


@v1_design_mac_router.get("/blacklist_check", summary="Check information for ip address")
def blacklist_check(ip: IPvAnyNetwork = "147.0.218.64/29"):
    """Check information for ip address"""

    return is_blacklisted(ip)
