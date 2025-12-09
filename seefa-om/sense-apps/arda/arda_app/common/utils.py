# Flake8: noqa: E402
import re
import logging
import warnings

warnings.simplefilter("ignore", UserWarning)

from urllib import parse
from thefuzz import fuzz
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def find_best_match(options, original, primary_key):
    """Do levenshtien matching to find closest match in a dictionary"""
    logger.info("find best match started")
    best_match = (0, {})

    for option in options:
        opk = option[primary_key]

        if opk == original:
            best_match = (0, option)
            break

        distance = fuzz.ratio(opk, original)

        if 92 < distance > best_match[0]:
            best_match = distance, option

    if best_match[1]:
        res = f"Would have retried using this address: {best_match[1]}"
        logger.error(res)
        return (500, res)

    res = f"Did not find a close match for {original}"
    logger.error(res)
    return (500, res)


def find_fuzzy_matches(options, original, primary_key, cj=True):
    """Do fuzzy wuzzy matching to find closest multiple matches in a dictionary, in case of variations on
    punctuation, etc."""
    # use set token ratio and partial ratio, then use whichever ends up being highest!
    best_partial_match = (0, [])
    best_set_token_match = (0, [])
    maurice_ratio = (0, [])
    suggested_percent = 80 if cj else 70

    partial_distance = 40
    token_distance = 40
    distance_by_words = 40

    for option in options:
        # fixing None type error sense bug
        if option.get("clean_name", "") is None:
            option["clean_name"] = ""

        if len(option.get("clean_name").split()) > 1:
            clean_option = option[primary_key]
            partial_distance = fuzz.partial_ratio(clean_option, original)
            token_distance = fuzz.token_set_ratio(clean_option, original)
            distance_by_words = words_alone(clean_option, original)

            if suggested_percent < partial_distance >= best_partial_match[0]:
                if partial_distance == best_partial_match[0]:
                    best_partial_match[1].append(option)
                else:
                    best_partial_match = partial_distance, [option]

            if suggested_percent < token_distance >= best_set_token_match[0]:
                if token_distance == best_set_token_match[0]:
                    best_set_token_match[1].append(option)
                else:
                    best_set_token_match = token_distance, [option]

            if 3 <= distance_by_words >= maurice_ratio[0]:
                if distance_by_words == maurice_ratio[0]:
                    maurice_ratio[1].append(option)
                else:
                    maurice_ratio = distance_by_words, [option]

    if best_partial_match[1] or best_set_token_match[1]:
        if best_partial_match[0] >= best_set_token_match[0]:
            return best_partial_match[1], best_partial_match[0], "best_partial"

        return best_set_token_match[1], best_set_token_match[0], "best_set"
    elif maurice_ratio[1]:
        return (maurice_ratio[1], maurice_ratio[0], "maurice_ratio")
    elif not cj:
        cj_percent = max(distance_by_words, token_distance, partial_distance)

        if distance_by_words == 0:
            cj_percent = 39

        return None, cj_percent, "No CJ"

    return None, 0, "CJ"


def find_similar_names(options, original, cj=True):
    matches = []
    suggested_percent = 88 if cj else 70
    percentage = 0
    cj_percent = 41

    for option in options:
        clean_distance = fuzz.ratio(option["clean_name"], original)
        siteid_distance = fuzz.ratio(option.get("siteId"), original)

        if clean_distance >= suggested_percent or siteid_distance >= suggested_percent:
            matches.append(option)
        elif not cj:
            cj_percent = max(clean_distance, siteid_distance)

            if cj_percent > percentage:
                percentage = cj_percent

    return matches, percentage


def words_alone(option, original):
    word_match_count = 0
    words = original.strip().split()

    for word in words:
        if bool(word) and word in option:
            word_match_count += 1

    return word_match_count


def validate_required_parameters(required_parameters, given_data, data_name="data"):
    logger.debug(f"Input data - {given_data}")
    missing_site_data = [x for x in required_parameters if x not in given_data.keys() or not given_data[x]]

    if missing_site_data:
        abort(500, f"Missing the following required {data_name} - {', '.join(missing_site_data)}")


def get_bandwidth_in_mbps(bw_type, bw_value):
    if bw_type.lower() == "mbps":
        bandwidth_in_mbps = float(bw_value)
    elif bw_type.lower() == "gbps":
        bandwidth_in_mbps = float(bw_value) * 1000
    else:
        abort(500, "invalid bandwidth_type - must be Mbps or Gbps.")

    return bandwidth_in_mbps


def bandwidth_in_bps(bw_value: str, bw_type: str) -> float:
    """bw_value like '20' and bw_type like 'Mbps'"""
    if bw_type.lower() == "mbps":
        return float(bw_value) * 1_000_000
    elif bw_type.lower() == "gbps":
        return float(bw_value) * 1_000_000_000
    else:
        abort(500, "invalid bw_type - must be Mbps or Gbps")


def convert_bandwidth(bw_type, bw_value, mtu, ct="LC"):
    bandwidth_in_mbps = get_bandwidth_in_mbps(bw_type, bw_value)

    if bandwidth_in_mbps <= 1000 and not mtu:
        bandwidth_string = "1 Gbps"
        optic = "GE"

        if ct == "SC":
            card_template = "GENERIC SFP LEVEL 1 SC"
        else:  # LC
            card_template = "GENERIC SFP LEVEL 1"
    else:
        bandwidth_string = "10 Gbps"
        optic = "XE"
        card_template = "GENERIC SFP+ LEVEL 1"

    return bandwidth_string, optic, card_template


def create_bw_string(bw_type, bw_value):
    bandwidth = ""

    if bw_type == "gbps":
        if int(bw_value) > 1:
            bandwidth = "10 Gbps"
        else:
            bandwidth = "1 Gbps"
    elif bw_type == "mbps":
        if (int(bw_value) / 1000) > 1:
            bandwidth = "10 Gbps"
        else:
            bandwidth = "1 Gbps"

    return bandwidth


def path_regex_match(string: str, match_type: str = "cid") -> list:
    """Regex findall() on a string for CIDs (default) or match_type = "path_name" (to include transports)
    Return a list of all matches"""
    cid_regex = r"(\d{2}\.[A-Z0-9]{4}\.\d{6}\.[A-Z0-9]{0,3}\.[TWCC|CHTR]{4})"
    path_regex = (
        r"(\d{2}\.[A-Z0-9]{4}\.\d{6}\.[A-Z0-9]{0,3}\.[TWCC|CHTR]{4}|\d{5}\.[A-Z0-9]{3,5}\.[A-Z0-9]{11}\.[A-Z0-9]{11})"
    )
    string = string.upper()

    if match_type == "cid":
        return re.findall(cid_regex, string)
    elif match_type == "path_name":
        return re.findall(path_regex, string)


def sanitize_site_string(site_name):
    """Use urllib to sanitize strings before building a requests URL"""
    return parse.quote(site_name)
