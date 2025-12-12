# MDSO Instrumentation Refactoring Plan

## Current State Analysis

### Existing Structure
The instrumentation code is split across two files:

1. **`instrumentation.py`** (311 lines)
   - Standalone functions for OTel setup
   - Functions: `setup_otel()`, `get_otel_logger()`, `inject_correlation_context()`, etc.
   - Context manager: `mdso_span` class

2. **`otel_mdso_utils.py`** (454 lines)
   - Helper classes: `MDSORegexPatterns`, `MDSOSpanHelper`, `ErrorPatternMatcher`
   - Beorn topology helpers
   - Vendor resource mapping

### Usage Patterns Across Products

| Product | Current Usage | Entry Point |
|---------|---------------|-------------|
| MDSO Scriptplans | Standalone functions | `setup_otel()` in script |
| SENSE Apps | `setup_otel_sense()` | Flask/FastAPI middleware |
| Correlation Engine | Direct tracer usage | MDSOClient, LogCollector |

---

## Refactoring Goals

### 1. Create Unified `MDSOInstrumentation` Class
- Single class that encapsulates all OTel functionality
- Easy to instantiate in a plan's `run()` method
- Maintains backward compatibility with existing code

### 2. Key Design Principles
- **Single Responsibility**: Each method does one thing well
- **Easy Integration**: Simple instantiation and usage
- **Flexible Configuration**: Support different products/environments
- **Context Management**: Built-in context managers for spans

### 3. Benefits
- Consistent instrumentation across all products
- Easier testing and maintenance
- Clear API for developers
- Reduced code duplication

---

## Proposed Class Structure

```python
class MDSOInstrumentation:
    """
    Unified OpenTelemetry instrumentation for MDSO products

    Usage in a plan's run() method:
        def run(self):
            instrumentation = MDSOInstrumentation(
                service_name="my-scriptplan",
                environment="prod"
            )
            instrumentation.setup()

            with instrumentation.span("operation.name", circuit_id="123") as span:
                # Do work
                instrumentation.add_topology_attrs(span, ...)
    """

    def __init__(self, service_name, endpoint=None, environment="dev", version="1.0.0"):
        """Initialize instrumentation configuration"""

    def setup(self):
        """Setup OTel tracer and logger"""

    def span(self, name, kind=SpanKind.INTERNAL, **attributes):
        """Context manager for creating spans"""

    def inject_context(self, circuit_id, product_id, resource_id, resource_type_id):
        """Inject correlation context"""

    def extract_context(self):
        """Extract correlation context"""

    def add_topology_attrs(self, span, ...):
        """Add topology-specific attributes"""

    def add_network_function_attrs(self, span, ...):
        """Add network function attributes"""

    def add_error_attrs(self, span, ...):
        """Add error attributes"""

    def log(self, message, state="STARTED", **context):
        """Structured logging with OTel integration"""
```

---

## Integration Patterns

### Pattern 1: MDSO Scriptplan (Common Plan)

```python
from mdso_instrumentation import MDSOInstrumentation

class CommonPlan:
    def run(self, circuit_id, resource_id):
        # Initialize instrumentation
        instr = MDSOInstrumentation(
            service_name="circuit-provisioner",
            environment="prod"
        )
        instr.setup()

        # Inject correlation context
        instr.inject_context(
            circuit_id=circuit_id,
            resource_id=resource_id
        )

        # Main operation with tracing
        with instr.span("provision.circuit", circuit_id=circuit_id) as span:
            instr.log("Starting provisioning", "STARTED", circuit_id=circuit_id)

            try:
                # Fetch topology
                with instr.span("beorn.topology.fetch") as topology_span:
                    topology = self.fetch_topology(circuit_id)
                    instr.add_topology_attrs(
                        topology_span,
                        service_type="FIA",
                        vendor="juniper",
                        topology_node_count=len(topology)
                    )

                # Configure devices
                for device in topology:
                    with instr.span("device.configure", tid=device.tid) as dev_span:
                        instr.add_network_function_attrs(
                            dev_span,
                            vendor=device.vendor,
                            ip_address=device.ip
                        )
                        self.configure_device(device)

                instr.log("Provisioning complete", "COMPLETED", circuit_id=circuit_id)

            except Exception as e:
                instr.add_error_attrs(
                    span,
                    error_message=str(e),
                    error_category="PROVISIONING_ERROR"
                )
                instr.log("Provisioning failed", "FAILED", circuit_id=circuit_id, error=str(e))
                raise
```

### Pattern 2: SENSE App (Flask/FastAPI)

```python
from mdso_instrumentation import MDSOInstrumentation

app = Flask(__name__)

# Initialize once at app startup
instrumentation = MDSOInstrumentation(
    service_name="beorn",
    environment="prod"
)
instrumentation.setup()

@app.route("/topology/<circuit_id>")
def get_topology(circuit_id):
    with instrumentation.span("beorn.api.get_topology", circuit_id=circuit_id) as span:
        topology = fetch_topology(circuit_id)
        instrumentation.add_topology_attrs(
            span,
            topology_node_count=len(topology),
            validation_status=True
        )
        return jsonify(topology)
```

### Pattern 3: Standalone Script

```python
from mdso_instrumentation import MDSOInstrumentation

def main():
    instr = MDSOInstrumentation(
        service_name="device-audit",
        environment="dev"
    )
    instr.setup()

    with instr.span("audit.devices") as span:
        devices = get_devices()
        instr.log(f"Found {len(devices)} devices", "STARTED")

        for device in devices:
            audit_device(device)

        instr.log("Audit complete", "COMPLETED")

if __name__ == "__main__":
    main()
```

---

## Migration Strategy

### Phase 1: Create New Class (Backward Compatible)
1. Create `mdso_instrumentation.py` with new `MDSOInstrumentation` class
2. Keep existing `instrumentation.py` and `otel_mdso_utils.py` unchanged
3. Add tests for new class

### Phase 2: Gradual Adoption
1. Update documentation with migration guide
2. Refactor one scriptplan as proof of concept
3. Update SENSE apps to use new class
4. Update correlation engine

### Phase 3: Deprecation (Future)
1. Mark old functions as deprecated
2. Add deprecation warnings
3. Eventually remove old code after all products migrated

---

## File Structure After Refactoring

```
mdso-instrumentation/
├── otel_instrumentation/
│   ├── __init__.py                    # Re-export main class
│   ├── mdso_instrumentation.py        # NEW: Main MDSOInstrumentation class
│   ├── instrumentation.py             # KEEP: Backward compatibility (deprecated)
│   ├── otel_mdso_utils.py            # KEEP: Utilities (may refactor into main class)
│   ├── patterns.py                    # NEW: Extract regex patterns
│   ├── helpers.py                     # NEW: Extract helper functions
│   └── requirements.txt
└── tests/
    ├── test_mdso_instrumentation.py   # NEW: Tests for main class
    └── test_integration.py            # NEW: Integration tests
```

---

## Implementation Checklist

- [ ] Create `MDSOInstrumentation` class with all methods
- [ ] Move regex patterns to `patterns.py`
- [ ] Move helper functions to `helpers.py`
- [ ] Create comprehensive tests
- [ ] Write migration guide
- [ ] Update documentation
- [ ] Create example scriptplan using new class
- [ ] Update SENSE apps
- [ ] Update correlation engine

---

## Testing Strategy

### Unit Tests
- Test each method in isolation
- Mock external dependencies (OTLP exporter)
- Verify span attributes are set correctly

### Integration Tests
- Test full workflow: setup → span creation → context propagation
- Test with real OTLP collector
- Test error handling and recovery

### Migration Tests
- Ensure backward compatibility
- Test old code still works alongside new code
- Verify no breaking changes

---

## Open Questions

1. **Should we support multiple tracer instances?**
   - Current code uses global tracer
   - Class-based approach could support multiple instances

2. **How to handle SENSE app-specific instrumentation?**
   - Keep `setup_otel_sense()` as separate function?
   - Or add Flask/FastAPI-specific methods to main class?

3. **Should we extract regex patterns to separate module?**
   - Cleaner separation of concerns
   - Easier to update patterns independently

4. **Versioning strategy?**
   - Semantic versioning for instrumentation package?
   - How to track compatibility with different products?
