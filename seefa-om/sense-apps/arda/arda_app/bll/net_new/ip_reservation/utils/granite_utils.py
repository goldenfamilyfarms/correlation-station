import logging
from arda_app.bll.net_new.ip_reservation.ip_models import MPSCloudModel

from common_sense.common.errors import abort
from arda_app.bll.net_new.ip_reservation.utils.ipc_utils import (
    edna_asn_container_lookup,
    existing_fia_container_method,
    map_ipc_container_from_bgp,
    map_ipc_container_from_isis,
)
from arda_app.bll.circuit_design.bh_mapping import map_ipc_container_for_bh
from arda_app.common.cd_utils import (
    validate_values,
    get_circuit_site_url,
    granite_paths_url,
    get_pathelements_url,
    granite_get_siteUDAs_url,
)
from arda_app.dll.granite import get_granite, put_granite
from arda_app.dll.mdso import onboard_and_exe_cmd, get_mx_asn


logger = logging.getLogger(__name__)


def get_circuit_info_and_map_legacy(cid, attempt_onboarding):
    """Call path elements from granite and return circuit information."""
    # get the path elements circuit data from granite
    url = get_pathelements_url(cid)
    path_elements_resp = get_granite(url)

    if isinstance(path_elements_resp, dict) and path_elements_resp.get("retString"):
        abort(500, path_elements_resp["retString"])
    path_elements_lvl1 = [element for element in path_elements_resp if element["LVL"] == "1"]
    # path_elements_lvl2 = [element for element in path_elements_resp if element["LVL"] == "2"]

    mpls_cloud = MPSCloudModel(**path_elements_lvl1[0])

    if not mpls_cloud.customer_name or not mpls_cloud.customer_id:
        abort(500, "Circuit ordering customer should not be empty")

    # get mx for ip assignment
    mx, mx_legacy_network, state_code = _get_mx_info(url, path_elements_resp)

    logger.info(f"Successfully obtained required circuit info for {cid}")
    return {
        "mx": mx,
        "ipc_path": _get_ipc_path(mx, mx_legacy_network, mpls_cloud, state_code, cid, attempt_onboarding),
        "customer_name": mpls_cloud.customer_name,
        "customer_id": mpls_cloud.customer_id,
        "leg_name": mpls_cloud.leg_name,
        "path_name": mpls_cloud.path_name,
        "path_rev": mpls_cloud.path_rev,
    }


def _get_mx_info(url: str, path_elements_resp: list) -> tuple:
    """get mx for ip assignment"""
    mx = ""
    state_code = ""
    mx_legacy_network = ""
    mx_site_name = ""
    for elem in path_elements_resp:
        if elem["ELEMENT_CATEGORY"] == "ROUTER" and elem["ELEMENT_TYPE"] == "PORT" and elem["TID"].endswith("CW"):
            mx = elem["TID"]
            mx_legacy_network = elem["LEGACY_EQUIP_SOURCE"]
            state_code = mx[4:6]
            mx_site_name = elem["PATH_Z_SITE"]
            break
    if not mx:
        abort(500, "No hub router ending in 'CW' found in path elements")
    if not mx_legacy_network:
        url = granite_get_siteUDAs_url(f"SITE_NAME={mx_site_name}")
        res = get_granite(url)
        if isinstance(res, list):
            for uda in res:
                if uda.get("GROUP_NAME") == "LEGACY_SITE" and uda.get("ATTR_NAME") == "SOURCE":
                    mx_legacy_network = uda.get("ATTR_VALUE")
                    break

    return mx, mx_legacy_network, state_code


def _get_ipc_path(
    mx: str, mx_legacy_network: str, mpls_cloud: MPSCloudModel, state_code: str, cid: str, attempt_onboarding: bool
) -> str:
    """IP Control container lookup based on the MX router and the legacy network of the circuit."""
    ipc_path = ""
    try:
        # Based on ASN if EDNA migrated L-CHTR
        edna_migrated = onboard_and_exe_cmd(command="is_edna", hostname=mx, attempt_onboarding=attempt_onboarding)
        edna_migrated = (
            edna_migrated["result"] if isinstance(edna_migrated, dict) and edna_migrated.get("result") else ""
        )
        if edna_migrated:
            asn = get_mx_asn(mx)
            if not asn:
                abort(500, message="Unable to obtain the ASN of the MX")
            else:
                ipc_path = edna_asn_container_lookup(asn, mx_legacy_network, state_code, mx)
        else:
            logger.error("Unable to determine IPC container based on EDNA status")
            raise Exception("Unable to determine IPC container based on EDNA status")
    except Exception:
        try:
            # Based on existing FIA on the MX
            ipc_path = existing_fia_container_method(mx, attempt_onboarding)
        except Exception as e:
            logger.error(f"Unable to determine container based on existing FIA due to error: {e}")
            # Based on legacy container determination logic
            if mx_legacy_network == "L-TWC":
                parent_mpls = mpls_cloud.element_name
                ipc_path = _map_ipc_container_from_mpls(cid, parent_mpls)
            elif mx_legacy_network == "L-CHTR":
                ipc_path = map_ipc_container_from_isis(cid, mx, attempt_onboarding)
                if not ipc_path:
                    ipc_path = map_ipc_container_from_bgp(cid, mx)
            elif mx_legacy_network == "L-BHN":
                ipc_path = map_ipc_container_for_bh(mpls_cloud.z_clli, mx, mpls_cloud.path_a_site)
            else:
                abort(500, message=f"Unsupported legacy company: {mx_legacy_network}. Must be L-TWC, L-CHTR, or L-BHN")
    logger.debug(f"IPC container determined: {ipc_path}")
    if not ipc_path.endswith("/Customer"):
        ipc_path += "/Customer"
    if not ipc_path.startswith("/"):
        ipc_path = "/" + ipc_path
    return ipc_path


def circuit_site_info_path(cid, full_info=True):
    logger.info(f"Pulling circuit site information for {cid}")
    url = get_circuit_site_url(cid=cid, full_info=full_info)
    res = get_granite(url)

    csip_data = None
    try:
        csip_data = res[0]
    except (TypeError, KeyError, IndexError):
        logger.exception(f"No circuit site data found for {cid} \nURL: {url} \nResponse: \n{res}")
        abort(500, f"No circuit site data found for {cid}", url=url, response=res)

    expected = ["A_STATE", "Z_ADDRESS", "Z_CITY", "Z_STATE", "Z_ZIP"]
    missing = validate_values(csip_data, expected)
    if missing:
        logger.error(f"Circuit site data in Granite missing {missing}")
        abort(500, message=f"Circuit site data in Granite missing required value(s): {missing}", url=url, response=res)

    csip_values = {
        "a_state": csip_data["A_STATE"],
        "z_address": csip_data["Z_ADDRESS"],
        "z_city": csip_data["Z_CITY"],
        "z_state": csip_data["Z_STATE"],
        "z_zip": csip_data["Z_ZIP"],
    }

    logger.info(f"Successfully obtained circuit site info for {cid} and assigned to 'csip_values': \n{csip_values}")
    return csip_values


def granite_assignment(payload):
    logger.info("Updating Granite path and UDA info\nPayload: \n{payload}")

    url = granite_paths_url()
    data = put_granite(url, payload, timeout=60)
    try:
        if data.get("retString").lower() != "path updated":
            logger.error(
                f"Unexpected Granite retString value for UDA update (!= 'path updated') "
                f"\nretString value: {data.get('retString')}"
                f"\nURL: {url} \nResponse: \n{data}"
            )
            abort(
                500,
                message=f"Unexpected Granite response for path and UDA update: {data.get('retString')}",
                url=url,
                response=data,
            )
    except (AttributeError, KeyError):
        logger.exception(
            f"Error parsing retString value for Granite UDA update response. \nURL: {url} \nResponse: \n{data}"
        )
        abort(
            500,
            f"Error while validating Granite response for UDA update. \nGranite response value: {data.get('retString')}",
            url=url,
            response=data,
        )


def _map_ipc_container_from_mpls(cid, parent_mpls):
    """Assign IPC container based on the Parent Network value of the circuit in Granite. Not all MPLS naming directly
    maps to the appropriate container in IPC, so we will handle the exceptions here to ensure that we are not
    attempting to pull customer statics from incorrect/invalid containers.

    This approach is only feasible for LTWC and LBHN. LCHTR must rely on IS-IS area mappings.

    :param cid: The main service circuit ID
    :param parent_mpls: The parent MPLS network ID of the circuit, should match the values defined below.

        Currently supported MPLS Networks:
            * CHTRSE.CEN.CAROLINAS.MPLS
            * CHTRSE.CEN.CENTRAL STATES.MPLS
            * CHTRSE.CEN.GREAT LAKES.MPLS
            * CHTRSE.CEN.NYC.MPLS
            * CHTRSE.CEN.NORTHEAST.MPLS
            * CHTRSE.CEN.SOUTHERN OHIO.MPLS
            * CHTRSE.CEN.TEXAS.MPLS
            * CHTRSE.CEN.HAWAII.MPLS
            * CHTRSE.CEN.WEST.MPLS
            * CHTRSE.CEN.SOUTH.MPLS

        MPLS Networks which are unsupported, and should hit SF fallout criteria before reaching SEnSE:
            * CHTRSE.CEN.FLORIDA.MPLS
            * CHTRSE.CEN.NORTHWEST.MPLS
    """

    logger.info("Attempting to discern IPC Container based on Granite parent network")
    region = None
    try:
        region = parent_mpls.split(".")[-2]
        logger.info(f"Region {region} extracted from parent network {parent_mpls} for {cid}")
    except IndexError:
        logger.exception(f"Unable to extract region value from {parent_mpls}")
        abort(500, f"Unable to extract region value from {parent_mpls}")

    # Midwest requires special treatment, and is kept in its own list
    granular_map = ["CENTRAL STATES", "GREAT LAKES", "SOUTHERN OHIO", "CAROLINAS"]
    # These markets map more directly to IPC
    direct_map = ["NYC", "NORTHEAST", "TEXAS", "HAWAII", "WEST", "SOUTH"]

    # Filter out anything that doesn't fit the above supported values, these should fall out
    if not any(i == region for i in granular_map + direct_map):
        logger.error(f"Parent network {parent_mpls} is not supported")
        abort(500, f"Parent network {parent_mpls} is not supported")

    if any(i == region for i in granular_map):
        if region in ("CENTRAL STATES", "CAROLINAS"):
            hub_state = circuit_site_info_path(cid).get("a_state")
            if hub_state == "AL":
                region = "NDC/TW-Dothan"
            elif hub_state in ["NC", "SC"]:
                region = "Carolinas"
            elif hub_state == "NE":
                region = "Texas/Lincoln"
            elif hub_state == "WI":
                region = "Midwest/Wisconsin"
            elif hub_state == "KS" or hub_state == "MO":
                region = "Texas/KansasCity"
            else:
                logger.error(f"State {hub_state} for parent network {parent_mpls} is not supported")
                abort(500, f"State {hub_state} for parent network {parent_mpls} is not supported")
                # In case any Minnesota or other unsupported areas make it through prior filters
        else:
            region = "Midwest"

    elif region in "HAWAII":
        # Hawaii container is nested under West container
        region = "West/Hawaii"
    else:
        region = region.title()
    logger.info(f"IPC Container region for {cid} set as {region}")
    return f"/Commercial/LTWC/{region}/Customer"
