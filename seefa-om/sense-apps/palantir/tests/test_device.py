import json
import logging
import socket
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from pytest import fail

from palantir_app.bll import device
from palantir_app.bll.device import Device
from palantir_app.dll import ipc

logger = logging.getLogger(__name__)


@contextmanager
def not_raises(exception):
    try:
        yield
    except exception:
        raise fail("DID RAISE {0}".format(exception))


class MockResponse:
    def __init__(self, json_data, status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(self.json_data)

    def json(self):
        return self.json_data


def get_prerequisite_validated():
    # THIS IS AN ATTR FROM DEVICE CLASS THAT WE NEED TO SET FOR TESTS
    return {
        "ping": False,  # no IPs associated with device ping
        "hostname": False,  # hostname mismatch
        "snmp": False,  # snmp not enabled, so we can't validate hostname
    }


def get_validated():
    # THIS IS AN ATTR FROM DEVICE CLASS THAT WE NEED TO SET FOR TESTS
    return {
        "tacacs": False  # unable to log in using TACACS creds
    }


def get_base_msg():
    return {
        "hostname": {},  # granite TID comparison against device TID via SNMP
        "ip": {},  # designated usable IP determined by pingability and hostname match
        "fqdn": {},  # DNS IP from FQDN matches usable IP
        "tacacs": {},  # login via TACACS creds
        "ise": {},  # onboard device to ISE
        "granite": {},  # track database reconciliation efforts
        "reachable": "",  # preferred method of accessing device - FQDN if resolves else usable IP
    }


@pytest.mark.unittest
def test_init_export_child_block(monkeypatch):
    def mocked_ipc_get(*args, **kwargs):
        return MockResponse(
            json_data=[
                {
                    "childBlock": {
                        "SWIPname": "",
                        "blockAddr": "10.4.242.0",
                        "blockName": "10.4.242.0/24",
                        "blockSize": "24",
                        "blockStatus": "Deployed",
                        "blockType": "MGMT-Private",
                        "container": "/Commercial/WestRegion/SWM/SW-CEN/SNAXTXFP1CW",
                        "createDate": "2013-07-30 15:03:28",
                        "createReverseDomains": "true",
                        "description": "",
                        "discoveryAgent": "InheritFromContainer",
                        "domainType": "Default",
                        "excludeFromDiscovery": "false",
                        "interfaceAddress": ["10.4.242.1"],
                        "interfaceName": "irb.99",
                        "ipv6": False,
                        "lastUpdateDate": "2020-05-27 09:59:06",
                        "nonBroadcast": False,
                        "primarySubnet": False,
                    },
                    "subnetPolicy": {
                        "DHCPOptionsSet": "SW",
                        "DHCPPolicySet": "TWC Default DHCP Policy",
                        "DNSServers": ["austx-ipc-agent-01.chtrse.com"],
                        "cascadePrimaryDhcpServer": False,
                        "defaultGateway": "10.4.242.1",
                        "forwardDomainTypes": ["Default", "Default"],
                        "forwardDomains": ["cml.chtrse.com.", "sw.twcbiz.com."],
                        "primaryDHCPServer": "austx-ipc-agent-01.chtrse.com",
                        "primaryWINSServer": "",
                        "networkLink": "SNAXTXFP1CW-irb.99-v4",
                    },
                }
            ],
            status_code=200,
        )

    monkeypatch.setattr(ipc.requests, "get", mocked_ipc_get)

    ip = "FAKE_IP"
    response = device._init_export_child_block(ip)

    assert response == "24"


@pytest.mark.unittest
def test_device_determine_tacacs(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        return "Success"

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "FAKE_usable_ip"
        d.msg = get_base_msg()
        d.validated = get_validated()
        d.determine_tacacs()
        assert d.msg["tacacs"] == {"status": "validated", "message": "logged in successfully"}


@pytest.mark.unittest
def test_device_determine_tacacs_exception(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        raise Exception("FAKE EXCEPTION")

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "FAKE_usable_ip"
        d.tid = "FAKE_TID"
        d.usable_ip = "FAKE_IP"
        d.fqdn = "FAKE_FQDN"
        d.vendor = "VENDOR"
        d.model = "MODEL"
        d.eq_type = "DEVICE ROLE"
        d.msg = get_base_msg()
        d.is_err_state = False
        d.determine_tacacs()
        assert d.msg["tacacs"] == {
            "status": "failed",
            "message": "unhandled error",
            "data": {
                "ip": "FAKE_IP",
                "vendor": "VENDOR",
                "model": "MODEL",
                "role": "DEVICE ROLE",
                "response": "FAKE EXCEPTION",
            },
        }


@pytest.mark.unittest
def test_device_determine_tacacs_auth_failed_wrong_vendor(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        return "Auth not successful remediation required"

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "IP"
        d.is_cpe = True
        d.vendor = "FAKE_VENDOR"
        d.model = "MODEL"
        d.eq_type = "DEVICE ROLE"
        d.msg = get_base_msg()
        d.validated = get_validated()
        d.determine_tacacs()
        assert d.msg["tacacs"] == {
            "status": "failed",
            "message": "authentication error",
            "data": {
                "ip": "IP",
                "vendor": "FAKE_VENDOR",
                "model": "MODEL",
                "role": "DEVICE ROLE",
                "response": "Auth not successful remediation required",
            },
        }
        assert d.validated["tacacs"] is False


@pytest.mark.unittest
def test_device_determine_tacacs_auth_unsupported_cpe_remediation_req(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        return "Auth not successful remediation required"

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "IP"
        d.is_cpe = True
        d.vendor = "ADVA"
        d.model = "FSP 150-GE114PRO-C"
        d.eq_type = "CPE"
        d.tacacs_remediation_required = False  # this initializes as False and updates to True if required
        d.msg = get_base_msg()
        d.validated = get_validated()
        d.determine_tacacs()
        assert d.msg["tacacs"] == {
            "status": "failed",
            "message": "authentication error",
            "data": {
                "ip": "IP",
                "vendor": "ADVA",
                "model": "FSP 150-GE114PRO-C",
                "role": "CPE",
                "response": "Auth not successful remediation required",
            },
        }
        assert d.validated["tacacs"] is False
        # although remediation is required, below should be False to prevent unsupported automation attempt
        assert d.tacacs_remediation_required is False


@pytest.mark.unittest
def test_device_determine_tacacs_auth_unsupported_vendor_remediation_req(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        return "Auth not successful remediation required"

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "FAKE_usable_ip"
        d.tid = "TID"
        d.vendor = "VENDOR"
        d.model = "MODEL"
        d.eq_type = "CPE"
        d.is_cpe = True
        d.msg = get_base_msg()
        d.validated = get_validated()
        d.tacacs_remediation_required = False
        d.determine_tacacs()
        assert d.msg["tacacs"] == {
            "status": "failed",
            "message": "authentication error",
            "data": {
                "ip": "FAKE_usable_ip",
                "vendor": "VENDOR",
                "model": "MODEL",
                "role": "CPE",
                "response": "Auth not successful remediation required",
            },
        }
        assert d.validated["tacacs"] is False
        # remediation required is False if vendor is not in supported vendors
        assert d.tacacs_remediation_required is False


@pytest.mark.unittest
def test_device_tacacs_remediation_success(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        return "Success"

    def mocked_remediate_tacacs_connection(*args, **kwargs):
        return {"Success": "MSG"}

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    monkeypatch.setattr(device, "remediate_tacacs_connection", mocked_remediate_tacacs_connection)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "FAKE_usable_ip"
        d.tid = "FAKE_TID"
        d.is_cpe = True
        d.vendor = "ADVA"
        d.msg = get_base_msg()
        d.validated = get_validated()
        d.tacacs_remediation_required = False
        d.remediate_tacacs()
        assert d.msg["tacacs"] == {"status": "validated", "message": "tacacs config applied"}
        assert d.tacacs_remediation_required is False


@pytest.mark.unittest
def test_device_tacacs_remediation_failed(monkeypatch):
    def mocked_get_tacacs_status(*args, **kwargs):
        return "Failed"

    def mocked_remediate_tacacs_connection(*args, **kwargs):
        return {"Failed": "MSG"}

    monkeypatch.setattr(device, "get_tacacs_status", mocked_get_tacacs_status)
    monkeypatch.setattr(device, "remediate_tacacs_connection", mocked_remediate_tacacs_connection)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "IP"
        d.tid = "FAKE_TID"
        d.is_cpe = True
        d.vendor = "RAD"
        d.model = "220"
        d.eq_type = "CPE"
        d.msg = get_base_msg()
        d.validated = get_validated()
        d.tacacs_remediation_required = False
        d.remediate_tacacs()
        assert d.msg["tacacs"] == {
            "status": "failed",
            "message": "unable to update config",
            "data": {"ip": "IP", "vendor": "RAD", "model": "220", "role": "CPE", "response": {"Failed": "MSG"}},
        }
        assert d.validated["tacacs"] is False
        assert d.tacacs_remediation_required is True


@pytest.mark.unittest
def test_device_class_init_fqdn_resolves(monkeypatch):
    def mocked_get_ipc_ip(*args, **kwargs):
        return "FAKE_IPC_IP"

    def mocked_get_dns_ip(*args, **kwargs):
        return "FAKE_DNS_IP"

    def mocked_get_pingable_ips(*args, **kwargs):
        return {"FAKE_DNS_IP": {"validated": True, "source": "ipc"}}

    def mocked_usable_ip(*args, **kwargs):
        return "FAKE_DNS_IP"

    def mocked_is_granite_remediation_required(*args, **kwargs):
        return False

    monkeypatch.setattr(device, "get_ip_from_tid", mocked_get_ipc_ip)
    monkeypatch.setattr(Device, "_get_dns_ip", mocked_get_dns_ip)
    monkeypatch.setattr(Device, "_get_pingable_ips", mocked_get_pingable_ips)
    monkeypatch.setattr(Device, "_get_validated_hostname_ip", mocked_usable_ip)
    monkeypatch.setattr(Device, "_is_granite_remediation_required", mocked_is_granite_remediation_required)

    fake_device_attributes = {
        "ip": "FAKE_IP",
        "tid": "FAKE_TID",
        "fqdn": "FAKE_FQDN",
        "port": "FAKE_PORT",
        "vlan": "FAKE_VLAN",
        "vendor": "FAKE_VENDOR",
        "channel": "FAKE_IDK",
        "category": "FAKE_EQ_TYPE",
        "leg": "FAKE_NUMBER",
    }

    d = Device(fake_device_attributes, "FAKE_CID")
    assert d.cid == "FAKE_CID"
    assert d.ip == "FAKE_IP"
    assert d.tid == "FAKE_TID"
    assert d.fqdn == "FAKE_FQDN"
    assert d.vendor == "FAKE_VENDOR"
    assert d.is_cpe is False
    assert d.model is None
    assert d.tacacs_remediation_required is False
    assert d.ise_success is False
    assert d.granite_remediation_required is False
    assert d.port == "FAKE_PORT"
    assert d.vlan == "FAKE_VLAN"
    assert d.chan_name == "FAKE_IDK"
    assert d.eq_type == "FAKE_EQ_TYPE"
    assert d.leg_name == "FAKE_NUMBER"
    assert d.ips_by_source == {"ipc": "FAKE_IPC_IP", "dns": "FAKE_DNS_IP", "granite": "FAKE_IP"}
    assert d.prerequisite_validated == {"ping": False, "hostname": False, "snmp": False}
    assert d.validated == {"tacacs": False}
    assert d.msg == {
        "hostname": {},
        "ip": {},
        "fqdn": {
            "status": "validated",
            "message": "fqdn resolves to usable ip",
        },  # every other msg update is bypassed in this test
        "tacacs": {},
        "ise": {},
        "granite": {},
        "reachable": "FAKE_FQDN",
    }
    assert d.usable_ip == "FAKE_DNS_IP"
    assert d.granite_remediation_required is False
    # not testing the prerequisite err state here because the updates are bypassed in this test


@pytest.mark.unittest
def test_device_class_init_fqdn_not_resolvable(monkeypatch):
    def mocked_get_ipc_ip(*args, **kwargs):
        return "FAKE_IPC_IP"

    def mocked_get_dns_ip(*args, **kwargs):
        return "FAKE_DNS_IP"

    def mocked_get_pingable_ips(*args, **kwargs):
        return {"FAKE_IPC_IP": {"validated": True, "source": "ipc"}}

    def mocked_usable_ip(*args, **kwargs):
        return "FAKE_IPC_IP"

    def mocked_is_granite_remediation_required(*args, **kwargs):
        return False

    monkeypatch.setattr(device, "get_ip_from_tid", mocked_get_ipc_ip)
    monkeypatch.setattr(Device, "_get_dns_ip", mocked_get_dns_ip)
    monkeypatch.setattr(Device, "_get_pingable_ips", mocked_get_pingable_ips)
    monkeypatch.setattr(Device, "_get_validated_hostname_ip", mocked_usable_ip)
    monkeypatch.setattr(Device, "_is_granite_remediation_required", mocked_is_granite_remediation_required)

    fake_device_attributes = {
        "ip": "FAKE_IP",
        "tid": "FAKE_TID",
        "fqdn": "FAKE_FQDN",
        "port": "FAKE_PORT",
        "vlan": "FAKE_VLAN",
        "vendor": "FAKE_VENDOR",
        "channel": "FAKE_IDK",
        "category": "FAKE_EQ_TYPE",
        "leg": "FAKE_NUMBER",
    }

    d = Device(fake_device_attributes, "FAKE_CID")
    assert d.cid == "FAKE_CID"
    assert d.ip == "FAKE_IP"
    assert d.tid == "FAKE_TID"
    assert d.fqdn == "FAKE_FQDN"
    assert d.vendor == "FAKE_VENDOR"
    assert d.is_cpe is False
    assert d.model is None
    assert d.tacacs_remediation_required is False
    assert d.ise_success is False
    assert d.port == "FAKE_PORT"
    assert d.vlan == "FAKE_VLAN"
    assert d.chan_name == "FAKE_IDK"
    assert d.eq_type == "FAKE_EQ_TYPE"
    assert d.leg_name == "FAKE_NUMBER"
    assert d.ips_by_source == {"ipc": "FAKE_IPC_IP", "dns": "FAKE_DNS_IP", "granite": "FAKE_IP"}
    assert d.prerequisite_validated == {"ping": False, "hostname": False, "snmp": False}
    assert d.validated == {"tacacs": False}
    assert d.msg == {
        "hostname": {},
        "ip": {},
        "fqdn": {
            "status": "failed",
            "message": "not resolvable",
            "data": {"fqdn": "FAKE_FQDN", "dns": "FAKE_DNS_IP", "usable": "FAKE_IPC_IP"},
        },  # every other msg update is bypassed in this test
        "tacacs": {},
        "ise": {},
        "granite": {},
        "reachable": "FAKE_IPC_IP",
    }
    assert d.usable_ip == "FAKE_IPC_IP"
    assert d.granite_remediation_required is False
    # not testing the prerequisite err state here because the updates are bypassed in this test


@pytest.mark.unittest
def test_device_is_granite_remediation_required_true():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "IP"
        d.ip = "FAKE_IP"
        d.is_cpe = True
        d.ips_by_source = {"ipc": "IP", "dns": "DNS", "granite": "FAKE_IP"}
        d.msg = get_base_msg()
        assert d._is_granite_remediation_required() is True
        assert d.msg["granite"] == {
            "status": "reconciliation required",
            "message": "database disagreement",
            "data": {"found": {"ipc": "IP", "dns": "DNS", "granite": "FAKE_IP"}, "usable": "IP"},
        }


@pytest.mark.unittest
def test_device_is_granite_remediation_required_false():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.usable_ip = "FAKE_usable_ip"
        d.ip = "FAKE_IP"
        d.is_cpe = False
        d.msg = get_base_msg()
        assert d._is_granite_remediation_required() is False
        assert d.msg.get("granite") is None


@pytest.mark.unittest
def test_device_is_fqdn_usable_success():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.msg = get_base_msg()
        d.ips_by_source = {"dns": "FAKE_DNS_IP"}
        d.usable_ip = "FAKE_DNS_IP"
        d._validate_fqdn_resolves()
        assert d.msg["fqdn"] == {"status": "validated", "message": "fqdn resolves to usable ip"}


@pytest.mark.unittest
def test_device_is_fqdn_usable_failed():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.fqdn = "FQDN"
        d.msg = get_base_msg()
        d.ips_by_source = {"dns": "FAKE_DNS_IP"}
        d.usable_ip = "FAKE_OTHER_IP"
        d._validate_fqdn_resolves()
        assert d.msg["fqdn"] == {
            "status": "failed",
            "message": "not resolvable",
            "data": {"fqdn": "FQDN", "dns": "FAKE_DNS_IP", "usable": "FAKE_OTHER_IP"},
        }


@pytest.mark.unittest
def test_get_validated_hostname_ip_success(monkeypatch):
    def mocked_snmp_tid_validation(*args, **kwargs):
        return True, "FAKE_TID"

    def mocked_is_ip_pinging(*args, **kwargs):
        return True

    def mocked_pingable_ips():
        return {"FAKE_IPC_IP": {"source": "ipc", "validated": True}}

    pingable_ips = mocked_pingable_ips()
    monkeypatch.setattr(Device, "_is_validated_hostname", mocked_snmp_tid_validation)
    monkeypatch.setattr(Device, "_is_ip_pinging", mocked_is_ip_pinging)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.cid = "FAKE_CID"
        d.msg = get_base_msg()
        d.tid = "FAKE_TID"
        d.ip = "FAKE_IP"
        d.fqdn = "FQDN"
        d.ips_by_source = {"ipc": "FAKE_IPC_IP", "dns": "FAKE_DNS_IP", "granite": "FAKE_IP"}
        d.prerequisite_validated = get_prerequisite_validated()
        d.validated = get_validated()
        d._get_validated_hostname_ip(pingable_ips)
        assert d.msg["hostname"] == {"status": "validated", "message": "device name matches design"}
        assert d.msg["ip"] == {"status": "validated", "message": "usable: FAKE_IPC_IP source: ipc"}
        assert d.prerequisite_validated["hostname"] is True


@pytest.mark.unittest
def test_get_pingable_ips_failed(monkeypatch):
    def mocked_snmp_tid_validation(*args, **kwargs):
        return True, "FAKE_TID"

    def mocked_is_ip_pinging(*args, **kwargs):
        return False

    monkeypatch.setattr(Device, "_is_validated_hostname", mocked_snmp_tid_validation)
    monkeypatch.setattr(Device, "_is_ip_pinging", mocked_is_ip_pinging)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.cid = "FAKE_CID"
        d.msg = get_base_msg()
        d.tid = "FAKE_TID"
        d.ips_by_source = {"ipc": "FAKE_IPC_IP", "dns": "FAKE_DNS_IP", "granite": "FAKE_IP"}
        d.ip = "FAKE_IP"
        d.prerequisite_validated = get_prerequisite_validated()
        d.validated = get_validated()
        pingable = d._get_pingable_ips()
        assert d.prerequisite_validated["ping"] is False
        assert pingable is None


@pytest.mark.unittest
def test_device_get_vendor_and_model_by_ip(monkeypatch):
    def mocked_beorn_get(*args, **kwargs):
        data = {"vendor": "FAKE_VENDOR", "model": "FAKE_MODEL"}
        return MockResponse(json_data=data).json()

    monkeypatch.setattr(device, "beorn_get", mocked_beorn_get)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._get_vendor_and_model_by_ip("FAKE_TID", "FAKE_IP") == {"vendor": "FAKE_VENDOR", "model": "FAKE_MODEL"}


@pytest.mark.unittest
def test_device_get_vendor_and_model_by_ip_granite_fallback(monkeypatch):
    def mocked_beorn_get(*args, **kwargs):
        data = {"error": "FAKE_ERROR"}
        return MockResponse(json_data=data).json()

    def mocked_get_device_vendor_and_model(*args, **kwargs):
        return {"vendor": "FAKE_VENDOR", "model": "FAKE_MODEL"}

    monkeypatch.setattr(device, "beorn_get", mocked_beorn_get)
    monkeypatch.setattr(device, "get_device_vendor_model_site_category", mocked_get_device_vendor_and_model)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._get_vendor_and_model_by_ip("FAKE_TID", "FAKE_IP") == {"vendor": "FAKE_VENDOR", "model": "FAKE_MODEL"}


@pytest.mark.unittest
def test_device_get_device_hostname_by_snmp(monkeypatch):
    def mocked_beorn_get(*args, **kwargs):
        data = {"name": "FAKE_HOSTNAME"}
        return MockResponse(json_data=data).json()

    monkeypatch.setattr(device, "beorn_get", mocked_beorn_get)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.msg = get_base_msg()
        d.prerequisite_validated = get_prerequisite_validated()
        d.validated = get_validated()
        assert d._get_device_hostname_by_snmp("FAKE_IP", "granite") == "FAKE_HOSTNAME"


@pytest.mark.unittest
def test_device_snmp_tid_validation(monkeypatch):
    def mocked_get_device_hostname_by_snmp(*args, **kwargs):
        return "FAKE_TID"

    monkeypatch.setattr(Device, "_get_device_hostname_by_snmp", mocked_get_device_hostname_by_snmp)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.tid = "FAKE_TID"
        d.ip = "FAKE_IP"
        d.fqdn = "FAKE_HOSTNAME"
        d.validated = get_validated()
        d.msg = get_base_msg()
        validated_hostname = d._is_validated_hostname("FAKE_IP", "granite")
        assert validated_hostname[0] is True
        assert validated_hostname[1] == "FAKE_TID"


@pytest.mark.unittest
def test_device_is_ip_valid():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._is_ip_valid("1.1.1.1") is True


@pytest.mark.unittest
def test_device_is_ip_valid_false():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._is_ip_valid("NOT A IP") is False


@pytest.mark.unittest
def test_device_is_ip_pinging(monkeypatch):
    def mocked_is_ip_valid(*args, **kwargs):
        return True

    def mocked_subprocess_call(*args, **kwargs):
        return 0

    monkeypatch.setattr(Device, "_is_ip_valid", mocked_is_ip_valid)
    monkeypatch.setattr(device.subprocess, "call", mocked_subprocess_call)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._is_ip_pinging("FAKE_IP") is True


@pytest.mark.unittest
def test_device_is_ip_pinging_false(monkeypatch):
    def mocked_is_ip_valid(*args, **kwargs):
        return True

    def mocked_subprocess_call(*args, **kwargs):
        return 1

    monkeypatch.setattr(Device, "_is_ip_valid", mocked_is_ip_valid)
    monkeypatch.setattr(device.subprocess, "call", mocked_subprocess_call)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._is_ip_pinging("FAKE_IP") is False


@pytest.mark.unittest
def test_device_get_dns_ip(monkeypatch):
    def mocked_socket_gethostbyname(*args, **kwargs):
        return "FAKE_IP"

    monkeypatch.setattr(device.socket, "gethostbyname", mocked_socket_gethostbyname)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        assert d._get_dns_ip("FAKE_HOSTNAME") == "FAKE_IP"


@pytest.mark.unittest
def test_device_get_dns_ip_exception(monkeypatch):
    def mocked_socket_gethostbyname(*args, **kwargs):
        raise socket.gaierror

    monkeypatch.setattr(device.socket, "gethostbyname", mocked_socket_gethostbyname)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.fqdn = "FAKE_HOSTNAME"
        assert d._get_dns_ip("FAKE_HOSTNAME") is None


@pytest.mark.unittest
def test_device_update_granite_ip(monkeypatch, caplog):
    def mocked_init_export_child_block(*args, **kwargs):
        return "/27"

    def mocked_update_granite_shelf(*args, **kwargs):
        return True

    monkeypatch.setattr(device, "_init_export_child_block", mocked_init_export_child_block)
    monkeypatch.setattr(device, "update_granite_shelf", mocked_update_granite_shelf)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.tid = "FAKE_TID"
        d.cid = "FAKE_CID"
        d.ip = "FAKE_IP"
        d.usable_ip = "FAKE_IP"
        d.msg = get_base_msg()
        d.update_granite_ip()
    assert "GRANITE IP UPDATE - Updating Granite Shelf..." in caplog.text
    assert "GRANITE IP UPDATE - Updated Successfully." in caplog.text
    assert d.msg["granite"] == {"status": "validated", "message": "updated design ip to usable ip"}


@pytest.mark.unittest
def test_device_update_granite_ip_failed(monkeypatch, caplog):
    def mocked_init_export_child_block(*args, **kwargs):
        return "/27"

    def mocked_update_granite_shelf(*args, **kwargs):
        return False

    monkeypatch.setattr(device, "_init_export_child_block", mocked_init_export_child_block)
    monkeypatch.setattr(device, "update_granite_shelf", mocked_update_granite_shelf)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.tid = "FAKE_TID"
        d.cid = "FAKE_CID"
        d.ip = "FAKE_IP"
        d.usable_ip = "FAKE_IP2"
        d.ips_by_source = {"ipc": "FAKE_IP2", "dns": "DNS_IP", "granite": "FAKE_IP"}
        d.msg = get_base_msg()
        d.update_granite_ip()
    assert "GRANITE IP UPDATE - Updating Granite Shelf..." in caplog.text
    assert "GRANITE IP UPDATE - Failed" in caplog.text
    assert d.msg["granite"] == {
        "status": "failed",
        "message": "unable to reconcile databases",
        "data": {"granite": "FAKE_IP", "usable": "FAKE_IP2"},
    }


@pytest.mark.unittest
def test_device_repr():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.tid = "FAKE_TID"
        d.fqdn = "FAKE_FQDN"
        d.ip = "FAKE_IP"
        assert d.__repr__() == "Device(TID:FAKE_TID, GRANITE_IP:FAKE_IP, GRANITE_FQDN:FAKE_FQDN)"


@pytest.mark.unittest
def test_device_str():
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "FAKE_CID")
        d.tid = "FAKE_TID"
        d.fqdn = "FAKE_FQDN"
        d.ip = "FAKE_IP"
        assert d.__str__() == "Device(TID:FAKE_TID, GRANITE_IP:FAKE_IP, GRANITE_FQDN:FAKE_FQDN)"


def mock_get_ise_record_by_id_cluster_specified(*args, **kwargs):
    return [
        {
            "id": "ID",
            "name": "DNTNTXKI1ZW",
            "description": "DNTNTXKI1ZW",
            "authenticationSettings": {
                "enableKeyWrap": False,
                "dtlsRequired": False,
                "keyInputFormat": "ASCII",
                "enableMultiSecret": "false",
            },
            "tacacsSettings": {
                "sharedSecret": "SECRETS",
                "connectModeOptions": "OFF",
                "previousSharedSecret": "",
                "previousSharedSecretExpiry": 99,
            },
            "profileName": "Cisco",
            "coaPort": 0,
            "link": {
                "rel": "self",
                "href": "https://iseisebaby/ers/config/networkdevice/id",
                "type": "application/json",
            },
            "NetworkDeviceIPList": [{"ipaddress": "1.1.1.1", "mask": 32}],
            "NetworkDeviceGroupList": [
                "Access#TWC#Edge",
                "Device Type#All Device Types#RAD",
                "Location#All Locations#Southwest",
                "IPSEC#Is IPSEC Device",
                "Legacy-Deployment#Legacy-Deployment",
                "Network Test device group#Network Test device group",
                "DukeEnergy#DukeEnergy",
            ],
        }
    ]


def mock_id_lookup_cluster(*args, **kwargs):
    return (
        {"west_id": [], "east_id": [], "south_id": ["ID"]},
        {
            "west_result": [],
            "east_result": [],
            "south_result": [
                {
                    "id": "ID",
                    "name": "DNTNTXKI1ZW",
                    "description": "DNTNTXKI1ZW",
                    "link": {
                        "rel": "self",
                        "href": "https://iseisebaby/ers/config/networkdevice/id",
                        "type": "application/json",
                    },
                }
            ],
            "region": "south",
        },
    )


def mock_id_lookup_cluster_no_results(*args, **kwargs):
    return (
        {"west_id": [], "east_id": [], "south_id": [""]},
        {"west_result": [], "east_result": [], "south_result": [], "region": ""},
    )


@pytest.mark.unittest
def test_process_ise_secret_secrets_match(monkeypatch):
    monkeypatch.setattr(device, "id_lookup_cluster", mock_id_lookup_cluster)
    monkeypatch.setattr(device, "get_ise_record_by_id_cluster_specified", mock_get_ise_record_by_id_cluster_specified)
    monkeypatch.setattr(device, "determine_ise_secret", lambda x: "SECRETS")
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.vendor = "ADVA"
        d.usable_ip = "IP"
        d.tid = "DNTNTXKI1ZW"
        d.ise_success = False
        d.tacacs_remediation_required = False
        d.msg = get_base_msg()
        d._process_ise_secret()
        assert d.msg["ise"] == {"status": "validated", "message": "secret validated on existing entry"}
        assert d.ise_success is True
        assert d.tacacs_remediation_required is False


@pytest.mark.unittest
def test_process_ise_secret_update_required_success(monkeypatch):
    monkeypatch.setattr(device, "id_lookup_cluster", mock_id_lookup_cluster)
    monkeypatch.setattr(device, "get_ise_record_by_id_cluster_specified", mock_get_ise_record_by_id_cluster_specified)
    monkeypatch.setattr(device, "determine_ise_secret", lambda x: "SECRETS!!!")
    monkeypatch.setattr(device, "update_shared_secret", lambda w, x, y, z: True)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.vendor = "ADVA"
        d.usable_ip = "IP"
        d.tid = "DNTNTXKI1ZW"
        d.ise_success = False
        d.tacacs_remediation_required = False
        d.msg = get_base_msg()
        d._process_ise_secret()
        assert d.msg["ise"] == {"status": "validated", "message": "secret updated on existing entry"}
        assert d.ise_success is True
        assert d.tacacs_remediation_required is False


@pytest.mark.unittest
def test_process_ise_secret_update_required_fail(monkeypatch):
    monkeypatch.setattr(device, "id_lookup_cluster", mock_id_lookup_cluster)
    monkeypatch.setattr(device, "get_ise_record_by_id_cluster_specified", mock_get_ise_record_by_id_cluster_specified)
    monkeypatch.setattr(device, "determine_ise_secret", lambda x: "SECRETS!!!")
    monkeypatch.setattr(device, "update_shared_secret", lambda w, x, y, z: False)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.vendor = "ADVA"
        d.usable_ip = "IP"
        d.tid = "DNTNTXKI1ZW"
        d.ise_success = False
        d.tacacs_remediation_required = False
        d.msg = get_base_msg()
        d._process_ise_secret()
        assert d.msg["ise"] == {
            "status": "failed",
            "message": "unable to update shared secret",
            "data": {"ip": "IP", "tid": "DNTNTXKI1ZW"},
        }
        assert d.ise_success is False
        assert d.tacacs_remediation_required is True


@pytest.mark.unittest
def test_get_device_ise_id_and_region(monkeypatch):
    monkeypatch.setattr(device, "id_lookup_cluster", mock_id_lookup_cluster)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.usable_ip = "IP"
        ise_id, region = d._get_device_ise_id_and_region()
        assert ise_id == "ID"
        assert region == "south"


@pytest.mark.unittest
def test_get_device_ise_id_and_region_not_found(monkeypatch):
    monkeypatch.setattr(device, "id_lookup_cluster", mock_id_lookup_cluster_no_results)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.usable_ip = "IP"
        d.tid = "DNTNTXKI1ZW"
        d.msg = get_base_msg()
        ise_id, region = d._get_device_ise_id_and_region()
        assert ise_id == ""
        assert region == ""
        assert d.msg["ise"] == {
            "status": "failed",
            "message": "unable to find device id",
            "data": {"ip": "IP", "tid": "DNTNTXKI1ZW"},
        }


@pytest.mark.unittest
def test_get_ise_device(monkeypatch):
    monkeypatch.setattr(device, "get_ise_record_by_id_cluster_specified", mock_get_ise_record_by_id_cluster_specified)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.tid = "DNTNTXKI1ZW"
        ise_device = d._get_ise_device("id", "south")
        assert ise_device == {
            "id": "ID",
            "name": "DNTNTXKI1ZW",
            "description": "DNTNTXKI1ZW",
            "authenticationSettings": {
                "enableKeyWrap": False,
                "dtlsRequired": False,
                "keyInputFormat": "ASCII",
                "enableMultiSecret": "false",
            },
            "tacacsSettings": {
                "sharedSecret": "SECRETS",
                "connectModeOptions": "OFF",
                "previousSharedSecret": "",
                "previousSharedSecretExpiry": 99,
            },
            "profileName": "Cisco",
            "coaPort": 0,
            "link": {
                "rel": "self",
                "href": "https://iseisebaby/ers/config/networkdevice/id",
                "type": "application/json",
            },
            "NetworkDeviceIPList": [{"ipaddress": "1.1.1.1", "mask": 32}],
            "NetworkDeviceGroupList": [
                "Access#TWC#Edge",
                "Device Type#All Device Types#RAD",
                "Location#All Locations#Southwest",
                "IPSEC#Is IPSEC Device",
                "Legacy-Deployment#Legacy-Deployment",
                "Network Test device group#Network Test device group",
                "DukeEnergy#DukeEnergy",
            ],
        }


@pytest.mark.unittest
def test_compare_secrets_no_tacacs_settings(monkeypatch):
    def mock_get_ise_device_no_tacacs_settings(*args, **kwargs):
        return [
            {
                "id": "c2319b30-5cf1-11f0-976e-c6f8dbef3b79",
                "name": "HLNAMTKY1ZW",
                "description": "HLNAMTKY1ZW",
                "authenticationSettings": {
                    "enableKeyWrap": False,
                    "dtlsRequired": False,
                    "keyEncryptionKey": "",
                    "messageAuthenticatorCodeKey": "",
                    "keyInputFormat": "ASCII",
                    "enableMultiSecret": "false",
                },
                "profileName": "Cisco",
                "coaPort": 1700,
                "link": {
                    "rel": "self",
                    "href": "https://anaca-ise-pan-w21.chtrse.com:9060/ers/config/networkdevice/c2319b30-5cf1-11f0-976e-c6f8dbef3b79",
                    "type": "application/json",
                },
                "NetworkDeviceIPList": [{"ipaddress": "10.29.116.184", "mask": 32}],
                "NetworkDeviceGroupList": [
                    "Location#All Locations#CHTR-Southwest",
                    "IPSEC#Is IPSEC Device#No",
                    "Device Type#All Device Types#RAD",
                    "Access#TWC#Edge",
                    "Network Test device group#Network Test device group",
                    "Legacy-Deployment#Legacy-Deployment",
                    "DukeEnergy#DukeEnergy",
                ],
            }
        ]

    ise_device = mock_get_ise_device_no_tacacs_settings()[0]
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        assert d._compare_secrets(ise_device, "SECRETS") is False


@pytest.mark.unittest
def test_compare_secrets_match():
    ise_device = mock_get_ise_record_by_id_cluster_specified()[0]
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        assert d._compare_secrets(ise_device, "SECRETS") is True


@pytest.mark.unittest
def test_compare_secrets_mismatch():
    ise_device = mock_get_ise_record_by_id_cluster_specified()[0]
    ise_device["tacacsSettings"]["sharedSecret"] = "OUTDATED"
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        assert d._compare_secrets(ise_device, "SECRETS") is False


@pytest.mark.unittest
def test_update_ise_secret(monkeypatch):
    ise_id = "ID"
    sense_shared_secret = "SECRETS!!!"
    monkeypatch.setattr(device, "update_shared_secret", lambda w, x, y, z: True)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.msg = get_base_msg()
        d.tid = "TID"
        d.usable_ip = "IP"
        d.ise_success = False  # init value
        d.tacacs_remediation_required = False
        d._update_ise_secret(ise_id, sense_shared_secret)
        assert d.ise_success is True
        assert d.tacacs_remediation_required is False
        assert d.msg["ise"] == {"status": "validated", "message": "secret updated on existing entry"}


@pytest.mark.unittest
def test_update_ise_secret_failed(monkeypatch):
    ise_id = "ID"
    sense_shared_secret = "SECRETS!!!"
    monkeypatch.setattr(device, "update_shared_secret", lambda w, x, y, z: False)
    with patch.object(Device, "__init__", lambda x, y, z: None):
        d = Device({}, "CID")
        d.msg = get_base_msg()
        d.tid = "TID"
        d.usable_ip = "IP"
        d.ise_success = False  # init value
        d.tacacs_remediation_required = False
        d._update_ise_secret(ise_id, sense_shared_secret)
        assert d.ise_success is False  # shouldn't be updating to True
        assert d.tacacs_remediation_required is True
        assert d.msg["ise"] == {
            "status": "failed",
            "message": "unable to update shared secret",
            "data": {"ip": "IP", "tid": "TID"},
        }
