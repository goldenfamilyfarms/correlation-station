import logging
import re
from time import sleep

import requests
import urllib3

from arda_app.common import url_config
from arda_app.bll.utils import get_ips_from_subnet
from common_sense.common.errors import abort

# Suppress warnings about insecure requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
MAX_IP_ADDRESSES_TO_CHECK = 64
TRIES = 3
AUTH_SLEEP_TIME = 9
QUERY_SLEEP_TIME = 0.3

# Logger setup
logger = logging.getLogger(__name__)


def remove_html_tags(text: str):
    """Remove HTML tags from a text."""
    clean = re.compile("<.*?>|&nbsp;")
    text_without_tags = re.sub(clean, "", text)
    return text_without_tags.replace("Detail", "").strip()


def skip_info_values(row: dict):
    """Skip specific values in the 'Info' column."""
    skip_values = ["UCEProtectL1", "UCEProtectL2", "UCEProtectL3", "RATS NoPtr", "RATS Dyna"]
    for skip in skip_values:
        if skip.lower() == row.get("Info", "").lower():
            return False
    return True


def analyze_blacklist_table(data: list):
    """Analyze the results of the blacklist table."""
    timeouts = 0
    blacklist_reason = []
    blacklisted = False
    for row in data:
        if row.get("Status") == "OK":
            continue
        if row.get("Status") == "TIMEOUT":
            timeouts += 1
            if len(data) == timeouts:
                return "Timeout", ""
            continue
        if row.get("Info", "").upper() in ["UCEPROTECTL1", "UCEPROTECTL2", "UCEPROTECTL3", "RATS NOPTR", "RATS DYNA"]:
            continue
        blacklist_reason.append(row.get("Info"))
        blacklisted = True
    return blacklisted, blacklist_reason


def get_table_from_html(html_text: str):
    """Extract table data from HTML."""
    row_pattern = r"<tr>(.*?)</tr>"
    cell_pattern = r"<td.*?>(.*?)</td>"

    rows = re.findall(row_pattern, html_text, re.DOTALL)

    table_data = []
    for row in rows:
        cells = re.findall(cell_pattern, row, re.DOTALL)
        row_data = [remove_html_tags(cell).strip() for cell in cells]

        if len(row_data) == 6:
            row_dict = {
                "Status": row_data[0],
                "Info": row_data[1],
                "Reason": row_data[2],
                "TTL": row_data[3],
                "ResponseTime": row_data[4],
            }
            table_data.append(row_dict)
    return table_data


def get_temp_auth_key() -> str:
    """Retrieve the temporary authentication key from the blacklist IP service."""
    url = url_config.BLACKLIST_IP_SERVICE_URL + "api/v1/user"
    tries = TRIES

    while tries:
        tries -= 1
        try:
            response = requests.get(url, verify=False, timeout=300)
            return response.json()["TempAuthKey"]
        except Exception as e:
            logger.error(f"BLACKLIST IP SERVICE Auth error: {e}")
            sleep(AUTH_SLEEP_TIME)

    logger.error("BLACKLIST IP SERVICE Auth failed")
    abort(500, "BLACKLIST IP SERVICE Auth failed")


def get_ip_status(auth_key: str, ip_address: str) -> bool:
    """
    Check the status of an IP address in the blacklist IP service.

    Returns:
        bool: True if the IP address is blacklisted, False otherwise.
    """

    url = "".join(
        (
            url_config.BLACKLIST_IP_SERVICE_URL,
            "api/v1/Lookup?command=blacklist&resultIndex=3&disableRhsbl=true&format=2&argument=",
            ip_address,
        )
    )
    try:
        response = requests.get(url, headers={"TempAuthorization": auth_key}, verify=False, timeout=300)
        # Example Response
        # {
        #     HTML_Value: '<long_html_value>',
        #     UID: '59f19def-6297-4959-8213-a6749a6bff3a',
        #     CommandArgument: '98.7.6.5',
        #     Command: 'blacklist',
        #     ResultIndex: '3',
        #     ga_setCustomVar: [ 'OnBlacklist', 'true', null ]
        # }

        result = response.json()

        result_table = get_table_from_html(result.get("HTML_Value"))
        result, blacklist_reason = analyze_blacklist_table(result_table)
        if result:
            blacklist_reason = {ip_address: blacklist_reason}
        return result, blacklist_reason

    except Exception as e:
        logger.error(f"GETTING BLACKLIST IP status error: {e}")
        return e, ""


def is_blacklisted(ip_address: str) -> dict:
    """
    Check if an IP address or subnet is blacklisted.

    Args:
        ip_address (str): The IP address or subnet to check.

    Returns:
        dict: A dictionary containing the results of the check.
            - 'ip's_checked': The list of IP addresses checked.
            - 'blacklist_status': True if any IP address is blacklisted, False otherwise.
            - 'blacklist_ip's': The list of blacklisted IP addresses.
    """
    logger.info(f"Checking if IP is blacklisted: {ip_address}")
    ips_to_check = get_ips_from_subnet(ip_address)
    if not ips_to_check:
        logger.error("IP address not correct or empty")
        abort(500, "IP address not correct or empty")

    if len(ips_to_check) > MAX_IP_ADDRESSES_TO_CHECK:
        logger.error("Too many IP addresses to check")
        abort(500, "Too many IP addresses to check")

    blacklisted = []
    blacklist_reasons = []

    auth_key = get_temp_auth_key()
    for ip in ips_to_check:
        tries = TRIES

        while tries:
            tries -= 1
            logger.info(f"Checking IP status: {ip}")
            check_ip, blacklist_reason = get_ip_status(auth_key, ip)
            if check_ip:
                logger.info(f"IP is blacklisted: {ip}")
                blacklisted.append(ip)
                blacklist_reasons.append(blacklist_reason)
                break
            if check_ip is False:
                logger.info(f"IP is not blacklisted: {ip}")
                break
            sleep(AUTH_SLEEP_TIME)
            auth_key = get_temp_auth_key()
        sleep(QUERY_SLEEP_TIME)

    return {
        "ip's_checked": ips_to_check,
        "blacklist_status": bool(blacklisted),
        "blacklist_reason": blacklist_reasons if blacklist_reasons else None,
        "blacklist_ip's": blacklisted,
    }
