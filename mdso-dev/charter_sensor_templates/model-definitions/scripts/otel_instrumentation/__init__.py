"""
OpenTelemetry Instrumentation for MDSO Scriptplan
Provides drop-in replacement for BP's splunk_logger with OTel SDK
"""

from .common_otel import OTelPlan
from .instrumentation import setup_otel, get_otel_logger, otel_enter_exit_log

__version__ = "1.0.0"

__all__ = [
    "OTelPlan",
    "setup_otel",
    "get_otel_logger",
    "otel_enter_exit_log",
]
