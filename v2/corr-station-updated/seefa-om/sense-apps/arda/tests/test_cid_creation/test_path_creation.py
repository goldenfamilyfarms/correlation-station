import time
import pytest
from arda_app.api import circuitpath as c4
from copy import deepcopy
from arda_app.bll.cid import pathid as path_ops
from arda_app.common import npa_operations
from tests.test_cid_creation.test_cid_creation_mock_functions import MockResponse, path_data_v2

cp_endpoint = "/arda/v4/circuitpath"


def mock_post(*args, **kwargs):
    return MockResponse({"pathId": "success", "instId": "success", "pathInstanceId": "success"})


@pytest.mark.unittest
def test_unitless_bandwidths():
    rf_path = {"product_service": "COM-VIDEO SBB", "bw_value": "5", "bw_unit": "Gbps"}
    wireless_path = {
        "product_service": "CUS-INTERNET ACCESS",
        "service_media": "LTE",
        "bw_value": "5",
        "bw_unit": "Gbps",
    }
    dark_path = {"product_service": "CAR-DARKFIBER"}

    rf_path = path_ops.unitless_bandwidths(rf_path)
    assert rf_path["bw_unit"] == "Gbps"
    assert rf_path["bw_value"] == "5"

    rf_path["bw_value"] = "RF"
    rf_path["bw_unit"] = ""
    rf_path = path_ops.unitless_bandwidths(rf_path)
    assert rf_path["bw_value"] == "RF"

    wireless_path = path_ops.unitless_bandwidths(wireless_path)
    assert wireless_path["bw_value"] == "RF"

    dark_path = path_ops.unitless_bandwidths(dark_path)
    assert dark_path["bw_value"] == "OPTICAL"

    reg_path = {"product_service": "COM-DIA", "bw_value": "1000", "bw_unit": "Mbps"}

    with pytest.raises(Exception):
        assert path_ops.unitless_bandwidths(reg_path) is None

    reg_path2 = {"product_service": "COM-DIA", "bw_value": "801", "bw_unit": "Gbps"}

    with pytest.raises(Exception):
        assert path_ops.unitless_bandwidths(reg_path2) is None


@pytest.mark.unittest
def test_check_if_path_has_a_side():
    assert path_ops.check_if_path_has_a_side({}) is False
    assert path_ops.check_if_path_has_a_side(None) is False
    assert path_ops.check_if_path_has_a_side({"a_side_site": "test"}) is True


@pytest.mark.unittest
def test_check_sites_for_customer_all_variations():
    "Tests with both side sites, 1 side site, and no side sites"
    new_test_data_v4 = deepcopy(path_data_v2)
    assert path_ops.check_sites_for_customer(new_test_data_v4) is True

    new_test_data_v4["a_side_site"] = ""
    assert path_ops.check_sites_for_customer(new_test_data_v4) is True

    new_test_data_v4["z_side_site"] = ""
    assert path_ops.check_sites_for_customer(new_test_data_v4) is False


@pytest.mark.unittest
def test_check_sites_for_zip_all_variations():
    "Tests with both side sites, 1 side site, and no side sites"
    data = deepcopy(path_data_v2)
    data["z_side_site"] = {
        "customer": "KNIGHTS INN-CHARLOTTE",
        "site": "SPBJFLSJ-KNIGHTS INN//25953 54TH AVE N",
        "site_zip_code": "12465",
    }
    assert path_ops.check_side_for_val(data, "a_side_site", "site_zip_code") is False
    assert path_ops.check_side_for_val(data, "z_side_site", "site_zip_code") is True
    assert path_ops.get_value_from_path(data, "site_zip_code") == "12465"

    data["a_side_site"] = {
        "customer": "KNIGHTS INN-CHARLOTTE",
        "site": "SPBJFLSJ-KNIGHTS INN//25953 54TH AVE N",
        "site_zip_code": "62841",
    }
    data["z_side_site"] = ""
    assert path_ops.check_side_for_val(data, "a_side_site", "site_zip_code") is True
    assert path_ops.check_side_for_val(data, "z_side_site", "site_zip_code") is False
    assert path_ops.get_value_from_path(data, "site_zip_code") == "62841"

    data["a_side_site"] = ""
    assert path_ops.check_side_for_val(data, "a_side_site", "site_zip_code") is False
    assert path_ops.check_side_for_val(data, "z_side_site", "site_zip_code") is False
    assert path_ops.get_value_from_path(data, "site_zip_code") is None

    data["z_side_site"] = {"customer": "", "site": "", "site_zip_code": ""}
    data["a_side_site"] = {"customer": "", "site": "", "site_zip_code": ""}
    assert path_ops.check_side_for_val(data, "a_side_site", "site_zip_code") is False
    assert path_ops.check_side_for_val(data, "z_side_site", "site_zip_code") is False


@pytest.mark.unittest
def test_create_path_v4(monkeypatch):
    path1 = {
        "bw_value": "",
        "bw_unit": "",
        "product_service": "FINISHED INTERNET",
        "z_side_site": {"site": "test"},
        "service_media": "test",
        "off-net_provider_cid": "test",
        "off-net_service_provider": "test",
        "assigned_ip_subnet": "test",
        "ipv4_service_type": "test",
        "managed_service": "test",
    }
    path2 = {
        "bw_value": "",
        "bw_unit": "",
        "product_service": "FINISHED INTERNET",
        "a_side_site": {"site_enni": "test"},
        "tsp_auth": "test",
        "z_side_site": {"site": "test"},
        "service_media": "test",
        "off-net_provider_cid": "test",
        "off-net_service_provider": "test",
        "assigned_ip_subnet": "test",
        "ipv4_service_type": "test",
        "managed_service": "test",
    }
    monkeypatch.setattr(path_ops, "check_if_path_has_a_side", lambda _: False)
    monkeypatch.setattr(path_ops, "template_selector_v2", lambda *args, **kwargs: "test")
    monkeypatch.setattr(path_ops, "path_type_selector", lambda _: "test")
    monkeypatch.setattr(path_ops, "get_value_from_path", lambda *args: "test")
    monkeypatch.setattr(path_ops, "path_creation_call", lambda *args: "test")

    with pytest.raises(Exception):
        assert path_ops.create_path_v4("test", path1, "suffix_test") is None

    monkeypatch.setattr(path_ops, "check_if_path_has_a_side", lambda _: True)
    monkeypatch.setattr(path_ops, "set_a_side_from_enni", lambda _: path2)

    with pytest.raises(Exception):
        assert path_ops.create_path_v4("test", path2) is None

    path2["product_service"] = "CUS-INTERNET ACCESS"

    with pytest.raises(Exception):
        assert path_ops.create_path_v4("test", path2) is None

    monkeypatch.setattr(path_ops, "check_if_path_has_a_side", lambda _: False)
    path2["product_service"] = "COM-VIDEO SBB"

    with pytest.raises(Exception):
        assert path_ops.create_path_v4("test", path2) is None


@pytest.mark.unittest
def test_path_creation_call(monkeypatch):
    path1 = {
        "bw_value": "100",
        "bw_unit": "Mbps",
        "customer_type": "ENTERPRISE",
        "product_service": "COM-DIA",
        "z_side_site": {
            "customer": "ACCT-27659472",
            "site": "AUSTTXEG-TEST S 20//5000 PLAZA ON THE LK",
            "site_zip_code": "78746",
        },
        "tsp_expiration": "",
        "path_order_num": "COM-FIA-080216,ENG-03723700",
        "service_media": "FIBER",
        "contract_type": "NON-FEDERAL",
    }

    monkeypatch.setattr(path_ops, "post_granite", lambda *args, **kwargs: MockResponse(path1))
    assert path_ops.path_creation_call("test_url", "test_body") == path1

    monkeypatch.setattr(path_ops, "post_granite", lambda *args, **kwargs: MockResponse({}, status_code=500))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert path_ops.path_creation_call("test_url", "test_body") is None


@pytest.mark.unittest
def test_create_path_v4_data_parsing(monkeypatch):
    monkeypatch.setattr(path_ops, "post_granite", mock_post)

    path_data = {
        "bw_value": "100",
        "bw_unit": "MBPS",
        "customer_type": "Dedicated Internet Access",
        "product_service": "COM-DIA",
        "a_side_site": {"customer": "", "site": "", "site_zip_code": ""},
        "z_side_site": {
            "customer": "TX COMMERCIAL-CARRIER SERVICES",
            "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
            "site_zip_code": "78664",
        },
        "path_order_num": "1234",
        "managed_service": False,
        "service_media": "Fiber",
    }

    path = path_ops.create_path_v4("51.L1XX.%..CHTR", path_data)
    assert path["pathId"] == "success"


@pytest.mark.unittest
def test_create_path_v4_data_parsing_for_ethernet(monkeypatch):
    monkeypatch.setattr(path_ops, "post_granite", mock_post)

    path_data = {
        "bw_value": "100",
        "bw_unit": "MBPS",
        "customer_type": "Dedicated Internet Access",
        "product_service": "COM-EPL",
        "a_side_site": {
            "customer": "PARADIGM (PAR)",
            "site": "AUSWTX49-VZW//2012 BRUSHY CREEK RD",
            "site_zip_code": "78664",
        },
        "z_side_site": {
            "customer": "TX COMMERCIAL-CARRIER SERVICES",
            "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
            "site_zip_code": "78664",
        },
        "path_order_num": "1234",
        "service_media": "Fiber",
        "managed_service": False,
    }

    path = path_ops.create_path_v4("51.L1XX.%..CHTR", path_data)
    assert path["pathId"] == "success"


@pytest.mark.unittest
def test_create_path_v4_master(client, monkeypatch, path=path_data_v2):
    """Integration test to create a path. Doesn't *actually* create a path, but verifies output is in correct format,
    and cid is created and passed in correctly"""
    monkeypatch.setattr(c4, "get_npa_and_site_type_with_site", lambda *args, **kwargs: ("npa", "site_type"))
    monkeypatch.setattr(c4, "generate_cid_v3", lambda *args: "3")
    monkeypatch.setattr(c4, "get_suffix", lambda *args, **kwargs: ".002")
    monkeypatch.setattr(c4, "create_path_v4", lambda *args, **kwargs: {"pathId": "123", "instId": "456"})
    monkeypatch.setattr(npa_operations, "get_granite", lambda *args: [{"npaNxx": "51"}])

    r = client.post(cp_endpoint, json=path)
    assert r.status_code, "" if not r.json().get("message") else r.json["message"]

    payloade = deepcopy(path)
    payloade["path_order_num"] = "OL-UC"
    monkeypatch.setattr(c4, "get_suffix", lambda *args, **kwargs: None)
    monkeypatch.setattr(c4, "_add_parent_network_element", lambda *args, **kwargs: None)

    resp = client.post(cp_endpoint, json=payloade)
    assert resp.status_code == 201

    del payloade["z_side_site"]["site"]
    resp = client.post(cp_endpoint, json=payloade)
    assert resp.status_code == 500

    resp = client.post(cp_endpoint, json="ab1")
    assert resp.status_code == 500


@pytest.mark.unittest
def test_create_path_v4_Retail_DIA(client, monkeypatch):
    """Integration test to create a path. Doesn't *actually* create a path, but verifies output is in correct format,
    and cid is created and passed in correctly"""
    monkeypatch.setattr(c4, "create_path_v4", lambda *args: {"pathId": "123", "instId": "456"})
    monkeypatch.setattr(c4, "generate_cid_v3", lambda *args: "3")
    monkeypatch.setattr(npa_operations, "get_granite", lambda _: [{"npaNxx": "64"}])

    data = deepcopy(path_data_v2)
    data["customer_type"] = "Dedicated Internet Access"

    r = client.post(cp_endpoint, json=data)
    assert r.status_code == 201
    assert r.json()["path"] == "123"
    assert r.json()["circuit_inst_id"] == "456"


@pytest.mark.unittest
def test_create_sister_path(monkeypatch):
    monkeypatch.setattr(path_ops, "create_path_v4", lambda *args: None)
    assert path_ops.create_sister_path("test", {}) is None


@pytest.mark.unittest
def test_create_sub_paths(client, monkeypatch):
    """Integration test to create a path. Doesn't *actually* create a path, but verifies output is in correct format,
    and cid is created and passed in correctly"""
    monkeypatch.setattr(c4, "create_path_v4", lambda *args: {"pathId": "123", "instId": "456"})
    monkeypatch.setattr(c4, "generate_cid_v3", lambda *args: "52")

    def mock_create_sub_path(new_cid, path):
        return [
            {"path": "31.TGXX.%..CHTR..001", "circuit_inst_id": "1234"},
            {"path": "31.TGXX.%..CHTR..002", "circuit_inst_id": "1234"},
            {"path": "31.TGXX.%..CHTR..003", "circuit_inst_id": "1234"},
        ]

    monkeypatch.setattr(c4, "create_sub_paths", mock_create_sub_path)

    path = {
        "bw_value": "200",
        "bw_unit": "MBPS",
        "customer_type": "Carrier",
        "product_service": "CUS-VOICE-PRI",
        "a_side_site": {
            "customer": "PARADIGM (PAR)",
            "site": "AUSWTX49-VZW//2012 BRUSHY CREEK RD",
            "site_zip_code": "78664",
        },
        "z_side_site": {
            "customer": "TX COMMERCIAL-CARRIER SERVICES",
            "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
            "site_zip_code": "78664",
        },
        "path_order_num": "1234",
        "service_media": "Fiber",
        "trunk": "3",
    }

    monkeypatch.setattr(npa_operations, "get_granite", lambda _: [{"npaNxx": "52"}])

    r = client.post(cp_endpoint, json=path)
    assert r.status_code == 201

    response_body = {
        "path": "123",
        "circuit_inst_id": "456",
        "relatedCircuitId": [
            {"path": "31.TGXX.%..CHTR..001", "circuit_inst_id": "1234"},
            {"path": "31.TGXX.%..CHTR..002", "circuit_inst_id": "1234"},
            {"path": "31.TGXX.%..CHTR..003", "circuit_inst_id": "1234"},
        ],
    }
    assert response_body == r.json()


@pytest.mark.unittest
def test_create_sub_paths2(monkeypatch):
    monkeypatch.setattr(path_ops, "create_path_v4", lambda *args: {"pathId": "test", "instId": "test"})
    assert path_ops.create_sub_paths({"trunk": 1}, None) == [{"path": "test"}]
    assert path_ops.create_sub_paths({"trunk": 0}, None) == []

    with pytest.raises(Exception):
        assert path_ops.create_sub_paths({"trunk": "test"}, None) is None


@pytest.mark.unittest
def test_create_two_paths(client, monkeypatch):
    """Integration test to create a path. Doesn't *actually* create a path, but verifies output is in correct format,
    and cid is created and passed in correctly"""
    monkeypatch.setattr(c4, "create_path_v4", lambda *args: {"pathId": "123", "instId": "456"})
    monkeypatch.setattr(c4, "create_sister_path", lambda *args: {"pathId": "124", "instId": "457"})
    monkeypatch.setattr(c4, "generate_cid_v3", lambda *args: "52")

    path = {
        "bw_value": "200",
        "bw_unit": "MBPS",
        "customer_type": "Carrier",
        "product_service": "CAR-E-ACCESS FIBER/DOCSIS EPL",
        "a_side_site": {
            "customer": "PARADIGM (PAR)",
            "site": "AUSWTX49-VZW//2012 BRUSHY CREEK RD",
            "site_zip_code": "78664",
        },
        "z_side_site": {
            "customer": "TX COMMERCIAL-CARRIER SERVICES",
            "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
            "site_zip_code": "78664",
        },
        "path_order_num": "1234",
        "service_media": "Fiber",
    }

    monkeypatch.setattr(npa_operations, "get_granite", lambda _: [{"npaNxx": "52"}])

    r = client.post(cp_endpoint, json=path)
    assert r.status_code == 201

    response_body = {"path": "123", "circuit_inst_id": "456", "relatedCircuitId": {"path": "124"}}
    assert response_body == r.json()


@pytest.mark.unittest
def test_get_pathid_v4(monkeypatch):
    site = {"bw_value": "", "product_service": ""}
    monkeypatch.setattr(path_ops, "get_value_from_path", lambda *args: None)
    monkeypatch.setattr(path_ops, "validate_elements_v2", lambda *args: (None, None))
    monkeypatch.setattr(path_ops, "get_npa_three_digits", lambda _: "test")
    monkeypatch.setattr(path_ops, "update_npa", lambda _: None)

    with pytest.raises(Exception):
        assert path_ops.get_pathid_v4(site, "FIA", npa_val=None) is None

    monkeypatch.setattr(path_ops, "validate_elements_v2", lambda *args: (None, "test"))
    monkeypatch.setattr(path_ops, "get_npa_three_digits", lambda _: "979")
    assert path_ops.get_pathid_v4(site, "CAR-CTBH 4G", npa_val=None) == (200, {"pathIDvalue": "97.test.%..CHTR"})

    monkeypatch.setattr(path_ops, "get_npa_three_digits", lambda _: "")

    with pytest.raises(Exception):
        assert path_ops.get_pathid_v4(site, "CAR-CTBH 4G", npa_val=None) is None


@pytest.mark.unittest
def test_get_service_code():
    scenarios = {
        "COM-VIDEO INSERTION": ("", "RF", "TVXE"),
        "CUS-VIDEO-IP": ("", "RF", "VSXX"),
        "COM-VIDEO SBB": ("", "RF", "VCXX"),
        "COM-WAVELENGTH": ("", "RF", "WCXX"),
        "COM-EPL": ("Gbps", "10", "L4XX"),
        "CUS-INTERNET ACCESS": ("", "RF", "L1XX"),
        "COM-DARKFIBER": ("", "OPTICAL", "TXXX"),
        "INT-MANAGEMENT": ("MBPS", "1", "L1XX"),
        "CAR-CTBH 4G": ("Gbps", "1", "L1XX"),
        "CAR-E-ACCESS FIBER/DOCSIS EPL": ("Gbps", "10", "L4XX"),
    }

    for k, v in scenarios.items():
        assert path_ops.get_service_code(v[0], v[1], k) == (None, v[2])


@pytest.mark.unittest
def test_get_suffix():
    assert path_ops.get_suffix("COM-DARKFIBER") == ".002"


@pytest.mark.unittest
def test_path_type_selector():
    assert path_ops.path_type_selector({"product_service": "CAR-DARKFIBER", "customer_type": "CTBH"}) == "DARK FIBER"
    assert path_ops.path_type_selector({"product_service": "CUS-VOICE-SIP"}) == "CUSTOMER SIP TRUNKS"
    assert path_ops.path_type_selector({"product_service": "CUS-VOICE-PRI"}) == "PRI TRUNKS"
    assert path_ops.path_type_selector({"product_service": "COM-VIDEO SBB"}) == "RF"
    assert path_ops.path_type_selector({"product_service": "CAR-WAVELENGTH", "customer_type": "ENTERPRISE"}) == "WDM"
    assert (
        path_ops.path_type_selector({"product_service": "CUS-INTERNET ACCESS", "customer_type": "ENTERPRISE"})
        == "ETHERNET"
    )
    assert path_ops.path_type_selector({"product_service": "INT-MANAGEMENT", "customer_type": "ENTERPRISE"}) is None


@pytest.mark.unittest
def test_product_service_validation_v2(monkeypatch):
    path = {}
    monkeypatch.setattr(path_ops, "check_sites_for_customer", lambda _: False)

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None

    monkeypatch.setattr(path_ops, "check_sites_for_customer", lambda _: True)
    monkeypatch.setattr(path_ops, "check_side_for_val", lambda *args: False)

    path = {"product_service": "CAR-CTBH 4G", "a_side_site": {"site_enni": "test"}}

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None

    path = {"product_service": "CAR-CTBH 4G", "bad_key": {"bad_key": "test"}}

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None

    path = {"product_service": "CAR-EPL"}

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None

    path = {"product_service": "test"}

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None

    path = {"product_service": "CUS-VOICE-SIP"}

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None

    path = {"product_service": "EPLAN"}
    monkeypatch.setattr(path_ops, "check_side_for_val", lambda *args: True)

    with pytest.raises(Exception):
        assert path_ops.product_service_validation_v2(path) is None


@pytest.mark.unittest
def test_set_a_side_from_enni(monkeypatch):
    path = {"a_side_site": {"site_enni": "test"}, "z_side_site": {"customer": "test"}}
    monkeypatch.setattr(path_ops, "get_site_by_enni_for_circuitpath", lambda _: {"siteName": "test", "zipcode": "12345"})
    assert path_ops.set_a_side_from_enni(path) == {
        "a_side_site": {"site_enni": "test", "site": "test", "site_zip_code": "12345", "customer": "test"},
        "z_side_site": {"customer": "test"},
    }

    path = {
        "product_service": "CAR-CTBH 4G",
        "a_side_site": {"site_enni": "test"},
        "z_side_site": {"customer": "test", "site_zip_code": "12345"},
    }
    monkeypatch.setattr(path_ops, "get_site_by_enni_for_circuitpath", lambda _, is_ctbh=True: [])
    assert path_ops.set_a_side_from_enni(path) == {
        "product_service": "CAR-CTBH 4G",
        "a_side_site": {"site_enni": "test", "site": "", "site_zip_code": "12345", "customer": "test"},
        "z_side_site": {"customer": "test", "site_zip_code": "12345"},
    }


@pytest.mark.unittest
def test_template_v2_decision():
    scenarios = {
        "CUS-VOICE-HOSTED": "WS HOSTED VOICE",
        "FINISHED INTERNET": "WS-FINISHED INTERNET TEMPLATE",
        "COM-EPL": "EXPO WS ETHERNET PATH TEMPLATE",
        "EPLAN": "WS ELAN VPLS",
        "": "EXPO WS ENTERPRISE DIA PATH TEMPLATE",
        "COM-DARKFIBER": "WS DARK FIBER",
        "INT-MANAGEMENT": "EXPO WS ETHERNET PATH TEMPLATE",
    }

    for k, v in scenarios.items():
        data = {"customer_type": "ENTERPRISE", "product_service": k, "path_order_num": "other"}
        assert path_ops.template_selector_v2(data) == v

    path = {"path_order_num": "OL-UC", "product_service": "CUS-VOICE-HOSTED", "customer_type": "Other"}
    assert path_ops.template_selector_v2(path) == "UC RING CENTRAL"

    path = {"product_service": "Other", "customer_type": "Other", "path_order_num": "other"}
    assert path_ops.template_selector_v2(path) == "EXPO WS CARRIER DIA PATH TEMPLATE"
    assert path_ops.template_selector_v2(path, suffix=True) == "PRI CHILD"


@pytest.mark.unittest
def test_update_npa(monkeypatch):
    monkeypatch.setattr(path_ops, "put_granite", lambda *args, **kwargs: True)
    path_ops.update_npa({"site": "test", "site_type": "test", "npa": "test"})


@pytest.mark.unittest
def test_validate_elements_v2():
    scenarios = {
        ("54321", "5", "CUS-VOICE-PRI", "GBPS"): (None, "HNXN"),
        ("54321", "20", "CUS-VOICE-HOSTED", "GBPS"): (None, "TGXX"),
        ("54321", "25", "CUS-VOICE-SIP", "GBPS"): (None, "IPXN"),
        ("54321", "1", "FIA", "GBPS"): (None, "L1XX"),
        ("54321", "2", "FIA", "GBPS"): (None, "L4XX"),
        ("54321", "999", "FIA", "MBPS"): (None, "L1XX"),
        ("54321", "1001", "FIA", "MBPS"): (None, "L4XX"),
        ("52312", "RF", "CUS-INTERNET ACCESS", None): (None, "L1XX"),
        ("54321", "5", "FIA", 1): (500, "BW Unit must be in the formats of - 'GBPS' or 'MBPS'"),
        ("54321", "5", "FIA", "GB"): (500, "BW Unit must be in the formats of - 'GBPS' or 'MBPS'"),
        ("654321", "5", "FIA", "GBPS"): (
            500,
            "Invalid value '654321' for query parameter zip_code. Expected length to be 5",
        ),
        ("54321", "5x", "FIA", "GBPS"): (500, "bw_val: 5x should be in integer form"),
        ("54321", "1", "INT-MANAGEMENT", "MBPS"): (None, "L1XX"),
        ("54321", "OPTICAL", "COM-DARKFIBER", None): (None, "TXXX"),
    }

    for k, v in scenarios.items():
        assert path_ops.validate_elements_v2(k[0], k[1], k[2], k[3]) == v


@pytest.mark.unittest
def test_validate_zip():
    assert path_ops.validate_zip("12345") is None
    assert path_ops.validate_zip("1234") == (
        500,
        "Invalid value '1234' for query parameter zip_code. Expected length to be 5",
    )


@pytest.mark.unittest
def test_video_check():
    path = {"z_side_site": {"customer": ""}}
    assert path_ops.video_check(path) == ""

    path = {"z_side_site": {"customer": "test"}, "product_service": "CUS-VIDEO-IP"}
    assert path_ops.video_check(path) == ""

    path = {"z_side_site": {"customer": "test"}, "product_service": "test"}
    assert path_ops.video_check(path) == "test"
