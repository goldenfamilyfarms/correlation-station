import copy

import pytest

from arda_app.api import vlan_reservation

from arda_app.bll.net_new.vlan_reservation import collect_vlans, vlan_reservation_main

payload = {
    "service_type": "z_side",
    "cid": "81.L1XX.006522..TWCC",
    "product_name": "Carrier E-Access (Fiber)",
    "primary_vlan": "50",
}


@pytest.mark.unittest
def test_no_cid(client):
    """Test design with a valid, defined cid"""

    data = copy.deepcopy(payload)
    del data["cid"]

    resp = client.post("arda/v1/vlan_reservation", json=data)

    assert resp.status_code == 500
    assert "Required query parameter(s) not specified: cid" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_json_error(client):
    """Test design with a valid, defined cid"""

    resp = client.post("arda/v1/vlan_reservation", data=b"/")

    assert resp.status_code == 500
    assert "JSON decode error" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_available_vlan_fail(monkeypatch, client):
    """Raise a 502 if primary vlan is in use."""

    # Update primary vlan to one that is already in use
    payload["primary_vlan"] = "1200"
    monkeypatch.setattr(vlan_reservation_main, "get_circuit_data", lambda *_: "")
    monkeypatch.setattr(collect_vlans, "get_device_vendor", lambda *_: "RAD")
    monkeypatch.setattr(vlan_reservation_main, "get_network_vlans", lambda *_: ["1400", "1401", "1402"])
    monkeypatch.setattr(vlan_reservation_main, "get_granite_vlans", lambda *_: ["1200", "1201", "1202"])

    resp = client.post("arda/v1/vlan_reservation", json=payload)

    assert resp.status_code == 500
    assert "is already in use" in resp.json().get("message")


@pytest.mark.unittest
def test_success(monkeypatch, client):
    """Test design with a valid, defined cid"""
    # mock vlan_reservation is ok

    monkeypatch.setattr(vlan_reservation, "vlan_reservation_main", lambda *_: None)

    resp = client.post("arda/v1/vlan_reservation", json=payload)

    assert resp.status_code == 200
    assert "Successful VLAN Reservation" in resp.json().get("message")
