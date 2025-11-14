"""Correlation Engine - Core windowed correlation logic with MDSO support"""
import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import structlog

from app.models import LogBatch, CorrelationEvent, SyntheticEvent
from app.pipeline.normalizer import LogNormalizer
from app.pipeline.exporters import ExporterManager
from app.pipeline.mdso_correlator import MDSOCorrelator
from app.config import settings
from prometheus_client import Counter, Gauge

CORRELATION_EVENTS = Counter('correlation_events_total', 'Total correlation events created', ['status'])
QUEUE_DEPTH = Gauge('correlation_queue_depth', 'Current queue depth', ['queue_type'])

logger = structlog.get_logger()


class CorrelationWindow:
    """Sliding window for correlation"""
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.logs_by_trace: Dict[str, List[dict]] = defaultdict(list)
        self.traces_by_trace: Dict[str, List[dict]] = defaultdict(list)
        self.window_start = datetime.now(timezone.utc)

    def add_log(self, log_record: dict):
        trace_id = log_record.get("trace_id")
        if trace_id:
            self.logs_by_trace[trace_id].append(log_record)

    def add_trace(self, trace_record: dict):
        trace_id = trace_record.get("trace_id")
        if trace_id:
            self.traces_by_trace[trace_id].append(trace_record)

    def should_close(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.window_start).total_seconds()
        return elapsed >= self.window_seconds

    def create_correlations(self) -> List[CorrelationEvent]:
        correlations = []
        all_trace_ids = set(self.logs_by_trace.keys()) | set(self.traces_by_trace.keys())

        for trace_id in all_trace_ids:
            logs = self.logs_by_trace.get(trace_id, [])
            traces = self.traces_by_trace.get(trace_id, [])

            if logs or traces:
                service = "unknown"
                env = "dev"
                circuit_id = None
                product_id = None
                resource_id = None
                resource_type_id = None
                request_id = None

                if logs:
                    service = logs[0].get("service", "unknown")
                    env = logs[0].get("env", "dev")
                    circuit_id = logs[0].get("circuit_id")
                    product_id = logs[0].get("product_id")
                    resource_id = logs[0].get("resource_id")
                    resource_type_id = logs[0].get("resource_type_id")
                    request_id = logs[0].get("request_id")
                elif traces:
                    service = traces[0].get("service", "unknown")
                    env = traces[0].get("env", "dev")

                correlation = CorrelationEvent(
                    correlation_id=str(uuid.uuid4()),
                    trace_id=trace_id,
                    timestamp=datetime.now(timezone.utc),
                    service=service,
                    env=env,
                    log_count=len(logs),
                    span_count=len(traces),
                    circuit_id=circuit_id,
                    product_id=product_id,
                    resource_id=resource_id,
                    resource_type_id=resource_type_id,
                    request_id=request_id,
                    metadata={
                        "window_start": self.window_start.isoformat(),
                        "window_seconds": self.window_seconds,
                    }
                )
                correlations.append(correlation)

        return correlations


class CorrelationEngine:
    """Main correlation engine with windowed correlation and MDSO support"""
    def __init__(self, window_seconds: int, exporter_manager: ExporterManager):
        self.window_seconds = window_seconds
        self.exporter_manager = exporter_manager
        self.normalizer = LogNormalizer()
        self.mdso_correlator = MDSOCorrelator()

        self.current_window = CorrelationWindow(window_seconds)
        self.correlation_history: List[CorrelationEvent] = []
        self.max_history = settings.max_correlation_history

        self.correlation_index: Dict[str, List[CorrelationEvent]] = {
            "by_trace_id": defaultdict(list),
            "by_service": defaultdict(list),
        }

        self.running = False
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.max_queue_size)
        self.trace_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.max_queue_size)

    async def add_logs(self, batch: LogBatch):
        try:
            await self.log_queue.put(batch)
        except asyncio.QueueFull:
            logger.warning("Log queue full, dropping batch", service=batch.resource.service)

    async def add_traces(self, trace_batch: dict):
        try:
            await self.trace_queue.put(trace_batch)
        except asyncio.QueueFull:
            logger.warning("Trace queue full, dropping batch")

    def query_correlations(self, trace_id: Optional[str] = None, service: Optional[str] = None,
                          start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                          limit: int = 100) -> List[CorrelationEvent]:
        results = []

        if trace_id:
            candidates = self.correlation_index["by_trace_id"].get(trace_id, [])
        elif service:
            candidates = self.correlation_index["by_service"].get(service, [])
        else:
            candidates = self.correlation_history

        for correlation in reversed(candidates):
            if trace_id and correlation.trace_id != trace_id:
                continue
            if service and correlation.service != service:
                continue
            if start_time and correlation.timestamp < start_time:
                continue
            if end_time and correlation.timestamp > end_time:
                continue

            results.append(correlation)
            if len(results) >= limit:
                break

        return results

    def _add_to_correlation_history(self, correlation: CorrelationEvent):
        self.correlation_history.append(correlation)
        self.correlation_index["by_trace_id"][correlation.trace_id].append(correlation)
        self.correlation_index["by_service"][correlation.service].append(correlation)

        if len(self.correlation_history) > self.max_history:
            removed = self.correlation_history.pop(0)
            self.correlation_index["by_trace_id"][removed.trace_id].remove(removed)
            self.correlation_index["by_service"][removed.service].remove(removed)

    async def inject_synthetic_event(self, event: SyntheticEvent) -> CorrelationEvent:
        correlation = CorrelationEvent(
            correlation_id=str(uuid.uuid4()),
            trace_id=event.trace_id,
            timestamp=datetime.now(timezone.utc),
            service=event.service,
            env="dev",
            log_count=1,
            span_count=0,
            metadata={
                "synthetic": True,
                "message": event.message,
                "severity": event.severity,
                **(event.attributes or {}),
            }
        )

        self._add_to_correlation_history(correlation)
        CORRELATION_EVENTS.labels(status="synthetic").inc()
        await self.exporter_manager.export_correlation_span(correlation)

        return correlation

    def _normalize_trace(self, trace_batch: dict) -> List[dict]:
        normalized = []

        for resource_span in trace_batch.get("resourceSpans", []):
            resource = resource_span.get("resource", {})
            attributes = {attr["key"]: attr.get("value", {}) for attr in resource.get("attributes", [])}

            service = attributes.get("service.name", {}).get("stringValue", "unknown")
            env = attributes.get("deployment.environment", {}).get("stringValue", "dev")

            for scope_span in resource_span.get("scopeSpans", []):
                for span in scope_span.get("spans", []):
                    span_attrs = {attr["key"]: attr.get("value", {}) for attr in span.get("attributes", [])}

                    trace_id = span.get("traceId", "")
                    if isinstance(trace_id, bytes):
                        trace_id = trace_id.hex()

                    span_id = span.get("spanId", "")
                    if isinstance(span_id, bytes):
                        span_id = span_id.hex()

                    normalized.append({
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "service": service,
                        "env": env,
                        "name": span.get("name", ""),
                        "circuit_id": span_attrs.get("circuit_id", {}).get("stringValue"),
                        "product_id": span_attrs.get("product_id", {}).get("stringValue"),
                        "resource_id": span_attrs.get("resource_id", {}).get("stringValue"),
                        "resource_type_id": span_attrs.get("resource_type_id", {}).get("stringValue"),
                        "timestamp": datetime.fromtimestamp(
                            int(span.get("startTimeUnixNano", 0)) / 1e9, tz=timezone.utc
                        ).isoformat() if span.get("startTimeUnixNano") else datetime.now(timezone.utc).isoformat(),
                    })

        return normalized

    async def run(self):
        self.running = True
        logger.info("Correlation engine started", window_seconds=self.window_seconds)

        while self.running:
            try:
                QUEUE_DEPTH.labels(queue_type="logs").set(self.log_queue.qsize())
                QUEUE_DEPTH.labels(queue_type="traces").set(self.trace_queue.qsize())

                while not self.log_queue.empty():
                    try:
                        batch = await asyncio.wait_for(self.log_queue.get(), timeout=0.1)
                        normalized_logs = self.normalizer.normalize_log_batch(batch)
                        for log in normalized_logs:
                            self.current_window.add_log(log)
                        await self.exporter_manager.export_logs(batch)
                    except asyncio.TimeoutError:
                        break

                while not self.trace_queue.empty():
                    try:
                        trace_batch = await asyncio.wait_for(self.trace_queue.get(), timeout=0.1)
                        normalized_traces = self._normalize_trace(trace_batch)
                        for trace in normalized_traces:
                            self.current_window.add_trace(trace)
                        await self.exporter_manager.export_traces(trace_batch)
                    except asyncio.TimeoutError:
                        break

                if self.current_window.should_close():
                    correlations = self.current_window.create_correlations()

                    logger.info("correlation_window_closed", correlations=len(correlations),
                               window_seconds=self.window_seconds)

                    for correlation in correlations:
                        self._add_to_correlation_history(correlation)

                    CORRELATION_EVENTS.labels(status="success").inc(len(correlations))

                    for correlation in correlations:
                        await self.exporter_manager.export_correlation_span(correlation)

                    self.current_window = CorrelationWindow(self.window_seconds)

                await asyncio.sleep(1)
            except Exception as e:
                logger.exception("Error in correlation loop", error=str(e))
                await asyncio.sleep(5)

    def stop(self):
        self.running = False
        logger.info("Correlation engine stopping")
