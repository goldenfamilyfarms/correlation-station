import logging
from base64 import b64encode
from copy import deepcopy

import pytest

from arda_app.common import srvc_prod_eligibility_template
from common_sense.common.errors import AbortException

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

credentials = b64encode(b"sense_api:$en$e_api").decode("utf-8")
head = {"accept": "application/json", "Authorization": f"Basic {credentials}"}

home_run_payload = deepcopy(payload)
home_run_payload["a_side_info"]["build_type"] = "home_run"
home_run_payload["a_side_info"]["clli"] = "ATSCCAAB"
home_run_payload["z_side_info"]["build_type"] = "home_run"
home_run_payload["z_side_info"]["clli"] = "ATSCCAAB"


@pytest.mark.unittest
def test_create_srvc_prod_eligibility_template_object():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    assert spet_obj.payload == home_run_payload
    assert spet_obj.supported_product_api == "POST /arda/v1/supported_product"


@pytest.mark.unittest
def test_post_call_supported_product_endpoint(monkeypatch):
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    monkeypatch.setattr(
        srvc_prod_eligibility_template,
        "post_sense",
        lambda url, payload, timeout, resp: {"message": "mocked POST SEnSE call"},
        200,
    )
    resp = spet_obj.call_supported_product_endpoint()
    assert resp == {"message": "mocked POST SEnSE call"}, 200


@pytest.mark.unittest
def test_get_call_supported_product_endpoint(monkeypatch):
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    spet_obj.supported_product_api = "GET /mock/url"
    monkeypatch.setattr(
        srvc_prod_eligibility_template,
        "get_sense",
        lambda url, payload, timeout, resp: {"message": "mocked GET SEnSE call"},
        200,
    )
    resp = spet_obj.call_supported_product_endpoint()
    assert resp == {"message": "mocked GET SEnSE call"}, 200


@pytest.mark.unittest
def test_put_call_supported_product_endpoint(monkeypatch):
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    spet_obj.supported_product_api = "PUT /mock/url"
    monkeypatch.setattr(
        srvc_prod_eligibility_template,
        "put_sense",
        lambda url, payload, timeout, resp: {"message": "mocked PUT SEnSE call"},
        200,
    )
    resp = spet_obj.call_supported_product_endpoint()
    assert resp == {"message": "mocked PUT SEnSE call"}, 200


@pytest.mark.unittest
def test_get_supported_services():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    assert spet_obj.supported_services_1 == ("net_new_cj", "net_new_qc")
    assert spet_obj.supported_services_2 == ("net_new_cj", "net_new_qc", "net_new_serviceable", "net_new_no_cj")


@pytest.mark.unittest
def test_is_service_supported_with_no_data():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    try:
        spet_obj.supported_products.get(None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_is_service_supported_returns_true():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    service = spet_obj.supported_products.get(home_run_payload["z_side_info"]["product_name"])
    assert home_run_payload["z_side_info"]["service_type"] in service


@pytest.mark.unittest
def test_is_service_supported_returns_false():
    data = home_run_payload.get("z_side_info")
    data["service_type"] = "net_new"
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(data)
    service = spet_obj.supported_products.get(data["product_name"])
    assert data["service_type"] not in service


@pytest.mark.unittest
def test_get_supported_products():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    assert tuple(spet_obj.supported_products.keys()) == (
        "FC + Remote PHY",
        "Fiber Internet Access",
        "Carrier E-Access (Fiber)",
        "EP-LAN (Fiber)",
        "EPL (Fiber)",
        "Carrier Fiber Internet Access",
        "Hosted Voice - (Fiber)",
        "Hosted Voice - (DOCSIS)",
        "Hosted Voice - (Overlay)",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
        "PRI Trunk (DOCSIS)",
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "SIP - Trunk (DOCSIS)",
        "Wireless Internet Access-Primary",
        "Wireless Internet Access-Primary-Out of Footprint",
        "Wireless Internet Access-Backup",
        "Wireless Internet Access",
        "Wireless Internet Access - Off-Net",
        "Wireless Internet Backup",
    )


@pytest.mark.unittest
def test_is_product_supported_with_no_data():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    try:
        spet_obj.supported_products.get(None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_is_product_supported_returns_true():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    assert spet_obj.supported_products.get(home_run_payload["z_side_info"]["product_name"])


@pytest.mark.unittest
def test_is_product_supported_returns_false():
    data = home_run_payload.get("z_side_info")
    data["product_name"] = "Carrier E-Access"
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(data)
    assert not spet_obj.supported_products.get(data["product_name"])


@pytest.mark.unittest
def test_get_payload_for_each_side():
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(home_run_payload)
    assert spet_obj.get_payload_for_each_side() == [
        ("a_side_info", home_run_payload.get("a_side_info")),
        ("z_side_info", home_run_payload.get("z_side_info")),
    ]


@pytest.mark.unittest
def test_check_service_and_product_eligibility_with_unsupported_service(monkeypatch):
    payload_z = home_run_payload.get("z_side_info")
    payload_z["service_type"] = "quick_connect"
    payload_z["product_name"] = "Carrier E-Access (Fiber)"
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(payload_z)
    monkeypatch.setattr(
        srvc_prod_eligibility_template.SrvcProdEligibilityTemplate,
        "get_payload_for_each_side",
        lambda _: [("z_side_info", payload_z)],
    )
    try:
        spet_obj.check_service_and_product_eligibility()
    except AbortException as e:
        assert e.code == 500
        assert "is unsupported" in e.data.get("message")


@pytest.mark.unittest
def test_check_service_and_product_eligibility_with_unsupported_product(monkeypatch):
    payload_z = home_run_payload.get("z_side_info")
    payload_z["service_type"] = "net_new_cj"
    payload_z["product_name"] = "CEA"
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(payload_z)
    monkeypatch.setattr(
        srvc_prod_eligibility_template.SrvcProdEligibilityTemplate,
        "get_payload_for_each_side",
        lambda _: [("z_side_info", payload_z)],
    )
    try:
        spet_obj.check_service_and_product_eligibility()
    except AbortException as e:
        payload_z["product_name"] = "Fiber Internet Access"
        assert e.code == 500
        assert "is unsupported" in e.data.get("message")


@pytest.mark.unittest
def test_check_service_and_product_eligibility_with_unsupported_service_and_product(monkeypatch):
    payload_a = home_run_payload.get("a_side_info")
    payload_a["service_type"] = "net_new_noqc"
    payload_a["product_name"] = "DIA"
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(payload_a)
    monkeypatch.setattr(
        srvc_prod_eligibility_template.SrvcProdEligibilityTemplate,
        "get_payload_for_each_side",
        lambda _: [("a_side_info", payload_a), ("z_side_info", home_run_payload.get("z_side_info"))],
    )
    try:
        spet_obj.check_service_and_product_eligibility()
    except AbortException as e:
        assert e.code == 500
        assert "is unsupported" in e.data.get("message")


@pytest.mark.unittest
def test_check_service_and_product_eligibility_with_empty_payload(monkeypatch):
    payload_z = home_run_payload.get("z_side_info")
    payload_z["product_name"] = "Wireless Internet Backup"
    payload_z["service_type"] = "net_new_cj"
    payload_a = {}
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(payload_z)
    logger.debug(f"payload_a - {payload_a}")
    logger.debug(f"payload_z - {payload_z}")
    logger.debug(f"spet_obj - {spet_obj}")
    monkeypatch.setattr(
        srvc_prod_eligibility_template.SrvcProdEligibilityTemplate,
        "get_payload_for_each_side",
        lambda _: [("z_side_info", payload_z), ("a_side_info", payload_a)],
    )
    assert spet_obj.check_service_and_product_eligibility() is None


@pytest.mark.unittest
def test_temporary_workaround_to_accept_net_new_no_cj(monkeypatch):
    payload_a = home_run_payload.get("a_side_info")
    payload_a["service_type"] = "net_new_no_cj"
    payload_a["product_name"] = "Carrier E-Access (Fiber)"
    logger.debug(f"payload_a - {payload_a}")
    spet_obj = srvc_prod_eligibility_template.SrvcProdEligibilityTemplate(payload_a)
    monkeypatch.setattr(
        srvc_prod_eligibility_template.SrvcProdEligibilityTemplate,
        "get_payload_for_each_side",
        lambda _: [("a_side_info", payload_a)],
    )
    spet_obj.check_service_and_product_eligibility()
    logger.debug(f"spet_obj.payload - {spet_obj.payload}")
    assert spet_obj.payload.get("service_type") == "net_new_cj"
