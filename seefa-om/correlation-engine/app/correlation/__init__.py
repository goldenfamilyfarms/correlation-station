"""
Correlation module for trace synthesis and span injection
"""

from .trace_synthesizer import TraceSynthesizer, TraceSegment
from .span_injector import SpanInjector
from .link_resolver import LinkResolver

__all__ = [
    "TraceSynthesizer",
    "TraceSegment",
    "SpanInjector",
    "LinkResolver",
]
