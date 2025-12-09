from fastapi import Query

from arda_app.dll.denodo import get_isp_group
from arda_app.api._routers import v1_isp_router


@v1_isp_router.get("/isp_group", summary="ISP Group Lookup")
def isp_group(clli: str = Query(..., examples=["CHRLNCRL"])):
    """GET ISP group using CLLI"""
    isp_group = get_isp_group(clli)
    return isp_group
