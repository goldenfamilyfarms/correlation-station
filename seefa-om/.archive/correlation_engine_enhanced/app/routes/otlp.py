"""OTLP ingestion endpoints (supports both JSON and protobuf)"""
import structlog
from fastapi import APIRouter, HTTPException, Request

from opentelemetry.proto.logs.v1.logs_pb2 import LogsData
from opentelemetry.proto.trace.v1.trace_pb2 import TracesData
from google.protobuf.json_format import MessageToDict

router = APIRouter()
logger = structlog.get_logger()


@router.post("/logs", status_code=202)
async def ingest_otlp_logs(request: Request):
    correlation_engine = request.app.state.correlation_engine
    LOG_RECORDS_RECEIVED = request.app.state.LOG_RECORDS_RECEIVED
    
    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/x-protobuf" in content_type:
            body = await request.body()
            logs_data = LogsData()
            logs_data.ParseFromString(body)
            data = MessageToDict(logs_data, preserving_proto_field_name=True)
        else:
            data = await request.json()

        resource_logs = data.get("resourceLogs", [])
        total_logs = sum(len(scope_log.get("logRecords", [])) 
                        for resource_log in resource_logs 
                        for scope_log in resource_log.get("scopeLogs", []))

        LOG_RECORDS_RECEIVED.labels(source="otlp").inc(total_logs)
        logger.info("otlp_logs_ingested", count=total_logs)

        return {"status": "accepted", "count": total_logs}
    except Exception as e:
        logger.exception("Failed to ingest OTLP logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest OTLP logs: {str(e)}")


@router.post("/traces", status_code=202)
async def ingest_otlp_traces(request: Request):
    correlation_engine = request.app.state.correlation_engine
    TRACES_RECEIVED = request.app.state.TRACES_RECEIVED

    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    try:
        content_type = request.headers.get("content-type", "")

        if "application/x-protobuf" in content_type:
            body = await request.body()
            traces_data = TracesData()
            traces_data.ParseFromString(body)
            data = MessageToDict(traces_data, preserving_proto_field_name=True)
        else:
            data = await request.json()

        resource_spans = data.get("resourceSpans", [])
        total_spans = sum(len(scope_span.get("spans", [])) 
                         for resource_span in resource_spans 
                         for scope_span in resource_span.get("scopeSpans", []))

        await correlation_engine.add_traces(data)
        TRACES_RECEIVED.labels(source="otlp").inc(total_spans)

        logger.info("otlp_traces_ingested", span_count=total_spans)

        return {"status": "accepted", "span_count": total_spans}
    except Exception as e:
        logger.exception("Failed to ingest OTLP traces", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest OTLP traces: {str(e)}")
