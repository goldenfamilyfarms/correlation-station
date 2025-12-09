import pytest
from pytest import raises

from arda_app.bll.net_new.with_cj import create_mtu as mtu


class MockResponse:
    def __init__(self, role, device_bw, connector_type, vendor, model, device_template, uplink, handoff):
        self.role = role
        self.device_bw = device_bw
        self.connector_type = connector_type
        self.vendor = vendor
        self.model = model
        self.device_template = device_template
        self.uplink = uplink
        self.handoff = handoff

    def get(self):
        return self

    def set_handoff(*args, **kwargs):
        return


class PortModel:
    def __init__(self, slot, template, connector, port_access_id):
        self.slot = slot
        self.template = template
        self.connector = connector
        self.port_access_id = port_access_id

    def get(self):
        return self


port_model = {"slot": "NET 1", "template": "testtemp", "connector": "", "port_access_id": "ETH PORT 1"}
portmodel = PortModel(**port_model)

DEVICE = {
    "role": "cpe",
    "device_bw": "1 Gbps",
    "uplink": portmodel,
    "model": "ARC CBA850",
    "connector_type": "LC",
    "vendor": "RAD",
    "device_template": "ETX203AX/2SFP/2UTP2SFP",
    "handoff": portmodel,
}


@pytest.mark.unittest
def test_create_shelf(monkeypatch):
    shelf_create_data = "Shelf has nothing to update"
    monkeypatch.setattr(mtu, "post_granite", lambda *args, **kwargs: shelf_create_data)

    with raises(Exception):
        assert mtu._create_shelf({}) is None

    shelf_create_data = {"retString": "test"}
    monkeypatch.setattr(mtu, "post_granite", lambda *args, **kwargs: shelf_create_data)

    with raises(Exception):
        assert mtu._create_shelf({}) is None

    shelf_create_data = {"retString": "Shelf Added"}
    monkeypatch.setattr(mtu, "post_granite", lambda *args, **kwargs: shelf_create_data)

    assert mtu._create_shelf({}) is None


@pytest.mark.unittest
def test_build_uplink(monkeypatch):
    mock_payload = MockResponse(**DEVICE)
    mock_payload.uplink = None
    monkeypatch.setattr(mtu, "get_equipment_buildout", lambda *args, **kwargs: None)

    with raises(Exception):
        assert mtu._build_uplink("shelf_name", mock_payload) is None

    mock_payload1 = MockResponse(**DEVICE)
    mock_payload1.uplink.slot = "1"
    equipment_data1 = [{"SLOT": "1"}]
    equipment_data2 = [{"PORT_INST_ID": "123", "SLOT": "1"}]
    mock_query = iter([equipment_data1, equipment_data2])
    monkeypatch.setattr(mtu, "get_equipment_buildout", lambda *args, **kwargs: next(mock_query))
    monkeypatch.setattr(mtu, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(mtu, "put_granite", lambda *args, **kwargs: None)

    assert mtu._build_uplink("shelf_name", mock_payload1) == "123"


@pytest.mark.unittest
def test_build_handoff(monkeypatch):
    mock_payload = MockResponse(**DEVICE)
    mock_payload.handoff = None
    monkeypatch.setattr(mtu, "get_equipment_buildout", lambda *args, **kwargs: None)

    with raises(Exception):
        assert mtu._build_handoff("shelf_name", "1 Gbps", mock_payload) is None

    mock_payload1 = MockResponse(**DEVICE)
    mock_payload1.handoff.slot = "1"
    equipment_data1 = [{"SLOT": "1"}]
    equipment_data2 = [{"PORT_INST_ID": "123", "SLOT": "1"}]
    mock_query = iter([equipment_data1, equipment_data2])
    monkeypatch.setattr(mtu, "get_equipment_buildout", lambda *args, **kwargs: next(mock_query))
    monkeypatch.setattr(mtu, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(mtu, "put_granite", lambda *args, **kwargs: None)

    assert mtu._build_handoff("shelf_name", "1 Gbps", mock_payload1) == "123"
