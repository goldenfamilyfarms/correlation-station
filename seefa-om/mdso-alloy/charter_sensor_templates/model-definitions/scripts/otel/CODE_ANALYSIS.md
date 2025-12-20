# Detailed Code Analysis: otel Directory

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Module-by-Module Analysis](#module-by-module-analysis)
3. [Step-by-Step Code Flow](#step-by-step-code-flow)
4. [Usage Patterns](#usage-patterns)
5. [Integration Examples](#integration-examples)

---

## Architecture Overview

The `otel` directory provides a comprehensive OpenTelemetry (OTel) instrumentation framework for MDSO scripts. It's designed with:

- **Graceful Degradation**: Works even if OTel packages aren't installed
- **Dual Export Modes**: File-based (for isolated containers) and OTLP (direct export)
- **Non-Invasive Design**: Mixin pattern allows easy integration without breaking existing code
- **Correlation Support**: Automatic correlation key propagation across services
- **Error Categorization**: Intelligent error pattern matching and categorization

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Script (CommonPlan)                  │
│  class MyScript(CommonPlan, OTelMixin):                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    otel_mixin.py                             │
│  - __init_otel__() → Initializes OTel                       │
│  - create_root_span() → Creates root span                    │
│  - otel_log() → Dual logging                                │
│  - otel_error_handler() → Error handling                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│ instrumentation.py│          │ otel_mdso_utils.py│
│  - setup_otel()   │          │  - MDSOSpanHelper │
│  - FileSpanExporter│          │  - ErrorMatcher   │
│  - get_otel_logger()│         │  - RegexPatterns  │
└──────────────────┘          └──────────────────┘
        │                               │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│   metrics.py     │          │ feature_flags.py │
│  - MDSOMetrics   │          │  - is_otel_enabled│
│  - setup_metrics()│         │  - Sampling       │
└──────────────────┘          └──────────────────┘
```

---

## Module-by-Module Analysis

### 1. `instrumentation.py` - Core Setup and Utilities

**Purpose**: Provides the foundational OTel setup functions and file-based export capability.

#### Key Components

##### A. Configuration Helper (`_get_otel_config`)

```python
def _get_otel_config(key: str, default_value=None, instance=None):
```

**Step-by-Step Logic**:
1. **Priority 1**: Check instance attributes (e.g., `self.OTEL_EXPORT_MODE`)
2. **Priority 2**: Check class attributes (e.g., `MyClass.OTEL_EXPORT_MODE`)
3. **Priority 3**: Check environment variables (e.g., `os.getenv("OTEL_EXPORT_MODE")`)
4. **Priority 4**: Return default value

**Why This Design?**
- Allows per-class configuration (useful for different script types)
- Falls back gracefully if constants aren't set
- Supports both programmatic and environment-based configuration

##### B. FileSpanExporter Class

**Purpose**: Writes traces to a file when containers can't reach Alloy agent directly.

**Initialization Flow** (`__init__`):
```
1. Store file path
2. Determine if sudo is needed:
   a. Check OTEL_USE_SUDO config
   b. If not set, auto-detect by checking directory write permissions
   c. Try creating directory to test permissions
3. Create directory if it doesn't exist (with sudo if needed)
4. Log directory permissions for debugging
5. Open file handle (if not using sudo) or prepare for sudo writes
```

**Export Flow** (`export` method):
```
1. Check if spans list is empty → return SUCCESS
2. Get file size before write (for verification)
3. If using sudo:
   a. Convert all spans to JSON lines
   b. Combine into single content string
   c. Use `sudo tee -a` to append to file
   d. Verify file size increased
4. If not using sudo:
   a. Check if file handle is open (reopen if needed)
   b. For each span:
      - Convert to OTLP-compatible dict via `_span_to_dict()`
      - Serialize to JSON
      - Write as single line (NDJSON format)
   c. Flush file handle
   d. Verify file size increased
5. Handle PermissionError → fallback to sudo
6. Return SUCCESS or FAILURE
```

**Span Conversion** (`_span_to_dict`):
- Extracts trace_id, span_id (formatted as hex)
- Converts attributes to JSON-serializable types
- Includes resource attributes
- Adds events with timestamps
- Creates OTLP-compatible structure

##### C. Main Setup Function (`setup_otel`)

**Step-by-Step Execution**:

```python
def setup_otel(service_name, endpoint, environment, version, 
               use_file_export, trace_log_dir, instance):
```

**Flow**:
1. **Check OTel Availability**
   - If not available, return None (graceful degradation)

2. **Determine Export Mode**
   ```
   if use_file_export is None:
       - Check OTEL_EXPORT_MODE env var/constant
       - If "file" → use_file_export = True
       - If "otlp" → use_file_export = False
       - If not set → default to True (file mode, safe for isolated containers)
   ```

3. **Create Resource**
   ```python
   Resource.create({
       "service.name": service_name,      # e.g., "mdso.servicemapper"
       "service.version": version,         # e.g., "1.0.0"
       "deployment.environment": environment,  # "dev", "staging", "prod"
       "telemetry.sdk.name": "opentelemetry",
       "telemetry.sdk.language": "python",
       "telemetry.sdk.version": "1.20.0"
   })
   ```

4. **Create TracerProvider**
   - Wraps the resource
   - Will hold span processors

5. **Create Span Processor** (two paths):

   **Path A: File Export Mode**
   ```
   a. Determine trace log directory:
      - From trace_log_dir parameter
      - Or OTEL_TRACE_LOG_DIR config
      - Or default: /opt/ciena/bp2/alloy-collector
   
   b. Build file path: {trace_log_dir}/traces.ndjson
   
   c. Check if sudo needed:
      - From OTEL_USE_SUDO config
      - Or auto-detect from permissions
   
   d. Create FileSpanExporter:
      - Passes file path, sudo flag, instance
      - Exporter handles directory creation, file opening
   
   e. Create BatchSpanProcessor:
      - max_queue_size=2048 (spans queued before export)
      - max_export_batch_size=512 (spans per batch)
      - schedule_delay_millis=5000 (export every 5 seconds)
   ```

   **Path B: OTLP Export Mode**
   ```
   a. Determine endpoint:
      - From endpoint parameter
      - Or OTEL_EXPORTER_OTLP_ENDPOINT config
      - Or default: http://localhost:4318
   
   b. Create OTLPSpanExporter:
      - Endpoint: {endpoint}/v1/traces
      - Timeout: 30 seconds
   
   c. Create BatchSpanProcessor (same config as file mode)
   ```

6. **Attach Processor to Provider**
   - `provider.add_span_processor(processor)`

7. **Set Global Tracer Provider**
   - `trace.set_tracer_provider(provider)`
   - Makes tracer available globally via `trace.get_tracer()`

8. **Verify File Writable** (file mode only)
   - Try writing empty string to verify permissions

9. **Return Tracer**
   - `trace.get_tracer(__name__)`

##### D. Correlation Context Functions

**`inject_correlation_context`**:
```
1. Get current span (if exists)
2. Set span attributes (circuit_id, resource_id, etc.)
3. Set baggage (for cross-service propagation):
   - Uses OpenTelemetry baggage API
   - Attaches to current context
4. Set structlog contextvars (for automatic log inclusion)
5. Return dictionary of injected context
```

**`extract_correlation_context`**:
```
1. Extract from baggage (OTel propagation mechanism)
2. Also check structlog contextvars (local context)
3. Merge (baggage takes precedence)
4. Return dictionary
```

**`clear_correlation_context`**:
```
1. Clear all baggage keys (set to None)
2. Clear structlog contextvars
```

##### E. Span Creation Helpers

**`create_mdso_span`**:
- Creates span with `mdso.component="scriptplan"` attribute
- Merges additional attributes
- Returns started span (must call `.end()` manually)

**`mdso_span` Context Manager**:
```python
class mdso_span:
    def __enter__(self):
        # Create span
        # Return span
    def __exit__(self, exc_type, exc_val, exc_tb):
        # If exception → set status to ERROR
        # If no exception → set status to OK
        # Always call span.end()
```

**Usage**:
```python
with mdso_span("operation.name", circuit_id="123") as span:
    # span is automatically ended and status set
    pass
```

##### F. Structured Logger (`get_otel_logger`)

**Configuration**:
```python
structlog.configure(
    processors=[
        merge_contextvars,      # Merge contextvars (circuit_id, etc.)
        add_trace_context,      # Add trace_id, span_id, baggage
        add_log_level,          # Add log level
        TimeStamper(fmt="iso"), # Add ISO timestamp
        JSONRenderer()          # Output as JSON
    ]
)
```

**`add_trace_context` Processor**:
```
1. Get current span
2. Extract trace_id, span_id, trace_flags (format as hex)
3. Extract baggage keys (circuit_id, resource_id, etc.)
4. Add all to event_dict
5. Return enhanced event_dict
```

**Result**: Every log automatically includes:
- `trace_id`: Current trace ID
- `span_id`: Current span ID
- `circuit_id`: From baggage/contextvars
- `resource_id`: From baggage/contextvars
- Plus any additional context passed to log call

##### G. Diagnostic Function (`test_file_export`)

**Purpose**: Test if file-based export is working.

**Flow**:
```
1. Determine trace log file path
2. Check if parent directory exists (create if needed)
3. Check if file exists (get size if exists)
4. Test file writability (try opening in append mode)
5. Create test tracer with file export
6. Create test span with attributes
7. Force flush span processor
8. Check if file size increased
9. Return result dictionary with:
   - success: bool
   - file_path: str
   - file_exists: bool
   - file_writable: bool
   - file_size: int
   - test_span_written: bool
   - error: str (if any)
```

---

### 2. `otel_mixin.py` - Mixin Class for Easy Integration

**Purpose**: Provides OTel capabilities as a mixin that can be added to any CommonPlan class.

#### Initialization (`__init_otel__`)

**Step-by-Step**:
```
1. Check feature flag:
   - Call is_otel_enabled(self)
   - If disabled → set _otel_initialized = False, return

2. Prevent double initialization:
   - If _otel_initialized already True → return

3. Determine service name:
   - Get class name (e.g., "ServiceMapper")
   - Format: f"mdso.{class_name.lower()}" → "mdso.servicemapper"

4. Determine environment:
   - Check class constant: MyClass.MDSO_ENV
   - Check instance attribute: self.MDSO_ENV
   - Check instance attribute: self.environment
   - Check env var: MDSO_ENV
   - Default: "dev"

5. Setup OTel tracer:
   - Call setup_otel(service_name, environment, instance=self)
   - Pass self to allow access to class constants

6. Setup structured logger:
   - Call get_otel_logger(service_name)

7. Initialize helpers:
   - self.span_helper = MDSOSpanHelper()
   - self.error_matcher = ErrorPatternMatcher()

8. Initialize metrics:
   - self.metrics = MDSOMetrics(service_name)

9. Mark as initialized:
   - self._otel_initialized = True
```

#### Root Span Creation (`create_root_span`)

**Flow**:
```
1. Check if initialized:
   - If not → call __init_otel__() first

2. If still not initialized:
   - Return nullcontext() (no-op context manager)

3. Determine span name:
   - Use operation_name parameter if provided
   - Or default: f"mdso.product.{class_name}"

4. Extract correlation context from instance:
   - Check self.circuit_id
   - Check self.resource_id
   - Check self.product_id

5. Inject correlation context:
   - Call inject_correlation_context(**correlation_attrs)

6. Create span context:
   - Call mdso_span(name=span_name, **correlation_attrs)
   - Returns context manager

7. Return context manager
```

**Usage**:
```python
with self.create_root_span():
    # All code here is automatically traced
    # Span is automatically ended and status set
    pass
```

#### Dual Logging (`otel_log`)

**Flow**:
```
1. Standard logging (existing behavior):
   - If hasattr(self, 'logger'):
       getattr(self.logger, level)(message)

2. Structured OTel logging (new):
   - If initialized and has otel_logger:
     a. Extract correlation context
     b. Merge with provided context
     c. Call otel_logger.{level}(message, **merged_context)
     d. Add span event with log details
```

**Result**: Logs appear in both:
- Standard logger (existing behavior preserved)
- Structured OTel logger (with trace context)

#### Error Handling (`otel_error_handler`)

**Flow**:
```
1. Categorize error:
   - Call error_matcher.categorize_error(error_message)
   - Returns: {"category": "...", "type": "..."}

2. Extract identifiers:
   - Call error_matcher.extract_all_identifiers(error_message)
   - Returns: {"circuit_id": "...", "tid": "...", etc.}

3. Get current span:
   - trace.get_current_span()

4. Add error attributes to span:
   - error.category
   - error.message (truncated to 500 chars)
   - error.{identifier} for each extracted identifier

5. Set span status to ERROR:
   - span.set_status(trace.Status(trace.StatusCode.ERROR, error_message))

6. Log error:
   - Call self.otel_log() with error details

7. Standard error logging:
   - self.logger.error(error_message, exc_info=exception)
```

#### Topology Span Context (`create_topology_span_context`)

**Flow**:
```
1. Check if initialized → return nullcontext if not

2. Create topology span:
   - Call span_helper.create_topology_span(tracer, circuit_id, operation)
   - Returns started span

3. Create context manager:
   - Yields span
   - Always calls span.end() in finally

4. Return context manager
```

**Usage**:
```python
with self.create_topology_span_context("123-456", "fetch") as span:
    topology = fetch_topology()
    self.add_topology_attributes_to_span(
        span=span,
        service_type="FIA",
        vendor="juniper"
    )
```

#### Network Function Span Context (`create_network_function_span_context`)

**Similar to topology span, but for device operations.**

#### Correlation Baggage from Instance (`set_correlation_baggage_from_instance`)

**Flow**:
```
1. Extract from instance attributes:
   - circuit_id = getattr(self, 'circuit_id', None)
   - resource_id = getattr(self, 'resource_id', None)
   - tid = getattr(self, 'tid', None)
   - fqdn = getattr(self, 'fqdn', None)
   - provider_resource_id = getattr(self, 'provider_resource_id', None)

2. Also check resource properties:
   - If hasattr(self, 'resource'):
       - Try resource['properties']['circuit_id']
       - Try resource['id']

3. Call span_helper.set_correlation_baggage(**extracted)
```

#### Timed Operation (`timed_operation`)

**Purpose**: Context manager that records operation duration as metrics.

**Flow**:
```
1. Record start time
2. Yield (execute operation)
3. Calculate duration_ms
4. Record metrics:
   - metrics.record_operation(operation_name, attributes)
   - metrics.record_operation_duration(operation_name, duration_ms, attributes)
5. Record span event with duration
```

**Usage**:
```python
with self.timed_operation("device.provision", {"vendor": "juniper"}):
    provision_device()
    # Duration automatically recorded
```

---

### 3. `otel_mdso_utils.py` - MDSO-Specific Helpers

#### MDSOSpanHelper Class

**Purpose**: Provides MDSO-specific span creation and attribute helpers.

##### `create_topology_span`

**Flow**:
```
1. Start span: tracer.start_span(f"beorn.topology.{operation}")
2. Set attributes:
   - mdso.circuit_id = circuit_id
   - beorn.operation = operation
3. Return span
```

##### `create_network_function_span`

**Flow**:
```
1. Start span: tracer.start_span(f"network_function.{operation}")
2. Set attributes:
   - network.device.tid = tid
   - network.device.fqdn = fqdn (if provided)
3. Return span
```

##### `add_topology_attributes`

**Flow**:
```
1. If service_type:
   - Set beorn.service_type attribute
   - Set serviceType baggage

2. If vendor:
   - Set network.device.vendor attribute (lowercase)
   - Look up resource type from VENDOR_RESOURCE_MAPPING
   - Set network.device.resource_type attribute

3. If fqdn:
   - Set network.device.fqdn attribute

4. If topology_node_count:
   - Set beorn.topology.node_count attribute

5. If validation_status:
   - Set beorn.topology.validation_passed attribute
```

##### `add_network_function_attributes`

**Similar pattern, sets device-specific attributes.**

##### `set_correlation_baggage`

**Flow**:
```
For each provided identifier:
  - Call baggage.set_baggage("mdso.{key}", value)
  - Or baggage.set_baggage("network.device.{key}", value)
```

**Correlation Chain**:
- `circuit_id` → `fqdn` → `provider_resource_id`
- Each level adds more context for cross-service tracing

#### ErrorPatternMatcher Class

**Purpose**: Categorizes errors and extracts identifiers from error messages.

##### `extract_all_identifiers`

**Flow**:
```
1. Use MDSORegexPatterns to extract:
   - circuit_id (from CIRCUIT_ID pattern)
   - tid (from TID pattern)
   - resource_id (from RESOURCE_ID pattern - UUID)
   - fqdn (from FQDN pattern)
   - ipv4 (from IPV4 pattern)

2. Return dictionary with all found identifiers
```

##### `categorize_error`

**Flow**:
```
1. Check error message against patterns:
   - NOT_IPV4_IPV6 → IP_VALIDATION_ERROR
   - NOT_NETWORK_ADDRESS → IP_VALIDATION_ERROR
   - IP_EXISTS → IP_CONFLICT_ERROR
   - DEVICE_CPE_ROLE_INVALID → DEVICE_ROLE_ERROR
   - DEVICE_PE_ROLE_INVALID → DEVICE_ROLE_ERROR
   - NODE_NAME_INVALID → NODE_ERROR
   - "GRANITE DESIGN" → GRANITE_ERROR
   - "unable to connect" → CONNECTIVITY_ERROR

2. Return {"category": "...", "type": "..."}
3. Default: {"category": "UNKNOWN_ERROR", "type": "Uncategorized"}
```

#### MDSORegexPatterns Class

**Purpose**: Comprehensive regex patterns for MDSO log parsing.

**Patterns Include**:
- Port patterns: ET, GE, XE, ETH_PORT, LAG, AE
- Interface patterns: TPE_FP, TPE_ACCESS, ACCESS, FP, etc.
- Core identifiers: RESOURCE_ID (UUID), IPV4, IPV6, TID, CIRCUIT_ID, FQDN
- Error patterns: IP validation, device role, connectivity errors

**Class Methods**:
- `extract_circuit_id(text)` → Uses CIRCUIT_ID pattern
- `extract_tid(text)` → Uses TID pattern
- `extract_resource_id(text)` → Uses RESOURCE_ID pattern
- `extract_fqdn(text)` → Uses FQDN pattern
- `extract_ipv4(text)` → Uses IPV4 pattern

#### Topology Helpers

**`extract_vendor_from_node_name`**:
```
1. Check if node_name_list has at least 3 elements
2. Get node_name_list[2]["value"] (vendor is at index 2)
3. Return lowercase vendor name
```

**`extract_fqdn_from_node_name`**:
```
1. Check if node_name_list has at least 7 elements
2. Get node_name_list[6]["value"] (FQDN is at index 6)
3. Return FQDN
```

**`validate_beorn_response`**:
```
1. Check if data is dict
2. Count elements: len(data)
3. Return True if >= 8 elements (healthy response)
```

---

### 4. `metrics.py` - Metrics Collection

#### Setup Function (`setup_metrics`)

**Flow**:
```
1. Check if already initialized → return existing meter

2. Create resource:
   - service.name, service.version, deployment.environment

3. Determine endpoint:
   - Check OTEL_EXPORTER_OTLP_METRICS_ENDPOINT
   - Fall back to OTEL_EXPORTER_OTLP_ENDPOINT
   - Default: http://localhost:4318

4. Create metric exporter:
   - OTLPMetricExporter(endpoint="{endpoint}/v1/metrics")

5. Create metric reader:
   - PeriodicExportingMetricReader(exporter, export_interval_millis=60000)
   - Exports every 60 seconds

6. Create meter provider:
   - MeterProvider(resource, metric_readers=[reader])

7. Set global meter provider

8. Create and return meter
```

#### MDSOMetrics Class

**Initialization**:
```
1. Get meter (via get_meter())
2. Create counters and histograms:
   - operation_counter: mdso.operation.count
   - operation_duration: mdso.operation.duration (histogram)
   - error_counter: mdso.error.count
   - topology_fetch_counter: mdso.topology.fetch.count
   - topology_fetch_duration: mdso.topology.fetch.duration
   - network_function_operation_counter: mdso.network_function.operation.count
   - network_function_operation_duration: mdso.network_function.operation.duration
   - device_onboard_counter: mdso.device.onboard.count
   - device_onboard_duration: mdso.device.onboard.duration
   - provisioning_counter: mdso.provisioning.count
   - provisioning_duration: mdso.provisioning.duration
   - service_type_counter: mdso.service_type.count
   - vendor_counter: mdso.vendor.operation.count
```

**Methods**:
- `record_operation(name, attributes)` → Increment counter
- `record_operation_duration(name, duration_ms, attributes)` → Record histogram
- `record_error(category, attributes)` → Increment error counter
- `record_topology_fetch(circuit_id, duration_ms)` → Record topology metrics
- `record_network_function_operation(...)` → Record device operation metrics
- `record_device_onboard(vendor, duration_ms, success)` → Record onboarding
- `record_provisioning(service_type, context, duration_ms, device_count)` → Record provisioning
- `record_vendor_operation(vendor, operation)` → Record vendor-specific operation

---

### 5. `feature_flags.py` - Feature Flag Management

#### Configuration Helper (`_get_config_value`)

**Same pattern as `_get_otel_config` in instrumentation.py**:
1. Check instance attribute
2. Check class attribute
3. Check environment variable
4. Return default

#### Feature Flag Functions

**`is_otel_enabled(instance=None)`**:
```
1. Get OTEL_ENABLED config value (default: "true")
2. Convert to boolean:
   - If already bool → return as-is
   - If string → check if "true" (case-insensitive)
3. Return bool
```

**`is_otel_sampling_enabled(instance=None)`**:
```
Same pattern, checks OTEL_SAMPLING_ENABLED (default: "true")
```

**`get_otel_sampling_rate(instance=None)`**:
```
1. Get OTEL_SAMPLING_RATE config value (default: "1.0")
2. Convert to float
3. Return float (0.0 to 1.0)
```

---

## Step-by-Step Code Flow

### Example: Instrumenting a New Script

#### Step 1: Class Definition
```python
from scripts.common_plan import CommonPlan
from scripts.otel.otel_mixin import OTelMixin

class MyScript(CommonPlan, OTelMixin):
    pass
```

#### Step 2: Initialize in process() Method
```python
def process(self):
    self.__init_otel__()  # Step 2
```

**What Happens**:
1. `__init_otel__()` checks feature flag
2. Determines service name: "mdso.myscript"
3. Determines environment: "dev" (or from config)
4. Calls `setup_otel("mdso.myscript", environment="dev", instance=self)`
5. `setup_otel()`:
   - Checks OTEL_EXPORT_MODE (defaults to file mode)
   - Creates Resource with service metadata
   - Creates TracerProvider
   - Creates FileSpanExporter (or OTLPSpanExporter)
   - Creates BatchSpanProcessor
   - Attaches processor to provider
   - Sets global tracer provider
   - Returns tracer
6. Creates structured logger
7. Initializes helpers (span_helper, error_matcher, metrics)
8. Sets `_otel_initialized = True`

#### Step 3: Create Root Span
```python
def process(self):
    self.__init_otel__()
    with self.create_root_span():  # Step 3
        # Your code
```

**What Happens**:
1. `create_root_span()` checks if initialized (calls `__init_otel__()` if not)
2. Extracts correlation context from `self.circuit_id`, `self.resource_id`, etc.
3. Calls `inject_correlation_context(**attrs)`:
   - Sets span attributes
   - Sets baggage
   - Sets structlog contextvars
4. Creates `mdso_span` context manager:
   - Starts span with name "mdso.product.MyScript"
   - Sets attributes from correlation context
5. Returns context manager
6. When context exits:
   - Sets span status (OK or ERROR)
   - Calls `span.end()`
   - Span is queued for export

#### Step 4: Add Operation Spans
```python
with self.create_topology_span_context("123-456", "fetch") as span:
    topology = fetch_topology()
    self.add_topology_attributes_to_span(span, service_type="FIA")
```

**What Happens**:
1. `create_topology_span_context()`:
   - Calls `span_helper.create_topology_span(tracer, "123-456", "fetch")`
   - Creates span named "beorn.topology.fetch"
   - Sets `mdso.circuit_id` and `beorn.operation` attributes
   - Returns context manager
2. Inside context:
   - Span is active (child of root span)
   - All logs automatically include trace_id, span_id
3. `add_topology_attributes_to_span()`:
   - Sets `beorn.service_type="FIA"`
   - Sets `beorn.serviceType` baggage
   - Sets vendor, fqdn, node_count, validation_status if provided
4. When context exits:
   - `span.end()` is called
   - Span is queued for export

#### Step 5: Error Handling
```python
try:
    risky_operation()
except Exception as e:
    self.otel_error_handler(f"Operation failed: {e}", e)
    raise
```

**What Happens**:
1. `otel_error_handler()`:
   - Calls `error_matcher.categorize_error(error_message)`
   - Calls `error_matcher.extract_all_identifiers(error_message)`
   - Gets current span
   - Adds error attributes:
     - `error.category`
     - `error.message` (truncated)
     - `error.circuit_id`, `error.tid`, etc. (from extracted identifiers)
   - Sets span status to ERROR
   - Calls `self.otel_log()` with error details
   - Calls standard `self.logger.error()`

#### Step 6: Span Export

**File Mode**:
1. BatchSpanProcessor collects spans
2. Every 5 seconds (or when queue is full):
   - Calls `FileSpanExporter.export(spans)`
   - Converts spans to JSON lines
   - Writes to `/opt/ciena/bp2/alloy-collector/traces.ndjson`
   - Alloy agent tails the file
   - Alloy forwards to Meta Server

**OTLP Mode**:
1. BatchSpanProcessor collects spans
2. Every 5 seconds (or when queue is full):
   - Calls `OTLPSpanExporter.export(spans)`
   - Sends HTTP POST to `localhost:4318/v1/traces`
   - Alloy agent receives traces
   - Alloy forwards to Meta Server

---

## Usage Patterns

### Pattern 1: Basic Instrumentation (Minimum)

```python
class MyScript(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span():
            # Your code here
            pass
```

**What You Get**:
- Root span for entire operation
- Automatic correlation context extraction
- Structured logging with trace context
- Error handling with categorization

### Pattern 2: With Operation Spans

```python
class MyScript(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span():
            self.set_correlation_baggage_from_instance()
            
            # Topology operation
            with self.create_topology_span_context(self.circuit_id, "fetch") as span:
                topology = fetch_topology()
                self.add_topology_attributes_to_span(
                    span=span,
                    service_type=topology.get("service_type"),
                    vendor="juniper"
                )
            
            # Device operation
            with self.create_network_function_span_context(device.tid, device.fqdn) as span:
                result = check_device(device.tid)
                self.add_network_function_attributes_to_span(
                    span=span,
                    communication_state="reachable",
                    vendor=device.vendor
                )
```

**What You Get**:
- Hierarchical span structure (root → topology → device)
- Detailed attributes for each operation
- Automatic correlation between spans

### Pattern 3: With Metrics

```python
class MyScript(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span():
            # Time an operation
            with self.timed_operation("device.provision", {"vendor": "juniper"}):
                provision_device()
                # Duration automatically recorded
            
            # Manual metrics
            self.metrics.record_operation("custom.operation", {"type": "special"})
```

**What You Get**:
- Operation duration metrics
- Custom operation counters
- Metrics exported to OTLP endpoint

### Pattern 4: Standalone Functions (No Mixin)

```python
from scripts.otel.instrumentation import (
    setup_otel,
    mdso_span,
    inject_correlation_context
)

# Setup
tracer = setup_otel("my-service", environment="dev")

# Use
with mdso_span("my.operation", circuit_id="123") as span:
    inject_correlation_context(circuit_id="123", resource_id="456")
    # Your code
```

**What You Get**:
- Same functionality without inheriting from OTelMixin
- Useful for utility scripts or standalone functions

### Pattern 5: Error Handling

```python
class MyScript(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span():
            try:
                risky_operation()
            except Exception as e:
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler(f"Operation failed: {e}", e)
                raise
```

**What You Get**:
- Automatic error categorization
- Identifier extraction from error messages
- Error attributes on span
- Error metrics recorded

---

## Integration Examples

### Example 1: Service Mapper (Existing)

```python
class Activate(Common, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span():
            self.set_correlation_baggage_from_instance()
            
            # Extract topology context
            if getattr(self, '_otel_initialized', False):
                self.extract_and_set_topology_context(
                    self.circuit_details["properties"]
                )
            
            for device_data in topology_devices:
                device = Device(device_data)
                
                with self.create_network_function_span_context(
                    device.tid,
                    fqdn=device.fqdn,
                    operation="validate_and_remediate"
                ) as nf_span:
                    self.add_network_function_attributes_to_span(
                        span=nf_span,
                        vendor=device.vendor.upper(),
                        ip_address=device.ipAddress,
                        device_role="service_device"
                    )
                    
                    self.record_span_event_from_instance(
                        "servicemapper.device.processing.started",
                        {"tid": device.tid, "vendor": device.vendor}
                    )
                    
                    # Process device
                    self.get_service_differences(device)
                    self.validate_network_data(device)
                    
                    self.record_span_event_from_instance(
                        "servicemapper.device.processing.completed",
                        {"tid": device.tid}
                    )
```

### Example 2: Network Service Termination

```python
class Terminate(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span(operation_name="network_service_terminate"):
            try:
                self.soft_terminate_process()
                # ... termination logic ...
            except Exception as ex:
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler(f"Termination failed: {ex}", ex)
                raise
```

### Example 3: Device Reset

```python
class Activate(CommonPlan, OTelMixin):
    def process(self):
        self.__init_otel__()
        with self.create_root_span(operation_name="device_reset"):
            self.set_correlation_baggage_from_instance()
            
            # Add span attributes
            if getattr(self, '_otel_initialized', False):
                span = trace.get_current_span()
                if span:
                    span.set_attribute("device_reset.circuit_id", self.circuit_id)
                    span.set_attribute("device_reset.service_type", self.service_type)
            
            topology_devices = self.get_all_devices_from_topology()
            
            # Record device count
            self.record_span_event_from_instance("device_reset.devices_found", {
                "device_count": len(topology_devices)
            })
            
            # Reset devices
            for device in topology_devices:
                # ... reset logic ...
                pass
```

---

## Summary

The `otel` directory provides:

1. **Core Setup** (`instrumentation.py`):
   - OTel tracer initialization
   - File-based and OTLP export modes
   - Structured logging with trace context
   - Correlation context management

2. **Easy Integration** (`otel_mixin.py`):
   - Mixin class for non-invasive instrumentation
   - Automatic initialization
   - Context managers for spans
   - Dual logging (standard + structured)

3. **MDSO Helpers** (`otel_mdso_utils.py`):
   - Topology and network function span creation
   - Error pattern matching and categorization
   - Regex patterns for identifier extraction

4. **Metrics** (`metrics.py`):
   - Operation counters and durations
   - Error tracking
   - Domain-specific metrics (topology, devices, provisioning)

5. **Feature Flags** (`feature_flags.py`):
   - Enable/disable OTel
   - Sampling control
   - Configuration management

**Key Design Principles**:
- Graceful degradation (works without OTel installed)
- Non-invasive (doesn't break existing code)
- Automatic correlation (extracts context from instances)
- Comprehensive error handling (categorization + identifier extraction)
- Dual export modes (file for isolated containers, OTLP for direct connection)
