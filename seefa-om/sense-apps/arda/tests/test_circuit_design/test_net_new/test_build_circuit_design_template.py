from base64 import b64encode
from copy import deepcopy

import pytest

from arda_app.common import build_circuit_design_template

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
def test_create_build_circuit_design_template_object():
    bcdt_obj = build_circuit_design_template.BuildCircuitDesignTemplate(home_run_payload)
    assert bcdt_obj.payload == home_run_payload
