import pytest
from pytest import raises

import arda_app.bll.cpe_swap.cpe_swap_main as csm


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

    def set_handoff(*args):
        return


device = {
    "role": "cpe",
    "device_bw": "1 Gbps",
    "uplink": portmodel,
    "model": "ARC CBA850",
    "connector_type": "LC",
    "vendor": "CHTR",
    "device_template": "ETX203AX/2SFP/2UTP2SFP",
    "handoff": portmodel,
}

mock_payload = MockResponse(**device)


@pytest.mark.skip
def test_cid_revision_check(monkeypatch):
    monkeypatch.setattr(csm, "get_granite", lambda *args: [1, 2])

    with raises(Exception):
        assert csm._cid_revision_check("cid") is None

    monkeypatch.setattr(csm, "get_granite", lambda *args: [1])
    assert csm._cid_revision_check("cid") is None


@pytest.mark.skip
def test_l1_l2_evp_check():
    with raises(Exception):
        assert csm._l1_l2_evp_check([{"PORT_ROLE": "UNI-EVP"}], "tid") is None

    with raises(Exception):
        assert csm._l1_l2_evp_check([{"PORT_ROLE": 1}], "tid") is None

    with raises(Exception):
        assert csm._l1_l2_evp_check([{"LVL": 1}, {"LVL": 2}], "tid") is None

    assert csm._l1_l2_evp_check([{"LVL": "1"}, {"LVL": "2"}], "tid") is None


@pytest.mark.skip
def test_get_mdso_resource_id(monkeypatch):
    monkeypatch.setattr(
        csm,
        "get_resource_id_from_tid",
        lambda *args: [
            {"orchState": "active", "properties": {"communicationState": "AVAILABLE"}, "providerResourceId": "1234"}
        ],
    )
    assert csm._get_mdso_resource_id("tid") == "1234"

    monkeypatch.setattr(csm, "get_resource_id_from_tid", lambda *args: [])
    assert csm._get_mdso_resource_id("tid") is None


@pytest.mark.skip
def test_get_interface_descriptions_from_network(monkeypatch):
    monkeypatch.setattr(csm, "_show_1g_adva_ports", lambda *args, **kwargs: None)
    monkeypatch.setattr(csm, "_show_10g_adva_flows", lambda *args, **kwargs: None)
    monkeypatch.setattr(csm, "_show_rad_ports", lambda *args, **kwargs: None)
    assert csm._get_interface_descriptions_from_network("ADVA", "model114", "resource_id") is None
    assert csm._get_interface_descriptions_from_network("ADVA", "model", "resource_id") is None
    assert csm._get_interface_descriptions_from_network("RAD", "model", "resource_id") is None
    assert csm._get_interface_descriptions_from_network("test", "model", "resource_id") is None


@pytest.mark.skip
def test_transport_channel_validation(monkeypatch):
    channel_availability_resp = [
        {"CHAN_INST_ID": "123456", "MEMBER_PATH": "21.test..chtr", "NEXT_PATH": "21.test..chtr"},
        {"CHAN_INST_ID": "654321", "MEMBER_PATH": "21.test2..chtr", "NEXT_PATH": "21.test2..chtr"},
    ]

    cpe_path_elements = [
        {"PATH_NAME": "21.test..chtr", "PATH_REV": "1", "PORT_ACCESS_ID": "ETH-1-1-1-3"},
        {"PATH_NAME": "21.test2..chtr", "PATH_REV": "1", "PORT_ACCESS_ID": "ETH-1-1-1-4"},
    ]

    monkeypatch.setattr(csm, "get_granite", lambda *args: channel_availability_resp)
    monkeypatch.setattr(csm, "_cid_revision_check", lambda *args: None)
    monkeypatch.setattr(csm, "get_path_elements", lambda *args: cpe_path_elements)
    monkeypatch.setattr(csm, "_l1_l2_evp_check", lambda *args: None)
    monkeypatch.setattr(csm, "_uplink_handoff_values", lambda *args, **kwargs: None)
    monkeypatch.setattr(csm, "_granite_create_circuit_revision", lambda *args: (None, "rev_instance", None))
    monkeypatch.setattr(csm, "_create_path_put_payloads", lambda *args, **kwargs: ("cid_put_payload_remove_lvl1", None))
    monkeypatch.setattr(csm, "put_granite", lambda *args: None)

    assert csm._transport_channel_validation("transport_id", "123456", "cid", "tid", "vendor", "model", True, None) == (
        {
            "21.test2..chtr": [
                None,
                [
                    {"PATH_NAME": "21.test..chtr", "PATH_REV": "1", "PORT_ACCESS_ID": "ETH-1-1-1-3"},
                    {"PATH_NAME": "21.test2..chtr", "PATH_REV": "1", "PORT_ACCESS_ID": "ETH-1-1-1-4"},
                ],
                "ETH-1-1-1-3",
            ]
        },
        None,
    )


@pytest.mark.skip
def test_uplink_handoff_values(monkeypatch):
    cpe_path_elements = [{"MODEL": "model", "VENDOR": "vendor"}, {"MODEL": "model", "VENDOR": "vendor"}]
    monkeypatch.setattr(csm, "_existing_port_vlan_info", lambda *args: "_existing_port_vlan_info")
    assert csm._uplink_handoff_values(cpe_path_elements, True) == ("model", "vendor", None, "_existing_port_vlan_info")

    assert csm._uplink_handoff_values(cpe_path_elements, True, True) == (
        "model",
        "vendor",
        "_existing_port_vlan_info",
        "_existing_port_vlan_info",
    )


@pytest.mark.skip
def test_build_create_shelf_post_payload():
    cpe_path_elements = {"A_SITE_NAME": "A_SITE_NAME", "IPV4_ADDRESS": "IPV4_ADDRESS"}
    payload = {
        "new_vendor": "ADVA",
        "transport_10G": "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW",
        "path_inst_id": "path_inst_id",
    }
    assert csm._build_create_shelf_post_payload(cpe_path_elements, payload, "template", "legacy_source") == {
        "SHELF_NAME": "BFLRNYZV3ZW/999.9999.999.99/SWT",
        "SHELF_TEMPLATE": "template",
        "SITE_NAME": "A_SITE_NAME",
        "SHELF_FQDN": "BFLRNYZV3ZW.CML.CHTRSE.COM",
        "UDA": {
            "Purchase Info": {"PURCHASING GROUP": "ENTERPRISE"},
            "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            "Device Info": {"NETWORK ROLE": "CUSTOMER PREMISE EQUIPMENT"},
            "Device Config-Equipment": {"TARGET ID (TID)": "BFLRNYZV3ZW", "IPv4 ADDRESS": "IPV4_ADDRESS"},
            "LEGACY_EQUIPMENT": {"SOURCE": "legacy_source"},
        },
    }


@pytest.mark.skip
def test_build_put_add_payload():
    cpe_path_elements = {
        "PATH_NAME": "PATH_NAME",
        "LEG_NAME": "1",
        "LEG_INST_ID": "LEG_INST_ID",
        "SEQUENCE": "SEQUENCE",
        "CIRC_PATH_INST_ID": "CIRC_PATH_INST_ID",
    }
    get_equip_buildout_resp = [{"PORT_INST_ID": "PORT_INST_ID"}]
    assert csm._build_put_add_payload(cpe_path_elements, get_equip_buildout_resp, "new_inst_id") == {
        "PATH_NAME": "PATH_NAME",
        "PATH_INST_ID": "new_inst_id",
        "LEG_NAME": "1",
        "PATH_LEG_INST_ID": "LEG_INST_ID",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "SEQUENCE",
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "PORT_INST_ID": "PORT_INST_ID",
    }


@pytest.mark.skip
def test_build_ports_put_payload():
    vlan_info = {
        "c_vlan": "c_vlan",
        "cust_s_vlan": "cust_s_vlan",
        "vlan_operation": "vlan_operation",
        "s_vlan": "s_vlan",
        "port_role": "port_role",
    }
    assert csm._build_ports_put_payload("port_inst_id", "port_access_id", vlan_info) == {
        "PORT_INST_ID": "port_inst_id",
        "PORT_ACCESS_ID": "port_access_id",
        "PORT_STATUS": "Assigned",
        "UDA": {
            "VLAN INFO": {
                "BUNDLED C-VLAN": "c_vlan",
                "CUSTOMER S-VLAN": "cust_s_vlan",
                "INCOMING VLAN OPERATION": "vlan_operation",
                "S-VLAN": "s_vlan",
                "PORT-ROLE": "port_role",
            }
        },
    }


@pytest.mark.skip
def test_existing_port_vlan_info():
    cpe_path_elements = {
        "C_VLAN": "C_VLAN",
        "CUST_S_VLAN": "CUST_S_VLAN",
        "S_VLAN": "S_VLAN",
        "VLAN_OPERATION": "VLAN_OPERATION",
        "PORT_ROLE": "PORT_ROLE",
    }
    assert csm._existing_port_vlan_info(cpe_path_elements) == {
        "c_vlan": "C_VLAN",
        "cust_s_vlan": "CUST_S_VLAN",
        "s_vlan": "S_VLAN",
        "vlan_operation": "VLAN_OPERATION",
        "port_role": "PORT_ROLE",
    }


@pytest.mark.skip
def test_remove_ports_from_path(monkeypatch):
    monkeypatch.setattr(
        csm,
        "_create_path_put_payloads",
        lambda *args: ("cid_put_payload_remove_lvl1", "transport_put_payload_remove_lvl2"),
    )
    monkeypatch.setattr(csm, "put_granite", lambda *args: None)
    assert csm._remove_ports_from_path("cpe_path_elements", False) is None


@pytest.mark.skip
def test_delete_shelf(monkeypatch):
    cpe_path_elements = [{"ELEMENT_REFERENCE": "ELEMENT_REFERENCE", "ELEMENT_STATUS": "Live"}]
    monkeypatch.setattr(csm, "delete_granite", lambda *args: None)
    assert csm._delete_shelf(cpe_path_elements) is None


@pytest.mark.skip
def test_create_shelf(monkeypatch):
    cpe_path_elements = [{1: 1}]
    monkeypatch.setattr(csm, "_build_create_shelf_post_payload", lambda *args: "create_shelf_payload")
    monkeypatch.setattr(csm, "post_granite", lambda *args: "create_shelf_resp")
    assert csm._create_shelf("args", cpe_path_elements, "new_model_template", "legacy_source") == (
        "create_shelf_payload",
        "create_shelf_resp",
    )


@pytest.mark.skip
def test_uplink_card_and_paid(monkeypatch):
    get_uplink_equip_buildout_resp = [{"SLOT_INST_ID": "1234567", "PORT_INST_ID": "ETH-1-1-1-8"}]
    monkeypatch.setattr(csm, "get_equipment_buildout", lambda *args: get_uplink_equip_buildout_resp)
    monkeypatch.setattr(csm, "post_granite", lambda *args: None)
    monkeypatch.setattr(csm, "_build_ports_put_payload", lambda *args: "uplink_put_ports_payload")
    monkeypatch.setattr(csm, "put_granite", lambda *args: None)

    assert (
        csm._uplink_card_and_paid(
            {"device_tid": "TEST1ZW"},
            "equip_buildout",
            {"SHELF_NAME": "test2ZW"},
            mock_payload,
            "existing_uplink_vlan_info",
        )
        == get_uplink_equip_buildout_resp
    )


@pytest.mark.skip
def test_handoff_get_equipment_buildout(monkeypatch):
    get_handoff_equip_buildout_resp = [
        {"SLOT_INST_ID": "1234589", "PORT_INST_ID": "ETH-1-1-1-3", "CARD_TEMPLATE": "CARD"}
    ]
    monkeypatch.setattr(csm, "get_equipment_buildout", lambda *args: get_handoff_equip_buildout_resp)

    assert csm._handoff_get_equipment_buildout(mock_payload, "TID", True) == (
        get_handoff_equip_buildout_resp,
        "CARD",
        "SLOT=NET 1",
    )

    assert csm._handoff_get_equipment_buildout(mock_payload, "TID") == (
        get_handoff_equip_buildout_resp,
        "CARD",
        "PORT_ACCESS_ID=ETH PORT 1",
    )


@pytest.mark.skip
def test_set_handoff_card_template(monkeypatch):
    create_shelf_payload = {"SHELF_NAME": "test1zw"}
    monkeypatch.setattr(csm, "post_granite", lambda *args: None)
    monkeypatch.setattr(csm, "get_equipment_buildout", lambda *args: "get_handoff_equip_buildout_resp")

    assert (
        csm._set_handoff_card_template(
            create_shelf_payload, mock_payload, "TID", "equip_build", [{"SLOT_INST_ID": "1234590"}]
        )
        == "get_handoff_equip_buildout_resp"
    )


@pytest.mark.skip
def test_set_handoff_paid(monkeypatch):
    monkeypatch.setattr(csm, "put_granite", lambda *args: None)
    monkeypatch.setattr(csm, "_build_ports_put_payload", lambda *args: "handoff_put_ports_payload")

    assert csm._set_handoff_paid([{"PORT_INST_ID": "1234590"}], mock_payload, "VLAN_INFO") is None


@pytest.mark.skip
def test_create_path_put_payloads():
    cpe_path_elements = [
        {
            "PATH_NAME": "PATH_NAME",
            "CIRC_PATH_INST_ID": "CIRC_PATH_INST_ID",
            "LEG_NAME": "LEG_NAME",
            "REMOVE_ELEMENT": "true",
            "SEQUENCE": "SEQUENCE",
        },
        {
            "PATH_NAME": "PATH_NAME",
            "CIRC_PATH_INST_ID": "CIRC_PATH_INST_ID",
            "LEG_NAME": "LEG_NAME",
            "REMOVE_ELEMENT": "true",
            "SEQUENCE": "SEQUENCE",
        },
    ]

    path_put_payload_lvl = {
        "PATH_NAME": "PATH_NAME",
        "PATH_INST_ID": "CIRC_PATH_INST_ID",
        "LEG_NAME": "LEG_NAME",
        "REMOVE_ELEMENT": "true",
        "ELEMENTS_TO_REMOVE": "SEQUENCE",
    }

    assert csm._create_path_put_payloads(cpe_path_elements, True) == (None, path_put_payload_lvl)

    assert csm._create_path_put_payloads(cpe_path_elements, False) == (path_put_payload_lvl, path_put_payload_lvl)


@pytest.mark.skip
def test_cpe_swap_main(monkeypatch):
    cpe_swap_payload = {
        "cid": "93.L1XX.004785..CHTR",
        "device_tid": "TEST1ZW",
        "new_vendor": "ADVA",
        "path_inst_id": "123456",
        "trans_inst_id": "876543",
        "transport_10G": "pathId_10G",
    }
    monkeypatch.setattr(csm, "get_path_elements", lambda *args: cpe_swap_payload)
