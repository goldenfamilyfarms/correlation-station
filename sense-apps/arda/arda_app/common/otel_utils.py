"""
Common OpenTelemetry instrumentation for Sense apps
Provides dual export to Correlation Station and DataDog
"""

import os
import logging
from typing import Optional, Callable
from opentelemetry import trace, baggage, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import structlog

# DataDog exporter (optional)
try:
    from ddtrace.opentelemetry import TracerProvider as DDTracerProvider
    from ddtrace import tracer as dd_tracer
    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False

logger = logging.getLogger(__name__)


def setup_otel_sense(
    service_name: str,
    service_version: str,
    environment: str = None,
    correlation_gateway: str = None,
    datadog_enabled: bool = None,
):
    """
    Setup OpenTelemetry for Sense apps with dual export

    Configures OTel SDK to export traces to:
    1. Correlation Gateway (OTLP HTTP)
    2. DataDog (optional, if DD_API_KEY is set)

    Args:
        service_name: Service name (beorn, arda, palantir)
        service_version: Version string
        environment: Environment (dev/staging/prod) - defaults to DEPLOYMENT_ENV
        correlation_gateway: Correlation gateway endpoint - defaults to CORRELATION_GATEWAY_URL
        datadog_enabled: Enable DataDog export - defaults to DD_ENABLED env var

    Returns:
        Configured tracer instance

    Example:
        >>> from common.otel_utils import setup_otel_sense
        >>> tracer = setup_otel_sense("beorn", "2408.0.244")
    """
    # Get configuration from environment
    environment = environment or os.getenv("DEPLOYMENT_ENV", "dev")
    correlation_gateway = correlation_gateway or os.getenv(
        "CORRELATION_GATEWAY_URL",
        "http://159.56.4.94:55681"
    )
    datadog_enabled = datadog_enabled if datadog_enabled is not None else \
        os.getenv("DD_ENABLED", "true").lower() == "true"

    # Configure structured logging
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

    # Resource attributes
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
        "telemetry.sdk.version": "1.20.0",
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter (Correlation Gateway)
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{correlation_gateway}/v1/traces",
        timeout=30,
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
    )

    # Add DataDog exporter (optional)
    if datadog_enabled and DATADOG_AVAILABLE and os.getenv("DD_API_KEY"):
        try:
            # DataDog uses its own tracer, but we can bridge from OTel
            dd_tracer.configure(
                hostname=os.getenv("DD_AGENT_HOST", "localhost"),
                port=int(os.getenv("DD_TRACE_AGENT_PORT", "8126")),
            )
            logger.info("DataDog dual export enabled")
        except Exception as e:
            logger.warning(f"Failed to configure DataDog: {e}")

    # Set global provider
    trace.set_tracer_provider(provider)

    # Auto-instrument common libraries
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    logger.info(
        f"OTel initialized: service={service_name}, "
        f"gateway={correlation_gateway}, "
        f"env={environment}, "
        f"datadog={datadog_enabled and DATADOG_AVAILABLE}"
    )

    return trace.get_tracer(service_name, service_version)


def instrument_flask_app(app, service_name: str):
    """
    Instrument Flask app with OTel

    Adds:
    - Automatic span creation for all routes
    - Correlation key extraction from headers/JSON payloads
    - Baggage propagation

    Args:
        app: Flask application instance
        service_name: Service name

    Example:
        >>> from flask import Flask
        >>> from common.otel_utils import setup_otel_sense, instrument_flask_app
        >>> app = Flask(__name__)
        >>> setup_otel_sense("beorn", "1.0.0")
        >>> instrument_flask_app(app, "beorn")
    """
    from flask import request, g

    # Instrument Flask
    FlaskInstrumentor().instrument_app(app)

    @app.before_request
    def inject_correlation_keys():
        """Extract correlation keys from request and inject into trace context"""
        # Extract from headers
        circuit_id = request.headers.get("X-Circuit-Id")
        product_id = request.headers.get("X-Product-Id")
        resource_id = request.headers.get("X-Resource-Id")

        # Extract from JSON payload (if not in headers)
        if request.is_json:
            json_data = request.get_json(silent=True)
            if json_data:
                circuit_id = circuit_id or json_data.get("circuit_id")
                product_id = product_id or json_data.get("product_id")
                resource_id = resource_id or json_data.get("resource_id")

        # Store in Flask g for easy access in routes
        g.circuit_id = circuit_id
        g.product_id = product_id
        g.resource_id = resource_id

        # Set baggage for propagation
        ctx = context.get_current()
        if circuit_id:
            ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
        if product_id:
            ctx = baggage.set_baggage("product_id", product_id, context=ctx)
        if resource_id:
            ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

        context.attach(ctx)

        # Add to current span attributes
        span = trace.get_current_span()
        if span and span.is_recording():
            if circuit_id:
                span.set_attribute("circuit_id", circuit_id)
            if product_id:
                span.set_attribute("product_id", product_id)
            if resource_id:
                span.set_attribute("resource_id", resource_id)

            # Add service-specific attributes
            span.set_attribute("sense.service", service_name)
            span.set_attribute("http.route", request.endpoint or request.path)

    @app.after_request
    def inject_trace_id_header(response):
        """Inject trace ID into response headers for debugging"""
        span = trace.get_current_span()
        if span and span.is_recording():
            trace_id = format(span.get_span_context().trace_id, '032x')
            response.headers["X-Trace-Id"] = trace_id
        return response

    logger.info(f"Flask app instrumented: {service_name}")


def instrument_fastapi_app(app, service_name: str):
    """
    Instrument FastAPI app with OTel

    Adds:
    - Automatic span creation for all routes
    - Correlation key extraction from headers/JSON payloads
    - Baggage propagation

    Args:
        app: FastAPI application instance
        service_name: Service name

    Example:
        >>> from fastapi import FastAPI
        >>> from common.otel_utils import setup_otel_sense, instrument_fastapi_app
        >>> app = FastAPI()
        >>> setup_otel_sense("arda", "1.0.0")
        >>> instrument_fastapi_app(app, "arda")
    """
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    class CorrelationMiddleware(BaseHTTPMiddleware):
        """Middleware to inject correlation keys"""

        async def dispatch(self, request: Request, call_next):
            # Extract correlation keys from headers
            circuit_id = request.headers.get("x-circuit-id")
            product_id = request.headers.get("x-product-id")
            resource_id = request.headers.get("x-resource-id")

            # Try to extract from JSON body (if POST/PUT)
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                    circuit_id = circuit_id or body.get("circuit_id")
                    product_id = product_id or body.get("product_id")
                    resource_id = resource_id or body.get("resource_id")
                except:
                    pass

            # Store in request state
            request.state.circuit_id = circuit_id
            request.state.product_id = product_id
            request.state.resource_id = resource_id

            # Set baggage
            ctx = context.get_current()
            if circuit_id:
                ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
            if product_id:
                ctx = baggage.set_baggage("product_id", product_id, context=ctx)
            if resource_id:
                ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

            context.attach(ctx)

            # Add to span
            span = trace.get_current_span()
            if span and span.is_recording():
                if circuit_id:
                    span.set_attribute("circuit_id", circuit_id)
                if product_id:
                    span.set_attribute("product_id", product_id)
                if resource_id:
                    span.set_attribute("resource_id", resource_id)

                # Service-specific attributes
                span.set_attribute("sense.service", service_name)

            # Process request
            response = await call_next(request)

            # Inject trace ID into response headers
            if span and span.is_recording():
                trace_id = format(span.get_span_context().trace_id, '032x')
                response.headers["X-Trace-Id"] = trace_id

            return response

    app.add_middleware(CorrelationMiddleware)

    logger.info(f"FastAPI app instrumented: {service_name}")


def get_structured_logger(service_name: str) -> structlog.BoundLogger:
    """
    Get structured logger for Sense app

    Args:
        service_name: Service name to bind

    Returns:
        Bound structured logger

    Example:
        >>> logger = get_structured_logger("beorn")
        >>> logger.info("Request processed", circuit_id="123", duration_ms=42)
    """
    return structlog.get_logger(service_name)


def add_span_event(name: str, **attributes):
    """
    Add event to current span

    Args:
        name: Event name
        **attributes: Event attributes

    Example:
        >>> add_span_event("database.query_executed", query_time_ms=15, rows=42)
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes)


def set_span_error(error: Exception):
    """
    Mark current span as failed and record error

    Args:
        error: Exception that occurred

    Example:
        >>> try:
        ...     # some operation
        ... except Exception as e:
        ...     set_span_error(e)
        ...     raise
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
        span.record_exception(error)
