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

# Exporter metrics
EXPORT_ATTEMPTS = Counter(
    'export_attempts_total',
    'Total export attempts',
    ['backend', 'status']
)
EXPORT_DURATION = Histogram(
    'export_duration_seconds',
    'Export duration',
    ['backend']
)
EXPORT_RETRIES = Counter(
    'export_retries_total',
    'Total export retries',
    ['backend']
)
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['backend']
)


class CircuitBreaker:
    """Simple circuit breaker pattern"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if recovery timeout elapsed
            if self.last_failure_time and datetime.now() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker half-open, testing connection")
                return True
            return False

        # half-open state - allow single request
        return True

    def record_success(self):
        """Record successful execution"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker closed, connection recovered")

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state != "open":
                self.state = "open"
                logger.warning(
                    "Circuit breaker open, too many failures",
                    failures=self.failure_count,
                    recovery_timeout=self.recovery_timeout.total_seconds()
                )

    def get_state_code(self) -> int:
        """Get state as numeric code for metrics"""
        return {"closed": 0, "open": 1, "half-open": 2}.get(self.state, 0)


async def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0, backend: str = "unknown"):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            delay = initial_delay * (2 ** attempt)
            EXPORT_RETRIES.labels(backend=backend).inc()
            logger.warning(
                f"Export failed, retrying in {delay}s",
                backend=backend,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )
            await asyncio.sleep(delay)


class LokiExporter:
    """Export logs to Loki"""
    def __init__(self, loki_url: str):
        self.loki_url = loki_url
        self.client = httpx.AsyncClient(timeout=settings.export_timeout)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout
        ) if settings.enable_circuit_breaker else None

    async def export_logs(self, batch: LogBatch):
        """Export log batch to Loki with retry and circuit breaker"""
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            EXPORT_ATTEMPTS.labels(backend="loki", status="circuit_open").inc()
            logger.warning("Loki export skipped, circuit breaker open")
            return

        start_time = time.time()

        async def _export():
            # Convert to Loki streams format
            streams = self._convert_to_loki_streams(batch)

            # Send to Loki
            response = await self.client.post(
                self.loki_url,
                json={"streams": streams},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        try:
            await retry_with_backoff(
                _export,
                max_retries=settings.export_retry_attempts,
                initial_delay=settings.export_retry_delay,
                backend="loki"
            )

            EXPORT_ATTEMPTS.labels(backend="loki", status="success").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
                CIRCUIT_BREAKER_STATE.labels(backend="loki").set(self.circuit_breaker.get_state_code())
            logger.debug("Logs exported to Loki", service=batch.resource.service, count=len(batch.records))
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="loki", status="error").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
                CIRCUIT_BREAKER_STATE.labels(backend="loki").set(self.circuit_breaker.get_state_code())
            logger.error("Failed to export logs to Loki", error=str(e), service=batch.resource.service)
        finally:
            EXPORT_DURATION.labels(backend="loki").observe(time.time() - start_time)

    def _convert_to_loki_streams(self, batch: LogBatch) -> List[Dict[str, Any]]:
        """Convert log batch to Loki streams format"""
        streams_dict = {}

        for record in batch.records:
            labels = self._create_labels(batch.resource, record)
            label_str = self._labels_to_string(labels)
            log_line = self._create_log_line(batch.resource, record)

            if label_str not in streams_dict:
                streams_dict[label_str] = {"stream": labels, "values": []}

            timestamp_ns = self._to_nanoseconds(record.timestamp)
            streams_dict[label_str]["values"].append([str(timestamp_ns), json.dumps(log_line)])

        return list(streams_dict.values())

    def _create_labels(self, resource, record) -> Dict[str, str]:
        """Create low-cardinality labels for Loki"""
        labels = {"service": resource.service, "env": resource.env}
        if record.trace_id:
            labels["trace_id"] = record.trace_id
        return labels

    def _create_log_line(self, resource, record) -> Dict[str, Any]:
        """Create log line with all fields as JSON"""
        log_line = {
            "timestamp": record.timestamp,
            "severity": record.severity,
            "message": record.message,
            "host": resource.host,
        }
        
        optional_fields = {
            "span_id": record.span_id,
            "circuit_id": record.circuit_id,
            "product_id": record.product_id,
            "resource_id": record.resource_id,
            "resource_type_id": record.resource_type_id,
            "request_id": record.request_id,
            "labels": record.labels,
        }
        
        log_line.update({k: v for k, v in optional_fields.items() if v})
        return log_line

    def _labels_to_string(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to Loki label string"""
        parts = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(parts) + "}"

    def _to_nanoseconds(self, timestamp_str: str) -> int:
        """Convert ISO timestamp to nanoseconds"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1e9)
        except Exception:
            # Fallback to current time
            return int(time.time() * 1e9)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class TempoExporter:
    """Export traces to Tempo"""
    def __init__(self, tempo_http_endpoint: str):
        self.tempo_http_endpoint = tempo_http_endpoint
        self.client = httpx.AsyncClient(timeout=settings.export_timeout)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout
        ) if settings.enable_circuit_breaker else None

    async def export_correlation_span(self, correlation: CorrelationEvent):
        """Export a synthetic correlation span to Tempo"""
        start_time = time.time()

        try:
            # Create OTLP trace with correlation span
            otlp_trace = self._create_otlp_trace(correlation)

            # Send to Tempo (OTLP HTTP endpoint)
            response = await self.client.post(
                f"{self.tempo_http_endpoint}/v1/traces",
                json=otlp_trace,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            EXPORT_ATTEMPTS.labels(backend="tempo", status="success").inc()
            logger.debug("Correlation span exported to Tempo", correlation_id=correlation.correlation_id)
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="tempo", status="error").inc()
            logger.error("Failed to export correlation span to Tempo", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="tempo").observe(time.time() - start_time)

    def _validate_trace_id(self, trace_id: str) -> str:
        """Validate and normalize trace ID"""
        if not trace_id:
            raise ValueError("trace_id cannot be empty")

        # Remove any whitespace
        trace_id = trace_id.strip()

        # Validate hex format
        try:
            int(trace_id, 16)
        except ValueError:
            raise ValueError(f"trace_id must be hexadecimal: {trace_id}")

        # Normalize length (OTLP expects 32 hex chars for 128-bit trace ID)
        if len(trace_id) > 32:
            # Truncate to 32 chars
            trace_id = trace_id[:32]
            logger.warning("Truncating trace_id to 32 chars", original_length=len(trace_id))
        elif len(trace_id) < 32:
            # Pad with zeros
            trace_id = trace_id.ljust(32, '0')

        return trace_id

    def _create_otlp_trace(self, correlation: CorrelationEvent) -> Dict[str, Any]:
        """Create OTLP trace format for correlation span"""
        # Validate and convert trace_id to proper format
        try:
            trace_id_bytes = self._validate_trace_id(correlation.trace_id)
        except ValueError as e:
            logger.error("Invalid trace_id in correlation", error=str(e), correlation_id=correlation.correlation_id)
            # Use correlation_id as fallback trace_id
            trace_id_bytes = correlation.correlation_id.replace('-', '')[:32].ljust(32, '0')

        span_id_bytes = correlation.correlation_id.replace('-', '')[:16].ljust(16, '0')

        # Create span attributes
        attributes = [
            {"key": "correlation.id", "value": {"stringValue": correlation.correlation_id}},
            {"key": "correlation.log_count", "value": {"intValue": str(correlation.log_count)}},
            {"key": "correlation.span_count", "value": {"intValue": str(correlation.span_count)}},
            {"key": "service.name", "value": {"stringValue": correlation.service}},
            {"key": "deployment.environment", "value": {"stringValue": correlation.env}},
        ]

        # Add custom attributes if present
        if correlation.circuit_id:
            attributes.append({"key": "circuit_id", "value": {"stringValue": correlation.circuit_id}})
        if correlation.product_id:
            attributes.append({"key": "product_id", "value": {"stringValue": correlation.product_id}})
        if correlation.resource_id:
            attributes.append({"key": "resource_id", "value": {"stringValue": correlation.resource_id}})
        if correlation.resource_type_id:
            attributes.append({"key": "resource_type_id", "value": {"stringValue": correlation.resource_type_id}})
        if correlation.request_id:
            attributes.append({"key": "request_id", "value": {"stringValue": correlation.request_id}})

        # Create OTLP structure
        span_start_ns = int(correlation.timestamp.timestamp() * 1e9)
        span_end_ns = span_start_ns + 1000000  # 1ms duration

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "correlation-engine"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "correlation-engine"}},
                        {"key": "telemetry.sdk.language", "value": {"stringValue": "python"}},
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "correlation-engine",
                        "version": "1.0.0"
                    },
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
        """Export OTLP traces to Tempo"""
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            EXPORT_ATTEMPTS.labels(backend="tempo", status="circuit_open").inc()
            logger.warning("Tempo export skipped, circuit breaker open")
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
            await retry_with_backoff(
                _export,
                max_retries=settings.export_retry_attempts,
                initial_delay=settings.export_retry_delay,
                backend="tempo"
            )

            EXPORT_ATTEMPTS.labels(backend="tempo", status="success").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
                CIRCUIT_BREAKER_STATE.labels(backend="tempo").set(self.circuit_breaker.get_state_code())
            logger.debug("Traces exported to Tempo")
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="tempo", status="error").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
                CIRCUIT_BREAKER_STATE.labels(backend="tempo").set(self.circuit_breaker.get_state_code())
            logger.error("Failed to export traces to Tempo", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="tempo").observe(time.time() - start_time)

    async def export_bridge_span(self, bridge_span: Dict[str, Any]):
        """Export synthetic bridge span to Tempo"""
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            EXPORT_ATTEMPTS.labels(backend="tempo", status="circuit_open").inc()
            logger.warning("Tempo bridge span export skipped, circuit breaker open")
            return

        start_time = time.time()

        async def _export():
            # Convert bridge span dict to OTLP format
            otlp_trace = self._bridge_span_to_otlp(bridge_span)

            response = await self.client.post(
                f"{self.tempo_http_endpoint}/v1/traces",
                json=otlp_trace,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        try:
            await retry_with_backoff(
                _export,
                max_retries=settings.export_retry_attempts,
                initial_delay=settings.export_retry_delay,
                backend="tempo"
            )

            EXPORT_ATTEMPTS.labels(backend="tempo", status="success").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
                CIRCUIT_BREAKER_STATE.labels(backend="tempo").set(self.circuit_breaker.get_state_code())
            logger.debug("Bridge span exported to Tempo", span=bridge_span.get("name"))
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="tempo", status="error").inc()
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
                CIRCUIT_BREAKER_STATE.labels(backend="tempo").set(self.circuit_breaker.get_state_code())
            logger.error("Failed to export bridge span to Tempo", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="tempo").observe(time.time() - start_time)

    def _bridge_span_to_otlp(self, bridge_span: Dict[str, Any]) -> Dict[str, Any]:
        """Convert bridge span dict to OTLP format"""
        # Convert attributes to OTLP format
        attributes = []
        for key, value in bridge_span.get("attributes", {}).items():
            attr = {"key": key, "value": {}}
            if isinstance(value, bool):
                attr["value"]["boolValue"] = value
            elif isinstance(value, int):
                attr["value"]["intValue"] = str(value)
            elif isinstance(value, float):
                attr["value"]["doubleValue"] = value
            else:
                attr["value"]["stringValue"] = str(value)
            attributes.append(attr)

        # Convert links to OTLP format
        links = []
        for link in bridge_span.get("links", []):
            link_attrs = []
            for key, value in link.get("attributes", {}).items():
                link_attrs.append({
                    "key": key,
                    "value": {"stringValue": str(value)}
                })

            links.append({
                "traceId": link["trace_id"],
                "spanId": link["span_id"],
                "attributes": link_attrs
            })

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "correlation-station"}},
                        {"key": "span.type", "value": {"stringValue": "synthetic"}},
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "trace-synthesizer",
                        "version": "1.0.0"
                    },
                    "spans": [{
                        "traceId": bridge_span["trace_id"],
                        "spanId": bridge_span["span_id"],
                        "parentSpanId": bridge_span.get("parent_span_id", ""),
                        "name": bridge_span.get("name", "synthetic_bridge"),
                        "kind": bridge_span.get("kind", 3),
                        "startTimeUnixNano": str(bridge_span["start_time_unix_nano"]),
                        "endTimeUnixNano": str(bridge_span["end_time_unix_nano"]),
                        "attributes": attributes,
                        "links": links,
                        "status": bridge_span.get("status", {"code": 1})
                    }]
                }]
            }]
        }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class DatadogExporter:
    """Export to Datadog (optional dual-write)"""
    def __init__(self, api_key: Optional[str], site: str = "datadoghq.com"):
        self.api_key = api_key
        self.site = site
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = httpx.AsyncClient(timeout=10.0)
            logger.info("Datadog exporter enabled", site=site)
        else:
            logger.info("Datadog exporter disabled (no API key)")

    async def export_logs(self, batch: LogBatch):
        """Export logs to Datadog"""
        if not self.enabled:
            return

        start_time = time.time()

        try:
            # Convert to Datadog log format
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

            # Send to Datadog
            response = await self.client.post(
                f"https://http-intake.logs.{self.site}/v1/input",
                json=dd_logs,
                headers={
                    "Content-Type": "application/json",
                    "DD-API-KEY": self.api_key or "",
                },
            )
            response.raise_for_status()

            EXPORT_ATTEMPTS.labels(backend="datadog", status="success").inc()
            logger.debug("Logs exported to Datadog", count=len(dd_logs))
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="datadog", status="error").inc()
            logger.error("Failed to export logs to Datadog", error=str(e))
        finally:
            EXPORT_DURATION.labels(backend="datadog").observe(time.time() - start_time)

    async def close(self):
        """Close HTTP client"""
        if self.enabled:
            await self.client.aclose()


class ExporterManager:
    """Manages all exporters"""
    def __init__(
        self,
        loki_url: str,
        tempo_grpc_endpoint: str,
        tempo_http_endpoint: str,
        datadog_api_key: Optional[str] = None,
        datadog_site: str = "datadoghq.com",
    ):
        self.loki = LokiExporter(loki_url)
        self.tempo = TempoExporter(tempo_http_endpoint)
        self.datadog = DatadogExporter(datadog_api_key, datadog_site)

    async def export_logs(self, batch: LogBatch):
        """Export logs to all configured backends"""
        # Export to Loki (primary)
        await self.loki.export_logs(batch)

        # Export to Datadog (optional)
        await self.datadog.export_logs(batch)

    async def export_traces(self, trace_batch: Dict[str, Any]):
        """Export traces to Tempo"""
        await self.tempo.export_traces(trace_batch)

    async def export_correlation_span(self, correlation: CorrelationEvent):
        """Export correlation span to Tempo"""
        await self.tempo.export_correlation_span(correlation)

    async def export_bridge_span(self, bridge_span: Dict[str, Any]):
        """Export synthetic bridge span to Tempo"""
        await self.tempo.export_bridge_span(bridge_span)

    async def close(self):
        """Close all exporters with proper error handling"""
        errors = []

        # Attempt to close all exporters even if some fail
        try:
            await self.loki.close()
        except Exception as e:
            errors.append(f"Loki close error: {e}")
            logger.error("Failed to close Loki exporter", error=str(e))

        try:
            await self.tempo.close()
        except Exception as e:
            errors.append(f"Tempo close error: {e}")
            logger.error("Failed to close Tempo exporter", error=str(e))

        try:
            await self.datadog.close()
        except Exception as e:
            errors.append(f"Datadog close error: {e}")
            logger.error("Failed to close Datadog exporter", error=str(e))

        if errors:
            logger.warning("Some exporters failed to close cleanly", errors=errors)
        else:
            logger.info("All exporters closed successfully")