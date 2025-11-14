import pytest
from beorn_app.apis.v1 import managed_rphy as m_rphy


@pytest.mark.unittest
def test_rphy_get_pass(client, monkeypatch):
    # cid below is specifically for rphy testing
    monkeypatch.setattr(m_rphy, "get_existing_resource_by_query", lambda *args: {"id": "abc"})
    response = client.get("/beorn/v1/rphy?cid=97.VSXX.001606..CHTR")
    assert response.status_code == 200


@pytest.mark.unittest
def test_rphy_get_fail(client, monkeypatch):
    monkeypatch.setattr(m_rphy, "get_existing_resource_by_query", lambda *args: None)
    response = client.get("/beorn/v1/rphy?cid=123456789")
    assert response.status_code == 404


@pytest.mark.unittest
def test_rphy_bad_payload(client):
    response = client.get("/beorn/v1/rphy?CID=97.VSXX.001606..CHTR")
    assert response.status_code == 400
