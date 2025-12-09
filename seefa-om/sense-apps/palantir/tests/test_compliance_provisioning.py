import json
import logging
import pytest
import requests

from palantir_app.bll import compliance_provisioning
from palantir_app.common.compliance_utils import ComplianceStages
from palantir_app.common.constants import (
    NEW_ORDER_TYPE,
    CHANGE_ORDER_TYPE,
    DESIGN_COMPLIANCE_STAGE,
    FIBER_INTERNET_ACCESS,
    NETWORK_COMPLIANCE_STAGE,
    PATH_STATUS_STAGE,
    COMPLIANT,
)
from palantir_app.dll import granite
from palantir_app.dll import mdso
from tests.mock_data.compliance.compliance import (
    circuit_devices_single_cpe,
    granite_cpe_data_single_cpe,
    circuit_devices_double_cpe,
    granite_cpe_data_double_cpe,
    granite_info_fia_single_cpe,
    fia_post_with_cpe_swap,
    fia_post_with_ip,
    fia_post_no_ip,
    granite_info_eline_single_cpe,
    eline_post_single_cpe_with_ip,
    eline_post_single_cpe_no_ip,
    eline_post_double_cpe_double_ip,
    eline_post_double_cpe_no_ip,
    eline_post_double_cpe_single_ip,
    voice_passing_path,
    voice_two_path,
    voice_designed_path,
    empty_path_elements,
    path_elements,
    compliant_eline_service_mapper,
)


logger = logging.getLogger(__name__)


class DataResp:
    def __init__(self, status_code, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        try:
            with open(self.file_name) as f:
                data = json.load(f)
        except TypeError:
            data = self.file_name
        return data


cid = "51.L1XX.010026..TWCC"


def get_product_id(*args, **kwargs):
    return {"items": [{"id": "TEST PRODUCT ID"}]}


@pytest.mark.unittest
def test_remove_core_devices_single_cpe():
    request = {"remediation_flag": True}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    granite_cpe_data = compliance._remove_core_devices(circuit_devices_single_cpe)
    assert granite_cpe_data == granite_cpe_data_single_cpe


@pytest.mark.unittest
def test_remove_core_devices_double_cpe():
    request = {"remediation_flag": True}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    granite_cpe_data = compliance._remove_core_devices(circuit_devices_double_cpe)
    assert granite_cpe_data == granite_cpe_data_double_cpe


@pytest.mark.unittest
def test_create_service_mapper_post_payload_cpe_swap(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {"LARETXNR1ZW": "10.4.146.247"}
    cpe_swap_data = {
        "LARETXNR1ZW": {
            "designed": {"model": "ETX203AX/2SFP/2UTP2SFP", "vendor": "RAD"},
            "installed": {"model": "FSP 150-GE114PRO-C", "vendor": "ADVA"},
        }
    }
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_info_fia_single_cpe, "FIA", cpe_swap_data)
    assert payload == fia_post_with_cpe_swap


@pytest.mark.unittest
def test_create_service_mapper_post_payload_fia_with_ip(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {"LARETXNR1ZW": "10.4.146.247"}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_info_fia_single_cpe, "FIA")
    assert payload == fia_post_with_ip


@pytest.mark.unittest
def test_create_service_mapper_post_payload_fia_no_ip(monkeypatch):
    request = {"remediation_flag": True}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    device_ips = {}
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_info_fia_single_cpe, "FIA")
    assert payload == fia_post_no_ip


@pytest.mark.unittest
def test_create_service_mapper_post_payload_eline_single_cpe(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {"LARETXNR1ZW": "10.4.146.247"}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_info_eline_single_cpe, "EPL")
    assert payload == eline_post_single_cpe_with_ip


@pytest.mark.unittest
def test_create_service_mapper_post_payload_eline_single_cpe_no_ip(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)

    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_info_eline_single_cpe, "EPL")
    assert payload == eline_post_single_cpe_no_ip


@pytest.mark.unittest
def test_create_service_mapper_post_payload_eline_double_cpe(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {"LARETXNR1ZW": "10.4.146.247", "EGFHTXNR1ZW": "10.4.146.99"}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_cpe_data_double_cpe, "EPL")
    assert payload == eline_post_double_cpe_double_ip


@pytest.mark.unittest
def test_create_service_mapper_post_payload_eline_double_cpe_no_ip(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_cpe_data_double_cpe, "EPL")
    assert payload == eline_post_double_cpe_no_ip


@pytest.mark.unittest
def test_create_service_mapper_post_payload_eline_double_cpe_single_ip(monkeypatch):
    request = {"remediation_flag": True}
    device_ips = {"LARETXNR1ZW": "10.4.146.247"}
    compliance = compliance_provisioning.Initialize(cid, request, NEW_ORDER_TYPE)
    monkeypatch.setattr(mdso, "mdso_get", get_product_id)
    payload = compliance._create_payload(device_ips, granite_cpe_data_double_cpe, "EPL")
    assert payload == eline_post_double_cpe_single_ip


@pytest.mark.unittest
def test_live_check_passing_skip(monkeypatch):
    """Tests _is_circuit_live for the expected exit response for a STL Voice Change order"""
    request = {"remediation_flag": True}

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, voice_passing_path)

    compliance = compliance_provisioning.Initialize("21.IPXN.001628..CHTR", request, CHANGE_ORDER_TYPE)
    monkeypatch.setattr(granite.requests, "get", mocked_get_path_elements_call)
    response = compliance.is_pass_through()
    assert response is True


@pytest.mark.unittest
def test_live_check_two_paths(monkeypatch):
    """Tests _is_circuit_live for a False response from a voice order with two paths(Live, Designed)"""
    request = {"remediation_flag": True}

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, voice_two_path)

    compliance = compliance_provisioning.Initialize("21.IPXN.001628..CHTR", request, CHANGE_ORDER_TYPE)
    monkeypatch.setattr(granite.requests, "get", mocked_get_path_elements_call)
    response = compliance.is_pass_through()
    assert response is False


@pytest.mark.unittest
def test_live_designed_path(monkeypatch):
    """Tests _is_circuit_live for a False response from a voice order a designed path"""
    request = {"remediation_flag": True}

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, voice_designed_path)

    compliance = compliance_provisioning.Initialize("21.IPXN.001628..CHTR", request, CHANGE_ORDER_TYPE)
    monkeypatch.setattr(granite.requests, "get", mocked_get_path_elements_call)
    response = compliance.is_pass_through()
    assert response is False


@pytest.mark.unittest
def test_empty_path_elements(monkeypatch):
    """Tests _is_circuit_live for a False response from an empty path_elements response"""
    request = {"remediation_flag": True}

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, empty_path_elements)

    compliance = compliance_provisioning.Initialize("21.IPXN.001628..CHTR", request, CHANGE_ORDER_TYPE)
    monkeypatch.setattr(granite.requests, "get", mocked_get_path_elements_call)
    response = compliance.is_pass_through()
    assert response is False


cid = "51.L1XX.010026..TWCC"
compliance_status = ComplianceStages.COMPLIANCE_STAGES[NEW_ORDER_TYPE]


@pytest.mark.unittest
def test_check_design_against_order_with_bandwidth(monkeypatch):
    """Tests Bandwidth Check with passing data"""

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "bandwidth": "50 Mbps",
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "pass"


@pytest.mark.unittest
def test_check_design_against_order_with_bandwidth_sf_space(monkeypatch):
    """Tests Bandwidth Check with passing data but with a space in the sf bandwidth"""

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "bandwidth": "50 Mbps ",
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "pass"


@pytest.mark.unittest
def test_check_design_against_order_with_bandwidth_sf_lowercase(monkeypatch):
    """Tests Bandwidth Check with passing data, but lowercase sf data"""

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "bandwidth": "50 mbps",
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "pass"


@pytest.mark.unittest
def test_check_design_against_order_with_bandwidth_sf_wrong(monkeypatch):
    """Tests Bandwidth Check with failing sf data"""

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "bandwidth": "500 Mbps",
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "fail"
    assert check["errors"] == ["bandwidth match failed, design: 50 Mbps, order: 500 Mbps"]


@pytest.mark.unittest
def test_check_design_against_order_with_bandwidth_granite_fail(monkeypatch):
    """Tests Bandwidth Check with incorrect granite data"""

    def mocked_get_path_elements_bw_fail_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia_fail.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_bw_fail_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "bandwidth": "50 Mbps",
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "fail"
    assert check["errors"] == ["bandwidth match failed, design: 500 Mbps, order: 50 Mbps"]


@pytest.mark.unittest
def test_check_design_against_order_with_bandwidth_none(monkeypatch):
    """Tests Bandwidth Check with passing data but with None-type bandwidth"""

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "bandwidth": None,
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "pass"


@pytest.mark.unittest
def test_check_design_against_order_without_bandwidth(monkeypatch):
    """Tests Bandwidth Check with passing data without bandwidth"""

    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }
    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    check = compliance.check_design_against_order(compliance_status)
    assert check["result"] == "pass"


@pytest.mark.unittest
def test_translate_order_product_to_design_product(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    translated_product = compliance._translate_order_product_to_design_product()
    assert translated_product == "COM-DIA"


@pytest.mark.unittest
def test_check_product_name(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_product_name("COM-DIA")
    assert not result["error"]


@pytest.mark.unittest
def test_check_product_name_error(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_product_name("EPL (Fiber)")
    assert result["error"]


@pytest.mark.unittest
def test_check_connector_type(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    granite_data[0]["CONNECTOR_TYPE"] = "LC"
    result = compliance._check_connector_type(granite_data[0])
    assert not result["error"]


@pytest.mark.unittest
def test_check_connector_type_error(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    granite_data[0]["CONNECTOR_TYPE"] = "RJ-45"
    result = compliance._check_connector_type(granite_data[0])
    assert result["error"]


@pytest.mark.unittest
def test_check_ipv4(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_ipv4(granite_data[0])
    assert not result["error"]


@pytest.mark.unittest
def test_check_ipv4_error(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    granite_data[0]["IPV4_ASSIGNED_SUBNETS"] = "71.40.236.24/30"
    result = compliance._check_ipv4(granite_data[0])
    assert result["error"]


@pytest.mark.unittest
def test_check_dia_svc_type(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_dia_svc_type(granite_data[0])
    assert not result["error"]


@pytest.mark.unittest
def test_check_dia_svc_type_error(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "ROUTED",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_dia_svc_type(granite_data[0])
    assert result["error"]


@pytest.mark.unittest
def test_check_bandwidth(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
        "bandwidth": "50 Mbps",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_bandwidth("50 Mbps")
    assert not result["error"]


@pytest.mark.unittest
def test_check_bandwidth_error(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "ipv4": "/29=5",
        "connector_type": "LC",
        "bandwidth": "75 Mbps",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_bandwidth("50 Mbps")
    assert result["error"]


@pytest.mark.unittest
def test_check_compliance_eline_pass(monkeypatch):
    def mocked_path_elements(*args, **kwargs):
        return path_elements

    def mocked_active_resource(*args, **kwargs):
        return compliant_eline_service_mapper

    order_data = {
        "resource_id": "f9859bb0-e081-11ee-a494-11041a385232",
        "order_type": "NEW",
        "product_name": "EPL (Fiber)",
        "connector_type": "RJ45",
        "uni_type": "Access",
        "bandwidth": "75 Mbps",
    }

    monkeypatch.setattr(compliance_provisioning.granite, "get_path_elements_for_cid", mocked_path_elements)
    monkeypatch.setattr(compliance_provisioning, "get_active_resource", mocked_active_resource)
    compliance_provisioning.check_compliance(
        order_data, "51.L1XX.803425..TWCC", NEW_ORDER_TYPE, compliance_status, resource_id="resource_id"
    )
    assert compliance_status == {
        COMPLIANT: True,
        DESIGN_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS,
        NETWORK_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS,
        PATH_STATUS_STAGE: ComplianceStages.NOT_PERFORMED_STATUS,
    }


@pytest.mark.unittest
def test_check_retain_ips(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "retain_ip_address": "Yes",
        "ip_address": "71.40.236.24/29",
        "connector_type": "LC",
        "bandwidth": "75 Mbps",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_ipv4(granite_data[0])
    assert not result["error"]


@pytest.mark.unittest
def test_check_retain_ips_fail(monkeypatch):
    def mocked_get_path_elements_call(*args, **kwargs):
        return DataResp(200, "tests/samples/test_get_path_elements_fia.json")

    monkeypatch.setattr(requests, "get", mocked_get_path_elements_call)
    granite_data = granite.get_path_elements_for_cid(cid)

    check_data = {
        "product_name": FIBER_INTERNET_ACCESS,
        "dia_svc_type": "LAN",
        "uni_type": "Access",
        "retain_ip_address": "Yes",
        "ip_address": "71.40.236.24",
        "connector_type": "LC",
        "bandwidth": "75 Mbps",
    }

    compliance = compliance_provisioning.OrderDesignCompliance(NEW_ORDER_TYPE, granite_data, check_data)
    result = compliance._check_ipv4(granite_data[0])
    assert result["error"]
