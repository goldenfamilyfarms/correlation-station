from arda_app.dll.granite import post_granite, put_granite, get_result_as_list
from common_sense.common.errors import abort
import logging
from arda_app.common.cd_utils import granite_customers_url, granite_customersRest_get_url

logger = logging.getLogger(__name__)


def find_or_create_a_customer_v3(customer_data):
    logger.info("Find or create a customer started.")
    return_data = {"created new customer": False}
    customer_data["name"] = clean_billing_name(customer_data)
    customer = get_customer_v3(customer_data)

    if not customer:
        customer = create_customer_v3(customer_data)
        return_data["created new customer"] = True

    return_data["customer"] = customer
    return return_data


def update_sf_id(customer, sf_cust):
    logger.info("Update sf ID")
    update_parameters = {
        "CUSTOMER_ID": customer["id"],
        "CUST_TYPE": customer["type"].upper(),
        "UDA": {"Additional Customer Info": {"SF CUSTOMER UNIQUE ID": customer["id"]}},
    }

    if check_value(sf_cust, "name") is True:
        update_parameters["CUST_NAME"] = sf_cust["name"][:60].upper()

    url = granite_customers_url()
    put_granite(url, update_parameters, timeout=90)
    logger.info("sf ID updated.")


def update_customer_id(customer, sf_cust):
    logger.info("Update customer ID")
    update_parameters = {
        "CUST_INST_ID": customer["CUST_INST_ID"],
        "CUSTOMER_ID": customer["SFID"],
        "CUST_TYPE": customer["TYPE"].upper(),
    }

    if check_value(sf_cust, "name") is True:
        update_parameters["CUST_NAME"] = sf_cust["name"][:60].upper()

    url = granite_customers_url()
    logger.info(f"Updating Customer_ID - {update_parameters}")
    put_granite(url, update_parameters, timeout=90)


def create_customer_v3(customer):
    logger.info("Create Customer started.")
    update_parameters = {
        "CUSTOMER_ID": customer["sf_id"][:50],
        "CUST_TEMPLATE": "CARRIER CUSTOMER" if customer["type"].lower() == "carrier access" else "ENTERPRISE CUSTOMER",
        "CUST_TYPE": customer["type"].upper()[:30],
        "CUST_PRI_PHONE_NO": "" if not customer.get("phone") else customer["phone"][:30],
        "CUST_NAME": customer["name"][:60],
        "CUST_STATUS": "Active",
        "CUST_BILL_FAX": "" if not customer.get("fax") else customer["fax"][:50],
        "CUST_COUNTRY": "" if not customer.get("country") else customer["country"][:60],
        "UDA": {"Additional Customer Info": {"SF CUSTOMER UNIQUE ID": customer["sf_id"]}},
    }
    logger.info(f"Creating customer - {update_parameters}")
    url = granite_customers_url()
    response = post_granite(url, update_parameters, timeout=90, return_resp=True)

    if response.status_code != 200:
        abort(
            500,
            f"URL: {url} - "
            "METHOD: POST - "
            f"Payload: {update_parameters} - "
            f"Status code: {response.status_code} - "
            f"Granite Response: {response.json()['retString']}",
        )

    return customer["sf_id"].upper()


def get_customer_v3(customer, all_data=False):
    """
    Gets the Granite Customer Object for:
    1. customer id or
    2. uda of sf_id

    Parameters:
    customer query params (string): acct_id
    all data (bool): if True provides full customer obj

    Returns:
    None: if no customer is found
    str: acct id if all_data=False
    dict: customer_obj if all_data=True
    """
    logger.info("Get Customer started.")
    acct_id = f"{customer['sf_id']}"
    customers_url = granite_customers_url()
    query_params = f"?CUSTOMER_ID={acct_id}"
    url = f"{customers_url}{query_params}"
    customers_by_account_id = get_result_as_list(url, retry=2)

    if customers_by_account_id:
        update_sf_id(customers_by_account_id[0], customer)

        if all_data:
            return customers_by_account_id[0]

        return customers_by_account_id[0]["id"]
    else:
        customers_url = granite_customers_url()
        query_params = f"?CUSTOMER_ID=&SF_CUSTOMER_UNIQUE_ID={acct_id}"
        url = f"{customers_url}{query_params}"
        customers_by_uda_sf_id = get_result_as_list(url, retry=2)

        if customers_by_uda_sf_id:
            rest_url = granite_customersRest_get_url()
            query_params = f"?CUSTOMER_ID={customers_by_uda_sf_id[0]['id']}"
            url = f"{rest_url}{query_params}"
            rest_customer_results = get_result_as_list(url, retry=2)

            if rest_customer_results:
                update_customer_id(rest_customer_results[0], customer)

                if all_data:
                    return rest_customer_results[0]

                return rest_customer_results[0]["SFID"]

    return


def check_value(customer, value):
    try:
        if customer.get(value):
            return True

        return False
    except (AttributeError, KeyError):
        return False


def clean_billing_name(customer_data):
    customer_name = customer_data["name"]

    if "INDIVIDUALLY BILLED" in customer_name:
        if "-" in customer_name:
            clean_name = customer_name.rsplit("-", 1)[0]
        else:
            clean_name = customer_name.split("INDIVIDUALLY BILLED")[0]

        return clean_name.strip()
    # return original customer name if INDIVIDUALLY BILLED not found in the name
    return customer_name


def cid_entrance_criteria(payload):
    colo_datacenter = payload.get("colo_datacenter")
    if colo_datacenter and colo_datacenter.lower() == "yes":
        abort(500, f"Unsupported assigned colo datacenter value of {colo_datacenter}")
