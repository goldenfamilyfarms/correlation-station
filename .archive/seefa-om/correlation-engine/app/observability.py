"""
OpenTelemetry Observability Setup for Correlation Engine
Self-monitoring instrumentation - exports directly to backends to avoid infinite loops

Key Design Decisions:
- Exports DIRECTLY to Tempo/DataDog (NOT to self)
- Instruments internal correlation pipeline operations
- Tracks OTLP ingestion endpoint performance
- Monitors export operations to backends
"""
import logging
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import structlog

# FastAPI instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# DataDog exporter (optional)
try:
    from opentelemetry.exporter.datadog import DatadogSpanExporter
    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False
    logging.warning("DataDog exporter not available. Install with: pip install opentelemetry-exporter-datadog")


def setup_observability(
    app,
    service_name: str = "correlation-engine",
    service_version: str = "1.0.0",
    environment: Optional[str] = None,
    tempo_grpc_endpoint: Optional[str] = None,
    datadog_enabled: bool = False,
    datadog_agent_url: Optional[str] = None,
    enable_metrics: bool = True,
    metric_export_interval_ms: int = 60000,
) -> tuple:
    """
    Initialize OpenTelemetry for Correlation Engine with self-monitoring

    IMPORTANT: Exports directly to Tempo/DataDog to avoid infinite telemetry loops.
    The correlation engine does NOT send telemetry to itself.

    Args:
        app: FastAPI application instance
        service_name: Service name (default: "correlation-engine")
        service_version: Version string
        environment: Environment (dev/staging/prod) - defaults to DEPLOYMENT_ENV
        tempo_grpc_endpoint: Tempo OTLP GRPC endpoint (e.g., "tempo:4317")
        datadog_enabled: Enable DataDog export (default: False)
        datadog_agent_url: DataDog agent URL
        enable_metrics: Enable metrics collection (default: True)
        metric_export_interval_ms: Metrics export interval in milliseconds (default: 60000)

    Returns:
        tuple: (tracer_provider, meter_provider)

    Example:
        >>> from fastapi import FastAPI
        >>> from app.observability import setup_observability
        >>> app = FastAPI()
        >>> setup_observability(
        ...     app,
        ...     tempo_grpc_endpoint="tempo:4317",
        ...     environment="prod"
        ... )
    """
    # Resolve configuration
    environment = environment or os.getenv("DEPLOYMENT_ENV", "production")
    tempo_grpc_endpoint = tempo_grpc_endpoint or os.getenv("TEMPO_GRPC_ENDPOINT", "tempo:4317")
    datadog_agent_url = datadog_agent_url or os.getenv("DATADOG_AGENT_URL", "http://localhost:8126")

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

    # OTLP exporter to Tempo (GRPC) - DIRECT export to Tempo, NOT to correlation-engine
    try:
        tempo_span_exporter = GRPCSpanExporter(
            endpoint=tempo_grpc_endpoint,
            insecure=True,  # Use insecure for internal cluster communication
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                tempo_span_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,
            )
        )
        logging.info(f"Tempo trace exporter configured: {tempo_grpc_endpoint}")
    except Exception as e:
        logging.warning(f"Failed to configure Tempo exporter: {e}")

    # DataDog exporter (optional)
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
        try:
            # Export metrics to Tempo (OTLP GRPC)
            tempo_metric_reader = PeriodicExportingMetricReader(
                GRPCMetricExporter(
                    endpoint=tempo_grpc_endpoint,
                    insecure=True,
                ),
                export_interval_millis=metric_export_interval_ms,
            )

            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[tempo_metric_reader],
            )
            metrics.set_meter_provider(meter_provider)
            logging.info("Metrics exporter configured")
        except Exception as e:
            logging.warning(f"Failed to configure metrics: {e}")

    # ===== PROPAGATION =====
    # Use W3C Trace Context for propagation
    set_global_textmap(
        CompositeHTTPPropagator([
            TraceContextTextMapPropagator(),  # traceparent, tracestate
        ])
    )

    # ===== AUTO-INSTRUMENTATION =====
    # FastAPI instrumentation
    if FASTAPI_AVAILABLE:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        logging.info("FastAPI instrumentation enabled")
    else:
        logging.warning("FastAPI instrumentation not available")

    # HTTPX auto-instrumentation (for outbound HTTP calls to Loki/Tempo/DataDog)
    try:
        HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)
        logging.info("HTTPX instrumentation enabled")
    except Exception as e:
        logging.debug(f"HTTPX instrumentation not available: {e}")

    # ===== STRUCTURED LOGGING ENHANCEMENT =====
    _enhance_structlog()

    logging.info(f"✓ OpenTelemetry initialized for {service_name} v{service_version}")
    logging.info(f"  - Tempo GRPC: {tempo_grpc_endpoint}")
    logging.info(f"  - DataDog: {'Enabled' if datadog_enabled and DATADOG_AVAILABLE else 'Disabled'}")
    logging.info(f"  - Environment: {environment}")
    logging.info(f"  - Metrics: {'Enabled' if enable_metrics else 'Disabled'}")
    logging.info(f"  - Self-monitoring mode: Exports to backends directly (no infinite loop)")

    return tracer_provider, meter_provider


def _enhance_structlog():
    """
    Enhance existing structlog configuration with trace context.
    """

    def add_trace_context(logger, method_name, event_dict):
        """Add trace_id and span_id to logs"""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
            event_dict["trace_flags"] = format(ctx.trace_flags, "02x")

        return event_dict

    # Get current processors and add trace context
    try:
        current_config = structlog.get_config()
        processors = list(current_config.get("processors", []))

        # Insert trace context processor early
        insert_index = 1  # After merge_contextvars
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
        >>> add_span_event("correlation.window_processed", events_count=42, duration_ms=150)
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
