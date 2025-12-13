# MDSO OTel Testing Guide

**Products Location:** Validation branch - `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/`

**Date:** 2025-01-27

---

## Testing Strategy

### Phase 1: Unit Tests (Local)

Test the OTel mixin in isolation without requiring MDSO infrastructure.

### Phase 2: Integration Tests (Dev Environment)

Test products with OTel in a dev MDSO environment.

### Phase 3: E2E Validation (Grafana)

Verify telemetry flows through the entire pipeline.

---

## Phase 1: Unit Tests

### Test 1: OTel Mixin Initialization

**File:** `tests/test_otel_mixin.py` (already created)

```bash
cd seefa-om/mdso-alloy/mdso-instrumentation
pytest tests/test_otel_mixin.py::TestOTelMixin::test_init_otel -v
```

**Expected:**
- ✅ OTel tracer initialized
- ✅ Structured logger created
- ✅ Span helper available
- ✅ Error matcher available

### Test 2: Root Span Creation

```bash
pytest tests/test_otel_mixin.py::TestOTelMixin::test_create_root_span -v
```

**Expected:**
- ✅ Root span created
- ✅ Span has circuit_id attribute (if available)
- ✅ Span is recording

### Test 3: Dual Logging

```bash
pytest tests/test_otel_mixin.py::TestOTelMixin::test_otel_log -v
```

**Expected:**
- ✅ Standard logger called
- ✅ OTel logger called
- ✅ Span event added

### Test 4: Error Handling

```bash
pytest tests/test_otel_mixin.py::TestOTelMixin::test_otel_error_handler -v
```

**Expected:**
- ✅ Error categorized
- ✅ Identifiers extracted
- ✅ Span status set to ERROR
- ✅ Error attributes added

---

## Phase 2: Integration Tests

### Test 1: ServiceMapper with OTel

**Setup:**
```bash
# In validation branch
cd .archive/mdso-dev/charter_sensor_templates/model-definitions/scripts

# Copy OTel classes
cp -r ../../../../seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/ \
     ./otel_instrumentation/

# Install dependencies
pip install -r otel_instrumentation/requirements.txt

# Set environment
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:55681
export MDSO_ENV=dev
```

**Modify ServiceMapper:**
```python
# In serviceMapper/common.py
from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.feature_flags import is_otel_enabled

class Common(CommonPlan, OTelMixin):
    def run(self):
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()
```

**Execute:**
```bash
# Trigger a ServiceMapper product execution via MDSO API
# Or run directly if you have test harness
```

**Verify:**
1. Product executes successfully
2. No errors in logs
3. OTel initialization logged

---

## Phase 3: E2E Validation

### Test 1: Trace Visibility in Tempo

**Steps:**
1. Execute ServiceMapper product
2. Wait 5+ seconds (batch processor delay)
3. Open Grafana Tempo
4. Query: `{service.name="mdso.common"}`

**Expected:**
- ✅ Root span visible: `mdso.product.Common`
- ✅ Span has `circuit_id` attribute
- ✅ Span has `resource_id` attribute
- ✅ Span duration recorded
- ✅ Span status is OK (if successful)

### Test 2: Log Correlation in Loki

**Steps:**
1. Execute product
2. Open Grafana Loki
3. Query: `{service_name="mdso.common"} |= "ServiceMapper"`

**Expected:**
- ✅ Structured logs visible
- ✅ Logs have `trace_id` field
- ✅ Logs have `circuit_id` field
- ✅ Logs linked to traces (click trace_id → opens Tempo)

### Test 3: Error Tracking

**Steps:**
1. Trigger a product that will fail
2. Check Tempo for error spans
3. Check error attributes

**Expected:**
- ✅ Span status is ERROR
- ✅ `error.category` attribute set
- ✅ `error.message` attribute set
- ✅ Error identifiers extracted (circuit_id, tid, etc.)

### Test 4: Correlation Context Propagation

**Steps:**
1. Execute product with circuit_id
2. Check span attributes
3. Check baggage context

**Expected:**
- ✅ `circuit_id` in span attributes
- ✅ `circuit_id` in baggage
- ✅ Context propagated to child spans
- ✅ Context visible in logs

---

## Test Scripts

### Script 1: Validate OTel Setup

**File:** `tests/validate_otel_setup.py`

```python
#!/usr/bin/env python3
"""Validate OTel setup in product environment"""
import os
import sys

# Add product scripts to path
sys.path.insert(0, '.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts')

from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.feature_flags import is_otel_enabled

class TestProduct(OTelMixin):
    def __init__(self):
        self.circuit_id = "12.TEST.123456..TEST"
        self.resource_id = "test-resource-id"
        self.logger = __import__('logging').getLogger("test")

def main():
    print("=" * 50)
    print("OTel Setup Validation")
    print("=" * 50)
    
    # Check feature flag
    enabled = is_otel_enabled()
    print(f"OTel Enabled: {enabled}")
    
    if not enabled:
        print("⚠️  OTel is disabled. Set OTEL_ENABLED=true")
        return
    
    # Test initialization
    product = TestProduct()
    try:
        product.__init_otel__()
        print("✅ OTel initialized successfully")
        print(f"   Service: mdso.testproduct")
        print(f"   Tracer: {type(product.tracer).__name__}")
    except Exception as e:
        print(f"❌ OTel initialization failed: {e}")
        return
    
    # Test root span
    try:
        with product.create_root_span() as span:
            print("✅ Root span created")
            print(f"   Span name: {span.name}")
            print(f"   Attributes: {dict(span.attributes)}")
    except Exception as e:
        print(f"❌ Root span creation failed: {e}")
        return
    
    # Test logging
    try:
        with product.create_root_span():
            product.otel_log("Test message", level="info", test_key="test_value")
        print("✅ Dual logging works")
    except Exception as e:
        print(f"❌ Logging failed: {e}")
        return
    
    # Test error handling
    try:
        with product.create_root_span() as span:
            product.otel_error_handler("IP 192.168.1.1 already exists on device")
        print("✅ Error handling works")
        print(f"   Error category extracted")
    except Exception as e:
        print(f"❌ Error handling failed: {e}")
        return
    
    print()
    print("=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
```

**Run:**
```bash
cd /home/derrick/dev-work/correlation-station
python tests/validate_otel_setup.py
```

### Script 2: End-to-End Telemetry Test

**File:** `tests/e2e/test_product_telemetry.py`

```python
#!/usr/bin/env python3
"""E2E test for product telemetry"""
import os
import time
import sys

sys.path.insert(0, '.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts')

from opentelemetry import trace
from opentelemetry.sdk.trace.export import InMemorySpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from otel_instrumentation.otel_mixin import OTelMixin

class MockCommonPlan:
    def __init__(self):
        self.logger = __import__('logging').getLogger("test")
        self.circuit_id = "12.TEST.123456..TEST"
        self.resource_id = "test-resource-id"
    
    def run(self):
        return {"status": "success"}

class TestProduct(MockCommonPlan, OTelMixin):
    pass

def main():
    print("=" * 50)
    print("E2E Telemetry Test")
    print("=" * 50)
    
    # Setup test tracer with in-memory exporter
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Create and run product
    product = TestProduct()
    product.__init_otel__()
    
    print("Executing product...")
    result = product.run()
    
    # Wait for spans to be exported
    time.sleep(1)
    
    # Get exported spans
    spans = exporter.get_finished_spans()
    
    print(f"\n✅ Product executed: {result['status']}")
    print(f"📊 Spans created: {len(spans)}")
    
    if spans:
        root_span = spans[0]
        print(f"\nRoot Span:")
        print(f"   Name: {root_span.name}")
        print(f"   Status: {root_span.status.status_code}")
        print(f"   Attributes: {dict(root_span.attributes)}")
        print(f"   Duration: {root_span.end_time - root_span.start_time} ns")
    
    print("\n" + "=" * 50)
    print("✅ E2E test complete!")
    print("=" * 50)
    print("\nNext: Check Grafana Tempo for traces in production")

if __name__ == "__main__":
    main()
```

---

## Grafana Queries

### Tempo (Traces)

```traceql
# Find ServiceMapper traces
{service.name="mdso.common"}

# Find traces for specific circuit
{service.name="mdso.common" && circuit_id="12.LAVG.123456..ABCD"}

# Find error traces
{service.name="mdso.common" && status=error}

# Find slow traces (>5 seconds)
{service.name="mdso.common"} | duration > 5s
```

### Loki (Logs)

```logql
# ServiceMapper logs
{service_name="mdso.common"}

# Logs with trace correlation
{service_name="mdso.common"} | json | trace_id!=""

# Error logs
{service_name="mdso.common"} | json | level="error"

# Logs for specific circuit
{service_name="mdso.common"} | json | circuit_id="12.LAVG.123456..ABCD"
```

### Prometheus (Metrics)

```promql
# Span creation rate
rate(otel_span_count_total{service_name="mdso.common"}[5m])

# Error rate
rate(otel_span_errors_total{service_name="mdso.common"}[5m])

# Average duration
histogram_quantile(0.95, rate(otel_span_duration_seconds_bucket{service_name="mdso.common"}[5m]))
```

---

## Test Checklist

### Pre-Implementation
- [ ] OTel classes copied to product location
- [ ] Dependencies installed
- [ ] Environment variables set
- [ ] Feature flag works (can disable)

### Unit Tests
- [ ] OTel initialization test passes
- [ ] Root span creation test passes
- [ ] Dual logging test passes
- [ ] Error handling test passes
- [ ] Backward compatibility test passes

### Integration Tests
- [ ] Product executes with OTel enabled
- [ ] Product executes with OTel disabled
- [ ] No errors in execution
- [ ] Standard logging still works

### E2E Tests
- [ ] Traces visible in Tempo
- [ ] Logs visible in Loki
- [ ] Logs correlated with traces
- [ ] Error spans tracked correctly
- [ ] Correlation context propagated

### Performance Tests
- [ ] OTel overhead < 5%
- [ ] Memory usage acceptable
- [ ] Span export latency < 1s
- [ ] Batch processor working

---

## Troubleshooting

### No Spans in Tempo

**Check:**
1. Feature flag: `echo $OTEL_ENABLED`
2. Endpoint: `curl http://159.56.4.94:55681/v1/traces`
3. Wait time: 5+ seconds after execution
4. OTel logs: Check for export errors

**Debug:**
```python
import logging
logging.getLogger('opentelemetry').setLevel(logging.DEBUG)
```

### Import Errors

**Check:**
1. OTel classes in right location
2. Python path includes scripts directory
3. Dependencies installed

**Fix:**
```bash
cd .archive/mdso-dev/charter_sensor_templates/model-definitions/scripts
export PYTHONPATH=$PWD:$PYTHONPATH
```

### Performance Issues

**Check:**
1. Batch processor queue size
2. Export frequency
3. Span attribute size

**Fix:**
- Reduce `max_queue_size` in BatchSpanProcessor
- Increase `schedule_delay_millis`
- Limit span attribute size

---

## Success Criteria

✅ **All tests pass**
✅ **Traces visible in Grafana**
✅ **Logs correlated with traces**
✅ **Error tracking works**
✅ **Performance acceptable (<5% overhead)**
✅ **Backward compatibility maintained**

---

**Ready to test!** 🧪

