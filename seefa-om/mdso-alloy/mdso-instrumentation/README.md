# MDSO Instrumentation

Unified OpenTelemetry instrumentation package for MDSO products including scriptplans, SENSE apps, and correlation services.

## Version 2.0.0

This is a major refactoring that introduces a class-based approach to instrumentation while maintaining backward compatibility with existing code.

---

## Quick Start

### Installation

The instrumentation package is located at:
```
seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/
```

Dependencies:
```bash
pip install -r otel_instrumentation/requirements.txt
```

### Basic Usage

```python
from otel_instrumentation import create_instrumentation

# Create and setup instrumentation
instr = create_instrumentation("my-service", environment="prod")

# Use it in your code
with instr.span("operation.name") as span:
    instr.log("Starting operation", "STARTED")
    # Do work
    instr.log("Operation complete", "COMPLETED")
```

---

## What's New in 2.0

### ✨ New Features

1. **Unified `MDSOInstrumentation` Class**
   - All functionality in one easy-to-use class
   - Simple initialization and setup
   - Context managers for spans
   - Built-in utilities for common patterns

2. **Improved API**
   - Cleaner method names
   - Better documentation
   - Consistent interface across all products

3. **Enhanced Utilities**
   - Error categorization
   - Identifier extraction from logs
   - Vendor resource mapping
   - Topology and network function helpers

4. **Backward Compatibility**
   - All old functions still work
   - Gradual migration path
   - No breaking changes

---

## Documentation

- **[REFACTORING-PLAN.md](./REFACTORING-PLAN.md)** - Detailed refactoring plan and architecture
- **[INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md)** - How to integrate across different products
- **[otel_instrumentation/examples.py](./otel_instrumentation/examples.py)** - Complete working examples

---

## Architecture

### File Structure

```
mdso-instrumentation/
├── README.md                           # This file
├── REFACTORING-PLAN.md                 # Refactoring plan and design
├── INTEGRATION-GUIDE.md                # Integration guide for all products
├── otel_instrumentation/
│   ├── __init__.py                     # Package exports
│   ├── mdso_instrumentation.py         # ✨ NEW: Main MDSOInstrumentation class
│   ├── instrumentation.py              # Legacy standalone functions
│   ├── otel_mdso_utils.py             # Utility classes and helpers
│   ├── examples.py                     # ✨ NEW: Complete usage examples
│   └── requirements.txt                # Python dependencies
└── alloy/                              # Grafana Alloy configuration
```

### Component Overview

| Component | Purpose | Status |
|-----------|---------|--------|
| `MDSOInstrumentation` | Main class - unified API | ✨ New |
| `instrumentation.py` | Standalone functions | Legacy (deprecated) |
| `otel_mdso_utils.py` | Helper classes and utilities | Active |
| `examples.py` | Working examples | ✨ New |

---

## Usage by Product

### MDSO Scriptplans (Common Plan)

Integrate in your plan's `run()` method:

```python
from otel_instrumentation import MDSOInstrumentation

class CommonPlan:
    def run(self, circuit_id, resource_id):
        instr = MDSOInstrumentation(
            service_name="my-scriptplan",
            environment="prod"
        ).setup()

        instr.inject_context(circuit_id=circuit_id, resource_id=resource_id)

        with instr.span("plan.run", circuit_id=circuit_id) as span:
            # Execute plan logic
            result = self.execute_plan()
            return result
```

See: [INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md#mdso-scriptplans-common-plan) for complete patterns.

### SENSE Apps (Beorn, Arda, Palantir)

Initialize once at app startup:

```python
from otel_instrumentation import create_instrumentation

# At app startup
instrumentation = create_instrumentation("beorn", environment="prod")

# In route handlers
@app.route("/topology/<circuit_id>")
def get_topology(circuit_id):
    with instrumentation.span("beorn.api.get_topology", circuit_id=circuit_id) as span:
        topology = fetch_topology(circuit_id)
        instrumentation.add_topology_attrs(
            span,
            topology_node_count=len(topology)
        )
        return jsonify(topology)
```

See: [INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md#sense-apps-beorn-arda-palantir) for Flask/FastAPI patterns.

### Correlation Engine

Use in MDSO client and log collectors:

```python
from otel_instrumentation import MDSOInstrumentation

class MDSOClient:
    def __init__(self):
        self.instr = MDSOInstrumentation("correlation-mdso-client").setup()

    def get_resource(self, resource_id):
        with self.instr.span("mdso.get_resource", resource_id=resource_id) as span:
            response = self._api_call(resource_id)
            return response.json()
```

See: [INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md#correlation-engine) for complete patterns.

---

## Key Features

### 1. Span Creation with Context Manager

```python
with instr.span("operation.name", circuit_id="123") as span:
    # Automatically sets status
    # Records exceptions
    # Ends span on exit
    pass
```

### 2. Correlation Context Management

```python
# Inject context (sets span attributes + baggage)
instr.inject_context(
    circuit_id="22.ABCD.123456..",
    resource_id="550e8400-e29b-41d4-a716-446655440000"
)

# Extract context (from baggage)
ctx = instr.extract_context()
print(ctx["circuit_id"])
```

### 3. MDSO-Specific Attributes

```python
# Topology attributes
instr.add_topology_attrs(
    span,
    service_type="FIA",
    vendor="juniper",
    topology_node_count=5
)

# Network function attributes
instr.add_network_function_attrs(
    span,
    vendor="cisco",
    ip_address="10.0.0.1",
    device_role="PE"
)

# Error attributes
instr.add_error_attrs(
    span,
    error_message="Device unreachable",
    error_category="CONNECTIVITY_ERROR"
)
```

### 4. Structured Logging

```python
# Logs are emitted to stdout + added as span events
instr.log("Processing started", "STARTED", circuit_id="123")
instr.log("Processing complete", "COMPLETED", circuit_id="123")
instr.log("Processing failed", "FAILED", circuit_id="123", error="...")
```

### 5. Error Categorization

```python
# Automatically categorize errors using regex patterns
error_msg = "IP 10.0.0.1 already exists on device"
category = instr.categorize_error(error_msg)
# {'category': 'IP_CONFLICT_ERROR', 'type': 'IP Already Exists'}
```

### 6. Identifier Extraction

```python
# Extract circuit IDs, TIDs, IPs, etc. from log messages
log_msg = "Circuit 22.ABCD.123456.. failed on DEVICE001W"
ids = instr.extract_identifiers(log_msg)
# {'circuit_id': '22.ABCD.123456..', 'tid': 'DEVICE001W', ...}
```

---

## Configuration

### Basic Configuration

```python
instr = MDSOInstrumentation(
    service_name="my-service",           # Service name (required)
    endpoint="http://159.56.4.94:55681", # OTLP endpoint (optional)
    environment="prod",                   # Environment (dev/staging/prod)
    version="1.0.0"                       # Service version
)
```

### Advanced Configuration

```python
instr = MDSOInstrumentation(
    service_name="high-throughput-service",
    batch_config={
        "max_queue_size": 4096,              # Queue size for spans
        "max_export_batch_size": 1024,       # Batch size for export
        "schedule_delay_millis": 2000        # Export delay (ms)
    }
)
```

### Continuous Profiling (Optional)

```python
instr.setup_pyroscope(
    server_address="http://pyroscope:4040",
    tags={"team": "network-ops", "region": "us-east"}
)
```

---

## Migration from Old Code

### Before (v1.0 - Standalone Functions)

```python
from instrumentation import setup_otel, inject_correlation_context, mdso_span

tracer = setup_otel("my-service")
inject_correlation_context(circuit_id="123")

with mdso_span("operation") as span:
    pass
```

### After (v2.0 - Class-Based)

```python
from otel_instrumentation import create_instrumentation

instr = create_instrumentation("my-service")
instr.inject_context(circuit_id="123")

with instr.span("operation") as span:
    pass
```

**Note:** Old code still works! The migration is optional and can be gradual.

---

## Testing

### Run Examples

```bash
cd otel_instrumentation
python examples.py
```

This will run all example patterns and emit traces to the configured OTLP endpoint.

### Verify in Grafana

1. Traces should appear at: http://159.56.4.94:3000
2. Look for service name in Tempo
3. Verify span attributes and context propagation

---

## Dependencies

See `otel_instrumentation/requirements.txt`:

```
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-http==1.20.0
opentelemetry-semantic-conventions==0.41b0
structlog==23.2.0
opentelemetry-instrumentation-requests==0.41b0
opentelemetry-instrumentation-urllib3==0.41b0
pyroscope-io>=0.8.7  # Optional
```

---

## API Reference

### MDSOInstrumentation Class

#### Methods

| Method | Description |
|--------|-------------|
| `setup()` | Initialize tracer and logger |
| `span(name, **attrs)` | Create traced span (context manager) |
| `inject_context(**ctx)` | Inject correlation context |
| `extract_context()` | Extract correlation context |
| `add_topology_attrs(span, ...)` | Add topology attributes |
| `add_network_function_attrs(span, ...)` | Add network function attributes |
| `add_error_attrs(span, ...)` | Add error attributes |
| `log(msg, state, **ctx)` | Emit structured log |
| `categorize_error(msg)` | Categorize error message |
| `extract_identifiers(text)` | Extract IDs from text |
| `setup_pyroscope(**config)` | Enable profiling |

### Utility Classes

- `MDSORegexPatterns` - Regex patterns for log parsing
- `MDSOSpanHelper` - Helper methods for span attributes
- `ErrorPatternMatcher` - Error categorization
- `VENDOR_RESOURCE_MAPPING` - Vendor to resource type mapping

---

## Examples

See `otel_instrumentation/examples.py` for complete working examples:

1. Circuit Provisioning Scriptplan
2. Device Audit Script
3. Error Handling and Categorization
4. Context Propagation
5. Flask App Integration
6. Advanced Configuration

---

## Troubleshooting

### Common Issues

1. **"MDSOInstrumentation not setup"**
   - Call `setup()` after creating the instance

2. **Context not propagating**
   - Ensure you're calling `inject_context()` at entry point
   - Verify spans are nested using context managers

3. **Spans not in Grafana**
   - Check OTLP endpoint is reachable
   - Verify batch processor configuration
   - Check network connectivity

See [INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md#troubleshooting) for detailed troubleshooting.

---

## Contributing

### Adding New Features

1. Update `mdso_instrumentation.py` with new methods
2. Add corresponding utilities to `otel_mdso_utils.py` if needed
3. Add examples to `examples.py`
4. Update documentation

### Deprecation Policy

- Old standalone functions are deprecated but still work
- Will be removed in v3.0
- Migration guides provided in [INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md)

---

## Roadmap

### Version 2.1 (Planned)
- [ ] Add automatic framework instrumentation helpers
- [ ] Enhanced error pattern matching
- [ ] Support for custom exporters (DataDog, Jaeger)
- [ ] Performance optimizations

### Version 3.0 (Future)
- [ ] Remove deprecated standalone functions
- [ ] Python 3.11+ support only
- [ ] OpenTelemetry 2.0 support

---

## Support

- **Documentation**: See [INTEGRATION-GUIDE.md](./INTEGRATION-GUIDE.md)
- **Examples**: See [examples.py](./otel_instrumentation/examples.py)
- **Issues**: Contact platform team or create GitHub issue

---

## License

Internal MDSO project - all rights reserved.

---

## Changelog

### v2.0.0 (2024-12-12)
- ✨ NEW: `MDSOInstrumentation` class for unified API
- ✨ NEW: `create_instrumentation()` convenience function
- ✨ NEW: Comprehensive examples and integration guide
- 📚 Documentation overhaul
- 🔧 Backward compatibility maintained
- 🎯 Improved error categorization
- 🛠 Better utility methods

### v1.0.0 (Previous)
- Initial release with standalone functions
- Basic OTel setup
- MDSO-specific utilities
