"""
MDSO Regex Patterns and Error Extraction
Based on patterns from mdso-dev/meta/my_modules/auto_regex_error_tool.py

Author: Derrick Golden
Version: 1.0.0
"""

import re
from typing import Optional, Dict, List


class MDSOPatterns:
    """
    Comprehensive regex patterns for MDSO log parsing and error extraction
    Production-tested patterns from META tool
    """

    # ========================================
    # Port and Interface Patterns
    # ========================================
    ET_PORT = r"(?i:ET-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)"
    GE_PORT = r"(?i:GE-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)"
    XE_PORT = r"(?i:XE-\d{1,2}/\d{1,2}/\d{1,2}(\.\d{1,4})?)"
    ETH_PORT = r"(?i:ETH-PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    LAG = r"(?i:LAG\d)"
    AE = r"(?i:(?<=\W)AE(\d{1,2})?(\.\d{2,4})?)"
    TPE_FP = r"(?i:TPE_FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_CTP)"
    TPE_ACCESS = r"(?i:TPE_ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_PTP)"
    ACCESS = r"(?i:ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    FP = r"(?i:FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    FP_SHAPER = r"(?i:FP SHAPER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})"
    FP_POLICER = r"(?i:FP POLICER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})"
    FRE_FLOW = r"(?i:FRE_flow-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
    ETHERNET = r"(?i:ETHERNET-\d(/\d{1,2})?)"
    MANAGEMENT_TUNNEL = r"(?:(?<=MANAGEMENT TUNNEL-)\d{1,2})"

    # ========================================
    # Core Identifiers
    # ========================================
    RESOURCE_ID = r"(?:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
    DATE_TIME = r"(?P<DateTime_Search>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,6}Z))"
    IPV4 = r"(?:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d){1,3}(/\d{2})?)"
    IPV6 = r"(?:[a-fA-F0-9]{4}[:][^\s]+[:][a-fA-F0-9]{1,4})"
    TID = r"(?:[A-Z0-9]{10}W(-)?(: )?)"
    EVCID = r"(?<=evcId )\d{0,6}\s"
    VRFID = r"(?:(?<=\s)[A-Z]+\.[A-Z]+\.[0-9]+.[A-Z0-9_]+\.[A-Z]+)"
    VRFID_ELAN = r"(?:(?<=\s)[A-Z0-9_]+\.ELAN)"
    SERVICE_VLANS = r"(?:(FIA|DIA|ELINE|ELAN|VOICE|VIDEO)\d{3,4})"
    FQDN = r"[^\s]+\.COM"
    CIRCUIT_ID = r"(?:(FRE_)?[0-9]{2}\.[A-Z0-9]{4}\.[0-9]{6}\.\.[A-Z]{0,4})"
    REVISION_NUM = r"[0-9]{14}"
    BPS_DIGITS = r"(?P<bps>(\d+)(?= bps))"
    SHA_KEY = r"(?P<SHA>(?<=SHA )[a-f0-9]{40})"

    # ========================================
    # Error-Specific Patterns
    # ========================================
    NOT_IPV4_IPV6 = r"(?P<Not_IPv4_IPv6>([^\s]+)(?= does not appear to be an IPv4 or IPv6 address))"
    NOT_NETWORK_ADDRESS = r"(?P<Not_IP>(?<=IP )[^\s]+(?= is not a network address.))"
    IP_EXISTS = r"(?P<IP_Exists>(?<=IP )[^\s]+(?= already exists on device))"
    DEVICE_CPE_ROLE_INVALID = r"(?P<device_CPE_role_invalid>(?<=DEVICE ROLE CPE is INVALID for )[^\.]+)"
    DEVICE_PE_ROLE_INVALID = r"(?P<device_PE_role_invalid>(?<=DEVICE ROLE PE is INVALID for )[^\.]+)"
    NODE_NAME_INVALID = r"Node name: (.*?) is not valid"
    FAILED_TASK_NUM = r"(?:(?<=Failed task:)\(\d{1,2}\))"
    UNABLE_TO_CONNECT = r"unable to connect to device"
    GRANITE_DESIGN_ERROR = r"GRANITE DESIGN \|.*"

    @classmethod
    def extract_circuit_id(cls, text: str) -> Optional[str]:
        """Extract circuit ID from text"""
        match = re.search(cls.CIRCUIT_ID, text)
        return match.group(0) if match else None

    @classmethod
    def extract_tid(cls, text: str) -> Optional[str]:
        """Extract TID from text"""
        match = re.search(cls.TID, text)
        return match.group(0).rstrip('-: ') if match else None

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

    @classmethod
    def extract_ipv6(cls, text: str) -> Optional[str]:
        """Extract IPv6 address from text"""
        match = re.search(cls.IPV6, text)
        return match.group(0) if match else None

    @classmethod
    def extract_all_identifiers(cls, text: str) -> Dict[str, Optional[str]]:
        """Extract all MDSO identifiers from text"""
        return {
            "circuit_id": cls.extract_circuit_id(text),
            "tid": cls.extract_tid(text),
            "resource_id": cls.extract_resource_id(text),
            "fqdn": cls.extract_fqdn(text),
            "ipv4": cls.extract_ipv4(text),
            "ipv6": cls.extract_ipv6(text),
        }


class ErrorCategorizer:
    """
    Categorize errors using regex patterns
    Based on META tool's auto_regex_error_tool.py
    """

    def __init__(self):
        self.patterns = MDSOPatterns()

    def categorize(self, error_message: str) -> Dict[str, str]:
        """
        Categorize an error message

        Args:
            error_message: Raw error text

        Returns:
            Dictionary with category, type, and severity
        """
        # Normalize error message
        error_norm = error_message.lower()

        # Check for specific error patterns (priority order)
        if re.search(self.patterns.UNABLE_TO_CONNECT, error_norm):
            return {
                "category": "CONNECTIVITY_ERROR",
                "type": "Device Unreachable",
                "severity": "CRITICAL"
            }

        if re.search(self.patterns.GRANITE_DESIGN_ERROR, error_message):
            return {
                "category": "GRANITE_ERROR",
                "type": "Granite Design Issue",
                "severity": "ERROR"
            }

        if re.search(self.patterns.NOT_IPV4_IPV6, error_message):
            return {
                "category": "IP_VALIDATION_ERROR",
                "type": "Invalid IPv4/IPv6",
                "severity": "ERROR"
            }

        if re.search(self.patterns.NOT_NETWORK_ADDRESS, error_message):
            return {
                "category": "IP_VALIDATION_ERROR",
                "type": "Not Network Address",
                "severity": "ERROR"
            }

        if re.search(self.patterns.IP_EXISTS, error_message):
            return {
                "category": "IP_CONFLICT_ERROR",
                "type": "IP Already Exists",
                "severity": "WARNING"
            }

        if re.search(self.patterns.DEVICE_CPE_ROLE_INVALID, error_message):
            return {
                "category": "DEVICE_ROLE_ERROR",
                "type": "Invalid CPE Role",
                "severity": "ERROR"
            }

        if re.search(self.patterns.DEVICE_PE_ROLE_INVALID, error_message):
            return {
                "category": "DEVICE_ROLE_ERROR",
                "type": "Invalid PE Role",
                "severity": "ERROR"
            }

        if re.search(self.patterns.NODE_NAME_INVALID, error_message):
            return {
                "category": "NODE_ERROR",
                "type": "Invalid Node Name",
                "severity": "ERROR"
            }

        # Default
        return {
            "category": "UNKNOWN_ERROR",
            "type": "Uncategorized",
            "severity": "WARNING"
        }

    def extract_error_context(self, error_message: str) -> Dict[str, any]:
        """
        Extract full error context including identifiers and categorization

        Args:
            error_message: Raw error text

        Returns:
            Dictionary with identifiers and categorization
        """
        # Extract identifiers
        identifiers = self.patterns.extract_all_identifiers(error_message)

        # Categorize error
        categorization = self.categorize(error_message)

        # Combine
        return {
            **identifiers,
            **categorization,
            "raw_error": error_message[:500],  # Truncate like meta_main.py
        }


# ========================================
# Vendor Resource Type Mapping
# ========================================

VENDOR_RESOURCE_MAPPING = {
    "adva": "bpraadva.resourceTypes.NetworkFunction",
    "bpraadva": "bpraadva.resourceTypes.NetworkFunction",
    "juniper": "junipereq.resourceTypes.NetworkFunction",
    "rajuniper": "junipereq.resourceTypes.NetworkFunction",
    "cisco": "bpracisco.resourceTypes.NetworkFunction",
    "bpracisco": "bpracisco.resourceTypes.NetworkFunction",
    "rad": "radra.resourceTypes.NetworkFunction",
    "radra": "radra.resourceTypes.NetworkFunction",
}


def map_vendor_to_resource_type(vendor: str) -> Optional[str]:
    """
    Map vendor name to MDSO resource type ID

    Args:
        vendor: Vendor name (case-insensitive)

    Returns:
        Resource type ID or None
    """
    return VENDOR_RESOURCE_MAPPING.get(vendor.lower())


# ========================================
# Beorn Topology Helpers
# ========================================

def extract_vendor_from_beorn_node(node_name_list: List[Dict]) -> Optional[str]:
    """
    Extract vendor from Beorn node name array
    Vendor is at index 2 in the name array

    Args:
        node_name_list: Node name array from Beorn topology

    Returns:
        Vendor name (lowercase) or None
    """
    try:
        if len(node_name_list) > 2:
            vendor = node_name_list[2].get("value")
            return vendor.lower() if vendor else None
    except (IndexError, KeyError, AttributeError):
        return None


def extract_fqdn_from_beorn_node(node_name_list: List[Dict]) -> Optional[str]:
    """
    Extract FQDN from Beorn node name array
    FQDN is at index 6 in the name array

    Args:
        node_name_list: Node name array from Beorn topology

    Returns:
        FQDN or None
    """
    try:
        if len(node_name_list) > 6:
            return node_name_list[6].get("value")
    except (IndexError, KeyError, AttributeError):
        return None


def validate_beorn_response(data: Dict) -> bool:
    """
    Validate Beorn response has minimum required elements
    Healthy Beorn response has >= 8 elements

    Args:
        data: Beorn API response

    Returns:
        True if valid, False otherwise
    """
    element_count = len(data) if isinstance(data, dict) else 0
    return element_count >= 8
