def mock_payload_no_epl():
    return {
        "related_circuit_ids": [{"circuit_id": "51.L1XX.008342..CHTR", "product_name_order_info": "Ethernet"}],
        "transport_path": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
        "service_location_address": "24219 Railroad Ave Newhall CA 91321",
    }


def mock_payload_epl_no_address_match():
    return {
        "related_circuit_ids": [{"circuit_id": "51.L1XX.008342..CHTR", "product_name_order_info": "EPL (Fiber)"}],
        "transport_path": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
        "service_location_address": "1234 Mock Address",
    }


def mock_payload_epl_a_address():
    return {
        "related_circuit_ids": [{"circuit_id": "51.L1XX.008342..CHTR", "product_name_order_info": "EPL (Fiber)"}],
        "transport_path": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
        "service_location_address": "24219 Railroad Ave Newhall CA 91321",
    }


def mock_payload_evpl_z_addresss():
    return {
        "related_circuit_ids": [{"circuit_id": "51.L1XX.008342..CHTR", "product_name_order_info": "EVPL (Fiber)"}],
        "transport_path": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
        "service_location_address": "208 E BRIER LN",
    }


def mock_path_elements(*args, **kwargs):
    return [
        {
            "PATH_NAME": "51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW",
            "PATH_Z_SITE": "AUSDTXIR-NSM DEV TESTING/HUB SITE/11921 N MOPAC EXPY",
            "PATH_STATUS": "Planned",
        }
    ]


def mock_circuit_path_data(*args):
    return {
        "CIRC_PATH_INST_ID": "1841930",
        "CIRCUIT_NAME": "51.L1XX.816618..CHTR",
        "CIRCUIT_STATUS": "Planned",
        "CIRCUIT_BANDWIDTH": "100 Mbps",
        "CIRCUIT_CATEGORY": "ETHERNET",
        "SERVICE_TYPE": "COM-DIA",
        "A_SITE_NAME": "BURNTX15-TEST//208 E BRIER LN",
        "A_SITE_TYPE": "LOCAL",
        "A_SITE_REGION": "TEXAS",
        "A_ADDRESS": "24219 Railroad Ave Newhall CA 91321",
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
    }


def mock_get_transport_path_data(*args, **kwargs):
    transport_path_data = {
        "path_inst_id": "1823192",
        "leg_name": "1",
        "leg_inst_id": "2067073",
        "z_site_name": "BURNTX15-TEST//208 E BRIER LN",
    }
    return transport_path_data
