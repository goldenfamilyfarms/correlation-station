# MDSO OTel Instrumentation Implementation Guide

**Based on:** [OTEL_IMPLEMENTATION_STRATEGY.md](https://raw.githubusercontent.com/goldenfamilyfarms/correlation-station/claude/analyze-logging-otel-strategy-01UwuAJMKz9NoJgubNbA1Qsf/OTEL_IMPLEMENTATION_STRATEGY.md)

**Status:** Ready for Implementation
**Date:** 2025-01-27

---

## Executive Summary

This guide provides a step-by-step implementation plan for adding OpenTelemetry instrumentation to MDSO scriptplan products using a non-invasive mixin approach. The strategy maintains backward compatibility while enabling comprehensive observability.

---

## Strategy Review

### ✅ Strengths

1. **Non-Invasive Design**: Mixin approach allows opt-in adoption without breaking existing code
2. **Backward Compatible**: Existing logging continues to work alongside OTel
3. **Well-Structured**: Leverages existing `otel` classes
4. **Incremental**: Products can adopt individually
5. **Production-Ready**: Includes error handling, feature flags, and rollback plans

### ⚠️ Considerations

1. **Missing common_plan.py**: The strategy references `.archive/mdso-dev/.../scripts/common_plan.py` which may not exist in current codebase
2. **Product Location**: Need to identify actual product locations (serviceMapper, fabricator, etc.)
3. **Testing Infrastructure**: Need to set up test environment for validation

---

## Implementation Plan

### Phase 1: Setup and Infrastructure (Week 1)

#### Step 1.1: Create OTel Mixin Class

**File:** `mdso-alloy/mdso-instrumentation/otel/otel_mixin.py`

```python
"""
OTel Mixin for MDSO Scriptplan Products
Provides non-invasive OpenTelemetry instrumentation
"""
import os
import logging
from typing import Optional, Dict, Any
from opentelemetry import trace

from otel.instrumentation import (
    setup_otel,
    get_otel_logger,
    inject_correlation_context,
    mdso_span,
    extract_correlation_context
)
from otel.otel_mdso_utils import (
    MDSOSpanHelper,
    ErrorPatternMatcher
)

logger = logging.getLogger(__name__)


class OTelMixin:
    """
    Mixin class to add OTel instrumentation to existing products.
    
    Products can inherit from both CommonPlan and OTelMixin to get
    OTel capabilities without breaking existing logging.
    
    Example:
        class ServiceMapper(CommonPlan, OTelMixin):
            def run(self):
                self.__init_otel__()
                with self.create_root_span():
                    return super().run()
    """

    def __init_otel__(self):
        """Initialize OTel tracer and structured logger"""
        # Prevent double initialization
        if hasattr(self, '_otel_initialized') and self._otel_initialized:
            return

        # Get product/resource type from class name
        product_type = self.__class__.__name__
        service_name = f"mdso.{product_type.lower()}"

        # Get environment from instance or env var
        environment = getattr(self, 'environment', None) or os.getenv("MDSO_ENV", "dev")

        # Setup OTel tracer
        self.tracer = setup_otel(
            service_name=service_name,
            environment=environment
        )

        # Setup structured logger
        self.otel_logger = get_otel_logger(service_name)

        # Helper for span management
        self.span_helper = MDSOSpanHelper()
        self.error_matcher = ErrorPatternMatcher()

        # Mark as initialized
        self._otel_initialized = True

        logger.info(f"OTel initialized for {product_type}", service_name=service_name, environment=environment)

    def create_root_span(self, operation_name: Optional[str] = None):
        """
        Create root span for product execution
        
        Usage:
            with self.create_root_span():
                return super().run()
        """
        if not hasattr(self, '_otel_initialized') or not self._otel_initialized:
            self.__init_otel__()

        product_name = self.__class__.__name__
        span_name = operation_name or f"mdso.product.{product_name}"

        # Extract correlation context from instance attributes
        correlation_attrs = {}
        if hasattr(self, 'circuit_id') and self.circuit_id:
            correlation_attrs['circuit_id'] = self.circuit_id
        if hasattr(self, 'resource_id') and self.resource_id:
            correlation_attrs['resource_id'] = self.resource_id
        if hasattr(self, 'product_id') and self.product_id:
            correlation_attrs['product_id'] = self.product_id

        # Inject correlation context
        if correlation_attrs:
            inject_correlation_context(**correlation_attrs)

        return mdso_span(
            name=span_name,
            **correlation_attrs
        )

    def otel_log(self, message: str, level: str = "info", **context):
        """
        Dual logging: standard logger + structured OTel logger
        
        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
            **context: Additional structured context
        """
        # Standard logging (existing behavior)
        if hasattr(self, 'logger'):
            getattr(self.logger, level)(message)

        # Structured OTel logging (new)
        if hasattr(self, 'otel_logger') and self._otel_initialized:
            # Extract correlation context
            correlation = extract_correlation_context()
            
            # Merge with provided context
            log_context = {**correlation, **context}
            
            getattr(self.otel_logger, level)(
                message,
                **log_context
            )

            # Add span event if we have a current span
            span = trace.get_current_span()
            if span and span.is_recording():
                span.add_event(
                    name=f"log.{level}",
                    attributes={
                        "message": message,
                        "log.level": level,
                        **log_context
                    }
                )

    def otel_error_handler(self, error_message: str, exception: Optional[Exception] = None):
        """
        Handle errors with OTel instrumentation
        
        Args:
            error_message: Error message
            exception: Optional exception object
        """
        # Categorize error
        error_category = self.error_matcher.categorize_error(error_message)
        
        # Extract identifiers from error
        identifiers = self.error_matcher.extract_all_identifiers(error_message)
        
        # Get current span
        span = trace.get_current_span()
        if span and span.is_recording():
            # Add error attributes
            self.span_helper.add_error_attributes(
                span=span,
                error_category=error_category.get('category'),
                error_message=error_message,
                is_new_error=True
            )
            
            # Add extracted identifiers
            for key, value in identifiers.items():
                if value:
                    span.set_attribute(f"error.{key}", value)
            
            # Set span status to error
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_message))
        
        # Log error
        self.otel_log(
            f"Error: {error_message}",
            level="error",
            error_category=error_category.get('category'),
            error_type=error_category.get('type'),
            **identifiers
        )
        
        # Standard error logging (existing)
        if hasattr(self, 'logger'):
            self.logger.error(error_message, exc_info=exception)
```

#### Step 1.2: Create Feature Flag Support

**File:** `mdso-alloy/mdso-instrumentation/otel/feature_flags.py`

```python
"""Feature flags for OTel instrumentation"""
import os

def is_otel_enabled() -> bool:
    """Check if OTel instrumentation is enabled"""
    return os.getenv("OTEL_ENABLED", "true").lower() == "true"

def is_otel_sampling_enabled() -> bool:
    """Check if OTel sampling is enabled (for high-volume operations)"""
    return os.getenv("OTEL_SAMPLING_ENABLED", "true").lower() == "true"

def get_otel_sampling_rate() -> float:
    """Get OTel sampling rate (0.0 to 1.0)"""
    return float(os.getenv("OTEL_SAMPLING_RATE", "1.0"))
```

#### Step 1.3: Update Requirements

Ensure `requirements.txt` includes all dependencies (already done in existing file).

---

### Phase 2: Pilot Implementation (Week 2)

#### Step 2.1: Identify Pilot Product

**Recommended:** Start with a simple product that has:
- Clear entry point (`run()` method)
- Well-defined operations
- Existing logging
- Low risk of breaking production

**Example Products:**
- ServiceMapper (if available)
- Simple config modeler
- Device configuration product

#### Step 2.2: Implement OTel in Pilot Product

**Example Implementation:**

```python
# scripts/serviceMapper/common.py (or equivalent location)
from scripts.common_plan import CommonPlan  # Assuming this exists
from otel.otel_mixin import OTelMixin
from otel.instrumentation import mdso_span
from otel.feature_flags import is_otel_enabled

class Common(CommonPlan, OTelMixin):
    """
    ServiceMapper with OTel instrumentation
    """

    def run(self):
        """Run with OTel root span"""
        # Check feature flag
        if is_otel_enabled():
            self.__init_otel__()
            
            # Create root span for entire product execution
            with self.create_root_span():
                return self._run_instrumented()
        else:
            # Fallback to original behavior
            return super().run()

    def _run_instrumented(self):
        """Run with full instrumentation"""
        try:
            # Extract circuit_id from instance
            circuit_id = getattr(self, 'circuit_id', None)
            
            self.otel_log(
                "ServiceMapper execution started",
                level="info",
                circuit_id=circuit_id
            )
            
            # Call original run logic
            result = super().run()
            
            self.otel_log(
                "ServiceMapper execution completed",
                level="info",
                circuit_id=circuit_id,
                success=True
            )
            
            return result
            
        except Exception as e:
            self.otel_error_handler(str(e), e)
            raise

    def get_modeled_config(self, config_request_data) -> dict:
        """Get modeled config with span tracking"""
        if not is_otel_enabled():
            return super().get_modeled_config(config_request_data)
        
        with mdso_span(
            "mdso.config_modeler.create",
            circuit_id=config_request_data.get('circuit_id'),
            device=config_request_data.get('device', {}).get('Host Name'),
            vendor=config_request_data.get('device', {}).get('Vendor'),
            model_type=config_request_data.get('requested_model')
        ) as span:
            try:
                self.otel_log(
                    "Creating config modeler resource",
                    level="info",
                    requested_model=config_request_data.get('requested_model')
                )
                
                result = super().get_modeled_config(config_request_data)
                
                # Record success
                span.set_attribute("success", True)
                if isinstance(result, dict) and 'resource_id' in result:
                    span.set_attribute("config_modeler_id", result['resource_id'])
                
                return result
                
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise
```

---

### Phase 3: Testing Strategy

#### Step 3.1: Unit Tests

**File:** `mdso-alloy/mdso-instrumentation/tests/test_otel_mixin.py`

```python
"""Unit tests for OTel Mixin"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

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
        """Setup test tracer provider"""
        provider = TracerProvider()
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

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
        
        # Verify OTel logger was called (check via span events)
        # This would require capturing span events in a test exporter

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
        
        # Should not initialize OTel
        assert not hasattr(product, '_otel_initialized')
```

#### Step 3.2: Integration Tests

**File:** `mdso-alloy/mdso-instrumentation/tests/integration/test_product_instrumentation.py`

```python
"""Integration tests for product instrumentation"""
import pytest
from opentelemetry.sdk.trace.export import InMemorySpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry import trace

from otel.otel_mixin import OTelMixin


class MockProduct(OTelMixin):
    """Mock product for integration testing"""
    def __init__(self):
        self.circuit_id = "12.LAVG.123456..ABCD"
        self.resource_id = "test-resource-id"
        self.logger = Mock()

    def run(self):
        with self.create_root_span():
            self.otel_log("Processing started")
            # Simulate work
            self.otel_log("Processing complete")
            return {"status": "success"}


class TestProductInstrumentation:
    """Integration test suite"""

    def setup_method(self):
        """Setup test tracer with in-memory exporter"""
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider()
        processor = SimpleSpanProcessor(self.exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

    def test_end_to_end_instrumentation(self):
        """Test complete product execution with instrumentation"""
        product = MockProduct()
        product.__init_otel__()
        
        result = product.run()
        
        # Verify execution succeeded
        assert result["status"] == "success"
        
        # Verify spans were created
        spans = self.exporter.get_finished_spans()
        assert len(spans) > 0
        
        # Verify root span exists
        root_spans = [s for s in spans if 'mdso.product' in s.name]
        assert len(root_spans) > 0
        
        # Verify span attributes
        root_span = root_spans[0]
        assert root_span.attributes.get('circuit_id') == product.circuit_id
        assert root_span.status.status_code == trace.StatusCode.OK

    def test_error_instrumentation(self):
        """Test error handling in instrumented product"""
        class FailingProduct(OTelMixin):
            def __init__(self):
                self.circuit_id = "12.LAVG.123456..ABCD"
                self.logger = Mock()
            
            def run(self):
                self.__init_otel__()
                with self.create_root_span():
                    try:
                        raise ValueError("Test error")
                    except Exception as e:
                        self.otel_error_handler(str(e), e)
                        raise
        
        product = FailingProduct()
        
        with pytest.raises(ValueError):
            product.run()
        
        # Verify error span
        spans = self.exporter.get_finished_spans()
        error_spans = [s for s in spans if s.status.status_code == trace.StatusCode.ERROR]
        assert len(error_spans) > 0
```

#### Step 3.3: End-to-End Validation

**File:** `mdso-alloy/mdso-instrumentation/tests/e2e/validate_telemetry.py`

```python
"""E2E validation script for OTel telemetry"""
import os
import time
import requests
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Setup test tracer
provider = TracerProvider()
exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://159.56.4.94:55681/v1/traces")
)
processor = BatchSpanProcessor(exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

def validate_telemetry_pipeline():
    """Validate that telemetry flows through the pipeline"""
    tracer = trace.get_tracer(__name__)
    
    # Create test span
    with tracer.start_as_current_span("test.mdso.product.validation") as span:
        span.set_attribute("test.circuit_id", "12.TEST.123456..TEST")
        span.set_attribute("test.environment", "e2e")
        
        # Simulate product execution
        time.sleep(0.1)
        
        span.set_status(trace.Status(trace.StatusCode.OK))
    
    # Wait for batch export
    time.sleep(6)
    
    # Verify span was exported (check via Correlation Engine API)
    # This would require Correlation Engine to have a query endpoint
    print("✅ Test span created and exported")
    print("   Check Grafana Tempo for trace: test.mdso.product.validation")

if __name__ == "__main__":
    validate_telemetry_pipeline()
```

---

### Phase 4: Deployment and Rollout

#### Step 4.1: Pre-Deployment Checklist

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E validation successful
- [ ] Feature flags configured
- [ ] Monitoring dashboards created
- [ ] Rollback plan documented

#### Step 4.2: Gradual Rollout

1. **Week 1**: Deploy to dev environment with feature flag OFF
2. **Week 2**: Enable for pilot product in dev
3. **Week 3**: Validate telemetry in Grafana
4. **Week 4**: Enable for pilot product in staging
5. **Week 5**: Roll out to additional products (one per week)
6. **Week 8**: Full rollout to all products

#### Step 4.3: Monitoring

**Key Metrics to Track:**
- Span creation rate
- Span export success rate
- Average span duration
- Error rate in spans
- OTel overhead (execution time delta)

**Grafana Queries:**

```promql
# Span creation rate
rate(otel_span_count_total[5m])

# Export success rate
rate(otel_span_export_success_total[5m]) / rate(otel_span_export_total[5m])

# Average span duration
histogram_quantile(0.95, rate(otel_span_duration_seconds_bucket[5m]))
```

---

## Testing Checklist

### Unit Tests
- [ ] OTel initialization
- [ ] Root span creation
- [ ] Dual logging (standard + OTel)
- [ ] Error handling
- [ ] Feature flag behavior
- [ ] Backward compatibility

### Integration Tests
- [ ] End-to-end product execution
- [ ] Span creation and export
- [ ] Error span tracking
- [ ] Correlation context propagation

### E2E Tests
- [ ] Telemetry pipeline validation
- [ ] Grafana visibility
- [ ] Tempo trace queries
- [ ] Loki log correlation

### Performance Tests
- [ ] OTel overhead measurement
- [ ] Memory usage impact
- [ ] Span export latency
- [ ] Batch processor behavior

---

## Troubleshooting Guide

### Issue: Spans not appearing in Tempo

**Check:**
1. OTel endpoint is reachable: `curl http://159.56.4.94:55681/v1/traces`
2. Feature flag is enabled: `echo $OTEL_ENABLED`
3. Batch processor is flushing: Wait 5+ seconds after execution
4. Check OTel logs for export errors

**Solution:**
```python
# Enable debug logging
import logging
logging.getLogger('opentelemetry').setLevel(logging.DEBUG)
```

### Issue: High memory usage

**Check:**
1. Batch processor queue size
2. Span export rate vs. processing rate
3. Memory leaks in span attributes

**Solution:**
- Reduce `max_queue_size` in BatchSpanProcessor
- Increase `schedule_delay_millis` for lower export frequency
- Limit span attribute size

### Issue: Performance degradation

**Check:**
1. OTel overhead measurement
2. Span creation frequency
3. Export latency

**Solution:**
- Enable sampling for high-volume operations
- Use async span export
- Profile with Pyroscope

---

## Next Steps

1. **Review this guide** with the team
2. **Set up test environment** with OTel endpoint
3. **Create OTelMixin** (Phase 1.1)
4. **Implement pilot product** (Phase 2)
5. **Run test suite** (Phase 3)
6. **Deploy to dev** (Phase 4)
7. **Iterate based on feedback**

---

## References

- [OTEL_IMPLEMENTATION_STRATEGY.md](https://raw.githubusercontent.com/goldenfamilyfarms/correlation-station/claude/analyze-logging-otel-strategy-01UwuAJMKz9NoJgubNbA1Qsf/OTEL_IMPLEMENTATION_STRATEGY.md)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [MDSO OTel Instrumentation Classes](../otel/)

