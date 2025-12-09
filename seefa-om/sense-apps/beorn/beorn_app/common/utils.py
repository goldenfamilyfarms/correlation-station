import codecs
import ipaddress as ip
import json
import re
from hashlib import md5

from common_sense.common.errors import abort


# todo: should add a def ipv6 str processor and make the other two methods versatile for both ipv4 and ipv6
def ipv4_str_processor(ipv4_address):
    # process input strings into a list of ipv4 addresses and ipv4 addresses with cidr
    data = {}
    data["ipv4_list"] = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ipv4_address)
    data["ipv4_subnet_list"] = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{0,2})", ipv4_address)
    return data


def is_valid_cpe_tid(tid):
    tidLen = len(tid)
    if tidLen != 11:
        return False

    stateVal = tid[4:6]

    stateList = [
        "AI",
        "AK",
        "AL",
        "AR",
        "AZ",
        "CA",
        "CO",
        "CT",
        "DC",
        "DE",
        "FL",
        "GA",
        "HI",
        "IA",
        "ID",
        "IL",
        "IN",
        "KS",
        "KY",
        "LA",
        "MA",
        "MD",
        "ME",
        "MH",
        "MI",
        "MN",
        "MO",
        "MS",
        "MT",
        "NC",
        "ND",
        "NE",
        "NH",
        "NJ",
        "NM",
        "NV",
        "NY",
        "OH",
        "OK",
        "OR",
        "PA",
        "PR",
        "PW",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UM",
        "UT",
        "VA",
        "VI",
        "VT",
        "WA",
        "WI",
        "WV",
        "WY",
    ]

    if stateVal not in stateList:
        return False

    if tid[9:11] not in ["ZW", "WW", "XW", "YW"]:
        return False
    else:
        return True


def ipv4_length_validator(ipv4_dict):
    # pass processed ipv4 dict to length validator to ensure that
    # the same number of IP's that were found had CIDR notation
    data = ipv4_dict
    ipListLen = len(data["ipv4_list"])
    ipSubnetListLen = len(data["ipv4_subnet_list"])
    listDiff = ipSubnetListLen - ipListLen

    if ipListLen == 0:
        data["ipv4_len_check"] = "No IP Addresses"
    elif listDiff < 0:
        diff = listDiff * -1
        data["ipv4_len_check"] = f"No subnet on {diff} IP Addresses"
    elif listDiff == 0:
        data["ipv4_len_check"] = f"{ipListLen} Valid IP Addresses"
    else:
        data["ipv4_len_check"] = "Logic Error"
    return data


def ipv4_block_processor(ipv4_dict):
    # Pass processed ipv4 dict to subnetter to get default gateway (next hop ip) as well as other ip's
    ipv4_dict["ipv4_assignments"] = []
    netDict = {"network_ip": "", "gateway_ip": "", "customer_ips": []}
    try:
        for ipv4 in ipv4_dict["ipv4_subnet_list"]:
            network, gateway, *customer_ips = list(ip.ip_network(ipv4, False))
            netDict["network_ip"] = str(network)
            netDict["gateway_ip"] = str(gateway)
            netDict["customer_ips"] = [str(ip) for ip in netDict["customer_ips"] + customer_ips]
    except ValueError as e:
        abort(501, f"Invalid IP address format. Must be a valid IPv4 or IPv6 network. Error: {e}")
    ipv4_dict["ipv4_assignments"].append(netDict)
    return ipv4_dict


def clean_data(**kwargs):
    data = {}
    if "ipv4" in kwargs:
        ipv4_process = ipv4_str_processor(kwargs["ipv4"])  # cleaned ipv4 + ipv4 w/ subnet
        ipv4_length = ipv4_length_validator(ipv4_process)  # length for ip is correct
        ipv4_block = ipv4_block_processor(ipv4_length)  # get default gateway & ips
        data["ipv4"] = ipv4_block
    return data


def unhash_dict(hash_):
    """
    Decrypt python dictionary from base64.

    Takes a base64 hashed string and decodes it to the original object.

    Parameters
    ----------
    hash_: str
        Base64 encoded string.

    Returns
    -------
    dict
        Decoded dictionary object.

    """
    return json.loads(codecs.decode(hash_.encode(), "base64"))


def hash_dict(dict_obj):
    return codecs.encode(json.dumps(dict_obj).encode(), "base64")


def md5_hash(*args):
    """Creates an md5 hash of the given strings.

    Strings are concatentated and then converted to uppercase and then hashed.  If any values given
    are not strings they will be converted to strings.

    Parameters
    ----------
    args: str
        One or more strings to be hashed. The function takes one or more arguments.

    Returns
    -------
    str
        It returns the string formed by hashing the passed arguments.

    """
    return md5("".join(str(x).replace(" ", "") for x in args).upper().encode()).hexdigest()  # noqa: S324


def set_headers(accept="application/json", content_type="application/json", authorization="Bearer ", token=None):
    headers = {"Accept": accept, "Content-Type": content_type}
    if token:
        headers["Authorization"] = authorization + token

    return headers


def is_ip(device_id):
    is_ip = True
    try:
        ip.ip_address(device_id)
    except ValueError:
        is_ip = False
    return is_ip


def flatten_list(nested_list):
    return [item for item_group in nested_list for item in item_group]


def anthropomorphize_the_camel(camel):
    # thanks geeks for geeks
    space_cadet = re.sub("(.)([A-Z][a-z]+)", r"\1 \2", camel)
    return re.sub("([a-z0-9])([A-Z])", r"\1 \2", space_cadet).upper()
