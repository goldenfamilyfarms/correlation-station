"""Tests for queue backpressure and retry logic"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.correlator import CorrelationEngine, DROPPED_BATCHES, QUEUE_FULL_RETRIES
from app.models import LogBatch, LogRecord, ResourceInfo
from app.config import settings


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
def correlation_engine(mock_exporter_manager):
    """Create CorrelationEngine instance"""
    return CorrelationEngine(
        window_seconds=60,
        exporter_manager=mock_exporter_manager
    )


@pytest.fixture
def sample_log_batch():
    """Create sample log batch for testing"""
    return LogBatch(
        resource=ResourceInfo(
            service="test-service",
            host="test-host",
            env="dev"
        ),
        records=[
            LogRecord(
                timestamp="2025-11-14T10:00:00Z",
                severity="INFO",
                message="Test log message",
                trace_id="abc123"
            )
        ]
    )


class TestQueueBackpressure:
    """Test queue backpressure and retry logic"""

    @pytest.mark.asyncio
    async def test_successful_enqueue_no_retry(self, correlation_engine, sample_log_batch):
        """Successfully enqueuing should not trigger retries"""
        initial_retries = QUEUE_FULL_RETRIES.labels(type="logs")._value._value

        await correlation_engine.add_logs(sample_log_batch)

        # Verify batch was added
        assert correlation_engine.log_queue.qsize() == 1

        # Verify no retries were triggered
        current_retries = QUEUE_FULL_RETRIES.labels(type="logs")._value._value
        assert current_retries == initial_retries

    @pytest.mark.asyncio
    async def test_retry_on_queue_full(self, correlation_engine, sample_log_batch):
        """Should retry when queue is full"""
        # Fill the queue
        for _ in range(settings.max_queue_size):
            try:
                correlation_engine.log_queue.put_nowait(sample_log_batch)
            except asyncio.QueueFull:
                break

        # Verify queue is full
        assert correlation_engine.log_queue.full()

        # Attempt to add (should trigger retries then drop)
        initial_retries = QUEUE_FULL_RETRIES.labels(type="logs")._value._value
        initial_drops = DROPPED_BATCHES.labels(type="logs")._value._value

        await correlation_engine.add_logs(sample_log_batch)

        # Verify retries were attempted
        current_retries = QUEUE_FULL_RETRIES.labels(type="logs")._value._value
        assert current_retries > initial_retries

        # Verify batch was eventually dropped
        current_drops = DROPPED_BATCHES.labels(type="logs")._value._value
        assert current_drops == initial_drops + 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, correlation_engine, sample_log_batch):
        """Should use exponential backoff between retries"""
        # Fill the queue
        for _ in range(settings.max_queue_size):
            try:
                correlation_engine.log_queue.put_nowait(sample_log_batch)
            except asyncio.QueueFull:
                break

        start_time = asyncio.get_event_loop().time()
        await correlation_engine.add_logs(sample_log_batch)
        end_time = asyncio.get_event_loop().time()

        # With 3 retries and 0.1s base delay, total should be:
        # 0.1 + 0.2 + 0.4 = 0.7s minimum
        elapsed = end_time - start_time
        assert elapsed >= 0.6  # Allow some margin

    @pytest.mark.asyncio
    async def test_dropped_batch_metric_incremented(self, correlation_engine, sample_log_batch):
        """DROPPED_BATCHES metric should increment on drop"""
        # Fill the queue
        for _ in range(settings.max_queue_size):
            try:
                correlation_engine.log_queue.put_nowait(sample_log_batch)
            except asyncio.QueueFull:
                break

        initial_drops = DROPPED_BATCHES.labels(type="logs")._value._value

        await correlation_engine.add_logs(sample_log_batch)

        current_drops = DROPPED_BATCHES.labels(type="logs")._value._value
        assert current_drops == initial_drops + 1

    @pytest.mark.asyncio
    async def test_trace_queue_backpressure(self, correlation_engine):
        """Trace queue should also have backpressure"""
        # Fill the trace queue
        for _ in range(settings.max_queue_size):
            try:
                correlation_engine.trace_queue.put_nowait({"test": "data"})
            except asyncio.QueueFull:
                break

        initial_drops = DROPPED_BATCHES.labels(type="traces")._value._value

        await correlation_engine.add_traces({"test": "data"})

        current_drops = DROPPED_BATCHES.labels(type="traces")._value._value
        assert current_drops == initial_drops + 1

    @pytest.mark.asyncio
    async def test_error_logging_on_drop(self, correlation_engine, sample_log_batch, caplog):
        """Should log ERROR when dropping batch"""
        # Fill the queue
        for _ in range(settings.max_queue_size):
            try:
                correlation_engine.log_queue.put_nowait(sample_log_batch)
            except asyncio.QueueFull:
                break

        import logging
        caplog.set_level(logging.ERROR)

        await correlation_engine.add_logs(sample_log_batch)

        # Verify error was logged
        assert "Log queue full after retries" in caplog.text
        assert "dropping batch" in caplog.text
        assert "recommendation" in caplog.text.lower()


class TestQueueConfiguration:
    """Test queue configuration"""

    def test_configurable_retry_attempts(self, mock_exporter_manager):
        """Retry attempts should be configurable"""
        # This is tested via settings.queue_retry_attempts
        assert settings.queue_retry_attempts >= 0

    def test_configurable_retry_delay(self, mock_exporter_manager):
        """Retry delay should be configurable"""
        # This is tested via settings.queue_retry_delay
        assert settings.queue_retry_delay > 0

    def test_configurable_queue_size(self, mock_exporter_manager):
        """Queue size should be configurable"""
        assert settings.max_queue_size > 0
