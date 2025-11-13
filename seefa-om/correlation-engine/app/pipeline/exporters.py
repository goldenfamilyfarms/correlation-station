"""Exporters - send correlated data to backends (Loki/Tempo/Prometheus/Datadog)"""
import json
import time
from typing import Optional, List, Dict, Any
import httpx
import structlog
from prometheus_client import Counter, Histogram

from app.models import LogBatch, CorrelationEvent

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


class LokiExporter:
    """Export logs to Loki"""
    def __init__(self, loki_url: str):
        self.loki_url = loki_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def export_logs(self, batch: LogBatch):
        """Export log batch to Loki"""
        start_time = time.time()

        try:
            # Convert to Loki streams format
            streams = self._convert_to_loki_streams(batch)

            # Send to Loki
            response = await self.client.post(
                self.loki_url,
                json={"streams": streams},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            EXPORT_ATTEMPTS.labels(backend="loki", status="success").inc()
            logger.debug("Logs exported to Loki", service=batch.resource.service, count=len(batch.records))
        except Exception as e:
            EXPORT_ATTEMPTS.labels(backend="loki", status="error").inc()
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
        self.client = httpx.AsyncClient(timeout=10.0)

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

    def _create_otlp_trace(self, correlation: CorrelationEvent) -> Dict[str, Any]:
        """Create OTLP trace format for correlation span"""
        # Convert trace_id to proper format
        trace_id_bytes = correlation.trace_id.ljust(32, '0')[:32]  # Ensure 32 chars
        span_id_bytes = correlation.correlation_id[:16].ljust(16, '0')[:16]  # Use first 16 chars of correlation_id

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

    async def export_correlation_span(self, correlation: CorrelationEvent):
        """Export correlation span to Tempo"""
        await self.tempo.export_correlation_span(correlation)

    async def close(self):
        """Close all exporters"""
        await self.loki.close()
        await self.tempo.close()
        await self.datadog.close()