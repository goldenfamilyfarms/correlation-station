import json


def test_found_cid(client):
    """Test our URL returns a 200 when sending request with valid cid and verify siteid"""
    ticket_query_params = "cid=57.L1XX.000240..TWCC&start_time=1527184648&end_time=1527280676"
    url = "/palantir/v1/ice/tickets?{}".format(ticket_query_params)
    resp = client.get(url)
    assert resp.status_code == 200
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["siteID"] == "460009"


def test_found_siteid(client):
    """Test our URL returns a 200 when sending request with valid siteid and verify siteid"""
    url = "/palantir/v1/ice/tickets?site_id=460009&start_time=1527184648&end_time=1527280676"
    resp = client.get(url)
    assert resp.status_code == 200
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["siteID"] == "460009"


def test_cid_not_found(client):
    url = "/palantir/v1/ice/tickets?cid=5&start_time=1527184648&end_time=1527280676"
    resp = client.get(url)
    assert resp.status_code == 500


def test_start_time_missing(client):
    url = "/palantir/v1/ice/tickets?cid=00.L1XX.000000..TWCC&start_time=&end_time=1527280676"
    resp = client.get(url)
    assert resp.status_code == 500
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["message"] == "Required parameter missing: Start Date Time"


def test_end_time_missing(client):
    url = "/palantir/v1/ice/tickets?cid=00.L1XX.000000..TWCC&start_time=1527184648&end_time="
    resp = client.get(url)
    assert resp.status_code == 500
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["message"] == "Required parameter missing: End Date Time"
