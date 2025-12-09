import pytest

from unittest import mock

from palantir_app.bll import compliance_disconnect
from palantir_app.common.constants import FIA
from palantir_app.dll import granite
from tests.mock_data.compliance.topologies import fia, eline
from tests.mock_data.compliance.compliance import circuit_data_docsis_disco


def mock_get_granite_count_partial(*args, **kwargs):
    return 3


def mock_get_granite_count_full(*args, **kwargs):
    return 2


compliance = compliance_disconnect.Initialize(
    "51.L1XX.010158..TWCC",
    {"order_type": "PARTIAL DISCONNECT", "product_name": "Fiber Internet Access"},
    "PARTIAL DISCONNECT",
)


@pytest.mark.unittest
def test_get_endpoint_by_side_fia_partial(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_partial)
    impact = compliance._get_endpoint_by_side(topology=fia, side="z_side", topology_index_type=FIA)
    assert impact == {
        "z_side_disconnect": "PARTIAL",
        "z_side_endpoint": "CNI2TXA49ZW",
        "z_side_address": "11921 N MO PAC EXPY 78739",
        "service_type": "FIA",
    }


@pytest.mark.unittest
def test_get_endpoint_by_side_fia_full(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_full)
    impact = compliance._get_endpoint_by_side(topology=fia, side="z_side", topology_index_type=FIA)
    assert impact == {
        "z_side_disconnect": "FULL",
        "z_side_endpoint": "CNI2TXA49ZW",
        "z_side_address": "11921 N MO PAC EXPY 78739",
        "service_type": "FIA",
    }


@pytest.mark.unittest
def test_get_impact_by_side_eline_partial(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_partial)
    impact = compliance._get_endpoint_by_side(topology=eline, side="a_side", topology_index_type="ELINE")
    assert impact == {
        "a_side_disconnect": "PARTIAL",
        "a_side_endpoint": "AUSDTXIR2CW",
        "a_side_address": "11921 N MOPAC EXPY 78759",
        "service_type": "ELINE",
    }


@pytest.mark.unittest
def test_get_impact_by_side_eline_full(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_full)
    impact = compliance._get_endpoint_by_side(topology=eline, side="z_side", topology_index_type="ELINE")
    assert impact == {
        "z_side_disconnect": "FULL",
        "z_side_endpoint": "CNI5TXR38ZW",
        "z_side_address": "11921 N MOPAC EXPY 78759",
        "service_type": "ELINE",
    }


def mock_get_fia_topology(*args, **kwargs):
    return fia


@pytest.mark.unittest
def test_get_granite_impact_analysis_fia_partial(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_partial)
    monkeypatch.setattr(compliance_disconnect, "sense_get", mock_get_fia_topology)
    response = compliance.get_endpoint_data_from_design()
    assert response == {
        "z_side_disconnect": "PARTIAL",
        "z_side_endpoint": "CNI2TXA49ZW",
        "z_side_address": "11921 N MO PAC EXPY 78739",
        "service_type": "FIA",
    }


@pytest.mark.unittest
def test_get_granite_impact_analysis_fia_full(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_full)
    monkeypatch.setattr(compliance_disconnect, "sense_get", mock_get_fia_topology)
    response = compliance.get_endpoint_data_from_design()
    assert response == {
        "z_side_disconnect": "FULL",
        "z_side_endpoint": "CNI2TXA49ZW",
        "z_side_address": "11921 N MO PAC EXPY 78739",
        "service_type": "FIA",
    }


def mock_get_eline_topology(*args, **kwargs):
    return eline


@pytest.mark.unittest
def test_get_granite_impact_analysis_eline_partial_partial(monkeypatch):
    monkeypatch.setattr(granite, "get_equipment_count", mock_get_granite_count_partial)
    monkeypatch.setattr(compliance_disconnect, "sense_get", mock_get_eline_topology)
    response = compliance.get_endpoint_data_from_design()
    assert response == {
        "a_side_disconnect": "PARTIAL",
        "a_side_endpoint": "AUSDTXIR2CW",
        "a_side_address": "11921 N MOPAC EXPY 78759",
        "z_side_disconnect": "PARTIAL",
        "z_side_endpoint": "CNI5TXR38ZW",
        "z_side_address": "11921 N MOPAC EXPY 78759",
        "service_type": "ELINE",
    }


@pytest.mark.unittest
def test_get_granite_impact_analysis_eline_partial_full(monkeypatch):
    granite_count_return = [3, 2]
    mock_granite_count = mock.Mock(side_effect=granite_count_return)
    monkeypatch.setattr(granite, "get_equipment_count", mock_granite_count)
    monkeypatch.setattr(compliance_disconnect, "sense_get", mock_get_eline_topology)
    response = compliance.get_endpoint_data_from_design()
    assert response == {
        "a_side_disconnect": "PARTIAL",
        "a_side_endpoint": "AUSDTXIR2CW",
        "a_side_address": "11921 N MOPAC EXPY 78759",
        "z_side_disconnect": "FULL",
        "z_side_endpoint": "CNI5TXR38ZW",
        "z_side_address": "11921 N MOPAC EXPY 78759",
        "service_type": "ELINE",
    }


@pytest.mark.unittest
def test_get_granite_impact_analysis_eline_full_full(monkeypatch):
    granite_count_return = [2, 2]
    mock_granite_count = mock.Mock(side_effect=granite_count_return)
    monkeypatch.setattr(granite, "get_equipment_count", mock_granite_count)
    monkeypatch.setattr(compliance_disconnect, "sense_get", mock_get_eline_topology)
    response = compliance.get_endpoint_data_from_design()
    assert response == {
        "a_side_disconnect": "FULL",
        "a_side_endpoint": "AUSDTXIR2CW",
        "a_side_address": "11921 N MOPAC EXPY 78759",
        "z_side_disconnect": "FULL",
        "z_side_endpoint": "CNI5TXR38ZW",
        "z_side_address": "11921 N MOPAC EXPY 78759",
        "service_type": "ELINE",
    }


@pytest.mark.unittest
def test_get_granite_impact_analysis_eline_full_partial(monkeypatch):
    granite_count_return = [2, 3]
    mock_granite_count = mock.Mock(side_effect=granite_count_return)
    monkeypatch.setattr(granite, "get_equipment_count", mock_granite_count)
    monkeypatch.setattr(compliance_disconnect, "sense_get", mock_get_eline_topology)
    response = compliance.get_endpoint_data_from_design()
    assert response == {
        "a_side_disconnect": "FULL",
        "a_side_endpoint": "AUSDTXIR2CW",
        "a_side_address": "11921 N MOPAC EXPY 78759",
        "z_side_disconnect": "PARTIAL",
        "z_side_endpoint": "CNI5TXR38ZW",
        "z_side_address": "11921 N MOPAC EXPY 78759",
        "service_type": "ELINE",
    }


@pytest.mark.unittest
def test_get_docsis_endpoint_data(monkeypatch):
    def mocked_circuit_data(*args, **kwargs):
        return circuit_data_docsis_disco

    def mocked_paths_from_site(*args, **kwargs):
        return ["50.TGXX.000050..TWCC", "Circuit ID 2"]

    monkeypatch.setattr(compliance_disconnect, "denodo_get", mocked_circuit_data)
    monkeypatch.setattr(granite, "get_paths_from_site", mocked_paths_from_site)
    compliance = compliance_disconnect.Initialize(
        "50.TGXX.000050..TWCC",
        {
            "resource_id": "passthrough",
            "order_type": "FULL DISCONNECT",
            "product_name": "SIP - Trunk (DOCSIS)",
            "site_order_data": [
                {
                    "engineering_page": "ENG-01234567",
                    "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759",
                }
            ],
        },
        "FULL DISCONNECT",
    )
    endpoint_data = compliance._get_docsis_endpoint_data()
    assert endpoint_data == {
        "z_side_endpoint": "LSVNKYFDG01",
        "z_side_address": "600 MARRET AVE",
        "docsis_service_name": "COAX VOICE-SIP",
        "z_side_disconnect": "PARTIAL",
    }


@pytest.mark.unittest
def test_get_impact_analysis_from_site_full(monkeypatch):
    def mocked_paths_from_site(*args, **kwargs):
        return ["50.TGXX.000050..TWCC"]

    monkeypatch.setattr(granite, "get_paths_from_site", mocked_paths_from_site)
    compliance = compliance_disconnect.Initialize(
        "50.TGXX.000050..TWCC",
        {
            "resource_id": "passthrough",
            "order_type": "FULL DISCONNECT",
            "product_name": "SIP - Trunk (DOCSIS)",
            "site_order_data": [
                {
                    "engineering_page": "ENG-01234567",
                    "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759",
                }
            ],
        },
        "FULL DISCONNECT",
    )
    impact = compliance._get_impact_analysis_from_site(349367)
    assert impact == "FULL"


@pytest.mark.unittest
def test_get_impact_analysis_from_site_partial(monkeypatch):
    def mocked_paths_from_site(*args, **kwargs):
        return ["50.TGXX.000050..TWCC", "Circuit ID 2"]

    monkeypatch.setattr(granite, "get_paths_from_site", mocked_paths_from_site)
    compliance = compliance_disconnect.Initialize(
        "50.TGXX.000050..TWCC",
        {
            "resource_id": "passthrough",
            "order_type": "FULL DISCONNECT",
            "product_name": "SIP - Trunk (DOCSIS)",
            "site_order_data": [
                {
                    "engineering_page": "ENG-01234567",
                    "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759",
                }
            ],
        },
        "FULL DISCONNECT",
    )
    impact = compliance._get_impact_analysis_from_site(349367)
    assert impact == "PARTIAL"
