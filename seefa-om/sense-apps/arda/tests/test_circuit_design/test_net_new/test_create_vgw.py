import pytest
from pytest import raises

from arda_app.bll.net_new import create_vgw as vgw


OVERLAY = {"role": "vgw", "vendor": "AUDIOCODES", "model": "ARC CBA850", "device_template": "MEDIANT 500B SBC"}


@pytest.mark.unittest
def test_create_vgw_shelf(monkeypatch):
    shelf_payload = {
        "cid": "cid",
        "product_name": "Wireless Internet Access-Primary",
        "service_type": "net_new_cj",
        "legacy_company": "Charter",
        "build_type": "MTU New Build",
        "role": "cpe",
        "side": "a_side",
        "connector_type": "RJ45",
        "uni_type": "Access",
        "number_of_b_channels": "23",
        "number_of_circuits_in_group": "1",
    }
    lvl1 = {
        "BANDWIDTH": "1 Gbps",
        "SEQUENCE": "1",
        "A_CLLI": "AUSDTXIR",
        "Z_CLLI": "AUSXTXZR",
        "ELEMENT_NAME": "51001.GE1.AUSDTXIR8CW.AUSXTXZR5ZW",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "PATH_A_SITE": "AUSXTXZR-SEEFA_TESTING//11921 N MO PAC EXPY",
        "PATH_Z_SITE": "AUSXTXZR-SEEFA_TESTING//11921 N MO PAC EXPY",
        "ELEMENT_REFERENCE": "test",
        "CIRC_PATH_INST_ID": "testcid",
        "ELEMENT_BANDWIDTH": "1 Gbps",
        "Z_SITE_NAME": "AUSXTXZR-SEEFA_TESTING//11921 N MO PAC EXPY",
    }
    resp = {
        "circ_path_inst_id": "testcid",
        "vgw_handoff": "vgw_handoff_pid",
        "vgw_handoff_paid": "vgw_handoff_paid",
        "vgw_shelf": "shelf_name",
        "vgw_tid": "tid",
        "vgw_uplink": "vgw_uplink_pid",
        "vgw_uplink_paid": "vgw_uplink_paid",
    }

    payload = shelf_payload
    payload["product_name"] = "SIP - Trunk (Fiber)"
    monkeypatch.setattr(vgw, "get_circuit_site_info", lambda *args, **kwargs: [lvl1])
    monkeypatch.setattr(vgw, "get_shelf_names", lambda *args, **kwargs: ("shelf_name", "tid"))
    monkeypatch.setattr(vgw, "_create_shelf", lambda *args, **kwargs: None)
    monkeypatch.setattr(vgw, "_build_uplink", lambda *args, **kwargs: ("vgw_uplink_pid", "vgw_uplink_paid"))
    monkeypatch.setattr(vgw, "_build_handoff", lambda *args, **kwargs: ("vgw_handoff_pid", "vgw_handoff_paid"))
    assert vgw.create_vgw_shelf(payload) == resp

    payload1 = shelf_payload.copy()
    payload1["product_name"] = "PRI Trunk (Fiber)"
    payload1["number_of_circuits_in_group"] = "1"
    assert vgw.create_vgw_shelf(payload1) == resp

    payload2 = shelf_payload.copy()
    payload2["product_name"] = "PRI Trunk (Fiber)"
    payload2["number_of_circuits_in_group"] = "2"

    with raises(Exception):
        assert vgw.create_vgw_shelf(payload2) is None

    payload3 = shelf_payload.copy()
    payload3["product_name"] = "PRI Trunk (Fiber)"
    payload3["number_of_circuits_in_group"] = "3"

    with raises(Exception):
        assert vgw.create_vgw_shelf(payload3) is None

    payload4 = shelf_payload.copy()
    payload4["product_name"] = "SIP Trunk(Fiber) Analog"
    payload4["service_code"] = "RZ901"
    assert vgw.create_vgw_shelf(payload4) == resp

    payload5 = shelf_payload.copy()
    payload5["product_name"] = "PRI Trunk(Fiber) Analog"
    payload5["service_code"] = "RZ900"
    assert vgw.create_vgw_shelf(payload5) == resp

    payload6 = shelf_payload.copy()
    payload6["product_name"] = "SIP Trunk(Fiber) Analog"
    payload6["service_code"] = "RZ900"
    assert vgw.create_vgw_shelf(payload6) == resp

    payload7 = shelf_payload.copy()
    payload7["product_name"] = "SIP Trunk(Fiber) Analog"
    payload7["service_code"] = None

    with raises(Exception):
        assert vgw.create_vgw_shelf(payload7) is None


@pytest.mark.unittest
def test_create_shelf(monkeypatch):
    shelf_create_data = {"retString": "Shelf has nothing to update"}
    monkeypatch.setattr(vgw, "post_granite", lambda *args, **kwargs: shelf_create_data)

    with raises(Exception):
        assert vgw._create_shelf({}) is None

    shelf_create_data = {"retString": "test"}
    monkeypatch.setattr(vgw, "post_granite", lambda *args, **kwargs: shelf_create_data)

    with raises(Exception):
        assert vgw._create_shelf({}) is None

    shelf_create_data = {"retString": "Shelf Added"}
    monkeypatch.setattr(vgw, "post_granite", lambda *args, **kwargs: shelf_create_data)

    assert vgw._create_shelf({}) is None


@pytest.mark.unittest
def test_build_uplink(monkeypatch):
    mock_payload = vgw.OverlayDeviceTopologyModel(**OVERLAY)
    mock_payload.uplink = None
    monkeypatch.setattr(vgw, "get_equipment_buildout", lambda *args, **kwargs: None)

    with raises(Exception):
        assert vgw._build_uplink("shelf_name", mock_payload) is None

    mock_payload1 = vgw.OverlayDeviceTopologyModel(**OVERLAY)
    mock_payload1.uplink.slot = "1"
    equipment_data1 = [{"SLOT": "1"}]
    equipment_data2 = [{"PORT_INST_ID": "123", "SLOT": "1"}]
    mock_query = iter([equipment_data1, equipment_data2])
    monkeypatch.setattr(vgw, "get_equipment_buildout", lambda *args, **kwargs: next(mock_query))
    monkeypatch.setattr(vgw, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(vgw, "put_granite", lambda *args, **kwargs: None)

    assert vgw._build_uplink("shelf_name", mock_payload1) == ("", "2/1")


@pytest.mark.unittest
def test_build_handoff(monkeypatch):
    mock_payload = vgw.OverlayDeviceTopologyModel(**OVERLAY)
    mock_payload.handoff = None
    monkeypatch.setattr(vgw, "get_equipment_buildout", lambda *args, **kwargs: None)

    with raises(Exception):
        assert vgw._build_handoff("shelf_name", mock_payload) is None

    mock_payload1 = vgw.OverlayDeviceTopologyModel(**OVERLAY)
    mock_payload1.uplink.slot = "1"
    mock_payload1.handoff.slot = "1"
    equipment_data1 = [{"SLOT": "1"}]
    equipment_data2 = [{"PORT_INST_ID": "123", "SLOT": "1", "PORT_NAME": "1"}]
    mock_query = iter([equipment_data1, equipment_data2])
    monkeypatch.setattr(vgw, "get_equipment_buildout", lambda *args, **kwargs: next(mock_query))
    monkeypatch.setattr(vgw, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(vgw, "put_granite", lambda *args, **kwargs: None)

    assert vgw._build_handoff("shelf_name", mock_payload1) == ("123", "GE1/1")
