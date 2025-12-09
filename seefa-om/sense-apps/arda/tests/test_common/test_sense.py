import json
from pytest import mark, raises

from arda_app.dll import sense
from common_sense.common import device
from tests.data import device_validator_data


class MockResponse:
    def __init__(self, json_data, status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(self.json_data)

    def json(self):
        return self.json_data


@mark.unittest
def test_get_optic_info(monkeypatch):
    # bad test - beorn_response is not a dict
    monkeypatch.setattr(sense, "post_sense", lambda *args, **kwargs: ["mock_resp"])
    with raises(Exception):
        sense.get_optic_info("hostname", "1234")

    # good test
    beorn_response = {"mock_resp": "temp"}
    monkeypatch.setattr(sense, "post_sense", lambda *args, **kwargs: beorn_response)
    assert sense.get_optic_info("hostname", "1234") == beorn_response


@mark.unittest
def test_verify_device_connectivity_fqdn_resolves(monkeypatch):
    fqdn_resolves = MockResponse(device_validator_data.full_success_response)
    monkeypatch.setattr(device, "get_device_validation", lambda *args, **kwargs: fqdn_resolves)
    resolves = fqdn_resolves.json()
    assert device.verify_device_connectivity(hostname="IRMTMIBJ1CW") == resolves
    assert resolves["message"]["IRMTMIBJ1CW"]["reachable"] == "IRMTMIBJ1CW.DEV.CHTRSE.COM"


@mark.unittest
def test_verify_device_connectivity_fqdn_does_not_resolve(monkeypatch):
    fqdn_does_not_resolve = MockResponse(device_validator_data.fqdn_not_resolving_response)
    monkeypatch.setattr(device, "get_device_validation", lambda *args, **kwargs: fqdn_does_not_resolve)
    not_resolves = fqdn_does_not_resolve.json()
    print(not_resolves)
    assert device.verify_device_connectivity(hostname="IRMTMIBJ1CW") == not_resolves
    assert not_resolves["message"]["IRMTMIBJ1CW"]["reachable"] == "150.181.2.44"
