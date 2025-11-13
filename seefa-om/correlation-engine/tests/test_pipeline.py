"""
Tests for Correlation Engine Pipeline Components
"""
import pytest
from datetime import datetime

from app.pipeline.normalizer import LogNormalizer
from app.models import LogBatch, LogRecord, ResourceInfo


class TestLogNormalizer:
    """Tests for log normalization"""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance"""
        return LogNormalizer()

    def test_normalize_simple_log_batch(self, normalizer):
        """Test normalizing a simple log batch"""
        batch = LogBatch(
            resource=ResourceInfo(service="test", host="localhost", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:00.000Z",
                    severity="INFO",
                    message="Test message",
                    labels={}
                )
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert len(normalized) == 1
        assert normalized[0]["service"] == "test"
        assert normalized[0]["message"] == "Test message"
        assert normalized[0]["severity"] == "INFO"

    def test_normalize_log_with_trace_id(self, normalizer):
        """Test normalizing log with trace_id"""
        batch = LogBatch(
            resource=ResourceInfo(service="test", host="localhost", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:00.000Z",
                    severity="INFO",
                    message="Test message",
                    trace_id="abc123def456789012345678901234567",
                    span_id="1234567890123456",
                    labels={}
                )
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert normalized[0]["trace_id"] == "abc123def456789012345678901234567"
        assert normalized[0]["span_id"] == "1234567890123456"

    def test_normalize_log_with_custom_attributes(self, normalizer):
        """Test normalizing log with custom Sense attributes"""
        batch = LogBatch(
            resource=ResourceInfo(service="test", host="localhost", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:00.000Z",
                    severity="INFO",
                    message="Test message",
                    circuit_id="CIRCUIT-123",
                    product_id="PROD-456",
                    resource_id="RES-789",
                    resource_type_id="TYPE-001",
                    request_id="REQ-abc",
                    labels={}
                )
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert normalized[0]["circuit_id"] == "CIRCUIT-123"
        assert normalized[0]["product_id"] == "PROD-456"
        assert normalized[0]["resource_id"] == "RES-789"
        assert normalized[0]["resource_type_id"] == "TYPE-001"
        assert normalized[0]["request_id"] == "REQ-abc"

    def test_normalize_syslog_line_standard_format(self, normalizer):
        """Test parsing standard syslog format"""
        syslog_line = "2025-10-15T10:30:45.123Z hostname service[1234]: Test message"

        normalized = normalizer.normalize_syslog_line(syslog_line)

        assert normalized["service"] == "service"
        assert normalized["host"] == "hostname"
        assert "Test message" in normalized["message"]

    def test_normalize_syslog_line_with_trace_id(self, normalizer):
        """Test extracting trace_id from syslog message"""
        syslog_line = "2025-10-15T10:30:45.123Z host service: message with trace_id=abc123def456789012345678901234567"

        normalized = normalizer.normalize_syslog_line(syslog_line)

        assert normalized["trace_id"] == "abc123def456789012345678901234567"

    def test_infer_severity_from_message(self, normalizer):
        """Test severity inference from message content"""
        assert normalizer._infer_severity("ERROR: Something failed") == "ERROR"
        assert normalizer._infer_severity("WARN: Be careful") == "WARN"
        assert normalizer._infer_severity("DEBUG: Details here") == "DEBUG"
        assert normalizer._infer_severity("Normal message") == "INFO"

    def test_extract_trace_id_from_message(self, normalizer):
        """Test trace ID extraction from various formats"""
        # Standard format
        msg1 = "Processing request with trace_id=abc123def456789012345678901234567"
        assert normalizer._extract_trace_id_from_message(msg1) == "abc123def456789012345678901234567"

        # Alternative formats
        msg2 = "traceId=abc123def456789012345678901234567 here"
        assert normalizer._extract_trace_id_from_message(msg2) == "abc123def456789012345678901234567"

        # No trace ID
        msg3 = "No trace ID in this message"
        assert normalizer._extract_trace_id_from_message(msg3) is None


class TestCorrelationWindow:
    """Tests for correlation windowing"""

    def test_correlation_window_creation(self):
        """Test creating a correlation window"""
        from app.pipeline.correlator import CorrelationWindow

        window = CorrelationWindow(window_seconds=60)
        assert window.window_seconds == 60
        assert len(window.logs_by_trace) == 0
        assert len(window.traces_by_trace) == 0

    def test_add_log_to_window(self):
        """Test adding log to window"""
        from app.pipeline.correlator import CorrelationWindow

        window = CorrelationWindow(window_seconds=60)
        log_record = {
            "trace_id": "abc123",
            "service": "test",
            "message": "Test log"
        }

        window.add_log(log_record)
        assert "abc123" in window.logs_by_trace
        assert len(window.logs_by_trace["abc123"]) == 1

    def test_window_should_close(self):
        """Test window closing logic"""
        from app.pipeline.correlator import CorrelationWindow
        import time

        # Window with 1 second duration
        window = CorrelationWindow(window_seconds=1)
        assert not window.should_close()

        # Wait for window to expire
        time.sleep(1.1)
        assert window.should_close()

    def test_create_correlations_with_logs_and_traces(self):
        """Test creating correlation events"""
        from app.pipeline.correlator import CorrelationWindow

        window = CorrelationWindow(window_seconds=60)

        # Add logs with same trace_id
        window.add_log({
            "trace_id": "abc123",
            "service": "test",
            "env": "dev",
            "message": "Log 1"
        })
        window.add_log({
            "trace_id": "abc123",
            "service": "test",
            "env": "dev",
            "message": "Log 2"
        })

        # Create correlations
        correlations = window.create_correlations()

        assert len(correlations) == 1
        assert correlations[0].trace_id == "abc123"
        assert correlations[0].log_count == 2
        assert correlations[0].service == "test"


class TestCorrelationEngine:
    """Tests for main correlation engine"""

    @pytest.mark.asyncio
    async def test_add_logs_to_queue(self):
        """Test adding logs to processing queue"""
        from app.pipeline.correlator import CorrelationEngine
        from app.pipeline.exporters import ExporterManager

        exporter_manager = ExporterManager(
            loki_url="http://test:3100",
            tempo_grpc_endpoint="test:4317",
            tempo_http_endpoint="http://test:4318"
        )

        engine = CorrelationEngine(
            window_seconds=60,
            exporter_manager=exporter_manager
        )

        batch = LogBatch(
            resource=ResourceInfo(service="test", host="localhost", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:00.000Z",
                    severity="INFO",
                    message="Test",
                    labels={}
                )
            ]
        )

        await engine.add_logs(batch)

        # Queue should have one item
        assert not engine.log_queue.empty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])