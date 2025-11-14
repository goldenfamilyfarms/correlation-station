"""Compatibility package for common_sense imports.

This package provides a thin namespace so callers using `from common_sense.telemetry`
will continue to work. It intentionally contains no runtime logic - see
`telemetry.py` for the compatibility shim.
"""

__all__ = ["telemetry"]
