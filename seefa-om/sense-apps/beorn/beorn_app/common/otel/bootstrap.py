"""
OpenTelemetry Bootstrap Module
Unified initialization using standard OTEL environment variables with dual export support
"""
import logging
import os
from typing import Optional, Tuple

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator

from .config import OTelConfig

logger = logging.getLogger(__name__)


def get_otlp_trace_exporter(endpoint: str, protocol: str, headers: Optional[dict] = None):
    """
    Get OTLP trace exporter based on protocol
    
    Args:
        endpoint: OTLP endpoint URL
        protocol: Protocol (http/protobuf, grpc, http/json)
        headers: Optional headers dict
    
    Returns:
        OTLP span exporter instance
    """
    if protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        return OTLPSpanExporter(endpoint=endpoint, headers=headers or {})
    elif protocol == "http/json":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        return OTLPSpanExporter(endpoint=endpoint, headers=headers or {}, timeout=30)
    else:  # http/protobuf (default)
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        return OTLPSpanExporter(endpoint=endpoint, headers=headers or {}, timeout=30)


def get_otlp_metric_exporter(endpoint: str, protocol: str, headers: Optional[dict] = None):
    """
    Get OTLP metric exporter based on protocol
    
    Args:
        endpoint: OTLP endpoint URL
        protocol: Protocol (http/protobuf, grpc, http/json)
        headers: Optional headers dict
    
    Returns:
        OTLP metric exporter instance
    """
    if protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        return OTLPMetricExporter(endpoint=endpoint, headers=headers or {})
    elif protocol == "http/json":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        return OTLPMetricExporter(endpoint=endpoint, headers=headers or {}, timeout=30)
    else:  # http/protobuf (default)
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        return OTLPMetricExporter(endpoint=endpoint, headers=headers or {}, timeout=30)


def setup_tracer_provider(config: OTelConfig) -> TracerProvider:
    """
    Setup tracer provider with dual export (Datadog Agent + Correlation Engine)
    
    Args:
        config: OTelConfig instance
    
    Returns:
        Configured TracerProvider
    """
    # Build resource attributes
    resource_attrs = {
        SERVICE_NAME: config.service_name,
        SERVICE_VERSION: config.service_version,
        DEPLOYMENT_ENVIRONMENT: config.deployment_environment,
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    }
    # Add any additional resource attributes from env
    resource_attrs.update(config.resource_attributes)
    
    resource = Resource.create(resource_attrs)
    tracer_provider = TracerProvider(resource=resource)
    
    # Apply sampling
    if config.traces_sampler == "parentbased_traceidratio":
        from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
        sampler = ParentBasedTraceIdRatio(config.traces_sampler_arg)
        tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    elif config.traces_sampler == "traceidratio":
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        sampler = TraceIdRatioBased(config.traces_sampler_arg)
        tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    elif config.traces_sampler == "always_on":
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON
        tracer_provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
    elif config.traces_sampler == "always_off":
        from opentelemetry.sdk.trace.sampling import ALWAYS_OFF
        tracer_provider = TracerProvider(resource=resource, sampler=ALWAYS_OFF)
    else:
        # Default to parentbased_traceidratio
        from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
        sampler = ParentBasedTraceIdRatio(config.traces_sampler_arg)
        tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    
    exporters_added = 0
    
    # Export 1: Datadog Agent (OTLP)
    if config.otlp_endpoint:
        try:
            datadog_endpoint = config.get_datadog_traces_endpoint()
            if datadog_endpoint:
                datadog_exporter = get_otlp_trace_exporter(
                    endpoint=datadog_endpoint,
                    protocol=config.otlp_protocol,
                    headers=config.otlp_headers
                )
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(
                        datadog_exporter,
                        max_queue_size=2048,
                        max_export_batch_size=512,
                        schedule_delay_millis=5000,
                    )
                )
                exporters_added += 1
                logger.info(f"Datadog Agent OTLP exporter configured: {datadog_endpoint} ({config.otlp_protocol})")
        except Exception as e:
            logger.warning(f"Failed to configure Datadog Agent OTLP exporter: {e}")
    
    # Export 2: Correlation Engine (OTLP)
    if config.correlation_engine_url:
        try:
            correlation_endpoint = config.get_correlation_traces_endpoint()
            correlation_exporter = get_otlp_trace_exporter(
                endpoint=correlation_endpoint,
                protocol="http/protobuf",  # Correlation engine uses HTTP/protobuf
                headers=None
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    correlation_exporter,
                    max_queue_size=2048,
                    max_export_batch_size=512,
                    schedule_delay_millis=5000,
                )
            )
            exporters_added += 1
            logger.info(f"Correlation Engine OTLP exporter configured: {correlation_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure Correlation Engine OTLP exporter: {e}")
    
    if exporters_added == 0:
        logger.warning("No trace exporters configured! Traces will not be exported.")
    
    trace.set_tracer_provider(tracer_provider)
    return tracer_provider


def setup_meter_provider(config: OTelConfig, export_interval_ms: int = 60000) -> Optional[MeterProvider]:
    """
    Setup meter provider with dual export (Datadog Agent + Correlation Engine)
    
    Args:
        config: OTelConfig instance
        export_interval_ms: Metrics export interval in milliseconds
    
    Returns:
        Configured MeterProvider or None if metrics disabled
    """
    if config.metrics_exporter != "otlp":
        logger.info(f"Metrics exporter disabled (OTEL_METRICS_EXPORTER={config.metrics_exporter})")
        return None
    
    # Build resource attributes (same as traces)
    resource_attrs = {
        SERVICE_NAME: config.service_name,
        SERVICE_VERSION: config.service_version,
        DEPLOYMENT_ENVIRONMENT: config.deployment_environment,
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    }
    resource_attrs.update(config.resource_attributes)
    resource = Resource.create(resource_attrs)
    
    metric_readers = []
    
    # Export 1: Datadog Agent (OTLP)
    if config.otlp_endpoint:
        try:
            datadog_endpoint = config.get_datadog_metrics_endpoint()
            if datadog_endpoint:
                datadog_exporter = get_otlp_metric_exporter(
                    endpoint=datadog_endpoint,
                    protocol=config.otlp_protocol,
                    headers=config.otlp_headers
                )
                metric_readers.append(
                    PeriodicExportingMetricReader(
                        datadog_exporter,
                        export_interval_millis=export_interval_ms,
                    )
                )
                logger.info(f"Datadog Agent OTLP metric reader configured: {datadog_endpoint} ({config.otlp_protocol})")
        except Exception as e:
            logger.warning(f"Failed to configure Datadog Agent OTLP metric reader: {e}")
    
    # Export 2: Correlation Engine (OTLP)
    if config.correlation_engine_url:
        try:
            correlation_endpoint = config.get_correlation_metrics_endpoint()
            correlation_exporter = get_otlp_metric_exporter(
                endpoint=correlation_endpoint,
                protocol="http/protobuf",  # Correlation engine uses HTTP/protobuf
                headers=None
            )
            metric_readers.append(
                PeriodicExportingMetricReader(
                    correlation_exporter,
                    export_interval_millis=export_interval_ms,
                )
            )
            logger.info(f"Correlation Engine OTLP metric reader configured: {correlation_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure Correlation Engine OTLP metric reader: {e}")
    
    if not metric_readers:
        logger.warning("No metric readers configured! Metrics will not be exported.")
        return None
    
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    return meter_provider


def setup_propagators(config: OTelConfig):
    """
    Setup context propagators from OTEL_PROPAGATORS env var
    
    Args:
        config: OTelConfig instance
    """
    propagator_list = []
    
    for prop_name in config.propagators:
        if prop_name == "tracecontext":
            propagator_list.append(TraceContextTextMapPropagator())
        elif prop_name == "baggage":
            propagator_list.append(W3CBaggagePropagator())
        elif prop_name == "b3":
            try:
                from opentelemetry.propagators.b3 import B3MultiFormat
                propagator_list.append(B3MultiFormat())
            except ImportError:
                logger.warning("B3 propagator not available. Install opentelemetry-propagator-b3")
        else:
            logger.warning(f"Unknown propagator: {prop_name}")
    
    if not propagator_list:
        # Default to tracecontext + baggage
        propagator_list = [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
    
    set_global_textmap(CompositeHTTPPropagator(propagator_list))
    logger.info(f"Propagators configured: {', '.join(config.propagators)}")


def bootstrap_otel(
    service_name: Optional[str] = None,
    service_version: Optional[str] = None,
    enable_metrics: bool = True,
    metric_export_interval_ms: int = 60000,
) -> Tuple[TracerProvider, Optional[MeterProvider]]:
    """
    Bootstrap OpenTelemetry with dual export using standard environment variables
    
    This is the main entry point for OTel initialization. It reads standard OTEL
    environment variables and sets up dual export to both Datadog Agent (OTLP) and
    Correlation Engine (OTLP).
    
    Args:
        service_name: Override service name (defaults to OTEL_SERVICE_NAME env var)
        service_version: Override service version (defaults to OTEL_SERVICE_VERSION env var)
        enable_metrics: Enable metrics collection (default: True)
        metric_export_interval_ms: Metrics export interval in milliseconds
    
    Returns:
        Tuple of (TracerProvider, MeterProvider)
    
    Example:
        >>> from common.otel.bootstrap import bootstrap_otel
        >>> tracer_provider, meter_provider = bootstrap_otel()
        >>> # Or override service name
        >>> tracer_provider, meter_provider = bootstrap_otel(service_name="my-service")
    """
    config = OTelConfig()
    
    # Override with function args if provided
    if service_name:
        config.service_name = service_name
    if service_version:
        config.service_version = service_version
    
    # Setup propagators first
    setup_propagators(config)
    
    # Setup tracing
    tracer_provider = setup_tracer_provider(config)
    
    # Setup metrics
    meter_provider = None
    if enable_metrics:
        meter_provider = setup_meter_provider(config, metric_export_interval_ms)
    
    logger.info(
        f"OpenTelemetry bootstrapped: service={config.service_name}, "
        f"version={config.service_version}, env={config.deployment_environment}, "
        f"dual_export={config.is_dual_export_enabled()}"
    )
    
    return tracer_provider, meter_provider
