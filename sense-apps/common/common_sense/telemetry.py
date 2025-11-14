"""Compatibility shim for telemetry imports.

Some modules import telemetry using the `common_sense.telemetry` path. The
actual helper implementation lives in `common_sense_telemetry.tracer`. This
shim re-exports the common symbols from that module so both import styles
work without changing existing code.

The shim tries a couple of import paths to be robust across different
packaging/deployment layouts and will raise a clear ImportError if neither
works.
"""
from typing import Any

__all__ = [
    "init_telemetry",
    "get_tracer",
    "set_baggage_context",
    "get_current_span",
    "add_span_attributes",
    "add_span_event",
]

try:
    # Most common layout in this workspace
    from common_sense_telemetry.tracer import (
        init_telemetry,
        get_tracer,
        set_baggage_context,
        get_current_span,
        add_span_attributes,
        add_span_event,
    )
except Exception:
    # Fallback for alternate packaging layouts (e.g., package name
    # `common_sense.common_sense_telemetry`)
    try:
        from common_sense.common_sense_telemetry.tracer import (
            init_telemetry,
            get_tracer,
            set_baggage_context,
            get_current_span,
            add_span_attributes,
            add_span_event,
        )
    except Exception as exc:  # pragma: no cover - very unlikely in normal runs
        raise ImportError(
            "Could not import telemetry helpers from common_sense_telemetry; "
            "ensure the package `common_sense_telemetry` is available on PYTHONPATH"
        ) from exc


# Provide a tiny helper to allow callers to perform a safe init without
# needing to import the tracer internals directly.
def safe_init(service_name: str, *args: Any, **kwargs: Any):
    """Alias to init_telemetry kept for callers expecting a simple API.

    This is optional — most callers should import and call `init_telemetry`
    directly. The alias exists to reduce import churn in older services.
    """
    return init_telemetry(service_name, *args, **kwargs)

__all__.append("safe_init")
