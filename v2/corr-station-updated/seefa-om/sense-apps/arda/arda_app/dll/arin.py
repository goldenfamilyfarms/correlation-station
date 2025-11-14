import logging
import requests
import xmltodict
import ipaddress

from json import JSONDecodeError
from ipaddress import IPv4Network, IPv6Network
from time import sleep
from mock_data.circuit_design.net_new.ip_swip.data import arin_error_codes

from arda_app.common import url_config, auth_config
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)
ARIN_KEY = auth_config.ARIN_API_KEY


def whois_record(ip):
    logger.info(f"Executing WHOIS lookup and validation for {ip}")
    ip, _ = ip.split("/")
    headers = {"Accept": "application/json"}
    url = f"{url_config.WHOIS_BASE_URL}/rest/ip/{ip}"
    for x in range(6):
        try:
            resp = requests.get(url, timeout=30, headers=headers, verify=False)
        except Exception as e:
            logger.info(f"WHOIS lookup failed for {ip} - {str(e)}")
            continue
        if resp.status_code == 200:
            resp = resp.json()
            get_org = resp.get("net").get("orgRef")
            handle = resp.get("net").get("handle").get("$")

            if get_org:
                get_org = get_org.get("@name")
                if "Charter Communications" not in get_org:
                    customer_ref = resp.get("net").get("customerRef")
                    customer_handle = customer_ref.get("@handle") if customer_ref else None
                    return customer_handle, handle, False
                else:
                    return None, handle, True

            if not get_org:
                customer_ref = resp.get("net").get("customerRef")
                customer_handle = customer_ref.get("@handle") if customer_ref else None
                return customer_handle, handle, False
        else:
            if x != 5:
                sleep(10)

    logger.info(f"WHOIS lookup completed for {ip}")
    # Nothing was found
    abort(500, f"Failed to retrieve WHOIS IP info for block {ip} - STATUS CODE: {resp.status_code}")


def whois_check(ip):
    logger.info(f"Executing WHOIS record lookup for {ip}")
    if "/" in ip:
        ip, _ = ip.split("/")
    headers = {"Accept": "application/json"}
    url = f"{url_config.WHOIS_BASE_URL}/rest/ip/{ip}"

    for x in range(6):
        try:
            resp = requests.get(url, timeout=30, headers=headers, verify=False)
        except Exception as e:
            logger.info(f"WHOIS lookup failed for {ip} - {str(e)}")
            continue
        if resp.status_code == 200:
            resp = resp.json()
            return resp["net"]
        else:
            if x != 5:
                sleep(10)

    logger.error(f"Issue running WHOIS for {ip}")
    abort(500, "IP address is composed Incorrectly")


def format_arin_field(field):
    """Handle substitions explicitly for easy fixes."""
    subs = [
        (" & ", " and "),
        ("&", " and "),  # must follow ' & '
        ("_", " "),
        ("-", " "),
    ]
    for s in subs:
        field = field.replace(s[0], s[1])

    field = remove_special_chars(field).rstrip()  # remove trailing whitespace
    return field


def remove_special_chars(_str: str):
    """Remove special chars to prevent fallout"""
    return "".join(c for c in _str if c.isalnum() or c.isspace())


def has_special_chars(_str):
    """Original string will not be changed. Repeating trivial work okay."""
    if remove_special_chars(_str) != _str:
        return True


def get_arin_records(customer_id, handle):
    net_endpoint = f"/net/{handle}"
    customer_endpoint = f"/customer/{customer_id}"
    logger.info(handle)
    logger.info(customer_id)
    net_record = None
    customer_record = None
    if handle:
        net_record = get_arin_record_by_record_type(net_endpoint)
    if customer_id:
        customer_record = get_arin_record_by_record_type(customer_endpoint)
    arin_records = {"records": {"net": net_record, "customer": customer_record}}

    return arin_records


def create_arin_record(ip, customer_info, handle):
    logger.info(f"Creating ARIN records for {ip}")
    # Creates a Network Object out of IP
    _, cidr = ip.split("/")

    if ":" in ip:
        net = IPv6Network(ip)
    else:
        net = IPv4Network(ip)

    customer_name = format_arin_field(customer_info["customer_id"])
    customer_address = format_arin_field(customer_info["z_address"])
    customer_city = format_arin_field(customer_info["z_city"])
    fields = [customer_address, customer_city, customer_info["z_state"], customer_info["z_zip"]]
    y = []
    for item in fields:
        if has_special_chars(item):
            y.append(item)
    if y:
        logger.error(f"Special characters in customer info triggering fallout. \nCustomer Info: \n{customer_info}")
        abort(500, f'Customer info can not contain special characters. Please update: "{y}"')

    # 50 Char limit on name
    if len(customer_name) > 50:
        customer_name = customer_name[:50]

    xml_post = f"""<customer xmlns="http://www.arin.net/regrws/core/v1" >
    <customerName>{customer_name}</customerName>
    <iso3166-1>
        <name>UNITED STATES</name>
        <code2>US</code2>
        <code3>USA</code3>
        <e164>1</e164>
    </iso3166-1>
    <handle></handle>
    <streetAddress>
        <line number = "1">{customer_address}</line>
    </streetAddress>
    <city>{customer_city}</city>
    <iso3166-2>{customer_info["z_state"]}</iso3166-2>
    <postalCode>{customer_info["z_zip"]}</postalCode>
    <comment>
        <line number = "1"></line>
    </comment>
    <parentOrgHandle>CC04</parentOrgHandle>
    <registrationDate></registrationDate>
    <privateCustomer>false</privateCustomer>
    </customer>"""

    # Create Customer Record
    if ":" in ip:
        version = "6"
    else:
        version = "4"
    logger.info("Creating ARIN Customer Record")
    post_url = f"{url_config.ARIN_CREATE_BASE_URL}/rest/net/{handle}/customer?apikey={ARIN_KEY}"
    headers = {"Accept": "application/xml", "Content-Type": "application/xml"}
    post_resp = requests.post(post_url, headers=headers, data=xml_post, timeout=30, verify=False)
    logger.info(xmltodict.parse(post_resp.text)["customer"])

    # Returns True if there is a failure
    if post_resp.status_code != 200:
        logger.info("Customer creation failed")
        logger.info(post_resp)
        return True, None, "Failed Customer Creation"

    logger.info("CREATE DATA:")
    # logger.info(post_resp.json())
    # post_resp = post_resp.json()
    post_resp = xmltodict.parse(post_resp.text)["customer"]

    xml_put = f"""<net xmlns="http://www.arin.net/regrws/core/v1" >
    <version>{version}</version>
    <comment>
        <line number = "1"></line>
    </comment>
    <registrationDate></registrationDate>
    <orgHandle></orgHandle>
    <handle></handle>
    <netBlocks>
        <netBlock>
            <type>S</type>
            <description></description>
            <startAddress>{net[0]}</startAddress>
            <cidrLength>{cidr}</cidrLength>
        </netBlock>
    </netBlocks>
    <customerHandle>{post_resp["handle"]}</customerHandle>
    <parentNetHandle>{handle}</parentNetHandle>
    <netName>{customer_name}</netName>
    </net>"""

    # NOTE If no errors it will return ticketed request payload with NET payload
    # NOTE If cannot be automatically processed ticket payload will be embedded
    # NOTE Else will return an Error payload

    # Update NET Record
    logger.info("Creating ARIN NET record")
    put_url = f"{url_config.ARIN_CREATE_BASE_URL}/rest/net/{handle}/reassign?apikey={ARIN_KEY}"
    headers = {"Accept": "application/xml", "Content-Type": "application/xml"}
    resp = requests.put(put_url, data=xml_put, headers=headers, timeout=30, verify=False)
    if resp.status_code == 200:
        try:
            resp = xmltodict.parse(resp.text)
        except (JSONDecodeError, AttributeError):
            logger.exception(
                f"JSON decode error while parsing ARIN API response \nURL: {put_url}"
                f"\nPayload: \n{xml_put} \nResponse: {resp}"
            )
            abort(500, "Unexpected response from ARIN during NET record update", response=f"{resp}")
    else:
        logger.info(resp)
        customer_id, handle, org = arin_whois(ip)
        arin_record = get_arin_records(customer_id, handle)
        net_name = arin_record["records"]["net"]["net"]["netName"]
        new_net_name = net_name.replace("-", " ")
        if new_net_name != customer_name:
            logger.info(
                f"Found existing customer {new_net_name} did not match ordering customer {customer_name}. \
                    Customer id {customer_id} and handle {handle}. arin record {arin_record} and IP {ip}"
            )
        return False, None, None

    # Pull the json data
    if resp.get("error"):
        error_code = resp["error"]["code"]
        logger.info(f"Error {error_code} during ARIN NET record creation")
        return True, None, arin_error_codes[error_code]
    else:
        return False, None, None


def delete_arin_record(customer_id, handle):
    logger.info("Executing ARIN record delete")
    try:
        # Delete Net Record
        headers = {"Accept": "application/xml"}
        net_url = f"{url_config.ARIN_CREATE_BASE_URL}/rest/net/{handle}?apikey={ARIN_KEY}"
        net_resp = requests.delete(net_url, timeout=30, headers=headers, verify=False)
        logger.info(f"NET record deleted. Response payload: \n{net_resp}")

        # Delete Customer Record
        customer_url = f"{url_config.ARIN_CREATE_BASE_URL}/rest/customer/{customer_id}?apikey={ARIN_KEY}"
        customer_resp = requests.delete(customer_url, timeout=30, headers=headers, verify=False)
        logger.info(f"Customer record deleted. Response payload: \n{customer_resp}")
        return True
    except Exception:
        logger.exception("ARIN record delete failed")
        return False


def get_arin_record_by_record_type(endpoint):
    headers = {"Accept": "application/xml"}
    url = f"{url_config.ARIN_CREATE_BASE_URL}/rest{endpoint}?apikey={ARIN_KEY}"
    resp = requests.get(url, timeout=30, headers=headers, verify=False)
    if resp.status_code == 200:
        return xmltodict.parse(resp.text)
    else:
        abort(500, f"Error getting ARIN data {xmltodict.parse(resp.text)}")


def ip_range_start_end(ip):
    # Create an IPv4 network object
    network = ipaddress.ip_network(ip, strict=False)

    # Get the starting and ending IP addresses
    start_ip = network[0]  # First IP in the range
    end_ip = network[-1]  # Last IP in the range

    return start_ip, end_ip


def arin_whois(ip):
    logger.info(f"Executing Arin lookup and validation for {ip}")
    headers = {"Accept": "application/xml"}

    start_ip, end_ip = ip_range_start_end(ip)

    if start_ip and end_ip:
        endpoint = f"/net/netsByIpRange/{start_ip}/{end_ip}/"
        url = f"{url_config.ARIN_CREATE_BASE_URL}/rest{endpoint}?apikey={ARIN_KEY}"
    else:
        abort(500, f"Unable to find starting and ending IP: {ip}")

    for x in range(6):
        try:
            resp = requests.get(url, timeout=30, headers=headers, verify=False)
        except Exception:
            logger.info(f"ARIN lookup failed for {ip}")
            continue

        if resp.status_code == 200:
            resp = xmltodict.parse(resp.text)
            customer_ref = resp.get("collection").get("net").get("customerHandle")
            handle = resp.get("collection").get("net").get("parentNetHandle")

            # looking up by customer
            if customer_ref:
                endpoint = f"/customer/{customer_ref}/"
                org_resp = get_arin_record_by_record_type(endpoint)
                org = org_resp.get("customer").get("parentOrgHandle")

                # looking up by org
                if org:
                    endpoint = f"/org/{org}/"
                    parent_org_resp = get_arin_record_by_record_type(endpoint)
                    get_org = parent_org_resp.get("org").get("orgName")

                    if get_org:
                        if "Charter Communications" not in get_org:
                            customer_handle = customer_ref
                            return customer_handle, handle, False
                        else:
                            return None, handle, True

                    if not get_org:
                        customer_handle = customer_ref
                        return customer_handle, handle, False
        else:
            if x != 5:
                sleep(10)

    logger.info(f"ARIN lookup completed for {ip}")
    # Nothing was found
    abort(500, f"Failed to retrieve ARIN IP info for block {ip} - STATUS CODE: {resp.status_code}")
