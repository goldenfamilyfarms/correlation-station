import time

import pytest

from beorn_app.common.mdso_auth import create_token, delete_token
from beorn_app.common.mdso_operations import delete_service, service_id_lookup


@pytest.mark.unittest
def test_service_no_cid(client):
    """Test not providing a CID results in a 400"""
    response = client.get("/beorn/v1/service")
    assert response.status_code == 400

    response = client.post("beorn/v1/service")
    assert response.status_code == 400

    response = client.delete("beorn/v1/service")
    assert response.status_code == 400

    response = client.put("beorn/v1/service")
    assert response.status_code == 400


@pytest.mark.skip(reason="related to hydra url needing verify=False")
def test_integration(client):
    token = create_token()
    headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

    cid = "51.L1XX.009025..TWCC"

    err_msg, service_id = service_id_lookup(headers, cid)
    assert err_msg is None
    if service_id:
        err_msg = delete_service(headers, service_id)
        delete_token(token)
        assert err_msg is None
        response = client.get("beorn/v1/service?cid={}".format(cid))
        timeout = 0
        while response.status_code != 404 and timeout <= 15:
            timeout += 1
            time.sleep(3)
            response = client.get("beorn/v1/service?cid={}".format(cid))
        assert timeout <= 15

    response = client.get("beorn/v1/service?cid={}".format(cid))
    assert response.status_code == 404

    response = client.post("beorn/v1/service?cid={}".format(cid))
    assert response.status_code == 201

    response = client.get("beorn/v1/service?cid={}".format(cid))
    assert response.status_code == 200
    assert response.json["Desired service state"] == "active"

    data = {"bw": "true", "ip": "true", "dsc": "true"}
    response = client.put("beorn/v1/service?cid={}".format(cid), json=data)
    assert response.status_code == 201
    assert len(response.json.items()) == 3

    response = client.delete("beorn/v1/service?cid={}".format(cid))
    assert response.status_code == 200


@pytest.mark.skip(reason="related to hydra url needing verify=False")
def test_service_v3_success(client):
    """test for specific successes in v3"""
    data = {"cid": "51.L1XX.010026..TWCC", "product_name": "Fiber Internet Access"}

    # success; 200 "Pass"
    resp = client.post("beorn/v3/service", json=data)
    assert resp.status_code == 200
    assert resp.json["resource_id"] == "60bf8f03-56e5-4673-85e5-492e5f83bc24"


@pytest.mark.skip(reason="related to hydra url needing verify=False")
def test_service_v3_fail(client):
    """test for specific failures in v3"""
    data = {"cid": "51.L1XX.802896..CHTR", "product_name": "Fiber Internet Access"}
    return_data = [
        "Path Leg  (1) A-Side Site does not match Path A-Side Site.",
        "Assigned IPv4 Range must be defined when IPv4 Service Type has a value.",
        "Assigned IPv4 Subnet must be defined when IPv4 Service Type has a value.",
        "Gateway IPv4 Address must be defined when IPv4 Service Type has a value.",
        "Assigned IPv4 Subnet Mask must be defined when IPv4 Service Type has a value.",
        "Z-Side Customer not found.",
    ]

    resp = client.post("beorn/v3/service", json=data)
    assert resp.status_code == 501
    assert "gsip_non_compliant" in resp.json
    assert resp.json["gsip_non_compliant"] == return_data
