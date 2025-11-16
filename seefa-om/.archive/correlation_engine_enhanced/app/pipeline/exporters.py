"""Exporters - send correlated data to backends (Loki/Tempo/Prometheus/Datadog)"""
import json
import time
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import structlog
from prometheus_client import Counter, Histogram, Gauge

from app.models import LogBatch, CorrelationEvent
from app.config import settings

logger = structlog.get_logger()

EXPORT_ATTEMPTS = Counter('export_attempts_total', 'Total export attempts', ['backend', 'status'])
EXPORT_DURATION = Histogram('export_duration_seconds', 'Export duration', ['backend'])
EXPORT_RETRIES = Counter('export_retries_total', 'Total export retries', ['backend'])
CIRCUIT_BREAKER_STATE = Gauge('circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open, 2=half-open)', ['backend'])


class CircuitBreaker:
    """Simple circuit breaker pattern"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and datetime.now() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        return True

    def record_success(self):
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold and self.state != "open":
            self.state = "open"

    def get_state_code(self) -> int:
        return {"closed": 0, "open": 1, "half-open": 2}.get(self.state, 0)


async def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0, backend: str = "unknown"):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            EXPORT_RETRIES.labels(backend=backend).inc()
            await asyncio.sleep(delay)


class LokiExporter:
    """Export logs to Loki"""
    def __init__(self, loki_url: str):
        self.loki_url = loki_url
        self.client = httpx.AsyncClient(timeout=settings.export_timeout)
        self.circuit_breaker = CircuitBreaker() if settings.enable_circuit_breaker else None

    async def export_logs(self, batch: LogBatch):
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            EXPORT_ATTEMPTS.labels(backend="loki", status="circuit_open").inc()
            return

        start_time = time.time()

        async def _export():
            streams = self._convert_to_loki_streams(batch)
            response = await self.client.post(
                self.loki_url,
                json={"streams": streams},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        try:
            await retry_with_backoff(_export, max_retries=settings.export_retry_attempts, backend="loki")
            EXPORT_ATTEMPTS.labels(backend="loki", status="success").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
                CIRCUIT_BREAKER_STATE.labels(backend="loki").set(self.circuit_breaker.get_state_code())
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="loki", status="error").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
                CIRCUIT_BREAKER_STATE.labels(backend="loki").set(self.circuit_breaker.get_state_code())
            logger.error("Failed to export logs to Loki", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="loki").observe(time.time() - start_time)

    def _convert_to_loki_streams(self, batch: LogBatch) -> List[Dict[str, Any]]:
        streams_dict = {}
        for record in batch.records:
            labels = {"service": batch.resource.service, "env": batch.resource.env}
            if record.trace_id:
                labels["trace_id"] = record.trace_id
            label_str = "{" + ",".join([f'{k}="{v}"' for k, v in sorted(labels.items())]) + "}"
            
            log_line = {
                "timestamp": record.timestamp,
                "severity": record.severity,
                "message": record.message,
                "host": batch.resource.host,
            }
            for attr in ['span_id', 'circuit_id', 'product_id', 'resource_id', 'resource_type_id', 'request_id', 'labels']:
                if val := getattr(record, attr, None):
                    log_line[attr] = val

            if label_str not in streams_dict:
                streams_dict[label_str] = {"stream": labels, "values": []}

            timestamp_ns = int(datetime.fromisoformat(record.timestamp.replace('Z', '+00:00')).timestamp() * 1e9)
            streams_dict[label_str]["values"].append([str(timestamp_ns), json.dumps(log_line)])

        return list(streams_dict.values())

    async def close(self):
        await self.client.aclose()


class TempoExporter:
    """Export traces to Tempo"""
    def __init__(self, tempo_http_endpoint: str):
        self.tempo_http_endpoint = tempo_http_endpoint
        self.client = httpx.AsyncClient(timeout=settings.export_timeout)
        self.circuit_breaker = CircuitBreaker() if settings.enable_circuit_breaker else None

    async def export_correlation_span(self, correlation: CorrelationEvent):
        start_time = time.time()
        try:
            otlp_trace = self._create_otlp_trace(correlation)
            response = await self.client.post(
                f"{self.tempo_http_endpoint}/v1/traces",
                json=otlp_trace,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            EXPORT_ATTEMPTS.labels(backend="tempo", status="success").inc()
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="tempo", status="error").inc()
            logger.error("Failed to export correlation span to Tempo", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="tempo").observe(time.time() - start_time)

    def _create_otlp_trace(self, correlation: CorrelationEvent) -> Dict[str, Any]:
        trace_id_bytes = correlation.trace_id.ljust(32, '0')[:32]
        span_id_bytes = correlation.correlation_id[:16].ljust(16, '0')[:16]

        attributes = [
            {"key": "correlation.id", "value": {"stringValue": correlation.correlation_id}},
            {"key": "correlation.log_count", "value": {"intValue": str(correlation.log_count)}},
            {"key": "correlation.span_count", "value": {"intValue": str(correlation.span_count)}},
            {"key": "service.name", "value": {"stringValue": correlation.service}},
            {"key": "deployment.environment", "value": {"stringValue": correlation.env}},
        ]

        for attr in ['circuit_id', 'product_id', 'resource_id', 'resource_type_id', 'request_id']:
            if val := getattr(correlation, attr, None):
                attributes.append({"key": attr, "value": {"stringValue": val}})

        span_start_ns = int(correlation.timestamp.timestamp() * 1e9)
        span_end_ns = span_start_ns + 1000000

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "correlation-engine"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "correlation-engine"}},
                    ]
                },
                "scopeSpans": [{
                    "scope": {"name": "correlation-engine", "version": "2.0.0"},
                    "spans": [{
                        "traceId": trace_id_bytes,
                        "spanId": span_id_bytes,
                        "name": f"correlation.{correlation.service}",
                        "kind": "SPAN_KIND_INTERNAL",
                        "startTimeUnixNano": str(span_start_ns),
                        "endTimeUnixNano": str(span_end_ns),
                        "attributes": attributes,
                        "status": {"code": "STATUS_CODE_OK"}
                    }]
                }]
            }]
        }

    async def export_traces(self, trace_batch: Dict[str, Any]):
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            EXPORT_ATTEMPTS.labels(backend="tempo", status="circuit_open").inc()
            return

        start_time = time.time()

        async def _export():
            response = await self.client.post(
                f"{self.tempo_http_endpoint}/v1/traces",
                json=trace_batch,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        try:
            await retry_with_backoff(_export, max_retries=settings.export_retry_attempts, backend="tempo")
            EXPORT_ATTEMPTS.labels(backend="tempo", status="success").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="tempo", status="error").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            logger.error("Failed to export traces to Tempo", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="tempo").observe(time.time() - start_time)

    async def close(self):
        await self.client.aclose()


class DatadogExporter:
    """Export to Datadog (optional dual-write)"""
    def __init__(self, api_key: Optional[str], site: str = "datadoghq.com"):
        self.api_key = api_key
        self.site = site
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = httpx.AsyncClient(timeout=10.0)

    async def export_logs(self, batch: LogBatch):
        if not self.enabled:
            return

        start_time = time.time()
        try:
            dd_logs = []
            for record in batch.records:
                dd_log = {
                    "ddsource": "correlation-engine",
                    "ddtags": f"service:{batch.resource.service},env:{batch.resource.env}",
                    "hostname": batch.resource.host,
                    "message": record.message,
                    "timestamp": record.timestamp,
                    "status": record.severity.lower(),
                }
                if record.trace_id:
                    dd_log["dd.trace_id"] = record.trace_id
                if record.span_id:
                    dd_log["dd.span_id"] = record.span_id
                dd_logs.append(dd_log)

            response = await self.client.post(
                f"https://http-intake.logs.{self.site}/v1/input",
                json=dd_logs,
                headers={"Content-Type": "application/json", "DD-API-KEY": self.api_key or ""},
            )
            response.raise_for_status()
            EXPORT_ATTEMPTS.labels(backend="datadog", status="success").inc()
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="datadog", status="error").inc()
            logger.error("Failed to export logs to Datadog", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="datadog").observe(time.time() - start_time)

    async def close(self):
        if self.enabled:
            await self.client.aclose()


class ExporterManager:
    """Manages all exporters"""
    def __init__(self, loki_url: str, tempo_grpc_endpoint: str, tempo_http_endpoint: str,
                 datadog_api_key: Optional[str] = None, datadog_site: str = "datadoghq.com"):
        self.loki = LokiExporter(loki_url)
        self.tempo = TempoExporter(tempo_http_endpoint)
        self.datadog = DatadogExporter(datadog_api_key, datadog_site)

    async def export_logs(self, batch: LogBatch):
        await self.loki.export_logs(batch)
        await self.datadog.export_logs(batch)

    async def export_traces(self, trace_batch: Dict[str, Any]):
        await self.tempo.export_traces(trace_batch)

    async def export_correlation_span(self, correlation: CorrelationEvent):
        await self.tempo.export_correlation_span(correlation)

    async def close(self):
        await self.loki.close()
        await self.tempo.close()
        await self.datadog.close()
