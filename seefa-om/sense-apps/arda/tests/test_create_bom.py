import pytest

from arda_app.bll import determine_bom as db
from common_sense.common.errors import AbortException


# Successful test cases
@pytest.mark.unittest
def test_determine_bom_wia_service_codes():
    payload = {
        "cid": "test",
        "product_name": "Wireless Internet Access",
        "granite_site_name": "test",
        "service_code": "RW700",
    }
    assert db.determine_bom(payload) == "WIA Cradlepoint E100 BOM"


@pytest.mark.unittest
def test_determine_bom_voice_products():
    payload = {"cid": "test", "product_name": "SIP", "granite_site_name": "test"}
    assert db.determine_bom(payload) == "HCT_SIP plus Adva114 BOM"


@pytest.mark.unittest
def test_bandwidth_logic(monkeypatch):
    monkeypatch.setattr("arda_app.bll.net_new.utils.shelf_utils.get_device_bw", lambda *args: "1 Gbps")
    payload = {"agg_bandwidth": "1 Gbps"}
    assert db.bandwidth_logic(payload) == "ADVA114 BOM"


@pytest.mark.unittest
def test_adva_1g_template():
    assert db.adva_1g_template({}) == "ADVA114 BOM"
    assert db.adva_1g_template({"voltage": "DC 48"}) == "ADVA114 DC BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_models(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG108"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "ADVA108 BOM"


@pytest.mark.unittest
def test_bandwidth_logic_mbps(monkeypatch):
    monkeypatch.setattr("arda_app.bll.net_new.utils.shelf_utils.get_device_bw", lambda *args: "1 Gbps")
    assert db.bandwidth_logic({"agg_bandwidth": "100 Mbps"}) == "ADVA114 BOM"


@pytest.mark.unittest
def test_adva_10g_template():
    assert db.adva_10g_template({}) == "ADVA108 BOM"
    assert db.adva_10g_template({"voltage": "DC 48"}) == "ADVA116 PRO H BOM DC"
    assert (
        db.adva_10g_template({"type_of_protection_needed": "Optional UDA - Redundant Power", "voltage": "DC 48"})
        == "ADVA116 PRO H BOM DC"
    )


@pytest.mark.unittest
def test_determine_bom_wia_rw702():
    payload = {
        "cid": "test",
        "product_name": "Wireless Internet Access",
        "granite_site_name": "test",
        "service_code": "RW702",
    }
    assert db.determine_bom(payload) == "WIA Cradlepoint W1850 BOM"


@pytest.mark.unittest
def test_determine_bom_wia_rw703():
    payload = {
        "cid": "test",
        "product_name": "Wireless Internet Access",
        "granite_site_name": "test",
        "service_code": "RW703",
    }
    assert db.determine_bom(payload) == "WIA Cradlepoint W1855 BOM"


@pytest.mark.unittest
def test_determine_bom_wia_5g_media(monkeypatch):
    monkeypatch.setattr("arda_app.bll.determine_bom.get_attributes_for_path", lambda *args: [{"serviceMedia": "5G"}])
    payload = {"cid": "test", "product_name": "Wireless Internet Access", "granite_site_name": "test"}
    assert db.determine_bom(payload) == "WIA Cradlepoint W1850 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_fsp_150_xg116proh(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG116PROH"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "ADVA116 PRO H BOM AC"


@pytest.mark.unittest
def test_granite_cpe_logic_fsp_150_xg116proh_dc(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG116PROH"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {"voltage": "DC 48"}) == "ADVA116 PRO H BOM DC"


@pytest.mark.unittest
def test_granite_cpe_logic_fsp_150_xg116proh_redundant_power(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG116PROH"}],
    )
    assert (
        db.granite_cpe_logic(
            "cid", "test_site", "product", {"type_of_protection_needed": "Optional UDA - Redundant Power"}
        )
        == "ADVA116 PRO H BOM AC"
    )


@pytest.mark.unittest
def test_granite_cpe_logic_fsp_150_xg116pro(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG116PRO"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "ADVA108 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_cradlepoint_models(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "E100 C4D/C7C"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "WIA Cradlepoint E100 BOM"

    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "W1855"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "WIA Cradlepoint W1855 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_voice_products_with_model(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-GE114PRO-C"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "SIP product", {}) == "HCT_SIP plus Adva114 BOM"
    assert db.granite_cpe_logic("cid", "test_site", "PRI product", {}) == "HCT_PRI plus Adva114 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_arc_cba850(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "ARC CBA850"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "WIA Cradlepoint E100 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_fsp_150_xg116proh_redundant_dc(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG116PROH"}],
    )
    assert (
        db.granite_cpe_logic(
            "cid",
            "test_site",
            "product",
            {"type_of_protection_needed": "Optional UDA - Redundant Power", "voltage": "DC 48"},
        )
        == "ADVA116 PRO H BOM DC"
    )


@pytest.mark.unittest
def test_bandwidth_logic_10gbps(monkeypatch):
    monkeypatch.setattr("arda_app.bll.net_new.utils.shelf_utils.get_device_bw", lambda *args: "10 Gbps")
    assert db.bandwidth_logic({"agg_bandwidth": "10 Gbps"}) == "ADVA108 BOM"


@pytest.mark.unittest
def test_determine_bom_with_agg_bandwidth(monkeypatch):
    monkeypatch.setattr("arda_app.bll.determine_bom.bandwidth_logic", lambda *args: "ADVA114 BOM")
    payload = {
        "cid": "test",
        "product_name": "Fiber Internet Access",
        "granite_site_name": "test",
        "agg_bandwidth": "1 Gbps",
    }
    assert db.determine_bom(payload) == "ADVA114 BOM"


@pytest.mark.unittest
def test_determine_bom_pri_product():
    payload = {"cid": "test", "product_name": "PRI Service", "granite_site_name": "test"}
    assert db.determine_bom(payload) == "HCT_PRI plus Adva114 BOM"


@pytest.mark.unittest
def test_adva_1g_template_redundant_power_ac():
    payload = {"type_of_protection_needed": "Optional UDA - Redundant Power", "voltage": "AC 120"}
    assert db.adva_1g_template(payload) == "ADVA114 PRO HE AC (dual PS) BOM"


@pytest.mark.unittest
def test_adva_10g_template_redundant_power_ac():
    payload = {"type_of_protection_needed": "Optional UDA - Redundant Power", "voltage": "AC 120"}
    assert db.adva_10g_template(payload) == "ADVA116 PRO H BOM AC"


@pytest.mark.unittest
def test_determine_bom_default_case(monkeypatch):
    monkeypatch.setattr("arda_app.bll.determine_bom.granite_cpe_logic", lambda *args: "ADVA114 BOM")
    payload = {"cid": "test", "product_name": "Regular Product", "granite_site_name": "test"}
    assert db.determine_bom(payload) == "ADVA114 BOM"


@pytest.mark.unittest
def test_determine_bom_wia_lte_media(monkeypatch):
    monkeypatch.setattr("arda_app.bll.determine_bom.get_attributes_for_path", lambda *args: [{"serviceMedia": "LTE"}])
    payload = {"cid": "test", "product_name": "Wireless Internet Access", "granite_site_name": "test"}
    assert db.determine_bom(payload) == "WIA Cradlepoint E100 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_fsp_150_ge114pro_c_non_voice(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-GE114PRO-C"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "Fiber Internet Access", {}) == "ADVA114 BOM"


@pytest.mark.unittest
def test_granite_cpe_logic_w1850_model(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "W1850"}],
    )
    assert db.granite_cpe_logic("cid", "test_site", "product", {}) == "WIA Cradlepoint W1850 BOM"


@pytest.mark.unittest
def test_adva_1g_template_redundant_power_dc():
    payload = {"type_of_protection_needed": "Optional UDA - Redundant Power", "voltage": "DC 48"}
    assert db.adva_1g_template(payload) == "ADVA114 PRO HE DC (dual PS) BOM"


# AbortException test cases
@pytest.mark.unittest
def test_determine_bom_no_site_name_error():
    with pytest.raises(AbortException) as exc_info:
        db.determine_bom({"cid": "test", "product_name": "test"})
    assert "granite site name was not provided" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_determine_bom_wia_backup_error():
    with pytest.raises(AbortException) as exc_info:
        db.determine_bom({"cid": "test", "product_name": "Wireless Internet Access Backup", "granite_site_name": "test"})
    assert "Unsupported product :: Wireless Internet Access Backup" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_determine_bom_wia_wisim_error():
    with pytest.raises(AbortException) as exc_info:
        db.determine_bom(
            {
                "cid": "test",
                "product_name": "Wireless Internet Access",
                "granite_site_name": "test",
                "service_code": "WISIM",
            }
        )
    assert "Unsupported WIA Service Code: WISIM" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_determine_bom_wia_service_media_error(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_attributes_for_path", lambda *args: [{"serviceMedia": "UNKNOWN"}]
    )
    with pytest.raises(AbortException) as exc_info:
        db.determine_bom({"cid": "test", "product_name": "Wireless Internet Access", "granite_site_name": "test"})
    assert "Unexpected WIA service media UNKNOWN" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_determine_bom_voice_dc_voltage_error():
    with pytest.raises(AbortException) as exc_info:
        db.determine_bom({"cid": "test", "product_name": "SIP", "granite_site_name": "test", "voltage": "DC 48"})
    assert "No BOM template for DC voltage ADVA 114PRO on Voice circuit" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_determine_bom_voice_redundant_power_error():
    with pytest.raises(AbortException) as exc_info:
        db.determine_bom(
            {
                "cid": "test",
                "product_name": "PRI",
                "granite_site_name": "test",
                "type_of_protection_needed": "Optional UDA - Redundant Power",
            }
        )
    assert "No BOM template for Redundant Power ADVA 114PRO on Voice circuit" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_multiple_models(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [
            {"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test1", "MODEL": "FSP 150-XG116PROH"},
            {"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test2", "MODEL": "FSP 150-XG116PROH"},
        ],
    )
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "product", {})
    assert "More than one ADVA shelf in circuit path at test_site" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_no_site_match(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "other_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-XG108"}],
    )
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "product", {})
    assert "No ADVAs in the path with the Granite site: test_site" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_unknown_model(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "UNKNOWN_MODEL"}],
    )
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "product", {})
    assert "No BOM template for CPE model: UNKNOWN_MODEL" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_voice_dc_voltage_error(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-GE114PRO-C"}],
    )
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "SIP product", {"voltage": "DC 48"})
    assert "No BOM template for DC voltage ADVA 114PRO on Voice circuit" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_voice_redundant_power_error(monkeypatch):
    monkeypatch.setattr(
        "arda_app.bll.determine_bom.get_path_elements",
        lambda *args: [{"A_SITE_NAME": "test_site", "ELEMENT_NAME": "test", "MODEL": "FSP 150-GE114PRO-C"}],
    )
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic(
            "cid", "test_site", "PRI product", {"type_of_protection_needed": "Optional UDA - Redundant Power"}
        )
    assert "No BOM template for Redundant Power ADVA 114PRO on Voice circuit" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_bandwidth_logic_invalid_format():
    with pytest.raises(AbortException) as exc_info:
        db.bandwidth_logic({"agg_bandwidth": "invalid format"})
    assert "Payload agg_bandwidth field invalid format is invalid" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_non_list_path_elements(monkeypatch):
    monkeypatch.setattr("arda_app.bll.determine_bom.get_path_elements", lambda *args: "not_a_list")
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "product", {})
    assert "No BOM template for CPE model: None" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_empty_list(monkeypatch):
    monkeypatch.setattr("arda_app.bll.determine_bom.get_path_elements", lambda *args: [])
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "product", {})
    assert "No ADVAs in the path with the Granite site: test_site" in exc_info.value.data["message"]


@pytest.mark.unittest
def test_granite_cpe_logic_exception_handling(monkeypatch):
    def mock_get_path_elements(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr("arda_app.bll.determine_bom.get_path_elements", mock_get_path_elements)
    with pytest.raises(AbortException) as exc_info:
        db.granite_cpe_logic("cid", "test_site", "product", {})
    assert "No ADVA in the path of circuit cid" in exc_info.value.data["message"]
