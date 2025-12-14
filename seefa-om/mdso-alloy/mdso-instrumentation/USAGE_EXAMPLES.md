# OTel Instrumentation Usage Examples

## Using OTelMixin

### Basic Usage

```python
from common_plan import CommonPlan
from otel_instrumentation.otel_mixin import OTelMixin

class ServiceMapper(CommonPlan, OTelMixin):
    def run(self):
        # Initialize OTel (checks feature flags automatically)
        self.__init_otel__()
        
        # Create root span - automatically extracts circuit_id, resource_id from self
        with self.create_root_span():
            # Your existing code here
            result = self.provision_service()
            return result
```

### With Error Handling

```python
class Fabricator(CommonPlan, OTelMixin):
    def run(self):
        self.__init_otel__()
        
        with self.create_root_span():
            try:
                self.otel_log("Starting fabricator execution", level="info")
                result = self.create_fabric()
                self.otel_log("Fabricator completed", level="info", fabric_id=result.id)
                return result
            except Exception as e:
                self.otel_error_handler(f"Fabricator failed: {str(e)}", exception=e)
                raise
```

### Manual Correlation Context

```python
class ConfigModeler(CommonPlan, OTelMixin):
    def run(self):
        self.__init_otel__()
        
        # Manually set correlation context if not in instance attributes
        from otel_instrumentation.instrumentation import inject_correlation_context
        
        inject_correlation_context(
            circuit_id="80.L1XX.005054..CHTR",
            resource_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        with self.create_root_span():
            return self.model_config()
```

## Using Feature Flags

### Environment Variables

```bash
# Disable OTel entirely
export OTEL_ENABLED=false

# Enable sampling at 50% rate
export OTEL_SAMPLING_ENABLED=true
export OTEL_SAMPLING_RATE=0.5

# Enable full tracing (default)
export OTEL_ENABLED=true
export OTEL_SAMPLING_RATE=1.0
```

### In Code

```python
from otel_instrumentation.feature_flags import (
    is_otel_enabled,
    is_otel_sampling_enabled,
    get_otel_sampling_rate
)

# Check if OTel is enabled
if is_otel_enabled():
    tracer = setup_otel("my-service")
    
    # Apply sampling
    if is_otel_sampling_enabled():
        sampling_rate = get_otel_sampling_rate()
        # Use sampling_rate in your logic
```

## Standalone Functions (Without Mixin)

### Basic Setup

```python
from otel_instrumentation.instrumentation import (
    setup_otel,
    get_otel_logger,
    inject_correlation_context,
    mdso_span
)

# Setup tracer
tracer = setup_otel("mdso-scriptplan", environment="dev")

# Get logger (automatically includes trace context)
logger = get_otel_logger("mdso-scriptplan")

# Set correlation context
inject_correlation_context(
    circuit_id="80.L1XX.005054..CHTR",
    resource_id="uuid-123"
)

# Create span
with mdso_span("mdso.product.ServiceProvisioner", circuit_id="80.L1XX.005054..CHTR"):
    logger.info("Provisioning service")
    # ... do work ...
```

### Log Levels and States

```python
from otel_instrumentation.instrumentation import otel_enter_exit_log

# Different states map to different log levels:
otel_enter_exit_log("Starting", "STARTED")        # debug
otel_enter_exit_log("Activating", "ACTIVATING")    # info
otel_enter_exit_log("Active", "ACTIVE")            # info
otel_enter_exit_log("Complete", "COMPLETED")       # info
otel_enter_exit_log("Failed", "FAILED")            # error
```

## Handling None Values

The `extract_correlation_context()` function filters out None values:

```python
from otel_instrumentation.instrumentation import extract_correlation_context

# Only returns keys with non-None values
context = extract_correlation_context()
# Returns: {"circuit_id": "123", "resource_id": "456"}
# Does NOT include: product_id, resource_type_id (if they were None)

# Safe to use in logging
logger.info("Processing", **extract_correlation_context())
```
