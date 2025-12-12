# OpenTelemetry Implementation Strategy for MDSO Scripts

## Executive Summary

This document outlines a strategy to implement OpenTelemetry (OTel) instrumentation in the MDSO scripts directory, leveraging existing OTel classes from `mdso-alloy/mdso-instrumentation` while maintaining compatibility with the current logging structure in `scripts/common_plan.py`.

## Current State Analysis

### 1. Logging Structure in scripts/common_plan.py

The current logging implementation in the scripts directory uses Python's standard `logging` module with the following characteristics:

**Location**: `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/common_plan.py`

**Key Components**:

```python
# Line 387-399: Logger initialization in run() method
self.plansdk_logger = logging.getLogger("plansdk.bpo.http")
self.plansdk_logger.setLevel(logging.WARN)
self.logger = logging.getLogger("scriptplan")

# Splunk logger setup
self.splunk_logger = self.splunk_logger_setup()

# Syslog initialization
self.syslogger = None
self.__initialize_syslog()
```

**Logging Features**:
- **Three logger types**:
  - `self.logger` - Main scriptplan logger
  - `self.splunk_logger` - Splunk-specific logger with RotatingFileHandler
  - `self.syslogger` - System logging via SysLogHandler

- **Sensitive data filtering**: Custom `sensitiveLogDataFormatter` class that masks passwords and sensitive information in logs

- **Log destinations**:
  - Main logs: Standard Python logging
  - Splunk logs: `/bp2/log/splunk-logs/sensor-templates-splunk.log`
  - Syslog: `/dev/log`

### 2. OpenTelemetry Classes Available

**Location**:
- `.archive/otel_instrumentation/`
- `v2/corr-station-updated/seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/`

**Available Modules**:

#### instrumentation.py
Provides standalone functions for OTel setup:
- `setup_otel()` - Initialize OTel tracer with OTLP exporter
- `get_otel_logger()` - Get structlog-based logger
- `otel_enter_exit_log()` - Standalone enter/exit logging with span events
- `inject_correlation_context()` - Set correlation baggage
- `extract_correlation_context()` - Retrieve correlation data
- `create_mdso_span()` - Create MDSO-specific spans
- `mdso_span` - Context manager for spans

#### otel_mdso_utils.py
Provides MDSO-specific utilities:
- `MDSORegexPatterns` - Comprehensive regex patterns for parsing logs (circuit IDs, TIDs, FQDNs, IPs, error patterns)
- `MDSOSpanHelper` - Helper methods for creating and enriching spans
  - Topology spans (Beorn operations)
  - Network function spans
  - Error tracking attributes
  - Correlation baggage management
- `ErrorPatternMatcher` - Categorize and extract error information
- Vendor mapping utilities
- Beorn topology helpers

## Implementation Strategy

### Phase 1: Non-Invasive Integration (Recommended First Step)

**Objective**: Add OTel instrumentation alongside existing logging without modifying current behavior.

**Approach**: Create a mixin class that products can optionally inherit.

```python
# New file: scripts/otel_mixin.py
from otel_instrumentation.instrumentation import (
    setup_otel,
    get_otel_logger,
    inject_correlation_context,
    mdso_span
)
from otel_instrumentation.otel_mdso_utils import MDSOSpanHelper
from opentelemetry import trace

class OTelMixin:
    """
    Mixin class to add OTel instrumentation to existing products.

    Products can inherit from both CommonPlan and OTelMixin to get
    OTel capabilities without breaking existing logging.
    """

    def __init_otel__(self):
        """Initialize OTel tracer and structured logger"""
        # Get product/resource type from class name
        product_type = self.__class__.__name__

        # Setup OTel tracer
        self.tracer = setup_otel(
            service_name=f"mdso.{product_type}",
            environment=os.getenv("MDSO_ENV", "dev")
        )

        # Setup structured logger
        self.otel_logger = get_otel_logger(product_type)

        # Helper for span management
        self.span_helper = MDSOSpanHelper()

    def otel_run_wrapper(self):
        """
        Wrap the main run() method with a root span.

        Usage in product:
            def run(self):
                with self.create_root_span():
                    return super().run()
        """
        span_name = f"mdso.product.{self.__class__.__name__}"

        with self.tracer.start_as_current_span(span_name) as span:
            # Inject correlation context
            if hasattr(self, 'circuit_id'):
                inject_correlation_context(
                    circuit_id=self.circuit_id,
                    resource_id=self.resource_id
                )
                span.set_attribute("circuit_id", self.circuit_id)
                span.set_attribute("resource_id", self.resource_id)

            # Set product attributes
            span.set_attribute("mdso.product", self.__class__.__name__)
            span.set_attribute("mdso.component", "scriptplan")

            return span

    def otel_log(self, message, level="info", **context):
        """
        Dual logging: standard logger + structured OTel logger

        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
            **context: Additional structured context
        """
        # Standard logging (existing)
        getattr(self.logger, level)(message)

        # Structured OTel logging (new)
        if hasattr(self, 'otel_logger'):
            getattr(self.otel_logger, level)(
                message,
                circuit_id=getattr(self, 'circuit_id', None),
                resource_id=getattr(self, 'resource_id', None),
                **context
            )
```

**Benefits**:
- Zero impact on existing products
- Opt-in instrumentation
- Maintains backward compatibility
- Easy to test and validate

**Example Usage**:

```python
# In scripts/serviceMapper/common.py
from scripts.otel_mixin import OTelMixin

class Common(CommonPlan, OTelMixin):
    """
    common functionalities utilized by mapper products
    """

    def run(self):
        # Initialize OTel if mixin is available
        if hasattr(self, '__init_otel__'):
            self.__init_otel__()

        # Create root span
        with self.otel_run_wrapper():
            return super().run()

    def get_modeled_config(self, config_request_data) -> dict:
        payload = self.create_config_modeler_payload(config_request_data)

        # Dual logging
        if hasattr(self, 'otel_log'):
            self.otel_log(
                "Creating config model",
                level="info",
                payload=payload,
                requested_model=config_request_data['requested_model']
            )
        else:
            self.logger.info(f"Creating {config_request_data['requested_model']} config model")

        # Existing logic...
```

### Phase 2: Enhanced Instrumentation with Span Helpers

**Objective**: Add detailed span instrumentation for key operations.

**Key Areas to Instrument**:

1. **Config Modeling Operations** (serviceMapper/common.py)
   - `create_modeled_config()` - Lines 30-39
   - `get_modeled_config()` - Lines 69-75
   - `get_network_config()` - Lines 134-141

2. **Network Service Operations**
   - `get_network_service()` - Lines 83-99
   - `patch_service_diffs()` - Lines 154-193

3. **SLM Operations**
   - `slm_verification_process()` - Lines 268-274
   - `slm_traffic_verification()` - Lines 276-320

4. **Device Communication**
   - `__send_commands()` - Lines 360-363
   - Network function queries

**Implementation Example**:

```python
def get_modeled_config(self, config_request_data) -> dict:
    """Create config modeler resource with OTel instrumentation"""

    # Create span for this operation
    with mdso_span(
        f"mdso.config_modeler.{config_request_data['requested_model']}",
        circuit_id=config_request_data['circuit_id'],
        device=config_request_data['device']['Host Name']
    ) as span:
        payload = self.create_config_modeler_payload(config_request_data)

        # Add payload attributes
        span.set_attribute("vendor", config_request_data['device']['Vendor'])
        span.set_attribute("location", config_request_data['device']['location'])
        span.set_attribute("model_type", config_request_data['requested_model'])

        self.otel_log(
            "Creating config model",
            requested_model=config_request_data['requested_model'],
            vendor=config_request_data['device']['Vendor']
        )

        config_modeler = self.create_modeled_config(payload)

        # Record success
        span.set_attribute("modeled_config_created", True)

        return config_modeler.resource["properties"]["modeled_config"]
```

### Phase 3: Error Tracking and Pattern Matching

**Objective**: Automatically categorize and track errors using `ErrorPatternMatcher`.

**Implementation**:

```python
from otel_instrumentation.otel_mdso_utils import ErrorPatternMatcher

class OTelMixin:
    def __init_otel__(self):
        # ... existing setup ...
        self.error_matcher = ErrorPatternMatcher()

    def otel_error_handler(self, error_message: str, exception: Exception = None):
        """
        Enhanced error handling with OTel tracking

        Args:
            error_message: Error message
            exception: Optional exception object
        """
        # Get current span
        span = trace.get_current_span()

        # Categorize error
        error_info = self.error_matcher.categorize_error(error_message)

        # Extract identifiers from error
        identifiers = self.error_matcher.extract_all_identifiers(error_message)

        # Add error attributes to span
        if span and span.is_recording():
            self.span_helper.add_error_attributes(
                span,
                error_category=error_info['category'],
                error_message=error_message
            )

            # Add extracted identifiers
            for key, value in identifiers.items():
                if value:
                    span.set_attribute(f"error.extracted.{key}", value)

            # Set span status
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_message[:500]))

        # Log structured error
        self.otel_logger.error(
            error_message,
            error_category=error_info['category'],
            error_type=error_info['type'],
            **identifiers
        )
```

**Usage in existing error handling**:

```python
# In common_plan.py exit_error method
def exit_error(self, reason=None):
    """called when there is a plan failure"""

    if reason is None:
        msg = f"Error when running class {self.the_class}, please check file {self.log_file}."
    else:
        msg = f"Error in {self.the_class}, {reason}.  Please check file: {self.log_file}"

    # Existing logging
    self.logger.error(msg)

    # Add OTel error tracking
    if hasattr(self, 'otel_error_handler'):
        self.otel_error_handler(msg)

    # ... rest of existing logic ...
```

### Phase 4: Correlation Context Propagation

**Objective**: Ensure correlation IDs flow through the entire execution chain.

**Implementation Points**:

1. **Resource Creation**:
```python
def _create_resource(self, label: str, properties: dict, wait_active=False):
    """Create child resource with correlation context"""

    with mdso_span("mdso.resource.create", resource_type=self.product) as span:
        # Inject correlation into child resource properties
        if hasattr(self, 'circuit_id'):
            properties['_otel_parent_circuit_id'] = self.circuit_id
            span.set_attribute("circuit_id", self.circuit_id)

        # ... existing create logic ...
```

2. **Circuit Details Handler**:
```python
def _set_circuit_details(self):
    """Set circuit details with span tracking"""

    with mdso_span("mdso.circuit_details.fetch", circuit_id=self.circuit_id) as span:
        handler = CircuitDetailsHandler(self, self.circuit_id, self.operation)

        # Track results
        span.set_attribute("circuit_details_id", handler.circuit_details_id)
        span.set_attribute("leg_count", len(handler.leg_details_ids))

        self.circuit_details = handler.circuit_details
        self.circuit_details_id = handler.circuit_details_id
        self.leg_details_ids = handler.leg_details_ids
```

### Phase 5: Integration with Existing Splunk Logger

**Objective**: Bridge OTel structured logging with existing Splunk infrastructure.

**Approach**: Configure structlog to also write to Splunk log file.

```python
def splunk_otel_logger_setup(self):
    """
    Enhanced Splunk logger with OTel structured logging

    Returns:
        Combined logger that writes to both Splunk file and OTel
    """
    import structlog
    from logging.handlers import RotatingFileHandler

    # Existing Splunk file handler
    if not os.path.exists("/bp2/log/splunk-logs"):
        os.makedirs("/bp2/log/splunk-logs")

    splunk_file_handler = RotatingFileHandler(
        "/bp2/log/splunk-logs/sensor-templates-splunk.log",
        backupCount=10
    )

    # Configure structlog with Splunk output
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),  # JSON for Splunk parsing
        ],
        logger_factory=structlog.PrintLoggerFactory(file=splunk_file_handler.stream),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("mdso-scriptplan")
```

## Migration Path

### Incremental Adoption Strategy

**Week 1-2: Foundation**
1. Add `otel_instrumentation` package to scripts directory
2. Create `OTelMixin` class
3. Document usage examples
4. Create unit tests

**Week 3-4: Pilot Products**
1. Instrument 2-3 high-priority products (e.g., ServiceMapper, ConfigModeler)
2. Validate telemetry in Grafana/Tempo
3. Gather feedback from operations team
4. Refine patterns based on learnings

**Week 5-6: Expand Coverage**
1. Instrument 5-10 additional products
2. Add error categorization
3. Implement correlation propagation
4. Document common patterns

**Week 7-8: Full Rollout**
1. Instrument remaining products
2. Update CommonPlan base class with optional OTel support
3. Create migration guide
4. Training for development team

### Backward Compatibility Guarantees

1. **No Breaking Changes**: All OTel features are opt-in
2. **Existing Logging Preserved**: Standard Python logging continues to work
3. **Splunk Compatibility**: Splunk logs maintained in current format
4. **Gradual Migration**: Products can adopt OTel individually
5. **Rollback Plan**: OTel can be disabled via environment variable

## Configuration Management

### Environment Variables

```bash
# OTel Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:55681  # Meta server
OTEL_ENABLED=true                                      # Enable/disable OTel
MDSO_ENV=dev                                           # Environment (dev/staging/prod)
OTEL_LOG_LEVEL=INFO                                    # OTel log verbosity

# Existing Configuration (preserved)
LOG_LEVEL=INFO
SPLUNK_ENABLED=true
```

### Feature Flags

```python
# In common_plan.py
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() == "true"

def run(self):
    # Conditional OTel initialization
    if OTEL_ENABLED and hasattr(self, '__init_otel__'):
        self.__init_otel__()

    # ... rest of run method ...
```

## Testing Strategy

### Unit Tests

```python
# tests/test_otel_mixin.py
import unittest
from scripts.otel_mixin import OTelMixin
from opentelemetry import trace

class TestOTelMixin(unittest.TestCase):
    def test_otel_initialization(self):
        """Test OTel setup initializes correctly"""
        mixin = OTelMixin()
        mixin.__init_otel__()

        self.assertIsNotNone(mixin.tracer)
        self.assertIsNotNone(mixin.otel_logger)
        self.assertIsNotNone(mixin.span_helper)

    def test_correlation_context(self):
        """Test correlation context injection"""
        mixin = OTelMixin()
        mixin.__init_otel__()
        mixin.circuit_id = "99.TEST.123456..FIA"
        mixin.resource_id = "550e8400-e29b-41d4-a716-446655440000"

        with mixin.otel_run_wrapper() as span:
            self.assertEqual(span.attributes['circuit_id'], mixin.circuit_id)
```

### Integration Tests

```python
# tests/integration/test_service_mapper_otel.py
def test_service_mapper_with_otel(mock_bpo):
    """Test ServiceMapper with OTel instrumentation"""
    from scripts.serviceMapper.common import Common

    mapper = Common()
    mapper.__init_otel__()

    # Execute operation
    result = mapper.get_network_service()

    # Verify spans were created
    spans = get_recorded_spans()
    assert any('mdso.product.Common' in s.name for s in spans)
```

## Monitoring and Observability

### Key Metrics to Track

1. **Product Execution**:
   - Execution duration per product
   - Success/failure rates
   - Resource creation counts

2. **Network Operations**:
   - Device communication latency
   - Config modeling time
   - Network service query duration

3. **Error Patterns**:
   - Error categories distribution
   - Top failing circuit IDs
   - Vendor-specific error rates

### Grafana Dashboards

**Dashboard 1: Product Overview**
- Products executed (count by type)
- Average execution time
- Success rate trend
- Top errors by category

**Dashboard 2: Circuit Analysis**
- Circuit processing time distribution
- Circuits by vendor
- Service type breakdown
- SLM verification rates

**Dashboard 3: Network Function Health**
- Device communication success rate
- Average command execution time
- Devices by communication state
- Vendor distribution

## Dependencies and Requirements

### Python Packages

```txt
# requirements.txt additions
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp-proto-http>=1.20.0
structlog>=23.1.0
```

### Infrastructure

- Meta server OTLP endpoint: `http://159.56.4.94:55681`
- Grafana instance with Tempo data source
- Loki for log aggregation (optional)

## Risks and Mitigation

### Risk 1: Performance Impact
**Mitigation**:
- Batch span processor with 5-second delay
- Async OTLP export
- Sampling for high-volume operations
- Performance benchmarking before rollout

### Risk 2: Breaking Existing Functionality
**Mitigation**:
- Opt-in design via mixin
- Extensive unit and integration tests
- Gradual rollout with rollback capability
- Feature flag to disable OTel

### Risk 3: Learning Curve
**Mitigation**:
- Clear documentation with examples
- Training sessions for dev team
- Code review support
- Slack channel for questions

### Risk 4: Increased Complexity
**Mitigation**:
- Encapsulate OTel logic in mixin
- Provide helper methods for common patterns
- Maintain backward compatibility
- Document common pitfalls

## Success Criteria

1. **Adoption**: 80% of products instrumented within 8 weeks
2. **Performance**: <5% overhead on product execution time
3. **Visibility**: End-to-end trace visibility for circuit operations
4. **Reliability**: Zero production incidents caused by OTel integration
5. **Developer Experience**: 90% positive feedback from dev team

## Conclusion

This strategy provides a low-risk, incremental path to adopting OpenTelemetry instrumentation in the MDSO scripts directory. By leveraging the existing `otel_instrumentation` classes and using a mixin-based approach, we can add comprehensive observability without disrupting existing functionality.

The key principles are:
- **Backward compatibility**: No breaking changes
- **Gradual adoption**: Products opt-in individually
- **Dual logging**: OTel complements, doesn't replace existing logging
- **Vendor agnostic**: Works across all MDSO products and vendors
- **Production ready**: Feature flags, testing, and rollback plans

## Next Steps

1. Review this strategy with the team
2. Set up OTel test environment
3. Create OTelMixin prototype
4. Instrument pilot product (ServiceMapper)
5. Validate telemetry in Grafana
6. Iterate based on feedback
7. Roll out to remaining products

## Appendix A: Code Location Reference

### Current Logging Implementation
- **File**: `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/common_plan.py`
- **Lines**: 387-412 (logger setup), 5203-5223 (Splunk logger)

### OTel Instrumentation Classes
- **Files**:
  - `.archive/otel_instrumentation/instrumentation.py`
  - `.archive/otel_instrumentation/otel_mdso_utils.py`
  - `v2/corr-station-updated/seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/`

### Key Products to Instrument
- `scripts/serviceMapper/common.py`
- `scripts/fabricator/common.py`
- `scripts/configmodeler/`
- `scripts/deviceconfiguration/`
- `scripts/networkservice/`

## Appendix B: Example Full Product Implementation

```python
# scripts/serviceMapper/common_otel.py
"""
ServiceMapper with full OTel instrumentation
Example implementation showing all patterns
"""

from scripts.common_plan import CommonPlan
from scripts.otel_mixin import OTelMixin
from otel_instrumentation.instrumentation import mdso_span
from otel_instrumentation.otel_mdso_utils import MDSOSpanHelper

class Common(CommonPlan, OTelMixin):
    """
    ServiceMapper with OTel instrumentation
    """

    def run(self):
        """Run with OTel root span"""
        # Initialize OTel
        self.__init_otel__()

        # Create root span for entire product execution
        with self.otel_run_wrapper():
            return super().run()

    def get_modeled_config(self, config_request_data) -> dict:
        """Get modeled config with span tracking"""

        with mdso_span(
            "mdso.config_modeler.create",
            circuit_id=config_request_data['circuit_id'],
            device=config_request_data['device']['Host Name'],
            vendor=config_request_data['device']['Vendor'],
            model_type=config_request_data['requested_model']
        ) as span:

            payload = self.create_config_modeler_payload(config_request_data)

            self.otel_log(
                "Creating config modeler resource",
                level="info",
                requested_model=config_request_data['requested_model'],
                device=config_request_data['device']['Host Name']
            )

            try:
                config_modeler = self.create_modeled_config(payload)

                # Success - add attributes
                span.set_attribute("success", True)
                span.set_attribute("config_modeler_id", config_modeler.resource_id)

                return config_modeler.resource["properties"]["modeled_config"]

            except Exception as e:
                # Error - track with pattern matcher
                self.otel_error_handler(str(e), e)
                raise

    def slm_traffic_verification(self):
        """SLM verification with detailed span tracking"""

        with mdso_span(
            "mdso.slm.traffic_verification",
            circuit_id=self.circuit_id
        ) as span:

            # Create slm resource
            slm_service = self.get_resource(
                self.create_slm_service_finder_resource().resource_id
            )

            # Extract probe data
            probe_data = slm_service["properties"]["slm_configuration"]["probe"]

            # Add span attributes
            span.set_attribute("probe.fqdn", probe_data["device_details"]["fqdn"])
            span.set_attribute("probe.vendor", probe_data["device_details"]["vendor"])

            # Send commands with sub-spans
            with mdso_span("mdso.slm.send_initial_commands") as cmd_span:
                initial_output = self.__send_commands(
                    network_function["providerResourceId"],
                    command_file,
                    command_data
                ).json()["result"]

                cmd_span.set_attribute("output_received", initial_output is not None)

            # Wait and send second command
            sleep(1)

            with mdso_span("mdso.slm.send_secondary_commands") as cmd_span:
                second_output = self.__send_commands(
                    network_function["providerResourceId"],
                    command_file,
                    command_data
                ).json()["result"]

            # Verify traffic
            traffic_passing = self.is_slm_traffic_passing_bidirectionally(
                initial_output,
                second_output,
                probe_data["device_details"]["vendor"],
                command_data["ma"]
            )

            # Record result
            span.set_attribute("slm_traffic_passing", traffic_passing)

            self.otel_log(
                "SLM traffic verification complete",
                level="info",
                traffic_passing=traffic_passing,
                probe_fqdn=probe_data["device_details"]["fqdn"]
            )

            return traffic_passing
```
