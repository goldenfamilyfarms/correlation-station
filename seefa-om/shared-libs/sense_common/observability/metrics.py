"""
RED Metrics Module for Sense Apps
Implements Rate, Errors, Duration metrics for HTTP servers

RED Metrics:
- Rate: HTTP request count per second
- Errors: HTTP error count (4xx, 5xx)
- Duration: HTTP request duration histogram

All metrics are exported to both Datadog Agent and Correlation Engine via OTLP.
"""
import logging
import time
from typing import Optional, Dict, Any
from opentelemetry import metrics

logger = logging.getLogger(__name__)

# Global meter instance (initialized by bootstrap)
_meter: Optional[metrics.Meter] = None

# Metric instruments (created lazily)
_http_request_counter: Optional[metrics.Counter] = None
_http_error_counter: Optional[metrics.Counter] = None
_http_duration_histogram: Optional[metrics.Histogram] = None


def initialize_metrics(meter: Optional[metrics.Meter] = None):
    """
    Initialize RED metrics instruments
    
    Args:
        meter: Meter instance (defaults to global meter from bootstrap)
    """
    global _meter, _http_request_counter, _http_error_counter, _http_duration_histogram
    
    if meter is None:
        _meter = metrics.get_meter(__name__)
    else:
        _meter = meter
    
    if _meter is None:
        logger.warning("Meter not available - RED metrics will not be collected")
        return
    
    # HTTP Request Counter (Rate)
    _http_request_counter = _meter.create_counter(
        name="http.server.request.count",
        description="Total number of HTTP requests",
        unit="1",
    )
    
    # HTTP Error Counter (Errors)
    _http_error_counter = _meter.create_counter(
        name="http.server.error.count",
        description="Total number of HTTP errors (4xx, 5xx)",
        unit="1",
    )
    
    # HTTP Duration Histogram (Duration)
    _http_duration_histogram = _meter.create_histogram(
        name="http.server.request.duration",
        description="HTTP request duration",
        unit="ms",
    )
    
    logger.info("RED metrics initialized: http.server.request.count, http.server.error.count, http.server.request.duration")


def record_http_request(
    method: str,
    route: str,
    status_code: int,
    duration_ms: float,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Record HTTP request metrics (RED)
    
    Args:
        method: HTTP method (GET, POST, etc.)
        route: Route template (e.g., "/api/v1/users/{id}")
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        attributes: Additional attributes to attach to metrics
    """
    global _http_request_counter, _http_error_counter, _http_duration_histogram
    
    if _http_request_counter is None or _http_error_counter is None or _http_duration_histogram is None:
        # Lazy initialization if not already done
        initialize_metrics()
        if _http_request_counter is None:
            return
    
    # Build base attributes (low cardinality)
    base_attrs = {
        "http.method": method,
        "http.route": route,
        "http.status_code": status_code,
    }
    
    # Add status class for better aggregation
    if 200 <= status_code < 300:
        base_attrs["http.status_class"] = "2xx"
    elif 300 <= status_code < 400:
        base_attrs["http.status_class"] = "3xx"
    elif 400 <= status_code < 500:
        base_attrs["http.status_class"] = "4xx"
    elif 500 <= status_code < 600:
        base_attrs["http.status_class"] = "5xx"
    else:
        base_attrs["http.status_class"] = "unknown"
    
    # Merge with additional attributes
    if attributes:
        base_attrs.update(attributes)
    
    # Record request count (Rate)
    _http_request_counter.add(1, base_attrs)
    
    # Record error count (Errors) - only for 4xx and 5xx
    if status_code >= 400:
        error_attrs = base_attrs.copy()
        error_attrs["error.type"] = "http_error"
        _http_error_counter.add(1, error_attrs)
    
    # Record duration (Duration)
    _http_duration_histogram.record(duration_ms, base_attrs)


def record_http_error(
    method: str,
    route: str,
    status_code: int,
    error_type: str = "http_error",
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Record HTTP error explicitly
    
    Args:
        method: HTTP method
        route: Route template
        status_code: HTTP status code
        error_type: Type of error (default: "http_error")
        attributes: Additional attributes
    """
    global _http_error_counter
    
    if _http_error_counter is None:
        initialize_metrics()
        if _http_error_counter is None:
            return
    
    attrs = {
        "http.method": method,
        "http.route": route,
        "http.status_code": status_code,
        "error.type": error_type,
    }
    
    if attributes:
        attrs.update(attributes)
    
    _http_error_counter.add(1, attrs)


def get_http_metrics_summary() -> Dict[str, Any]:
    """
    Get summary of HTTP metrics configuration
    
    Returns:
        Dictionary with metrics configuration info
    """
    return {
        "metrics_initialized": _meter is not None,
        "instruments": {
            "request_counter": _http_request_counter is not None,
            "error_counter": _http_error_counter is not None,
            "duration_histogram": _http_duration_histogram is not None,
        },
    }
