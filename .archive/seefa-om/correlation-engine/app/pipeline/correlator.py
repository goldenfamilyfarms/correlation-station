"""Correlation Engine - Core windowed correlation logic"""
import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import structlog

from app.models import (
    LogBatch,
    CorrelationEvent,
    SyntheticEvent,
)
from app.pipeline.normalizer import LogNormalizer
from app.pipeline.exporters import ExporterManager
from app.correlation.trace_synthesizer import TraceSynthesizer, TraceSegment
from app.correlation.link_resolver import LinkResolver, TraceLink
from app.config import settings
from prometheus_client import Counter, Gauge

# Metrics
CORRELATION_EVENTS = Counter(
    'correlation_events_total',
    'Total correlation events created',
    ['status']
)
QUEUE_DEPTH = Gauge(
    'correlation_queue_depth',
    'Current queue depth',
    ['queue_type']
)
TRACE_SYNTHESIS = Counter(
    'trace_synthesis_total',
    'Trace synthesis operations',
    ['status']
)

logger = structlog.get_logger()


class CorrelationWindow:
    """Sliding window for correlation"""
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.logs_by_trace: Dict[str, List[dict]] = defaultdict(list)
        self.traces_by_trace: Dict[str, List[dict]] = defaultdict(list)
        self.window_start = datetime.now(timezone.utc)

    def add_log(self, log_record: dict):
        """Add a log record to the window"""
        trace_id = log_record.get("trace_id")
        if trace_id:
            self.logs_by_trace[trace_id].append(log_record)

    def add_trace(self, trace_record: dict):
        """Add a trace record to the window"""
        trace_id = trace_record.get("trace_id")
        if trace_id:
            self.traces_by_trace[trace_id].append(trace_record)

    def should_close(self) -> bool:
        """Check if window should close"""
        elapsed = (datetime.now(timezone.utc) - self.window_start).total_seconds()
        return elapsed >= self.window_seconds

    def create_correlations(self) -> List[CorrelationEvent]:
        """Create correlation events for all trace_ids in window"""
        correlations = []

        # Find all trace_ids that have both logs and traces
        all_trace_ids = set(self.logs_by_trace.keys()) | set(self.traces_by_trace.keys())

        for trace_id in all_trace_ids:
            logs = self.logs_by_trace.get(trace_id, [])
            traces = self.traces_by_trace.get(trace_id, [])

            if logs or traces:
                # Extract common attributes
                service = "unknown"
                env = "dev"
                circuit_id = None
                product_id = None
                resource_id = None
                resource_type_id = None
                request_id = None

                # Get service from first log or trace
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
    """Main correlation engine with windowed correlation"""
    def __init__(self, window_seconds: int, exporter_manager: ExporterManager):
        self.window_seconds = window_seconds
        self.exporter_manager = exporter_manager
        self.normalizer = LogNormalizer()

        self.current_window = CorrelationWindow(window_seconds)
        self.correlation_history: List[CorrelationEvent] = []
        self.max_history = settings.max_correlation_history

        # Performance optimization: Index correlation history for faster queries
        self.correlation_index: Dict[str, List[CorrelationEvent]] = {
            "by_trace_id": defaultdict(list),
            "by_service": defaultdict(list),
        }

        # Advanced correlation features
        self.trace_synthesizer = None
        self.link_resolver = None
        if settings.enable_trace_synthesis:
            self.trace_synthesizer = TraceSynthesizer(
                correlation_window_seconds=settings.trace_synthesis_window_seconds
            )
            self.link_resolver = LinkResolver(retention_hours=24)
            logger.info("Trace synthesis enabled", window=settings.trace_synthesis_window_seconds)

        self.running = False
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.max_queue_size)
        self.trace_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.max_queue_size)

    async def add_logs(self, batch: LogBatch):
        """Add log batch to processing queue"""
        try:
            await self.log_queue.put(batch)
        except asyncio.QueueFull:
            logger.warning("Log queue full, dropping batch", service=batch.resource.service)

    async def add_traces(self, trace_batch: dict):
        """Add trace batch to processing queue"""
        try:
            await self.trace_queue.put(trace_batch)
        except asyncio.QueueFull:
            logger.warning("Trace queue full, dropping batch")

    def query_correlations(
        self,
        trace_id: Optional[str] = None,
        service: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[CorrelationEvent]:
        """Query correlation history with optimized indexing"""
        results = []

        # Use index for faster lookup when possible
        if trace_id:
            candidates = self.correlation_index["by_trace_id"].get(trace_id, [])
        elif service:
            candidates = self.correlation_index["by_service"].get(service, [])
        else:
            candidates = self.correlation_history

        for correlation in reversed(candidates):
            # Apply filters
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
        """Add correlation to history and update indices"""
        self.correlation_history.append(correlation)

        # Update indices
        self.correlation_index["by_trace_id"][correlation.trace_id].append(correlation)
        self.correlation_index["by_service"][correlation.service].append(correlation)

        # Trim history if needed
        if len(self.correlation_history) > self.max_history:
            # Remove oldest
            removed = self.correlation_history.pop(0)
            # Remove from indices
            self.correlation_index["by_trace_id"][removed.trace_id].remove(removed)
            self.correlation_index["by_service"][removed.service].remove(removed)

    async def inject_synthetic_event(self, event: SyntheticEvent) -> CorrelationEvent:
        """Inject a synthetic correlation event"""
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

        # Export synthetic span to Tempo
        await self.exporter_manager.export_correlation_span(correlation)

        return correlation

    def _normalize_trace(self, trace_batch: dict) -> List[dict]:
        """Normalize OTLP trace batch to internal format"""
        normalized = []

        for resource_span in trace_batch.get("resourceSpans", []):
            resource = resource_span.get("resource", {})
            attributes = {attr["key"]: attr.get("value", {}) for attr in resource.get("attributes", [])}

            service = attributes.get("service.name", {}).get("stringValue", "unknown")
            env = attributes.get("deployment.environment", {}).get("stringValue", "dev")

            for scope_span in resource_span.get("scopeSpans", []):
                for span in scope_span.get("spans", []):
                    # Extract span attributes
                    span_attrs = {attr["key"]: attr.get("value", {}) for attr in span.get("attributes", [])}

                    trace_id = span.get("traceId", "")
                    if isinstance(trace_id, bytes):
                        trace_id = trace_id.hex()

                    span_id = span.get("spanId", "")
                    if isinstance(span_id, bytes):
                        span_id = span_id.hex()

                    # Extract correlation keys
                    circuit_id = span_attrs.get("circuit_id", {}).get("stringValue")
                    product_id = span_attrs.get("product_id", {}).get("stringValue")
                    resource_id = span_attrs.get("resource_id", {}).get("stringValue")
                    resource_type_id = span_attrs.get("resource_type_id", {}).get("stringValue")

                    normalized.append({
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "service": service,
                        "env": env,
                        "name": span.get("name", ""),
                        "circuit_id": circuit_id,
                        "product_id": product_id,
                        "resource_id": resource_id,
                        "resource_type_id": resource_type_id,
                        "timestamp": datetime.fromtimestamp(
                            int(span.get("startTimeUnixNano", 0)) / 1e9, tz=timezone.utc
                        ).isoformat() if span.get("startTimeUnixNano") else datetime.now(timezone.utc).isoformat(),
                    })

        return normalized

    async def run(self):
        """Main correlation loop"""
        self.running = True
        logger.info("Correlation engine started", window_seconds=self.window_seconds)

        while self.running:
            try:
                # Update queue depth metrics
                QUEUE_DEPTH.labels(queue_type="logs").set(self.log_queue.qsize())
                QUEUE_DEPTH.labels(queue_type="traces").set(self.trace_queue.qsize())

                # Process logs from queue
                while not self.log_queue.empty():
                    try:
                        batch = await asyncio.wait_for(self.log_queue.get(), timeout=0.1)

                        # Normalize and add to window
                        normalized_logs = self.normalizer.normalize_log_batch(batch)
                        for log in normalized_logs:
                            self.current_window.add_log(log)

                        # Export logs to Loki immediately
                        await self.exporter_manager.export_logs(batch)
                    except asyncio.TimeoutError:
                        break

                # Process traces from queue
                while not self.trace_queue.empty():
                    try:
                        trace_batch = await asyncio.wait_for(self.trace_queue.get(), timeout=0.1)

                        # Normalize traces and add to window
                        normalized_traces = self._normalize_trace(trace_batch)
                        for trace in normalized_traces:
                            self.current_window.add_trace(trace)

                            # Add to trace synthesizer if enabled
                            if self.trace_synthesizer and trace.get("circuit_id"):
                                segment = TraceSegment(
                                    trace_id=trace["trace_id"],
                                    span_id=trace["span_id"],
                                    service=trace["service"],
                                    timestamp=trace["timestamp"],
                                    circuit_id=trace.get("circuit_id"),
                                    resource_id=trace.get("resource_id"),
                                    product_id=trace.get("product_id"),
                                    resource_type_id=trace.get("resource_type_id"),
                                    operation=trace.get("name"),
                                )
                                self.trace_synthesizer.add_segment(segment)

                        # Export traces to Tempo immediately
                        await self.exporter_manager.export_traces(trace_batch)
                    except asyncio.TimeoutError:
                        break

                # Perform trace synthesis if enabled
                if self.trace_synthesizer and self.link_resolver:
                    await self._perform_trace_synthesis()

                # Check if window should close
                if self.current_window.should_close():
                    # Create correlations
                    correlations = self.current_window.create_correlations()

                    logger.info(
                        "correlation_window_closed",
                        correlations=len(correlations),
                        window_seconds=self.window_seconds,
                    )

                    # Add to history with indexing
                    for correlation in correlations:
                        self._add_to_correlation_history(correlation)

                    # Track metrics
                    CORRELATION_EVENTS.labels(status="success").inc(len(correlations))

                    # Export correlation spans to Tempo
                    for correlation in correlations:
                        await self.exporter_manager.export_correlation_span(correlation)

                    # Create new window
                    self.current_window = CorrelationWindow(self.window_seconds)

                # Sleep briefly
                await asyncio.sleep(1)
            except Exception as e:
                logger.exception("Error in correlation loop", error=str(e))
                await asyncio.sleep(5)

    async def _perform_trace_synthesis(self):
        """Perform trace synthesis to link disconnected traces"""
        if not self.trace_synthesizer or not self.link_resolver:
            return

        # Get all segments from the synthesizer
        for segment in self.trace_synthesizer.segments[-100:]:  # Process last 100 segments
            # Try to find parent trace
            parent_match = self.trace_synthesizer.find_parent_trace(segment)

            if parent_match:
                parent_segment, confidence = parent_match

                if confidence >= settings.correlation_confidence_threshold:
                    # Create bridge span
                    bridge_span = self.trace_synthesizer.create_bridge_span(
                        parent_segment, segment, confidence
                    )

                    # Export bridge span to Tempo
                    await self.exporter_manager.export_bridge_span(bridge_span)

                    # Add trace link
                    link = TraceLink(
                        parent_trace_id=parent_segment.trace_id,
                        child_trace_id=segment.trace_id,
                        link_type="synthetic",
                        timestamp=datetime.now(timezone.utc),
                        circuit_id=segment.circuit_id,
                        confidence=confidence,
                    )
                    self.link_resolver.add_link(link)

                    TRACE_SYNTHESIS.labels(status="success").inc()
                    logger.debug(
                        "trace_synthesis_complete",
                        parent=parent_segment.service,
                        child=segment.service,
                        confidence=confidence,
                    )

    def stop(self):
        """Stop the correlation engine"""
        self.running = False
        logger.info("Correlation engine stopping")