import logging

from fastapi import Query

from arda_app.bll.atlas.snmp import snmp_get
from arda_app.api import atlas_router

logger = logging.getLogger(__name__)


@atlas_router.get("/snmp/get", summary="Get Vendor/Model via SNMP")
def atlas_snmp(
    obj_identifier: str = Query(
        ...,
        description="The object identifier is an indicator in SNMP that signifies what data is being requested.",
        examples=["sysDescr"],
    ),
    device_tid: str = Query(..., description="The TID or IP address of the device", examples=["GNBTNC391ZW"]),
):
    """Get Vendor/Model via SNMP"""

    return snmp_get(device_tid, obj_identifier)
