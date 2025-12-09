"""OpenTelemetry setup for Sense applications"""
from typing import Optional
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
import structlog

logger = structlog.get_logger()


def setup_observability(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "dev",
    endpoint: str = "http://gateway:4318",
    protocol: str = "http",
    enable_traces: bool = True,
    enable_metrics: bool = True,
) -> None:
    """
    Setup OpenTelemetry instrumentation for a Sense service

    Args:
        service_name: Name of the service (e.g., "palantir", "arda", "beorn")
        service_version: Version of the service
        environment: Deployment environment (dev, staging, prod)
        endpoint: OTEL collector endpoint
        protocol: OTEL protocol ("http" or "grpc")
        enable_traces: Whether to enable trace export
        enable_metrics: Whether to enable metrics export

    Example:
        from sense_common.observability import setup_observability

        setup_observability(
            service_name="palantir",
            service_version="1.0.0",
            environment="prod",
            endpoint="http://gateway:4318"
        )
    """
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment,
        "telemetry.sdk.name": "sense-common",
        "telemetry.sdk.language": "python",
    })

    # Setup traces
    if enable_traces:
        _setup_traces(resource, endpoint, protocol)

    # Setup metrics
    if enable_metrics:
        _setup_metrics(resource, endpoint, protocol)

    logger.info(
        "Observability initialized",
        service=service_name,
        version=service_version,
        environment=environment,
        endpoint=endpoint,
        protocol=protocol
    )


def _setup_traces(resource: Resource, endpoint: str, protocol: str):
    """Setup trace provider and exporter"""
    # Create exporter based on protocol
    if protocol == "grpc":
        exporter = GRPCSpanExporter(endpoint=endpoint)
    else:
        # HTTP/protobuf
        exporter = HTTPSpanExporter(endpoint=f"{endpoint}/v1/traces")

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Add batch span processor
    span_processor = BatchSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)


def _setup_metrics(resource: Resource, endpoint: str, protocol: str):
    """Setup metrics provider and exporter"""
    # Create exporter based on protocol
    if protocol == "grpc":
        exporter = GRPCMetricExporter(endpoint=endpoint)
    else:
        # HTTP/protobuf
        exporter = HTTPMetricExporter(endpoint=f"{endpoint}/v1/metrics")

    # Create metric reader with 60s export interval
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)

    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[reader]
    )

    # Set global meter provider
    metrics.set_meter_provider(meter_provider)


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer for instrumentation

    Args:
        name: Tracer name (usually __name__)

    Returns:
        Tracer instance

    Example:
        from sense_common.observability import get_tracer

        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("my_operation"):
            # Your code here
            pass
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """
    Get a meter for custom metrics

    Args:
        name: Meter name (usually __name__)

    Returns:
        Meter instance

    Example:
        from sense_common.observability import get_meter

        meter = get_meter(__name__)
        counter = meter.create_counter("requests_total")
        counter.add(1, {"endpoint": "/api/health"})
    """
    return metrics.get_meter(name)
