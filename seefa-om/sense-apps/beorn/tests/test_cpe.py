def test_get_circuit_details(client):
    response = client.get("/beorn/v1/cpe?cid=51.L1XX.009025..TWCC")
    assert response.status_code in (200, 404)


def test_activate_cpe(client):
    data = {"cid": "51.L1XX.009025..TWCC", "ip": "71.42.150.146", "tid": "AUSDTXIR2CW", "port_id": "GE-1/0/4"}
    response = client.put("beorn/v1/cpe", query_string=data)
    data = response.json
    if response.status_code == 201:
        assert data.get("resourceId")
        assert data.get("operationId")
    else:
        assert response.status_code == 404
