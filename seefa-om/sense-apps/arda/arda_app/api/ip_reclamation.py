import logging
from typing import Optional

from fastapi import Depends, Query

from arda_app.bll.models.payloads import IPReclamationPayloadModel
from arda_app.bll.net_new.ip_reclamation import delete_ip_subnet_block_by_cid, get_subnet_block_by_cid
from common_sense.common.errors import abort
from arda_app.common.http_auth import verify_password
from sense_common.observability import get_tracer, set_mdso_correlation, add_span_event, set_span_error
from sense_common.observability.mdso_patterns import ErrorCategorizer
from arda_app.dll.ipc import create_subnet_block
from ._routers import v1_tools_router


logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


@v1_tools_router.post("/ip_reclamation", summary="Return a Reserved IP to IP Control (IPC)")
def ip_reclamation(
    container: Optional[str] = Query(
        None, description="The name of the subnet block's container", examples=["C0555555"]
    ),
    cid: str = Query(
        ..., description="Circuit ID whose IPv4/IPv6 subnet blocks you want from IPC", examples=["51.L1XX.054855..CHTR"]
    ),
    authenticated: bool = Depends(verify_password),
):
    """Reclaim a Subnet Block by deleting it from IP Control (IPC)"""
    with tracer.start_as_current_span("arda.ip_reclamation.delete") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("ip_reclamation.operation", "delete")
        if container:
            span.set_attribute("ip_reclamation.container", container)
        
        try:
            add_span_event("ip_reclamation.delete.start", circuit_id=cid, container=container)
            result = delete_ip_subnet_block_by_cid(cid, container)
            add_span_event("ip_reclamation.delete.complete", circuit_id=cid)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "IP_RECLAMATION_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise


@v1_tools_router.get("/ip_reclamation/subnet", summary="Return a Reserved IP to IP Control (IPC)")
def get_subnet_block(
    cid: str = Query(
        ..., description="Circuit ID whose IPv4/IPv6 subnet blocks you want from IPC", examples=["51.L1XX.054855..CHTR"]
    ),
):
    """Retrieve Subnet Block Data from IP Control (IPC)"""
    if cid:
        return get_subnet_block_by_cid(cid)
    else:
        abort(500, "Invalid CID parameter")


@v1_tools_router.post("/ip_reclamation/subnet", summary="Return a Reserved IP to IP Control (IPC)")
def post_subnet_block(payload: IPReclamationPayloadModel, authenticated: bool = Depends(verify_password)):
    """Add a new subnet child block to a specific container in IP Control (IPC)"""
    payload_dict = payload.model_dump()
    cid = payload_dict.get("cid")
    
    with tracer.start_as_current_span("arda.ip_reclamation.create_subnet") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("ip_reclamation.operation", "create_subnet")
        if "container" in payload_dict:
            span.set_attribute("ip_reclamation.container", payload_dict["container"])
        
        try:
            add_span_event("ip_reclamation.create_subnet.start", circuit_id=cid)
            result = create_subnet_block(payload_dict)
            add_span_event("ip_reclamation.create_subnet.complete", circuit_id=cid)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "IP_RECLAMATION_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise
