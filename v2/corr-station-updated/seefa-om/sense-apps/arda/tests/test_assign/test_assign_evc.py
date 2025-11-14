import copy
from unittest.mock import Mock

import pytest
import requests

from arda_app.api import assign_evc

from arda_app.bll.assign import evc


class MockResponse200:
    status_code = 200
    text = "not found"

    def json(self):
        return "ok"


class MockResponse404:
    status_code = 404
    text = "not found"


payload = {"side": "z_side", "cid": "81.L1XX.006522..TWCC", "product_name": "Carrier E-Access (Fiber)"}

granite_response = [{"NUMBER": "", "RANGE_NAME": ""}]


@pytest.mark.unittest
def test_no_cid(client):
    """Test design with a valid, defined cid"""

    data = copy.deepcopy(payload)
    del data["cid"]

    resp = client.post("arda/v1/assign_evc", json=data)

    assert resp.status_code == 500
    assert "Required query parameter(s) not specified: cid" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_json_error(monkeypatch, client):
    """Test design with a valid, defined cid"""

    resp = client.post("arda/v1/assign_evc", data=b"/")

    assert resp.status_code == 500
    assert "JSON decode error" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_firstPathEVC_fail(monkeypatch, client):
    """Test design with a valid, defined cid"""

    monkeypatch.setattr(evc, "get_granite", lambda *_: granite_response)

    resp = client.post("arda/v1/assign_evc", json=payload)

    assert resp.status_code == 500
    assert "Get granite firstPathEVC error data" in resp.json().get("message")


@pytest.mark.unittest
def test_Assign_EVC_PUT_CALL(monkeypatch, client):
    """Test design with a valid, defined cid"""

    def mock_put_404(*args, **kwargs):
        return MockResponse404()

    def mock_put_200(*args, **kwargs):
        return MockResponse200()

    g_res = copy.deepcopy(granite_response)
    g_res[0].update({"NUMBER": "NUMBER", "RANGE_NAME": "RANGE_NAME"})

    monkeypatch.setattr(evc, "get_granite", lambda *_: g_res)
    monkeypatch.setattr(evc, "put_granite", lambda *_: g_res)
    monkeypatch.setattr(requests, "put", Mock(side_effect=[mock_put_200(), mock_put_404()]))

    resp = client.post("arda/v1/assign_evc", json=payload)

    assert resp.status_code == 200
    assert "EVC ID has been added successfully" in resp.json().get("message")


@pytest.mark.unittest
def test_success(monkeypatch, client):
    """Test design with a valid, defined cid"""

    monkeypatch.setattr(
        assign_evc, "assign_evc_main", lambda payload: {"message": "EVC ID has been added successfully."}
    )

    resp = client.post("arda/v1/assign_evc", json=payload)

    assert resp.status_code == 200
    assert "EVC ID has been added successfully" in resp.json().get("message")
