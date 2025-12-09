import pytest


@pytest.mark.unittest
def test_bandwidth_available_no_cid(client):
    """GET: No Service Id passed in: null CID results in a 400"""
    response = client.get("/beorn/v1/bandwidth/available")
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_available_good(client):
    """ "GET: On -good- Service ID: Good CID results in a 400"""
    response = client.get("/beorn/v1/bandwidth/available?CID=123456789")
    assert response.status_code == 200


# Invalid Service Id passed in for GET is NOT Checked ... Verified by Caller:


@pytest.mark.unittest
def test_bandwidth_bad_parameter_1(client):
    """PUT: Bad Parameter: Bad Param results in a 400"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "50", "bw_unit": "ZBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_bad_parameter_2(client):
    """PUT: Bad Parameter: Bad Param results in a 400"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "55", "bw_unit": "MBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_bad_parameter_3(client):
    """PUT: Bad Parameter: Bad Param results in a 400"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "1G", "bw_unit": "GBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_bad_range(client):
    """ "PUT: Out of Range Parameter: No CID results in a 400"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "100", "bw_unit": "GBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_no_cid(client):
    """PUT: No Service Id passed in: No CID results in a 400"""
    data = {"bw_value": "50", "bw_unit": "MBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_no_bw_unit(client):
    """PUT: No Service Id passed in: No CID results in a 400"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "50", "bw_unit": ""}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_no_bw_val(client):
    """PUT: No Service Id passed in: No CID results in a 400"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "", "bw_unit": "MBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.unittest
def test_bandwidth_no_params(client):
    """PUT: No Service Id passed in: No CID results in a 400"""
    data = {"CID": "", "bw_value": "", "bw_unit": ""}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 400


@pytest.mark.skip(reason="firewall issue")
def test_bandwidth_good(client):
    """PUT: Good Case: Test CID results in a 201"""
    data = {"CID": "51.L1XX.009025..TWCC", "bw_value": "100", "bw_unit": "MBPS"}
    response = client.put("/beorn/v1/bandwidth", query_string=data)
    assert response.status_code == 201


# Not retesting MDSO Token being done elsewhere
