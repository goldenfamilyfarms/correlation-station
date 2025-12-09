import logging
import re

from datetime import datetime

from common_sense.common.errors import abort
from arda_app.bll.remedy.remedy_ticket import RemedyTicket

logger = logging.getLogger(__name__)

open_status = ("open", "assigned", "pending", "waiting approval", "planning", "in progress")

bad_status = ("rejected", "cancelled")


def wo_main(body):
    """Main function to compare remedy information and return correct remedy WO info to expo"""
    logger.info(f"Nova to Sova started - {body}")
    prism_id = body["prism_id"]
    related_eprs = body["related_eprs"]

    wo_num, good_eprs = compare_wo(related_eprs)

    if wo_num:
        related_eprs = [x for x in related_eprs if x["engineering_name"] != wo_num["engineering_name"]]
        return update_eprs(wo_num, related_eprs, prism_id)

    wo_info_rem = get_wo_info(good_eprs)
    wo_info = []

    # removing eprs that are rejected or cancelled
    for x in wo_info_rem:
        status = "" if not x["status"] else x["status"]
        if status.lower() not in bad_status:
            wo_info.append(x)

    # check to see if WO is blank test needed
    if len(wo_info) == 1:
        related_eprs = [x for x in related_eprs if x["engineering_name"] != wo_info[0]["engineering_name"]]
        return update_eprs(wo_info[0], related_eprs, prism_id)
    elif len(wo_info) == 0:  # more than one will stay with the original wo_info
        wo_info = good_eprs

    main_epr = compare_date(wo_info)

    # TODO remove below code once tested (submitted date is to the sec)
    if isinstance(main_epr, bool):
        # main_epr = compare_fields(wo_info)

        for epr in related_eprs:
            epr["circuit_design_notes"] = "Unable to determine correct remedy work order due to all dates matching"
            epr["isp_request_issue_flags"] = "Automation: Unsupported Scenario - Investigation Required"

        # set 1st epr as main
        main_epr = good_eprs[0]

    # remove main epr from related_eprs
    related_eprs = [x for x in related_eprs if x["engineering_name"] != main_epr["engineering_name"]]
    return update_eprs(main_epr, related_eprs, prism_id)


def compare_wo(related_eprs):
    """Compare remedy work order numbers from submitted payload
    Input:
      [{"WO": "WO123456789", ...}, {"WO": "WO89672344", ...}, ...]

    Output:
      {
        "engineering_name": "ENG-03806752",
        "WO": "WO0000000000001",
        "submitted_date": "2023-10-01",
        "submitted_by": "0051W000004cV9LQAU",
        "complete_date": "",
        "status": "Open"
      }
        or
      None
    """
    logger.info("Compare epr work orders")
    same_wo = []

    for epr in related_eprs:
        work_order = epr.get("WO", "")
        if work_order:
            same_wo.append(epr)

    if all(x["WO"] == same_wo[0]["WO"] for x in same_wo):
        # Returning first epr since all remedy work orders are matching
        return same_wo[0], None
    return None, same_wo


def compare_date(related_eprs):
    """Compare remedy submitted date from submitted payload
    Input:
      [{"submited_date": "2023-10-01", ...}, {"submited_date": "2023-10-08", ...}, ...]

    Output:
      True
        or
      {
        "engineering_name": "ENG-03806752",
        "WO": "WO0000000000001",
        "submitted_date": "2023-10-01",
        "submitted_by": "0051W000004cV9LQAU",
        "complete_date": "",
        "status": "Open"
      }
    """
    logger.info("Compare epr dates")
    same_date = []

    for epr in related_eprs:
        same_date.append(epr.get("submitted_date", ""))

    date_match = all(x == same_date[0] for x in same_date)

    if date_match:
        # All WO submitted dates are matching. return True
        return date_match

    # find latest date
    if "T" in same_date[0]:
        converted_date = [datetime.strptime(date, "%Y-%m-%dT%H:%M:%S") for date in same_date if date]
        latest_date = max(converted_date).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        converted_date = [datetime.strptime(date, "%Y-%m-%d") for date in same_date if date]
        latest_date = max(converted_date).strftime("%Y-%m-%d")

    for epr in related_eprs:
        if latest_date == epr.get("submitted_date"):
            # Returning epr with the lastest date since the submitted dates are not matching
            return epr


def get_wo_info(related_eprs):
    """Getting remedy work order information on all WO's in submitted payload
    Input:
      [{"WO": "WO123456789", ...}, {"WO": "WO89672344", ...}, ...]

    Output:
      {
        "engineering_name": "ENG-03806752",
        "WO": "WO0000000000001",
        "submitted_date": "2023-10-01",
        "submitted_by": "0051W000004cV9LQAU",
        "complete_date": "",
        "status": "Open",
        "hub_clli": "AUSTXABT,
        "wavelength": "1590",
        "ftp_assignment": "123/456/678",
      }
        or
      abort
    """
    logger.info("Getting work order information")
    rem_wo = []

    # Getting remedy ticket info for each WO in related epr
    for epr in related_eprs:
        if epr.get("WO"):
            resp = get_remedy_wo(epr)

            if resp:
                rem_wo.append(resp)

    if len(rem_wo) > 0:
        return rem_wo

    msg = (
        "is_fallout: Remedy did not respond accordingly, "
        "Unable to get remedy ticket information on all work orders. Please investigate!"
    )

    logging.error(msg)
    abort(500, msg)


def get_remedy_wo(epr):
    """Getting remedy work order information on all WO's in submitted payload
    Input:
      {"WO": "WO123456789", ...}

    Output:
      {
        "engineering_name": "ENG-03806752",
        "WO": "WO0000000000001",
        "submitted_date": "2023-10-01",
        "submitted_by": "0051W000004cV9LQAU",
        "complete_date": "",
        "status": "Open",
        "hub_clli": "AUSTXABT,
        "wavelength": "1590",
        "ftp_assignment": "123/456/678",
      }
        or
      abort
    """
    logger.info(f"Get remedy work orders - {epr}")
    rm = RemedyTicket({})
    content = rm.get_wo_info(epr["WO"])

    if not content:
        return

    # Parse XML response and return Work order info
    wavelength = re.findall(r"<ns0:WO_Target_Wavelength>(\d+\.\d+)", content)
    wo_status = re.findall(r"<ns0:WO_Status>(\w+\s\w+|\w+)", content)
    hub_clli = re.findall(r"<ns0:WO_PE_Device>(.{8})", content)
    complete_date = re.findall(r"<ns0:WO_Completed_Date>(\d+-\d+-\d+T\d+:\d+:\d+-\d+:\d+)", content)
    submit_date = re.findall(r"<ns0:WO_Submit_Date>(\d+-\d+-\d+T\d+:\d+:\d+-\d+:\d+)", content)
    ftp_assign = re.findall(r"<ns0:WO_FTP_Assign_OSP>(.*)</ns0:WO_FTP_Assign_OSP>", content)

    # Adding information into EPR data to compare later
    epr["status"] = wo_status[0] if wo_status else ""
    epr["complete_date"] = complete_date[0] if complete_date else ""

    # Will grab info from get remedy call at later date
    epr["hub_clli"] = hub_clli[0] if hub_clli else ""
    epr["wavelength"] = wavelength[0] if wavelength else ""
    epr["ftp_assignment"] = ftp_assign[0] if ftp_assign else ""
    epr["submitted_date"] = submit_date[0].rsplit("-", 1)[0] if submit_date else ""

    logger.debug(f"WORK ORDER: {epr['WO']}")
    return epr


def compare_fields(wo_info):
    """Comparing remedy fiber information on all WO's that are not rejected or cancelled
    Input:
      [{"WO": "WO123456789", ...}, {"WO": "WO89672344", ...}, ...]

    Output:
      {
        "engineering_name": "ENG-03806752",
        "WO": "WO0000000000001",
        "submitted_date": "2023-10-01",
        "submitted_by": "0051W000004cV9LQAU",
        "complete_date": "",
        "status": "Open",
        "hub_clli": "AUSTXABT,
        "wavelength": "1590",
        "ftp_assignment": "123/456/678",
      }
        or
      None
    """
    """Comparing each fiber assignment information and returning True if matches or False if they do not"""
    logger.info("Compare work order fields")

    ftp_assignment = all(x.get("ftp_assignment") == wo_info[0].get("ftp_assignment") for x in wo_info)
    hub_clli = all(x.get("hub_clli") == wo_info[0].get("hub_clli") for x in wo_info)
    wavelength = all(x.get("wavelength") == wo_info[0].get("wavelength") for x in wo_info)

    fiber_assignment = [ftp_assignment, hub_clli, wavelength]

    # Checking if all fiber assignment information is True
    if all(fiber_assignment):
        return wo_info[0]


def update_eprs(main_epr, related_eprs, prism_id):
    # add notes to the eprs
    logger.info("Adding Notes to eprs")
    logger.info(f"Input payload: {related_eprs}")

    main_status = "" if not main_epr["status"] else main_epr["status"]
    main_epr["status"] = main_status

    for epr in related_eprs:
        epr_wo = epr.get("WO", "")
        epr_status = "" if not epr["status"] else epr["status"]

        # checking for design notes so we do not replace them
        if not epr.get("circuit_design_notes"):
            if main_epr["WO"] != epr_wo and epr_status.lower() in open_status and epr_wo:
                epr["circuit_design_notes"] = (
                    f"{epr_wo} has a status of {epr_status} & was not chosen. Please close out in remedy."
                )

        # adding main epr values to related eprs
        epr["WO"] = main_epr["WO"]
        epr["submitted_date"] = main_epr["submitted_date"]
        epr["submitted_by"] = main_epr["submitted_by"]
        epr["complete_date"] = main_epr["complete_date"]
        epr["status"] = main_status

        # remove extra fields from a related epr
        epr = remove_epr_fields(epr)

    if main_status.lower() in bad_status:
        cdn = f"Main EPR that was chosen has a status of {main_status}. Please investigate"
        issue_flag = "Automation: Unsupported Scenario - Investigation Required"

        main_epr["circuit_design_notes"] = cdn
        main_epr["isp_request_issue_flags"] = issue_flag

        for epr in related_eprs:
            epr["circuit_design_notes"] = cdn
            epr["isp_request_issue_flags"] = issue_flag

    # remove extra fields from main epr
    main_epr = remove_epr_fields(main_epr)
    expo_payload = {"prism_id": prism_id, "main_epr": main_epr, "related_eprs": related_eprs}

    logger.info(f"Output payload: {expo_payload}")
    return expo_payload


def remove_epr_fields(epr):
    # remove extra epr fields
    epr.pop("hub_clli", "")
    epr.pop("wavelength", "")
    epr.pop("ftp_assignment", "")

    return epr
