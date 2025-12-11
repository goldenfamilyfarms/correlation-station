"""
Mock clients for external dependencies

Blueprint Feature 7: Demo branch with mocked responses
Provides 20-30 hardcoded JSON variants per dependency
"""
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class MockIPControlClient:
    """Mock IP Control (IPAM) client"""

    RESPONSES = [
        # Successful IPv4 allocation - 10 variants
        {
            "status": "success",
            "allocated_ips": ["10.100.1.10", "10.100.1.11"],
            "subnet": "10.100.1.0/24",
            "vlan": 100,
            "dns_records": ["circuit-001.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.2.15", "10.100.2.16"],
            "subnet": "10.100.2.0/24",
            "vlan": 101,
            "dns_records": ["circuit-002.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.3.20", "10.100.3.21"],
            "subnet": "10.100.3.0/24",
            "vlan": 102,
            "dns_records": ["circuit-003.demo.com", "circuit-003-backup.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.4.25"],
            "subnet": "10.100.4.0/24",
            "vlan": 103,
            "dns_records": ["circuit-004.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.5.30", "10.100.5.31", "10.100.5.32"],
            "subnet": "10.100.5.0/24",
            "vlan": 104,
            "dns_records": ["circuit-005.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.6.40", "10.100.6.41"],
            "subnet": "10.100.6.0/24",
            "vlan": 105,
            "dns_records": ["circuit-006.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.7.50", "10.100.7.51"],
            "subnet": "10.100.7.0/24",
            "vlan": 106,
            "dns_records": []
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.8.60", "10.100.8.61"],
            "subnet": "10.100.8.0/24",
            "vlan": 107,
            "dns_records": ["circuit-008.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.9.70"],
            "subnet": "10.100.9.0/24",
            "vlan": 108,
            "dns_records": ["circuit-009.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["10.100.10.80", "10.100.10.81"],
            "subnet": "10.100.10.0/24",
            "vlan": 109,
            "dns_records": ["circuit-010.demo.com"]
        },
        # Successful IPv6 allocation - 5 variants
        {
            "status": "success",
            "allocated_ips": ["2001:db8:100::10", "2001:db8:100::11"],
            "subnet": "2001:db8:100::/64",
            "vlan": 200,
            "dns_records": ["ipv6-circuit-001.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["2001:db8:101::20", "2001:db8:101::21"],
            "subnet": "2001:db8:101::/64",
            "vlan": 201,
            "dns_records": ["ipv6-circuit-002.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["2001:db8:102::30"],
            "subnet": "2001:db8:102::/64",
            "vlan": 202,
            "dns_records": ["ipv6-circuit-003.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["2001:db8:103::40", "2001:db8:103::41", "2001:db8:103::42"],
            "subnet": "2001:db8:103::/64",
            "vlan": 203,
            "dns_records": ["ipv6-circuit-004.demo.com"]
        },
        {
            "status": "success",
            "allocated_ips": ["2001:db8:104::50", "2001:db8:104::51"],
            "subnet": "2001:db8:104::/64",
            "vlan": 204,
            "dns_records": []
        },
        # Error cases - 10 variants
        {
            "status": "error",
            "error": "No available IPs in pool",
            "subnet": "10.100.20.0/24",
            "vlan": 110
        },
        {
            "status": "error",
            "error": "Subnet not found in IPAM",
            "requested_subnet": "10.100.99.0/24"
        },
        {
            "status": "error",
            "error": "VLAN already assigned to another circuit",
            "vlan": 111,
            "existing_circuit": "DEMO.CIRCUIT.999..MOCK"
        },
        {
            "status": "error",
            "error": "IP address already in use",
            "ip": "10.100.1.10",
            "assigned_to": "DEMO.CIRCUIT.888..MOCK"
        },
        {
            "status": "error",
            "error": "DNS registration failed",
            "allocated_ips": ["10.100.11.90"],
            "dns_error": "Domain not found"
        },
        {
            "status": "error",
            "error": "Invalid subnet mask",
            "requested_subnet": "10.100.12.0/33"
        },
        {
            "status": "error",
            "error": "IPAM database connection timeout",
            "timeout_ms": 30000
        },
        {
            "status": "error",
            "error": "Insufficient permissions for subnet",
            "subnet": "10.100.13.0/24",
            "required_role": "network_admin"
        },
        {
            "status": "error",
            "error": "IP allocation quota exceeded",
            "current_allocations": 1000,
            "quota_limit": 1000
        },
        {
            "status": "error",
            "error": "Reserved IP range conflict",
            "requested_ips": ["10.100.14.1", "10.100.14.2"],
            "reserved_range": "10.100.14.1-10.100.14.10"
        },
    ]

    def allocate_ips(self, circuit_id: str, count: int = 2, ipv6: bool = False) -> Dict:
        """Allocate IP addresses (mocked)"""
        return random.choice(self.RESPONSES)

    def release_ips(self, circuit_id: str, ips: List[str]) -> Dict:
        """Release IP addresses (mocked)"""
        return random.choice([
            {"status": "success", "released_ips": ips},
            {"status": "error", "error": "IP not found in allocation table"}
        ])


class MockGraniteClient:
    """Mock Granite (CMDB) client"""

    RESPONSES = [
        # Successful circuit creation - 10 variants
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.001..MOCK",
            "product_id": "prod-12345",
            "device_a": "router-a.demo.com",
            "device_z": "router-z.demo.com",
            "bandwidth": "10G",
            "service_type": "eline"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.002..MOCK",
            "product_id": "prod-12346",
            "device_a": "switch-a.demo.com",
            "device_z": "switch-z.demo.com",
            "bandwidth": "1G",
            "service_type": "elan"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.003..MOCK",
            "product_id": "prod-12347",
            "device_a": "router-b.demo.com",
            "device_z": "router-c.demo.com",
            "bandwidth": "100G",
            "service_type": "eline"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.004..MOCK",
            "product_id": "prod-12348",
            "device_a": "router-d.demo.com",
            "device_z": "router-e.demo.com",
            "bandwidth": "40G",
            "service_type": "evpl"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.005..MOCK",
            "product_id": "prod-12349",
            "device_a": "switch-b.demo.com",
            "device_z": "switch-c.demo.com",
            "bandwidth": "10G",
            "service_type": "elan"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.006..MOCK",
            "product_id": "prod-12350",
            "device_a": "router-f.demo.com",
            "device_z": "router-g.demo.com",
            "bandwidth": "25G",
            "service_type": "eline"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.007..MOCK",
            "product_id": "prod-12351",
            "device_a": "router-h.demo.com",
            "device_z": "router-i.demo.com",
            "bandwidth": "50G",
            "service_type": "evpl"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.008..MOCK",
            "product_id": "prod-12352",
            "device_a": "switch-d.demo.com",
            "device_z": "switch-e.demo.com",
            "bandwidth": "10G",
            "service_type": "elan"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.009..MOCK",
            "product_id": "prod-12353",
            "device_a": "router-j.demo.com",
            "device_z": "router-k.demo.com",
            "bandwidth": "100G",
            "service_type": "eline"
        },
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.010..MOCK",
            "product_id": "prod-12354",
            "device_a": "router-l.demo.com",
            "device_z": "router-m.demo.com",
            "bandwidth": "10G",
            "service_type": "eline"
        },
        # Error cases - 15 variants
        {
            "status": "error",
            "error": "Circuit already exists",
            "existing_circuit_id": "DEMO.CIRCUIT.999..MOCK"
        },
        {
            "status": "error",
            "error": "Device not found in CMDB",
            "device": "router-invalid.demo.com"
        },
        {
            "status": "error",
            "error": "Insufficient port capacity on device",
            "device": "router-a.demo.com",
            "available_bandwidth": "5G",
            "requested_bandwidth": "10G"
        },
        {
            "status": "error",
            "error": "Invalid service type",
            "service_type": "invalid_type",
            "valid_types": ["eline", "elan", "evpl"]
        },
        {
            "status": "error",
            "error": "Device not reachable",
            "device": "router-down.demo.com",
            "last_seen": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "status": "error",
            "error": "Duplicate product ID",
            "product_id": "prod-12345",
            "existing_circuit": "DEMO.CIRCUIT.001..MOCK"
        },
        {
            "status": "error",
            "error": "CMDB write permission denied",
            "user": "demo_user",
            "required_role": "provisioning_admin"
        },
        {
            "status": "error",
            "error": "Device maintenance window active",
            "device": "router-b.demo.com",
            "maintenance_until": (datetime.utcnow() + timedelta(hours=4)).isoformat()
        },
        {
            "status": "error",
            "error": "Invalid bandwidth value",
            "bandwidth": "999G",
            "valid_options": ["1G", "10G", "25G", "40G", "50G", "100G"]
        },
        {
            "status": "error",
            "error": "Device pair not in same location",
            "device_a": "router-a.demo.com",
            "device_z": "router-z.demo.com",
            "location_a": "NYC",
            "location_z": "LAX"
        },
        {
            "status": "error",
            "error": "Circuit validation failed",
            "validation_errors": ["Missing VLAN tag", "Invalid port configuration"]
        },
        {
            "status": "error",
            "error": "CMDB database timeout",
            "timeout_ms": 5000
        },
        {
            "status": "error",
            "error": "Device model not supported",
            "device": "legacy-switch.demo.com",
            "model": "Old-Switch-2000"
        },
        {
            "status": "error",
            "error": "Port already assigned",
            "device": "router-a.demo.com",
            "port": "GigabitEthernet0/0/1",
            "assigned_to": "DEMO.CIRCUIT.888..MOCK"
        },
        {
            "status": "error",
            "error": "Circuit creation quota exceeded",
            "daily_quota": 100,
            "circuits_created_today": 100
        },
    ]

    def create_circuit(self, circuit_data: Dict) -> Dict:
        """Create circuit in CMDB (mocked)"""
        return random.choice(self.RESPONSES)

    def update_circuit(self, circuit_id: str, updates: Dict) -> Dict:
        """Update circuit in CMDB (mocked)"""
        return random.choice([
            {"status": "success", "circuit_id": circuit_id, "updated_fields": list(updates.keys())},
            {"status": "error", "error": "Circuit not found", "circuit_id": circuit_id}
        ])

    def delete_circuit(self, circuit_id: str) -> Dict:
        """Delete circuit from CMDB (mocked)"""
        return random.choice([
            {"status": "success", "circuit_id": circuit_id, "deleted": True},
            {"status": "error", "error": "Circuit has active services", "circuit_id": circuit_id}
        ])


class MockKongClient:
    """Mock Kong (API Gateway) client"""

    RESPONSES = [
        # Successful auth - 10 variants
        {
            "status": "success",
            "authenticated": True,
            "user": "demo-user",
            "permissions": ["read", "write"],
            "token_expires_in": 3600
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "admin-user",
            "permissions": ["read", "write", "admin"],
            "token_expires_in": 7200
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "readonly-user",
            "permissions": ["read"],
            "token_expires_in": 3600
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "service-account",
            "permissions": ["read", "write", "provision"],
            "token_expires_in": 86400
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "operator-user",
            "permissions": ["read", "write", "monitor"],
            "token_expires_in": 3600
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "developer-user",
            "permissions": ["read", "write", "debug"],
            "token_expires_in": 3600
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "manager-user",
            "permissions": ["read", "write", "approve"],
            "token_expires_in": 7200
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "guest-user",
            "permissions": ["read"],
            "token_expires_in": 1800
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "automation-user",
            "permissions": ["read", "write", "provision", "deprovision"],
            "token_expires_in": 86400
        },
        {
            "status": "success",
            "authenticated": True,
            "user": "auditor-user",
            "permissions": ["read", "audit"],
            "token_expires_in": 3600
        },
        # Error cases - 15 variants
        {
            "status": "error",
            "authenticated": False,
            "error": "Invalid credentials"
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "User not found"
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Account locked due to multiple failed attempts",
            "locked_until": (datetime.utcnow() + timedelta(minutes=30)).isoformat()
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Token expired",
            "expired_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Insufficient permissions",
            "required": "admin",
            "current": "read"
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Account disabled",
            "disabled_at": (datetime.utcnow() - timedelta(days=30)).isoformat()
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Authentication service unavailable",
            "retry_after": 60
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Invalid API key format"
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Rate limit exceeded",
            "limit": 100,
            "window": "1 minute",
            "retry_after": 45
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "IP address not whitelisted",
            "ip": "192.168.1.100"
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Multi-factor authentication required"
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Password expired",
            "expired_days_ago": 90
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Session timeout",
            "last_activity": (datetime.utcnow() - timedelta(hours=8)).isoformat()
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Token revoked",
            "revoked_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "status": "error",
            "authenticated": False,
            "error": "Invalid client certificate"
        },
    ]

    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate user (mocked)"""
        return random.choice(self.RESPONSES)

    def validate_token(self, token: str) -> Dict:
        """Validate auth token (mocked)"""
        return random.choice([
            {"status": "success", "valid": True, "user": "demo-user"},
            {"status": "error", "valid": False, "error": "Token expired"}
        ])


class MockMDSOClient:
    """Mock MDSO (orchestrator) client"""

    # 30 different RA telemetry configurations
    RA_TELEMETRY_RESPONSES = [
        # Successful provisions - 15 variants
        {
            "status": "success",
            "operation": "provision_eline",
            "device": "ciena-saos-01.demo.com",
            "commands_executed": 15,
            "elapsed_time_ms": 3500,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_elan",
            "device": "ciena-saos-02.demo.com",
            "commands_executed": 22,
            "elapsed_time_ms": 4200,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_evpl",
            "device": "cisco-ios-01.demo.com",
            "commands_executed": 18,
            "elapsed_time_ms": 2800,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "deprovision_eline",
            "device": "ciena-saos-03.demo.com",
            "commands_executed": 10,
            "elapsed_time_ms": 2100,
            "telemetry": {
                "pre_check": "PASSED",
                "config_removed": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "modify_bandwidth",
            "device": "ciena-saos-04.demo.com",
            "commands_executed": 8,
            "elapsed_time_ms": 1500,
            "telemetry": {
                "pre_check": "PASSED",
                "bandwidth_updated": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_eline",
            "device": "juniper-mx-01.demo.com",
            "commands_executed": 20,
            "elapsed_time_ms": 5000,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_elan",
            "device": "nokia-sr-01.demo.com",
            "commands_executed": 25,
            "elapsed_time_ms": 6200,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "verify_service",
            "device": "ciena-saos-05.demo.com",
            "commands_executed": 5,
            "elapsed_time_ms": 800,
            "telemetry": {
                "service_status": "ACTIVE",
                "bandwidth_test": "PASSED",
                "connectivity_test": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "restore_service",
            "device": "ciena-saos-06.demo.com",
            "commands_executed": 12,
            "elapsed_time_ms": 2500,
            "telemetry": {
                "pre_check": "PASSED",
                "config_restored": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "update_vlan",
            "device": "cisco-ios-02.demo.com",
            "commands_executed": 6,
            "elapsed_time_ms": 1200,
            "telemetry": {
                "pre_check": "PASSED",
                "vlan_updated": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_eline",
            "device": "arista-eos-01.demo.com",
            "commands_executed": 14,
            "elapsed_time_ms": 3000,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_l2vpn",
            "device": "juniper-mx-02.demo.com",
            "commands_executed": 28,
            "elapsed_time_ms": 7500,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED",
                "vpn_tunnel_up": True
            }
        },
        {
            "status": "success",
            "operation": "activate_protection",
            "device": "ciena-saos-07.demo.com",
            "commands_executed": 10,
            "elapsed_time_ms": 1800,
            "telemetry": {
                "pre_check": "PASSED",
                "protection_enabled": True,
                "switchover_test": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "provision_qos",
            "device": "cisco-ios-03.demo.com",
            "commands_executed": 16,
            "elapsed_time_ms": 3200,
            "telemetry": {
                "pre_check": "PASSED",
                "qos_policy_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "success",
            "operation": "sync_inventory",
            "device": "nokia-sr-02.demo.com",
            "commands_executed": 30,
            "elapsed_time_ms": 8000,
            "telemetry": {
                "devices_scanned": 15,
                "services_discovered": 42,
                "inventory_updated": True
            }
        },
        # Error cases - 15 variants
        {
            "status": "error",
            "operation": "provision_eline",
            "device": "ciena-saos-08.demo.com",
            "error": "Device timeout after 30s",
            "commands_executed": 5,
            "elapsed_time_ms": 30000
        },
        {
            "status": "error",
            "operation": "provision_elan",
            "device": "cisco-ios-04.demo.com",
            "error": "Port not available",
            "commands_executed": 3,
            "elapsed_time_ms": 1200,
            "telemetry": {
                "pre_check": "FAILED",
                "reason": "Port already in use"
            }
        },
        {
            "status": "error",
            "operation": "provision_evpl",
            "device": "juniper-mx-03.demo.com",
            "error": "Configuration rollback required",
            "commands_executed": 10,
            "elapsed_time_ms": 2500,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": False,
                "post_check": "FAILED",
                "rollback_executed": True
            }
        },
        {
            "status": "error",
            "operation": "deprovision_eline",
            "device": "nokia-sr-03.demo.com",
            "error": "Service not found on device",
            "commands_executed": 2,
            "elapsed_time_ms": 800
        },
        {
            "status": "error",
            "operation": "modify_bandwidth",
            "device": "ciena-saos-09.demo.com",
            "error": "Insufficient bandwidth available",
            "commands_executed": 4,
            "elapsed_time_ms": 1500,
            "telemetry": {
                "requested_bandwidth": "100G",
                "available_bandwidth": "50G"
            }
        },
        {
            "status": "error",
            "operation": "provision_eline",
            "device": "arista-eos-02.demo.com",
            "error": "Authentication failed",
            "commands_executed": 0,
            "elapsed_time_ms": 500
        },
        {
            "status": "error",
            "operation": "provision_l2vpn",
            "device": "juniper-mx-04.demo.com",
            "error": "VPN tunnel failed to establish",
            "commands_executed": 20,
            "elapsed_time_ms": 15000,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "tunnel_status": "DOWN"
            }
        },
        {
            "status": "error",
            "operation": "verify_service",
            "device": "cisco-ios-05.demo.com",
            "error": "Service verification failed",
            "commands_executed": 5,
            "elapsed_time_ms": 2000,
            "telemetry": {
                "service_status": "INACTIVE",
                "bandwidth_test": "FAILED",
                "connectivity_test": "FAILED"
            }
        },
        {
            "status": "error",
            "operation": "provision_elan",
            "device": "ciena-saos-10.demo.com",
            "error": "VLAN ID conflict",
            "commands_executed": 6,
            "elapsed_time_ms": 1800,
            "telemetry": {
                "pre_check": "FAILED",
                "conflicting_vlan": 100,
                "existing_service": "DEMO.CIRCUIT.999..MOCK"
            }
        },
        {
            "status": "error",
            "operation": "update_vlan",
            "device": "nokia-sr-04.demo.com",
            "error": "Invalid VLAN range",
            "commands_executed": 2,
            "elapsed_time_ms": 600,
            "telemetry": {
                "requested_vlan": 5000,
                "valid_range": "1-4094"
            }
        },
        {
            "status": "error",
            "operation": "restore_service",
            "device": "ciena-saos-11.demo.com",
            "error": "Backup configuration not found",
            "commands_executed": 1,
            "elapsed_time_ms": 400
        },
        {
            "status": "error",
            "operation": "activate_protection",
            "device": "cisco-ios-06.demo.com",
            "error": "Protection path unavailable",
            "commands_executed": 8,
            "elapsed_time_ms": 2200,
            "telemetry": {
                "primary_path": "UP",
                "protection_path": "DOWN"
            }
        },
        {
            "status": "error",
            "operation": "provision_qos",
            "device": "juniper-mx-05.demo.com",
            "error": "QoS policy validation failed",
            "commands_executed": 4,
            "elapsed_time_ms": 1000,
            "telemetry": {
                "policy_errors": ["Invalid queue depth", "Unsupported scheduling algorithm"]
            }
        },
        {
            "status": "error",
            "operation": "sync_inventory",
            "device": "arista-eos-03.demo.com",
            "error": "Device firmware incompatible",
            "commands_executed": 1,
            "elapsed_time_ms": 300,
            "telemetry": {
                "current_version": "4.20.1F",
                "required_version": "4.22.0F+"
            }
        },
        {
            "status": "error",
            "operation": "provision_eline",
            "device": "nokia-sr-05.demo.com",
            "error": "License limit exceeded",
            "commands_executed": 3,
            "elapsed_time_ms": 900,
            "telemetry": {
                "licensed_services": 1000,
                "active_services": 1000
            }
        },
    ]

    def execute_scriptplan(self, plan_name: str, params: Dict) -> Dict:
        """Execute MDSO ScriptPlan (mocked)"""
        return random.choice(self.RA_TELEMETRY_RESPONSES)

    def get_service_status(self, circuit_id: str) -> Dict:
        """Get service status from MDSO (mocked)"""
        return random.choice([
            {"status": "ACTIVE", "circuit_id": circuit_id, "uptime_hours": 720},
            {"status": "INACTIVE", "circuit_id": circuit_id, "reason": "Service not provisioned"},
            {"status": "DEGRADED", "circuit_id": circuit_id, "reason": "Protection path down"}
        ])


class MockTACACSClient:
    """Mock TACACS+ authentication client"""

    RESPONSES = [
        # Success cases - 10 variants
        {"status": "success", "authenticated": True, "privilege_level": 15},
        {"status": "success", "authenticated": True, "privilege_level": 7},
        {"status": "success", "authenticated": True, "privilege_level": 1},
        {"status": "success", "authenticated": True, "privilege_level": 15, "session_timeout": 3600},
        {"status": "success", "authenticated": True, "privilege_level": 10},
        {"status": "success", "authenticated": True, "privilege_level": 15, "command_logging": True},
        {"status": "success", "authenticated": True, "privilege_level": 5},
        {"status": "success", "authenticated": True, "privilege_level": 15, "accounting_enabled": True},
        {"status": "success", "authenticated": True, "privilege_level": 3},
        {"status": "success", "authenticated": True, "privilege_level": 15, "session_id": "tacacs-12345"},
        # Error cases - 15 variants
        {"status": "error", "authenticated": False, "error": "Invalid password"},
        {"status": "error", "authenticated": False, "error": "User not found"},
        {"status": "error", "authenticated": False, "error": "Account disabled"},
        {"status": "error", "authenticated": False, "error": "TACACS+ server timeout"},
        {"status": "error", "authenticated": False, "error": "Invalid privilege level requested"},
        {"status": "error", "authenticated": False, "error": "Maximum sessions exceeded"},
        {"status": "error", "authenticated": False, "error": "Password expired"},
        {"status": "error", "authenticated": False, "error": "IP address not authorized"},
        {"status": "error", "authenticated": False, "error": "Time-based access restriction"},
        {"status": "error", "authenticated": False, "error": "Device not in allowed list"},
        {"status": "error", "authenticated": False, "error": "TACACS+ server unreachable"},
        {"status": "error", "authenticated": False, "error": "Insufficient privilege level"},
        {"status": "error", "authenticated": False, "error": "Account locked after failed attempts"},
        {"status": "error", "authenticated": False, "error": "Invalid shared secret"},
        {"status": "error", "authenticated": False, "error": "Authorization denied for command"},
    ]

    def authenticate_device(self, device: str, username: str, password: str) -> Dict:
        """Authenticate device access (mocked)"""
        return random.choice(self.RESPONSES)

    def authorize_command(self, device: str, username: str, command: str) -> Dict:
        """Authorize command execution (mocked)"""
        return random.choice([
            {"status": "success", "authorized": True, "privilege_level": 15},
            {"status": "error", "authorized": False, "error": "Command not permitted"}
        ])


class MockSNMPClient:
    """Mock SNMP client for device polling"""

    RESPONSES = [
        # Router metrics - 10 variants
        {
            "device": "router-a.demo.com",
            "uptime": "45 days, 12:30:00",
            "cpu_usage": 35.2,
            "memory_usage": 62.5,
            "interfaces": [
                {"name": "GigabitEthernet0/0/0", "status": "up", "speed": "1000Mbps", "in_octets": 1234567890, "out_octets": 9876543210},
                {"name": "GigabitEthernet0/0/1", "status": "down", "speed": "1000Mbps", "in_octets": 0, "out_octets": 0}
            ]
        },
        {
            "device": "router-b.demo.com",
            "uptime": "120 days, 05:15:22",
            "cpu_usage": 12.8,
            "memory_usage": 45.1,
            "interfaces": [
                {"name": "TenGigabitEthernet0/0/0", "status": "up", "speed": "10000Mbps", "in_octets": 12345678901234, "out_octets": 98765432109876},
                {"name": "TenGigabitEthernet0/0/1", "status": "up", "speed": "10000Mbps", "in_octets": 11111111111111, "out_octets": 22222222222222}
            ]
        },
        {
            "device": "router-c.demo.com",
            "uptime": "30 days, 08:45:10",
            "cpu_usage": 55.7,
            "memory_usage": 78.3,
            "interfaces": [
                {"name": "HundredGigE0/0/0", "status": "up", "speed": "100000Mbps", "in_octets": 99999999999999, "out_octets": 88888888888888}
            ]
        },
        {
            "device": "router-d.demo.com",
            "uptime": "180 days, 22:10:05",
            "cpu_usage": 8.4,
            "memory_usage": 32.1,
            "interfaces": [
                {"name": "GigabitEthernet0/0/0", "status": "up", "speed": "1000Mbps", "in_octets": 5555555555, "out_octets": 6666666666},
                {"name": "GigabitEthernet0/0/1", "status": "up", "speed": "1000Mbps", "in_octets": 7777777777, "out_octets": 8888888888},
                {"name": "GigabitEthernet0/0/2", "status": "down", "speed": "1000Mbps", "in_octets": 0, "out_octets": 0}
            ]
        },
        {
            "device": "router-e.demo.com",
            "uptime": "60 days, 14:20:30",
            "cpu_usage": 42.1,
            "memory_usage": 68.9,
            "interfaces": [
                {"name": "FortyGigabitEthernet0/0/0", "status": "up", "speed": "40000Mbps", "in_octets": 44444444444444, "out_octets": 55555555555555}
            ]
        },
        # Switch metrics - 10 variants
        {
            "device": "switch-a.demo.com",
            "uptime": "90 days, 03:45:12",
            "cpu_usage": 18.5,
            "memory_usage": 52.3,
            "interfaces": [
                {"name": "Port1", "status": "up", "speed": "10000Mbps", "in_octets": 1111111111, "out_octets": 2222222222},
                {"name": "Port2", "status": "up", "speed": "10000Mbps", "in_octets": 3333333333, "out_octets": 4444444444},
                {"name": "Port3", "status": "down", "speed": "10000Mbps", "in_octets": 0, "out_octets": 0}
            ]
        },
        {
            "device": "switch-b.demo.com",
            "uptime": "200 days, 18:30:45",
            "cpu_usage": 6.2,
            "memory_usage": 28.7,
            "interfaces": [
                {"name": "Ethernet1", "status": "up", "speed": "1000Mbps", "in_octets": 123456789, "out_octets": 987654321},
                {"name": "Ethernet2", "status": "up", "speed": "1000Mbps", "in_octets": 246802468, "out_octets": 135791357}
            ]
        },
        {
            "device": "switch-c.demo.com",
            "uptime": "15 days, 06:15:30",
            "cpu_usage": 72.4,
            "memory_usage": 85.6,
            "interfaces": [
                {"name": "Port1/1", "status": "up", "speed": "25000Mbps", "in_octets": 99887766554433, "out_octets": 11223344556677},
                {"name": "Port1/2", "status": "up", "speed": "25000Mbps", "in_octets": 22446688001122, "out_octets": 33557799221144}
            ]
        },
        {
            "device": "switch-d.demo.com",
            "uptime": "150 days, 12:00:00",
            "cpu_usage": 22.8,
            "memory_usage": 48.2,
            "interfaces": [
                {"name": "Gi1/0/1", "status": "up", "speed": "1000Mbps", "in_octets": 1000000000, "out_octets": 2000000000},
                {"name": "Gi1/0/2", "status": "up", "speed": "1000Mbps", "in_octets": 3000000000, "out_octets": 4000000000},
                {"name": "Gi1/0/3", "status": "up", "speed": "1000Mbps", "in_octets": 5000000000, "out_octets": 6000000000},
                {"name": "Gi1/0/4", "status": "down", "speed": "1000Mbps", "in_octets": 0, "out_octets": 0}
            ]
        },
        {
            "device": "switch-e.demo.com",
            "uptime": "75 days, 09:30:15",
            "cpu_usage": 38.7,
            "memory_usage": 61.4,
            "interfaces": [
                {"name": "Te0/1", "status": "up", "speed": "10000Mbps", "in_octets": 77777777777777, "out_octets": 88888888888888},
                {"name": "Te0/2", "status": "up", "speed": "10000Mbps", "in_octets": 99999999999999, "out_octets": 11111111111111}
            ]
        },
        # Error cases - 10 variants
        {
            "device": "router-error-1.demo.com",
            "error": "SNMP timeout",
            "timeout_ms": 5000
        },
        {
            "device": "router-error-2.demo.com",
            "error": "SNMP community string mismatch"
        },
        {
            "device": "switch-error-1.demo.com",
            "error": "Device unreachable",
            "last_seen": (datetime.utcnow() - timedelta(hours=6)).isoformat()
        },
        {
            "device": "switch-error-2.demo.com",
            "error": "SNMP version not supported",
            "device_version": "SNMPv1",
            "required_version": "SNMPv2c+"
        },
        {
            "device": "router-error-3.demo.com",
            "error": "OID not found",
            "requested_oid": "1.3.6.1.2.1.2.2.1.8"
        },
        {
            "device": "switch-error-3.demo.com",
            "error": "SNMP agent not responding"
        },
        {
            "device": "router-error-4.demo.com",
            "error": "Authentication failure",
            "auth_protocol": "MD5"
        },
        {
            "device": "switch-error-4.demo.com",
            "error": "Port limit exceeded in response",
            "max_ports": 100
        },
        {
            "device": "router-error-5.demo.com",
            "error": "Device rebooting",
            "uptime": "0 days, 00:02:15"
        },
        {
            "device": "switch-error-5.demo.com",
            "error": "SNMP access denied by ACL",
            "source_ip": "192.168.1.100"
        },
    ]

    def poll_device(self, device: str) -> Dict:
        """Poll device via SNMP (mocked)"""
        return random.choice(self.RESPONSES)

    def get_interface_stats(self, device: str, interface: str) -> Dict:
        """Get specific interface statistics (mocked)"""
        return random.choice([
            {
                "interface": interface,
                "status": "up",
                "speed": "10000Mbps",
                "in_octets": 12345678901234,
                "out_octets": 98765432109876,
                "in_errors": 0,
                "out_errors": 0
            },
            {
                "interface": interface,
                "error": "Interface not found"
            }
        ])


# Factory function to get mock clients
def get_mock_client(client_type: str):
    """Get mock client instance"""
    clients = {
        "ip_control": MockIPControlClient,
        "granite": MockGraniteClient,
        "kong": MockKongClient,
        "mdso": MockMDSOClient,
        "tacacs": MockTACACSClient,
        "snmp": MockSNMPClient
    }

    if client_type not in clients:
        raise ValueError(f"Unknown client type: {client_type}. Valid types: {list(clients.keys())}")

    return clients[client_type]()
