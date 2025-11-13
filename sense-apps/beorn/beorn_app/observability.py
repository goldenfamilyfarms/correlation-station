"""
OpenTelemetry Observability Setup for BEORN
Initializes traces, metrics, logs with dual export to OTel Collector + DataDog

Usage:
    from beorn_app.observability import setup_observability

    app = Flask(__name__)
    setup_observability(app)
"""
import logging
import os
from typing import Optional

from opentelemetry import trace, metrics, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
import structlog

# Try to import DataDog exporter
try:
    from opentelemetry.exporter.datadog import DatadogSpanExporter
    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False
    logging.warning("DataDog exporter not available. Install with: pip install opentelemetry-exporter-datadog")

# ========================================
# Configuration
# ========================================
# Send directly to correlation-engine (NOT OTel Gateway)
# Correlation-engine will handle correlation BEFORE forwarding to Loki/Tempo
CORRELATION_ENGINE_BASE_URL = os.getenv("CORRELATION_ENGINE_URL", "http://159.56.4.94:8080")
OTEL_TRACES_ENDPOINT = f"{CORRELATION_ENGINE_BASE_URL}/api/otlp/v1/traces"
OTEL_METRICS_ENDPOINT = f"{CORRELATION_ENGINE_BASE_URL}/api/otlp/v1/metrics"
DATADOG_AGENT_URL = os.getenv("DATADOG_AGENT_URL", "http://localhost:8126")
SERVICE_NAME_STR = "beorn"
SERVICE_VERSION_STR = "1.58.20"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Baggage keys to propagate
BAGGAGE_KEYS = [
    "serviceType",      # eline, elan, transport
    "orderType",        # provision, disconnect, modify
    "resource_id",      # Resource ID
    "resourceType",     # CPE, PE, port, etc.
    "productType",      # Product type
    "request_id",       # Request/transaction ID
]


def setup_observability(app) -> tuple:
    """
    Initialize OpenTelemetry for BEORN

    Args:
        app: Flask application instance

    Returns:
        tuple: (tracer_provider, meter_provider)
    """

    # Resource attributes (attached to all telemetry)
    resource = Resource.create({
        SERVICE_NAME: SERVICE_NAME_STR,
        SERVICE_VERSION: SERVICE_VERSION_STR,
        DEPLOYMENT_ENVIRONMENT: ENVIRONMENT,
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
    })

    # ===== TRACING =====
    tracer_provider = TracerProvider(resource=resource)

    # OTLP exporter to correlation-engine (HTTP/JSON)
    otlp_span_exporter = OTLPSpanExporter(
        endpoint=OTEL_TRACES_ENDPOINT,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))

    # DataDog exporter to local agent (port 8126)
    if DATADOG_AVAILABLE:
        try:
            datadog_span_exporter = DatadogSpanExporter(
                agent_url=DATADOG_AGENT_URL,
                service=SERVICE_NAME_STR,
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(datadog_span_exporter))
            logging.info(f"DataDog exporter configured: {DATADOG_AGENT_URL}")
        except Exception as e:
            logging.warning(f"Failed to configure DataDog exporter: {e}")

    trace.set_tracer_provider(tracer_provider)

    # ===== METRICS =====
    # OTLP metrics to correlation-engine (HTTP/JSON)
    otlp_metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=OTEL_METRICS_ENDPOINT),
        export_interval_millis=60000,  # Export every 60 seconds
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
    # Flask auto-instrumentation
    FlaskInstrumentor().instrument_app(app, tracer_provider=tracer_provider)

    # Requests library auto-instrumentation (for outbound HTTP calls)
    RequestsInstrumentor().instrument(tracer_provider=tracer_provider)

    # ===== STRUCTURED LOGGING =====
    # BEORN already uses structlog, enhance it with trace context
    enhance_existing_structlog()

    logging.info(f"✓ OpenTelemetry initialized for {SERVICE_NAME_STR} v{SERVICE_VERSION_STR}")
    logging.info(f"  - Correlation Engine: {CORRELATION_ENGINE_BASE_URL}")
    logging.info(f"  - DataDog Agent: {DATADOG_AGENT_URL}")
    logging.info(f"  - Environment: {ENVIRONMENT}")

    return tracer_provider, meter_provider


def enhance_existing_structlog():
    """
    Enhance BEORN's existing structlog configuration with trace context.
    BEORN already has structlog configured in middleware.py
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
        for key in BAGGAGE_KEYS:
            value = baggage.get_baggage(key)
            if value:
                event_dict[key] = value

        return event_dict

    # Get current processors and add trace context
    current_config = structlog.get_config()
    processors = list(current_config.get("processors", []))

    # Insert trace context processor after contextvars merge
    # Find the index of merge_contextvars
    insert_index = 1  # Default to index 1
    for i, proc in enumerate(processors):
        if hasattr(proc, '__name__') and 'merge_contextvars' in proc.__name__:
            insert_index = i + 1
            break

    processors.insert(insert_index, add_trace_context)

    # Reconfigure structlog
    structlog.configure(
        processors=processors,
        logger_factory=current_config.get("logger_factory"),
        wrapper_class=current_config.get("wrapper_class"),
        cache_logger_on_first_use=current_config.get("cache_logger_on_first_use", True),
    )


# ========================================
# Utility Functions
# ========================================

def set_baggage_from_request(
    serviceType: Optional[str] = None,
    orderType: Optional[str] = None,
    resource_id: Optional[str] = None,
    resourceType: Optional[str] = None,
    productType: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """
    Set baggage values for the current context.
    Call this at API entry points to propagate context.

    Example:
        @api.route('/provision')
        def provision_device():
            set_baggage_from_request(
                serviceType=request.json.get('service_type'),
                orderType='provision',
                resource_id=request.json.get('resource_id'),
            )
            # ... rest of handler
    """
    if serviceType:
        baggage.set_baggage("serviceType", serviceType)
    if orderType:
        baggage.set_baggage("orderType", orderType)
    if resource_id:
        baggage.set_baggage("resource_id", str(resource_id))
    if resourceType:
        baggage.set_baggage("resourceType", resourceType)
    if productType:
        baggage.set_baggage("productType", productType)
    if request_id:
        baggage.set_baggage("request_id", request_id)


def get_tracer(name: str = __name__):
    """Get a tracer instance for manual instrumentation"""
    return trace.get_tracer(name)


def get_meter(name: str = __name__):
    """Get a meter instance for custom metrics"""
    return metrics.get_meter(name)
