import codecs
import json
import re
import datetime

import palantir_app

from palantir_app.common.constants import SEEFA_DL


def list_sub_dictionaries_by_key(key, dictionary):
    # TODO - Check key for legitimate /w and no special characters, non None
    entries = []
    if isinstance(dictionary, dict):
        content = json.dumps(dictionary)
        # check: is this a key : simple object type (int, string, etc ) Or
        # is this a key : { complex object type }
        complex_cut_pattern = r"(\s*{\s*" + r"\"device\"" + r"\s*:\s*{.*[^}]\s*(,|})\s*)[^" + r"\"device\"]"
        found_list = re.findall(complex_cut_pattern, content)
        if found_list is not None:
            # ok ... it's a complex object ... otherwise assume simple
            residue = r"^\s*(\{*|\}*)\s*$"
            entries = []
            for elements in found_list:
                # elements is a tuple
                entry = "".join(elements)
                x = len(re.findall(residue, entry))
                if x > 0:
                    # this is residue that needs to be fixed in regex ... next entry
                    continue
                else:
                    # count number of left and right braces to form a new dict
                    left_braces = len(re.findall("{", entry))
                    right_braces = len(re.findall("}", entry))
                    truncate = None
                    if left_braces > right_braces:
                        count = left_braces - right_braces
                        while count > 0:
                            entry = entry + r"}"
                            count = count - 1
                        entries.append(json.loads(entry))
                    elif right_braces > left_braces:
                        count = right_braces - left_braces
                        while count > 0:
                            truncate = truncate + r"\s*}\s*"
                            count = count - 1
                        truncate = truncate + r"$"
                        entry = re.sub(truncate, r"", entry)
                        entries.append(json.loads(entry))
                    else:
                        entries.append(json.loads(entry))
        else:
            # for now, assume simple pattern, then
            simple_cut_pattern = r"{\s*device\s*:\s*.*[^{|}]},"
            simple_cut_pattern = key + simple_cut_pattern

        # count the drill-down level using the begin {
        # there are count levels of dictionary to get to the key entry or list
    else:
        return None

    if entries is None:
        return None
    else:
        return entries


def range_max_inclusive(a, b, step=1):
    return range(a + step, b + step)


def range_minmax_inclusive(a, b, step=1):
    return range(a, b + step)


def range_min_inclusive(a, b, step=1):
    return range(a, b)


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


def get_hydra_key(operation="general"):
    """
    Returns string api key
    """
    # general and spirent have different prod/dev keys
    # mne, tid, and ipc have one key for both
    hydra_api_key = {
        "general": palantir_app.auth_config.PALANTIR_GENERAL_HYDRA_KEY,
        "mne": palantir_app.auth_config.PALANTIR_MNE_HYDRA_KEY,
        "tid": palantir_app.auth_config.PALANTIR_TID_HYDRA_KEY,
        "spirent": palantir_app.auth_config.PALANTIR_SPIRENT_HYDRA_KEY,
        "ipc": palantir_app.auth_config.PALANTIR_IPC_HYDRA_KEY,
    }
    if operation not in hydra_api_key.keys():
        operation = "general"
    if operation == "general":
        if palantir_app.app_config.USAGE_DESIGNATION == "PRODUCTION":
            return palantir_app.auth_config.PALANTIR_GENERAL_HYDRA_KEY
        else:
            return palantir_app.auth_config.PALANTIR_HYDRA_STAGIUS_KEY
    return hydra_api_key[operation]


def get_hydra_headers(operation="general", accept_text_html_xml=False):
    headers = {
        "APPLICATION": "SENSE-PALANTIR",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "X-Api-Key": get_hydra_key(operation),
        "X-Requested-With": f"username=SEEFA,useremail={SEEFA_DL},sessionid=SEEFA-Automation,"
        f"exptime={datetime.datetime.now(datetime.timezone.utc)},action=SENSE-Palantir",
    }
    if accept_text_html_xml:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    return headers


def is_ctbh(granite_elements):
    if "CTBH" in str(granite_elements):
        return True
