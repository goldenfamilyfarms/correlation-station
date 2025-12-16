# OpenTelemetry Instrumentation Analysis for Sense Apps

## Overview
This document identifies which APIs and their Business Logic Layer (BLL) / Data Logic Layer (DLL) components need OpenTelemetry instrumentation for comprehensive observability.

## Instrumentation Priority Levels
- **P0 (Critical)**: Core provisioning/design operations, external system calls, error-prone paths
- **P1 (High)**: Important business operations, data transformations, validation logic
- **P2 (Medium)**: Supporting operations, utility functions, read-only operations

---

## BEORN Application (Flask)

### Critical APIs Requiring Instrumentation (P0)

#### 1. **v3/service** (`apis/v3/service.py`)
**Why**: Core provisioning service - creates/updates services, calls MDSO
- **API Methods**: `GET`, `POST`, `PUT`
- **BLL**: `beorn_app/bll/service.py`
  - `create_core_service()` - Creates service in MDSO
  - `get_service_info()` - Retrieves service status
  - `update_service()` - Updates service resources
  - `_service_update()` - Internal update logic
- **DLL**: `beorn_app/dll/mdso.py`
  - `create_service()` - MDSO API calls
  - `mdso_get()`, `mdso_post()` - HTTP calls to MDSO
  - `service_details()`, `service_id_lookup()` - Service queries
- **Instrumentation Needs**:
  - Trace service creation/update operations
  - Track MDSO API call latency and errors
  - Capture circuit_id, product_id, resource_id for correlation
  - Monitor service state transitions

#### 2. **v3/topologies** (`apis/v3/topologies.py`)
**Why**: Complex topology generation with multiple external calls
- **API Methods**: `GET`
- **BLL**: `beorn_app/bll/topologies.py`
  - `Topologies.create_topology()` - Main topology creation
  - `_create_topology()`, `_create_multi_leg_topology()` - Topology builders
  - `_validate_required_circuit_data()` - Validation logic
- **DLL**: 
  - `beorn_app/common/granite_operations.py` - `call_denodo_for_circuit_devices()`
  - `beorn_app/bll/granite.py` - Granite data retrieval
- **Instrumentation Needs**:
  - Trace topology generation flow
  - Track Denodo/Granite query performance
  - Capture topology validation errors
  - Add topology-specific attributes (node_count, service_type, vendor)

#### 3. **v3/cpe** (`apis/v3/cpe.py`)
**Why**: CPE management operations
- **API Methods**: `GET`, `PUT`
- **BLL**: `beorn_app/bll/cpe.py`
- **DLL**: `beorn_app/dll/mdso.py`, `beorn_app/dll/granite.py`
- **Instrumentation Needs**:
  - Track CPE operations
  - Monitor device connectivity checks
  - Capture CPE resource creation/updates

### High Priority APIs (P1)

#### 4. **v1/service** (`apis/v1/service.py`)
**Why**: Legacy service operations
- Similar to v3/service but older version
- Same BLL/DLL dependencies

#### 5. **v1/eligibility** (`apis/v1/eligibility.py`)
**Why**: Eligibility checks before provisioning
- **BLL**: `beorn_app/bll/eligibility/`
  - `automation_eligibility.py` - Automation checks
  - `mdso_eligible.py` - MDSO eligibility validation
  - `circuit_test_eligibility.py` - Circuit test checks
- **Instrumentation Needs**:
  - Track eligibility decision flow
  - Capture eligibility failure reasons
  - Monitor automation decision logic

#### 6. **v1/managed_service** (`apis/v1/managed_service.py`)
**Why**: Managed service operations
- **BLL**: `beorn_app/bll/managed_service.py`
- **DLL**: `beorn_app/dll/mdso.py`, `beorn_app/dll/sales_force.py`
- **Instrumentation Needs**:
  - Track managed service lifecycle
  - Monitor Salesforce integration calls

---

## ARDA Application (FastAPI)

### Critical APIs Requiring Instrumentation (P0)

#### 1. **circuit_design** (`api/circuit_design.py`)
**Why**: Core circuit design automation - most complex operation
- **API Methods**: `POST`
- **BLL**: `arda_app/bll/circuit_design/`
  - `circuit_design_main.py` - Main design orchestration
  - `bandwidth_change/bw_change_main.py` - Bandwidth operations
  - `common.py` - Common design utilities
  - `exit_criteria.py` - Exit criteria validation
- **DLL**: 
  - `arda_app/dll/granite.py` - Granite operations
  - `arda_app/dll/mdso.py` - MDSO operations
  - `arda_app/common/mdso_operations.py` - MDSO helpers
- **Instrumentation Needs**:
  - Trace entire circuit design flow
  - Track each design step (validation, path creation, resource assignment)
  - Capture design errors with context
  - Monitor external system calls (Granite, MDSO)
  - Add circuit_id, engineering_job_type, service_type attributes

#### 2. **build_circuit_design** (`api/build_circuit_design.py`)
**Why**: Initial circuit design intake
- **API Methods**: `POST`
- **BLL**: `arda_app/common/build_circuit_design_template.py`
  - `build_circuit_design_main()` - Main build logic
- **Instrumentation Needs**:
  - Trace design build initiation
  - Track eligibility checks
  - Monitor design template processing

#### 3. **disconnect** (`api/disconnect.py`)
**Why**: Circuit disconnection operations
- **API Methods**: `POST`
- **BLL**: `arda_app/bll/disconnect.py`, `arda_app/bll/disconnect_utils.py`
- **DLL**: `arda_app/dll/granite.py`, `arda_app/dll/mdso.py`
- **Instrumentation Needs**:
  - Trace disconnect workflow
  - Track resource cleanup operations
  - Monitor disconnect validation

#### 4. **logical_change** (`api/logical_change.py`)
**Why**: Logical circuit changes
- **API Methods**: `POST`
- **BLL**: `arda_app/bll/logical_change.py`
- **Instrumentation Needs**:
  - Trace logical change operations
  - Track change validation and application

#### 5. **ip_reservation** (`api/ip_reservation.py`)
**Why**: IP address reservation operations
- **API Methods**: `POST`
- **BLL**: `arda_app/bll/net_new/ip_reservation/`
  - `ip_reservation_main.py` - Main IP reservation logic
  - `utils/` - IP utilities (granite, ipc, mdso, static_ip)
- **DLL**: `arda_app/dll/ipc.py` - IPC operations
- **Instrumentation Needs**:
  - Trace IP reservation flow
  - Track IPC API calls
  - Monitor IP conflict detection
  - Capture IP subnet information

#### 6. **vlan_reservation** (`api/vlan_reservation.py`)
**Why**: VLAN reservation operations
- **API Methods**: `POST`
- **BLL**: `arda_app/bll/net_new/vlan_reservation/`
  - `vlan_reservation_main.py` - Main VLAN logic
  - `collect_vlans.py`, `vlan_utils.py` - VLAN utilities
- **Instrumentation Needs**:
  - Trace VLAN reservation flow
  - Track VLAN conflict detection
  - Monitor VLAN assignment operations

#### 7. **transport_path** (`api/transport_path.py`)
**Why**: Transport path creation
- **API Methods**: `POST`
- **BLL**: `arda_app/bll/transport_path.py`, `arda_app/bll/type_two_transport_path.py`
- **DLL**: `arda_app/dll/granite.py`
- **Instrumentation Needs**:
  - Trace transport path creation
  - Track path validation and segment operations
  - Monitor Granite path operations

### High Priority APIs (P1)

#### 8. **bandwidth_change** (`api/bandwidth_change.py`)
**Why**: Bandwidth modification operations
- **BLL**: `arda_app/bll/circuit_design/bandwidth_change/`
  - `bw_change_main.py`, `normal_bw_upgrade.py`, `express_bw_upgrade.py`
- **Instrumentation Needs**:
  - Track bandwidth change operations
  - Monitor upgrade/downgrade flows

#### 9. **create_bom** (`api/create_bom.py`)
**Why**: Bill of Materials generation
- **BLL**: `arda_app/bll/determine_bom.py`
- **Instrumentation Needs**:
  - Trace BOM generation
  - Track component selection logic

#### 10. **cpe_swap** (`api/cpe_swap.py`)
**Why**: CPE swap operations
- **BLL**: `arda_app/bll/cpe_swap/`
  - `cpe_swap_main.py`, `cpe_swap_utils.py`
- **Instrumentation Needs**:
  - Trace CPE swap workflow
  - Track device replacement operations

#### 11. **ip_reclamation** (`api/ip_reclamation.py`)
**Why**: IP address reclamation
- **BLL**: `arda_app/bll/net_new/ip_reclamation.py`
- **Instrumentation Needs**:
  - Trace IP reclamation flow
  - Track subnet block operations

#### 12. **remedyticket** (`api/remedyticket.py`)
**Why**: Remedy ticket operations
- **BLL**: `arda_app/bll/remedy/`
  - `remedy_ticket.py`, `remedy_utils.py`
- **DLL**: `arda_app/dll/remedy.py` (if exists)
- **Instrumentation Needs**:
  - Trace Remedy ticket creation/updates
  - Track ticket status operations

---

## PALANTIR Application (Flask)

### Critical APIs Requiring Instrumentation (P0)

#### 1. **v3/circuit_test** (`apis/v3/circuit_test.py`)
**Why**: Circuit testing operations - critical for validation
- **API Methods**: `GET`
- **BLL**: `palantir_app/bll/circuit_test_v3.py`
  - `circuit_test_model_v3()` - Main test logic
- **DLL**: `palantir_app/dll/granite.py`, `palantir_app/dll/mdso.py`
- **Instrumentation Needs**:
  - Trace circuit test execution
  - Track Granite/MDSO queries for test data
  - Capture test results and validation status
  - Monitor test timeout scenarios

#### 2. **v4/circuit_test** (`apis/v4/circuit_test.py`)
**Why**: Updated circuit test API
- Similar to v3 but newer version
- Same instrumentation needs

#### 3. **v1/compliance_provisioning** (`apis/v1/compliance_provisioning.py`)
**Why**: Compliance checks for provisioning
- **BLL**: `palantir_app/bll/compliance/` (if exists)
- **Instrumentation Needs**:
  - Trace compliance validation flow
  - Track compliance rule evaluation
  - Capture compliance failures

#### 4. **v1/compliance_disconnect** (`apis/v1/compliance_disconnect.py`)
**Why**: Compliance checks for disconnection
- Similar to compliance_provisioning
- Same instrumentation needs

#### 5. **v4/resource_status** (`apis/v4/resource_status.py`)
**Why**: Resource status polling and monitoring
- **API Methods**: `GET`
- **BLL**: `palantir_app/bll/resource_status.py`
  - `get_resource_status()` - Main status retrieval
  - `_poll_response()` - Polling logic
  - `_handle_failure_reason()` - Error handling
- **DLL**: `palantir_app/dll/mdso.py`
  - `mdso_get()` - MDSO API calls
- **Instrumentation Needs**:
  - Trace resource status queries
  - Track polling operations
  - Monitor status transitions
  - Capture failure reasons with error categorization
  - Add resource_id, poll_counter attributes

#### 6. **v1/resource_status** (`apis/v1/resource_status.py`)
**Why**: Legacy resource status API
- Similar to v4 but older version

### High Priority APIs (P1)

#### 7. **v3/ise** (`apis/v3/ise.py`)
**Why**: ISE (Identity Services Engine) operations
- **API Methods**: `GET`, `POST`, `DELETE`
- **BLL**: `palantir_app/bll/ise_operations.py` (if exists)
- **Instrumentation Needs**:
  - Trace ISE device operations
  - Track ISE ID lookups
  - Monitor device registration/removal

#### 8. **v2/device** (`apis/v2/device.py`)
**Why**: Device management operations
- **BLL**: `palantir_app/bll/device.py` (if exists)
- **Instrumentation Needs**:
  - Trace device operations
  - Track device validation

#### 9. **v1/overlay_compliance** (`apis/v1/overlay_compliance.py`)
**Why**: Overlay compliance checks
- **BLL**: `palantir_app/bll/route_overlay.py`
  - `route_compliance()` - Compliance logic
- **Instrumentation Needs**:
  - Trace overlay compliance validation
  - Track route compliance checks

#### 10. **v1/overlay_acceptance** (`apis/v1/overlay_acceptance.py`)
**Why**: Overlay acceptance operations
- **BLL**: `palantir_app/bll/route_overlay.py`
  - `route_acceptance()` - Acceptance logic
- **Instrumentation Needs**:
  - Trace overlay acceptance flow
  - Track acceptance validation

---

## Common DLL Components Requiring Instrumentation

### MDSO Operations (All Apps)
**Files**: 
- `beorn_app/dll/mdso.py`
- `arda_app/common/mdso_operations.py`
- `palantir_app/common/mdso_operations.py`

**Functions to Instrument**:
- `mdso_get()` - GET requests to MDSO
- `mdso_post()` - POST requests to MDSO
- `mdso_put()` - PUT requests to MDSO
- `create_service()` - Service creation
- `service_details()` - Service queries
- `service_id_lookup()` - Service lookups

**Instrumentation Needs**:
- Track all MDSO API calls with endpoint, method, status code
- Capture request/response sizes
- Monitor latency and timeout scenarios
- Track MDSO errors with error categorization
- Add resource_id, circuit_id attributes

### Granite Operations (All Apps)
**Files**:
- `beorn_app/dll/granite.py`
- `arda_app/dll/granite.py`
- `palantir_app/dll/granite.py`

**Functions to Instrument**:
- `granite_get()` - GET requests to Granite
- `granite_post()` - POST requests to Granite
- `granite_put()` - PUT requests to Granite
- `get_path_elements_from_filter()` - Path element queries
- `get_circuit_site_info()` - Site information queries

**Instrumentation Needs**:
- Track all Granite API calls
- Monitor query performance
- Capture Granite errors
- Track circuit path operations

### IPC Operations (Arda)
**Files**: `arda_app/dll/ipc.py`

**Functions to Instrument**:
- All IPC API interaction functions
- IP reservation/reclamation operations

**Instrumentation Needs**:
- Track IPC API calls
- Monitor IP operations
- Capture IPC errors

### Denodo Operations (Beorn)
**Files**: `beorn_app/dll/denodo.py`

**Functions to Instrument**:
- All Denodo query functions
- `call_denodo_for_circuit_devices()` - Device queries

**Instrumentation Needs**:
- Track Denodo query performance
- Monitor query complexity
- Capture Denodo errors

---

## Instrumentation Implementation Strategy

### 1. Decorator-Based Approach
Use the `@traced` decorator from `otel_sense.py` for BLL functions:

```python
from beorn_app.common.otel import traced

@traced("beorn.service.create", {"operation": "create_service"})
def create_core_service(body):
    # Service creation logic
    pass
```

### 2. Manual Span Creation
For complex flows, create manual spans:

```python
from beorn_app.common.otel import get_tracer, set_mdso_correlation

tracer = get_tracer(__name__)
with tracer.start_as_current_span("beorn.topology.create") as span:
    set_mdso_correlation(circuit_id=cid, service_type="FIA")
    # Topology creation logic
    span.set_attribute("topology.node_count", node_count)
```

### 3. DLL HTTP Call Instrumentation
The auto-instrumentation from `observability.py` already instruments `requests` and `httpx`, but add explicit attributes:

```python
from beorn_app.common.otel import add_span_event, set_span_error

try:
    response = mdso_get(endpoint)
    add_span_event("mdso.api.call", endpoint=endpoint, status_code=response.status_code)
except Exception as e:
    set_span_error(e)
    add_span_event("mdso.api.error", endpoint=endpoint, error_type=type(e).__name__)
```

### 4. Error Categorization
Use MDSO patterns for error extraction:

```python
from beorn_app.common.otel.mdso_patterns import ErrorCategorizer

categorizer = ErrorCategorizer()
error_context = categorizer.extract_error_context(str(error))
span.set_attribute("error.category", error_context["category"])
span.set_attribute("error.severity", error_context["severity"])
```

---

## Recommended Implementation Order

### Phase 1: Critical Paths (Week 1)
1. Beorn: v3/service, v3/topologies
2. Arda: circuit_design, build_circuit_design, disconnect
3. Palantir: v3/circuit_test, v4/resource_status

### Phase 2: High Priority (Week 2)
1. Beorn: v3/cpe, v1/eligibility
2. Arda: ip_reservation, vlan_reservation, transport_path
3. Palantir: compliance_provisioning, compliance_disconnect

### Phase 3: Supporting Operations (Week 3)
1. All apps: DLL instrumentation (MDSO, Granite, IPC, Denodo)
2. Remaining P1 APIs
3. Error categorization enhancement

### Phase 4: Optimization (Week 4)
1. Add custom metrics for business KPIs
2. Enhance error categorization
3. Add performance monitoring dashboards

---

## Key Attributes to Capture

### Common Attributes
- `circuit_id` (cid) - Primary correlation key
- `product_id` - Product identifier
- `resource_id` - MDSO resource ID
- `service_type` - FIA, ELAN, ELINE, etc.
- `order_type` - provision, disconnect, modify
- `engineering_job_type` - New, Upgrade, etc.

### Beorn-Specific
- `topology.node_count` - Number of nodes
- `topology.service_type` - Service type
- `topology.vendor` - Device vendor
- `service.stage` - Service stage

### Arda-Specific
- `design.operation` - Design operation type
- `ip.subnet` - IP subnet information
- `vlan.id` - VLAN identifier
- `transport_path.segments` - Number of segments

### Palantir-Specific
- `test.type` - Test type
- `test.status` - Test status
- `compliance.rule` - Compliance rule evaluated
- `resource.status` - Resource status

---

## Metrics to Track

### Business Metrics
- Service creation success rate
- Circuit design completion time
- Topology generation latency
- IP/VLAN reservation success rate
- Compliance check pass rate

### Technical Metrics
- MDSO API call latency (p50, p95, p99)
- Granite query performance
- External system error rates
- Request processing time by endpoint
- Error categorization distribution

---

## Next Steps

1. **Review and Approve**: Review this analysis with the team
2. **Create Implementation Plan**: Break down into specific tasks
3. **Start with Phase 1**: Implement critical path instrumentation
4. **Iterate**: Add instrumentation incrementally based on priorities
5. **Monitor**: Use correlation engine to validate instrumentation effectiveness
