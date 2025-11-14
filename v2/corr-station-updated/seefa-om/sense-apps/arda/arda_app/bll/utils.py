import logging

import ipaddress
from arda_app.dll.granite import get_paths_from_ip, update_vgw_shelf_ipv4_address
from common_sense.common.errors import abort
from typing import List


logger = logging.getLogger(__name__)


def check_keys(body: dict, keys: List[str]) -> List[str]:
    """
    Check if all the required keys are present in a dictionary.

    :param body: The dictionary to check.
    :param keys: A list of required keys.
    :return: A list of missing keys.
    """
    missing = [key for key in keys if key not in body]
    return missing


def get_4_digits(chan: str) -> str:
    """
    Extract the first 4 consecutive digits from a string.

    :param chan: The string to extract from.
    :return: The extracted 4-digit string.
    """
    vlan = ""

    for i in chan:
        if i.isnumeric():
            vlan += str(i)
            if len(vlan) == 4:
                return vlan

    return vlan


def get_special_char(chan: str) -> str:
    """
    Find the first special character (non-alphanumeric) in a string.

    :param chan: The string to search in.
    :return: The first special character found.
    """
    for c in chan:
        if not c.isalnum():
            return c

    return ""


def convert_to_int(num: str, default: int = 0) -> int:
    """
    Convert a string to an integer. If conversion fails, return the default value.

    :param num: The string to convert.
    :param default: The default value to return if conversion fails. Default is 0.
    :return: The converted integer or the default value.
    """
    try:
        return int(num)
    except ValueError:
        return default


def get_ips_from_subnet(subnet: str) -> List[str]:
    """
    Get a list of all IP addresses within a subnet.

    :param subnet: The subnet in CIDR notation.
    :return: A list of IP addresses in the subnet.
    """
    try:
        ip_network = ipaddress.ip_interface(subnet).network
    except ValueError as e:
        logger.info(f"Invalid subnet: {e}")
        return []

    all_ips = [str(ip) for ip in ip_network]
    return all_ips


def compare_ipv6_addresses(address1: str, address2: str) -> bool:
    """
    Compare two IPv6 addresses.

    :param address1: The first IPv6 address.
    :param address2: The second IPv6 address.
    :return: True if the addresses are equal, False otherwise.
    """

    if not all((isinstance(address1, str), isinstance(address2, str))):
        return False

    address1 = address1.replace(" ", "")
    address2 = address2.replace(" ", "")

    try:
        ip1 = ipaddress.IPv6Interface(address1)
        ip2 = ipaddress.IPv6Interface(address2)

        return ip1.network == ip2.network
    except ipaddress.AddressValueError:
        return False


def compare_ipv4_addresses_and_cidr_notation(db_address: str, net_address: str, cid: str, vgw_ipv4: str) -> bool:
    """
    Compare two IPv4 addresses first, then compare their CIDR notations

    :param db_address: The first IPv4 address as stored in Granite DB.
    :param net_address: The second IPv4 address as returned from the network.
    :return: True if the addresses are equal, False otherwise.
    """

    if not all((isinstance(db_address, str), isinstance(net_address, str))):
        return False

    db_address = db_address.replace(" ", "")
    net_address = net_address.replace(" ", "")

    try:
        ip1 = ipaddress.IPv4Interface(db_address)
        ip2 = ipaddress.IPv4Interface(net_address)

        # check IPv4 address format
        if str(ip1.ip) == str(ip2.ip):
            # check subnets (CIDR notations)
            if str(ip1.network.prefixlen) != str(ip2.network.prefixlen):
                # update granite with the CIDR found on the network
                vgw_ip = vgw_ipv4.split("/")[0]
                update_vgw_shelf_ipv4_address(cid, f"{vgw_ip}/{str(ip2.network.prefixlen)}")
            return True
        else:
            return False
    except ipaddress.AddressValueError:
        return False


def compare_models(model1: str, model2: str) -> bool:
    try:
        model1 = model1.split("-")[1]
        model2 = model2.split("-")[1]
        return model1 == model2
    except IndexError:
        # Handles models that are operationally considered 'equivalent' despite a difference in model names
        # e.g. RAD ETX-203AX/GE30/2SFP/4UTP (Granite) == RAD ETX203AX/2SFP/2UTP2SFP (network)
        #      will return True
        return True if ("203AX" in model1.upper()) and ("203AX" in model2.upper()) else False


def retaining_ip_addresses(payload: dict, exit_payload: dict) -> dict:
    cid = payload.get("cid")
    if not cid:
        msg = f"Unable to retrieve CID from payload {payload}"
        logger.error(msg)
        abort(500, msg)
    # process only IP addresses with CIDR notation
    ip = payload.get("ip_address")
    if not ip:
        msg = f"Unable to retrieve IP address from payload {payload}"
        logger.error(msg)
        abort(500, msg)
    try:
        if ipaddress.ip_interface(ip) and ("/" in ip):
            pass
        else:
            msg = f"IP address {ip} isn't in CIDR notation"
            logger.error(msg)
            abort(500, msg)
    except ValueError:
        msg = f"IP address {ip} doesn't appear to be formatted as IPv4 or IPv6"
        logger.error(msg)
        abort(500, msg)
    # verify no usable IP addresses are requested
    ip_requested = payload.get("usable_ip_addresses_requested")
    if ip_requested is not None:
        if ip_requested not in ("", "None"):
            msg = f"Usable IP addresses are erroneously requested when attempting to retain IP addresses for {cid}"
            logger.error(msg)
            abort(500, msg)
    # verify IP addresses to move are currently associated with a pending decom CID
    cid_to_move_ips_from, cid_status = get_cid_info_from_ip(ip)
    if cid_status.upper() != "PENDING DECOMMISSION":
        msg = f"Not able to move IP addresses from CID {cid_to_move_ips_from} because its status is {cid_status}"
        logger.error(msg)
        abort(500, msg)
    # add new info to exit payload before returning
    msg = "Yes - No Hub Impact - Inflight Customer Only Impacted"
    exit_payload["maintenance_window_needed"] = msg
    msg = "MW to migrate Customer IPs"
    existing_notes = exit_payload.get("circuit_design_notes", "")
    exit_payload["circuit_design_notes"] = f"{msg}; {existing_notes}" if existing_notes else msg
    return exit_payload


def get_cid_info_from_ip(ip: str) -> tuple:
    cid = None
    status = None
    data = get_paths_from_ip(ip)
    if data and isinstance(data, list):
        cid = data[0].get("PATH_NAME")
        status = data[0].get("STATUS")
    else:
        msg = f"Unable to retrieve path data from IP {ip}"
        logger.error(msg)
        abort(500, msg)
    if cid and status:
        return cid, status
    else:
        msg = f"Unable to determine CID info IP {ip} belongs to"
        logger.error(msg)
        abort(500, msg)
