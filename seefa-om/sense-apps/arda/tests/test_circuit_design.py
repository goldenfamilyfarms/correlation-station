import json

import pytest
import requests


class MockResponse:
    def __init__(self, file):
        self.file = file

    status_code = 200

    def json(self):
        with open(self.file) as j:
            return json.load(j)


class MockEmptyResponse:
    status_code = 200

    @staticmethod
    def json():
        return {"elements": []}


# CID tests
@pytest.mark.skip
def test_circuit_design_cid_valid(client, monkeypatch):
    """Test design with a valid, defined cid"""

    def mock_get(*args, **kwargs):
        return MockResponse("mock_data/cans_cid_get_resp.json")

    monkeypatch.setattr(requests, "get", mock_get)
    url = "/arda/v1/noc_analysis?cid=80.L1XX.001812..TWCC"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json() is not None


@pytest.mark.skip
def test_circuit_design_cid_undefined(client, monkeypatch):
    """test design with an undefined cid"""

    def mock_get(*args, **kwargs):
        return MockEmptyResponse

    monkeypatch.setattr(requests, "get", mock_get)
    url = "/arda/v1/noc_analysis?cid=asd"
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - no records found" in resp.json().get("message")


@pytest.mark.skip
def test_circuit_design_cid_empty(client):
    """test design with an empty cid"""
    url = "/arda/v1/noc_analysis?cid="
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - nothing specified for parameter 'cid'" in resp.json().get("message")


# TID tests
@pytest.mark.skip
def test_circuit_design_tid_valid(client, monkeypatch):
    """Test design with a valid, defined tid"""

    def mock_get(*args, **kwargs):
        return MockResponse("mock_data/cans_tid_get_resp.json")

    monkeypatch.setattr(requests, "get", mock_get)

    url = "/arda/v1/noc_analysis?tid=AMDAOH031ZW"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json() is not None


@pytest.mark.skip
def test_circuit_design_tid_invalid(client, monkeypatch):
    """test design with an invalid tid"""

    def mock_get(*args, **kwargs):
        return MockEmptyResponse

    monkeypatch.setattr(requests, "get", mock_get)
    url = "/arda/v1/noc_analysis?tid=asd"
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - no records found" in resp.json().get("message")


@pytest.mark.skip
def test_circuit_design_tid_empty(client):
    """test design with an empty cid"""
    url = "/arda/v1/noc_analysis?tid="
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - nothing specified for parameter 'tid'" in resp.json().get("message")


# Broader tests
@pytest.mark.skip
def test_circuit_design_no_tid_cid(client):
    """test design response without 'tid' or 'cid' specified"""
    url = "/arda/v1/noc_analysis"
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - invalid parameter provided - please use either 'tid' or 'cid'" in resp.json().get("message")


@pytest.mark.skip
def test_circuit_design_both_tid_and_cid(client):
    """test design response with both 'tid' and 'cid' provided"""
    url = "/arda/v1/noc_analysis?cid=80.L1XX.001812..TWCC&tid=WRRNOHCB1ZW"
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - more than one parameter provided, please use either 'tid' or 'cid'" in resp.json().get("message")


@pytest.mark.skip
def test_circiutdesign_valid_and_invalid_param(client):
    """test design with 'cid' and an invalid param provided"""
    url = "/arda/v1/noc_analysis?cid=80.L1XX.001812..TWCC&id=WRRNOHCB1ZW"
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - more than one parameter provided, please use either 'tid' or 'cid'" in resp.json().get("message")
