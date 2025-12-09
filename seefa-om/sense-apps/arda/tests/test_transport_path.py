import pytest

from pydantic import BaseModel
from typing import Optional
from arda_app.bll import transport_path as trp
from tests.data import transport_path_data
from common_sense.common.errors import AbortException


class UplinkData(BaseModel):
    slot: str
    template: str
    port_access_id: str


class SecondaryData(BaseModel):
    slot: str
    template: str
    port_access_id: str


class HandoffData(BaseModel):
    slot: str
    template: str
    port_access_id: str
    connector: str


class UnderlayDeviceTopologyModel(BaseModel):
    uplink: Optional[UplinkData] = None
    secondary: Optional[SecondaryData] = None
    handoff: Optional[HandoffData] = None
    model: str = "W1850"
    device_template: str = "RAD_203AX_1G"
    vendor: str = "VENDOR"

    def set_handoff(*args, **kwargs):
        return

    def get_available_handoff_ports(*args, **kwargs):
        return [["eth-4/1", "eth-4/2"], ["0/0/1", "0/0/2"]]


@pytest.mark.unittest
def test_update_port_access_id(monkeypatch):
    monkeypatch.setattr(trp, "put_granite", lambda *args, **kwargs: None)
    assert trp.update_port_access_id("port_inst_id", "port_access_id") is None

    monkeypatch.setattr(trp, "put_granite", lambda *args, **kwargs: (_ for _ in ()).throw(KeyError))

    with pytest.raises(AbortException):
        assert trp.update_port_access_id("port_inst_id", "port_access_id") is None


@pytest.mark.unittest
def test_get_existing_path_elements_none(monkeypatch):
    body = transport_path_data.mock_payload()
    monkeypatch.setattr(trp, "get_circuit_path_info", transport_path_data.mock_circuit_path_data)
    monkeypatch.setattr(trp, "get_granite", transport_path_data.mock_no_granite_records)

    response = trp.get_existing_path_elements(body)
    assert response is None

    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: ["fail"])
    assert trp.get_existing_path_elements("cid") is None


@pytest.mark.unittest
def test_get_existing_path_elements(monkeypatch):
    body = transport_path_data.mock_payload()
    monkeypatch.setattr(trp, "get_circuit_path_info", transport_path_data.mock_circuit_path_data)
    monkeypatch.setattr(trp, "get_granite", transport_path_data.mock_path_elements)

    response = trp.get_existing_path_elements(body)
    assert response == [
        {
            "PATH_NAME": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
            "PATH_Z_SITE": "AUSDTXIR-NSM DEV TESTING/HUB SITE/11921 N MOPAC EXPY",
            "PATH_STATUS": "Planned",
        }
    ]


@pytest.mark.unittest
def test_get_existing_transports_none(monkeypatch):
    body = transport_path_data.mock_payload()
    monkeypatch.setattr(trp, "get_circuit_path_info", transport_path_data.mock_circuit_path_data)
    monkeypatch.setattr(
        trp, "get_circuit_site_info", lambda *args, **kwargs: transport_path_data.mock_no_granite_records()
    )

    response = trp.get_existing_transports(body)
    assert response is None


@pytest.mark.unittest
def test_get_existing_transports_no_match(monkeypatch):
    body = transport_path_data.mock_payload()
    monkeypatch.setattr(trp, "get_circuit_path_info", transport_path_data.mock_circuit_path_data)
    monkeypatch.setattr(
        trp, "get_circuit_site_info", lambda *args, **kwargs: transport_path_data.mock_no_matching_transports()
    )

    response = trp.get_existing_transports(body)
    assert response is None


@pytest.mark.unittest
def test_get_existing_transports_match(monkeypatch):
    body = transport_path_data.mock_payload()
    monkeypatch.setattr(trp, "get_circuit_path_info", transport_path_data.mock_circuit_path_data)
    monkeypatch.setattr(
        trp, "get_circuit_site_info", lambda *args, **kwargs: transport_path_data.mock_matching_transports()
    )
    monkeypatch.setattr(trp, "use_existing_transport", lambda *args, **kwargs: False)

    response = trp.get_existing_transports(body)
    assert response == {"transport_path": "83001.GE1.MRFLTX230QW.BURNTX153ZW", "transport_status": "Planned"}


@pytest.mark.unittest
def test_get_circuit_path_info(monkeypatch):
    # circuit site info not found
    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: {"retString": "error"})

    with pytest.raises(Exception):
        assert (
            trp.get_circuit_path_info({"circuit_id": "cid", "service_location_address": "service_location_address"})
            is None
        )

    # multiple revisions
    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: ["1value", "2value"])

    with pytest.raises(Exception):
        assert (
            trp.get_circuit_path_info({"circuit_id": "cid", "service_location_address": "service_location_address"})
            is None
        )

    # 1 revision
    granite_resp = [{"Z_CLLI": "target_clli", "Z_SITE_NAME": "service_location_address"}]
    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: granite_resp)

    assert trp.get_circuit_path_info({"circuit_id": "cid", "service_location_address": "service_location_address"}) == (
        "target_clli",
        "service_location_address",
        granite_resp[0],
    )


@pytest.mark.unittest
def test_convert_bandwidth():
    bw_type = "mbps"
    bw_value = "50"
    bandwidth_string, optic, card_template = trp.convert_bandwidth(bw_type, bw_value, False)
    assert bandwidth_string == "1 Gbps"
    assert optic == "GE"
    assert card_template == "GENERIC SFP LEVEL 1"


@pytest.mark.unittest
def test_create_transport_path_main(monkeypatch):
    body = transport_path_data.mock_payload_5gbps()

    # MTU 1AW shelf error
    body["build_type"] = "MTU"
    monkeypatch.setattr(trp, "get_circuit_path_info", transport_path_data.mock_circuit_path_data)
    monkeypatch.setattr(trp, "get_aw_shelf", lambda *args, **kwargs: "shelf")

    with pytest.raises(Exception):
        assert trp.create_transport_path_main(body, attempt_onboarding=True) is None

    # MTU shelf good, uplink_port error
    monkeypatch.setattr(trp, "get_aw_shelf", lambda *args, **kwargs: "shelf1AW")
    monkeypatch.setattr(trp, "find_or_create_mtu_site", lambda *args, **kwargs: "transport_z_site")
    monkeypatch.setattr(trp, "get_npa", lambda *args, **kwargs: "512")

    monkeypatch.setattr(trp, "_get_next_available_port", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert trp.create_transport_path_main(body, attempt_onboarding=True) is None

    # CTBH not shelf, uplink_port good
    body["build_type"] = ""
    body["product_name_order_info"] = "CTBH"

    monkeypatch.setattr(trp, "_get_next_available_port", transport_path_data.mock_1gbps_qfx_port)
    monkeypatch.setattr(trp, "get_existing_ctbh_cpe_shelf", lambda *args, **kwargs: {})
    monkeypatch.setattr(trp, "get_equipment_buildout_v2", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert trp.create_transport_path_main(body, attempt_onboarding=True) is None

    # CTBH shelf good and existing_path_elements
    monkeypatch.setattr(trp, "get_equipment_buildout_v2", lambda *args, **kwargs: {})
    monkeypatch.setattr(trp, "check_transport_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "_create_transport_path_at_granite", lambda *args, **kwargs: None)

    monkeypatch.setattr(trp, "get_transport_path_data", transport_path_data.mock_get_transport_path_data)
    monkeypatch.setattr(trp, "_reserve_port_on_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "get_existing_path_elements", lambda *args, **kwargs: "existing_path_elements")

    with pytest.raises(Exception):
        assert trp.create_transport_path_main(body, attempt_onboarding=True) == "51001.GE10.AUSBTX500QW.AUSZTXOC2ZW"

    # not CTBH and bad shelf
    body["product_name_order_info"] = ""

    monkeypatch.setattr(trp, "get_existing_shelf", lambda *args, **kwargs: [{"EQUIP_VENDOR": ""}])

    with pytest.raises(Exception):
        assert trp.create_transport_path_main(body, attempt_onboarding=True) is None

    # "EQUIP_VENDOR": "CRADLEPOINT" and NOT existing_path_elements
    monkeypatch.setattr(trp, "get_existing_shelf", lambda *args, **kwargs: [{"EQUIP_VENDOR": "CRADLEPOINT"}])
    monkeypatch.setattr(trp, "get_next_available_zw_shelf", lambda *args, **kwargs: "AUSZTXOC2ZW")

    monkeypatch.setattr(trp, "get_existing_path_elements", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "granite_add_path_elements", lambda *args, **kwargs: None)

    assert trp.create_transport_path_main(body, attempt_onboarding=True) == "51001.GE10.AUSBTX500QW.AUSZTXOC2ZW"


@pytest.mark.unittest
def test_filter_edr(monkeypatch):
    # no new ports
    port_list = [{"EQUIP_NAME": "LSAICAEV1QW/000.0000.000.00/SWT#1"}]
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: None)
    assert trp.filter_edr(port_list) == port_list

    # no transport path found for tid
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: {})
    assert trp.filter_edr(port_list) == port_list

    # new ports
    monkeypatch.setattr(
        trp,
        "get_granite",
        lambda *args, **kwargs: [{"CIRCUIT_NAME": "31001.GE40L.LSAICAEV1CW.LSAICAEV1QW", "A_CLLI": "LSAICAEV"}],
    )
    monkeypatch.setattr(trp, "edna_check_w_equipid", lambda *args, **kwargs: True)
    assert trp.filter_edr(port_list) == port_list


@pytest.mark.unittest
def test_edna_check_w_equipid(monkeypatch):
    # no device UDAs
    monkeypatch.setattr(trp, "get_equipid", lambda *args, **kwargs: None)
    assert trp.edna_check_w_equipid("equip_name") is False

    # no shelf UDAs
    monkeypatch.setattr(trp, "get_equipid", lambda *args, **kwargs: [{"EQUIP_INST_ID": "123"}])
    monkeypatch.setattr(trp, "get_shelf_udas", lambda *args, **kwargs: None)
    assert trp.edna_check_w_equipid("equip_name") is False

    # no network role
    monkeypatch.setattr(trp, "get_shelf_udas", lambda *args, **kwargs: [])
    assert trp.edna_check_w_equipid("equip_name") is False

    # "ENTERPRISE DISTRIBUTION ROUTER" in a_network_role
    monkeypatch.setattr(trp, "get_shelf_udas", lambda *args, **kwargs: [{"ATTR_NAME": "NETWORK", "ATTR_VALUE": "EDNA"}])
    assert trp.edna_check_w_equipid("equip_name") is True


@pytest.mark.unittest
def test_get_order_account_id(monkeypatch):
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: [{"orderingCustomer": "orderingCustomer"}])
    assert trp.get_order_account_id("cid") == "orderingCustomer"

    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: {})

    with pytest.raises(AbortException):
        assert trp.get_order_account_id("cid") is None


@pytest.mark.unittest
def test_create_circuit_path_data(monkeypatch):
    granite_resp = [
        {
            "Z_SITE_NAME": "Z_SITE_NAME",
            "CIRC_PATH_INST_ID": "CIRC_PATH_INST_ID",
            "LEG_NAME": "LEG_NAME",
            "LEG_INST_ID": "LEG_INST_ID",
            "Z_CLLI": "Z_CLLI",
        }
    ]
    circuit_path_data = {
        "z_site_name": "Z_SITE_NAME",
        "CIRC_PATH_INST_ID": "CIRC_PATH_INST_ID",
        "leg_name": "LEG_NAME",
        "leg_inst_id": "LEG_INST_ID",
        "z_clli": "Z_CLLI",
        "a_site_name": "",
        "A_ADDRESS": "",
        "Z_ADDRESS": "",
    }
    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: granite_resp)
    assert trp.create_circuit_path_data("cid") == circuit_path_data

    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: (_ for _ in ()).throw(KeyError))

    with pytest.raises(Exception):
        assert trp.create_circuit_path_data("cid") is None

    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: (_ for _ in ()).throw(Exception))

    with pytest.raises(Exception):
        assert trp.create_circuit_path_data("cid") is None


@pytest.mark.unittest
def test_get_transport_path_data(monkeypatch):
    granite_resp = [
        {
            "CIRC_PATH_INST_ID": "CIRC_PATH_INST_ID",
            "LEG_NAME": "LEG_NAME",
            "LEG_INST_ID": "LEG_INST_ID",
            "Z_SITE_NAME": "Z_SITE_NAME",
        }
    ]
    circuit_path_data = {
        "path_inst_id": "CIRC_PATH_INST_ID",
        "leg_name": "LEG_NAME",
        "leg_inst_id": "LEG_INST_ID",
        "z_site_name": "Z_SITE_NAME",
    }
    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: granite_resp)
    assert trp.get_transport_path_data("transport_path_name") == circuit_path_data

    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: (_ for _ in ()).throw(KeyError))

    with pytest.raises(Exception):
        assert trp.get_transport_path_data("transport_path_name") is None

    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: (_ for _ in ()).throw(Exception))

    with pytest.raises(Exception):
        assert trp.get_transport_path_data("transport_path_name") is None


@pytest.mark.unittest
def test_get_port_access_id():
    assert trp.get_port_access_id("1", "1#1") == "1/0/1"


@pytest.mark.unittest
def test_update_port_status(monkeypatch):
    monkeypatch.setattr(trp, "put_granite", lambda *args, **kwargs: None)
    assert trp.update_port_status("port_inst_id", "port_status") is None


@pytest.mark.unittest
def test_get_next_available_port(monkeypatch):
    port_dict = {
        "hub_clli_code": "test01",
        "bandwidth_type": "Gbps",
        "bandwidth_value": "1",
        "build_type_mtu": "build_type_mtu",
        "attempt_onboarding": "No",
        "cid": "circuit_id",
        "product": "FC + Remote PHY",
    }

    port_list = [
        {
            "PORT": "testport1",
            "MODEL": "ACX",
            "OPTIC_TEMPLATE": "GENERIC SFP LEVEL 1",
            "EQUIP_NAME": "testeq",
            "SLOT_INST_ID": "1234589",
            "VENDOR": "JUNIPER",
            "TYPE": "ROUTER",
            "PORT_INST_ID": "90876",
            "PORT_ACCESS_ID": "XE-0/0/1",
        }
    ]

    new_port_list = {
        "PORT": "testport1",
        "MODEL": "ACX",
        "OPTIC_TEMPLATE": "GENERIC SFP LEVEL 1",
        "EQUIP_NAME": "testeq",
        "SLOT_INST_ID": "1234589",
        "VENDOR": "JUNIPER",
        "TYPE": "ROUTER",
        "PORT_INST_ID": "90876",
        "PORT_ACCESS_ID": "XE-0/0/1",
    }

    monkeypatch.setattr(trp, "get_available_uplink_ports", lambda *args, **kwargs: port_list)
    monkeypatch.setattr(trp, "filter_rphy", lambda *args, **kwargs: port_list)
    monkeypatch.setattr(trp, "filter_edr", lambda *args, **kwargs: port_list)
    monkeypatch.setattr(trp, "check_equipment_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "port_available_on_network", lambda *args, **kwargs: True)
    monkeypatch.setattr(trp, "delete_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        trp, "get_equipment_buildout", lambda *args, **kwargs: [{"SLOT_INST_ID": "1234", "PORT_INST_ID": "5678"}]
    )
    monkeypatch.setattr(trp, "update_port_access_id", lambda *args, **kwargs: None)

    assert trp._get_next_available_port(port_dict) == new_port_list


@pytest.mark.unittest
def test_filter_rphy(monkeypatch):
    # bad test abort no rphy ports available
    port_list = [{"EQUIP_NAME": "LSAICAEV1QW/000.0000.000.00/SWT#1"}]
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert trp.filter_rphy(port_list, "cid") is None

    # good test found rphy on CW device
    granite_resp = [
        {"CIRCUIT_NAME": "31001.GE40L.LSAICAEV1CW.LSAICAEV1QW", "A_CLLI": "LSAICAEV", "LEG_NAME": "AE17/AE17 20G"}
    ]
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: granite_resp)
    monkeypatch.setattr(trp, "confirm_router_supports_rphy", lambda *args, **kwargs: True)
    assert trp.filter_rphy(port_list, "cid") == port_list


@pytest.mark.unittest
def test_account_id_match(monkeypatch):
    # good test return true orphan transport
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: {})

    assert trp.account_id_match("transport_path", "order_account_id") is True

    # good test return True acct id matches
    monkeypatch.setattr(
        trp,
        "get_granite",
        lambda *args, **kwargs: [{"NEXT_CUSTOMER": "order_account_id", "MEMBER_CUSTOMER": "order_account_id"}],
    )
    assert trp.account_id_match("transport_path", "order_account_id") is True


@pytest.mark.unittest
def test_check_equipment_status(monkeypatch):
    # bad test abort port in do not use status
    with pytest.raises(Exception):
        assert trp.check_equipment_status({"PORT_STATUS": "DO NOT USE"}) is None

    # bad test abort port[0] has bad status
    monkeypatch.setattr(trp, "get_equipment_buildout", lambda *args, **kwargs: [{"EQUIP_STATUS": "DO-NOT-USE"}])

    with pytest.raises(Exception):
        assert trp.check_equipment_status({"EQUIP_NAME": "TID/999/swt", "PORT_STATUS": "Live"}) is None


@pytest.mark.unittest
def test_check_transport_status(monkeypatch):
    # bad test abort do not use status
    monkeypatch.setattr(trp, "get_circuit_site_info", lambda *args, **kwargs: [{"CIRCUIT_STATUS": "DO-NOT-USE"}])

    with pytest.raises(Exception):
        assert trp.check_transport_status({"circuit_name"}) is None


@pytest.mark.unittest
def test_find_or_create_mtu_site(monkeypatch):
    # bad test abort fail on try except
    monkeypatch.setattr(trp, "get_sites", lambda *args, **kwargs: [{"bad_key": None}])

    with pytest.raises(Exception):
        assert trp.find_or_create_mtu_site({"clli"}) is None

    # bad test abort no building site
    monkeypatch.setattr(trp, "get_sites", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert trp.find_or_create_mtu_site({"clli"}) is None

    # good test return active mtu site name
    monkeypatch.setattr(trp, "get_sites", lambda *args, **kwargs: [{"siteType": "ACTIVE MTU", "siteName": "mysite"}])

    assert trp.find_or_create_mtu_site({"clli"}) == "mysite"

    # good test building create mtu site
    site = [
        {
            "siteType": "BUILDING",
            "siteName": "buildingsite",
            "clli": "myclli",
            "address": "512 address",
            "latitude": "123456",
            "longitude": "-123456",
            "zip1": "78728",
            "city": "mycity",
            "state": "mystate",
            "gemBuildingKeyUda": "67890",
        }
    ]

    monkeypatch.setattr(trp, "get_sites", lambda *args, **kwargs: site)
    monkeypatch.setattr(trp, "create_mtu_site", lambda *args, **kwargs: None)

    assert trp.find_or_create_mtu_site({"clli"}) == "myclli-MTU//512 address"


@pytest.mark.unittest
def test_create_transport_path_at_granite(monkeypatch):
    # good test build type mtu True
    monkeypatch.setattr(trp, "post_granite", lambda *args, **kwargs: None)

    assert trp._create_transport_path_at_granite("t_path_name", "100", "asite", "zsite", build_type_mtu=True) is None

    # good test build type mtu False
    assert trp._create_transport_path_at_granite("t_path_name", "100", "asite", "zsite", build_type_mtu=False) is None


@pytest.mark.unittest
def test_create_transport_path_at_granite_for_qc(monkeypatch):
    # good test create transport for quick connect
    monkeypatch.setattr(trp, "post_granite", lambda *args, **kwargs: None)

    assert trp._create_transport_path_at_granite_for_qc("t_path_name", "100", "asite", "zsite", "service_type") is None


@pytest.mark.unittest
def test_reserve_port_on_granite(monkeypatch):
    # good test port reserved in granite
    trans_path_data = {
        "transport_path_name": "t_path_name",
        "path_inst_id": "12345",
        "leg_name": "1",
        "leg_inst_id": "181812",
    }

    uplink_port = {"PORT_INST_ID": "121811"}
    monkeypatch.setattr(trp, "put_granite", lambda *args, **kwargs: None)

    assert trp._reserve_port_on_granite(trans_path_data, uplink_port) is None


@pytest.mark.unittest
def test_granite_add_path_elements(monkeypatch):
    # good test add path elements
    trans_path_data = {
        "transport_path_name": "t_path_name",
        "path_inst_id": "12345",
        "leg_name": "1",
        "leg_inst_id": "181812",
    }

    circuit_path_data = {"CIRC_PATH_INST_ID": "1218112"}
    monkeypatch.setattr(trp, "put_granite", lambda *args, **kwargs: None)

    assert trp.granite_add_path_elements("cid", circuit_path_data, trans_path_data) is None


@pytest.mark.unittest
def test_quick_connect_create_transport_path(monkeypatch):
    # bad test abort multiple devices
    monkeypatch.setattr(trp, "_get_parent_site", lambda *args, **kwargs: {"z_clli": "z_clli", "z_site_name": "site"})
    monkeypatch.setattr(trp, "get_existing_shelf", lambda *args, **kwargs: [{}, {}])

    with pytest.raises(Exception):
        assert trp.quick_connect_create_transport_path("cid", "1 Gbps") is None

    # bad test abort Equipment status not in good status
    resp = [{"EQUIP_STATUS": "bad status", "TARGET_ID": "TID", "EQUIP_VENDOR": "Juniper"}]
    monkeypatch.setattr(trp, "get_existing_shelf", lambda *args, **kwargs: resp)

    with pytest.raises(Exception):
        assert trp.quick_connect_create_transport_path("cid", "1 Gbps") is None

    # bad test abort Equipment vendor not a good vendor
    resp[0]["EQUIP_STATUS"] = "Live"

    with pytest.raises(Exception):
        assert trp.quick_connect_create_transport_path("cid", "1 Gbps") is None

    # bad test abort bad agg bandwidth value
    monkeypatch.setattr(trp, "get_existing_shelf", lambda *args, **kwargs: {})
    monkeypatch.setattr(trp, "get_next_zw_shelf", lambda *args, **kwargs: "next_zw_shelf")

    with pytest.raises(Exception):
        assert trp.quick_connect_create_transport_path("cid", "bad bw value") is None

    # bad test abort uplink port is None
    resp[0]["EQUIP_VENDOR"] = "RAD"
    monkeypatch.setattr(trp, "get_existing_shelf", lambda *args, **kwargs: resp)
    monkeypatch.setattr(trp, "get_qc_available_uplink_ports", lambda *args, **kwargs: "mtu ports")
    monkeypatch.setattr(trp, "get_qc_uplink_port_for_tp", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert trp.quick_connect_create_transport_path("cid", "1.0 Gbps") is None

    # good test juniper mtu port
    mtu_ports = [{"VENDOR": "JUNIPER"}]
    mtu_ports2 = [{"VENDOR": "JUNIPER", "EXPECTED_PAID": "XE-0/0/1"}]
    mtu_ports3 = [
        {
            "VENDOR": "JUNIPER",
            "EXPECTED_PAID": "XE-0/0/1",
            "PORT_INST_ID": "1234",
            "EQUIP_NAME": "myequip",
            "SITE_NAME": "sitename",
        }
    ]
    jun_mtu_ports = iter([mtu_ports, mtu_ports2, mtu_ports3])
    uplink = "0/0/1"
    monkeypatch.setattr(trp, "get_qc_available_uplink_ports", lambda *args, **kwargs: next(jun_mtu_ports))
    monkeypatch.setattr(trp, "get_qc_uplink_port_for_tp", lambda *args, **kwargs: uplink)
    monkeypatch.setattr(trp, "assign_card_qc", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "get_npa", lambda *args, **kwargs: "713")
    monkeypatch.setattr(trp, "put_port_access_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "create_circuit_path_data", lambda *args, **kwargs: {"z_site_name": "sitename"})
    monkeypatch.setattr(trp, "_create_transport_path_at_granite_for_qc", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        trp, "get_transport_path_data", lambda *args, **kwargs: {"transport_path_name": "71001.GE10.myequip.TID"}
    )
    monkeypatch.setattr(trp, "_reserve_port_on_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "update_port_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "granite_add_path_elements", lambda *args, **kwargs: None)

    assert trp.quick_connect_create_transport_path("cid", "1.0 Gbps") == "71001.GE10.myequip.TID"

    # good test mbps
    jun2_mtu_ports = iter([mtu_ports, mtu_ports2, mtu_ports3])
    monkeypatch.setattr(trp, "get_qc_available_uplink_ports", lambda *args, **kwargs: next(jun2_mtu_ports))

    assert trp.quick_connect_create_transport_path("cid", "100 Mbps") == "71001.GE1.myequip.TID"


@pytest.mark.unittest
def test_get_qc_uplink_port_for_tp(monkeypatch):
    # bad test abort ard template mismatch or no ports matched on Granite
    with pytest.raises(Exception):
        assert trp.get_qc_uplink_port_for_tp([{}], "zclli", "10 Gbps") is None

    # bad test abort no port on RAD
    mtu_ports = [
        {"CARD_TEMPLATE_NAME": "bad_card", "VENDOR": "ADVA"},
        {
            "CARD_TEMPLATE_NAME": "GENERIC SFP LEVEL 1",
            "VENDOR": "RAD",
            "EQUIP_NAME": "myequip",
            "EXPECTED_PAID": "0/0/2",
            "MODEL": "EX-4200",
        },
    ]

    monkeypatch.setattr(trp, "qc_port_available_on_network", lambda *args, **kwargs: {})
    monkeypatch.setattr(trp, "qc_port_for_rad", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") is None

    # good test port return on RAD
    monkeypatch.setattr(trp, "qc_port_for_rad", lambda *args, **kwargs: "0/0/1")

    assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") == "0/0/1"

    # bad test abort no port on ADVA
    mtu_ports[1]["VENDOR"] = "ADVA"

    monkeypatch.setattr(trp, "qc_port_for_adva", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") is None

    # good test port return on ADVA
    monkeypatch.setattr(trp, "qc_port_for_adva", lambda *args, **kwargs: "1-1-1-3")

    assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") == "1-1-1-3"

    # bad test no port return on Juniper try except
    mtu_ports[1]["VENDOR"] = "JUNIPER"

    monkeypatch.setattr(trp, "qc_port_available_on_network", lambda *args, **kwargs: None)

    assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") is None

    # good test port return on juniper
    network_port = {"result": {"data": {"configuration": ""}}}
    monkeypatch.setattr(trp, "qc_port_available_on_network", lambda *args, **kwargs: network_port)
    monkeypatch.setattr(trp, "underlay_topology_model_available_handoffs", lambda *args, **kwargs: ["0/0/1", "0/0/2"])

    assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") == "0/0/2"

    # bad test no port return on Juniper
    monkeypatch.setattr(trp, "underlay_topology_model_available_handoffs", lambda *args, **kwargs: ["0/0/1"])

    with pytest.raises(Exception):
        assert trp.get_qc_uplink_port_for_tp(mtu_ports, "zclli", "1 Gbps") is None


@pytest.mark.unittest
def test_underlay_topology_model_available_handoffs(monkeypatch):
    # good test RAD
    UNDERLAY_PAYLOAD = {
        "uplink": {"slot": "LAN 1", "template": "template", "port_access_id": "port_access_id"},
        "secondary": {"slot": "LAN 1", "template": "template", "port_access_id": "port_access_id"},
        "handoff": {"slot": "LAN 1", "template": "template", "port_access_id": "port_access_id", "connector": "RJ-45"},
        "vendor": "VENDOR",
    }

    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)
    monkeypatch.setattr(trp, "UnderlayDeviceTopologyModel", lambda *args, **kwargs: device_topology)

    assert trp.underlay_topology_model_available_handoffs("203AX", "1 Gbps", "RAD") == ["eth-4/1", "0/0/1"]

    # good test ADVA
    assert trp.underlay_topology_model_available_handoffs("116pro", "1 Gbps", "ADVA") == ["eth-4/2", "0/0/2"]

    # good test JUNIPER
    assert trp.underlay_topology_model_available_handoffs("EX-4200", "1 Gbps", "JUNIPER") == ["eth-4/2", "0/0/2"]


@pytest.mark.unittest
def test_get_existing_path_elements_for_qc(monkeypatch):
    # bad test exception return None
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: "")

    assert trp.get_existing_path_elements_for_qc("cid") is None

    # good test no path z side site return None
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: [{}])

    assert trp.get_existing_path_elements_for_qc("cid") is None

    # good test path z side site return resp
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: [{"PATH_Z_SITE": "zsite"}])

    assert trp.get_existing_path_elements_for_qc("cid") == [{"PATH_Z_SITE": "zsite"}]


@pytest.mark.unittest
def test_assign_card_qc(monkeypatch):
    # good test return None
    mtu_ports = {"EQUIP_NAME": "TID", "CARD_TEMPLATE_NAME": "SFP+", "SLOT_INST_ID": "12345"}

    monkeypatch.setattr(trp, "_card_the_slot", lambda *args, **kwargs: None)

    assert trp.assign_card_qc(mtu_ports) is None


@pytest.mark.unittest
def test_lookup_hub_clli(monkeypatch):
    # bad test abort clli less that 3 characters.
    with pytest.raises(Exception):
        assert trp.lookup_hub_clli("MBM") is None

    # bad test abort clli len not == to 8
    monkeypatch.setattr(trp, "get_hub_site", lambda *args, **kwargs: "MILESBADZW")

    with pytest.raises(Exception):
        assert trp.lookup_hub_clli("MILES") is None

    # good test 8 char clli
    monkeypatch.setattr(trp, "get_hub_site", lambda *args, **kwargs: "MILES1CW")

    assert trp.lookup_hub_clli("MILES") == "MILES1CW"


@pytest.mark.unittest
def test_card_the_slot(monkeypatch):
    # bad test abort no data from granite
    monkeypatch.setattr(trp, "post_granite", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert trp._card_the_slot({"0/0/1", "0/0/2"}) is None

    # bad test abort missing card added in retSting from granite
    monkeypatch.setattr(trp, "post_granite", lambda *args, **kwargs: {"retString": "not added", "httpCode": "200"})

    with pytest.raises(Exception):
        assert trp._card_the_slot({"0/0/1", "0/0/2"}) is None

    # bad test abort on exception try except missing http code
    monkeypatch.setattr(trp, "post_granite", lambda *args, **kwargs: {"retString": "not added"})

    with pytest.raises(Exception):
        assert trp._card_the_slot({"0/0/1", "0/0/2"}) is None


@pytest.mark.unittest
def test_get_parent_site(monkeypatch):
    # bad test abort index error try except
    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert trp._get_parent_site("cid") is None

    # bad test abort missing keys in res from granite get call
    res = [
        {
            "CIRC_PATH_INST_ID": "1234",
            "Z_ADDRESS": "zadress",
            "Z_CITY": "zcity",
            "Z_STATE": "zstate",
            "Z_ZIP": "zzip",
            "LEG_NAME": "1",
            "LEG_INST_ID": "4567",
            "Z_SITE_NAME": "zsite",
        }
    ]

    monkeypatch.setattr(trp, "get_granite", lambda *args, **kwargs: res)

    with pytest.raises(Exception):
        assert trp._get_parent_site("cid") is None

    # good test return csip values
    res[0]["Z_CLLI"] = "zclli"
    res[0]["A_CLLI"] = "aclli"
    res[0]["A_SITE_NAME"] = "asite"

    csip_vals = {
        "circ_path_inst_id": "1234",
        "z_address": "zadress",
        "z_city": "zcity",
        "z_state": "zstate",
        "z_zip": "zzip",
        "leg_name": "1",
        "leg_inst_id": "4567",
        "z_site_name": "zsite",
        "z_clli": "zclli",
        "a_site_name": "asite",
        "a_clli": "aclli",
    }

    assert trp._get_parent_site("cid") == csip_vals


@pytest.mark.unittest
def test_use_existing_transport(monkeypatch):
    # good test return none
    body = {"bandwidth_value": "1", "bandwidth_type": "Gbps", "circuit_id": "cid"}

    monkeypatch.setattr(trp, "bandwidth_in_bps", lambda *args, **kwargs: 1000)
    monkeypatch.setattr(trp, "will_transport_be_oversubscribed", lambda *args, **kwargs: False)
    monkeypatch.setattr(trp, "get_order_account_id", lambda *args, **kwargs: "acct-123456")
    monkeypatch.setattr(trp, "account_id_match", lambda *args, **kwargs: False)

    assert trp.use_existing_transport(body, "21001.GE10.austin091QW.austin091ZW") is None

    # good test return transport path
    monkeypatch.setattr(trp, "account_id_match", lambda *args, **kwargs: True)
    monkeypatch.setattr(trp, "check_transport_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(trp, "create_circuit_path_data", lambda *args, **kwargs: "circuit_path_data")
    monkeypatch.setattr(trp, "get_transport_path_data", lambda *args, **kwargs: "transport_path_data")
    monkeypatch.setattr(trp, "granite_add_path_elements", lambda *args, **kwargs: None)

    assert trp.use_existing_transport(body, "21001.GE10.austin091QW.austin091ZW") == "21001.GE10.austin091QW.austin091ZW"
