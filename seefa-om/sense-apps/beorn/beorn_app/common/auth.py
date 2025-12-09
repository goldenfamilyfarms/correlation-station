import codecs
import hashlib
import json
import logging

import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


creds = {"sense": "eyJ1c2VybmFtZSI6ICJzZW5zZV9hcGkiLCAicGFzc3dvcmQiOiAiJGVuJGVfYXBpIn0=\n"}


def unhash_dict(hash_):
    """Decrypt python dictionary from base64 string.
    Commonly used for retrieval of auth from encryption"""
    return json.loads(codecs.decode(hash_.encode(), "base64"))


def hash_dict(dict_obj):
    """Encrypt python dictionary to base64.
    This is the most commonly used for auth storage of plain text"""
    return codecs.encode(json.dumps(dict_obj).encode(), "base64")


def hash_dict_md5(dict_obj):
    """Convert dict to md5 string. One-way hash for IDs, authentication, not storage.
    Commonly used for ID generation"""
    as_str = json.dumps(dict_obj).encode()
    return hashlib.md5(as_str).hexdigest()  # noqa: S324


def get_creds(service):
    """Use service info to unhash and return specific creds.
    Creds will be in {'pw': '', 'un': ''} format unless specified otherwise
    (some may use 'password', 'username', so please check before using)

    example
    my_creds = get_creds('my_service')
    pw, un = my_creds['pw'], my_creds['un']
    """
    _hash = creds[service]
    if isinstance(_hash, bytes):  # be able to handle bytes or string
        _hash = _hash.decode("utf-8")
    return unhash_dict(_hash)


# MDSO information


mdso_creds = {
    "production": "eyJ1c2VybmFtZSI6ICJzZW5zZV9jbGkiLCAicGFzc3dvcmQiOiAiUHl0aG9uUm9ja3MifQ==",
    "stage": "eyJ1c2VybmFtZSI6ICJhZG1pbiIsICJwYXNzd29yZCI6ICJhZG1pbnB3In0=",
}


# SNMP Community String
snmp_comm_str_hash = "eyJjb21tX3N0cmluZyI6ICJONGNTRGdXUFU5NzNRWGc2TWpSNSJ9"
snmp_pub_str_hash = "eyJjb21tX3N0cmluZyI6ICJwdWJsaWMifQ=="
snmp_decrypt = unhash_dict(snmp_comm_str_hash)
snmp_pub_decrypt = unhash_dict(snmp_pub_str_hash)

snmp_comm_str = snmp_decrypt["comm_string"]
snmp_pub_str = snmp_pub_decrypt["comm_string"]
