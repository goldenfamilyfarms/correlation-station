from time import sleep
from dotenv import dotenv_values
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from simple_salesforce import Salesforce

config = dotenv_values("../../prod_06_26_2025.env")

f = Fernet(config["SALESFORCE_PASS_SKELLY"])
config["SALESFORCE_PASS"] = f.decrypt(config["SALESFORCE_PASS"]).decode()
f = Fernet(config["SALESFORCE_TOKEN_SKELLY"])
config["SALESFORCE_TOKEN"] = f.decrypt(config["SALESFORCE_TOKEN"]).decode()


class SalesforceConnection:
    def __init__(self):
        self.sf = Salesforce(
            instance_url=config["SALESFORCE_BASE_URL"],
            username=config["SALESFORCE_EMAIL"],
            password=config["SALESFORCE_PASS"],
            security_token=config["SALESFORCE_TOKEN"],
        )
        self.sessionId = self.sf.session_id

    def run_query(self, query):
        return self.sf.query(query)

    def epr_str(self, epr):
        epr_str = (
            f"{epr['Name']} - {epr['Product_Name_order_info__c']} - "
            f"{epr['SR_Order_Type__c']} - {epr['Engineering_Job_Type__c']}"
        )
        return epr_str


sf = SalesforceConnection()

yesterday = datetime.today() - timedelta(hours=24)
yesterday = yesterday.strftime("%Y-%m-%d")

workstream_date_fields = {
    "CID": "Circuit_ID_Assignment_Complete_Date__c",
    "ISP": "ISP_Install_Ticket_Submitted_Date__c",
    "CD": "Primary_Circuit_Design_Complete_Date__c",
    "ESP": "Circuit_Provisioning_Complete_Date__c",
    "NA": "NOC_Acceptance_Date__c",
    "NC": "Date_Granite_Set_to_Live_Decommissioned__c",
}

workstream_success_fields = {
    "CID": "Completed_CID_Automation__c",
    "ISP": "Completed_ISP_Automation__c",
    "CD": "Completed_CD_Automation__c",
    "ESP": "Completed_NetworkProvisioning_Automation__c",
    "NA": "Completed_Network_Acceptance_Automation__c",
    "NC": "Completed_Network_Compliance_Automation__c",
}

workstream_engineer_fields = {
    "CID": "Circuit_ID_Engineer__r.Name",
    "ISP": "ISP_Install_Ticket_Submitted_By__r.Name",
    "CD": "Circuit_Design_Engineer__r.Name",
    "ESP": "Circuit_Provisioning_Engineer__r.Name",
    "NA": "New_Acceptance_Engineer__r.Name",
    "NC": "CND_STL_Engineer__r.Name",
}

print("\nInitial Counts:\n")
initial = True
initial_totals = {"CID": 0, "ISP": 0, "CD": 0, "ESP": 0, "NA": 0, "NC": 0}
eprs = {"CID": set(), "ISP": set(), "CD": set(), "ESP": set(), "NA": set(), "NC": set()}
run_totals = {"CID": 0, "ISP": 0, "CD": 0, "ESP": 0, "NA": 0, "NC": 0}

while True:
    for workstream in workstream_date_fields:
        query = f"""
            SELECT Id, Name, Product_Name_order_info__c, SR_Order_Type__c, Engineering_Job_Type__c
            FROM Engineering__c
            WHERE {workstream_date_fields[workstream]} > {yesterday}
            AND {workstream_success_fields[workstream]} = true
            AND {workstream_engineer_fields[workstream]} = 'EXPO INTEGRATION (DO NOT CONTACT)'
            AND Flagged_for_Deletion__c = false
            """

        sf_resp = sf.run_query(query)

        # Initial totals at script start
        if initial:
            print(f"{workstream}: {sf_resp['totalSize']}")
            initial_totals[workstream] = sf_resp["totalSize"]
            for epr in sf_resp["records"]:
                eprs[workstream].add(epr["Name"])
        else:
            # Change in counts after every sleep
            change = sf_resp["totalSize"] - initial_totals[workstream] - run_totals[workstream]
            if change >= 0:
                run_totals[workstream] += change
            else:
                # Negative numbers mean an EPR had it's complete date removed
                # Update the initial counts instead of displaying a negative change
                initial_totals[workstream] += change
                change = 0
            print(f"{workstream}: {run_totals[workstream]}  (+{change})")
            if change:
                print(f"""\t{[sf.epr_str(epr) for epr in sf_resp["records"] if epr["Name"] not in eprs[workstream]]}""")
                for epr in sf_resp["records"]:
                    eprs[workstream].add(epr["Name"])

    print("\n--------------\n")
    # Change sleep seconds to wait between refreshing Salesforce counts
    sleep(60)
    if initial:
        print("Running totals and (+change):\n")
    initial = False
