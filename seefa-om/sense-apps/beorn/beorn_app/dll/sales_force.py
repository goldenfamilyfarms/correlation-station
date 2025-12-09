import json

from simple_salesforce import Salesforce

from beorn_app import auth_config, url_config

HTTP_SERVER_ERROR = 500
HTTP_SUCCESS = 200

PRODUCT_FAMILY = "Product_Family__c"
FIBER_CONNECT_PLUS = "Fiber Connect Plus"
SF_NULL_RESPONSE = "Failed to Find Data in SalesForce"
CIRCUIT_ID = "Circuit_ID2__c"
ENGINEERING_TABLE = "Engineering__c"

ERROR_MESSAGES = {
    "error_prefix": "RF Codes Error",
    "json_decode": "JSON Error Querying Salesforce",
    "index_error": "Empty Response From Salesforce Query",
    "general_exception": "Salesforce Query Failed with Exception",
}


class SalesforceRecordsNotFound(Exception):
    def __init__(self, table: str, query_data: str):  # noqa: B042
        self.table = table
        self.query_data = query_data
        self.message = f"Failed to pull Salesforce records from {self.table} table with query data: {self.query_data}"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


def setup_salesforce() -> Salesforce:
    sf = Salesforce(
        instance_url=url_config.SALESFORCE_BASE_URL,
        username=auth_config.SALESFORCE_EMAIL,
        password=auth_config.SALESFORCE_PASS,
        security_token=auth_config.SALESFORCE_TOKEN,
    )
    return sf


def salesforce_request(query: str) -> dict:
    sf = setup_salesforce()
    result = json.loads(json.dumps((sf.query_all(query))))
    return result


def get_codes(eng_id: str, prefix="RF") -> dict:
    """
    gets the RF codes from SF
    :param eng_id: Engineering ID
    :return: dict
    """

    try:
        eng_table_query: dict = salesforce_request(
            f"SELECT Service_Request__c, Service_Location_Street__c FROM Engineering__c WHERE Name IN ('{eng_id}')"
        )

        if not eng_table_query.get("records"):
            query_data: str = f"ENG-ID: {eng_id}"
            raise SalesforceRecordsNotFound("Engineering", query_data)

        service_request: str = eng_table_query.get("records", [{}])[0].get("Service_Request__c", "")

        street: str = eng_table_query.get("records", [{}])[0].get("Service_Location_Street__c", "")

        if not all([service_request, street]):
            query_data: str = (
                f"Service Request: {service_request if service_request else 'Not Found'}, "
                f"Street: {street if street else 'Not Found'}"
            )
            raise SalesforceRecordsNotFound("Engineering", query_data)

        service_request_type: dict = salesforce_request(
            f"SELECT Service_Request_Order_Type__c FROM Service_Request__c WHERE Id = '{service_request}'"
        )

        if service_request_type.get("records", [{}])[0].get("Service_Request_Order_Type__c") != "New Install":
            raise SalesforceRecordsNotFound("Service Request", f"{eng_id} Not Listed as New Install")

        opp_table_query: dict = salesforce_request(
            f"SELECT Service_Code__c, Ntl_ICOMS_Service_Code__c, Offer__c, Quantity "
            f"FROM OpportunityLineItem WHERE Service_Request__c = '{service_request}' AND Opp_Service_Loc_Name__c"
            f" LIKE '%{street}%' AND Quantity > 0"
        )

        if not opp_table_query.get("records"):
            query_data: str = (
                f"Service Request: {service_request if service_request else 'Not Found'}, "
                f"Street: {street if street else 'Not Found'}"
            )
            raise SalesforceRecordsNotFound("Opportunity", query_data)

        offer_ids = [result.get("Offer__c") for result in opp_table_query.get("records") if result.get("Offer__c")]

        zero_rated_codes_query: dict = query_zero_rated_codes(offer_ids)

        svc_codes: list = aggregate_svc_codes(
            opp_table_query.get("records") + zero_rated_codes_query.get("records"), prefix
        )

        return {"svc_codes": svc_codes, "status": HTTP_SUCCESS}

    except SalesforceRecordsNotFound as salesforce_records_error:
        return {"error": str(salesforce_records_error), "status": HTTP_SERVER_ERROR}

    except json.JSONDecodeError as json_error:
        message = f"{ERROR_MESSAGES.get('error_prefix')}: {ERROR_MESSAGES.get('json_decode')}: {json_error}"
        return {"error": json_error, "status": HTTP_SERVER_ERROR}

    except IndexError as index_error:
        message = f"{ERROR_MESSAGES.get('error_prefix')}: {ERROR_MESSAGES.get('index_error')}: {index_error}"
        return {"error": message, "status": HTTP_SERVER_ERROR}

    except Exception as exception:
        message = f"{ERROR_MESSAGES.get('error_prefix')}: {ERROR_MESSAGES.get('general_exception')}: {exception}"
        return {"error": message, "status": HTTP_SERVER_ERROR}


def query_zero_rated_codes(ids: list) -> dict:
    def zero_rated_code_request(id):
        return salesforce_request(f"SELECT Zero_Rated_Version_of_Service_Code__c FROM Offers__c WHERE Id = '{id}'")

    zero_rated_codes = [zero_rated_code_request(id).get("records", [{}])[0] for id in ids]

    offer_table_query: dict = {"records": zero_rated_codes}

    return offer_table_query


def aggregate_svc_codes(query_result: dict, prefix) -> list:
    def sc_extractor(service_code_column: str) -> list:
        service_codes = [
            service_code.get(service_code_column)
            for service_code in query_result
            if service_code.get(service_code_column)
        ]
        return [service_code for service_code in service_codes if prefix in service_code]

    service_codes: list = sc_extractor("Service_Code__c")
    national_icoms_codes: list = sc_extractor("Ntl_ICOMS_Service_Code__c")
    zero_rated_service_codes: list = sc_extractor("Zero_Rated_Version_of_Service_Code__c")

    sc_codes = list(set(service_codes + national_icoms_codes + zero_rated_service_codes))

    return sc_codes
