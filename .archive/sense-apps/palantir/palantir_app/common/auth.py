import codecs
import json
import logging
import urllib3
from hashlib import md5

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


# Some Encryptions Used Have Platform Dependency
server_type = None


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
    """
    Encrypt python dictionary to base64.

    Takes a dictionary object and encodes it suing base64 hashing.

    Parameters
    ----------
    dict_obj: dict
        Dictionary object to be encoded.

    Returns
    str
        Base64 hashed string .

    """
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


# MDSO information

mdso_creds = {
    "production": "eyJ1c2VybmFtZSI6ICJzZW5zZV9jbGkiLCAicGFzc3dvcmQiOiAiUHl0aG9uUm9ja3MifQ==",
    "stage": "eyJ1c2VybmFtZSI6ICJhZG1pbiIsICJwYXNzd29yZCI6ICJhZG1pbnB3In0=",
}


# ise information
ise_creds = "eyJ1c2VybmFtZSI6ICJvc3MiLCAicGFzc3dvcmQiOiAiVG1yZ2txNlAyVzZQIn0="

ise_decrypt = unhash_dict(ise_creds)

ise_usr = ise_decrypt["username"]
ise_pwd = ise_decrypt["password"]

# ca spectrum

ca_creds = "eyJ1c2VybmFtZSI6ICJtdWxlc29mdCIsICJwYXNzd29yZCI6ICJtdWxlc29mdHBhc3N3b3JkIn0="

ca_decrypt = unhash_dict(ca_creds)

ca_usr = ca_decrypt["username"]
ca_pwd = ca_decrypt["password"]


# IPC auths

# Dev IPC
# ipc_creds = "eyJ1c2VybmFtZSI6ICJtdWxlc29mdCIsICJwYXNzd29yZCI6ICJ6YXExQFdTWCJ9"

# Prod IPC
ipc_creds = "eyJ1c2VybmFtZSI6ICJzdmMtc2Vuc2UtYXBpIiwgInBhc3N3b3JkIjogIjQ3d3NEcFV2dzN0THg4RCJ9"

ipc_decrypt = unhash_dict(ipc_creds)

ipc_usr = ipc_decrypt["username"]
ipc_pass = ipc_decrypt["password"]

# AWS SMTP Creds
email_creds = "eyJ1c2VybmFtZSI6ICJBS0lBNVA1R0Q3R1pKT1RIQUxPWCIsICJwYXNzd29yZCI6ICJCT1RXeGxk\n\
    YnMrSTJocGJCdmtxNXVlNDVLc2ZjSHB1cnRxcjlRZm45a1hERyIsICJlbWFpbF9zZXJ2ZXIiOiAi\nZW1haWwtc210c\
    C51cy1lYXN0LTEuYW1hem9uYXdzLmNvbSIsICJlbWFpbF9wb3J0IjogNTg3fQ==\n"
email_decrypt = unhash_dict(email_creds)

# Salesforce Creds
sf_auth = (
    "eyJlbWFpbCI6ICJkbC1zZWVvLWF1dG9tYXRpb25AY2hhcnRlci5jb"
    "20uZW9tIiwgInBhc3N3b3Jk\nIjogIkt0djl1aSN6NFRnclFMOCIsICJ0b2"
    "tlbiI6ICJzOFFZd043eURQUG9pMWJjaGR6NE96VnUi\nfQ==\n"
)
sf_decrypt = unhash_dict(sf_auth)


# SNMP Community String
snmp_comm_str_hash = "eyJjb21tX3N0cmluZyI6ICJONGNTRGdXUFU5NzNRWGc2TWpSNSJ9"
snmp_pub_str_hash = "eyJjb21tX3N0cmluZyI6ICJwdWJsaWMifQ=="
snmp_decrypt = unhash_dict(snmp_comm_str_hash)
snmp_pub_decrypt = unhash_dict(snmp_pub_str_hash)

snmp_comm_str = snmp_decrypt["comm_string"]
snmp_pub_str = snmp_pub_decrypt["comm_string"]
