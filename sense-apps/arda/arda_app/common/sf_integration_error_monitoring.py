from time import sleep
from dotenv import dotenv_values
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone
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
        resp = self.sf.query_all(query)
        if resp.get("records"):
            return resp["records"]
        return "No records found"

    def get_epr(self, error):
        query = f"""
            SELECT Id, Name, Product_Name_order_info__c, SR_Order_Type__c, Engineering_Job_Type__c
            FROM Engineering__c
            WHERE Id = '{error["Engineering__c"]}'
            """

        epr_resp = self.run_query(query)

        print(epr_resp[0]["Name"])
        print(epr_resp[0]["Product_Name_order_info__c"])
        print(epr_resp[0]["SR_Order_Type__c"])
        print(epr_resp[0]["Engineering_Job_Type__c"])
        print(error["Error_Message__c"], end="\n\n")


sf = SalesforceConnection()
print("\n", "-" * 100, "\n")

# Change here for number of seconds you want to wait before checking for new errors
sec = 60

while True:
    now = datetime.now(timezone.utc)
    delta = now - timedelta(seconds=sec)

    query = f"""
        SELECT CreatedDate, Error_Message__c, Summary__c, Engineering__c
        FROM Integration_Error__c
        WHERE CreatedDate > {delta.strftime("%Y-%m-%dT%H:%M:%SZ")}
        AND Name = 'Automation Fallout Issue'
        """

    sf_resp = sf.run_query(query)
    if isinstance(sf_resp, list):
        print(f"All workstreams error count in the last {sec} seconds: {len(sf_resp)}", end="\n\n")

        for error in sf_resp:
            # For all errors, not just Arda ones, uncomment this sf.get_epr(error) and comment out the if condition
            # sf.get_epr(error)
            if "CD-" in error["Summary__c"] or "CID:" in error["Summary__c"] or "ISP:" in error["Summary__c"]:
                sf.get_epr(error)
    else:
        print(f"All workstreams error count in the last {sec} seconds: 0", end="\n\n")

    sleep(sec)
    print("-" * 100, "\n")
