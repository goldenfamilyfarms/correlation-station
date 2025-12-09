"""
Sense Common - Shared library for SEEFA Sense applications

This package provides shared functionality across Palantir, Arda, and Beorn services.
"""

__version__ = "1.0.0"
__author__ = "SEEFA Observability Team"

from .config import BaseServiceConfig
from .http import AsyncHTTPClient
from .observability import setup_observability

__all__ = [
    "BaseServiceConfig",
    "AsyncHTTPClient",
    "setup_observability",
]
