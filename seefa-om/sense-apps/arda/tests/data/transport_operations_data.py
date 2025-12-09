from requests.models import Response


def mock_payload():
    return {
        "circuit_id": "51.L1XX.803170..TWCC",
        "hub_clli_code": "AUSBTX50",
        "z_site_name": "AUSZTXOC_VIRTU FINANCIAL OPERATING /307 CAMP CRAFT RD",
        "bandwidth_value": "100",
        "bandwidth_type": "Mbps",
    }


def mock_payload_1gbps():
    return {
        "circuit_id": "51.L1XX.803170..TWCC",
        "hub_clli_code": "AUSBTX50",
        "z_site_name": "AUSZTXOC_VIRTU FINANCIAL OPERATING /307 CAMP CRAFT RD",
        "bandwidth_value": "1",
        "bandwidth_type": "Gbps",
    }


def mock_payload_5gbps():
    return {
        "circuit_id": "51.L1XX.803170..TWCC",
        "hub_clli_code": "AUSBTX50",
        "z_site_name": "AUSZTXOC_VIRTU FINANCIAL OPERATING /307 CAMP CRAFT RD",
        "bandwidth_value": "5",
        "bandwidth_type": "Gbps",
    }


def mock_no_existing_transports(n, m=0):
    return {
        "instId": "0",
        "retCode": 2,
        "httpCode": 200,
        "retString": "No records found with the specified search criteria...",
    }


def mock_matching_transport(n, m=0):
    return [
        {
            "CIRC_PATH_INST_ID": "1943668",
            "CIRCUIT_NAME": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
            "Z_SITE_NAME": "AUSZTXOC_VIRTU FINANCIAL OPERATING /307 CAMP CRAFT RD",
            "Z_CLLI": "AUSZTXOC",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2203286",
            "CIRCUIT_STATUS": "Decommissioned",
        }
    ]


def mock_no_matching_transports(n, m=0):
    return [
        {
            "CIRCUIT_NAME": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
            "z_site_name": "AUSDTXIR-NSM DEV TESTING/HUB SITE/11921 N MOPAC EXPY",
        }
    ]


def mock_npa_good(n):
    return [{"NPA_NXX": "512"}]


def mock_shelf_good(n):
    return [{"SHELF": "AUSZTXOC2ZW"}]


def mock_circuit_path_data_good(n):
    return [
        {
            "CIRC_PATH_INST_ID": "1592711",
            "CIRCUIT_NAME": "51.L1XX.803170..TWCC",
            "A_SITE_NAME": "AUSBTX50_TWC/HUB B-MT LARSON",
            "A_SITE_TYPE": "HUB",
            "A_SITE_REGION": "TEXAS",
            "A_ADDRESS": "901 MT LARSON RD",
            "A_CITY": "AUSTIN",
            "A_STATE": "TX",
            "A_ZIP": "78746",
            "A_CLLI": "AUSBTX50",
            "A_LONGITUDE": "-97.789099",
            "A_LATITUDE": "30.300923",
            "Z_SITE_NAME": "AUSZTXOC-UNDERCOVER TOURIST/200/307 CAMP CRAFT RD",
            "Z_SITE_TYPE": "LOCAL",
            "Z_ADDRESS": "307 CAMP CRAFT RD",
            "Z_CITY": "WEST LAKE HILLS",
            "Z_STATE": "TX",
            "Z_ZIP": "78746",
            "Z_CLLI": "AUSZTXOC",
            "Z_LONGITUDE": "-97.812225",
            "Z_LATITUDE": "30.280277",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1808821",
        }
    ]


def mock_get_circuit_path_info(n):
    return {
        "z_site_name": "AUSZTXOC-UNDERCOVER TOURIST/200/307 CAMP CRAFT RD",
        "a_site_name": "AUSBTX50_TWC/HUB B-MT LARSON",
        "path_inst_id": "1592711",
        "leg_name": "1",
        "leg_inst_id": "1808821",
        "z_clli": "AUSZTXOC",
    }


def mock_get_uplink_port(n):
    return {
        "SITE_INST_ID": "393412",
        "SITE_NAME": "AUSDTXIR-NSM DEV TESTING/HUB SITE/11921 N MO PAC EXPY",
        "CLLI": "AUSDTXIR",
        "NPA_NXX": "512",
        "EQUIP_INST_ID": "941785",
        "EQUIP_NAME": "AUSDTXIR2QW/003.0000.LAB.00/SWT#2",
        "VENDOR": "JUNIPER",
        "MODEL": "QFX5100-96S",
        "TYPE": "SWITCH",
        "FQDN": "AUSDTXIR2QW.DEV.CHTRSE.COM",
        "IP_ADDRESS": "71.42.150.235",
        "SLOT": "7",
        "SLOT_INST_ID": "7039480",
        "CARD_INST_ID": "6827292",
        "PORT_INST_ID": "109197874",
        "PORT_ACCESS_ID": "1/0/7",
        "OPTIC": "XE",
    }


def mock_post_transport_path_200(n, m):
    response = Response()
    response.status_code = 200
    response._content = b'{ \
        "pathId": "51001.GE1.AUSBTX500QW.AUSZTXOC4ZW", \
        "pathRev": "1", \
        "status": "Live", \
        "pathInstanceId": "1618083", \
        "retString": "Path Updated" }'
    return response


def mock_transport_path_data_good(n):
    return [
        {
            "CIRC_PATH_INST_ID": "1618083",
            "CIRCUIT_NAME": "51001.GE1.AUSBTX500QW.AUSZTXOC4ZW",
            "A_SITE_NAME": "AUSBTX50_TWC/HUB B-MT LARSON",
            "A_SITE_TYPE": "HUB",
            "A_SITE_REGION": "TEXAS",
            "A_ADDRESS": "901 MT LARSON RD",
            "A_CITY": "AUSTIN",
            "A_STATE": "TX",
            "A_ZIP": "78746",
            "A_CLLI": "AUSBTX50",
            "A_LONGITUDE": "-97.789099",
            "A_LATITUDE": "30.300923",
            "Z_SITE_NAME": "AUSZTXOC-UNDERCOVER TOURIST/200/307 CAMP CRAFT RD",
            "Z_SITE_TYPE": "LOCAL",
            "Z_ADDRESS": "307 CAMP CRAFT RD",
            "Z_CITY": "WEST LAKE HILLS",
            "Z_STATE": "TX",
            "Z_ZIP": "78746",
            "Z_CLLI": "AUSZTXOC",
            "Z_LONGITUDE": "-97.812225",
            "Z_LATITUDE": "30.280277",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1837240",
        }
    ]


def mock_put_reserve_port_200(n, m):
    response = Response()
    response.status_code = 200
    response._content = b'{\
        "status_code": 200, \
        "pathId": "86.L1XX.990297..CHTR", \
        "pathRev": "1", \
        "status": "WEB SERVICE", \
        "pathInstanceId": "1842515", \
        "retString": "Path Updated"}'
    return response


def mock_add_path_elements_200(n, m):
    response = Response()
    response.status_code = 200
    response._content = b'{\
        "status_code": 200, \
        "pathId": "51.L1XX.816645..CHTR", \
        "pathRev": "1", \
        "status": "WEB SERVICE", \
        "pathInstanceId": "1843794", \
        "retString": "Path Added"}'
    return response
