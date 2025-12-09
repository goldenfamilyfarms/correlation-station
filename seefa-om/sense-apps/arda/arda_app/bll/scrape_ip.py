from common_sense.common.errors import abort
from arda_app.dll.salesforce import SalesforceConnection


def get_service_type(sf_resp: dict) -> str:
    """Define service type of an EPR."""
    match sf_resp["Engineering_Job_Type__c"]:
        case "New":
            # net_new
            if sf_resp["PRISM_Id__c"]:
                if sf_resp["CJ_Sub_Status__c"] != "Not Required: Location Serviceable":
                    return "net_new_cj"
                return "net_new_serviceable"
            # PRISM ID is not populated
            if sf_resp["Fiber_Building_Serviceability_Status__c"] == "Quick Connect On-Net":
                return "net_new_qc"
            return "net_new_serviceable"
        case None | "Partial Disconnect" | "Full Disconnect":
            if sf_resp["SR_Order_Type__c"] == "Disconnect":
                return "disconnect"
        case "Upgrade" | "Express BW Upgrade" | "Downgrade":
            return "bw_change"
        case "Logical Change":
            return "change_logical"

    # none of the cases apply
    abort(500, "Service type could not be found")


def reformat_fields(sf_resp: {}) -> {}:
    """Re-configure SalesForce API-named fields."""
    z_side_info = {}
    decoder = {
        "Legacy_Company__c": "legacy_company",
        "Circuit_ID2__c": "cid",
        "DIA_Type__c": "ipv4_type",
        "IP_Address_Requested__c": "block_size",
        "BuildType__c": "build_type",
        "Name": "engineering_id",
        "Product_Name_order_info__c": "product_name",
    }

    z_side_info["service_type"] = get_service_type(sf_resp)

    for k, v in sf_resp.items():
        if k in decoder:
            z_side_info[decoder[k]] = v

    # sales eng notes are not required for ip reservation endpoint
    return {
        "z_side_info": z_side_info,
        "notes": sf_resp.get("Sales_Engineering_Notes__c", "No Sales Engineering notes found"),
    }


def scrape_ip_main(epr: str) -> dict:
    """Scrape data required for IP reservation from SalesForce given an EPR."""

    # search EPR in SF
    ip_fields = [
        "Legacy_Company__c",
        "DIA_Type__c",  # ipv4_type
        "IP_Address_Requested__c",  # block_size
        "BuildType__c",
        "PRISM_Id__c",  # below are used for service_type
        "Fiber_Building_Serviceability_Status__c",
        "CJ_Sub_Status__c",
        "Sales_Engineering_Notes__c",  # extra field for engineer
    ]
    sf = SalesforceConnection()
    if sf is None:
        abort(500, "Salesforce Connection failed")

    sf_resp = sf.get_epr_fields(epr, add_fields=ip_fields)
    if not sf_resp or len(sf_resp) != 1:
        abort(500, "Incorrect return from Salesforce query")

    # return reformatted version to endpoint
    return reformat_fields(sf_resp[0])
