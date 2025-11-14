import pytest
from pytest import raises

import arda_app.bll.net_new.create_cpe as cp
from common_sense.common.errors import AbortException
from arda_app.bll.models.device_topology import ADVA_114PRO_1G, CRADLEPOINT_ARC, RAD_203AX_1G


from copy import deepcopy
from pydantic import BaseModel
from typing import Optional


PAYLOAD = {
    "cid": "cid",
    "product_name": "Wireless Internet Access-Primary",
    "service_type": "net_new_cj",
    "service_code": "RW700",
    "legacy_company": "Charter",
    "build_type": "STU (Single Tenant Unit)",
    "role": "cpe",
    "side": "a_side",
    "connector_type": "RJ45",
    "uni_type": "Access",
    "third_party_provided_circuit": "Y",
}

UNDERLAY_PAYLOAD = {
    "uplink": {"slot": "LAN 1", "template": "template", "port_access_id": "port_access_id"},
    "secondary": {"slot": "LAN 1", "template": "template", "port_access_id": "port_access_id"},
    "handoff": {"slot": "LAN 1", "template": "template", "port_access_id": "port_access_id", "connector": "RJ-45"},
    "vendor": "VENDOR",
}

EQUIPMENT_DATA = {
    "SLOT": "LAN 1",
    "EQUIP_STATUS": "Planned",
    "PORT_NAME": "LAN 1",
    "PORT_INST_ID": "PORT_INST_ID",
    "PORT_ACCESS_ID": "port_access_id",
    "EQUIP_NAME": "EQUIP_NAME",
    "SLOT_INST_ID": "SLOT_INST_ID",
    "CARD_TEMPLATE": "CARD_TEMPLATE",
}


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
    device_template: str = RAD_203AX_1G
    vendor: str = "VENDOR"

    def set_handoff(*args, **kwargs):
        return


@pytest.mark.unittest
def test_create_cpe_shelf(monkeypatch):
    shelf_payload = deepcopy(PAYLOAD)
    payload = shelf_payload

    resp = {
        "cpe_shelf": "tid/999.9999.999.99/RTR",
        "cpe_tid": "tid",
        "cpe_uplink": "port_inst_id",
        "cpe_handoff": "cpe_handoff_pid",
        "cpe_handoff_paid": "port_access_id",
        "zw_path": "ELEMENT_REFERENCE",
        "circ_path_inst_id": "CIRC_PATH_INST_ID",
    }

    # Fiber Internet Access
    # type2 == "Y"
    # uni_type in ("N/A"
    # "ELEMENT_CATEGORY" != "ETHERNET TRANSPORT"
    cpe_trans = {"ELEMENT_CATEGORY": "TRANSPORT"}

    payload["product_name"] = "Fiber Internet Access"
    payload["uni_type"] = "N/A"
    payload["model"] = "FSP 150-GE114PRO-C"

    monkeypatch.setattr(cp, "check_and_add_existing_transport", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "get_type2_path_elements_data", lambda *args, **kwargs: (cpe_trans, None))

    with raises(KeyError):
        assert cp.create_cpe_shelf(payload) is None

    # "FC + Remote PHY":
    # "BANDWIDTH"="1 Gbps"
    payload["product_name"] = "FC + Remote PHY"

    cpe_trans = {
        "BANDWIDTH": "1 Gbps",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_NAME": "QW.ZW",
        "SEQUENCE": "1",
        "PATH_A_SITE": "PATH_A_SITE",
        "PATH_Z_SITE": "PATH_Z_SITE",
    }
    monkeypatch.setattr(cp, "get_path_elements_data", lambda *args, **kwargs: (cpe_trans, None))

    with raises(AbortException):
        assert cp.create_cpe_shelf(payload) is None

    # "BANDWIDTH"="5 Gbps"
    # model == "FSP 150-GE114PRO-C"
    cpe_trans["BANDWIDTH"] = "5 Gbps"
    monkeypatch.setattr(cp, "_check_existing_cpe", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "wia_check", lambda *args, **kwargs: "memyitid1zw")
    monkeypatch.setattr(
        cp,
        "get_equipment_buildout_v2",
        lambda *args, **kwargs: [{"EQUIP_STATUS": "Planned", "SITE_NAME": "not the same"}],
    )

    with raises(AbortException):
        assert cp.create_cpe_shelf(payload) is None

    # Invalid device bandwidth
    monkeypatch.setattr(cp, "_check_existing_cpe", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "get_device_bw", lambda *args, **kwargs: None)

    with raises(AbortException):
        assert cp.create_cpe_shelf(payload) is None

    # bad equip_status third_party_provided_circuit = "N"
    payload["product_name"] = "Fiber Internet Access"
    payload["third_party_provided_circuit"] = "N"
    payload["side"] = "z_side"

    cpe_trans["ELEMENT_NAME"] = "AUSWTXMA2AW"
    cpe_trans["SEQUENCE"] = "1"
    cpe_trans["PATH_Z_SITE"] = "PATH_Z_SITE"

    cpe_site = [{"EQUIP_STATUS": "bad"}]

    monkeypatch.setattr(cp, "get_device_bw", lambda *args, **kwargs: "1 Gbps")
    monkeypatch.setattr(cp, "get_next_zw_shelf", lambda *args, **kwargs: "tid")
    monkeypatch.setattr(cp, "wia_check", lambda *args, **kwargs: "tid")
    monkeypatch.setattr(cp, "get_equipment_buildout_v2", lambda *args, **kwargs: cpe_site)

    with raises(Exception):
        assert cp.create_cpe_shelf(payload) is None

    # good equip_status third_party_provided_circuit = 'Y'
    payload["third_party_provided_circuit"] = "Y"
    payload["connector_type"] = "LC"
    payload["side"] = "a_side"
    payload["build_type"] = "New Build"
    payload["cpe_gear"] = "RAD2i-10G-B (10G)"

    cpe_trans["ELEMENT_NAME"] = "AUSWTXMA2ZW"
    cpe_trans["ELEMENT_BANDWIDTH"] = "1 Gbps"
    cpe_trans["PATH_A_SITE"] = "PATH_A_SITE"
    cpe_trans["ELEMENT_REFERENCE"] = "ELEMENT_REFERENCE"
    cpe_trans["CIRC_PATH_INST_ID"] = "CIRC_PATH_INST_ID"

    cpe_site = [{"EQUIP_STATUS": "Planned", "SITE_NAME": "PATH_Z_SITE", "VENDOR": "VENDOR", "MODEL": "MODEL"}]
    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)

    monkeypatch.setattr(cp, "UnderlayDeviceTopologyModel", lambda *args, **kwargs: device_topology)
    monkeypatch.setattr(cp, "get_shelf_names", lambda *args, **kwargs: ("tid/999.9999.999.99/RTR", "tid"))
    monkeypatch.setattr(cp, "type2_uplink", lambda *args, **kwargs: "port_inst_id")

    monkeypatch.setattr(cp, "_build_handoff", lambda *args, **kwargs: "cpe_handoff_pid")
    monkeypatch.setattr(cp, "_set_uni_type", lambda *args, **kwargs: None)
    resp["cpe_model_number"] = device_topology.model

    assert cp.create_cpe_shelf(payload) == resp

    # Trunked
    payload["third_party_provided_circuit"] = "N"
    payload["uni_type"] = "Trunked"
    payload["product_name"] = "EPL (Fiber)"
    payload["side"] = "z_side"
    payload["cpe_gear"] = "ADVA-XG108 (10G)"

    cpe_trans["SEQUENCE"] = "2"
    cpe_site[0]["SLOT"] = "LAN 1"
    cpe_site[0]["PORT_INST_ID"] = "port_inst_id"

    resp["cpe_trunked_path"] = "cpe_trunked_path"

    monkeypatch.setattr(cp, "_create_trunked_handoff", lambda *args, **kwargs: "cpe_trunked_path")

    assert cp.create_cpe_shelf(payload) == resp

    # "FC + Remote PHY" cpe_site NOT list cpe_site False
    payload["third_party_provided_circuit"] = "Y"
    payload["product_name"] = "FC + Remote PHY"
    resp.pop("cpe_trunked_path")

    monkeypatch.setattr(cp, "get_equipment_buildout_v2", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "_create_shelf", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "_build_uplink", lambda *args, **kwargs: "port_inst_id")
    monkeypatch.setattr(cp, "_build_handoff", lambda *args, **kwargs: "cpe_handoff_pid")

    assert cp.create_cpe_shelf(payload) == resp


@pytest.mark.unittest
def test_create_shelf_WIA(monkeypatch):
    shelf_payload = deepcopy(PAYLOAD)
    resp = {
        "cpe_shelf": "tid/999.9999.999.99/RTR",
        "cpe_tid": "tid",
        "cpe_uplink": "cpe_uplink_pid",
        "cpe_handoff": "cpe_handoff_pid",
        "cpe_handoff_paid": "LAN 1",
        "circ_path_inst_id": "1234",
        "zw_path": "1234",
    }

    # "RW700"
    path_payload = [{"Z_SITE_NAME": "Z_SITE_NAME", "CIRC_PATH_INST_ID": "1234"}]

    payload = shelf_payload

    monkeypatch.setattr(cp, "get_granite", lambda *args, **kwargs: path_payload)
    monkeypatch.setattr(cp, "get_next_zw_shelf", lambda *args, **kwargs: "tid")
    monkeypatch.setattr(cp, "_create_shelf", lambda *args, **kwargs: None)

    monkeypatch.setattr(cp, "_build_uplink", lambda *args, **kwargs: "cpe_uplink_pid")
    monkeypatch.setattr(cp, "_build_handoff", lambda *args, **kwargs: "cpe_handoff_pid")

    assert cp.create_shelf_WIA(payload) == resp

    # "RW702"
    shelf_payload["service_code"] = "RW702"
    payload = shelf_payload
    assert cp.create_shelf_WIA(payload) == resp


@pytest.mark.unittest
def test_create_shelf(monkeypatch):
    # Shelf has nothing to update
    monkeypatch.setattr(cp, "granite_shelves_post_url", lambda *args, **kwargs: "shelf_create_url")
    shelf_create_data = {"retString": "Shelf has nothing to update"}
    monkeypatch.setattr(cp, "post_granite", lambda *args, **kwargs: shelf_create_data)

    with raises(AbortException):
        assert cp._create_shelf({}) is None

    # shelf_create_data["retString"] != "Shelf Added":
    shelf_create_data = {"retString": "Shelf NOT Added"}

    with raises(AbortException):
        assert cp._create_shelf({}) is None

    # all good
    shelf_create_data = {"retString": "Shelf Added"}
    assert cp._create_shelf({}) is None


@pytest.mark.unittest
def test_build_uplink(monkeypatch):
    # not device_topology.uplink
    buildout1 = [{"SLOT": "LAN 1", "EQUIP_STATUS": "Planned", "PORT_NAME": "LAN 1"}]
    buildout2 = [EQUIPMENT_DATA]
    buildout = iter([buildout1, buildout2, buildout2])

    monkeypatch.setattr(cp, "get_equipment_buildout", lambda *args, **kwargs: next(buildout))
    device_topology = UnderlayDeviceTopologyModel(**{})

    with raises(AbortException):
        assert cp._build_uplink("shelf_name", device_topology) is None

    # uplink good device_topology.model "W1850"
    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)
    device_topology.model = "NOT W1850"

    monkeypatch.setattr(cp, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "granite_ports_put_url", lambda *args, **kwargs: "ports_url")
    monkeypatch.setattr(cp, "put_granite", lambda *args, **kwargs: None)

    assert cp._build_uplink("shelf_name", device_topology) == "PORT_INST_ID"

    # uplink good device_topology.model not ("ARC CBA850", "E100 C4D/C7C", "W1850")
    device_topology.model = "W1850"

    assert cp._build_uplink("shelf_name", device_topology) == "PORT_INST_ID"


@pytest.mark.unittest
def test_build_handoff(monkeypatch):
    # RF device_template == RAD_203AX_1G
    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)
    device_topology.device_template = RAD_203AX_1G
    monkeypatch.setattr(cp, "get_equipment_buildout", lambda *args, **kwargs: [EQUIPMENT_DATA])
    monkeypatch.setattr(cp, "granite_ports_put_url", lambda *args, **kwargs: "put_url")
    monkeypatch.setattr(cp, "put_granite", lambda *args, **kwargs: None)

    assert cp._build_handoff("shelf_name", "RF", device_topology, "cpe_site") == "PORT_INST_ID"

    # no PORT_ACCESS_ID use slot instead
    equip_data = deepcopy(EQUIPMENT_DATA)
    equip_data.pop("PORT_ACCESS_ID")

    monkeypatch.setattr(cp, "get_equipment_buildout", lambda *args, **kwargs: [equip_data])
    assert cp._build_handoff("shelf_name", "RF", device_topology, "cpe_site") == "PORT_INST_ID"

    # existing CPE ("PORT_USE") != "IN USE" and no handoff
    cpe_site = [{"PORT_USE": "PORT_USE"}]
    payload = deepcopy(UNDERLAY_PAYLOAD)
    payload.pop("handoff")
    device_topology = UnderlayDeviceTopologyModel(**payload)

    monkeypatch.setattr(cp, "get_equipment_buildout", lambda *args, **kwargs: [EQUIPMENT_DATA])

    with raises(AbortException):
        assert cp._build_handoff("shelf_name", "1 Gbps", device_topology, cpe_site, True) is None

    # RF no handoff
    device_topology.device_template = "bad"

    with raises(AbortException):
        assert cp._build_handoff("shelf_name", "RF", device_topology, cpe_site, False) is None

    # ADVA_114PRO_1G existing CPE False ("PORT_USE") = "IN USE" and handoff CARD_TEMPLATE
    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)
    device_topology.device_template = ADVA_114PRO_1G

    monkeypatch.setattr(cp, "delete_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "insert_card_template", lambda *args, **kwargs: None)

    assert cp._build_handoff("shelf_name", "1 Gbps", device_topology, cpe_site) == "PORT_INST_ID"

    # no CARD_TEMPLATE
    equip_data = deepcopy(EQUIPMENT_DATA)
    equip_data.pop("CARD_TEMPLATE")
    monkeypatch.setattr(cp, "get_equipment_buildout", lambda *args, **kwargs: [equip_data])

    assert cp._build_handoff("shelf_name", "1 Gbps", device_topology, cpe_site) == "PORT_INST_ID"

    # RF CRADLEPOINT_ARC
    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)
    device_topology.device_template = CRADLEPOINT_ARC

    monkeypatch.setattr(cp, "get_equipment_buildout", lambda *args, **kwargs: [EQUIPMENT_DATA])

    assert cp._build_handoff("shelf_name", "RF", device_topology, "cpe_site") == "PORT_INST_ID"

    # different device_template
    device_topology.device_template = "different"
    assert cp._build_handoff("shelf_name", "RF", device_topology, "cpe_site") == "PORT_INST_ID"


@pytest.mark.unittest
def test_set_uni_type(monkeypatch):
    monkeypatch.setattr(cp, "granite_ports_put_url", lambda *args, **kwargs: "put_url")
    monkeypatch.setattr(cp, "put_granite", lambda *args, **kwargs: None)

    assert cp._set_uni_type("handoff_pid", "port_role", trunked=True) is None


@pytest.mark.unittest
def test_create_trunked_handoff(monkeypatch):
    monkeypatch.setattr(cp, "get_device_bw", lambda *args, **kwargs: "bw")
    monkeypatch.setattr(cp, "granite_paths_url", lambda *args, **kwargs: "paths_url")
    monkeypatch.setattr(cp, "post_granite", lambda *args, **kwargs: {"pathInstanceId": "pathInstanceId"})
    monkeypatch.setattr(cp, "put_granite", lambda *args, **kwargs: {"pathInstanceId": "pathInstanceId"})

    assert cp._create_trunked_handoff("RJ45", "handoff_pid", "cid", "Z_SITE_NAME", "tid", "1 Gbps") == "pathInstanceId"


@pytest.mark.unittest
def test_check_existing_cpe(monkeypatch):
    # bad test 1 Gbps model abort
    cpe_path_elements = {"ELEMENT_NAME": "tid", "PATH_Z_SITE": "SITE_NAME"}
    cpe_site = [{"SITE_NAME": "SITE_NAME", "VENDOR": "RAD", "MODEL": "ETX203AX"}]

    monkeypatch.setattr(cp, "get_equipment_buildout_v2", lambda *args, **kwargs: cpe_site)

    with raises(Exception):
        assert cp._check_existing_cpe(cpe_path_elements) is None

    # good test 10 Gbps model success
    cpe_site[0]["MODEL"] = "FSP 150-XG108"

    assert cp._check_existing_cpe(cpe_path_elements) is None


@pytest.mark.unittest
def test_type2_uplink(monkeypatch):
    cpe_site = [{"SLOT": "LAN 1"}]
    cpe_site2 = [{"SLOT": "LAN 1", "PORT_INST_ID": "PORT_INST_ID"}]

    device_topology = UnderlayDeviceTopologyModel(**UNDERLAY_PAYLOAD)

    monkeypatch.setattr(cp, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(cp, "get_equipment_buildout_v2", lambda *args, **kwargs: cpe_site2)
    monkeypatch.setattr(cp, "granite_ports_put_url", lambda *args, **kwargs: "ports_url")
    monkeypatch.setattr(cp, "put_granite", lambda *args, **kwargs: None)

    assert cp.type2_uplink(cpe_site, device_topology, "tid") == "PORT_INST_ID"


@pytest.mark.unittest
def test_wia_check(monkeypatch):
    cpe = [{"VENDOR": "CRADLEPOINT", "SITE_NAME": "SITE_NAME"}]
    cpe_trans = {"ELEMENT_NAME": "ELEMENT_NAME", "ELEMENT_REFERENCE": "ELEMENT_REFERENCE"}

    monkeypatch.setattr(cp, "get_equipment_buildout_v2", lambda *args, **kwargs: cpe)
    monkeypatch.setattr(cp, "get_next_zw_shelf", lambda *args, **kwargs: "new_tid")
    monkeypatch.setattr(cp, "granite_paths_url", lambda *args, **kwargs: "url")

    # bad resp_data
    resp_data = {"retString": "bad"}
    monkeypatch.setattr(cp, "put_granite", lambda *args, **kwargs: resp_data)

    with raises(Exception):
        assert cp.wia_check("tid", cpe_trans) is None

    # good resp_data
    resp_data["retString"] = "Path Updated"
    assert cp.wia_check("tid", cpe_trans) == "new_tid"

    # equip buildout not list
    monkeypatch.setattr(cp, "get_equipment_buildout_v2", lambda *args, **kwargs: "cpe")
    assert cp.wia_check("tid", cpe_trans) == "tid"
