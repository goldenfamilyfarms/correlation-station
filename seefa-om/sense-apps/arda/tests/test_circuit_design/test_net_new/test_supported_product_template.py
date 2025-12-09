import logging
from base64 import b64encode
from copy import deepcopy

import pytest

from arda_app.common import supported_prod_template
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

circuit_sites_resp = [
    {
        "CIRC_PATH_INST_ID": "732695",
        "CIRCUIT_NAME": "95.L1XX.000671..TWCC",
        "CIRCUIT_STATUS": "Auto-Planned",
        "CIRCUIT_BANDWIDTH": "5 Mbps",
        "CIRCUIT_CATEGORY": "ETHERNET",
        "SERVICE_TYPE": "COM-DIA",
        "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
        "CLASS_OF_SERVICE": "GOLD REGIONAL",
        "A_SITE_NAME": "AUSGTXLG_TWC/HUB C-BUCKNER (620)",
        "A_SITE_TYPE": "HUB",
        "A_SITE_REGION": "TEXAS",
        "A_ADDRESS": "11827 BUCKNER RD",
        "A_CITY": "AUSTIN",
        "A_STATE": "TX",
        "A_ZIP": "78726",
        "A_CLLI": "AUSGTXLG",
        "A_NPA": "512",
        "A_LONGITUDE": "-97.835885",
        "A_LATITUDE": "30.443762",
        "Z_SITE_NAME": "LARETXAF-SEEFA TEST SITE CD ITQA//2007 S ZAPATA HWY",
        "Z_SITE_TYPE": "LOCAL",
        "Z_SITE_REGION": "TEXAS",
        "Z_ADDRESS": "2007 S ZAPATA HWY",
        "Z_CITY": "LAREDO",
        "Z_STATE": "TX",
        "Z_ZIP": "78046",
        "Z_CLLI": "LARETXAF",
        "Z_NPA": "956",
        "Z_LONGITUDE": "-99.473583",
        "Z_LATITUDE": "27.479359",
        "LEG_NAME": "1",
        "LEG_INST_ID": "851729",
    }
]


@pytest.mark.unittest
def test_create_supported_prod_template_object():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.order == ()
    assert spt_obj.payload == home_run_payload
    assert spt_obj.carryover_payload == {}
    assert spt_obj.execution_output == []


@pytest.mark.unittest
def test_common_tasks_list():
    common_tasks = ["Assign_Uplinks", "Assign_Handoffs", "Assign_Parent_Paths"]
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.common_tasks == common_tasks


@pytest.mark.unittest
def test_construction_job_tasks_list():
    construction_job_tasks = ["Create_CPE_Shelf", "Assign_Uplinks", "Assign_Handoffs", "Assign_Parent_Paths"]
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.cj_tasks == construction_job_tasks


@pytest.mark.unittest
def test_no_construction_job_tasks_list():
    no_construction_job_tasks = ["Serviceable_Shelf", "Assign_Handoffs", "Assign_Parent_Paths"]
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.no_cj_tasks == no_construction_job_tasks


@pytest.mark.unittest
def test_construction_job_mtu_tasks_list():
    construction_job_mtu_tasks = [
        "Create_MTU_Shelf",
        "Create_CPE_Shelf",
        "Create_MTU_Transport",
        "Assign_Uplinks",
        "Assign_Handoffs",
        "Assign_Parent_Paths",
    ]
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.cj_mtu_tasks == construction_job_mtu_tasks


@pytest.mark.unittest
def test_quick_connect_tasks_list():
    quick_connect_tasks = [
        "Quick_Connect_Transport_Path",
        "Create_CPE_Shelf",
        "Assign_Uplinks",
        "Assign_Handoffs",
        "Assign_Parent_Paths",
    ]
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.qc_tasks == quick_connect_tasks


@pytest.mark.unittest
def test_get_order_tasks_map():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_order_tasks_map()


@pytest.mark.unittest
def test_get_task_microservice_map():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_task_microservice_main_funcs()


@pytest.mark.unittest
def test_get_task_payload_keys_map():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_task_payload_keys_map()


@pytest.mark.unittest
def test_get_order_task_carryover_payload_keys_map():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_order_task_carryover_payload_keys_map()


@pytest.mark.unittest
def test_get_FIA_uniqueness_task_list():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_FIA_uniqueness_task_list()


@pytest.mark.unittest
def test_get_HVF_uniqueness_task_list():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_HVF_uniqueness_task_list()


@pytest.mark.unittest
def test_get_RPHY_uniqueness_task_list():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_RPHY_uniqueness_task_list()


@pytest.mark.unittest
def test_get_CEA_uniqueness_task_list():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_CEA_uniqueness_task_list()


@pytest.mark.unittest
def test_get_EPL_uniqueness_task_list():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_EPL_uniqueness_task_list()


@pytest.mark.unittest
def test_get_WIA_uniqueness_task_list():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_WIA_uniqueness_task_list()


@pytest.mark.unittest
def test_get_supported_orders():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    assert spt_obj.get_supported_orders()


@pytest.mark.unittest
def test_service_type_builder_with_no_payload():
    spt_obj = supported_prod_template.SupportedProdTemplate(None)
    try:
        spt_obj.service_type_builder(None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_service_type_builder_with_success(monkeypatch):
    data = home_run_payload
    payload_z = data.get("z_side_info")
    payload_z["side"] = "z_side"
    spt_obj = supported_prod_template.SupportedProdTemplate(payload_z)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "create_order", lambda self, _, btype: ("net_new_cj", "Home Run")
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "is_order_supported", lambda self, payload: True)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_list_of_tasks_for_order",
        lambda _: ["Create_CPE_Shelf", "Assign_Uplinks", "Assign_Handoffs", "Assign_Parent_Paths"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: "ok"
    )
    stb_obj = spt_obj.service_type_builder(payload_z)
    assert stb_obj is None
    assert spt_obj.execution_output


@pytest.mark.unittest
def test_product_uniqueness_identifier_with_no_payload_list(monkeypatch):
    data = home_run_payload
    payload_a = data.get("a_side_info")
    payload_a["product_name"] = "Fiber Internet Access"
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "Fiber Internet Access"
    revised_payload = {"a_side_info": payload_a, "z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda *_: [])
    try:
        spt_obj.product_uniqueness_identifier()
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_FIA_and_unknown(monkeypatch):
    data = home_run_payload
    payload_a = data.get("a_side_info")
    payload_a["product_name"] = "Fiber Internet Access"
    payload_a["side"] = "a_side"
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "Unknown Product"
    payload_z["side"] = "z_side"
    revised_payload = {"a_side_info": payload_a, "z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda _: [payload_a, payload_z]
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "service_type_builder", lambda self, data: None)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_FIA_uniqueness_task_list",
        lambda self: ["Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: None
    )
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert "  -- Product Uniqueness --" in pui_obj
    assert len(pui_obj) == 2


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_CEA_and_EPL(monkeypatch):
    data = home_run_payload
    payload_a = data.get("a_side_info")
    payload_a["product_name"] = "Carrier E-Access (Fiber)"
    payload_a["side"] = "a_side"
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "EPL (Fiber)"
    payload_z["side"] = "z_side"
    revised_payload = {"a_side_info": payload_a, "z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda _: [payload_a, payload_z]
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "service_type_builder", lambda self, data: None)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_CEA_uniqueness_task_list",
        lambda self: ["Assign_ENNI", "Assign_EVC", "Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_EPL_uniqueness_task_list",
        lambda self: ["Assign_EVC", "Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: None
    )
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert "  -- Product Uniqueness --" in pui_obj
    assert len(pui_obj) == 2


@pytest.mark.unittest
def test_create_order_with_missing_service_type():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.create_order(None, "Home Run")
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_create_order_with_no_build_type():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    order = spt_obj.create_order("net_new_cj", None)
    assert order == ("net_new_cj", None)


@pytest.mark.unittest
def test_create_order_with_service_and_build_type():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    order = spt_obj.create_order("net_new_cj", "Home Run")
    assert order == ("net_new_cj", "Home Run")


@pytest.mark.unittest
def test_is_order_supported_with_missing_payload():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.is_order_supported(None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_is_order_supported_with_unsupported_order(monkeypatch):
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    spt_obj.order = ("net_new_nocj", "MTU New Build")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_supported_orders",
        lambda *_: (
            ("net_new_cj", "MTU New Build"),
            ("net_new_qc", None),
            ("net_new_cj", "Home Run"),
            ("net_new_cj", "STU (Single Tenant Unit)"),
            ("net_new_cj", "Strip Mall"),
            ("net_new_cj", "home_run"),
        ),
    )
    try:
        spt_obj.is_order_supported(home_run_payload)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_is_order_supported_with_success(monkeypatch):
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    spt_obj.order = ("net_new_cj", "MTU New Build")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_supported_orders",
        lambda *_: (
            ("net_new_cj", "MTU New Build"),
            ("net_new_qc", None),
            ("net_new_cj", "Home Run"),
            ("net_new_cj", "STU (Single Tenant Unit)"),
            ("net_new_cj", "Strip Mall"),
            ("net_new_cj", "home_run"),
        ),
    )
    order_is_supported = spt_obj.is_order_supported(home_run_payload)
    assert order_is_supported is True


@pytest.mark.unittest
def test_is_payload_key_optional_with_missing_key():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.is_payload_key_optional(None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_is_payload_key_optional_returning_False():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    payload_key_is_optional = spt_obj.is_payload_key_optional("cid")
    assert payload_key_is_optional is False


@pytest.mark.unittest
def test_is_payload_key_optional_returning_True():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    payload_key_is_optional = spt_obj.is_payload_key_optional(("cid",))
    assert payload_key_is_optional is True


@pytest.mark.unittest
def test_add_side_info_to_payload_without_side():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.add_side_info_to_payload(None, home_run_payload)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_add_side_info_to_payload_without_payload():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.add_side_info_to_payload("a_side_info", None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_add_side_info_to_payload_with_success():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    revised_payload = spt_obj.add_side_info_to_payload("a_side", data.get("a_side_info"))
    assert "side" in revised_payload.keys()
    assert revised_payload.get("side") == "a_side"


@pytest.mark.unittest
def test_add_role_info_to_payload_without_role():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.add_role_info_to_payload(None, home_run_payload)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_add_role_info_to_payload_without_payload():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.add_role_info_to_payload("cpe", None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_add_role_info_to_payload_with_success():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    revised_payload = spt_obj.add_role_info_to_payload("mtu", data.get("z_side_info"))
    assert "role" in revised_payload.keys()
    assert revised_payload.get("role") == "mtu"


@pytest.mark.unittest
def test_add_port_role_info_to_payload_without_port_role():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.add_port_role_info_to_payload(None, home_run_payload)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_add_port_role_info_to_payload_without_payload():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.add_port_role_info_to_payload("uplink", None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_add_port_role_info_to_payload_with_success():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    revised_payload = spt_obj.add_port_role_info_to_payload("handoff", data.get("z_side_info"))
    assert "port_role" in revised_payload.keys()
    assert revised_payload.get("port_role") == "handoff"


@pytest.mark.unittest
def test_update_carryover_payload_without_data():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.update_carryover_payload(None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_update_carryover_payload_with_success():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.carryover_payload = {
        "mtu_shelf": "string",
        "mtu_tid": "string",
        "mtu_uplink": "string",
        "mtu_handoff": "string",
        "mtu_pe_path": "string",
    }
    response_data = {
        "cpe_shelf": "string",
        "cpe_tid": "string",
        "cpe_uplink": "string",
        "cpe_handoff": "string",
        "zw_path": "string",
        "circ_path_inst_id": "string",
    }
    spt_obj.update_carryover_payload(response_data)
    assert spt_obj.carryover_payload == {
        "mtu_shelf": "string",
        "mtu_tid": "string",
        "mtu_uplink": "string",
        "mtu_handoff": "string",
        "mtu_pe_path": "string",
        "cpe_shelf": "string",
        "cpe_tid": "string",
        "cpe_uplink": "string",
        "cpe_handoff": "string",
        "zw_path": "string",
        "circ_path_inst_id": "string",
    }


@pytest.mark.unittest
def test_get_payload_for_each_side_with_success():
    data = home_run_payload
    logger.debug(f"data - {data}")
    payload_a = data.get("a_side_info")
    payload_a["side"] = "a_side"
    payload_a["product_name"] = "Fiber Internet Access"
    logger.debug(f"payload_a - {payload_a}")
    payload_z = data.get("z_side_info")
    payload_z["side"] = "z_side"
    logger.debug(f"payload_z - {payload_z}")
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    payload_list = spt_obj.get_payload_for_each_side()
    logger.debug(f"payload_list - {payload_list}")
    assert payload_a in payload_list
    assert payload_z in payload_list
    assert payload_list == [payload_a, payload_z]


@pytest.mark.unittest
def test_build_payload_for_task_without_task():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.build_payload_for_task(None, spt_obj.payload.get("a_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_build_payload_for_task_without_payload():
    spt_obj = supported_prod_template.SupportedProdTemplate(home_run_payload)
    try:
        spt_obj.build_payload_for_task("Create_MTU_Shelf", None)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_build_payload_for_task_Create_MTU_Shelf():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ("net_new_cj", "MTU New Build")
    completed_payload = spt_obj.build_payload_for_task("Create_MTU_Shelf", data.get("z_side_info"))
    assert completed_payload == {
        "service_type": "net_new_cj",
        "product_name": "EPL (Fiber)",
        "cid": "84.L4XX.000058..CHTR",
        "build_type": "MTU New Build",
        "role": "mtu",
        "side": "z_side",
    }


@pytest.mark.unittest
def test_build_payload_for_task_Create_CPE_Shelf():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ("net_new_cj", "MTU New Build")
    completed_payload = spt_obj.build_payload_for_task("Create_CPE_Shelf", data.get("z_side_info"))
    assert completed_payload == {
        "service_type": "net_new_cj",
        "product_name": "EPL (Fiber)",
        "cid": "84.L4XX.000058..CHTR",
        "build_type": "MTU New Build",
        "connector_type": "LC",
        "uni_type": "Access",
        "role": "cpe",
        "side": "z_side",
    }


@pytest.mark.unittest
def test_build_payload_for_task_Create_MTU_Transport():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ("net_new_cj", "MTU New Build")
    spt_obj.carryover_payload = {"mtu_tid": "2222", "cpe_tid": "3333", "mtu_handoff": "0/1", "cpe_uplink": "0/3"}
    completed_payload = spt_obj.build_payload_for_task("Create_MTU_Transport", data.get("z_side_info"))
    assert completed_payload == {
        "service_type": "net_new_cj",
        "product_name": "EPL (Fiber)",
        "cid": "84.L4XX.000058..CHTR",
        "build_type": "MTU New Build",
        "mtu_tid": "2222",
        "cpe_tid": "3333",
        "mtu_handoff": "0/1",
        "cpe_uplink": "0/3",
        "side": "z_side",
    }


@pytest.mark.unittest
def test_build_payload_for_task_Create_MTU_Transport_with_key_error():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    data["z_side_info"].pop("cpe_uplink")
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ("net_new_cj", "MTU New Build")
    spt_obj.carryover_payload = {"mtu_tid": "2222", "cpe_tid": "3333", "mtu_handoff": "0/1", "generate_key_error": "0/3"}
    completed_payload = spt_obj.build_payload_for_task("Create_MTU_Transport", data.get("z_side_info"))
    assert completed_payload == {
        "service_type": "net_new_cj",
        "product_name": "EPL (Fiber)",
        "cid": "84.L4XX.000058..CHTR",
        "build_type": "MTU New Build",
        "mtu_tid": "2222",
        "cpe_tid": "3333",
        "mtu_handoff": "0/1",
        "side": "z_side",
    }


@pytest.mark.skip("transition to using Create_CPE_Shelf")
# @pytest.mark.unittest
def test_build_payload_for_task_Create_CPE_Shelf_QC():
    data = home_run_payload
    data["z_side_info"]["service_type"] = "net_new_qc"
    data["z_side_info"]["build_type"] = None
    data["z_side_info"]["product_name"] = "Fiber Internet Access"
    logger.debug(f"data - {data}")
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ("net_new_qc", None)
    spt_obj.carryover_payload = data.get("z_side_info")
    logger.debug(f"spt_obj.carryover_payload - {spt_obj.carryover_payload}")
    completed_payload = spt_obj.build_payload_for_task("Create_CPE_Shelf_QC", data.get("z_side_info"))
    logger.debug(f"completed_payload - {completed_payload}")
    assert completed_payload == {
        "service": "quick_connect",
        "cid": "84.L4XX.000058..CHTR",
        "connector_type": "LC",
        "media_type": "Access",
        "agg_bandwidth": "200Mbps",
    }


@pytest.mark.unittest
def test_build_payload_for_task_Assign_Uplinks():
    data = home_run_payload
    data["z_side_info"]["product_name"] = "Fiber Internet Access"
    logger.debug(f"data - {data}")
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.carryover_payload = data.get("z_side_info")
    spt_obj.carryover_payload["service_type"] = "net_new_cj"
    spt_obj.carryover_payload["build_type"] = "home_run"
    spt_obj.carryover_payload["circ_path_inst_id"] = "3333333"
    spt_obj.carryover_payload.pop("port_role")
    logger.debug(f"spt_obj.carryover_payload - {spt_obj.carryover_payload}")
    completed_payload = spt_obj.build_payload_for_task("Assign_Uplinks", data.get("z_side_info"))
    logger.debug(f"completed_payload - {completed_payload}")
    assert all(
        (
            "service_type" in completed_payload.keys(),
            "product_name" in completed_payload.keys(),
            "cid" in completed_payload.keys(),
            "circ_path_inst_id" in completed_payload.keys(),
            "build_type" in completed_payload.keys(),
            "side" in completed_payload.keys(),
            "port_role" in completed_payload.keys(),
        )
    )
    assert all(
        (
            completed_payload.get("service_type") == "net_new_cj",
            completed_payload.get("product_name") == "Fiber Internet Access",
            completed_payload.get("cid") == "84.L4XX.000058..CHTR",
            completed_payload.get("circ_path_inst_id") == "3333333",
            completed_payload.get("build_type") == "home_run",
            completed_payload.get("side") == "z_side",
            completed_payload.get("port_role") == "uplink",
        )
    )


@pytest.mark.unittest
def test_build_payload_for_task_Assign_Handoffs():
    data = home_run_payload
    data["z_side_info"]["product_name"] = "Fiber Internet Access"
    logger.debug(f"data - {data}")
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.carryover_payload = data.get("z_side_info")
    spt_obj.carryover_payload["service_type"] = "net_new_cj"
    spt_obj.carryover_payload["build_type"] = "home_run"
    spt_obj.carryover_payload["circ_path_inst_id"] = "3333333"
    spt_obj.carryover_payload.pop("port_role")
    logger.debug(f"spt_obj.carryover_payload - {spt_obj.carryover_payload}")
    completed_payload = spt_obj.build_payload_for_task("Assign_Handoffs", data.get("z_side_info"))
    logger.debug(f"completed_payload - {completed_payload}")
    assert all(
        (
            "service_type" in completed_payload.keys(),
            "product_name" in completed_payload.keys(),
            "cid" in completed_payload.keys(),
            "circ_path_inst_id" in completed_payload.keys(),
            "build_type" in completed_payload.keys(),
            "side" in completed_payload.keys(),
            "port_role" in completed_payload.keys(),
        )
    )
    assert all(
        (
            completed_payload.get("service_type") == "net_new_cj",
            completed_payload.get("product_name") == "Fiber Internet Access",
            completed_payload.get("cid") == "84.L4XX.000058..CHTR",
            completed_payload.get("circ_path_inst_id") == "3333333",
            completed_payload.get("build_type") == "home_run",
            completed_payload.get("side") == "z_side",
            completed_payload.get("port_role") == "handoff",
        )
    )


@pytest.mark.unittest
def test_get_payload_for_task_without_task():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    try:
        spt_obj.get_payload_for_task(None, data.get("z_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_get_payload_for_task_without_payload():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    try:
        spt_obj.get_payload_for_task("Create_CPE_Shelf", {})
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_get_payload_for_task_with_success():
    data = home_run_payload
    data["z_side_info"]["product_name"] = "Fiber Internet Access"
    data["z_side_info"]["build_type"] = "MTU New Build"
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    payload_for_task = spt_obj.get_payload_for_task("Create_CPE_Shelf", data.get("z_side_info"))
    logger.debug(f"payload_for_task - {payload_for_task}")
    assert payload_for_task
    assert payload_for_task == {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "cid": "84.L4XX.000058..CHTR",
        "build_type": "MTU New Build",
        "connector_type": "LC",
        "uni_type": "Access",
        "role": "cpe",
        "side": "z_side",
    }


@pytest.mark.unittest
def test_check_payload_keys_for_task_without_task():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    try:
        spt_obj.check_payload_keys_for_task(None, data.get("z_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_check_payload_keys_for_task_without_payload():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    try:
        spt_obj.check_payload_keys_for_task("Create_CPE_Shelf", {})
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_check_payload_keys_for_task_with_success():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    resp = spt_obj.check_payload_keys_for_task("Create_CPE_Shelf", data.get("z_side_info"))
    assert resp is None


@pytest.mark.unittest
def test_check_payload_keys_for_task_showing_keys_with_no_value():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    data["z_side_info"]["mtu_tid"] = ""
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    try:
        spt_obj.check_payload_keys_for_task("Assign_Uplinks", data.get("z_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_check_payload_keys_for_task_with_missing_key():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    data["z_side_info"]["mtu_tid"] = "2222"
    data["z_side_info"].pop("cid")
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    try:
        spt_obj.check_payload_keys_for_task("Assign_Handoffs", data.get("z_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_check_payload_keys_for_task_with_missing_keys():
    data = home_run_payload
    data["z_side_info"]["build_type"] = "MTU New Build"
    data["z_side_info"]["cid"] = "84.L4XX.000058..CHTR"
    data["z_side_info"].pop("circ_path_inst_id")
    data["z_side_info"]["side"] = ""
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    try:
        spt_obj.check_payload_keys_for_task("Assign_Uplinks", data.get("z_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_get_list_of_tasks_for_order_without_an_order():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ""
    try:
        spt_obj.get_list_of_tasks_for_order()
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_get_list_of_tasks_for_order_with_success():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    spt_obj.order = ("net_new_cj", "Home Run")
    list_of_tasks = spt_obj.get_list_of_tasks_for_order()
    assert list_of_tasks == ["Create_CPE_Shelf", "Assign_Uplinks", "Assign_Handoffs", "Assign_Parent_Paths"]


@pytest.mark.unittest
def test_execute_each_task_without_task_list():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    try:
        spt_obj.execute_each_task([], data.get("z_side_info"))
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_execute_each_task_without_payload():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data)
    try:
        spt_obj.execute_each_task("Assign_Parent_Paths", {})
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_execute_each_task_with_success(monkeypatch):
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))

    def mock_main_func(payload):
        return {"message": "Call to SEnSE is successful"}

    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_func_for_task", lambda self, task: mock_main_func
    )

    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_payload_for_task",
        lambda *_: {
            "service_type": "net_new_cj",
            "product_name": "Fiber Internet Access",
            "cid": "84.L4XX.000058..CHTR",
            "build_type": "MTU New Build",
            "connector_type": "LC",
            "uni_type": "Access",
            "role": "cpe",
            "side": "z_side",
        },
    )
    spt_obj.execute_each_task(["Create_CPE_Shelf"], data.get("z_side_info"))
    assert "   Create_CPE_Shelf" in spt_obj.execution_output


@pytest.mark.unittest
def test_get_method_and_endpoint_for_api_without_api():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    try:
        spt_obj.get_method_and_endpoint_for_api("")
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_get_method_and_endpoint_for_api_with_real_api():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    method, endpoint = spt_obj.get_method_and_endpoint_for_api("POST /arda/v1/create_shelf")
    assert method == "POST"
    assert endpoint == "/arda/v1/create_shelf"


@pytest.mark.unittest
def test_get_method_and_endpoint_for_api_with_mock_api():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    method, endpoint = spt_obj.get_method_and_endpoint_for_api("/arda/v1/future_endpoint")
    assert method is None
    assert endpoint == "/arda/v1/future_endpoint"


@pytest.mark.unittest
def test_call_sense_endpoint_without_endpoint():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    try:
        spt_obj.call_sense_endpoint("POST", "", "Create_CPE_Shelf", {"cid": "84.L4XX.000058..CHTR"})
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_call_sense_endpoint_without_payload():
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    try:
        spt_obj.call_sense_endpoint("POST", "/arda/v1/future_endpoint", "Create_CPE_Shelf", {})
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_call_sense_endpoint_with_post_method(monkeypatch):
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    monkeypatch.setattr(
        supported_prod_template, "post_sense", lambda *_, **__: {"message": "Call to SEnSE is successful"}
    )
    resp = spt_obj.call_sense_endpoint(
        "POST", "/arda/v1/future_endpoint", "Create_CPE_Shelf", {"cid": "84.L4XX.000058..CHTR"}
    )
    assert resp == {"message": "Call to SEnSE is successful"}


@pytest.mark.unittest
def test_call_sense_endpoint_with_put_method(monkeypatch):
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    monkeypatch.setattr(
        supported_prod_template, "put_sense", lambda *_, **__: {"message": "Call to SEnSE is successful"}
    )
    resp = spt_obj.call_sense_endpoint(
        "PUT", "/arda/v1/future_endpoint", "Create_CPE_Shelf", {"cid": "84.L4XX.000058..CHTR"}
    )
    assert resp == {"message": "Call to SEnSE is successful"}


@pytest.mark.unittest
def test_call_sense_endpoint_with_get_method(monkeypatch):
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    monkeypatch.setattr(
        supported_prod_template, "get_sense", lambda *_, **__: {"message": "Call to SEnSE is successful"}
    )
    resp = spt_obj.call_sense_endpoint(
        "GET", "/arda/v1/future_endpoint", "Create_CPE_Shelf", {"cid": "84.L4XX.000058..CHTR"}
    )
    assert resp == {"message": "Call to SEnSE is successful"}


@pytest.mark.unittest
def test_call_sense_endpoint_generating_mock_response(monkeypatch):
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    resp = spt_obj.call_sense_endpoint("DELETE", "/arda/v1/future_endpoint", "Create_CPE_Shelf", {"uni_type": "Trunked"})
    assert resp == {
        "cpe_shelf": "string",
        "cpe_tid": "string",
        "cpe_uplink": "string",
        "cpe_trunked_path": "string",
        "cpe_handoff": "string",
        "cpe_handoff_paid": "string",
        "circ_path_inst_id": "string",
    }


@pytest.mark.unittest
def test_call_sense_endpoint_generating_mock_response2(monkeypatch):
    data = home_run_payload
    spt_obj = supported_prod_template.SupportedProdTemplate(data.get("z_side_info"))
    resp = spt_obj.call_sense_endpoint(
        "", "/arda/v1/future_endpoint", "Assign_GSIP_Attributes", {"cid": "84.L4XX.000058..CHTR"}
    )
    assert resp == {"message": "GSIP Attributes have been added successfully."}


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_Hosted_Voice(monkeypatch):
    data = home_run_payload
    payload_a = data.get("a_side_info")
    payload_a["product_name"] = "Hosted Voice - (DOCSIS)"
    payload_a["side"] = "a_side"
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "Hosted Voice - (Overlay)"
    payload_z["side"] = "z_side"
    revised_payload = {"a_side_info": payload_a, "z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda self: [payload_a, payload_z]
    )
    monkeypatch.setattr(supported_prod_template, "get_granite", lambda self: circuit_sites_resp)
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert pui_obj == {"circ_path_inst_id": "732695"}
    # assert {"circ_path_inst_id": "732695"} in pui_obj


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_Hosted_Voice_with_missing_circ_path_inst_id(monkeypatch):
    data = home_run_payload
    payload_a = data.get("a_side_info")
    payload_a["product_name"] = "Hosted Voice - (DOCSIS)"
    payload_a["side"] = "a_side"
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "Hosted Voice - (Overlay)"
    payload_z["side"] = "z_side"
    revised_payload = {"a_side_info": payload_a, "z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda self: [payload_a, payload_z]
    )
    monkeypatch.setattr(
        supported_prod_template, "get_granite", lambda self: circuit_sites_resp[0].pop("CIRC_PATH_INST_ID")
    )
    try:
        spt_obj.product_uniqueness_identifier()
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_Hosted_Voice_Fiber(monkeypatch):
    data = home_run_payload
    payload_a = data.get("a_side_info")
    payload_a["product_name"] = "Fiber Internet Access"
    payload_a["side"] = "a_side"
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "Hosted Voice - (Fiber)"
    payload_z["side"] = "z_side"
    revised_payload = {"a_side_info": payload_a, "z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda _: [payload_a, payload_z]
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "service_type_builder", lambda self, data: None)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_HVF_uniqueness_task_list",
        lambda self: ["Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: None
    )
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert "  -- Product Uniqueness --" in pui_obj
    assert len(pui_obj) == 2


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_Wireless_Internet_Access(monkeypatch):
    data = home_run_payload
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "Wireless Internet Access - Off-Net"
    payload_z["side"] = "z_side"
    revised_payload = {"z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda _: [payload_z]
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "service_type_builder", lambda self, data: None)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_WIA_uniqueness_task_list",
        lambda self: ["Assign_Relationship", "Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: None
    )
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert "  -- Product Uniqueness --" in pui_obj
    assert len(pui_obj) == 1


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_RPHY(monkeypatch):
    data = home_run_payload
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "FC + Remote PHY"
    payload_z["side"] = "z_side"
    revised_payload = {"z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda _: [payload_z]
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "service_type_builder", lambda self, data: None)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_RPHY_uniqueness_task_list",
        lambda self: ["Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: None
    )
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert "  -- Product Uniqueness --" in pui_obj
    assert len(pui_obj) == 1


@pytest.mark.unittest
def test_product_uniqueness_identifier_for_SIP(monkeypatch):
    data = home_run_payload
    payload_z = data.get("z_side_info")
    payload_z["product_name"] = "SIP - Trunk (Fiber)"
    payload_z["side"] = "z_side"
    revised_payload = {"z_side_info": payload_z}
    spt_obj = supported_prod_template.SupportedProdTemplate(revised_payload)
    logger.debug(f"spt_obj.payload - {spt_obj.payload}")
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "get_payload_for_each_side", lambda _: [payload_z]
    )
    monkeypatch.setattr(supported_prod_template.SupportedProdTemplate, "service_type_builder", lambda self, data: None)
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate,
        "get_HVF_uniqueness_task_list",
        lambda self: ["Assign_GSIP_Attributes"],
    )
    monkeypatch.setattr(
        supported_prod_template.SupportedProdTemplate, "execute_each_task", lambda self, tlist, payload: None
    )
    pui_obj = spt_obj.product_uniqueness_identifier()
    logger.debug(f"pui_obj - {pui_obj}")
    assert "  -- Product Uniqueness --" in pui_obj
    assert len(pui_obj) == 1
