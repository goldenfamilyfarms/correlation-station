import pytest

from pytest import raises

from unittest.mock import patch

from palantir_app.bll import device_validator
from tests.mock_data.acceptance.device import (
    mock_granite_circuit_devices,
    mock_granite_circuit_devices_bad_inital_cid,
    mock_granite_circuit_devices_bad_inital_cid_emptystr,
    mock_granite_circuit_devices_bad_service_type,
    mock_granite_circuit_devices_return,
)


@pytest.mark.unittest
def test_get_cid_data(monkeypatch):
    def mocked_get_circuit_devices(cid):
        return mock_granite_circuit_devices

    monkeypatch.setattr(device_validator, "get_circuit_devices", mocked_get_circuit_devices)

    cid = "33.L1XX.006714..TWCC"
    topology, device_list = device_validator._get_cid_data(cid)
    assert topology == mock_granite_circuit_devices_return["topology"]
    assert device_list == mock_granite_circuit_devices_return["device_list"]


@pytest.mark.unittest
def test_get_cid_data_fail_mismatched_cid(monkeypatch):
    def mocked_get_circuit_devices(cid):
        return mock_granite_circuit_devices

    monkeypatch.setattr(device_validator, "get_circuit_devices", mocked_get_circuit_devices)

    cid = ""
    with raises(Exception):
        topology, device_list = device_validator._get_cid_data(cid)


@pytest.mark.unittest
def test_get_cid_data_fail_bad_servicetype(monkeypatch):
    def mocked_get_circuit_devices(cid):
        return mock_granite_circuit_devices_bad_service_type

    monkeypatch.setattr(device_validator, "get_circuit_devices", mocked_get_circuit_devices)

    cid = "33.L1XX.006714..TWCC"
    with raises(Exception):
        topology, device_list = device_validator._get_cid_data(cid)


@pytest.mark.unittest
def test_get_cid_data_fail_bad_initial_cid(monkeypatch):
    def mocked_get_circuit_devices(cid):
        return mock_granite_circuit_devices_bad_inital_cid

    monkeypatch.setattr(device_validator, "get_circuit_devices", mocked_get_circuit_devices)

    cid = "33.L1XX.006714..TWCC"
    with raises(Exception):
        topology, device_list = device_validator._get_cid_data(cid)


@pytest.mark.unittest
def test_get_cid_data_fail_bad_initial_cid_empty_str(monkeypatch):
    def mocked_get_circuit_devices(cid):
        return mock_granite_circuit_devices_bad_inital_cid_emptystr

    monkeypatch.setattr(device_validator, "get_circuit_devices", mocked_get_circuit_devices)

    cid = "33.L1XX.006714..TWCC"
    with raises(Exception):
        topology, device_list = device_validator._get_cid_data(cid)


def get_base_msg():
    return {"hostname": {}, "ip": {}, "fqdn": {}, "tacacs": {}, "ise": {}, "granite": {}}


@pytest.mark.unittest
def test_device_combine_message_no_l2circuit_error():
    with patch.object(device_validator.Device, "__init__", lambda x, y, z: None):
        d = device_validator.Device({}, "FAKE_CID")
        d.msg = get_base_msg()
        d.tid = "FAKE_TID"
        e = device_validator.Device({}, "FAKE_CID")
        e.msg = get_base_msg()
        e.tid = "FAKE_TID_2"

        devices = [d, e]
        assert device_validator.get_combined_message(devices) == {
            "FAKE_TID": {"hostname": {}, "ip": {}, "fqdn": {}, "tacacs": {}, "ise": {}, "granite": {}},
            "FAKE_TID_2": {"hostname": {}, "ip": {}, "fqdn": {}, "tacacs": {}, "ise": {}, "granite": {}},
        }


@pytest.mark.unittest
def test_device_combine_message_l2circuit_error():
    def mock_validate_l2_connection(*args, **kwargs):
        return {
            "status": "failed",
            "reason": "l2circuit status",
            "data": {"interface": "ge-2/2/2", "connection": "down"},
        }

    with patch.object(device_validator.Device, "__init__", lambda x, y, z: None):
        d = device_validator.Device({}, "FAKE_CID")
        d.msg = get_base_msg()
        d.tid = "FAKE_TID"
        d.msg["additional"] = {"l2circuit": mock_validate_l2_connection()}
        e = device_validator.Device({}, "FAKE_CID")
        e.msg = get_base_msg()
        e.tid = "FAKE_TID_2"
        devices = [d, e]
        assert device_validator.get_combined_message(devices) == {
            "FAKE_TID": {
                "hostname": {},
                "ip": {},
                "fqdn": {},
                "tacacs": {},
                "ise": {},
                "granite": {},
                "additional": {
                    "l2circuit": {
                        "status": "failed",
                        "reason": "l2circuit status",
                        "data": {"interface": "ge-2/2/2", "connection": "down"},
                    }
                },
            },
            "FAKE_TID_2": {"hostname": {}, "ip": {}, "fqdn": {}, "tacacs": {}, "ise": {}, "granite": {}},
        }
