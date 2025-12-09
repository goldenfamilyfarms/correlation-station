import logging

from fastapi import Depends, Request, status

from arda_app.bll.models.payloads import AssignParentPathsPayloadModel
from arda_app.bll.net_new.assign_parent_paths import assign_parent_paths_main
from arda_app.common import app_config
from arda_app.common.http_auth import verify_password
from arda_app.common.regres_testing import regression_testing_check
from arda_app.api._routers import v1_design_new_router

logger = logging.getLogger(__name__)


@v1_design_new_router.put(
    "/assign_parent_paths", summary="[Build_Circuit_Design] Assign Parent Paths", status_code=status.HTTP_201_CREATED
)
def assign_parent_paths(
    request: Request, payload: AssignParentPathsPayloadModel, authenticated: bool = Depends(verify_password)
):
    """Assign Parent Paths Create"""
    logger.info("Initializing Assign Parent Paths")
    logger.info(f"v1/assign_parent_paths payload: {payload.model_dump()}")

    if payload.service_type == "net_new_cj":
        # return response for QA regression testing
        if "STAGE" in app_config.USAGE_DESIGNATION:
            url_path = request.url.path
            test_response = regression_testing_check(url_path, payload.cid)

            if test_response != "pass":
                return test_response

    return assign_parent_paths_main(payload.model_dump())
