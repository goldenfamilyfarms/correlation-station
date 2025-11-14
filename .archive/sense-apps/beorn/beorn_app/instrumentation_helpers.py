"""
Enhanced OTEL Instrumentation for Beorn
Topology extraction spans with vendor/FQDN attributes

Based on patterns from mdso-dev/all-product-logs-multiprocess and mdso-dev/meta
"""

import logging
from typing import Optional, Dict, Any, List
from functools import wraps
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

# Import shared utilities
import sys
import os
# Add mdso-instrumentation to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'mdso-instrumentation'))

try:
    from otel_mdso_utils import (
        MDSOSpanHelper,
        MDSORegexPatterns,
        ErrorPatternMatcher,
        extract_vendor_from_node_name,
        extract_fqdn_from_node_name,
        validate_beorn_response,
        VENDOR_RESOURCE_MAPPING
    )
except ImportError as e:
    logger.warning(f"Could not import otel_mdso_utils: {e}. Using local implementations.")
    # Fallback implementations
    class MDSOSpanHelper:
        @staticmethod
        def create_topology_span(tracer, circuit_id, operation="fetch"):
            return tracer.start_span(f"beorn.topology.{operation}")

        @staticmethod
        def add_topology_attributes(span, **kwargs):
            for key, value in kwargs.items():
                if value is not None:
                    span.set_attribute(f"beorn.{key}", value)

        @staticmethod
        def set_correlation_baggage(**kwargs):
            pass

        @staticmethod
        def record_span_event(span, event_name, attributes=None):
            span.add_event(event_name, attributes=attributes or {})

    class ErrorPatternMatcher:
        def extract_all_identifiers(self, error_message):
            return {}

        def categorize_error(self, error_message):
            return {"category": "UNKNOWN_ERROR", "type": "Uncategorized"}

    def extract_vendor_from_node_name(node_name_list):
        try:
            if len(node_name_list) > 2:
                return node_name_list[2].get("value", "").lower()
        except:
            return None

    def extract_fqdn_from_node_name(node_name_list):
        try:
            if len(node_name_list) > 6:
                return node_name_list[6].get("value")
        except:
            return None

    def validate_beorn_response(data):
        return len(data) >= 8 if isinstance(data, dict) else False


# Get tracer
tracer = trace.get_tracer(__name__)


# ========================================
# Decorators for Topology Operations
# ========================================

def instrument_topology_fetch(circuit_id_arg="cid"):
    """
    Decorator to instrument topology fetch operations

    Args:
        circuit_id_arg: Name of the argument containing circuit_id

    Usage:
        @instrument_topology_fetch()
        def fetch_topology(self, cid):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract circuit_id from arguments
            circuit_id = kwargs.get(circuit_id_arg)
            if not circuit_id and len(args) > 0:
                # Try to get from self.cid if it's a method
                if hasattr(args[0], circuit_id_arg):
                    circuit_id = getattr(args[0], circuit_id_arg)

            circuit_id = circuit_id or "unknown"

            # Create span
            with MDSOSpanHelper.create_topology_span(
                tracer,
                circuit_id,
                operation="fetch"
            ) as span:
                try:
                    # Set correlation baggage
                    MDSOSpanHelper.set_correlation_baggage(circuit_id=circuit_id)

                    # Execute function
                    result = func(*args, **kwargs)

                    # Add success event
                    MDSOSpanHelper.record_span_event(
                        span,
                        "topology.fetch.success",
                        {"circuit_id": circuit_id}
                    )

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    # Record error
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)

                    # Categorize error
                    error_matcher = ErrorPatternMatcher()
                    error_info = error_matcher.categorize_error(str(e))

                    MDSOSpanHelper.add_error_attributes(
                        span,
                        error_category=error_info.get("category"),
                        error_message=str(e)
                    )

                    raise

        return wrapper
    return decorator


def instrument_topology_parse():
    """
    Decorator to instrument topology parsing operations

    Usage:
        @instrument_topology_parse()
        def parse_topology(self, topology_data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_span("beorn.topology.parse") as span:
                try:
                    result = func(*args, **kwargs)

                    # Extract topology metadata if result is available
                    if isinstance(result, dict):
                        service_type = result.get("serviceType")
                        if service_type:
                            MDSOSpanHelper.add_topology_attributes(
                                span,
                                service_type=service_type
                            )

                        # Count topology nodes
                        if "topology" in result:
                            total_nodes = 0
                            for topo in result.get("topology", []):
                                nodes = topo.get("data", {}).get("node", [])
                                total_nodes += len(nodes)

                            MDSOSpanHelper.add_topology_attributes(
                                span,
                                topology_node_count=total_nodes
                            )

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator


# ========================================
# Helper Functions for Topology Instrumentation
# ========================================

def instrument_device_extraction(
    circuit_id: str,
    node_data: Dict[str, Any],
    node_index: int,
    topology_type: str = "aloc"
) -> None:
    """
    Create a span for device extraction from topology

    Args:
        circuit_id: Circuit identifier
        node_data: Node data from Beorn topology
        node_index: Index of node in topology
        topology_type: Type of topology (aloc, zloc)
    """
    with tracer.start_span(f"beorn.device.extract") as span:
        try:
            # Set basic attributes
            span.set_attribute("mdso.circuit_id", circuit_id)
            span.set_attribute("beorn.node_index", node_index)
            span.set_attribute("beorn.topology_type", topology_type)

            # Extract device info
            node_name_list = node_data.get("name", [])

            vendor = extract_vendor_from_node_name(node_name_list)
            fqdn = extract_fqdn_from_node_name(node_name_list)

            # Add device attributes
            MDSOSpanHelper.add_topology_attributes(
                span,
                vendor=vendor,
                fqdn=fqdn
            )

            # Set correlation baggage
            if fqdn:
                MDSOSpanHelper.set_correlation_baggage(
                    circuit_id=circuit_id,
                    fqdn=fqdn
                )

            # Record event
            MDSOSpanHelper.record_span_event(
                span,
                "device.extracted",
                {
                    "vendor": vendor,
                    "fqdn": fqdn,
                    "topology_type": topology_type,
                    "node_index": node_index
                }
            )

            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.warning(f"Failed to instrument device extraction: {e}")


def instrument_beorn_validation(
    circuit_id: str,
    response_data: Dict[str, Any]
) -> bool:
    """
    Create a span for Beorn response validation

    Args:
        circuit_id: Circuit identifier
        response_data: Beorn API response

    Returns:
        True if valid, False otherwise
    """
    with tracer.start_span("beorn.validation") as span:
        try:
            span.set_attribute("mdso.circuit_id", circuit_id)

            # Validate response
            is_valid = validate_beorn_response(response_data)
            element_count = len(response_data) if isinstance(response_data, dict) else 0

            # Add validation attributes
            MDSOSpanHelper.add_topology_attributes(
                span,
                validation_status=is_valid
            )
            span.set_attribute("beorn.element_count", element_count)
            span.set_attribute("beorn.validation.expected_count", 8)

            # Record event
            MDSOSpanHelper.record_span_event(
                span,
                "validation.complete",
                {
                    "is_valid": is_valid,
                    "element_count": element_count,
                    "expected_count": 8
                }
            )

            if is_valid:
                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, "Validation failed: insufficient elements"))

            return is_valid

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Beorn validation error: {e}")
            return False


def create_vendor_mapping_span(
    fqdn: str,
    vendor: str
) -> Optional[str]:
    """
    Create a span for vendor resource type mapping

    Args:
        fqdn: Device FQDN
        vendor: Device vendor name

    Returns:
        Resource type ID or None
    """
    with tracer.start_span("beorn.vendor.map") as span:
        try:
            span.set_attribute("network.device.fqdn", fqdn)
            span.set_attribute("network.device.vendor", vendor.lower())

            # Map vendor to resource type
            from otel_mdso_utils import VENDOR_RESOURCE_MAPPING
            resource_type = VENDOR_RESOURCE_MAPPING.get(vendor.lower())

            if resource_type:
                span.set_attribute("network.device.resource_type", resource_type)

                # Record event
                MDSOSpanHelper.record_span_event(
                    span,
                    "vendor.mapped",
                    {
                        "vendor": vendor,
                        "resource_type": resource_type,
                        "fqdn": fqdn
                    }
                )

                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, f"Unknown vendor: {vendor}"))

            return resource_type

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.warning(f"Vendor mapping error: {e}")
            return None


# ========================================
# Context Manager for Topology Operations
# ========================================

class TopologyOperationContext:
    """
    Context manager for topology operations

    Usage:
        with TopologyOperationContext(circuit_id, "fetch") as ctx:
            topology = fetch_from_beorn(circuit_id)
            ctx.add_device(fqdn="device.example.com", vendor="juniper")
    """

    def __init__(self, circuit_id: str, operation: str = "process"):
        self.circuit_id = circuit_id
        self.operation = operation
        self.span = None
        self.devices = []

    def __enter__(self):
        self.span = MDSOSpanHelper.create_topology_span(
            tracer,
            self.circuit_id,
            operation=self.operation
        )
        self.span.__enter__()

        # Set correlation baggage
        MDSOSpanHelper.set_correlation_baggage(circuit_id=self.circuit_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)

            # Categorize error
            error_matcher = ErrorPatternMatcher()
            error_info = error_matcher.categorize_error(str(exc_val))

            MDSOSpanHelper.add_error_attributes(
                self.span,
                error_category=error_info.get("category"),
                error_message=str(exc_val)
            )
        else:
            self.span.set_status(Status(StatusCode.OK))

            # Record summary event
            MDSOSpanHelper.record_span_event(
                self.span,
                f"topology.{self.operation}.complete",
                {
                    "circuit_id": self.circuit_id,
                    "device_count": len(self.devices)
                }
            )

        self.span.__exit__(exc_type, exc_val, exc_tb)
        return False

    def add_device(self, fqdn: Optional[str] = None, vendor: Optional[str] = None):
        """Record a device found in topology"""
        device_info = {}
        if fqdn:
            device_info["fqdn"] = fqdn
        if vendor:
            device_info["vendor"] = vendor

        self.devices.append(device_info)

        # Update span attributes
        MDSOSpanHelper.add_topology_attributes(
            self.span,
            vendor=vendor,
            fqdn=fqdn,
            topology_node_count=len(self.devices)
        )

        # Set correlation baggage for last device
        if fqdn:
            MDSOSpanHelper.set_correlation_baggage(
                circuit_id=self.circuit_id,
                fqdn=fqdn
            )
