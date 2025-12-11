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
ip_control_client: Any = None
granite_client: Any = None
kong_client: Any = None

if DEMO_MODE:
    # Use mock clients for demo
    ip_control_client = get_mock_client("ip_control")
    granite_client = get_mock_client("granite")
    kong_client = get_mock_client("kong")

    print("🎭 DEMO MODE ENABLED: Using mock clients for external dependencies")
else:
    # Use real clients for production
    # These imports will fail in demo mode if actual client code doesn't exist
    try:
        from arda_app.clients import IPControlClient, GraniteClient, KongClient
        ip_control_client = IPControlClient()
        granite_client = GraniteClient()
        kong_client = KongClient()

        print("✓ Production mode: Using real external clients")
    except ImportError as e:
        print(f"⚠️  Warning: Could not import production clients: {e}")
        print("    Falling back to mock clients for development")
        ip_control_client = get_mock_client("ip_control")
        granite_client = get_mock_client("granite")
        kong_client = get_mock_client("kong")


def is_demo_mode() -> bool:
    """Check if running in demo mode"""
    return DEMO_MODE


def get_ip_control_client():
    """Get IP Control client (real or mocked based on DEMO_MODE)"""
    return ip_control_client


def get_granite_client():
    """Get Granite CMDB client (real or mocked based on DEMO_MODE)"""
    return granite_client


def get_kong_client():
    """Get Kong API Gateway client (real or mocked based on DEMO_MODE)"""
    return kong_client
