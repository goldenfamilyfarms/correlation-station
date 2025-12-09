import logging
import string
from urllib.parse import quote

from arda_app.bll.cid.cid_globals import (
    ABBREVIATIONS,
    BAD_UNITS,
    BAD_WORDS,
    CTBH_ABBREVIATIONS,
    LOCAL,
    NON_LOCAL,
    ROOM_TYPES,
    MTU,
)
from arda_app.bll.cid.lata_codes import LATA_CODES
from arda_app.common.cd_utils import granite_siteCustomers_put_url, granite_sites_put_url, granite_paths_url
from common_sense.common.errors import abort
from arda_app.dll.denodo import get_npa_three_digits
from arda_app.common.utils import find_best_match, find_fuzzy_matches, find_similar_names
from arda_app.dll.granite import (
    get_granite,
    get_result_as_list,
    get_sites,
    post_granite,
    put_granite,
    get_circuit_site_info,
)
from arda_app.bll.cid.customer import clean_billing_name

logger = logging.getLogger(__name__)


def find_or_create_a_site_v5(site_data):
    site_data["name"] = clean_billing_name(site_data)
    site_data["clean_name"] = clean_up_name(site_data["name"])
    return_data = {"created new site": False}

    if is_type_II(site_data) is True:
        site_data["type"] = "CUST_OFFNET"

    att_check(site_data)

    if is_ctbh(site_data) is True:
        site_data["type"] = "CELL"
        site = get_ctbh_cell_sites(site_data)
    elif site_data.get("related_circuit_id"):
        site = get_site_by_related_CID(site_data["related_circuit_id"])
    elif site_data.get("enni"):
        site = get_site_by_enni(site_data["enni"])
    else:
        sites = get_sites_v3(site_data)
        site = validate_site_records_v4(site_data, sites) if sites else None

    if site:
        site_clli_check(site.get("siteName", ""), site.get("clli", ""))

        if site.get("zip1"):
            update_existing_site_npaxx(site)

        find_or_create_building(site_data, site)
    else:
        site = create_site_v4(site_data)
        find_or_create_building(site_data, site, new_site=True)
        return_data["created new site"] = True

    return_data["siteName"] = site["siteName"]
    return_data["clli"] = site["clli"]
    return_data["lat"] = site.get("latitude")
    return_data["lon"] = site.get("longitude")

    return return_data


def site_clli_check(sitename, clli):
    # this checks length of clli and aborts if its not equal to 8
    if len(clli) != 8:
        msg = f"The CLLI: {clli} is not equal to 8 characters. Please investigate site {sitename}"
        logger.error(msg)
        abort(500, msg)


def update_existing_site_npaxx(site):
    logger.info("Update existing site NPAXX.")
    update_params = {}
    update_params["SITE_NAME"] = site["siteName"]
    update_params["SITE_TYPE"] = site["siteType"]
    update_params["SITE_NPA_NXX"] = get_npa_three_digits(site["zip1"])

    logger.info(f"Updating site - {update_params}")
    url = granite_sites_put_url()
    put_granite(url, update_params, timeout=90)


def att_check(site_data):
    logger.info("ATT check.")
    pnoi = site_data.get("product_name_order_info", "").upper()

    if site_data.get("clean_name", "").startswith("ATT ") and pnoi == "CARRIER CTBH":
        if not site_data.get("fixed_access_code") or not site_data.get("lata_code"):
            logger.error("ATT site missing fixed_access_code or lata_code.")


def update_site_parent(site):
    update_parameters = {"SITE_NAME": site["name"], "SITE_TYPE": site["type"], "SITE_PARENT": site["parent"]}
    logger.info(f"Updating site parent - {update_parameters}")
    url = granite_sites_put_url()
    put_granite(url, update_parameters, timeout=90)


def update_existing_bldg_site(site):
    """Make the updates to an existing building site in one call"""
    update_params = {}
    update_params["SITE_NAME"] = site["siteName"]
    update_params["SITE_TYPE"] = "BUILDING"
    logger.info(f"Updating building site - {update_params}")
    url = granite_sites_put_url()
    put_granite(url, update_params, timeout=90)


def update_existing_site(provided_site, record):
    """Make the updates to an existing site in one call instead of a bunch"""
    logger.info("Update existing site.")
    update_params = {}

    if "gemBuildingKeyUda" not in record and "gems_key" in provided_site:
        update_params["UDA"] = {"BUILDING DETAILS": {"GEMS BUILDING KEY": provided_site["gems_key"]}}

    if record.get("status") and record["status"] not in ("Auto-Planned", "Designed", "Live", "Planned"):
        update_params["SITE_STATUS"] = "Planned"

    if "RingCentral" in provided_site["product_family"]:
        update_params["SITE_STATUS"] = "Live"

    if record["siteType"] in LOCAL and provided_site.get("customer"):
        if not record.get("customerRec_id") or (
            provided_site["sf_id"] != record["customerRec_id"]
            and provided_site["sf_id"] != record.get("sfUniqueCustomerId_UDA")
        ):
            update_params["SITE_CUST"] = provided_site["customer"].upper()

    if update_params:
        update_params["SITE_NAME"] = record["siteName"]
        update_params["SITE_TYPE"] = record["siteType"]
        logger.info(f"Updating site - {update_params}")
        url = granite_sites_put_url()
        put_granite(url, update_params, timeout=90)


def saint_cities(original_address, given_address):
    logger.info("Update saint cities.")
    abbreviations = {"FORT": "FT", "MOUNT": "MT", "MOUNTAIN": "MT", "SAINT": "ST"}
    original_address = original_address.upper()
    given_address = given_address.upper()

    for k, v in abbreviations.items():
        if k in original_address:
            if original_address.replace(k, v) == given_address:
                return k, v
            elif original_address.replace(v, k) == given_address:
                return v, k

    return False


def parse_site_error(error, site, building=False, payload=None):
    logger.info("parse site error")
    original_address = f"{site['address']}, {site['city']}, {site['state']} {site['zip_code']}"

    if "Not a valid address. iConnective LocateIt found a similar address:" in error:
        address = error.split("\n")[-1]
        abbreviations = saint_cities(original_address, address)

        if abbreviations:
            site["city"] = site["city"].upper().replace(abbreviations[0], abbreviations[1])

            return create_site_v4(site, building)
        else:
            find_best_match([{"address": address}], original_address, "address")
    elif "Duplicate Site Address info found" in error:
        # addresses look like this:
        # - 4515 SETON CENTER TRAVIS 78759 -- 4515 SETON CENTER PKWY TRAVIS 78759 -
        # This has county name instead of city
        addresses = []

        for address in error.split("\n")[-1][2:-2].split(" -- "):
            if site["zip_code"] in address:
                # THIS ASSUMES THE ZIP CODE PROVIDED IS MORE CORRECT THAN STREET ADDRESS
                street_line = " ".join(address.split()[:-2])
                # TODO THIS ASSUMES THE COUNTY IS ONLY ONE WORD. PHYSICAL LOOK UP WOULD BE BETTER.
                # TODO ALSO, IF WE RETRIED WITH THE INFO PROVIDED, WE'D BE SUBMITTING THE COUNTY AS THE CITY???
                addresses.append({"address": street_line, "complete address": address})

        find_best_match(addresses, site["address"], "address")
    elif "Multiple site addresses matched" in error:
        # addresses look like this:
        # n1.null, MT WHITTIER MOTEL//1695 ROUTE 16, Planned, LOCAL, 43.787266, -71.172284,
        # 1695 STATE HWY 16, CENTER OSSIPEE, 03814, NH, USA\n-------End of Site Address-------
        # TODO THE SITES PROVIDED HAVE A LAT/LONG - PHYSICAL LOOKUP WOULD BE USEFUL
        # TODO INSTEAD OF CREATING A NEW SITE, WOULD A MATCH MEAN THAT WE SHOULD BE USING THAT EXISTING SITE?
        addresses_block = error.split("address below and try again")[-1]
        addresses = addresses_block.replace("\n", "").strip().split("-------End of Site Address------- ")
        clean_addresses = []

        for a in addresses:
            a = a.split(", ")
            clean_addresses.append({"address": f"{a[6]}, {a[7]}, {a[9]} {a[8]}", "complete address": ", ".join(a[6:9])})

        find_best_match(clean_addresses, original_address, "address")

    abort(500, f"{error.get('retString', '<error retString not found>')} - for payload: {payload}")


def abbreviate(astring, address=False):
    astring = astring.upper().strip()

    # turn '9 th street' into '9th street'
    address_words = astring.split()
    slices = []
    sliver = []

    for i, word in enumerate(address_words):
        if word in ("ST", "ND", "RD", "TH") and i != 0 and address_words[i - 1].isnumeric():
            slices.append(" ".join(sliver))
            sliver = [word]
        else:
            sliver.append(word)

    slices.append(" ".join(sliver))
    astring = "".join(slices)

    if address:
        return abbreviate_address(astring)

    if "UNITED STATES" in astring:
        astring = astring.replace("UNITED STATES", "US")
    elif "FARM TO MARKET" in astring:
        astring = astring.replace("FARM TO MARKET", "FM")

    # turn '9th street' into '9th st'
    abbreviated_address = []

    for word in astring.split():
        if word in ABBREVIATIONS:
            abbreviated_address.append(ABBREVIATIONS[word])
        else:
            abbreviated_address.append(word)

    return " ".join(abbreviated_address)


def abbreviate_address(a):
    address_words = a.split()
    address_word = address_words[-1]
    abb = abbreviate(address_word)

    return a.replace(address_word, abb)


def loop_through_pages(url, original_site):
    """As we go through pagination, make a list of sites that match on address"""
    logger.info("Loop through address match results.")
    address = cleanup_address(original_site["address"])
    page = 1
    records = 1000
    sites = []

    if "CELL" in url:
        records = 100

    results = get_granite(f"{url}&PAGE_NBR={page}&RECORDS={records}", retry=2)

    while len(results) > 0 and isinstance(results, list):
        page += 1
        address_matches = []

        # Limit search results to just those with a matching address
        for x in results:
            if address == abbreviate(x["address"]) or address == abbreviate(x.get("siteName", "").split("/")[-1]):
                if x["siteType"] != "BUILDING":
                    if check_unit_match(original_site, x["siteName"]) is True:
                        stripped_name = x["siteName"].split("/")[0][9:]
                        x["clean_name"] = clean_up_name(stripped_name)
                        address_matches.append(x)
                else:
                    address_matches.append(x)

        # Remove records that don't have a site type to prevent key errors since we use site type as a criteria
        sites.extend([x for x in address_matches if x.get("siteType")])
        results = get_granite(f"{url}&PAGE_NBR={page}&RECORDS={records}", retry=2)

    return sites


def cleanup_address(address):
    logger.info("Cleanup address.")
    address = abbreviate(address)
    address = rem_punc(address)

    for i in ROOM_TYPES:
        if f" {i} " in address:
            new_address = address.split(i)[0].strip()

            if new_address:
                return new_address

    return address


def match_on_account_id_or_name(sf_id, clean_name, site):
    """If there is a match on service request name AND/OR account id, return True"""

    if site.get("customerRec_id"):
        if site.get("sfUniqueCustomerId_UDA") and site["sfUniqueCustomerId_UDA"] == sf_id:
            return True

    if site.get("siteName"):
        if site["clean_name"] == clean_name.upper():
            return True

    if site.get("siteId"):
        if site["siteId"] == clean_name.upper():
            return True

    return False


def sort_out_multiple_candidates_v2(sites, clean_name, provided_name):
    """
    if there's one local site that matches on name live or not, use it
    if there's a live local site with name match, use it
    if there's one non_local site, use it
    else return none
    """
    logger.info("Sort out multiple candidates.")

    local_sites = [x for x in sites if x["siteType"].upper() in LOCAL]
    non_local_sites = [x for x in sites if x["siteType"].upper() in NON_LOCAL]
    local_sites_with_name_matches = [x for x in local_sites if x["clean_name"] in (clean_name, provided_name)]
    local_live_sites = [x for x in local_sites if x["status"] == "Live"]

    if len(local_sites_with_name_matches) == 1:
        return local_sites_with_name_matches[0]
    elif len(local_live_sites) == 1:
        return local_live_sites[0]
    elif len(non_local_sites) == 1:
        return non_local_sites[0]


def is_ctbh(site):
    logger.info("Check if site is CTBH.")
    return "ctbh" in site.get("product_family", "").lower()


def is_carrier(site):
    logger.info("Check if site is carrier.")
    return "carrier" in site.get("product_family", "").lower()


def is_type_II(site):
    logger.info("Check if site is type II.")

    if site.get("third_party_provided_circuit"):
        return site.get("third_party_provided_circuit", "").upper() == "TRUE"

    return "(TYPE II)" in site["product_name_order_info"].upper() or "OFF-NET" in site["parent"].upper()


def validate_site_records_v4(provided_site, records, building_search=False):
    """Same as validate_site_records_v3 except it looks for a 90% local match before going to the FUZZ"""
    logger.info("Validating the site records.")

    clean_records = add_clean_names(records)
    records = remove_dukenet_sites(clean_records)

    non_local_records = [x for x in records if x["siteType"].upper() in NON_LOCAL and x["status"] == "Live"]

    local_records = [x for x in records if x["siteType"].upper() in LOCAL]
    mtu = [x for x in records if x["siteType"].upper() in MTU]
    carrier = is_ctbh(provided_site) or is_carrier(provided_site)

    sites = []
    cj = provided_site.get("construction_job_number", False)

    # moving above 40% threshold
    percent = 41

    if len(non_local_records) > 1:
        abort(500, "Multiple COLO/POP records at this address.")
    elif provided_site["type"] == "CELL":
        cell_sites = [x for x in records if x["siteType"].upper() == "CELL" and x["status"] == "Live"]

        for c in cell_sites:
            if c.get("clean_name") == provided_site["name"] or c.get("clean_name") == ctbh_customer_abbreviations(
                provided_site["name"]
            ):
                sites.append(c)
    elif carrier:
        similar_names, percent = find_similar_names(local_records, provided_site["clean_name"], cj)

        if len(similar_names) == 1 and not non_local_records:
            sites.append(similar_names[0])
        elif len(similar_names) > 1 and not non_local_records:
            multi_sim = [x["siteName"] for x in similar_names]
            abort(500, f"Found multiple similarly named sites - {multi_sim}")
    elif building_search:
        sites = [x for x in records if x["siteType"].upper() == "BUILDING"]
    else:  # none building_search:
        sites = non_local_records

        logger.info("Match on account id or name started.")

        for site in local_records:
            if match_on_account_id_or_name(provided_site["sf_id"], provided_site["clean_name"], site):
                sites.append(site)

        if (not len(sites) or len(sites) > 1) and len(local_records):
            sites = local_records
            matches, percent, method = find_fuzzy_matches(sites, provided_site["clean_name"], "clean_name", cj)

            if matches:
                # remove sites that got matched on more than once (it's a carrier thing mostly)
                unique_matches = []

                for match in matches:
                    if match["siteName"] not in [x["siteName"] for x in unique_matches]:
                        unique_matches.append(match)

                unique_names = [x["siteName"] for x in matches]

                if len(unique_matches) > 1:
                    # checking if any site matches the provided unit before aborting
                    unreal_matches = []
                    if provided_site.get("room"):
                        sf_room, _ = clean_unit_v3(provided_site["room"], "")

                        for cust_site in unique_matches:
                            unit = cust_site["siteName"].split("/")[1]

                            if unit:
                                granite_room, _ = clean_unit_v3(unit, "")

                                if sf_room == granite_room:
                                    unreal_matches.append(cust_site)

                        if len(unreal_matches) == 1:
                            return unreal_matches[0]

                    abort(500, f"More than one site tied as a good match - {', '.join(unique_names)}")
                elif len(unique_matches) == 1 and isinstance(percent, int):
                    match_percent = 90 if cj else 79

                    if percent >= match_percent:
                        return matches[0]

                    abort(
                        500,
                        f"Instead of creating a new site, found potential match (less than {match_percent}%) "
                        f"site: {unique_names[0]} - used {method} at {percent}%",
                    )
            else:
                sites = non_local_records
        else:
            # changing percent when no matching sites and no local sites at address
            percent = 39

    if len(sites) == 1:
        return sites[0]
    elif len(sites) > 1:
        if building_search or provided_site["type"] == "CELL":
            msg = "Multiple potential buildings or CELL site matches"
            logger.error(msg)
            abort(500, msg)

        best_site = sort_out_multiple_candidates_v2(sites, provided_site["clean_name"], provided_site["name"])

        if best_site:
            return best_site
    # added to fallout for colo sites but no existing customer site
    elif not building_search and len(non_local_records):
        msg = "Found COLO site, but no local customer site."
        logger.error(msg)
        abort(500, msg)

    # checking percentage to create new site
    if cj or building_search or mtu or percent < 40:
        return

    # abort if no construction job
    msg = "No CJ on order and no existing customer site found. Please investigate"
    logger.error(msg)
    abort(500, msg)


def get_sites_v3(provided_site):
    """Search by street number + state."""
    logger.info(f"Get sites: {provided_site}")
    street_number = quote(f"{provided_site['address'].split()[0]} %")
    site_url = granite_siteCustomers_put_url()
    url = f"{site_url}?ADDRESS={street_number}&STATE_PROV={provided_site['state']}&CUST-ID={provided_site['customer']}"

    return loop_through_pages(url, provided_site)


def get_site_by_enni(enni):
    logger.info(f"Get site by enni: {enni}")
    path_url = f"/circuitSites?CIRCUIT_NAME={enni}&PATH_CLASS=P"
    results = get_result_as_list(f"{path_url}", timeout=60, retry=2)

    if len(results) == 1:
        return {
            "created new site": False,
            "siteName": results[0]["A_SITE_NAME"],
            "siteType": results[0]["A_SITE_TYPE"],
            "clli": results[0]["A_CLLI"],
            "latitude": results[0]["A_LATITUDE"],
            "longitude": results[0]["A_LONGITUDE"],
        }
    elif len(results) > 1:
        for x in results:
            if x["CIRCUIT_STATUS"] == "Live":
                return {
                    "created new site": False,
                    "siteName": x["A_SITE_NAME"],
                    "siteType": x["A_SITE_TYPE"],
                    "clli": x["A_CLLI"],
                    "latitude": x["A_LATITUDE"],
                    "longitude": x["A_LONGITUDE"],
                }

    abort(500, "Could not find site by ENNI.")


def get_site_by_related_CID(related_cid):
    logger.info(f"Get site by related CID: {related_cid}")
    path_url = f"/circuitSites?CIRCUIT_NAME={related_cid}&PATH_CLASS=P"
    results = get_result_as_list(f"{path_url}", timeout=60, retry=2)

    if len(results) == 1:
        return {
            "created new site": False,
            "siteName": results[0]["Z_SITE_NAME"],
            "siteType": results[0]["Z_SITE_TYPE"],
            "clli": results[0]["Z_CLLI"],
            "latitude": results[0]["Z_LATITUDE"],
            "longitude": results[0]["Z_LONGITUDE"],
        }
    elif len(results) > 1:
        for x in results:
            if x["CIRCUIT_STATUS"] == "Live":
                return {
                    "created new site": False,
                    "siteName": x["Z_SITE_NAME"],
                    "siteType": x["Z_SITE_TYPE"],
                    "clli": x["Z_CLLI"],
                    "latitude": x["Z_LATITUDE"],
                    "longitude": x["Z_LONGITUDE"],
                }

    abort(500, "Could not find site by related CID.")


def get_site_by_enni_for_circuitpath(enni, is_ctbh=False):
    logger.info(f"Get site by enni for circuitpath: {enni}")
    path_url = f"/circuitSites?CIRCUIT_NAME={enni}&PATH_CLASS=P"
    results = get_result_as_list(f"{path_url}", timeout=60, retry=2)

    if len(results) == 1:
        return {"siteName": results[0]["A_SITE_NAME"], "zipcode": results[0]["A_ZIP"]}
    elif len(results) > 1:
        for x in results:
            if x["CIRCUIT_STATUS"] == "Live":
                return {"siteName": x["A_SITE_NAME"], "zipcode": x["A_ZIP"]}
    elif is_ctbh:
        return

    abort(500, "Could not find site by ENNI.")


def clean_unit_v3(unit, given_floor):
    """Clean unit and floor"""
    if not unit and not given_floor:
        return "", ""

    floor_words = ("FLR", "FLOOR", "FL")
    special_characters = f"{string.punctuation} "  # do not remove the extra space
    combined = BAD_UNITS + ROOM_TYPES + floor_words + tuple(special_characters)

    room = floor = ""
    unit_has_floor = floor_has_rm = ""

    def split_assign(ufparam):
        for char in special_characters:
            if char in ufparam:
                split_list = ufparam.split(char)
                break
        else:
            split_list = ufparam.split()

        len_sp_lst = len(split_list)

        if len_sp_lst == 2:
            if any(x for x in floor_words if x in split_list[0]):
                return split_list[1], split_list[0]
            elif any(x for x in ROOM_TYPES if x in split_list[0]):
                return split_list[0], split_list[1]
        elif len_sp_lst == 3:
            if split_list[1] in ROOM_TYPES:
                return "".join(split_list[1:]), split_list[0]
            elif split_list[1] in floor_words:
                return split_list[0], "".join(split_list[1:])
            elif split_list[0] in floor_words and split_list[1]:
                return split_list[2], "".join(split_list[:2])
            elif split_list[0] in ROOM_TYPES and split_list[1]:
                return "".join(split_list[:2]), split_list[2]
        elif len_sp_lst == 4:
            if split_list[0] in floor_words and split_list[1]:
                return "".join(split_list[2:]), "".join(split_list[:2])
            elif split_list[0] in ROOM_TYPES and split_list[1]:
                return "".join(split_list[:2]), "".join(split_list[2:])

        return "", ""

    if unit:
        unit = unit.upper().strip()
        unit_has_floor = any(x for x in floor_words if x in unit)
        unit_has_both = unit_has_floor and any(x for x in ROOM_TYPES if x in unit)

        if unit_has_both:
            unit, given_floor = split_assign(unit)
            unit_has_floor = False

    if given_floor:
        given_floor = given_floor.upper().strip()
        floor_has_rm = any(x for x in ROOM_TYPES if x in given_floor)
        floor_has_both = floor_has_rm and any(x for x in floor_words if x in given_floor)

        if floor_has_both:
            unit, given_floor = split_assign(given_floor)
            floor_has_rm = False

    if unit and unit_has_floor:
        if given_floor:
            given_floor, unit = unit, given_floor
        else:
            given_floor, unit = unit, None

    def parse_str(astring):
        "Removing combined words from string"

        for x in combined:
            if x in astring:
                astring = astring.replace(x, "")

        return astring

    if unit:
        room = parse_str(unit)

    if given_floor:
        floor = parse_str(given_floor)

    return room, floor


def create_site_v4(site, building=False):
    """Create a site and then parse the error"""
    logger.info("Create Site started.")

    if building:
        room = ""
        floor = ""
    else:
        room, floor = clean_unit_v3(site.get("room"), site.get("floor"))

    name = (
        ctbh_customer_abbreviations(site["clean_name"]) if "CELL" in site["type"] else clean_up_name(site["clean_name"])
    )
    address = take_room_info_from_name(site["address"])

    if not address:
        msg = f"Site address unsupported: {site['address']}"
        logger.error(msg)
        abort(500, msg)

    # will fallout for sitenames that will be greater than 100 characters granite field restiction
    if len(name) + len(room) + len(address) > 89:
        msg = "The length of the granite sitename will be greater than the 100 character limit."
        logger.error(msg)
        abort(500, msg)

    update_parameters = {
        "SITE_NAME": f"{name}/{room if room else ''}/{address}" if not building else site["name"][:91],
        "SITE_LATITUDE": "" if not site.get("lat") else site["lat"][:20],
        "SITE_LONGITUDE": "" if not site.get("lon") else site["lon"][:20],
        "SITE_CLLI": "" if not site.get("clli") else site["clli"][:50],
        "SITE_NPA_NXX": get_npa_three_digits(site["zip_code"]),
        "SITE_PARENT": site["parent"][:100],
        "SITE_TYPE": site["type"].upper()[:30] if not building else "BUILDING",
        "SITE_ROOM": "" if not room else room[:40],
        "SITE_FLOOR": "" if not floor else floor[:40],
        "SITE_ADDRESS": abbreviate(address, True)[:4000],
        "SITE_CITY": abbreviate(site["city"][:60]),
        "SITE_STATE_PROV": site["state"][:40],
        "SITE_POST_CODE_1": site["zip_code"][:10],
        "SITE_COUNTRY": "USA",
        "SITE_STATUS": "Planned",
    }

    if "RingCentral" in site["product_family"]:
        update_parameters["SITE_STATUS"] = "Live"

    if not building:
        if site.get("customer"):
            update_parameters["SITE_CUST"] = site.get("customer") or site["name"]
    else:
        update_parameters["SITE_COUNTRY"] = site["country"]

        if site["county"]:
            update_parameters["SITE_COUNTY"] = site["county"]

    if site.get("gems_key"):
        update_parameters["UDA"] = {"BUILDING DETAILS": {"GEMS BUILDING KEY": site["gems_key"]}}

    if site.get("lata_code"):
        latanum = site["lata_code"]
        lata = f"{latanum}-{LATA_CODES[latanum]}"

        try:
            if update_parameters["UDA"]:
                update_parameters["UDA"]["ADDITIONAL LOCATION INFO"] = {
                    "FIXED ASSET (FA) CODE": site["fixed_access_code"],
                    "LATA": lata,
                }
        except KeyError:
            update_parameters["UDA"] = {
                "ADDITIONAL LOCATION INFO": {"FIXED ASSET (FA) CODE": site.get("fixed_access_code"), "LATA": lata}
            }

    logger.info(f"Creating {'building ' if building else ''}site - {update_parameters}")
    url = granite_sites_put_url()
    r = post_granite(url, update_parameters, timeout=60, return_resp=True)

    if r.status_code != 200:
        logger.error(
            f"Granite responded with code {r.status_code} "
            f"creating a site - {r.json().get('retString', '<error retString not found>')}"
            f": {update_parameters}"
        )

        return parse_site_error(r.json(), site, building, payload=update_parameters)

    return r.json()


def ctbh_customer_abbreviations(name):
    logger.info("Update customer abbreviations.")

    if name in CTBH_ABBREVIATIONS.keys():
        return CTBH_ABBREVIATIONS[name]

    return name


def take_room_info_from_name(name):
    words = name.split()

    for i, word in enumerate(words):
        if word.upper() in ROOM_TYPES:
            return " ".join(words[:i])

    return name


def find_or_create_building(site_data, site, new_site=False):
    logger.info("Find or create Building.")
    url = f"/sites?SITE_HUM_ID={quote(site['siteName'])}"
    site_record = get_result_as_list(url, retry=2)

    if len(site_record) != 1:
        abort(500, "Something went wrong looking up the site in Granite")

    try:
        url = f"/sites?CLLI={site_record[0]['clli']}&SITE_TYPE=BUILDING"
    except KeyError:
        logger.error("Created site missing CLLI")
        abort(500, "Created site missing CLLI, unable to create building site")

    sites = get_result_as_list(url, retry=2)
    site["parent_site"] = site_record[0]["parent_site"] if site_record[0].get("parent_site") else site_data.get("parent")
    building = validate_site_records_v4(site_data, sites, building_search=True)

    if not building:
        building = get_building(site["clli"])

    if building:
        update_site_with_building(site_data, site, building, new_site)
    elif new_site is True:
        create_building(site_data, site, site_record, new_site=True)
    elif new_site is False and site["parent_site"].upper() not in ("BUILDING", "MTU"):
        create_building(site_data, site, site_record)


def get_building(site_clli):
    logger.info("Get Building.")
    sites = get_sites(site_clli)

    for site in sites:
        if site["siteName"] == site_clli:
            if site["siteType"] == "BUILDING":
                return site
            else:
                update_existing_bldg_site(site)
                return site


def create_building(site_data, site, site_record, new_site=False):
    logger.info("Create Building.")

    # create building
    building_data = site_data.copy()
    building_data["room"] = ""
    building_extras = {
        "clli": site["clli"],
        "name": site["clli"],
        "lat": site.get("latitude"),
        "lon": site.get("longitude"),
        "county": site_record[0].get("county"),
        "country": site_record[0].get("country"),
    }
    building_data.update(building_extras)
    building = create_site_v4(building_data, building=True)
    update_site_with_building(site_data, site, building, new_site)

    return building


def update_site_with_building(site_data, site, building, new_site=False):
    logger.info("Update site with building.")
    site_data["parent"] = building["siteName"]
    site_data["name"] = site["siteName"]

    if new_site:
        update_site_parent(site_data)
    else:
        site_data["type"] = site["siteType"]

        if not site.get("parent_site"):
            update_site_parent(site_data)
        elif site["parent_site"] and "MTU" not in site["parent_site"]:
            update_site_parent(site_data)

        update_existing_site(site_data, site)


def remove_dukenet_sites(records):
    logger.info("Remove dukenet sites.")

    records = [x for x in records if "dukenet" not in x["siteName"].lower()]

    return records


def create_mtu_site(site):
    """Create an MTU site and then parse the error"""
    logger.info("Create MTU Site.")
    update_parameters = {
        "SITE_NAME": site["name"][:90],
        "SITE_CLLI": site["site_clli"][:8],
        "SITE_LATITUDE": "" if not site.get("lat") else site.get("lat")[:20],
        "SITE_LONGITUDE": "" if not site.get("lon") else site.get("lon")[:20],
        "SITE_NPA_NXX": get_npa_three_digits(site["zip_code"]),
        "SITE_PARENT": site["parent"][:100],
        "SITE_TYPE": site["type"].upper()[:30],
        "SITE_ADDRESS": abbreviate(site["address"])[:4000],
        "SITE_CITY": abbreviate(site["city"])[:60],
        "SITE_STATE_PROV": site["state"][:40],
        "SITE_POST_CODE_1": site["zip_code"][:10],
        "SITE_COUNTRY": "USA",
        "SITE_STATUS": "Planned",
        "UDA": {"BUILDING DETAILS": {"GEMS BUILDING KEY": site["gems_key"], "BUILDING MTU": "ACTIVE MTU PRESENT"}},
    }

    logger.info(f"Creating MTU site - {update_parameters}")
    url = granite_sites_put_url()
    r = post_granite(url, update_parameters, timeout=60, return_resp=True)

    if r.status_code != 200:
        logger.error(
            f"Granite responded with code {r.status_code} "
            f"creating a site - {r.json().get('retString', '<error retString not found>')}"
        )
        return parse_site_error(r.json(), site, payload=update_parameters)

    return r.json()


def find_mtu_site(clli):
    logger.info(f"Find MTU site: {clli}")
    sites = get_sites(clli)
    mtu_exists = False

    try:
        for i in range(len(sites)):
            if sites[i]["siteType"] == "ACTIVE MTU":
                mtu_exists = True
                break

        return mtu_exists
    except (KeyError, IndexError):
        abort(500, f"No sites found for hub CLLI: {clli}")


def get_ctbh_cell_sites(provided_site):
    provided_site["clean_name"] = clean_up_name(provided_site["name"])
    customer = (
        ctbh_customer_abbreviations(provided_site["customer"])
        if provided_site.get("customer")
        else ctbh_customer_abbreviations(provided_site["clean_name"])
    )

    """Search by street number + state for only CELL sites"""
    street_number = quote(f"{provided_site['address'].split()[0]} %")
    site_url = granite_sites_put_url()
    url = f"{site_url}?ADDRESS={street_number}&STATE_PROV={provided_site['state']}&SITE_TYPE=CELL"
    sites = loop_through_pages(url, provided_site)

    # Adding clean name to existing sites to compare
    sites = add_clean_names(sites)

    for site in sites:
        clean_name = site.get("clean_name", "")

        if customer in clean_name or provided_site["clean_name"] in clean_name:
            return site


def add_clean_names(sites):
    for site in sites:
        if not site.get("clean_name"):
            clean_site = site["siteName"]

            if "/" in clean_site:
                clean_site = clean_site.split("/")[0].split("-", 1)[-1]

            site["clean_name"] = clean_up_name(clean_site)

    return sites


def check_unit_match(site, site_name):
    logger.info(f"check unit match: {site_name}")

    if "-MTU" in site_name or "_MTU" in site_name:
        return True

    if site_name.count("/") == 1:
        site_name = site_name.replace("/", "//")

    try:
        unit = site_name.split("/")[1]
    except IndexError:
        unit = None

    room = site.get("room", "")

    # check unit if salesforce payload and existing site both have unit/room info
    if room and unit:
        rm, fl = clean_unit_v3(room, "")

        if fl:
            return True

        return unit == rm

    # if no salesforce room in payload and granite unit exist
    # if salesforce has room info payload and granite unit does not exist
    # returns true if no room in site and no unit in sitename
    return True


def clean_up_name(name):
    if not name:
        return

    name = name.upper()
    cleaner = ""

    for i in name:
        if i.isalnum():
            cleaner += i
        elif i in "&":  # keeping for customer names that need them
            cleaner += i
        elif i in "'.":  # Removing characters and replacing with no space
            cleaner += ""
        else:  # adding space
            cleaner += " "

    name_words = cleaner.split()
    last_word = name_words[-1]
    last_2_words = " ".join(name_words[-2:])
    last_3_words = " ".join(name_words[-3:])

    if last_3_words == "DEDICATED INTERNET SERVICE":
        name_words = name_words[:-3]
    elif last_2_words in ("PARENT ACCOUNT", "NT L", "NATIONAL ACCOUNT", "NATIONAL FIA"):
        name_words = name_words[:-2]
    elif last_word in BAD_WORDS:
        name_words.pop()

    return " ".join(name_words)


def rem_punc(astring):
    sp = string.punctuation

    # remove the dash and slash from string punctuation
    sp = sp.replace("-", "")
    sp = sp.replace("/", "")

    # removes all the punc from string except list above and joins back together
    return " ".join(astring.translate(str.maketrans("", "", sp)).split())


def rel_site_name_main(payload):
    """Getting sitename of the request cid and
    updating the product/service if product family is Secure Dedicated Internet

    input:
    related_circuit_id
    product_family(optional)

    output:
    z_site_name
    or
    abort

    """
    related_circuit_id = payload.get("related_circuit_id")
    product_family = payload.get("product_family")

    return_data = {}

    response = get_circuit_site_info(related_circuit_id)

    if isinstance(response, dict):
        msg = f"No records found with related cid: {related_circuit_id}"
        logger.error(msg)
        abort(500, msg)
    elif product_family == "Secure Dedicated Internet":
        # updating Product servcie and service media in granite for Secure Internet
        url = granite_paths_url()

        put_payload = {
            "PATH_NAME": related_circuit_id,
            "PATH_INST_ID": response[0]["CIRC_PATH_INST_ID"],
            "UDA": {"SERVICE TYPE": {"PRODUCT/SERVICE": "CUS-SECURE INTERNET ACCESS", "SERVICE MEDIA": "FIBER"}},
        }

        resp = put_granite(url, put_payload)

        if resp.get("retString") != "Path Updated":
            msg = "Error updating Product/Service and/or Service media in granite"
            logger.error(msg)
            abort(500, msg)

    return_data["siteName"] = response[0]["Z_SITE_NAME"]

    return return_data
