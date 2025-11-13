import json
import pytest

from palantir_app.bll import ipc


class MockResponse:
    def __init__(self, json_data, status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(self.json_data)

    def json(self):
        return self.json_data


@pytest.mark.unittest
def test_get_ipc_ip(monkeypatch):
    def mocked_ipc_get(*args, **kwargs):
        data = {"devices": [{"interfaces": [{"ipAddress": ["FAKE_IP"]}, {"macAddress": "FAKE_MAC"}]}]}
        return MockResponse(json_data=data).json()

    monkeypatch.setattr(ipc, "ipc_get", mocked_ipc_get)
    assert ipc.get_ip_from_tid("tid") == "FAKE_IP"


@pytest.mark.unittest
def test_get_ipc_ip_no_data(monkeypatch):
    def mocked_ipc_get(*args, **kwargs):
        return None

    monkeypatch.setattr(ipc, "ipc_get", mocked_ipc_get)
    ip = ipc.get_ip_from_tid("tid")
    assert ip == ""


@pytest.mark.unittest
def test_get_ipc_ip_more_than_1(monkeypatch):
    def mocked_ipc_get(*args, **kwargs):
        data = {
            "devices": [
                {"interfaces": [{"ipAddress": ["FAKE_IP"]}]},
                {"interfaces": [{"ipAddress": ["FAKE_IP_2"]}, {"macAddress": "FAKE_MAC_2"}]},
            ]
        }
        return MockResponse(json_data=data).json()

    monkeypatch.setattr(ipc, "ipc_get", mocked_ipc_get)
    assert ipc.get_ip_from_tid("tid") == "FAKE_IP_2"


@pytest.mark.unittest
def test_get_ipc_ip_bad_data(monkeypatch):
    def mocked_ipc_get(*args, **kwargs):
        data = {"devices": [{"interfaces": [{"BAD_DATA": "BAD_DATA"}]}]}
        return MockResponse(json_data=data).json()

    monkeypatch.setattr(ipc, "ipc_get", mocked_ipc_get)
    ip = ipc.get_ip_from_tid("tid")
    assert ip == ""
