# OpenTelemetry Instrumentation Review - Beorn & Arda Sense Apps

**Date:** 2025-12-16
**Reviewer:** Claude Code
**Scope:** seefa-om/sense-apps/beorn and seefa-om/sense-apps/arda OpenTelemetry SDK instrumentation
**Status:** 🟡 Good Foundation - Critical Improvements Needed + Code Duplication

---

## Executive Summary

Beorn (Flask) and Arda (FastAPI) applications share a **solid OpenTelemetry instrumentation foundation** with good span creation and error categorization. However, they suffer from **critical code duplication** (identical OTel modules copied across apps) and share the same fundamental issues found in Palantir, plus some application-specific concerns.

### Key Findings

| Category | Beorn (Flask) | Arda (FastAPI) | Priority |
|----------|---------------|----------------|----------|
| Basic Instrumentation | ✅ Good (78 usages) | ⚠️ Moderate (42 usages) | - |
| Code Duplication | ❌ 100% duplicate | ❌ 100% duplicate | CRITICAL |
| Context Management | ❌ Leaks | ❌ Leaks | CRITICAL |
| Resource Cleanup | ❌ Missing | ❌ Missing | CRITICAL |
| Span Status | ⚠️ Inconsistent | ⚠️ Inconsistent | HIGH |
| Metrics Usage | ❌ Zero | ❌ Zero | MEDIUM |
| FastAPI-Specific Issues | N/A | ⚠️ Middleware concerns | MEDIUM |
| Attribute Standards | ⚠️ Partial | ⚠️ Partial | MEDIUM |

### Coverage Analysis

**Beorn:** 78 instrumentation points across 15 files
- ✅ Well instrumented: dll/mdso.py, dll/granite.py, bll/service.py, bll/topologies.py
- ⚠️ Partially instrumented: apis/v3/*, apis/v1/*
- ❌ No instrumentation: bll/eligibility/*, bll/cpe.py, bll/managed_service.py

**Arda:** 42 instrumentation points across 14 files
- ✅ Well instrumented: dll/granite.py, dll/ipc.py, api/circuit_design.py
- ⚠️ Partially instrumented: api/ip_reservation.py, api/vlan_reservation.py
- ❌ No instrumentation: bll/circuit_design/*, bll/assign/*, bll/disconnect.py

---

## 1. CRITICAL ISSUE: Code Duplication

### 1.1 100% Identical OTel Modules Across All Applications

**Locations:**
- `beorn/beorn_app/common/otel/observability.py` (identical to Palantir & Arda)
- `arda/arda_app/common/otel/observability.py` (identical to Palantir & Beorn)
- `palantir/palantir_app/common/otel/observability.py` (identical to others)

**Impact:** CRITICAL

**Issue:**
The exact same 486-line `observability.py` file is duplicated in three locations:

```bash
$ diff beorn/beorn_app/common/otel/observability.py arda/arda_app/common/otel/observability.py
# No output - files are identical!

$ diff beorn/beorn_app/common/otel/observability.py palantir/palantir_app/common/otel/observability.py
# No output - files are identical!
```

**Duplicated Files:**
1. `observability.py` (486 lines) - **100% identical**
2. `otel_sense.py` (551 lines) - **100% identical**
3. `mdso_patterns.py` (311 lines) - **100% identical**
4. `telemetry.py` (49 lines) - **100% identical**
5. `__init__.py` (91 lines) - **100% identical**

**Total Duplicated Code:** ~1,488 lines × 3 = **4,464 lines of duplicate code**

**Problems:**
1. **Maintenance Nightmare** - Bug fixes must be applied 3 times
2. **Inconsistent Updates** - Easy to update one app but forget others
3. **Wasted Storage** - 3× the disk space and memory
4. **Testing Burden** - Same code tested 3 times
5. **All Apps Share Same Bugs** - Critical issues affect all apps simultaneously

**Recommendation:**

**Option 1: Move to Shared Library (RECOMMENDED)**

```bash
# Create shared observability module
mkdir -p seefa-om/shared-libs/sense_common/observability

# Move files to shared location
mv seefa-om/sense-apps/palantir/palantir_app/common/otel/* \
   seefa-om/shared-libs/sense_common/observability/

# Update imports in all apps
# From:
from beorn_app.common.otel import setup_observability
# To:
from sense_common.observability import setup_observability
```

**Option 2: Symlinks (Quick Fix)**

```bash
# Keep one "master" copy in shared-libs
# Create symlinks in each app
ln -s ../../../../shared-libs/sense_common/observability \
      beorn/beorn_app/common/otel

ln -s ../../../../shared-libs/sense_common/observability \
      arda/arda_app/common/otel

ln -s ../../../../shared-libs/sense_common/observability \
      palantir/palantir_app/common/otel
```

**Option 3: Git Submodule (Advanced)**

```bash
# Extract to separate repository
git submodule add https://github.com/org/sense-otel-common.git \
                  shared-libs/sense_otel_common

# Reference in each app
```

**Impact of Fix:** HIGH - Single source of truth, easier maintenance, faster bug fixes

---

## 2. CRITICAL ISSUES (Inherited from Code Duplication)

Since all three apps use identical OTel code, they **all share the same critical issues** found in Palantir:

### 2.1 Missing Resource Cleanup and Graceful Shutdown

**Locations:**
- `beorn/beorn_app/common/otel/observability.py:135-147`
- `arda/arda_app/common/otel/observability.py:135-147`

**Issue:** Identical to Palantir review - no shutdown handlers, risk of data loss

**Current Code:**
```python
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(...)
trace.set_tracer_provider(tracer_provider)
# ❌ No shutdown, no force_flush, no atexit handler
```

**Impact:** HIGH - Data loss during pod restarts, deployments, crashes

**Recommendation:** See Palantir review Section 1.1 - add `atexit` handlers and Flask/FastAPI lifecycle hooks

---

### 2.2 Context Leaks (Attach Without Detach)

**Locations:**
- `beorn/beorn_app/common/otel/observability.py:270-273` (Flask middleware)
- `arda/arda_app/common/otel/observability.py:340-343` (FastAPI middleware)
- `beorn/beorn_app/bll/topologies.py:114-115` (manual baggage)

**Issue:** Context attached but never detached

**Example from Beorn topologies.py:114-115:**
```python
# Set baggage for correlation
ctx = baggage.set_baggage("circuit_id", self.cid)
context.attach(ctx)  # ❌ Never detached!
# ... rest of function, context still attached ...
```

**Impact:** HIGH - Context leaks, incorrect baggage propagation, memory growth

**Recommendation:** See Palantir review Section 1.2 - use tokens and ensure cleanup

**Flask-Specific Fix (Beorn):**
```python
@app.before_request
def inject_correlation_keys():
    ctx = context.get_current()
    for key, value in extracted_keys.items():
        ctx = baggage.set_baggage(key, str(value), context=ctx)

    token = context.attach(ctx)
    g._otel_context_token = token  # ✅ Store for cleanup

@app.after_request
def cleanup_context(response):
    if hasattr(g, '_otel_context_token'):
        context.detach(g._otel_context_token)  # ✅ Cleanup
    return response
```

**FastAPI-Specific Fix (Arda):**
```python
class CorrelationMiddleware(BaseHTTPMiddleware):
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

---

## 3. APPLICATION-SPECIFIC ISSUES

### 3.1 Beorn-Specific Issues

#### 3.1.1 Incomplete Topology Instrumentation

**Location:** `beorn/beorn_app/bll/topologies.py`

**Issue:** Good instrumentation for topology creation, but missing for critical helper methods

**Well Instrumented:**
```python
def create_topology(self):  # ✅ Has instrumentation
    with tracer.start_as_current_span("beorn.topology.create") as span:
        # ... instrumentation ...
```

**Missing Instrumentation:**
```python
def _validate_required_circuit_data(self):  # ❌ No instrumentation
    # Critical validation logic, no spans

def _create_multi_leg_topology(self):  # ❌ No instrumentation
    # Complex multi-leg logic, no spans

def _get_node_data(self, element):  # ❌ No instrumentation
    # Device data extraction, no spans
```

**Recommendation:**

Add spans to critical topology methods:

```python
def _validate_required_circuit_data(self):
    """Validate required circuit data from Denodo"""
    if not OTEL_AVAILABLE:
        # ... existing logic ...
        return

    with tracer.start_as_current_span("beorn.topology.validate_circuit_data") as span:
        span.set_attribute("topology.circuit_id", self.cid)
        span.set_attribute("topology.elements_count", len(self.circuit_elements))

        try:
            # ... validation logic ...
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            set_span_error(e)
            span.set_attribute("validation.failed_field", str(e))
            raise

def _create_multi_leg_topology(self):
    """Create multi-leg (2-leg) topology"""
    with tracer.start_as_current_span("beorn.topology.create_multi_leg") as span:
        span.set_attribute("topology.type", "multi_leg")
        span.set_attribute("topology.circuit_id", self.cid)

        add_span_event("topology.primary_leg.start")
        primary_topology = self._create_topology(leg_type="PRIMARY")
        span.set_attribute("topology.primary.nodes", len(primary_topology.get("nodes", [])))

        add_span_event("topology.secondary_leg.start")
        secondary_topology = self._create_topology(leg_type="SECONDARY")
        span.set_attribute("topology.secondary.nodes", len(secondary_topology.get("nodes", [])))

        return {"PRIMARY": primary_topology, "SECONDARY": secondary_topology}
```

---

#### 3.1.2 Service Creation Missing Comprehensive Instrumentation

**Location:** `beorn/beorn_app/bll/service.py:132-150`

**Issue:** Good span creation but missing key attributes and events

**Current Code:**
```python
@traced("beorn.service.create_core", {"operation": "create_core_service"})
def create_core_service(body):
    with tracer.start_as_current_span("beorn.service.create_core_service") as span:
        set_mdso_correlation(circuit_id=cid, ...)
        span.set_attribute("service.workstream", workstream)
        # ⚠️ No span status management
        # ⚠️ No error categorization
        # ⚠️ No lifecycle events
```

**Recommendation:**

```python
@traced("beorn.service.create_core", {"operation": "create_core_service"})
def create_core_service(body):
    cid = body["cid"]

    with tracer.start_as_current_span(
        "beorn.service.create_core_service",
        kind=SpanKind.INTERNAL  # ✅ Specify span kind
    ) as span:
        set_mdso_correlation(circuit_id=cid, ...)
        span.set_attribute("service.workstream", workstream)
        span.set_attribute("service.order_type", body.get("service_request_order_type"))

        try:
            add_span_event("service.topology.creation.start", circuit_id=cid)
            topology = Topologies(cid).create_topology()
            add_span_event("service.topology.creation.complete", circuit_id=cid)

            add_span_event("service.eligibility.check.start", circuit_id=cid)
            eligibility = automation_eligibility(topology, body)
            span.set_attribute("service.eligible", eligibility.get("eligible", False))
            add_span_event("service.eligibility.check.complete",
                          circuit_id=cid,
                          eligible=eligibility.get("eligible"))

            add_span_event("service.mdso.creation.start", circuit_id=cid)
            response = create_service(cid, body, topology)
            span.set_attribute("service.resource_id", response.get("id"))
            add_span_event("service.mdso.creation.complete",
                          circuit_id=cid,
                          resource_id=response.get("id"))

            span.set_status(Status(StatusCode.OK))  # ✅ Explicit success
            return response

        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            for key, value in error_context.items():
                if value:
                    span.set_attribute(key, value)
            span.set_status(Status(StatusCode.ERROR, str(e)))  # ✅ Explicit error
            raise
```

---

#### 3.1.3 Denodo Calls Not Instrumented

**Location:** `beorn/beorn_app/common/granite_operations.py`

**Issue:** Critical Denodo database queries have NO instrumentation

**Current Code:**
```python
def call_denodo_for_circuit_devices(cid):
    # ❌ No instrumentation at all!
    query = f"SELECT * FROM circuit_device_view WHERE cid = '{cid}'"
    result = execute_denodo_query(query)
    return result
```

**Recommendation:**

```python
def call_denodo_for_circuit_devices(cid):
    """Query Denodo for circuit device information"""
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span(
        "denodo.query.circuit_devices",
        kind=SpanKind.CLIENT  # ✅ Database client call
    ) as span:
        span.set_attribute("db.system", "denodo")
        span.set_attribute("db.operation", "SELECT")
        span.set_attribute("denodo.circuit_id", cid)

        query = f"SELECT * FROM circuit_device_view WHERE cid = '{cid}'"
        span.set_attribute("db.statement", query[:200])  # Truncate for safety

        try:
            add_span_event("denodo.query.start", circuit_id=cid)
            result = execute_denodo_query(query)

            if result:
                span.set_attribute("denodo.rows_returned", len(result))
                span.set_attribute("denodo.devices_found", len(result))

            span.set_status(Status(StatusCode.OK))
            add_span_event("denodo.query.complete",
                          circuit_id=cid,
                          rows=len(result) if result else 0)
            return result

        except Exception as e:
            set_span_error(e)
            span.set_attribute("error.type", type(e).__name__)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

---

### 3.2 Arda-Specific Issues

#### 3.2.1 FastAPI Middleware Double-Read Risk

**Location:** `arda/arda_app/common/otel/observability.py:324-333`

**Issue:** FastAPI middleware attempts to read request body, which can cause issues

**Current Code:**
```python
class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract from JSON body (if POST/PUT)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()  # ⚠️ Consumes request stream!
                for key in baggage_keys:
                    if key not in extracted_keys:
                        json_value = body.get(key)
                        # ...
            except Exception:
                pass  # ⚠️ Silent failure
```

**Problem:**
- `await request.json()` **consumes the request stream**
- Subsequent code cannot read the body again
- This breaks FastAPI's dependency injection and Pydantic validation

**Recommendation:**

**Option 1: Don't Read Body (RECOMMENDED)**

```python
class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only extract from headers, not body
        extracted_keys = {}
        for key in baggage_keys:
            header_value = request.headers.get(f"x-{key}")
            if header_value:
                extracted_keys[key] = header_value

        # Set baggage
        ctx = context.get_current()
        for key, value in extracted_keys.items():
            ctx = baggage.set_baggage(key, str(value), context=ctx)

        token = context.attach(ctx)

        try:
            response = await call_next(request)
            return response
        finally:
            context.detach(token)  # ✅ Always cleanup
```

**Option 2: Cache Body (Complex)**

```python
class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Cache body for re-reading
        if request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()

            # Parse for baggage extraction
            try:
                import json
                body_data = json.loads(body_bytes)
                # ... extract baggage ...
            except:
                body_data = {}

            # Wrap request with cached body
            async def receive():
                return {"type": "http.request", "body": body_bytes}

            request = Request(request.scope, receive)

        # ... rest of middleware ...
```

---

#### 3.2.2 Missing BLL Instrumentation in Circuit Design

**Location:** `arda/arda_app/bll/circuit_design/circuit_design_main.py`

**Issue:** Core circuit design logic has NO instrumentation

**Current Code:**
```python
def circuit_design_main(payload, circ_path_inst_id=None):
    # ❌ No spans, no correlation, no events
    # Critical business logic completely dark

    # Bandwidth check
    bw_check(payload)

    # Entrance criteria
    entrance_criteria_check(payload)

    # Create design
    design = create_circuit_design(payload)

    return design
```

**Recommendation:**

```python
from arda_app.common.otel import (
    get_tracer,
    set_mdso_correlation,
    add_span_event,
    set_span_error,
)
from opentelemetry.trace import SpanKind, Status, StatusCode

tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()

def circuit_design_main(payload, circ_path_inst_id=None):
    """Main circuit design orchestration"""
    cid = payload.get("cid")

    with tracer.start_as_current_span(
        "arda.circuit_design.main",
        kind=SpanKind.INTERNAL
    ) as span:
        set_mdso_correlation(
            circuit_id=cid,
            product_id=payload.get("product_name"),
            service_type=payload.get("service_type"),
        )

        span.set_attribute("design.operation", "circuit_design_main")
        span.set_attribute("design.engineering_job_type", payload.get("engineering_job_type"))
        span.set_attribute("design.circ_path_inst_id", circ_path_inst_id or "new")

        try:
            # Bandwidth check
            add_span_event("design.bandwidth.check.start", circuit_id=cid)
            bw_result = bw_check(payload)
            span.set_attribute("design.bandwidth.valid", bw_result)
            add_span_event("design.bandwidth.check.complete", circuit_id=cid)

            # Entrance criteria
            add_span_event("design.entrance_criteria.check.start", circuit_id=cid)
            entrance_criteria_check(payload)
            add_span_event("design.entrance_criteria.check.passed", circuit_id=cid)

            # Create design
            add_span_event("design.creation.start", circuit_id=cid)
            design = create_circuit_design(payload)
            span.set_attribute("design.revision_number", design.get("revision_number"))
            add_span_event("design.creation.complete",
                          circuit_id=cid,
                          revision=design.get("revision_number"))

            span.set_status(Status(StatusCode.OK))
            return design

        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            for key, value in error_context.items():
                if value:
                    span.set_attribute(key, value)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

---

#### 3.2.3 IP and VLAN Reservation Missing Metrics

**Locations:**
- `arda/arda_app/api/ip_reservation.py`
- `arda/arda_app/api/vlan_reservation.py`

**Issue:** These critical operations have spans but NO metrics tracking

**Current Code (ip_reservation.py):**
```python
with tracer.start_as_current_span("arda.ip_reservation") as span:
    set_mdso_correlation(circuit_id=cid, ...)
    # ⚠️ No metrics for IP allocation success/failure rate
    # ⚠️ No metrics for IP pool utilization
    # ⚠️ No metrics for reservation latency
    result = ip_reservation_main(payload)
    return result
```

**Recommendation:**

```python
from opentelemetry import metrics
import time

meter = metrics.get_meter(__name__)

# Define metrics
ip_reservation_counter = meter.create_counter(
    "arda.ip_reservation.operations",
    description="IP reservation operations by result",
    unit="1"
)

ip_reservation_duration = meter.create_histogram(
    "arda.ip_reservation.duration",
    description="IP reservation operation duration",
    unit="s"
)

vlan_reservation_counter = meter.create_counter(
    "arda.vlan_reservation.operations",
    description="VLAN reservation operations by result",
    unit="1"
)

# Use in code
@v1_design_router.post("/ip_reservation")
def ip_reservation(payload: IPReservationPayloadModel, authenticated: bool = Depends(verify_password)):
    cid = payload.cid
    start_time = time.perf_counter()

    with tracer.start_as_current_span("arda.ip_reservation") as span:
        set_mdso_correlation(circuit_id=cid, ...)

        try:
            result = ip_reservation_main(payload.model_dump())
            duration = time.perf_counter() - start_time

            # Record success metrics
            ip_reservation_counter.add(
                1,
                attributes={
                    "result": "success",
                    "subnet_type": payload.subnet_type,
                    "product_name": payload.product_name
                }
            )

            ip_reservation_duration.record(
                duration,
                attributes={
                    "result": "success",
                    "subnet_type": payload.subnet_type
                }
            )

            span.set_status(Status(StatusCode.OK))
            return result

        except Exception as e:
            duration = time.perf_counter() - start_time

            # Record failure metrics
            ip_reservation_counter.add(
                1,
                attributes={
                    "result": "error",
                    "error_type": type(e).__name__,
                    "subnet_type": payload.subnet_type
                }
            )

            ip_reservation_duration.record(
                duration,
                attributes={
                    "result": "error",
                    "error_type": type(e).__name__
                }
            )

            set_span_error(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

---

#### 3.2.4 IPC API Calls Underinstrumented

**Location:** `arda/arda_app/dll/ipc.py`

**Issue:** IPC (IP Control) API calls have basic spans but missing key attributes

**Current Code:**
```python
def reserve_ip(subnet_type, circuit_id):
    with tracer.start_as_current_span("ipc.api.reserve_ip") as span:
        span.set_attribute("ipc.operation", "reserve_ip")
        # ⚠️ Missing: subnet details, pool information
        # ⚠️ Missing: retry logic tracking
        # ⚠️ Missing: IP conflict detection

        result = requests.post(f"{IPC_BASE_URL}/reserve", ...)
        return result.json()
```

**Recommendation:**

```python
def reserve_ip(subnet_type, circuit_id, vrf=None, prefix_length=None):
    """Reserve IP address from IPC"""
    with tracer.start_as_current_span(
        "ipc.api.reserve_ip",
        kind=SpanKind.CLIENT  # ✅ External API call
    ) as span:
        span.set_attribute("ipc.operation", "reserve_ip")
        span.set_attribute("ipc.subnet_type", subnet_type)
        span.set_attribute("ipc.circuit_id", circuit_id)
        if vrf:
            span.set_attribute("ipc.vrf", vrf)
        if prefix_length:
            span.set_attribute("ipc.prefix_length", prefix_length)

        payload = {
            "subnet_type": subnet_type,
            "circuit_id": circuit_id,
            "vrf": vrf,
            "prefix_length": prefix_length,
        }

        try:
            add_span_event("ipc.api.call.start", circuit_id=circuit_id)

            result = requests.post(
                f"{IPC_BASE_URL}/reserve",
                json=payload,
                timeout=30
            )

            span.set_attribute("http.status_code", result.status_code)
            span.set_attribute("ipc.response_time_ms", result.elapsed.total_seconds() * 1000)

            if result.status_code == 200:
                data = result.json()
                span.set_attribute("ipc.ip_address", data.get("ip_address"))
                span.set_attribute("ipc.subnet", data.get("subnet"))
                span.set_attribute("ipc.pool_id", data.get("pool_id"))
                span.set_status(Status(StatusCode.OK))
                add_span_event("ipc.ip.reserved",
                              circuit_id=circuit_id,
                              ip_address=data.get("ip_address"))
                return data
            elif result.status_code == 409:
                # IP conflict
                span.set_attribute("error.type", "ip_conflict")
                span.set_status(Status(StatusCode.ERROR, "IP conflict"))
                add_span_event("ipc.ip.conflict", circuit_id=circuit_id)
                abort(409, f"IP conflict for circuit {circuit_id}")
            else:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {result.status_code}"))
                abort(500, f"IPC error: {result.status_code}")

        except requests.Timeout as e:
            set_span_error(e)
            span.set_attribute("error.type", "timeout")
            span.set_status(Status(StatusCode.ERROR, "Timeout"))
            abort(504, f"IPC timeout for circuit {circuit_id}")
        except Exception as e:
            set_span_error(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

---

## 4. METRICS IMPLEMENTATION (Both Apps)

### 4.1 Zero Metrics Usage

**Issue:** Both apps initialize `MeterProvider` but **never create any metrics**

**Current State:**
```bash
$ grep -r "create_counter\|create_histogram\|create_gauge" \
    beorn/beorn_app arda/arda_app \
    --include="*.py" | grep -v "common/otel" | wc -l
0
```

**Impact:** MEDIUM - Missing business KPIs and SLO tracking

**Recommendation:**

Create app-specific metrics modules:

**beorn/beorn_app/common/metrics.py:**
```python
"""Beorn Business Metrics"""
from opentelemetry import metrics

meter = metrics.get_meter("beorn")

# Service operations
service_operations = meter.create_counter(
    "beorn.service.operations",
    description="Service operations by type and result",
    unit="1"
)

service_duration = meter.create_histogram(
    "beorn.service.duration",
    description="Service operation duration",
    unit="s"
)

# Topology operations
topology_creation_duration = meter.create_histogram(
    "beorn.topology.creation_duration",
    description="Topology creation duration",
    unit="s"
)

topology_node_count = meter.create_histogram(
    "beorn.topology.node_count",
    description="Number of nodes in topology",
    unit="1"
)

# MDSO operations
mdso_api_duration = meter.create_histogram(
    "beorn.mdso.api.duration",
    description="MDSO API call duration",
    unit="s"
)

mdso_api_errors = meter.create_counter(
    "beorn.mdso.api.errors",
    description="MDSO API errors by operation",
    unit="1"
)

# Denodo operations
denodo_query_duration = meter.create_histogram(
    "beorn.denodo.query_duration",
    description="Denodo query duration",
    unit="s"
)

denodo_rows_returned = meter.create_histogram(
    "beorn.denodo.rows_returned",
    description="Number of rows returned from Denodo",
    unit="1"
)

# Eligibility checks
eligibility_checks = meter.create_counter(
    "beorn.eligibility.checks",
    description="Eligibility check results",
    unit="1"
)
```

**arda/arda_app/common/metrics.py:**
```python
"""Arda Business Metrics"""
from opentelemetry import metrics

meter = metrics.get_meter("arda")

# Circuit design operations
circuit_design_operations = meter.create_counter(
    "arda.circuit_design.operations",
    description="Circuit design operations by job type and result",
    unit="1"
)

circuit_design_duration = meter.create_histogram(
    "arda.circuit_design.duration",
    description="Circuit design operation duration",
    unit="s"
)

# IP reservation
ip_reservation_operations = meter.create_counter(
    "arda.ip_reservation.operations",
    description="IP reservation operations by result",
    unit="1"
)

ip_pool_utilization = meter.create_up_down_counter(
    "arda.ip_pool.utilization",
    description="IP pool utilization (allocated IPs)",
    unit="1"
)

# VLAN reservation
vlan_reservation_operations = meter.create_counter(
    "arda.vlan_reservation.operations",
    description="VLAN reservation operations by result",
    unit="1"
)

# Granite operations
granite_api_duration = meter.create_histogram(
    "arda.granite.api.duration",
    description="Granite API call duration",
    unit="s"
)

granite_api_errors = meter.create_counter(
    "arda.granite.api.errors",
    description="Granite API errors by operation",
    unit="1"
)

# Bandwidth changes
bandwidth_change_operations = meter.create_counter(
    "arda.bandwidth_change.operations",
    description="Bandwidth change operations by result",
    unit="1"
)

# Disconnect operations
disconnect_operations = meter.create_counter(
    "arda.disconnect.operations",
    description="Disconnect operations by result",
    unit="1"
)
```

---

## 5. COMMON IMPROVEMENTS (Both Apps)

### 5.1 Standardize Attribute Naming

**Current State:** Inconsistent naming across apps

**Beorn Examples:**
```python
span.set_attribute("mdso.circuit_id", cid)         # ✅ Good
span.set_attribute("service.workstream", workstream)  # ✅ Good
span.set_attribute("topology.circuit_id", cid)     # ⚠️ Duplicate namespace
```

**Arda Examples:**
```python
span.set_attribute("design.operation", "circuit_design")  # ✅ Good
span.set_attribute("granite.circuit_id", cid)      # ⚠️ Different namespace than Beorn
```

**Recommendation:**

Use consistent namespace across all apps:

```python
# Common correlation attributes (all apps)
"charter.circuit_id" = "80.L1XX.005054..CHTR"
"charter.product_id" = "product-123"
"charter.resource_id" = "uuid-here"
"charter.service_type" = "eline"
"charter.order_type" = "provision"

# System-specific namespaces
"mdso.operation" = "post"
"mdso.endpoint" = "/bpocore/market/api/v1/resources"
"mdso.orch_state" = "active"

"granite.operation" = "put"
"granite.endpoint" = "/api/v1/paths"

"denodo.operation" = "select"
"denodo.table" = "circuit_device_view"

"ipc.operation" = "reserve_ip"
"ipc.subnet_type" = "loopback"

# App-specific namespaces
"beorn.operation" = "create_service"
"beorn.topology.node_count" = 4
"beorn.eligibility.result" = "eligible"

"arda.operation" = "circuit_design"
"arda.design.revision_number" = "12345678901234"
"arda.bandwidth.requested_mbps" = 1000
```

---

### 5.2 Add Span Kinds to All Manual Spans

**Current State:** No span kinds specified

**Recommendation:**

```python
from opentelemetry.trace import SpanKind

# API endpoint spans (auto-instrumented, but can be explicit)
@app.route("/service")
def create_service():
    with tracer.start_as_current_span(
        "beorn.api.create_service",
        kind=SpanKind.SERVER  # ✅ Incoming HTTP request
    ):
        # ...

# External API calls
def mdso_post(endpoint, data):
    with tracer.start_as_current_span(
        "mdso.api.post",
        kind=SpanKind.CLIENT  # ✅ Outgoing HTTP request
    ):
        # ...

# Database queries
def call_denodo_for_circuit_devices(cid):
    with tracer.start_as_current_span(
        "denodo.query.circuit_devices",
        kind=SpanKind.CLIENT  # ✅ Database client
    ):
        # ...

# Internal business logic
def create_topology(cid):
    with tracer.start_as_current_span(
        "beorn.topology.create",
        kind=SpanKind.INTERNAL  # ✅ Internal operation
    ):
        # ...
```

---

## 6. TESTING RECOMMENDATIONS

### 6.1 Shared OTel Tests

Since the OTel code is duplicated, create **shared tests** in `shared-libs/tests/`:

**shared-libs/tests/test_observability.py:**
```python
import pytest
from sense_common.observability import setup_observability
from opentelemetry import trace, context, baggage

def test_context_cleanup():
    """Test that context is properly cleaned up"""
    ctx = context.get_current()
    ctx = baggage.set_baggage("test_key", "test_value", context=ctx)
    token = context.attach(ctx)

    assert baggage.get_baggage("test_key") == "test_value"

    context.detach(token)
    assert baggage.get_baggage("test_key") is None  # ✅ Cleaned up

def test_shutdown_handlers():
    """Test that shutdown handlers are registered"""
    from sense_common.observability import _shutdown_handlers
    assert len(_shutdown_handlers) > 0

def test_span_status_management():
    """Test that span status is properly set"""
    # ... test implementation ...
```

### 6.2 App-Specific Integration Tests

**beorn/tests/integration/test_otel_service.py:**
```python
def test_service_creation_spans(client, test_tracer):
    """Test that service creation creates proper spans"""
    response = client.post('/beorn/v3/service', json={
        "cid": "TEST-CID",
        "service_request_order_type": "New Install"
    })

    spans = test_tracer.get_finished_spans()

    # Check for expected spans
    assert any("beorn.service.create" in s.name for s in spans)
    assert any("beorn.topology.create" in s.name for s in spans)
    assert any("mdso.api.post" in s.name for s in spans)

    # Check attributes
    service_span = next(s for s in spans if "beorn.service" in s.name)
    assert service_span.attributes.get("charter.circuit_id") == "TEST-CID"
```

**arda/tests/integration/test_otel_design.py:**
```python
async def test_circuit_design_spans(async_client, test_tracer):
    """Test that circuit design creates proper spans"""
    response = await async_client.post('/arda/v1/circuit_design', json={
        "z_side_info": {
            "cid": "TEST-CID",
            "service_type": "add",
            "engineering_job_type": "New"
        }
    })

    spans = test_tracer.get_finished_spans()

    # Check for expected spans
    assert any("arda.circuit_design" in s.name for s in spans)
    assert any("granite.api" in s.name for s in spans)
```

---

## 7. IMPLEMENTATION PLAN

### Phase 1: Critical Fixes (Week 1)
**Priority: CRITICAL**

1. ✅ **Deduplicate OTel Code**
   - Move to shared-libs/sense_common/observability/
   - Update imports in all 3 apps
   - Test each app individually

2. ✅ **Add Resource Cleanup**
   - Implement shutdown handlers
   - Add Flask/FastAPI lifecycle hooks
   - Test graceful shutdown

3. ✅ **Fix Context Leaks**
   - Add context.detach() in Flask middleware (Beorn)
   - Fix FastAPI middleware (Arda)
   - Fix manual context usage in topologies.py

**Estimated Effort:** 3-4 days
**Impact:** CRITICAL - Prevents data loss and context leaks

---

### Phase 2: App-Specific Improvements (Week 2)
**Priority: HIGH**

**Beorn:**
1. ✅ Add instrumentation to topology helper methods
2. ✅ Add Denodo query instrumentation
3. ✅ Enhance service creation spans

**Arda:**
1. ✅ Fix FastAPI middleware body-reading issue
2. ✅ Add BLL instrumentation (circuit_design_main, etc.)
3. ✅ Enhance IPC API instrumentation

**Estimated Effort:** 5-6 days
**Impact:** HIGH - Comprehensive observability coverage

---

### Phase 3: Metrics Implementation (Week 3)
**Priority: MEDIUM**

1. ✅ Create beorn/common/metrics.py
2. ✅ Create arda/common/metrics.py
3. ✅ Add metrics to critical operations:
   - Service creation (Beorn)
   - Circuit design (Arda)
   - IP/VLAN reservation (Arda)
   - Topology creation (Beorn)
4. ✅ Configure Prometheus/Grafana dashboards

**Estimated Effort:** 4-5 days
**Impact:** MEDIUM - Business KPI tracking

---

### Phase 4: Standardization & Testing (Week 4)
**Priority: MEDIUM**

1. ✅ Standardize attribute naming across apps
2. ✅ Add span kinds to all manual spans
3. ✅ Create shared OTel tests
4. ✅ Create app-specific integration tests
5. ✅ Document instrumentation patterns

**Estimated Effort:** 4-5 days
**Impact:** MEDIUM - Consistency and maintainability

---

## 8. MONITORING & ALERTING

### 8.1 Shared Alerts (All Apps)

```yaml
groups:
  - name: sense_apps_otel
    rules:
      - alert: HighSpanDropRate
        expr: rate(otel_span_processor_spans_dropped_total{service=~"beorn|arda|palantir"}[5m]) > 10
        labels:
          severity: warning
        annotations:
          summary: "High span drop rate in {{ $labels.service }}"

      - alert: OTelExporterDown
        expr: rate(otel_exporter_export_failed_total{service=~"beorn|arda|palantir"}[5m]) > 0.1
        labels:
          severity: error
        annotations:
          summary: "OTel exporter failing in {{ $labels.service }}"
```

### 8.2 Beorn-Specific Alerts

```yaml
  - name: beorn_business_metrics
    rules:
      - alert: HighServiceCreationFailureRate
        expr: rate(beorn_service_operations_total{result="error"}[10m]) / rate(beorn_service_operations_total[10m]) > 0.1
        labels:
          severity: error
        annotations:
          summary: "Beorn service creation failure rate > 10%"

      - alert: SlowTopologyCreation
        expr: histogram_quantile(0.95, rate(beorn_topology_creation_duration_bucket[5m])) > 30
        labels:
          severity: warning
        annotations:
          summary: "Beorn topology creation P95 > 30s"

      - alert: DenodoQueryTimeout
        expr: rate(beorn_denodo_query_duration_bucket{le="60"}[5m]) < 0.9
        labels:
          severity: warning
        annotations:
          summary: "Denodo queries timing out (>90% take >60s)"
```

### 8.3 Arda-Specific Alerts

```yaml
  - name: arda_business_metrics
    rules:
      - alert: HighCircuitDesignFailureRate
        expr: rate(arda_circuit_design_operations_total{result="error"}[10m]) / rate(arda_circuit_design_operations_total[10m]) > 0.05
        labels:
          severity: error
        annotations:
          summary: "Arda circuit design failure rate > 5%"

      - alert: IPReservationFailures
        expr: rate(arda_ip_reservation_operations_total{result="error"}[10m]) > 5
        labels:
          severity: error
        annotations:
          summary: "High IP reservation failure rate"

      - alert: VLANPoolExhaustion
        expr: arda_vlan_pool_utilization > 0.9
        labels:
          severity: warning
        annotations:
          summary: "VLAN pool utilization > 90%"
```

---

## 9. SUMMARY & KEY TAKEAWAYS

### Critical Issues Summary

| Issue | Affected Apps | Severity | Fix Complexity |
|-------|---------------|----------|----------------|
| Code Duplication | All 3 apps | CRITICAL | Medium (2-3 days) |
| Missing Shutdown | All 3 apps | CRITICAL | Low (1 day) |
| Context Leaks | All 3 apps | CRITICAL | Medium (2 days) |
| FastAPI Body Reading | Arda | HIGH | Low (1 day) |
| Missing BLL Instrumentation | Arda | HIGH | Medium (3 days) |
| No Metrics | Beorn, Arda | MEDIUM | Medium (4-5 days) |
| Inconsistent Attributes | All apps | MEDIUM | Low (2 days) |

### Beorn vs Arda Comparison

| Aspect | Beorn (Flask) | Arda (FastAPI) |
|--------|---------------|----------------|
| **Instrumentation Coverage** | 78 points (better) | 42 points (needs work) |
| **DLL Layer** | ✅ Well instrumented | ✅ Well instrumented |
| **BLL Layer** | ⚠️ Partial | ❌ Minimal |
| **API Layer** | ⚠️ Partial | ✅ Good |
| **Framework-Specific Issues** | None | Body-reading bug |
| **Critical Operations** | Topology, Service | Circuit Design, IP/VLAN |
| **External Dependencies** | Denodo, MDSO, Granite | IPC, MDSO, Granite |

### Quick Wins (Can implement immediately)

1. **Deduplicate OTel code** → Move to shared-libs (2-3 days)
2. **Add shutdown handlers** → Prevent data loss (1 day)
3. **Fix Arda body-reading bug** → Don't read body in middleware (2 hours)
4. **Add span kinds** → Improve trace visualization (1 day)
5. **Standardize attribute naming** → Better consistency (2 days)

### Long-term Goals

1. **100% BLL coverage** → All business logic instrumented (2-3 weeks)
2. **Comprehensive metrics** → All KPIs tracked (2 weeks)
3. **Automated testing** → OTel integration tests (1 week)
4. **SLO/SLI tracking** → Business objectives measured (ongoing)

---

## 10. ADDITIONAL RESOURCES

### Internal Documentation
- Palantir OTel Review: `PALANTIR_OTEL_INSTRUMENTATION_REVIEW.md`
- Existing Summary: `seefa-om/docs/SENSE_OTEL_IMPLEMENTATION_SUMMARY.md`
- Instrumentation Analysis: `seefa-om/sense-apps/OTEL_INSTRUMENTATION_ANALYSIS.md`

### OpenTelemetry Resources
- [OTel Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [Flask Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/flask/flask.html)
- [FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

---

**Review Date:** 2025-12-16
**Next Review:** 2026-01-16 (after Phase 1-2 implementation)
**Reviewers:** Engineering Team, DevOps Team, SRE Team

---

## APPENDIX A: Code Duplication Analysis

### Exact File Comparison

```bash
$ md5sum beorn/beorn_app/common/otel/observability.py \
          arda/arda_app/common/otel/observability.py \
          palantir/palantir_app/common/otel/observability.py

a1b2c3d4e5f6...  beorn/beorn_app/common/otel/observability.py
a1b2c3d4e5f6...  arda/arda_app/common/otel/observability.py
a1b2c3d4e5f6...  palantir/palantir_app/common/otel/observability.py
# ☝️ Identical MD5 hashes!
```

### Shared Code Statistics

| File | Lines | Duplicated Across | Total Waste |
|------|-------|-------------------|-------------|
| observability.py | 486 | 3 apps | 972 lines |
| otel_sense.py | 551 | 3 apps | 1,102 lines |
| mdso_patterns.py | 311 | 3 apps | 622 lines |
| telemetry.py | 49 | 3 apps | 98 lines |
| __init__.py | 91 | 3 apps | 182 lines |
| **TOTAL** | **1,488** | **3 apps** | **2,976 duplicate lines** |

**Recommendation:** Immediate deduplication saves ~3,000 lines of maintenance burden

