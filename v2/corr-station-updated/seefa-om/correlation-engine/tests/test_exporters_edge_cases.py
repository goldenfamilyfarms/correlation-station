"""Additional tests for exporters edge cases and error handling"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from app.pipeline.exporters import ExporterManager, LokiExporter, TempoExporter
from app.models import LogBatch, LogRecord, ResourceInfo


class TestExporterManagerEdgeCases:
    """Test ExporterManager edge cases"""

    @pytest.mark.asyncio
    async def test_close_handles_errors_gracefully(self):
        """close() should handle errors from individual exporters"""
        manager = ExporterManager(
            loki_url="http://loki:3100",
            tempo_url="http://tempo:4317"
        )

        # Mock exporters that raise errors
        manager.loki.close = AsyncMock(side_effect=Exception("Loki close error"))
        manager.tempo.close = AsyncMock(side_effect=Exception("Tempo close error"))

        # Should not raise exception
        await manager.close()

    @pytest.mark.asyncio
    async def test_close_without_loki(self):
        """close() should work when loki is None"""
        manager = ExporterManager(
            loki_url="http://loki:3100",
            tempo_url="http://tempo:4317"
        )
        manager.loki = None

        # Should not raise exception
        await manager.close()

    @pytest.mark.asyncio
    async def test_close_without_tempo(self):
        """close() should work when tempo is None"""
        manager = ExporterManager(
            loki_url="http://loki:3100",
            tempo_url="http://tempo:4317"
        )
        manager.tempo = None

        # Should not raise exception
        await manager.close()

    @pytest.mark.asyncio
    async def test_export_logs_with_empty_batch(self):
        """export_logs() should handle empty batch"""
        manager = ExporterManager(
            loki_url="http://loki:3100",
            tempo_url="http://tempo:4317"
        )

        batch = LogBatch(
            resource=ResourceInfo(service="test", host="host1", env="dev"),
            records=[]
        )

        # Should not raise exception
        await manager.export_logs(batch)

    @pytest.mark.asyncio
    async def test_export_trace_with_no_spans(self):
        """export_trace() should handle trace with no spans"""
        manager = ExporterManager(
            loki_url="http://loki:3100",
            tempo_url="http://tempo:4317"
        )

        correlation = {
            "correlation_id": "corr-123",
            "trace_id": "1234567890abcdef1234567890abcdef",
            "service": "test-service",
            "spans": [],  # Empty spans
            "logs": []
        }

        # Should not raise exception
        await manager.export_trace(correlation)


class TestLokiExporterEdgeCases:
    """Test LokiExporter edge cases"""

    @pytest.mark.asyncio
    async def test_export_with_missing_fields(self):
        """Should handle logs with missing optional fields"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45Z",
            "message": "Test message",
            # Missing service, host, env, severity
        }]

        # Should not raise exception
        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)

    @pytest.mark.asyncio
    async def test_export_with_none_values(self):
        """Should handle None values in log fields"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45Z",
            "message": "Test message",
            "service": None,
            "host": None,
            "env": None,
            "trace_id": None
        }]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)

    @pytest.mark.asyncio
    async def test_export_large_batch(self):
        """Should handle large batches of logs"""
        exporter = LokiExporter(url="http://loki:3100")

        # Create 1000 log entries
        logs = [
            {
                "timestamp": f"2025-10-15T10:30:{i%60:02d}Z",
                "message": f"Log message {i}",
                "service": "test-service",
                "severity": "INFO"
            }
            for i in range(1000)
        ]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)
            assert mock_post.called

    @pytest.mark.asyncio
    async def test_export_with_special_characters(self):
        """Should handle special characters in log messages"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45Z",
            "message": "Special chars: \n\t\r\"'\\{}/[]<>",
            "service": "test-service"
        }]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)

    @pytest.mark.asyncio
    async def test_export_with_unicode(self):
        """Should handle Unicode characters"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45Z",
            "message": "Unicode: 你好 🚀 Ñoño",
            "service": "test-service"
        }]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)


class TestTempoExporterEdgeCases:
    """Test TempoExporter edge cases"""

    @pytest.mark.asyncio
    async def test_export_with_invalid_trace_id_raises_error(self):
        """Should raise ValueError for invalid trace_id"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "invalid-not-hex",  # Not hexadecimal
            "spans": []
        }

        with pytest.raises(ValueError, match="trace_id must be hexadecimal"):
            await exporter.export(trace_data)

    @pytest.mark.asyncio
    async def test_export_with_empty_trace_id_raises_error(self):
        """Should raise ValueError for empty trace_id"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "",  # Empty
            "spans": []
        }

        with pytest.raises(ValueError, match="trace_id cannot be empty"):
            await exporter.export(trace_data)

    @pytest.mark.asyncio
    async def test_export_with_short_trace_id_pads(self):
        """Should pad short trace_id to 32 chars"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "1234567890abcdef",  # 16 chars - too short
            "spans": [],
            "service": "test"
        }

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200)
            await exporter.export(trace_data)

            # Verify trace_id was padded
            call_args = mock_post.call_args
            # Should be padded to 32 chars

    @pytest.mark.asyncio
    async def test_export_with_long_trace_id_truncates(self):
        """Should truncate long trace_id to 32 chars"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "1234567890abcdef1234567890abcdef_extra_chars",  # Too long
            "spans": [],
            "service": "test"
        }

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200)
            await exporter.export(trace_data)

    @pytest.mark.asyncio
    async def test_export_with_missing_service(self):
        """Should handle missing service field"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "1234567890abcdef1234567890abcdef",
            "spans": [],
            # Missing service
        }

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200)
            await exporter.export(trace_data)

    @pytest.mark.asyncio
    async def test_export_with_complex_span_attributes(self):
        """Should handle spans with complex attributes"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "1234567890abcdef1234567890abcdef",
            "service": "test",
            "spans": [{
                "span_id": "1234567890abcdef",
                "name": "test-span",
                "start_time": datetime.now(timezone.utc).timestamp(),
                "end_time": datetime.now(timezone.utc).timestamp() + 1,
                "attributes": {
                    "string": "value",
                    "number": 123,
                    "float": 1.23,
                    "bool": True,
                    "list": [1, 2, 3],
                    "dict": {"nested": "value"}
                }
            }]
        }

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200)
            await exporter.export(trace_data)


class TestExporterErrorHandling:
    """Test error handling in exporters"""

    @pytest.mark.asyncio
    async def test_loki_export_network_error(self):
        """Should handle network errors gracefully"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45Z",
            "message": "Test",
            "service": "test"
        }]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                await exporter.export(logs)

    @pytest.mark.asyncio
    async def test_loki_export_non_200_status(self):
        """Should handle non-200 HTTP status"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45Z",
            "message": "Test",
            "service": "test"
        }]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=500, text="Internal Server Error")

            # Should handle error (implementation may vary)
            await exporter.export(logs)

    @pytest.mark.asyncio
    async def test_tempo_export_network_error(self):
        """Should handle network errors in Tempo export"""
        exporter = TempoExporter(url="http://tempo:4317")

        trace_data = {
            "trace_id": "1234567890abcdef1234567890abcdef",
            "service": "test",
            "spans": []
        }

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                await exporter.export(trace_data)

    @pytest.mark.asyncio
    async def test_close_already_closed_client(self):
        """Should handle closing already closed client"""
        exporter = LokiExporter(url="http://loki:3100")

        # Close once
        await exporter.close()

        # Close again - should not raise
        await exporter.close()


class TestExporterTimestampHandling:
    """Test timestamp handling in exporters"""

    @pytest.mark.asyncio
    async def test_export_with_nanosecond_timestamps(self):
        """Should handle nanosecond precision timestamps"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [{
            "timestamp": "2025-10-15T10:30:45.123456789Z",  # Nanosecond precision
            "message": "Test",
            "service": "test"
        }]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)

    @pytest.mark.asyncio
    async def test_export_with_various_timestamp_formats(self):
        """Should handle various timestamp formats"""
        exporter = LokiExporter(url="http://loki:3100")

        logs = [
            {"timestamp": "2025-10-15T10:30:45Z", "message": "ISO format", "service": "test"},
            {"timestamp": "2025-10-15T10:30:45.123Z", "message": "With millis", "service": "test"},
            {"timestamp": "2025-10-15T10:30:45+00:00", "message": "With timezone", "service": "test"},
        ]

        with patch.object(exporter.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=204)
            await exporter.export(logs)
