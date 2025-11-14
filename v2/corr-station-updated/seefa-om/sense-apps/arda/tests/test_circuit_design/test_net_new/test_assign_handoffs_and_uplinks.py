import logging

import pytest

from arda_app.bll.net_new import assign_uplinks_and_handoffs

from . import arda_headers
from arda_app.common import auth_config


logger = logging.getLogger(__name__)


test_uplink_payload = {
    "service_type": "net_new_cj",
    "product_name": "Carrier E-Access (Fiber)",
    "cid": "51.L1XX.814879..TWCC",
    "circ_path_inst_id": "string",
    "legacy_company": "Charter",
    "build_type": "MTU New Build",
    "mtu_tid": "ORLFFLPL1AW",
    "cpe_tid": "ORLFFLPL1ZW",
    "port_role": "uplink",
    "mtu_uplink": "123",
    "mtu_pe_path": "456",
    "cpe_uplink": "789",
    "zw_path": "0123",
    "side": "z_side",
}

test_handoff_payload = {
    "service_type": "net_new_cj",
    "product_name": "Carrier E-Access (Fiber)",
    "cid": "51.L1XX.814879..TWCC",
    "circ_path_inst_id": "123",
    "legacy_company": "Charter",
    "build_type": "Home Run",
    "mtu_tid": "ORLFFLPL1AW",
    "cpe_tid": "ORLFFLPL1ZW",
    "port_role": "handoff",
    "cpe_handoff": "123",
    "cpe_handoff_paid": "456",
    "cpe_trunked_path": "789",
    "side": "z_side",
}

sense_usr, sense_pass = auth_config.SENSE_TEST_SWAGGER_USER, auth_config.SENSE_TEST_SWAGGER_PASS
auth = (sense_usr, sense_pass)


@pytest.mark.unittest
def test_assign_uplink(monkeypatch, client):
    monkeypatch.setattr(
        assign_uplinks_and_handoffs, "get_path_elements", lambda cid, _: [{"PORT_INST_ID": "TESTPID123"}]
    )

    test_cpe_uplink_payload = test_uplink_payload.copy()
    test_cpe_uplink_payload["build_type"] = "Home Run"

    monkeypatch.setattr(assign_uplinks_and_handoffs, "put_granite", lambda _, body: {"BANDWIDTH": 1})
    resp = client.post(
        "/arda/v1/assign_handoffs_and_uplinks", json=test_cpe_uplink_payload, headers=arda_headers, auth=auth
    )
    logger.debug(f"Response status code - {resp.status_code}")

    assert resp.status_code == 201

    expected = {"message": "CPE Uplink has been added successfully."}
    assert resp.json() == expected


@pytest.mark.unittest
def test_assign_handoff(monkeypatch, client):
    monkeypatch.setattr(
        assign_uplinks_and_handoffs, "get_path_elements", lambda _, url_params: [{"PORT_INST_ID": "TESTPID123"}]
    )

    monkeypatch.setattr(assign_uplinks_and_handoffs, "put_granite", lambda _, body: {"BANDWIDTH": 1})

    resp = client.post(
        "/arda/v1/assign_handoffs_and_uplinks", json=test_handoff_payload, headers=arda_headers, auth=auth
    )

    assert resp.status_code == 201

    expected = {"message": "CPE Handoff has been added successfully."}
    assert resp.json() == expected
