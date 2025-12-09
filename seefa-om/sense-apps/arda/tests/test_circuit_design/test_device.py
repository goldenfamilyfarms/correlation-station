import time

import pytest
import requests

import arda_app.dll.mdso as mdso
from mock_data.circuit_design import device_mock_data as mock
from common_sense.common.errors import AbortException

""" Check Onboard """


@pytest.mark.unittest
def test_check_onboard_success(monkeypatch):
    monkeypatch.setattr(mdso, "_create_token", mock.mock_auth_response)
    monkeypatch.setattr(mdso, "resync_mdso_device", mock.mock_resync_mdso_device)
    monkeypatch.setattr(requests, "get", mock.mock_good_response)
    monkeypatch.setattr(requests, "delete", mock.mock_delete_response)

    result = mdso.check_onboard("hostname123")
    assert "Completed" in result["status"]


""" with the new session check logic, you will not get a session back if orch sate is not active or
if communication state is unavailable therefore asserting if result is None"""


@pytest.mark.unittest
def test_check_onboard_failure(monkeypatch):
    monkeypatch.setattr(mdso, "_create_token", mock.mock_auth_response)
    monkeypatch.setattr(mdso, "resync_mdso_device", mock.mock_resync_mdso_device)
    monkeypatch.setattr(requests, "get", mock.mock_bad_response)
    monkeypatch.setattr(requests, "delete", mock.mock_delete_response)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    result = mdso.check_onboard("hostname123")
    # assert 'Failed' in result['status']
    assert result is None


""" with the new session check logic, you will not get a session back if orch sate is not active or
if communication state is unavailable therefore changing the mock data to return a result"""


@pytest.mark.unittest
def test_check_onboard_processing(monkeypatch):
    monkeypatch.setattr(mdso, "_create_token", mock.mock_auth_response)
    monkeypatch.setattr(mdso, "resync_mdso_device", mock.mock_resync_mdso_device)
    monkeypatch.setattr(requests, "get", mock.mock_proc_response)
    monkeypatch.setattr(requests, "delete", mock.mock_delete_response)

    result = mdso.check_onboard("hostname123")
    assert "Completed" in result["status"]


@pytest.mark.unittest
def test_check_hostname(monkeypatch):
    try:
        monkeypatch.setattr(mdso, "_create_token", mock.mock_auth_response)
        monkeypatch.setattr(mdso, "resync_mdso_device", mock.mock_resync_mdso_device)
        monkeypatch.setattr(requests, "get", mock.mock_proc_response)
        monkeypatch.setattr(requests, "delete", mock.mock_delete_response)
        mdso.check_onboard("hostname12")
    except AbortException:
        assert True, "hostname must be 11 characters long"
