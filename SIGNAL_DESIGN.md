# Signal Design Matrix - End-to-End Observability

## Overview

This document defines all telemetry signals (spans, logs, metrics, events, baggage) for each communication path in the MDSO ↔ Sense ecosystem.

---

## Communication Path 1: Sense → MDSO (API Calls)

### Example: Beorn calls MDSO to create NetworkService resource

#### Spans

| Span Name | Service | Kind | Attributes | Events |
|-----------|---------|------|------------|--------|
| `beorn.create_network_service` | beorn | CLIENT | `http.method=POST`<br>`http.url=/bpocore/market/api/v1/resources`<br>`circuit_id=<UUID>`<br>`product_id=<UUID>`<br>`resource_type_id=charter.resourceTypes.NetworkService`<br>`mdso.endpoint=bpocore/market`<br>`sense.operation=create_service` | `request.sent` (timestamp)<br>`response.received` (timestamp, status_code) |
| `mdso.api_gateway.receive_request` | api-gw (synthetic) | SERVER | `http.method=POST`<br>`http.target=/bpocore/market/api/v1/resources`<br>`http.status_code=201`<br>`circuit_id=<from payload>`<br>`product_id=<from payload>` | `auth.validated`<br>`request.routed` |
| `mdso.bpocore.create_resource` | bpocore (synthetic) | INTERNAL | `resource_id=<UUID>`<br>`resource_type_id=charter.resourceTypes.NetworkService`<br>`circuit_id=<UUID>`<br>`product_id=<UUID>`<br>`orch_state=requested`<br>`operation=ACTIVATE` | `resource.created`<br>`dependencies.analyzed`<br>`scriptplan.scheduled` |

#### Logs

| Source | Level | Message | Structured Fields |
|--------|-------|---------|------------------|
| beorn | INFO | "Creating network service in MDSO" | `circuit_id`, `product_id`, `resource_type_id`, `mdso_url`, `request_payload` (redacted) |
| beorn | DEBUG | "MDSO API response received" | `circuit_id`, `resource_id`, `status_code`, `response_time_ms` |
| api-gw | INFO | "Incoming resource creation request" | `http.method`, `http.path`, `circuit_id` (extracted), `source_ip`, `user_agent` |
| bpocore | INFO | "Resource created successfully" | `resource_id`, `resource_type_id`, `circuit_id`, `product_id`, `tenant_id`, `orch_state` |

#### Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `sense_mdso_requests_total` | Counter | `service=beorn`, `endpoint=create_resource`, `status=success\|error` | Total Sense → MDSO API calls |
| `sense_mdso_request_duration_seconds` | Histogram | `service=beorn`, `endpoint=create_resource` | Request duration (P50, P95, P99) |
| `mdso_resource_created_total` | Counter | `resource_type_id`, `orch_state` | Resources created by type |

#### Baggage (W3C Trace Context Propagation)

| Key | Value | Propagation Path |
|-----|-------|------------------|
| `circuit_id` | `<UUID>` | Beorn → API-GW → Bpocore → Scriptplan |
| `product_id` | `<UUID>` | Beorn → API-GW → Bpocore → Scriptplan |
| `sense.source` | `beorn` | Beorn → MDSO |
| `sense.operation` | `create_network_service` | Beorn → MDSO |

**Note**: MDSO does NOT currently support W3C Trace Context. Baggage is injected by Correlation Station synthetically.

#### Events

| Event Name | Timestamp | Attributes | Source |
|------------|-----------|------------|--------|
| `sense.api.request_sent` | ISO8601 | `circuit_id`, `product_id`, `endpoint` | Beorn OTel SDK |
| `mdso.resource.created` | ISO8601 | `resource_id`, `resource_type_id`, `circuit_id` | Bpocore logs (parsed) |
| `mdso.scriptplan.scheduled` | ISO8601 | `resource_id`, `scriptplan_container` | Bpocore logs (parsed) |

---

## Communication Path 2: MDSO → Sense (Callbacks/Responses)

### Example: MDSO scriptplan calls Arda to get topology data

#### Spans

| Span Name | Service | Kind | Attributes | Events |
|-----------|---------|------|------------|--------|
| `mdso.scriptplan.call_arda` | scriptplan (synthetic) | CLIENT | `http.method=GET`<br>`http.url=http://arda:5003/api/v3/topologies/{circuit_id}`<br>`circuit_id=<UUID>`<br>`resource_id=<UUID>`<br>`scriptplan.process=CircuitDetailsCollector` | `request.sent`<br>`response.received` |
| `arda.get_topology` | arda | SERVER | `http.method=GET`<br>`http.route=/api/v3/topologies/:circuit_id`<br>`circuit_id=<UUID>`<br>`http.status_code=200`<br>`arda.data_source=granite` | `db.query.executed`<br>`response.serialized` |

#### Logs

| Source | Level | Message | Structured Fields |
|--------|-------|---------|------------------|
| scriptplan | INFO | "Calling Arda for topology data" | `circuit_id`, `resource_id`, `arda_url`, `scriptplan_process` |
| arda | INFO | "Topology data requested" | `circuit_id`, `source_ip` (MDSO), `query_params` |
| arda | DEBUG | "Querying Granite database" | `circuit_id`, `sql_query` (sanitized), `query_time_ms` |
| scriptplan | INFO | "Received topology data from Arda" | `circuit_id`, `resource_id`, `response_size_bytes`, `endpoint_count` |

#### Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `mdso_sense_callbacks_total` | Counter | `target=arda`, `endpoint=get_topology`, `status` | MDSO → Sense callbacks |
| `arda_topology_requests_total` | Counter | `source=mdso`, `circuit_type`, `status` | Topology requests by source |
| `arda_granite_query_duration_seconds` | Histogram | `query_type=topology` | Granite DB query latency |

#### Baggage

**Problem**: MDSO scriptplan does NOT propagate trace context when calling Sense apps.

**Solution**: Correlation Station creates synthetic parent span based on:
- `circuit_id` match between MDSO scriptplan logs and Arda request logs
- Temporal correlation (MDSO request timestamp → Arda request timestamp within window)
- URL pattern matching

#### Events

| Event Name | Timestamp | Attributes | Source |
|------------|-----------|------------|--------|
| `mdso.scriptplan.arda_call_initiated` | ISO8601 | `circuit_id`, `resource_id`, `arda_endpoint` | Scriptplan logs |
| `arda.request.received` | ISO8601 | `circuit_id`, `http.path`, `source_ip` | Arda OTel SDK |
| `arda.granite.query_executed` | ISO8601 | `circuit_id`, `query_type`, `row_count` | Arda OTel SDK |

---

## Communication Path 3: Sense → Sense (Inter-Service)

### Example: Beorn calls Palantir to validate service eligibility

#### Spans

| Span Name | Service | Kind | Attributes | Events |
|-----------|---------|------|------------|--------|
| `beorn.check_eligibility` | beorn | CLIENT | `http.method=POST`<br>`http.url=http://palantir:5002/api/v1/eligibility/check`<br>`circuit_id=<UUID>`<br>`service_type=FIA`<br>`palantir.check_type=device_availability` | `request.sent`<br>`response.received` |
| `palantir.validate_eligibility` | palantir | SERVER | `http.method=POST`<br>`http.route=/api/v1/eligibility/check`<br>`circuit_id=<UUID>`<br>`service_type=FIA`<br>`eligibility.result=eligible\|not_eligible`<br>`eligibility.reason=<reason>` | `db.query.executed`<br>`validation.completed` |

#### Logs

| Source | Level | Message | Structured Fields |
|--------|-------|---------|------------------|
| beorn | INFO | "Checking service eligibility with Palantir" | `circuit_id`, `service_type`, `palantir_url` |
| palantir | INFO | "Eligibility check requested" | `circuit_id`, `service_type`, `source=beorn` |
| palantir | INFO | "Eligibility check result" | `circuit_id`, `service_type`, `result`, `reason`, `devices_checked` |

#### Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `sense_inter_service_calls_total` | Counter | `source=beorn`, `target=palantir`, `operation=check_eligibility` | Inter-service calls |
| `palantir_eligibility_checks_total` | Counter | `service_type`, `result=eligible\|not_eligible` | Eligibility check results |

#### Baggage

| Key | Value | Propagation Path |
|-----|-------|------------------|
| `circuit_id` | `<UUID>` | Beorn → Palantir |
| `trace.parent.service` | `beorn` | Beorn → Palantir |
| `trace.parent.operation` | `create_network_service` | Beorn → Palantir |

**Trace Context**: ✅ Fully propagated using W3C `traceparent` header

---

## Communication Path 4: MDSO Internal Workflow Execution

### Example: Scriptplan orchestrates CircuitDetailsCollector → ServiceProvisioner → DeviceOnboarder

#### Spans

| Span Name | Service | Kind | Attributes | Events |
|-----------|---------|------|------------|--------|
| `mdso.workflow.network_service_activation` | scriptplan | INTERNAL | `resource_id=<UUID>`<br>`circuit_id=<UUID>`<br>`product_id=<UUID>`<br>`resource_type_id=charter.resourceTypes.NetworkService`<br>`operation=ACTIVATE`<br>`trace_id=<from MDSO params>` | `workflow.started`<br>`workflow.completed` |
| `mdso.product.circuit_details_collector` | scriptplan | INTERNAL | `resource_id=<child UUID>`<br>`parent_resource_id=<parent UUID>`<br>`circuit_id=<UUID>`<br>`resource_type_id=charter.resourceTypes.CircuitDetailsCollector`<br>`process=CircuitDetailsCollectorPlan` | `started_processing`<br>`arda.topology_fetched`<br>`circuit_details.validated`<br>`completed_processing` |
| `mdso.product.service_provisioner` | scriptplan | INTERNAL | `resource_id=<UUID>`<br>`circuit_id=<UUID>`<br>`resource_type_id=charter.resourceTypes.ServiceProvisioner`<br>`device_vendor=JUNIPER\|CISCO\|ADVA\|RAD`<br>`process=ServiceProvisionerPlan` | `started_processing`<br>`device.config_generated`<br>`ra.command_sent`<br>`device.config_applied`<br>`completed_processing` |

#### Logs

| Source | Level | Message | Structured Fields |
|--------|-------|---------|------------------|
| scriptplan | INFO | "STARTED PROCESSING" | `trace_id`, `resource_id`, `resource_type_id`, `circuit_id`, `product_id`, `operation`, `process`, `timestamp`, `elapsed_time=0` |
| scriptplan | INFO | "Calling Arda for topology" | `trace_id`, `resource_id`, `circuit_id`, `arda_endpoint` |
| scriptplan | INFO | "COMPLETED PROCESSING" | `trace_id`, `resource_id`, `resource_type_id`, `circuit_id`, `state=COMPLETED`, `elapsed_time=<seconds>` |
| scriptplan | ERROR | "FAILED PROCESSING" | `trace_id`, `resource_id`, `circuit_id`, `state=FAILED`, `categorized_error`, `error_message`, `elapsed_time` |

#### Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `mdso_scriptplan_executions_total` | Counter | `resource_type_id`, `operation`, `state=completed\|failed` | Scriptplan executions |
| `mdso_scriptplan_duration_seconds` | Histogram | `resource_type_id`, `operation` | Execution duration by product type |
| `mdso_product_failures_total` | Counter | `resource_type_id`, `error_category` | Product failures by category |

#### Events (from enter_exit_log)

| Event Name | Timestamp | Attributes | Source |
|------------|-----------|------------|--------|
| `mdso.process.started` | `trace_details.timestamp` | `resource_id`, `resource_type_id`, `process`, `log_file`, `state=STARTED` | enter_exit_log() |
| `mdso.process.completed` | `trace_details.timestamp` | `resource_id`, `process`, `state=COMPLETED`, `elapsed_time` | enter_exit_log() |
| `mdso.process.failed` | `trace_details.timestamp` | `resource_id`, `process`, `state=FAILED`, `categorized_error`, `elapsed_time` | enter_exit_log() |

---

## Communication Path 5: Sense → Non-MDSO Services

### Example: Arda queries Granite database for circuit topology

#### Spans

| Span Name | Service | Kind | Attributes | Events |
|-----------|---------|------|------------|--------|
| `arda.query_granite` | arda | CLIENT | `db.system=postgresql`<br>`db.name=granite`<br>`db.operation=SELECT`<br>`circuit_id=<UUID>`<br>`db.table=topology_endpoints`<br>`db.statement=<sanitized SQL>` | `query.started`<br>`query.completed` |

#### Logs

| Source | Level | Message | Structured Fields |
|--------|-------|---------|------------------|
| arda | DEBUG | "Executing Granite query" | `circuit_id`, `query_type=topology`, `sql_query` (sanitized) |
| arda | INFO | "Granite query results" | `circuit_id`, `row_count`, `query_time_ms`, `endpoint_count` |

#### Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `arda_db_queries_total` | Counter | `db=granite`, `operation=SELECT\|INSERT`, `table`, `status` | Database queries |
| `arda_db_query_duration_seconds` | Histogram | `db=granite`, `operation` | Query latency |

---

## Correlation Station Synthetic Span Injection

### Scenario 1: Bridging Sense → MDSO → Sense Callback

**Problem**: MDSO doesn't propagate trace context when calling back to Sense apps.

**Solution**: Correlation Station creates synthetic "bridge" span:

```json
{
  "name": "mdso.callback_bridge",
  "kind": "INTERNAL",
  "trace_id": "<inherited from Sense → MDSO span>",
  "parent_span_id": "<mdso.bpocore.create_resource span_id>",
  "span_id": "<generated>",
  "start_time": "<mdso scriptplan log timestamp>",
  "end_time": "<arda request received timestamp>",
  "attributes": {
    "bridge.type": "mdso_to_sense_callback",
    "circuit_id": "<matched from logs>",
    "resource_id": "<from MDSO logs>",
    "callback.target": "arda",
    "callback.endpoint": "/api/v3/topologies/{circuit_id}",
    "synthetic": true
  },
  "events": [
    {"name": "correlation.matched", "timestamp": "<ISO8601>", "attributes": {"match_key": "circuit_id", "confidence": 0.95}}
  ]
}
```

### Scenario 2: Async Resource Provisioning

**Problem**: MDSO scriptplan creates child resources asynchronously; no direct parent-child span relationship.

**Solution**: Correlation Station creates synthetic parent span for the entire workflow:

```json
{
  "name": "mdso.workflow.network_service_activation",
  "kind": "INTERNAL",
  "trace_id": "<from MDSO trace_id>",
  "span_id": "<generated>",
  "start_time": "<workflow start from orchestration_trace>",
  "end_time": "<workflow end from orchestration_trace>",
  "attributes": {
    "resource_id": "<network_service resource_id>",
    "circuit_id": "<UUID>",
    "product_id": "<UUID>",
    "operation": "ACTIVATE",
    "workflow.total_steps": 12,
    "workflow.failed_steps": 0,
    "synthetic": true
  },
  "links": [
    {"trace_id": "<UUID>", "span_id": "<circuit_details_collector span>"},
    {"trace_id": "<UUID>", "span_id": "<service_provisioner span>"},
    {"trace_id": "<UUID>", "span_id": "<device_onboarder span>"}
  ]
}
```

---

## Standard Attribute Conventions

### Required Attributes (ALL spans)

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `service.name` | string | `beorn` | Service emitting the span |
| `service.version` | string | `2408.0.244` | Service version |
| `deployment.environment` | string | `dev` | Environment (dev/staging/prod) |

### Resource Attributes (MDSO-related spans)

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `resource_id` | string (UUID) | `550e8400-e29b-41d4-a716-446655440000` | MDSO resource UUID |
| `product_id` | string (UUID) | `7c9e6679-7425-40de-944b-e07fc1f90ae7` | MDSO product UUID |
| `circuit_id` | string (UUID) | `123e4567-e89b-12d3-a456-426614174000` | Circuit identifier |
| `resource_type_id` | string | `charter.resourceTypes.NetworkService` | Resource type |
| `resourceType` | string | `NetworkService` | Short resource type |

### HTTP Attributes (API spans)

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `http.method` | string | `POST` | HTTP method |
| `http.url` | string | `http://mdso:8181/bpocore/market/api/v1/resources` | Full URL |
| `http.target` | string | `/bpocore/market/api/v1/resources` | URL path |
| `http.status_code` | int | `201` | Response status code |
| `http.user_agent` | string | `python-requests/2.31.0` | User agent |

### MDSO-Specific Attributes

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `mdso.operation` | string | `ACTIVATE` | Operation type (ACTIVATE/UPDATE/TERMINATE) |
| `mdso.orch_state` | string | `active` | Orchestration state |
| `mdso.trace_id` | string | `trace-12345` | MDSO internal trace_id (from params) |
| `mdso.tenant_id` | string (UUID) | `07e4d137-7b97-4208-8a02-ccdf6d272258` | Tenant ID |
| `mdso.scriptplan.process` | string | `CircuitDetailsCollectorPlan` | Scriptplan process class name |

### Error Attributes

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `error` | boolean | `true` | Whether span encountered error |
| `error.type` | string | `CONNECTIVITY_ERROR` | Error category |
| `error.message` | string | `Connection to device failed` | Error message |
| `error.stack` | string | `Traceback...` | Stack trace (redacted) |
| `categorized_error` | string | `MDSO \| NETWORK \| Connectivity Error` | BP error format |

---

## Baggage Propagation Strategy

### Sense → MDSO
- **Method**: HTTP headers (X-Circuit-Id, X-Product-Id, X-Resource-Id)
- **Fallback**: Extract from JSON payload in Correlation Station

### MDSO → Sense
- **Method**: NOT SUPPORTED (MDSO limitation)
- **Workaround**: Correlation Station matches by circuit_id + temporal correlation

### Sense → Sense
- **Method**: W3C Trace Context (`traceparent`, `tracestate`)
- **Baggage**: circuit_id, product_id, resource_id

---

## Metric Label Cardinality Control

### High Cardinality (AVOID as labels)
- ❌ `resource_id` (UUID - millions of values)
- ❌ `product_id` (UUID - millions of values)
- ❌ `circuit_id` (UUID - millions of values)
- ❌ `trace_id` (UUID - billions of values)
- ❌ `user_id` (thousands of values)

### Low Cardinality (SAFE as labels)
- ✅ `service` (beorn, arda, palantir, mdso)
- ✅ `resource_type_id` (~50 types)
- ✅ `operation` (ACTIVATE, UPDATE, TERMINATE)
- ✅ `status` (success, error)
- ✅ `http.method` (GET, POST, PATCH, DELETE)
- ✅ `environment` (dev, staging, prod)

**Rule**: Keep total label cardinality < 10,000 unique combinations

---

## Log Sampling Strategy

| Log Level | Sampling Rate | Reason |
|-----------|---------------|--------|
| ERROR | 100% | Always capture errors |
| WARN | 100% | Always capture warnings |
| INFO (Sense apps) | 100% | Low volume |
| INFO (MDSO scriptplan) | 50% (sample by trace_id hash) | High volume |
| INFO (MDSO RA containers) | 25% (sample by trace_id hash) | Very high volume |
| DEBUG | 10% (sample by trace_id hash) | Extremely high volume |

**Sampling Algorithm**: Consistent hashing on `trace_id` to preserve trace completeness

```python
import hashlib

def should_sample(trace_id: str, sample_rate: float) -> bool:
    """Deterministic sampling based on trace_id hash"""
    hash_val = int(hashlib.md5(trace_id.encode()).hexdigest(), 16)
    return (hash_val % 100) < (sample_rate * 100)
```

---

## Next Steps

1. Implement OTel SDK instrumentation in Sense apps (see `IMPLEMENTATION_GUIDE.md`)
2. Deploy `otel_instrumentation` product to MDSO (see `mdso-instrumentation/` directory)
3. Configure Alloy agent on MDSO server (see `alloy/mdso-config.alloy`)
4. Deploy enhanced Correlation Station (see `seefa-om/correlation-engine/`)
5. Validate signal flow in Grafana dashboards
