"""
MDSO Regex Patterns and Error Extraction for Correlation Engine
Extracted patterns for parsing MDSO logs and categorizing errors

Author: Derrick Golden
Version: 1.0.0
"""

import re
from typing import Optional, Dict, List


class MDSOPatterns:
    """
    Comprehensive regex patterns for MDSO log parsing and error extraction
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
    FQDN = r"[A-Z0-9]{10}\.[A-Z0-9\.]+\.COM"
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
    ERROR_CODE = r"(?P<error_code>DE-\d+|DEF-\d+|ERR-\d+)"

    # ========================================
    # Service and Product Patterns
    # ========================================
    SERVICE_TYPE = r"(?i)(?:service[:\s]+|type[:\s]+)(ELAN|ELINE|FIA|VOICE|VIDEO)"
    PRODUCT_TYPE = r"(?i)(service_mapper|network_service|resource_agent|orchestration_engine)"
    ORCH_STATE = r"((?:CREATE|DELETE|UPDATE|ACTIVATE|DEACTIVATE)_IN_PROGRESS|(?:CREATE|DELETE|UPDATE)_(?:COMPLETE|FAILED))"

    @classmethod
    def extract_circuit_id(cls, text: str) -> Optional[str]:
        """Extract circuit ID from text"""
        match = re.search(cls.CIRCUIT_ID, text, re.IGNORECASE)
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
    def extract_error_code(cls, text: str) -> Optional[str]:
        """Extract error code (DE-1000, etc.)"""
        match = re.search(cls.ERROR_CODE, text)
        return match.group(1) if match else None

    @classmethod
    def extract_service_type(cls, text: str) -> Optional[str]:
        """Extract service type (ELAN, ELINE, etc.)"""
        match = re.search(cls.SERVICE_TYPE, text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    @classmethod
    def extract_product_type(cls, text: str) -> Optional[str]:
        """Extract product type"""
        match = re.search(cls.PRODUCT_TYPE, text, re.IGNORECASE)
        return match.group(1).lower() if match else None

    @classmethod
    def extract_orch_state(cls, text: str) -> Optional[str]:
        """Extract orchestration state"""
        match = re.search(cls.ORCH_STATE, text)
        return match.group(1) if match else None

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
            "error_code": cls.extract_error_code(text),
            "service_type": cls.extract_service_type(text),
            "product_type": cls.extract_product_type(text),
            "orch_state": cls.extract_orch_state(text),
        }


class ErrorCategorizer:
    """
    Categorize errors using regex patterns
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

        # Generic error detection
        if any(word in error_norm for word in ['error', 'fail', 'exception', 'critical']):
            return {
                "category": "GENERIC_ERROR",
                "type": "Unspecified Error",
                "severity": "ERROR"
            }

        # Default
        return {
            "category": "INFO",
            "type": "No Error",
            "severity": "INFO"
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

        # Combine (remove None values)
        result = {k: v for k, v in identifiers.items() if v is not None}
        result.update(categorization)
        result["raw_error"] = error_message[:500]  # Truncate

        return result


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
