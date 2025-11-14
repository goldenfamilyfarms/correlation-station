"""
MDSO OTEL Instrumentation Utilities
Shared utilities for enhanced OpenTelemetry instrumentation across SENSE apps

Based on patterns from:
- mdso-dev/all-product-logs-multiprocess/
- mdso-dev/meta/

Author: Derrick Golden
Version: 1.0.0
"""

import re
from typing import Optional, Dict, Any, List
from opentelemetry import trace, baggage
from opentelemetry.trace import Status, StatusCode
import logging

logger = logging.getLogger(__name__)

# ========================================
# Vendor Resource Type Mapping
# ========================================
VENDOR_RESOURCE_MAPPING = {
    "bpraadva": "bpraadva.resourceTypes.NetworkFunction",
    "rajuniper": "junipereq.resourceTypes.NetworkFunction",
    "radra": "radra.resourceTypes.NetworkFunction",
    "bpracisco": "bpracisco.resourceTypes.NetworkFunction",
    "adva": "bpraadva.resourceTypes.NetworkFunction",
    "juniper": "junipereq.resourceTypes.NetworkFunction",
    "rad": "radra.resourceTypes.NetworkFunction",
    "cisco": "bpracisco.resourceTypes.NetworkFunction",
}

# ========================================
# Regex Patterns for Log Parsing
# ========================================

class MDSORegexPatterns:
    """Comprehensive regex patterns for MDSO log parsing and error extraction"""

    # Port patterns
    ET = r"(?i:ET-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)"
    GE = r"(?i:GE-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)"
    XE = r"(?i:XE-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)"
    ETH_PORT = r"(?i:ETH-PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    LAG = r"(?i:LAG\d)"
    AE = r"(?i:(?<=\W)AE(\d{1,2})?(\.\d{2,4})?)"

    # Interface patterns
    TPE_FP = r"(?i:TPE_FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_CTP)"
    TPE_ACCESS = r"(?i:TPE_ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_PTP)"
    ACCESS = r"(?i:ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    FP = r"(?i:FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    FP_SHAPER = r"(?i:FP SHAPER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})"
    FP_POLICER = r"(?i:FP POLICER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})"
    FRE_FLOW = r"(?i:FRE_flow-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    ETHERNET = r"(?i:ETHERNET-\d(/\d{1,2})?)"
    MANAGEMENT_TUNNEL = r"(?:(?<=MANAGEMENT TUNNEL-)\d{1,2})"

    # Core identifiers
    RESOURCE_ID = r"(?:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
    DATE_TIME = r"(?P<DateTime_Search>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,6}Z))"
    IPV4 = r"(?:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d){1,3}(/\d{2})?)"
    IPV6 = r"(?:[a-fA-F0-9]{4}[:][^\s]+[:][a-fA-F0-9]{1,4})"
    TID = r"(?:[A-Z0-9]{10}W(-)?(:)?)"
    EVCID = r"(?<=evcId )\d{0,6}\s"
    VRFID = r"(?:(?<=\s)[A-Z]+\.[A-Z]+\.[0-9]+.[A-Z0-9_]+\.[A-Z]+)"
    VRFID_ELAN = r"(?:(?<=\s)[A-Z0-9_]+\.ELAN)"
    SERVICE_VLANS = r"(?:(FIA|DIA|ELINE|ELAN|VOICE|VIDEO)\d{3,4})"
    FQDN = r"[^\s]+COM"
    CIRCUIT_ID = r"(?:(FRE_)?[0-9]{2}\.[A-Z0-9]{4}\.[0-9]{6}\.\.[A-Z]{0,4})"
    REVISION_NUM = r"[0-9]{14}"
    BPS_DIGITS = r"(?P<bps>(\d+)(?= bps))"
    SHA_KEY = r"(?P<SHA>(?<=SHA )[a-f0-9]{40})"

    # Error-specific patterns
    NOT_IPV4_IPV6 = r"(?P<Not_IPv4_IPv6>([^\s]+)(?= does not appear to be an IPv4 or IPv6 address))"
    NOT_NETWORK_ADDRESS = r"(?P<Not_IP>(?<=IP )[^\s]+(?= is not a network address.))"
    IP_EXISTS = r"(?P<IP_Exists>(?<=IP )[^\s]+(?= already exists on device))"
    DEVICE_CPE_ROLE_INVALID = r"(?P<device_CPE_role_invalid>(?<=DEVICE ROLE CPE is INVALID for )[^\.]+)"
    DEVICE_PE_ROLE_INVALID = r"(?P<device_PE_role_invalid>(?<=DEVICE ROLE PE is INVALID for )[^\.]+)"
    NODE_NAME_INVALID = r"Node name: (.*?) is not valid"
    FAILED_TASK_NUM = r"(?:(?<=Failed task:)\(\d{1,2}\))"

    @classmethod
    def extract_circuit_id(cls, text: str) -> Optional[str]:
        """Extract circuit ID from text"""
        match = re.search(cls.CIRCUIT_ID, text)
        return match.group(0) if match else None

    @classmethod
    def extract_tid(cls, text: str) -> Optional[str]:
        """Extract TID from text"""
        match = re.search(cls.TID, text)
        return match.group(0) if match else None

    @classmethod
    def extract_resource_id(cls, text: str) -> Optional[str]:
        """Extract resource ID (UUID) from text"""
        match = re.search(cls.RESOURCE_ID, text)
        return match.group(0) if match else None

    @classmethod
    def extract_fqdn(cls, text: str) -> Optional[str]:
        """Extract FQDN from text"""
        match = re.search(cls.FQDN, text)
        return match.group(0) if match else None

    @classmethod
    def extract_ipv4(cls, text: str) -> Optional[str]:
        """Extract IPv4 address from text"""
        match = re.search(cls.IPV4, text)
        return match.group(0) if match else None


# ========================================
# OTEL Span Helpers
# ========================================

class MDSOSpanHelper:
    """Helper class for creating MDSO-specific OTEL spans"""

    @staticmethod
    def create_topology_span(
        tracer: trace.Tracer,
        circuit_id: str,
        operation: str = "fetch"
    ) -> trace.Span:
        """
        Create a span for Beorn topology operations

        Args:
            tracer: OpenTelemetry tracer
            circuit_id: Circuit identifier
            operation: Operation type (fetch, parse, validate)

        Returns:
            Active span
        """
        span = tracer.start_span(f"beorn.topology.{operation}")
        span.set_attribute("mdso.circuit_id", circuit_id)
        span.set_attribute("beorn.operation", operation)
        return span

    @staticmethod
    def create_network_function_span(
        tracer: trace.Tracer,
        tid: str,
        fqdn: Optional[str] = None,
        operation: str = "check"
    ) -> trace.Span:
        """
        Create a span for network function operations

        Args:
            tracer: OpenTelemetry tracer
            tid: Device TID
            fqdn: Device FQDN
            operation: Operation type (check, query, validate)

        Returns:
            Active span
        """
        span = tracer.start_span(f"network_function.{operation}")
        span.set_attribute("network.device.tid", tid)
        if fqdn:
            span.set_attribute("network.device.fqdn", fqdn)
        return span

    @staticmethod
    def add_topology_attributes(
        span: trace.Span,
        service_type: Optional[str] = None,
        vendor: Optional[str] = None,
        fqdn: Optional[str] = None,
        topology_node_count: Optional[int] = None,
        validation_status: Optional[bool] = None,
    ):
        """
        Add Beorn topology-specific attributes to a span

        Args:
            span: Active OTEL span
            service_type: Service type (FIA, ELAN, ELINE, etc.)
            vendor: Device vendor (adva, juniper, cisco, rad)
            fqdn: Device FQDN
            topology_node_count: Number of nodes in topology
            validation_status: Whether topology validation passed
        """
        if service_type:
            span.set_attribute("beorn.service_type", service_type)
            baggage.set_baggage("serviceType", service_type)

        if vendor:
            span.set_attribute("network.device.vendor", vendor.lower())
            resource_type = VENDOR_RESOURCE_MAPPING.get(vendor.lower())
            if resource_type:
                span.set_attribute("network.device.resource_type", resource_type)

        if fqdn:
            span.set_attribute("network.device.fqdn", fqdn)

        if topology_node_count is not None:
            span.set_attribute("beorn.topology.node_count", topology_node_count)

        if validation_status is not None:
            span.set_attribute("beorn.topology.validation_passed", validation_status)

    @staticmethod
    def add_network_function_attributes(
        span: trace.Span,
        communication_state: Optional[str] = None,
        ip_address: Optional[str] = None,
        vendor: Optional[str] = None,
        device_role: Optional[str] = None,
        provider_resource_id: Optional[str] = None,
    ):
        """
        Add network function-specific attributes to a span

        Args:
            span: Active OTEL span
            communication_state: Device communication state
            ip_address: Device IP address
            vendor: Device vendor
            device_role: Device role (CPE, PE)
            provider_resource_id: MDSO provider resource ID
        """
        if communication_state:
            span.set_attribute("network.device.communication_state", communication_state)

        if ip_address:
            span.set_attribute("network.device.ip_address", ip_address)

        if vendor:
            span.set_attribute("network.device.vendor", vendor.lower())
            resource_type = VENDOR_RESOURCE_MAPPING.get(vendor.lower())
            if resource_type:
                span.set_attribute("network.device.resource_type", resource_type)

        if device_role:
            span.set_attribute("network.device.role", device_role)

        if provider_resource_id:
            span.set_attribute("mdso.provider_resource_id", provider_resource_id)

    @staticmethod
    def add_error_attributes(
        span: trace.Span,
        error_code: Optional[str] = None,
        error_category: Optional[str] = None,
        error_message: Optional[str] = None,
        is_new_error: Optional[bool] = None,
    ):
        """
        Add error-tracking attributes to a span

        Args:
            span: Active OTEL span
            error_code: Error code (e.g., DE-1000)
            error_category: Categorized error type
            error_message: Raw error message (truncated to 500 chars)
            is_new_error: Whether this is a newly discovered error
        """
        if error_code:
            span.set_attribute("error.code", error_code)

        if error_category:
            span.set_attribute("error.category", error_category)

        if error_message:
            # Truncate to 500 chars like meta_main.py does
            truncated_msg = error_message[:500]
            span.set_attribute("error.message", truncated_msg)

        if is_new_error is not None:
            span.set_attribute("error.is_new", is_new_error)

    @staticmethod
    def set_correlation_baggage(
        circuit_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        tid: Optional[str] = None,
        fqdn: Optional[str] = None,
        provider_resource_id: Optional[str] = None,
    ):
        """
        Set correlation keys as baggage for cross-service tracing

        Implements the correlation chain:
        circuit_id → fqdn → provider_resource_id

        Args:
            circuit_id: Circuit identifier
            resource_id: MDSO resource ID
            tid: Device TID
            fqdn: Device FQDN
            provider_resource_id: MDSO provider resource ID
        """
        if circuit_id:
            baggage.set_baggage("mdso.circuit_id", circuit_id)

        if resource_id:
            baggage.set_baggage("mdso.resource_id", resource_id)

        if tid:
            baggage.set_baggage("network.device.tid", tid)

        if fqdn:
            baggage.set_baggage("network.device.fqdn", fqdn)

        if provider_resource_id:
            baggage.set_baggage("mdso.provider_resource_id", provider_resource_id)

    @staticmethod
    def record_span_event(
        span: trace.Span,
        event_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a span event with attributes

        Args:
            span: Active OTEL span
            event_name: Name of the event
            attributes: Event attributes
        """
        span.add_event(event_name, attributes=attributes or {})


# ========================================
# Error Pattern Matcher
# ========================================

class ErrorPatternMatcher:
    """Match and categorize errors using regex patterns from auto_regex_error_tool.py"""

    def __init__(self):
        self.patterns = MDSORegexPatterns()

    def extract_all_identifiers(self, error_message: str) -> Dict[str, Any]:
        """
        Extract all identifiers from an error message

        Args:
            error_message: Raw error text

        Returns:
            Dictionary of extracted identifiers
        """
        return {
            "circuit_id": self.patterns.extract_circuit_id(error_message),
            "tid": self.patterns.extract_tid(error_message),
            "resource_id": self.patterns.extract_resource_id(error_message),
            "fqdn": self.patterns.extract_fqdn(error_message),
            "ipv4": self.patterns.extract_ipv4(error_message),
        }

    def categorize_error(self, error_message: str) -> Dict[str, str]:
        """
        Categorize an error message

        Args:
            error_message: Raw error text

        Returns:
            Dictionary with category and details
        """
        # Check for specific error patterns
        if re.search(self.patterns.NOT_IPV4_IPV6, error_message):
            return {"category": "IP_VALIDATION_ERROR", "type": "Invalid IPv4/IPv6"}

        if re.search(self.patterns.NOT_NETWORK_ADDRESS, error_message):
            return {"category": "IP_VALIDATION_ERROR", "type": "Not Network Address"}

        if re.search(self.patterns.IP_EXISTS, error_message):
            return {"category": "IP_CONFLICT_ERROR", "type": "IP Already Exists"}

        if re.search(self.patterns.DEVICE_CPE_ROLE_INVALID, error_message):
            return {"category": "DEVICE_ROLE_ERROR", "type": "Invalid CPE Role"}

        if re.search(self.patterns.DEVICE_PE_ROLE_INVALID, error_message):
            return {"category": "DEVICE_ROLE_ERROR", "type": "Invalid PE Role"}

        if re.search(self.patterns.NODE_NAME_INVALID, error_message):
            return {"category": "NODE_ERROR", "type": "Invalid Node Name"}

        if "GRANITE DESIGN" in error_message:
            return {"category": "GRANITE_ERROR", "type": "Granite Design Issue"}

        if "unable to connect to device" in error_message.lower():
            return {"category": "CONNECTIVITY_ERROR", "type": "Device Unreachable"}

        return {"category": "UNKNOWN_ERROR", "type": "Uncategorized"}


# ========================================
# Beorn Topology Helpers
# ========================================

def extract_vendor_from_node_name(node_name_list: List[Dict]) -> Optional[str]:
    """
    Extract vendor from Beorn node name array

    Args:
        node_name_list: Node name array from Beorn topology

    Returns:
        Vendor name (lowercase) or None
    """
    try:
        # Vendor is at index 2 in the name array
        if len(node_name_list) > 2 and node_name_list[2].get("value"):
            return node_name_list[2]["value"].lower()
    except (IndexError, KeyError, AttributeError) as e:
        logger.warning(f"Failed to extract vendor from node: {e}")
    return None


def extract_fqdn_from_node_name(node_name_list: List[Dict]) -> Optional[str]:
    """
    Extract FQDN from Beorn node name array

    Args:
        node_name_list: Node name array from Beorn topology

    Returns:
        FQDN or None
    """
    try:
        # FQDN is at index 6 in the name array
        if len(node_name_list) > 6 and node_name_list[6].get("value"):
            return node_name_list[6]["value"]
    except (IndexError, KeyError, AttributeError) as e:
        logger.warning(f"Failed to extract FQDN from node: {e}")
    return None


def validate_beorn_response(data: Dict) -> bool:
    """
    Validate Beorn response has minimum required elements

    Args:
        data: Beorn API response

    Returns:
        True if valid (>= 8 elements), False otherwise
    """
    # Healthy Beorn response has 8 elements minimum
    element_count = len(data) if isinstance(data, dict) else 0
    return element_count >= 8
