from typing import Any, Callable

from fastapi import APIRouter as FastAPIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pydantic_core import ValidationError

from arda_app.api import (
    v1_cid_router,
    v4_cid_router,
    v5_cid_router,
    v1_isp_router,
    v3_isp_router,
    v1_design_router,
    v1_design_new_router,
    v1_design_mac_router,
    v2_remedy_router,
    v1_tools_router,
    atlas_router,
    v1_internal_router,
)

from arda_app.common.logging_setup import setup_logging
from common_sense.common.errors import AbortException
from arda_app.error_handler import error_message_handler, set_body, validation_message_handler
from arda_app.version import __VERSION__


app = FastAPI(
    docs_url="/arda",
    openapi_url="/arda/openapi.json",
    description="An Inventory SEEFA Design Microservice",
    title="ARDA - SEEFA Design Microservices",
    version=__VERSION__,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "none"},
)

# Homepage at "/"
app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/", include_in_schema=False)
async def read_index():
    return FileResponse("public/index.html")


# Set logger
logger = setup_logging()


# APIRouter: Prevent the 307 Temporary Redirect When There's a Missing Trailing Slash
class APIRouter(FastAPIRouter):
    def add_api_route(
        self, path: str, endpoint: Callable[..., Any], *, include_in_schema: bool = True, **kwargs: Any
    ) -> None:
        if path.endswith("/"):
            alternate_path = path[:-1]
        else:
            alternate_path = path + "/"
        super().add_api_route(alternate_path, endpoint, include_in_schema=False, **kwargs)
        return super().add_api_route(path, endpoint, include_in_schema=include_in_schema, **kwargs)


# Root router
root_router = APIRouter(prefix="/arda")

# Routers
root_router.include_router(v1_cid_router)
root_router.include_router(v4_cid_router)
root_router.include_router(v5_cid_router)
root_router.include_router(v1_isp_router)
root_router.include_router(v3_isp_router)
root_router.include_router(v1_design_router)
root_router.include_router(v1_design_new_router)
root_router.include_router(v1_design_mac_router)
root_router.include_router(v2_remedy_router)
root_router.include_router(v1_tools_router)
root_router.include_router(atlas_router)
root_router.include_router(v1_internal_router)
app.include_router(root_router)


def custom_openapi():
    if not app.openapi_schema:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )
        for _, method_item in app.openapi_schema.get("paths").items():
            for _, param in method_item.items():
                responses = param.get("responses")
                # remove 422 response, also can remove other status code
                if "422" in responses:
                    del responses["422"]
    return app.openapi_schema


app.openapi = custom_openapi


# Exception Handler
@app.middleware("http")
async def errors_handling(request: Request, call_next):
    """Handles sense errors."""
    body = await request.body()
    try:
        await set_body(request, await request.body())
        return await call_next(request)
    except Exception as exc:
        logger.exception(f"Error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_message_handler(body, exc, request)
        )


@app.exception_handler(AbortException)
def abort_exception_handler(_, exc: AbortException):
    """Handles abort errors."""
    logger.exception(f"Abort Error: {exc}")
    return JSONResponse(status_code=exc.status_code, content=exc.data)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_, exc: RequestValidationError):
    """Handles incoming request payload validation errors."""
    logger.exception(f"Validation Error: {exc}")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=validation_message_handler(exc))


@app.exception_handler(ValidationError)
async def validation_exception_handler(_, exc: ValidationError):
    """Handles all Pydantic validation errors."""
    logger.exception(f"Validation Error: {exc}")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=validation_message_handler(exc))
