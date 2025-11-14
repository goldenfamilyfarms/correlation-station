import logging
import pytest
from arda_app.api import supported_product
from copy import deepcopy
from common_sense.common.errors import abort
from arda_app.common import auth_config


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

sense_usr, sense_pass = auth_config.SENSE_TEST_SWAGGER_USER, auth_config.SENSE_TEST_SWAGGER_PASS
head = {"accept": "application/json"}
auth = (sense_usr, sense_pass)

home_run_payload = deepcopy(payload)
home_run_payload["a_side_info"]["build_type"] = "home_run"
home_run_payload["a_side_info"]["clli"] = "ATSCCAAB"
home_run_payload["z_side_info"]["build_type"] = "home_run"
home_run_payload["z_side_info"]["clli"] = "ATSCCAAB"


def test_supported_product(client):
    url = "/arda/v1/supported_product"
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 200


@pytest.mark.unittest
def test_product_uniqueness_identifier_with_mock_response_error(monkeypatch, client):
    url = "/arda/v1/supported_product"
    traceback_data = (
        "Sense Text Response: {message: ARDA - Sense unexpected status code:"
        " 400 - URL: http://127.0.0.1:5001/arda/v1/assign_gsip - METHOD: POST - "
        "Payload: {cid: 95.L1XX.000671..TWCC, product_name: EPL (Fiber), legacy_company: TWC} - "
        "Sense Text Response: {message: ARDA - Unsupported product name: EPL (Fiber)"
    )

    monkeypatch.setattr(
        supported_product.SupportedProdTemplate, "product_uniqueness_identifier", lambda *_: abort(500, "Bad Gateway")
    )
    monkeypatch.setattr(supported_product.traceback, "format_exc", lambda *_: traceback_data)
    logger.debug("UNIT TEST: test_product_uniqueness_identifier_with_mock_response_error")
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 500


@pytest.mark.unittest
def test_product_uniqueness_identifier_with_mock_response_error2(monkeypatch, client):
    url = "/arda/v1/supported_product"
    traceback_data = "Sense Text Response: {message: ARDA - Unsupported product name: EPL (Fiber)"

    monkeypatch.setattr(
        supported_product.SupportedProdTemplate, "product_uniqueness_identifier", lambda *_: abort(500, "Bad Gateway")
    )
    monkeypatch.setattr(supported_product.traceback, "format_exc", lambda *_: traceback_data)
    logger.debug("UNIT TEST: test_product_uniqueness_identifier_with_mock_response_error2")
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 500


@pytest.mark.unittest
def test_product_uniqueness_identifier_with_mock_response_error3(monkeypatch, client):
    url = "/arda/v1/supported_product"
    traceback_data = "Sense Text Response: {message: Found existing transport path 51001.GE10.AUSGTXLG0QW.AUSWTXSU2ZW"

    monkeypatch.setattr(
        supported_product.SupportedProdTemplate, "product_uniqueness_identifier", lambda *_: abort(500, "Bad Gateway")
    )
    monkeypatch.setattr(supported_product.traceback, "format_exc", lambda *_: traceback_data)
    logger.debug("UNIT TEST: test_product_uniqueness_identifier_with_mock_response_error3")
    r = client.post(url, json=home_run_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 500


@pytest.mark.unittest
def test_supported_product_with_json_decode_error(monkeypatch, client):
    url = "/arda/v1/supported_product"
    logger.debug("UNIT TEST: test_supported_product_with_json_decode_error")

    r = client.post(url, json="ab1", headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 500
