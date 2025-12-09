# --------------
# Endpoint tests
# --------------
import pytest


@pytest.mark.unittest
def test_root_url_resolves(client):
    """Test our root API resolves"""
    response = client.get("/beorn/")
    assert response.status_code == 200


@pytest.mark.unittest
def test_health_check_resolves(client):
    """Test the /health endpoint resolves"""
    response = client.get("/beorn/v1/health")
    assert response.status_code == 200


@pytest.mark.unittest
@pytest.mark.skip(reason="research POST call")
def test_sf_post_call_resolves(client):
    """Test the POSt call from salesforce returns data as expected"""
    response = client.post("/v1/salesforce/mydata")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.data == b'{"Received sf data": "mydata"}\n'


@pytest.mark.skip(reason="research PUT call")
def test_cid_put_call_resolves(client):
    """Test the PUT call from returns dummy data as expected"""
    response = client.put("/cid/arostien")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.data == b'{"PUT": "arostien"}\n'
