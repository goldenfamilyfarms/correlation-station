"""Tests for log normalization"""
import pytest
from app.pipeline.normalizer import LogNormalizer
from app.models import LogBatch, LogRecord, ResourceInfo


class TestLogNormalizer:
    """Test LogNormalizer class"""

    @pytest.fixture
    def normalizer(self):
        """Create a LogNormalizer instance"""
        return LogNormalizer()

    def test_normalize_log_batch(self, normalizer):
        """Should normalize a batch of logs"""
        batch = LogBatch(
            resource=ResourceInfo(service="test-service", host="host1", env="production"),
            records=[
                LogRecord(timestamp="2025-10-15T10:30:45Z", message="Log 1"),
                LogRecord(timestamp="2025-10-15T10:30:46Z", message="Log 2", severity="ERROR"),
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert len(normalized) == 2
        assert normalized[0]["service"] == "test-service"
        assert normalized[0]["env"] == "production"
        assert normalized[1]["severity"] == "ERROR"

    def test_normalize_log_batch_with_trace_id(self, normalizer):
        """Should preserve trace_id in normalized logs"""
        batch = LogBatch(
            resource=ResourceInfo(service="test-service", host="host1", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:45Z",
                    message="Log with trace",
                    trace_id="1234567890abcdef1234567890abcdef"
                ),
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert normalized[0]["trace_id"] == "1234567890abcdef1234567890abcdef"

    def test_normalize_log_batch_with_custom_attributes(self, normalizer):
        """Should preserve custom Sense attributes"""
        batch = LogBatch(
            resource=ResourceInfo(service="test-service", host="host1", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:45Z",
                    message="Log with attributes",
                    circuit_id="CIRCUIT-123",
                    product_id="PROD-456",
                    resource_id="RES-789",
                    resource_type_id="TYPE-001",
                    request_id="REQ-111"
                ),
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert normalized[0]["circuit_id"] == "CIRCUIT-123"
        assert normalized[0]["product_id"] == "PROD-456"
        assert normalized[0]["resource_id"] == "RES-789"
        assert normalized[0]["resource_type_id"] == "TYPE-001"
        assert normalized[0]["request_id"] == "REQ-111"

    def test_normalize_log_batch_with_labels(self, normalizer):
        """Should preserve labels"""
        batch = LogBatch(
            resource=ResourceInfo(service="test-service", host="host1", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:45Z",
                    message="Log with labels",
                    labels={"key1": "value1", "key2": "value2"}
                ),
            ]
        )

        normalized = normalizer.normalize_log_batch(batch)

        assert normalized[0]["labels"]["key1"] == "value1"
        assert normalized[0]["labels"]["key2"] == "value2"


class TestSyslogNormalization:
    """Test syslog parsing"""

    @pytest.fixture
    def normalizer(self):
        """Create a LogNormalizer instance"""
        return LogNormalizer()

    def test_normalize_syslog_standard_format(self, normalizer):
        """Should parse standard syslog format"""
        line = "2025-10-15T10:30:45.123Z myhost myservice[1234]: Test message"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["timestamp"] == "2025-10-15T10:30:45.123Z"
        assert normalized["host"] == "myhost"
        assert normalized["service"] == "myservice"
        assert normalized["message"] == "Test message"

    def test_normalize_syslog_without_pid(self, normalizer):
        """Should parse syslog without PID"""
        line = "2025-10-15T10:30:45Z myhost myservice: Test message"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["service"] == "myservice"
        assert normalized["message"] == "Test message"

    def test_normalize_syslog_traditional_format(self, normalizer):
        """Should parse traditional syslog format"""
        line = "Oct 15 10:30:45 myhost myservice: Test message"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["host"] == "myhost"
        assert normalized["service"] == "myservice"
        assert normalized["message"] == "Test message"
        # Timestamp should be constructed
        assert "2025-10-15" in normalized["timestamp"] or "10-15" in normalized["timestamp"]

    def test_normalize_syslog_with_trace_id_in_message(self, normalizer):
        """Should extract trace_id from message"""
        line = "2025-10-15T10:30:45Z host service: trace_id=1234567890abcdef1234567890abcdef message"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["trace_id"] == "1234567890abcdef1234567890abcdef"

    def test_normalize_syslog_unparseable(self, normalizer):
        """Should handle unparseable syslog gracefully"""
        line = "This is not a valid syslog line"

        normalized = normalizer.normalize_syslog_line(line)

        # Should return minimal structure
        assert normalized["service"] == "syslog"  # Default
        assert normalized["message"] == line
        assert "timestamp" in normalized

    def test_normalize_syslog_with_error_severity(self, normalizer):
        """Should infer ERROR severity from message"""
        line = "2025-10-15T10:30:45Z host service: Error occurred in system"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["severity"] == "ERROR"

    def test_normalize_syslog_with_warn_severity(self, normalizer):
        """Should infer WARN severity from message"""
        line = "2025-10-15T10:30:45Z host service: Warning: disk space low"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["severity"] == "WARN"

    def test_normalize_syslog_with_debug_severity(self, normalizer):
        """Should infer DEBUG severity from message"""
        line = "2025-10-15T10:30:45Z host service: Debug: entering function"

        normalized = normalizer.normalize_syslog_line(line)

        assert normalized["severity"] == "DEBUG"


class TestTraceIdExtraction:
    """Test trace ID extraction from messages"""

    @pytest.fixture
    def normalizer(self):
        """Create a LogNormalizer instance"""
        return LogNormalizer()

    def test_extract_trace_id_with_equals(self, normalizer):
        """Should extract trace_id=<hex>"""
        message = "Request processed trace_id=1234567890abcdef1234567890abcdef successfully"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id == "1234567890abcdef1234567890abcdef"

    def test_extract_trace_id_with_colon(self, normalizer):
        """Should extract trace_id:<hex>"""
        message = "trace_id:1234567890abcdef1234567890abcdef"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id == "1234567890abcdef1234567890abcdef"

    def test_extract_trace_id_case_insensitive(self, normalizer):
        """Should extract traceId, TraceId, etc."""
        message = "traceId=ABCD567890abcdef1234567890abcdef"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id.lower() == "abcd567890abcdef1234567890abcdef"

    def test_extract_trace_id_standalone_hex(self, normalizer):
        """Should extract standalone 32-char hex string"""
        message = "Processing 1234567890abcdef1234567890abcdef request"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id == "1234567890abcdef1234567890abcdef"

    def test_extract_trace_id_no_match(self, normalizer):
        """Should return None if no trace ID found"""
        message = "This message has no trace ID"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id is None

    def test_extract_trace_id_short_hex_ignored(self, normalizer):
        """Should ignore hex strings that are too short"""
        message = "Short hex: 1234567890abcdef"

        trace_id = normalizer._extract_trace_id_from_message(message)

        # 16-char hex should be ignored (we need 32 for OTEL trace IDs)
        assert trace_id is None

    def test_extract_trace_id_with_underscores(self, normalizer):
        """Should extract trace_id with underscores"""
        message = "trace_id=1234567890abcdef1234567890abcdef"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id == "1234567890abcdef1234567890abcdef"

    def test_extract_trace_id_with_hyphens(self, normalizer):
        """Should extract trace-id with hyphens"""
        message = "trace-id=1234567890abcdef1234567890abcdef"

        trace_id = normalizer._extract_trace_id_from_message(message)

        assert trace_id == "1234567890abcdef1234567890abcdef"


class TestSeverityInference:
    """Test severity inference from message content"""

    @pytest.fixture
    def normalizer(self):
        """Create a LogNormalizer instance"""
        return LogNormalizer()

    def test_infer_error_severity(self, normalizer):
        """Should infer ERROR from error keywords"""
        assert normalizer._infer_severity("error occurred") == "ERROR"
        assert normalizer._infer_severity("Failed to connect") == "ERROR"
        assert normalizer._infer_severity("Exception in thread") == "ERROR"
        assert normalizer._infer_severity("Critical system failure") == "ERROR"

    def test_infer_warn_severity(self, normalizer):
        """Should infer WARN from warning keywords"""
        assert normalizer._infer_severity("warning: disk space low") == "WARN"
        assert normalizer._infer_severity("Warning message here") == "WARN"

    def test_infer_debug_severity(self, normalizer):
        """Should infer DEBUG from debug keywords"""
        assert normalizer._infer_severity("debug: entering function") == "DEBUG"
        assert normalizer._infer_severity("trace: variable value") == "DEBUG"

    def test_infer_info_severity_default(self, normalizer):
        """Should default to INFO for neutral messages"""
        assert normalizer._infer_severity("Request processed successfully") == "INFO"
        assert normalizer._infer_severity("Normal log message") == "INFO"

    def test_infer_severity_case_insensitive(self, normalizer):
        """Severity inference should be case-insensitive"""
        assert normalizer._infer_severity("ERROR in system") == "ERROR"
        assert normalizer._infer_severity("Error in system") == "ERROR"
        assert normalizer._infer_severity("error in system") == "ERROR"


class TestTimestampConstruction:
    """Test timestamp construction from syslog date parts"""

    @pytest.fixture
    def normalizer(self):
        """Create a LogNormalizer instance"""
        return LogNormalizer()

    def test_construct_timestamp_jan(self, normalizer):
        """Should construct timestamp for January"""
        timestamp = normalizer._construct_timestamp("Jan", "15", "10:30:45")

        assert "-01-15T10:30:45" in timestamp

    def test_construct_timestamp_dec(self, normalizer):
        """Should construct timestamp for December"""
        timestamp = normalizer._construct_timestamp("Dec", "31", "23:59:59")

        assert "-12-31T23:59:59" in timestamp

    def test_construct_timestamp_single_digit_day(self, normalizer):
        """Should zero-pad single digit days"""
        timestamp = normalizer._construct_timestamp("Mar", "5", "08:00:00")

        assert "-03-05T08:00:00" in timestamp

    def test_construct_timestamp_invalid_month(self, normalizer):
        """Should handle invalid month gracefully"""
        timestamp = normalizer._construct_timestamp("InvalidMonth", "15", "10:30:45")

        # Should return current timestamp instead of failing
        assert "T" in timestamp
        assert "Z" in timestamp

    def test_construct_timestamp_empty_values(self, normalizer):
        """Should handle empty values gracefully"""
        timestamp = normalizer._construct_timestamp("", "", "")

        # Should return current timestamp
        assert "T" in timestamp
        assert "Z" in timestamp
