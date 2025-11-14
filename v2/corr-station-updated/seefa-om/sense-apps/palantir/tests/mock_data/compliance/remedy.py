test_isp_required_sites_fia = {"z": {"address": "1234 Alden Marshall Pkwy Austin TX 78759"}}


test_isp_required_sites_eline = {
    "z": {"address": "1208 S KINGSHIGHWAY ST 63703"},
    "a": {"address": "1015 LOCUST ST 63101"},
}


test_endpoint_data_fia_full = {
    "z_side_disconnect": "FULL",
    "z_side_endpoint": "CNI5TXR38ZW",
    "z_side_address": "1234 Alden Marshall Pkwy Austin TX 78759",
    "a_side_disconnect": None,
    "a_side_endpoint": None,
    "a_side_address": None,
    "optic_slotted": True,
    "isp_required_sites": test_isp_required_sites_fia,
}

test_site_order_data_fia = [
    {"engineering_page": "ENG-01234567", "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759"}
]


test_endpoint_data_fia_full_mismatched_address = {
    "z_side_disconnect": "FULL",
    "z_side_endpoint": "CNI5TXR38ZW",
    "z_side_address": "1234 Alden Marshall Pkwy Austin TX 78759",
    "a_side_disconnect": None,
    "a_side_endpoint": None,
    "a_side_address": None,
    "optic_slotted": True,
    "site_order_data": [{"engineering_page": "ENG-01234567", "service_location_address": "9999 Mismatch Ave"}],
    "isp_required_sites": test_isp_required_sites_fia,
}

test_endpoint_data_eline_partial_full = {
    "z_side_disconnect": "FULL",
    "z_side_endpoint": "CNI5TXR38ZW",
    "z_side_address": "1234 Alden Marshall Pkwy Austin TX 78759",
    "a_side_disconnect": "PARTIAL",
    "a_side_endpoint": "AUSDTXIR2CW",
    "a_side_address": "334 Moonbeam Ave Austin TX 78759",
    "optic_slotted": True,
    "site_order_data": [
        {"engineering_page": "ENG-01234567", "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759"},
        {"engineering_page": "ENG-12345678", "service_location_address": "334 Moonbeam Ave Austin TX 78759"},
    ],
    "isp_required_sites": test_isp_required_sites_fia,
}

test_endpoint_data_eline_full_partial = {
    "z_side_disconnect": "PARTIAL",
    "z_side_endpoint": "CNI5TXR38ZW",
    "z_side_address": "1234 Alden Marshall Pkwy Austin TX 78759",
    "a_side_disconnect": "FULL",
    "a_side_endpoint": "AUSDTXIR2CW",
    "a_side_address": "334 Moonbeam Ave Austin TX 78759",
    "optic_slotted": True,
    "site_order_data": [
        {"engineering_page": "ENG-01234567", "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759"},
        {"engineering_page": "ENG-12345678", "service_location_address": "334 Moonbeam Ave Austin TX 78759"},
    ],
    "isp_required_sites": test_isp_required_sites_fia,
}

test_endpoint_data_eline_full_full = {
    "z_side_disconnect": "FULL",
    "z_side_endpoint": "CNI5TXR38ZW",
    "z_side_address": "1234 Alden Marshall Pkwy Austin TX 78759",
    "a_side_disconnect": "FULL",
    "a_side_endpoint": "AUS6TXIR2ZW",
    "a_side_address": "334 Moonbeam Ave Austin TX 78759",
    "optic_slotted": True,
    "site_order_data": [
        {"engineering_page": "ENG-01234567", "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759"},
        {"engineering_page": "ENG-12345678", "service_location_address": "334 Moonbeam Ave Austin TX 78759"},
    ],
    "isp_required_sites": test_isp_required_sites_eline,
}


test_endpoint_data_eline_full_full_create = {
    "z_side_disconnect": "FULL",
    "z_side_endpoint": "CPGRMORR1ZW",
    "z_side_address": "1234 Alden Marshall Pkwy Austin TX 78759",
    "a_side_disconnect": "FULL",
    "a_side_endpoint": "STLSMOPL1CW",
    "a_side_address": "334 Moonbeam Ave Austin TX 78759",
    "optic_slotted": True,
    "isp_required_sites": test_isp_required_sites_eline,
}

test_site_order_data_eline_full_full = [
    {"engineering_page": "ENG-01234567", "service_location_address": "1234 Alden Marshall Pkwy Austin TX 78759"},
    {"engineering_page": "ENG-12345678", "service_location_address": "334 Moonbeam Ave Austin TX 78759"},
]

test_endpoint_data_wavelength = {"z_side_target_wavelength": "1310 nm"}

test_granite_data = {
    "z": {
        "shelf_id": "734656",
        "site_id": "349879",
        "transport_data": [
            {
                "aSideSiteName": "NYCLNYRG-TWC/HUB C-MANHATTAN",
                "bandwidth": "1 Gbps",
                "category": "ETHERNET TRANSPORT",
                "gia_UDA": "NO",
                "off_NetFacility_UDA": "NO",
                "pathId": "21001.GE1.NYCLNYRG2QW.NYCNNYBU1ZW",
                "pathInService": "2020-08-27 12:00:00.0",
                "pathRev": "1",
                "product_Service_UDA": "INT-ACCESS TO PREM TRANSPORT",
                "servicePriority": "NO",
                "status": "Pending Decommission",
                "topology": "P",
                "tspChildPresent_UDA": "NO",
                "zSideSiteName": "NYCNNYBU-UNIVERSAL MUSIC GROUP/FL8/1755 BROADWAY",
                "instanceProtocol": "9999",
                "pathInstanceId": "1849261",
                "serviceMedia": "FIBER",
                "startChanNbr": "1",
                "virtualChans": "D",
            }
        ],
        "element_data": {
            "customer_name": "COGENT COMMUNICATIONS, INC-CHTR-ICOMS",
            "hub_clli": "OWTNMN02",
            "hub_site": "FRBLMNAK-DAIKIN APPLIED AMERICAS I//300 24TH ST NW",
            "port_access_id": "GE-0/0/29",
            "upstream_device": "OWTNMN020QW",
            "upstream_handoff": "OWTNMN020QW:GE-0/0/29",
        },
    },
    "path_data": [
        {
            "aSideCustomer": "ATT WIRELINE",
            "aSideSiteName": "NYCMNYBW-ATT WIRELINE/WIRELESS//33 THOMAS ST",
            "bandwidth": "100 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ATT WIRELINE",
            "orderNumber": "ENG-02331148,D-ENG-03777705",
            "pathId": "21.L1XX.990582..TWCC",
            "pathInService": "2022-06-03 12:00:00.0",
            "pathRev": "2",
            "pathScheduled": "2021-12-30 12:00:00.0",
            "product_Service_UDA": "CAR-E-ACCESS FIBER/FIBER EPL",
            "servicePriority": "NO",
            "status": "Pending Decommission",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ATT WIRELINE",
            "zSideSiteName": "NYCNNYBU-UNIVERSAL MUSIC GROUP/FL8/1755 BROADWAY",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "1",
            "pathInstanceId": "2031650",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ],
    "cid": "21.L1XX.990582..TWCC",
}


test_granite_data_double = {
    "z": {
        "shelf_id": "1792032",
        "site_id": "843789",
        "transport_data": [
            {
                "aSideSiteName": "CPGRMOLK-CHTR/HUB-CAPE GIRARDEAU MO (CPGRMO21714)",
                "bandwidth": "1 Gbps",
                "category": "ETHERNET TRANSPORT",
                "gia_UDA": "NO",
                "off_NetFacility_UDA": "NO",
                "pathId": "57001.GE1.CPGRMOLK0QW.CPGRMORR1ZW",
                "pathInService": "2023-06-14 12:00:00.0",
                "pathRev": "1",
                "product_Service_UDA": "INT-ACCESS TO PREM TRANSPORT",
                "protectedFlag_UDA": "NO",
                "servicePriority": "NO",
                "status": "Live",
                "topology": "P",
                "tspChildPresent_UDA": "NO",
                "zSideSiteName": "CPGRMORR-COLAS ISS INC/MDF/1208 S KINGSHIGHWAY",
                "instanceProtocol": "999999",
                "pathInstanceId": "2493838",
                "serviceMedia": "FIBER",
                "startChanNbr": "1",
                "virtualChans": "D",
            }
        ],
        "element_data": {
            "customer_name": "COGENT COMMUNICATIONS, INC-CHTR-ICOMS",
            "hub_clli": "OWTNMN02",
            "hub_site": "FRBLMNAK-DAIKIN APPLIED AMERICAS I//300 24TH ST NW",
            "port_access_id": "GE-0/0/29",
            "upstream_device": "OWTNMN020QW",
            "upstream_handoff": "OWTNMN020QW:GE-0/0/29",
        },
    },
    "a": {
        "shelf_id": "1402910",
        "site_id": "445988",
        "transport_data": [
            {
                "aSideSiteName": "CPGRMOLK-CHTR/HUB-CAPE GIRARDEAU MO (CPGRMO21714)",
                "bandwidth": "1 Gbps",
                "category": "ETHERNET TRANSPORT",
                "gia_UDA": "NO",
                "off_NetFacility_UDA": "NO",
                "pathId": "57001.GE1.CPGRMOLK0QW.CPGRMORR1ZW",
                "pathInService": "2023-06-14 12:00:00.0",
                "pathRev": "1",
                "product_Service_UDA": "INT-ACCESS TO PREM TRANSPORT",
                "protectedFlag_UDA": "NO",
                "servicePriority": "NO",
                "status": "Live",
                "topology": "P",
                "tspChildPresent_UDA": "NO",
                "zSideSiteName": "CPGRMORR-COLAS ISS INC/MDF/1208 S KINGSHIGHWAY",
                "instanceProtocol": "999999",
                "pathInstanceId": "2493838",
                "serviceMedia": "FIBER",
                "startChanNbr": "1",
                "virtualChans": "D",
            }
        ],
        "element_data": {
            "customer_name": "COGENT COMMUNICATIONS, INC-CHTR-ICOMS",
            "hub_clli": "ABCNMN02",
            "hub_site": "ABCMNAK-DAIKIN APPLIED AMERICAS I//900 MOON MEADOW ST",
            "port_access_id": "GE-0/0/11",
            "upstream_device": "ABCNMN020QW",
            "upstream_handoff": "ABCNMN020QW:GE-0/0/11",
        },
    },
    "path_data": [
        {
            "aSideCustomer": "ACCT-26463357",
            "aSideSiteName": "STLSMOPL-CHTR/COLO-LEVEL3-1015 LOCUST ST (ENT/ENT LEC)",
            "bandwidth": "100 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-26463357",
            "orderNumber": "CAR-EPL-00029771,ENG-03841212,ENG-03841211",
            "pathId": "57.L1XX.001489..CHTR",
            "pathInService": "2023-06-14 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "CAR-E-ACCESS FIBER/FIBER EPL",
            "protectedFlag_UDA": "NO",
            "servicePriority": "NO",
            "status": "Live",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-26463357",
            "zSideSiteName": "CPGRMORR-COLAS ISS INC/MDF/1208 S KINGSHIGHWAY",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "1",
            "pathInstanceId": "2483801",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ],
    "CID": "57.L1XX.001489..CHTR",
}


test_validated_fia = [{"z": {"address": "1234 Bananas St Austin TX 78759", "engineering_page": "ENG-23456789"}}]


test_validated_eline = [
    {
        "z": {"address": "1234 Bananas St Austin TX 78759", "engineering_page": "ENG-23456789"},
        "a": {"address": "5678 Pineapple Cove Austin TX 78759", "engineering_page": "ENG-34567890"},
    }
]
