import pytest
from pytest import raises


from arda_app.bll.net_new.vlan_reservation import vlan_reservation_main as vrm


class MockResponse:
    def __init__(
        self, service_type, product_name, cid, primary_vlan, vlan_requested, service_provider_vlan, path_instid
    ):
        self.service_type = service_type
        self.product_name = product_name
        self.cid = cid
        self.primary_vlan = primary_vlan
        self.vlan_requested = vlan_requested
        self.service_provider_vlan = service_provider_vlan
        self.path_instid = path_instid

    def get(self):
        return self


class MockResponse_3:
    def __init__(self, service_type, product_name, cid, primary_vlan, service_provider_vlan):
        self.service_type = service_type
        self.product_name = product_name
        self.cid = cid
        self.primary_vlan = primary_vlan
        self.service_provider_vlan = service_provider_vlan

    def get(self):
        return self


class MockResponse_type2:
    def __init__(
        self,
        service_type,
        product_name,
        cid,
        primary_vlan,
        service_provider_vlan,
        spectrum_buy_nni_circuit_id,
        path_instid,
    ):
        self.service_type = service_type
        self.product_name = product_name
        self.cid = cid
        self.primary_vlan = primary_vlan
        self.service_provider_vlan = service_provider_vlan
        self.spectrum_buy_nni_circuit_id = spectrum_buy_nni_circuit_id
        self.path_instid = path_instid

    def get(self):
        return self


circuit_info_data = [
    {
        "CUSTOMER_NAME": "test_customer",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_NAME": "CW.QW",
        "ELEMENT_REFERENCE": "123",
        "CHAN_INST_ID": "111",
    },
    {
        "CUSTOMER_NAME": "test_customer2",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_NAME": "QW.ZW",
        "ELEMENT_REFERENCE": "456",
        "CHAN_INST_ID": "222",
    },
    {
        "CUSTOMER_NAME": "test_customer3",
        "ELEMENT_CATEGORY": "PORT",
        "ELEMENT_NAME": "ZW",
        "ELEMENT_REFERENCE": "789",
        "CHAN_INST_ID": None,
    },
]


circuit_info_data2 = [
    {
        "CUSTOMER_NAME": "test_customer",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_NAME": "21001.GE40.TESTCW.TESTQW",
        "ELEMENT_REFERENCE": "123",
        "CHAN_INST_ID": "111",
    },
    {
        "CUSTOMER_NAME": "test_customer2",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_NAME": "21001.GE10.TESTQW.TESTZW",
        "ELEMENT_REFERENCE": "456",
        "CHAN_INST_ID": "222",
    },
    {
        "CUSTOMER_NAME": "test_customer3",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_NAME": "21001.GE1.TESTZW.TESTZW",
        "ELEMENT_REFERENCE": "789",
        "CHAN_INST_ID": None,
    },
]

get_data = [
    {"PORT_INST_ID": "123", "VENDOR": "ADVA", "PORT_ROLE": "UNI-EP"},
    {"PORT_INST_ID": "123", "VENDOR": "JUNIPER", "PORT_ROLE": "UNI-EP"},
]

get_data2 = [{"PORT_INST_ID": "123", "VENDOR": "ADVA", "PORT_ROLE": "UNI-EP"}]


def _exception():
    raise Exception


@pytest.mark.unittest
def test_vlan_reservation_main(monkeypatch):
    # bad abort vlan_requested and primary_vlan detected.
    vlan_payload = {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "cid": "81.L1XX.013211..CHTR",
        "primary_vlan": "1114",
        "vlan_requested": "1114",
        "service_provider_vlan": None,
        "path_instid": None,
    }
    vlan_pay = MockResponse(**vlan_payload)

    with raises(Exception):
        assert vrm.vlan_reservation_main(vlan_pay) is None

    # good success
    vlan_payload2 = {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "cid": "81.L1XX.013211..CHTR",
        "primary_vlan": None,
        "vlan_requested": "1114",
        "service_provider_vlan": None,
        "path_instid": None,
    }
    vlan_pay2 = MockResponse(**vlan_payload2)

    monkeypatch.setattr(vrm, "get_circuit_data", lambda *args, **kwargs: "transport")
    monkeypatch.setattr(
        vrm, "get_assigned_vlan_or_subinterface", lambda *args, **kwargs: "assigned_vlan_or_subinterface"
    )
    monkeypatch.setattr(vrm, "assign_vlans", lambda *args, **kwargs: None)
    assert vrm.vlan_reservation_main(vlan_pay2) is None


@pytest.mark.unittest
def test_get_circuit_data(monkeypatch):
    # bad abort No record found in Granite
    monkeypatch.setattr(vrm, "get_path_elements_inst_l1", lambda *args, **kwargs: "retString")

    with raises(Exception):
        assert vrm.get_circuit_data("test_cid", "123456") is None

    # bad abort Premiere Client HEB STORES
    monkeypatch.setattr(vrm, "get_path_elements", lambda *args, **kwargs: [{"CUSTOMER_NAME": "HEB STORES"}])

    with raises(Exception):
        assert vrm.get_circuit_data("test_cid", None) is None

    # bad abort No transport paths

    monkeypatch.setattr(vrm, "get_path_elements", lambda *args, **kwargs: [circuit_info_data[2]])

    with raises(Exception):
        assert vrm.get_circuit_data("test_cid", None) is None

    # good success
    transport_elements = circuit_info_data[:2]

    monkeypatch.setattr(vrm, "get_path_elements", lambda *args, **kwargs: circuit_info_data)
    assert vrm.get_circuit_data("test_cid", None) == transport_elements


@pytest.mark.unittest
def test_assign_vlans(monkeypatch):
    # bad abort Unable to locate port info
    vlan_payload3 = {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "cid": "76.L1XX.002172..CHTR",
        "primary_vlan": "",
        "service_provider_vlan": "2026",
        "spectrum_buy_nni_circuit_id": "85.KGFD.000004..TWCC",
        "path_instid": None,
    }

    vlan_pay3 = MockResponse_type2(**vlan_payload3)

    monkeypatch.setattr(vrm, "put_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: {})
    monkeypatch.setattr(vrm, "get_path_elements", lambda *args, **kwargs: {})

    with raises(Exception):
        assert vrm.assign_vlans(1100, circuit_info_data, vlan_pay3, True) is None

    # good test type2 ENNI does not match and 2 ports
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: get_data)
    monkeypatch.setattr(vrm, "put_granite", lambda *args, **kwargs: "put_data")
    assert vrm.assign_vlans(1100, circuit_info_data, vlan_pay3, True) is None

    # good uni-evp 2 ports
    get_data[0]["PORT_ROLE"] = "UNI-EVP"
    get_data[1]["PORT_ROLE"] = "UNI-EVP"
    monkeypatch.setattr(vrm, "get_trunked_port_access_id", lambda *args, **kwargs: "port_access_id")
    assert vrm.assign_vlans(1100, circuit_info_data, vlan_pay3, True) is None

    # good test type2 ENNI matches and 1 ports
    circuit_info_data[0]["ELEMENT_NAME"] = "85.KGFD.000004..TWCC"
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: get_data2)
    assert vrm.assign_vlans(1100, circuit_info_data, vlan_pay3, True) is None

    # good uni_evp 1 port
    get_data2[0]["PORT_ROLE"] = "UNI-EVP"
    assert vrm.assign_vlans(1100, circuit_info_data, vlan_pay3, True) is None

    # good test R-PHY vlan has dash
    vlan_pay3.product_name = "FC + Remote PHY"
    assert vrm.assign_vlans("#1100-1100", circuit_info_data, vlan_pay3, True) is None

    # 1st exception R-PHY abort VLAN assignment failed
    # redo = iter((_exception, None))
    monkeypatch.setattr(vrm, "put_granite", lambda *args, **kwargs: _exception())

    with raises(Exception):
        assert vrm.assign_vlans("#4063-1100", circuit_info_data, vlan_pay3, True) is None

    # 2nd exception abort Unable to locate 'PORT_INST_ID port 2
    vlan_pay3.product_name = "Fiber Internet Access"

    get_data[1].pop("PORT_INST_ID")
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: get_data)
    monkeypatch.setattr(vrm, "put_granite", lambda *args, **kwargs: None)

    with raises(Exception):
        assert vrm.assign_vlans("1100", circuit_info_data, vlan_pay3, True) is None

    # 3rd exception abort Unable to locate 'PORT_INST_ID port 1
    get_data[1]["PORT_INST_ID"] = "123"
    get_data[0].pop("PORT_INST_ID")

    with raises(Exception):
        assert vrm.assign_vlans("1100", circuit_info_data, vlan_pay3, True) is None

    # 4th exception single port abort Unable to locate 'PORT_INST_ID
    get_data2[0].pop("PORT_INST_ID")
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: get_data2)

    with raises(Exception):
        assert vrm.assign_vlans("1100", circuit_info_data, vlan_pay3, True) is None


@pytest.mark.unittest
def test_get_trunked_port_access_id(monkeypatch):
    # good test
    monkeypatch.setattr(vrm, "get_paid_from_zw_to_zw_path", lambda *args, **kwargs: "port_access_id")
    assert vrm.get_trunked_port_access_id("test_cid", circuit_info_data2) == "port_access_id"

    # bad test Unrecognized format for transport path
    with raises(Exception):
        assert vrm.get_trunked_port_access_id("test_cid", [{"BADKEY": "VALUE1"}]) is None

    # bad test no port access id
    with raises(Exception):
        assert vrm.get_trunked_port_access_id("test_cid", {}) is None

    # bad test ZWs to do not match abort
    circuit_info_data2[2]["ELEMENT_NAME"] = "21001.GE1.TEST1ZW.TEST2ZW"

    with raises(Exception):
        assert vrm.get_trunked_port_access_id("test_cid", circuit_info_data2) is None


@pytest.mark.unittest
def test_get_paid_from_zw_to_zw_path(monkeypatch):
    # bad test abort No record found in Granite
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: "retString")

    with raises(Exception):
        assert vrm.get_paid_from_zw_to_zw_path("element_name") is None

    # bad test no port access id in list of dict
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: [{"PORT_ACCESS_ID": None}])

    with raises(Exception):
        assert vrm.get_paid_from_zw_to_zw_path("element_name") is None

    # good test success
    handoff_data = [{"PORT_ACCESS_ID": "123"}]
    monkeypatch.setattr(vrm, "get_granite", lambda *args, **kwargs: handoff_data)
    assert vrm.get_paid_from_zw_to_zw_path("element_name") == handoff_data[0]["PORT_ACCESS_ID"]


@pytest.mark.unittest
def test_get_assigned_vlan_or_subinterface(monkeypatch):
    vlan_payload4 = {
        "service_type": "net_new_cj",
        "product_name": "FC + Remote PHY",
        "cid": "76.L1XX.002172..CHTR",
        "primary_vlan": "",
        "service_provider_vlan": None,
    }

    vlan_pay4 = MockResponse_3(**vlan_payload4)
    monkeypatch.setattr(vrm, "get_granite_vlans", lambda *args, **kwargs: "granite_vlans_or_subinterfaces")
    monkeypatch.setattr(vrm, "get_next_available_vlan_or_subinterface", lambda *args, **kwargs: None)

    assert vrm.get_assigned_vlan_or_subinterface(vlan_pay4, circuit_info_data, False, False) is None
