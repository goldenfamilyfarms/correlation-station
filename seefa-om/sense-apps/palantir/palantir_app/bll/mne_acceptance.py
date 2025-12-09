import logging

from common_sense.common.errors import abort
from palantir_app.dll.sales_force import get_sf_data
from palantir_app.dll.mdso import mdso_post, product_query
from palantir_app.dll.granite import get_path_elements_from_filter, get_udas

logger = logging.getLogger(__name__)


def run_mne_acceptance(cid, eng_id):
    # Get UDAs and Path Elements from Granite
    path_elements = get_path_elements_from_filter(cid, level="1")
    if path_elements[0] != 200:
        abort(500, path_elements[1])
    highest_rev = sorted([x["PATH_REV"] for x in path_elements[1]])[-1]
    inst_id = ""
    for elems in path_elements[1]:
        if elems["PATH_REV"] == highest_rev:
            inst_id = elems["CIRC_PATH_INST_ID"]
            break
    response, udas = get_udas(cid, highest_rev)
    if response != 200:
        abort(500, f"Error getting UDA from Granite: {udas}")
    if udas:
        udas = {x["ATTR_NAME"]: x["ATTR_VALUE"] for x in udas}
        logger.info(f"NA: CID: {cid}, SORTED UDA: {udas}, inst_id: {inst_id}")
        # once UDAs are successfully acquired, attempt to get SF Elements
        sf_return = get_sf_data(eng_id)
        logger.info(f"sf_return: {sf_return}")
        if isinstance(sf_return, str):
            abort(500, sf_return)
        # Start MDSO Process. Get product ID.
        prod_id = product_query("merakiAcceptance", False)
        if not prod_id:
            abort(500, "Error fetching product id from MDSO")
        nwid = udas.get("MERAKI NETWORK ID", None)
        if nwid and "," in nwid:
            abort(500, f"Unexpected/Invalid NWID found in granite: {nwid}")
        clli = path_elements[1][0]["Z_CLLI"]
        if not all((nwid, clli)):
            abort(500, f"Missing Elements. nwid: {nwid} clli: {clli}")
        sf_return["nwid"] = nwid
        sf_return["CLLI"] = clli

        data = {"productId": prod_id, "label": eng_id, "properties": {"expected_data": sf_return}}
        endpoint = "/bpocore/market/api/v1/resources?validate=false&obfuscate=true"
        return mdso_post(endpoint, data, "meraki_acceptance")
    else:
        abort(500, "Granite issue. UDA or CID not found")
