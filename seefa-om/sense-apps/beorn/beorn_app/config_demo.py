"""
Demo configuration with mocked dependencies
Blueprint Feature 7: Public Demo Branch

When DEMO_MODE=true, use mock clients instead of real external dependencies
"""
import os
import sys
from typing import Any

# Add demo_mocks to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../shared-libs"))

from demo_mocks.external_clients import get_mock_client

# Feature flag for demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Client instances
mdso_client: Any = None
tacacs_client: Any = None
snmp_client: Any = None

if DEMO_MODE:
    # Use mock clients for demo
    mdso_client = get_mock_client("mdso")
    tacacs_client = get_mock_client("tacacs")
    snmp_client = get_mock_client("snmp")

    print("🎭 DEMO MODE ENABLED: Using mock clients for external dependencies")
else:
    # Use real clients for production
    try:
        from beorn_app.clients import MDSOClient, TACACSClient, SNMPClient
        mdso_client = MDSOClient()
        tacacs_client = TACACSClient()
        snmp_client = SNMPClient()

        print("✓ Production mode: Using real external clients")
    except ImportError as e:
        print(f"⚠️  Warning: Could not import production clients: {e}")
        print("    Falling back to mock clients for development")
        mdso_client = get_mock_client("mdso")
        tacacs_client = get_mock_client("tacacs")
        snmp_client = get_mock_client("snmp")


def is_demo_mode() -> bool:
    """Check if running in demo mode"""
    return DEMO_MODE


def get_mdso_client():
    """Get MDSO client (real or mocked based on DEMO_MODE)"""
    return mdso_client


def get_tacacs_client():
    """Get TACACS+ client (real or mocked based on DEMO_MODE)"""
    return tacacs_client


def get_snmp_client():
    """Get SNMP client (real or mocked based on DEMO_MODE)"""
    return snmp_client
