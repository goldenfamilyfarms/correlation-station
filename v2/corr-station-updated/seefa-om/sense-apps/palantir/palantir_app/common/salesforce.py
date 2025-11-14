import re

from palantir_app.common.constants import FIA, FIBER_INTERNET_ACCESS


def product_sort(product, check_data):
    if product.endswith("EPL"):
        return "EPL"
    elif product.endswith(FIA):
        check_data["product_type"] = FIA
    elif product.endswith("TPE"):
        check_data["product_type"] = "TPE"
    elif product.endswith("DIA"):
        check_data["product_type"] = "DIA"
    elif product.endswith("SVC"):
        check_data["product_type"] = "DIA"
    elif product.endswith(FIBER_INTERNET_ACCESS):
        check_data["product_type"] = FIA


def cpe_check(granite_data):
    for x in granite_data:
        granite_device_tid = str(x["TID"])
        if re.match(".{9}[WXYZ]W", granite_device_tid.upper()):
            return True
    return False


def compare_circuits(granite_cid, check_data_cid):
    if granite_cid != check_data_cid:
        return "circuit id match failed, Granite value: {} not matching Salesforce value: {}".format(
            granite_cid, check_data_cid
        )


def compare_productname(granite_product, check_data_product):
    if granite_product == check_data_product:
        return
    if not granite_product or granite_product.lower().strip() in ("none", "null"):
        if check_data_product == "None":
            return
        return "product name match failed, Granite value None not matching Salesforce value : {}".format(
            check_data_product
        )

    if check_data_product.lower() == FIBER_INTERNET_ACCESS.lower():
        if (
            granite_product.lower() in ("com-dia", "com-fia")
            or granite_product.lower().endswith("dia")
            or granite_product.lower().endswith(FIA.lower())
        ):
            return
    else:
        return "product name match failed, Granite value: {} not matching Salesforce value: {}".format(
            granite_product, check_data_product
        )


def compare_connectortype(granite_data, check_data_connector):
    if not granite_data["CONNECTOR_TYPE"] or granite_data["CONNECTOR_TYPE"].lower().strip() in ("none", "null"):
        if check_data_connector == "None":
            return
        return "connector type match failed, Granite value: None not matching Salesforce value: {}".format(
            check_data_connector
        )
    if re.match(".{9}[WXYZ]W", granite_data["TID"].upper()) and "TRANSPORT" not in granite_data["ELEMENT_TYPE"]:
        granite_connector_type = granite_data["CONNECTOR_TYPE"].lower().replace("-", "")
        check_data_connector = check_data_connector.lower().replace("-", "")
        if granite_connector_type == check_data_connector:
            return
        else:
            return "connector type match failed, Granite value: {} not matching Salesforce value: {}".format(
                granite_connector_type, check_data_connector
            )


def compare_unispeed(granite_data, check_data_unispeed):
    if re.match(".{9}[WXYZ]W", granite_data["TID"].upper()) and "TRANSPORT" not in granite_data["ELEMENT_TYPE"]:
        if not granite_data["uni_speed"] or granite_data["uni_speed"].lower().strip() in ("none", "null"):
            if check_data_unispeed == "None":
                return

            return "unispeed match failed, Granite value: None not matching Salesforce value: {}".format(
                check_data_unispeed
            )
        granite_uni_speed = granite_data["uni_speed"].lower().strip()
        if granite_uni_speed in ("1 gbps", "1000 base", "10/100 base", "10/100/1000 base"):
            if check_data_unispeed.lower() == "1000 base":
                return
        if granite_uni_speed in ("1 gbps", "1000 base", "10/100 base"):
            if check_data_unispeed.lower() == "10/100 base":
                return
        if granite_uni_speed in ("1 gbps", "1000 base", "10000 base", "10/100/1000 base"):
            if check_data_unispeed.lower() == "10/100/1000 Base":
                return

        return "unispeed match failed, Granite value: {} not matching Salesforce value: {}".format(
            granite_uni_speed, check_data_unispeed
        )


def compare_diasvctype(granite_data, check_data_svc_type):
    granite_device_tid = granite_data["TID"]
    if re.match(".{9}[WXYZ]W", granite_device_tid.upper()) and "TRANSPORT" not in granite_data["ELEMENT_TYPE"]:
        service_type = granite_data["IPV4_SERVICE_TYPE"]
        if service_type is None:
            service_type = "EMPTY"
        if service_type.upper() == check_data_svc_type.upper():
            if not granite_data.get("IPV4_GLUE_SUBNET") or granite_data["IPV4_GLUE_SUBNET"] is None:
                if check_data_svc_type.lower().strip() != "lan":
                    return "Granite has NO Glue IP value; SalesForce {} is not LAN service type".format(
                        check_data_svc_type
                    )
            else:
                if check_data_svc_type.lower().strip() != "routed":
                    return "Granite has a Glue IP {}; SalesForce must specify ROUTED service type,currently {}".format(
                        granite_data["IPV4_GLUE_SUBNET"], check_data_svc_type
                    )
        else:
            return "Granite Service Type Value: {} not matching Salesforce Service Type value: {}".format(
                granite_data["IPV4_SERVICE_TYPE"], check_data_svc_type
            )


def compare_ipv4(granite_data, check_data_ipv4):
    granite_device_tid = granite_data["TID"]
    if re.match(".{9}[WXYZ]W", granite_device_tid.upper()) and "TRANSPORT" not in granite_data["ELEMENT_TYPE"]:
        granite_cidr = "EMPTY"
        if re.search("/", granite_data["IPV4_ASSIGNED_SUBNETS"]):
            granite_cidr = "/" + granite_data["IPV4_ASSIGNED_SUBNETS"].split(",")[0].split("/")[1]
        if granite_cidr == "EMPTY":
            if re.search("/", granite_data["IPV4_ADDRESS"]):
                granite_cidr = "/" + granite_data["IPV4_ADDRESS"].split(",")[0].split("/")[1]

        if granite_cidr == "EMPTY":
            return "Granite Subnet CIDR Notation is missing"

        sf_cidr = check_data_ipv4.split("=")[0]
        if granite_cidr == sf_cidr:
            return
        else:
            return "Granite Subnet CIDR Notation: {} not matching Salesforce CIDR value: {}".format(
                granite_cidr, sf_cidr
            )


def service_to_codes(service_type):
    service_codes = {
        "Managed Network Switch": [
            "RM661",
            "RM662",
            "RM663",
            "RM664",
            "RM665",
            "RM666",
            "RM667",
            "RM668",
            "RM669",
            "RM670",
            "RM671",
            "RM672",
            "RM626",
            "RM627",
            "RM628",
            "RM629",
            "RM630",
            "RM631",
            "RI273",
        ],
        "Managed Network WiFi": [
            "TBD23",
            "RM632",
            "RM633",
            "RM634",
            "RM635",
            "RM636",
            "RM637",
            "RM638",
            "RM639",
            "RM640",
            "RM641",
            "RM642",
            "RM643",
            "RI275",
        ],
        "Managed Network Camera": [
            "RM675",
            "RM676",
            "RM677",
            "RM678",
            "RM644",
            "RM645",
            "RM646",
            "RM647",
            "RM648",
            "RI274",
        ],
        "Managed Network Edge": [
            "RM600",
            "RM601",
            "RM602",
            "RM603",
            "RM604",
            "RM605",
            "RM606",
            "RM607",
            "RM608",
            "RM609",
            "RM610",
            "RM611",
            "RM612",
            "RM613",
            "RM614",
            "RM615",
            "RM616",
            "RM617",
            "RM618",
            "RM619",
            "RM620",
            "RM621",
            "RI270",
        ],
    }
    return service_codes[service_type]
