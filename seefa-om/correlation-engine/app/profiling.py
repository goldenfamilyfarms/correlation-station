"""Pyroscope profiling utilities for hot path instrumentation"""
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Try to import Pyroscope
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    PYROSCOPE_AVAILABLE = False
    logger.warning("Pyroscope not available")


def profile_function(tags: dict = None):
    """
    Decorator to profile a function with Pyroscope.

    Args:
        tags: Optional dict of tags to add to the profiling data

    Usage:
        @profile_function(tags={"operation": "correlation"})
        async def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        if not PYROSCOPE_AVAILABLE:
            # Return original function if Pyroscope not available
            return func

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            function_tags = {
                "function": func.__name__,
                "module": func.__module__,
            }
            if tags:
                function_tags.update(tags)

            with pyroscope.tag_wrapper(function_tags):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            function_tags = {
                "function": func.__name__,
                "module": func.__module__,
            }
            if tags:
                function_tags.update(tags)

            with pyroscope.tag_wrapper(function_tags):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x100:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ProfileContext:
    """Context manager for profiling code blocks"""

    def __init__(self, tags: dict):
        self.tags = tags
        self.enabled = PYROSCOPE_AVAILABLE

    def __enter__(self):
        if self.enabled:
            pyroscope.tag_wrapper(self.tags).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled:
            pyroscope.tag_wrapper(self.tags).__exit__(exc_type, exc_val, exc_tb)
