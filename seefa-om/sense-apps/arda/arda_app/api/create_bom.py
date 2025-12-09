import os
import base64
import logging

from fastapi import Depends
from fastapi.responses import Response

from arda_app.api._routers import v1_tools_router
from arda_app.bll.determine_bom import determine_bom, adva_1g_template
from arda_app.bll.models.payloads.create_bom import CreateBOMPayloadModel
from arda_app.common.http_auth import verify_password


logger = logging.getLogger(__name__)


@v1_tools_router.post("/create_bom", summary="Generate a BOM")
def generate_bom(payload: CreateBOMPayloadModel, authenticated: bool = Depends(verify_password)):
    """Generate BOM"""
    body = payload.model_dump()
    logger.info(f"v1/create_bom payload: {body}")

    if body.get("expedite") and body["expedite"].lower() == "yes":
        template = adva_1g_template(body)
    else:
        template = determine_bom(body)

    filepath = os.path.abspath(f"arda_app/data/BOM_templates/{template}.xlsx")
    with open(filepath, "rb") as f:
        file = base64.b64encode(f.read()).decode("utf-8")

    headers = {"Content-Disposition": f'attachment; filename="{template}.xlsx"'}

    return Response(
        content=file, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
