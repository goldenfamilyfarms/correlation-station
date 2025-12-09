import pytest

from arda_app.bll.circuit_design import exit_criteria

EXIT_FIELDS = {
    "cid": "51.L1XX.008342..CHTR",
    "circ_path_inst_id": "2356781",
    "engineering_job_type": "partial",
    "product_name": "Fiber Internet Access",
    "cpe_model_number": "FSP 150-GE114PRO-C",
    "cpe_installer_needed": "No",
    # "create_new_elan_instance": True,
    # "customer_elan_name": "customer vrfid",
    "network": {"passed": True, "granite": ["granite"], "network": ["network"]},
    "blacklist": {"passed": True, "ips": ["123.54.6.7"]},
}

glink = "https://granite-ise.chartercom.com:2269/web-access/WebAccess.html#"
plink = "HistoryToken,type=Path,mode=VIEW_MODE,instId="
instid = EXIT_FIELDS["circ_path_inst_id"]

EXIT_DATA = {
    "cid": "51.L1XX.008342..CHTR",
    "circ_path_inst_id": "2356781",
    "granite_link": f"{glink}{plink}{instid}",
    "maintenance_window_needed": "No",
    "ip_video_on_cen": "No",
    "ctbh_on_cen": "No",
    "cpe_model_number": "FSP 150-GE114PRO-C",
    # "create_new_elan_instance": True,
    # "customer_elan_name": "customer vrfid",
}

EXIT_DATA2 = {
    "cid": "51.L1XX.008342..CHTR",
    "circ_path_inst_id": "2356781",
    "granite_link": f"{glink}{plink}{instid}",
    "maintenance_window_needed": "No",
    "ip_video_on_cen": "No",
    "ctbh_on_cen": "No",
    "cpe_model_number": "FSP 150-GE114PRO-C",
    # "create_new_elan_instance": True,
    # "customer_elan_name": "customer vrfid",
    "engineering_job_type": "Partial Disconnect",
    "hub_work_required": "No",
    "cpe_installer_needed": "No",
    "message": "Granite, Network, and IP check successful",
}


@pytest.mark.unittest
def test_create_base_exit_criteria():
    assert exit_criteria.create_base_exit_criteria(EXIT_FIELDS) == EXIT_DATA

    EXIT_FIELDS["product_name"] = "Wireless Internet Access"
    with pytest.raises(Exception):
        assert exit_criteria.create_base_exit_criteria(EXIT_FIELDS) is None


@pytest.mark.unittest
def test_create_exit_criteria():
    EXIT_FIELDS["product_name"] = "Fiber Internet Access"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    EXIT_FIELDS["engineering_job_type"] = "full"
    EXIT_FIELDS["hub_work_required"] = "Yes"
    EXIT_FIELDS["cpe_installer_needed"] = "Yes"
    EXIT_DATA2["hub_work_required"] = "Yes"
    EXIT_DATA2["cpe_installer_needed"] = "Yes"
    EXIT_DATA2["engineering_job_type"] = "Full Disconnect"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    EXIT_FIELDS["engineering_job_type"] = "Add"

    with pytest.raises(Exception):
        assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) is None

    EXIT_FIELDS["network"]["passed"] = False

    with pytest.raises(Exception):
        assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) is None

    EXIT_FIELDS["network"]["passed"] = True
    EXIT_FIELDS["blacklist"]["passed"] = False

    with pytest.raises(Exception):
        assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) is None

    # eng_job_type == "express bw upgrade"
    EXIT_FIELDS["engineering_job_type"] = "express bw upgrade"
    EXIT_DATA2["engineering_job_type"] = "Express BW Upgrade"
    EXIT_DATA2["cpe_installer_needed"] = "No"
    EXIT_DATA2["hub_work_required"] = "No"
    EXIT_DATA2["message"] = "Circuit Bandwidth upgraded successfully"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    # eng_job_type == "upgrade"
    EXIT_FIELDS["engineering_job_type"] = "upgrade"
    EXIT_FIELDS["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["engineering_job_type"] = "Upgrade"
    EXIT_DATA2["cpe_installer_needed"] = "Yes"
    EXIT_DATA2["hub_work_required"] = "Yes"
    EXIT_DATA2["maintenance_window_needed"] = "Yes"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    # eng_job_type == "downgrade"
    EXIT_FIELDS["engineering_job_type"] = "downgrade"
    EXIT_FIELDS["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["engineering_job_type"] = "Downgrade"
    EXIT_DATA2["cpe_installer_needed"] = "Yes"
    EXIT_DATA2["hub_work_required"] = "Yes"
    EXIT_DATA2["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["message"] = "Circuit Bandwidth downgraded successfully"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    # eng_job_type == "logical change"
    EXIT_FIELDS["engineering_job_type"] = "logical change"
    EXIT_FIELDS["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["engineering_job_type"] = "Logical Change"
    EXIT_DATA2["cpe_installer_needed"] = "No"
    EXIT_DATA2["hub_work_required"] = "No"
    EXIT_DATA2["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["message"] = "Logical change completed successfully"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    # eng_job_type == "new"
    EXIT_FIELDS["engineering_job_type"] = "new"
    EXIT_FIELDS["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["engineering_job_type"] = "New"
    EXIT_DATA2["cpe_installer_needed"] = "Yes"
    EXIT_DATA2["hub_work_required"] = "Yes"
    EXIT_DATA2["maintenance_window_needed"] = "Yes"
    EXIT_DATA2["message"] = "New Install completed successfully"
    assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) == EXIT_DATA2

    # networkcheck is False
    EXIT_FIELDS["engineering_job_type"] = "full"
    EXIT_FIELDS["network"]["passed"] = False

    with pytest.raises(Exception):
        assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) is None

    # blacklist is False and networkcheck is True
    EXIT_FIELDS["network"]["passed"] = True
    EXIT_FIELDS["blacklist"]["passed"] = False

    with pytest.raises(Exception):
        assert exit_criteria.create_exit_criteria(EXIT_FIELDS, EXIT_DATA) is None
