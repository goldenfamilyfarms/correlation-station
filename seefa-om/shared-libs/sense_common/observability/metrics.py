"""
Metrics instrumentation helpers for Sense applications

Provides decorators and context managers for automatic metric tracking
with safe cardinality management.

Usage:
    from sense_common.observability.metrics import track_request_metrics, track_dependency_call

    @track_request_metrics(service_name="arda", endpoint_group="/api/v1/circuit")
    def create_circuit(circuit_data):
        with track_dependency_call("arda", "granite", "create_circuit"):
            response = granite_client.create_circuit(circuit_data)
        return response
"""
import time
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Callable, Dict, Any
from opentelemetry import metrics
import structlog

logger = structlog.get_logger()

# Get global meter
meter = metrics.get_meter("sense_common.metrics")

# Define meters once (reused across all calls)
request_counter = meter.create_counter(
    "sense_requests_total",
    description="Total API requests processed",
    unit="1"
)

request_latency = meter.create_histogram(
    "sense_request_duration_seconds",
    description="Request processing time in seconds",
    unit="s"
)

error_counter = meter.create_counter(
    "sense_errors_total",
    description="Total errors encountered",
    unit="1"
)

dependency_call_counter = meter.create_counter(
    "sense_dependency_calls_total",
    description="Total calls to external dependencies",
    unit="1"
)

dependency_latency = meter.create_histogram(
    "sense_dependency_duration_seconds",
    description="Dependency call duration in seconds",
    unit="s"
)


def categorize_error(exception: Exception) -> str:
    """
    Map exception types to low-cardinality error categories

    Args:
        exception: The exception that occurred

    Returns:
        Error category string (validation_error, timeout_error, etc.)
    """
    error_type = type(exception).__name__

    # Validation errors
    if any(keyword in error_type for keyword in ["Validation", "ValueError", "TypeError", "KeyError"]):
        return "validation_error"

    # Timeout errors
    if "Timeout" in error_type or "timeout" in str(exception).lower():
        return "timeout_error"

    # Connection errors
    if any(keyword in error_type for keyword in ["Connection", "Network", "Socket"]):
        return "connection_error"

    # Authentication/Authorization errors
    if any(keyword in error_type for keyword in ["Auth", "Permission", "Forbidden", "Unauthorized"]):
        return "authentication_error"

    # Not found errors
    if "NotFound" in error_type or "404" in str(exception):
        return "not_found_error"

    # HTTP errors
    if "HTTPError" in error_type or "RequestException" in error_type:
        # Try to extract status code
        if "400" in str(exception):
            return "validation_error"
        elif "404" in str(exception):
            return "not_found_error"
        elif "401" in str(exception) or "403" in str(exception):
            return "authentication_error"
        elif "500" in str(exception) or "502" in str(exception) or "503" in str(exception):
            return "dependency_error"
        else:
            return "http_error"

    # Generic dependency errors
    if "Dependency" in error_type or "Service" in error_type:
        return "dependency_error"

    # Data errors
    if "Data" in error_type or "Parse" in error_type or "Json" in error_type:
        return "data_error"

    # Default to internal error
    return "internal_error"


def track_request_metrics(
    service_name: str,
    endpoint_group: Optional[str] = None,
    product_type: Optional[str] = None,
    extract_product_type: Optional[Callable[[Any, Any], str]] = None
):
    """
    Decorator to automatically track request metrics

    Metrics tracked:
    - sense_requests_total (counter)
    - sense_request_duration_seconds (histogram)
    - sense_errors_total (counter, on failure)

    Args:
        service_name: Service name (arda, beorn, palantir)
        endpoint_group: Endpoint group (e.g., "/api/v1/circuit")
        product_type: Product type (eline, elan, transport) - optional
        extract_product_type: Function to extract product_type from args/kwargs

    Usage:
        @track_request_metrics(
            service_name="arda",
            endpoint_group="/api/v1/circuit",
            product_type="eline"
        )
        def create_circuit(circuit_data):
            return response

        # Or extract product type dynamically:
        @track_request_metrics(
            service_name="beorn",
            endpoint_group="/api/v2/eligibility",
            extract_product_type=lambda args, kwargs: kwargs.get("product_type", "unknown")
        )
        def check_eligibility(**kwargs):
            return response
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract product type if function provided
            actual_product_type = product_type
            if extract_product_type:
                try:
                    actual_product_type = extract_product_type(args, kwargs)
                except Exception as e:
                    logger.warning("Failed to extract product_type", error=str(e))
                    actual_product_type = "unknown"

            start_time = time.time()
            result_type = "success"
            error_category = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                result_type = "failure"
                error_category = categorize_error(e)

                # Record error metric
                error_labels = {
                    "service.name": service_name,
                    "endpoint_group": endpoint_group or func.__name__,
                    "error_category": error_category,
                }
                if actual_product_type:
                    error_labels["product_type"] = actual_product_type

                error_counter.add(1, error_labels)
                logger.error(
                    "Request failed",
                    service=service_name,
                    endpoint=endpoint_group or func.__name__,
                    error_category=error_category,
                    error=str(e)
                )
                raise
            finally:
                duration = time.time() - start_time

                # Build labels
                labels = {
                    "service.name": service_name,
                    "endpoint_group": endpoint_group or func.__name__,
                    "result_type": result_type
                }

                if actual_product_type:
                    labels["product_type"] = actual_product_type

                # Record metrics
                request_counter.add(1, labels)
                request_latency.record(duration, labels)

                logger.debug(
                    "Request metrics recorded",
                    service=service_name,
                    endpoint=endpoint_group or func.__name__,
                    duration=duration,
                    result=result_type
                )

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract product type if function provided
            actual_product_type = product_type
            if extract_product_type:
                try:
                    actual_product_type = extract_product_type(args, kwargs)
                except Exception as e:
                    logger.warning("Failed to extract product_type", error=str(e))
                    actual_product_type = "unknown"

            start_time = time.time()
            result_type = "success"
            error_category = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                result_type = "failure"
                error_category = categorize_error(e)

                # Record error metric
                error_labels = {
                    "service.name": service_name,
                    "endpoint_group": endpoint_group or func.__name__,
                    "error_category": error_category,
                }
                if actual_product_type:
                    error_labels["product_type"] = actual_product_type

                error_counter.add(1, error_labels)
                logger.error(
                    "Request failed",
                    service=service_name,
                    endpoint=endpoint_group or func.__name__,
                    error_category=error_category,
                    error=str(e)
                )
                raise
            finally:
                duration = time.time() - start_time

                # Build labels
                labels = {
                    "service.name": service_name,
                    "endpoint_group": endpoint_group or func.__name__,
                    "result_type": result_type
                }

                if actual_product_type:
                    labels["product_type"] = actual_product_type

                # Record metrics
                request_counter.add(1, labels)
                request_latency.record(duration, labels)

                logger.debug(
                    "Request metrics recorded",
                    service=service_name,
                    endpoint=endpoint_group or func.__name__,
                    duration=duration,
                    result=result_type
                )

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def track_dependency_call(
    service_name: str,
    dependency: str,
    operation: str
):
    """
    Context manager for tracking dependency calls

    Metrics tracked:
    - sense_dependency_calls_total (counter)
    - sense_dependency_duration_seconds (histogram)

    Args:
        service_name: Service making the call (arda, beorn, palantir)
        dependency: Dependency being called (granite, ip_control, kong, mdso, etc.)
        operation: Operation being performed (get_circuit, allocate_ips, etc.)

    Usage:
        with track_dependency_call("arda", "granite", "get_circuit"):
            response = granite_client.get_circuit(circuit_id)
    """
    start_time = time.time()
    result_type = "success"

    try:
        yield
    except Exception as e:
        result_type = "failure"
        logger.error(
            "Dependency call failed",
            service=service_name,
            dependency=dependency,
            operation=operation,
            error=str(e)
        )
        raise
    finally:
        duration = time.time() - start_time

        labels = {
            "service.name": service_name,
            "dependency": dependency,
            "operation": operation,
            "result_type": result_type
        }

        dependency_call_counter.add(1, labels)
        dependency_latency.record(duration, labels)

        logger.debug(
            "Dependency call metrics recorded",
            service=service_name,
            dependency=dependency,
            operation=operation,
            duration=duration,
            result=result_type
        )


def record_queue_depth(
    service_name: str,
    queue_name: str,
    depth: int
):
    """
    Record queue depth as a gauge metric

    Args:
        service_name: Service name (arda, beorn, palantir)
        queue_name: Name of the queue
        depth: Current queue depth

    Usage:
        record_queue_depth("arda", "circuit_provisioning", queue.size())
    """
    # Note: For observable gauges, use meter.create_observable_gauge in the service startup
    # This is a helper for manual gauge recording
    logger.debug(
        "Queue depth recorded",
        service=service_name,
        queue=queue_name,
        depth=depth
    )
    # In practice, this would update a gauge metric
    # For now, just log it


def create_custom_counter(
    name: str,
    description: str,
    unit: str = "1"
):
    """
    Create a custom counter metric

    Args:
        name: Metric name (should start with "sense_")
        description: Metric description
        unit: Unit of measurement (default: "1" for count)

    Returns:
        Counter metric object

    Usage:
        circuit_created_counter = create_custom_counter(
            "sense_circuits_created_total",
            "Total circuits created",
            "1"
        )

        circuit_created_counter.add(1, {
            "service.name": "arda",
            "product_type": "eline"
        })
    """
    return meter.create_counter(name, description=description, unit=unit)


def create_custom_histogram(
    name: str,
    description: str,
    unit: str = "s"
):
    """
    Create a custom histogram metric

    Args:
        name: Metric name (should start with "sense_")
        description: Metric description
        unit: Unit of measurement (default: "s" for seconds)

    Returns:
        Histogram metric object

    Usage:
        circuit_provision_time = create_custom_histogram(
            "sense_circuit_provision_duration_seconds",
            "Time to provision a circuit",
            "s"
        )

        circuit_provision_time.record(duration, {
            "service.name": "arda",
            "product_type": "eline",
            "result_type": "success"
        })
    """
    return meter.create_histogram(name, description=description, unit=unit)


# Example custom metrics for Sense-specific operations
circuit_provision_duration = create_custom_histogram(
    "sense_circuit_provision_duration_seconds",
    "Time to provision a circuit end-to-end",
    "s"
)

circuit_validation_duration = create_custom_histogram(
    "sense_circuit_validation_duration_seconds",
    "Time to validate circuit configuration",
    "s"
)

device_config_duration = create_custom_histogram(
    "sense_device_config_duration_seconds",
    "Time to configure network device",
    "s"
)
