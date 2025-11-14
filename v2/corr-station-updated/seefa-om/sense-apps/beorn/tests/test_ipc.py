import pytest

from beorn_app.dll import ipc


def mock_ipc_no_devices(*args, **kwargs):
    # crosswalk 409 status code, {"count": 0, "devices": []}
    # hydra_get will return empty dict with failout=False
    return {}


@pytest.mark.unittest
def test_get_ip_from_tid_no_devices(monkeypatch):
    monkeypatch.setattr(ipc, "hydra_get", mock_ipc_no_devices)
    ip = ipc.get_ip_from_tid("SNACTXLW1ZW")
    assert ip is None


def mock_ipc_one_device(*args, **kwargs):
    return {
        "count": 1,
        "devices": [
            {
                "addressType": "Dynamic DHCP",
                "adminLoginId": "P2991880",
                "createdate": "",
                "description": "",
                "deviceType": "Unspecified",
                "domainName": "dev.chtrse.com.",
                "domainType": "Default",
                "hostname": "CNI4TXR37ZW",
                "id": 10879288,
                "interfaces": [
                    {
                        "addressType": ["Dynamic DHCP"],
                        "container": ["AUSDTXIR5CW"],
                        "excludeFromDiscovery": "false",
                        "hwType": "ethernet",
                        "id": 10879284,
                        "ipAddress": ["71.42.150.184"],
                        "macAddress": "0020D25B1E81",
                        "name": "Default",
                        "relayAgentCircuitId": ["6972622e39395c2667652d322f302f392e3939"],
                        "relayAgentRemoteId": [None],
                        "sequence": 0,
                        "virtual": [False],
                    }
                ],
                "lastupdate": "2023-04-15 02:19",
                "resourceRecordFlag": "false",
                "userDefinedFields": [],
            }
        ],
    }


@pytest.mark.unittest
def test_get_ip_from_tid_one_device(monkeypatch):
    monkeypatch.setattr(ipc, "hydra_get", mock_ipc_one_device)
    ip = ipc.get_ip_from_tid("CNI4TXR37ZW")
    assert ip == "71.42.150.184"
