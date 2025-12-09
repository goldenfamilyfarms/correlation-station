from arda_app.dll.granite import get_selected_vendor

from arda_app.api._routers import v1_tools_router


@v1_tools_router.get(
    "/adva_rad_by_year", summary="50/50 vender design determination", description="50/50 vender design determination"
)
def adva_rad_by_year():
    """Get Adva or Rad by year"""
    return get_selected_vendor(source="adva_rad")
