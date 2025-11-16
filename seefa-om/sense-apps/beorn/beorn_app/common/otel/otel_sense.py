"""
Consolidated OpenTelemetry Instrumentation for SENSE Apps
Combines best practices from common_sense_telemetry and otel_utils
Adds MDSO-specific instrumentation without resource-intensive middleware

Author: Derrick Golden
Version: 2.0.0
"""

import os
import time
import uuid
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps

from opentelemetry import trace, baggage, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode
import structlog

logger = logging.getLogger(__name__)

# ========================================
# Configuration
# ========================================

DEFAULT_CORRELATION_GATEWAY = os.getenv(
    "CORRELATION_GATEWAY_URL",
    "http://159.56.4.94:8080"
)

# MDSO-specific baggage keys for correlation
MDSO_BAGGAGE_KEYS = [
    "circuit_id",
    "resource_id",
    "product_id",
    "product_type",
    "tid",
    "fqdn",
    "provider_resource_id",
    "service_type",
    "vendor",
]


# ========================================
# Core Initialization
# ========================================

def setup_otel_sense(
    service_name: str,
    service_version: str = "1.0.0",
    environment: Optional[str] = None,
    correlation_gateway: Optional[str] = None,
) -> trace.Tracer:
    """
    Initialize OpenTelemetry for SENSE applications

    Optimized for performance - no heavy middleware

    Args:
        service_name: Service name (beorn, arda, palantir)
        service_version: Version string
        environment: Environment (dev/staging/prod)
        correlation_gateway: Correlation gateway endpoint

    Returns:
        Configured tracer instance

    Example:
        >>> from common.otel_sense import setup_otel_sense
        >>> tracer = setup_otel_sense("beorn", "2408.0.244")
    """
    environment = environment or os.getenv("DEPLOYMENT_ENV", "dev")
    correlation_gateway = correlation_gateway or DEFAULT_CORRELATION_GATEWAY

    # Resource attributes
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": "sense",
        "service.version": service_version,
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter with optimized batch settings
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{correlation_gateway}/api/otlp/v1/traces",
        timeout=10,  # Reduced timeout
    )

    provider.add_span_processor(
        BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=1024,  # Reduced from 2048
            max_export_batch_size=256,  # Reduced from 512
            schedule_delay_millis=5000,
        )
    )

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Auto-instrument HTTP clients (lightweight)
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    logger.info(
        f"OTEL initialized: {service_name} v{service_version} "
        f"-> {correlation_gateway} ({environment})"
    )

    return trace.get_tracer(service_name, service_version)


# ========================================
# Lightweight Flask Instrumentation
# (Replaces resource-intensive middleware.py)
# ========================================

def instrument_flask_lightweight(app, service_name: str):
    """
    Lightweight Flask instrumentation without heavy middleware

    Replaces LoggingWSGIMiddleware with efficient Flask hooks

    Args:
        app: Flask application
        service_name: Service name

    Example:
        >>> from flask import Flask
        >>> from common.otel_sense import setup_otel_sense, instrument_flask_lightweight
        >>> app = Flask(__name__)
        >>> setup_otel_sense("beorn", "1.0.0")
        >>> instrument_flask_lightweight(app, "beorn")
    """
    from flask import request, g

    # Use Flask's native instrumentation (efficient)
    FlaskInstrumentor().instrument_app(app)

    @app.before_request
    def before_request_otel():
        """Lightweight request processing"""
        # Generate request ID
        g.request_id = str(uuid.uuid4()).replace("-", "")[:8].upper()
        g.start_time = time.perf_counter_ns()

        # Bind request ID to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=g.request_id)

        # Extract correlation keys from headers
        circuit_id = request.headers.get("X-Circuit-Id")
        product_id = request.headers.get("X-Product-Id")
        resource_id = request.headers.get("X-Resource-Id")

        # Extract from JSON payload (non-blocking)
        if request.is_json and request.content_length and request.content_length < 10240:  # 10KB limit
            try:
                json_data = request.get_json(silent=True)
                if json_data:
                    circuit_id = circuit_id or json_data.get("circuit_id")
                    product_id = product_id or json_data.get("product_id")
                    resource_id = resource_id or json_data.get("resource_id")
            except:
                pass

        # Store in Flask g
        g.circuit_id = circuit_id
        g.product_id = product_id
        g.resource_id = resource_id

        # Add to current span (efficient)
        span = trace.get_current_span()
        if span and span.is_recording():
            if circuit_id:
                span.set_attribute("mdso.circuit_id", circuit_id)
            if product_id:
                span.set_attribute("mdso.product_id", product_id)
            if resource_id:
                span.set_attribute("mdso.resource_id", resource_id)

            span.set_attribute("sense.service", service_name)
            span.set_attribute("request.id", g.request_id)

        # Set baggage for propagation
        ctx = context.get_current()
        if circuit_id:
            ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
        if product_id:
            ctx = baggage.set_baggage("product_id", product_id, context=ctx)
        if resource_id:
            ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

        context.attach(ctx)

    @app.after_request
    def after_request_otel(response):
        """Lightweight response processing"""
        # Calculate request duration
        if hasattr(g, 'start_time'):
            duration_s = (time.perf_counter_ns() - g.start_time) / 10**9
            structlog.contextvars.bind_contextvars(ProcessTime=f"{duration_s:.4f}")

        # Add trace ID to response headers
        span = trace.get_current_span()
        if span and span.is_recording():
            trace_id = format(span.get_span_context().trace_id, '032x')
            response.headers["X-Trace-Id"] = trace_id
            if hasattr(g, 'request_id'):
                response.headers["X-Request-Id"] = g.request_id

        return response

    logger.info(f"Flask app instrumented (lightweight): {service_name}")


# ========================================
# Lightweight FastAPI Instrumentation
# ========================================

def instrument_fastapi_lightweight(app, service_name: str):
    """
    Lightweight FastAPI instrumentation

    Args:
        app: FastAPI application
        service_name: Service name

    Example:
        >>> from fastapi import FastAPI
        >>> from common.otel_sense import setup_otel_sense, instrument_fastapi_lightweight
        >>> app = FastAPI()
        >>> setup_otel_sense("arda", "1.0.0")
        >>> instrument_fastapi_lightweight(app, "arda")
    """
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware

    # Use FastAPI's native instrumentation
    FastAPIInstrumentor.instrument_app(app)

    class LightweightCorrelationMiddleware(BaseHTTPMiddleware):
        """Minimal overhead correlation middleware"""

        async def dispatch(self, request: Request, call_next):
            # Generate request ID
            request_id = str(uuid.uuid4()).replace("-", "")[:8].upper()
            start_time = time.perf_counter_ns()

            # Extract correlation keys from headers
            circuit_id = request.headers.get("x-circuit-id")
            product_id = request.headers.get("x-product-id")
            resource_id = request.headers.get("x-resource-id")

            # Store in request state
            request.state.request_id = request_id
            request.state.circuit_id = circuit_id
            request.state.product_id = product_id
            request.state.resource_id = resource_id

            # Add to span
            span = trace.get_current_span()
            if span and span.is_recording():
                if circuit_id:
                    span.set_attribute("mdso.circuit_id", circuit_id)
                if product_id:
                    span.set_attribute("mdso.product_id", product_id)
                if resource_id:
                    span.set_attribute("mdso.resource_id", resource_id)

                span.set_attribute("sense.service", service_name)
                span.set_attribute("request.id", request_id)

            # Set baggage
            ctx = context.get_current()
            if circuit_id:
                ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
            if product_id:
                ctx = baggage.set_baggage("product_id", product_id, context=ctx)
            if resource_id:
                ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

            context.attach(ctx)

            # Process request
            response = await call_next(request)

            # Add headers
            if span and span.is_recording():
                trace_id = format(span.get_span_context().trace_id, '032x')
                response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Request-Id"] = request_id

            # Log duration
            duration_s = (time.perf_counter_ns() - start_time) / 10**9
            logger.debug(f"Request completed in {duration_s:.4f}s")

            return response

    app.add_middleware(LightweightCorrelationMiddleware)
    logger.info(f"FastAPI app instrumented (lightweight): {service_name}")


# ========================================
# MDSO-Specific Helpers
# ========================================

def set_mdso_correlation(
    circuit_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    product_id: Optional[str] = None,
    tid: Optional[str] = None,
    fqdn: Optional[str] = None,
    provider_resource_id: Optional[str] = None,
    service_type: Optional[str] = None,
    vendor: Optional[str] = None,
):
    """
    Set MDSO correlation keys in current span and baggage

    Implements the correlation chain: circuit_id → fqdn → provider_resource_id

    Args:
        circuit_id: Circuit identifier
        resource_id: MDSO resource ID
        product_id: Product ID
        tid: Device TID
        fqdn: Device FQDN
        provider_resource_id: MDSO provider resource ID
        service_type: Service type (FIA, ELAN, etc.)
        vendor: Device vendor

    Example:
        >>> set_mdso_correlation(
        ...     circuit_id="80.L1XX.005054..CHTR",
        ...     fqdn="DEVICE.CHTRSE.COM",
        ...     vendor="juniper"
        ... )
    """
    span = trace.get_current_span()
    ctx = context.get_current()

    # Add to span attributes
    if span and span.is_recording():
        if circuit_id:
            span.set_attribute("mdso.circuit_id", circuit_id)
        if resource_id:
            span.set_attribute("mdso.resource_id", resource_id)
        if product_id:
            span.set_attribute("mdso.product_id", product_id)
        if tid:
            span.set_attribute("network.device.tid", tid)
        if fqdn:
            span.set_attribute("network.device.fqdn", fqdn)
        if provider_resource_id:
            span.set_attribute("mdso.provider_resource_id", provider_resource_id)
        if service_type:
            span.set_attribute("service.type", service_type)
        if vendor:
            span.set_attribute("network.device.vendor", vendor)

    # Set baggage for cross-service propagation
    if circuit_id:
        ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
    if resource_id:
        ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)
    if product_id:
        ctx = baggage.set_baggage("product_id", product_id, context=ctx)
    if tid:
        ctx = baggage.set_baggage("tid", tid, context=ctx)
    if fqdn:
        ctx = baggage.set_baggage("fqdn", fqdn, context=ctx)
    if provider_resource_id:
        ctx = baggage.set_baggage("provider_resource_id", provider_resource_id, context=ctx)

    context.attach(ctx)


def add_topology_span_attrs(
    service_type: Optional[str] = None,
    vendor: Optional[str] = None,
    fqdn: Optional[str] = None,
    node_count: Optional[int] = None,
    validation_passed: Optional[bool] = None,
):
    """
    Add Beorn topology-specific attributes to current span

    Args:
        service_type: Service type (FIA, ELAN, ELINE, etc.)
        vendor: Device vendor
        fqdn: Device FQDN
        node_count: Number of nodes in topology
        validation_passed: Whether topology validation passed
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        if service_type:
            span.set_attribute("beorn.service_type", service_type)
        if vendor:
            span.set_attribute("beorn.vendor", vendor)
        if fqdn:
            span.set_attribute("beorn.fqdn", fqdn)
        if node_count is not None:
            span.set_attribute("beorn.topology.node_count", node_count)
        if validation_passed is not None:
            span.set_attribute("beorn.topology.validation_passed", validation_passed)


def add_network_function_attrs(
    communication_state: Optional[str] = None,
    ip_address: Optional[str] = None,
    vendor: Optional[str] = None,
    device_role: Optional[str] = None,
):
    """
    Add network function-specific attributes to current span

    Args:
        communication_state: Device communication state
        ip_address: Device IP address
        vendor: Device vendor
        device_role: Device role (CPE, PE)
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        if communication_state:
            span.set_attribute("network.device.communication_state", communication_state)
        if ip_address:
            span.set_attribute("network.device.ip_address", ip_address)
        if vendor:
            span.set_attribute("network.device.vendor", vendor)
        if device_role:
            span.set_attribute("network.device.role", device_role)


# ========================================
# Decorators
# ========================================

def traced(span_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically trace a function

    Args:
        span_name: Span name (defaults to function name)
        attributes: Additional span attributes

    Example:
        >>> @traced("beorn.topology.fetch", {"operation": "fetch"})
        ... def fetch_topology(circuit_id):
        ...     # function code
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ========================================
# Utility Functions
# ========================================

def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name)


def get_current_span() -> trace.Span:
    """Get the current active span"""
    return trace.get_current_span()


def add_span_event(name: str, **attributes):
    """Add event to current span"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes)


def set_span_error(error: Exception):
    """Mark current span as failed"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)


def get_structured_logger(service_name: str) -> structlog.BoundLogger:
    """Get structured logger for Sense app"""
    return structlog.get_logger(service_name)
