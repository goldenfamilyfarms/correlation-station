import json

import pytest

from palantir_app.bll.compliance_disconnect_housekeeping import DisconnectHousekeeping, DisconnectServiceIPs
from palantir_app.common.compliance_utils import ComplianceStages
from palantir_app.common.constants import FIA, IP_RECLAIM_STAGE, IP_DISCONNECT_STAGE, IP_UNSWIP_STAGE, PATH_STATUS_STAGE
from palantir_app.dll import granite, sense
from tests.mock_data.compliance.compliance import (
    crosswalk_ipc_device,
    mock_disconnect_design_data_eline,
    mock_disconnect_designed_path_eline,
    mock_sense_post_ok,
)


class MockResponse:
    def __init__(self, json_data, status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(self.json_data)

    def json(self):
        return self.json_data


@pytest.mark.unittest
def test_ip_release_process(monkeypatch):
    def mocked_sense_post(*args, **kwargs):
        return MockResponse(json_data=mock_sense_post_ok, status_code=200)

    monkeypatch.setattr(sense.requests, "post", mocked_sense_post)

    housekeeping = DisconnectServiceIPs()
    compliance_status = housekeeping.ip_release_process("CID", FIA)
    assert compliance_status[IP_DISCONNECT_STAGE][IP_UNSWIP_STAGE] == "Successful. Additional info: Success"
    assert compliance_status[IP_DISCONNECT_STAGE][IP_RECLAIM_STAGE] == "Successful. Additional info: Success"


@pytest.mark.unittest
def test_set_path_to_decom(monkeypatch):
    endpoint_data = {
        "a_side_endpoint": "WLVGCA167ZW",
        "a_side_address": "2 DOLE DR 91362",
        "a_side_disconnect": "FULL",
        "z_side_endpoint": "CLCYCADB9ZW",
        "z_side_address": "10525 WASHINGTON BLVD 90232",
        "z_side_disconnect": "FULL",
    }
    housekeeping = DisconnectHousekeeping("21.L1XX.990582..TWCC", FIA, endpoint_data)
    housekeeping.disconnect_design_data = mock_disconnect_design_data_eline
    housekeeping.designed_path = mock_disconnect_designed_path_eline

    def mocked_granite_delete(*args, **kwargs):
        return None

    monkeypatch.setattr(granite, "delete_path", mocked_granite_delete)
    decom_path_status = housekeeping.set_path_to_decom()
    assert decom_path_status == {PATH_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS}


@pytest.mark.unittest
def test_get_ipc_cpe_mgmt_ip_dhcp():
    endpoint_data = {
        "a_side_endpoint": "WLVGCA167ZW",
        "a_side_address": "2 DOLE DR 91362",
        "a_side_disconnect": "FULL",
        "z_side_endpoint": "CLCYCADB9ZW",
        "z_side_address": "10525 WASHINGTON BLVD 90232",
        "z_side_disconnect": "FULL",
    }
    housekeeping = DisconnectHousekeeping("21.L1XX.990582..TWCC", FIA, endpoint_data)

    cpe_mgmt_ip = housekeeping._get_ipc_cpe_mgmt_ip(crosswalk_ipc_device["interfaces"])
    assert cpe_mgmt_ip == "Dynamic DHCP"


@pytest.mark.unittest
def test_get_ipc_cpe_mgmt_ip_static():
    endpoint_data = {
        "a_side_endpoint": "WLVGCA167ZW",
        "a_side_address": "2 DOLE DR 91362",
        "a_side_disconnect": "FULL",
        "z_side_endpoint": "CLCYCADB9ZW",
        "z_side_address": "10525 WASHINGTON BLVD 90232",
        "z_side_disconnect": "FULL",
    }
    housekeeping = DisconnectHousekeeping("21.L1XX.990582..TWCC", FIA, endpoint_data)
    crosswalk_ipc_device["interfaces"][0]["ipAddress"] = ["11.11.11.11"]
    crosswalk_ipc_device["interfaces"][0]["addressType"] = ["Static"]
    cpe_mgmt_ip = housekeeping._get_ipc_cpe_mgmt_ip(crosswalk_ipc_device["interfaces"])
    assert cpe_mgmt_ip == "11.11.11.11"
