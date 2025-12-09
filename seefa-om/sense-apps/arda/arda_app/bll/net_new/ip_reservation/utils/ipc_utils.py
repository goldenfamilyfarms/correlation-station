import ipaddress
from arda_app.bll.net_new.ip_reservation.utils.mdso_utils import obtain_pe_bgp_asn, obtain_pe_isis_area
from common_sense.common.errors import abort
from arda_app.dll.mdso import onboard_and_exe_cmd
from arda_app.dll.ipc import get_container_by_block
from arda_app.dll.granite import get_granite
from arda_app.common.cd_utils import get_circuit_site_url
import logging

logger = logging.getLogger(__name__)


def existing_fia_container_method(mx, attempt_onboarding):
    """Get the container of an existing FIA on the MX"""
    mdso_response = onboard_and_exe_cmd(command="get_all_interfaces", hostname=mx, attempt_onboarding=attempt_onboarding)
    fia_address_on_mx = _get_fia_address(mdso_response["result"]["configuration"]["interfaces"])

    if not fia_address_on_mx:
        raise Exception(f"Unable to obtain an existing FIA on the MX: {mx}")

    ip_network = ipaddress.ip_interface(fia_address_on_mx).network
    return get_container_by_block(ip_network)


def _get_fia_address(interfaces):
    """From the MDSO return of all MX interfaces, return the first FIA block found on an AGG interface"""
    for k, v in interfaces.items():
        if "ae" in k and v.get("unit"):
            for subinterface in v["unit"]:
                if _is_valid_fia(subinterface):
                    try:
                        if isinstance(subinterface["family"]["inet"]["address"], list):
                            return subinterface["family"]["inet"]["address"][0]["name"]
                        else:
                            return subinterface["family"]["inet"]["address"]["name"]
                    except Exception:
                        logger.info("Unable to find FIA address")
    return None


def _is_valid_fia(subint):
    if (
        1100 <= int(subint.get("name", "0")) <= 1399
        and "FIA" in subint.get("description", "")
        and "SPIRENT" not in subint.get("description", "").upper()
    ):
        return True

    return False


def edna_asn_container_lookup(asn, legacy_network, state_code, tid):
    l_network = (
        "LCHTR"
        if legacy_network == "L-CHTR"
        else "LTWC"
        if legacy_network == "L-TWC"
        else "LBHN"
        if legacy_network == "L-BHN"
        else ""
    )

    if not l_network:
        abort(500, f"Unable to use legacy network: {legacy_network}")

    if asn == "20001" and state_code == "HI":
        return "/Commercial/LTWC/West/Hawaii/Customer"
    elif asn == "20115":
        if state_code == "AL":
            if l_network == "LCHTR":
                return "/Commercial/LCHTR/GA-AL-TN-SC-NC/Alabama/Customer"
            else:
                return "/Commercial/LBHN/Birmingham/Customer"

        if state_code == "GA":
            return "/Commercial/LCHTR/GA-AL-TN-SC-NC/Georgia/Customer"

        if state_code == "TN":
            return "/Commercial/LCHTR/GA-AL-TN-SC-NC/Tennessee/Customer"

        abort(500, f"Unmapped state code {state_code} for ASN 20115")
    elif asn == "33363":
        url = get_circuit_site_url(f"%{tid}%", full_info=False)
        res = get_granite(url)

        if isinstance(res, list):
            city = res[0]["A_CITY"]

            if city == "TAMPA":
                return "/Commercial/LBHN/TampaBay/Customer"
            else:
                return "/Commercial/LBHN/CentralFL/Customer"
        else:
            abort(500, f"No paths found for TID: {tid}")

    containers = {
        "7843": "/Commercial/LTWC/NDC/TW-Backbone/Customer",
        "10796": "/Commercial/LTWC/Midwest/Customer",
        "10838": "/Commercial/LTWC/Northwest/Customer",
        "11351": "/Commercial/LTWC/Northeast/Customer",
        "11426": "/Commercial/LTWC/Carolinas/Customer",
        "11427": "/Commercial/LTWC/Texas/Customer",
        "11955": "/Commercial/LTWC/NDC/TW-Dothan/Customer",
        "12271": "/Commercial/LTWC/NYC/Customer",
        "20001": [
            "/Commercial/LTWC/West/Customer",
            "/Commercial/LTWC/West/Hawaii/Customer",
            "/Commercial/LCHTR/SoCal/Customer",
        ],
        "20115": [
            "/Commercial/LCHTR/GA-AL-TN-SC-NC/Alabama/Customer",
            "/Commercial/LCHTR/GA-AL-TN-SC-NC/Georgia/Customer",
            "/Commercial/LCHTR/GA-AL-TN-SC-NC/Tennessee/Customer",
            "/Commercial/LBHN/Birmingham/Customer",
        ],
        "20231": [
            "/Commercial/LTWC/Texas/KansasCity/Customer",
            "/Commercial/LTWC/Texas/Lincoln/Customer",
            "/Commercial/LCHTR/Nebraska/Customer",
        ],
        "22513": "/Commercial/LCHTR/Northwest/Customer",
        "22516": ["/Commercial/LCHTR/SanLuisObispo/Customer", "/Commercial/LBHN/Bakersfield/Customer"],
        "22677": "/Commercial/LCHTR/Central/Customer",
        "22710": "/Commercial/LCHTR/Louisiana/Customer",
        "22974": ["/Commercial/LBHN/Detroit/Customer", "/Commercial/LCHTR/Michigan/Customer"],
        "23132": "/Commercial/LCHTR/NewEngland/Customer",
        "23200": "/Commercial/LBHN/Indianapolis/Customer",
        "23222": "/Commercial/LCHTR/Nevada/Customer",
        "33363": ["/Commercial/LBHN/CentralFL/Customer", "/Commercial/LBHN/TampaBay/Customer"],
        "33588": ["/Commercial/LTWC/West/Mountain/Customer", "/Commercial/LCHTR/MountainStates/Customer"],
        "40264": ["/Commercial/LTWC/Midwest/Wisconsin/Customer", "/Commercial/LCHTR/WI-MN/Customer"],
        "65200": "/Commercial/LTWC/NDC/TW-Backbone/Customer",
    }

    container = containers.get(asn)
    if not container:
        abort(500, f"Unmapped ASN found: {asn}")
    elif isinstance(container, list):
        for sub_container in container:
            if l_network in sub_container:
                return sub_container

        abort(500, f"No valid combination for ASN: {asn} and legacy network: {l_network} for TID: {tid}")

    return container


def map_ipc_container_from_isis(cid, pe, attempt_onboarding):
    """Map the proper IPC container to be used for Static IP assignment based on IS-IS Area ID"""

    # Obtain the IS-IS Area
    isis_area = obtain_pe_isis_area(cid, pe, attempt_onboarding)

    nested_map_1850 = {
        "AL": "/Commercial/LCHTR/GA-AL-TN-SC-NC/Alabama/Customer",
        "GA": "/Commercial/LCHTR/GA-AL-TN-SC-NC/Georgia/Customer",
        "NC": "/Commercial/LCHTR/GA-AL-TN-SC-NC/Customer",
        "SC": "/Commercial/LCHTR/GA-AL-TN-SC-NC/Customer",
        "TN": "/Commercial/LCHTR/GA-AL-TN-SC-NC/Tennessee/Customer",
        "VA": "/Commercial/LCHTR/GA-AL-TN-SC-NC/Customer",
    }

    # IS-IS area values and corresponding IPC paths
    isis_map = {
        "0001": "/Commercial/LCHTR/Central/Customer",
        "0425": "/Commercial/LCHTR/WI-MN/Customer",  # 60.L2XX.009964..CHTR
        "0650": "/Commercial/LCHTR/Michigan/Customer",
        "1850": nested_map_1850,
        "1900": "/Commercial/LCHTR/Nevada/Customer",
        "2200": "/Commercial/LCHTR/SoCal/Customer",
        "2225": "/Commercial/LCHTR/SanLuisObispo/Customer",
        "2250": "/Commercial/LCHTR/Northwest/Customer",
        "2400": "/Commercial/LCHTR/Texas/Customer",
        "2500": "/Commercial/LCHTR/Nebraska/Customer",  # 40.L1XX.993744..CHTR
        "2302": "/Commercial/LCHTR/MountainStates/Customer",
        "2303": "/Commercial/LCHTR/MountainStates/Customer",
        "2304": "/Commercial/LCHTR/MountainStates/Customer",
        "2397": "/Commercial/LCHTR/MountainStates/Customer",
        "2398": "/Commercial/LCHTR/MountainStates/Customer",
        "2399": "/Commercial/LCHTR/MountainStates/Customer",
        "2ca2": nested_map_1850,
        "3000": "/Commercial/LCHTR/Louisiana/Customer",
        "7590": "/Commercial/LCHTR/WI-MN/Customer",
        "7790": "/Commercial/LCHTR/Texas/Customer",
        "8350": "/Commercial/LCHTR/NewEngland/Customer",
    }

    ipc_path = isis_map.get(isis_area)

    if isis_area in ("1850", "2ca2"):
        ipc_path = ipc_path.get(pe[4:6])  # Grabs the state abbreviation from pe for use in 1850

    # if not ipc_path and isis_area and isis_area.isdigit() and 2299 < int(isis_area) < 2400:
    #     ipc_path = isis_map.get("2399")  # All 23xx - "/Commercial/LCHTR/MountainStates/Customer"

    if ipc_path is None:
        abort(
            501,
            (f"isis area {isis_area} does not have an associated mapping folder for ipc that is currently supported"),
        )

    return ipc_path


def map_ipc_container_from_bgp(cid, pe):
    """Determine appropriate IPC Container to use based on BGP AS number"""

    # For exception mappings we will need to use the CLLI Code as well as ASN
    pe_clli = pe[0:7]

    # Obtain the IS-IS Area
    bgp_as = obtain_pe_bgp_asn(cid, pe)

    # ASNs which map directly to an IPC container
    bgp_direct_maps = {
        "10838": "/Commercial/LTWC/Northwest/Customer",
        "11351": "/Commercial/LTWC/Northeast/Customer",
        "11426": "/Commercial/LTWC/Carolinas/Customer",
        "11955": "/Commercial/LTWC/NDC/TW-Dothan/Customer",
        "12271": "/Commercial/LTWC/NYC/Customer",
    }

    # ASNs which map to more than one IPC container and need additional processing
    bgp_multi_maps = ["10796", "11427", "20001"]

    ipc_path = None

    if pe_clli in ["RPLYTNCK", "BEREKY24"]:
        ipc_path = "/Commercial/LTWC/Midwest/Customer"

    if pe_clli == "SGRTNY13":
        ipc_path = "/Commercial/LTWC/NYC/Customer"

    for i in bgp_direct_maps.items():
        if bgp_as == i[0] and pe_clli == "SGRTNY13":
            ipc_path = "/Commercial/LTWC/NYC/Customer"
        elif bgp_as == i[0] and pe_clli != "SGRTNY13":
            ipc_path = i[0]
        else:
            continue
    else:
        if bgp_as in bgp_multi_maps:
            if pe_clli in ["RPLYTNCK", "BEREKY24"]:
                ipc_path = "/Commercial/LTWC/Midwest/Customer"
            else:
                return False

    if pe_clli in ["PTVLCA03", "TRLCCACO"]:
        isis_area = "2255"
        ipc_path = bgp_direct_maps.get(isis_area)
    elif pe_clli == "DAVLVTAD":
        isis_area = "8350"
        ipc_path = bgp_direct_maps.get(isis_area)

    return ipc_path
