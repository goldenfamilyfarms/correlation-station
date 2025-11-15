"""Observability utilities for OTEL instrumentation"""

from .otel import setup_observability, get_tracer, get_meter

__all__ = [
    "setup_observability",
    "get_tracer",
    "get_meter",
]
