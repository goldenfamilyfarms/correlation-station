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
from prometheus_client import Counter

# Define metric here to avoid circular import
CORRELATION_EVENTS = Counter(
    'correlation_events_total',
    'Total correlation events created',
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
        self.max_history = 10000

        self.running = False
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.trace_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

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
        """Query correlation history"""
        results = []

        for correlation in reversed(self.correlation_history):
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

        self.correlation_history.append(correlation)
        CORRELATION_EVENTS.labels(status="synthetic").inc()

        # Export synthetic span to Tempo
        await self.exporter_manager.export_correlation_span(correlation)

        return correlation

    async def run(self):
        """Main correlation loop"""
        self.running = True
        logger.info("Correlation engine started", window_seconds=self.window_seconds)

        while self.running:
            try:
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
                        # TODO: Normalize traces and add to window
                        # For now, just pass through to Tempo
                    except asyncio.TimeoutError:
                        break

                # Check if window should close
                if self.current_window.should_close():
                    # Create correlations
                    correlations = self.current_window.create_correlations()

                    logger.info(
                        "correlation_window_closed",
                        correlations=len(correlations),
                        window_seconds=self.window_seconds,
                    )

                    # Add to history
                    self.correlation_history.extend(correlations)
                    if len(self.correlation_history) > self.max_history:
                        self.correlation_history = self.correlation_history[-self.max_history:]

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

    def stop(self):
        """Stop the correlation engine"""
        self.running = False
        logger.info("Correlation engine stopping")