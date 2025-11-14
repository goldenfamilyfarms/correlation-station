import pytest
import requests

from arda_app.dll import ipc as ipc_ops
from common_sense.common.errors import AbortException


class MockResp:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        return {"access_token": "you got a token!", "happy_days": "are here again"}

    def text(self):
        return ""


class NoToken:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        return {"happy_days": "are here again"}


@pytest.mark.unittest
def test_get_ipc_success(monkeypatch):
    def mock_token(*args, **kwargs):
        return MockResp(200)

    def mock_get_200(*args, **kwargs):
        return MockResp(200)

    monkeypatch.setattr(requests, "post", mock_token)
    monkeypatch.setattr(requests, "get", mock_get_200)
    r = ipc_ops.get_ipc(url="hello")
    assert r
    assert "are here again" in r.get("happy_days")


@pytest.mark.unittest
def test_get_ipc_fail_on_timeout(monkeypatch):
    def mock_get_connection_error(*args, **kwargs):
        raise ConnectionError

    monkeypatch.setattr(requests, "get", mock_get_connection_error)

    try:
        ipc_ops.get_ipc(url="hello")
    except AbortException as e:
        assert e.code == 500 and "timeout" in e.data["message"]


@pytest.mark.unittest
def test_get_ipc_fail_on_unknown_status_code(monkeypatch):
    def mock_get_weirdo_error(*args, **kwargs):
        return MockResp(909)

    monkeypatch.setattr(requests, "get", mock_get_weirdo_error)

    try:
        ipc_ops.get_ipc(url="hello")
    except AbortException as e:
        assert e.code == 500 and "unexpected status code" in e.data["message"]


@pytest.mark.unittest
def test_post_ipc_success(monkeypatch):
    def mock_get_200(*args, **kwargs):
        return MockResp(200)

    monkeypatch.setattr(requests, "post", mock_get_200)
    r = ipc_ops.post_ipc(url="hello", payload={"hagbard": "celine"})
    assert "are here again" in r.get("happy_days")


@pytest.mark.unittest
def test_post_ipc_fail_on_timeout(monkeypatch):
    def mock_get_connection_error(*args, **kwargs):
        raise ConnectionError

    monkeypatch.setattr(requests, "post", mock_get_connection_error)

    try:
        ipc_ops.post_ipc(url="hello", payload={"hagbard": "celine"})
    except AbortException as e:
        assert e.code == 500 and "timeout" in e.data["message"]


@pytest.mark.unittest
def test_post_ipc_fail_on_unknown_status_code(monkeypatch):
    def mock_get_weirdo_error(*args, **kwargs):
        return MockResp(909)

    monkeypatch.setattr(requests, "post", mock_get_weirdo_error)

    try:
        ipc_ops.post_ipc(url="hello", payload={"hagbard": "celine"})
    except AbortException as e:
        assert e.code == 500 and "unexpected status code" in e.data["message"]
