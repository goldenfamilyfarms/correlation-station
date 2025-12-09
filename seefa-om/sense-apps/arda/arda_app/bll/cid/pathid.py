import logging
import time

from arda_app.bll.cid import cid_globals as cgl
from arda_app.bll.cid.site import get_site_by_enni_for_circuitpath
from arda_app.common.cd_utils import granite_paths_url, granite_sites_put_url
from common_sense.common.errors import abort
from arda_app.dll.denodo import get_npa_three_digits
from arda_app.dll.granite import post_granite, put_granite

logger = logging.getLogger(__name__)


def generate_cid_v3(site, npa_val=None, service_type="FIA", company="CHTR"):
    logger.info("Generate CID started.")
    code, value = get_pathid_v4(site, service_type, npa_val, company)

    if code == 200:
        return value["pathIDvalue"]
    else:
        msg = f"Couldn't create a CID - {value}"
        logger.info(msg)
        abort(500, msg)


def update_npa(site):
    logger.info("Update NPA")
    name = get_value_from_path(site, "site")
    update_parameters = {"SITE_NAME": name, "SITE_TYPE": site["site_type"], "SITE_NPA_NXX": site["npa"]}
    logger.info(f"Updating npa for existing site {update_parameters}")
    url = granite_sites_put_url()
    put_granite(url, update_parameters, timeout=90)


def template_selector_v2(path, suffix=None):
    logger.info("Select Granite Template")

    if path["product_service"] == "FINISHED INTERNET" or path["product_service"] in cgl.WIRELESS_TYPES:
        return "WS-FINISHED INTERNET TEMPLATE"
    elif path["product_service"].upper() in (cgl.ETHERNET_TYPES + cgl.MANAGED_TYPES):
        return "EXPO WS ETHERNET PATH TEMPLATE"
    elif "EPLAN" in path["product_service"]:
        return "WS ELAN VPLS"
    elif "OL-UC" in path["path_order_num"] or "OL-CC" in path["path_order_num"]:
        return "UC RING CENTRAL"
    elif suffix:
        return "PRI CHILD"
    elif path["product_service"].upper() in ("CUS-VOICE-HOSTED", "CUS-VOICE-PRI"):
        return "WS HOSTED VOICE"
    elif path["product_service"].upper() in cgl.DARKFIBER_TYPES:
        return "WS DARK FIBER"

    return (
        "EXPO WS ENTERPRISE DIA PATH TEMPLATE"
        if path["customer_type"].upper() in ("ENTERPRISE", "HOSPITALITY")
        else "EXPO WS CARRIER DIA PATH TEMPLATE"
    )


def product_service_validation_v2(path):
    logger.info("Product Service Validation.")

    if check_sites_for_customer(path) is False:
        abort(500, "Neither side site has a customer")

    z_side_products = (
        cgl.VOICE_TYPES
        + cgl.HOSPITALITY_TYPES
        + cgl.WIRELESS_TYPES
        + cgl.MANAGED_TYPES
        + cgl.ENNI_TYPES
        + cgl.OTHER_TYPES
    )
    a_side_products = cgl.EPL_TYPES + cgl.WAVE_TYPES + cgl.DARKFIBER_TYPES + cgl.ENNI_TYPES

    if path["product_service"] in cgl.ENNI_TYPES:
        try:
            if path["a_side_site"].get("site_enni"):
                if check_side_for_val(path, "a_side_site", "site_enni") is False:
                    msg = f"service_type {path['product_service']} requires an a and z side."
                    logger.info(msg)
                    abort(500, msg)
        except KeyError:
            msg = "A side ENNI information missing from path payload"
            logger.error(msg)
            abort(500, msg)
    elif path["product_service"] in a_side_products:
        if check_side_for_val(path, "a_side_site", "site") is False:
            msg = f"service_type {path['product_service']} requires an a and z side."
            logger.info(msg)
            abort(500, msg)
    elif "EPLAN" in path.get("product_service") or "EP-LAN" in (
        path.get("product_service") or "DIA" in path.get("product_service")
    ):
        if check_side_for_val(path, "a_side_site", "site") is True:
            msg = f"service_type {path['product_service']} can not have an a side."
            logger.info(msg)
            abort(500, msg)
    elif path["product_service"] in z_side_products:
        if check_side_for_val(path, "z_side_site", "site") is False:
            msg = f"service_type {path['product_service']} requires a z side."
            logger.info(msg)
            abort(500, msg)
    else:
        if check_side_for_val(path, "a_side_site", "site") is False:
            msg = f"service_type {path['product_service']} requires an a and z side."
            logger.info(msg)
            abort(500, msg)


def path_type_selector(path):
    logger.info("Select Path Type")

    if path["product_service"] == "CUS-VOICE-SIP":
        return "CUSTOMER SIP TRUNKS"
    elif path["product_service"] == "CUS-VOICE-PRI":
        return "PRI TRUNKS"
    elif path["product_service"] in cgl.HOSPITALITY_TYPES:
        return "RF"
    elif path["product_service"] in (cgl.WIRELESS_TYPES + cgl.OTHER_TYPES + cgl.ETHERNET_TYPES):
        return "ETHERNET"
    elif path["product_service"] in cgl.WAVE_TYPES:
        return "WDM"
    elif path["product_service"] in cgl.DARKFIBER_TYPES:
        return "DARK FIBER"


def video_check(path):
    logger.info("Check if video")

    if not path["z_side_site"].get("customer"):
        return ""
    elif path["product_service"] in cgl.HOSPITALITY_TYPES:
        return ""
    else:
        return path["z_side_site"]["customer"][:50]


def create_path_v4(new_cid, path, suffix=None):
    logger.info("Create path started.")
    path_needs_a_side = check_if_path_has_a_side(path)

    if path_needs_a_side is True:
        if path["a_side_site"].get("site_enni"):
            path = set_a_side_from_enni(path)

    template = template_selector_v2(path, suffix)
    path["path_type"] = path_type_selector(path) if not path.get("path_type") else path["path_type"]

    if suffix:
        path_name = new_cid + suffix
    else:
        path_name = new_cid

    band_width = path["bw_value"] if not path.get("bw_unit") else f"{path['bw_value']} {path['bw_unit'].capitalize()}"
    body = {
        "PATH_NAME": f"{path_name}"[:100],
        "PATH_BANDWIDTH": band_width[:30],
        "PATH_TEMPLATE_NAME": template[:100],
        "CUST_ID": get_value_from_path(path, "customer"),
        "PATH_ORDER_NUM": "" if not path.get("path_order_num") else path["path_order_num"][:50],
        "Z_SITE_NAME": "" if not path["z_side_site"].get("site") else path["z_side_site"]["site"][:100],
        "A_SITE_NAME": "" if not path["z_side_site"].get("site") else path["z_side_site"]["site"][:100],
        "LEG_Z_SITE_NAME": path["z_side_site"]["site"][:100],
        "Z_CUST_NAME": video_check(path),
        "PATH_STATUS": "Planned",
        "UDA": {
            "ADDITIONAL CIRCUIT INFORMATION": {"CONTRACT TYPE": path.get("contract_type", "")},
            "SERVICE TYPE": {
                "PRODUCT/SERVICE": "" if not path.get("product_service") else path["product_service"][:50],
                "SERVICE MEDIA": path["service_media"],
            },
            "TSP CIRCUIT INFO": {
                "TSP AUTHORIZATION CODE": "" if not path.get("tsp_auth") else path["tsp_auth"][:12],
                "TSP EXPIRATION DATE": path.get("tsp_expiration", ""),
            },
        },
    }

    if "tsp_auth" in path:
        if path["tsp_auth"] or path["tsp_expiration"]:
            body["PATH_SVC_PRIORITY"] = "YES"

    # TSP will be in the UDA
    if path["path_type"]:
        body["PATH_TYPE"] = path["path_type"]

    if path_needs_a_side is True:
        body["A_SITE_NAME"] = "" if not path["a_side_site"].get("site") else path["a_side_site"]["site"][:100]
        body["LEG_A_SITE_NAME"] = "" if not path["a_side_site"].get("site") else path["a_side_site"]["site"][:100]
        body["A_CUST_NAME"] = "" if not path["a_side_site"].get("customer") else path["a_side_site"]["customer"][:50]
    elif path.get("product_service") == "COM-VIDEO SBB":
        body["LEG_A_SITE_NAME"] = path["z_side_site"]["site"][:100]

    if path["product_service"] in cgl.WIRELESS_TYPES:
        body["LEG_A_SITE_NAME"] = path["z_side_site"]["site"][:100]
        body["UDA"] = {
            "ADDITIONAL CIRCUIT INFORMATION": {"CONTRACT TYPE": path.get("contract_type", "")},
            "INTERNET SERVICE ATTRIBUTES": {"IPv4 SERVICE TYPE": "NONE", "IPv6 SERVICE TYPE": "NONE"},
            "SERVICE TYPE": {"SERVICE MEDIA": path["service_media"]},
        }

    url = granite_paths_url()
    logger.info(f"Creating path - {url} {body}")
    resp_json = path_creation_call(url, body)

    return {"pathId": resp_json["pathId"], "instId": resp_json["pathInstanceId"]}


def path_creation_call(url, body):
    retries = 4

    for retry in range(1, retries):
        logger.info(f"Creating path - try # {retry} of 3")
        resp = post_granite(url, body, timeout=90, return_resp=True)

        if resp.status_code == 200:
            return resp.json()
        else:
            time.sleep(7.3)

            if retry >= retries - 1:
                abort(
                    500,
                    "Creating path failed after trying multiple times."
                    f"Granite status code: {resp.status_code} "
                    f"and error message: {resp.json()['retString']} ",
                )


def validate_zip(zip_code):
    # Verify length of zip code
    logger.info("Validate Zip")

    if len(zip_code) != 5:
        return (500, f"Invalid value '{zip_code}' for query parameter zip_code. Expected length to be 5")


def validate_elements_v2(zip_code, bw_val, product_service, bw_unit=None):
    """Validate input and come up with the bandwidth tier value"""
    # Verify bandwidth unit is supported
    logger.info("Validate Elements")
    valid_values = ("RF", "DS1", "OPTICAL")

    if bw_val not in valid_values:
        valid_types = ("MBPS", "GBPS")

        try:
            bw_unit = bw_unit.upper()
        except AttributeError:
            return 500, "BW Unit must be in the formats of - 'GBPS' or 'MBPS'"

        if bw_unit not in valid_types:
            return 500, "BW Unit must be in the formats of - 'GBPS' or 'MBPS'"

    # Verify length of zip code
    if len(zip_code) != 5:
        return (500, f"Invalid value '{zip_code}' for query parameter zip_code. Expected length to be 5")

    # Verify supported range of bandwidth value
    error, bw_tier = get_service_code(bw_unit, bw_val, product_service)

    return error, bw_tier


def get_pathid_v4(path, service_type, npa_val=None, company="CHTR"):
    # Verify company meets length requirement
    logger.info("Get pathid")

    if len(company) < 4:
        return (500, f"Invalid value '{company}' for query parameter company. Expected min length 4")

    # Verify service type is supported
    valid_types = (
        cgl.ETHERNET_TYPES
        + cgl.OTHER_TYPES
        + cgl.VOICE_TYPES
        + cgl.HOSPITALITY_TYPES
        + cgl.WIRELESS_TYPES
        + cgl.WAVE_TYPES
        + cgl.DARKFIBER_TYPES
        + cgl.MANAGED_TYPES
    )

    if service_type.upper() not in valid_types:
        return 500, f"Service type of {service_type} not supported"

    zip_code = get_value_from_path(path, "site_zip_code")

    if path.get("bw_unit"):
        error, bw_tier = validate_elements_v2(zip_code, path["bw_value"], path["product_service"], path["bw_unit"])
    else:
        error, bw_tier = validate_elements_v2(zip_code, path["bw_value"], path["product_service"])

    if error:
        return error, bw_tier

    # Collect data needed to create a path id
    if npa_val is None:
        # lookup the 3 digit npa
        npa = get_npa_three_digits(zip_code)
        path["npa"] = npa
        # pass the three digits to the update
        update_npa(path)
        # carry on with life
        npa_val = npa[:2]

    # Create path id
    if npa_val and bw_tier:
        resp = {"pathIDvalue": f"{npa_val}.{bw_tier}.%..{company}"}
        return 200, resp
    else:
        logger.info("Error with components of path id")
        abort(500, "Error with components of path id")


def get_service_code(bw_unit, bw_val, product_service):
    logger.info("Get Service Code")
    l1xx_types = cgl.WIRELESS_TYPES + cgl.MANAGED_TYPES

    if product_service in cgl.DARKFIBER_TYPES:
        return None, "TXXX"

    if product_service in cgl.HOSPITALITY_TYPES:
        if product_service == "COM-VIDEO INSERTION":
            return None, "TVXE"
        elif product_service == "COM-VIDEO SBB":
            return None, "VCXX"

        return None, "VSXX"

    if product_service in l1xx_types:
        return None, "L1XX"
    elif product_service in ["CAR-CTBH 4G", "CAR-E-ACCESS FIBER/DOCSIS EPL", "CAR-E-ACCESS FIBER/FIBER EPL"]:
        service_code = unit_check(bw_unit, bw_val)
        return None, service_code
    elif product_service in cgl.WAVE_TYPES:
        return None, "WCXX"

    try:
        bw_val = int(bw_val)
    except ValueError:
        return 500, f"bw_val: {bw_val} should be in integer form"

    if product_service in cgl.VOICE_TYPES:
        if bw_val == 5:
            service_code = "HNXN"
        elif bw_val == 20:
            service_code = "TGXX"
        else:
            service_code = "IPXN"
    elif bw_val <= 0:
        return 500, "BW must be greater than 0Gbps or 0Mbps"
    else:
        service_code = unit_check(bw_unit, bw_val)

    return None, service_code


def unit_check(bw_unit, bw_val):
    logger.info("Check bandwidth and value")

    if bw_unit.upper() == "GBPS":
        if int(bw_val) == 1:
            service_code = "L1XX"
        else:
            service_code = "L4XX"
    elif bw_unit.upper() == "MBPS":
        if int(bw_val) <= 1000:
            service_code = "L1XX"
        else:
            service_code = "L4XX"

    return service_code


def check_sites_for_customer(path):
    logger.info("Check sites for customer")
    return check_side_for_val(path, "z_side_site", "customer") or check_side_for_val(path, "a_side_site", "customer")


def check_side_for_val(path, side, value):
    logger.info("Check A/Z side for value.")

    try:
        if path[side].get(value):
            return True

        return False
    except (AttributeError, KeyError):
        return False


def check_if_path_has_a_side(path):
    logger.info("Check if path has A side.")

    try:
        if path.get("a_side_site"):
            return True

        return False
    except (AttributeError, KeyError):
        return False


def get_value_from_path(path, value):
    logger.info("Get value from path.")

    try:
        if path[value]:
            return path[value]
    except (AttributeError, KeyError):
        if check_side_for_val(path, "z_side_site", value) is True:
            return path["z_side_site"].get(value)
        elif check_side_for_val(path, "a_side_site", value) is True:
            return path["a_side_site"].get(value)

        return


def get_suffix(product_service):
    logger.info("Get suffix")

    if product_service in cgl.DARKFIBER_TYPES:
        return ".002"


def create_sub_paths(body, new_cid):
    logger.info("Create sub paths.")
    sub_list = []

    try:
        if "trunk" in body:
            if 0 < int(body["trunk"]) < 13:
                for x in range(int(body["trunk"])):
                    suffix = f".00{x + 1}"
                    body["path_type"] = "TDM"
                    body["bw_value"] = "DS1"
                    body["bw_unit"] = None
                    sub_paths = create_path_v4(new_cid, body, suffix)
                    sub_list.append({"path": sub_paths["pathId"]})
    except ValueError:
        msg = "Invalid trunk value"
        logger.info(msg)
        abort(500, msg)

    return sub_list


def create_sister_path(new_cid, body):
    logger.info("Create Sister path")
    cid = f"{new_cid[:2]}.L1XX.%..CHTR"
    body["bw_value"] = "1"
    body["bw_unit"] = "MBPS"
    body["product_service"] = "INT-MANAGEMENT"
    body["service_media"] = "FIBER/COAX HYBRID"

    return create_path_v4(cid, body)


def unitless_bandwidths(path):
    logger.info("Return path for unitless bandwidths & check bandwidth value.")
    bw_unit = path["bw_unit"].upper() if path.get("bw_unit") else ""
    bw_value = path.get("bw_value", "")

    if path["product_service"] in cgl.RF_TYPES:
        if not bw_unit:
            path["bw_unit"], path["bw_value"] = None, "RF"
    elif path["product_service"] in cgl.WIRELESS_TYPES and path["service_media"] == "LTE":
        path["bw_unit"], path["bw_value"] = None, "RF"
    elif path["product_service"] in cgl.DARKFIBER_TYPES:
        path["bw_unit"], path["bw_value"] = None, "OPTICAL"
    elif bw_unit == "MBPS" and int(bw_value) > 999:
        mes = "Bandwidth value is greater than 999 Mbps please convert to Gbps"
        logger.info(mes)
        abort(500, mes)
    elif bw_unit == "GBPS" and int(bw_value) > 800:
        mes = "Bandwidth value is greater than 800 Gbps please check bandwidth conversion"
        logger.info(mes)
        abort(500, mes)

    return path


def set_a_side_from_enni(path):
    logger.info("Set A side from Enni")
    is_ctbh = "CAR-CTBH 4G" in path.get("product_service", "")

    if is_ctbh:
        name_zip = get_site_by_enni_for_circuitpath(path["a_side_site"]["site_enni"], True)
    else:
        name_zip = get_site_by_enni_for_circuitpath(path["a_side_site"]["site_enni"])

    if name_zip:
        path["a_side_site"]["site"] = name_zip["siteName"]
        path["a_side_site"]["site_zip_code"] = name_zip["zipcode"]
        path["a_side_site"]["customer"] = path["z_side_site"]["customer"]
    else:
        path["a_side_site"]["site"] = ""
        path["a_side_site"]["site_zip_code"] = path["z_side_site"]["site_zip_code"]
        path["a_side_site"]["customer"] = path["z_side_site"]["customer"]

    return path
