"""
Test MDSO field extraction in correlation engine normalizer
"""
import pytest
from app.pipeline.normalizer import LogNormalizer
from app.models import LogBatch, LogRecord, LogResource


def test_circuit_id_extraction():
    """Test circuit ID extraction from message"""
    normalizer = LogNormalizer()

    message = "Creating service for circuit: 80.L1XX.005054..CHTR on device JFVLINBJ2CW.CHTRSE.COM"
    extracted = normalizer._extract_mdso_fields(message, {})

    assert extracted["circuit_id"] == "80.L1XX.005054..CHTR"


def test_resource_id_extraction():
    """Test resource ID (UUID) extraction"""
    normalizer = LogNormalizer()

    message = "Processing resource: 550e8400-e29b-41d4-a716-446655440000 for deployment"
    extracted = normalizer._extract_mdso_fields(message, {})

    assert extracted["resource_id"] == "550e8400-e29b-41d4-a716-446655440000"


def test_fqdn_extraction():
    """Test FQDN and TID extraction"""
    normalizer = LogNormalizer()

    message = "Connecting to device JFVLINBJ2CW.CHTRSE.COM for configuration"
    extracted = normalizer._extract_mdso_fields(message, {})

    assert extracted["fqdn"] == "JFVLINBJ2CW.CHTRSE.COM"
    assert extracted["tid"] == "JFVLINBJ2CW"


def test_service_type_extraction():
    """Test service type extraction (ELAN, ELINE, etc.)"""
    normalizer = LogNormalizer()

    message = "Provisioning service type: ELAN for customer"
    extracted = normalizer._extract_mdso_fields(message, {})

    assert extracted["service_type"] == "ELAN"


def test_error_code_extraction():
    """Test error code extraction (DE-1000, etc.)"""
    normalizer = LogNormalizer()

    message = "Operation failed with error code DE-1000: Device unreachable"
    extracted = normalizer._extract_mdso_fields(message, {})

    assert extracted["error_code"] == "DE-1000"


def test_error_categorization():
    """Test error categorization"""
    normalizer = LogNormalizer()

    message = "unable to connect to device JFVLINBJ2CW.CHTRSE.COM - timeout after 30s"
    extracted = normalizer._extract_mdso_fields(message, {"severity": "ERROR"})

    assert extracted["error_category"] == "CONNECTIVITY_ERROR"
    assert extracted["error_type"] == "Device Unreachable"


def test_comprehensive_extraction():
    """Test extraction of multiple fields from complex message"""
    normalizer = LogNormalizer()

    message = (
        "Nov 16 10:30:00 mdso-host: Creating circuit: 80.L1XX.005054..CHTR "
        "for device JFVLINBJ2CW.CHTRSE.COM (vendor: juniper) "
        "resource: 550e8400-e29b-41d4-a716-446655440000 service type: ELAN "
        "state: CREATE_IN_PROGRESS"
    )
    extracted = normalizer._extract_mdso_fields(message, {})

    assert extracted["circuit_id"] == "80.L1XX.005054..CHTR"
    assert extracted["fqdn"] == "JFVLINBJ2CW.CHTRSE.COM"
    assert extracted["tid"] == "JFVLINBJ2CW"
    assert extracted["resource_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert extracted["service_type"] == "ELAN"
    assert extracted["orch_state"] == "CREATE_IN_PROGRESS"


def test_no_overwrite_existing_fields():
    """Test that existing fields are not overwritten"""
    normalizer = LogNormalizer()

    message = "Creating circuit: 99.L1XX.999999..TEST"
    existing = {"circuit_id": "80.L1XX.005054..CHTR"}  # Existing value
    extracted = normalizer._extract_mdso_fields(message, existing)

    # Should not overwrite existing circuit_id
    assert "circuit_id" not in extracted


def test_full_normalization_with_mdso_extraction():
    """Test full log record normalization with MDSO field extraction"""
    normalizer = LogNormalizer()

    # Create a log batch with MDSO log
    resource = LogResource(
        service="mdso",
        host="mdso-dev-host",
        env="dev"
    )

    record = LogRecord(
        timestamp="2025-11-16T10:30:00.000Z",
        severity="ERROR",
        message="Failed to provision circuit: 80.L1XX.005054..CHTR on JFVLINBJ2CW.CHTRSE.COM - unable to connect to device",
    )

    batch = LogBatch(resource=resource, records=[record])

    # Normalize
    normalized = normalizer.normalize_log_batch(batch)

    assert len(normalized) == 1
    result = normalized[0]

    # Check basic fields
    assert result["service"] == "mdso"
    assert result["severity"] == "ERROR"

    # Check extracted MDSO fields
    assert result["circuit_id"] == "80.L1XX.005054..CHTR"
    assert result["fqdn"] == "JFVLINBJ2CW.CHTRSE.COM"
    assert result["tid"] == "JFVLINBJ2CW"

    # Check error categorization
    assert result["error_category"] == "CONNECTIVITY_ERROR"
    assert result["error_type"] == "Device Unreachable"


def test_ip_validation_error():
    """Test IP validation error categorization"""
    normalizer = LogNormalizer()

    message = "IP 192.168.1.999 does not appear to be an IPv4 or IPv6 address"
    extracted = normalizer._extract_mdso_fields(message, {"severity": "ERROR"})

    assert extracted["error_category"] == "IP_VALIDATION_ERROR"
    assert extracted["error_type"] == "Invalid IPv4/IPv6"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
