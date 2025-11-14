def mock_payload():
    return {
        "circuit_id": "51.L1XX.803170..TWCC",
        "hub_clli_code": "AUSBTX50",
        "z_site_name": "AUSZTXOC_VIRTU FINANCIAL OPERATING /307 CAMP CRAFT RD",
        "bandwidth_value": "100",
        "bandwidth_type": "Mbps",
        "service_location_address": "",
        "product_name_order_info": "",
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
        "service_location_address": "",
        "product_name_order_info": "",
    }


def mock_circuit_path_data(*args):
    return (
        "clli",
        "BURNTX15-TEST//208 E BRIER LN",
        {
            "CIRC_PATH_INST_ID": "1841930",
            "CIRCUIT_NAME": "51.L1XX.816618..CHTR",
            "CIRCUIT_STATUS": "Planned",
            "CIRCUIT_BANDWIDTH": "100 Mbps",
            "CIRCUIT_CATEGORY": "ETHERNET",
            "SERVICE_TYPE": "COM-DIA",
            "A_SITE_NAME": "BURNTX15-TEST//208 E BRIER LN",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_REGION": "TEXAS",
            "A_ADDRESS": "208 E BRIER LN",
            "A_CITY": "BURNET",
            "A_STATE": "TX",
            "A_ZIP": "78611",
            "A_CLLI": "BURNTX15",
            "A_NPA": "512",
            "A_LONGITUDE": "-98.226756",
            "A_LATITUDE": "30.760969",
            "z_site_name": "BURNTX15-TEST//208 E BRIER LN",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_REGION": "TEXAS",
            "Z_ADDRESS": "208 E BRIER LN",
            "Z_CITY": "BURNET",
            "Z_STATE": "TX",
            "Z_ZIP": "78611",
            "z_clli": "BURNTX15",
            "Z_NPA": "512",
            "Z_LONGITUDE": "-98.226756",
            "Z_LATITUDE": "30.760969",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2087500",
        },
    )


def mock_no_granite_records(*args, **kwargs):
    return {
        "instId": "0",
        "retCode": 2,
        "httpCode": 200,
        "retString": "No records found with the specified search criteria...",
    }


def mock_path_elements(*args, **kwargs):
    return [
        {
            "PATH_NAME": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
            "PATH_Z_SITE": "AUSDTXIR-NSM DEV TESTING/HUB SITE/11921 N MOPAC EXPY",
            "PATH_STATUS": "Planned",
        }
    ]


def mock_no_matching_transports(*args, **kwargs):
    return [
        {
            "CIRCUIT_NAME": "51001.GE10.MRFLTX231CW.BURNTX152ZW",
            "CIRCUIT_STATUS": "Live",
            "Z_SITE_NAME": "BURNTX15_BURNET CONSOLIDATED ISD//208 E BRIER LN",
        },
        {
            "CIRCUIT_NAME": "70001.GE1.CHRLNC320QW.AUSZTXOC2ZW",
            "CIRCUIT_STATUS": "Planned",
            "Z_SITE_NAME": "AUSZTXOC-UNDERCOVER TOURIST/200/307 CAMP CRAFT RD",
        },
    ]


def mock_matching_transports(*args, **kwargs):
    return [
        {
            "CIRCUIT_NAME": "51001.GE10.MRFLTX231CW.BURNTX152ZW",
            "CIRCUIT_STATUS": "Live",
            "Z_SITE_NAME": "BURNTX15_BURNET CONSOLIDATED ISD//208 E BRIER LN",
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        },
        {
            "CIRCUIT_NAME": "83001.GE1.MRFLTX230QW.BURNTX153ZW",
            "CIRCUIT_STATUS": "Planned",
            "Z_SITE_NAME": "BURNTX15-TEST//208 E BRIER LN",
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        },
    ]


def mock_1gbps_qfx_port(*args, **kwargs):
    return {
        "SITE_INST_ID": "1236",
        "SITE_NAME": "AUSBTX50_TWC/HUB B-MT LARSON",
        "CLLI": "AUSBTX50",
        "NPA_NXX": "512",
        "EQUIP_INST_ID": "934145",
        "EQUIP_NAME": "AUSBTX500QW/001.0001.004.01/SWT#1",
        "VENDOR": "JUNIPER",
        "MODEL": "QFX5100-96S",
        "TYPE": "SWITCH",
        "FQDN": "AUSBTX500QW.CHTRSE.COM",
        "IP_ADDRESS": "10.4.218.7",
        "SLOT": "4",
        "SLOT_INST_ID": "6895344",
        "CARD_INST_ID": "5019395",
        "PORT_INST_ID": "103221930",
        "PORT_ACCESS_ID": "0/0/4",
        "BANDWIDTH": "1G/10G",
        "OPTIC": "GE",
        "OPTIC_TEMPLATE": "GENERIC SFP LEVEL 1",
    }


def mock_convert_bandwidth_5_mbps(*args, **kwargs):
    return "1 Gbps", "GE", "GENERIC SFP LEVEL 1"


def mock_get_transport_path_data(*args, **kwargs):
    transport_path_data = {
        "path_inst_id": "1823192",
        "leg_name": "1",
        "leg_inst_id": "2067073",
        "z_site_name": "BURNTX15-TEST//208 E BRIER LN",
    }
    return transport_path_data
