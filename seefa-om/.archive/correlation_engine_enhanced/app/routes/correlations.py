"""Correlation query and synthetic event injection endpoints"""
import structlog
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from datetime import datetime

from app.models import CorrelationEvent, SyntheticEvent

router = APIRouter()
logger = structlog.get_logger()


@router.get("/correlations", response_model=List[CorrelationEvent])
async def query_correlations(
    request: Request,
    trace_id: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(default=100, le=1000),
):
    correlation_engine = request.app.state.correlation_engine
    
    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        correlations = correlation_engine.query_correlations(
            trace_id=trace_id,
            service=service,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        logger.info("correlations_queried", trace_id=trace_id, service=service, count=len(correlations))

        return correlations
    except Exception as e:
        logger.exception("Failed to query correlations", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to query correlations: {str(e)}")


@router.post("/events", status_code=201)
async def inject_synthetic_event(event: SyntheticEvent, request: Request):
    correlation_engine = request.app.state.correlation_engine
    
    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        correlation = await correlation_engine.inject_synthetic_event(event)

        logger.info("synthetic_event_injected", trace_id=event.trace_id, service=event.service)

        return correlation
    except Exception as e:
        logger.exception("Failed to inject synthetic event", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to inject synthetic event: {str(e)}")
