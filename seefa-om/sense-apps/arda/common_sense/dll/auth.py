import codecs
import hashlib
import json
import logging


logger = logging.getLogger(__name__)


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
    return hashlib.md5(as_str).hexdigest()
