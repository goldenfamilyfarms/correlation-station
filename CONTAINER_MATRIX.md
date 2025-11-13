# MDSO Container Instrumentation Matrix

## Priority 1: Critical Path Containers

| Container | Signals to Collect | Collection Method | Rationale | Log Path | Metrics Port |
|-----------|-------------------|-------------------|-----------|----------|--------------|
| **scriptplan** | Logs, Metrics | Alloy file tail + metrics scrape | Executes all automation workflows; contains orchestration trace | `/opt/ciena/bp2/scriptplan/logs/*.log` | N/A |
| **bpocore** | Logs, Metrics | Alloy file tail + Prometheus scrape | Core orchestration engine; resource lifecycle | `/opt/ciena/bp2/bpocore/logs/*.log` | 8181 |
| **bpopg** | Metrics only | Postgres exporter | Database health/performance critical for queries | N/A | 5432 |
| **bpo-ui** | Logs (errors only) | Alloy file tail | User-facing errors indicate UX issues | `/opt/ciena/bp2/bpo-ui/logs/error.log` | N/A |
| **api-gw** | Logs, Metrics | Alloy file tail + metrics | API gateway for all Sense → MDSO calls | `/opt/ciena/bp2/api-gw/logs/*.log` | TBD |

## Priority 2: Resource Adapters (RA Containers)

| Container | Signals to Collect | Collection Method | Rationale | Log Path |
|-----------|-------------------|-------------------|-----------|----------|
| **bpracisco** | Logs | Alloy file tail | Cisco device automation; high volume | `/opt/ciena/bp2/bpracisco/logs/*.log` |
| **bprajuniper** | Logs | Alloy file tail | Juniper device automation | `/opt/ciena/bp2/bprajuniper/logs/*.log` |
| **bpraadva** | Logs | Alloy file tail | ADVA device automation | `/opt/ciena/bp2/bpraadva/logs/*.log` |
| **bprarad** | Logs | Alloy file tail | RAD device automation | `/opt/ciena/bp2/bprarad/logs/*.log` |

## Priority 3: Supporting Services

| Container | Signals to Collect | Collection Method | Rationale | Log Path |
|-----------|-------------------|-------------------|-----------|----------|
| **tron** | Logs | Alloy file tail | Authentication/authorization | `/opt/ciena/bp2/tron/logs/*.log` |
| **kafka** | Metrics | Prometheus JMX exporter | Message bus health | N/A |
| **prometheus** | Metrics | Federation scrape | MDSO internal metrics | N/A |
| **camunda** | Logs | Alloy file tail | Workflow engine state | `/opt/ciena/bp2/camunda/logs/*.log` |

## Priority 4: Monitoring Only

| Container | Signals to Collect | Collection Method | Rationale |
|-----------|-------------------|-------------------|-----------|
| **asset-manager** | Metrics (health) | Health check endpoint | Inventory management |
| **pathfinder** | Logs (errors) | Alloy file tail | Network path calculation |
| **pce** | Logs (errors) | Alloy file tail | Path computation engine |
| **vault** | Metrics (health) | Health check endpoint | Secrets management |

## Excluded Containers (Out of Scope)

| Container | Reason for Exclusion |
|-----------|---------------------|
| **elasticsearch**, **kibana**, **gvselasticsearch** | MDSO internal observability; conflicts with our stack |
| **fluentbit** | MDSO log shipper; replaced by Alloy |
| **graphite** | MDSO metrics; we use Prometheus |
| **nagios**, **collectd**, **nrpe** | MDSO legacy monitoring |
| **postgres** (data) | Too verbose; use metrics only via bpopg |
| **seaweedfs**, **glusterfs** | Storage; not relevant to workflows |
| **swagger-ui**, **open-api** | Documentation UIs |
| **landing-page-ui**, **bp-platform-ui** | Static UIs |

## Signal Volume Estimates

| Priority Level | Containers | Est. Log Volume/Day | Est. Metrics/Min |
|----------------|------------|---------------------|------------------|
| Priority 1 | 5 | ~50 GB | ~10K time series |
| Priority 2 | 4 | ~200 GB | ~2K time series |
| Priority 3 | 4 | ~20 GB | ~5K time series |
| Priority 4 | 4 | ~5 GB | ~500 time series |
| **TOTAL** | **17** | **~275 GB** | **~17.5K time series** |

## Correlation Key Availability

| Container | resource_id | product_id | circuit_id | resourceTypeId | trace_id | Notes |
|-----------|-------------|------------|------------|----------------|----------|-------|
| scriptplan | ✅ | ✅ | ✅ | ✅ | ✅ | All keys available in orchestration_trace |
| bpocore | ✅ | ✅ | ✅ | ✅ | ✅ | Resource lifecycle events |
| api-gw | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | Need to extract from request payloads |
| RA containers | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | Context depends on scriptplan injection |
| tron | ❌ | ❌ | ❌ | ❌ | ❌ | Authentication only; no business context |

Legend:
- ✅ = Always present in logs
- ⚠️ = Sometimes present (depends on request type)
- ❌ = Not present

## Alloy Collection Strategy

### File Tail Patterns
```alloy
// Priority 1: High-value, structured logs
loki.source.file "scriptplan" {
  targets = [
    {__path__ = "/opt/ciena/bp2/scriptplan/logs/*.log"},
  ]
  forward_to = [loki.process.parse_syslog.receiver]
}

// Priority 2: RA containers (high volume)
loki.source.file "ra_containers" {
  targets = [
    {__path__ = "/opt/ciena/bp2/bpra*/logs/*.log", container = "bpra"},
  ]
  forward_to = [loki.process.parse_syslog.receiver]
}

// Priority 3: Supporting services
loki.source.file "supporting" {
  targets = [
    {__path__ = "/opt/ciena/bp2/{tron,camunda}/logs/*.log"},
  ]
  forward_to = [loki.process.parse_syslog.receiver]
}
```

### Parsing Strategy
1. **Stage 1 (Alloy)**: Extract syslog fields (timestamp, severity, process)
2. **Stage 2 (Alloy)**: Regex extract correlation keys (resource_id, circuit_id, product_id)
3. **Stage 3 (Correlation Station)**: Deep JSON parsing, trace linking

## Retention & Sampling

| Priority | Retention | Sampling Rate | Reason |
|----------|-----------|---------------|--------|
| Priority 1 | 30 days | 100% | Critical path; full fidelity |
| Priority 2 | 14 days | 100% (ERROR), 50% (INFO) | High volume; errors always kept |
| Priority 3 | 7 days | 100% (ERROR), 25% (INFO) | Supporting; sample INFO |
| Priority 4 | 3 days | 100% (ERROR), 10% (INFO) | Monitoring; minimal INFO |

## Next Steps
1. Deploy Alloy agent to MDSO server (159.56.4.37 → 47.43.111.107)
2. Configure file tail for Priority 1 containers
3. Validate log parsing in Correlation Station
4. Gradually add Priority 2-4 containers
5. Monitor storage/performance; adjust sampling
