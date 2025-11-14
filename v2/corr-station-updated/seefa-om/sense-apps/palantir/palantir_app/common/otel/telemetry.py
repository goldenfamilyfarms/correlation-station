"""
Unified OpenTelemetry Module for SENSE Apps
Consolidates common_sense_telemetry, observability.py, and otel_sense.py
"""
from common.otel_sense import (
    # Core setup
    setup_otel_sense,
    instrument_flask_lightweight,
    instrument_fastapi_lightweight,
    
    # MDSO-specific helpers
    set_mdso_correlation,
    add_topology_span_attrs,
    add_network_function_attrs,
    
    # Decorators
    traced,
    
    # Utility functions
    get_tracer,
    get_current_span,
    add_span_event,
    set_span_error,
    get_structured_logger,
)

# Backward compatibility aliases
init_telemetry = setup_otel_sense
set_baggage_context = set_mdso_correlation
add_span_attributes = lambda **attrs: get_current_span().set_attributes(attrs) if get_current_span().is_recording() else None

__all__ = [
    "setup_otel_sense",
    "init_telemetry",
    "instrument_flask_lightweight",
    "instrument_fastapi_lightweight",
    "set_mdso_correlation",
    "set_baggage_context",
    "add_topology_span_attrs",
    "add_network_function_attrs",
    "traced",
    "get_tracer",
    "get_current_span",
    "add_span_event",
    "add_span_attributes",
    "set_span_error",
    "get_structured_logger",
]
