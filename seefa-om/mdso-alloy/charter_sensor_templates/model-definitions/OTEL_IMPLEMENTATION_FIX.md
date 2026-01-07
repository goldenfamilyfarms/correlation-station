# OpenTelemetry Implementation Fix - Resolution Guide

## Problem Summary

The remote scripts in `scripts.fabricator` were failing with OpenTelemetry import errors:
```
Failed remote script for job c89e1bfd-eb3e-11f0-8bc4-6df956d7cef3 (exit code: 1):
instrumentation.py: Failed to import OpenTelemetry modules - OTEL_AVAILABLE=False
Error: No module named 'opentelemetry'
Error: 'Activate' object has no attribute '_delete_existing_resource_and_dependencies'
```

## Root Causes Identified

### 1. Missing TOML Configuration
**Issue**: No `scripts.fabricator.toml` existed to specify dependencies for fabricator scripts.

**Impact**: Scripts used the generic `scripts.toml` which pointed to `requirements_cst.txt` with outdated OpenTelemetry versions.

### 2. Version Mismatch
**Issue**: Incompatible OpenTelemetry package versions between requirements files:
- `requirements_cst.txt`: OpenTelemetry 1.12.0
- `scripts/otel/requirements.txt`: OpenTelemetry 1.20.0

**Impact**: Code written for 1.20.0 features failed with 1.12.0 packages.

### 3. Missing Method
**Issue**: `compliance.py` called `_delete_existing_resource_and_dependencies()` which didn't exist in `FactoryBase`.

**Impact**: Script crashed when trying to clean up existing resources.

### 4. Incorrect Export Path
**Issue**: OpenTelemetry traces were configured to export to `/opt/ciena/bp2/alloy-collector/` instead of `/opt/ciena/bp2/alloy-collector/logs/`.

**Impact**: Trace logs weren't appearing in the expected location.

## Solutions Implemented

### Solution 1: Created `scripts.fabricator.toml`
**File**: `scripts.d/scripts.fabricator.toml`

```toml
[virtualenv]
python = "py3"
requirements = "requirements_cst.txt"
```

**Per Blue Planet Orchestrator Documentation**:
> When executing a remote script named `foo.scripts.Activate`, the virtualenv configuration will be drawn from the `.toml` file that most closely matches the script's fully-qualified Python name (FQPN). The following filenames will be tried, in order:
> 1. `scripts.d/foo.scripts.Activate.toml`
> 2. `scripts.d/foo.scripts.toml`
> 3. `scripts.d/foo.toml`

For `scripts.fabricator.compliance.Activate`, the matching order is:
1. `scripts.d/scripts.fabricator.compliance.Activate.toml` ❌ (doesn't exist)
2. `scripts.d/scripts.fabricator.compliance.toml` ❌ (doesn't exist)
3. `scripts.d/scripts.fabricator.toml` ✅ **MATCHES** (newly created)

### Solution 2: Updated OpenTelemetry Versions
**File**: `requirements_cst.txt`

Updated all OpenTelemetry packages to version 1.20.0:
```
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-http==1.20.0
opentelemetry-semantic-conventions==0.41b0
structlog==23.2.0
opentelemetry-instrumentation-requests==0.41b0
opentelemetry-instrumentation-urllib3==0.41b0
```

### Solution 3: Added Missing Method
**File**: `scripts/fabricator/common.py`

Added `_delete_existing_resource_and_dependencies()` method to `FactoryBase` class:
- Retrieves existing child resources from the factory resource
- Terminates dependencies first (proper cleanup order)
- Terminates child resources
- Handles errors gracefully without failing the entire operation

### Solution 4: Updated Export Path
**Files Modified**:
1. `scripts/common_plan.py`: Updated `OTEL_TRACE_LOG_DIR` constant
2. `scripts/otel/instrumentation.py`: Updated `DEFAULT_TRACE_LOG_DIR` constant

**New path**: `/opt/ciena/bp2/alloy-collector/logs/`

Trace files will now be written to:
```
/opt/ciena/bp2/alloy-collector/logs/traces.ndjson
```

## How Remote Script Dependencies Work

Per the Blue Planet Orchestrator documentation:

### Virtual Environment Configuration
1. **TOML files** in `scripts.d/` directory configure the virtualenv for each script namespace
2. **Python version** must be one of: `"py38"`, `"py35"` (deprecated), or `"py3"` (alias for py38)
3. **Requirements file** must be at the root of model-definitions/ and named `requirements*.txt`

### Dependency Installation Process
When scriptplan executes a remote script:
1. Checks out the Model Definitions asset area
2. Matches the script's FQPN to a TOML configuration file
3. Creates a Python virtualenv with specified Python version
4. Installs packages from the specified requirements file
5. Runs the script in this isolated environment

### Package Requirements
- **Source distributions** requiring compilation are not allowed (optional C extensions OK)
- **Binary wheels** are strongly preferred for faster installation
- **Platform compatibility tags** must match the scriptplan environment:
  - Python: `py3`, `py38`, `cp38`
  - Platform: `manylinux_2_31_x86_64`, `manylinux2014_x86_64`, `linux_x86_64`, or `any`

## OpenTelemetry Architecture

### Two Export Modes

#### Mode 1: Direct OTLP (Not Used Here)
```
MDSO Scripts → Alloy Agent (localhost:4318) → Meta Server (159.56.4.94:55681)
```
- Requires network connectivity to Alloy agent
- Not suitable for isolated containers in BluePlanet solution manager

#### Mode 2: File-Based Export (ACTIVE)
```
MDSO Scripts → Write to /opt/ciena/bp2/alloy-collector/logs/traces.ndjson
Alloy Agent → Tails file → Meta Server (159.56.4.94:55681)
```
- Works in isolated Docker containers
- No network connectivity required
- Alloy agent reads traces from shared volume

### Export Mode Detection Priority
1. **Explicit parameter**: `use_file_export` in `setup_otel()`
2. **Environment variable**: `OTEL_EXPORT_MODE` ("file" or "otlp")
3. **Class constant**: `CommonPlan.OTEL_EXPORT_MODE`
4. **Auto-detect**: Defaults to `"file"` for safety

### Configuration Constants in CommonPlan
```python
# OTel Export Mode
OTEL_EXPORT_MODE = None  # None = auto-detect (defaults to "file")

# Trace log directory for file-based export
OTEL_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector/logs"

# Use sudo for file operations
OTEL_USE_SUDO = None  # None = auto-detect based on permissions

# OTLP exporter endpoint (for direct OTLP mode - not used)
OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4318"

# Feature flags
OTEL_ENABLED = True
OTEL_SAMPLING_ENABLED = True
OTEL_SAMPLING_RATE = 1.0
```

## Entry Points and Instrumentation Flow

### Primary Entry Points
1. **`scripts/fabricator/compliance.py`** - Service Mapper compliance operations
2. **`scripts/fabricator/provisioning.py`** - Network Service provisioning operations

### Inheritance Chain
```
compliance.Activate
├─ extends: FactoryBase
│  └─ extends: CommonPlan
│     └─ extends: Plan, Utils, OTelMixin
└─ extends: OTelMixin (direct)
```

### Instrumentation Pattern in Entry Points
```python
class Activate(FactoryBase, OTelMixin):
    def process(self):
        # Step 1: Initialize OTel instrumentation
        self.__init_otel__()

        # Step 2: Create root span for operation
        with self.create_root_span(operation_name="compliance_activate"):

            # Step 3: Set correlation baggage
            self.set_correlation_baggage_from_instance()

            # Step 4: Record span events
            self.record_span_event_from_instance("compliance.started", {...})

            # Step 5: Wrap operations in timed spans
            with self.timed_operation("compliance.get_circuit_details"):
                self._set_circuit_details()

            # Step 6: Handle errors with OTel context
            try:
                # ... operation logic ...
            except RuntimeError as err:
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler("Service mapper activation failed", exception=err)
                raise
```

### OTelMixin Methods Available
- `__init_otel__()` - Initialize OpenTelemetry instrumentation
- `create_root_span(operation_name)` - Create root span context manager
- `timed_operation(operation_name, attributes)` - Create timed sub-span
- `record_span_event_from_instance(event_name, attributes)` - Record span event
- `set_correlation_baggage_from_instance()` - Set correlation context
- `otel_error_handler(message, exception)` - Handle errors with OTel context

## Verification Steps

### Step 1: Verify TOML Configuration
```bash
# Check that scripts.fabricator.toml exists
ls -la seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts.d/scripts.fabricator.toml

# Verify contents
cat seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts.d/scripts.fabricator.toml
```

**Expected output**:
```toml
[virtualenv]
python = "py3"
requirements = "requirements_cst.txt"
```

### Step 2: Verify OpenTelemetry Package Versions
```bash
grep -A 10 "OpenTelemetry instrumentation packages" \
  seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/requirements_cst.txt
```

**Expected output**:
```
# OpenTelemetry instrumentation packages
# Updated to version 1.20.0 to match scripts/otel/requirements.txt
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-http==1.20.0
opentelemetry-semantic-conventions==0.41b0
structlog==23.2.0
opentelemetry-instrumentation-requests==0.41b0
opentelemetry-instrumentation-urllib3==0.41b0
```

### Step 3: Verify Method Exists
```bash
grep -A 5 "def _delete_existing_resource_and_dependencies" \
  seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts/fabricator/common.py
```

**Expected**: Method definition found at line 65

### Step 4: Verify Export Path Configuration
```bash
# Check common_plan.py
grep "OTEL_TRACE_LOG_DIR" \
  seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts/common_plan.py

# Check instrumentation.py
grep "DEFAULT_TRACE_LOG_DIR" \
  seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts/otel/instrumentation.py
```

**Expected output**:
```
OTEL_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector/logs"
DEFAULT_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector/logs"
```

### Step 5: Test Remote Script Execution

#### Option A: Using Blue Planet Orchestrator
1. Onboard the updated model-definitions to BPO
2. Trigger a compliance activation operation
3. Monitor the script execution logs
4. Check for successful OpenTelemetry initialization

**Expected log messages**:
```
compliance.py: Module loaded with OTelMixin
instrumentation.py: OpenTelemetry modules loaded successfully - OTEL_AVAILABLE=True
setup_otel: Using file-based trace export mode
setup_otel: Trace log file: /opt/ciena/bp2/alloy-collector/logs/traces.ndjson
setup_otel: OTel initialization complete
```

#### Option B: Using script-dev Container
```bash
# In script-dev environment
cd /model-definitions
python -c "
import sys
sys.path.append('.')
from scripts.fabricator.compliance import Activate
print('✓ Import successful')
"

# Test OTel availability
python -c "
import sys
sys.path.append('.')
from scripts.otel.instrumentation import OTEL_AVAILABLE
print(f'OTEL_AVAILABLE: {OTEL_AVAILABLE}')
"
```

**Expected output**:
```
✓ Import successful
OTEL_AVAILABLE: True
```

### Step 6: Verify Trace File Creation
After running a compliance or provisioning operation:

```bash
# Check if trace log directory exists
ls -la /opt/ciena/bp2/alloy-collector/logs/

# Check if trace file was created
ls -lh /opt/ciena/bp2/alloy-collector/logs/traces.ndjson

# View recent traces (last 10 lines)
tail -n 10 /opt/ciena/bp2/alloy-collector/logs/traces.ndjson

# Count number of trace spans exported
wc -l /opt/ciena/bp2/alloy-collector/logs/traces.ndjson
```

**Expected**: Trace file exists and contains NDJSON-formatted trace spans

### Step 7: Validate Trace Content
```bash
# Pretty-print a trace span to verify structure
tail -n 1 /opt/ciena/bp2/alloy-collector/logs/traces.ndjson | python -m json.tool
```

**Expected JSON structure**:
```json
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "mdso-scriptplan"}},
        {"key": "deployment.environment", "value": {"stringValue": "dev"}}
      ]
    },
    "scopeSpans": [{
      "scope": {"name": "..."},
      "spans": [{
        "traceId": "...",
        "spanId": "...",
        "name": "compliance_activate",
        "startTimeUnixNano": "...",
        "endTimeUnixNano": "...",
        "attributes": [
          {"key": "circuit_id", "value": {...}},
          {"key": "operation", "value": {...}}
        ]
      }]
    }]
  }]
}
```

## Testing Plan

### Unit Testing
1. **Import tests**: Verify all OpenTelemetry modules can be imported
2. **Method tests**: Test `_delete_existing_resource_and_dependencies()` with mock resources
3. **Configuration tests**: Verify TOML file matching logic

### Integration Testing
1. **Compliance activation**: Test full compliance workflow with OTel instrumentation
2. **Provisioning activation**: Test full provisioning workflow with OTel instrumentation
3. **Error handling**: Verify OTel error handler captures exceptions correctly
4. **Trace export**: Verify traces are written to file successfully

### Test Scenarios

#### Scenario 1: Compliance Service Mapper Creation
**Payload**:
```json
{
  "circuit_id": "TEST-12345",
  "remediation_flag": false,
  "order_type": "new",
  "slm_eligible": true
}
```

**Expected traces**:
- Root span: `compliance_activate`
- Child spans: `compliance.get_circuit_details`, `compliance.create_mappers`, `compliance.await_active`
- Events: `compliance.started`, `compliance.mapper.creation.started`, `compliance.mapper.creation.completed`

#### Scenario 2: Provisioning Network Service Creation
**Payload**:
```json
{
  "circuit_id": "TEST-67890",
  "service_type": "ethernet",
  "bandwidth": "1000"
}
```

**Expected traces**:
- Root span: `provisioning_activate`
- Child spans: `provisioning.get_circuit_details`, `provisioning.create_services`, `provisioning.await_active`
- Events: `provisioning.started`, `provisioning.leg.creation.started`, `provisioning.leg.creation.completed`

#### Scenario 3: Error Handling
**Test**: Trigger an error during resource creation

**Expected**:
- Error captured in span status
- Error event recorded with exception details
- `otel_error_handler` logs error with correlation context

## Troubleshooting

### Issue: OpenTelemetry modules still not found
**Diagnosis**:
```bash
# Check which TOML file is being used
# Look for scriptplan logs showing virtualenv creation

# Verify requirements file has correct packages
grep opentelemetry requirements_cst.txt
```

**Resolution**:
- Ensure `scripts.fabricator.toml` exists and references correct requirements file
- Re-onboard model-definitions to trigger virtualenv rebuild

### Issue: Trace file not created
**Diagnosis**:
```bash
# Check directory permissions
ls -la /opt/ciena/bp2/alloy-collector/

# Check if sudo is needed
stat /opt/ciena/bp2/alloy-collector/logs/
```

**Resolution**:
- Create directory manually: `sudo mkdir -p /opt/ciena/bp2/alloy-collector/logs`
- Set appropriate permissions: `sudo chmod 777 /opt/ciena/bp2/alloy-collector/logs`
- Or set `OTEL_USE_SUDO=True` in environment

### Issue: Trace file exists but is empty
**Diagnosis**:
```bash
# Check if spans are being created
# Look for setup_otel log messages in scriptplan logs

# Verify file exporter is working
python seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts/otel/test_file_export.py
```

**Resolution**:
- Verify `__init_otel__()` is being called in the script
- Check for exceptions during span export
- Ensure `BatchSpanProcessor` is flushing spans (check timeouts)

### Issue: Permission denied writing to trace file
**Diagnosis**:
```bash
# Check file ownership
ls -l /opt/ciena/bp2/alloy-collector/logs/traces.ndjson

# Check current user
whoami
```

**Resolution**:
- Enable sudo mode: Set `OTEL_USE_SUDO=True` in CommonPlan or environment
- Or change file permissions: `sudo chown $(whoami) /opt/ciena/bp2/alloy-collector/logs/traces.ndjson`

## Files Modified

| File | Change Type | Description |
|------|------------|-------------|
| `scripts.d/scripts.fabricator.toml` | Created | TOML configuration for fabricator scripts |
| `requirements_cst.txt` | Updated | OpenTelemetry packages upgraded to 1.20.0 |
| `scripts/fabricator/common.py` | Updated | Added `_delete_existing_resource_and_dependencies()` method |
| `scripts/common_plan.py` | Updated | Changed `OTEL_TRACE_LOG_DIR` to include `/logs` subdirectory |
| `scripts/otel/instrumentation.py` | Updated | Changed `DEFAULT_TRACE_LOG_DIR` to include `/logs` subdirectory |

## Next Steps

1. **Onboard to BPO**: Use `bpocore-cli` to onboard updated model-definitions
2. **Test in dev**: Run compliance and provisioning operations in dev environment
3. **Monitor traces**: Verify traces are being written to `/opt/ciena/bp2/alloy-collector/logs/traces.ndjson`
4. **Validate Alloy**: Confirm Alloy agent is tailing the trace file and forwarding to Meta server
5. **Performance test**: Verify no significant performance impact from instrumentation

## References

- [Blue Planet Orchestrator - Remote Scripts Documentation](https://developer.blueplanet.com/docs/bpocore-docs/references/type_layer/remote_scripts.html)
- [OpenTelemetry Python SDK Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [MDSO OTel Implementation Summary](./OTEL_IMPLEMENTATION_SUMMARY.md)
- [MDSO OTel Instrumentation Guide](./README_INSTRUMENTATION.md)
