import logging


logger = logging.getLogger(__name__)

RESPNOSES_50 = {}

RESPNOSES_60 = {}

RESPNOSES_70 = {}

RESPNOSES_80 = {
    "/v1/ip/swip": {
        "message": "IP SWIP operation completed",
        "IPs Assigned": [
            {"ip": "192.168.0.0/29", "status": "success"},
            {"ip": "2600:FFFF:FFFFF::/48", "status": "success"},
        ],
    },
    "/v1/light_test_check": {
        "port_activation_link": "https://light-test.seek.chtrse.com/light_test/HRMYWIAP0QW/2762838/GE-0/0/50"
    },
    "/v2/circuitpath": {
        "cid": "60.L1XX.994298..CHTR",
        "ethernet_transport": "60001.GE1.HRMYWIAP0QW.MLTNWIBU2ZW",
        "status": "Auto-Designed",
    },
    "/v2/cpe": {"path_inst_id": "2239578", "customer_id": "REGRESSION TESTING"},
    "/v3/ip/static": {
        "ipv4_service_type": "LAN",
        "ipv4_glue_subnet": "",
        "ipv4_assigned_subnets": "192.168.1.0/29",
        "ipv4_assigned_gateway": "192.168.1.1/29",
        "ipv6_service_type": "ROUTED",
        "ipv6_glue_subnet": "2600:FFFF:FFFF::FFFF:FF:FF/127",
        "ipv6_assigned_subnet": "2600:FFFF:FFFF::/48",
    },
    "/v3/pe": {
        "message": "Successful PE Creation",
        "z_address": "9999 REGRESSION AVE",
        "z_city": "REGRESSION",
        "z_state": "TX",
        "z_zip": "78701",
    },
    "/v4/vlan": {"message": "Successful VLAN Assignment"},
}

RESPNOSES_90 = {
    "/v1/isp_update_related_circuits": None,
    "/v2/remedy_ticket": {"work_order": "WO0000009999999"},
    "/v3/transport_path": {
        "transport_path": "99999.GE1.ZZZZZZZZ0QW.ZZZZZZZZ1ZW",
        "message": "Created new transport path",
    },
}


def regression_testing_check(endpoint, cid):
    result = "pass"

    if not isinstance(cid, str):
        return result

    if not all((cid.startswith("51.L1XX.9999"), cid.endswith(".CHTR"))):
        return result

    # try to extract last 2 digits from CID
    try:
        num = int(cid.split(".")[-2][-2:])
    except Exception:
        logger.error(f"Wrong CID format: {cid}")
        return result

    if 49 < num < 60:
        result = RESPNOSES_50.get(endpoint, result)
    elif 59 < num < 70:
        result = RESPNOSES_60.get(endpoint, result)
    elif 69 < num < 80:
        result = RESPNOSES_70.get(endpoint, result)
    elif 79 < num < 90:
        result = RESPNOSES_80.get(endpoint, result)
    elif 89 < num < 100:
        result = RESPNOSES_90.get(endpoint, result)
    else:
        pass

    return result
