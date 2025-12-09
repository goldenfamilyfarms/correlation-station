import pytest
from pytest import raises

from arda_app.bll.circuit_design import common as cmn
from arda_app.bll.circuit_design.bandwidth_change import express_bw_upgrade as ebu
from mock_data.circuit_design import circuit_upgrade as cu

payload = {
    "service_type": "bw_upgrade",
    "product_name": "Fiber Internet Access",
    "engineering_id": "ENG-12345689",
    "cid": cu.pathid,
    "bw_speed": "100",
    "bw_unit": "Gbps",
    "change_reason": "change request",
    "engineering_name": "ENG-12345689",
}

result = {"circuitId": "20.L4XX.%..CHRT", "circuit_inst_id": "227564", "bw_speed": "100", "bw_unit": "Gbps"}

assc_resp = [
    {"associationValue": "associationValue", "associationName": "associationName", "numberRangeName": "numberRangeName"}
]


@pytest.mark.unittest
def test_ebu_from_Mbps_to_Gbps(monkeypatch):
    """Tests a good GB express bw unit upgrade"""
    """Tests G units instead of M"""
    monkeypatch.setattr(cmn, "validate_payload_express_bw_upgrade", lambda *args: ("100", "Gbps", 100000))
    monkeypatch.setattr(cmn, "_check_granite_bandwidth", lambda *args: ("100", "Mbps", 100, "227563", "1"))
    monkeypatch.setattr(cmn, "_granite_create_circuit_revision", lambda *args: (True, "227564", "2"))
    monkeypatch.setattr(cmn, "express_update_circuit_bw", lambda *args: result)
    monkeypatch.setattr(ebu, "update_circuit_status", lambda *args: None)
    monkeypatch.setattr(ebu, "bw_upgrade_assign_gsip", lambda *args: None)

    assert ebu.express_bw_upgrade_main(payload) == result


@pytest.mark.unittest
def test_ebu_w_association(monkeypatch):
    payload["product_name"] = "EP-LAN (Fiber)"

    monkeypatch.setattr(cmn, "validate_payload_express_bw_upgrade", lambda *args: ("100", "Gbps", 100000))
    monkeypatch.setattr(cmn, "_check_granite_bandwidth", lambda *args: ("100", "Mbps", 100, "227563", "1"))
    monkeypatch.setattr(ebu, "get_path_association", lambda *args: assc_resp)
    monkeypatch.setattr(cmn, "_granite_create_circuit_revision", lambda *args: (True, "227564", "2"))
    monkeypatch.setattr(ebu, "assign_association", lambda *args: True)
    monkeypatch.setattr(cmn, "add_vrfid_link", lambda *args: None)
    monkeypatch.setattr(cmn, "express_update_circuit_bw", lambda *args: result)
    monkeypatch.setattr(ebu, "update_circuit_status", lambda *args: None)
    monkeypatch.setattr(ebu, "bw_upgrade_assign_gsip", lambda *args: None)

    assert ebu.express_bw_upgrade_main(payload) == result


@pytest.mark.unittest
def test_ebu_from_Mbps_to_Mbps(monkeypatch):
    """Tests a good MB express bw unit upgrade"""
    payload["product_name"] = "Fiber Internet Access"
    payload["bw_speed"] = "300"
    payload["bw_unit"] = "Mbps"
    result["bw_speed"] = "300"
    result["bw_unit"] = "Mbps"

    monkeypatch.setattr(cmn, "validate_payload_express_bw_upgrade", lambda *args: ("300", "Mbps", 300))
    monkeypatch.setattr(cmn, "_check_granite_bandwidth", lambda *args: ("100", "Mbps", 100, "227563", "1"))
    monkeypatch.setattr(cmn, "_granite_create_circuit_revision", lambda *args: (True, "227564", "2"))
    monkeypatch.setattr(cmn, "express_update_circuit_bw", lambda *args: result)
    monkeypatch.setattr(ebu, "update_circuit_status", lambda *args: None)
    monkeypatch.setattr(ebu, "bw_upgrade_assign_gsip", lambda *args: None)

    assert ebu.express_bw_upgrade_main(payload) == result


@pytest.mark.unittest
def test_ebu_same_bw(monkeypatch):
    """Tests to see if the bandwidth for upgrade is the same"""
    """Returns message saying upgrade is not needed because 500 == 500"""
    monkeypatch.setattr(cmn, "validate_payload_express_bw_upgrade", lambda *args: ("500", "Mbps", 500))
    monkeypatch.setattr(cmn, "_check_granite_bandwidth", lambda *args: ("500", "Mbps", 500, "227563", "1"))

    with raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None


@pytest.mark.unittest
def test_ebu_smaller_bw_request(monkeypatch):
    """Tests the ebu func for smaller bw requested than current bw"""
    """Returns a 500 because 300 < 500"""
    monkeypatch.setattr(cmn, "validate_payload_express_bw_upgrade", lambda *args: ("100", "Mbps", 100))
    monkeypatch.setattr(cmn, "_check_granite_bandwidth", lambda *args: ("500", "Mbps", 500, "227563", "1"))

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None


@pytest.mark.unittest
def test_aborts(monkeypatch):
    # unsupported product
    payload["product_name"] = "Bad Product"

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None

    # Unable to create revision
    payload["product_name"] = "Fiber Internet Access"

    monkeypatch.setattr(cmn, "validate_payload_express_bw_upgrade", lambda *args: ("100", "Gbps", 100000))
    monkeypatch.setattr(cmn, "_check_granite_bandwidth", lambda *args: ("100", "Mbps", 100, "227563", "1"))
    monkeypatch.setattr(cmn, "_granite_create_circuit_revision", lambda *args: (None, "227564", "2"))

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None

    # New revision instance ID matches current instance ID
    monkeypatch.setattr(cmn, "_granite_create_circuit_revision", lambda *args: (True, "227563", "2"))

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None

    # missing association
    payload["product_name"] = "EPL (Fiber)"

    monkeypatch.setattr(cmn, "_granite_create_circuit_revision", lambda *args: (True, "123", "2"))
    monkeypatch.setattr(ebu, "get_path_association", lambda *args: {"retString": True})

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None

    # No assign association result
    monkeypatch.setattr(ebu, "get_path_association", lambda *args: assc_resp)
    monkeypatch.setattr(ebu, "assign_association", lambda *args: False)

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None

    # not compliant
    payload["product_name"] = "Fiber Internet Access"

    monkeypatch.setattr(cmn, "express_update_circuit_bw", lambda *args: result)
    monkeypatch.setattr(ebu, "update_circuit_status", lambda *args: None)
    monkeypatch.setattr(ebu, "bw_upgrade_assign_gsip", lambda *args: None)

    with pytest.raises(Exception):
        assert ebu.express_bw_upgrade_main(payload) is None
