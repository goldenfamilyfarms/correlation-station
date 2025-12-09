import json
import logging
from contextlib import contextmanager
import pytest
from pytest import fail, raises

from palantir_app.dll import granite
from tests.mock_data.compliance.compliance import (
    mock_path_associations_delete,
    mock_path_associations_delete_fail,
    mock_path_data,
    mock_path_delete_by_parameters_fail,
    mock_path_delete_by_parameters_ok,
    mock_path_update_by_parameters_502,
    mock_path_update_by_parameters_missing_status,
    mock_path_update_by_parameters_ok,
    mock_path_update_by_parameters_wrong_status,
    mock_shelf_delete_fail,
    mock_shelf_delete_ok,
    mock_site_delete_fail,
    mock_site_delete_ok,
    mock_transport_data,
    mock_granite_elements,
    mock_path_details_by_cid_live_and_designed_status,
)

logger = logging.getLogger(__name__)


@contextmanager
def not_raises(exception):
    try:
        yield
    except exception:
        raise fail("DID RAISE {0}".format(exception))


class MockResponse:
    def __init__(self, json_data, status_code: int = None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(self.json_data)

    def json(self):
        return self.json_data


@pytest.mark.unittest
def test_path_update_by_parameters_ok(monkeypatch):
    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_update_by_parameters_ok, status_code=200)

    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)

    update_params = {"PATH_STATUS": "LIVE"}
    response = granite.update_path_by_parameters(update_params)
    assert response == "Successful"


@pytest.mark.unittest
def test_path_update_by_paramters_wrong_status(monkeypatch):
    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_update_by_parameters_wrong_status, status_code=500)

    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)
    update_params = {"PATH_STATUS": "LIVE"}
    with raises(Exception):
        granite.update_path_by_parameters(update_params)


@pytest.mark.unittest
def test_path_update_by_paramters_502(monkeypatch):
    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_update_by_parameters_502, status_code=500)

    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)
    update_params = {"PATH_STATUS": "LIVE"}
    with raises(Exception):
        granite.update_path_by_parameters(update_params)


@pytest.mark.unittest
def test_path_update_by_paramters_missing_status(monkeypatch):
    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_update_by_parameters_missing_status, status_code=500)

    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)
    update_params = {"PATH_STATUS": "LIVE"}
    with raises(Exception):
        granite.update_path_by_parameters(update_params)


@pytest.mark.unittest
def test_path_delete_by_parameters(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_path_delete_by_parameters_ok, status_code=200)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    update_params = {"CIRC_PATH_INST_ID": "11111", "PATH_NAME": "CID"}
    with not_raises(Exception):
        granite.delete_path_by_parameters(update_params)


@pytest.mark.unittest
def test_path_delete_by_parameters_fail_delete(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_path_delete_by_parameters_fail, status_code=400)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    update_params = {"CIRC_PATH_INST_ID": "11111", "PATH_NAME": "CID"}
    error = granite.delete_path_by_parameters(update_params)
    assert "Granite-Delete Path Errored" in error


@pytest.mark.unittest
def test_delete_granite_path_associations(monkeypatch):
    def mocked_requests_get(*args, **kwargs):
        return MockResponse(json_data=mock_transport_data, status_code=200)

    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_associations_delete, status_code=200)

    monkeypatch.setattr(granite.requests, "get", mocked_requests_get)
    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)

    error = granite.delete_path_associations(mock_transport_data, "CID")
    assert not error


@pytest.mark.unittest
def test_delete_granite_path_associations_fail(monkeypatch):
    def mocked_requests_get(*args, **kwargs):
        return MockResponse(json_data=mock_transport_data, status_code=200)

    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_associations_delete_fail, status_code=200)

    monkeypatch.setattr(granite.requests, "get", mocked_requests_get)
    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)

    error = granite.delete_path_associations(mock_transport_data, "CID")
    assert error


@pytest.mark.unittest
def test_delete_path(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_path_delete_by_parameters_ok, status_code=200)

    def mocked_requests_get(*args, **kwargs):
        return MockResponse(json_data=mock_transport_data, status_code=200)

    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_associations_delete, status_code=200)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    monkeypatch.setattr(granite.requests, "get", mocked_requests_get)
    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)

    error = granite.delete_path(mock_path_data, "CID", "Decommissioned")
    assert not error


@pytest.mark.unittest
def test_delete_path_fail(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_path_delete_by_parameters_fail, status_code=400)

    def mocked_requests_get(*args, **kwargs):
        return MockResponse(json_data=mock_transport_data, status_code=200)

    def mocked_requests_put(*args, **kwargs):
        return MockResponse(json_data=mock_path_associations_delete, status_code=200)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    monkeypatch.setattr(granite.requests, "get", mocked_requests_get)
    monkeypatch.setattr(granite.requests, "put", mocked_requests_put)

    error = granite.delete_path(mock_path_data, "CID", "Decommissioned")
    assert error


@pytest.mark.unittest
def test_get_transport_path(monkeypatch):
    def mocked_requests_get(*args, **kwargs):
        return MockResponse(json_data=mock_transport_data, status_code=200)

    monkeypatch.setattr(granite.requests, "get", mocked_requests_get)

    tid = "NYCNNYBU1ZW"
    response = granite.get_transport_path(mock_granite_elements, tid)
    assert response == mock_transport_data


@pytest.mark.unittest
def test_delete_granite_site(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_site_delete_ok, status_code=200)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    error = granite.delete_site("454545")
    assert not error


@pytest.mark.unittest
def test_delete_granite_site_fail(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_site_delete_fail, status_code=500)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    error = granite.delete_site("454545")
    assert error


@pytest.mark.unittest
def test_delete_granite_shelf(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_shelf_delete_ok, status_code=200)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    error = granite.delete_shelf("454545")
    assert not error


@pytest.mark.unittest
def test_delete_granite_shelf_fail(monkeypatch):
    def mocked_requests_delete(*args, **kwargs):
        return MockResponse(json_data=mock_shelf_delete_fail, status_code=200)

    monkeypatch.setattr(granite.requests, "delete", mocked_requests_delete)
    error = granite.delete_shelf("454545")
    assert error


@pytest.mark.unittest
def test_get_all_revisions():
    revisions, count = granite.get_all_revisions(mock_path_details_by_cid_live_and_designed_status)
    assert revisions, count == (["1", "2"], 2)


@pytest.mark.unittest
def test_get_latest_revision():
    latest_revision = granite.get_latest_revision(["1", "2"])
    assert latest_revision == "2"
