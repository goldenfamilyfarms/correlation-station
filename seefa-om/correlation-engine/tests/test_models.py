"""Tests for Pydantic data models"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models import (
    LogRecord,
    ResourceInfo,
    LogBatch,
    Correlation,
    CorrelationQuery,
    HealthStatus,
    CorrelationEvent,
    SyntheticEvent,
)


class TestLogRecord:
    """Test LogRecord model"""

    def test_log_record_minimal(self):
        """LogRecord should work with minimal fields"""
        record = LogRecord(
            timestamp="2025-10-15T10:30:45.123Z",
            message="Test message"
        )

        assert record.timestamp == "2025-10-15T10:30:45.123Z"
        assert record.message == "Test message"
        assert record.severity == "INFO"  # Default
        assert record.trace_id is None
        assert record.labels == {}

    def test_log_record_full(self):
        """LogRecord should work with all fields"""
        record = LogRecord(
            timestamp="2025-10-15T10:30:45.123Z",
            severity="ERROR",
            message="Error occurred",
            trace_id="1234567890abcdef1234567890abcdef",
            span_id="1234567890abcdef",
            circuit_id="CIRCUIT-123",
            product_id="PROD-456",
            resource_id="RES-789",
            resource_type_id="TYPE-001",
            request_id="REQ-111",
            labels={"env": "prod", "version": "1.0"}
        )

        assert record.severity == "ERROR"
        assert record.trace_id == "1234567890abcdef1234567890abcdef"
        assert record.circuit_id == "CIRCUIT-123"
        assert record.labels["env"] == "prod"

    def test_log_record_requires_timestamp(self):
        """LogRecord should require timestamp"""
        with pytest.raises(ValidationError):
            LogRecord(message="Test")

    def test_log_record_requires_message(self):
        """LogRecord should require message"""
        with pytest.raises(ValidationError):
            LogRecord(timestamp="2025-10-15T10:30:45.123Z")


class TestResourceInfo:
    """Test ResourceInfo model"""

    def test_resource_info_valid(self):
        """ResourceInfo should validate with all fields"""
        resource = ResourceInfo(
            service="test-service",
            host="test-host",
            env="production"
        )

        assert resource.service == "test-service"
        assert resource.host == "test-host"
        assert resource.env == "production"

    def test_resource_info_requires_all_fields(self):
        """ResourceInfo should require all fields"""
        with pytest.raises(ValidationError):
            ResourceInfo(service="test", host="host")  # Missing env

        with pytest.raises(ValidationError):
            ResourceInfo(service="test", env="prod")  # Missing host


class TestLogBatch:
    """Test LogBatch model"""

    def test_log_batch_valid(self):
        """LogBatch should validate with resource and records"""
        batch = LogBatch(
            resource=ResourceInfo(service="test", host="host1", env="dev"),
            records=[
                LogRecord(timestamp="2025-10-15T10:30:45Z", message="Log 1"),
                LogRecord(timestamp="2025-10-15T10:30:46Z", message="Log 2"),
            ]
        )

        assert batch.resource.service == "test"
        assert len(batch.records) == 2

    def test_log_batch_empty_records(self):
        """LogBatch should allow empty records list"""
        batch = LogBatch(
            resource=ResourceInfo(service="test", host="host1", env="dev"),
            records=[]
        )

        assert len(batch.records) == 0


class TestCorrelation:
    """Test Correlation model"""

    def test_correlation_minimal(self):
        """Correlation should work with minimal fields"""
        corr = Correlation(
            correlation_id="corr-123",
            service="test-service",
            env="dev",
            timestamp=datetime.now(),
            duration_seconds=1.5
        )

        assert corr.correlation_id == "corr-123"
        assert corr.log_count == 0  # Default
        assert corr.span_count == 0  # Default
        assert corr.severity_counts == {}
        assert corr.participating_services == []

    def test_correlation_full(self):
        """Correlation should work with all fields"""
        now = datetime.now()
        corr = Correlation(
            correlation_id="corr-123",
            trace_id="1234567890abcdef1234567890abcdef",
            service="test-service",
            env="production",
            timestamp=now,
            duration_seconds=2.5,
            log_count=10,
            span_count=5,
            metrics_count=3,
            severity_counts={"ERROR": 2, "WARN": 3, "INFO": 5},
            participating_services=["service-a", "service-b"],
            attributes={"key": "value"},
            circuit_id="CIRCUIT-123",
            product_id="PROD-456",
        )

        assert corr.log_count == 10
        assert corr.severity_counts["ERROR"] == 2
        assert "service-a" in corr.participating_services
        assert corr.circuit_id == "CIRCUIT-123"

    def test_correlation_requires_timestamp(self):
        """Correlation should require timestamp"""
        with pytest.raises(ValidationError):
            Correlation(
                correlation_id="corr-123",
                service="test",
                env="dev",
                duration_seconds=1.0
            )


class TestCorrelationQuery:
    """Test CorrelationQuery model"""

    def test_correlation_query_minimal(self):
        """CorrelationQuery should work with no filters"""
        query = CorrelationQuery()

        assert query.trace_id is None
        assert query.service is None
        assert query.limit == 100  # Default

    def test_correlation_query_with_filters(self):
        """CorrelationQuery should accept all filter fields"""
        start = datetime(2025, 10, 15, 0, 0, 0)
        end = datetime(2025, 10, 15, 23, 59, 59)

        query = CorrelationQuery(
            trace_id="1234567890abcdef1234567890abcdef",
            service="test-service",
            start_time=start,
            end_time=end,
            limit=50
        )

        assert query.trace_id == "1234567890abcdef1234567890abcdef"
        assert query.service == "test-service"
        assert query.limit == 50

    def test_correlation_query_limit_validation(self):
        """CorrelationQuery should enforce limit <= 1000"""
        with pytest.raises(ValidationError):
            CorrelationQuery(limit=1001)

        # Should work at exactly 1000
        query = CorrelationQuery(limit=1000)
        assert query.limit == 1000


class TestHealthStatus:
    """Test HealthStatus model"""

    def test_health_status_valid(self):
        """HealthStatus should validate with all fields"""
        now = datetime.now()
        health = HealthStatus(
            status="healthy",
            version="1.0.0",
            timestamp=now,
            components={"api": "healthy", "db": "healthy"}
        )

        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert health.components["api"] == "healthy"

    def test_health_status_default_version(self):
        """HealthStatus should have default version"""
        health = HealthStatus(
            status="healthy",
            timestamp=datetime.now(),
            components={}
        )

        assert health.version == "1.0.0"


class TestCorrelationEvent:
    """Test CorrelationEvent model"""

    def test_correlation_event_minimal(self):
        """CorrelationEvent should work with minimal fields"""
        event = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="1234567890abcdef1234567890abcdef",
            timestamp=datetime.now(),
            service="test-service",
            env="dev"
        )

        assert event.log_count == 0  # Default
        assert event.span_count == 0  # Default
        assert event.metadata == {}

    def test_correlation_event_full(self):
        """CorrelationEvent should work with all fields"""
        event = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="1234567890abcdef1234567890abcdef",
            timestamp=datetime.now(),
            service="test-service",
            env="production",
            log_count=5,
            span_count=3,
            circuit_id="CIRCUIT-123",
            product_id="PROD-456",
            resource_id="RES-789",
            resource_type_id="TYPE-001",
            request_id="REQ-111",
            metadata={"key": "value"}
        )

        assert event.log_count == 5
        assert event.circuit_id == "CIRCUIT-123"
        assert event.metadata["key"] == "value"


class TestSyntheticEvent:
    """Test SyntheticEvent model"""

    def test_synthetic_event_minimal(self):
        """SyntheticEvent should work with minimal fields"""
        event = SyntheticEvent(
            trace_id="1234567890abcdef1234567890abcdef",
            service="test-service",
            message="Test event"
        )

        assert event.severity == "INFO"  # Default
        assert event.attributes == {}

    def test_synthetic_event_full(self):
        """SyntheticEvent should work with all fields"""
        event = SyntheticEvent(
            trace_id="1234567890abcdef1234567890abcdef",
            service="test-service",
            message="Error event",
            severity="ERROR",
            attributes={"error_code": "500", "retry_count": "3"}
        )

        assert event.severity == "ERROR"
        assert event.attributes["error_code"] == "500"

    def test_synthetic_event_requires_fields(self):
        """SyntheticEvent should require trace_id, service, message"""
        with pytest.raises(ValidationError):
            SyntheticEvent(service="test", message="msg")  # Missing trace_id

        with pytest.raises(ValidationError):
            SyntheticEvent(trace_id="abc", message="msg")  # Missing service

        with pytest.raises(ValidationError):
            SyntheticEvent(trace_id="abc", service="test")  # Missing message
