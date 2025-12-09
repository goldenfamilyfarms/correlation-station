from copy import deepcopy

import pytest

from arda_app.api import circuit_design as cd


url = "/arda/v1/circuit_design"

payload = {
    "z_side_info": {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "cid": "84.L4XX.000058..CHTR",
        "cpe_gear": "ADVA-XG108 (10G)",
    }
}


@pytest.mark.unittest
def test_circuit_design_aborts(client, monkeypatch):
    payload_abort = deepcopy(payload)

    # invalid payload
    r = client.post(url, json=None)
    assert r.status_code == 500

    # bad service type
    payload_abort["z_side_info"]["service_type"] = "bad service type"
    monkeypatch.setattr(cd, "colo_site_check", lambda *args, **kwargs: None)
    r = client.post(url, json=payload_abort)
    assert r.status_code == 500

    # bw_change w/pid
    payload_abort["z_side_info"]["service_type"] = "bw_change"
    payload_abort["z_side_info"]["pid"] = "pid"
    r = client.post(url, json=payload_abort)
    assert r.status_code == 500

    # no z_side
    payload_abort["z_side_info"] = None
    r = client.post(url, json=payload_abort)
    assert r.status_code == 500


@pytest.mark.unittest
def test_test_case_responses(client, monkeypatch):
    payload_resp = payload.copy()

    test_resp = {
        "circ_path_inst_id": "2480215",
        "maintenance_window_needed": "No",
        "hub_work_required": "No",
        "cpe_installer_needed": "No",
        "ip_video_on_cen": "No",
        "ctbh_on_cen": "No",
        "engineering_job_type": "Partial Disconnect",
        "cpe_model_number": "114PRO",
        "cosc_blacklist_ticket": "ticket_ABCD",
        "message": "",
    }
    monkeypatch.setattr(cd, "test_case_responses", lambda *args: test_resp)
    r = client.post(url, json=payload_resp)
    assert r.status_code == 200


@pytest.mark.unittest
def test_normal(client, monkeypatch):
    payload_norm = payload.copy()

    create_exit_criteria = {
        "circ_path_inst_id": "2480215",
        "maintenance_window_needed": "No",
        "hub_work_required": "No",
        "cpe_installer_needed": "No",
        "ip_video_on_cen": "No",
        "ctbh_on_cen": "No",
        "engineering_job_type": "Partial Disconnect",
        "cpe_model_number": "114PRO",
        "cosc_blacklist_ticket": "ticket_ABCD",
        "message": "",
    }

    # change_logical
    payload_norm["z_side_info"]["service_type"] = "change_logical"
    payload_norm["z_side_info"]["engineering_name"] = "engineering_name"
    payload_norm["z_side_info"]["change_reason"] = "Upgrading Service"
    payload_norm["z_side_info"]["pid"] = ""
    monkeypatch.setattr(cd, "entrance_criteria_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(cd, "colo_site_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(cd, "create_base_exit_criteria", lambda *args, **kwargs: {})
    monkeypatch.setattr(cd, "create_exit_criteria", lambda *args, **kwargs: create_exit_criteria)
    monkeypatch.setattr(
        cd,
        "logical_change_main",
        lambda *args, **kwargs: {
            "circ_path_inst_id": "1234",
            "engineering_job_type": "Logical Change",
            "maintenance_window_needed": "No",
            "message": "Logical Change updated successfully",
        },
    )
    resp = client.post(url, json=payload_norm)
    assert resp.status_code == 200

    # disconnect
    payload_norm["z_side_info"]["service_type"] = "disconnect"
    resp = {
        "circ_path_inst_id": "1234",
        "blacklist": "y",
        "networkcheck": "y",
        "hub_work_required": "y",
        "cpe_installer_needed": "y",
        "mw_needed": True,
        "cpe_installer": True,
        "create_new_elan_instance": "create_new_elan_instance",
        "customers_elan_name": "customer elan name",
    }

    resp_2 = ["", "", "", resp, "", ""]
    monkeypatch.setattr(
        cd,
        # "disconnect",
        "disconnect_processing",
        lambda *args, **kwargs: {
            "networkcheck": {"passed": True, "granite": [], "network": []},
            "cpe_model": "none",
            "blacklist": {"passed": True, "ips": []},
            "circ_path_inst_id": "1234",
            "engineering_job_type": "full",
            "hub_work_required": "true",
            "cpe_installer_needed": "false",
        },
    )
    resp = client.post(url, json=payload_norm)
    assert resp.status_code == 200

    # bw_change "Express BW Upgrade"
    payload_norm["z_side_info"]["service_type"] = "bw_change"
    payload_norm["z_side_info"]["engineering_job_type"] = "Express BW Upgrade"
    payload_norm["z_side_info"]["bw_speed"] = "10"
    payload_norm["z_side_info"]["bw_unit"] = "Gbps"
    payload_norm["z_side_info"]["retain_ip_addresses"] = "No"
    payload_norm["z_side_info"]["primary_fia_service_type"] = "LAN"
    payload_norm["z_side_info"]["usable_ip_addresses_requested"] = "No"
    payload_norm["z_side_info"]["ip_address"] = "N/A"
    payload_norm["z_side_info"]["connector_type"] = "RJ-45"
    payload_norm["z_side_info"]["uni_type"] = "ACCESS"
    monkeypatch.setattr(
        cd,
        "bandwidth_change_main",
        lambda *args, **kwargs: {"circ_path_inst_id": "1234", "engineering_job_type": "Express BW Upgrade"},
    )
    resp = client.post(url, json=payload_norm)

    assert resp.status_code == 200

    # bw_change "Normal Upgrade"
    payload_norm["z_side_info"]["engineering_job_type"] = "Upgrade"
    monkeypatch.setattr(
        cd,
        "bandwidth_change_main",
        lambda *args, **kwargs: {
            "circ_path_inst_id": "1234",
            "engineering_job_type": "Upgrade",
            "mw_needed": "No",
            "cpe_installer": False,
            "hub_work_required": False,
        },
    )
    resp = client.post(url, json=payload_norm)
    assert resp.status_code == 200

    # net_new_cj
    payload_norm["z_side_info"]["service_type"] = "net_new_cj"
    monkeypatch.setattr(cd, "build_circuit_design_main", lambda *args, **kwargs: resp_2)
    monkeypatch.setattr("arda_app.api.circuit_design.bw_check", lambda *args, **kwargs: None)
    resp = client.post(url, json=payload_norm)
    assert resp.status_code == 200
