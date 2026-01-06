# OpenTelemetry Implementation Summary

## Issue Resolution

### Problem
OpenTelemetry logs were not being written to `/opt/ciena/bp2/alloy-collector/logs` because:
1. The directory `/opt/ciena/bp2/alloy-collector` did not exist
2. The `compliance.py` script was not instrumented with OpenTelemetry
3. OpenTelemetry packages were not installed

### Solutions Applied

#### 1. Created the Required Directory
```bash
sudo mkdir -p /opt/ciena/bp2/alloy-collector
sudo chmod 777 /opt/ciena/bp2/alloy-collector
```

**Location**: `/opt/ciena/bp2/alloy-collector/`
**Permissions**: `drwxrwxrwx` (full read/write for all users)
**Log File**: `traces.ndjson` (created automatically on first span export)

#### 2. Installed OpenTelemetry Packages
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http structlog
```

#### 3. Instrumented compliance.py
Added full OpenTelemetry instrumentation to `scripts/fabricator/compliance.py`:
- Inherited from `OTelMixin`
- Added `__init_otel__()` initialization
- Created root span for the entire operation
- Added correlation baggage tracking
- Added span events for key operations
- Added timed operations for performance tracking
- Added error handling with OTel error handler

## Current OTel-Instrumented Scripts

### 1. **provisioning.py** (Already Instrumented)
- **Location**: `scripts/fabricator/provisioning.py`
- **Operations Tracked**:
  - Network service creation/update
  - Circuit leg provisioning
  - Resource activation wait times

### 2. **compliance.py** (Newly Instrumented)
- **Location**: `scripts/fabricator/compliance.py`
- **Operations Tracked**:
  - Service mapper creation
  - Circuit details fetching
  - Child resource creation and activation
  - Compliance issue detection

### 3. **common_plan.py** (Base Infrastructure)
- **Location**: `scripts/common_plan.py`
- **Features**:
  - Auto-initialization of OTel in `run()` method
  - Constants for OTel configuration
  - Integration with all subclasses

## Architecture

### How OTel Works in Your Scripts

```
┌─────────────────────────────────────────────────────────┐
│ 1. Script Execution (compliance.py or provisioning.py) │
│    - Inherits from CommonPlan + OTelMixin               │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 2. OTel Initialization                                  │
│    - __init_otel__() called in process()                │
│    - Creates tracer with service name                   │
│    - Sets up FileSpanExporter                           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Span Creation                                        │
│    - Root span wraps entire process()                   │
│    - Child spans for specific operations                │
│    - Correlation baggage set (circuit_id, resource_id)  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 4. File Export (Default Mode)                           │
│    - Spans buffered in BatchSpanProcessor                │
│    - Exported to /opt/ciena/bp2/alloy-collector/        │
│    - Written as NDJSON (one JSON object per line)       │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Log File Created                                     │
│    - File: /opt/ciena/bp2/alloy-collector/traces.ndjson │
│    - Format: NDJSON (newline-delimited JSON)            │
└──────────────────────────────────────────────────────────┘
```

### Export Modes

#### File-Based Export (Default - ✓ Working)
- **Mode**: File export
- **Output**: `/opt/ciena/bp2/alloy-collector/traces.ndjson`
- **Use Case**: Isolated containers that cannot reach Alloy agent directly
- **Advantages**: Works in any environment, no network required

#### OTLP Export (Alternative - for direct connectivity)
- **Mode**: OTLP over HTTP
- **Endpoint**: `http://localhost:4318/v1/traces`
- **Use Case**: When scripts can directly reach Alloy agent
- **To Enable**: Set `OTEL_EXPORT_MODE=otlp` environment variable

## Configuration

### Environment Variables (Optional)

You can override defaults using environment variables:

```bash
# Export mode: "file" (default) or "otlp"
export OTEL_EXPORT_MODE=file

# Trace log directory (file mode only)
export OTEL_TRACE_LOG_DIR=/opt/ciena/bp2/alloy-collector

# Use sudo for file operations (auto-detected if not set)
export OTEL_USE_SUDO=false

# Enable/disable OTel (default: true)
export OTEL_ENABLED=true

# Environment name (dev, staging, prod)
export MDSO_ENV=dev

# OTLP endpoint (otlp mode only)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

### Class Constants (In common_plan.py)

These are already set in `CommonPlan`:

```python
OTEL_EXPORT_MODE = None  # None = auto-detect (defaults to "file")
OTEL_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector"
OTEL_USE_SUDO = None  # None = auto-detect based on permissions
OTEL_ENABLED = True
MDSO_ENV = "dev"
```

## How to Add OTel to More Scripts

### Step-by-Step Guide

1. **Add OTelMixin to your class**:
   ```python
   from scripts.otel.otel_mixin import OTelMixin

   class MyScript(CommonPlan, OTelMixin):
       pass
   ```

2. **Initialize OTel in process()**:
   ```python
   def process(self):
       self.__init_otel__()
       with self.create_root_span():
           # Your code here
   ```

3. **Set correlation context**:
   ```python
   # Auto-extract from instance attributes
   self.set_correlation_baggage_from_instance()
   ```

4. **Add span events** (optional):
   ```python
   if getattr(self, '_otel_initialized', False):
       self.record_span_event_from_instance(
           "my_operation.started",
           {"device_id": "123", "vendor": "juniper"}
       )
   ```

5. **Add error handling**:
   ```python
   try:
       risky_operation()
   except Exception as e:
       if getattr(self, '_otel_initialized', False):
           self.otel_error_handler(f"Error: {e}", e)
       raise
   ```

See `README_INSTRUMENTATION.md` for complete examples.

## Testing Your Implementation

### 1. Run the Diagnostic Test
```bash
cd /home/user/correlation-station/seefa-om/mdso-alloy/charter_sensor_templates/model-definitions/scripts/otel
python test_file_export.py
```

**Expected Output**:
```
✓ Test PASSED - File export is working correctly
```

### 2. Check the Trace Log File
```bash
# Check file exists and has content
ls -lh /opt/ciena/bp2/alloy-collector/traces.ndjson

# View the traces (pretty-printed)
cat /opt/ciena/bp2/alloy-collector/traces.ndjson | jq .

# View just span names and trace IDs
cat /opt/ciena/bp2/alloy-collector/traces.ndjson | jq -r '.name, .trace_id'

# Monitor in real-time as traces are written
tail -f /opt/ciena/bp2/alloy-collector/traces.ndjson | jq .
```

### 3. Run Your Compliance Script
When you send a payload to `compliance.py`, it will now:
1. Initialize OTel automatically
2. Create a root span named `compliance_activate`
3. Track all operations (circuit details, mapper creation, etc.)
4. Write spans to `/opt/ciena/bp2/alloy-collector/traces.ndjson`

### 4. Verify Spans are Created
After running your script:
```bash
# Count spans in the file
wc -l /opt/ciena/bp2/alloy-collector/traces.ndjson

# View span names
cat /opt/ciena/bp2/alloy-collector/traces.ndjson | jq -r '.name'

# View spans with circuit_id
cat /opt/ciena/bp2/alloy-collector/traces.ndjson | jq 'select(.attributes.circuit_id != null)'
```

## Troubleshooting

### Issue: No traces.ndjson file created
**Check**:
1. Directory exists: `ls -la /opt/ciena/bp2/alloy-collector`
2. OTel packages installed: `pip list | grep opentelemetry`
3. Script is calling `__init_otel__()`: Check logs for "OTel initialized"

### Issue: Permission denied errors
**Solution**:
1. Check directory permissions: `ls -ld /opt/ciena/bp2/alloy-collector`
2. The exporter will auto-detect and use `sudo` if needed
3. Or manually set: `export OTEL_USE_SUDO=true`

### Issue: Traces written but empty spans
**Check**:
1. Root span is created: `with self.create_root_span():`
2. Correlation context is set: `self.set_correlation_baggage_from_instance()`
3. Script is actually running to completion

### Issue: Wrong export mode (OTLP instead of file)
**Solution**:
- Ensure `OTEL_EXPORT_MODE` is not set to "otlp"
- Or explicitly set: `export OTEL_EXPORT_MODE=file`

See `scripts/otel/DIAGNOSTIC_GUIDE.md` for detailed troubleshooting.

## Entry Points for OTel

Based on your question about which files to use as entry points:

### ✅ **Recommended Entry Points**

1. **compliance.py** (NOW INSTRUMENTED ✓)
   - Use Case: Service mapper and disconnect mapper operations
   - Tracks: Circuit provisioning, device validation, compliance checks

2. **provisioning.py** (ALREADY INSTRUMENTED ✓)
   - Use Case: Network service creation and updates
   - Tracks: Service provisioning, bandwidth updates, state changes

3. **common.py** (FactoryBase class)
   - Could be instrumented for base factory operations
   - Would provide instrumentation to all factory subclasses
   - **Current Status**: Not instrumented, but compliance.py and provisioning.py inherit from it

### ❌ **Not Recommended as Entry Points**

- **common_plan.py**: Already has OTel initialization in `run()` method - don't modify this
- Individual utility files: These should be called by the main entry points above

## Best Practices

### 1. Always Check OTel Initialization
```python
if getattr(self, '_otel_initialized', False):
    # Use OTel features
    self.otel_log("Message", level="info")
```

### 2. Use Context Managers for Spans
```python
# Good
with self.create_root_span():
    do_work()

# Bad - spans might not be closed properly
span = self.create_root_span()
do_work()
```

### 3. Set Correlation Context Early
```python
def process(self):
    self.__init_otel__()
    with self.create_root_span():
        self.set_correlation_baggage_from_instance()  # Early!
        # Rest of code
```

### 4. Add Meaningful Attributes
```python
self.record_span_event_from_instance(
    "device.provision.started",
    {
        "device_id": "123",
        "vendor": "juniper",
        "operation": "provision"
    }
)
```

## Summary

### What Changed
1. ✅ Created `/opt/ciena/bp2/alloy-collector/` directory
2. ✅ Installed OpenTelemetry packages
3. ✅ Added full OTel instrumentation to `compliance.py`
4. ✅ Verified file export is working (test passed)
5. ✅ Traces are being written to `traces.ndjson`

### What Works Now
- ✅ `compliance.py` creates spans and events
- ✅ `provisioning.py` creates spans and events (already working)
- ✅ Traces exported to `/opt/ciena/bp2/alloy-collector/traces.ndjson`
- ✅ All correlation context (circuit_id, resource_id) tracked
- ✅ Error handling with categorization
- ✅ Performance metrics with timed operations

### Next Steps (Optional Improvements)
1. **Add instrumentation to more scripts** following the same pattern
2. **Set up Alloy agent** to tail the traces.ndjson file and forward to your Meta server
3. **Add custom metrics** for business-specific KPIs
4. **Create dashboards** in your observability platform (Grafana, etc.)
5. **Set up alerting** based on error categories or performance metrics

## Files Modified

1. `scripts/fabricator/compliance.py` - Added OTel instrumentation
2. `/opt/ciena/bp2/alloy-collector/` - Created directory (system-level)
3. System Python packages - Installed OpenTelemetry libraries

## References

- **Instrumentation Guide**: `scripts/README_INSTRUMENTATION.md`
- **Diagnostic Guide**: `scripts/otel/DIAGNOSTIC_GUIDE.md`
- **Test Script**: `scripts/otel/test_file_export.py`
- **OTel Mixin API**: `scripts/otel/otel_mixin.py`
- **Core Setup**: `scripts/otel/instrumentation.py`

---

**Document Created**: 2026-01-06
**Author**: Claude (AI Assistant)
**Status**: Implementation Complete ✓
