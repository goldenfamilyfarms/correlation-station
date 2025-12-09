"""Tests for trace ID validation"""
import pytest
from unittest.mock import AsyncMock

from app.pipeline.exporters import TempoExporter
from app.models import CorrelationEvent
from datetime import datetime, timezone


@pytest.fixture
def tempo_exporter():
    """Create TempoExporter instance"""
    return TempoExporter(tempo_http_endpoint="http://tempo:4318")


class TestTraceIDValidation:
    """Test trace ID validation logic"""

    def test_valid_32_char_hex_trace_id(self, tempo_exporter):
        """Valid 32-character hex trace ID should pass"""
        valid_id = "0123456789abcdef0123456789abcdef"

        result = tempo_exporter._validate_trace_id(valid_id)

        assert result == valid_id
        assert len(result) == 32

    def test_short_trace_id_padded(self, tempo_exporter):
        """Short trace ID should be padded to 32 chars"""
        short_id = "abc123"

        result = tempo_exporter._validate_trace_id(short_id)

        assert len(result) == 32
        assert result.startswith("abc123")
        assert result == "abc123" + "0" * 26

    def test_long_trace_id_truncated(self, tempo_exporter):
        """Long trace ID should be truncated to 32 chars"""
        long_id = "0123456789abcdef" * 4  # 64 chars

        result = tempo_exporter._validate_trace_id(long_id)

        assert len(result) == 32
        assert result == long_id[:32]

    def test_whitespace_stripped(self, tempo_exporter):
        """Whitespace should be stripped"""
        id_with_spaces = "  abc123def456  "

        result = tempo_exporter._validate_trace_id(id_with_spaces)

        assert len(result) == 32
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_invalid_hex_raises_error(self, tempo_exporter):
        """Non-hex characters should raise ValueError"""
        invalid_id = "not-a-hex-string!"

        with pytest.raises(ValueError, match="must be hexadecimal"):
            tempo_exporter._validate_trace_id(invalid_id)

    def test_empty_trace_id_raises_error(self, tempo_exporter):
        """Empty trace ID should raise ValueError"""
        with pytest.raises(ValueError, match="cannot be empty"):
            tempo_exporter._validate_trace_id("")

    def test_none_trace_id_raises_error(self, tempo_exporter):
        """None trace ID should raise ValueError"""
        with pytest.raises(ValueError):
            tempo_exporter._validate_trace_id(None)


class TestOTLPTraceCreation:
    """Test OTLP trace creation with validation"""

    def test_valid_trace_id_creates_trace(self, tempo_exporter):
        """Valid trace ID should create OTLP trace"""
        correlation = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="0123456789abcdef0123456789abcdef",
            timestamp=datetime.now(timezone.utc),
            service="test-service",
            env="dev",
            log_count=1,
            span_count=1
        )

        otlp_trace = tempo_exporter._create_otlp_trace(correlation)

        # Verify structure
        assert "resourceSpans" in otlp_trace
        assert len(otlp_trace["resourceSpans"]) > 0

        # Verify trace ID
        span = otlp_trace["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["traceId"] == correlation.trace_id

    def test_invalid_trace_id_uses_fallback(self, tempo_exporter, caplog):
        """Invalid trace ID should use correlation_id as fallback"""
        correlation = CorrelationEvent(
            correlation_id="12345678-1234-1234-1234-123456789abc",
            trace_id="invalid!!!",
            timestamp=datetime.now(timezone.utc),
            service="test-service",
            env="dev",
            log_count=1,
            span_count=1
        )

        otlp_trace = tempo_exporter._create_otlp_trace(correlation)

        # Should not crash - verify trace was created
        assert "resourceSpans" in otlp_trace

        # Verify error was logged
        assert "Invalid trace_id" in caplog.text

    def test_short_trace_id_padded_in_trace(self, tempo_exporter):
        """Short trace ID should be padded in OTLP trace"""
        correlation = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="abc123",
            timestamp=datetime.now(timezone.utc),
            service="test-service",
            env="dev",
            log_count=1,
            span_count=1
        )

        otlp_trace = tempo_exporter._create_otlp_trace(correlation)

        span = otlp_trace["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        trace_id = span["traceId"]

        # Should be padded to 32 chars
        assert len(trace_id) == 32
        assert trace_id.startswith("abc123")

    def test_span_id_generated_from_correlation_id(self, tempo_exporter):
        """Span ID should be generated from correlation_id"""
        correlation = CorrelationEvent(
            correlation_id="12345678-abcd-efgh-ijkl-123456789012",
            trace_id="0123456789abcdef0123456789abcdef",
            timestamp=datetime.now(timezone.utc),
            service="test-service",
            env="dev",
            log_count=1,
            span_count=1
        )

        otlp_trace = tempo_exporter._create_otlp_trace(correlation)

        span = otlp_trace["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        span_id = span["spanId"]

        # Should be 16 chars (128-bit)
        assert len(span_id) == 16

    def test_attributes_preserved(self, tempo_exporter):
        """Custom attributes should be preserved in OTLP trace"""
        correlation = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="0123456789abcdef0123456789abcdef",
            timestamp=datetime.now(timezone.utc),
            service="test-service",
            env="dev",
            log_count=5,
            span_count=3,
            circuit_id="CIRCUIT-123",
            product_id="PROD-456",
            resource_id="RES-789"
        )

        otlp_trace = tempo_exporter._create_otlp_trace(correlation)

        span = otlp_trace["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        attributes = {attr["key"]: attr["value"] for attr in span["attributes"]}

        # Verify custom attributes
        assert attributes["circuit_id"]["stringValue"] == "CIRCUIT-123"
        assert attributes["product_id"]["stringValue"] == "PROD-456"
        assert attributes["resource_id"]["stringValue"] == "RES-789"
        assert attributes["correlation.log_count"]["intValue"] == "5"
        assert attributes["correlation.span_count"]["intValue"] == "3"
