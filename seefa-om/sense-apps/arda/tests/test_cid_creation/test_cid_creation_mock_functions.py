class MockResponse:
    def __init__(self, data_set, status_code=200):
        self.status_code = status_code
        self.data_set = data_set

    def json(self):
        return self.data_set


def mock_this_is_not_carrier(_):
    return False


def mock_this_is_carrier(_):
    return True


def mock_update(_, *args, **kwargs):
    return


def mock_npa_lookup(_):
    return "123"


def mock_empty_query(_):
    return []


def mock_get_sites_v3(_):
    return [
        {
            "siteName": "KRVLNCPS-KERNERSVILLE WESLEYAN//930 N MAIN ST",
            "clli": "KRVLNCPS",
            "latitude": "36.129297",
            "longitude": "-80.054790",
            "parent_site": "KRVLNCPS",
            "status": "Auto-Planned",
            "siteType": "LOCAL",
            "address": "930 N MAIN ST",
            "city": "KERNERSVILLE",
            "state": "NC",
            "zip1": "27284",
            "npaNxx": "336",
        }
    ]


def mock_get_related_cid(_):
    return {
        "created new site": False,
        "siteName": "CSMSCA07-VZW/COSTA MESA",
        "siteType": "LOCAL",
        "clli": "CSMSCA07",
        "latitude": "33.639217",
        "longitude": "-117.939405",
    }


def mock_get_site_by_enni(_):
    return {
        "created new site": False,
        "siteName": "KRVLNCPS",
        "siteType": "LOCAL",
        "clli": "KRVLNCPS",
        "latitude": "36.129297",
        "longitude": "-80.054790",
    }


def mock_get_sites(_):
    return [{"siteName": "KRVLNCPS", "address": "930 N MAIN ST", "siteType": "BUILDING"}]


test_site = {
    "name": "TEST SITE",
    "clean_name": "TEST SITE",
    "parent": "SITE PARENT",
    "type": "ENTERPRISE",
    "address": "123 DAWN DRIVE",
    "city": "AUSTIN",
    "state": "TX",
    "zip_code": "12345",
    "gems_key": "12345",
    "product_name_order_info": "Fiber Internet Access",
    "sf_id": "ACCT-3",
    "customer": "TEST CUSTOMER",
    "product_family": "blah",
}

site_in_data1 = {
    "name": "KERNERSVILLE WESLEYAN",
    "parent": "WESTERN NORTH CAROLINA",
    "type": "LOCAL",
    "address": "930 N MAIN ST",
    "city": "KERNERSVILLE",
    "state": "NC",
    "zip_code": "27284",
    "product_name_order_info": "SIP - Trunk (Fiber)",
    "sf_id": "ACCT-26522374",
    "product_family": "blah",
    "construction_job_number": False,
}

site_in_data2 = {
    "name": "KERNERSVILLE WESLEYAN",
    "parent": "WESTERN NORTH CAROLINA",
    "type": "CELL",
    "address": "930 N MAIN ST",
    "city": "KERNERSVILLE",
    "state": "NC",
    "zip_code": "27284",
    "product_name_order_info": "Carrier CTBH",
    "sf_id": "ACCT-26522374",
    "product_family": "ctbh",
}

site_in_data_w_enni = {
    "name": "KERNERSVILLE WESLEYAN",
    "parent": "WESTERN NORTH CAROLINA",
    "type": "LOCAL",
    "address": "930 N MAIN ST",
    "city": "KERNERSVILLE",
    "state": "NC",
    "zip_code": "27284",
    "product_name_order_info": "SIP - Trunk (Fiber)",
    "sf_id": "ACCT-26522374",
    "enni": "123",
    "product_family": "blah",
}

site_in_data_w_related_cid = {
    "name": "KERNERSVILLE WESLEYAN",
    "parent": "WESTERN NORTH CAROLINA",
    "type": "LOCAL",
    "address": "930 N MAIN ST",
    "city": "KERNERSVILLE",
    "state": "NC",
    "zip_code": "27284",
    "product_name_order_info": "SIP - Trunk (Fiber)",
    "sf_id": "ACCT-26522374",
    "related_circuit_id": "21.L1XX.000211.LXM.TWCC",
    "product_family": "blah",
}

test_customer = {
    "name": "test customer",
    "type": "ENTERPRISE",
    "phone": "(910) 343-0624",
    "address": "address",
    "city": "city",
    "state": "state",
    "zip_code": "zip",
    "bill_code": "12345",
    "country": "USA",
    "sf_id": "id",
}

path_data_v2 = {
    "bw_value": "100",
    "bw_unit": "MBPS",
    "customer_type": "Dedicated Internet Access",
    "product_service": "COM-EPLAN",
    "z_side_site": {
        "customer": "TX COMMERCIAL-CARRIER SERVICES",
        "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
        "site_zip_code": "78664",
    },
    "path_order_num": "1234",
    "tsp_auth": "optional",
    "tsp_expiration": "optional",
    "off-net_provider_cid": "required for Finished Internet",
    "off-net_service_provider": "required for Finished Internet",
    "assigned_ip_subnet": "required for Finished Internet",
    "ipv4_service_type": "required for Finished Internet",
    "managed_service": False,
    "service_media": "required for Finished Internet",
}

path_data_v3 = {
    "bw_value": "100",
    "bw_unit": "MBPS",
    "customer_type": "ENTERPRISE",
    "product_service": "COM-DIA",
    "a_side_site": {
        "customer": "TX COMMERCIAL-CARRIER SERVICES",
        "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
        "site_zip_code": "33333",
    },
    "z_side_site": {
        "customer": "TX COMMERCIAL-CARRIER SERVICES",
        "site": "RDRKTXAZ-TWC/HUB R-ROUND ROCK",
        "site_zip_code": "33333",
    },
    "path_order_num": "1234",
    "managed_service": False,
    "service_media": "Fiber",
}

loop_data = [
    {
        "address": "689 OAK HILL RD",
        "state": "ME",
        "name": "SPRINT",
        "type": "CELL",
        "sf_id": "bad",
        "product_name_order_info": "Carrier CTBH",
        "clean_name": "SPRINT",
    }
]

fall_out_scenarios = [
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "Live"},
    ],
    [
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "Live"},
    ],
]

scenarios = [
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "colo", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "planned"},
    ],
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "colo", "status": "Live"},
    ],
]

name_match_scenarios = [
    [
        {"siteName": "SITE100", "clean_name": "test name", "siteType": "local", "status": "planned"},
        {"siteName": "SITE100", "clean_name": "not match", "siteType": "local", "status": "planned"},
    ]
]
# used for update_site_with_building tests
site_data1 = {"product_name_order_info": "Test", "parent": "Test Parent", "type": "test"}
site_data2 = {"product_name_order_info": "(TYPE II)", "parent": "Test Parent", "type": "test"}
site1 = {"siteName": "Test Site", "siteType": "Test Type"}
site2 = {"siteName": "Test Site", "siteType": "Test Type", "parent_site": "Test Parent"}
building = {"siteName": "Test Building"}

fall_out_scenarios = [
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "Live"},
    ],
    [
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "Live"},
    ],
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "planned"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "planned"},
    ],
]

scenarios = [
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "colo", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "local", "status": "planned"},
    ],
    [
        {"siteName": "SITE1", "clean_name": "test name", "siteType": "local", "status": "Live"},
        {"siteName": "SITE1", "clean_name": "not match", "siteType": "colo", "status": "Live"},
    ],
]

name_match_scenarios = [
    [
        {"siteName": "SITE100", "clean_name": "not match", "siteType": "local", "status": "Live"},
        {"siteName": "SITE100", "clean_name": "not match", "siteType": "local", "status": "Live"},
    ],
    [
        {"siteName": "SITE100", "clean_name": "test name", "siteType": "local", "status": "planned"},
        {"siteName": "SITE100", "clean_name": "not match", "siteType": "local", "status": "planned"},
    ],
]
