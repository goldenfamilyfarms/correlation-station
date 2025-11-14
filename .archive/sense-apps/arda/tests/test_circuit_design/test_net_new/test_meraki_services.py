import pytest

from arda_app.bll.net_new import meraki_services


# Create a mock granite response that has json method
class MockResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


@pytest.mark.unittest
def test_create_meraki(monkeypatch):
    # good test
    mock_granite_resp = MockResponse({"retString": "AMO Updated"})
    monkeypatch.setattr(meraki_services, "post_granite", lambda *args, **kwargs: mock_granite_resp)
    assert meraki_services.create_meraki("temp_payload") == mock_granite_resp.json()


@pytest.mark.unittest
def test_dissociate_meraki(monkeypatch):
    # bad test - response["retString"] != "AMO Updated"
    monkeypatch.setattr(
        meraki_services, "put_granite", lambda *args, **kwargs: MockResponse({"retString": "AMO Not Updated"})
    )
    with pytest.raises(Exception):
        meraki_services.disassociate_meraki("mne_name", "parent_mne")

    # good test
    monkeypatch.setattr(
        meraki_services, "put_granite", lambda *args, **kwargs: MockResponse({"retString": "AMO Updated"})
    )
    assert meraki_services.disassociate_meraki("mne_name", "parent_mne") is None


@pytest.mark.unittest
def test_update_meraki_status(monkeypatch):
    # bad test - response["retString"] != "AMO Updated"
    monkeypatch.setattr(
        meraki_services, "put_granite", lambda *args, **kwargs: MockResponse({"retString": "AMO Not Updated"})
    )
    with pytest.raises(Exception):
        meraki_services.update_meraki_status("mne_name")

    # good test
    monkeypatch.setattr(
        meraki_services, "put_granite", lambda *args, **kwargs: MockResponse({"retString": "AMO Updated"})
    )
    assert meraki_services.update_meraki_status("mne_name") is None


@pytest.mark.unittest
def test_add_mne_to_parentorg(monkeypatch):
    # bad test - response["retString"] != "AMO Updated"
    monkeypatch.setattr(
        meraki_services, "put_granite", lambda *args, **kwargs: MockResponse({"retString": "AMO Not Updated"})
    )
    with pytest.raises(Exception):
        meraki_services.add_mne_to_parentorg("mne_name", "parent_mne", "mne_category")

    # good test
    monkeypatch.setattr(
        meraki_services, "put_granite", lambda *args, **kwargs: MockResponse({"retString": "AMO Updated"})
    )
    assert meraki_services.add_mne_to_parentorg("mne_name", "parent_mne", "mne_category") is None
