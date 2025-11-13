from arda_app.bll.models.responses import HealthResponseModel
from arda_app.api._routers import v1_internal_router


@v1_internal_router.get("/health", summary="Arda App Health Check", response_model=HealthResponseModel)
def health():
    """Arda App Health Check"""
    return {"status": "healthy"}
