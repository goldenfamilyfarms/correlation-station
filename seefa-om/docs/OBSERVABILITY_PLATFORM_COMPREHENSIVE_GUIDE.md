# Correlation Station — Comprehensive Observability Platform Guide

> MDSO Observability Platform · Multi-Domain Service Orchestrator · Telecom Circuit Provisioning

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [System Architecture](#2-system-architecture)
3. [Correlation Engine Deep Dive](#3-correlation-engine-deep-dive)
   - 3.1 [Windowed Batching & Correlation](#31-windowed-batching--correlation)
   - 3.2 [Backpressure & Queue Management](#32-backpressure--queue-management)
   - 3.3 [Circuit Breaker Pattern](#33-circuit-breaker-pattern)
   - 3.4 [Log / Trace Correlation](#34-log--trace-correlation)
   - 3.5 [Trace Synthesis](#35-trace-synthesis)
4. [Data Flow](#4-data-flow)
5. [Component Reference](#5-component-reference)
   - 5.1 [FastAPI Backend](#51-fastapi-backend)
   - 5.2 [OTel Gateway](#52-otel-gateway)
   - 5.3 [Sense Apps (Demo Microservices)](#53-sense-apps-demo-microservices)
   - 5.4 [Grafana Alloy Log Collector](#54-grafana-alloy-log-collector)
   - 5.5 [Observability Stack](#55-observability-stack)
   - 5.6 [React Frontend](#56-react-frontend)
6. [OpenTelemetry Integration](#6-opentelemetry-integration)
   - 6.1 [SDK Instrumentation Strategy](#61-sdk-instrumentation-strategy)
   - 6.2 [OTLP Protocol Endpoints](#62-otlp-protocol-endpoints)
   - 6.3 [Attribute Schema](#63-attribute-schema)
7. [Storage Architecture](#7-storage-architecture)
8. [Redis Caching Layer](#8-redis-caching-layer)
9. [Multi-Backend Export](#9-multi-backend-export)
10. [Service-Level Objectives (SLOs)](#10-service-level-objectives-slos)
11. [Horizontal Scaling](#11-horizontal-scaling)
12. [Deployment Guide](#12-deployment-guide)
    - 12.1 [Docker Compose (Development)](#121-docker-compose-development)
    - 12.2 [Kubernetes (Production)](#122-kubernetes-production)
13. [CI/CD Pipeline](#13-cicd-pipeline)
14. [Operations Runbook](#14-operations-runbook)
15. [Security Hardening](#15-security-hardening)
16. [Metrics Reference](#16-metrics-reference)
17. [API Reference Summary](#17-api-reference-summary)
18. [Troubleshooting Guide](#18-troubleshooting-guide)
19. [Go Integration Strategy](#19-go-integration-strategy)
20. [Datadog Dual-Write Strategy](#20-datadog-dual-write-strategy)

---

## 1. Platform Overview

**Correlation Station** is a production-grade observability platform built for **MDSO (Multi-Domain Service Orchestrator)**, a telecom system that provisions and manages network circuits across multi-vendor infrastructure. The platform delivers end-to-end visibility into circuit provisioning workflows by correlating distributed logs and traces across heterogeneous services in real time.

### Core Capabilities

| Capability | Description |
|---|---|
| Real-time correlation | Links logs and traces across services within configurable time windows |
| OTLP-native ingestion | Accepts OpenTelemetry Protocol (OTLP) over gRPC and HTTP |
| Multi-backend export | Simultaneously writes to Loki, Tempo, Prometheus, and optionally Datadog |
| Trace synthesis | Generates synthetic bridge spans when native trace context is absent |
| Continuous profiling | Pyroscope FlameGraph integration for CPU and memory analysis |
| SECA error tracking | Aggregates and prioritises network activation errors (SECA = Service Error Correlation Analysis) |
| Self-observability | The correlation engine instruments itself with OTel traces and Prometheus metrics |

### Business Context

Each MDSO workflow is uniquely identified by a set of business attributes that flow through every layer of the observability stack:

| Attribute | Purpose |
|---|---|
| `circuit_id` | End-to-end circuit lifecycle identifier |
| `product_id` | Commercial product SKU linked to the circuit |
| `resource_id` | Physical or logical network resource |
| `resource_type_id` | Device/port/service type classifier |
| `request_id` | Individual API request within a workflow |

These attributes are the foundation of all correlation queries and dashboard filters.

---

## 2. System Architecture

```
                 ┌─────────────────────────────────────────────────────┐
                 │                   MDSO Platform                     │
                 │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
                 │  │  ARDA    │  │  BEORN   │  │    PALANTIR      │  │
                 │  │ :5001    │  │ :5002    │  │     :5003        │  │
                 │  │FastAPI   │  │  Flask   │  │     Flask        │  │
                 │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
                 │       │             │                  │            │
                 │       └─────────────┼──────────────────┘            │
                 │                     │ OTLP/gRPC                    │
                 └─────────────────────┼────────────────────────────────┘
                                       │
                 ┌─────────────────────▼────────────────────────────────┐
                 │         OTel Collector Gateway                       │
                 │  Receivers: OTLP gRPC :4317 · OTLP HTTP :4318       │
                 │  Processors: batch · memory_limiter · attributes     │
                 └──────┬──────────┬──────────┬───────────┬────────────┘
                        │          │           │           │
             ┌──────────▼─┐  ┌─────▼────┐ ┌───▼──┐ ┌─────▼──────┐
             │Correlation  │  │  Loki    │ │Tempo │ │ Prometheus │
             │Engine :8080 │  │  :3100   │ │:3200 │ │   :9090    │
             │FastAPI/Python│  │  Logs    │ │Traces│ │  Metrics   │
             └──────┬──────┘  └──────────┘ └──────┘ └────────────┘
                    │                                       │
             ┌──────▼──────┐                      ┌────────▼──────────┐
             │    Redis    │                      │   Grafana :8443   │
             │    :6379    │                      │  Dashboards & VIZ │
             │  Cache/Queue│                      └────────┬──────────┘
             └─────────────┘                               │
                                                  ┌────────▼──────────┐
                                                  │  React Frontend   │
                                                  │  TypeScript :3002 │
                                                  └───────────────────┘

                 ┌─────────────────────────────────────────────────────┐
                 │     Grafana Alloy (mdso-alloy)                      │
                 │     Tails /var/log/ciena/blueplanet.log             │
                 │     Parses syslog → structured OTLP                 │
                 └────────────────────────┬────────────────────────────┘
                                          │ OTLP/HTTP
                                          ▼
                                    OTel Gateway
```

### Design Principles

1. **Async-first** — All I/O in the correlation engine is non-blocking (asyncio + aiohttp/httpx).
2. **Separation of concerns** — Ingestion, correlation, and export are independent pipeline stages.
3. **Low-cardinality labels** — Only three Loki labels (`service_name`, `level`, `environment`) prevent metric-cardinality explosion.
4. **Idempotent export** — Duplicate telemetry is deduplicated by trace/span ID before persistence.
5. **Resilience by default** — Circuit breakers and exponential-backoff retries protect all external calls.
6. **Cache-aside pattern** — Redis stores pre-indexed telemetry for O(1) correlation lookups.

---

## 3. Correlation Engine Deep Dive

The correlation engine (`seefa-om/correlation-engine/`) is the central intelligence of the platform. Written in Python 3.11 with FastAPI, it receives raw telemetry, enriches and correlates it, then fans it out to the configured storage backends.

### 3.1 Windowed Batching & Correlation

**File:** `app/pipeline/correlator.py`

The engine groups incoming telemetry into fixed-size time windows before running correlation logic. This is the equivalent of a stream-processing tumbling window.

```
Time →
 [t0]────────────[t0 + window_size]────────────[t0 + 2×window_size]
  │   Window 1                 │   Window 2                 │
  │  Accumulate spans+logs     │  Accumulate spans+logs     │
  │  → run correlate()         │  → run correlate()         │
  │  → emit to backends        │  → emit to backends        │
  └────────────────────────────┴────────────────────────────┘
```

**Default window:** 60 seconds (overridden by `CORRELATION_WINDOW_SECONDS` env var).

**Correlation algorithm:**

```python
# Pseudo-code of the core correlate() loop
for each window:
    group logs by (trace_id OR business_id)
    group traces by trace_id
    for each group:
        if trace_id present in both:
            create Correlation(type=TRACE_LOG_MATCH, confidence=HIGH)
        elif business_id matches:
            create Correlation(type=BUSINESS_ID_MATCH, confidence=MEDIUM)
            optionally synthesise bridge span
        emit CorrelationEvent to Redis + Loki
```

**Why windowing?**
- Network provisioning workflows span seconds to minutes; a 60-second window captures most multi-hop flows.
- Batching amortises the per-item overhead of HTTP calls to Loki/Tempo.
- Windows are configurable so operators can tune for throughput vs. latency trade-offs.

---

### 3.2 Backpressure & Queue Management

**File:** `app/pipeline/correlator.py`, `app/config.py`

The engine exposes two configurable queue-depth limits:

| Config Var | Default | Purpose |
|---|---|---|
| `LOG_QUEUE_MAX_SIZE` | 10 000 | Maximum pending log records before applying backpressure |
| `TRACE_QUEUE_MAX_SIZE` | 5 000 | Maximum pending spans before applying backpressure |

**Backpressure flow:**

```
Ingress (OTLP endpoint)
        │
        ▼
  queue.put_nowait()
        │
   queue full?
   ┌────┴──────────────────────────────┐
   │ No                                │ Yes
   ▼                                   ▼
 enqueue                        drop + increment
 normally                       correlation_engine_dropped_total{type="log|trace"}
                                log WARNING with current queue depth
```

When the queue is full the engine:
1. Increments the `correlation_engine_dropped_total` Prometheus counter (labelled by signal type).
2. Emits a structured warning log so Loki/Alertmanager can fire an alert.
3. Returns HTTP 429 to the upstream OTel Collector so the Collector can apply its own retry/queue logic.

This prevents memory exhaustion under burst conditions while giving upstream components a back-channel signal to throttle.

---

### 3.3 Circuit Breaker Pattern

**File:** `app/pipeline/exporters.py`

Every export target (Loki, Tempo, Prometheus, Datadog) is wrapped in a circuit breaker to prevent cascading failures.

```
State Machine:
                   failures >= threshold
  CLOSED ────────────────────────────────► OPEN
    ▲                                        │
    │                                        │ after reset_timeout
    │  probe succeeds                        ▼
    └────────────────────────────────── HALF-OPEN
                                             │
                                probe fails  │
                                      ───────┘ → OPEN again
```

| Parameter | Default | Description |
|---|---|---|
| `failure_threshold` | 5 | Consecutive failures before opening circuit |
| `reset_timeout` | 30 s | Wait before probing in HALF-OPEN state |
| `success_threshold` | 2 | Consecutive successes needed to close from HALF-OPEN |

**Metrics exposed:**
- `correlation_engine_circuit_breaker_state{backend}` — gauge: 0=CLOSED, 1=HALF-OPEN, 2=OPEN
- `correlation_engine_export_failures_total{backend}` — counter of failed export attempts

When a circuit is OPEN, data is queued in Redis rather than dropped, so a recovering backend can catch up once the circuit closes.

---

### 3.4 Log / Trace Correlation

**File:** `app/pipeline/correlator.py`

The engine correlates logs and traces using a two-pass strategy:

**Pass 1 — Exact match (trace_id)**

```
Log record has trace_id field?
    Yes → look up trace in Redis TraceIndex by trace_id
          found? → attach log to trace, emit CorrelationEvent(type=TRACE_LOG_MATCH)
          not found yet? → buffer log for up to window_size seconds
```

**Pass 2 — Business ID fuzzy match**

```
Log record has circuit_id / resource_id / product_id?
    Yes → query Redis for any trace within the same time window
          sharing one or more business attributes
          found? → create CorrelationEvent(type=BUSINESS_ID_MATCH, confidence=MEDIUM)
                   optionally synthesise a bridge span (see §3.5)
```

**Confidence scoring:**

| Correlation Type | Confidence | Description |
|---|---|---|
| `TRACE_LOG_MATCH` | HIGH | Exact W3C trace-id match between log and span |
| `BUSINESS_ID_MATCH` | MEDIUM | One or more shared business attributes |
| `TEMPORAL_PROXIMITY` | LOW | Same time window, same service, no shared ID |

Correlation events are stored in Redis with a 48-hour TTL and indexed by `circuit_id` for fast dashboard queries.

---

### 3.5 Trace Synthesis

**File:** `app/pipeline/correlator.py`

Legacy MDSO components emit rich structured logs but lack OTel instrumentation. Trace synthesis creates a synthetic distributed trace from these logs so they appear in Tempo alongside native OTel traces.

**Synthesis algorithm:**

```python
def synthesise_trace(log_batch: list[LogRecord]) -> OTLPTrace:
    root_span = create_span(
        name=f"synthetic/{log_batch[0].service_name}",
        trace_id=generate_deterministic_trace_id(log_batch[0].circuit_id),
        parent_span_id=None,
        start_time=log_batch[0].timestamp,
        end_time=log_batch[-1].timestamp,
        attributes={
            "synthetic": True,
            "circuit_id": log_batch[0].circuit_id,
            "source_log_count": len(log_batch),
        }
    )
    child_spans = [log_to_span(l, root_span.span_id) for l in log_batch[1:]]
    return OTLPTrace(spans=[root_span] + child_spans)
```

`generate_deterministic_trace_id` hashes `circuit_id + date-hour` so synthetic traces for the same circuit are always addressable by the same trace ID — enabling stable Grafana Tempo deep-links.

**Toggle:** Set `ENABLE_TRACE_SYNTHESIS=false` to disable (e.g., when all services have native instrumentation).

---

## 4. Data Flow

```
1. MDSO Service emits telemetry via OTLP/gRPC
        │
        ▼
2. OTel Collector Gateway receives signal
   ├── Applies batch processor (500 spans / 200 ms)
   ├── Applies memory_limiter (512 MiB heap ceiling)
   └── Routes to:
       ├── Correlation Engine  (all signals)
       ├── Loki                (logs only)
       ├── Tempo               (traces only)
       └── Prometheus          (metrics only, via receiver)
        │
        ▼
3. Correlation Engine ingests via /v1/logs, /v1/traces, /v1/metrics
   ├── Normalises OTLP protobuf → internal Pydantic models
   ├── Enriches with MDSO business attributes
   ├── Places signal on async queue
   └── Returns 200 OK immediately (async hand-off)
        │
        ▼
4. Correlator worker (background asyncio task)
   ├── Drains queue into current time window
   ├── Runs Pass 1 (trace_id exact match)
   ├── Runs Pass 2 (business ID fuzzy match)
   ├── Optionally synthesises traces
   └── Emits CorrelationEvents to Redis
        │
        ▼
5. Exporter worker (background asyncio task)
   ├── Reads correlated batches from window
   ├── Fans out to Loki (logs) via push API
   ├── Fans out to Tempo (traces) via OTLP/HTTP
   ├── Updates Prometheus metrics via client library
   └── Optionally dual-writes to Datadog
        │
        ▼
6. Grafana reads from Loki / Tempo / Prometheus
   └── React frontend queries Correlation Engine API
       for CorrelationEvents, SECA errors, health
```

---

## 5. Component Reference

### 5.1 FastAPI Backend

**Path:** `seefa-om/correlation-engine/`
**Port:** 8080
**Language:** Python 3.11, FastAPI 0.104+, Uvicorn 0.24+

#### Module Map

| Module | Responsibility |
|---|---|
| `app/main.py` | Application bootstrap, middleware, lifespan hooks |
| `app/config.py` | Pydantic-settings: reads all env vars with defaults |
| `app/models.py` | Pydantic data models for all API request/response bodies |
| `app/database.py` | Async SQLite via aiosqlite (users, progress, SECA reviews) |
| `app/redis_schema.py` | Redis data models: `TraceIndex`, `CircuitEvent` |
| `app/observability.py` | Self-instrumentation: FastAPI OTel middleware, httpx tracing |
| `app/profiling.py` | Pyroscope initialisation |
| `app/pipeline/correlator.py` | Core correlation logic (windowing, business-ID matching) |
| `app/pipeline/exporters.py` | Multi-backend export with circuit breakers |
| `app/pipeline/processors.py` | OTLP protobuf parsing and attribute normalisation |
| `app/mdso/client.py` | HTTP client for MDSO REST API |
| `app/mdso/repository.py` | MDSO data access layer |
| `app/mdso/error_analyzer.py` | SECA error classification engine |
| `app/routes/otlp.py` | OTLP ingestion endpoints (345 lines) |
| `app/routes/correlations.py` | Correlation query API |
| `app/routes/health.py` | Liveness, readiness, component status |
| `app/routes/user_auth.py` | Authentication (SHA-256, session tokens) |
| `app/routes/seca_reviews.py` | SECA error CRUD and priority management |
| `app/pdf_generator.py` | PDF report generation (ReportLab) |
| `app/seca_scraper.py` | Selenium-based SECA data collection |
| `app/seca_xlsx_processor.py` | Excel SECA data import (openpyxl) |

#### Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOKI_URL` | `http://loki:3100` | Loki push endpoint |
| `TEMPO_URL` | `http://tempo:3200` | Tempo OTLP endpoint |
| `PROMETHEUS_URL` | `http://prometheus:9090` | Prometheus remote-write target |
| `REDIS_URL` | `redis://redis:6379` | Redis connection string |
| `CORRELATION_WINDOW_SECONDS` | `60` | Correlation time window |
| `LOG_QUEUE_MAX_SIZE` | `10000` | Max pending log records |
| `TRACE_QUEUE_MAX_SIZE` | `5000` | Max pending spans |
| `ENABLE_TRACE_SYNTHESIS` | `true` | Generate synthetic traces for un-instrumented services |
| `ENABLE_DATADOG` | `false` | Enable Datadog dual-write |
| `DD_API_KEY` | _(required if Datadog enabled)_ | Datadog API key |
| `AUTH_ENABLED` | `true` | Enable user authentication |
| `PYROSCOPE_URL` | `http://pyroscope:4040` | Continuous profiling server |

---

### 5.2 OTel Gateway

**Path:** `seefa-om/gateway/`
**Config:** `otel-config.yaml`

The gateway is a vanilla **OpenTelemetry Collector 0.96** instance acting as a fan-out router.

#### Receiver → Exporter Mapping

| Signal | Receiver Port | Exporters |
|---|---|---|
| Traces (gRPC) | 4317 | Correlation Engine, Tempo |
| Traces (HTTP) | 4318 | Correlation Engine, Tempo |
| Logs (HTTP) | 4318 | Correlation Engine, Loki |
| Metrics | 4317/4318 | Correlation Engine, Prometheus |

#### Pipeline Processors

```yaml
processors:
  batch:
    send_batch_size: 500
    timeout: 200ms
  memory_limiter:
    limit_mib: 512
    spike_limit_mib: 128
    check_interval: 5s
  attributes/add_env:
    actions:
      - key: deployment.environment
        value: ${ENVIRONMENT}
        action: insert
```

---

### 5.3 Sense Apps (Demo Microservices)

**Path:** `seefa-om/sense-apps/`

Three purpose-built microservices that simulate realistic MDSO workflows and emit OTel telemetry.

| Service | Framework | Port | Role |
|---|---|---|---|
| **ARDA** | FastAPI | 5001 | Inventory & SEEFA circuit design (90+ endpoints) |
| **BEORN** | Flask | 5002 | Authentication & identity, trace context propagation |
| **PALANTIR** | Flask | 5003 | Data aggregation, request tracing |

All three share a common OTel configuration pattern:

```python
# Common OTel setup in each sense app
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

with tracer.start_as_current_span("provision_circuit") as span:
    span.set_attribute("circuit_id", circuit_id)
    span.set_attribute("product_id", product_id)
    span.set_attribute("resource_id", resource_id)
    # ...business logic...
```

Exporter: OTLP/gRPC → `otel-gateway:4317`

---

### 5.4 Grafana Alloy Log Collector

**Path:** `seefa-om/mdso-alloy/`

Grafana Alloy (successor to Grafana Agent) tails the live MDSO system log and ships it as structured OTLP.

**Source:** `/var/log/ciena/blueplanet.log` (syslog format)
**Output:** OTLP/HTTP → OTel Gateway `:4318`
**Deployment:** systemd service on the MDSO Dev host

**Pipeline:**
1. `local.file_match` — watches for new log lines
2. `loki.source.file` — reads and parses syslog
3. `otelcol.receiver.loki` — converts Loki log entries to OTel log records
4. `otelcol.exporter.otlphttp` — forwards to gateway

---

### 5.5 Observability Stack

**Path:** `seefa-om/observability-stack/`

Pre-configured with Docker Compose. All services run in the `observability` Docker network.

| Service | Version | Port | Role | Retention |
|---|---|---|---|---|
| Grafana | 10.2 | 8443 (HTTPS) | Dashboards & alerting | N/A |
| Prometheus | 2.48 | 9090 | Metrics TSDB | 15 days |
| Loki | 2.9 | 3100 | Log aggregation | 7 days |
| Tempo | 2.3 | 3200 | Distributed traces | 7 days |
| Pyroscope | latest | 4040 | Continuous profiling | 7 days |
| Redis | 7 | 6379 | Cache & queue | 48-hour TTL |

---

### 5.6 React Frontend

**Path:** `seefa-om/frontend/`
**Port:** 3002
**Stack:** React 18.3 · TypeScript 5.6 · Vite 5.4 · Zustand 4.5 · Tailwind CSS 3.4 · Recharts 3.5

#### Page Map

| Route | Page | Description |
|---|---|---|
| `/` | `HomePage` | Landing page with platform summary |
| `/engine` | `CorrelationEnginePage` | Real-time KPI dashboard with Recharts |
| `/seca` | `SecaReviewsPage` | SECA error tracking with filters |
| `/login` | `LoginPage` | Authentication flow |
| `/compliance` | `CompliancePage` | Compliance reporting |
| `/architecture` | `ArchitecturePage` | Embedded architecture diagrams |
| `/tutorials` | `TutorialsPageNew` | 20+ interactive OTel tutorials |

#### State Management

```
Zustand store (persisted to localStorage)
├── auth/
│   ├── user: { id, username, role }
│   ├── token: string
│   └── actions: login(), logout(), register()
└── progress/
    ├── completedModules: Set<string>
    └── actions: markComplete(), reset()
```

#### API Communication

All API calls go through `lib/httpClient.ts` which:
- Attaches the JWT bearer token from Zustand on every request
- Proxies to the correlation engine via Vite's dev proxy (→ `http://correlation-engine:8080`)
- Normalises error shapes into `{ message, status, detail }`

---

## 6. OpenTelemetry Integration

### 6.1 SDK Instrumentation Strategy

The platform follows the **OTel API / SDK separation principle**:

- **Application code uses the OTel API** (`opentelemetry-api`) — zero vendor lock-in.
- **Runtime binds the SDK** (`opentelemetry-sdk`) — configured once at startup in `app/observability.py`.
- **Auto-instrumentation patches** (`opentelemetry-instrumentation-*`) handle FastAPI, HTTPX, SQLAlchemy, and Redis with zero application code changes.

```python
# app/observability.py — SDK bootstrap
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

provider = TracerProvider(resource=Resource.create({
    SERVICE_NAME: "correlation-engine",
    "service.version": os.getenv("APP_VERSION", "dev"),
    "deployment.environment": os.getenv("ENVIRONMENT", "development"),
}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-gateway:4317")
)))
trace.set_tracer_provider(provider)

FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
```

### 6.2 OTLP Protocol Endpoints

**File:** `app/routes/otlp.py`

| Endpoint | Method | Content-Type | Signal |
|---|---|---|---|
| `/v1/logs` | POST | `application/x-protobuf` | OTLP LogsServiceRequest |
| `/v1/traces` | POST | `application/x-protobuf` | OTLP TracesServiceRequest |
| `/v1/metrics` | POST | `application/x-protobuf` | OTLP MetricsServiceRequest |
| `/v1/logs` | POST | `application/json` | OTLP JSON encoding |
| `/v1/traces` | POST | `application/json` | OTLP JSON encoding |

Both protobuf and JSON encodings are supported for compatibility with all OTel SDKs.

### 6.3 Attribute Schema

All telemetry MUST carry the following attributes to participate in business-ID correlation:

```
Resource attributes (set once per SDK instance):
  service.name          string   e.g. "arda", "beorn", "palantir", "mdso-core"
  service.version       string   semver
  deployment.environment string  "production" | "staging" | "development"

Span / Log attributes (set per operation):
  circuit_id            string   UUID of the circuit being provisioned
  product_id            string   Product SKU
  resource_id           string   Network resource identifier
  resource_type_id      string   Device/port/service type
  request_id            string   Per-API-call unique ID (UUID v4)
```

Services lacking native OTel instrumentation (legacy MDSO components) MUST at minimum include `circuit_id` in their structured log lines so the engine can synthesise traces.

---

## 7. Storage Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Storage Layer                            │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐  │
│  │  SQLite    │  │    Redis     │  │   Loki   │  │  Tempo   │  │
│  │            │  │              │  │          │  │          │  │
│  │ Users      │  │ TraceIndex   │  │  Logs    │  │  Traces  │  │
│  │ Auth       │  │ CircuitEvents│  │  (7 days)│  │  (7 days)│  │
│  │ Progress   │  │ CorrelEvents │  │          │  │          │  │
│  │ SECA data  │  │ Job queue    │  │ LogQL    │  │  TraceQL │  │
│  │            │  │ (48hr TTL)   │  │          │  │          │  │
│  └────────────┘  └──────────────┘  └──────────┘  └──────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               Prometheus (Metrics TSDB)                    │  │
│  │  15-day retention · scrapes every 15 s · PromQL queries    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Ownership

| Store | Data | Access Pattern | Backup |
|---|---|---|---|
| SQLite | Users, sessions, SECA reviews, tutorial progress | Low-volume transactional | Daily snapshot |
| Redis | Active correlation state, telemetry index | High-throughput KV; TTL-based eviction | Optional RDB/AOF |
| Loki | Log streams | Write-once append; LogQL reads | Object storage backend |
| Tempo | Trace data | Write-once append; TraceQL reads | Object storage backend |
| Prometheus | Metrics time-series | Scrape write; PromQL reads | Thanos/Cortex for HA |

---

## 8. Redis Caching Layer

**File:** `app/redis_schema.py`

Redis serves two roles: **telemetry index** (100× faster correlation lookups) and **job queue** (background SECA processing via RQ).

### Data Structures

```
# TraceIndex — indexed by trace_id
KEY  trace:{trace_id}
TYPE hash
FIELDS:
  span_ids        list<string>
  service_names   list<string>
  start_time      float (unix epoch)
  end_time        float (unix epoch)
  circuit_id      string
  product_id      string
TTL  48 hours

# CircuitEvent — indexed by circuit_id
KEY  circuit:{circuit_id}:events
TYPE list (sorted by timestamp)
ELEMENTS:
  JSON-serialised CorrelationEvent
TTL  48 hours

# Exporter queue — one per backend
KEY  export_queue:{loki|tempo|prometheus|datadog}
TYPE list (FIFO)
ELEMENTS:
  JSON-serialised telemetry batch
TTL  none (manual consumption by exporter worker)
```

### Why Redis for Correlation?

Without a cache, each correlation check requires querying Loki and Tempo over HTTP for every incoming event — 50–200 ms per call. With Redis, the trace index is a local hash lookup — O(1) at sub-millisecond latency. At 1 000 events/second this is the difference between a single-core pipeline saturating at ~200 events/sec versus handling the full load with headroom.

---

## 9. Multi-Backend Export

**File:** `app/pipeline/exporters.py`

The `ExportManager` class manages concurrent fan-out to all configured backends:

```python
class ExportManager:
    backends: list[Backend] = [
        LokiExporter(),
        TempoExporter(),
        PrometheusExporter(),
        DatadogExporter(),   # only when ENABLE_DATADOG=true
    ]

    async def export_batch(self, batch: TelemetryBatch) -> ExportResult:
        results = await asyncio.gather(
            *[b.export(batch) for b in self.backends if b.enabled],
            return_exceptions=True
        )
        return ExportResult(successes=..., failures=...)
```

Each `Backend` wraps its HTTP call with:
1. **Circuit breaker** (see §3.3)
2. **Retry with exponential backoff** (max 3 retries, 1 s / 2 s / 4 s delays)
3. **Prometheus counter** incremented on success/failure

### Loki Export

- Endpoint: `POST /loki/api/v1/push`
- Payload: `{ streams: [{ stream: { service_name, level, environment }, values: [[ts, line]] }] }`
- Label cardinality: exactly 3 labels — prevents high-cardinality Loki stream explosion

### Tempo Export

- Endpoint: `POST /otlp/v1/traces` (OTLP/HTTP JSON)
- Payload: standard `TracesData` protobuf message serialised as JSON
- Trace ID: 128-bit hex string (W3C-compatible)

### Prometheus Export

- Uses `prometheus_client` library — metrics are **pushed** from the engine to Prometheus via remote-write OR pulled by Prometheus scraping `/metrics`
- Key metrics: see §16

---

## 10. Service-Level Objectives (SLOs)

SLOs for each component are expressed as availability + latency targets. Burn rates are calculated over a 30-day rolling window.

### Correlation Engine

| SLO | Target | Alert Threshold |
|---|---|---|
| Availability (5xx rate) | ≥ 99.9% | Error rate > 0.1% over 5 min |
| P50 ingestion latency | ≤ 10 ms | P50 > 25 ms over 10 min |
| P99 ingestion latency | ≤ 200 ms | P99 > 500 ms over 5 min |
| Correlation window lag | ≤ 90 s | Lag > 3× window over 10 min |
| Queue depth (logs) | < 80% of max | > 80% sustained for 5 min |
| Queue depth (traces) | < 80% of max | > 80% sustained for 5 min |

### OTel Gateway

| SLO | Target | Alert Threshold |
|---|---|---|
| Availability | ≥ 99.9% | Any restart within 5 min |
| Export success rate | ≥ 99.5% | Failure rate > 0.5% over 5 min |
| Memory usage | < 80% of limit (512 MiB) | > 80% sustained for 5 min |

### Sense Apps (ARDA / BEORN / PALANTIR)

| SLO | Target | Alert Threshold |
|---|---|---|
| HTTP 5xx rate | ≤ 0.1% | > 1% over 5 min |
| P99 response time | ≤ 500 ms | > 1 s over 10 min |
| OTel export success | ≥ 99% | < 95% over 5 min |

### Grafana Alloy

| SLO | Target | Alert Threshold |
|---|---|---|
| Log tail lag | ≤ 30 s behind real time | Lag > 60 s for 5 min |
| Export drop rate | ≤ 0.01% | Any drop over 15 min |

### Observability Stack (Loki / Tempo / Prometheus)

| Service | SLO | Target |
|---|---|---|
| Loki | Write availability | ≥ 99.5% |
| Loki | Query P99 | ≤ 2 s for 1-hour range |
| Tempo | Write availability | ≥ 99.5% |
| Tempo | Trace lookup P99 | ≤ 500 ms |
| Prometheus | Scrape success rate | ≥ 99.9% |
| Prometheus | Query P99 | ≤ 500 ms for instant queries |

### Error Budget Calculation

```
Error budget (30 days) = 30 days × (1 − SLO target)
Example (Correlation Engine, 99.9% availability):
  = 43,200 min × 0.001
  = 43.2 minutes per month
```

Prometheus rule to track spend rate:

```yaml
# In prometheus/rules/slo.yml
- alert: CorrelationEngineErrorBudgetBurn
  expr: |
    sum(rate(http_requests_total{job="correlation-engine",status=~"5.."}[1h]))
    /
    sum(rate(http_requests_total{job="correlation-engine"}[1h]))
    > 0.001
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Correlation engine error budget burning fast"
```

---

## 11. Horizontal Scaling

**Reference:** `seefa-om/docs/HORIZONTAL_SCALING_SETUP_GUIDE.md`

The engine is designed to scale horizontally. All mutable state is stored externally in Redis; the FastAPI process itself is stateless.

```
                  Load Balancer (NGINX / k8s Ingress)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
  Engine replica-1  replica-2  replica-3
          │              │              │
          └──────────────┼──────────────┘
                         │
                      Redis
               (shared state store)
```

**Scaling checklist:**

- [ ] `REDIS_URL` points to shared Redis (not `localhost`)
- [ ] Each replica has a unique `REPLICA_ID` env var (used for leader election)
- [ ] Session affinity disabled — requests can hit any replica
- [ ] Correlation window state stored in Redis (not in-process)
- [ ] Export queue stored in Redis — any replica can consume
- [ ] Leader election via Redis `SETNX` for the correlator worker (prevents duplicate processing)

**Kubernetes HPA example:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: correlation-engine-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: correlation-engine
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: correlation_engine_queue_depth
      target:
        type: AverageValue
        averageValue: "5000"
```

---

## 12. Deployment Guide

### 12.1 Docker Compose (Development)

**Prerequisites:** Docker 20.10+, Docker Compose 2.0+, 8 GiB RAM minimum

```bash
# Clone and enter the project
cd seefa-om

# Copy environment template
cp correlation-engine/.env.example correlation-engine/.env

# Start all services (detached)
make up
# Equivalent to: docker compose up -d

# Check health of all services
make health

# Tail logs for correlation engine
docker compose logs -f correlation-engine

# Run test suite
make test

# Stop all services
make down
```

**Service startup order** (enforced via `depends_on`):

```
redis → correlation-engine → otel-gateway → sense-apps → grafana-alloy
                         ↗
observability-stack (grafana, prometheus, loki, tempo, pyroscope) — independent
```

**Useful Make targets:**

| Target | Description |
|---|---|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Rolling restart of correlation engine |
| `make health` | Check all service health endpoints |
| `make test` | Run full test suite with coverage |
| `make lint` | Run ruff + flake8 |
| `make build` | Build all Docker images |
| `make logs` | Tail correlation engine logs |
| `make redis-cli` | Open Redis CLI in container |
| `make psql` | Open SQLite shell |

### 12.2 Kubernetes (Production)

**Manifests:** `portfolio/k8s/demo/`

Apply in order:

```bash
# 1. Namespace
kubectl apply -f 00-namespace.yaml

# 2. Config and secrets
kubectl apply -f 40-configmap.yaml
kubectl create secret generic correlation-engine-secrets \
  --from-env-file=correlation-engine/.env \
  -n correlation-station

# 3. Stateful services
kubectl apply -f 10-redis.yaml

# 4. Application services
kubectl apply -f 20-correlation-engine.yaml
kubectl apply -f 30-arda-demo.yaml

# 5. Ingress
kubectl apply -f 50-ingress.yaml

# Wait for rollout
kubectl rollout status deployment/correlation-engine -n correlation-station
```

**Resource requests/limits** (per replica):

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
```

**Health probes:**

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## 13. CI/CD Pipeline

**File:** `.gitlab-ci.yml` (248 lines)

The GitLab CI pipeline has 5 stages:

```
lint ──► test ──► build ──► deploy ──► validate
```

### Stage Details

| Stage | Jobs | Tools | Triggers |
|---|---|---|---|
| `lint` | `ruff-check`, `flake8-check` | ruff, flake8 | Every push |
| `test` | `pytest-unit`, `pytest-integration` | pytest 7.4, pytest-asyncio, pytest-cov | Every push |
| `build` | `build-engine`, `build-frontend`, `build-worker` | Docker buildx | Tags + main |
| `deploy` | `deploy-staging`, `deploy-production` | docker stack deploy / kubectl | Tags only |
| `validate` | `health-check`, `smoke-test` | curl, httpx | After deploy |

**Coverage gate:** merge requests are blocked if coverage drops below 75%.

**Notification:** Slack webhook on pipeline failure (configurable via `SLACK_WEBHOOK_URL` CI variable).

---

## 14. Operations Runbook

### Starting / Stopping Services

```bash
# Start specific service
docker compose up -d correlation-engine

# Restart after config change
docker compose restart correlation-engine

# Force recreate (picks up new image)
docker compose up -d --force-recreate correlation-engine

# Emergency stop
docker compose stop correlation-engine
```

### Checking Health

```bash
# Overall health
curl http://localhost:8080/health

# Detailed component status
curl http://localhost:8080/health/components | jq .

# Redis connectivity
docker compose exec redis redis-cli ping

# Loki write health
curl http://localhost:3100/ready
```

### Viewing Metrics

```bash
# Prometheus raw metrics
curl http://localhost:8080/metrics

# Key counters
curl -s http://localhost:8080/metrics | grep correlation_engine_
```

### Draining and Restarting the Correlation Engine

```bash
# 1. Enable maintenance mode (stops new ingestion)
curl -X POST http://localhost:8080/admin/maintenance/enable

# 2. Wait for in-flight queue to drain
watch -n 2 'curl -s http://localhost:8080/health/components | jq .queue_depth'

# 3. Restart
docker compose restart correlation-engine

# 4. Disable maintenance mode
curl -X POST http://localhost:8080/admin/maintenance/disable
```

### Flushing Redis State

```bash
# Flush correlation event cache only (preserves job queue)
docker compose exec redis redis-cli --scan --pattern "circuit:*" \
  | xargs docker compose exec -T redis redis-cli DEL

# Nuclear option (clears ALL Redis state)
docker compose exec redis redis-cli FLUSHDB
```

### Rotating Logs

Loki retains logs for 7 days by default. To adjust:

```yaml
# observability-stack/loki/loki-config.yaml
limits_config:
  retention_period: 168h  # 7 days; increase as needed
```

### Backup Procedures

```bash
# SQLite backup
docker compose exec correlation-engine \
  sqlite3 /app/data/correlation.db ".backup /app/data/backup-$(date +%Y%m%d).db"

# Copy backup out of container
docker compose cp correlation-engine:/app/data/backup-*.db ./backups/

# Redis RDB snapshot
docker compose exec redis redis-cli BGSAVE
docker compose cp redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb
```

---

## 15. Security Hardening

### Container Security

- All application containers run as **non-root** users (UID 1000).
- Read-only root filesystems where possible (`read_only: true` in Compose).
- No `--privileged` flag; only required capabilities are added.
- Images are based on `python:3.11-slim` and `node:20-slim` — minimal attack surface.

### Authentication

- User passwords hashed with **SHA-256** + per-user salt (see `app/routes/user_auth.py`).
- Session tokens are opaque random strings stored in Redis with a 24-hour TTL.
- All authenticated routes require `Authorization: Bearer <token>` header.
- Role-based: `admin` can manage users; `operator` can read/write correlations; `viewer` is read-only.

### Network Isolation

- All services communicate over the `observability` Docker network — not exposed to the host unless explicitly port-mapped.
- The OTel Gateway is the only service that accepts external OTLP; all other services are internal only.
- Grafana is exposed on HTTPS `:8443` with self-signed TLS by default; replace with a signed cert in production.

### Secrets Management

- All secrets (API keys, DB passwords) are passed as environment variables, never baked into images.
- In Kubernetes, use `Secret` objects and inject via `envFrom`.
- Recommended: integrate with HashiCorp Vault or AWS Secrets Manager for production.

---

## 16. Metrics Reference

All metrics are exposed at `GET /metrics` (Prometheus text format).

### Pipeline Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `correlation_engine_logs_ingested_total` | Counter | `service_name` | Total log records received |
| `correlation_engine_traces_ingested_total` | Counter | `service_name` | Total spans received |
| `correlation_engine_correlations_created_total` | Counter | `type`, `confidence` | Correlations emitted |
| `correlation_engine_dropped_total` | Counter | `signal_type` | Records dropped due to full queue |
| `correlation_engine_queue_depth` | Gauge | `signal_type` | Current queue depth |
| `correlation_engine_window_lag_seconds` | Histogram | — | Delay between signal receipt and window close |

### Export Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `correlation_engine_export_success_total` | Counter | `backend` | Successful export batches |
| `correlation_engine_export_failures_total` | Counter | `backend` | Failed export batches |
| `correlation_engine_circuit_breaker_state` | Gauge | `backend` | 0=CLOSED, 1=HALF-OPEN, 2=OPEN |
| `correlation_engine_export_latency_seconds` | Histogram | `backend` | Time per export call |

### HTTP Metrics (auto-instrumented by OpenTelemetry)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `http_server_request_duration_seconds` | Histogram | `method`, `route`, `status_code` | FastAPI request latency |
| `http_server_active_requests` | Gauge | `method`, `route` | In-flight requests |

### System Metrics (Prometheus node_exporter)

Standard CPU, memory, disk, and network metrics for the host. Recommended to deploy `node_exporter` alongside the stack for infrastructure-level visibility.

---

## 17. API Reference Summary

Full interactive docs available at `http://localhost:8080/docs` (Swagger UI) or `http://localhost:8080/redoc` (ReDoc).

### Ingestion Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/v1/logs` | OTLP log ingestion (proto or JSON) |
| POST | `/v1/traces` | OTLP trace ingestion (proto or JSON) |
| POST | `/v1/metrics` | OTLP metrics ingestion (proto or JSON) |
| POST | `/api/v1/logs` | Custom structured log ingestion |

### Correlation Query Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/correlations` | List correlations (filter by circuit_id, time range) |
| GET | `/api/v1/correlations/{id}` | Get single correlation event |
| GET | `/api/v1/correlations/circuit/{circuit_id}` | All events for a circuit |

### SECA Review Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/seca/reviews` | List SECA error reviews |
| POST | `/api/v1/seca/reviews` | Create new SECA review |
| PUT | `/api/v1/seca/reviews/{id}` | Update review status / priority |
| DELETE | `/api/v1/seca/reviews/{id}` | Delete review |
| POST | `/api/v1/seca/upload` | Upload SECA Excel file |
| GET | `/api/v1/seca/report` | Generate PDF report |

### Authentication Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Authenticate, returns session token |
| POST | `/api/v1/auth/register` | Create new user account |
| POST | `/api/v1/auth/logout` | Invalidate session token |
| GET | `/api/v1/auth/me` | Get current user profile |

### Health Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Overall health (200 OK / 503) |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe (checks Redis, Loki, Tempo) |
| GET | `/health/components` | Detailed per-component status |

---

## 18. Troubleshooting Guide

### No correlations appearing in the dashboard

1. **Check queue depth:** `curl http://localhost:8080/health/components | jq .queue_depth`
2. **Check circuit breakers:** `curl -s http://localhost:8080/metrics | grep circuit_breaker_state`
3. **Verify OTel attributes:** Ensure spans carry `circuit_id` or `trace_id` — without these no correlation is possible.
4. **Check window flush:** Correlations only appear after the window closes (default 60 s). Wait 90 s after sending telemetry.

### High correlation lag

- **Symptom:** `correlation_engine_window_lag_seconds` P99 > 90 s
- **Cause 1:** Export backends are slow (high Loki/Tempo latency). Check `export_latency_seconds`.
- **Cause 2:** Queue depth near `LOG_QUEUE_MAX_SIZE` — increase queue size or add engine replicas.
- **Cause 3:** Correlator worker is CPU-bound — profile with Pyroscope at `:4040`.

### Loki export failing (circuit open)

1. `curl http://localhost:3100/ready` — if not ready, restart Loki.
2. Check Loki disk usage: `df -h $(docker inspect loki | jq -r '.[0].Mounts[0].Source')`
3. If Loki disk is full, increase storage or prune old streams: `docker compose exec loki lokitool delete --tenant=fake --query='{service_name="old-service"}' --from=2024-01-01T00:00:00Z --to=2024-06-01T00:00:00Z`

### Redis connection refused

1. `docker compose ps redis` — verify running.
2. `docker compose exec redis redis-cli ping` — should return `PONG`.
3. Check memory: `docker compose exec redis redis-cli INFO memory | grep used_memory_human`
4. If OOM: increase `--maxmemory` in Redis config or flush stale keys.

### Frontend shows "Failed to fetch"

1. Verify correlation engine is running: `curl http://localhost:8080/health`.
2. Check CORS: the engine must have the frontend origin in `CORS_ORIGINS`.
3. Check browser console for the actual HTTP status code.
4. Verify Vite proxy config in `frontend/vite.config.ts` matches the engine URL.

### GitLab CI lint failing

```bash
# Run locally before push
cd seefa-om/correlation-engine
pip install ruff flake8
ruff check app/
flake8 app/ --max-line-length=120
```

---

## 19. Go Integration Strategy

When integrating a Go-based MDSO component (e.g., a new provisioning microservice written in Go), follow this pattern to participate in the observability platform:

### 1. Install the Go OTel SDK

```bash
go get go.opentelemetry.io/otel@latest
go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc@latest
go get go.opentelemetry.io/otel/sdk/trace@latest
go get go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp@latest
```

### 2. Bootstrap the tracer (once at startup)

```go
// otel.go
package observability

import (
    "context"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

func InitTracer(serviceName, endpoint string) (*sdktrace.TracerProvider, error) {
    exporter, err := otlptracegrpc.New(
        context.Background(),
        otlptracegrpc.WithEndpoint(endpoint), // "otel-gateway:4317"
        otlptracegrpc.WithInsecure(),
    )
    if err != nil {
        return nil, err
    }

    res := resource.NewWithAttributes(
        semconv.SchemaURL,
        semconv.ServiceName(serviceName),
        attribute.String("deployment.environment", "production"),
    )

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
    )
    otel.SetTracerProvider(tp)
    return tp, nil
}
```

### 3. Instrument HTTP handlers

```go
import "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

// Wrap your existing ServeMux
http.Handle("/provision", otelhttp.NewHandler(
    http.HandlerFunc(provisionHandler),
    "provision-circuit",
))
```

### 4. Add MDSO business attributes

```go
tracer := otel.Tracer("mdso-go-service")
ctx, span := tracer.Start(r.Context(), "provision_circuit")
defer span.End()

span.SetAttributes(
    attribute.String("circuit_id", req.CircuitID),
    attribute.String("product_id", req.ProductID),
    attribute.String("resource_id", req.ResourceID),
    attribute.String("resource_type_id", req.ResourceTypeID),
    attribute.String("request_id", requestID),
)
```

### 5. Structured logging with trace context injection

```go
import (
    "go.opentelemetry.io/otel/trace"
    "go.uber.org/zap"
)

spanCtx := trace.SpanFromContext(ctx).SpanContext()
logger.Info("provisioning started",
    zap.String("trace_id", spanCtx.TraceID().String()),
    zap.String("span_id", spanCtx.SpanID().String()),
    zap.String("circuit_id", req.CircuitID),
)
```

Injecting `trace_id` and `span_id` into log lines allows the correlation engine's **Pass 1 (exact match)** to link Go service logs to their parent spans even before they reach Loki.

### 6. Export target

Point `OTEL_EXPORTER_OTLP_ENDPOINT` to `otel-gateway:4317`. The gateway handles routing to the correlation engine, Loki, and Tempo — no per-service configuration needed.

---

## 20. Datadog Dual-Write Strategy

The platform supports parallel export to Datadog alongside the Grafana stack, enabling a migration path from Datadog to the open-source stack without losing existing dashboards or alerts.

### Enabling Dual-Write

```bash
# correlation-engine/.env
ENABLE_DATADOG=true
DD_API_KEY=<your-datadog-api-key>
DD_SITE=datadoghq.com          # or datadoghq.eu
DD_SERVICE=correlation-station
DD_ENV=production
```

### What Gets Sent to Datadog

| Signal | Datadog Product | Notes |
|---|---|---|
| Traces | APM | Forwarded as OTLP via `otlp.agent.datadoghq.com:443` |
| Logs | Log Management | Forwarded via Datadog Logs Intake API |
| Metrics | Metrics | Only custom business metrics; infra metrics still come from Datadog Agent |
| Profiles | Continuous Profiler | Pyroscope profiles converted to Datadog pprof format |

### Architecture with Dual-Write

```
OTel Collector Gateway
        │
        ├──► Correlation Engine ──► Loki / Tempo / Prometheus (OSS stack)
        │                      └──► Datadog Logs Intake / APM / Metrics
        │
        └──► Datadog Agent (running on host)
                  └──► Infrastructure metrics (CPU, memory, disk)
```

### ddtrace SDK vs OTel API

For Python services that already use `ddtrace`, the recommended migration path is:

1. **Phase 1 (current):** Run `ddtrace` alongside `opentelemetry-sdk`. Both SDKs instrument the same application simultaneously. This produces duplicate traces but allows Datadog dashboards to keep working.

2. **Phase 2:** Replace `ddtrace.tracer.start_span()` calls with `opentelemetry.trace.get_tracer().start_as_current_span()`. Remove ddtrace import.

3. **Phase 3:** Remove `ddtrace` dependency entirely. All telemetry flows through OTel → Correlation Engine. Datadog receives data via the OTel exporter, not a native SDK.

**Phase 1 configuration example:**

```python
# Both SDKs active simultaneously
import ddtrace
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# ddtrace auto-patches (legacy)
ddtrace.patch_all()

# OTel SDK (new)
provider = TracerProvider(...)
trace.set_tracer_provider(provider)

# Application code uses OTel API going forward
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my_span") as span:
    span.set_attribute("circuit_id", cid)
    # ddtrace still captures this via its own patcher
```

**Disabling Datadog export** once migration is complete:

```bash
ENABLE_DATADOG=false  # Removes Datadog from the ExportManager fan-out
```

No code changes required — the circuit-breaker state for the Datadog backend is simply never created when the feature flag is off.

---

*Last updated: 2026-02-25 · Correlation Station v1.0 · MDSO Observability Platform*
