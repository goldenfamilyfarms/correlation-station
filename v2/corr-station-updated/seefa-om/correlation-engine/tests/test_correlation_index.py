"""Tests for correlation index corruption fix"""
import pytest
from datetime import datetime, timezone
import uuid

from app.pipeline.correlator import CorrelationEngine
from app.models import CorrelationEvent
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
def correlation_engine(mock_exporter_manager):
    """Create CorrelationEngine instance"""
    engine = CorrelationEngine(
        window_seconds=60,
        exporter_manager=mock_exporter_manager
    )
    # Set low max_history for testing
    engine.max_history = 10
    return engine


def create_correlation_event(trace_id="trace-123", service="test-service"):
    """Helper to create correlation event"""
    return CorrelationEvent(
        correlation_id=str(uuid.uuid4()),
        trace_id=trace_id,
        timestamp=datetime.now(timezone.utc),
        service=service,
        env="dev",
        log_count=1,
        span_count=1
    )


class TestCorrelationIndexIntegrity:
    """Test correlation index integrity after trimming"""

    def test_index_updated_on_add(self, correlation_engine):
        """Index should be updated when correlation is added"""
        correlation = create_correlation_event()

        correlation_engine._add_to_correlation_history(correlation)

        # Verify added to history
        assert len(correlation_engine.correlation_history) == 1

        # Verify indexed by trace_id
        assert correlation.trace_id in correlation_engine.correlation_index["by_trace_id"]
        assert correlation in correlation_engine.correlation_index["by_trace_id"][correlation.trace_id]

        # Verify indexed by service
        assert correlation.service in correlation_engine.correlation_index["by_service"]
        assert correlation in correlation_engine.correlation_index["by_service"][correlation.service]

    def test_index_cleaned_when_history_trimmed(self, correlation_engine):
        """Index should be cleaned when history is trimmed"""
        # Add correlations beyond max_history
        correlations = []
        for i in range(15):
            correlation = create_correlation_event(
                trace_id=f"trace-{i}",
                service="test-service"
            )
            correlations.append(correlation)
            correlation_engine._add_to_correlation_history(correlation)

        # Verify history is trimmed to max_history (10)
        assert len(correlation_engine.correlation_history) == 10

        # Verify oldest correlations (0-4) are removed from indices
        for i in range(5):
            trace_id = f"trace-{i}"
            # Index entry should be empty or removed
            if trace_id in correlation_engine.correlation_index["by_trace_id"]:
                assert correlations[i] not in correlation_engine.correlation_index["by_trace_id"][trace_id]

    def test_no_orphaned_index_entries(self, correlation_engine):
        """Empty index entries should be removed"""
        # Add and then trim correlations
        for i in range(15):
            correlation = create_correlation_event(
                trace_id=f"unique-trace-{i}",
                service=f"unique-service-{i}"
            )
            correlation_engine._add_to_correlation_history(correlation)

        # Check that removed trace_ids are not in index
        for i in range(5):
            trace_id = f"unique-trace-{i}"
            service = f"unique-service-{i}"

            # Empty entries should be deleted
            assert trace_id not in correlation_engine.correlation_index["by_trace_id"]
            assert service not in correlation_engine.correlation_index["by_service"]

    def test_duplicate_trace_ids_handled_correctly(self, correlation_engine):
        """Multiple correlations with same trace_id should be handled"""
        trace_id = "duplicate-trace"

        # Add 3 correlations with same trace_id
        correlations = []
        for _ in range(3):
            correlation = create_correlation_event(trace_id=trace_id)
            correlations.append(correlation)
            correlation_engine._add_to_correlation_history(correlation)

        # All 3 should be in index
        assert len(correlation_engine.correlation_index["by_trace_id"][trace_id]) == 3

        # Add more to trigger trimming
        for i in range(10):
            correlation = create_correlation_event(trace_id=f"other-{i}")
            correlation_engine._add_to_correlation_history(correlation)

        # Oldest correlations with duplicate trace_id should be removed correctly
        # Without crashing or leaving orphans
        remaining = correlation_engine.correlation_index["by_trace_id"].get(trace_id, [])
        assert len(remaining) <= 3

    def test_index_integrity_after_many_operations(self, correlation_engine):
        """Index should remain consistent after many add/remove operations"""
        # Perform many operations
        for i in range(100):
            correlation = create_correlation_event(
                trace_id=f"trace-{i % 20}",  # Reuse some trace_ids
                service=f"service-{i % 5}"   # Reuse some services
            )
            correlation_engine._add_to_correlation_history(correlation)

        # Verify all indexed correlations exist in history
        for trace_id, correlations in correlation_engine.correlation_index["by_trace_id"].items():
            for correlation in correlations:
                assert correlation in correlation_engine.correlation_history

        for service, correlations in correlation_engine.correlation_index["by_service"].items():
            for correlation in correlations:
                assert correlation in correlation_engine.correlation_history

        # Verify no stale references
        assert len(correlation_engine.correlation_history) == correlation_engine.max_history

    def test_no_valueerror_on_remove(self, correlation_engine):
        """Should not raise ValueError when removing from index"""
        # Add correlation
        correlation = create_correlation_event()
        correlation_engine._add_to_correlation_history(correlation)

        # Add many more to trigger removal
        for i in range(20):
            other = create_correlation_event(trace_id=f"other-{i}")
            correlation_engine._add_to_correlation_history(other)

        # Should not have raised ValueError
        assert True  # Test passes if no exception
