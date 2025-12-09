import logging

from arda_app.common.cd_utils import granite_paths_url
from arda_app.dll.granite import get_granite, put_granite, get_attributes_for_path
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def type_2_gsip(payload: dict):
    logger.info("Assigning Type II GSIP information")
    put_granite_url = granite_paths_url()

    product_name = payload.get("product_name")

    if product_name == "Fiber Internet Access":
        paths_payload = {
            "PATH_NAME": payload.get("cid"),
            "PATH_REVISION": "1",
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {
                    "VC CLASS": "TYPE 2",
                    "# OF ENNIs": "1",
                    "OFF-NET SERVICE PROVIDER": payload.get("service_provider"),
                    "OFF-NET PROVIDER EVC CID": payload.get("service_provider_cid"),
                    "OFF-NET PROVIDER UNI CID": payload.get("service_provider_uni_cid"),
                },
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "ELIGIBLE DESIGN"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
            },
        }

        put_granite(put_granite_url, paths_payload)
    else:
        logger.info(f"Unsupported product name: {product_name}.")
        abort(f"GSIP did not run due to unsupported product name: {product_name}.")


def assign_gsip_main(payload: dict):
    cid = payload.get("cid")
    product_name = payload.get("product_name")
    class_of_service_type = payload.get("class_of_service_type")
    path_inst_id = payload.get("path_inst_id") if payload.get("path_inst_id") else ""
    type_2 = payload.get("third_party_provided_circuit") if payload.get("third_party_provided_circuit") else ""

    # default for class_of_service_type: Gold
    if not class_of_service_type:
        class_of_service_type = (
            "Silver" if product_name in ("EP-LAN (Fiber)", "EP-LAN (Fiber UHS)", "EVP-LAN") else "Gold"
        )

    # Type II
    if type_2 == "Y" and product_name == "Fiber Internet Access":
        type_2_gsip(payload)
        return {"message": "GSIP Attributes have been added successfully."}

    # FIA Attributes: Assign GSIP Attributes to Circuit Path
    if product_name in ("Fiber Internet Access", "Carrier Fiber Internet Access"):
        cid_resp = get_attributes_for_path(cid)

        manage_serv = "NO"

        if isinstance(cid_resp, list):
            if cid_resp[0]["product_Service_UDA"] == "CUS-SECURE INTERNET ACCESS":
                manage_serv = "YES"

        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": manage_serv},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "ELIGIBLE DESIGN"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    # HVF Attributes: Assign GSIP Attributes to Circuit Path
    elif product_name in (
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "SIP - Trunk (DOCSIS)",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
        "PRI Trunk (DOCSIS)",
    ):
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "INELIGIBLE SERVICE"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    # HVF Attributes: Assign GSIP Attributes to Circuit Path
    elif product_name in ("Hosted Voice - (Fiber)", "Hosted Voice - (Overlay)"):
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "YES"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "INELIGIBLE SERVICE"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    elif product_name in ("Hosted Voice - (DOCSIS)"):
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "YES"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "INELIGIBLE SERVICE"},
                "INTERNET SERVICE ATTRIBUTES": {"IPv4 SERVICE TYPE": "NONE", "IPv6 SERVICE TYPE": "NONE"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    elif product_name == "Carrier E-Access (Fiber)":
        # Carrier E-Access Attributes
        if class_of_service_type:
            class_of_service_type = cos_check(cid, class_of_service_type)

        # Assign GSIP Attributes to Circuit Path with CLASS OF SERVICE
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "1"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "CCC"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "ELIGIBLE DESIGN"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        if class_of_service_type:
            paths_payload["UDA"]["CIRCUIT SOAM PM"]["CLASS OF SERVICE"] = class_of_service_type

        put_granite(put_granite_url, paths_payload)

    elif "Wireless Internet Access" in product_name:
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 3", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "INET/VOICE"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "INELIGIBLE SERVICE"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    # RPHY Attributes: Assign GSIP Attributes to Circuit Path
    elif product_name in ("FC + Remote PHY",):
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "YES"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "CCC"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    # EPLAN Attributes: Assign GSIP Attributes to Circuit Path
    elif product_name in ("EP-LAN (Fiber)", "EP-LAN (Fiber UHS)", "EVP-LAN"):
        logger.info(f"Assigning GSIP information to {cid}")
        if class_of_service_type:
            class_of_service_type = cos_check(cid, class_of_service_type)

        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "VPLS"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "ELIGIBLE DESIGN"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        if class_of_service_type:
            paths_payload["UDA"]["CIRCUIT SOAM PM"]["CLASS OF SERVICE"] = class_of_service_type

        put_granite(put_granite_url, paths_payload)

    # EPL Attributes: Assign GSIP Attributes to Circuit Path
    elif product_name in ("EPL (Fiber)", "Carrier Transport EPL"):
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "0"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "CCC"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "ELIGIBLE DESIGN"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        put_granite(put_granite_url, paths_payload)

    elif product_name == "Carrier CTBH":
        # Carrier CTBH Attributes
        if class_of_service_type:
            class_of_service_type = cos_check(cid, class_of_service_type)

        # Assign GSIP Attributes to Circuit Path with CLASS OF SERVICE
        logger.info(f"Creating Granite circuit revision for {cid}")
        put_granite_url = granite_paths_url()
        paths_payload = {
            "PATH_NAME": cid,
            "UDA": {
                "ADDITIONAL CIRCUIT INFORMATION": {"VC CLASS": "TYPE 1", "# OF ENNIs": "2"},
                "ADDITIONAL ETHERNET INFO": {"INSTANCE PROTOCOL": "CCC"},
                "SERVICE_TYPE": {"MANAGED SERVICE": "NO"},
                "CIRCUIT SOAM PM": {"SLM ELIGIBILITY": "ELIGIBLE DESIGN"},
            },
        }

        if path_inst_id:
            paths_payload["PATH_INST_ID"] = path_inst_id
        else:
            paths_payload["PATH_REVISION"] = "1"

        if class_of_service_type:
            paths_payload["UDA"]["CIRCUIT SOAM PM"]["CLASS OF SERVICE"] = class_of_service_type

        put_granite(put_granite_url, paths_payload)

    else:
        logger.info(f"Unsupported product name: {product_name}.")
        abort(f"GSIP did not run due to unsupported product name: {product_name}.")
    return {"message": "GSIP Attributes have been added successfully."}


def cos_check(cid, class_of_service_type):
    get_granite_url = f"/circuitSites?CIRCUIT_NAME={cid}&PATH_CLASS=P"

    circuit_site = get_granite(get_granite_url)

    if class_of_service_type:
        class_of_service_type = class_of_service_type.upper()
    else:
        logger.info("Class of Service was not provided in the payload")
        abort(f"Class of Service was not provided in the payload for {cid}")

    get_granite_url = (
        "/cOSbyDistance?"
        f"LAT1={circuit_site[0].get('A_LATITUDE')}&LON1={circuit_site[0].get('A_LONGITUDE')}&"
        f"LAT2={circuit_site[0].get('Z_LATITUDE')}&LON2={circuit_site[0].get('Z_LONGITUDE')}"
    )

    area = get_granite(get_granite_url)

    if area[0].get("SERVICE_LEVEL") not in ("METRO", "REGIONAL", "NATIONAL"):
        logger.info("Class of Service could not be determined, please investigate.")
        abort("Class of Service could not be determined, please investigate.")

    return f"{class_of_service_type} {area[0]['SERVICE_LEVEL']}"
