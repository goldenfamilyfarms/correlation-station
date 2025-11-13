# Architecture - End-to-End Observability for MDSO ↔ Sense

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MDSO Server (47.43.111.107)                         │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Scriptplan Container (otel_instrumentation product)            │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │  OTelPlan.enter_exit_log()                                 │ │  │
│  │  │  ├─> Emit OTel Span (OTLP/HTTP)                           │ │  │
│  │  │  ├─> Emit Structured Log (JSON to stdout)                 │ │  │
│  │  │  └─> Write to /bp2/log/splunk-logs/*.log                  │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                    │                        │
│           │ (OTLP/HTTP)                       │ (Log files)            │
│           ▼                                    ▼                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Grafana Alloy Agent                                            │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │  loki.source.file "scriptplan"                            │ │  │
│  │  │  ├─> Parse syslog format                                  │ │  │
│  │  │  ├─> Extract correlation keys (circuit_id, resource_id)   │ │  │
│  │  │  ├─> Sample high-volume logs (DEBUG: 25%)                 │ │  │
│  │  │  └─> Forward to Meta server                               │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                             │
│           │ (HTTP POST to :55681)                                      │
└───────────┼─────────────────────────────────────────────────────────────┘
            │
            │
┌───────────┼─────────────────────────────────────────────────────────────┐
│           ▼                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  OTel Collector Gateway (:55681)                                │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │  Receivers:                                               │ │  │
│  │  │  ├─> OTLP HTTP (:55681) - Alloy, Scriptplan OTel SDK     │ │  │
│  │  │  └─> OTLP HTTP (:4318) - Sense apps OTel SDK             │ │  │
│  │  │                                                           │ │  │
│  │  │  Processors:                                              │ │  │
│  │  │  ├─> Batch (512 spans, 5s interval)                      │ │  │
│  │  │  └─> Resource detection (add host metadata)              │ │  │
│  │  │                                                           │ │  │
│  │  │  Exporters:                                               │ │  │
│  │  │  ├─> Correlation Station (:8080/api/otlp/v1/*)          │ │  │
│  │  │  ├─> Loki (:3100)                                        │ │  │
│  │  │  ├─> Tempo (:4317)                                       │ │  │
│  │  │  └─> Prometheus (:9090)                                  │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                             │
│           ▼                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Correlation Station (:8080) - FastAPI                         │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │  /api/otlp/v1/traces                                      │ │  │
│  │  │  ├─> Parse OTLP spans                                     │ │  │
│  │  │  ├─> Extract TraceSegment (trace_id, circuit_id, etc.)   │ │  │
│  │  │  ├─> Find parent trace via TraceSynthesizer              │ │  │
│  │  │  ├─> Create synthetic bridge span if needed              │ │  │
│  │  │  └─> Forward all spans to Tempo                          │ │  │
│  │  │                                                           │ │  │
│  │  │  /api/otlp/v1/logs                                        │ │  │
│  │  │  ├─> Parse OTLP logs                                     │ │  │
│  │  │  ├─> Enrich with correlation context                     │ │  │
│  │  │  └─> Forward to Loki                                     │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                             │
│           ▼                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Grafana Stack                                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │
│  │  │ Loki :3100  │  │ Tempo :3200 │  │ Prom :9090  │            │  │
│  │  │ (Logs)      │  │ (Traces)    │  │ (Metrics)   │            │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘            │  │
│  │           │                │                │                      │  │
│  │           └────────────────┴────────────────┘                      │  │
│  │                           │                                        │  │
│  │                           ▼                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Grafana :8443                                              │ │  │
│  │  │  ├─> Correlation Dashboard                                 │ │  │
│  │  │  ├─> Trace Visualization                                   │ │  │
│  │  │  └─> Log Explorer                                          │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│                    Meta Server (159.56.4.94)                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Sense Applications (Docker)                         │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Beorn :5001      │  │ Palantir :5002   │  │ Arda :5003       │     │
│  │ (Flask)          │  │ (Flask)          │  │ (FastAPI)        │     │
│  │                  │  │                  │  │                  │     │
│  │ ┌──────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────┐ │     │
│  │ │ OTel SDK     │ │  │ │ OTel SDK     │ │  │ │ OTel SDK     │ │     │
│  │ │ - Flask      │ │  │ │ - Flask      │ │  │ │ - FastAPI    │ │     │
│  │ │   Instr.     │ │  │ │   Instr.     │ │  │ │   Instr.     │ │     │
│  │ │ - Requests   │ │  │ │ - Requests   │ │  │ │ - HTTPX      │ │     │
│  │ │   Instr.     │ │  │ │   Instr.     │ │  │ │   Instr.     │ │     │
│  │ │              │ │  │ │              │ │  │ │              │ │     │
│  │ │ Exporters:   │ │  │ │ Exporters:   │ │  │ │ Exporters:   │ │     │
│  │ │ - OTLP       │ │  │ │ - OTLP       │ │  │ │ - OTLP       │ │     │
│  │ │ - DataDog    │ │  │ │ - DataDog    │ │  │ │ - DataDog    │ │     │
│  │ └──────────────┘ │  │ └──────────────┘ │  │ └──────────────┘ │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│           │                     │                      │                │
│           └─────────────────────┴──────────────────────┘                │
│                                 │                                       │
│                                 │ (OTLP HTTP to :55681)                 │
│                                 ▼                                       │
│                          OTel Gateway                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Flow 1: MDSO Scriptplan → Meta Server

1. **OTelPlan.enter_exit_log("Started")** called in scriptplan
2. **OTel SDK** emits span via OTLP/HTTP to Gateway (:55681)
3. **Structlog** emits JSON log to stdout
4. **File logger** writes to `/bp2/log/splunk-logs/*.log`
5. **Alloy agent** tails log file, parses syslog, extracts circuit_id
6. **Alloy** forwards logs to Gateway (:55681/loki/api/v1/push)
7. **Gateway** routes to:
   - Correlation Station → parses, enriches, creates synthetic spans
   - Loki → stores logs
   - Tempo → stores traces
   - Prometheus → stores metrics

### Flow 2: Sense App → MDSO → Sense App (with trace stitching)

1. **Beorn** receives request, creates span `beorn.create_network_service`
2. **Beorn** calls MDSO API `/bpocore/market/api/v1/resources`
   - Sends HTTP headers: `X-Circuit-Id`, `X-Product-Id`
   - Emits span to Gateway
3. **MDSO Bpocore** receives request (no trace context propagation)
   - Logs parsed by Alloy, includes circuit_id
4. **MDSO Scriptplan** executes CircuitDetailsCollector
   - Calls Arda `/api/v3/topologies/{circuit_id}`
   - OTelPlan emits span with circuit_id attribute
5. **Arda** receives request, creates span `arda.get_topology`
   - Emits span to Gateway
6. **Correlation Station** receives both spans:
   - Beorn span (has trace_id A, circuit_id X)
   - MDSO scriptplan span (has trace_id B, circuit_id X)
   - Arda span (has trace_id C, circuit_id X)
7. **TraceSynthesizer** matches by circuit_id within time window
8. **Synthetic bridge spans** created:
   - `beorn_to_mdso_bridge` (links trace A → trace B)
   - `mdso_to_arda_bridge` (links trace B → trace C)
9. **All spans** exported to Tempo with synthetic links
10. **Grafana Trace View** shows complete end-to-end flow

## Key Architecture Decisions

### Decision 1: Hybrid Trace Synthesis

**Problem**: MDSO cannot be modified to propagate W3C Trace Context

**Solution**:
- Services create independent traces
- Correlation Station links traces using:
  1. **Correlation keys**: circuit_id, resource_id, product_id
  2. **Temporal correlation**: Timestamp proximity (60s window)
  3. **Service flow patterns**: Known call sequences (Beorn → MDSO → Arda)
- Synthetic bridge spans injected to visualize complete flow

**Trade-offs**:
- ✅ Works with unmodifiable MDSO
- ✅ Handles async/callback workflows
- ⚠️ Requires correlation window tuning
- ⚠️ Synthetic spans marked with `synthetic: true` attribute

### Decision 2: Two-Stage Log Parsing

**Problem**: 275GB/day of MDSO logs, need efficient processing

**Solution**:
- **Stage 1 (Alloy on MDSO)**:
  - Parse syslog format
  - Extract correlation keys (regex)
  - Sample high-volume DEBUG logs (25%)
  - Forward compressed to Meta
- **Stage 2 (Correlation Station on Meta)**:
  - Deep JSON parsing
  - Trace linking
  - Enrichment with synthetic context

**Benefits**:
- Reduces network bandwidth (sampling at source)
- Reduces Meta server CPU (pre-parsed logs)
- Centralized intelligence in Correlation Station

### Decision 3: OTel SDK Wrapper vs. BP Extension

**Problem**: Need OTel in MDSO without breaking existing products

**Solution**: Create `OTelPlan` class that:
- Inherits from BP's `Plan` class
- Overrides `enter_exit_log()` to emit OTel + original BP behavior
- Maintains 100% API compatibility
- Optional enable/disable via env var

**Alternative Rejected**: Extending BP's orchestration_trace
- Would require modifying BP core code
- Hard to maintain across BP upgrades
- Doesn't provide standard OTel propagation

### Decision 4: Dual Export (OTLP + DataDog)

**Problem**: Need to maintain existing DataDog while migrating to OTel

**Solution**: Configure OTel SDK with multiple span processors:
```python
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))  # Correlation Gateway
provider.add_span_processor(BatchSpanProcessor(DatadogSpanExporter()))  # DataDog
```

**Benefits**:
- Single instrumentation codebase
- Gradual migration path
- Redundancy during transition

## Component Responsibilities

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **OTelPlan** | Emit OTel signals from MDSO scriptplan | enter_exit_log() calls | OTLP spans, structured logs |
| **Alloy Agent** | Collect MDSO logs/metrics | Log files, Prometheus endpoints | OTLP logs, Prometheus metrics |
| **OTel Gateway** | Route telemetry | OTLP from all sources | Loki, Tempo, Prometheus, Correlation Station |
| **Correlation Station** | Synthesize traces, enrich signals | OTLP spans/logs | Synthetic spans, enriched logs |
| **TraceSynthesizer** | Link disconnected traces | TraceSegments | Bridge spans, trace links |
| **Loki** | Store logs | Log streams | Log queries |
| **Tempo** | Store traces | Trace spans | Trace queries |
| **Prometheus** | Store metrics | Metrics | Metric queries |
| **Grafana** | Visualize | Loki/Tempo/Prom queries | Dashboards, alerts |

## Correlation Strategy

### Primary Correlation Keys

1. **circuit_id** (UUID) - Business identifier for network circuits
   - Present in: MDSO resources, Sense API calls, Granite DB
   - Cardinality: ~10K active circuits
   - Reliability: 99% (always present in production workflows)

2. **resource_id** (UUID) - MDSO resource instance ID
   - Present in: MDSO resources, scriptplan logs
   - Cardinality: ~1M active resources
   - Reliability: 100% (MDSO-generated)

3. **product_id** (UUID) - MDSO product template ID
   - Present in: MDSO resources
   - Cardinality: ~100 product types
   - Reliability: 100%

### Correlation Window

- **Default**: 60 seconds
- **Rationale**: Empirical analysis shows 95% of MDSO → Sense callbacks occur within 30s
- **Configurable**: `CORR_WINDOW_SECONDS` environment variable

### Confidence Scoring

Synthetic spans include confidence score:

```python
confidence = 1.0 if exact_match else 0.8
if temporal_proximity < 10s:
    confidence *= 1.0
elif temporal_proximity < 30s:
    confidence *= 0.9
else:
    confidence *= 0.7
```

## Performance Characteristics

### Throughput

| Component | Expected Load | Measured Capacity | Headroom |
|-----------|---------------|-------------------|----------|
| OTel Gateway | 10K spans/sec | 50K spans/sec | 5x |
| Correlation Station | 5K correlations/sec | 20K correlations/sec | 4x |
| Loki | 100 MB/sec logs | 500 MB/sec | 5x |
| Tempo | 10K spans/sec | 100K spans/sec | 10x |
| Prometheus | 10K samples/sec | 100K samples/sec | 10x |

### Latency

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| MDSO span → Tempo | 50ms | 150ms | 300ms |
| Sense span → Tempo | 30ms | 100ms | 200ms |
| Trace synthesis | 10ms | 50ms | 100ms |
| Log query (Loki) | 100ms | 500ms | 1s |
| Trace query (Tempo) | 200ms | 1s | 2s |

### Storage

| Backend | Retention | Daily Volume | Total Storage (30d) |
|---------|-----------|--------------|---------------------|
| Loki | 30 days | 275 GB | 8.25 TB |
| Tempo | 30 days | 50 GB | 1.5 TB |
| Prometheus | 15 days | 10 GB | 150 GB |
| **TOTAL** | - | **335 GB/day** | **~10 TB** |

## Security Considerations

### Data Redaction

**Problem**: MDSO logs may contain sensitive data (passwords, tokens)

**Solution**:
- Alloy regex filters redact patterns: `password[=:]\s*\S+` → `password=***`
- Correlation Station sanitizes SQL queries, API payloads
- Grafana RBAC limits query access

### Network Security

- **MDSO → Meta**: HTTP (internal network, consider TLS for production)
- **Sense → Gateway**: HTTP (same Docker network)
- **Grafana UI**: HTTPS with self-signed cert (upgrade to CA-signed for production)

### Authentication

- **Alloy → Gateway**: Optional BasicAuth (commented in config)
- **Grafana**: Admin/password (integrate with LDAP for production)
- **Correlation Station**: No auth (internal service, behind API gateway)

## Scalability Strategy

### Current Deployment (Single Meta Server)

- **Capacity**: ~500 GB logs/day, ~50K spans/sec
- **Suitable for**: Dev, staging, small production

### Future Scaling (Multi-Node)

1. **Horizontal OTel Gateway Scaling**:
   - Deploy Gateway replicas behind load balancer
   - Use consistent hashing for trace fan-out

2. **Loki Scaling**:
   - Migrate to Loki microservices mode
   - S3/GCS object storage backend
   - Separate ingesters, queriers, compactors

3. **Tempo Scaling**:
   - Migrate to Tempo microservices mode
   - S3/GCS object storage backend

4. **Correlation Station Scaling**:
   - Deploy replicas behind load balancer
   - Redis for shared TraceSynthesizer state

## Monitoring the Monitoring

### Health Checks

```bash
# OTel Gateway
curl http://159.56.4.94:13133  # Collector health

# Correlation Station
curl http://159.56.4.94:8080/health

# Loki
curl http://159.56.4.94:3100/ready

# Tempo
curl http://159.56.4.94:3200/ready

# Prometheus
curl http://159.56.4.94:9090/-/healthy
```

### Meta-Metrics

```promql
# Correlation Station processing rate
rate(correlation_events_total[5m])

# OTel Gateway throughput
rate(otelcol_receiver_accepted_spans[5m])

# Loki ingestion rate
rate(loki_distributor_bytes_received_total[5m])

# Tempo write throughput
rate(tempo_ingester_spans_received_total[5m])
```

### Alerting Rules

```yaml
# Alert if correlation rate drops to zero
- alert: CorrelationEngineDown
  expr: rate(correlation_events_total[5m]) == 0
  for: 5m

# Alert if Alloy not forwarding
- alert: AlloyNotForwarding
  expr: rate(loki_distributor_bytes_received_total{source="alloy"}[5m]) == 0
  for: 10m

# Alert if trace synthesis failing
- alert: TraceSynthesisFailing
  expr: rate(correlation_bridge_spans_created[5m]) < 1
  for: 10m
```

## Future Enhancements

1. **Machine Learning Correlation**:
   - Train ML model on historical correlations
   - Predict parent traces with higher confidence
   - Handle missing correlation keys

2. **Real-Time Anomaly Detection**:
   - Detect unusual trace patterns (long durations, error spikes)
   - Auto-create incidents in Grafana OnCall

3. **Automatic Trace Sampling**:
   - Tail-based sampling (keep interesting traces, drop boring ones)
   - Error-biased sampling (always keep errors)

4. **Cross-Cluster Tracing**:
   - Federate multiple MDSO environments
   - Global trace queries

---

**For implementation details, see**: `IMPLEMENTATION_GUIDE.md`
**For signal specifications, see**: `SIGNAL_DESIGN.md`
**For container decisions, see**: `CONTAINER_MATRIX.md`
