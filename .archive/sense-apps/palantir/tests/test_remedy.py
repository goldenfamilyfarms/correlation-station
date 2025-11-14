from unittest import mock

import pytest

from palantir_app.bll import remedy
from palantir_app.common.compliance_utils import ComplianceStages
from palantir_app.common.constants import (
    FULL_DISCO_ORDER_TYPE,
    IP_DISCONNECT_STAGE,
    ISP_STAGE,
    NETWORK_COMPLIANCE_STAGE,
    PATH_STATUS_STAGE,
    SITE_STATUS_STAGE,
)
from tests.mock_data.compliance.remedy import (
    test_endpoint_data_eline_full_full,
    test_endpoint_data_eline_full_full_create,
    test_endpoint_data_eline_full_partial,
    test_endpoint_data_eline_partial_full,
    test_endpoint_data_fia_full,
    test_granite_data,
    test_granite_data_double,
    test_isp_required_sites_fia,
    test_site_order_data_eline_full_full,
    test_site_order_data_fia,
    test_validated_eline,
    test_validated_fia,
    test_endpoint_data_wavelength,
)


def mock_post_success_z(*args, **kwargs):
    ok_response = mock.MagicMock()
    type(ok_response).status_code = mock.PropertyMock(return_value=201)
    ok_response.json.return_value = {"work_order": "WO123456TEST"}
    return ok_response


def mock_post_success_a(*args, **kwargs):
    ok_response = mock.MagicMock()
    type(ok_response).status_code = mock.PropertyMock(return_value=201)
    ok_response.json.return_value = {"work_order": "WO234567MEOW"}
    return ok_response


class TestSingleFull:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(FULL_DISCO_ORDER_TYPE)
        compliance.set_status()
        compliance.status[NETWORK_COMPLIANCE_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[IP_DISCONNECT_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[PATH_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[SITE_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[ISP_STAGE] = ComplianceStages.NOT_PERFORMED_STATUS
        return compliance.status

    @pytest.mark.unittest
    def test_create_remedy_disconnect_ticket_full_single_sided_success(self, monkeypatch, compliance_status):
        monkeypatch.setattr(remedy, "post_sense", mock_post_success_z)
        remedy.create_remedy_disconnect_ticket(
            cid="51.L1XX.010158..TWCC",
            endpoint_data=test_endpoint_data_fia_full,
            design_data=test_granite_data,
            site_order_data=test_site_order_data_fia,
            compliance_status=compliance_status,
        )
        assert compliance_status == {
            NETWORK_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS,
            IP_DISCONNECT_STAGE: ComplianceStages.SUCCESS_STATUS,
            PATH_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS,
            SITE_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS,
            ISP_STAGE: ComplianceStages.SUCCESS_STATUS,
            "ISP Information": [
                {
                    "ispDisconnectTicket": "WO123456TEST",
                    "site": "1234 Alden Marshall Pkwy Austin TX 78759",
                    "engineeringPage": "ENG-01234567",
                }
            ],
        }


class TestDoubleFull:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(FULL_DISCO_ORDER_TYPE)
        compliance.set_status()
        compliance.status[NETWORK_COMPLIANCE_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[IP_DISCONNECT_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[PATH_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[SITE_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[ISP_STAGE] = ComplianceStages.NOT_PERFORMED_STATUS
        return compliance.status

    @pytest.mark.unittest
    def test_create_remedy_disconnect_ticket_full_full_success(self, monkeypatch, compliance_status):
        remedy_post_response = [mock_post_success_z(), mock_post_success_a()]
        mock_remedy_response = mock.Mock(side_effect=remedy_post_response)
        monkeypatch.setattr(remedy, "post_sense", mock_remedy_response)
        remedy.create_remedy_disconnect_ticket(
            cid="51.L1XX.010158..TWCC",
            endpoint_data=test_endpoint_data_eline_full_full_create,
            design_data=test_granite_data_double,
            site_order_data=test_site_order_data_eline_full_full,
            compliance_status=compliance_status,
        )
        assert compliance_status == {
            NETWORK_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS,
            IP_DISCONNECT_STAGE: ComplianceStages.SUCCESS_STATUS,
            PATH_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS,
            SITE_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS,
            ISP_STAGE: ComplianceStages.SUCCESS_STATUS,
            "ISP Information": [
                {
                    "ispDisconnectTicket": "WO123456TEST",
                    "site": "1208 S KINGSHIGHWAY ST 63703",
                    "engineeringPage": "ENG-01234567",
                },
                {
                    "ispDisconnectTicket": "WO234567MEOW",
                    "site": "1015 LOCUST ST 63101",
                    "engineeringPage": "ENG-12345678",
                },
            ],
        }


class TestCorrelateSingle:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(FULL_DISCO_ORDER_TYPE)
        compliance.set_status()
        compliance.status[NETWORK_COMPLIANCE_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[IP_DISCONNECT_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[PATH_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[SITE_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[ISP_STAGE] = ComplianceStages.NOT_PERFORMED_STATUS
        return compliance.status

    @pytest.mark.unittest
    def test_correlate_eng_page_to_full_disco_address_single_sided(self, compliance_status):
        test_fia_data = remedy.correlate_eng_page_to_full_disco_address(
            test_endpoint_data_fia_full, test_site_order_data_fia, compliance_status
        )
        assert test_fia_data == [
            {"z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"}}
        ]

    @pytest.mark.unittest
    def test_correlate_eng_page_to_full_disco_address_double_sided_partial_full(self, compliance_status):
        test_eline_partial_full_data = remedy.correlate_eng_page_to_full_disco_address(
            test_endpoint_data_eline_partial_full, test_site_order_data_fia, compliance_status
        )
        assert test_eline_partial_full_data == [
            {"z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"}}
        ]

    @pytest.mark.unittest
    def test_correlate_eng_page_to_full_disco_address_double_sided_full_partial(self, compliance_status):
        test_eline_full_partial_data = remedy.correlate_eng_page_to_full_disco_address(
            test_endpoint_data_eline_full_partial,
            test_endpoint_data_eline_full_partial["site_order_data"],
            compliance_status,
        )
        assert test_eline_full_partial_data == [
            {"a": {"address": "334 Moonbeam Ave Austin TX 78759", "engineering_page": "ENG-12345678"}}
        ]

    @pytest.mark.unittest
    def test_create_full_site_order_data_fia(self, compliance_status):
        full_data = remedy.create_full_site_order_data(
            compliance_status, test_endpoint_data_fia_full, test_site_order_data_fia, side="z"
        )
        assert full_data == {
            "z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"}
        }

    @pytest.mark.unittest
    def test_create_full_site_order_data_eline_z_side(self, compliance_status):
        full_data = remedy.create_full_site_order_data(
            compliance_status, test_endpoint_data_eline_partial_full, test_site_order_data_fia, side="z"
        )
        assert full_data == {
            "z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"}
        }

    @pytest.mark.unittest
    def test_create_full_site_order_data_eline_a_side(self, compliance_status):
        full_data = remedy.create_full_site_order_data(
            compliance_status,
            test_endpoint_data_eline_full_partial,
            test_endpoint_data_eline_full_partial["site_order_data"],
            side="a",
        )
        assert full_data == {"a": {"address": "334 Moonbeam Ave Austin TX 78759", "engineering_page": "ENG-12345678"}}


class TestCorrelateDouble:
    @pytest.fixture(scope="class")
    def compliance_status(self):
        compliance = ComplianceStages(FULL_DISCO_ORDER_TYPE)
        compliance.set_status()
        compliance.status[NETWORK_COMPLIANCE_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[IP_DISCONNECT_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[PATH_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[SITE_STATUS_STAGE] = ComplianceStages.SUCCESS_STATUS
        compliance.status[ISP_STAGE] = ComplianceStages.NOT_PERFORMED_STATUS
        return compliance.status

    @pytest.mark.unittest
    def test_correlate_eng_page_to_full_disco_address_double_sided_full_full(self, compliance_status):
        test_eline_full_full_data = remedy.correlate_eng_page_to_full_disco_address(
            test_endpoint_data_eline_full_full, test_site_order_data_eline_full_full, compliance_status
        )
        assert test_eline_full_full_data == [
            {
                "z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"},
                "a": {"address": "334 Moonbeam Ave Austin TX 78759", "engineering_page": "ENG-12345678"},
            }
        ]

    @pytest.mark.unittest
    def test_create_full_site_order_data_eline_a_and_z_side(self, compliance_status):
        z_side_full_data = {
            "z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"}
        }
        full_data = remedy.create_full_site_order_data(
            compliance_status,
            test_endpoint_data_eline_partial_full,
            test_site_order_data_eline_full_full,
            side="a",
            full_data=z_side_full_data,
        )
        assert full_data == {
            "z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759", "engineering_page": "ENG-01234567"},
            "a": {"address": "334 Moonbeam Ave Austin TX 78759", "engineering_page": "ENG-12345678"},
        }


# only single sided allowed for unvalidated tests
@pytest.mark.unittest
def test_get_engineering_page_unvalidated_single_sided():
    test_engineering_page = remedy.get_engineering_page(
        site="z", site_order_data=test_site_order_data_fia, validated_full_sites=None
    )
    assert test_engineering_page == "ENG-01234567"


# only single sided allowed for unvalidated tests
@pytest.mark.unittest
def test_get_full_disco_address_unvalidated_single_sided():
    test_address = remedy.get_full_disco_address(
        site="z", isp_required_sites=test_isp_required_sites_fia, validated_full_sites=None
    )
    assert test_address == "1234 Alden Marshall Pkwy Austin TX 78759"


@pytest.mark.unittest
def test_get_engineering_page_validated_z_side():
    test_engineering_page = remedy.get_engineering_page(
        site="z", site_order_data=test_site_order_data_fia, validated_full_sites=test_validated_fia
    )
    assert test_engineering_page == "ENG-23456789"


@pytest.mark.unittest
def test_get_engineering_page_validated_a_side():
    test_engineering_page = remedy.get_engineering_page(
        site="a", site_order_data=test_site_order_data_eline_full_full, validated_full_sites=test_validated_eline
    )
    assert test_engineering_page == "ENG-34567890"


@pytest.mark.unittest
def test_get_full_disco_address_validated_z_side():
    test_address = remedy.get_full_disco_address(
        site="z", isp_required_sites=test_isp_required_sites_fia, validated_full_sites=test_validated_fia
    )
    assert test_address == "1234 Bananas St Austin TX 78759"


@pytest.mark.unittest
def test_get_full_disco_address_validated_a_side():
    test_address = remedy.get_full_disco_address(
        site="a", isp_required_sites=test_isp_required_sites_fia, validated_full_sites=test_validated_eline
    )
    assert test_address == "5678 Pineapple Cove Austin TX 78759"


@pytest.mark.unittest
def test_create_notes():
    element_data = test_granite_data["z"]["element_data"]
    test_notes = remedy.create_notes("21.L1XX.990582..TWCC", element_data, "300 24TH ST NW")
    assert (
        test_notes
        == "COGENT COMMUNICATIONS, INC-CHTR-ICOMS :: 300 24TH ST NW :: Single-Customer Disconnect :: 21.L1XX.990582..TWCC :: OWTNMN020QW:GE-0/0/29"  # noqa
    )


@pytest.mark.unittest
def test_create_remedy_payload_no_validation():
    test_payload = remedy.create_remedy_payload(
        site="z",
        cid="21.L1XX.990582..TWCC",
        isp_required_sites=test_isp_required_sites_fia,
        engineering_page="ENG-01234567",
        design_data=test_granite_data,
        endpoint_data=test_endpoint_data_wavelength,
        validated_full_sites=None,
    )
    assert test_payload == {
        "circuit_id": "21.L1XX.990582..TWCC",
        "address": "1234 Alden Marshall Pkwy Austin TX 78759",
        "customer_name": "COGENT COMMUNICATIONS, INC-CHTR-ICOMS",
        "hub_clli": "OWTNMN02",
        "equipment_id": "OWTNMN020QW",
        "port_access_id": "GE-0/0/29",
        "order_number": "ENG-01234567",
        "notes": "COGENT COMMUNICATIONS, INC-CHTR-ICOMS :: 1234 Alden Marshall Pkwy Austin TX 78759 :: Single-Customer Disconnect :: 21.L1XX.990582..TWCC :: OWTNMN020QW:GE-0/0/29",  # noqa
        "summary": "NYCLNYRG-TWC/HUB C-MANHATTAN :: Single-Customer Disconnect",
        "additional_details": None,
        "wavelength": "1310 nm",
    }
