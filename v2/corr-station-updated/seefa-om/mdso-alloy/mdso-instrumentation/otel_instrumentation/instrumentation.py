"""
instrumentation.py - Utility functions for OTel instrumentation

Provides standalone functions for products that don't inherit from OTelPlan
"""

import os
import logging
from typing import Optional, Dict, Any

from opentelemetry import trace, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import structlog

logger = logging.getLogger(__name__)

# Try importing Pyroscope
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    PYROSCOPE_AVAILABLE = False
    logger.warning("Pyroscope not available")


def setup_otel(
    service_name: str = "mdso-scriptplan",
    endpoint: str = None,
    environment: str = "dev",
    version: str = "1.0.0"
) -> trace.Tracer:
    """
    Setup OpenTelemetry tracer for MDSO scriptplan

    Args:
        service_name: Service name for resource attributes
        endpoint: OTLP exporter endpoint (defaults to env var or Meta server)
        environment: Deployment environment (dev/staging/prod)
        version: Service version

    Returns:
        Configured tracer instance

    Example:
        >>> tracer = setup_otel("mdso-scriptplan", environment="dev")
        >>> with tracer.start_as_current_span("my_operation") as span:
        ...     span.set_attribute("circuit_id", "123-456")
        ...     # ... do work ...
    """
    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://159.56.4.94:55681")

    # Create resource with service metadata
    resource = Resource.create({
        "service.name": service_name,
        "service.version": version,
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
        "telemetry.sdk.version": "1.20.0",
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        timeout=30,
    )

    # Add batch span processor
    processor = BatchSpanProcessor(
        otlp_exporter,
        max_queue_size=2048,
        max_export_batch_size=512,
        schedule_delay_millis=5000,
    )
    provider.add_span_processor(processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    logger.info(f"OTel initialized: service={service_name}, endpoint={endpoint}, env={environment}")

    return trace.get_tracer(__name__, version=version)


def get_otel_logger(service_name: str = "mdso-scriptplan") -> structlog.BoundLogger:
    """
    Get structured logger for OTel-compatible logging

    Args:
        service_name: Service name to bind to logger

    Returns:
        Structured logger instance

    Example:
        >>> logger = get_otel_logger("mdso-scriptplan")
        >>> logger.info("Processing started", circuit_id="123", resource_id="456")
    """
    # Configure structlog
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

    # Create bound logger with service context
    return structlog.get_logger(service_name)


def otel_enter_exit_log(
    message: str,
    state: str = "STARTED",
    tracer: trace.Tracer = None,
    **context: Any
):
    """
    Standalone enter_exit_log function for products that don't inherit OTelPlan

    Emits structured log and optional span event.

    Args:
        message: Log message
        state: Process state (STARTED, COMPLETED, FAILED)
        tracer: Optional tracer instance (will use global if not provided)
        **context: Additional context fields (circuit_id, resource_id, etc.)

    Example:
        >>> otel_enter_exit_log("Starting provisioning", "STARTED",
        ...                     circuit_id="123", resource_id="456")
        >>> # ... do work ...
        >>> otel_enter_exit_log("Provisioning complete", "COMPLETED",
        ...                     circuit_id="123", resource_id="456")
    """
    logger = get_otel_logger()

    # Determine log level
    if state == "FAILED":
        log_level = "error"
    elif state == "COMPLETED":
        log_level = "info"
    else:
        log_level = "debug"

    # Emit structured log
    getattr(logger, log_level)(message, state=state, **context)

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


def inject_correlation_context(
    circuit_id: Optional[str] = None,
    product_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Inject correlation keys into current trace context

    Sets both span attributes and baggage for propagation.

    Args:
        circuit_id: Circuit identifier
        product_id: Product identifier
        resource_id: Resource identifier
        resource_type_id: Resource type identifier

    Returns:
        Dictionary of injected context

    Example:
        >>> inject_correlation_context(
        ...     circuit_id="550e8400-e29b-41d4-a716-446655440000",
        ...     resource_id="7c9e6679-7425-40de-944b-e07fc1f90ae7"
        ... )
    """
    from opentelemetry import context

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


def extract_correlation_context() -> Dict[str, Optional[str]]:
    """
    Extract correlation keys from current baggage

    Returns:
        Dictionary with correlation keys (may contain None values)

    Example:
        >>> context = extract_correlation_context()
        >>> print(context["circuit_id"])
        550e8400-e29b-41d4-a716-446655440000
    """
    return {
        "circuit_id": baggage.get_baggage("circuit_id"),
        "product_id": baggage.get_baggage("product_id"),
        "resource_id": baggage.get_baggage("resource_id"),
        "resource_type_id": baggage.get_baggage("resource_type_id"),
    }


def create_mdso_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    tracer: Optional[trace.Tracer] = None
) -> trace.Span:
    """
    Create a span with MDSO-specific attributes

    Args:
        name: Span name (e.g., "mdso.product.CircuitDetailsCollector")
        kind: Span kind (INTERNAL, CLIENT, SERVER, etc.)
        attributes: Additional attributes
        tracer: Optional tracer (uses global if not provided)

    Returns:
        Started span (remember to call .end()!)

    Example:
        >>> span = create_mdso_span(
        ...     "mdso.product.ServiceProvisioner",
        ...     attributes={"circuit_id": "123", "vendor": "JUNIPER"}
        ... )
        >>> try:
        ...     # ... do work ...
        ...     span.set_status(trace.Status(trace.StatusCode.OK))
        ... except Exception as e:
        ...     span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        ...     raise
        ... finally:
        ...     span.end()
    """
    if tracer is None:
        tracer = trace.get_tracer(__name__)

    # Merge with default MDSO attributes
    span_attributes = {
        "mdso.component": "scriptplan",
        **(attributes or {})
    }

    return tracer.start_span(
        name=name,
        kind=kind,
        attributes=span_attributes
    )


# Context manager for easier span usage
class mdso_span:
    """
    Context manager for MDSO spans

    Example:
        >>> with mdso_span("mdso.product.DeviceOnboarder", circuit_id="123") as span:
        ...     # ... do work ...
        ...     span.set_attribute("device_count", 5)
    """

    def __init__(
        self,
        name: str,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        **attributes: Any
    ):
        self.name = name
        self.kind = kind
        self.attributes = attributes
        self.span = None

    def __enter__(self) -> trace.Span:
        self.span = create_mdso_span(
            name=self.name,
            kind=self.kind,
            attributes=self.attributes
        )
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type is not None:
                self.span.set_status(
                    trace.Status(trace.StatusCode.ERROR, str(exc_val))
                )
            else:
                self.span.set_status(trace.Status(trace.StatusCode.OK))
            self.span.end()
        return False  # Don't suppress exceptions


def setup_pyroscope(
    service_name: str = "mdso-scriptplan",
    server_address: str = None,
    environment: str = "dev",
    version: str = "1.0.0",
    tags: Optional[Dict[str, str]] = None
) -> bool:
    """
    Setup Pyroscope continuous profiling for MDSO scripts

    Args:
        service_name: Application name for profiling
        server_address: Pyroscope server URL (defaults to env var or local instance)
        environment: Deployment environment (dev/staging/prod)
        version: Service version
        tags: Additional tags for profiling data

    Returns:
        True if Pyroscope was successfully configured, False otherwise

    Example:
        >>> from instrumentation import setup_pyroscope
        >>> setup_pyroscope("mdso-circuit-provisioner", environment="prod", tags={"team": "network-ops"})
        >>> # Script execution will now be profiled
    """
    if not PYROSCOPE_AVAILABLE:
        logger.warning("Pyroscope not available - install with: pip install pyroscope-io")
        return False

    server_address = server_address or os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040")

    # Merge default tags with provided tags
    profiling_tags = {
        "environment": environment,
        "version": version,
        **(tags or {})
    }

    try:
        pyroscope.configure(
            application_name=service_name,
            server_address=server_address,
            tags=profiling_tags
        )
        logger.info(f"Pyroscope profiling enabled: service={service_name}, server={server_address}, env={environment}")
        return True
    except Exception as e:
        logger.error(f"Failed to configure Pyroscope: {e}")
        return False
