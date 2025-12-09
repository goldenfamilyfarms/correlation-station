# import json


# def test_found_ip(client):
#     """Test our ip URL returns a 200 when sending request with valid ip"""
#     url = '/palantir/v1/ipblock?ip=24.123.44.0'
#     resp = client.get(url)
#     assert resp.status_code == 200
#     resp_data = json.loads(resp.data.decode('utf-8'))
#     assert resp_data['ipc']['Account_Number'] == '110821801'


# def test_ip_not_found(client):
#     url = '/palantir/v1/ipblock?ip=1.1.1.1'
#     resp = client.get(url)
#     assert resp.status_code == 500


# def test_bad_ip_address(client):
#     url = '/palantir/v1/ipblock?ip=1.1.1'
#     resp = client.get(url)
#     assert resp.status_code == 500
#     resp_data = json.loads(resp.data.decode('utf-8'))
#     assert resp_data['message'] == 'invalid ip address'


# def test_no_ip_address(client):
#     url = '/palantir/v1/ipblock'
#     resp = client.get(url)
#     assert resp.status_code == 500
#     resp_data = json.loads(resp.data.decode('utf-8'))
#     assert resp_data['message'] == 'Required parameter missing: IP Address'
