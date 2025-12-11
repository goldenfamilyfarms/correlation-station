# Metrics Cardinality Guide for Sense Applications

**Purpose:** Ensure metrics don't explode cardinality in Prometheus/Mimir while providing useful observability.

**Date:** 2025-12-11
**Applies to:** ARDA, BEORN, PALANTIR, and all Sense microservices

---

## The Cardinality Problem

**High cardinality** = Using unique values (like user IDs, circuit IDs, timestamps) as metric labels.

### ❌ BAD Example (High Cardinality)
```python
request_counter = meter.create_counter("requests_total")
request_counter.add(1, {
    "circuit_id": "33.L1XX.801233..TWCC",  # ❌ Thousands of unique values!
    "user_id": "user_12345",                # ❌ Thousands of unique values!
    "timestamp": "2025-12-11T10:30:45Z"     # ❌ Millions of unique values!
})
```

**Result:** Prometheus creates a **separate time series** for each unique label combination.
- 10,000 circuits × 1,000 users × 1,000,000 timestamps = **10 trillion time series** 💥
- Prometheus crashes or becomes unusably slow

---

## Safe vs Unsafe Labels

### ✅ SAFE Labels (Low Cardinality)

Use these as metric labels:

| Label | Cardinality | Example Values |
|-------|------------|----------------|
| `service.name` | 3-10 | `arda`, `beorn`, `palantir` |
| `endpoint_group` | 10-50 | `/api/v1/circuit`, `/api/v2/eligibility` |
| `product_type` | 5-20 | `eline`, `elan`, `transport`, `managed_service` |
| `environment` | 3-5 | `dev`, `staging`, `prod` |
| `result_type` | 5-10 | `success`, `failure`, `timeout`, `validation_error` |
| `http.method` | 7 | `GET`, `POST`, `PUT`, `DELETE`, `PATCH` |
| `http.status_code` | 50 | `200`, `400`, `404`, `500` |
| `service_type` | 10-30 | `provision`, `disconnect`, `modify` |
| `dependency` | 10-20 | `granite`, `ip_control`, `kong`, `mdso` |

**Total estimated cardinality:** ~10 million time series (manageable)

### ❌ UNSAFE Labels (High Cardinality)

**NEVER use these as metric labels:**

| Label | Why Unsafe | Cardinality | Alternative |
|-------|-----------|------------|-------------|
| `circuit_id` | Unique per circuit | 100,000+ | ✅ Use traces/logs instead |
| `user_id` | Unique per user | 10,000+ | ✅ Use traces/logs instead |
| `product_id` | Unique per product instance | 50,000+ | ✅ Use traces/logs instead |
| `resource_id` | Unique per resource | 100,000+ | ✅ Use traces/logs instead |
| `request_id` | Unique per request | Millions | ✅ Use traces/logs instead |
| `timestamp` | Unique per millisecond | Billions | ✅ Prometheus auto-timestamps |
| `ip_address` | Unique per client IP | 10,000+ | ✅ Use traces/logs instead |
| Raw error messages | Unique per error | 1,000+ | ✅ Use `result_type` grouping |

**Rule of Thumb:** If a label has more than ~100 unique values, it's too high-cardinality for metrics.

---

## Recommended Metrics for Sense Apps

### 1. Request Counter

Track total requests with safe labels:

```python
from sense_common.observability import get_meter

meter = get_meter(__name__)
request_counter = meter.create_counter(
    "sense_requests_total",
    description="Total API requests processed",
    unit="1"
)

# On each request:
request_counter.add(1, {
    "service.name": "arda",
    "endpoint_group": "/api/v1/circuit",
    "http.method": "POST",
    "product_type": "eline",
    "result_type": "success",  # or "failure", "timeout", etc.
})
```

**Cardinality:** ~10 services × 50 endpoints × 7 methods × 20 products × 10 results = **700,000 time series** ✅

### 2. Request Latency Histogram

Track request duration with percentiles:

```python
request_latency = meter.create_histogram(
    "sense_request_duration_seconds",
    description="Request processing time",
    unit="s"
)

# On each request:
start_time = time.time()
# ... process request ...
duration = time.time() - start_time

request_latency.record(duration, {
    "service.name": "arda",
    "endpoint_group": "/api/v1/circuit",
    "product_type": "eline",
    "result_type": "success"
})
```

**Cardinality:** Same as request counter ✅

### 3. Dependency Call Counter

Track external dependency calls (IP Control, Granite, MDSO, Kong):

```python
dependency_call_counter = meter.create_counter(
    "sense_dependency_calls_total",
    description="Total calls to external dependencies",
    unit="1"
)

dependency_call_counter.add(1, {
    "service.name": "beorn",
    "dependency": "granite",
    "operation": "get_circuit_status",
    "result_type": "success"
})
```

**Cardinality:** ~10 services × 20 dependencies × 30 operations × 10 results = **60,000 time series** ✅

### 4. Error Counter

Track errors with categorization:

```python
error_counter = meter.create_counter(
    "sense_errors_total",
    description="Total errors encountered",
    unit="1"
)

error_counter.add(1, {
    "service.name": "palantir",
    "endpoint_group": "/api/v1/compliance",
    "error_category": "validation_error",  # NOT the raw error message!
    "product_type": "eline"
})
```

**Error Categories** (use these instead of raw error text):
- `validation_error`
- `timeout_error`
- `connection_error`
- `authentication_error`
- `authorization_error`
- `not_found_error`
- `internal_error`
- `dependency_error`
- `data_error`

**Cardinality:** ~10 services × 50 endpoints × 10 error categories × 20 products = **100,000 time series** ✅

### 5. Queue Depth Gauge (for async operations)

Track queue depth for background tasks:

```python
queue_depth_gauge = meter.create_observable_gauge(
    "sense_queue_depth",
    callbacks=[lambda options: queue.size()],
    description="Current queue depth",
    unit="1"
)

# Label with queue name
queue_depth_gauge.observe(queue.size(), {
    "service.name": "arda",
    "queue_name": "circuit_provisioning"
})
```

**Cardinality:** ~10 services × 10 queues = **100 time series** ✅

---

## Helper Functions & Decorators

Add to `sense_common/observability/metrics.py`:

### Automatic Request Metrics

```python
from functools import wraps
from sense_common.observability import get_meter
import time

meter = get_meter(__name__)

request_counter = meter.create_counter("sense_requests_total")
request_latency = meter.create_histogram("sense_request_duration_seconds")
error_counter = meter.create_counter("sense_errors_total")

def track_request_metrics(
    service_name: str,
    endpoint_group: str = None,
    product_type: str = None
):
    """
    Decorator to automatically track request metrics

    Usage:
        @track_request_metrics(
            service_name="arda",
            endpoint_group="/api/v1/circuit",
            product_type="eline"
        )
        def create_circuit(circuit_data):
            # Your code here
            return response
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result_type = "success"

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                result_type = "failure"
                error_counter.add(1, {
                    "service.name": service_name,
                    "endpoint_group": endpoint_group or func.__name__,
                    "error_category": categorize_error(e),
                    "product_type": product_type or "unknown"
                })
                raise
            finally:
                duration = time.time() - start_time

                labels = {
                    "service.name": service_name,
                    "endpoint_group": endpoint_group or func.__name__,
                    "result_type": result_type
                }

                if product_type:
                    labels["product_type"] = product_type

                request_counter.add(1, labels)
                request_latency.record(duration, labels)

        return wrapper
    return decorator


def categorize_error(exception: Exception) -> str:
    """Map exception types to error categories"""
    error_type = type(exception).__name__

    if "Validation" in error_type or "ValueError" in error_type:
        return "validation_error"
    elif "Timeout" in error_type:
        return "timeout_error"
    elif "Connection" in error_type or "Network" in error_type:
        return "connection_error"
    elif "Auth" in error_type:
        return "authentication_error"
    elif "NotFound" in error_type or "404" in str(exception):
        return "not_found_error"
    else:
        return "internal_error"
```

### Dependency Call Tracking

```python
def track_dependency_call(
    service_name: str,
    dependency: str,
    operation: str
):
    """
    Context manager for tracking dependency calls

    Usage:
        with track_dependency_call("arda", "granite", "get_circuit"):
            response = granite_client.get_circuit(circuit_id)
    """
    @contextmanager
    def _tracker():
        dependency_call_counter = meter.create_counter("sense_dependency_calls_total")
        dependency_latency = meter.create_histogram("sense_dependency_duration_seconds")

        start_time = time.time()
        result_type = "success"

        try:
            yield
        except Exception:
            result_type = "failure"
            raise
        finally:
            duration = time.time() - start_time

            labels = {
                "service.name": service_name,
                "dependency": dependency,
                "operation": operation,
                "result_type": result_type
            }

            dependency_call_counter.add(1, labels)
            dependency_latency.record(duration, labels)

    return _tracker()
```

---

## Usage Examples

### FastAPI Endpoint (ARDA)

```python
from fastapi import APIRouter
from sense_common.observability.metrics import track_request_metrics

router = APIRouter()

@router.post("/api/v1/circuit")
@track_request_metrics(
    service_name="arda",
    endpoint_group="/api/v1/circuit",
    product_type="eline"
)
async def create_circuit(circuit_data: CircuitCreateRequest):
    """Create a new circuit with automatic metrics tracking"""

    # Call Granite
    with track_dependency_call("arda", "granite", "create_circuit"):
        granite_response = granite_client.create_circuit(circuit_data)

    # Call IP Control
    with track_dependency_call("arda", "ip_control", "allocate_ips"):
        ip_allocation = ip_control_client.allocate_ips(circuit_data)

    return {"circuit_id": granite_response.circuit_id}
```

### Flask Endpoint (BEORN)

```python
from flask import Blueprint
from sense_common.observability.metrics import track_request_metrics

eligibility_bp = Blueprint('eligibility', __name__)

@eligibility_bp.route("/api/v2/eligibility", methods=["POST"])
@track_request_metrics(
    service_name="beorn",
    endpoint_group="/api/v2/eligibility"
)
def check_eligibility():
    """Check service eligibility with automatic metrics"""

    # Your business logic here
    with track_dependency_call("beorn", "granite", "check_device"):
        device_info = granite_client.check_device(device_id)

    return {"eligible": True}
```

---

## Querying Metrics in Prometheus/Grafana

### Request Rate (QPS)
```promql
sum(rate(sense_requests_total{service_name="arda"}[5m])) by (endpoint_group, result_type)
```

### Success Rate (%)
```promql
sum(rate(sense_requests_total{service_name="arda", result_type="success"}[5m]))
/
sum(rate(sense_requests_total{service_name="arda"}[5m]))
* 100
```

### P95 Latency
```promql
histogram_quantile(0.95,
  sum(rate(sense_request_duration_seconds_bucket{service_name="arda"}[5m]))
  by (le, endpoint_group)
)
```

### Error Rate by Category
```promql
sum(rate(sense_errors_total{service_name="arda"}[5m])) by (error_category)
```

### Dependency Success Rate
```promql
sum(rate(sense_dependency_calls_total{dependency="granite", result_type="success"}[5m]))
/
sum(rate(sense_dependency_calls_total{dependency="granite"}[5m]))
* 100
```

---

## Migration Plan for Existing Endpoints

1. **Inventory Endpoints**: List all API routes across ARDA, BEORN, PALANTIR
2. **Categorize**: Group endpoints by functionality (circuit, eligibility, compliance, etc.)
3. **Add Decorators**: Apply `@track_request_metrics()` to high-traffic endpoints first
4. **Test in Dev**: Verify metrics appear in Prometheus
5. **Monitor Cardinality**: Use `topk(100, count by (__name__, service_name) ({__name__=~"sense_.*"}))`
6. **Roll Out to Prod**: Deploy incrementally (ARDA → BEORN → PALANTIR)

---

## Cardinality Monitoring

Monitor your metrics cardinality in Prometheus:

```promql
# Total time series per metric
count by (__name__) ({__name__=~"sense_.*"})

# Top 10 metrics by cardinality
topk(10, count by (__name__) ({__name__=~"sense_.*"}))

# Time series per service
count by (service_name) ({__name__=~"sense_.*"})
```

**Alert if cardinality exceeds 1 million:**
```yaml
- alert: HighMetricsCardinality
  expr: count by (__name__) ({__name__=~"sense_.*"}) > 1000000
  for: 10m
  annotations:
    summary: "Metric {{ $labels.__name__ }} has >1M time series"
```

---

## Summary

### ✅ DO
- Use low-cardinality labels (service, endpoint_group, product_type, result_type)
- Group errors into categories
- Use decorators for automatic tracking
- Store high-cardinality data (circuit_id, user_id) in **traces and logs**

### ❌ DON'T
- Use unique IDs (circuit_id, user_id, request_id) as metric labels
- Use raw error messages as labels
- Use timestamps as labels
- Add labels "just in case" - be intentional

### 📊 Use Traces & Logs For
- Circuit IDs, product IDs, resource IDs
- User IDs, session IDs
- Full error messages
- Request/response payloads
- Detailed debugging information

**Metrics are for aggregated trends. Traces are for individual transactions.**

---

## References
- [Prometheus Best Practices - Cardinality](https://prometheus.io/docs/practices/naming/#labels)
- [OpenTelemetry Metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/)
- [Grafana Cardinality Management](https://grafana.com/docs/grafana-cloud/billing-and-usage/control-prometheus-metrics-usage/)
