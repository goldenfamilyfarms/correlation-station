"""OTLP ingestion endpoints (supports both JSON and protobuf)"""
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any

from opentelemetry.proto.logs.v1.logs_pb2 import LogsData
from opentelemetry.proto.trace.v1.trace_pb2 import TracesData
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError

from app.routes.auth import verify_basic_auth
from app.config import settings
from app.profiling import profile_function

router = APIRouter()
logger = structlog.get_logger()


async def validate_request_size(request: Request):
    """Validate request body size to prevent DoS attacks"""
    # Check Content-Length header if present
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
            if size > settings.max_request_body_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request too large: {size} bytes (max {settings.max_request_body_size} bytes)"
                )
        except ValueError:
            pass  # Invalid content-length, will be caught when reading body


@router.post("/logs", status_code=202)
@profile_function(tags={"endpoint": "otlp_logs", "operation": "ingest"})
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

    # Validate request size
    await validate_request_size(request)

    try:
        content_type = request.headers.get("content-type", "")

        # Handle protobuf format
        if "application/x-protobuf" in content_type:
            body = await request.body()

            # Additional size check after reading body
            if len(body) > settings.max_protobuf_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Protobuf payload too large: {len(body)} bytes"
                )

            try:
                logs_data = LogsData()
                logs_data.ParseFromString(body)
                data = MessageToDict(logs_data, preserving_proto_field_name=True)
            except DecodeError as e:
                logger.error("Invalid protobuf format", error=str(e))
                raise HTTPException(status_code=400, detail=f"Invalid protobuf format: {str(e)}")
            except Exception as e:
                logger.error("Failed to parse protobuf", error=str(e))
                raise HTTPException(status_code=400, detail=f"Failed to parse protobuf: {str(e)}")
        else:
            # Handle JSON format with size check
            body = await request.body()
            if len(body) > settings.max_json_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"JSON payload too large: {len(body)} bytes"
                )

            import json
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON format", error=str(e))
                raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

        # Extract resource logs and convert to internal format
        resource_logs = data.get("resourceLogs", [])

        from app.models import LogBatch, LogRecord, ResourceInfo
        from datetime import datetime, timezone

        total_logs = 0
        for resource_log in resource_logs:
            # Extract resource attributes
            resource = resource_log.get("resource", {})
            resource_attrs = {}
            for attr in resource.get("attributes", []):
                key = attr.get("key", "")
                value = attr.get("value", {})
                # Extract string value (simplified - could handle other types)
                if "stringValue" in value:
                    resource_attrs[key] = value["stringValue"]

            # Build ResourceInfo
            resource_info = ResourceInfo(
                service=resource_attrs.get("service.name", "unknown"),
                host=resource_attrs.get("host.name", "unknown"),
                env=resource_attrs.get("deployment.environment", "dev")
            )

            # Extract log records
            records = []
            for scope_log in resource_log.get("scopeLogs", []):
                for log_record in scope_log.get("logRecords", []):
                    # Extract timestamp
                    time_unix_nano = log_record.get("timeUnixNano", 0)
                    if time_unix_nano:
                        timestamp = datetime.fromtimestamp(int(time_unix_nano) / 1e9, tz=timezone.utc).isoformat()
                    else:
                        timestamp = datetime.now(timezone.utc).isoformat()

                    # Extract message
                    body = log_record.get("body", {})
                    message = body.get("stringValue", str(body))

                    # Extract severity
                    severity_number = log_record.get("severityNumber", 9)  # Default to INFO
                    severity_map = {
                        1: "TRACE", 5: "DEBUG", 9: "INFO",
                        13: "WARN", 17: "ERROR", 21: "FATAL"
                    }
                    severity = severity_map.get(severity_number, "INFO")

                    # Extract trace context
                    trace_id = log_record.get("traceId", "")
                    if isinstance(trace_id, bytes):
                        trace_id = trace_id.hex()

                    span_id = log_record.get("spanId", "")
                    if isinstance(span_id, bytes):
                        span_id = span_id.hex()

                    # Extract custom attributes
                    log_attrs = {}
                    for attr in log_record.get("attributes", []):
                        key = attr.get("key", "")
                        value = attr.get("value", {})
                        if "stringValue" in value:
                            log_attrs[key] = value["stringValue"]

                    # Create LogRecord
                    record = LogRecord(
                        timestamp=timestamp,
                        severity=severity,
                        message=message,
                        trace_id=trace_id or None,
                        span_id=span_id or None,
                        circuit_id=log_attrs.get("circuit_id"),
                        product_id=log_attrs.get("product_id"),
                        resource_id=log_attrs.get("resource_id"),
                        resource_type_id=log_attrs.get("resource_type_id"),
                        request_id=log_attrs.get("request_id"),
                        labels=log_attrs
                    )
                    records.append(record)
                    total_logs += 1

            # Create and add batch to correlator
            if records:
                batch = LogBatch(resource=resource_info, records=records)
                await correlation_engine.add_logs(batch)

        LOG_RECORDS_RECEIVED.labels(source="otlp").inc(total_logs)

        logger.info("otlp_logs_ingested", count=total_logs)

        return {"status": "accepted", "count": total_logs}
    except Exception as e:
        logger.exception("Failed to ingest OTLP logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest OTLP logs: {str(e)}")


@router.post("/traces", status_code=202)
@profile_function(tags={"endpoint": "otlp_traces", "operation": "ingest"})
async def ingest_otlp_traces(
    request: Request,
    authenticated: bool = Depends(verify_basic_auth),
):
    """
    Ingest OTLP traces (supports both JSON and protobuf)

    Accepts OTLP format traces and adds them to correlation windows.
    Caches trace data in Redis for deduplication and fast lookups.
    """
    correlation_engine = request.app.state.correlation_engine
    TRACES_RECEIVED = request.app.state.TRACES_RECEIVED
    telemetry_cache = getattr(request.app.state, "telemetry_cache", None)

    if not correlation_engine:
        raise HTTPException(status_code=503, detail="Correlation engine not initialized")

    # Validate request size
    await validate_request_size(request)

    try:
        content_type = request.headers.get("content-type", "")

        # Handle protobuf format
        if "application/x-protobuf" in content_type:
            body = await request.body()

            # Additional size check
            if len(body) > settings.max_protobuf_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Protobuf payload too large: {len(body)} bytes"
                )

            try:
                traces_data = TracesData()
                traces_data.ParseFromString(body)
                data = MessageToDict(traces_data, preserving_proto_field_name=True)
            except DecodeError as e:
                logger.error("Invalid protobuf format", error=str(e))
                raise HTTPException(status_code=400, detail=f"Invalid protobuf format: {str(e)}")
            except Exception as e:
                logger.error("Failed to parse protobuf", error=str(e))
                raise HTTPException(status_code=400, detail=f"Failed to parse protobuf: {str(e)}")
        else:
            # Handle JSON format with size check
            body = await request.body()
            if len(body) > settings.max_json_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"JSON payload too large: {len(body)} bytes"
                )

            import json
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON format", error=str(e))
                raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

        # Extract resource spans
        resource_spans = data.get("resourceSpans", [])

        total_spans = 0
        cached_spans = 0

        # Cache traces in Redis if available
        if telemetry_cache:
            for resource_span in resource_spans:
                # Extract resource attributes for service name
                resource = resource_span.get("resource", {})
                resource_attrs = {}
                for attr in resource.get("attributes", []):
                    key = attr.get("key", "")
                    value = attr.get("value", {})
                    if "stringValue" in value:
                        resource_attrs[key] = value["stringValue"]

                service_name = resource_attrs.get("service.name", "unknown")

                scope_spans = resource_span.get("scopeSpans", [])
                for scope_span in scope_spans:
                    spans = scope_span.get("spans", [])
                    total_spans += len(spans)

                    for span in spans:
                        # Extract trace ID
                        trace_id = span.get("traceId", "")
                        if isinstance(trace_id, bytes):
                            trace_id = trace_id.hex()
                        elif not trace_id:
                            continue  # Skip spans without trace_id

                        # Extract span details
                        span_name = span.get("name", "")
                        status_code = span.get("status", {}).get("code", 0)
                        status = "error" if status_code == 2 else "ok"

                        # Calculate duration
                        start_time_ns = int(span.get("startTimeUnixNano", 0))
                        end_time_ns = int(span.get("endTimeUnixNano", 0))
                        duration_ms = (end_time_ns - start_time_ns) // 1_000_000 if end_time_ns > start_time_ns else 0

                        # Extract custom attributes
                        correlation_id = ""
                        resource_id = ""
                        for attr in span.get("attributes", []):
                            key = attr.get("key", "")
                            value = attr.get("value", {})
                            if key == "circuit_id" and "stringValue" in value:
                                correlation_id = value["stringValue"]
                            elif key == "resource_id" and "stringValue" in value:
                                resource_id = value["stringValue"]

                        # Cache trace in Redis
                        try:
                            from app.redis_schema import TraceIndex
                            trace_index = TraceIndex(
                                trace_id=trace_id,
                                service=service_name,
                                status=status,
                                duration_ms=duration_ms,
                                resource_id=resource_id or trace_id,
                                correlation_id=correlation_id or trace_id,
                            )
                            await telemetry_cache.store_trace(trace_index)
                            cached_spans += 1
                        except Exception as e:
                            logger.warning("Failed to cache trace", trace_id=trace_id, error=str(e))
        else:
            # No cache - just count spans
            for resource_span in resource_spans:
                scope_spans = resource_span.get("scopeSpans", [])
                for scope_span in scope_spans:
                    spans = scope_span.get("spans", [])
                    total_spans += len(spans)

        # Forward traces to correlation engine for processing
        await correlation_engine.add_traces(data)

        TRACES_RECEIVED.labels(source="otlp").inc(total_spans)

        logger.info(
            "otlp_traces_ingested",
            span_count=total_spans,
            cached_count=cached_spans if telemetry_cache else None
        )

        return {"status": "accepted", "span_count": total_spans, "cached": cached_spans}
    except Exception as e:
        logger.exception("Failed to ingest OTLP traces", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to ingest OTLP traces: {str(e)}")