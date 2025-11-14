import pytest

from arda_app.bll.net_new import create_mtu_transport as cmt

from . import arda_headers
from arda_app.common import auth_config


test_payload = {
    "service_type": "net_new_cj",
    "product_name": "Carrier E-Access (Fiber)",
    "cid": "51.L1XX.814879..TWCC",
    "legacy_company": "Charter",
    "build_type": "MTU New Build",
    "mtu_tid": "ORLFFLPL1AW",
    "cpe_tid": "ORLFFLPL1ZW",
    "mtu_handoff": "123",
    "cpe_uplink": "456",
    "side": "z_side",
}

test_resp = {
    "mtu_new_build_transport_name": "456",
    "mtu_new_build_transport": "123",
    "message": "te001.GE10.ORLFFLPL1AW.ORLFFLPL1ZW has been successfully created and added to 51.L1XX.814879..TWCC",
}

sense_usr, sense_pass = auth_config.SENSE_TEST_SWAGGER_USER, auth_config.SENSE_TEST_SWAGGER_PASS
auth = (sense_usr, sense_pass)


@pytest.mark.unittest
def test_create_mtu_transport(monkeypatch, client):
    monkeypatch.setattr(
        cmt,
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
                "Z_SITE_NAME": "Test Z Site",
            },
            {"LVL": 2},
        ],
    )

    monkeypatch.setattr(cmt, "get_site", lambda *args, **kwargs: [{"npaNxx": "testNpaNxx"}])
    monkeypatch.setattr(cmt, "put_granite", lambda *args, **kwargs: {"BANDWIDTH": 1})
    monkeypatch.setattr(cmt, "post_granite", lambda *args, **kwargs: {"pathInstanceId": "123", "pathId": "456"})

    monkeypatch.setattr(cmt, "_assign_handoff_to_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(cmt, "_assign_uplink_to_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(cmt, "_add_transport_to_path", lambda *args, **kwargs: None)

    resp = client.post("/arda/v1/create_mtu_transport", json=test_payload, headers=arda_headers)

    assert resp.status_code == 201
    assert resp.json() == test_resp


@pytest.mark.unittest
def test_assign_handoff_to_path(monkeypatch):
    monkeypatch.setattr(cmt, "put_granite", lambda *args, **kwargs: None)
    assert cmt._assign_handoff_to_path("transport_name", "transport", "mtu_handoff", "paths_url") is None


@pytest.mark.unittest
def test_assign_uplink_to_path(monkeypatch):
    monkeypatch.setattr(cmt, "put_granite", lambda *args, **kwargs: None)
    assert cmt._assign_uplink_to_path("transport_name", "transport", "cpe_uplink", "paths_url") is None


@pytest.mark.unittest
def test_add_transport_to_path(monkeypatch):
    monkeypatch.setattr(cmt, "put_granite", lambda *args, **kwargs: None)
    assert cmt._add_transport_to_path("cid", "transport", "EPL (Fiber)", "a_side", "paths_url") is None
