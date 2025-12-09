import json
import requests

from simple_salesforce import Salesforce

from arda_app.common import auth_config, url_config
from common_sense.common.errors import abort


class SalesforceConnection:
    def __init__(self):
        self.sf = Salesforce(
            instance_url=url_config.SALESFORCE_BASE_URL,
            username=auth_config.SALESFORCE_EMAIL,
            password=auth_config.SALESFORCE_PASS,
            security_token=auth_config.SALESFORCE_TOKEN,
        )
        self.sessionId = self.sf.session_id

    def run_query(self, query):
        resp = self.sf.query_all(query)
        if resp.get("records"):
            return resp["records"]
        return "No records found"

    def get_epr_fields(self, epr, add_fields=None):
        # https://workbench.developerforce.com/describe.php
        # ^ to see all possible EPR fields, choose Engineering__c int the dropdown
        # must have SF login to access

        fields = [
            "Name",
            "Id",
            "Circuit_ID2__c",
            "Product_Family__c",
            "Product_Name_order_info__c",
            "Service_Location_Address__c",
            "SR_Order_Type__c",
            "Engineering_Job_Type__c",
        ]

        if add_fields:
            fields += add_fields

        query = f"""
            SELECT
                {",".join(fields)}
            FROM
                Engineering__c
            WHERE
                Name = '{epr}'
                AND Flagged_for_Deletion__c = false
            """

        return self.run_query(query)

    def find_eprs_by_cid(self, cid):
        query = f"""
            SELECT
                Name
            FROM
                Engineering__c
            WHERE
                Circuit_ID2__c = '{cid}'
                AND Flagged_for_Deletion__c = false
            """

        return self.run_query(query)

    def user_lookup_by_name(self, name):
        query = f"""
            SELECT Id, Email, Title, Charter_PID__c
            FROM User
            WHERE Name = '{name}'
            """
        return self.run_query(query)

    def add_attachment(self, filename: str, file: str, epr_id: str):
        """'epr_id' is the Salesforce ID like 'a2g8Z000009Dmw7'\n
        'filename' like 'excel_filename.xlsx'\n
        'file' needs to be a base64 encoded utf-8 string\n
        Example:
            import os
            import base64
            filepath = os.path.abspath(f"arda_app/data/BOM_templates/{template}.xlsx")
            with open(filepath, "rb") as f:
                file = base64.b64encode(f.read()).decode("utf-8")
        """
        response = requests.post(
            f"{url_config.SALESFORCE_BASE_URL}/services/data/v53.0/sobjects/Attachment/",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.sessionId}"},
            data=json.dumps({"ParentId": epr_id, "Name": filename, "body": file}),
            timeout=300,
        )
        if response.status_code != 200:
            abort(500, "Failed to attach file to Salesforce EPR")
        return response.text
