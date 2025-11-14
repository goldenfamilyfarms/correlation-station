import pytest
from arda_app.api import circuit_design as cd
from arda_app.bll.circuit_design import common


payload = {
    "z_side_info": {
        "build_type": "MTU New Build",
        "assigned_cd_team": "Retail - NE",
        "primary_construction_job_fiber_type": "other",
        "protection_notes": "",
        "type_of_protection_needed": "",
        "complex": "no",
        "physical_diversity_needed": "no",
        "secondary_fia_service_type": "other",
    },
    "a_side_info": {"build_type": "MTU New Build"},
}


@pytest.mark.unittest
def test_health_check_api(client):
    """Test the /health check url"""
    resp = client.get("/arda/v1/health")
    assert resp.status_code == 200


@pytest.mark.unittest
def test_swagger_doc_resolves(client):
    """Test the swagger UI document loads properly"""
    resp = client.get("/arda/")
    assert resp.status_code == 200
    assert b"Design Microservice" in resp.content


@pytest.mark.unittest
def test_entrance_criteria_check():
    # good test - no abort occurs
    assert common.entrance_criteria_check(payload) is None

    # bad test - build_type = "Colocation"
    payload["z_side_info"]["build_type"] = "Colocation"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - assigned_cd_team = "Complex"
    payload["z_side_info"]["build_type"] = "MTU New Build"
    payload["z_side_info"]["assigned_cd_team"] = "Complex"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - primary_construction_job_fiber_type = "EPON"
    payload["z_side_info"]["assigned_cd_team"] = "Retail - NE"
    payload["z_side_info"]["primary_construction_job_fiber_type"] = "EPON"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - protection_notes is populated
    payload["z_side_info"]["primary_construction_job_fiber_type"] = "other"
    payload["z_side_info"]["protection_notes"] = "temp"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - type_of_protection_needed is populated
    payload["z_side_info"]["protection_notes"] = ""
    payload["z_side_info"]["type_of_protection_needed"] = "temp"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - complex = "yes"
    payload["z_side_info"]["type_of_protection_needed"] = ""
    payload["z_side_info"]["complex"] = "yes"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - physical_diversity_needed = "yes"
    payload["z_side_info"]["complex"] = "no"
    payload["z_side_info"]["physical_diversity_needed"] = "yes"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None

    # bad test - secondary_fia_service_type = "BGP"
    payload["z_side_info"]["physical_diversity_needed"] = "no"
    payload["z_side_info"]["secondary_fia_service_type"] = "BGP"
    with pytest.raises(Exception):
        assert common.entrance_criteria_check(payload) is None


def test_epl_circuit_check(monkeypatch):
    # bad test - abort missing a side info
    payload = {
        "z_side_info": {
            "service_type": "net_new_cj",
            "product_name": "EPL (Fiber)",
            "cid": "58.L1XX.002994..CHTR",
            "pid": "6060764",
            "connector_type": "RJ45",
            "uni_type": "Access",
            "granite_site_name": "IRNDNYBB-ROCHESTER ACADEMY OF SCIENCE CHARTER SCHOOL//125 KINGS HWY S",
        }
    }

    with pytest.raises(Exception):
        assert cd.epl_circuit_check(payload) is None

    # bad test - abort uni type trunked
    payload2 = {
        "z_side_info": {
            "service_type": "net_new_serviceable",
            "product_name": "EPL (Fiber)",
            "cid": "58.L1XX.002994..CHTR",
            "pid": None,
            "connector_type": "RJ45",
            "uni_type": "Trunked",
            "granite_site_name": "ROCKNYLZ-ROCHESTER ACADEMY OF SCIENCE CHARTER SCH//545 HUMBOLDT ST",
        },
        "a_side_info": {
            "service_type": "net_new_cj",
            "product_name": "EPL (Fiber)",
            "cid": "58.L1XX.002994..CHTR",
            "pid": "6060764",
            "connector_type": "RJ45",
            "uni_type": "Access",
            "granite_site_name": "IRNDNYBB-ROCHESTER ACADEMY OF SCIENCE CHARTER SCHOOL//125 KINGS HWY S",
        },
    }

    with pytest.raises(Exception):
        assert cd.epl_circuit_check(payload2) is None

    # bad test - abort cj and transport not equal
    payload2["z_side_info"]["uni_type"] = "Access"

    granite_resp2 = [{"PATH_NAME": "transport1"}, {"PATH_NAME": "transport2"}]

    monkeypatch.setattr(common, "get_path_elements", lambda *args, **kwargs: granite_resp2)

    with pytest.raises(Exception):
        assert cd.epl_circuit_check(payload2) is None

    # bad test - abort no circuit found
    payload2["z_side_info"]["pid"] = "456789"

    monkeypatch.setattr(common, "get_granite", lambda *args, **kwargs: {"retString": ""})

    with pytest.raises(Exception):
        assert cd.epl_circuit_check(payload2) is None

    # bad test - abort sf and granite site names do no match
    data = [
        {
            "aSideSiteName": "bad site name",
            "zSideSiteName": "ROCKNYLZ-ROCHESTER ACADEMY OF SCIENCE CHARTER SCH//545 HUMBOLDT ST",
        }
    ]

    monkeypatch.setattr(common, "get_granite", lambda *args, **kwargs: data)

    with pytest.raises(Exception):
        assert cd.epl_circuit_check(payload2) is None

    # good test
    data[0]["aSideSiteName"] = "IRNDNYBB-ROCHESTER ACADEMY OF SCIENCE CHARTER SCHOOL//125 KINGS HWY S"

    assert cd.epl_circuit_check(payload2) is None


@pytest.mark.unittest
def test_get_cpe_info(monkeypatch):
    cid = "58.L1XX.002994..CHTR"

    # bad test - no path elements found for cid
    monkeypatch.setattr(common, "get_path_elements", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert common.get_cpe_info(cid) is None

    # good test - port.get("TID") ends in "ZW"
    granite_resp = [
        {
            "CIRC_PATH_INST_ID": "2532667",
            "PATH_NAME": "71.L1XX.006171..TWCC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "VENDOR": "CISCO",
            "MODEL": "ME-3400-2CS",
            "TID": "ALNAWIBX1ZW",
        }
    ]
    monkeypatch.setattr(common, "get_path_elements", lambda *args, **kwargs: granite_resp)

    assert common.get_cpe_info(cid) == ("ALNAWIBX1ZW", "CISCO", "ME-3400-2CS")

    # good test - port.get("TID") does not end in with "ZW"
    granite_resp[0]["TID"] = "ALNAWIBX1"
    assert common.get_cpe_info(cid) == ("", "", "")
