"""OpenTelemetry tracer initialization and utilities for SENSE apps"""
import os
from typing import Optional
from opentelemetry import trace, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def init_telemetry(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    environment: str = "dev"
) -> trace.Tracer:
    """Initialize OpenTelemetry for a SENSE application
    
    Args:
        service_name: Name of the service (arda, beorn, palantir)
        otlp_endpoint: OTLP endpoint URL (defaults to env var or correlation-engine)
        environment: Deployment environment
        
    Returns:
        Configured tracer instance
    """
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://correlation-engine:8080/api/otlp/v1/traces"
        )
    
    # Create resource with service metadata
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": "sense",
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    })
    
    # Configure trace provider
    provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Set as global provider
    trace.set_tracer_provider(provider)
    
    # Auto-instrument frameworks
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()
    RequestsInstrumentor.instrument()
    
    return trace.get_tracer(service_name)


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name)


def get_current_span() -> trace.Span:
    """Get the current active span"""
    return trace.get_current_span()


def set_baggage_context(**kwargs) -> object:
    """Set baggage items for cross-service context propagation
    
    Example:
        ctx = set_baggage_context(circuit_id="123", product_type="service_mapper")
        with tracer.start_as_current_span("operation", context=ctx):
            # baggage is propagated
    """
    ctx = baggage.get_baggage_in_context()
    for key, value in kwargs.items():
        ctx = baggage.set_baggage(key, str(value), context=ctx)
    return ctx


def add_span_attributes(**attributes):
    """Add attributes to current span"""
    span = get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict] = None):
    """Add an event to current span"""
    span = get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})
