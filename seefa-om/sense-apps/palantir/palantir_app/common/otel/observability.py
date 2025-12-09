"""
OpenTelemetry Observability Setup for Sense Apps
Initializes traces, metrics, logs with dual export to Correlation Engine + DataDog

Supports both Flask and FastAPI applications.

Usage:
    # Flask app
    from common.observability import setup_observability
    app = Flask(__name__)
    setup_observability(app, service_name="beorn", service_version="1.0.0")

    # FastAPI app
    from common.observability import setup_observability
    app = FastAPI()
    setup_observability(app, service_name="arda", service_version="1.0.0")
"""
import logging
import os
from typing import Optional, List, Union

from opentelemetry import trace, metrics, baggage, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
import structlog

# Try to import Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Try to import FastAPI instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Try to import DataDog exporter
try:
    from opentelemetry.exporter.datadog import DatadogSpanExporter
    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False
    logging.warning("DataDog exporter not available. Install with: pip install opentelemetry-exporter-datadog")


# Default configuration
DEFAULT_CORRELATION_ENGINE_URL = os.getenv("CORRELATION_ENGINE_URL", "http://159.56.4.94:8080")
DEFAULT_DATADOG_AGENT_URL = os.getenv("DATADOG_AGENT_URL", "http://localhost:8126")
DEFAULT_ENVIRONMENT = os.getenv("DEPLOYMENT_ENV", os.getenv("ENVIRONMENT", "production"))

# Default baggage keys to propagate (can be overridden)
DEFAULT_BAGGAGE_KEYS = [
    "circuit_id",       # Circuit/Service ID
    "product_id",       # Product ID
    "resource_id",      # Resource ID
    "serviceType",      # eline, elan, transport
    "orderType",        # provision, disconnect, modify
    "resourceType",     # CPE, PE, port, etc.
    "productType",      # Product type
    "request_id",       # Request/transaction ID
]


def setup_observability(
    app,
    service_name: str,
    service_version: str,
    environment: Optional[str] = None,
    correlation_engine_url: Optional[str] = None,
    datadog_enabled: bool = True,
    datadog_agent_url: Optional[str] = None,
    baggage_keys: Optional[List[str]] = None,
    enable_metrics: bool = True,
    metric_export_interval_ms: int = 60000,
) -> tuple:
    """
    Initialize OpenTelemetry for Sense apps with comprehensive observability

    Args:
        app: Flask or FastAPI application instance
        service_name: Service name (arda, beorn, palantir)
        service_version: Version string
        environment: Environment (dev/staging/prod) - defaults to DEPLOYMENT_ENV
        correlation_engine_url: Correlation engine base URL
        datadog_enabled: Enable DataDog export (default: True)
        datadog_agent_url: DataDog agent URL
        baggage_keys: List of baggage keys to propagate (defaults to DEFAULT_BAGGAGE_KEYS)
        enable_metrics: Enable metrics collection (default: True)
        metric_export_interval_ms: Metrics export interval in milliseconds (default: 60000)

    Returns:
        tuple: (tracer_provider, meter_provider)

    Example:
        >>> from flask import Flask
        >>> from common.observability import setup_observability
        >>> app = Flask(__name__)
        >>> setup_observability(app, "beorn", "1.0.0")
    """
    # Resolve configuration
    environment = environment or DEFAULT_ENVIRONMENT
    correlation_engine_url = correlation_engine_url or DEFAULT_CORRELATION_ENGINE_URL
    datadog_agent_url = datadog_agent_url or DEFAULT_DATADOG_AGENT_URL
    baggage_keys = baggage_keys or DEFAULT_BAGGAGE_KEYS

    # Determine app framework
    app_framework = _detect_framework(app)

    # Resource attributes (attached to all telemetry)
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        DEPLOYMENT_ENVIRONMENT: environment,
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    })

    # ===== TRACING =====
    tracer_provider = TracerProvider(resource=resource)

    # OTLP exporter to correlation-engine (HTTP/JSON)
    otel_traces_endpoint = f"{correlation_engine_url}/api/otlp/v1/traces"
    otlp_span_exporter = OTLPSpanExporter(endpoint=otel_traces_endpoint, timeout=30)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            otlp_span_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
    )

    # DataDog exporter to local agent (port 8126)
    if datadog_enabled and DATADOG_AVAILABLE:
        try:
            datadog_span_exporter = DatadogSpanExporter(
                agent_url=datadog_agent_url,
                service=service_name,
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(datadog_span_exporter))
            logging.info(f"DataDog exporter configured: {datadog_agent_url}")
        except Exception as e:
            logging.warning(f"Failed to configure DataDog exporter: {e}")

    trace.set_tracer_provider(tracer_provider)

    # ===== METRICS =====
    meter_provider = None
    if enable_metrics:
        otel_metrics_endpoint = f"{correlation_engine_url}/api/otlp/v1/metrics"
        otlp_metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otel_metrics_endpoint),
            export_interval_millis=metric_export_interval_ms,
        )

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[otlp_metric_reader],
        )
        metrics.set_meter_provider(meter_provider)

    # ===== PROPAGATION =====
    # Use W3C Trace Context + Baggage
    set_global_textmap(
        CompositeHTTPPropagator([
            TraceContextTextMapPropagator(),  # traceparent, tracestate
            W3CBaggagePropagator(),          # baggage header
        ])
    )

    # ===== AUTO-INSTRUMENTATION =====
    # Framework-specific instrumentation
    if app_framework == "flask":
        _instrument_flask(app, service_name, baggage_keys, tracer_provider)
    elif app_framework == "fastapi":
        _instrument_fastapi(app, service_name, baggage_keys, tracer_provider)
    else:
        logging.warning(f"Unknown framework for app: {type(app)}")

    # Requests library auto-instrumentation (for outbound HTTP calls)
    RequestsInstrumentor().instrument(tracer_provider=tracer_provider)

    # HTTPX auto-instrumentation (for async HTTP calls)
    try:
        HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception as e:
        logging.debug(f"HTTPX instrumentation not available: {e}")

    # ===== STRUCTURED LOGGING =====
    # Enhance existing structlog with trace context
    _enhance_structlog(baggage_keys)

    logging.info(f"✓ OpenTelemetry initialized for {service_name} v{service_version}")
    logging.info(f"  - Correlation Engine: {correlation_engine_url}")
    logging.info(f"  - DataDog: {'Enabled' if datadog_enabled and DATADOG_AVAILABLE else 'Disabled'}")
    logging.info(f"  - Environment: {environment}")
    logging.info(f"  - Framework: {app_framework}")
    logging.info(f"  - Metrics: {'Enabled' if enable_metrics else 'Disabled'}")

    return tracer_provider, meter_provider


def _detect_framework(app) -> str:
    """Detect the framework type from the app instance"""
    app_type = type(app).__name__
    if "Flask" in app_type:
        return "flask"
    elif "FastAPI" in app_type or "Starlette" in app_type:
        return "fastapi"
    return "unknown"


def _instrument_flask(app, service_name: str, baggage_keys: List[str], tracer_provider):
    """Instrument Flask app with OTel"""
    if not FLASK_AVAILABLE:
        logging.warning("Flask instrumentation not available")
        return

    from flask import request, g

    # Auto-instrument Flask
    FlaskInstrumentor().instrument_app(app, tracer_provider=tracer_provider)

    @app.before_request
    def inject_correlation_keys():
        """Extract correlation keys from request and inject into trace context"""
        # Extract from headers (case-insensitive)
        extracted_keys = {}
        for key in baggage_keys:
            # Check headers with X- prefix and various case formats
            header_value = (
                request.headers.get(f"X-{key}") or
                request.headers.get(f"x-{key}") or
                request.headers.get(key)
            )
            if header_value:
                extracted_keys[key] = header_value

        # Extract from JSON payload (if not in headers)
        if request.is_json:
            json_data = request.get_json(silent=True)
            if json_data:
                for key in baggage_keys:
                    if key not in extracted_keys:
                        json_value = json_data.get(key)
                        if json_value:
                            extracted_keys[key] = json_value

        # Store in Flask g for easy access in routes
        for key, value in extracted_keys.items():
            setattr(g, key, value)

        # Set baggage for propagation
        ctx = context.get_current()
        for key, value in extracted_keys.items():
            ctx = baggage.set_baggage(key, str(value), context=ctx)
        context.attach(ctx)

        # Add to current span attributes
        span = trace.get_current_span()
        if span and span.is_recording():
            for key, value in extracted_keys.items():
                span.set_attribute(key, str(value))

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

    logging.info(f"Flask app instrumented: {service_name}")


def _instrument_fastapi(app, service_name: str, baggage_keys: List[str], tracer_provider):
    """Instrument FastAPI app with OTel"""
    if not FASTAPI_AVAILABLE:
        logging.warning("FastAPI instrumentation not available")
        return

    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    class CorrelationMiddleware(BaseHTTPMiddleware):
        """Middleware to inject correlation keys"""

        async def dispatch(self, request: Request, call_next):
            # Extract correlation keys from headers
            extracted_keys = {}
            for key in baggage_keys:
                header_value = (
                    request.headers.get(f"x-{key}") or
                    request.headers.get(key)
                )
                if header_value:
                    extracted_keys[key] = header_value

            # Try to extract from JSON body (if POST/PUT)
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                    for key in baggage_keys:
                        if key not in extracted_keys:
                            json_value = body.get(key)
                            if json_value:
                                extracted_keys[key] = json_value
                except Exception:
                    pass

            # Store in request state
            for key, value in extracted_keys.items():
                setattr(request.state, key, value)

            # Set baggage
            ctx = context.get_current()
            for key, value in extracted_keys.items():
                ctx = baggage.set_baggage(key, str(value), context=ctx)
            context.attach(ctx)

            # Add to span
            span = trace.get_current_span()
            if span and span.is_recording():
                for key, value in extracted_keys.items():
                    span.set_attribute(key, str(value))

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

    logging.info(f"FastAPI app instrumented: {service_name}")


def _enhance_structlog(baggage_keys: List[str]):
    """
    Enhance existing structlog configuration with trace context.
    """

    def add_trace_context(logger, method_name, event_dict):
        """Add trace_id, span_id, and baggage to logs"""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
            event_dict["trace_flags"] = format(ctx.trace_flags, "02x")

        # Add baggage to logs for correlation
        for key in baggage_keys:
            value = baggage.get_baggage(key)
            if value:
                event_dict[key] = value

        return event_dict

    # Get current processors and add trace context
    try:
        current_config = structlog.get_config()
        processors = list(current_config.get("processors", []))

        # Insert trace context processor after contextvars merge (if exists)
        insert_index = 1  # Default to index 1
        for i, proc in enumerate(processors):
            if hasattr(proc, '__name__') and 'merge_contextvars' in proc.__name__:
                insert_index = i + 1
                break

        # Only add if not already present
        if add_trace_context not in processors:
            processors.insert(insert_index, add_trace_context)

            # Reconfigure structlog
            structlog.configure(
                processors=processors,
                logger_factory=current_config.get("logger_factory"),
                wrapper_class=current_config.get("wrapper_class"),
                cache_logger_on_first_use=current_config.get("cache_logger_on_first_use", True),
            )
    except Exception as e:
        logging.debug(f"Could not enhance structlog: {e}")


# ========================================
# Utility Functions
# ========================================

def set_correlation_context(**kwargs):
    """
    Set baggage values for the current context.
    Call this at API entry points to propagate context.

    Args:
        **kwargs: Key-value pairs to set as baggage (circuit_id, product_id, etc.)

    Example:
        >>> set_correlation_context(
        ...     circuit_id="CKT123",
        ...     serviceType="eline",
        ...     orderType="provision"
        ... )
    """
    for key, value in kwargs.items():
        if value is not None:
            baggage.set_baggage(key, str(value))


def get_tracer(name: str = __name__):
    """Get a tracer instance for manual instrumentation"""
    return trace.get_tracer(name)


def get_meter(name: str = __name__):
    """Get a meter instance for custom metrics"""
    return metrics.get_meter(name)


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
