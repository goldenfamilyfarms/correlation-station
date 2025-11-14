#!/usr/bin/env python3
"""
Correlation Engine API
Ingests OTLP-JSON telemetry (traces, logs, metrics) and performs correlation analysis
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("correlation-engine")

# Configuration
API_PORT = int(os.getenv('CORRELATION_API_PORT', '8080'))
AUTH_TOKEN = os.getenv('CORRELATION_API_AUTH_TOKEN', 'dev-secret-token-change-me')

# In-memory storage (replace with DB for production)
trace_store: Dict[str, List[Dict]] = defaultdict(list)
log_store: Dict[str, List[Dict]] = defaultdict(list)
metric_store: Dict[str, List[Dict]] = defaultdict(list)
correlation_stats = {
    'traces_received': 0,
    'logs_received': 0,
    'metrics_received': 0,
    'correlations_found': 0,
    'last_ingest': None
}

app = FastAPI(
    title="Correlation Engine API",
    description="Ingests and correlates OTLP telemetry data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


class OTLPPayload(BaseModel):
    """OTLP JSON payload structure"""
    resourceSpans: Optional[List[Dict]] = None
    resourceLogs: Optional[List[Dict]] = None
    resourceMetrics: Optional[List[Dict]] = None


def verify_auth(authorization: Optional[str] = None) -> bool:
    """Verify bearer token"""
    if not authorization:
        return False

    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            return False
        return token == AUTH_TOKEN
    except:
        return False


def extract_trace_id(span: Dict) -> Optional[str]:
    """Extract trace ID from span"""
    return span.get('traceId') or span.get('trace_id')


def extract_span_id(span: Dict) -> Optional[str]:
    """Extract span ID from span"""
    return span.get('spanId') or span.get('span_id')


def extract_attributes(item: Dict) -> Dict[str, Any]:
    """Extract attributes from OTLP item"""
    attrs = {}
    attributes = item.get('attributes', [])

    for attr in attributes:
        key = attr.get('key')
        value = attr.get('value', {})

        # Extract typed value
        if 'stringValue' in value:
            attrs[key] = value['stringValue']
        elif 'intValue' in value:
            attrs[key] = value['intValue']
        elif 'doubleValue' in value:
            attrs[key] = value['doubleValue']
        elif 'boolValue' in value:
            attrs[key] = value['boolValue']

    return attrs


def process_traces(resource_spans: List[Dict]) -> Dict:
    """Process trace spans and store for correlation"""
    traces_count = 0
    trace_ids = set()

    for resource_span in resource_spans:
        scope_spans = resource_span.get('scopeSpans', [])

        for scope_span in scope_spans:
            spans = scope_span.get('spans', [])

            for span in spans:
                trace_id = extract_trace_id(span)
                span_id = extract_span_id(span)

                if trace_id:
                    trace_ids.add(trace_id)

                    # Store span with metadata
                    trace_store[trace_id].append({
                        'span_id': span_id,
                        'name': span.get('name'),
                        'start_time': span.get('startTimeUnixNano'),
                        'end_time': span.get('endTimeUnixNano'),
                        'attributes': extract_attributes(span),
                        'status': span.get('status', {}),
                        'ingested_at': datetime.utcnow().isoformat()
                    })
                    traces_count += 1

    logger.info(f"Processed {traces_count} spans across {len(trace_ids)} traces")
    return {
        'traces_count': traces_count,
        'unique_traces': len(trace_ids),
        'trace_ids': list(trace_ids)
    }


def process_logs(resource_logs: List[Dict]) -> Dict:
    """Process log records and correlate with traces"""
    logs_count = 0
    correlated_count = 0

    for resource_log in resource_logs:
        scope_logs = resource_log.get('scopeLogs', [])

        for scope_log in scope_logs:
            log_records = scope_log.get('logRecords', [])

            for log_record in log_records:
                logs_count += 1

                # Extract trace context
                trace_id = None
                span_id = None
                attrs = extract_attributes(log_record)

                # Look for trace_id in attributes
                trace_id = (
                    attrs.get('trace_id') or
                    log_record.get('traceId') or
                    log_record.get('trace_id')
                )
                span_id = (
                    attrs.get('span_id') or
                    log_record.get('spanId') or
                    log_record.get('span_id')
                )

                # Store log with trace correlation
                log_entry = {
                    'timestamp': log_record.get('timeUnixNano'),
                    'body': log_record.get('body', {}),
                    'severity': log_record.get('severityText'),
                    'attributes': attrs,
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'ingested_at': datetime.utcnow().isoformat()
                }

                if trace_id:
                    log_store[trace_id].append(log_entry)
                    correlated_count += 1
                else:
                    log_store['uncorrelated'].append(log_entry)

    logger.info(f"Processed {logs_count} logs, {correlated_count} correlated with traces")
    return {
        'logs_count': logs_count,
        'correlated': correlated_count,
        'uncorrelated': logs_count - correlated_count
    }


def process_metrics(resource_metrics: List[Dict]) -> Dict:
    """Process metrics"""
    metrics_count = 0

    for resource_metric in resource_metrics:
        scope_metrics = resource_metric.get('scopeMetrics', [])

        for scope_metric in scope_metrics:
            metrics = scope_metric.get('metrics', [])
            metrics_count += len(metrics)

            for metric in metrics:
                metric_name = metric.get('name')
                if metric_name:
                    metric_store[metric_name].append({
                        'description': metric.get('description'),
                        'unit': metric.get('unit'),
                        'data': metric.get('gauge') or metric.get('sum') or metric.get('histogram'),
                        'ingested_at': datetime.utcnow().isoformat()
                    })

    logger.info(f"Processed {metrics_count} metrics")
    return {'metrics_count': metrics_count}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Correlation Engine API",
        "status": "healthy",
        "version": "1.0.0",
        "stats": correlation_stats
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": correlation_stats,
        "storage": {
            "traces": len(trace_store),
            "logs": len(log_store),
            "metrics": len(metric_store)
        }
    }


@app.post("/ingest")
async def ingest_telemetry(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Ingest OTLP-JSON telemetry data

    Accepts resourceSpans, resourceLogs, and resourceMetrics in OTLP JSON format
    """
    # Verify authentication
    if not verify_auth(authorization):
        logger.warning("Unauthorized ingest attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Parse JSON body
        body = await request.json()

        # Process each signal type
        results = {}

        if 'resourceSpans' in body:
            results['traces'] = process_traces(body['resourceSpans'])
            correlation_stats['traces_received'] += results['traces']['traces_count']

        if 'resourceLogs' in body:
            results['logs'] = process_logs(body['resourceLogs'])
            correlation_stats['logs_received'] += results['logs']['logs_count']
            correlation_stats['correlations_found'] += results['logs']['correlated']

        if 'resourceMetrics' in body:
            results['metrics'] = process_metrics(body['resourceMetrics'])
            correlation_stats['metrics_received'] += results['metrics']['metrics_count']

        correlation_stats['last_ingest'] = datetime.utcnow().isoformat()

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "results": results,
                "message": "Telemetry ingested successfully"
            }
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/correlations/{trace_id}")
async def get_correlations(trace_id: str):
    """
    Get all correlated data for a specific trace ID
    """
    if trace_id not in trace_store:
        raise HTTPException(status_code=404, detail="Trace ID not found")

    return {
        "trace_id": trace_id,
        "spans": trace_store.get(trace_id, []),
        "logs": log_store.get(trace_id, []),
        "span_count": len(trace_store.get(trace_id, [])),
        "log_count": len(log_store.get(trace_id, []))
    }


@app.get("/stats")
async def get_stats():
    """Get ingestion statistics"""
    return {
        "stats": correlation_stats,
        "storage": {
            "unique_traces": len(trace_store),
            "trace_groups": len(log_store),
            "metric_types": len(metric_store)
        }
    }


if __name__ == "__main__":
    logger.info(f"Starting Correlation Engine API on port {API_PORT}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info",
        access_log=True
    )