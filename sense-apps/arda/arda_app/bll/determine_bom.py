import re

from arda_app.dll.granite import get_path_elements, get_attributes_for_path
from common_sense.common.errors import abort
from arda_app.bll.net_new.utils.shelf_utils import get_device_bw


def determine_bom(payload: dict) -> str:
    """Determine the correct BOM template"""
    cid, product, site_name = (payload["cid"], payload["product_name"], payload.get("granite_site_name"))

    if not site_name:
        abort(500, "granite site name was not provided")

    if "Wireless Internet Access" in product:
        if "Backup" in product:
            abort(500, f"Unsupported product :: {product}")

        if payload.get("service_code"):
            match payload["service_code"]:
                case "RW700":
                    return "WIA Cradlepoint E100 BOM"
                case "RW702":
                    return "WIA Cradlepoint W1850 BOM"
                case "RW703":
                    return "WIA Cradlepoint W1855 BOM"
                case "WISIM":
                    abort(500, "Unsupported WIA Service Code: WISIM")
        else:
            path_info = get_attributes_for_path(cid)

            if path_info[0]["serviceMedia"] == "LTE":
                return "WIA Cradlepoint E100 BOM"
            elif path_info[0]["serviceMedia"] == "5G":
                return "WIA Cradlepoint W1850 BOM"
            else:
                abort(500, f"Unexpected WIA service media {path_info[0]['serviceMedia']}")

    if "SIP" in product or "PRI" in product:
        if payload.get("voltage") and "DC" in payload["voltage"]:
            abort(500, "No BOM template for DC voltage ADVA 114PRO on Voice circuit")
        elif payload.get("type_of_protection_needed") == "Optional UDA - Redundant Power":
            abort(500, "No BOM template for Redundant Power ADVA 114PRO on Voice circuit")
        if "SIP" in product:
            return "HCT_SIP plus Adva114 BOM"
        elif "PRI" in product:
            return "HCT_PRI plus Adva114 BOM"

    if payload.get("agg_bandwidth"):
        return bandwidth_logic(payload)
    else:
        return granite_cpe_logic(cid, site_name, product, payload)


def granite_cpe_logic(cid: str, site_name: str, product: str, payload: dict) -> str:
    """Original tempmlate logic to be removed after EXPO cutover to agg bandwidth logic"""
    try:
        # Only ADVAs are used for type II CPE on non-WIA products
        path_elements = get_path_elements(cid, "&VENDOR=ADVA")
    except Exception:
        abort(500, f"No ADVA in the path of circuit {cid}")

    cpe_model = None
    if isinstance(path_elements, list):
        # Only look at ADVAs at the correct A/Z side
        site_elements = []
        for element in path_elements:
            if element["A_SITE_NAME"] == site_name:
                site_elements.append(element)
        if not site_elements:
            abort(500, f"No ADVAs in the path with the Granite site: {site_name}")

        # There should only ever be one ADVA at the A or Z side
        if len({element.get("ELEMENT_NAME") for element in site_elements}) == 1:
            cpe_model = site_elements[0].get("MODEL")
        else:
            abort(500, f"More than one ADVA shelf in circuit path at {site_name}")

    # Map model to BOM template
    if cpe_model == "FSP 150-GE114PRO-C":
        if "SIP" in product or "PRI" in product:
            if payload.get("voltage") and "DC" in payload["voltage"]:
                abort(500, "No BOM template for DC voltage ADVA 114PRO on Voice circuit")
            elif payload.get("type_of_protection_needed") == "Optional UDA - Redundant Power":
                abort(500, "No BOM template for Redundant Power ADVA 114PRO on Voice circuit")
        if "SIP" in product:
            return "HCT_SIP plus Adva114 BOM"
        elif "PRI" in product:
            return "HCT_PRI plus Adva114 BOM"
        else:
            return adva_1g_template(payload)
    elif cpe_model == "FSP 150-XG116PROH":
        if payload.get("type_of_protection_needed") == "Optional UDA - Redundant Power":
            if payload.get("voltage") and "DC" in payload["voltage"]:
                return "ADVA116 PRO H BOM DC"
            else:
                return "ADVA116 PRO H BOM AC"
        elif payload.get("voltage") and "DC" in payload["voltage"]:
            return "ADVA116 PRO H BOM DC"
        else:
            return "ADVA116 PRO H BOM AC"
    elif cpe_model == "FSP 150-XG108" or cpe_model == "FSP 150-XG116PRO":
        return "ADVA108 BOM"
    elif cpe_model in ["E100 C4D/C7C", "ARC CBA850"]:
        return "WIA Cradlepoint E100 BOM"
    elif cpe_model == "W1850":
        return "WIA Cradlepoint W1850 BOM"
    elif cpe_model == "W1855":
        return "WIA Cradlepoint W1855 BOM"
    else:
        abort(500, f"No BOM template for CPE model: {cpe_model}")


def bandwidth_logic(payload: dict) -> str:
    bandwidth = payload["agg_bandwidth"].lower()
    if "gbps" in bandwidth:
        bw_type = re.split(r"(gbps)", bandwidth)
    elif "mbps" in bandwidth:
        bw_type = re.split(r"(mbps)", bandwidth)
    else:
        abort(500, f"Payload agg_bandwidth field {bandwidth} is invalid")

    bw_unit = bw_type[0].strip()
    bw_type = bw_type[1].strip()

    if get_device_bw(bw_unit, bw_type) == "1 Gbps":
        return adva_1g_template(payload)
    else:
        return adva_10g_template(payload)


def adva_1g_template(payload: dict) -> str:
    if payload.get("type_of_protection_needed") == "Optional UDA - Redundant Power":
        if payload.get("voltage") and "DC" in payload["voltage"]:
            return "ADVA114 PRO HE DC (dual PS) BOM"
        else:
            return "ADVA114 PRO HE AC (dual PS) BOM"
    elif payload.get("voltage") and "DC" in payload["voltage"]:
        return "ADVA114 DC BOM"
    else:
        return "ADVA114 BOM"


def adva_10g_template(payload) -> str:
    if payload.get("type_of_protection_needed") == "Optional UDA - Redundant Power":
        if payload.get("voltage") and "DC" in payload["voltage"]:
            return "ADVA116 PRO H BOM DC"
        else:
            return "ADVA116 PRO H BOM AC"
    elif payload.get("voltage") and "DC" in payload["voltage"]:
        return "ADVA116 PRO H BOM DC"
    else:
        return "ADVA108 BOM"
