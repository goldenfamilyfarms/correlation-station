import pytest

from arda_app.bll.net_new.utils import shelf_utils
from common_sense.common.errors import AbortException


@pytest.mark.unittest
def test_get_zsite(monkeypatch):
    cid = "71.L1XX.013079..CHTR"
    site_info = {
        "CIRC_PATH_INST_ID": "2453128",
        "CIRCUIT_NAME": "71.L1XX.013079..CHTR",
        "CIRCUIT_STATUS": "Live",
        "CIRCUIT_BANDWIDTH": "100 Mbps",
        "CIRCUIT_CATEGORY": "ETHERNET",
        "NEXT_PATH_INST_ID": "0",
        "SERVICE_TYPE": "COM-DIA",
        "ORDER_NUM": "COM-FIA-126505,ENG-03758647",
        "ORDERED": "MAR 16, 2023",
        "IN_SERVICE": "MAR 25, 2023",
        "DECOMMISSION": "JAN 03, 2024",
        "A_SITE_NAME": "BFLONYKK-TWC/HUB BC-CHICAGO ST (BUFFNYCHG)",
        "A_SITE_TYPE": "HUB",
        "A_SITE_MARKET": "WESTERN NEW YORK",
        "A_SITE_REGION": "NORTHEAST",
        "A_ADDRESS": "355 CHICAGO ST",
        "A_CITY": "BUFFALO",
        "A_STATE": "NY",
        "A_ZIP": "14204",
        "A_CLLI": "BFLONYKK",
        "A_NPA": "716",
        "A_LONGITUDE": "-78.866250",
        "A_LATITUDE": "42.877805",
        "Z_SITE_NAME": "BFLRNYZV-CAR TEAM//199 SCOTT ST",
        "Z_SITE_TYPE": "LOCAL",
        "Z_SITE_MARKET": "WESTERN NEW YORK",
        "Z_SITE_REGION": "NORTHEAST",
        "Z_ADDRESS": "199 SCOTT ST",
        "Z_CITY": "BUFFALO",
        "Z_STATE": "NY",
        "Z_ZIP": "14204",
        "Z_COMMENTS": "== Inserted via REST Web Service ==",
        "Z_CLLI": "BFLRNYZV",
        "Z_NPA": "716",
        "Z_LONGITUDE": "-78.869291",
        "Z_LATITUDE": "42.875621",
        "LEG_NAME": "1",
        "LEG_INST_ID": "2824268",
    }
    monkeypatch.setattr(shelf_utils, "get_granite", lambda *args, **kwargs: site_info)
    assert shelf_utils.get_zsite(cid)


@pytest.mark.unittest
def test_get_cpe_transport_paths(monkeypatch):
    device = "BFLRNYZV3ZW"
    shelf_info = [
        {
            "SITE_NAME": "BFLRNYZV-CAR TEAM//199 SCOTT ST",
            "SITE_INST_ID": "829134",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "BFLRNYZV",
            "EQUIP_NAME": "BFLRNYZV3ZW/999.9999.999.99/SWT",
            "EQUIP_INST_ID": "1755518",
            "EQUIP_CATEGORY": "SWITCH",
            "EQUIP_STATUS": "Live",
            "EQUIP_VENDOR": "ADVA",
            "EQUIP_MODEL": "FSP 150-GE114PRO-C",
            "FQDN": "BFLRNYZV3ZW.CML.CHTRSE.COM",
            "TARGET_ID": "BFLRNYZV3ZW",
            "IPV4_ADDRESS": "10.12.250.183/24",
            "SLOT": "01",
            "PARENT_SLOT": "CHASSIS PORTS",
            "SLOT_INST_ID": "14498532",
            "CARD_DESCRIPTION": "GENERIC SFP",
            "CARD_INST_ID": "8971162",
            "CARD_STATUS": "Live",
            "CARD_TEMPLATE_NAME": "ADVA GENERIC SFP LEVEL 1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "114969193",
            "PORT_STATUS": "Assigned",
            "PORT_ACCESS_ID": "NETWORK-1-1-1-1",
            "BANDWIDTH": "1 Gbps",
            "USED": "IN USE",
            "CURRENT_PATH_NAME": "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW",
            "CURRENT_PATH_INST": "2469550",
            "OBJECT_TYPE": "PORT",
        },
        {
            "SITE_NAME": "BFLRNYZV-CAR TEAM//199 SCOTT ST",
            "SITE_INST_ID": "829134",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "BFLRNYZV",
            "EQUIP_NAME": "BFLRNYZV3ZW/999.9999.999.99/SWT",
            "EQUIP_INST_ID": "1755518",
            "EQUIP_CATEGORY": "SWITCH",
            "EQUIP_STATUS": "Live",
            "EQUIP_VENDOR": "ADVA",
            "EQUIP_MODEL": "FSP 150-GE114PRO-C",
            "FQDN": "BFLRNYZV3ZW.CML.CHTRSE.COM",
            "TARGET_ID": "BFLRNYZV3ZW",
            "IPV4_ADDRESS": "10.12.250.183/24",
            "SLOT": "CHASSIS PORTS",
            "SLOT_INST_ID": "14498531",
            "CARD_DESCRIPTION": "ADVA FSP 150CC-GE114PRO CHASSIS PORTS",
            "CARD_INST_ID": "8971161",
            "CARD_STATUS": "Live",
            "CARD_TEMPLATE_NAME": "ADVA FSP 150CC-GE114PRO CHASSIS PORTS",
            "PORT_NAME": "03",
            "PORT_INST_ID": "114969196",
            "PORT_STATUS": "Assigned",
            "PORT_ACCESS_ID": "ACCESS-1-1-1-3",
            "BANDWIDTH": "10/100/1000 BASET",
            "USED": "IN USE",
            "CURRENT_PATH_NAME": "71.L1XX.013079..CHTR",
            "CURRENT_PATH_INST": "2453128",
            "OBJECT_TYPE": "PORT",
        },
    ]
    z_site_info = {
        "CIRC_PATH_INST_ID": "2453128",
        "CIRCUIT_NAME": "71.L1XX.013079..CHTR",
        "CIRCUIT_STATUS": "Live",
        "CIRCUIT_BANDWIDTH": "100 Mbps",
        "CIRCUIT_CATEGORY": "ETHERNET",
        "NEXT_PATH_INST_ID": "0",
        "SERVICE_TYPE": "COM-DIA",
        "ORDER_NUM": "COM-FIA-126505,ENG-03758647",
        "ORDERED": "MAR 16, 2023",
        "IN_SERVICE": "MAR 25, 2023",
        "DECOMMISSION": "JAN 03, 2024",
        "A_SITE_NAME": "BFLONYKK-TWC/HUB BC-CHICAGO ST (BUFFNYCHG)",
        "A_SITE_TYPE": "HUB",
        "A_SITE_MARKET": "WESTERN NEW YORK",
        "A_SITE_REGION": "NORTHEAST",
        "A_ADDRESS": "355 CHICAGO ST",
        "A_CITY": "BUFFALO",
        "A_STATE": "NY",
        "A_ZIP": "14204",
        "A_CLLI": "BFLONYKK",
        "A_NPA": "716",
        "A_LONGITUDE": "-78.866250",
        "A_LATITUDE": "42.877805",
        "Z_SITE_NAME": "BFLRNYZV-CAR TEAM//199 SCOTT ST",
        "Z_SITE_TYPE": "LOCAL",
        "Z_SITE_MARKET": "WESTERN NEW YORK",
        "Z_SITE_REGION": "NORTHEAST",
        "Z_ADDRESS": "199 SCOTT ST",
        "Z_CITY": "BUFFALO",
        "Z_STATE": "NY",
        "Z_ZIP": "14204",
        "Z_COMMENTS": "== Inserted via REST Web Service ==",
        "Z_CLLI": "BFLRNYZV",
        "Z_NPA": "716",
        "Z_LONGITUDE": "-78.869291",
        "Z_LATITUDE": "42.875621",
        "LEG_NAME": "1",
        "LEG_INST_ID": "2824268",
    }
    expected = {
        "BFLRNYZV3ZW": [
            ["71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW", "ADVA", "FSP 150-GE114PRO-C"],
            ["71.L1XX.013079..CHTR", "ADVA", "FSP 150-GE114PRO-C"],
        ]
    }
    monkeypatch.setattr(shelf_utils, "get_shelf_used_ports", lambda *args, **kwargs: shelf_info)
    assert shelf_utils.get_cpe_transport_paths(device, z_site_info) == expected


@pytest.mark.unittest
def test_get_cpe_services():
    shelf_dict = {
        "BFLRNYZV3ZW": [
            ["71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW", "ADVA", "FSP 150-GE114PRO-C"],
            ["71.L1XX.013079..CHTR", "ADVA", "FSP 150-GE114PRO-C"],
        ]
    }
    shelf_info, cids = ("BFLRNYZV3ZW", "ADVA", "FSP 150-GE114PRO-C"), ["71.L1XX.013079..CHTR"]
    assert shelf_utils.get_cpe_services(shelf_dict) == (shelf_info, cids)


@pytest.mark.unittest
def test_check_and_add_existing_transport(monkeypatch):
    # good test with existing transport return None
    monkeypatch.setattr(shelf_utils, "get_granite", lambda *args, **kwargs: [])
    assert shelf_utils.check_and_add_existing_transport("test_cid") is None

    # bad find existing transport with Live status abort
    monkeypatch.setattr(shelf_utils, "get_granite", lambda *args, **kwargs: {})
    path_data = {"Z_CLLI": "AUSTXDRE", "Z_SITE_NAME": "123 Test Dr", "CIRC_PATH_INST_ID": "1234567"}
    transport_data = {"Z_SITE_NAME": "123 Test Dr", "CIRCUIT_STATUS": "Live"}
    circuit_site_info = iter([[path_data], [transport_data]])
    monkeypatch.setattr(shelf_utils, "get_circuit_site_info", lambda *args, **kwargs: next(circuit_site_info))

    with pytest.raises(Exception):
        assert shelf_utils.check_and_add_existing_transport("test_cid") is None

    # good find existing transport with non Live status return None
    transport_data = {"Z_SITE_NAME": "123 Test Dr", "CIRCUIT_STATUS": "Designed"}
    circuit_site_info = iter([[path_data], [transport_data]])
    resp = {"retString": "Path Updated"}
    monkeypatch.setattr(shelf_utils, "_granite_add_path_elements", lambda *args, **kwargs: resp)
    assert shelf_utils.check_and_add_existing_transport("test_cid") is None

    # bad failed on adding existing transport with non live status to cid
    circuit_site_info = iter([[path_data], [transport_data]])
    resp = {"retString": "Failed to Update"}

    with pytest.raises(Exception):
        assert shelf_utils.check_and_add_existing_transport("test_cid") is None

    # multiple existing transport paths abort
    circuit_site_info = iter([[path_data], [transport_data, transport_data]])

    with pytest.raises(Exception):
        assert shelf_utils.check_and_add_existing_transport("test_cid") is None

    # no existing transport path abort
    circuit_site_info = iter([[path_data], []])

    with pytest.raises(Exception):
        assert shelf_utils.check_and_add_existing_transport("test_cid") is None


@pytest.mark.unittest
def test_granite_add_path_elements(monkeypatch):
    path_elements_data = {"CIRC_PATH_INST_ID": "test_inst_id", "LEG_NAME": "LEG_NAME", "LEG_INST_ID": "LEG_INST_ID"}

    monkeypatch.setattr(shelf_utils, "put_granite", lambda *args, **kwargs: None)
    assert shelf_utils._granite_add_path_elements("test_cid", "test_inst_id", path_elements_data) is None


@pytest.mark.unittest
def test_get_circuit_side_info(monkeypatch):
    cid = "77.L1XX.002735..CHTR"
    cid_data = [
        {
            "aSideCustomer": "ACCT-25268196",
            "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "bandwidth": "50 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-25268196",
            "orderNumber": "D-ENG-8675309,D-ENG-8675309,D-ENG-8675309",
            "pathId": "77.L1XX.002735..CHTR",
            "pathInService": "2023-11-21 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "COM-EPL",
            "servicePriority": "NO",
            "status": "Pending Decommission",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-25268196",
            "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "0",
            "pathInstanceId": "2564904",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ]
    expected = {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
    }
    monkeypatch.setattr(shelf_utils, "get_network_path", lambda *args, **kwargs: cid_data)
    assert shelf_utils.get_circuit_side_info(cid) == expected

    # generate fall-out condition
    empty_cid_data = []
    monkeypatch.setattr(shelf_utils, "get_network_path", lambda *args, **kwargs: empty_cid_data)
    try:
        shelf_utils.get_circuit_side_info(cid)
    except AbortException as e:
        assert "Unable to retrieve circuit data" in e.data["message"]


@pytest.mark.unittest
def test_get_cpe_side_info():
    devices = {
        "RENRNVYB1ZW": "ETH PORT 4",
        "STEDNVRR3ZW": "ETH PORT 3",
        "RENQNVLX1QW": "GE-0/0/49",
        "RENQNVLX1CW": "AE17",
        "RENQNVLX0QW": "GE-0/0/34",
    }
    truncated_path_elements = [
        {
            "PATH_NAME": "77.L1XX.002735..CHTR",
            "A_SITE_NAME": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "ELEMENT_NAME": "RENRNVYB1ZW/999.9999.999.99/NIU",
            "PORT_ACCESS_ID": "ETH PORT 4",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "TID": "RENRNVYB1ZW",
        },
        {
            "PATH_NAME": "77.L1XX.002735..CHTR",
            "A_SITE_NAME": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "ELEMENT_NAME": "STEDNVRR3ZW/999.9999.999.99/NIU",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "TID": "STEDNVRR3ZW",
        },
    ]
    circuit_data = {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
    }
    expected = {
        "a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP"),
        "z_side_cpe": ("STEDNVRR3ZW", "ETX203AX/2SFP/2UTP2SFP"),
    }
    assert shelf_utils.get_cpe_side_info(devices, truncated_path_elements, circuit_data) == expected

    # generate fall-out condition
    empty_path_elements = []
    try:
        shelf_utils.get_cpe_side_info(devices, empty_path_elements, circuit_data)
    except AbortException as e:
        assert "Unable to designate which side a ZW device belongs to" in e.data["message"]


@pytest.mark.unittest
def test_get_cpe_at_service_location(monkeypatch):
    service_location_address = "4615 ECHO AVE"
    circuit_data = {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
    }
    cpe_per_side = {
        "a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP"),
        "z_side_cpe": ("STEDNVRR3ZW", "ETX203AX/2SFP/2UTP2SFP"),
    }
    expected = {"a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP")}
    assert shelf_utils.get_cpe_at_service_location(service_location_address, circuit_data, cpe_per_side) == expected

    # generate faulty conditions
    cpe_missing_a_side = {"z_side_cpe": ("STEDNVRR3ZW", "ETX203AX/2SFP/2UTP2SFP")}
    empty_a_side_cpe = {"a_side_cpe": ()}
    assert (
        shelf_utils.get_cpe_at_service_location(service_location_address, circuit_data, cpe_missing_a_side)
        == empty_a_side_cpe
    )

    incorrect_service_location_address = "11921 N. Mopac Expressway"
    try:
        shelf_utils.get_cpe_at_service_location(incorrect_service_location_address, circuit_data, cpe_per_side)
    except AbortException as e:
        assert "Unable to determine ZW device at" in e.data["message"]

    ratio = iter([70, 75, 85, 85])
    monkeypatch.setattr(shelf_utils.fuzz, "partial_ratio", lambda *args, **kwargs: next(ratio))
    try:
        shelf_utils.get_cpe_at_service_location(service_location_address, circuit_data, cpe_per_side)
    except AbortException as e:
        assert "Unable to determine ZW device at" in e.data["message"]
    try:
        shelf_utils.get_cpe_at_service_location(service_location_address, circuit_data, cpe_per_side)
    except AbortException as e:
        assert "Unable to distinguish which ZW device services" in e.data["message"]


@pytest.mark.unittest
def test_switch_sites_for_each_side():
    switch_site_info = [
        {
            "A_SITE_NAME": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "A_SITE_REGION": "NORTHWEST",
            "A_ADDRESS": "4615 ECHO AVE",
            "A_CITY": "RENO",
            "A_STATE": "NV",
            "A_ZIP": "89506",
            "A_COMMENTS": "= Inserted via REST Web Service ==  CPE: RAD 203 1.Floor: 1st  2.Suite/RM: electrical room",
            "A_CLLI": "RENRNVYB",
            "A_NPA": "775",
            "A_LONGITUDE": "-119.87078",
            "A_LATITUDE": "39.653391",
            "Z_SITE_NAME": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "Z_SITE_REGION": "NORTHWEST",
            "Z_ADDRESS": "14100 LEAR BLVD",
            "Z_CITY": "STEAD",
            "Z_STATE": "NV",
            "Z_ZIP": "89506",
            "Z_CLLI": "STEDNVRR",
            "Z_NPA": "775",
            "Z_LONGITUDE": "-119.893003",
            "Z_LATITUDE": "39.642515",
        }
    ]
    expected = [
        {
            "A_SITE_NAME": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "A_SITE_REGION": "NORTHWEST",
            "A_ADDRESS": "14100 LEAR BLVD",
            "A_CITY": "STEAD",
            "A_STATE": "NV",
            "A_ZIP": "89506",
            "A_COMMENTS": "",
            "A_CLLI": "STEDNVRR",
            "A_NPA": "775",
            "A_LONGITUDE": "-119.893003",
            "A_LATITUDE": "39.642515",
            "Z_SITE_NAME": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_MARKET": "NORTHERN CALIFORNIA-NEVADA",
            "Z_SITE_REGION": "NORTHWEST",
            "Z_ADDRESS": "4615 ECHO AVE",
            "Z_CITY": "RENO",
            "Z_STATE": "NV",
            "Z_ZIP": "89506",
            "Z_CLLI": "RENRNVYB",
            "Z_NPA": "775",
            "Z_LONGITUDE": "-119.87078",
            "Z_LATITUDE": "39.653391",
            "Z_COMMENTS": "= Inserted via REST Web Service ==  CPE: RAD 203 1.Floor: 1st  2.Suite/RM: electrical room",
        }
    ]
    assert shelf_utils.switch_sites_for_each_side(switch_site_info) == expected


@pytest.mark.unittest
def test_get_vgw_shelf_info(monkeypatch):
    pathid = "31.IPXN.001093..CHTR"

    data = [
        {
            "CIRC_PATH_INST_ID": "2570846",
            "PATH_NAME": "31.IPXN.001093..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "PRI TRUNKS",
            "PATH_A_SITE": "GENVNYAA-TWC/HUB GE-GENEVA (NY) (ROCHNYGNV)",
            "PATH_Z_SITE": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "A_CLLI": "GENVNYAA",
            "Z_CLLI": "GENVNYEA",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-PRI",
            "BANDWIDTH": "10 Mbps",
            "BW_SIZE": "10000000",
            "CUSTOMER_ID": "ACCT-00596242",
            "CUSTOMER_NAME": "LYONS NATIONAL BANK",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2979075",
            "A_SITE_NAME": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "GENVNYEA1ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "715729",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "CHASSIS PORTS",
            "PORT_NAME": "NETWORK PORT-1-1-1-2",
            "PORT_INST_ID": "97164933",
            "PORT_ACCESS_ID": "ACCESS-1-1-1-2",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "GENVNYEA1ZW.CML.CHTRSE.COM",
            "MODEL": "FSP 150CC-GE114/114S",
            "VENDOR": "ADVA",
            "TID": "GENVNYEA1ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.91.133/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1309",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "31.IPXN.001093..CHTR",
            "INITIAL_CIRCUIT_ID": "2570846",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2570846",
            "PATH_NAME": "31.IPXN.001093..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "PRI TRUNKS",
            "PATH_A_SITE": "GENVNYAA-TWC/HUB GE-GENEVA (NY) (ROCHNYGNV)",
            "PATH_Z_SITE": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "A_CLLI": "GENVNYAA",
            "Z_CLLI": "GENVNYEA",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-PRI",
            "BANDWIDTH": "10 Mbps",
            "BW_SIZE": "10000000",
            "CUSTOMER_ID": "ACCT-00596242",
            "CUSTOMER_NAME": "LYONS NATIONAL BANK",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "5.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "5",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2979075",
            "A_SITE_NAME": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "GENVNYEAG2W/999.9999.999.99/RTR",
            "ELEMENT_REFERENCE": "1817687",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED ETHERNET PORTS",
            "PORT_NAME": "WAN",
            "PORT_INST_ID": "115715982",
            "PORT_ACCESS_ID": "WAN",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": "DYNAMIC",
            "FQDN": "GENVNYEAG2W.CHTRSE.COM",
            "MODEL": "M500",
            "VENDOR": "AUDIOCODES",
            "TID": "GENVNYEAG2W",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "50.75.87.154/30",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.IPXN.001093..CHTR",
            "INITIAL_CIRCUIT_ID": "2570846",
            "LVL": "1",
        },
    ]

    vgw_shelf = {
        "SHELF_NAME": "GENVNYEAG2W",
        "VENDOR": "AUDIOCODES",
        "MODEL": "M500",
        "CIRC_PATH_INST_ID": "2570846",
        "IPV4_ADDRESS": "50.75.87.154/30",
    }

    monkeypatch.setattr(shelf_utils, "get_path_elements", lambda *args, **kwargs: data)

    assert shelf_utils.get_vgw_shelf_info(pathid) == vgw_shelf
