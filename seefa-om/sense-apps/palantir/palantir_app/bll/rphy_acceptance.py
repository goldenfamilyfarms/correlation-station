import logging
import re

from palantir_app.dll.denodo import denodo_get
from palantir_app.dll.seek import get_seek
from palantir_app.dll.sense import beorn_get, sense_get
from palantir_app.dll.granite import get_path_elements_from_filter
from palantir_app.dll.mdso import mdso_post, product_query
from common_sense.common.errors import abort
from palantir_app.common.endpoints import DENODO_VIEWS


logger = logging.getLogger(__name__)


def run_rphy_acceptance(cid, eng_id):
    # Get RF codes and VCD info
    vcd_response = get_vcd_info(cid, eng_id)
    cpe_info = get_cpe_info(cid)
    cmts_ip = get_cmts_ip(cid)

    # Get RPD #
    _, path_elements = get_path_elements_from_filter(cid, level="1")
    rpd = [e["CHAN_NAME"] for e in path_elements if e["LEG_NAME"] == "RPHY"]
    if not rpd:
        abort(500, "Could not find rpd information from granite return, check leg name")
    if len(rpd) > 0:
        rpd = rpd[0] + ":0"

    if isinstance(vcd_response, dict):
        mdso_payload = {}
        product_id = product_query("RPHYAcceptance", False)
        mdso_payload = {
            "label": cid,
            "productId": product_id,
            "properties": {
                "channel_numbers": sorted(set(vcd_response["channels"])),
                "rpd": rpd,
                "service_groups": [x["name"] for x in vcd_response["service_group_data"]],
                "cid": cid,
                "cmtsipAddress": cmts_ip,
                "CPE": {
                    "model": cpe_info["cpe_model"],
                    "vendor": cpe_info["cpe_vendor"],
                    "ipAddress": cpe_info["cpe_ip"],
                },
            },
        }
        logger.info("All required RPHY information present. Creating resource")
        endpoint = "/bpocore/market/api/v1/resources?validate=false&obfuscate=true"
        return mdso_post(endpoint, mdso_payload, "RPHYAcceptance")
    else:
        abort(500, f"invalid response from SEEK: {vcd_response}")


def get_vcd_info(cid, eng_id):
    rf_codes = beorn_get("/v1/rphy/rf_codes", {"eng_id": eng_id})
    if "error" in rf_codes:
        abort(500, f"Salesforce Query issue: {rf_codes}")
    logger.info(f"RF codes call returned: {rf_codes}")
    rf_codes_str = ",".join(rf_codes["svc_codes"])
    # Translate RF codes into channels and other info
    body = {"CID": cid, "ENG_ID": eng_id}
    zip_codes = sense_get("/palantir/v1/rphyipcmac/clu_zip_codes", body)["zip_code"]
    seek_payload = {"zip_code": zip_codes, "rf_codes": rf_codes_str}
    vcd_response = get_seek("/video_channel_db/api/diceinfo/", seek_payload)
    logger.info(f"VCD response: {vcd_response}")
    if "Error" in vcd_response:
        abort(500, f"SEEK_GET issue: {vcd_response}")
    return vcd_response


def get_cpe_info(cid):
    code, path_elements = get_path_elements_from_filter(cid, level="1")
    if code != 200:
        abort(500, path_elements)
    cpe_dict = None
    for e in path_elements:
        if e.get("TID", None) and re.match(".{9}[WXYZ]W", e.get("TID").upper()):
            cpe_dict = e
            break

    if not cpe_dict:
        abort(500, "CPE Information missing from Granite")

    if cpe_dict["IPV4_ADDRESS"] and cpe_dict["IPV4_ADDRESS"] != "DHCP":
        cpe_ip = cpe_dict["IPV4_ADDRESS"].split("/")[0]
    else:
        cpe_ip = cpe_dict["FQDN"]

    if not cpe_ip:
        abort(500, "FQDN and IPV4 Adddress missing for CPE from Granite")

    cpe_info = {"cpe_vendor": cpe_dict.get("VENDOR"), "cpe_ip": cpe_ip, "cpe_model": cpe_dict.get("MODEL")}
    return cpe_info


def get_cmts_ip(cid):
    # Get CMTS IP address
    denodo_response = denodo_get(f"{DENODO_VIEWS}?cid={cid}", operation="mne")["elements"][0]["data"]
    cmts_ip = None
    for elem in denodo_response:
        if elem["vendor"] == "HARMONIC" and elem["model"] == "CABLEOS CORE":
            if elem.get("management_ip") and elem.get("management_ip") != "DHCP":
                cmts_ip = elem["management_ip"].split("/")[0]
                return cmts_ip
            else:
                cmts_ip = elem.get("device_id")
                if cmts_ip:
                    return cmts_ip
    if not cmts_ip:
        abort(500, "Unable to locate CMTS Mgmt IP")
