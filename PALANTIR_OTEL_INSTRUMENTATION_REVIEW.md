# OpenTelemetry Instrumentation Review - Palantir Sense Apps

**Date:** 2025-12-16
**Reviewer:** Claude Code
**Scope:** seefa-om/sense-apps/palantir OpenTelemetry SDK instrumentation
**Status:** 🟡 Good Foundation - Multiple Improvement Opportunities Identified

---

## Executive Summary

The Palantir application has a **solid OpenTelemetry instrumentation foundation** with comprehensive span creation, baggage propagation, and error categorization. However, there are **several critical improvement opportunities** that could enhance reliability, performance, and observability quality.

### Key Findings

| Category | Status | Priority |
|----------|--------|----------|
| Basic Instrumentation | ✅ Good | - |
| Context Management | ⚠️ Needs Improvement | HIGH |
| Resource Cleanup | ❌ Missing | CRITICAL |
| Span Lifecycle | ⚠️ Inconsistent | HIGH |
| Error Handling | ✅ Good | - |
| Attribute Standards | ⚠️ Partial | MEDIUM |
| Performance | 🟡 Adequate | MEDIUM |
| Metrics Implementation | ⚠️ Underutilized | MEDIUM |

---

## 1. CRITICAL ISSUES

### 1.1 Missing Resource Cleanup and Graceful Shutdown

**Location:** `palantir_app/common/otel/observability.py`, `otel_sense.py`

**Issue:**
The TracerProvider and MeterProvider are never explicitly shut down, which can lead to:
- Lost spans if the application terminates before all batches are exported
- Resource leaks in container environments
- Data loss during deployments or pod restarts

**Current Code (observability.py:135-147):**
```python
tracer_provider = TracerProvider(resource=resource)
# ... add span processors ...
trace.set_tracer_provider(tracer_provider)
# ❌ No shutdown handler registered
```

**Recommendation:**

Add explicit shutdown handlers using `atexit` or Flask/FastAPI lifecycle hooks:

```python
import atexit
from opentelemetry.sdk.trace import TracerProvider

def setup_observability(app, ...):
    # ... existing setup ...

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(...)
    trace.set_tracer_provider(tracer_provider)

    # Add shutdown handler
    def shutdown_telemetry():
        """Gracefully shutdown telemetry on app termination"""
        try:
            tracer_provider.force_flush(timeout_millis=5000)
            tracer_provider.shutdown()
            if meter_provider:
                meter_provider.force_flush(timeout_millis=5000)
                meter_provider.shutdown()
            logger.info("Telemetry shut down successfully")
        except Exception as e:
            logger.error(f"Error during telemetry shutdown: {e}")

    # Register shutdown handler
    atexit.register(shutdown_telemetry)

    # Flask-specific shutdown hook
    if hasattr(app, 'teardown_appcontext'):
        @app.teardown_appcontext
        def shutdown_on_teardown(exception=None):
            if exception:
                # Ensure spans are flushed even on error
                tracer_provider.force_flush(timeout_millis=1000)

    return tracer_provider, meter_provider
```

**Impact:** HIGH - Prevents data loss during deployments and ensures all telemetry is exported

---

### 1.2 Context Attachment Without Detachment

**Location:** Multiple files including `observability.py:270-273`, `otel_sense.py:202-210`

**Issue:**
Context is attached using `context.attach()` but **never detached**, which can cause:
- Context leaks in async/threaded environments
- Incorrect baggage propagation across unrelated requests
- Memory growth over time

**Current Code (observability.py:269-273):**
```python
ctx = context.get_current()
for key, value in extracted_keys.items():
    ctx = baggage.set_baggage(key, str(value), context=ctx)
context.attach(ctx)  # ❌ Never detached
```

**Recommendation:**

Use context tokens and ensure proper cleanup:

```python
def inject_correlation_keys():
    """Extract correlation keys from request and inject into trace context"""
    extracted_keys = {}
    # ... extraction logic ...

    # Set baggage and attach context
    ctx = context.get_current()
    for key, value in extracted_keys.items():
        ctx = baggage.set_baggage(key, str(value), context=ctx)

    # Store token for cleanup
    token = context.attach(ctx)

    # Store token in Flask g for cleanup in after_request
    g._otel_context_token = token

@app.after_request
def cleanup_context(response):
    """Detach context after request completes"""
    if hasattr(g, '_otel_context_token'):
        try:
            context.detach(g._otel_context_token)
        except Exception as e:
            logger.debug(f"Error detaching context: {e}")
    return response
```

**For FastAPI (async):**
```python
async def dispatch(self, request: Request, call_next):
    ctx = context.get_current()
    # ... set baggage ...
    token = context.attach(ctx)

    try:
        response = await call_next(request)
        return response
    finally:
        context.detach(token)  # ✅ Always cleanup
```

**Impact:** HIGH - Prevents context leaks and ensures correct correlation across requests

---

## 2. HIGH PRIORITY IMPROVEMENTS

### 2.1 Inconsistent Span Status Management

**Location:** `dll/granite.py`, `bll/resource_status.py`

**Issue:**
Some spans set status explicitly, others don't. Error spans should always set `StatusCode.ERROR`.

**Current Code (granite.py:86-93):**
```python
with tracer.start_as_current_span("granite.api.put") as span:
    # ... operation ...
    r = requests.put(...)
    span.set_attribute("http.status_code", r.status_code)
    # ⚠️ No status set - defaults to UNSET instead of OK
    if r.status_code in [200, 204]:
        return r.json()
```

**Recommendation:**

Always explicitly set span status:

```python
from opentelemetry.trace import Status, StatusCode

with tracer.start_as_current_span("granite.api.put") as span:
    span.set_attribute("granite.operation", "put")
    span.set_attribute("granite.endpoint", endpoint)

    try:
        r = requests.put(url, headers=headers, json=payload, ...)
        span.set_attribute("http.status_code", r.status_code)

        if r.status_code in [200, 204]:
            span.set_status(Status(StatusCode.OK))  # ✅ Explicit success
            return r.json()
        else:
            # HTTP error response
            span.set_status(Status(StatusCode.ERROR, f"HTTP {r.status_code}"))
            span.record_exception(HTTPError(r.text))
            # ... error handling ...
    except Exception as e:
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.record_exception(e)
        raise
```

**Impact:** MEDIUM-HIGH - Improves error tracking and SLI/SLO calculations

---

### 2.2 Duplicate Instrumentation Initialization

**Location:** `palantir_app/__init__.py:88-99`

**Issue:**
Both `setup_observability()` (comprehensive) and potentially `setup_otel_sense()` (lightweight) are available, but only one should be used.

**Current Code:**
```python
# Uses comprehensive observability
setup_observability(
    app,
    service_name="palantir",
    service_version=version.strip(),
    environment=os.getenv("DEPLOYMENT_ENV", "prod")
)
```

**Recommendation:**

1. **Standardize on one approach** - `setup_observability()` appears more feature-complete
2. Document when to use each (if both are needed)
3. Prevent double-instrumentation:

```python
# Add guard against double initialization
_OTEL_INITIALIZED = False

def setup_observability(app, ...):
    global _OTEL_INITIALIZED

    if _OTEL_INITIALIZED:
        logger.warning("OpenTelemetry already initialized, skipping")
        return trace.get_tracer_provider(), metrics.get_meter_provider()

    # ... setup code ...

    _OTEL_INITIALIZED = True
    return tracer_provider, meter_provider
```

**Impact:** MEDIUM - Prevents accidental double-instrumentation and resource waste

---

### 2.3 Missing Span Kind Specifications

**Location:** Multiple span creation sites

**Issue:**
Spans don't specify their kind (CLIENT, SERVER, INTERNAL), making it harder to understand trace topology.

**Recommendation:**

Set appropriate span kinds:

```python
from opentelemetry.trace import SpanKind

# For HTTP client calls
with tracer.start_as_current_span(
    "granite.api.put",
    kind=SpanKind.CLIENT  # ✅ This is an HTTP client call
) as span:
    requests.put(...)

# For internal operations
with tracer.start_as_current_span(
    "palantir.resource_status.get_resource_status",
    kind=SpanKind.INTERNAL  # ✅ Business logic
) as span:
    # ... business logic ...

# For API endpoints (already handled by FlaskInstrumentor, but can be explicit)
with tracer.start_as_current_span(
    "palantir.compliance.provisioning",
    kind=SpanKind.SERVER  # ✅ Incoming HTTP request
) as span:
    # ... endpoint handler ...
```

**Impact:** MEDIUM - Improves trace visualization and service dependency mapping

---

## 3. MEDIUM PRIORITY IMPROVEMENTS

### 3.1 Underutilized Metrics

**Location:** `observability.py:163-176`

**Issue:**
Metrics provider is initialized but **no custom metrics are created**. Only infrastructure metrics are collected.

**Current State:**
```python
# Metrics provider created but unused
meter_provider = MeterProvider(resource=resource, metric_readers=[...])
metrics.set_meter_provider(meter_provider)
# ❌ No business metrics defined
```

**Recommendation:**

Add business-critical metrics:

```python
# In observability.py or separate metrics.py
def create_business_metrics(service_name: str):
    """Create service-specific business metrics"""
    meter = metrics.get_meter(service_name)

    # Request metrics
    request_counter = meter.create_counter(
        name="palantir.requests.total",
        description="Total number of requests by endpoint",
        unit="1"
    )

    request_duration = meter.create_histogram(
        name="palantir.request.duration",
        description="Request duration in seconds",
        unit="s"
    )

    # Granite API metrics
    granite_api_duration = meter.create_histogram(
        name="palantir.granite.api.duration",
        description="Granite API call duration",
        unit="s"
    )

    granite_api_errors = meter.create_counter(
        name="palantir.granite.api.errors",
        description="Granite API error count by operation",
        unit="1"
    )

    # MDSO API metrics
    mdso_api_duration = meter.create_histogram(
        name="palantir.mdso.api.duration",
        description="MDSO API call duration",
        unit="s"
    )

    # Compliance metrics
    compliance_operations = meter.create_counter(
        name="palantir.compliance.operations",
        description="Compliance operations by type and result",
        unit="1"
    )

    # Resource status metrics
    resource_status_poll_count = meter.create_counter(
        name="palantir.resource_status.polls",
        description="Number of MDSO resource status polls",
        unit="1"
    )

    return {
        "request_counter": request_counter,
        "request_duration": request_duration,
        "granite_api_duration": granite_api_duration,
        "granite_api_errors": granite_api_errors,
        "mdso_api_duration": mdso_api_duration,
        "compliance_operations": compliance_operations,
        "resource_status_poll_count": resource_status_poll_count,
    }
```

**Usage in code:**

```python
# In granite.py
import time
from palantir_app.common.otel import get_meter

meter = get_meter(__name__)
granite_api_duration = meter.create_histogram("palantir.granite.api.duration", unit="s")
granite_api_errors = meter.create_counter("palantir.granite.api.errors", unit="1")

def granite_put(endpoint, payload, ...):
    start_time = time.perf_counter()

    with tracer.start_as_current_span("granite.api.put") as span:
        try:
            r = requests.put(url, ...)
            duration = time.perf_counter() - start_time

            # Record metrics
            granite_api_duration.record(
                duration,
                attributes={
                    "operation": "put",
                    "endpoint": endpoint,
                    "status_code": r.status_code
                }
            )

            if r.status_code not in [200, 204]:
                granite_api_errors.add(
                    1,
                    attributes={
                        "operation": "put",
                        "endpoint": endpoint,
                        "status_code": r.status_code
                    }
                )

            return r.json()
        except Exception as e:
            duration = time.perf_counter() - start_time
            granite_api_duration.record(duration, attributes={"operation": "put", "error": type(e).__name__})
            granite_api_errors.add(1, attributes={"operation": "put", "error": type(e).__name__})
            raise
```

**Impact:** MEDIUM - Enables business KPI tracking and SLI/SLO monitoring

---

### 3.2 Attribute Naming Inconsistency

**Location:** Throughout codebase

**Issue:**
Mix of attribute naming conventions:
- `granite.circuit_id` (dot notation)
- `mdso.circuit_id` (dot notation)
- `http.status_code` (standard semantic conventions)
- `sense.service` (custom)

**Recommendation:**

Follow OpenTelemetry semantic conventions and be consistent:

**Standard Semantic Conventions:**
```python
# HTTP
"http.method" = "PUT"
"http.status_code" = 200
"http.url" = "https://granite.example.com/api/v1/paths"
"http.request.body.size" = 1024

# Network
"network.protocol.name" = "http"
"network.protocol.version" = "1.1"

# Server
"server.address" = "granite.example.com"
"server.port" = 443
```

**Custom Attributes (use consistent namespace):**
```python
# Use a consistent namespace for all custom attributes
"charter.circuit_id" = "80.L1XX.005054..CHTR"
"charter.product_id" = "12345"
"charter.resource_id" = "uuid-here"
"charter.service_type" = "eline"
"charter.order_type" = "provision"

# System-specific namespaces
"granite.operation" = "put"
"granite.endpoint" = "/api/v1/paths"
"granite.best_effort" = true

"mdso.orch_state" = "active"
"mdso.provider_resource_id" = "provider-123"

"palantir.operation" = "compliance_provisioning"
"palantir.compliance.remediation_flag" = true
```

**Impact:** MEDIUM - Improves consistency and compatibility with OTel tooling

---

### 3.3 BatchSpanProcessor Configuration Tuning

**Location:** `observability.py:141-146`, `otel_sense.py:106-111`

**Issue:**
Two different configurations exist with different queue sizes, which is confusing.

**Current Configurations:**

`observability.py` (comprehensive):
```python
BatchSpanProcessor(
    otlp_span_exporter,
    max_queue_size=2048,
    max_export_batch_size=512,
    schedule_delay_millis=5000,
)
```

`otel_sense.py` (lightweight):
```python
BatchSpanProcessor(
    otlp_exporter,
    max_queue_size=1024,  # Reduced from 2048
    max_export_batch_size=256,  # Reduced from 512
    schedule_delay_millis=5000,
)
```

**Recommendation:**

1. **Standardize on one configuration** or clearly document when to use each
2. **Tune based on actual traffic patterns:**

```python
# For high-throughput services (many requests/sec)
HIGH_THROUGHPUT_CONFIG = {
    "max_queue_size": 4096,      # Larger queue for burst traffic
    "max_export_batch_size": 512,
    "schedule_delay_millis": 3000,  # Export more frequently
    "export_timeout_millis": 30000,
}

# For standard services
STANDARD_CONFIG = {
    "max_queue_size": 2048,
    "max_export_batch_size": 256,
    "schedule_delay_millis": 5000,
    "export_timeout_millis": 30000,
}

# For low-traffic services
LOW_TRAFFIC_CONFIG = {
    "max_queue_size": 512,
    "max_export_batch_size": 128,
    "schedule_delay_millis": 10000,  # Less frequent exports
    "export_timeout_millis": 30000,
}

# Select based on environment or service characteristics
def get_span_processor_config():
    env = os.getenv("DEPLOYMENT_ENV", "dev")
    traffic_profile = os.getenv("TRAFFIC_PROFILE", "standard")

    if traffic_profile == "high":
        return HIGH_THROUGHPUT_CONFIG
    elif traffic_profile == "low":
        return LOW_TRAFFIC_CONFIG
    else:
        return STANDARD_CONFIG
```

**Impact:** MEDIUM - Optimizes performance and resource usage

---

### 3.4 Error Categorization Could Be Enhanced

**Location:** `mdso_patterns.py:118-202`

**Issue:**
Good error categorization exists, but could be more comprehensive.

**Current Categories:**
- CONNECTIVITY_ERROR
- GRANITE_ERROR
- IP_VALIDATION_ERROR
- IP_CONFLICT_ERROR
- DEVICE_ROLE_ERROR
- NODE_ERROR
- UNKNOWN_ERROR

**Recommendation:**

Add more categories and use OpenTelemetry exception events:

```python
class ErrorCategorizer:
    ERROR_CATEGORIES = {
        "CONNECTIVITY_ERROR": {
            "patterns": [r"unable to connect", r"connection refused", r"connection timeout"],
            "severity": "CRITICAL",
            "retryable": True,
        },
        "AUTHENTICATION_ERROR": {
            "patterns": [r"authentication failed", r"invalid credentials", r"unauthorized"],
            "severity": "ERROR",
            "retryable": False,
        },
        "TIMEOUT_ERROR": {
            "patterns": [r"timeout", r"timed out"],
            "severity": "ERROR",
            "retryable": True,
        },
        "VALIDATION_ERROR": {
            "patterns": [r"validation failed", r"invalid.*format", r"does not appear to be"],
            "severity": "WARNING",
            "retryable": False,
        },
        "RESOURCE_NOT_FOUND": {
            "patterns": [r"not found", r"does not exist", r"no records found"],
            "severity": "WARNING",
            "retryable": False,
        },
        "CONFLICT_ERROR": {
            "patterns": [r"already exists", r"conflict", r"duplicate"],
            "severity": "WARNING",
            "retryable": False,
        },
        "CONFIGURATION_ERROR": {
            "patterns": [r"invalid configuration", r"misconfigured"],
            "severity": "ERROR",
            "retryable": False,
        },
        # ... existing categories ...
    }

    def categorize_with_attributes(self, error_message: str) -> Dict[str, Any]:
        """Enhanced categorization with span-ready attributes"""
        category_info = self.categorize(error_message)
        identifiers = MDSOPatterns.extract_all_identifiers(error_message)

        return {
            "error.type": category_info["type"],
            "error.category": category_info["category"],
            "error.severity": category_info["severity"],
            "error.retryable": category_info.get("retryable", False),
            "error.circuit_id": identifiers.get("circuit_id"),
            "error.resource_id": identifiers.get("resource_id"),
            "error.device_fqdn": identifiers.get("fqdn"),
        }
```

**Impact:** MEDIUM - Better error analysis and automated retry logic

---

### 3.5 Missing Baggage Size Limits

**Location:** `observability.py`, `otel_sense.py`

**Issue:**
Baggage can grow unbounded, potentially causing header size issues (W3C recommends max 8KB).

**Recommendation:**

Add baggage size validation:

```python
MAX_BAGGAGE_VALUE_SIZE = 1024  # 1KB per value
MAX_TOTAL_BAGGAGE_SIZE = 8192  # 8KB total

def set_baggage_with_limit(key: str, value: str, context_obj=None):
    """Set baggage with size validation"""
    if len(value) > MAX_BAGGAGE_VALUE_SIZE:
        logger.warning(
            f"Baggage value for '{key}' exceeds limit ({len(value)} > {MAX_BAGGAGE_VALUE_SIZE}), truncating"
        )
        value = value[:MAX_BAGGAGE_VALUE_SIZE] + "..."

    ctx = context_obj or context.get_current()

    # Check total baggage size
    current_baggage = baggage.get_all(ctx)
    current_size = sum(len(k) + len(v) for k, v in current_baggage.items())
    new_size = current_size + len(key) + len(value)

    if new_size > MAX_TOTAL_BAGGAGE_SIZE:
        logger.warning(
            f"Total baggage size would exceed limit ({new_size} > {MAX_TOTAL_BAGGAGE_SIZE}), skipping '{key}'"
        )
        return ctx

    return baggage.set_baggage(key, value, context=ctx)
```

**Impact:** LOW-MEDIUM - Prevents HTTP header size issues

---

## 4. LOW PRIORITY / NICE-TO-HAVE

### 4.1 Add Sampling Configuration

**Current:** No sampling configured (all spans exported)

**Recommendation:**

Add configurable sampling for high-traffic environments:

```python
from opentelemetry.sdk.trace.sampling import (
    ParentBased,
    TraceIdRatioBased,
    ALWAYS_ON,
    ALWAYS_OFF
)

def get_sampler(environment: str, service_name: str):
    """Get appropriate sampler based on environment"""

    if environment == "dev":
        # Always sample in dev
        return ALWAYS_ON

    elif environment == "prod":
        # Sample 10% in prod, but always sample errors
        return ParentBased(
            root=TraceIdRatioBased(0.1),  # 10% sampling
            # Always sample if parent was sampled
            remote_parent_sampled=ALWAYS_ON,
            remote_parent_not_sampled=TraceIdRatioBased(0.1),
        )

    else:
        # Staging: 50% sampling
        return ParentBased(root=TraceIdRatioBased(0.5))

# Use in setup
tracer_provider = TracerProvider(
    resource=resource,
    sampler=get_sampler(environment, service_name)
)
```

---

### 4.2 Add Trace Context Injection for Outbound HTTP Calls

**Issue:** Auto-instrumentation handles this, but explicit injection provides more control

**Recommendation:**

```python
from opentelemetry.propagate import inject

def granite_put(endpoint, payload, ...):
    headers = get_hydra_headers()

    # Explicitly inject trace context
    inject(headers)  # Adds traceparent, tracestate headers

    with tracer.start_as_current_span("granite.api.put") as span:
        r = requests.put(url, headers=headers, json=payload, ...)
        # ...
```

---

### 4.3 Add Structured Logging Integration

**Current:** Some structlog usage but not fully integrated with traces

**Recommendation:**

Ensure all logs include trace context:

```python
import structlog

def configure_logging_with_traces():
    """Configure structlog with OTel trace context"""

    def add_trace_context(logger, method_name, event_dict):
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")

        # Add baggage
        for key in ["circuit_id", "product_id", "resource_id"]:
            value = baggage.get_baggage(key)
            if value:
                event_dict[key] = value

        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_trace_context,  # ✅ Add trace context to all logs
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )
```

---

## 5. PERFORMANCE CONSIDERATIONS

### Current Performance Profile

| Metric | Current | Recommendation |
|--------|---------|----------------|
| Span Queue Size | 2048 (observability) / 1024 (otel_sense) | 2048 for prod, 1024 for dev |
| Batch Size | 512 / 256 | 256 (good balance) |
| Export Interval | 5000ms | 3000-5000ms (adjust based on latency requirements) |
| Payload Limit | 10KB (otel_sense) | Good |
| Context Cleanup | ❌ Missing | ✅ Add |

### Memory Impact

Estimated memory per span: ~2-4KB
Max queued spans: 2048
**Total memory for span queue: ~4-8MB** ✅ Acceptable

---

## 6. RECOMMENDED IMPLEMENTATION PLAN

### Phase 1: Critical Fixes (Week 1)
**Priority: CRITICAL**

1. ✅ Add resource cleanup and graceful shutdown
2. ✅ Fix context attachment/detachment
3. ✅ Standardize span status management
4. ✅ Prevent double-instrumentation

**Files to modify:**
- `palantir_app/common/otel/observability.py`
- `palantir_app/common/otel/otel_sense.py`
- `palantir_app/__init__.py`

### Phase 2: High Priority Improvements (Week 2)
**Priority: HIGH**

1. ✅ Add span kinds to all manual spans
2. ✅ Implement business metrics
3. ✅ Standardize attribute naming
4. ✅ Add baggage size limits

**Files to modify:**
- `palantir_app/dll/granite.py`
- `palantir_app/bll/resource_status.py`
- `palantir_app/apis/v1/compliance_provisioning.py`
- Create new: `palantir_app/common/otel/metrics.py`

### Phase 3: Medium Priority Enhancements (Week 3)
**Priority: MEDIUM**

1. ✅ Tune BatchSpanProcessor config
2. ✅ Enhance error categorization
3. ✅ Add sampling configuration
4. ✅ Improve structured logging integration

**Files to modify:**
- `palantir_app/common/otel/mdso_patterns.py`
- All span creation sites

### Phase 4: Documentation and Testing (Week 4)
**Priority: MEDIUM**

1. ✅ Document instrumentation patterns
2. ✅ Add unit tests for OTel utilities
3. ✅ Create runbook for troubleshooting
4. ✅ Add integration tests

---

## 7. CODE EXAMPLES - BEFORE & AFTER

### Example 1: Granite API Call

**BEFORE:**
```python
def granite_put(endpoint, payload, best_effort=False, calling_function="not specified"):
    with tracer.start_as_current_span("granite.api.put") as span:
        span.set_attribute("granite.operation", "put")
        span.set_attribute("granite.endpoint", endpoint)

        headers = get_hydra_headers()
        url = f"{granite_base_url}{endpoint}"

        try:
            r = requests.put(url, headers=headers, json=payload, verify=False, timeout=60)
            span.set_attribute("http.status_code", r.status_code)

            if r.status_code in [200, 204]:
                return r.json()
            # ... error handling ...
        except (ConnectionError, requests.ConnectionError) as exception:
            set_span_error(exception)
            abort(504, f"Connection error: {exception}")
```

**AFTER:**
```python
from opentelemetry.trace import Status, StatusCode, SpanKind
import time

def granite_put(endpoint, payload, best_effort=False, calling_function="not specified"):
    start_time = time.perf_counter()

    with tracer.start_as_current_span(
        "granite.api.put",
        kind=SpanKind.CLIENT  # ✅ Specify span kind
    ) as span:
        # Set attributes
        span.set_attribute("granite.operation", "put")
        span.set_attribute("granite.endpoint", endpoint)
        span.set_attribute("granite.best_effort", best_effort)
        span.set_attribute("granite.calling_function", calling_function)

        # Extract and set circuit_id if present
        if isinstance(payload, dict):
            cid = payload.get("PATH_NAME") or payload.get("CIRC_PATH_INST_ID")
            if cid:
                span.set_attribute("charter.circuit_id", cid)

        headers = get_hydra_headers()
        inject(headers)  # ✅ Explicit trace context injection
        url = f"{granite_base_url}{endpoint}"

        try:
            add_span_event("granite.api.call.start", endpoint=endpoint)

            r = requests.put(url, headers=headers, json=payload, verify=False, timeout=60)
            duration = time.perf_counter() - start_time

            # Set HTTP attributes
            span.set_attribute("http.method", "PUT")
            span.set_attribute("http.url", url)
            span.set_attribute("http.status_code", r.status_code)
            span.set_attribute("http.request_duration_seconds", duration)

            # Record metric
            granite_api_duration.record(
                duration,
                attributes={
                    "operation": "put",
                    "endpoint": endpoint,
                    "status_code": r.status_code
                }
            )

            if r.status_code in [200, 204]:
                span.set_status(Status(StatusCode.OK))  # ✅ Explicit success status
                add_span_event("granite.api.call.success", status_code=r.status_code)
                return r.json()
            else:
                # Non-success HTTP status
                span.set_status(Status(StatusCode.ERROR, f"HTTP {r.status_code}"))
                error_msg = f"Granite API error: {r.status_code}"

                # Categorize error
                error_context = error_categorizer.categorize_with_attributes(r.text)
                for key, value in error_context.items():
                    if value:
                        span.set_attribute(key, value)

                # Record error metric
                granite_api_errors.add(
                    1,
                    attributes={
                        "operation": "put",
                        "status_code": r.status_code,
                        "error_category": error_context.get("error.category", "UNKNOWN")
                    }
                )

                if best_effort:
                    return {"errorStatusCode": r.status_code, "errorStatusMessage": error_msg}
                else:
                    abort(502, error_msg)

        except (ConnectionError, requests.ConnectionError) as exception:
            duration = time.perf_counter() - start_time

            # Set error status
            span.set_status(Status(StatusCode.ERROR, str(exception)))
            span.record_exception(exception)  # ✅ Record exception with stacktrace

            # Categorize error
            error_context = error_categorizer.categorize_with_attributes(str(exception))
            for key, value in error_context.items():
                if value:
                    span.set_attribute(key, value)

            # Record metric
            granite_api_errors.add(
                1,
                attributes={
                    "operation": "put",
                    "error_type": type(exception).__name__,
                    "error_category": error_context.get("error.category", "CONNECTIVITY_ERROR")
                }
            )

            abort(504, f"Connection error to Granite: {exception}")

        except requests.ReadTimeout as exception:
            duration = time.perf_counter() - start_time

            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            span.record_exception(exception)
            span.set_attribute("error.type", "timeout")
            span.set_attribute("error.timeout_seconds", 60)

            granite_api_errors.add(
                1,
                attributes={
                    "operation": "put",
                    "error_type": "timeout"
                }
            )

            abort(504, f"Timeout waiting for Granite response: {exception}")
```

### Example 2: Context Management

**BEFORE:**
```python
@app.before_request
def inject_correlation_keys():
    extracted_keys = {}
    for key in baggage_keys:
        header_value = request.headers.get(f"X-{key}")
        if header_value:
            extracted_keys[key] = header_value

    ctx = context.get_current()
    for key, value in extracted_keys.items():
        ctx = baggage.set_baggage(key, str(value), context=ctx)
    context.attach(ctx)  # ❌ Never detached
```

**AFTER:**
```python
@app.before_request
def inject_correlation_keys():
    """Extract correlation keys and attach context"""
    extracted_keys = {}

    # Extract from headers
    for key in baggage_keys:
        header_value = (
            request.headers.get(f"X-{key}") or
            request.headers.get(f"x-{key}") or
            request.headers.get(key)
        )
        if header_value:
            extracted_keys[key] = header_value

    # Extract from JSON (with size limit)
    if request.is_json and request.content_length and request.content_length < 10240:
        try:
            json_data = request.get_json(silent=True)
            if json_data:
                for key in baggage_keys:
                    if key not in extracted_keys:
                        json_value = json_data.get(key)
                        if json_value:
                            extracted_keys[key] = json_value
        except Exception:
            pass

    # Set baggage with size limits
    ctx = context.get_current()
    for key, value in extracted_keys.items():
        ctx = set_baggage_with_limit(key, str(value), ctx)  # ✅ Size validation

    # Attach context and store token for cleanup
    token = context.attach(ctx)  # ✅ Store token
    g._otel_context_token = token

    # Store in Flask g for easy access
    for key, value in extracted_keys.items():
        setattr(g, key, value)

    # Add to current span
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in extracted_keys.items():
            span.set_attribute(f"charter.{key}", str(value))

        span.set_attribute("http.route", request.endpoint or request.path)
        span.set_attribute("http.method", request.method)

@app.after_request
def cleanup_and_inject_trace_id(response):
    """Cleanup context and inject trace ID into response"""
    # Detach context
    if hasattr(g, '_otel_context_token'):
        try:
            context.detach(g._otel_context_token)  # ✅ Cleanup
        except Exception as e:
            logger.debug(f"Error detaching context: {e}")

    # Inject trace ID into response headers
    span = trace.get_current_span()
    if span and span.is_recording():
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Span-Id"] = span_id

    return response
```

---

## 8. TESTING RECOMMENDATIONS

### Unit Tests

```python
# tests/test_otel_instrumentation.py
import pytest
from opentelemetry import trace, baggage, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, InMemorySpanExporter
from palantir_app.common.otel import setup_observability

@pytest.fixture
def test_tracer():
    """Create test tracer with in-memory exporter"""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield trace.get_tracer(__name__), exporter

    # Cleanup
    provider.shutdown()

def test_span_creation_with_attributes(test_tracer):
    """Test that spans are created with correct attributes"""
    tracer, exporter = test_tracer

    with tracer.start_as_current_span("test.operation") as span:
        span.set_attribute("charter.circuit_id", "TEST-CID")
        span.set_attribute("charter.operation", "test")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.name == "test.operation"
    assert span.attributes["charter.circuit_id"] == "TEST-CID"
    assert span.attributes["charter.operation"] == "test"

def test_context_cleanup():
    """Test that context is properly cleaned up"""
    ctx = context.get_current()
    ctx = baggage.set_baggage("test_key", "test_value", context=ctx)

    token = context.attach(ctx)
    assert baggage.get_baggage("test_key") == "test_value"

    context.detach(token)
    # After detach, baggage should not leak to next request
    assert baggage.get_baggage("test_key") is None

def test_error_categorization():
    """Test error categorization logic"""
    from palantir_app.common.otel.mdso_patterns import ErrorCategorizer

    categorizer = ErrorCategorizer()

    # Test connectivity error
    result = categorizer.categorize("unable to connect to device")
    assert result["category"] == "CONNECTIVITY_ERROR"
    assert result["severity"] == "CRITICAL"

    # Test IP validation error
    result = categorizer.categorize("10.0.0.1 does not appear to be an IPv4 or IPv6 address")
    assert result["category"] == "IP_VALIDATION_ERROR"

def test_baggage_size_limits():
    """Test that baggage size limits are enforced"""
    from palantir_app.common.otel import set_baggage_with_limit

    # Test value size limit
    large_value = "x" * 2000
    ctx = set_baggage_with_limit("large_key", large_value)
    value = baggage.get_baggage("large_key", context=ctx)
    assert len(value) <= 1024 + 3  # 1KB + "..."
```

### Integration Tests

```python
# tests/integration/test_otel_end_to_end.py
def test_granite_api_call_creates_spans(client, test_tracer):
    """Test that Granite API calls create proper spans"""
    tracer, exporter = test_tracer

    # Make request to endpoint that calls Granite
    response = client.post('/palantir/v1/compliance/provisioning/TEST-CID', json={
        "service_request_order_type": "New Install",
        "order_type": "New",
        "product_name": "Fiber Internet Access"
    })

    # Check spans
    spans = exporter.get_finished_spans()

    # Should have multiple spans: endpoint, BLL, Granite call
    assert len(spans) >= 2

    # Check Granite span
    granite_spans = [s for s in spans if "granite" in s.name]
    assert len(granite_spans) > 0

    granite_span = granite_spans[0]
    assert granite_span.kind == SpanKind.CLIENT
    assert "http.status_code" in granite_span.attributes
    assert "charter.circuit_id" in granite_span.attributes
```

---

## 9. MONITORING AND ALERTING

### Recommended Alerts

```yaml
# alerts/otel_instrumentation.yaml
groups:
  - name: opentelemetry
    rules:
      - alert: HighSpanDropRate
        expr: rate(otel_span_processor_spans_dropped_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High span drop rate detected"
          description: "Span processor is dropping spans (rate: {{ $value }}/sec)"

      - alert: ExporterFailureRate
        expr: rate(otel_exporter_export_failed_total[5m]) > 1
        for: 5m
        labels:
          severity: error
        annotations:
          summary: "OTEL exporter failing"
          description: "Exporter failures detected (rate: {{ $value }}/sec)"

      - alert: HighGraniteAPILatency
        expr: histogram_quantile(0.95, rate(palantir_granite_api_duration_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High Granite API latency"
          description: "P95 latency is {{ $value }}s (threshold: 5s)"

      - alert: GraniteAPIErrorRate
        expr: rate(palantir_granite_api_errors_total[5m]) / rate(palantir_granite_api_calls_total[5m]) > 0.05
        for: 5m
        labels:
          severity: error
        annotations:
          summary: "High Granite API error rate"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
```

---

## 10. SUMMARY & NEXT STEPS

### Summary of Findings

✅ **Strengths:**
- Comprehensive span creation across critical paths
- Good error categorization with MDSO patterns
- Proper baggage propagation for correlation
- Lightweight instrumentation to avoid resource issues

⚠️ **Critical Issues:**
- Missing resource cleanup (data loss risk)
- Context leaks from missing detach
- Inconsistent span status management

📋 **Recommended Actions:**

1. **Immediate (Week 1):**
   - Implement graceful shutdown
   - Fix context management
   - Add span status to all operations

2. **Short-term (Weeks 2-3):**
   - Add business metrics
   - Standardize attribute naming
   - Enhance error categorization

3. **Medium-term (Week 4+):**
   - Add sampling configuration
   - Improve documentation
   - Create comprehensive test suite

### Success Metrics

- ✅ Zero span drops under normal load
- ✅ < 1% span export failure rate
- ✅ All critical paths instrumented
- ✅ Context properly managed (no leaks)
- ✅ Consistent attribute naming across all spans
- ✅ Business metrics available for SLI/SLO tracking

---

## 11. ADDITIONAL RESOURCES

### OpenTelemetry Best Practices
- [OTel Python SDK Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Performance Best Practices](https://opentelemetry.io/docs/specs/otel/performance/)

### Internal Resources
- Existing documentation: `seefa-om/docs/SENSE_OTEL_IMPLEMENTATION_SUMMARY.md`
- Instrumentation analysis: `seefa-om/sense-apps/OTEL_INSTRUMENTATION_ANALYSIS.md`
- MDSO patterns reference: `palantir_app/common/otel/mdso_patterns.py`

---

**Review Date:** 2025-12-16
**Next Review:** 2026-01-16 (after Phase 1-2 implementation)

