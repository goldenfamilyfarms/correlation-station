# Adding OpenTelemetry Instrumentation to MDSO Scripts

## Overview

The `model-definitions` directory contains MDSO (Multi-Domain Service Orchestration) scripts that provision and manage network services. This guide explains the instrumentation architecture and how to add OpenTelemetry (OTel) instrumentation to new scripts.

## Directory Structure

```
model-definitions/
├── scripts/
│   ├── otel/          # Core instrumentation modules
│   │   ├── instrumentation.py         # Main setup and utility functions
│   │   ├── otel_mixin.py             # Mixin class for easy integration
│   │   ├── otel_mdso_utils.py        # MDSO-specific span helpers
│   │   ├── metrics.py                # Metrics collection
│   │   ├── feature_flags.py          # Feature flag management
│   │   ├── requirements.txt          # OTel dependencies
│   │   └── DIAGNOSTIC_GUIDE.md       # Troubleshooting guide
│   ├── networkservice/               # Network service scripts
│   ├── serviceMapper/                # Service mapping scripts
│   ├── deviceReset/                  # Device reset scripts
│   └── [other script modules]/
├── scripts.d/                        # TOML configuration files
└── requirements_*.txt                # Module-specific dependencies
```

## Core Instrumentation Components

### 1. `instrumentation.py` - Main Setup Module

**Purpose**: Provides standalone functions for OTel setup and utilities.

**Key Functions**:
- `setup_otel()`: Initializes OTel tracer with file-based or OTLP export
- `get_otel_logger()`: Creates structured logger with trace context
- `inject_correlation_context()`: Sets correlation keys (circuit_id, resource_id, etc.)
- `mdso_span`: Context manager for creating spans
- `test_file_export()`: Diagnostic function for troubleshooting

**Export Modes**:
- **File-based** (default): Writes traces to `/opt/ciena/bp2/alloy-collector/traces.ndjson` for isolated containers
- **OTLP**: Direct export to Alloy agent at `localhost:4318`

### 2. `otel_mixin.py` - Mixin Class

**Purpose**: Non-invasive mixin that adds OTel capabilities to existing CommonPlan classes.

**Key Methods**:
- `__init_otel__()`: Initialize OTel (call once at start of `process()`)
- `create_root_span()`: Create root span for entire operation
- `otel_log()`: Dual logging (standard + structured)
- `otel_error_handler()`: Error handling with categorization
- `create_topology_span_context()`: Context manager for Beorn topology operations
- `create_network_function_span_context()`: Context manager for device operations
- `set_correlation_baggage_from_instance()`: Auto-extract correlation keys from instance

**Usage Pattern**:
```python
class MyScript(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span():
            # Your code here
            pass
```

### 3. `otel_mdso_utils.py` - MDSO Helpers

**Purpose**: MDSO-specific span creation and attribute helpers.

**Key Classes**:
- `MDSOSpanHelper`: Creates topology and network function spans
- `ErrorPatternMatcher`: Categorizes errors and extracts identifiers
- `MDSORegexPatterns`: Regex patterns for parsing logs/errors

**Key Functions**:
- `extract_vendor_from_node_name()`: Extract vendor from Beorn topology
- `extract_fqdn_from_node_name()`: Extract FQDN from Beorn topology
- `validate_beorn_response()`: Validate Beorn API responses

### 4. `metrics.py` - Metrics Collection

**Purpose**: Collects operation metrics (counters, histograms).

**Key Class**: `MDSOMetrics`
- Operation counters and durations
- Error counters
- Topology fetch metrics
- Network function operation metrics
- Device onboarding metrics
- Provisioning metrics

### 5. `feature_flags.py` - Feature Flag Management

**Purpose**: Controls OTel enablement via environment variables or class constants.

**Key Functions**:
- `is_otel_enabled()`: Check if OTel is enabled
- `is_otel_sampling_enabled()`: Check if sampling is enabled
- `get_otel_sampling_rate()`: Get sampling rate (0.0-1.0)

## Script Analysis

### Existing Instrumented Scripts

#### 1. `serviceMapper/serviceMapper.py` (Activate class)
- **Purpose**: Maps and validates service configurations across devices
- **Instrumentation**: 
  - Root span for entire process
  - Network function spans for each device
  - Topology context extraction
  - Device processing events

#### 2. `networkservice/networkservice.py` (Terminate, Update classes)
- **Purpose**: Network service lifecycle management
- **Instrumentation**:
  - Root spans for termination/update operations
  - Error handling with OTel error handler

#### 3. `deviceReset/deviceReset.py` (Activate class)
- **Purpose**: Resets device configurations
- **Instrumentation**:
  - Root span for reset operation
  - Device-specific attributes
  - Device count metrics

## How to Add Instrumentation to a New Script

### Step 1: Update Class Definition

Add `OTelMixin` to your class inheritance:

```python
from scripts.common_plan import CommonPlan
from scripts.otel.otel_mixin import OTelMixin

class MyNewScript(CommonPlan, OTelMixin):
    def process(self):
        # Step 2: Initialize OTel
        self.__init_otel__()
        
        # Step 3: Create root span
        with self.create_root_span():
            # Your existing code here
            pass
```

### Step 2: Initialize OTel

Call `__init_otel__()` at the start of your `process()` method:

```python
def process(self):
    self.__init_otel__()
    # ... rest of your code
```

### Step 3: Create Root Span

Wrap your main logic in a root span:

```python
def process(self):
    self.__init_otel__()
    with self.create_root_span():
        # Main processing logic
        self.do_work()
```

### Step 4: Add Correlation Context

If your script has `circuit_id`, `resource_id`, etc., set correlation baggage:

```python
def process(self):
    self.__init_otel__()
    with self.create_root_span():
        # Auto-extract from instance attributes
        self.set_correlation_baggage_from_instance()
        
        # Or manually set
        from scripts.otel.instrumentation import inject_correlation_context
        inject_correlation_context(
            circuit_id=self.circuit_id,
            resource_id=self.resource_id
        )
```

### Step 5: Add Operation-Specific Spans

For specific operations, create child spans:

```python
# For topology operations
with self.create_topology_span_context(circuit_id, "fetch") as span:
    topology = fetch_topology(circuit_id)
    self.add_topology_attributes_to_span(
        span=span,
        service_type="FIA",
        vendor="juniper",
        topology_node_count=len(topology["nodes"])
    )

# For device/network function operations
with self.create_network_function_span_context(tid, fqdn, "check") as span:
    result = check_device(tid)
    self.add_network_function_attributes_to_span(
        span=span,
        communication_state="reachable",
        vendor="adva",
        device_role="CPE"
    )
```

### Step 6: Add Error Handling

Use the OTel error handler for consistent error tracking:

```python
try:
    risky_operation()
except Exception as e:
    if getattr(self, '_otel_initialized', False):
        self.otel_error_handler(f"Operation failed: {e}", e)
    raise
```

### Step 7: Add Structured Logging

Replace standard logging with OTel logging:

```python
# Instead of:
self.logger.info("Processing started")

# Use:
self.otel_log("Processing started", level="info", circuit_id=self.circuit_id)
```

### Step 8: Add Metrics (Optional)

Record operation metrics:

```python
if getattr(self, '_otel_initialized', False):
    with self.timed_operation("my_operation", {"vendor": "juniper"}):
        # Operation code
        pass
```

## Complete Example

Here's a complete example of instrumenting a new script:

```python
"""Example: Instrumented Script"""
from scripts.common_plan import CommonPlan
from scripts.otel.otel_mixin import OTelMixin

class ProvisionDevice(CommonPlan, OTelMixin):
    """Provisions a network device"""
    
    def process(self):
        # Initialize OTel
        self.__init_otel__()
        
        # Create root span
        with self.create_root_span(operation_name="device_provision"):
            # Set correlation context
            self.set_correlation_baggage_from_instance()
            
            # Log start
            self.otel_log("Starting device provision", level="info")
            
            try:
                # Get device info
                device = self.get_device(self.device_tid)
                
                # Create span for topology fetch
                with self.create_topology_span_context(
                    self.circuit_id, 
                    "fetch"
                ) as topo_span:
                    topology = self.fetch_topology(self.circuit_id)
                    self.add_topology_attributes_to_span(
                        span=topo_span,
                        service_type=topology.get("service_type"),
                        vendor=device.vendor,
                        topology_node_count=len(topology.get("nodes", []))
                    )
                
                # Create span for device provisioning
                with self.create_network_function_span_context(
                    device.tid,
                    device.fqdn,
                    "provision"
                ) as nf_span:
                    self.add_network_function_attributes_to_span(
                        span=nf_span,
                        vendor=device.vendor,
                        device_role=device.role,
                        ip_address=device.ip_address
                    )
                    
                    # Record event
                    self.record_span_event_from_instance(
                        "device.provision.started",
                        {"tid": device.tid, "vendor": device.vendor}
                    )
                    
                    # Do provisioning
                    result = self.provision_device(device)
                    
                    # Record completion
                    self.record_span_event_from_instance(
                        "device.provision.completed",
                        {"tid": device.tid, "success": result.success}
                    )
                
                self.otel_log("Device provision completed", level="info")
                
            except Exception as e:
                # Use OTel error handler
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler(f"Provisioning failed: {e}", e)
                raise
```

## Configuration

### Environment Variables

Set these in your BluePlanet solution manager or script environment:

```bash
# Enable/disable OTel (default: true)
OTEL_ENABLED=true

# Export mode: "file" (default) or "otlp"
OTEL_EXPORT_MODE=file

# Trace log directory (file mode only)
OTEL_TRACE_LOG_DIR=/opt/ciena/bp2/alloy-collector

# Use sudo for file operations (auto-detected if not set)
OTEL_USE_SUDO=false

# OTLP endpoint (otlp mode only)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Environment
MDSO_ENV=dev  # or staging, prod
```

### Class Constants

You can also set constants on your class:

```python
class MyScript(CommonPlan, OTelMixin):
    OTEL_ENABLED = True
    OTEL_EXPORT_MODE = "file"
    OTEL_TRACE_LOG_DIR = "/opt/ciena/bp2/alloy-collector"
    MDSO_ENV = "prod"
```

### Requirements

Add OTel dependencies to your `requirements_*.txt`:

```txt
--index-url http://blueplanet/charter-pypi/simple/
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-http==1.20.0
structlog==23.2.0
```

Or reference the shared requirements:

```txt
-r scripts/otel/requirements.txt
```

## Best Practices

### 1. Always Initialize OTel First

```python
def process(self):
    self.__init_otel__()  # Always first
    with self.create_root_span():
        # Your code
```

### 2. Use Context Managers

Always use context managers for spans to ensure proper cleanup:

```python
# Good
with self.create_root_span():
    do_work()

# Bad
span = self.create_root_span()
do_work()  # Span might not be closed properly
```

### 3. Check Initialization Before Use

When using OTel features conditionally:

```python
if getattr(self, '_otel_initialized', False):
    self.otel_log("Message", level="info")
```

### 4. Set Correlation Context Early

Set correlation keys as soon as you have them:

```python
with self.create_root_span():
    self.set_correlation_baggage_from_instance()  # Early
    # Rest of code
```

### 5. Use Structured Logging

Include relevant context in logs:

```python
self.otel_log(
    "Processing device",
    level="info",
    tid=device.tid,
    vendor=device.vendor,
    operation="provision"
)
```

### 6. Handle Errors Consistently

Always use `otel_error_handler` for errors:

```python
try:
    risky_operation()
except Exception as e:
    if getattr(self, '_otel_initialized', False):
        self.otel_error_handler(f"Error: {e}", e)
    raise
```

### 7. Add Meaningful Attributes

Add attributes that help with debugging and correlation:

```python
span.set_attribute("device.vendor", vendor)
span.set_attribute("device.role", role)
span.set_attribute("operation.type", "provision")
```

## Troubleshooting

### Traces Not Appearing

1. **Check initialization**: Verify `__init_otel__()` is called
2. **Check export mode**: Ensure `OTEL_EXPORT_MODE=file` for isolated containers
3. **Check file permissions**: Verify `/opt/ciena/bp2/alloy-collector` is writable
4. **Run diagnostic**: Use `test_file_export()` function
5. **Check logs**: Look for FileSpanExporter logs in application logs

See `otel/DIAGNOSTIC_GUIDE.md` for detailed troubleshooting.

### Common Issues

**Issue**: `AttributeError: 'MyScript' object has no attribute '_otel_initialized'`
- **Solution**: Call `__init_otel__()` before using OTel features

**Issue**: Traces not appearing in Alloy
- **Solution**: Check export mode, file permissions, and Alloy configuration

**Issue**: Import errors
- **Solution**: Ensure OTel packages are in requirements file and installed

## Testing

### Manual Testing

1. Run your script in a test environment
2. Check that traces appear in `/opt/ciena/bp2/alloy-collector/traces.ndjson`
3. Verify spans have correct attributes
4. Check correlation keys are set correctly

### Diagnostic Script

Use the provided test script:

```bash
python scripts/otel/test_file_export.py
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   MDSO Script (Your Code)                │
│  class MyScript(CommonPlan, OTelMixin):                  │
│      def process(self):                                  │
│          self.__init_otel__()                            │
│          with self.create_root_span():                   │
│              # Your logic                                │
└──────────────────┬──────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              OTelMixin (otel_mixin.py)                   │
│  - __init_otel__()                                       │
│  - create_root_span()                                    │
│  - otel_log()                                            │
│  - otel_error_handler()                                  │
└──────────────────┬──────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│         instrumentation.py (Core Setup)                  │
│  - setup_otel() → Creates tracer                         │
│  - FileSpanExporter → Writes to file                     │
│  - OTLPSpanExporter → Sends to Alloy                     │
└──────────────────┬──────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│ File Export  │      │  OTLP Export      │
│ (Default)    │      │  (Direct)        │
│              │      │                   │
│ /opt/ciena/  │      │ localhost:4318    │
│ bp2/alloy-   │      │                   │
│ collector/   │      │                   │
│ traces.ndjson│      │                   │
└──────┬───────┘      └────────┬──────────┘
       │                       │
       └───────────┬───────────┘
                   │
                   ▼
         ┌──────────────────┐
         │   Alloy Agent    │
         │  (Tails file or  │
         │   receives OTLP) │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   Meta Server    │
         │  (Correlation    │
         │   Engine)        │
         └──────────────────┘
```

## Summary

1. **Inherit from OTelMixin**: `class MyScript(CommonPlan, OTelMixin)`
2. **Initialize**: Call `self.__init_otel__()` at start of `process()`
3. **Create root span**: Wrap main logic in `with self.create_root_span():`
4. **Set correlation**: Call `self.set_correlation_baggage_from_instance()`
5. **Add operation spans**: Use context managers for specific operations
6. **Handle errors**: Use `self.otel_error_handler()` for exceptions
7. **Use structured logging**: Replace standard logs with `self.otel_log()`

For more details, see:
- `otel/DIAGNOSTIC_GUIDE.md` - Troubleshooting
- `otel/instrumentation.py` - API reference
- `otel/otel_mixin.py` - Mixin methods
