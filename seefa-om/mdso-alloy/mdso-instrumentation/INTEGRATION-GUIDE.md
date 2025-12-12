# MDSO Instrumentation Integration Guide

## Overview

This guide explains how to use the **MDSOInstrumentation** class and **OTEL utils methods** across different MDSO products. The refactored instrumentation provides a unified, class-based approach that simplifies integration and maintains consistency across all products.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Integration Patterns by Product](#integration-patterns-by-product)
   - [MDSO Scriptplans (Common Plan)](#mdso-scriptplans-common-plan)
   - [SENSE Apps (Beorn, Arda, Palantir)](#sense-apps-beorn-arda-palantir)
   - [Correlation Engine](#correlation-engine)
   - [Standalone Scripts](#standalone-scripts)
3. [Using OTEL Utils Methods](#using-otel-utils-methods)
4. [Advanced Patterns](#advanced-patterns)
5. [Migration from Old Code](#migration-from-old-code)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```python
# Add to your script or module
from otel_instrumentation import MDSOInstrumentation, create_instrumentation
```

### Basic Usage

```python
# Method 1: Create and setup manually
instr = MDSOInstrumentation(
    service_name="my-service",
    environment="prod"
)
instr.setup()

# Method 2: Use convenience function
instr = create_instrumentation("my-service", environment="prod")

# Use it
with instr.span("operation.name") as span:
    instr.log("Starting operation", "STARTED")
    # Do work
    instr.log("Operation complete", "COMPLETED")
```

---

## Integration Patterns by Product

### MDSO Scriptplans (Common Plan)

Scriptplans should integrate instrumentation in the `run()` method of a common base class.

#### Pattern 1: Base Common Plan Class

```python
from otel_instrumentation import MDSOInstrumentation

class CommonPlan:
    """
    Base class for all MDSO scriptplans
    Provides standard instrumentation setup
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.instrumentation = None

    def run(self, circuit_id: str, resource_id: str, **kwargs):
        """
        Standard run method with instrumentation

        All subclasses should call super().run() or follow this pattern
        """
        # Setup instrumentation
        self.instrumentation = MDSOInstrumentation(
            service_name=self.service_name,
            environment=kwargs.get("environment", "prod"),
            version=kwargs.get("version", "1.0.0")
        )
        self.instrumentation.setup()

        # Inject correlation context
        self.instrumentation.inject_context(
            circuit_id=circuit_id,
            resource_id=resource_id,
            product_id=kwargs.get("product_id")
        )

        # Main operation
        with self.instrumentation.span(
            f"{self.service_name}.run",
            circuit_id=circuit_id
        ) as span:
            self.instrumentation.log(
                "Scriptplan execution started",
                "STARTED",
                circuit_id=circuit_id
            )

            try:
                result = self._execute(circuit_id, resource_id, **kwargs)

                self.instrumentation.log(
                    "Scriptplan execution completed",
                    "COMPLETED",
                    circuit_id=circuit_id
                )

                return result

            except Exception as e:
                self.instrumentation.add_error_attrs(
                    span,
                    error_message=str(e),
                    error_category=self._categorize_error(e)
                )

                self.instrumentation.log(
                    "Scriptplan execution failed",
                    "FAILED",
                    circuit_id=circuit_id,
                    error=str(e)
                )
                raise

    def _execute(self, circuit_id: str, resource_id: str, **kwargs):
        """Override this in subclasses"""
        raise NotImplementedError()

    def _categorize_error(self, error: Exception) -> str:
        """Categorize errors using instrumentation utilities"""
        if self.instrumentation:
            category = self.instrumentation.categorize_error(str(error))
            return category.get("category", "UNKNOWN_ERROR")
        return "UNKNOWN_ERROR"
```

#### Pattern 2: Specific Scriptplan Implementation

```python
class CircuitProvisionerPlan(CommonPlan):
    """
    Circuit provisioning scriptplan
    """

    def __init__(self):
        super().__init__(service_name="circuit-provisioner")

    def _execute(self, circuit_id: str, resource_id: str, **kwargs):
        # Fetch topology with tracing
        topology = self._fetch_topology(circuit_id)

        # Configure devices
        for device in topology["devices"]:
            self._configure_device(device, circuit_id)

        return {"status": "success"}

    def _fetch_topology(self, circuit_id: str):
        """Fetch topology from Beorn with full instrumentation"""
        with self.instrumentation.span(
            "beorn.topology.fetch",
            circuit_id=circuit_id
        ) as span:
            # Fetch topology (simplified)
            topology = beorn_client.get_topology(circuit_id)

            # Add topology-specific attributes
            self.instrumentation.add_topology_attrs(
                span,
                service_type=topology.get("service_type"),
                vendor=topology.get("vendor"),
                topology_node_count=len(topology.get("devices", [])),
                validation_status=True
            )

            return topology

    def _configure_device(self, device: dict, circuit_id: str):
        """Configure a device with instrumentation"""
        with self.instrumentation.span(
            "device.configure",
            tid=device["tid"]
        ) as span:
            # Add network function attributes
            self.instrumentation.add_network_function_attrs(
                span,
                vendor=device["vendor"],
                ip_address=device["ip"],
                device_role=device["role"],
                communication_state="reachable"
            )

            # Execute configuration
            device_client.configure(device)
```

---

### SENSE Apps (Beorn, Arda, Palantir)

SENSE apps should initialize instrumentation once at startup and use it in API handlers.

#### Pattern: Flask App Integration

```python
from flask import Flask, request, jsonify
from otel_instrumentation import MDSOInstrumentation

app = Flask(__name__)

# Initialize instrumentation ONCE at app startup
instrumentation = MDSOInstrumentation(
    service_name="beorn",
    environment=os.getenv("ENVIRONMENT", "prod"),
    version="2.0.0"
)
instrumentation.setup()

@app.route("/topology/<circuit_id>")
def get_topology(circuit_id):
    """
    Fetch topology with full tracing
    """
    # Extract correlation context from headers
    product_id = request.headers.get("X-Product-Id")
    resource_id = request.headers.get("X-Resource-Id")

    # Inject context
    instrumentation.inject_context(
        circuit_id=circuit_id,
        product_id=product_id,
        resource_id=resource_id
    )

    # Trace the operation
    with instrumentation.span(
        "beorn.api.get_topology",
        circuit_id=circuit_id
    ) as span:
        try:
            # Fetch from database
            with instrumentation.span("beorn.db.query") as db_span:
                topology = db.get_topology(circuit_id)

            # Validate
            with instrumentation.span("beorn.validate.topology") as val_span:
                is_valid = validate_topology(topology)

                instrumentation.add_topology_attrs(
                    span,
                    service_type=topology.get("service_type"),
                    topology_node_count=len(topology.get("nodes", [])),
                    validation_status=is_valid
                )

            return jsonify(topology)

        except Exception as e:
            instrumentation.add_error_attrs(
                span,
                error_message=str(e),
                error_category=instrumentation.categorize_error(str(e))["category"]
            )
            return jsonify({"error": str(e)}), 500
```

#### Pattern: FastAPI Integration

```python
from fastapi import FastAPI, Header
from otel_instrumentation import create_instrumentation

app = FastAPI()

# Initialize instrumentation
instrumentation = create_instrumentation("arda", environment="prod")

@app.get("/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    x_circuit_id: str = Header(None),
    x_product_id: str = Header(None)
):
    """Async endpoint with tracing"""

    # Inject context
    instrumentation.inject_context(
        circuit_id=x_circuit_id,
        product_id=x_product_id,
        resource_id=resource_id
    )

    with instrumentation.span("arda.api.get_resource", resource_id=resource_id) as span:
        # Fetch resource
        resource = await fetch_resource(resource_id)

        # Add attributes
        instrumentation.add_network_function_attrs(
            span,
            provider_resource_id=resource.get("provider_resource_id")
        )

        return resource
```

---

### Correlation Engine

The correlation engine should use instrumentation when interacting with MDSO APIs.

#### Pattern: MDSO Client with Tracing

```python
from otel_instrumentation import MDSOInstrumentation

class MDSOClient:
    """
    MDSO API client with built-in tracing
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.instrumentation = MDSOInstrumentation(
            service_name="correlation-engine-mdso-client"
        ).setup()

    def get_resource(self, resource_id: str, circuit_id: str = None):
        """Fetch resource from MDSO with tracing"""

        with self.instrumentation.span(
            "mdso.client.get_resource",
            resource_id=resource_id
        ) as span:
            # Inject context if provided
            if circuit_id:
                self.instrumentation.inject_context(
                    circuit_id=circuit_id,
                    resource_id=resource_id
                )

            try:
                # Make API call
                response = requests.get(
                    f"{self.base_url}/resources/{resource_id}",
                    headers=self._get_auth_headers()
                )
                response.raise_for_status()

                data = response.json()

                # Add attributes
                span.set_attribute("mdso.resource_type", data.get("type"))
                span.set_attribute("mdso.product_name", data.get("product_name"))

                return data

            except requests.HTTPError as e:
                self.instrumentation.add_error_attrs(
                    span,
                    error_message=str(e),
                    error_category="HTTP_ERROR"
                )
                raise

    def collect_logs(self, product_name: str, circuit_id: str, hours: int = 24):
        """Collect logs with tracing"""

        with self.instrumentation.span(
            "mdso.client.collect_logs",
            circuit_id=circuit_id,
            product_name=product_name
        ) as span:
            self.instrumentation.log(
                "Starting log collection",
                "STARTED",
                product_name=product_name,
                circuit_id=circuit_id,
                hours=hours
            )

            logs = []
            # Collection logic...

            span.set_attribute("logs.collected", len(logs))

            self.instrumentation.log(
                "Log collection complete",
                "COMPLETED",
                logs_collected=len(logs)
            )

            return logs
```

---

### Standalone Scripts

Standalone scripts should setup instrumentation in the main function.

```python
#!/usr/bin/env python3
from otel_instrumentation import create_instrumentation

def main():
    # Setup instrumentation
    instr = create_instrumentation(
        service_name="device-audit-script",
        environment="dev"
    )

    # Main operation
    with instr.span("audit.devices") as span:
        instr.log("Starting device audit", "STARTED")

        devices = get_all_devices()
        instr.log(f"Found {len(devices)} devices", device_count=len(devices))

        for device in devices:
            with instr.span("audit.device", tid=device["tid"]) as dev_span:
                instr.add_network_function_attrs(
                    dev_span,
                    ip_address=device["ip"],
                    vendor=device["vendor"]
                )

                audit_device(device)

        instr.log("Audit complete", "COMPLETED")

if __name__ == "__main__":
    main()
```

---

## Using OTEL Utils Methods

### Available Utils Methods

The `MDSOInstrumentation` class provides access to all utility methods:

#### 1. Topology Attributes

```python
# Add topology-specific attributes to a span
instr.add_topology_attrs(
    span,
    service_type="FIA",           # Service type (FIA, ELAN, ELINE, etc.)
    vendor="juniper",             # Device vendor
    fqdn="device.example.com",    # Device FQDN
    topology_node_count=5,        # Number of nodes
    validation_status=True        # Validation passed/failed
)
```

#### 2. Network Function Attributes

```python
# Add network function attributes to a span
instr.add_network_function_attrs(
    span,
    communication_state="reachable",              # Device communication state
    ip_address="10.0.0.1",                        # Device IP
    vendor="cisco",                               # Device vendor
    device_role="PE",                             # Device role (PE/CPE)
    provider_resource_id="resource-123"           # MDSO provider resource ID
)
```

#### 3. Error Attributes

```python
# Add error attributes to a span
instr.add_error_attrs(
    span,
    error_code="DE-1000",                         # Error code
    error_category="DEVICE_ERROR",                # Error category
    error_message="Device unreachable",           # Error message
    is_new_error=True                             # Is this a new error?
)
```

#### 4. Context Injection and Extraction

```python
# Inject correlation context
instr.inject_context(
    circuit_id="22.ABCD.123456..",
    product_id="product-123",
    resource_id="550e8400-e29b-41d4-a716-446655440000",
    resource_type_id="resourceType-456"
)

# Extract correlation context (from baggage)
ctx = instr.extract_context()
print(ctx["circuit_id"])  # "22.ABCD.123456.."
```

#### 5. Error Categorization

```python
# Categorize an error using regex patterns
error_msg = "IP 10.0.0.1 already exists on device"
category = instr.categorize_error(error_msg)
print(category)
# {'category': 'IP_CONFLICT_ERROR', 'type': 'IP Already Exists'}
```

#### 6. Identifier Extraction

```python
# Extract identifiers from log messages
log_msg = "Circuit 22.ABCD.123456.. failed on device DEVICE001W at 10.0.0.1"
identifiers = instr.extract_identifiers(log_msg)
print(identifiers)
# {
#   'circuit_id': '22.ABCD.123456..',
#   'tid': 'DEVICE001W',
#   'ipv4': '10.0.0.1',
#   'resource_id': None,
#   'fqdn': None
# }
```

---

## Advanced Patterns

### Pattern 1: Custom Batch Configuration

For high-throughput operations, customize the batch processor:

```python
instr = MDSOInstrumentation(
    service_name="high-throughput-processor",
    batch_config={
        "max_queue_size": 4096,              # Larger queue
        "max_export_batch_size": 1024,       # Larger batches
        "schedule_delay_millis": 2000        # Export more frequently
    }
)
instr.setup()
```

### Pattern 2: Continuous Profiling

Enable Pyroscope profiling for performance analysis:

```python
instr = create_instrumentation("my-service")

# Enable profiling with custom tags
instr.setup_pyroscope(
    server_address="http://pyroscope:4040",
    tags={
        "team": "network-ops",
        "region": "us-east-1"
    }
)
```

### Pattern 3: Context Propagation Across Services

Context automatically propagates through baggage:

```python
# Service A: Inject context
with instr_a.span("service_a.operation") as span:
    instr_a.inject_context(circuit_id="123", resource_id="456")

    # Call Service B (via HTTP, gRPC, etc.)
    response = call_service_b()

# Service B: Extract context
with instr_b.span("service_b.operation") as span:
    ctx = instr_b.extract_context()
    circuit_id = ctx["circuit_id"]  # "123" - automatically propagated!
```

### Pattern 4: Nested Spans for Complex Operations

```python
with instr.span("provision.circuit", circuit_id="123") as main_span:

    # Fetch topology
    with instr.span("fetch.topology") as fetch_span:
        topology = fetch_topology()
        instr.add_topology_attrs(fetch_span, topology_node_count=len(topology))

    # Configure each device
    for device in topology:
        with instr.span("configure.device", tid=device["tid"]) as dev_span:
            instr.add_network_function_attrs(dev_span, vendor=device["vendor"])

            # Even deeper nesting for device steps
            with instr.span("device.validate") as val_span:
                validate_device(device)

            with instr.span("device.push_config") as cfg_span:
                push_config(device)
```

---

## Migration from Old Code

### Old Code (Standalone Functions)

```python
from instrumentation import setup_otel, inject_correlation_context, mdso_span

tracer = setup_otel("my-service")
inject_correlation_context(circuit_id="123")

with mdso_span("operation") as span:
    span.set_attribute("key", "value")
```

### New Code (Class-Based)

```python
from otel_instrumentation import create_instrumentation

instr = create_instrumentation("my-service")
instr.inject_context(circuit_id="123")

with instr.span("operation") as span:
    span.set_attribute("key", "value")
```

### Migration Checklist

- [ ] Replace `setup_otel()` calls with `MDSOInstrumentation(...).setup()`
- [ ] Replace `inject_correlation_context()` with `instr.inject_context()`
- [ ] Replace `extract_correlation_context()` with `instr.extract_context()`
- [ ] Replace `mdso_span` context manager with `instr.span()`
- [ ] Replace `MDSOSpanHelper` static methods with `instr.add_*_attrs()`
- [ ] Update imports from `instrumentation` to `otel_instrumentation`

---

## Troubleshooting

### Common Issues

#### 1. "MDSOInstrumentation not setup" Error

**Problem:** Calling methods before `setup()` is called.

**Solution:**
```python
instr = MDSOInstrumentation("my-service")
instr.setup()  # Must call setup() before using!
```

#### 2. Context Not Propagating

**Problem:** Context not available in downstream functions.

**Solution:** Ensure you're injecting context and using span context managers:
```python
# Inject at top level
instr.inject_context(circuit_id="123")

# Context propagates automatically through spans
with instr.span("operation"):
    ctx = instr.extract_context()  # Context available!
```

#### 3. Spans Not Appearing in Grafana

**Problem:** OTLP endpoint not reachable.

**Solution:** Check endpoint configuration:
```python
instr = MDSOInstrumentation(
    service_name="my-service",
    endpoint="http://159.56.4.94:55681"  # Verify this is correct
)
```

#### 4. Import Errors

**Problem:** Cannot import `MDSOInstrumentation`.

**Solution:** Ensure you're importing from the correct package:
```python
# Correct
from otel_instrumentation import MDSOInstrumentation

# Also correct
from mdso_instrumentation import MDSOInstrumentation
```

---

## Summary

### Key Takeaways

1. **Use `MDSOInstrumentation` class** for all new code
2. **Initialize once, use everywhere** - setup at app/script start
3. **Inject context early** - at the entry point of your operation
4. **Use helper methods** - `add_topology_attrs()`, `add_network_function_attrs()`, etc.
5. **Leverage context propagation** - baggage automatically carries context
6. **Follow patterns** - use the examples in this guide

### Quick Reference

```python
# Setup
instr = create_instrumentation("service-name", environment="prod")

# Context
instr.inject_context(circuit_id="123", resource_id="456")
ctx = instr.extract_context()

# Spans
with instr.span("operation.name", **attrs) as span:
    pass

# Attributes
instr.add_topology_attrs(span, service_type="FIA", vendor="juniper")
instr.add_network_function_attrs(span, ip_address="10.0.0.1")
instr.add_error_attrs(span, error_message="Error", error_category="ERROR")

# Logging
instr.log("Message", "STARTED", **context)

# Utils
category = instr.categorize_error(error_msg)
ids = instr.extract_identifiers(log_msg)
```

---

## Next Steps

1. Review the `examples.py` file for complete working examples
2. Start with a simple scriptplan or standalone script
3. Gradually migrate existing code
4. Test in dev environment before deploying to prod
5. Monitor spans in Grafana to ensure everything works

For questions or issues, refer to the repository documentation or contact the platform team.
