import logging
import requests
import smtplib

import palantir_app

from common_sense.common.errors import abort
from palantir_app.common.utils import get_hydra_headers
from palantir_app.dll import granite
from palantir_app.dll.sales_force import get_sf_data
from palantir_app.dll.mdso import mdso_post, product_query
from palantir_app.common.endpoints import (
    GRANITE_AMOS,
    GRANITE_CARDS,
    GRANITE_EQUIPMENTS,
    GRANITE_MS,
    GRANITE_PATHS,
    GRANITE_PORTS,
    GRANITE_SHELVES,
    GRANITE_SITES,
)

logger = logging.getLogger(__name__)
from_email_address = "do-not-reply-ms-inc@charter.com"


def run_mne_compliance(cid, eng_id):
    # Get UDAs and Path Elements from Granite
    code, path_elements = granite.get_path_elements_from_filter(cid, level="1")
    if code != 200:
        abort(500, path_elements)
    highest_rev = sorted([x["PATH_REV"] for x in path_elements])[-1]
    inst_id = ""
    for elems in path_elements:
        if elems["PATH_REV"] == highest_rev:
            inst_id = elems["CIRC_PATH_INST_ID"]
        else:
            path_elements.pop(path_elements.index(elems))

    response, udas = granite.get_udas(cid, highest_rev)
    if response != 200:
        abort(500, f"Error getting UDA from Granite: {udas}")
    if udas:
        udas = {x["ATTR_NAME"]: x["ATTR_VALUE"] for x in udas}
        logger.info(f"NC: CID: {cid}, SORTED UDA: {udas}, inst_id: {inst_id}")
        # once UDAs are successfully acquired, attempt to get SF Elements
        sf_return = get_sf_data(eng_id)
        if not isinstance(sf_return, dict):
            abort(500, f"Erroneous return from Salesforce: {sf_return}")

        # Start MDSO Process. Get product ID.
        prod_id = product_query("merakiCompliance", False)
        if not prod_id:
            abort(500, "Error fetching product id from MDSO")
        nwid = udas.get("MERAKI NETWORK ID", None)
        clli = path_elements[0]["Z_CLLI"]
        if not all((nwid, clli)):
            abort(500, f"Missing Elements. nwid: {nwid} clli: {clli}")

        # Build Public IP info to check from Granite add to payload if found.
        tid_ips = get_public_ip_by_family(path_elements, sf_return["product_family"])
        sf_return["public_ip_block"] = tid_ips

        _a, ms_payload = call_granite_for_parent_managed_services(cid)
        if not ms_payload or not check_mgd_svc(ms_payload, sf_return["product_family"], sf_return["address"]):
            return "Meraki Services with appropriate Prod Family and Name not found or does not exist.", 500

        highest_path_elem = [elem for elem in path_elements if elem["PATH_REV"] == highest_rev and elem["MODEL"]]
        # Get Customer Account number from Granite, fail out if None returned
        account_num = get_account_number(path_elements)
        if not account_num:
            abort(500, "Account number not found")

        # Checking highest rev path_elements for Meraki shelf existing if product_family is MX
        shelf = False
        if sf_return["product_family"] == "MX":
            for elem in highest_path_elem:
                if "MERAKI" in elem["MODEL"]:
                    shelf = True
                    break
            if not shelf:
                abort(500, "MX Shelf not present in Granite.")

        # Build MDSO payload
        sf_return["nwid"] = nwid
        sf_return["CLLI"] = clli
        sf_return["account_number"] = account_num

        # Initiate MDSO Process
        prod_id = product_query("merakiCompliance", False)
        data = {"productId": prod_id, "label": eng_id, "properties": {"expected_data": sf_return}}
        endpoint = "/bpocore/market/api/v1/resources?validate=false&obfuscate=true"
        if nwid and clli:
            return mdso_post(endpoint, data, "Meraki_Compliance")
        else:
            abort(500, f"Granite Missing Elements. nwid: {nwid} clli: {clli}")
    else:
        abort(500, "Granite issue. UDA or CID not found")


def mne_compliance_stl(cid, eng_id):
    sf_return = get_sf_data(eng_id)
    _, ms_payload = call_granite_for_parent_managed_services(cid)
    if "No records found" in ms_payload:
        abort(500, f"No Meraki SVCS UDA Found in path {cid}")
    parent_amo = [payload for payload in ms_payload if "PARENT" in payload["CATEGORY"].upper()]
    if not parent_amo:
        abort(500, f"No Parent Meraki SVCs found: {[ms['NAME'] for ms in ms_payload]}")
    parent_payload = {"AMO_NAME": parent_amo[0]["NAME"], "AMO_STATUS": "Live"}

    # Check and Parent STL to live if not live.
    code, path_elems = granite.get_path_elements_from_filter(cid, level="1")
    if code != 200:
        abort(500, f"Failure fetching path_elements from Granite: {path_elems}")
    mgd_svcs_match = check_mgd_svc(ms_payload, sf_return["product_family"], sf_return["address"])
    parent_meraki_stl(parent_payload)
    meraki_services_stl(mgd_svcs_match)
    set_site_live(path_elems)

    # Set Path to live for CUS-INTERNET Access += BYO/COAX
    highest_rev = sorted([x["PATH_REV"] for x in path_elems])[-1]
    for elems in path_elems:
        if elems["PATH_REV"] == highest_rev:
            continue
        else:
            path_elems.pop(path_elems.index(elems))

    # Set Port/Shelf/Card live for CABLE MODEM DOCSIS shelves
    if True in ["CABLE MODEM" in x["ELEMENT_CATEGORY"] for x in path_elems]:
        set_shelf_live(path_elems, "CABLE")
        set_card_live(path_elems, "DOCSIS")
        set_ports_live(path_elems, "DOCSIS")

    # Set Port/Shelf/Card/MX Transports to Live
    if sf_return["product_family"] == "MX":
        set_shelf_live(path_elems)
        set_card_live(path_elems)
        set_ports_live(path_elems)
        transport_stl(path_elems)

    # Set path live under very specific circumstances
    path_stl(cid)

    return "Success", 200


def check_mgd_svc(ms_elements, product_family, address):
    """
    Parse through passed in managed services elements and return one with name matching
    the provided customer address and TYPE, per GSIP.
    param: ms_elements = list of dicts from parentManagedServices GK API call.
    param: address = customer address
    param: return_id = Bool to return a Bool or the matching Element/data
    """
    family_map = {"MX": "EDGE", "MS": "SWITCH", "MR": "WIFI", "MV": "CAMERA"}
    found_elements = []
    if ms_elements and isinstance(ms_elements, list):
        logger.info(f"ms_elements: {ms_elements}")
        for meraki_service in ms_elements:
            found_elements.append(meraki_service["NAME"])
            if address.upper() in meraki_service["NAME"] and family_map[product_family] in meraki_service["NAME"]:
                return meraki_service
        abort(500, f"No matching Meraki Svcs Found. Found: {found_elements}")
    else:
        abort(500, f"Incorrect Managed Services data passed in: {ms_elements}")


def get_account_number(path_elements):
    """
    Takes in Granite response from Path elements API and returns ACCT- numbers
    """
    accts = {e["CUSTOMER_ID"] for e in path_elements if e["CUSTOMER_ID"] and " NNI" not in e["CUSTOMER_NAME"]}
    logger.info(f"accounts: {accts}")
    if accts and len(accts) < 2:
        return list(accts)[0]
    else:
        return []


def get_public_ip_by_family(path_elements, product_family):
    """
    Takes in granite response from PathElements API and returns found public IPs
    Query field based on product_family
    """
    for e in path_elements:
        ip = e.get("IPV4_ASSIGNED_SUBNETS", "")
        routed = e.get("IPV4_GLUE_SUBNET", "") if e.get("IPV4_SERVICE_TYPE", "") == "ROUTED" else False
        if routed:
            return routed
        elif ip:
            return ip
        else:
            continue
    if not ip:
        return None


def meraki_services_stl(matching_meraki_svc):
    # takes payload and sets Meraki Svcs to live
    payload = {"AMO_NAME": matching_meraki_svc["NAME"], "AMO_STATUS": "Live"}
    logger.info(f"payload: {payload} ")
    mgd_svc_update = granite.granite_put(GRANITE_AMOS, payload, best_effort=True)
    if "errorStatusCode" in mgd_svc_update.keys():
        abort(500, f"Meraki Svc STL Error: {mgd_svc_update['errorStatusCode']}")


def parent_meraki_stl(parent_meraki_payload):
    # takes payload and sets Meraki Svcs to live
    logger.info(f"payload: {parent_meraki_payload} ")
    mgd_svc_update = granite.granite_put(GRANITE_AMOS, parent_meraki_payload, best_effort=True)
    if "errorStatusCode" in mgd_svc_update.keys():
        abort(500, f"Meraki Svc STL Error: {mgd_svc_update['errorStatusCode']}")


def dissociate_merakis_from_live(live_path):
    """
    Dissociate Meraki svcs AMOs from the live paths so new path can be STL
    Param: live_path
    """
    params = {"CIRC_PATH_INST_ID": live_path["pathInstanceId"]}
    meraki_response = granite.granite_get(GRANITE_MS, params, operation="mne", return_response_obj=True).json()
    if (
        isinstance(meraki_response, dict)
        and "No records found with the specified search criteria..." in meraki_response.values()
    ):
        logger.info(f"No Meraki SVC UDA found in Live path. Inst id: {live_path['pathInstanceId']} Moving on")
    else:
        for meraki in meraki_response:
            dissociate_payload = {
                "AMO_NAME": meraki["NAME"],
                "DISASSOCIATE_FROM_CHILDREN": "single",
                "TARGET_INST_ID": live_path["pathInstanceId"],
                "TARGET_TYPE": "Path",
            }
            dissociate_result = granite.granite_put(GRANITE_AMOS, dissociate_payload, best_effort=True)
            logger.info(f"dissociate result: {dissociate_result}")
            if "errorStatusCode" in dissociate_result.keys():
                abort(
                    500,
                    f"Meraki STL Error while attempting to Dissociate from Path:{dissociate_result['errorStatusCode']}",
                )


def path_stl(cid):
    """
    Sets Granite Path to Live after parsing for highest rev of path elems.
    """
    get_response = granite.granite_get(f"{GRANITE_PATHS}?CIRC_PATH_HUM_ID={cid}", operation="mne")
    if get_response and isinstance(get_response, list):
        live_path = [path for path in get_response if path["status"] == "Live"]
        if len(get_response) > 1 and live_path:
            logger.info(f"MS-NC: Removing live Revision with Inst ID: {live_path[0]['pathInstanceId']}")
            dissociate_merakis_from_live(live_path[0])
            granite.delete_path(live_path, cid, "Canceled")
        highest_rev = sorted([x["pathRev"] for x in get_response])[-1]
        for x in get_response:
            if x["pathRev"] < highest_rev:
                get_response.pop(get_response.index(x))
        logger.info(f"Highest Rev Paths : {get_response}")
        top_rev_paths = get_response
        path_params = {
            "PATH_NAME": top_rev_paths[0]["pathId"],
            "PATH_REVISION": top_rev_paths[0]["pathRev"],
            "BYPASS_CASCADE": "TRUE",
            "PATH_STATUS": "Live",
        }

        put_response = granite.granite_put(GRANITE_PATHS, path_params, True)
        if put_response.get("errorStatusMessage"):
            abort(500, f"Error setting Path to live: {put_response['errorStatusMessage']}")


def transport_stl(path_elems):
    """
    Used to set transport path/elements live
    """
    for e in path_elems:
        if e["ELEMENT_TYPE"] == "PATH" and e["ELEMENT_CATEGORY"] == "ETHERNET TRANSPORT":
            elem_name = e["ELEMENT_NAME"].split(".")
            if elem_name[-1] == elem_name[-2] and "MN" in elem_name[-1]:
                update_parameters = {
                    "PATH_INST_ID": e["ELEMENT_REFERENCE"],
                    "BYPASS_CASCADE": "TRUE",
                    "PATH_STATUS": "Live",
                }
                logger.info(f"UPDATE PARAMS {update_parameters}")
                granite.update_path_by_parameters(update_parameters)
                break


def set_site_live(path_elems):
    """
    This function will update Granite Z Site to live
    """
    z_site_name = path_elems[0]["PATH_Z_SITE"]
    if z_site_name:
        update_params = {"SITE_NAME": z_site_name, "SITE_STATUS": "Live", "SITE_TYPE": "LOCAL"}
        response = granite.granite_put(GRANITE_SITES, update_params)
        if response:
            return "Site STL Successfully"
        else:
            abort(500, "Site STL issue.")
    else:
        abort(500, "Z_SITE_NAME missing in granite.")


def set_ports_live(path_elems, model="MERAKI MX"):
    """
    This function will update Granite Ports live for Meraki devices
    Following 2 methods, including this one, will set their namesakes live
    ONLY for Meraki MX devices at this time.
    Ports are set to skip any template warnings from granite.
    """
    failed = False
    for record in path_elems:
        if record["MODEL"] and model in record["MODEL"]:
            params = {
                "PORT_INST_ID": record["PORT_INST_ID"],
                "PORT_STATUS": "Assigned",
                "PORT_NAME": record["PORT_NAME"],
                "SET_CONFIRMED": "TRUE",
            }
            response = granite.granite_put(GRANITE_PORTS, params)
            if response:
                continue
            else:
                failed = True
                reason = response
    if failed:
        abort(500, f"Ports STL failed due. response: {reason}")
    else:
        return 200, "Ports set to live successfully"


def set_card_live(path_elems, model="MERAKI MX"):
    tid = list(
        {record["ELEMENT_NAME"].split("/")[0] for record in path_elems if record["MODEL"] and model in record["MODEL"]}
    )
    port_id = [
        record["PORT_INST_ID"].split("/")[0] for record in path_elems if record["MODEL"] and model in record["MODEL"]
    ]
    get_url = f"?CLLI={tid[0][0:8]}&EQUIP_NAME={tid[0]}&OBJECT_TYPE=PORT&WILD_CARD_FLAG=1&PORT_INST_ID={port_id[0]}"

    response = granite.granite_get(GRANITE_EQUIPMENTS + get_url, operation="mne")
    if response:
        if response[0]["CARD_STATUS"] != "Live":
            params = {"CARD_INST_ID": response[0]["CARD_INST_ID"], "CARD_STATUS": "Live"}
            response = granite.granite_put(GRANITE_CARDS, params)
            if response:
                return "Card set to live successfully"
            else:
                abort(500, f"Error setting card to live: {response}")
        else:
            return "Card already live"
    else:
        abort(500, f"Error getting card from granite: {response}")


def set_shelf_live(path_elems, device="MX"):
    for record in path_elems:
        if device == "MX":
            if record["MODEL"] and "MERAKI MX" in record["MODEL"]:
                params = {
                    "SHELF_NAME": record["ELEMENT_NAME"],
                    "SITE_NAME": record["A_SITE_NAME"],
                    "SHELF_STATUS": "Live",
                }
                granite.granite_put(GRANITE_SHELVES, params)
        else:
            if record["ELEMENT_CATEGORY"] == "CABLE MODEM":
                params = {
                    "SHELF_INST_ID": record["ELEMENT_REFERENCE"],
                    "SITE_NAME": record["A_SITE_NAME"],
                    "SHELF_STATUS": "Live",
                    "SET_CONFIRMED": "TRUE",
                }
                granite.granite_put(GRANITE_SHELVES, params)


def send_email(
    customer_name, customer_poc, account_number, customer_email, customer_address, circuit_id, product_family
):
    email_un = palantir_app.auth_config.SENSE_EMAIL_NAME
    email_pw = palantir_app.auth_config.SENSE_EMAIL_PASS
    email_server = palantir_app.url_config.SENSE_EMAIL_SERVER
    email_port = palantir_app.url_config.SENSE_EMAIL_PORT

    server = smtplib.SMTP(email_server, email_port)
    server.ehlo()
    server.starttls()
    server.login(email_un, email_pw)
    email_body = f"\n\
    Hi {customer_poc},\n\n\
    We are pleased to inform you of the successful activation of Meraki {product_family}\n\
    If you have any questions please let me know.\n\
    For future change requests and technical support, please contact Enterprise Technical Support:\n\n\
    Enterprise Technical Support\n\
    Telephone# 1-888-812-2591\n\
    Email: ets@charter.com\n\n\
    Property: {customer_name}\n\
    Account# {account_number} \n\
    Location: {customer_address}\n\
    Internet Circuit ID: {circuit_id}\n\
    Device Installed: Meraki {product_family}\n\n\
    You also should have received the SpectrumEnterprise.Net activation email.\n\
    Once you have logged in, select the Managed Network Edge link on the left,\n\
    then click on the Managed Network Edge Portal link that is located in the upper right hand corner of the screen.\n\
    There you will be able to see all of your organization sites in one view. "

    email_subject = f"{customer_name} - {customer_name} - {customer_address}"

    msg = f"Subject: {email_subject}\n\n{email_body}"

    server.sendmail(from_email_address, customer_email, msg)
    logger.info(f"NC- MNE Compliance Email Sent successfully for: {circuit_id}")
    return None


def call_granite_for_parent_managed_services(cid):
    """
    Granite synchronous GET path elements using service path-circuit id (cid)
    returns latest PATH_REV
    """
    response, path_elems = granite.get_path_elements_from_filter(cid, level="1")
    if response != 200:
        abort(500, f"Error getting Path Elements from Granite: {path_elems}")
    highest_rev = sorted([x["PATH_REV"] for x in path_elems])[-1]
    inst_id = ""
    for elems in path_elems:
        if elems["PATH_REV"] == highest_rev:
            inst_id = elems["CIRC_PATH_INST_ID"]
            break
    params = {"CIRC_PATH_INST_ID": inst_id}
    headers = get_hydra_headers(operation="mne", accept_text_html_xml=True)
    try:
        r = requests.get(
            f"{palantir_app.url_config.GRANITE_BASE_URL}{GRANITE_MS}",
            params=params,
            headers=headers,
            verify=False,
            timeout=30,
        )
        if r.status_code != 200:
            logger.exception(f"Received {r.status_code} status from granite")
            if r.status_code == 404:
                return 404, f"No records found for {cid}"
            else:
                return 503, "GRANITE failed to process the request"
        else:
            if isinstance(r.json(), list):
                highest_rev = sorted([x["REVISION"] for x in r.json()])[-1]
                response = r.json()
                for x in response:
                    if x["REVISION"] < highest_rev:
                        response.pop(response.index(x))
                granite_elements = response
            else:
                key = "retString"
                value = "No records found with the specified search criteria..."
                if key in r.json().keys() and value in r.json().values():
                    return 404, f"No records found for {cid}"
                else:
                    return 503, "GRANITE failed to process the request"

        if not granite_elements:
            return 404, f"No records found for {cid}"
        logger.info(f"Granite_Elements PM: {granite_elements}")
        return 200, granite_elements

    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to GRANITE")
        return 504, "Timed out getting data from GRANITE"
