import json
import logging
import re

import requests

import palantir_app
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def ise_calls(base_url, url_path, device_type, device):
    # ISE endpoint supports both json and xml, so we must specify one (json in this case)
    logger.debug("== ise_calls ==")
    header = {"Content-type": "application/json", "Accept": "application/json"}
    try:
        ise_call = requests.get(
            f"{base_url}{url_path}?filter={device_type}.EQ.{device}",
            headers=header,
            verify=False,
            auth=(palantir_app.auth_config.ISE_USER, palantir_app.auth_config.ISE_PASS),
            timeout=30,
        )
        ise_call = json.loads(ise_call.content)
        logger.debug("= ise_call =")
        logger.debug(ise_call)
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        logger.exception("Can't connect to ISE")
        abort(504, "Timed out getting data from ISE")

    return ise_call


def id_lookup(device_type, device):
    logger.debug("== id_lookup ==")
    logger.debug("= device_type =")
    logger.debug(device_type)
    logger.debug("= device =")
    logger.debug(device)
    west_url = palantir_app.url_config.ISE_WEST_URL_PAN11
    east_url = palantir_app.url_config.ISE_EAST_URL_PAN11
    south_url = palantir_app.url_config.ISE_SOUTH_URL_PAN11
    url_path = "/ers/config/networkdevice"

    ise_ids = {}
    results = {}

    if not all((type, device)):
        abort(400, "necessary parameter missing")
    while device_type.lower() not in ["name", "ipaddress"]:
        abort(400, "incorrect type specified, must be either 'hostname' or 'ipaddress'")

    # Run call against all three endpoints, IDs extracted to 'ise_ids', summary data
    # pulled into results, keys are built from the keys in the for call
    summary_data = {
        "west": ise_calls(west_url, url_path, device_type, device),
        "east": ise_calls(east_url, url_path, device_type, device),
        "south": ise_calls(south_url, url_path, device_type, device),
    }
    logger.debug("= summary_data =")
    logger.debug(summary_data)
    for key, data in summary_data.items():
        if data["SearchResult"]["total"] == 0:
            ise_ids[f"{key}_id"] = "none"
            results[f"{key}_result"] = "none"
        else:
            ise_ids[f"{key}_id"] = data["SearchResult"]["resources"][0]["id"]
            results[f"{key}_result"] = data["SearchResult"]["resources"][0]

    logger.debug("= ise_ids =")
    logger.debug(ise_ids)
    logger.debug("= results =")
    logger.debug(results)
    return ise_ids, results


def determine_market(market, extended_market, hostname):
    if extended_market is None or "-" not in extended_market:
        return None, None, None
    ext_market_elements = extended_market.split("-")
    if len(ext_market_elements) >= 2:
        carrier = ext_market_elements[1]
        carrier = carrier.strip().upper()
    else:
        carrier = ""

    if len(ext_market_elements) >= 3:
        market_designation = ext_market_elements[2].strip().upper()
    else:
        market_designation = None

    if market_designation is not None:
        if market_designation == "C":
            # Central Device
            market = ("CENTRAL", "WEST")
            extended_market = "Central"
        elif market_designation == "GL":
            # Central Device
            market = ("GREAT LAKES", "EAST")
            extended_market = "Central"
        elif market_designation == "FL":
            # Florida Device
            market = ("FLORIDA", "EAST")
            extended_market = "Florida"
        elif market_designation == "W":
            # Central Device
            market = ("TEXAS", "WEST")
            extended_market = "Southwest"
        elif market_designation == "SE":
            # Florida Device
            if re.match("^....FL.*", hostname):
                market = ("FLORIDA", "EAST")
                if "BHN" in carrier:
                    extended_market = "Florida-SE"
                else:
                    extended_market = "Florida"
            else:
                market = ("SE", "EAST")
                extended_market = "Southeast"
    return market, extended_market, carrier


def find_location(cedr_market, cedr_extended, tid):
    ny_clli_list = [
        "ARVRNY",
        "ASTRNY",
        "BLRENY",
        "BLRSNY",
        "BRPNNY",
        "BRWDNY",
        "BYSDNY",
        "CBEGNY",
        "CFPKNJ",
        "CLPNNY",
        "CORNNY",
        "CRLSNJ",
        "EDWRNJ",
        "EEMHNY",
        "EMHRNY",
        "ENCLNJ",
        "ENWDNJ",
        "FBRGNJ",
        "FLPKNY",
        "FLSHNY",
        "FRHLNY",
        "FRRKNY",
        "FSMWNY",
        "FTLENJ",
        "GLDLNY",
        "GNKSNY",
        "GTBRNJ",
        "HCKNNJ",
        "HLLSNY",
        "HMPSNY",
        "HWBHNY",
        "INWDNY",
        "JAMCNY",
        "JCHTNY",
        "KWRNNY",
        "LEONNJ",
        "LICYNY",
        "LTFYNJ",
        "LTNCNY",
        "MDVGNY",
        "MHTBNY",
        "MNCHNJ",
        "MSPTNY",
        "MTVRNY",
        "NBRGNJ",
        "NBWKNJ",
        "NWCYNY",
        "NWRKNJ",
        "NWYKNY",
        "NYBKNY",
        "NYBLNY",
        "NYBMNY",
        "NYCANY",
        "NYCBNY",
        "NYCCNY",
        "NYCDNY",
        "NYCENY",
        "NYCFNY",
        "NYCGNY",
        "NYCHNY",
        "NYCINY",
        "NYCJNY",
        "NYCKNY",
        "NYCLNY",
        "NYCMNY",
        "NYCNNY",
        "NYCONY",
        "NYCPNY",
        "NYCQNY",
        "NYCRNY",
        "NYCSNY",
        "NYCTNY",
        "NYCUNY",
        "NYCVNY",
        "NYCWNY",
        "NYCXNY",
        "NYCYNY",
        "NYDANY",
        "NYDBNY",
        "NYDCNY",
        "NYDDNY",
        "NYDENY",
        "NYDFNY",
        "NYDKNY",
        "NYDLNY",
        "NYDRNY",
        "NYDSNY",
        "NYMANY",
        "NYMBNY",
        "NYMDNY",
        "NYMNNY",
        "NYMONY",
        "NYMPNY",
        "NYMQNY",
        "NYMRNY",
        "NYMSNY",
        "NYMTNY",
        "NYMUNY",
        "NYMVNY",
        "NYMWNY",
        "NYMXNY",
        "NYMYNY",
        "NYMZNY",
        "NYQNNY",
        "NYQONY",
        "NYQPNY",
        "NYQQNY",
        "NYQRNY",
        "NYQSNY",
        "NYQTNY",
        "NYQUNY",
        "NYQVNY",
        "ODRNNY",
        "OZPKNY",
        "PLPKNJ",
        "PLVWNY",
        "QNVGNY",
        "RCPKNJ",
        "RDFDNJ",
        "REPKNY",
        "RFPKNJ",
        "RGWDNY",
        "RKBHNY",
        "RKPKNY",
        "RMHLNY",
        "RSDLNY",
        "SHKNNJ",
        "SLRNNY",
        "SNSDNY",
        "SOPKNY",
        "SRHLNY",
        "TTBONJ",
        "VLSTNY",
        "WDHNNY",
        "WDSDNY",
        "WHSTNY",
        "WHWKNJ",
        "WLKLNY",
        "WNYRNJ",
        "WORNNJ",
    ]
    if tid[0:6] in ny_clli_list:
        return "TWC:New York City"

    group_names = {"swm": "Southwest", "pwm": "Pacwest", "mwm": "Midwest", "sem": "Southeast", "nem": "Northeast"}

    if cedr_market.lower() in group_names:
        group = group_names[cedr_market.lower()]
    else:
        group = ""

    market, extended_market, carrier = determine_market(cedr_market, cedr_extended, tid)

    if extended_market:
        return carrier + "-" + extended_market
    else:
        return group
