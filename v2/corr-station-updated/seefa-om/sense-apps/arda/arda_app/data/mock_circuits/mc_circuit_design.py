from typing import Union


def test_case_responses(payload: dict) -> Union[dict, None]:
    """Test cases for regression testing."""
    if payload.get("z_side_info") and payload["z_side_info"].get("cid") == "51.L1XX.partial_pass..CHTR":
        return {
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
    elif payload.get("z_side_info") and payload["z_side_info"].get("cid") == "20.L1XX.001748..TWCC":
        return {
            "circ_path_inst_id": "2480215",
            "maintenance_window_needed": "No",
            "hub_work_required": "No",
            "cpe_installer_needed": "No",
            "ip_video_on_cen": "No",
            "ctbh_on_cen": "No",
            "engineering_job_type": "Logical Change",
            "cpe_model_number": "114PRO",
            "message": "",
        }
    elif payload.get("z_side_info") and payload["z_side_info"].get("cid") == "20.L1XX.001747..TWCC":
        return {
            "circ_path_inst_id": "2480215",
            "maintenance_window_needed": "No",
            "hub_work_required": "No",
            "cpe_installer_needed": "No",
            "ip_video_on_cen": "No",
            "ctbh_on_cen": "No",
            "engineering_job_type": "Upgrade",
            "cpe_model_number": "114PRO",
            "message": "",
        }
    elif payload.get("z_side_info") and payload["z_side_info"].get("cid") == "20.L1XX.CD_PASS_UPS_FAIL..TWCC":
        # v1/circuit_design pass , v1/update_path_status fail
        return {
            "circ_path_inst_id": "2480215",
            "maintenance_window_needed": "No",
            "hub_work_required": "No",
            "cpe_installer_needed": "No",
            "ip_video_on_cen": "No",
            "ctbh_on_cen": "No",
            "engineering_job_type": "Upgrade",
            "cpe_model_number": "114PRO",
            "message": "",
        }
    elif payload.get("z_side_info") and payload["z_side_info"].get("cid") == "20.L1XX.DOWNGRADE_PASS..TWCC":
        return {
            "circ_path_inst_id": "2480215",
            "maintenance_window_needed": "No",
            "hub_work_required": "No",
            "cpe_installer_needed": "No",
            "ip_video_on_cen": "No",
            "ctbh_on_cen": "No",
            "engineering_job_type": "Downgrade",
            "message": "",
        }
