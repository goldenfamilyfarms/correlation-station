import os

# from flask import request
# import pytest
#
# import palantir
from palantir_app.common.config import Config

# ----------------
# High-level tests
# ----------------


def test_configuration():
    """Test configuration settings"""
    # Default when the "ENV" variable doesn't exist is STAGING
    environment = os.environ.get("ENV", None)
    assert environment is None
    config = Config()
    assert config.MDSO_IP == "97.105.228.53"

    os.environ["ENV"] = "PROD"
    assert "PROD" == os.environ.get("ENV")
    config = Config()
    assert config.MDSO_IP == "50.84.225.107"


# def test_request_ctxt(single_mx_post):
#     """Test we received JSON data in the request"""
#
#     headers = {'Content-Type': 'application/json'}
#
#     with palantir.app.test_request_context('/', method='GET',
#                                            data=json.dumps(single_mx_post),
#                                            headers=headers):
#         assert request.path == '/'
#         assert request.method == 'GET'
#         # `force=True` to skip content-type validation
#         assert request.get_json(force=True) == single_mx_post


# @pytest.mark.skip(reason="Fragile tests break if interfaces on the router change. "
#                   "Hard-coded data checked against")
# def test_valid_json_single(client, single_mx_post, single_mx_expected):
#     """High-level test focusing on passing in data and getting http response
#
#     Test the response from a lab router is what we expect it to be. Note that
#     this is a brittle test and may fail in the future with any changes to the
#     lab router it touches.
#     """
#
#     response = client.post('/', data=json.dumps(single_mx_post))
#
#     resp_json = json.loads(response.data)
#     resp_dict = resp_json.pop()
#
#     expected_dict = single_mx_expected.pop()
#
#     # Some minor inconsistencies between what's received through a request
#     # and what we read in from the config file, so turning both into a dict
#     # to try to eliminate those inconsistencies
#     assert expected_dict == resp_dict
#
#     assert response.status_code == 202


# def test_lab_data(client, lab_test_1, lab_test_2, lab_test_3, lab_test_4):
#     """Test against actual JSON received from Mulesoft flow"""
#
#     response1 = client.post('/', data=json.dumps(lab_test_1))
#     assert response1.status_code == 202
#
#     response2 = client.post('/', data=json.dumps(lab_test_2))
#     assert response2.status_code == 202
#
#     response3 = client.post('/', data=json.dumps(lab_test_3))
#     assert b'Invalid IP address' not in response3.data
#     assert response3.status_code == 202
#
#     response4 = client.post('/', data=json.dumps(lab_test_4))
#     assert response4.status_code == 202


# @pytest.mark.skip(reason="Fragile test - breaks when interfaces on the router "
#                   "change. Hard-coded data checked against")
# def test_valid_json_double(client, double_mx_post, double_mx_resp):
#     json_data = json.dumps(double_mx_post)
#     response = client.post('/', data=json_data)
#
#     resp_json = json.loads(response.data)
#     resp_dict = resp_json.pop()
#
#     expected_dict = double_mx_resp.pop()
#
#     # Some minor inconsistencies between what's received through a request
#     # and what we read in from the config file, so turning both into a dict
#     # and only testing keys are as expected to try to eliminate those
#     # inconsistencies
#     assert expected_dict.keys() == resp_dict.keys()
#
#     assert response.status_code == 202


# def test_400_if_no_json(client):
#     """Should get a 400 response if no JSON included in GET or DELETE"""
#
#     headers = {'Content-Type': 'application/json'}
#
#     response = client.post('/', data=None, headers=headers)
#
#     assert b'Bad JSON data received' in response.data
#     assert response.status_code == 500


# def test_400_if_invalid_json(client, sample_bad_json):
#     """Should receive a 400 response if JSON malformed or doesn't have
#     required fields
#     """
#     headers = {'Content-Type': 'application/json'}
#
#     response = client.post('/', data=sample_bad_json, headers=headers)
#
#     assert b'Bad JSON data received' in response.data
#     assert response.status_code == 500


# def test_400_msg_missing_ip(client, single_mx_post):
#     """Test for response for missing IP"""
#
#     json_dict = single_mx_post.pop()
#     # rm IP addr from data
#     json_dict.get('zSide').pop('ip')
#
#     headers = {'Content-Type': 'application/json'}
#     response = client.post('/', data=json.dumps([json_dict]), headers=headers)
#
#     assert b'Missing IP address in JSON. Transaction ID: 123' in response.data
#     assert response.status_code == 500


# def test_400_msg_bad_ip(client, single_mx_post):
#     """Test for response for bad IP address"""
#
#     json_dict = single_mx_post.pop()
#     # update IP address to a bad one
#     json_dict.get('zSide').update({'ip': '299.1.0.0'})
#
#     headers = {'Content-Type': 'application/json'}
#     response = client.post('/', data=json.dumps([json_dict]), headers=headers)
#
#     assert b'Invalid IP address in JSON. Transaction ID: 123' in response.data
#     assert response.status_code == 500


# def test_400_msg_missing_vlan(client, single_mx_post):
#     """Test for response for missing vlan"""
#     json_dict = single_mx_post.pop()
#     json_dict.get('zSide').pop('vlan')
#
#     headers = {'Content-Type': 'application/json'}
#     response = client.post('/', data=json.dumps([json_dict]), headers=headers)
#
#     assert b'Missing VLAN in JSON. Transaction ID: 123' in response.data
#     assert response.status_code == 500


# def test_400_msg_bad_vlan(client, single_mx_post):
#     """Test for response for bad vlan"""
#     json_dict = single_mx_post.pop()
#     json_dict.get('zSide').update({'vlan': '9999'})
#
#     headers = {'Content-Type': 'application/json'}
#     response = client.post('/', data=json.dumps([json_dict]), headers=headers)
#
#     assert b'Invalid VLAN in JSON. Transaction ID: 123' in response.data
#     assert response.status_code == 500


def test_health_check(client):
    """Test our health check URL returns a 200 when the server is up"""
    resp = client.get("/palantir/v1/health")
    assert resp.status_code == 200
