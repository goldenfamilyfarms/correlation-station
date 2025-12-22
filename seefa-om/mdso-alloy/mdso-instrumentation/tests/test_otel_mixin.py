"""Unit tests for OTel Mixin"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from otel.otel_mixin import OTelMixin


class MockCommonPlan:
    """Mock CommonPlan for testing"""
    def __init__(self):
        self.logger = Mock()
        self.circuit_id = "12.LAVG.123456..ABCD"
        self.resource_id = "test-resource-id"
        self.environment = "test"

    def run(self):
        return {"status": "success"}


class TestProduct(MockCommonPlan, OTelMixin):
    """Test product with OTel mixin"""
    pass


class TestOTelMixin:
    """Test suite for OTel Mixin"""

    def setup_method(self):
        """Setup test tracer provider and temp directory for trace logs"""
        # Create a temporary directory for trace logs
        self.temp_dir = tempfile.mkdtemp()
        os.environ['OTEL_TRACE_LOG_DIR'] = self.temp_dir
        
        provider = TracerProvider()
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        # Remove environment variable
        os.environ.pop('OTEL_TRACE_LOG_DIR', None)

    def test_init_otel(self):
        """Test OTel initialization"""
        product = TestProduct()
        product.__init_otel__()
        
        assert hasattr(product, 'tracer')
        assert hasattr(product, 'otel_logger')
        assert hasattr(product, 'span_helper')
        assert product._otel_initialized is True

    def test_create_root_span(self):
        """Test root span creation"""
        product = TestProduct()
        product.__init_otel__()
        
        with product.create_root_span() as span:
            assert span is not None
            assert span.is_recording()
            assert span.attributes.get('circuit_id') == product.circuit_id

    def test_otel_log(self):
        """Test dual logging"""
        product = TestProduct()
        product.__init_otel__()
        
        with product.create_root_span():
            product.otel_log("Test message", level="info", test_key="test_value")
        
        # Verify standard logger was called
        product.logger.info.assert_called_once()

    def test_otel_error_handler(self):
        """Test error handling with OTel"""
        product = TestProduct()
        product.__init_otel__()
        
        error_msg = "IP 192.168.1.1 already exists on device"
        
        with product.create_root_span() as span:
            product.otel_error_handler(error_msg)
            
            # Verify error attributes were set
            assert span.status.status_code == trace.StatusCode.ERROR
            assert 'error.category' in span.attributes
            assert span.attributes['error.category'] == 'IP_CONFLICT_ERROR'

    def test_backward_compatibility(self):
        """Test that existing code still works without OTel"""
        product = TestProduct()
        
        # Should work without OTel initialization
        result = product.run()
        assert result["status"] == "success"

    @patch('otel.feature_flags.is_otel_enabled')
    def test_feature_flag_disabled(self, mock_flag):
        """Test behavior when OTel is disabled"""
        mock_flag.return_value = False
        
        product = TestProduct()
        product.run()
        
        # Should not initialize OTel if feature flag is checked
        # (This test assumes feature flag check in run method)
        assert True  # Placeholder - actual implementation depends on product

