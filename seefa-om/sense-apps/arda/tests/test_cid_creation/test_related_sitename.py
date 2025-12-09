import pytest

from arda_app.api import related_sitename as rs

rs_endpoint = "/arda/v1/related_sitename"


@pytest.mark.unittest
def test_related_sitename(monkeypatch, client):
    # good test
    payload = {"related_circuit_id": "27.L1XX.000002.GSO.TWCC", "product_family": "Secure Dedicated Internet"}

    monkeypatch.setattr(rs, "rel_site_name_main", lambda *args, **kwargs: [{"Z_SITE_NAME": "test_sitename"}])
    resp = client.post(rs_endpoint, json=payload)
    assert resp.status_code == 200
