"""Integration tests for correlation pipeline"""
import pytest
import asyncio
from datetime import datetime, timezone

from app.pipeline.correlator import CorrelationEngine, CorrelationWindow
from app.models import LogBatch, LogRecord, ResourceInfo
from unittest.mock import AsyncMock


@pytest.fixture
def mock_exporter_manager():
    """Mock ExporterManager"""
    manager = AsyncMock()
    manager.export_logs = AsyncMock()
    manager.export_traces = AsyncMock()
    manager.export_correlation_span = AsyncMock()
    manager.close = AsyncMock()
    return manager


@pytest.fixture
async def correlation_engine(mock_exporter_manager):
    """Create and start CorrelationEngine"""
    engine = CorrelationEngine(
        window_seconds=2,  # Short window for testing
        exporter_manager=mock_exporter_manager
    )
    return engine


class TestEndToEndCorrelation:
    """Test end-to-end correlation flow"""

    @pytest.mark.asyncio
    async def test_logs_and_traces_correlation(self, correlation_engine, mock_exporter_manager):
        """Logs and traces with same trace_id should be correlated"""
        trace_id = "test-trace-123"

        # Add logs
        log_batch = LogBatch(
            resource=ResourceInfo(
                service="test-service",
                host="test-host",
                env="dev"
            ),
            records=[
                LogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="INFO",
                    message="Test log 1",
                    trace_id=trace_id
                ),
                LogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="ERROR",
                    message="Test log 2",
                    trace_id=trace_id
                )
            ]
        )

        # Add traces
        trace_batch = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "test-service"}},
                        {"key": "deployment.environment", "value": {"stringValue": "dev"}}
                    ]
                },
                "scopeSpans": [{
                    "spans": [
                        {
                            "traceId": trace_id,
                            "spanId": "span-1",
                            "name": "test-operation",
                            "startTimeUnixNano": "1699971234000000000",
                            "attributes": []
                        }
                    ]
                }]
            }]
        }

        # Process logs and traces
        await correlation_engine.add_logs(log_batch)
        await correlation_engine.add_traces(trace_batch)

        # Process one iteration
        await asyncio.sleep(0.1)

        # Verify exports were called
        assert mock_exporter_manager.export_logs.called
        assert mock_exporter_manager.export_traces.called

    @pytest.mark.asyncio
    async def test_multiple_services_correlation(self, correlation_engine, mock_exporter_manager):
        """Different services with same trace_id should be correlated"""
        trace_id = "multi-service-trace"

        # Service 1 logs
        log_batch_1 = LogBatch(
            resource=ResourceInfo(service="service-1", host="host-1", env="dev"),
            records=[
                LogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="INFO",
                    message="Service 1 log",
                    trace_id=trace_id
                )
            ]
        )

        # Service 2 logs
        log_batch_2 = LogBatch(
            resource=ResourceInfo(service="service-2", host="host-2", env="dev"),
            records=[
                LogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="INFO",
                    message="Service 2 log",
                    trace_id=trace_id
                )
            ]
        )

        await correlation_engine.add_logs(log_batch_1)
        await correlation_engine.add_logs(log_batch_2)

        # Both should be processed
        await asyncio.sleep(0.1)

        assert mock_exporter_manager.export_logs.call_count == 2


class TestCorrelationWindow:
    """Test correlation window behavior"""

    def test_window_creates_correlations(self):
        """Window should create correlations for matching trace_ids"""
        window = CorrelationWindow(window_seconds=60)

        # Add logs and traces with same trace_id
        trace_id = "window-test-trace"

        window.add_log({
            "trace_id": trace_id,
            "service": "test-service",
            "env": "dev",
            "message": "Test log"
        })

        window.add_trace({
            "trace_id": trace_id,
            "service": "test-service",
            "env": "dev",
            "name": "test-span"
        })

        # Create correlations
        correlations = window.create_correlations()

        # Should create one correlation
        assert len(correlations) == 1
        assert correlations[0].trace_id == trace_id
        assert correlations[0].log_count == 1
        assert correlations[0].span_count == 1

    def test_window_close_timing(self):
        """Window should close after specified duration"""
        window = CorrelationWindow(window_seconds=0.1)

        # Window should not close immediately
        assert not window.should_close()

        # Wait for window duration
        import time
        time.sleep(0.15)

        # Window should close
        assert window.should_close()

    def test_multiple_trace_ids_in_window(self):
        """Window should handle multiple different trace_ids"""
        window = CorrelationWindow(window_seconds=60)

        # Add multiple trace_ids
        for i in range(5):
            window.add_log({
                "trace_id": f"trace-{i}",
                "service": "test-service",
                "env": "dev"
            })

        correlations = window.create_correlations()

        # Should create 5 correlations
        assert len(correlations) == 5


class TestQueryCorrelations:
    """Test correlation querying"""

    def test_query_by_trace_id(self, correlation_engine):
        """Should be able to query correlations by trace_id"""
        from app.models import CorrelationEvent
        import uuid

        # Add correlations
        trace_id = "query-test-trace"
        correlation = CorrelationEvent(
            correlation_id=str(uuid.uuid4()),
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc),
            service="test-service",
            env="dev",
            log_count=1,
            span_count=1
        )

        correlation_engine._add_to_correlation_history(correlation)

        # Query
        results = correlation_engine.query_correlations(trace_id=trace_id)

        assert len(results) == 1
        assert results[0].trace_id == trace_id

    def test_query_by_service(self, correlation_engine):
        """Should be able to query correlations by service"""
        from app.models import CorrelationEvent
        import uuid

        # Add correlations for different services
        for i in range(3):
            correlation = CorrelationEvent(
                correlation_id=str(uuid.uuid4()),
                trace_id=f"trace-{i}",
                timestamp=datetime.now(timezone.utc),
                service="test-service" if i < 2 else "other-service",
                env="dev",
                log_count=1,
                span_count=1
            )
            correlation_engine._add_to_correlation_history(correlation)

        # Query for specific service
        results = correlation_engine.query_correlations(service="test-service")

        assert len(results) == 2
        assert all(r.service == "test-service" for r in results)

    def test_query_with_limit(self, correlation_engine):
        """Should respect limit parameter"""
        from app.models import CorrelationEvent
        import uuid

        # Add many correlations
        for i in range(10):
            correlation = CorrelationEvent(
                correlation_id=str(uuid.uuid4()),
                trace_id=f"trace-{i}",
                timestamp=datetime.now(timezone.utc),
                service="test-service",
                env="dev",
                log_count=1,
                span_count=1
            )
            correlation_engine._add_to_correlation_history(correlation)

        # Query with limit
        results = correlation_engine.query_correlations(limit=5)

        assert len(results) == 5


class TestExporterIntegration:
    """Test exporter integration"""

    @pytest.mark.asyncio
    async def test_logs_exported_immediately(self, correlation_engine, mock_exporter_manager):
        """Logs should be exported immediately upon ingestion"""
        log_batch = LogBatch(
            resource=ResourceInfo(service="test", host="test-host", env="dev"),
            records=[
                LogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="INFO",
                    message="Test",
                    trace_id="test-trace"
                )
            ]
        )

        # Start engine
        engine_task = asyncio.create_task(correlation_engine.run())

        # Add logs
        await correlation_engine.add_logs(log_batch)

        # Wait briefly for processing
        await asyncio.sleep(0.2)

        # Stop engine
        correlation_engine.stop()
        engine_task.cancel()

        try:
            await engine_task
        except asyncio.CancelledError:
            pass

        # Verify export was called
        assert mock_exporter_manager.export_logs.called

    @pytest.mark.asyncio
    async def test_correlation_spans_exported(self, correlation_engine, mock_exporter_manager):
        """Correlation spans should be exported when window closes"""
        # Start engine
        engine_task = asyncio.create_task(correlation_engine.run())

        # Add logs with trace_id
        log_batch = LogBatch(
            resource=ResourceInfo(service="test", host="test-host", env="dev"),
            records=[
                LogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="INFO",
                    message="Test",
                    trace_id="correlation-test-trace"
                )
            ]
        )

        await correlation_engine.add_logs(log_batch)

        # Wait for window to close (2 seconds in fixture)
        await asyncio.sleep(2.5)

        # Stop engine
        correlation_engine.stop()
        engine_task.cancel()

        try:
            await engine_task
        except asyncio.CancelledError:
            pass

        # Verify correlation span was exported
        assert mock_exporter_manager.export_correlation_span.called
