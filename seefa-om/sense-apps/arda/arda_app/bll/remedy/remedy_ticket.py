import re
import logging

from arda_app.bll.remedy.remedy_utils import (
    get_salesforce_crq_data,
    get_granite_crq_info,
    build_crq_freetext,
    create_date_string,
    create_crq_task_payload,
    create_impact_list_attachment,
    parse_for_wavelength,
    calculate_wo_start_end_dates,
)
from arda_app.dll.remedy import (
    get_workorder_info,
    create_workorder,
    create_crq,
    get_isp_group_cars,
    create_inc,
    # update_crq,
    # rst_remedy_user_lookup_by_email,
)
from arda_app.dll.granite import get_granite
from arda_app.common import auth_config
from common_sense.common.errors import abort


# from arda_app.dll.denodo import get_isp_group

logger = logging.getLogger(__name__)


class RemedyTicket:
    def __init__(self, construction_data):
        self.construction_data = construction_data
        self.port_access_id = ""
        self.hub_clli = ""
        self.pw = auth_config.REMEDY_PASS
        self.un = auth_config.REMEDY_USER
        return

    def calculate_optic_format_and_pe(self, disconnect=False):
        bandwidth, name, port_access_id, self.hub_clli = self.get_path_elements()

        # Disconnect tickets don't require all the info regular Remedy tickets need
        if not disconnect:
            fiber_distance = float(self.construction_data["fiber_distance"].split("k")[0])
            if fiber_distance < 80:
                optic_format = "&lt; 80km"
            elif fiber_distance <= 120:
                optic_format = "80-120km"
            else:
                optic_format = ">120km"

            if bandwidth == "1 Gbps":
                optic_format = "1G " + optic_format + " SFP"
            elif bandwidth == "10 Gbps":
                optic_format = "10G " + optic_format + " SFP+"
            logger.debug(f"OPTIC FORMAT: {optic_format}")
        else:
            fiber_distance = ""
            optic_format = ""

        self.construction_data["equipment_id"] = name
        json_string_router = (
            '{"portFree": true,"portDetails": [{"portFree": true,"portDetails":'
            ' {"name":"ge-0/0/84","apply-groups": "DISABLEIF"}}]}'
        )
        json_string_switch = (
            '{"portFree":true,"portDetails":[{"portFree":true,"portDetails":'
            '{"name":"ge-0/0/84","apply-groups":"DISABLEIF"}},{"portFree":true,'
            '"portDetails":{"name":"xe-0/0/84","apply-groups":"DISABLEIF"}}]}'
        )
        if name[10:12] == "CW":
            self.construction_data["pe_device_port_status"] = json_string_router.replace('"ge-0/0/84"', port_access_id)
        else:
            for r in (("ge-0/0/84", port_access_id), ("xe-0/0/84", port_access_id.replace("GE", "XE"))):
                json_string_switch = json_string_switch.replace(*r)
            self.construction_data["pe_device_port_status"] = json_string_switch
            self.port_access_id = port_access_id

        if "+" in optic_format:
            notes_optic_format = "10G SFP+"
        else:
            notes_optic_format = "1G SFP"

        return optic_format, notes_optic_format

    def get_path_elements(self):
        granite_url = f"/pathElements?CIRC_PATH_HUM_ID={self.construction_data['circuit_id']}&LVL=2"
        try:
            granite_resp = get_granite(granite_url)
            circuit = granite_resp[0]
            logger.debug(f"GRANITE_PATH_ELEMENTS_RESPONSE: {circuit}")
            element_bandwidth = circuit["ELEMENT_BANDWIDTH"]
            logger.debug(f"BANDWIDTH: {element_bandwidth}")
            element_name = circuit["ELEMENT_NAME"]
            logger.debug(f"NAME: {element_name}")
            port_access_id = circuit["PORT_ACCESS_ID"]
            logger.debug(f"PORT ACCESS ID: {port_access_id}")
            hub_clli = circuit["A_CLLI"]
            logger.debug(f"HUB CLLI: {hub_clli}")
            self.construction_data["a_site_name"] = circuit["PATH_A_SITE"]
            return element_bandwidth, element_name, port_access_id, hub_clli
        except (IndexError, KeyError):
            abort(404, f"Circuit id: {self.construction_data['circuit_id']} did not have Path Elements in Granite")

    def clean_payload(self):
        char_to_replace = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
        self.construction_data["address"] = self.construction_data["address"].translate(str.maketrans(char_to_replace))
        self.construction_data["customer_name"] = self.construction_data["customer_name"].translate(
            str.maketrans(char_to_replace)
        )
        try:
            self.construction_data["fiber_assigned"] = self.construction_data["fiber_assigned"].translate(
                str.maketrans(char_to_replace)
            )
        except (KeyError, AttributeError):
            pass

        try:
            self.construction_data["terminating_ftp_port"] = self.construction_data["terminating_ftp_port"].translate(
                str.maketrans(char_to_replace)
            )
        except KeyError:
            pass

    def create_workorder(self):
        self.clean_payload()
        optic_format, notes_optic_format = self.calculate_optic_format_and_pe()
        remedy_isp_groups = get_isp_group_cars(self.hub_clli)
        support_group = remedy_isp_groups["isp_group"]
        site = remedy_isp_groups["common_name"]
        region = remedy_isp_groups["region"]
        site_group = remedy_isp_groups["site_group"]
        address = f"{remedy_isp_groups['address']} {remedy_isp_groups['city']} {remedy_isp_groups['state']}"
        notes = (
            f"{self.construction_data['address']} :: New Single Customer Activation :: "
            f"{self.construction_data['circuit_id']} :: {self.construction_data['customer_name']} :: "
            f"{self.construction_data['equipment_id'].split('/')[0]}: {notes_optic_format} {self.port_access_id}: "
            f"{self.construction_data['terminating_ftp_port']}: {self.construction_data['wavelength']} \n"
            f"Additional Details: Fibers Assigned: {self.construction_data['fiber_assigned']}"
        )

        details = (
            "This ticket was generated by the SEEFA Remedy Ticket Automation System. To request assistance, "
            "please email: DL-SEE&amp;O-SESE-1Remedy-automation@charter.com"
        )
        a_site_name = self.construction_data["a_site_name"]
        a_site_name = a_site_name[:65] if len(a_site_name) > 65 else a_site_name
        # summary = f'{self.construction_data["a_site_name"]} :: New Single Customer Activation'
        summary = f"{a_site_name} ::New Single Customer Activation"
        pe_device_port_status = """Port Details:
                                Port Status: Admin Down/Down
                                Interface Description: {No Description on Interface}
                                Ok to remove fiber"""

        # priority_class check to add RAPID BUILD to notes and summary
        # if fall-out, please check a_site_name length and change from 65 to 55
        if self.construction_data.get("priority_class") == "Rapid Build":
            notes = f"RAPID BUILD {notes}"
            summary = f"RAPID BLD {summary}"
            # check 100 char limit
            if len(summary) > 100:
                abort(500, f"Summary exceeds 100 character limit: {summary}")

        start_date, end_date = calculate_wo_start_end_dates()

        soapenv_url = "http://schemas.xmlsoap.org/soap/envelope/"

        # replacing special char & to and to prevent issues with remedy
        site = str(site).replace("&", "and")
        summary = summary.replace("&", "and")

        xml_body = f"""<soapenv:Envelope xmlns:soapenv="{soapenv_url}" xmlns:urn="urn:CreateWorkOrder">
                            <soapenv:Header>
                                <urn:AuthenticationInfo>
                                    <urn:userName>{self.un}</urn:userName>
                                    <urn:password>{self.pw}</urn:password>
                                </urn:AuthenticationInfo>
                            </soapenv:Header>
                            <soapenv:Body>
                                <urn:CreateWorkOrder>
                                    <urn:Submitter>svc_seefa_remedyautomation</urn:Submitter>
                                     <urn:Status>Assigned</urn:Status>
                                     <urn:Short_Description>Field Ops Fiber Support ISP - WOT</urn:Short_Description>
                                     <urn:Site_Group>{site_group}</urn:Site_Group>
                                     <urn:Region>{region}</urn:Region>
                                     <urn:Site>{site}</urn:Site>
                                     <urn:WO_Type_Field_01>
                                        {"Yes" if self.construction_data["construction_complete"] is True else "No"}
                                     </urn:WO_Type_Field_01>
                                     <urn:WO_Type_Field_02>{pe_device_port_status}</urn:WO_Type_Field_02>
                                     <urn:WO_Type_Field_04>{optic_format}</urn:WO_Type_Field_04>
                                     <urn:WO_Type_Field_05>{self.construction_data["address"]}</urn:WO_Type_Field_05>
                                     <urn:WO_Type_Field_06>{start_date}</urn:WO_Type_Field_06>
                                     <urn:WO_Type_Field_07>{end_date}</urn:WO_Type_Field_07>
                                     <urn:Template_Name>Field Ops Fiber Support ISP - WOT</urn:Template_Name>
                                     <urn:z1D_WorklogDetails>SEE&amp;O Remedy Ticket Automation</urn:z1D_WorklogDetails>
                                     <urn:CustomerFullName>Spectrum Enterprise Automation</urn:CustomerFullName>
                                     <urn:z1D_Details>{details}</urn:z1D_Details>
                                     <urn:Secure_Work_Log>No</urn:Secure_Work_Log>
                                     <urn:TemplateID>IDGAA5V0GWMRHAPFWG4WPEZKNCNCKS</urn:TemplateID>
                                     <urn:RequesterLoginID>svc_seefa_remedyautomation</urn:RequesterLoginID>
                                     <urn:WO_Type_Field_10>{self.construction_data["circuit_id"]}</urn:WO_Type_Field_10>
                                     <urn:WO_Type_Field_11>{self.construction_data["customer_name"]}</urn:WO_Type_Field_11>
                                     <urn:WO_Type_Field_12>{self.construction_data["equipment_id"]}</urn:WO_Type_Field_12>
                                     <urn:WO_Type_Field_13>{self.port_access_id}</urn:WO_Type_Field_13>
                                     <urn:WO_Type_Field_14>{self.construction_data["terminating_ftp_port"]}</urn:WO_Type_Field_14>
                                     <urn:WO_Type_Field_15>{self.construction_data["wavelength"]}</urn:WO_Type_Field_15>
                                     <urn:WO_Type_Field_16>{self.construction_data["fiber_distance"]}</urn:WO_Type_Field_16>
                                     <urn:WO_Type_Field_17>{self.construction_data["sheath"]}</urn:WO_Type_Field_17>
                                     <urn:WO_Type_Field_18>{self.construction_data["prism_id"]}</urn:WO_Type_Field_18>
                                     <urn:WO_Type_Field_20>{self.construction_data["order_number"]}</urn:WO_Type_Field_20>
                                     <urn:DatasetId>0</urn:DatasetId>
                                     <urn:ReconciliationIdentity>0</urn:ReconciliationIdentity>
                                     <urn:Summary>{summary}</urn:Summary>
                                     <urn:Location_Company>Charter Internal</urn:Location_Company>
                                     <urn:Manager_Support_Organization>ISP</urn:Manager_Support_Organization>
                                     <urn:Manager_Support_Group_Name>{support_group}</urn:Manager_Support_Group_Name>
                                     <urn:Last_Name>Automation</urn:Last_Name>
                                     <urn:First_Name>Spec Ent</urn:First_Name>
                                     <urn:Chg_Location_Address>{address}</urn:Chg_Location_Address>
                                     <urn:Internet_E-mail>SEE&amp;O_SESE_1Remedy_automation@charter.com</urn:Internet_E-mail>
                                     <urn:Categorization_Tier_1>Add</urn:Categorization_Tier_1>
                                     <urn:Categorization_Tier_2>Single Customer</urn:Categorization_Tier_2>
                                     <urn:Categorization_Tier_3>A Loc</urn:Categorization_Tier_3>
                                     <urn:z1D_Action>CREATE</urn:z1D_Action>
                                     <urn:Company>Charter Internal</urn:Company>
                                     <urn:Add_Request_For_>Individual</urn:Add_Request_For_>
                                     <urn:Detailed_Description>{notes}</urn:Detailed_Description>
                                     <urn:Request_Manager_Company>Charter Internal</urn:Request_Manager_Company>
                                     <urn:Requestor_ID></urn:Requestor_ID>
                                     <urn:Scheduled_Start_Date>{start_date}</urn:Scheduled_Start_Date>
                                     <urn:Scheduled_End_Date>{end_date}</urn:Scheduled_End_Date>
                                     <urn:Product_Cat_Tier_1_2_>Spectrum Enterprise</urn:Product_Cat_Tier_1_2_>
                                     <urn:Product_Cat_Tier_2__2_>Fiber Service</urn:Product_Cat_Tier_2__2_>
                                     <urn:Product_Cat_Tier_3__2_>DIA/FIA</urn:Product_Cat_Tier_3__2_>
                                     <urn:Support_Organization>ISP</urn:Support_Organization>
                                     <urn:Support_Company>Charter Internal</urn:Support_Company>
                                     <urn:Support_Group_Name>{support_group}</urn:Support_Group_Name>
                                     <urn:Customer_First_Name>Spec Ent</urn:Customer_First_Name>
                                     <urn:Customer_Last_Name>Automation</urn:Customer_Last_Name>
                                     <urn:Customer_Company>Charter Internal</urn:Customer_Company>
                                     <urn:Customer_Internet_E-mail>SEE&amp;O_SESE_1Remedy_automation@charter.com</urn:Customer_Internet_E-mail>
                                     <urn:FormKeyword>SERVICE_REQUEST_INTERFACE</urn:FormKeyword>
                                     <urn:Source_Keyword>Interface Form</urn:Source_Keyword>
                                     <urn:OfferingTitle>.</urn:OfferingTitle>
                                     <urn:Entitlement_Qual>1=0</urn:Entitlement_Qual>
                                     <urn:SRD_TurnaroundTimeX>0</urn:SRD_TurnaroundTimeX>
                                     <urn:RequestQuantity>1</urn:RequestQuantity>
                                </urn:CreateWorkOrder>
                            </soapenv:Body>
                        </soapenv:Envelope>"""

        logger.info(f"xml to remedy for circuit {self.construction_data.get('circuit_id')} {xml_body}")
        response = create_workorder(xml_body)

        # Parse XML response and return WOID
        work_order = re.findall(r"<ns0:WOID>(\w+)</ns0:WOID>", str(response.content))
        if len(work_order) == 1:
            logger.debug(f"WORK ORDER: {work_order[0]}")
            return {"work_order": work_order[0]}
        else:
            if "faultstring" in str(response.content):
                fault = re.findall(r"<faultstring>(.*)</faultstring>", str(response.content))
                if len(fault) > 0:
                    logger.debug(f"REMEDY ERROR: {fault[0]}")
                    abort(500, f"Unexpected Remedy error. Work order was not created because: {fault[0]}")
            logger.debug(f"REMEDY ERROR: {response.content}")
            abort(500, "Unexpected Remedy error. Work order was not created.")

    def create_disconnect_workorder(self):
        self.clean_payload()
        hub_clli = self.construction_data["hub_clli"]
        equipment_id = self.construction_data["equipment_id"]
        port_access_id = self.construction_data["port_access_id"]
        remedy_isp_groups = get_isp_group_cars(hub_clli)
        support_group = remedy_isp_groups["isp_group"]
        site = remedy_isp_groups["common_name"]
        region = remedy_isp_groups["region"]
        site_group = remedy_isp_groups["site_group"]
        address = f"{remedy_isp_groups['address']} {remedy_isp_groups['city']} {remedy_isp_groups['state']}"
        notes = self.construction_data["notes"]
        if self.construction_data.get("additional_details"):
            notes += f"Additional Details: {self.construction_data['additional_details']}"
        summary = self.construction_data["summary"]
        details = (
            "This ticket was generated by the SEEFA Remedy Ticket Automation System. To request assistance, "
            "please email: DL-SEE&amp;O-SESE-1Remedy-automation@charter.com"
        )
        pe_device_port_status = """Port Details:
                                Port Status: Admin Down/Down
                                Interface Description: {No Description on Interface}
                                Ok to remove fiber"""

        start_date, end_date = calculate_wo_start_end_dates()

        soapenv_url = "http://schemas.xmlsoap.org/soap/envelope/"
        xml_body = f"""<soapenv:Envelope xmlns:soapenv="{soapenv_url}" xmlns:urn="urn:CreateWorkOrder">
                            <soapenv:Header>
                                <urn:AuthenticationInfo>
                                    <urn:userName>{self.un}</urn:userName>
                                    <urn:password>{self.pw}</urn:password>
                                </urn:AuthenticationInfo>
                            </soapenv:Header>
                            <soapenv:Body>
                                <urn:CreateWorkOrder>
                                    <urn:Submitter>svc_seefa_remedyautomation</urn:Submitter>
                                     <urn:Status>Assigned</urn:Status>
                                     <urn:Short_Description>Field Ops Fiber Support ISP - WOT</urn:Short_Description>
                                     <urn:Site_Group>{site_group}</urn:Site_Group>
                                     <urn:Region>{region}</urn:Region>
                                     <urn:Site>{site}</urn:Site>
                                     <urn:WO_Type_Field_01>{
            "Yes" if self.construction_data.get("construction_complete", "").title() == "True" else "No"
        }
                                     </urn:WO_Type_Field_01>
                                     <urn:WO_Type_Field_02>{pe_device_port_status}</urn:WO_Type_Field_02>
                                     <urn:WO_Type_Field_05>{self.construction_data["address"]}</urn:WO_Type_Field_05>
                                     <urn:WO_Type_Field_06>{start_date}</urn:WO_Type_Field_06>
                                     <urn:WO_Type_Field_07>{end_date}</urn:WO_Type_Field_07>
                                     <urn:Template_Name>Field Ops Fiber Support ISP - WOT</urn:Template_Name>
                                     <urn:z1D_WorklogDetails>SEE&amp;O Remedy Ticket Automation</urn:z1D_WorklogDetails>
                                     <urn:CustomerFullName>Spectrum Enterprise Automation</urn:CustomerFullName>
                                     <urn:z1D_Details>{details}</urn:z1D_Details>
                                     <urn:Secure_Work_Log>No</urn:Secure_Work_Log>
                                     <urn:TemplateID>IDGAA5V0GWMRHAPFWG4WPEZKNCNCKS</urn:TemplateID>
                                     <urn:RequesterLoginID>svc_seefa_remedyautomation</urn:RequesterLoginID>
                                     <urn:WO_Type_Field_10>{
            self.construction_data.get("circuit_id")
        }</urn:WO_Type_Field_10>
                                     <urn:WO_Type_Field_11>{
            self.construction_data.get("customer_name")
        }</urn:WO_Type_Field_11>
                                     <urn:WO_Type_Field_12>{equipment_id}</urn:WO_Type_Field_12>
                                     <urn:WO_Type_Field_13>{port_access_id}</urn:WO_Type_Field_13>
                                     <urn:WO_Type_Field_14></urn:WO_Type_Field_14>
                                     <urn:WO_Type_Field_15>{
            self.construction_data.get("wavelength", "")
        }</urn:WO_Type_Field_15>
                                     <urn:WO_Type_Field_16>{
            self.construction_data.get("fiber_distance", "")
        }</urn:WO_Type_Field_16>
                                     <urn:WO_Type_Field_17>{
            self.construction_data.get("sheath", "")
        }</urn:WO_Type_Field_17>
                                     <urn:WO_Type_Field_18>{
            self.construction_data.get("prism_id", "")
        }</urn:WO_Type_Field_18>
                                     <urn:WO_Type_Field_20>{
            self.construction_data.get("order_number")
        }</urn:WO_Type_Field_20>
                                     <urn:DatasetId>0</urn:DatasetId>
                                     <urn:ReconciliationIdentity>0</urn:ReconciliationIdentity>
                                     <urn:Summary>{summary}</urn:Summary>
                                     <urn:Location_Company>Charter Internal</urn:Location_Company>
                                     <urn:Manager_Support_Organization>ISP</urn:Manager_Support_Organization>
                                     <urn:Manager_Support_Group_Name>{support_group}</urn:Manager_Support_Group_Name>
                                     <urn:Last_Name>Automation</urn:Last_Name>
                                     <urn:First_Name>Spec Ent</urn:First_Name>
                                     <urn:Chg_Location_Address>{address}</urn:Chg_Location_Address>
                                     <urn:Internet_E-mail>SEE&amp;O_SESE_1Remedy_automation@charter.com</urn:Internet_E-mail>
                                     <urn:Categorization_Tier_1>Remove</urn:Categorization_Tier_1>
                                     <urn:Categorization_Tier_2>Single Customer</urn:Categorization_Tier_2>
                                     <urn:Categorization_Tier_3>A Loc</urn:Categorization_Tier_3>
                                     <urn:z1D_Action>CREATE</urn:z1D_Action>
                                     <urn:Company>Charter Internal</urn:Company>
                                     <urn:Add_Request_For_>Individual</urn:Add_Request_For_>
                                     <urn:Detailed_Description>{notes}</urn:Detailed_Description>
                                     <urn:Request_Manager_Company>Charter Internal</urn:Request_Manager_Company>
                                     <urn:Requestor_ID></urn:Requestor_ID>
                                     <urn:Scheduled_Start_Date>{start_date}</urn:Scheduled_Start_Date>
                                     <urn:Scheduled_End_Date>{end_date}</urn:Scheduled_End_Date>
                                     <urn:Product_Cat_Tier_1_2_>Spectrum Enterprise</urn:Product_Cat_Tier_1_2_>
                                     <urn:Product_Cat_Tier_2__2_>Fiber Service</urn:Product_Cat_Tier_2__2_>
                                     <urn:Product_Cat_Tier_3__2_>DIA/FIA</urn:Product_Cat_Tier_3__2_>
                                     <urn:Support_Organization>ISP</urn:Support_Organization>
                                     <urn:Support_Company>Charter Internal</urn:Support_Company>
                                     <urn:Support_Group_Name>{support_group}</urn:Support_Group_Name>
                                     <urn:Customer_First_Name>Spec Ent</urn:Customer_First_Name>
                                     <urn:Customer_Last_Name>Automation</urn:Customer_Last_Name>
                                     <urn:Customer_Company>Charter Internal</urn:Customer_Company>
                                     <urn:Customer_Internet_E-mail>SEE&amp;O_SESE_1Remedy_automation@charter.com</urn:Customer_Internet_E-mail>
                                     <urn:FormKeyword>SERVICE_REQUEST_INTERFACE</urn:FormKeyword>
                                     <urn:Source_Keyword>Interface Form</urn:Source_Keyword>
                                     <urn:OfferingTitle>.</urn:OfferingTitle>
                                     <urn:Entitlement_Qual>1=0</urn:Entitlement_Qual>
                                     <urn:SRD_TurnaroundTimeX>0</urn:SRD_TurnaroundTimeX>
                                     <urn:RequestQuantity>1</urn:RequestQuantity>
                                </urn:CreateWorkOrder>
                            </soapenv:Body>
                        </soapenv:Envelope>"""

        logger.info(f"xml to remedy for circuit {self.construction_data.get('circuit_id')} {xml_body}")
        response = create_workorder(xml_body)

        # Parse XML response and return WOID
        work_order = re.findall(r"<ns0:WOID>(\w+)</ns0:WOID>", str(response.content))
        if len(work_order) == 1:
            logger.debug(f"WORK ORDER: {work_order[0]}")
            return {"work_order": work_order[0]}
        else:
            logger.debug(f"REMEDY ERROR: {response.content}")
            abort(500, "Unexpected Remedy error. Work order was not created.")

    def get_wo_info(self, workorder):
        """GET existing WO info"""
        soapenv_url = "http://schemas.xmlsoap.org/soap/envelope/"

        pw, un = auth_config.REMEDY_PASS, auth_config.REMEDY_USER

        xml_body = f"""<soapenv:Envelope xmlns:soapenv="{soapenv_url}">
                        <soapenv:Header>
                            <AuthenticationInfo>
                            <userName>{un}</userName>
                            <password>{pw}</password>
                            </AuthenticationInfo>
                        </soapenv:Header>
                        <soapenv:Body>
                            <WorkOrder_GetInfo>
                            <WO_ID>{workorder}</WO_ID>
                            </WorkOrder_GetInfo>
                        </soapenv:Body>
                        </soapenv:Envelope>"""

        response = get_workorder_info(xml_body)

        if response.status_code != 200:
            logger.error(f"Work order {workorder} not found in Remedy")
            return

        return str(response.content)

    def create_crq_ticket(self, payload):
        """Main function for v2/remedy_ticket/create_crq"""

        resp_contacts = ""
        if payload["coordinator_group"] == "SEEI&O":
            group_name = "SEEI&amp;O"
        elif payload["coordinator_group"] == "Coordinated Impact Provisioning":
            group_name = payload["coordinator_group"]
            # CIP Managers: Estella, Lance, David, Steve
            resp_contacts = """<urn:AddResponsibleContacts>
                <urn:UserID>P2142171</urn:UserID>
                <urn:Relationship_Type>Contact</urn:Relationship_Type>
                <urn:Action>CREATE</urn:Action>
            </urn:AddResponsibleContacts>
            <urn:AddResponsibleContacts>
                <urn:UserID>P2151800</urn:UserID>
                <urn:Relationship_Type>Contact</urn:Relationship_Type>
                <urn:Action>CREATE</urn:Action>
            </urn:AddResponsibleContacts>
            <urn:AddResponsibleContacts>
                <urn:UserID>P2749885</urn:UserID>
                <urn:Relationship_Type>Contact</urn:Relationship_Type>
                <urn:Action>CREATE</urn:Action>
            </urn:AddResponsibleContacts>
            <urn:AddResponsibleContacts>
                <urn:UserID>P2148033</urn:UserID>
                <urn:Relationship_Type>Contact</urn:Relationship_Type>
                <urn:Action>CREATE</urn:Action>
            </urn:AddResponsibleContacts>"""
        else:
            abort(500, f"Invalid Change Coordinator Group: {payload['coordinator_group']}")

        template_str = ""
        if payload["template"] == "Verizon 1G to 10G":
            hub_impacting = True
            template_name = "VzW Upg Proj CHG24_001| In Flight Only | Hub Imp=Y | SITE CLLI"
            template_id = "IDGAA5V0GPIXLASIIQ0QSHIF1300IU"
            template_str = f"<urn:Template_InstanceID>{template_id}</urn:Template_InstanceID>"
        elif payload["template"] == "Routine 1G to 10G":
            hub_impacting = True
            template_name = None
            template_id = None
        else:
            abort(500, f"Unsupported template provided in payload: {payload['template']}")

        sf_resp, mw_pm_email = get_salesforce_crq_data(payload["epr"])
        # mw_pm = rst_remedy_user_lookup_by_email(mw_pm_email) if mw_pm_email else ""
        # PM email/PID was for the "Responsible Contact" in the CRQ, but not every PM has a Remedy account
        # so it was breaking the payload when their PID was not found. Leaving variable for possible future use.

        if not payload.get("cid"):
            payload["cid"] = sf_resp.get("Circuit_ID2__c")
        address = sf_resp.get("Service_Location_Address__c")

        try:
            wave = parse_for_wavelength(sf_resp)
        except Exception:
            wave = ""
        finally:
            if not wave:
                wave = "WAVE_NOT_FOUND"

        start_date = sf_resp.get("Maintenance_Window_Scheduled_For__c")
        if not start_date:
            abort(500, f"No maintenance window date in {payload['epr']}")

        start_datetime, end_datetime, downtime_minutes = create_date_string(
            start_date, payload["start_time"], payload["end_time"]
        )

        sf_order_type = sf_resp.get("SR_Order_Type__c")

        (
            hub_clli,
            customer,
            current_hub_port,
            new_hub_port,
            current_hub_device_tid,
            new_hub_device_tid,
            impact_list,
            dual_cpe_uplink,
            current_wave,
        ) = get_granite_crq_info(payload["cid"], sf_order_type)

        # Update wavelength with network value (only Junipers)
        if current_wave:
            wave = current_wave

        impact_attachment = ""
        if impact_list:
            b64_impact = create_impact_list_attachment(
                impact_list, customer, f"{current_hub_device_tid} {current_hub_port}", wave
            )
            if b64_impact:
                impact_attachment = f"""<urn:Work_Info_Type>Service Impact Assessment</urn:Work_Info_Type>
                                <urn:Work_Info_Summary>IMPACT</urn:Work_Info_Summary>
                                <urn:Work_Info_Notes>IMPACT</urn:Work_Info_Notes>
                                <urn:Work_Info_Locked>No</urn:Work_Info_Locked>
                                <urn:Work_Info_View_Access>Internal</urn:Work_Info_View_Access>
                                <urn:Attachment1Name>IMPACT.xlsx</urn:Attachment1Name>
                                <urn:Attachment1Data>{b64_impact}</urn:Attachment1Data>"""

        isp_info = get_isp_group_cars(hub_clli)
        isp_manager = ""  # Will be built out when manager info is added to the data lake

        freetext_values = {
            "cid": payload["cid"],
            "clli": hub_clli,
            "epr": payload["epr"],
            "address": address,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "timezone": payload["timezone"],
            "wave": wave,
            "current_device": current_hub_device_tid,
            "current_port": current_hub_port,
            "new_device": new_hub_device_tid,
            "new_port": new_hub_port,
            "customer": customer,
            "impacted_cids": impact_list,
            "hub_impacting": hub_impacting,
            "dual_cpe_uplink": dual_cpe_uplink,
        }

        summary, notes = build_crq_freetext(freetext_values)

        payload["isp_group"] = isp_info["isp_group"]
        payload["notes"] = notes
        payload["summary"] = summary
        payload["isp_manager"] = isp_manager

        xml_body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:urn="urn:CHG_ChangeInterface_Create_WS_v2_2">
            <soapenv:Header>
                <urn:AuthenticationInfo>
                    <urn:userName>{self.un}</urn:userName>
                    <urn:password>{self.pw}</urn:password>
                </urn:AuthenticationInfo>
            </soapenv:Header>
            <soapenv:Body>
                <urn:Change_Submit_Service>
                    <urn:Submitter>svc_seefa_remedyautomation</urn:Submitter>
                    <urn:Chg_Assignee_Support_Company>Charter Internal</urn:Chg_Assignee_Support_Company>
                    <urn:Chg_Assignee_Support_Organization>SPECTRUM ENTERPRISE</urn:Chg_Assignee_Support_Organization>
                    <urn:Chg_Assignee_Support_Group>{group_name}</urn:Chg_Assignee_Support_Group>
                    <urn:Change_Coordinator>Spec Ent Automation</urn:Change_Coordinator>
                    <urn:ASLOGID>svc_seefa_remedyautomation</urn:ASLOGID>
                    {template_str if template_str else ""}
                    <urn:Summary>{template_name if template_name else summary}</urn:Summary>
                    <urn:Notes>{notes}</urn:Notes>
                    <urn:Region>{isp_info["region"]}</urn:Region>
                    <urn:Site_Group>{isp_info["site_group"]}</urn:Site_Group>
                    <urn:Site>{isp_info["common_name"]}</urn:Site>
                    <urn:Class>Normal</urn:Class>
                    <urn:Impact>4-Minor/Localized</urn:Impact>
                    <urn:First_Name>Spec Ent</urn:First_Name>
                    <urn:Last_Name>Automation</urn:Last_Name>
                    <urn:Urgency>4-Low</urn:Urgency>
                    <urn:Risk_Level>Risk Level 1</urn:Risk_Level>
                    <urn:Status>Draft</urn:Status>
                    <urn:Company>Charter Internal</urn:Company>
                    <urn:Categorization_Tier_1>Change</urn:Categorization_Tier_1>
                    <urn:OTF_Project_POR>N/A</urn:OTF_Project_POR>
                    <urn:ServiceCI>Spectrumbusiness.net</urn:ServiceCI>
                    <urn:Change_Type>Change</urn:Change_Type>
                    <urn:Product_Cat_Tier_1>Spectrum Enterprise</urn:Product_Cat_Tier_1>
                    <urn:Product_Cat_Tier_2>Interface Config (active)</urn:Product_Cat_Tier_2>
                    <urn:Product_Cat_Tier_3>Add/Modify/Remove</urn:Product_Cat_Tier_3>
                    <urn:Scheduled_Start_Date>{start_datetime}</urn:Scheduled_Start_Date>
                    <urn:Scheduled_End_Date>{end_datetime}</urn:Scheduled_End_Date>
                    <urn:Location_Company>Charter Internal</urn:Location_Company>
                    <urn:Chg_Manager_Support_Company>Charter Internal</urn:Chg_Manager_Support_Company>
                    <urn:Chg_Manager_Support_Organization>Org1</urn:Chg_Manager_Support_Organization>
                    <urn:Chg_Manager_Suuport_Group>Change Management Priv</urn:Chg_Manager_Suuport_Group>
                    <urn:Action>CREATE</urn:Action>
                    <urn:Priority>Low</urn:Priority>
                    <urn:Service_Impact>Yes</urn:Service_Impact>
                    <urn:Downtime>{downtime_minutes}</urn:Downtime>
                    <urn:LBI_Actual>{len(impact_list)}</urn:LBI_Actual>
                    <urn:LBI_Potential>0</urn:LBI_Potential>
                    <urn:Charter_Internal_Service_Impact>None</urn:Charter_Internal_Service_Impact>
                    <urn:Metro_none>none</urn:Metro_none>
                    <urn:Backbone_none>none</urn:Backbone_none>
                    <urn:AddRelationship>
                        <urn:Action>ADDCHGASSOCIATION</urn:Action>
                    </urn:AddRelationship>
                    {resp_contacts if resp_contacts else ""}
                    {impact_attachment if impact_attachment else ""}
                    {self.add_crq_tasks(payload, hub_impacting, group_name, payload["template"])}
                </urn:Change_Submit_Service>
            </soapenv:Body>
        </soapenv:Envelope>"""

        response = create_crq(xml_body)

        # Parse XML response and return CRQ ID
        crq = re.findall(r"<ns0:Infrastructure_Change_ID>(\w+)</ns0:Infrastructure_Change_ID>", str(response.content))
        if isinstance(crq, list) and len(crq) > 0:
            crq_id = crq[0]
        else:
            if "faultstring" in str(response.content):
                fault = re.findall(r"<faultstring>(.*)</faultstring>", str(response.content))
                if len(fault) > 0:
                    logger.debug(f"REMEDY ERROR: {fault[0]}")
                    abort(500, f"Unexpected Remedy error. CRQ was not created because: {fault[0]}")
            logger.debug(f"REMEDY ERROR: {response.content}")
            abort(500, "Unexpected Remedy error. CRQ was not created.")

        isp_note = f"\n\nPlease assign Engineer in ISP task associated with: {crq_id}"

        return {
            "crq_id": crq_id,
            "clli": hub_clli,
            "summary": summary.replace("&amp;", "&"),
            "description": f"{notes.replace('&amp;', '&')}{isp_note}",
            "scope_of_work": f"Brief scope of work {notes.split('Brief scope of work')[-1]}{isp_note}",
            "date": start_date,
        }

    def add_crq_tasks(self, payload, hub_impacting, coordinator_group, template):
        """Add task(s) to CRQ"""
        values = {
            "summary": payload["summary"],
            "notes": payload["notes"],
            "isp_group": payload["isp_group"],
            "assigned_to": payload["isp_manager"],
            "coordinator_group": coordinator_group,
        }
        summary = payload["summary"]

        if hub_impacting:
            # Task templates are not currently functional through the Remedy SOAP payload (or the Remedy REST service)
            # Leaving for possible future use
            # values["template_name"] = "Supporting Task to engage ISP for SEEI&O work"
            # values["template_id"] = "TMGAA5V0GYNU1AQSPCP9QRQ3JW9I7G"
            values["summary"] = f"Vertical Support Task to engage ISP | {values['summary']}"
        else:
            values["template_name"] = "ad hoc"
            values["template_id"] = ""

        # ISP Task
        xml_body = create_crq_task_payload("ISP", values)
        # INO Task
        if template == "Routine 1G to 10G":
            values["summary"] = summary
            xml_body += create_crq_task_payload("INO", values)

        return xml_body

    def create_blacklist_inc(self, data):
        """Create Remedy INC ticket for Disconnect blacklisted IPs"""
        summary = f"IP Blacklist {data['epr']} | {data['cid']}"

        blacklisted_ips_str = ""
        for ip in data["blacklisted_reason"]:
            blacklisted_ips_str += (
                f"{list(ip.keys())[0]}\n{list(ip.values())[0]}\n"
                f"https://mxtoolbox.com/SuperTool.aspx?action=blacklist%3a{list(ip.keys())[0]}&amp;run=toolpage\n\n"
            )

        # notes string formatted for end-result in Remedy
        notes = f"""The following IP(s) were identified during the disconnect process as blacklisted.

{data["ip_block"]}

{blacklisted_ips_str}
"""

        xml_body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:urn="urn:WS_Charter_Incident_Interface_Stage">
            <soapenv:Header>
                <urn:AuthenticationInfo>
                    <urn:userName>{self.un}</urn:userName>
                    <urn:password>{self.pw}</urn:password>
                </urn:AuthenticationInfo>
            </soapenv:Header>
            <soapenv:Body>
                <urn:Create_Incident z1D_Action="CREATE" WSDL_Operation="Create_Incident">
                <urn:First_Name>Resolve</urn:First_Name>
                <urn:Last_Name>API</urn:Last_Name>
                <urn:Severity>Low</urn:Severity>
                <urn:Condition>Information</urn:Condition>
                <urn:Reported_Source>Alarms</urn:Reported_Source>
                <urn:Assigned_Group>CBO-CSOC</urn:Assigned_Group>
                <urn:Categorization_Tier_1>Applications</urn:Categorization_Tier_1>
                <urn:Summary>{summary}</urn:Summary>
                <urn:Notes>{notes}</urn:Notes>
                </urn:Create_Incident>
            </soapenv:Body>
            </soapenv:Envelope>"""

        response = create_inc(xml_body)

        # Parse XML response and return INC
        inc = re.findall(r"<ns0:Incident_Number>(\w+)</ns0:Incident_Number>", str(response.content))
        if isinstance(inc, list) and len(inc) > 0:
            return inc[0]
        else:
            if "faultstring" in str(response.content):
                fault = re.findall(r"<faultstring>(.*)</faultstring>", str(response.content))
                if len(fault) > 0:
                    logger.debug(f"REMEDY ERROR: {fault[0]}")
                    abort(500, f"Unexpected Remedy error. INC was not created because: {fault[0]}")
            logger.debug(f"REMEDY ERROR: {response.content}")
            abort(500, "Unexpected Remedy error. INC was not created.")
