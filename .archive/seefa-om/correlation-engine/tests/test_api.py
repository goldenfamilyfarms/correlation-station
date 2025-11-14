"""
Tests for Correlation Engine API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check_returns_200(self, client):
        """Test that health check returns 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_json(self, client):
        """Test that health check returns JSON"""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    def test_health_check_has_required_fields(self, client):
        """Test that health check response has required fields"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data

        assert data["status"] == "healthy"


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint"""

    def test_metrics_returns_200(self, client):
        """Test that metrics endpoint returns 200"""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_returns_text(self, client):
        """Test that metrics returns Prometheus text format"""
        response = client.get("/metrics")
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_contains_expected_metrics(self, client):
        """Test that metrics response contains expected metric names"""
        response = client.get("/metrics")
        content = response.text

        # Check for our custom metrics
        assert "correlation_events_total" in content
        assert "log_records_received_total" in content
        assert "export_attempts_total" in content


class TestLogsIngestionEndpoint:
    """Tests for logs ingestion endpoint"""

    def test_post_logs_returns_202(self, client):
        """Test that posting logs returns 202 Accepted"""
        payload = {
            "resource": {
                "service": "test-service",
                "host": "test-host",
                "env": "dev"
            },
            "records": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "severity": "INFO",
                    "message": "Test log message",
                    "labels": {"test": "true"}
                }
            ]
        }

        response = client.post("/api/logs", json=payload)
        assert response.status_code == 202

    def test_post_logs_with_trace_id(self, client):
        """Test posting logs with trace_id"""
        payload = {
            "resource": {
                "service": "test-service",
                "host": "test-host",
                "env": "dev"
            },
            "records": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "severity": "INFO",
                    "message": "Test log with trace",
                    "trace_id": "abc123def456789012345678901234567",
                    "span_id": "1234567890123456",
                    "labels": {}
                }
            ]
        }

        response = client.post("/api/logs", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["count"] == 1

    def test_post_logs_with_custom_attributes(self, client):
        """Test posting logs with custom Sense attributes"""
        payload = {
            "resource": {
                "service": "test-service",
                "host": "test-host",
                "env": "dev"
            },
            "records": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "severity": "INFO",
                    "message": "Test log with custom attrs",
                    "circuit_id": "CIRCUIT-123",
                    "product_id": "PROD-456",
                    "resource_id": "RES-789",
                    "labels": {}
                }
            ]
        }

        response = client.post("/api/logs", json=payload)
        assert response.status_code == 202

    def test_post_logs_invalid_payload_returns_422(self, client):
        """Test that invalid payload returns 422"""
        payload = {
            "invalid": "payload"
        }

        response = client.post("/api/logs", json=payload)
        assert response.status_code == 422

    def test_post_logs_batch(self, client):
        """Test posting a batch of logs"""
        payload = {
            "resource": {
                "service": "test-service",
                "host": "test-host",
                "env": "dev"
            },
            "records": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "severity": "INFO",
                    "message": f"Test log {i}",
                    "labels": {}
                }
                for i in range(10)
            ]
        }

        response = client.post("/api/logs", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["count"] == 10


class TestOTLPEndpoints:
    """Tests for OTLP ingestion endpoints"""

    def test_post_otlp_logs_returns_202(self, client):
        """Test that posting OTLP logs returns 202"""
        payload = {
            "resourceLogs": []
        }

        response = client.post("/api/otlp/v1/logs", json=payload)
        assert response.status_code == 202

    def test_post_otlp_traces_returns_202(self, client):
        """Test that posting OTLP traces returns 202"""
        payload = {
            "resourceSpans": []
        }

        response = client.post("/api/otlp/v1/traces", json=payload)
        assert response.status_code == 202


class TestCorrelationsEndpoint:
    """Tests for correlations query endpoint"""

    def test_get_correlations_returns_200(self, client):
        """Test that querying correlations returns 200"""
        response = client.get("/api/correlations")
        assert response.status_code == 200

    def test_get_correlations_returns_array(self, client):
        """Test that correlations endpoint returns array"""
        response = client.get("/api/correlations")
        data = response.json()
        assert isinstance(data, list)

    def test_get_correlations_with_limit(self, client):
        """Test correlations with limit parameter"""
        response = client.get("/api/correlations?limit=5")
        assert response.status_code == 200

    def test_get_correlations_with_trace_id_filter(self, client):
        """Test correlations with trace_id filter"""
        response = client.get("/api/correlations?trace_id=abc123")
        assert response.status_code == 200

    def test_get_correlations_with_service_filter(self, client):
        """Test correlations with service filter"""
        response = client.get("/api/correlations?service=test-service")
        assert response.status_code == 200


class TestSyntheticEventsEndpoint:
    """Tests for synthetic event injection"""

    def test_post_synthetic_event_returns_201(self, client):
        """Test posting synthetic event returns 201"""
        payload = {
            "trace_id": "abc123def456789012345678901234567",
            "service": "test-service",
            "message": "Synthetic test event",
            "severity": "INFO",
            "attributes": {"test": "true"}
        }

        response = client.post("/api/events", json=payload)
        assert response.status_code == 201

    def test_post_synthetic_event_invalid_returns_422(self, client):
        """Test invalid synthetic event returns 422"""
        payload = {
            "invalid": "payload"
        }

        response = client.post("/api/events", json=payload)
        assert response.status_code == 422


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_returns_200(self, client):
        """Test root endpoint returns 200"""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_service_info(self, client):
        """Test root endpoint returns service information"""
        response = client.get("/")
        data = response.json()

        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert "endpoints" in data

        assert data["service"] == "correlation-engine"


class TestBasicAuth:
    """Tests for BasicAuth when enabled"""

    def test_unauthenticated_request_without_auth_enabled(self, client):
        """Test that requests work without auth when disabled"""
        # Auth is disabled by default
        response = client.get("/health")
        assert response.status_code == 200

    # Note: Testing with auth enabled requires setting environment variables
    # and restarting the app, which is better done in integration tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])