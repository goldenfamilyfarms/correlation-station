import logging
from base64 import b64encode

import pytest

from fastapi.responses import JSONResponse
from common_sense.common.errors import AbortException
from arda_app.common import auth_config


from copy import deepcopy

logger = logging.getLogger(__name__)

payload = {
    "a_side_info": {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "product_family": "Dedicated Internet Service",
        "engineering_id": "ENG-03413018",
        "cid": "84.L4XX.000058..CHTR",
        "pid": "3029803",
        "legacy_company": "Charter",
        "service_location_address": "11921 N. Mopac Expwy, Austin, TX 78759",
        "build_type": "Home Run",
        "fiber_building_serviceability_status": "On Net",
        "bw_speed": "200",
        "bw_unit": "Mbps",
        "agg_bandwidth": "200Mbps",
        "connector_type": "LC",
        "uni_type": "Access",
        "spectrum_primary_enni": "cid",
        "primary_vlan": "cid",
        "class_of_service_type": "Gold",
        "class_of_service_needed": "yes",
        "related_order": "epr",
        "a_location": "11921 N. Mopac Expwy, Austin, TX 78759",
        "z_location": "11921 N. Mopac Expwy, Austin, TX 78759",
    },
    "z_side_info": {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "product_family": "Dedicated Internet Service",
        "engineering_id": "ENG-03413018",
        "cid": "84.L4XX.000058..CHTR",
        "related_cid": "84.L4XX.000058..CHTR",
        "pid": "3029803",
        "legacy_company": "Charter",
        "service_location_address": "11921 N. Mopac Expwy, Austin, TX 78759",
        "build_type": "Home Run",
        "fiber_building_serviceability_status": "On Net",
        "bw_speed": "200",
        "bw_unit": "Mbps",
        "agg_bandwidth": "200Mbps",
        "connector_type": "LC",
        "uni_type": "Access",
        "primary_fia_service_type": "Routed",
        "usable_ip_addresses_requested": "/30",
        "retain_ip_addresses": "no",
        "spectrum_primary_enni": "cid",
        "primary_vlan": "cid",
        "class_of_service_type": "Gold",
        "class_of_service_needed": "yes",
        "related_order": "epr",
        "a_location": "11921 N. Mopac Expwy, Austin, TX 78759",
        "z_location": "11921 N. Mopac Expwy, Austin, TX 78759",
        "create_new_elan_instance": "Yes",
        "customers_elan_name": "string",
        "billing_account_ordering_customer": "string",
        "network_platform": "Legacy",
        "number_of_b_channels": "integer",
        "number_of_analog_lines": "integer",
        "number_of_native_lines": "integer",
        "number_of_ported_lines": "integer",
        "number_of_circuits_in_group": "integer",
        "granite_site_name": "string",
    },
}

url = "/arda/v1/build_circuit_design"
credentials = b64encode(b"sense_api:$en$e_api").decode("utf-8")
sense_usr, sense_pass = auth_config.SENSE_TEST_SWAGGER_USER, auth_config.SENSE_TEST_SWAGGER_PASS
head = {"accept": "application/json"}
auth = (sense_usr, sense_pass)

home_run_payload = payload
home_run_payload["a_side_info"]["build_type"] = "home_run"
home_run_payload["a_side_info"]["clli"] = "ATSCCAAB"
home_run_payload["z_side_info"]["build_type"] = "home_run"
home_run_payload["z_side_info"]["clli"] = "ATSCCAAB"


def test_build_circuit_design(client):
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_build_circuit_design_with_carrier_FIA(monkeypatch, client):
    test_payload = deepcopy(home_run_payload)
    test_payload["a_side_info"]["product_name"] = "Carrier Fiber Internet Access"
    test_payload["z_side_info"]["product_name"] = "Carrier Fiber Internet Access"

    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)
    logger.debug("UNIT TEST: test_build_circuit_design_with_carrier_FIA")
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_build_circuit_design_with_WIA(monkeypatch, client):
    test_payload = deepcopy(home_run_payload)
    test_payload["z_side_info"]["product_name"] = "Wireless Internet Access-Primary-Out of Footprint"

    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)
    logger.debug("UNIT TEST: test_build_circuit_design_with_WIA")
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_build_circuit_design_with_missing_build_type_for_QC(monkeypatch, client):
    test_payload = deepcopy(home_run_payload)
    test_payload["a_side_info"]["product_name"] = "Fiber Internet Access"
    test_payload["a_side_info"]["service_type"] = "net_new_qc"
    test_payload["a_side_info"]["build_type"] = "Null"
    test_payload["z_side_info"]["product_name"] = "Carrier E-Access (Fiber)"
    test_payload["z_side_info"]["service_type"] = "net_new_qc"
    test_payload["z_side_info"].pop("build_type")

    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)
    logger.debug("UNIT TEST: test_build_circuit_design_with_missing_build_type_for_QC")
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_build_circuit_design_with_mock_response_success(monkeypatch, client):
    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)
    logger.debug("UNIT TEST: test_build_circuit_design_with_mock_response_success")
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_build_circuit_design_with_mock_response_error(monkeypatch, client):
    def mock_response(payload):
        return JSONResponse({"message": "Bad Gateway"}, 502)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)
    logger.debug("UNIT TEST: test_build_circuit_design_with_mock_response_error")
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 502


@pytest.mark.unittest
def test_build_circuit_design_with_json_decode_error(monkeypatch, client):
    r = client.post(url, json="ab1", headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 500


@pytest.mark.unittest
def test_build_circuit_design_with_missing_service_type_for_CEA(monkeypatch, client):
    test_payload = deepcopy(home_run_payload)
    test_payload.pop("a_side_info")
    test_payload["z_side_info"]["service_type"] = "net_new_no_cj"
    logger.debug(f"test_payload - {test_payload}")
    test_payload["z_side_info"]["product_name"] = "Carrier E-Access (Fiber)"
    test_payload["z_side_info"].pop("service_type")
    current_service_type = test_payload["z_side_info"].get("service_type", "")
    logger.debug(f"current service_type - {current_service_type}")
    logger.debug(f"test_payload - {test_payload}")

    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)

    logger.debug("UNIT TEST: test_build_circuit_design_with_missing_service_type_for_CEA")
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_build_circuit_design_with_missing_service_type_and_pid_for_CEA(client):
    test_payload = deepcopy(home_run_payload)
    test_payload.pop("a_side_info")
    test_payload["z_side_info"]["product_name"] = "Carrier E-Access (Fiber)"
    test_payload["z_side_info"].pop("service_type")
    test_payload["z_side_info"].pop("pid")
    current_service_type = test_payload["z_side_info"].get("service_type", "service_type_missing")
    current_pid = test_payload["z_side_info"].get("pid", "pid_missing")
    logger.debug(f"current service_type - {current_service_type}")
    logger.debug(f"current pid - {current_pid}")

    logger.debug("UNIT TEST: test_build_circuit_design_with_missing_service_type_and_pid_for_CEA")
    logger.debug(f"test_payload - {test_payload}")

    try:
        client.post(url, json=test_payload, headers=head, auth=auth)
    except AbortException as e:
        assert e.code == 400


@pytest.mark.unittest
def test_build_circuit_design_aborts(client):
    # payload["z_side_info"]["cid"] = "51.L1XX.FAIL_BCD..CHTR"
    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["cid"] = "51.L1XX.FAIL_BCD..CHTR"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 500

    # bad product name
    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["product_name"] = "bad_test"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 500

    # Wireless Internet Backup
    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["product_name"] = "Wireless Internet Backup"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 500

    # 3rd_party_provided_circuit
    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["third_party_provided_circuit"] = "Y"
    test_payload["z_side_info"]["product_name"] = "bad_test"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 500

    # not Apollo and SIP - Trunk (Fiber)
    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["network_platform"] = "bad"
    test_payload["z_side_info"]["product_name"] = "SIP - Trunk (Fiber)"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 500


@pytest.mark.unittest
def test_9999999(client, monkeypatch):
    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["cid"] = "51.L2XX.FAIL_VLAN..CHTR"

    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 200


@pytest.mark.unittest
def test_static_values(client, monkeypatch):
    def mock_response(payload):
        return JSONResponse({"message": "Successful mocked call"}, 200)

    monkeypatch.setattr("arda_app.api.build_circuit_design.build_circuit_design_main", mock_response)

    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["product_name"] = "Hosted Voice - (Fiber)"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 200

    test_payload = deepcopy(payload)
    test_payload["z_side_info"]["product_name"] = "FC + Remote PHY"
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    assert r.status_code == 200
