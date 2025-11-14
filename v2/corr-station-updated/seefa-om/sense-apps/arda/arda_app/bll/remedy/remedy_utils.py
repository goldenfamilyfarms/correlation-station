# Flake8: noqa: E501

import io
import base64
import logging
import pandas as pd

from datetime import datetime, timedelta

from arda_app.dll.salesforce import SalesforceConnection
from arda_app.dll.granite import get_path_elements, get_transport_channels, get_granite
from arda_app.dll.mdso import onboard_and_exe_cmd
from arda_app.common.cd_utils import granite_paths_get_url
from common_sense.common.errors import abort

# from arda_app.dll.denodo import get_isp_group

logger = logging.getLogger(__name__)


def get_salesforce_crq_data(epr):
    crq_fields = [
        "Maintenance_Window_Needed__c",
        "Maintenance_Window_Project_Manager__r.Name",
        "Maintenance_Window_Scheduled_For__c",
        "Maintenance_Window_Ticket__c",
        "Hub_Work_Required__c",
        "Primary_CNO_Provisioning_Team__c",
        "Circuit_Provisioning_Complete_Date__c",
        "Circuit_Provisioning_Engineer__r.Name",
        "CPR_Needed__c",
        "Is_this_an_Approved_Expedite__c",
        "CWDM_Wavelength__c",
        "Project_Manager__c",
        "PRISM_Id__c",
        "Cross_Provider_NNI__c",
        "Circuit_Design_Notes__c",
    ]
    sf = SalesforceConnection()
    sf_resp = sf.get_epr_fields(epr, add_fields=crq_fields)

    if isinstance(sf_resp, str) and sf_resp == "No records found":
        abort(500, f"No EPR found with {epr}")
    else:
        sf_resp = sf_resp[0]

    mw_pm = (
        sf_resp.get("Maintenance_Window_Project_Manager__r").get("Name")
        if sf_resp.get("Maintenance_Window_Project_Manager__r")
        and sf_resp.get("Maintenance_Window_Project_Manager__r").get("Name")
        else sf_resp.get("Project_Manager__c", "")
    )
    if "-" in mw_pm:
        mw_pm = mw_pm.split("-")[0].strip()
    mw_pm_email = sf.user_lookup_by_name(mw_pm)
    if isinstance(mw_pm_email, list) and mw_pm_email[0].get("Email"):
        mw_pm_email = mw_pm_email[0]["Email"]
    else:
        mw_pm_email = ""

    return sf_resp, mw_pm_email


def parse_for_wavelength(sf_resp):
    wave = ""
    if sf_resp.get("CWDM_Wavelength__c"):
        wave = sf_resp.get("CWDM_Wavelength__c")
    if not wave and (
        "EXISTING:" in sf_resp.get("Circuit_Design_Notes__c").upper()
        and "DESIGNED:" in sf_resp.get("Circuit_Design_Notes__c").upper()
    ):
        wave = sf_resp.get("Circuit_Design_Notes__c").upper().split("DESIGNED:")[0].split()[-1].lower()
    if not wave and sf_resp.get("Cross_Provider_NNI__c"):
        if "WL:" in sf_resp.get("Cross_Provider_NNI__c", "").upper():
            wave = sf_resp["Cross_Provider_NNI__c"].upper().split("WL:")[1]
            if "," in wave:
                wave = wave.split(",")[0]
            else:
                wave = wave.split()[0]
        elif "NM" in sf_resp.get("Cross_Provider_NNI__c", "").upper():
            wave = sf_resp["Cross_Provider_NNI__c"].upper().split("NM")[0].strip()
    if not wave[:4].isnumeric():
        wave = ""
    else:
        if "nm" not in wave:
            wave += "nm"
    return wave


def get_sf_user_email(user_full_name):
    sf = SalesforceConnection()
    resp = sf.user_lookup_by_name(user_full_name)
    return resp["Email"]


def get_granite_crq_info(cid, sf_order_type):
    """Parse Granite data and return tuple of variables used in CRQ payload"""
    cid_paths = get_granite(granite_paths_get_url(cid))
    live_path_inst_id = ""
    designed_path_inst_id = ""
    a_site_name = ""
    z_site_name = ""
    if isinstance(cid_paths, dict) and cid_paths.get("retString"):
        abort(500, f"No paths found for CID: {cid}")
    elif isinstance(cid_paths, list) and len(cid_paths) != 2 and sf_order_type != "New Install":
        abort(500, "Circuit needs both Live and Designed paths")
    else:
        for path in cid_paths:
            if path.get("status") == "Live":
                live_path_inst_id = path["pathInstanceId"]
            if path.get("status") == "Designed":
                designed_path_inst_id = path["pathInstanceId"]

    if sf_order_type != "New Install":
        live_path_elements = get_path_elements(cid, url_params=f"&INITIAL_CIRCUIT_ID={live_path_inst_id}")
        designed_path_elements = get_path_elements(cid, url_params=f"&INITIAL_CIRCUIT_ID={designed_path_inst_id}")
        if isinstance(live_path_elements, dict) or isinstance(designed_path_elements, dict):
            abort(500, "Circuit needs both Live and Designed paths")
        z_site_name = live_path_elements[0]["PATH_Z_SITE"]
        cid_path_elements = live_path_elements + designed_path_elements
    else:
        designed_path_elements = get_path_elements(cid, url_params=f"&INITIAL_CIRCUIT_ID={designed_path_inst_id}")
        if isinstance(designed_path_elements, dict):
            abort(500, "New Install orders require Designed circuit path in Granite")
        z_site_name = designed_path_elements[0]["PATH_Z_SITE"]
        cid_path_elements = designed_path_elements

    # Store EPL topology A-side values for later comparison so A-side hub elements can be passed over
    a_side_cllis = set()
    if cid_path_elements[0]["SERVICE_TYPE"] in [
        "CAR-EPL",
        "COM-EPL",
        "CAR-EVPL",
        "COM-EVPL",
        "CAR-E-ACCESS FIBER/FIBER EPL",
    ]:
        for elem in cid_path_elements:
            if elem["ELEMENT_CATEGORY"] == "SE MPLS CORE":
                a_site_name = cid_path_elements[0]["A_SITE_NAME"]
                a_side_cllis = list(a_side_cllis)
                break
            a_side_cllis.add(elem["A_CLLI"])

    customer = cid_path_elements[0]["CUSTOMER_NAME"].replace("&", "&amp;")

    transports = set()
    hub_clli = ""
    current_transport_to_cpe = ""
    current_hub_device_tid = ""
    current_hub_port = ""
    current_hub_device_model = ""
    current_hub_device_vendor = ""
    sec_current_hub_device_vendor = ""
    new_hub_device_tid = ""
    new_hub_port = ""
    new_hub_device_model = ""
    dual_cpe_uplink = False
    path_chan_vlans = []
    sec_current_hub_port = ""
    sec_current_hub_device_tid = ""
    sec_new_hub_port = ""
    sec_new_hub_device_tid = ""
    sec_new_hub_device_model = ""
    primary_vlan = ""
    sec_vlan = ""
    for elem in cid_path_elements:
        # Find hub to CPE transport paths and extract values into a set of tuples
        if valid_transport_to_cpe_path_element(elem, a_site_name, a_side_cllis):
            hub_clli, transports = extract_transport_element_values(elem, hub_clli, transports)

    transports = list(transports)
    if len(transports) == 0:
        abort(500, f"Unable to find any hub to CPE transport paths in Live or Designed revisions of {cid}")
    elif len(transports) == 1:
        transports = list(transports)
        current_transport_to_cpe = transports[0][0]
        if sf_order_type == "New Install":
            # New install CID with only a Designed path
            # Additional logic to get current hub info from existing impacted CID
            designed_channels = get_transport_channels(current_transport_to_cpe)
            impacted_cid = ""
            impacted_transports = set()
            a_side_cllis = []
            if isinstance(designed_channels, list):
                for channel in designed_channels:
                    if channel.get("MEMBER_PATH"):
                        impacted_cid = channel["MEMBER_PATH"]
            if impacted_cid:
                impacted_cid_path_elements = get_path_elements(impacted_cid)
                if isinstance(impacted_cid_path_elements, list):
                    for elem in impacted_cid_path_elements:
                        if valid_transport_to_cpe_path_element(elem, None, a_side_cllis):
                            # PATH_Z_SITE of a hub to CPE transport path should match the Z side of the primary CID
                            # regardless of whether the hub is on the A or Z side of the impacted CID
                            if elem["PATH_Z_SITE"] == z_site_name:
                                hub_clli, impacted_transports = extract_transport_element_values(
                                    elem, hub_clli, impacted_transports
                                )
                impacted_transports = list(impacted_transports)
                if (len(impacted_transports) == 1 and impacted_transports[0][3] == transports[0][3]) or (
                    len(impacted_transports) == 2 and impacted_transports[0][3] == impacted_transports[1][3]
                ):
                    # Same hub device as in EPR CID Designed path
                    (
                        new_hub_device_tid,
                        current_hub_device_tid,
                        current_hub_device_vendor,
                        new_hub_device_model,
                        current_hub_device_model,
                        new_hub_port,
                        current_hub_port,
                    ) = assign_single_hub_device_values(impacted_transports)
                else:
                    # Impacted CID has different hub device
                    for trans in impacted_transports:
                        if trans[1] == "Live":
                            transports.append(trans)
                            break

                    for trans in transports:
                        if trans[1] in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]:
                            new_hub_device_tid = trans[3]
                            new_hub_device_model = trans[5]
                            new_hub_port = trans[-1]
                        else:
                            current_transport_to_cpe = trans[0]
                            current_hub_device_tid = trans[3]
                            current_hub_device_vendor = trans[4]
                            current_hub_device_model = trans[5]
                            current_hub_port = trans[-1]
            else:
                (
                    new_hub_device_tid,
                    current_hub_device_tid,
                    current_hub_device_vendor,
                    new_hub_device_model,
                    current_hub_device_model,
                    new_hub_port,
                    current_hub_port,
                ) = assign_single_hub_device_values(transports)
        else:
            (
                new_hub_device_tid,
                current_hub_device_tid,
                current_hub_device_vendor,
                new_hub_device_model,
                current_hub_device_model,
                new_hub_port,
                current_hub_port,
            ) = assign_single_hub_device_values(transports)
    elif len(transports) == 2:
        if (
            "QFX" in transports[0][5]
            and transports[0][3] == transports[1][3]  # TID
            and transports[0][1] == transports[1][1]  # Status
            and transports[0][1] in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]
        ):
            # Dual uplink to same hub QFX with both ports being changed from GE to XE
            dual_cpe_uplink = True
            for trans in transports:
                path_chan_vlans.append(get_transport_channels(trans[0])[0])

            current_hub_device_vendor = sec_current_hub_device_vendor = "JUNIPER"
            current_hub_port = new_hub_port = transports[0][-1]
            sec_current_hub_port = sec_new_hub_port = transports[1][-1]

            # All same QFX TID
            current_hub_device_tid = transports[0][3]
            sec_current_hub_device_tid = new_hub_device_tid = sec_new_hub_device_tid = current_hub_device_tid

            current_hub_port, new_hub_port = qfx_port_check("QFX", current_hub_port, new_hub_port)

            sec_current_hub_port, sec_new_hub_port = qfx_port_check("QFX", sec_current_hub_port, sec_new_hub_port)

            # Tuples to be unpacked for CRQ notes
            current_hub_port = (current_hub_port, sec_current_hub_port)
            current_hub_device_tid = (current_hub_device_tid, sec_current_hub_device_tid)
            new_hub_port = (new_hub_port, sec_new_hub_port)
            new_hub_device_tid = (new_hub_device_tid, sec_new_hub_device_tid)
        else:
            for trans in transports:
                if trans[1] in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]:
                    new_hub_device_tid = trans[3]
                    new_hub_device_model = trans[5]
                    new_hub_port = trans[-1]
                else:
                    current_transport_to_cpe = trans[0]
                    current_hub_device_tid = trans[3]
                    current_hub_device_vendor = trans[4]
                    # current_hub_device_model = trans[5]
                    current_hub_port = trans[-1]
            if not current_transport_to_cpe:
                abort(500, f"Unable to process topology with transports: {transports}")
    elif len(transports) == 4:
        # Dual CPE uplink to single hub topology with primary and secondary paths
        dual_cpe_uplink = True

        for trans in transports:
            path_chan_vlans.append(get_transport_channels(trans[0])[0])
        for trans in transports:
            if trans[1] in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]:
                if not new_hub_device_model:
                    for path in path_chan_vlans:
                        if path["PATH_NAME"] == trans[0]:
                            primary_vlan = path["VLAN_NBR"]
                            new_hub_device_tid = trans[3]
                            new_hub_device_model = trans[5]
                            new_hub_port = trans[-1]
                            break
                else:
                    for path in path_chan_vlans:
                        if path["PATH_NAME"] == trans[0]:
                            sec_vlan = path["VLAN_NBR"]
                            sec_new_hub_device_tid = trans[3]
                            sec_new_hub_device_model = trans[5]
                            sec_new_hub_port = trans[-1]
                            break
        for trans in transports:
            if trans[1] not in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]:
                for path in path_chan_vlans:
                    if path["PATH_NAME"] == trans[0] and path["VLAN_NBR"] == primary_vlan:
                        current_transport_to_cpe = trans[0]
                        current_hub_device_tid = trans[3]
                        current_hub_device_vendor = trans[4]
                        # current_hub_device_model = trans[5]
                        current_hub_port = trans[-1]
                        break
                    elif path["PATH_NAME"] == trans[0] and path["VLAN_NBR"] == sec_vlan:
                        sec_current_hub_device_tid = trans[3]
                        sec_current_hub_device_vendor = trans[4]
                        # sec_current_hub_device_model = trans[5]
                        sec_current_hub_port = trans[-1]
                        break

        current_hub_port, new_hub_port = qfx_port_check(new_hub_device_model, current_hub_port, new_hub_port)

        sec_current_hub_port, sec_new_hub_port = qfx_port_check(
            sec_new_hub_device_model, sec_current_hub_port, sec_new_hub_port
        )

        # Tuples to be unpacked for CRQ notes
        current_hub_port = (current_hub_port, sec_current_hub_port)
        current_hub_device_tid = (current_hub_device_tid, sec_current_hub_device_tid)
        new_hub_port = (new_hub_port, sec_new_hub_port)
        new_hub_device_tid = (new_hub_device_tid, sec_new_hub_device_tid)
    else:
        abort(500, "Unexpected number of Hub to CPE transports found")

    if not dual_cpe_uplink:
        current_hub_port, new_hub_port = qfx_port_check(new_hub_device_model, current_hub_port, new_hub_port)

    # Check network for current wavelength on Juniper hub devices
    current_wave = ""
    sec_current_wave = ""
    if current_hub_device_vendor == "JUNIPER":
        current_wave = juniper_network_optic_check(
            current_hub_device_tid if not dual_cpe_uplink else current_hub_device_tid[0],
            current_hub_port if not dual_cpe_uplink else current_hub_port[0],
        )
        if dual_cpe_uplink and sec_current_hub_device_vendor == "JUNIPER":
            sec_current_wave = juniper_network_optic_check(current_hub_device_tid[1], current_hub_port[1])
    if dual_cpe_uplink:
        if not current_wave:
            current_wave = "WAVE_NOT_FOUND"
        if not sec_current_wave:
            sec_current_wave = "WAVE_NOT_FOUND"
        current_wave = (
            f"{current_wave}{'nm' if 'NOT' not in current_wave else ''}",
            f"{sec_current_wave}{'nm' if 'NOT' not in sec_current_wave else ''}",
        )
    elif current_wave:
        current_wave = current_wave + "nm"

    # Create impact list
    impact_list = set()
    transport_channels = (
        get_transport_channels(current_transport_to_cpe)
        if not path_chan_vlans
        else [
            path
            for path in path_chan_vlans
            if path["PATH_STATUS"] not in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]
        ]
    )
    if len(transport_channels) > 0:
        for chan in transport_channels:
            if chan.get("MEMBER_PATH"):
                # Only MEMBER_PATH CIDs for Live circuits.
                # NEXT_PATH are Designed CIDs not provisioned yet, so not impacted.
                impact_list.add(chan["MEMBER_PATH"])

    return (
        hub_clli,
        customer,
        current_hub_port,
        new_hub_port,
        current_hub_device_tid,
        new_hub_device_tid,
        impact_list,
        dual_cpe_uplink,
        current_wave,
    )


def valid_transport_to_cpe_path_element(element, a_site_name, a_side_cllis):
    if (
        element["PATH_A_SITE_TYPE"] in ["HUB", "HEAD END", "MDC"]
        and element["PATH_Z_SITE_TYPE"] != "MSC"
        and element["ELEMENT_BANDWIDTH"] not in ["WAVELENGTH", "OPTICAL"]
        and element["ELEMENT_CATEGORY"] != "ONS"
        and element["PATH_Z_SITE"] != a_site_name
        and element["A_CLLI"] not in a_side_cllis
    ) and (
        element["SERVICE_TYPE"] == "INT-ACCESS TO PREM TRANSPORT"  # to CPE
        or (element["SERVICE_TYPE"] == "INT-EDGE TRANSPORT" and element["PATH_Z_SITE_TYPE"] == "ACTIVE MTU")  # to MTU
    ):
        return True


def extract_transport_element_values(element, hub_clli, transports):
    if hub_clli and hub_clli != element["A_CLLI"]:
        if element["PATH_Z_SITE_TYPE"] != "ACTIVE MTU":
            abort(
                500,
                f"Hub migration or dual uplink CPE to different hubs detected. Hub CLLIs found: {hub_clli} and {element['A_CLLI']}",
            )
    hub_clli = element["A_CLLI"]
    if element["A_SITE_NAME"] == element["PATH_A_SITE"]:
        transports.add(
            (
                element["PATH_NAME"],
                element["PATH_STATUS"],
                element["CIRC_PATH_INST_ID"],
                element["TID"],
                element["VENDOR"],
                element["MODEL"],
                element["PORT_ACCESS_ID"],
            )
        )
    return hub_clli, transports


def assign_single_hub_device_values(transports):
    new_hub_device_tid = new_hub_device_model = new_hub_port = ""
    current_hub_device_tid = current_hub_device_vendor = current_hub_device_model = current_hub_port = ""
    if "QFX" in transports[0][5] or "ACX" in transports[0][5]:
        new_hub_device_tid = current_hub_device_tid = transports[0][3]
        current_hub_device_vendor = transports[0][4]
        new_hub_device_model = current_hub_device_model = transports[0][5]
        new_hub_port = current_hub_port = transports[0][-1]
    else:
        if transports[0][1] in ["Designed", "Planned", "Auto-Designed", "Auto-Planned"]:
            new_hub_device_tid = transports[0][3]
            new_hub_device_model = transports[0][5]
            new_hub_port = transports[0][-1]
            if len(transports) == 2 and transports[1][1] == "Live":
                current_hub_device_tid = transports[1][3]
                current_hub_device_vendor = transports[1][4]
                current_hub_device_model = transports[1][5]
                current_hub_port = transports[1][-1]
        else:
            current_hub_device_tid = transports[0][3]
            current_hub_device_vendor = transports[0][4]
            current_hub_device_model = transports[0][5]
            current_hub_port = transports[0][-1]
    return (
        new_hub_device_tid,
        current_hub_device_tid,
        current_hub_device_vendor,
        new_hub_device_model,
        current_hub_device_model,
        new_hub_port,
        current_hub_port,
    )


def qfx_port_check(new_hub_device_model, current_hub_port, new_hub_port):
    if "QFX" in new_hub_device_model:
        if "GE" not in current_hub_port and "XE" in new_hub_port:
            current_hub_port = current_hub_port.replace("XE", "GE")
        elif "GE" in current_hub_port and "GE" in new_hub_port:
            new_hub_port = new_hub_port.replace("GE", "XE")
    return current_hub_port, new_hub_port


def juniper_network_optic_check(hostname, granite_port):
    try:
        mdso_response = onboard_and_exe_cmd(hostname, "show_chassis", granite_port, attempt_onboarding=True)
        pic_detail = mdso_response["result"]["fpc-information"]["fpc"]["pic-detail"]
        ports = pic_detail["port-information"]["port"]
    except (KeyError, IndexError):
        return

    port_number = granite_port.split("/")[2]
    if isinstance(ports, list):
        for optic in ports:
            if optic["port-number"] == port_number:
                return optic["wavelength"].split()[0]
    elif isinstance(ports, dict):
        if ports["port-number"] == port_number:
            return ports["wavelength"].split()[0]


def create_impact_list_attachment(impact_list, customer, hub_tid_port, wave):
    """Create base64 encoded UTF-8 string of an xlsx file"""
    df_dict = {
        "Circuit ID Impacted": [cid for cid in impact_list],
        "Customer Impacted": [customer] * len(impact_list),
        "Port Customer Resides On": [hub_tid_port] * len(impact_list),
        "Wavelength Customer Is Using": [wave] * len(impact_list),
    }
    df = pd.DataFrame(df_dict)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="impact", index=False)
    worksheet = writer.sheets["impact"]
    # Auto-format column width
    for idx, col in enumerate(df):
        series = df[col]
        max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 1
        worksheet.set_column(idx, idx, max_len)
    writer.close()
    b64_string = base64.b64encode(output.getvalue()).decode()
    return b64_string


def build_crq_freetext(values):
    start = datetime.fromisoformat(values["start_datetime"])
    end = datetime.fromisoformat(values["end_datetime"])
    impacted_cids = ""
    for cid in values["impacted_cids"]:
        impacted_cids += f"{cid}\n"

    # The CRQ summary field has a 100 character limit
    # Only 24 characters allowed for the customer name
    summary = f"Customer coordinated/approved RGI | {values['clli']}:Port Migration: {values['customer'][:24]} - {values['epr']}"

    # Below string formatting is for the resulting look in Remedy
    notes = f"""
Maintenance Window for {start.strftime("%m/%d/%y")} @ {start.strftime("%I:%M %p")} - {end.strftime("%I:%M %p")} {values["timezone"]}

{summary}
{values["address"]}

{"Yes - Hub Impacted - Inflight Customer Only" if values["hub_impacting"] else "No"}
New/Upgraded Customer
{values["cid"]}

Affected Customers
{impacted_cids}

CHANGE REASON:  PROJECT DEADLINE

Brief scope of work
ISP to provide:
Optics: {values["wave"]}
fiber jumpers
"""

    if values["dual_cpe_uplink"]:
        notes += f"""Dual CPE Uplink:
Move From {values["current_device"][0]} Port {values["current_port"][0]} --To-- {values["new_device"][0]} Port {values["new_port"][0]} {values["wave"][0]}
Move From {values["current_device"][1]} Port {values["current_port"][1]} --To-- {values["new_device"][1]} Port {values["new_port"][1]} {values["wave"][1]}"""
    else:
        notes += f"Move From {values['current_device']} Port {values['current_port']} --To-- {values['new_device']} Port {values['new_port']} {values['wave']}"
    return summary, notes


def create_date_string(start_date, start_time, end_time):
    """Convert to ISO format for SOAP payload
    ex. 2023-08-15T04:00:00.00"""
    start = f"{start_date} {start_time}"
    end = f"{start_date} {end_time}"
    start = datetime.strptime(start, "%Y-%m-%d %I:%M %p")
    end = datetime.strptime(end, "%Y-%m-%d %I:%M %p")
    downtime_minutes = abs((end - start).total_seconds())
    downtime_minutes = round(downtime_minutes / 60)
    return start.isoformat(), end.isoformat(), downtime_minutes


def create_crq_task_payload(task_type, values):
    if task_type == "INO":
        task_name = "INO Task"
        assignee_org = "SPECTRUM ENTERPRISE"
        assignee_group = values["coordinator_group"]
        assigned_to = values["assigned_to"]
        values["notes"] = ""
    elif task_type == "ISP":
        task_name = "Vertical Support Task to engage ISP for SEEI&amp;O work"
        assignee_org = "ISP"
        assignee_group = values["isp_group"]
        assigned_to = values["assigned_to"]
    else:
        abort(500, f"Unsupported task type: {task_type}")

    payload = f"""<urn:AddTask>
                    <urn:Action>ADDCHANGETASK</urn:Action>
                    <urn:Submitter>svc_seefa_remedyautomation</urn:Submitter>
                    <urn:LocationCompany>Charter Internal</urn:LocationCompany>
                    <urn:TaskName>{task_name}</urn:TaskName>
                    <urn:TaskSummary>{values["summary"]}</urn:TaskSummary>
                    <urn:TaskNotes>{values["notes"]}</urn:TaskNotes>
                    <urn:Company>Charter Internal</urn:Company>
                    <urn:First_Name>Spec Ent</urn:First_Name>
                    <urn:Last_Name>Automation</urn:Last_Name>
                    <urn:Support_Company>Charter Internal</urn:Support_Company>
                    <urn:Support_Organization>SPECTRUM ENTERPRISE</urn:Support_Organization>
                    <urn:Support_Group_Name>{values["coordinator_group"]}</urn:Support_Group_Name>
                    <urn:Customer_Company>Charter Internal</urn:Customer_Company>
                    <urn:Customer_First_Name>Spec Ent</urn:Customer_First_Name>
                    <urn:Customer_Last_Name>Automation</urn:Customer_Last_Name>
                    <urn:Assignee_Organization>{assignee_org}</urn:Assignee_Organization>
                    <urn:Assignee_Group>{assignee_group}</urn:Assignee_Group>
                    <urn:Assignee_Login_ID>{assigned_to}</urn:Assignee_Login_ID>
                    <urn:Notify_Assignee>Yes</urn:Notify_Assignee>
                    <urn:ProductCategorizationTier1>Headend/Hub Facilities</urn:ProductCategorizationTier1>
                    <urn:ProductCategorizationTier2>Physical</urn:ProductCategorizationTier2>
                    <urn:ProductCategorizationTier3>Fiber</urn:ProductCategorizationTier3>
                    <urn:OperationalCategorizationTier1>Change</urn:OperationalCategorizationTier1>
                </urn:AddTask>"""
    return payload


def calculate_wo_start_end_dates():
    """Determine start and end dates for ISP WO SLO\n
    Responds with a tuple of ISO formatted date strings\n
    :return: ("2025-07-31T00:01:00", "2025-08-04T23:59:00")"""
    slo = 3  # default 3 day SLO
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Set start date for 12:01am of next business day
    current_date = datetime.now()
    start_date = current_date.replace(hour=0, minute=1, second=0, microsecond=0)
    match days[start_date.weekday()]:
        case "Friday":
            start_date = start_date + timedelta(days=3)
        case "Saturday":
            start_date = start_date + timedelta(days=2)
        case _:
            start_date = start_date + timedelta(days=1)

    # Set end date to 3 for standard SLO
    end_date = start_date + timedelta(days=3)

    # Add two days to SLO to allow for weekends
    if days[start_date.weekday()] in ["Thursday", "Friday"]:
        end_date = end_date + timedelta(days=2)
        slo += 2

    # Add 1 day to SLO if there is a holiday
    holiday_year = 2025
    holiday_list = [
        datetime(holiday_year, 1, 1),  # Jan 1st - New Years
        datetime(holiday_year, 1, 20),  # Jan 20th - MLK
        datetime(holiday_year, 5, 26),  # May 26th - Memorial Day
        datetime(holiday_year, 7, 4),  # July 4th - Independence Day
        datetime(holiday_year, 9, 1),  # Sept 1st - Labor Day
        datetime(holiday_year, 12, 25),  # Dec 25th - Christmas
    ]

    for x in range(slo + 1):
        date_check = datetime(start_date.year, start_date.month, start_date.day) + timedelta(days=x)
        if date_check in holiday_list:
            # Move the start date if it lands on a holiday
            if start_date.replace(minute=0) == date_check:
                start_date = start_date + timedelta(days=1)
                # Account for this putting the start date on Sat for Fri Holidays
                if days[start_date.weekday()] == "Saturday":
                    start_date = start_date + timedelta(days=2)
            end_date = end_date + timedelta(days=1)

    # Set end date to 11:59pm of the final SLO day
    end_date = end_date - timedelta(minutes=2)
    print(days[start_date.weekday()])
    print(days[end_date.weekday()])

    return start_date.isoformat(timespec="seconds"), end_date.isoformat(timespec="seconds")
