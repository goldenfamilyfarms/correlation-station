"""OTLP ingestion endpoints (supports both JSON and protobuf)"""
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any

from opentelemetry.proto.logs.v1.logs_pb2 import LogsData
from opentelemetry.proto.trace.v1.trace_pb2 import TracesData
from google.protobuf.json_format import MessageToDict

from app.routes.auth import verify_basic_auth

router = APIRouter()
logger = structlog.get_logger()


@router.post("/logs", status_code=202)
async def ingest_otlp_logs(
    request: Request,
    authenticated: bool = Depends(verify_basic_auth),
):
    """
    Ingest OTLP logs (supports both JSON and protobuf)

    Accepts OTLP format logs and normalizes them for correlation.
    """
    correlation_engine = request.app.state.correlation_engine
    LOG_RECORDS_RECEIVED = request.app.state.LOG_RECORDS_RECEIVED
    
    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        content_type = request.headers.get("content-type", "")
        
        # Handle protobuf format
        if "application/x-protobuf" in content_type:
            body = await request.body()
            logs_data = LogsData()
            logs_data.ParseFromString(body)
            data = MessageToDict(logs_data, preserving_proto_field_name=True)
        else:
            # Handle JSON format
            data = await request.json()

        # Extract resource logs (simplified parsing)
        resource_logs = data.get("resourceLogs", [])

        total_logs = 0
        for resource_log in resource_logs:
            resource = resource_log.get("resource", {})
            scope_logs = resource_log.get("scopeLogs", [])

            for scope_log in scope_logs:
                log_records = scope_log.get("logRecords", [])
                total_logs += len(log_records)

                # TODO: Convert to internal format and add to correlator
                # For now, just track metrics

        LOG_RECORDS_RECEIVED.labels(source="otlp").inc(total_logs)

        logger.info("otlp_logs_ingested", count=total_logs)

        return {"status": "accepted", "count": total_logs}
    except Exception as e:
        logger.exception("Failed to ingest OTLP logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest OTLP logs: {str(e)}")


@router.post("/traces", status_code=202)
async def ingest_otlp_traces(
    request: Request,
    authenticated: bool = Depends(verify_basic_auth),
):
    """
    Ingest OTLP traces (supports both JSON and protobuf)

    Accepts OTLP format traces and adds them to correlation windows.
    """
    correlation_engine = request.app.state.correlation_engine
    TRACES_RECEIVED = request.app.state.TRACES_RECEIVED

    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        content_type = request.headers.get("content-type", "")

        # Handle protobuf format
        if "application/x-protobuf" in content_type:
            body = await request.body()
            traces_data = TracesData()
            traces_data.ParseFromString(body)
            data = MessageToDict(traces_data, preserving_proto_field_name=True)
        else:
            # Handle JSON format
            data = await request.json()

        # Extract resource spans
        resource_spans = data.get("resourceSpans", [])

        total_spans = 0
        for resource_span in resource_spans:
            scope_spans = resource_span.get("scopeSpans", [])

            for scope_span in scope_spans:
                spans = scope_span.get("spans", [])
                total_spans += len(spans)

        # Forward traces to correlation engine for processing
        await correlation_engine.add_traces(data)

        TRACES_RECEIVED.labels(source="otlp").inc(total_spans)

        logger.info("otlp_traces_ingested", span_count=total_spans)

        return {"status": "accepted", "span_count": total_spans}
    except Exception as e:
        logger.exception("Failed to ingest OTLP traces", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest OTLP traces: {str(e)}")