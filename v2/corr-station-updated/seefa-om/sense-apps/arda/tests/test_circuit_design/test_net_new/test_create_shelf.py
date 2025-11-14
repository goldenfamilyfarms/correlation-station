import logging

import pytest

from arda_app.bll.models.device_topology import underlay
from arda_app.bll.net_new import create_cpe
from arda_app.bll.net_new.with_cj import create_mtu

from . import arda_headers
from arda_app.common import auth_config


logger = logging.getLogger(__name__)

test_cpe_payload = {
    "service_type": "net_new_cj",
    "product_name": "Carrier E-Access (Fiber)",
    "cid": "51.L1XX.814879..TWCC",
    "legacy_company": "Charter",
    "build_type": "Home Run",
    "connector_type": "RJ45",
    "uni_type": "Access",
    "role": "cpe",
    "side": "z_side",
}

test_cpe_resp = {
    "cpe_shelf": "ZW/999.9999.999.99/NIU",
    "cpe_tid": "ZW",
    "cpe_uplink": "",
    "cpe_handoff": "123",
    "cpe_handoff_paid": "0/1",
    "zw_path": "51.L1XX.814879..TWCC",
    "circ_path_inst_id": "1",
}

test_mtu_payload = {
    "service_type": "net_new_cj",
    "product_name": "Carrier E-Access (Fiber)",
    "cid": "51.L1XX.814879..TWCC",
    "legacy_company": "Charter",
    "build_type": "MTU New Build",
    "connector_type": "LC",
    "uni_type": "Trunked",
    "role": "mtu",
    "side": "z_side",
}

test_mtu_resp = {
    "mtu_shelf": "AW/999.9999.999.99/NIU",
    "mtu_tid": "AW",
    "mtu_uplink": "",
    "mtu_handoff": "123",
    "mtu_pe_path": "51.L1XX.814879..TWCC",
    "mtu_z_site": "Test Z Site",
}

sense_usr, sense_pass = auth_config.SENSE_TEST_SWAGGER_USER, auth_config.SENSE_TEST_SWAGGER_PASS
auth = (sense_usr, sense_pass)


@pytest.mark.skip
def test_create_cpe_shelf(monkeypatch, client):
    monkeypatch.setattr(
        create_cpe,
        "get_path_elements_data",
        lambda *args, **kwargs: [
            {
                "BANDWIDTH": "1 Gbps",
                "CIRC_PATH_INST_ID": "1",
                "ELEMENT_NAME": "Test.Element.Name.ZW",
                "ELEMENT_BANDWIDTH": "10 Gbps",
                "ELEMENT_REFERENCE": "51.L1XX.814879..TWCC",
                "LVL": 1,
                "PATH_Z_SITE": "Test Z Site",
                "SEQUENCE": "1",
                "Z_CLLI": "TESTCLLI",
            },
            {"LVL": 2},
        ],
    )
    monkeypatch.setattr(underlay, "get_selected_vendor", lambda *args, **kwargs: {"VENDOR": "RAD"})
    monkeypatch.setattr(
        create_cpe, "post_granite", lambda *args, **kwargs: {"pathInstanceId": "123", "retString": "Shelf Added"}
    )
    monkeypatch.setattr(
        create_cpe,
        "get_equipment_buildout",
        lambda *args, **kwargs: [{"PORT_USE": "USED", "SLOT": "0/1", "PORT_INST_ID": "123"}],
    )
    monkeypatch.setattr(create_cpe, "put_granite", lambda *args, **kwargs: {"BANDWIDTH": 1})

    resp = client.post("/arda/v1/create_shelf", json=test_cpe_payload, headers=arda_headers, auth=auth)
    logger.debug(f"Response status code - {resp.status_code}")

    assert resp.status_code == 201
    assert resp.json() == test_cpe_resp


@pytest.mark.unittest
def test_create_mtu_shelf(monkeypatch, client):
    monkeypatch.setattr(
        create_cpe,
        "get_path_elements_data",
        lambda *args, **kwargs: [
            {
                "BANDWIDTH": "1 Gbps",
                "CIRC_PATH_INST_ID": "1",
                "ELEMENT_NAME": "Test.Element.Name.AW",
                "ELEMENT_BANDWIDTH": "10 Gbps",
                "ELEMENT_REFERENCE": "51.L1XX.814879..TWCC",
                "LVL": 1,
                "PATH_Z_SITE": "Test Z Site",
                "SEQUENCE": "1",
                "Z_CLLI": "TESTCLLI",
            },
            {"LVL": 2},
        ],
    )
    monkeypatch.setattr(
        create_mtu,
        "get_path_elements_data",
        lambda *args, **kwargs: [
            {
                "BANDWIDTH": "1 Gbps",
                "CIRC_PATH_INST_ID": "1",
                "ELEMENT_NAME": "Test.Element.Name.AW",
                "ELEMENT_BANDWIDTH": "10 Gbps",
                "ELEMENT_REFERENCE": "51.L1XX.814879..TWCC",
                "LVL": 1,
                "PATH_Z_SITE": "Test Z Site",
                "SEQUENCE": "1",
                "Z_CLLI": "TESTCLLI",
                "Z_SITE_NAME": "Test Z Site",
            },
            {"LVL": 2},
        ],
    )
    monkeypatch.setattr(underlay, "get_selected_vendor", lambda *args, **kwargs: {"VENDOR": "RAD"})
    monkeypatch.setattr(
        create_cpe, "post_granite", lambda *args, **kwargs: {"pathInstanceId": "123", "retString": "Shelf Added"}
    )
    monkeypatch.setattr(
        create_mtu, "post_granite", lambda *args, **kwargs: {"pathInstanceId": "123", "retString": "Shelf Added"}
    )
    monkeypatch.setattr(
        create_cpe,
        "get_equipment_buildout",
        lambda *args, **kwargs: [{"PORT_USE": "USED", "SLOT": "0/1", "PORT_INST_ID": "123"}],
    )
    monkeypatch.setattr(
        create_mtu,
        "get_equipment_buildout",
        lambda *args, **kwargs: [{"PORT_USE": "USED", "SLOT": "0/5", "PORT_INST_ID": "123"}],
    )
    monkeypatch.setattr(create_cpe, "put_granite", lambda *args, **kwargs: {"BANDWIDTH": 1})
    monkeypatch.setattr(create_mtu, "put_granite", lambda *args, **kwargs: {"BANDWIDTH": 1})

    resp = client.post("/arda/v1/create_shelf", json=test_mtu_payload, headers=arda_headers, auth=auth)
    logger.debug(f"Response status code - {resp.status_code}")

    assert resp.status_code == 201
    assert test_mtu_resp == resp.json()
