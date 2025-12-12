"""
MDSOInstrumentation - Unified OpenTelemetry Instrumentation Class

This class provides a clean, object-oriented interface for instrumenting
MDSO products with OpenTelemetry. It consolidates functionality from
instrumentation.py and otel_mdso_utils.py into a single, easy-to-use class.

Usage in a plan's run() method:
    def run(self):
        instrumentation = MDSOInstrumentation(
            service_name="my-scriptplan",
            environment="prod"
        )
        instrumentation.setup()

        with instrumentation.span("operation.name", circuit_id="123") as span:
            # Do work
            instrumentation.add_topology_attrs(span, vendor="juniper")

Author: Derrick Golden
Version: 2.0.0
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

from opentelemetry import trace, baggage, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode, SpanKind
import structlog

# Import utilities from existing modules
from .otel_mdso_utils import (
    VENDOR_RESOURCE_MAPPING,
    MDSORegexPatterns,
    MDSOSpanHelper,
    ErrorPatternMatcher,
    extract_vendor_from_node_name,
    extract_fqdn_from_node_name,
    validate_beorn_response,
)

logger = logging.getLogger(__name__)

# Try importing Pyroscope
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    PYROSCOPE_AVAILABLE = False
    logger.warning("Pyroscope not available - continuous profiling disabled")


class MDSOInstrumentation:
    """
    Unified OpenTelemetry instrumentation for MDSO products

    This class provides a complete instrumentation solution for MDSO scriptplans,
    SENSE apps, and other products. It handles:
    - Tracer setup and configuration
    - Span creation with MDSO-specific attributes
    - Correlation context management
    - Structured logging
    - Error tracking
    - Topology and network function instrumentation

    Attributes:
        service_name: Name of the service being instrumented
        environment: Deployment environment (dev/staging/prod)
        version: Service version
        tracer: OpenTelemetry tracer instance
        logger: Structured logger instance
        regex_patterns: MDSORegexPatterns instance for log parsing
        error_matcher: ErrorPatternMatcher for error categorization
    """

    def __init__(
        self,
        service_name: str = "mdso-scriptplan",
        endpoint: Optional[str] = None,
        environment: str = "dev",
        version: str = "1.0.0",
        batch_config: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize MDSOInstrumentation

        Args:
            service_name: Service name for resource attributes
            endpoint: OTLP exporter endpoint (defaults to env var or Meta server)
            environment: Deployment environment (dev/staging/prod)
            version: Service version
            batch_config: Optional batch processor config:
                - max_queue_size: Maximum queue size (default: 2048)
                - max_export_batch_size: Maximum batch size (default: 512)
                - schedule_delay_millis: Delay in milliseconds (default: 5000)

        Example:
            >>> instr = MDSOInstrumentation(
            ...     service_name="circuit-provisioner",
            ...     environment="prod",
            ...     version="2.1.0"
            ... )
            >>> instr.setup()
        """
        self.service_name = service_name
        self.endpoint = endpoint or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://159.56.4.94:55681"
        )
        self.environment = environment
        self.version = version

        # Batch processor configuration
        self.batch_config = batch_config or {
            "max_queue_size": 2048,
            "max_export_batch_size": 512,
            "schedule_delay_millis": 5000,
        }

        # Initialize components (set in setup())
        self.tracer: Optional[trace.Tracer] = None
        self.logger: Optional[structlog.BoundLogger] = None

        # Initialize utilities
        self.regex_patterns = MDSORegexPatterns()
        self.span_helper = MDSOSpanHelper()
        self.error_matcher = ErrorPatternMatcher()

        self._is_setup = False

    def setup(self) -> 'MDSOInstrumentation':
        """
        Setup OpenTelemetry tracer and structured logger

        This method must be called before using any instrumentation features.
        It configures the tracer provider, OTLP exporter, and structured logging.

        Returns:
            Self for method chaining

        Example:
            >>> instr = MDSOInstrumentation("my-service").setup()
            >>> with instr.span("operation") as span:
            ...     pass
        """
        if self._is_setup:
            logger.warning("MDSOInstrumentation already setup, skipping")
            return self

        # Create resource with service metadata
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": self.version,
            "deployment.environment": self.environment,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "1.20.0",
            "mdso.instrumentation.version": "2.0.0",
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{self.endpoint}/v1/traces",
            timeout=30,
        )

        # Add batch span processor
        processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=self.batch_config["max_queue_size"],
            max_export_batch_size=self.batch_config["max_export_batch_size"],
            schedule_delay_millis=self.batch_config["schedule_delay_millis"],
        )
        provider.add_span_processor(processor)

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer
        self.tracer = trace.get_tracer(__name__, version=self.version)

        # Setup structured logger
        self._setup_logger()

        self._is_setup = True

        logger.info(
            f"MDSOInstrumentation initialized: "
            f"service={self.service_name}, endpoint={self.endpoint}, env={self.environment}"
        )

        return self

    def _setup_logger(self):
        """Setup structured logger for OTel-compatible logging"""
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.BoundLogger,
            cache_logger_on_first_use=True,
        )
        self.logger = structlog.get_logger(self.service_name)

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        **attributes: Any
    ):
        """
        Context manager for creating MDSO spans

        Automatically sets span status and records exceptions.

        Args:
            name: Span name (e.g., "mdso.product.DeviceOnboarder")
            kind: Span kind (INTERNAL, CLIENT, SERVER, etc.)
            **attributes: Span attributes (circuit_id, vendor, etc.)

        Yields:
            Active span

        Example:
            >>> with instr.span("provision.circuit", circuit_id="123") as span:
            ...     span.set_attribute("device_count", 5)
            ...     # Do work
        """
        if not self._is_setup or not self.tracer:
            raise RuntimeError("MDSOInstrumentation not setup. Call setup() first.")

        # Merge with default MDSO attributes
        span_attributes = {
            "mdso.component": "scriptplan",
            **attributes
        }

        # Create and start span
        span = self.tracer.start_span(
            name=name,
            kind=kind,
            attributes=span_attributes
        )

        # Use span as current context
        ctx = trace.set_span_in_context(span)
        token = context.attach(ctx)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            context.detach(token)
            span.end()

    def inject_context(
        self,
        circuit_id: Optional[str] = None,
        product_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Inject correlation keys into current trace context

        Sets both span attributes and baggage for cross-service propagation.

        Args:
            circuit_id: Circuit identifier
            product_id: Product identifier
            resource_id: Resource identifier
            resource_type_id: Resource type identifier

        Returns:
            Dictionary of injected context

        Example:
            >>> instr.inject_context(
            ...     circuit_id="550e8400-e29b-41d4-a716-446655440000",
            ...     resource_id="7c9e6679-7425-40de-944b-e07fc1f90ae7"
            ... )
        """
        # Get current span
        span = trace.get_current_span()

        # Collect context to inject
        correlation_context = {}

        # Set span attributes
        if span and span.is_recording():
            if circuit_id:
                span.set_attribute("circuit_id", circuit_id)
                correlation_context["circuit_id"] = circuit_id
            if product_id:
                span.set_attribute("product_id", product_id)
                correlation_context["product_id"] = product_id
            if resource_id:
                span.set_attribute("resource_id", resource_id)
                correlation_context["resource_id"] = resource_id
            if resource_type_id:
                span.set_attribute("resource_type_id", resource_type_id)
                correlation_context["resource_type_id"] = resource_type_id

        # Set baggage for propagation
        ctx = context.get_current()
        if circuit_id:
            ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
        if product_id:
            ctx = baggage.set_baggage("product_id", product_id, context=ctx)
        if resource_id:
            ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)
        if resource_type_id:
            ctx = baggage.set_baggage("resource_type_id", resource_type_id, context=ctx)

        context.attach(ctx)

        return correlation_context

    def extract_context(self) -> Dict[str, Optional[str]]:
        """
        Extract correlation keys from current baggage

        Returns:
            Dictionary with correlation keys (may contain None values)

        Example:
            >>> ctx = instr.extract_context()
            >>> print(ctx["circuit_id"])
            550e8400-e29b-41d4-a716-446655440000
        """
        return {
            "circuit_id": baggage.get_baggage("circuit_id"),
            "product_id": baggage.get_baggage("product_id"),
            "resource_id": baggage.get_baggage("resource_id"),
            "resource_type_id": baggage.get_baggage("resource_type_id"),
        }

    def add_topology_attrs(
        self,
        span: trace.Span,
        service_type: Optional[str] = None,
        vendor: Optional[str] = None,
        fqdn: Optional[str] = None,
        topology_node_count: Optional[int] = None,
        validation_status: Optional[bool] = None,
    ):
        """
        Add Beorn topology-specific attributes to a span

        Args:
            span: Active OTEL span
            service_type: Service type (FIA, ELAN, ELINE, etc.)
            vendor: Device vendor (adva, juniper, cisco, rad)
            fqdn: Device FQDN
            topology_node_count: Number of nodes in topology
            validation_status: Whether topology validation passed

        Example:
            >>> with instr.span("beorn.topology.fetch") as span:
            ...     topology = fetch_topology()
            ...     instr.add_topology_attrs(
            ...         span,
            ...         service_type="FIA",
            ...         vendor="juniper",
            ...         topology_node_count=len(topology)
            ...     )
        """
        self.span_helper.add_topology_attributes(
            span,
            service_type=service_type,
            vendor=vendor,
            fqdn=fqdn,
            topology_node_count=topology_node_count,
            validation_status=validation_status,
        )

    def add_network_function_attrs(
        self,
        span: trace.Span,
        communication_state: Optional[str] = None,
        ip_address: Optional[str] = None,
        vendor: Optional[str] = None,
        device_role: Optional[str] = None,
        provider_resource_id: Optional[str] = None,
    ):
        """
        Add network function-specific attributes to a span

        Args:
            span: Active OTEL span
            communication_state: Device communication state
            ip_address: Device IP address
            vendor: Device vendor
            device_role: Device role (CPE, PE)
            provider_resource_id: MDSO provider resource ID

        Example:
            >>> with instr.span("device.configure", tid=device.tid) as span:
            ...     instr.add_network_function_attrs(
            ...         span,
            ...         vendor="juniper",
            ...         ip_address="10.0.0.1",
            ...         device_role="PE"
            ...     )
        """
        self.span_helper.add_network_function_attributes(
            span,
            communication_state=communication_state,
            ip_address=ip_address,
            vendor=vendor,
            device_role=device_role,
            provider_resource_id=provider_resource_id,
        )

    def add_error_attrs(
        self,
        span: trace.Span,
        error_code: Optional[str] = None,
        error_category: Optional[str] = None,
        error_message: Optional[str] = None,
        is_new_error: Optional[bool] = None,
    ):
        """
        Add error-tracking attributes to a span

        Args:
            span: Active OTEL span
            error_code: Error code (e.g., DE-1000)
            error_category: Categorized error type
            error_message: Raw error message (will be truncated to 500 chars)
            is_new_error: Whether this is a newly discovered error

        Example:
            >>> try:
            ...     configure_device()
            ... except Exception as e:
            ...     instr.add_error_attrs(
            ...         span,
            ...         error_message=str(e),
            ...         error_category="DEVICE_ERROR"
            ...     )
        """
        self.span_helper.add_error_attributes(
            span,
            error_code=error_code,
            error_category=error_category,
            error_message=error_message,
            is_new_error=is_new_error,
        )

    def log(
        self,
        message: str,
        state: str = "STARTED",
        **context: Any
    ):
        """
        Emit structured log with optional span event

        Args:
            message: Log message
            state: Process state (STARTED, COMPLETED, FAILED)
            **context: Additional context fields (circuit_id, resource_id, etc.)

        Example:
            >>> instr.log("Starting provisioning", "STARTED", circuit_id="123")
            >>> # ... do work ...
            >>> instr.log("Provisioning complete", "COMPLETED", circuit_id="123")
        """
        if not self.logger:
            logger.warning("Logger not setup, skipping log")
            return

        # Determine log level
        if state == "FAILED":
            log_level = "error"
        elif state == "COMPLETED":
            log_level = "info"
        else:
            log_level = "debug"

        # Emit structured log
        getattr(self.logger, log_level)(message, state=state, **context)

        # Add span event if we have a current span
        span = trace.get_current_span()
        if span and span.is_recording():
            span.add_event(
                name=f"process.{state.lower()}",
                attributes={
                    "message": message,
                    "state": state,
                    **context
                }
            )

    def categorize_error(self, error_message: str) -> Dict[str, str]:
        """
        Categorize an error message using regex patterns

        Args:
            error_message: Raw error text

        Returns:
            Dictionary with category and type

        Example:
            >>> error = "IP 10.0.0.1 already exists on device"
            >>> category = instr.categorize_error(error)
            >>> print(category)
            {'category': 'IP_CONFLICT_ERROR', 'type': 'IP Already Exists'}
        """
        return self.error_matcher.categorize_error(error_message)

    def extract_identifiers(self, text: str) -> Dict[str, Any]:
        """
        Extract all MDSO identifiers from text

        Args:
            text: Text to parse

        Returns:
            Dictionary of extracted identifiers

        Example:
            >>> ids = instr.extract_identifiers(log_message)
            >>> print(ids["circuit_id"])
            22.ABCD.123456..
        """
        return self.error_matcher.extract_all_identifiers(text)

    def setup_pyroscope(
        self,
        server_address: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Setup Pyroscope continuous profiling

        Args:
            server_address: Pyroscope server URL (defaults to env var or local)
            tags: Additional tags for profiling data

        Returns:
            True if successfully configured, False otherwise

        Example:
            >>> instr.setup_pyroscope(tags={"team": "network-ops"})
        """
        if not PYROSCOPE_AVAILABLE:
            logger.warning("Pyroscope not available - install with: pip install pyroscope-io")
            return False

        server_address = server_address or os.getenv(
            "PYROSCOPE_SERVER_ADDRESS",
            "http://pyroscope:4040"
        )

        # Merge default tags with provided tags
        profiling_tags = {
            "environment": self.environment,
            "version": self.version,
            **(tags or {})
        }

        try:
            pyroscope.configure(
                application_name=self.service_name,
                server_address=server_address,
                tags=profiling_tags
            )
            logger.info(
                f"Pyroscope profiling enabled: "
                f"service={self.service_name}, server={server_address}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to configure Pyroscope: {e}")
            return False


# Convenience functions for backward compatibility
def create_instrumentation(
    service_name: str = "mdso-scriptplan",
    **kwargs
) -> MDSOInstrumentation:
    """
    Convenience function to create and setup instrumentation

    Args:
        service_name: Service name
        **kwargs: Additional arguments for MDSOInstrumentation

    Returns:
        Configured MDSOInstrumentation instance

    Example:
        >>> instr = create_instrumentation("my-service", environment="prod")
        >>> with instr.span("operation") as span:
        ...     pass
    """
    return MDSOInstrumentation(service_name, **kwargs).setup()
