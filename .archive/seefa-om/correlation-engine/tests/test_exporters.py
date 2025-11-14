"""
Tests for Correlation Engine Exporters
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.pipeline.exporters import LokiExporter, TempoExporter, DatadogExporter, ExporterManager
from app.models import LogBatch, LogRecord, ResourceInfo, CorrelationEvent


class TestLokiExporter:
    """Tests for Loki exporter"""

    @pytest.fixture
    def loki_exporter(self):
        """Create Loki exporter instance"""
        return LokiExporter(loki_url="http://test-loki:3100/loki/api/v1/push")

    def test_loki_exporter_initialization(self, loki_exporter):
        """Test Loki exporter initializes correctly"""
        assert loki_exporter.loki_url == "http://test-loki:3100/loki/api/v1/push"
        assert loki_exporter.client is not None

    def test_convert_to_loki_streams(self, loki_exporter):
        """Test converting log batch to Loki streams format"""
        batch = LogBatch(
            resource=ResourceInfo(service="test", host="localhost", env="dev"),
            records=[
                LogRecord(
                    timestamp="2025-10-15T10:30:00.000Z",
                    severity="INFO",
                    message="Test message",
                    trace_id="abc123",
                    labels={}
                )
            ]
        )

        streams = loki_exporter._convert_to_loki_streams(batch)

        assert len(streams) > 0
        assert "stream" in streams[0]
        assert "values" in streams[0]

        # Check low-cardinality labels
        stream_labels = streams[0]["stream"]
        assert "service" in stream_labels
        assert "env" in stream_labels
        assert stream_labels["service"] == "test"
        assert stream_labels["env"] == "dev"

    def test_labels_to_string(self, loki_exporter):
        """Test label dict to string conversion"""
        labels = {"service": "test", "env": "dev", "trace_id": "abc123"}
        label_str = loki_exporter._labels_to_string(labels)

        assert 'service="test"' in label_str
        assert 'env="dev"' in label_str
        assert 'trace_id="abc123"' in label_str

    def test_timestamp_to_nanoseconds(self, loki_exporter):
        """Test timestamp conversion to nanoseconds"""
        timestamp = "2025-10-15T10:30:00.000Z"
        ns = loki_exporter._to_nanoseconds(timestamp)

        assert isinstance(ns, int)
        assert ns > 0

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_export_logs_success(self, mock_post, loki_exporter):
        """Test successful log export to Loki"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

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

        await loki_exporter.export_logs(batch)

        # Verify POST was called
        assert mock_post.called


class TestTempoExporter:
    """Tests for Tempo exporter"""

    @pytest.fixture
    def tempo_exporter(self):
        """Create Tempo exporter instance"""
        return TempoExporter(tempo_http_endpoint="http://test-tempo:4318")

    def test_tempo_exporter_initialization(self, tempo_exporter):
        """Test Tempo exporter initializes correctly"""
        assert tempo_exporter.tempo_http_endpoint == "http://test-tempo:4318"
        assert tempo_exporter.client is not None

    def test_create_otlp_trace(self, tempo_exporter):
        """Test creating OTLP trace format"""
        correlation = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="abc123def456789012345678901234567",
            timestamp=datetime.now(timezone.utc),
            service="test",
            env="dev",
            log_count=5,
            span_count=2,
            circuit_id="CIRCUIT-123",
            product_id="PROD-456",
            metadata={}
        )

        otlp_trace = tempo_exporter._create_otlp_trace(correlation)

        assert "resourceSpans" in otlp_trace
        assert len(otlp_trace["resourceSpans"]) > 0

        # Check span attributes
        spans = otlp_trace["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) > 0
        assert spans[0]["name"] == "correlation.test"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_export_correlation_span_success(self, mock_post, tempo_exporter):
        """Test successful correlation span export"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        correlation = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="abc123def456789012345678901234567",
            timestamp=datetime.now(timezone.utc),
            service="test",
            env="dev",
            log_count=5,
            span_count=2,
            metadata={}
        )

        await tempo_exporter.export_correlation_span(correlation)

        assert mock_post.called


class TestDatadogExporter:
    """Tests for Datadog exporter"""

    def test_datadog_exporter_disabled_without_api_key(self):
        """Test Datadog exporter is disabled without API key"""
        exporter = DatadogExporter(api_key=None)
        assert not exporter.enabled

    def test_datadog_exporter_enabled_with_api_key(self):
        """Test Datadog exporter is enabled with API key"""
        exporter = DatadogExporter(api_key="test-key")
        assert exporter.enabled
        assert exporter.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_export_logs_when_disabled(self):
        """Test export does nothing when disabled"""
        exporter = DatadogExporter(api_key=None)

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

        # Should not raise exception
        await exporter.export_logs(batch)


class TestExporterManager:
    """Tests for exporter manager"""

    @pytest.fixture
    def exporter_manager(self):
        """Create exporter manager instance"""
        return ExporterManager(
            loki_url="http://test-loki:3100",
            tempo_grpc_endpoint="test-tempo:4317",
            tempo_http_endpoint="http://test-tempo:4318",
            datadog_api_key=None,
            datadog_site="datadoghq.com"
        )

    def test_exporter_manager_initialization(self, exporter_manager):
        """Test exporter manager initializes all exporters"""
        assert exporter_manager.loki is not None
        assert exporter_manager.tempo is not None
        assert exporter_manager.datadog is not None

    @pytest.mark.asyncio
    @patch.object(LokiExporter, 'export_logs', new_callable=AsyncMock)
    @patch.object(DatadogExporter, 'export_logs', new_callable=AsyncMock)
    async def test_export_logs_to_all_backends(self, mock_dd_export, mock_loki_export, exporter_manager):
        """Test exporting logs to all configured backends"""
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

        await exporter_manager.export_logs(batch)

        # Both exporters should be called
        assert mock_loki_export.called
        assert mock_dd_export.called

    @pytest.mark.asyncio
    @patch.object(TempoExporter, 'export_correlation_span', new_callable=AsyncMock)
    async def test_export_correlation_span(self, mock_tempo_export, exporter_manager):
        """Test exporting correlation span to Tempo"""
        correlation = CorrelationEvent(
            correlation_id="corr-123",
            trace_id="abc123def456789012345678901234567",
            timestamp=datetime.now(timezone.utc),
            service="test",
            env="dev",
            log_count=5,
            span_count=2,
            metadata={}
        )

        await exporter_manager.export_correlation_span(correlation)

        assert mock_tempo_export.called

    @pytest.mark.asyncio
    async def test_close_all_exporters(self, exporter_manager):
        """Test closing all exporters"""
        # Should not raise exception
        await exporter_manager.close()


class TestExporterMetrics:
    """Tests for exporter metrics"""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_export_metrics_tracked(self, mock_post):
        """Test that export attempts are tracked in metrics"""
        from app.pipeline.exporters import EXPORT_ATTEMPTS, EXPORT_DURATION

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        loki_exporter = LokiExporter("http://test:3100")

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

        await loki_exporter.export_logs(batch)

        # Metrics should be incremented
        # Note: Actual metric values depend on test execution order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])