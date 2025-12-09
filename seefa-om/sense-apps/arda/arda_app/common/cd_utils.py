import logging

from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite

logger = logging.getLogger(__name__)


def region_network_mapping(region, state, a_clli=None, z_clli=None, legacy=None):
    """Find cloud address by a_site_region and a_state values from circuit_site response values from Granite"""
    """ Reminder that f"%{a_site_region}%" is an option for more flexible mapping
    also, reminder that post-mvp this may need to be done dynamically with granite solution """

    # Hawaii is a special case
    if state in "HI":
        return "CHTRSE.CEN.HAWAII.MPLS"

    region_map = {
        "CAROLINAS": "CHTRSE.CEN.CAROLINAS.MPLS",
        "CENTRAL": "CHTRSE.CEN.CENTRAL STATES.MPLS",
        "FLORIDA": "CHTRSE.CEN.FLORIDA.MPLS",
        "GREAT LAKES": "CHTRSE.CEN.GREAT LAKES.MPLS",
        "NYC": "CHTRSE.CEN.NYC.MPLS",
        "NEW YORK CITY": "CHTRSE.CEN.NYC.MPLS",
        "NORTHEAST": "CHTRSE.CEN.NORTHEAST.MPLS",
        "NORTHWEST": "CHTRSE.CEN.NORTHWEST.MPLS",
        "SOUTH": "CHTRSE.CEN.SOUTH.MPLS",
        "SO OHIO": "CHTRSE.CEN.SOUTHERN OHIO.MPLS",
        "TEXAS": "CHTRSE.CEN.TEXAS.MPLS",
        "WEST": "CHTRSE.CEN.WEST.MPLS",
        "OHIO": "MID.CEN.MPLS",
        "EAST": "CHTRSE.CEN.CAROLINAS.MPLS",
        "MIDSOUTH": "CHTRSE.CEN.CAROLINAS.MPLS",
        "MIDWEST": "MID.CEN.MPLS",
        "NORTH CENTRAL": "MID.CEN.MPLS",
        "SOUTH CENTRAL": "MID.CEN.MPLS",
        "SOUTHEAST": ["CHTRSE.CEN.FLORIDA.MPLS", "CHTRSE.CEN.SOUTH.MPLS"],
        "TEXAS-LOUISIANA": "CHTRSE.CEN.TEXAS.MPLS",
    }

    legacy_charter_region_map = {
        "AL": "LEGACY_CHARTER.ALABAMA.MPLS",
        "IL": "LEGACY_CHARTER.CENTRAL_STATES.MPLS",
        "MO": "LEGACY_CHARTER.CENTRAL_STATES.MPLS",
        "GA": "LEGACY_CHARTER.GEORGIA.MPLS",
        "LA": "LEGACY_CHARTER.LOUISIANA.MPLS",
        "MA": "LEGACY_CHARTER.MASSACHUSETTS.MPLS",
        "MI": "LEGACY_CHARTER.MICHIGAN.MPLS",
        "MN": "LEGACY_CHARTER.MINNESOTA_NEBRASKA.MPLS",
        "WA": "LEGACY_CHARTER.MOUNTAIN_STATES.MPLS",
        "CO": "LEGACY_CHARTER.MOUNTAIN_STATES.MPLS",
        "MT": "LEGACY_CHARTER.MOUNTAIN_STATES.MPLS",
        "NY": "LEGACY_CHARTER.NEW YORK.MPLS",
        "CT": "LEGACY_CHARTER.NEW_ENGLAND.MPLS",
        "NC": "LEGACY_CHARTER.NORTH CAROLINA.MPLS",
        "OR": "LEGACY_CHARTER.OREGON.MPLS",
        "NV": "LEGACY_CHARTER.SIERRA_NEVADA.MPLS",
        "CA": "LEGACY_CHARTER.SOCAL.MPLS",
        "SC": "LEGACY_CHARTER.SOUTH_CAROLINA.MPLS",
        "TN": "LEGACY_CHARTER.TENNESSEE.MPLS",
        "TX": "LEGACY_CHARTER.TEXAS.MPLS",
        "VT": "LEGACY_CHARTER.VERMONT.MPLS",
        "VA": "LEGACY_CHARTER.VIRGINIA.MPLS",
        "WI": "LEGACY_CHARTER.WISCONSIN..000001.MPLS",
        "WY": "LEGACY_CHARTER.MOUNTAIN_STATES.MPLS",
    }

    if legacy == "L-CHTR":
        try:
            return legacy_charter_region_map[state]
        except (KeyError, TypeError):
            logger.exception(f"Error attempting to determine legacy region for parent network assignment using {state}")
            abort(500, f"Error attempting to determine legacy region for parent network assignment using {state}")

    # These CLLIs are considered to be in NYC region, not Northeast
    hudson_valley_cllis = [
        "LBRTNY15",
        "MTGMNYAR",
        "MNTINY02",
        "RHNBNY10",
        "NWBRNYCX",
        "HIFLNYAE",
        "SGRTNY13",
        "ULPKNY01",
        "PGHKNY09",
        "MMKTNYAF",
        "SCTWNY01",
    ]
    if a_clli in hudson_valley_cllis or z_clli in hudson_valley_cllis:
        region = "NYC"

    result = None
    try:
        result = region_map[region]
        if region == "SOUTHEAST":
            if state == "FL":
                result = result[0]  # for CHTRSE.CEN.FLORIDA.MPLS
            else:
                result = result[1]  # for CHTRSE.CEN.SOUTH.MPLS

    except (KeyError, TypeError):
        logger.exception(f"Error attempting to determine region for parent network assignment using {region}")
        abort(500, f"Error attempting to determine region for parent network assignment using {region}")

    return result


def validate_values(collection_to_check, expected_values: list):
    """Pass a collection and a separate list of expected values and this function will return whether or not the
    collection contains all expected values, handing you back a list of missing values. If you pass it a dictionary
    to check, it will look for the expected values in the keys."""
    # TODO: add strict parameter to determine whether or not 'None' value is added to missing
    # TODO: consider calling as cu.validate_values() to show it's a util in-line
    if isinstance(collection_to_check, list):
        missing_vals = []
        for i in expected_values:
            if i not in collection_to_check:
                missing_vals.append(i)
        if missing_vals:
            return missing_vals

    if isinstance(collection_to_check, dict):
        missing_vals = []
        for i in expected_values:
            try:
                collection_to_check[i]
            except KeyError:
                missing_vals.append(i)
        if missing_vals:
            return missing_vals


def validate_hub_clli(clli):
    """Pass a CLLI code; Returns True and reason str if CLLI is valid, else False and a reason string."""

    hub_clli_map = {
        "CLEVETND": "CLEVTNDL",
        "CLEVTN21": "CLEVTNDL",
        "Clevtn21": "CLEVTNDL",
        "MASSLHTE": "MSSLMTEH",
        "MONTEREY": "MTPKCACG",
        "MRFDWI00": "MRFDWI23",
        "OPLSACO": "OPLSLACO",
        "OPLSLA": "OPLSLACO",
        "RENOQNVL": "RENQNVLX",
        "STPTWI04": "STPTWIBX",
        "WTMAWI00": "WTMAWIBY",
        "WWSTSWIJ": "WWTSWIJL",
        "IRA_NY01": "IRA NY01",
        "LEE_MA04": "LEE MA04",
    }
    clli = clli[:8]
    if clli in hub_clli_map:
        clli = hub_clli_map.get(clli, None)

    # Assume the worst
    valid = False
    msg = f'Unsupported CLLI "{clli}" detected in path: '
    if clli is not None and not isinstance(clli, str):
        msg += "invalid hub CLLI code type"
    elif clli is None or clli == "":
        msg += "empty hub CLLI code"
    elif len(clli) != 8:
        msg += "hub CLLI code must be 8 characters"
    else:
        # Hey! we passed!
        valid = True
        msg = "good CLLI"

    return valid, msg


def will_transport_be_oversubscribed(transport: str, needed_bw: float) -> bool:
    """Check if the needed_bw (in bits per second) + the current transport utilization will oversubscribe the path.
    Return True if the transport will be oversubscribed"""
    url = granite_pathUtil_get_url(transport)
    resp = get_granite(url)
    if isinstance(resp, dict):
        abort(500, f"Unexpected response from /pathUtilization for {transport}")
    available_bw = float(resp[0].get("AVAILABLE_BW"))

    if available_bw > needed_bw:
        return False
    return True


def get_l1_url(cid):
    return f"/pathElements?CIRC_PATH_HUM_ID={cid}&LVL=1"


def get_l2_url(cid):
    return f"/pathElements?CIRC_PATH_HUM_ID={cid}&LVL=2"


def get_pathelements_url(cid):
    return f"/pathElements?CIRC_PATH_HUM_ID={cid}"


def get_circuit_site_url(cid, path_class="P", full_info=True):
    """Parses the appropriate URL to use for circuit_site_info with either 'P' (path) or 'N' (network) params
    also may use full_info=False to add a wildcard argument to search more broadly"""
    url = f"/circuitSites?CIRCUIT_NAME={cid}&PATH_CLASS={path_class}"
    if not full_info:
        url += "&WILD_CARD_FLAG=1"
    return url


def get_l1_port_url(cid):
    return f"/pathElements?CIRC_PATH_HUM_ID={cid}&ELEMENT_TYPE=PORT&LVL=1"


def get_l1_port_inst_url(inst_id):
    return f"/pathElements?CIRC_PATH_INST_ID={inst_id}&ELEMENT_TYPE=PORT&LVL=1"


def get_l2_cw_port_url(cid):
    return f"/pathElements?CIRC_PATH_HUM_ID={cid}&ELEMENT_NAME=CW/&LVL=2&wildCardFlag=1"


def granite_paths_get_url(pathid):
    return f"/paths?CIRC_PATH_HUM_ID={pathid}"


def granite_uda_get_url(inst_id):
    return f"/circuitUDAs?CIRC_PATH_INST_ID={inst_id}"


def granite_parent_mgd_get_url(inst_id):
    return f"/parentManagedServices?CIRC_PATH_INST_ID={inst_id}"


def granite_amos_url():
    return "/amos"


def granite_amoUDAs_url(name):
    return f"/amoUDAs?NAME={name}"


def granite_pathUtil_get_url(transport_path):
    return f"/pathUtilization?CIRC_PATH_HUM_ID={transport_path}"


def granite_paths_url():
    return "/paths"


def granite_ports_put_url():
    return "/ports"


def granite_customer_update_url():
    return "/updateCustomer"


def granite_cards_url():
    return "/cards"


def granite_shelves_post_url():
    return "/shelves"


def granite_customers_url():
    return "/customers"


def granite_customersRest_get_url():
    return "/customersRest"


def granite_sites_put_url():
    return "/sites"


def granite_siteCustomers_put_url():
    return "/siteCustomers"


def granite_equipments_url():
    return "/equipments"


def granite_get_siteUDAs_url(param=""):
    """required param is either SITE_INST_ID or SITE_NAME"""
    return f"/siteUDAs?{param}"


def granite_networks_url():
    return "/networks"


def granite_mne_url(inst_id):
    return f"/parentManagedServices?CIRC_PATH_INST_ID={inst_id}"
