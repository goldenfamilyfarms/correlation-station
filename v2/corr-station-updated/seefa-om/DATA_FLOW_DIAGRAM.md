# Correlation Station - Data Flow Diagram

## High-Level System Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                         │
│                                                                             │
│  MDSO (Multi-Domain Service Orchestrator) Dev (159.56.4.37)           Sense Apps (Meta Server)                 │
│  ├─ /var/log/ciena/blueplanet.log │ ├─ Beorn (port 5001)                │
│  └─ /bp2/log/*.log                │ ├─ Palantir (port 5002)             │
│                                    │ └─ Arda (port 5003)                 │
└────────────┬──────────────────────┬────────────────────────────────────────┘
             │                      │
             │ Syslog files         │ Native OTLP instrumentation
             ▼                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                     DATA COLLECTION & NORMALIZATION                        │
│                                                                            │
│  MDSO: Grafana Alloy                Sense Apps: OTel SDKs                │
│  ┌──────────────────────┐          ┌────────────────────┐               │
│  │ 1. local.file_match  │          │ 1. OTel initialization             │
│  │    Discovers logs    │          │    - Batch processor               │
│  │                      │          │    - OTLP exporter                │
│  │ 2. loki.source.file  │          │                     │               │
│  │    Tails files       │          │ 2. Auto-instrumentation           │
│  │                      │          │    - Flask/FastAPI hooks          │
│  │ 3. loki.process      │          │    - HTTP client tracing          │
│  │    Parses syslog:    │          │    - Request ID generation        │
│  │    - Regex extract   │          │                     │               │
│  │    - Add labels      │          │ 3. Custom attributes injection    │
│  │      {service=mdso,  │          │    - circuit_id from request      │
│  │       env=dev}       │          │    - resource_id from response    │
│  │                      │          │    - Baggage propagation         │
│  │ 4. Convert to OTLP   │          │                     │               │
│  │    Format JSON       │          │                     │               │
│  └──────────────────────┘          └────────────────────┘               │
└────────────┬───────────────────────────────────────┬─────────────────────┘
             │                                       │
             │ HTTP POST (OTLP)                      │ HTTP/gRPC (OTLP)
             │ Endpoint:55681                        │ Endpoint: 4318
             ▼                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    OTel Collector Gateway (Port 4318)                      │
│                    ┌──────────────────────────────┐                       │
│                    │ OTLP Receivers               │                       │
│                    │  - gRPC:4317 (logs/traces)   │                       │
│                    │  - HTTP:4318 (logs/traces)   │                       │
│                    │  - Filelog (optional)        │                       │
│                    └────────────┬─────────────────┘                       │
│                                 │                                         │
│                    ┌────────────▼──────────────┐                         │
│                    │ Processors                 │                         │
│                    │ - Memory limiter            │                         │
│                    │ - Resource attributes      │                         │
│                    │ - Batch (1024 records)     │                         │
│                    └────────────┬──────────────┘                         │
│                                 │                                         │
│          ┌──────────────────────┼──────────────────────┐                 │
│          ▼                      ▼                      ▼                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐       │
│  │ Correlation      │  │ Tempo Exporter   │  │ Loki Exporter  │       │
│  │ Engine Exporter  │  │ (traces/spans)   │  │ (logs only)    │       │
│  │ (:8080/api/otlp) │  │ (:4317 gRPC)     │  │ (:3100 push)   │       │
│  └──────────────────┘  └──────────────────┘  └────────────────┘       │
└────────────┬───────────────────┬────────────────────┬────────────────────┘
             │                   │                    │
             │ OTLP              │ OTLP gRPC          │ Loki push API
             ▼                   ▼                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    CORRELATION ENGINE (Port 8080)                          │
│                                                                            │
│  POST /api/otlp/v1/logs          POST /api/otlp/v1/traces               │
│           │                               │                              │
│           ▼                               ▼                              │
│  ┌──────────────────────┐      ┌──────────────────────┐                │
│  │ LogNormalizer        │      │ TraceNormalizer      │                │
│  │ ├─ Parse OTLP format │      │ ├─ Extract spans     │                │
│  │ ├─ Extract service   │      │ ├─ Extract trace_id  │                │
│  │ ├─ Find trace_id     │      │ └─ Map attributes    │                │
│  │ ├─ Regex patterns    │      └──────────────────────┘                │
│  │ │  (circuit_id, etc) │             │                                 │
│  │ └─ Create LogRecord  │             │                                 │
│  └──────────┬───────────┘             │                                 │
│             │                         │                                 │
│             └──────────────┬──────────┘                                 │
│                            ▼                                            │
│             ┌────────────────────────────┐                             │
│             │  CorrelationWindow         │                             │
│             │  (60-second sliding window)│                             │
│             │                            │                             │
│             │  Group by trace_id:        │                             │
│             │  - logs[] = [l1, l2, l3]   │                             │
│             │  - traces[] = [s1, s2]     │                             │
│             │  - services[] = [mdso, beorn]                            │
│             │  - duration = 45.5s        │                             │
│             └────────────┬───────────────┘                             │
│                          │                                             │
│          ┌───────────────┴────────────────┐                           │
│          ▼                                ▼                           │
│  ┌──────────────────┐          ┌──────────────────┐                 │
│  │TraceSynthesizer  │          │ MDSOCorrelator   │                 │
│  │(if no trace_id)  │          │ (if no trace_id) │                 │
│  │                  │          │                  │                 │
│  │Scoring:          │          │Correlate by:     │                 │
│  │- circuit_id: +100│          │- circuit_id      │                 │
│  │- resource_id:+80 │          │- resource_id     │                 │
│  │- product_id: +60 │          │                  │                 │
│  │- temporal: +40   │          │Enrich with:      │                 │
│  │- pattern: +50    │          │- device_tid      │                 │
│  │                  │          │- orch_state      │                 │
│  │Creates synthetic │          │- service_type    │                 │
│  │bridge span if:   │          │- vendor type     │                 │
│  │confidence > 0.5  │          │- management_ip   │                 │
│  └──────────────────┘          └──────────────────┘                 │
│          │                                │                          │
│          └────────────────┬────────────────┘                         │
│                           ▼                                          │
│             ┌────────────────────────────┐                          │
│             │ Create CorrelationEvent    │                          │
│             │                            │                          │
│             │ {                          │                          │
│             │  trace_id: "abc123...",    │                          │
│             │  service: "mdso",          │                          │
│             │  log_count: 3,             │                          │
│             │  span_count: 2,            │                          │
│             │  circuit_id: "80.L1XX...", │                          │
│             │  mdso_context: {...},      │                          │
│             │  severity_counts: {INFO:2} │                          │
│             │ }                          │                          │
│             └────────────┬───────────────┘                          │
│                          │                                          │
│          ┌───────────────┴────────────────┐                        │
│          ▼                                ▼                        │
└──────────────────┬──────────────────────────────┬────────────────────┘
                   │                              │
         ┌─────────▼──────────┐      ┌───────────▼──────────┐
         │ ExporterManager    │      │ ExporterManager      │
         │                    │      │                      │
         │ - Loki exporter    │      │ - Tempo exporter     │
         │ - Prometheus       │      │ - Datadog (optional) │
         │ - Circuit breaker  │      │ - Circuit breaker    │
         │ - Retry w/ backoff │      │ - Retry w/ backoff   │
         └─────────┬──────────┘      └───────────┬──────────┘
                   │                             │
                   │ HTTP POST                   │ OTLP gRPC
                   │ /loki/api/v1/push          │ :4317
                   ▼                             ▼
        ┌──────────────────┐        ┌──────────────────────┐
        │  LOKI :3100      │        │  TEMPO :3200         │
        │                  │        │                      │
        │ Stores logs:     │        │ Stores traces:       │
        │ {service,env,    │        │ ResourceSpans +      │
        │  trace_id} +     │        │ attributes +         │
        │ JSON log body    │        │ synthetic spans      │
        │                  │        │                      │
        │ Retention: 7d    │        │ Retention: 7d        │
        └──────────────────┘        └──────────────────────┘
                   │                             │
                   │                             │
                   └─────────────┬───────────────┘
                                 │
                    ┌────────────▼──────────┐
                    │  GRAFANA :8443        │
                    │                       │
                    │  - Log queries        │
                    │  - Trace inspection   │
                    │  - Correlation view   │
                    │  - Custom dashboards  │
                    └───────────────────────┘
```

## Data Format Transformation Journey

```
MDSO Raw Log
├─ Input: "Nov 13 10:30:00 mdso-host CIENA[1234]: ServiceMapper: Creating 
│           circuit 80.L1XX.005054..CHTR with resource uuid-xyz"
│
├─ Step 1: Alloy Parsing
│  └─ Output: {
│      timestamp: "Nov 13 10:30:00",
│      hostname: "mdso-host",
│      message: "CIENA[1234]: ServiceMapper: Creating circuit 80.L1XX.005054..CHTR 
│               with resource uuid-xyz",
│      service: "mdso",
│      env: "dev"
│     }
│
├─ Step 2: Convert to OTLP JSON
│  └─ Output: {
│      resourceLogs: [{
│        resource: {
│          attributes: [
│            {key: "service.name", value: {stringValue: "mdso"}},
│            {key: "deployment.environment", value: {stringValue: "dev"}}
│          ]
│        },
│        scopeLogs: [{
│          logRecords: [{
│            timeUnixNano: "1700000000000000000",
│            severityNumber: 9,
│            body: {stringValue: "CIENA[1234]: ServiceMapper: Creating..."},
│            attributes: []
│          }]
│        }]
│      }]
│     }
│
├─ Step 3: Correlation Engine Normalization
│  └─ Output: {
│      timestamp: "2025-11-13T10:30:00Z",
│      severity: "INFO",
│      message: "CIENA[1234]: ServiceMapper: Creating...",
│      service: "mdso",
│      host: "mdso-host",
│      env: "dev",
│      trace_id: null,  # Would be extracted if present
│      circuit_id: null,  # Would be extracted via regex if implemented
│      labels: {}
│     }
│
├─ Step 4: Trace Synthesis (if trace_id missing)
│  └─ IF circuit_id matches Sense app trace context:
│      - Find matching Sense app spans with same circuit_id
│      - Score confidence (circuit_id match = +100)
│      - Create synthetic bridge span linking MDSO → Sense app
│
├─ Step 5: MDSO Enrichment
│  └─ Output: {
│      correlation_id: "corr-abc123",
│      trace_id: "generated-or-matched",
│      log_count: 1,
│      span_count: 0,
│      circuit_id: "80.L1XX.005054..CHTR",  # NOW EXTRACTED
│      resource_id: "uuid-xyz",             # NOW EXTRACTED
│      mdso_context: {
│        circuit_id: "80.L1XX.005054..CHTR",
│        product_type: "service_mapper",
│        device_tid: "extracted-from-fqdn"
│      }
│     }
│
└─ Step 6: Export to Loki & Tempo
   ├─ Loki receives:
   │  {
   │    labels: {service="mdso", env="dev", trace_id="generated-or-matched"},
   │    timestamp: "2025-11-13T10:30:00Z",
   │    content: JSON string with all attributes
   │  }
   │
   └─ Tempo receives:
      {
        resourceSpans: [{
          scopeSpans: [{
            spans: [
              {
                traceId: "generated-or-matched",
                spanId: "synthetic-bridge-span-id",
                name: "mdso.service_creation",
                kind: "INTERNAL",
                attributes: {
                  "mdso.circuit_id": "80.L1XX.005054..CHTR",
                  "mdso.resource_id": "uuid-xyz",
                  "mdso.product_type": "service_mapper"
                }
              }
            ]
          }]
        }]
      }
```

## Key Data Extraction Points

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   WHERE DATA IS EXTRACTED                              │
│                                                                        │
│  MDSO Raw Message Content:                                            │
│  "ServiceMapper: Creating circuit 80.L1XX.005054..CHTR with          │
│   resource 550e8400-e29b-41d4-a716-446655440000 on device            │
│   JFVLINBJ2CW.CHTRSE.COM (vendor: juniper)"                         │
│                                                                        │
│  Currently Extracted:                                                 │
│  ✅ Timestamp (syslog header)                                        │
│  ✅ Hostname (syslog header)                                         │
│  ✅ Service label = "mdso"                                           │
│  ✅ Environment = "dev"                                              │
│                                                                        │
│  NOT Currently Extracted (Opportunities):                            │
│  ❌ circuit_id = "80.L1XX.005054..CHTR"                             │
│  ❌ resource_id = "550e8400-e29b-41d4-a716-446655440000"            │
│  ❌ device_fqdn = "JFVLINBJ2CW.CHTRSE.COM"                          │
│  ❌ vendor = "juniper"                                               │
│  ❌ device_tid = "JFVLINBJ2CW"                                       │
│  ❌ product_type = "service_mapper"                                   │
│  ❌ error_patterns = any error codes                                 │
│                                                                        │
│  WHERE TO EXTRACT:                                                    │
│  Option A: Alloy loki.process stage (early, efficient)             │
│  Option B: Correlation Engine normalizer (flexible, late)           │
│  Option C: Both (redundancy, guaranteed extraction)                 │
│                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Summary Matrix

```
┌────────────┬──────────────────┬─────────────────────┬────────────────┐
│ Stage      │ Input Format     │ Processing          │ Output Format  │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ MDSO Log   │ Syslog text      │ None (raw)          │ Syslog text    │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ Alloy      │ Syslog text      │ Regex + normalize   │ OTLP JSON      │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ Gateway    │ OTLP JSON/Proto  │ Batch + route       │ OTLP JSON/gRPC │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ Corr Eng   │ OTLP format      │ Parse + extract +   │ CorrelationEven│
│            │                  │ synthesize          │ t JSON         │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ Loki       │ Loki push API    │ Store + compress    │ Log query      │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ Tempo      │ OTLP gRPC        │ Store + index       │ Trace query    │
├────────────┼──────────────────┼─────────────────────┼────────────────┤
│ Grafana    │ PromQL/LogQL     │ Query + render      │ Dashboard view │
└────────────┴──────────────────┴─────────────────────┴────────────────┘
```

