import logging

from arda_app.common.cd_utils import (
    granite_amos_url,
    granite_parent_mgd_get_url,
    granite_paths_url,
    granite_customer_update_url,
    granite_amoUDAs_url,
)
from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite, post_granite, put_granite

logger = logging.getLogger(__name__)


def create_meraki_services(payload):
    """Create Customer Premise Equipment shelf."""
    cid = payload["CID"]
    path_response = get_granite(granite_paths_url() + f"?CIRC_PATH_HUM_ID={cid}", 60, True).json()
    logger.info(f"\n Paths call response: {path_response}\n")
    inst_id = path_response[0]["pathInstanceId"]
    acct_num = payload["Account Number"]
    # SDFI check
    sdfi = True if "SECURE" in payload["Product Name"].upper() else False
    # Check for Existing parent org.
    parent_mgd_svc = get_granite(granite_parent_mgd_get_url(inst_id))
    parent_in_path, service_in_path = False, False
    parent_category = "Meraki Service Org Parent" if not sdfi else "Secure Internet Org Parent"
    svc_category = (
        f"Meraki Network-{payload['Product Name'].split(' ')[-1]}" if not sdfi else "Secure Internet Access - Meraki"
    )
    logger.info(f"Parent mgd svc granite return: {parent_mgd_svc}")
    if isinstance(parent_mgd_svc, dict):
        parent_in_path = False
    else:
        for uda in parent_mgd_svc:
            if uda["CATEGORY"] == parent_category:
                parent_in_path = True
                parent_name = uda["NAME"]
            if uda["CATEGORY"] == svc_category:
                service_in_path = True
                service_name = uda["NAME"]

    amo_definition = "Secure Internet" if sdfi else "Meraki Service"
    # Handle Parent Org in Granite.
    if not parent_in_path:
        # Check for Existing Meraki Parent if not in path.
        ms_type = "SIP" if sdfi else "MRKI"
        parent_name = f"{ms_type}.{acct_num.split('-')[1]}.{payload['Customer Name']}".upper()
        parent_org_query = get_granite(granite_amoUDAs_url(parent_name))
        parent_exists = isinstance(parent_org_query, list)
        if parent_exists:
            logger.info(f"Meraki Service Org Parent found. Associating to path: {parent_org_query}")
            associate_response = associate_to_path(inst_id, {"amoName": parent_org_query[0]["NAME"]})
        else:
            parent_payload = {
                "AMO_NAME": parent_name,
                "AMO_DEFINITION": amo_definition,
                "AMO_STATUS": "Planned",
                "AMO_CATEGORY": parent_category,
            }
            logger.info(f"Parent Managed Service not found. Creating with following payload: {parent_payload}")
            parent_info = create_meraki(parent_payload)
            if parent_info.get("httpCode"):
                abort(500, f"Failed in creating Parent Org: {parent_info['retString']}")
            associate_response = associate_to_path(inst_id, parent_info)
            parent_name = parent_info["amoName"]
        if associate_response.get("httpCode"):
            abort(500, f"Failed in Associating Parent Org: {associate_response['retString']}")

    if not sdfi:
        service_map = {
            "Edge": "MN-EDGE",
            "Switch": "MN-SWITCH",
            "Camera": "MN-CAMERA",
            "WiFi": "MN-WIFI",
            "Room": "MN-WIFI PER ROOM",
        }
        prod_name = payload["Product Name"].split(" ")[-1]
        mapped_svc = service_map[prod_name]
        category = f"Meraki Network-{prod_name}" if prod_name != "Room" else "Meraki Network-Hospitality WiFi"
    else:
        mapped_svc = "SIA-M"
        category = "Secure Internet Access - Meraki"
    # Handle Meraki Service in Granite.
    if not service_in_path:
        # Check for Meraki Service if not in Path.
        service_name = f"{mapped_svc}.{payload['Customer Name']}.{payload['Customer Address']}".upper()
        service_query = get_granite(granite_amoUDAs_url(service_name))
        service_exists = isinstance(service_query, list)
        if service_exists:
            logger.info(f"Meraki Service found. Associating to path: {service_query}")
            associate_response = associate_to_path(inst_id, {"amoName": service_query[0]["NAME"]})
        else:
            service_payload = {
                "AMO_NAME": service_name,
                "AMO_DEFINITION": amo_definition,
                "AMO_STATUS": "Planned",
                "AMO_CATEGORY": category,
                "PARENT_AMO_NAME": parent_name,
            }
            logger.info(f"{mapped_svc} Meraki Service not found. Creating with following payload: {service_payload}")
            service_info = create_meraki(service_payload)
            if service_info.get("httpCode"):
                abort(500, f"Failed in creating meraki service {service_info['retString']}")
            associate_response = associate_to_path(inst_id, service_info)
            service_name = service_info["amoName"]
        if associate_response.get("httpCode"):
            abort(500, f"Failed in Associating Parent Org: {associate_response['retString']}")

    # Check that Ordering Customer and Z-side customer matches one provided and exists.
    check_existing_customer(cid, acct_num)

    # Update Path Service Type and Managed Services Availability based on input
    update_ms_path_elements(inst_id, payload.get("High Availability"), payload["NWID"] if payload.get("NWID") else None)
    # Associate Parent Meraki Org and Meraki Service to Customer
    associate_to_customer(acct_num, parent_name)
    associate_to_customer(acct_num, service_name)

    logger.info("Meraki Services creation success")

    return 200, "Successfully confirmed Meraki Services"


def update_ms_path_elements(inst_id, is_ha, nwid=None):
    payload = {
        "PATH_INST_ID": inst_id,
        "UDA": {
            "SERVICE TYPE": {"MANAGED SERVICE": "YES"},
            "MERAKI SERVICES": {
                "AVAILABILITY LEVEL": "HIGH" if is_ha else "STANDARD",
                "MERAKI NETWORK ID": nwid.split("_")[-1] if nwid else "",
            },
        },
    }
    response = put_granite(granite_paths_url(), payload, 60, True).json()
    if response["retString"] != "Path Updated":
        abort(500, f"Error Editing granite Service type and Meraki Services: {response['retString']}")
    else:
        return response


def check_existing_customer(cid: str, acct_num: str):
    path_response = get_granite(granite_paths_url() + f"?CIRC_PATH_HUM_ID={cid}", 60, True).json()
    if isinstance(path_response, list):
        ordering_customers = {path.get("orderingCustomer") for path in path_response}
        z_customers = {path.get("zSideCustomer") for path in path_response}
        if not ordering_customers and not z_customers:
            return False
        elif ordering_customers == z_customers and acct_num in z_customers:
            return True
        else:
            error_message = (
                f"Customer info mismatch in Granite. Existing Ordering Customer: {ordering_customers},"
                f" zSidecustomer: {z_customers}, Requested: {acct_num}"
            )
            abort(500, error_message)
    else:
        abort(500, f"Unexpected response to Paths received while associating Customer: {path_response}")


def associate_to_path(inst_id, amo_info):
    """
    Updates the path to associate an AMO to it.
    """
    payload = {"PATH_INST_ID": inst_id, "AMO_NAME": amo_info["amoName"]}
    response = put_granite(granite_paths_url(), payload, 60, True).json()
    return response


def associate_to_customer(customer_id, amo_name):
    payload = {"CUSTOMER_ID": customer_id, "AMO_NAME": amo_name}
    response = put_granite(granite_customer_update_url(), payload, 60, True).json()
    if response["retString"] != "Customer Updated":
        abort(500, f"Error Associating parent meraki to customer: {response['retString']}")
    else:
        return response


def create_meraki(payload):
    response = post_granite(granite_amos_url(), payload, 60, True).json()
    return response


def disassociate_meraki(mne_name, parent_mne):
    payload = {"AMO_NAME": mne_name, "DISASSOCIATE_FROM_PARENT": "TRUE", "PARENT_AMO_NAME": parent_mne}
    response = put_granite(granite_amos_url(), payload, 60, True).json()

    if response["retString"] != "AMO Updated":
        abort(500, f"Error disassociating {mne_name} from Parent: {parent_mne}")


def update_meraki_status(mne_name):
    payload = {"AMO_NAME": mne_name, "AMO_STATUS": "Pending Decommission"}
    response = put_granite(granite_amos_url(), payload, 60, True).json()

    if response["retString"] != "AMO Updated":
        abort(500, f"Error changing status of {mne_name} to Pending Decommission")


def add_mne_to_parentorg(mne_name, mne_parent, mne_category):
    payload = {"AMO_NAME": mne_name, "AMO_CATEGORY": mne_category, "PARENT_AMO_NAME": mne_parent}
    response = put_granite(granite_amos_url(), payload, 60, True).json()

    if response["retString"] != "AMO Updated":
        abort(500, f"Error adding {mne_name} back to {mne_parent}")
