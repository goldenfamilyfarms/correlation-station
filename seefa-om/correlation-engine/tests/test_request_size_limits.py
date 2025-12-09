"""Tests for request size limits (DoS protection)"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_correlation_engine():
    """Mock correlation engine"""
    engine = AsyncMock()
    engine.add_logs = AsyncMock()
    engine.add_traces = AsyncMock()
    return engine


class TestProtobufSizeLimits:
    """Test protobuf payload size limits"""

    def test_protobuf_within_limit_accepted(self, client, mock_correlation_engine):
        """Protobuf payload within limit should be accepted"""
        # Set up mock
        app.state.correlation_engine = mock_correlation_engine

        # Small valid protobuf payload (empty LogsData)
        small_payload = b'\n\x00'  # Minimal valid protobuf

        response = client.post(
            "/api/otlp/v1/logs",
            content=small_payload,
            headers={"Content-Type": "application/x-protobuf"}
        )

        # Should accept (202) even if empty
        assert response.status_code in [200, 202, 400]  # 400 for empty is ok

    def test_protobuf_exceeds_limit_rejected(self, client, mock_correlation_engine):
        """Protobuf payload exceeding limit should be rejected with 413"""
        # Set up mock
        app.state.correlation_engine = mock_correlation_engine

        # Create payload larger than max_protobuf_size
        large_payload = b'x' * (settings.max_protobuf_size + 1)

        response = client.post(
            "/api/otlp/v1/logs",
            content=large_payload,
            headers={"Content-Type": "application/x-protobuf"}
        )

        # Should reject with 413 Payload Too Large
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_json_exceeds_limit_rejected(self, client, mock_correlation_engine):
        """JSON payload exceeding limit should be rejected with 413"""
        # Set up mock
        app.state.correlation_engine = mock_correlation_engine

        # Create large JSON payload
        large_json = '{"data": "' + ('x' * settings.max_json_size) + '"}'

        response = client.post(
            "/api/otlp/v1/logs",
            content=large_json.encode(),
            headers={"Content-Type": "application/json"}
        )

        # Should reject with 413
        assert response.status_code == 413


class TestContentLengthValidation:
    """Test Content-Length header validation"""

    def test_content_length_within_limit(self, client, mock_correlation_engine):
        """Request with Content-Length within limit should proceed"""
        app.state.correlation_engine = mock_correlation_engine

        response = client.post(
            "/api/otlp/v1/logs",
            content=b'{"resourceLogs": []}',
            headers={
                "Content-Type": "application/json",
                "Content-Length": "100"
            }
        )

        # Should not reject based on Content-Length
        assert response.status_code in [200, 202, 400]

    def test_content_length_exceeds_limit(self, client, mock_correlation_engine):
        """Request with Content-Length exceeding limit should be rejected"""
        app.state.correlation_engine = mock_correlation_engine

        # Send header claiming huge size
        response = client.post(
            "/api/otlp/v1/logs",
            content=b'{"resourceLogs": []}',
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(settings.max_request_body_size + 1)
            }
        )

        # Should reject with 413
        assert response.status_code == 413


class TestInvalidPayloads:
    """Test handling of invalid payloads"""

    def test_invalid_protobuf_rejected(self, client, mock_correlation_engine):
        """Invalid protobuf should be rejected with 400"""
        app.state.correlation_engine = mock_correlation_engine

        # Invalid protobuf data
        response = client.post(
            "/api/otlp/v1/logs",
            content=b'invalid protobuf data',
            headers={"Content-Type": "application/x-protobuf"}
        )

        # Should reject with 400 Bad Request
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_invalid_json_rejected(self, client, mock_correlation_engine):
        """Invalid JSON should be rejected with 400"""
        app.state.correlation_engine = mock_correlation_engine

        # Invalid JSON
        response = client.post(
            "/api/otlp/v1/logs",
            content=b'{invalid json}',
            headers={"Content-Type": "application/json"}
        )

        # Should reject with 400
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


class TestTracesSizeLimits:
    """Test size limits for traces endpoint"""

    def test_traces_protobuf_exceeds_limit(self, client, mock_correlation_engine):
        """Large traces protobuf should be rejected"""
        app.state.correlation_engine = mock_correlation_engine

        large_payload = b'x' * (settings.max_protobuf_size + 1)

        response = client.post(
            "/api/otlp/v1/traces",
            content=large_payload,
            headers={"Content-Type": "application/x-protobuf"}
        )

        assert response.status_code == 413

    def test_traces_json_exceeds_limit(self, client, mock_correlation_engine):
        """Large traces JSON should be rejected"""
        app.state.correlation_engine = mock_correlation_engine

        large_json = '{"data": "' + ('x' * settings.max_json_size) + '"}'

        response = client.post(
            "/api/otlp/v1/traces",
            content=large_json.encode(),
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 413
