"""
OpenTelemetry Instrumentation Module for Beorn (Flask)

This module provides comprehensive OpenTelemetry instrumentation for Flask applications.
It includes automatic tracing, metrics, and structured logging integration.

Main exports:
    - setup_observability: Initialize OTEL for Flask/FastAPI apps
    - All utility functions from observability, otel_sense, and telemetry modules
"""

# Import main observability setup function
from .observability import (
    setup_observability,
    set_correlation_context,
    get_tracer,
    get_meter,
    add_span_event,
    set_span_error,
)

# Import otel_sense utilities for MDSO-specific instrumentation
from .otel_sense import (
    setup_otel_sense,
    instrument_flask_lightweight,
    instrument_fastapi_lightweight,
    set_mdso_correlation,
    add_topology_span_attrs,
    add_network_function_attrs,
    traced,
    get_current_span,
    get_structured_logger,
)

# Import MDSO patterns for error extraction
from .mdso_patterns import (
    MDSOPatterns,
    ErrorCategorizer,
    map_vendor_to_resource_type,
    extract_vendor_from_beorn_node,
    extract_fqdn_from_beorn_node,
    validate_beorn_response,
)

# Re-export from telemetry for backward compatibility
from .telemetry import (
    init_telemetry,
    set_baggage_context,
    add_span_attributes,
)

__all__ = [
    # Main setup
    "setup_observability",
    "setup_otel_sense",
    "init_telemetry",
    
    # Framework instrumentation
    "instrument_flask_lightweight",
    "instrument_fastapi_lightweight",
    
    # Correlation and context
    "set_correlation_context",
    "set_mdso_correlation",
    "set_baggage_context",
    
    # Span utilities
    "get_tracer",
    "get_meter",
    "get_current_span",
    "add_span_event",
    "add_span_attributes",
    "set_span_error",
    "traced",
    
    # MDSO-specific attributes
    "add_topology_span_attrs",
    "add_network_function_attrs",
    
    # MDSO patterns
    "MDSOPatterns",
    "ErrorCategorizer",
    "map_vendor_to_resource_type",
    "extract_vendor_from_beorn_node",
    "extract_fqdn_from_beorn_node",
    "validate_beorn_response",
    
    # Logging
    "get_structured_logger",
]
