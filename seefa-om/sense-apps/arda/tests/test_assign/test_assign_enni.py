import copy
import re

import pytest

from arda_app.api import assign_enni

from arda_app.bll.assign import enni
from arda_app.bll.assign import enni_utils as eu


payload = {
    "side": "z_side",
    "cid": "81.L1XX.006522..TWCC",
    "product_name": "Carrier E-Access (Fiber)",
    "spectrum_primary_enni": "94.KGFD.000010..TWCC",
}

granite_response = [
    {
        "CIRC_PATH_INST_ID": "",
        "ELEMENT_NAME": "",
        "PATH_Z_SITE": "",
        "PATH_STATUS": "Live",
        "A_SITE_NAME": "XXXXXXXXBHNX",
        "VENDOR": "JUNIPER",
        "ELEMENT_CATEGORY": "ROUTER",
        "ELEMENT_REFERENCE": "",
        "LEGACY_EQUIP_SOURCE": "L-TWC",
        "PORT_INST_ID": "",
        "PORT_ACCESS_ID": "",
        "TID": "",
        "LVL": "2",
        "BW_SIZE": "1000000",
        "PATH_REV": "1",
        "LEG_INST_ID": "12345",
    }
]


@pytest.mark.unittest
def test_no_cid(client):
    """Test design with a valid, defined cid"""

    data = copy.deepcopy(payload)
    del data["cid"]

    resp = client.post("arda/v1/assign_enni", json=data)

    assert resp.status_code == 500
    assert "Required query parameter(s) not specified: cid" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_json_error(monkeypatch, client):
    """Test design with a valid, defined cid"""

    resp = client.post("arda/v1/assign_enni", data=b"/")

    assert resp.status_code == 500
    assert "JSON decode error" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_granite_enni_info_fail(monkeypatch, client):
    """Test design with a valid, defined cid"""

    monkeypatch.setattr(enni, "get_path_elements", lambda *_: granite_response)
    monkeypatch.setattr(enni, "check_circ_path_inst_id", lambda *_: False)
    monkeypatch.setattr(enni, "_calculate_oversubscription", lambda *_: "0")

    resp = client.post("arda/v1/assign_enni", json=payload)

    assert resp.status_code == 500
    assert "ENNI Revisions" in resp.json().get("message")


@pytest.mark.unittest
def test_granite_status_fail(monkeypatch, client):
    """Test design with a valid, defined cid"""

    g_res = copy.deepcopy(granite_response)
    g_res[0]["PATH_STATUS"] = ""

    monkeypatch.setattr(enni, "get_path_elements", lambda *_: g_res)  # noqa: F821
    monkeypatch.setattr(enni, "check_circ_path_inst_id", lambda *_: True)
    monkeypatch.setattr(enni, "_calculate_oversubscription", lambda *_: "0")

    resp = client.post("arda/v1/assign_enni", json=payload)
    del g_res

    assert resp.status_code == 500
    assert "No Live items found" in resp.json().get("message")


@pytest.mark.unittest
def test_granite_vendor_fail(monkeypatch, client):
    """Test design with a valid, defined cid"""

    g_res = copy.deepcopy(granite_response)
    g_res[0]["VENDOR"] = "FF"

    monkeypatch.setattr(enni, "get_path_elements", lambda *_: g_res)
    monkeypatch.setattr(enni, "check_circ_path_inst_id", lambda *_: True)
    monkeypatch.setattr(enni, "_calculate_oversubscription", lambda *_: "0")

    resp = client.post("arda/v1/assign_enni", json=payload)

    assert resp.status_code == 500
    assert re.search("ENNI device (.*) is not supported at this time", resp.json().get("message"))


@pytest.mark.unittest
def test_dynamic_port_fail(monkeypatch, client):
    """Test design with a valid, defined cid"""

    g_res = copy.deepcopy(granite_response)
    g_res[0].update(
        {
            "TID": "CW",
            "PORT_INST_ID": "",
            "PORT_ACCESS_ID": "",
            "A_SITE_REGION": "TEST",
            "Z_SITE_REGION": "TEST",
            "A_STATE": "",
        }
    )

    g_res.append({"SEQUENCE": "SEQUENCE", "PORT_INST_ID": None, "LEGACY_EQUIP_SOURCE": "L-TWC"})

    monkeypatch.setattr(enni, "get_path_elements", lambda *args, **kwargs: g_res)
    monkeypatch.setattr(enni, "get_granite", lambda *args, **kwargs: g_res)
    monkeypatch.setattr(enni, "check_circ_path_inst_id", lambda *args, **kwargs: True)
    monkeypatch.setattr(enni, "_calculate_oversubscription", lambda *args, **kwargs: "0")
    monkeypatch.setattr(enni, "_inni_check", lambda *args, **kwargs: False)

    monkeypatch.setattr(enni, "put_granite", lambda *args, **kwargs: None)

    resp = client.post("arda/v1/assign_enni", json=payload)

    assert resp.status_code == 500
    assert "Get Dynamic Port Info Faild for" in resp.json().get("message")


@pytest.mark.unittest
def test_inni_added_fail(monkeypatch, client):
    """Test design with a valid, defined cid"""

    g_res = copy.deepcopy(granite_response)
    g_res[0].update({"A_SITE_REGION": "TEST", "Z_SITE_REGION": "OTHER", "A_STATE": ""})

    g_res.append({"SEQUENCE": "SEQUENCE", "PORT_INST_ID": "2"})

    monkeypatch.setattr(enni, "get_path_elements", lambda *_: g_res)
    monkeypatch.setattr(enni, "get_granite", lambda *_: g_res)
    monkeypatch.setattr(enni, "_inni_check", lambda *_: True)
    monkeypatch.setattr(enni, "_put_enni_mpls", lambda *_: True)
    monkeypatch.setattr(enni, "edna_mpls_in_path", lambda *_: True)
    monkeypatch.setattr(enni, "check_circ_path_inst_id", lambda *_: True)
    monkeypatch.setattr(enni, "_calculate_oversubscription", lambda *_: "0")

    monkeypatch.setattr(enni, "put_granite", lambda *_: None)

    resp = client.post("arda/v1/assign_enni", json=payload)

    assert resp.status_code == 500
    assert "INNI added but unable to perform latency testing" in resp.json().get("message")


@pytest.mark.unittest
def test_success(monkeypatch, client):
    """Test design with a valid, defined cid"""
    # mock assign_enni is ok

    monkeypatch.setattr(
        assign_enni, "assign_enni_main", lambda payload: {"message": "ENNI has been added successfully."}
    )

    resp = client.post("arda/v1/assign_enni", json=payload)

    assert resp.status_code == 200
    assert "ENNI has been added successfully" in resp.json().get("message")


@pytest.mark.unittest
def test_calculate_oversubscription(monkeypatch):
    # bad test abort on try and except no data from granite
    monkeypatch.setattr(eu, "get_granite", lambda *args, **Kwargs: None)

    with pytest.raises(Exception):
        assert eu._calculate_oversubscription("enni", 100) is None

    # good test return 0
    g_resp = [{"TOTAL_BW": "1000", "USED_BW": "0", "AVAILABLE_BW": "1000"}]
    monkeypatch.setattr(eu, "get_granite", lambda *args, **Kwargs: g_resp)

    assert eu._calculate_oversubscription("enni", 100) == "0"

    # good test return oversubscription percentage
    assert eu._calculate_oversubscription("enni", 2000) == "110"
