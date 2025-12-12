"""
MDSO OpenTelemetry Instrumentation Package

This package provides comprehensive OpenTelemetry instrumentation
for MDSO products including scriptplans, SENSE apps, and other services.

Quick Start:
    >>> from otel_instrumentation import MDSOInstrumentation
    >>> instr = MDSOInstrumentation("my-service").setup()
    >>> with instr.span("operation") as span:
    ...     # Do work
    ...     pass

Or use the convenience function:
    >>> from otel_instrumentation import create_instrumentation
    >>> instr = create_instrumentation("my-service", environment="prod")

Version: 2.0.0
Author: Derrick Golden
"""

# Version
__version__ = "2.0.0"

# Main instrumentation class (new unified approach)
from .mdso_instrumentation import (
    MDSOInstrumentation,
    create_instrumentation,
)

# Utilities from otel_mdso_utils
from .otel_mdso_utils import (
    VENDOR_RESOURCE_MAPPING,
    MDSORegexPatterns,
    MDSOSpanHelper,
    ErrorPatternMatcher,
    extract_vendor_from_node_name,
    extract_fqdn_from_node_name,
    validate_beorn_response,
)

# Backward compatibility - import standalone functions from instrumentation.py
from .instrumentation import (
    setup_otel,
    get_otel_logger,
    otel_enter_exit_log,
    inject_correlation_context,
    extract_correlation_context,
    create_mdso_span,
    mdso_span,
    setup_pyroscope,
)

# Define public API
__all__ = [
    # Main class (recommended)
    "MDSOInstrumentation",
    "create_instrumentation",

    # Utilities
    "VENDOR_RESOURCE_MAPPING",
    "MDSORegexPatterns",
    "MDSOSpanHelper",
    "ErrorPatternMatcher",
    "extract_vendor_from_node_name",
    "extract_fqdn_from_node_name",
    "validate_beorn_response",

    # Backward compatibility (deprecated, will be removed in v3.0)
    "setup_otel",
    "get_otel_logger",
    "otel_enter_exit_log",
    "inject_correlation_context",
    "extract_correlation_context",
    "create_mdso_span",
    "mdso_span",
    "setup_pyroscope",
]
