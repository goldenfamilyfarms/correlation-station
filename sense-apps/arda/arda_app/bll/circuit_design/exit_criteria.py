import logging
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def create_base_exit_criteria(exit_fields):
    # input: will be the payload - exit_fields
    # output: dictionary exit_data with base data that is static
    logger.info("Create exit criteria started")

    cid = exit_fields["cid"]
    glink = "https://granite-ise.chartercom.com:2269/web-access/WebAccess.html"
    plink = "#HistoryToken,type=Path,mode=VIEW_MODE,instId="
    instid = exit_fields["circ_path_inst_id"]

    # parse data and return exit_data
    exit_data = {}
    exit_data["cid"] = cid
    exit_data["circ_path_inst_id"] = instid
    exit_data["granite_link"] = f"{glink}{plink}{instid}"
    exit_data["maintenance_window_needed"] = "No"
    exit_data["ip_video_on_cen"] = "No"
    exit_data["ctbh_on_cen"] = "No"
    exit_data["cpe_model_number"] = exit_fields["cpe_model_number"]

    return exit_data


def create_exit_criteria(exit_fields, exit_data):
    # input:
    #  {
    # 'cid': '51.L1XX.008342..CHTR',
    # 'circ_path_inst_id': '2356781',
    # 'granite_link': f"{glink}{plink}{instid}",
    # 'maintenance_window_needed': 'No',
    # 'ip_video_on_cen': 'No',
    # 'ctbh_on_cen': 'No',
    # 'cpe_model_number': 'FSP 150-GE114PRO-C',
    # 'hub_work_required': 'No',
    # 'cpe_installer_needed': 'No',
    #  }
    #
    # output:
    # {
    # "cid": "51.L1XX.008342..CHTR",
    # "circ_path_inst_id": "2356781",
    # "granite_link": f"{glink}{plink}{instid}",
    # "maintenance_window_needed": "No",
    # "ip_video_on_cen": "No",
    # "ctbh_on_cen": "No",
    # "cpe_model_number": "FSP 150-GE114PRO-C",
    # "hub_work_required": "No",
    # "cpe_installer_needed": "No",
    # "engineering_job_type": "Partial Disconnect",
    # "Network check passed?": {networkcheck}",
    # "cosc_blacklist_ticket": "INC000034761521",
    # }
    eng_job_type = exit_fields["engineering_job_type"]

    if eng_job_type in ("partial", "full"):
        networkcheck = exit_fields["network"]["passed"]
        blacklist = exit_fields["blacklist"]["passed"]
        blacklist_IPs = exit_fields["blacklist"]["ips"]

        if not networkcheck:
            logger.error("The network check failed")
            granite = exit_fields["network"]["granite"][0]
            network = exit_fields["network"]["network"][0]

            abort(
                500,
                f"{f'Network check failed: Granite: {granite}, Network: {network} ' if not networkcheck else ''}"
                f"{f'Blacklist check failed: {blacklist_IPs} ' if not blacklist else ''}"
                f"""{f"INC Created: {exit_fields.get('cosc_blacklist_ticket')}" if exit_fields.get("cosc_blacklist_ticket") else ""}""",  # noqa E501
            )

    exit_data["message"] = "Granite, Network, and IP check successful"
    if exit_fields.get("cosc_blacklist_ticket"):
        exit_data["cosc_blacklist_ticket"] = exit_fields["cosc_blacklist_ticket"]
        exit_data["message"] += f". INC Created for Blacklisted IPs: {exit_fields['blacklist']['ips']}"

    if eng_job_type == "partial":
        if exit_fields["product_name"] in [
            "Hosted Voice - (Fiber)",
            "Hosted Voice - (DOCSIS)",
            "Hosted Voice - (Overlay)",
            "PRI Trunk (Fiber)",
            "PRI Trunk (DOCSIS)",
            "PRI Trunk(Fiber) Analog",
            "SIP - Trunk (Fiber)",
            "SIP - Trunk (DOCSIS)",
            "SIP Trunk(Fiber) Analog",
        ]:
            exit_data["hub_work_required"] = "No"
            exit_data["cpe_installer_needed"] = exit_fields["cpe_installer_needed"]
            exit_data["engineering_job_type"] = "Partial Disconnect"
        else:
            exit_data["hub_work_required"] = "No"
            exit_data["cpe_installer_needed"] = exit_fields["cpe_installer_needed"]
            exit_data["engineering_job_type"] = "Partial Disconnect"
    elif eng_job_type == "full":
        exit_data["hub_work_required"] = exit_fields["hub_work_required"]
        exit_data["cpe_installer_needed"] = exit_fields["cpe_installer_needed"]
        exit_data["engineering_job_type"] = "Full Disconnect"
    elif eng_job_type == "express bw upgrade":
        exit_data["hub_work_required"] = "No"
        exit_data["cpe_installer_needed"] = "No"
        exit_data["engineering_job_type"] = "Express BW Upgrade"
        exit_data["message"] = "Circuit Bandwidth upgraded successfully"
    elif eng_job_type == "upgrade":
        exit_data["maintenance_window_needed"] = exit_fields["maintenance_window_needed"]
        exit_data["hub_work_required"] = exit_fields["hub_work_required"]
        exit_data["cpe_installer_needed"] = exit_fields["cpe_installer_needed"]
        exit_data["engineering_job_type"] = "Upgrade"
        exit_data["message"] = "Circuit Bandwidth upgraded successfully"
        # adding circuit design notes to exit criteria dict only if it exist
        if exit_fields.get("circuit_design_notes"):
            exit_data["circuit_design_notes"] = exit_fields["circuit_design_notes"]
    elif eng_job_type == "downgrade":
        exit_data["maintenance_window_needed"] = exit_fields["maintenance_window_needed"]
        exit_data["hub_work_required"] = exit_fields["hub_work_required"]
        exit_data["cpe_installer_needed"] = exit_fields["cpe_installer_needed"]
        exit_data["engineering_job_type"] = "Downgrade"
        exit_data["message"] = "Circuit Bandwidth downgraded successfully"
    elif eng_job_type == "logical change":
        exit_data["hub_work_required"] = "No"
        if exit_fields["product_name"] in [
            "Hosted Voice - (Fiber)",
            "Hosted Voice - (DOCSIS)",
            "Hosted Voice - (Overlay)",
        ]:
            exit_data["cpe_installer_needed"] = "Yes"
        else:
            exit_data["cpe_installer_needed"] = "No"
        exit_data["engineering_job_type"] = "Logical Change"
        exit_data["maintenance_window_needed"] = exit_fields["maintenance_window_needed"]
        exit_data["message"] = "Logical change completed successfully"
    elif eng_job_type == "new":
        exit_data["hub_work_required"] = exit_fields["hub_work_required"]
        exit_data["cpe_installer_needed"] = "Yes"
        exit_data["engineering_job_type"] = "New"
        exit_data["message"] = "New Install completed successfully"
        # adding additional notes to exit criteria dict only if they exist
        if exit_fields.get("maintenance_window_needed"):
            exit_data["maintenance_window_needed"] = exit_fields["maintenance_window_needed"]
        if exit_fields.get("circuit_design_notes"):
            exit_data["circuit_design_notes"] = exit_fields["circuit_design_notes"]
        if exit_fields.get("email_recipients"):
            exit_data["email_recipients"] = exit_fields["email_recipients"]
            exit_data["email_bcc"] = exit_fields["email_bcc"]
            exit_data["email_subject"] = exit_fields["email_subject"]
            exit_data["email_body"] = exit_fields["email_body"]
            exit_data["email_from"] = exit_fields["email_from"]
    else:
        logger.error("The provided engineering job type is not valid")
        abort(500, "The provided engineering job type is not valid")

    logger.info(f"Exit data: {exit_data}")

    return exit_data
