import json
import logging
from contextlib import contextmanager
from werkzeug.exceptions import BadGateway

import pytest
from pytest import fail

from palantir_app.bll import compliance_provisioning_housekeeping as housekeeping
from palantir_app.common.compliance_utils import ComplianceStages
from palantir_app.common.constants import CHANGE_ORDER_TYPE, DESIGN_COMPLIANCE_STAGE, NEW_ORDER_TYPE, PATH_STATUS_STAGE
from palantir_app.dll import granite
from tests.mock_data.compliance.compliance import (
    mock_granite_elements,
    mock_path_data,
    mock_path_delete_by_parameters_ok,
    mock_path_details_by_cid_designed_status,
    mock_path_details_by_cid_live_and_designed_status,
    mock_path_update_by_parameters_ok,
    mock_granite_elements_shelf_update,
    mock_granite_shelf_uda_cpe,
    mock_granite_shelf_uda_vgw,
    mock_granite_shelf_update_cpe_resp,
    mock_granite_shelf_update_vgw_resp,
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


class TestNewFIAStages:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(NEW_ORDER_TYPE)
        compliance.set_status()
        compliance.status[DESIGN_COMPLIANCE_STAGE] = ComplianceStages.SUCCESS_STATUS
        return compliance.status

    @pytest.mark.unittest
    def test_set_to_live(self, monkeypatch, compliance_status):
        def mocked_path_details_by_cid(*args, **kwargs):
            return MockResponse(json_data=mock_path_details_by_cid_designed_status, status_code=200)

        def mocked_granite_put(*args, **kwargs):
            return MockResponse(json_data=mock_path_update_by_parameters_ok, status_code=200)

        def mocked_parent_stl(*args, **kwargs):
            return None

        monkeypatch.setattr(granite.requests, "get", mocked_path_details_by_cid)
        monkeypatch.setattr(granite.requests, "put", mocked_granite_put)
        monkeypatch.setattr(housekeeping, "update_parent_path_to_live", mocked_parent_stl)

        housekeeping.set_to_live("CID", NEW_ORDER_TYPE, compliance_status)

        assert compliance_status[PATH_STATUS_STAGE] == ComplianceStages.SUCCESS_STATUS


class TestChangeELINEStages:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(CHANGE_ORDER_TYPE)
        compliance.set_status()
        return compliance.status

    @pytest.mark.unittest
    def test_set_to_live_change_path(self, monkeypatch, compliance_status):
        def mocked_path_details_by_cid(*args, **kwargs):
            return MockResponse(json_data=mock_path_details_by_cid_live_and_designed_status, status_code=200)

        def mocked_granite_put(*args, **kwargs):
            return MockResponse(json_data=mock_path_update_by_parameters_ok, status_code=200)

        def mocked_granite_delete(*args, **kwargs):
            return MockResponse(json_data=mock_path_delete_by_parameters_ok, status_code=200)

        def mocked_delete_path_associations(*args, **kwargs):
            return None

        def mocked_delete_path_by_parameters(*args, **kwargs):
            return None

        def mocked_parent_stl(*args, **kwargs):
            return None

        monkeypatch.setattr(granite.requests, "get", mocked_path_details_by_cid)
        monkeypatch.setattr(granite.requests, "put", mocked_granite_put)
        monkeypatch.setattr(granite.requests, "delete", mocked_granite_delete)
        monkeypatch.setattr(granite, "delete_path_associations", mocked_delete_path_associations)
        monkeypatch.setattr(granite, "delete_path_by_parameters", mocked_delete_path_by_parameters)
        monkeypatch.setattr(housekeeping, "update_parent_path_to_live", mocked_parent_stl)

        housekeeping.set_to_live("CID", CHANGE_ORDER_TYPE, compliance_status)

        assert compliance_status[PATH_STATUS_STAGE] == ComplianceStages.SUCCESS_STATUS


class TestNewELINEStages:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(NEW_ORDER_TYPE)
        compliance.set_status()
        return compliance.status

    @pytest.mark.unittest
    def test_remove_existing_live_path(self, monkeypatch, compliance_status):
        def mocked_granite_put(*args, **kwargs):
            return MockResponse(json_data=mock_path_update_by_parameters_ok, status_code=200)

        def mocked_granite_delete(*args, **kwargs):
            return MockResponse(json_data=mock_path_delete_by_parameters_ok, status_code=200)

        def mocked_delete_path_associations(*args, **kwargs):
            return None

        monkeypatch.setattr(granite.requests, "put", mocked_granite_put)
        monkeypatch.setattr(granite.requests, "delete", mocked_granite_delete)
        monkeypatch.setattr(granite, "delete_path_associations", mocked_delete_path_associations)

        path_data = mock_path_details_by_cid_live_and_designed_status

        error = housekeeping._remove_existing_live_path(1, path_data, "CID", compliance_status)
        assert not error


@pytest.mark.unittest
def test_is_valid_current_path_status():
    valid = housekeeping._is_valid_current_path_status("Designed")
    assert valid


@pytest.mark.unittest
def test_is_valid_current_path_status_false():
    valid = housekeeping._is_valid_current_path_status("Live")
    assert not valid


@pytest.mark.unittest
def test_update_path_elements_to_live(monkeypatch):
    def mocked_get_elements(*args, **kwargs):
        return MockResponse(mock_granite_elements, 200)

    def mocked_update_elements(*args, **kwargs):
        return None

    monkeypatch.setattr(granite.requests, "get", mocked_get_elements)
    monkeypatch.setattr(granite.requests, "put", mocked_update_elements)
    error = housekeeping.update_path_elements_to_live("CUS-VOICE-HOSTED", "CID")
    assert not error


@pytest.mark.unittest
def test_get_elements_references(monkeypatch):
    def mocked_get_elements(*args, **kwargs):
        for element in mock_granite_elements:
            element["ELEMENT_STATUS"] = "Designed"
        return MockResponse(mock_granite_elements, 200)

    monkeypatch.setattr(granite.requests, "get", mocked_get_elements)
    elements = housekeeping._get_elements_references("CID", ["NETWORK"])
    assert elements


@pytest.mark.unittest
def test_update_shelf_info(monkeypatch):
    def mocked_get_elements(*args, **kwargs):
        return MockResponse(mock_granite_elements_shelf_update, 200)

    def mocked_get_shelf_uda_cpe(*args, **kwargs):
        return MockResponse(mock_granite_shelf_uda_cpe, 200)

    def mocked_get_shelf_uda_vgw(*args, **kwargs):
        return MockResponse(mock_granite_shelf_uda_vgw, 200)

    def mocked_shelf_update_cpe(*args, **kwargs):
        return MockResponse(mock_granite_shelf_update_cpe_resp, 200)

    def mocked_shelf_update_vgw(*args, **kwargs):
        return MockResponse(mock_granite_shelf_update_vgw_resp, 200)

    monkeypatch.setattr(granite.requests, "get", mocked_get_elements)
    monkeypatch.setattr(granite.requests, "get", mocked_get_shelf_uda_cpe)
    monkeypatch.setattr(granite.requests, "get", mocked_get_shelf_uda_vgw)
    monkeypatch.setattr(granite.requests, "put", mocked_shelf_update_cpe)
    monkeypatch.setattr(granite.requests, "put", mocked_shelf_update_vgw)
    error = housekeeping._update_shelf_info("CID", None, None)
    assert not error


@pytest.mark.unittest
def test_get_status():
    mock_path_data[0]["status"] = "Planned"
    mock_status = housekeeping._get_status(mock_path_data)
    assert mock_status == "Planned"


@pytest.mark.unittest
def test_is_invalid_status():
    mock_path_data[0]["status"] = "Planned"
    status = housekeeping._get_status(mock_path_data)
    invalid = housekeeping._is_invalid_status(status)
    assert invalid is True


@pytest.mark.unittest
def test_is_invalid_status_false():
    mock_path_data[0]["status"] = "Designed"
    status = housekeeping._get_status(mock_path_data)
    invalid = housekeeping._is_invalid_status(status)
    assert invalid is False


@pytest.mark.unittest
def test_change_required():
    mock_path_data[0]["status"] = "Designed"
    status = housekeeping._get_status(mock_path_data)
    required = housekeeping._change_required(status, compliance_status={})
    assert required is True


@pytest.mark.unittest
def test_change_required_false_live_status():
    mock_path_data[0]["status"] = "Live"
    status = housekeeping._get_status(mock_path_data)
    required = housekeeping._change_required(status, compliance_status={})
    assert required is False


@pytest.mark.unittest
def test_change_required_false_live_voice_order_change():
    mock_path_data[0]["status"] = "Live"
    mock_path_data[0]["product_Service_UDA"] = "CUS-VOICE-PRI"
    status = housekeeping._get_status(mock_path_data)
    required = housekeeping._change_required(status, compliance_status={})
    assert required is False


@pytest.mark.unittest
def test_change_required_abandon_ship():
    mock_path_data[0]["status"] = "SPOOKY STATUS"
    status = housekeeping._get_status(mock_path_data)
    with pytest.raises(BadGateway):
        housekeeping._change_required(status, compliance_status={})
