import palantir_app
from common_sense.common.errors import abort
from simple_salesforce import Salesforce
from palantir_app.common.salesforce import service_to_codes


MNE_WHITELIST = ["Managed Network Switch", "Managed Network Edge", "Managed Network Camera", "Managed Network WiFi"]


class SalesforceConnection:
    def __init__(self):
        self.sf = Salesforce(
            instance_url=palantir_app.url_config.SALESFORCE_BASE_URL,
            username=palantir_app.auth_config.SALESFORCE_EMAIL,
            password=palantir_app.auth_config.SALESFORCE_PASS,
            security_token=palantir_app.auth_config.SALESFORCE_TOKEN,
        )

    def query_sf(self, q, get_all=False):
        try:
            if get_all:
                return self.sf.query_all(q)
            return self.sf.query_all(q)["records"]
        except Exception:
            return None


def get_product_family(full_product_name: str):
    if "EDGE" in full_product_name.upper():
        return "MX"
    elif "WIFI" in full_product_name.upper():
        return "MR"
    elif "CAMERA" in full_product_name.upper():
        return "MV"
    elif "SWITCH" in full_product_name.upper():
        return "MS"
    else:
        abort(400, "Invalid Product Family")


def get_sf_data(epr):
    sf = SalesforceConnection()
    try:
        type_query = f"SELECT Opportunity__c, Product_Family__c, Circuit_ID2__c FROM Engineering__c WHERE Name = '{epr}'"
        address_query = (
            f"SELECT Service_Location_Street__c, Billing_Account__c  FROM Engineering__c WHERE Name = '{epr}'"
        )

        type_info = sf.query_sf(type_query)[0]
        address_info = sf.query_sf(address_query)[0]
        address = address_info["Service_Location_Street__c"]
        name = address_info["Billing_Account__c"]
        for item in type_info:
            if not type_info[item]:
                return f"error - None return from SF Query: {item}"
        cid = type_info["Circuit_ID2__c"]
        service_type = type_info["Product_Family__c"]
        if service_type in MNE_WHITELIST:
            codes = service_to_codes(service_type)
        else:
            return f"error - Unsupported Product Family: {service_type}"
        opp = type_info["Opportunity__c"]
        service_query = f"SELECT Service_Code__c FROM OpportunityLineItem WHERE OpportunityId ='{opp}'"
        services = sf.query_sf(service_query)
        codes = [c for c in codes if "RI" not in c]
        service_codes = [c["Service_Code__c"] for c in services]
        service_codes = {c for c in service_codes if c in codes}
        quantities = {}
        for sc in service_codes:
            quantity_query = (
                f"SELECT Quantity FROM OpportunityLineItem WHERE OpportunityId = '{opp}'"
                f"AND Service_Code__c = '{sc}' AND Service_Location_Street__c = '{address}'"
            )
            if sf.query_sf(quantity_query):
                quantity = sf.query_sf(quantity_query)[0]
                if len(quantity) == 0:
                    continue
                else:
                    quantity = quantity["Quantity"]
                quantities[sc] = quantity
            else:
                continue

        ret_obj = {"address": address, "product_family": get_product_family(service_type), "cid": cid, "name": name}

        # ret_obj['quantity'] = int(quantities[list(quantities.keys())[0]])
        ret_obj["quantity"] = int(sum([quantities[x] for x in quantities.keys()]))
        return ret_obj

    except Exception as e:
        return f"error: {e}"
