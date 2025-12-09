import logging

from fastapi import Query

from arda_app.bll.atlas.juniper import is_valid_interface, show_interface_config
from common_sense.common.errors import abort
from . import juniper_router

logger = logging.getLogger(__name__)


@juniper_router.get("/interface_config", summary="Get Interface Configuration")
def interface_config(
    device_tid: str = Query(..., description="The Device the interface is located on", examples=["GNBTNC391ZW"]),
    interface: str = Query(..., description="The interface you would like to check", examples=["GE-0/0/11"]),
):
    """Get Interface Configuration"""

    if not is_valid_interface(interface):
        abort(500, "Invalid interface format")

    interface_config = show_interface_config(device_tid, interface)
    return interface_config
