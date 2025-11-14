"""Logs ingestion endpoint"""
import structlog
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List

from app.models import LogBatch, LogRecord
from app.routes.auth import verify_basic_auth

router = APIRouter()
logger = structlog.get_logger()


@router.post("/logs", status_code=202)
async def ingest_logs(
    batch: LogBatch,
    request: Request,
    authenticated: bool = Depends(verify_basic_auth),
):
    """
    Ingest a batch of logs from Alloy/Gateway

    Accepts logs in normalized format with resource info and log records.
    Logs are queued for correlation and exported to Loki.
    """
    correlation_engine = request.app.state.correlation_engine
    LOG_RECORDS_RECEIVED = request.app.state.LOG_RECORDS_RECEIVED
    
    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        # Track metrics
        LOG_RECORDS_RECEIVED.labels(source="gateway").inc(len(batch.records))

        # Add to correlation engine
        await correlation_engine.add_logs(batch)

        logger.info(
            "logs_ingested",
            service=batch.resource.service,
            count=len(batch.records),
            has_trace_ids=sum(1 for r in batch.records if r.trace_id),
        )

        return {
            "status": "accepted",
            "count": len(batch.records),
            "service": batch.resource.service,
        }
    except Exception as e:
        logger.exception("Failed to ingest logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest logs: {str(e)}")