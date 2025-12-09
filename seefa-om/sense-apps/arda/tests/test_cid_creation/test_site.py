from unittest.mock import Mock
import pytest
from arda_app.api import site as se
from arda_app.bll.cid import site as so
from tests.test_cid_creation import test_cid_creation_mock_functions as mock
from copy import deepcopy

site_in_data = {
    "name": "TEST SITE",
    "parent": "SYRACUSE",
    "siteType": "local",
    "address": "123 DAWN STREET",
    "room": "ROOM 4",
    "city": "mount pleasant",
    "state": "TX",
    "zip_code": "78645",
    "gems_key": "1098765",
    "clli": "1234",
    "fixed_access_code": "12",
    "product_name_order_info": "COM-DIA",
    "type": "local",
    "clean_name": "TEST SITE",
    "product_family": "Dedicated Internet Service",
    "country": "USA",
    "county": "Smith",
    "customer": "test",
    "lata_code": "952",
}


@pytest.mark.unittest
def test_abbreviate():
    scenarios = {
        "9th street": "9TH ST",
        "9 th street": "9TH ST",
        "9 th st": "9TH ST",
        "123 9 th st W 45 th avenue": "123 9TH ST W 45TH AVE",
        "300 1 st st": "300 1ST ST",
        "2277 3 RD AVE": "2277 3RD AVE",
        "2277 2 ND AVE": "2277 2ND AVE",
        "2277 1 ST AVE": "2277 1ST AVE",
        "2277 5 TH": "2277 5TH",
    }

    for k, v in scenarios.items():
        assert so.abbreviate(k) == v

    scenarios = {
        "9th court street": "9TH COURT ST",
        "mountain road": "MOUNTAIN RD",
        "mount mountain road st": "MOUNT MOUNTAIN ROAD ST",
        "Lane Street": "LANE ST",
    }

    for k, v in scenarios.items():
        assert so.abbreviate(k, True) == v

    assert so.abbreviate("123 United States Highway") == "123 US HWY"
    assert so.abbreviate("123 Farm to Market Highway") == "123 FM HWY"


@pytest.mark.unittest
def test_att_check():
    site_data = {
        "clean_name": "ATT Wireless",
        "product_name_order_info": "Carrier CTBH",
        "fixed_access_code": "data",
        "lata_code": "data",
    }
    assert so.att_check(site_data) is None

    site_data["fixed_access_code"] = None
    site_data["lata_code"] = None
    assert so.att_check(site_data) is None

    site_data["clean_name"] = "ATT MOBILITY CA CBH"
    site_data["fixed_access_code"] = "data"
    assert so.att_check(site_data) is None

    site_data["fixed_access_code"] = None
    assert so.att_check(site_data) is None


@pytest.mark.unittest
def test_check_unit_match(monkeypatch):
    site = {"siteName": "test", "room": "test1"}
    site_name = "test0/test1/test2"

    site2 = {"siteName": "test"}
    site_name2 = "test//test2"

    monkeypatch.setattr(so, "clean_unit_v3", lambda *args, **kwargs: ("1", "1"))
    assert so.check_unit_match(site, site_name) is True

    monkeypatch.setattr(so, "clean_unit_v3", lambda *args, **kwargs: ("test1", ""))
    assert so.check_unit_match(site, site_name) is True

    assert so.check_unit_match({}, site_name) is True

    assert so.check_unit_match(site2, site_name2) is True

    site_name2 = "test-MTU//test"
    assert so.check_unit_match(site2, site_name2) is True

    site_name2 = "abcdesf-testcustomer"
    assert so.check_unit_match(site2, site_name2) is True

    site_name2 = "test-test/test"
    assert so.check_unit_match(site2, site_name2) is True


@pytest.mark.unittest
def test_clean_unit_v3():
    scenarios = (
        (None, None, ("", "")),
        ("room 45", None, ("45", "")),
        ("room[45]", None, ("45", "")),
        ("floor25", None, ("", "25")),
        ("unit4 dia", None, ("4", "")),
        ("ste-45", None, ("45", "")),
        ("APT #801", None, ("801", "")),
        ("RM1", "FL2", ("1", "2")),
        ("FL2", "RM1", ("1", "2")),
        ("RM-2A", None, ("2A", "")),
        ("Bldg RM-2A", None, ("2A", "")),
        ("IT RM", None, ("", "")),
        ("RM MDF", None, ("", "")),
        ("RM-MDF", "FL-BASEMENT", ("", "")),
        # new stuff
        (None, "RM1 FL2", ("1", "2")),
        ("RM1 FL2", None, ("1", "2")),
        (None, "FL2 RM1", ("1", "2")),
        (None, "FL2 RM 1", ("1", "2")),
        (None, "RM1 FL 2", ("1", "2")),
        (None, "FL 2 RM1", ("1", "2")),
        (None, "RM 1 FL2", ("1", "2")),
        (None, "RM 1 FL 2 ", ("1", "2")),
        (None, "FL 2 RM 1", ("1", "2")),
        ("? 45", None, ("45", "")),
        (None, "3/ELAN", ("", "3")),
        ("master", "FL8", ("", "8")),
        ("ste_45_fl_2", "", ("45", "2")),
        (None, "FL2RM1", ("", "")),
    )

    for x in scenarios:
        room, floor = so.clean_unit_v3(x[0], x[1])
        assert room == x[2][0]
        assert floor == x[2][1]


@pytest.mark.unittest
def test_cleanup_address():
    assert so.cleanup_address("test") == "TEST"
    assert so.cleanup_address("test office 123") == "TEST"


@pytest.mark.unittest
def test_clean_up_name():
    scenarios = {
        "national service's call.": "NATIONAL SERVICES CALL",
        "ntl #planned-parenthood austin!": "NTL PLANNED PARENTHOOD AUSTIN",
        "remove-master /here:": "REMOVE MASTER HERE",
        "hq welcome home": "HQ WELCOME HOME",
        "headquarters (HQ)": "HEADQUARTERS",
        "at&t place fiber subgroup": "AT&T PLACE FIBER",
        "KIPP SOCAL PUBLIC�SCHOOLS": "KIPP SOCAL PUBLIC SCHOOLS",
        "MIKE TIRE SHOP-PARENT ACCOUNT": "MIKE TIRE SHOP",
        "THE DEDICATED INTERNET SERVICE": "THE",
        "": None,
    }

    for k, v in scenarios.items():
        assert so.clean_up_name(k) == v


@pytest.mark.unittest
def test_create_building(monkeypatch):
    monkeypatch.setattr(so, "create_site_v4", lambda *args, **kwargs: "success")
    monkeypatch.setattr(so, "update_site_with_building", mock.mock_update)

    site = site_in_data.copy()
    site_record = [site]
    assert so.create_building(site_in_data, site, site_record) == "success"


@pytest.mark.unittest
def test_create_mtu_site(monkeypatch):
    def mock_granite_call(*args, **kwargs):
        return mock.MockResponse("success")

    monkeypatch.setattr(so, "post_granite", mock_granite_call)
    monkeypatch.setattr(so, "get_npa_three_digits", lambda *args, **kwargs: "512")

    site_in_data["site_clli"] = "12345678"

    assert so.create_mtu_site(site_in_data) == "success"

    monkeypatch.setattr(so, "post_granite", lambda *args, **kwargs: mock.MockResponse({"retString": "test"}, 500))
    monkeypatch.setattr(so, "parse_site_error", lambda *args, **kwargs: "fail")
    assert so.create_mtu_site(site_in_data) == "fail"


@pytest.mark.unittest
def test_create_site_v4(monkeypatch):
    # good test npa look up
    monkeypatch.setattr(so, "get_npa_three_digits", lambda *args, **kwargs: "512")
    monkeypatch.setattr(so, "post_granite", lambda *args, **kwargs: mock.MockResponse("success"))
    assert so.create_site_v4(site_in_data) == "success"

    # good test building cretion
    assert so.create_site_v4(site_in_data, building=True) == "success"

    # good test type 2 products
    monkeypatch.setattr(so, "is_type_II", lambda *args, **kwargs: True)
    assert so.create_site_v4(site_in_data) == "success"

    # good test no building gems key
    site_in_data["gems_key"] = ""
    assert so.create_site_v4(site_in_data) == "success"

    # good test ring central product
    site_in_data["product_family"] = "RingCentral"
    assert so.create_site_v4(site_in_data) == "success"

    # bad test no abort parse site error
    monkeypatch.setattr(so, "post_granite", lambda *args, **kwargs: mock.MockResponse({"retString": "test"}, 500))
    monkeypatch.setattr(so, "parse_site_error", lambda *args, **kwargs: "fail")
    assert so.create_site_v4(site_in_data, building=True) == "fail"

    # bad test abort no address
    site_in_data2 = deepcopy(site_in_data)
    site_in_data2["address"] = ""

    with pytest.raises(Exception):
        assert so.create_site_v4(site_in_data2) is None

    # bad test abort sitename greater than 91(100 with clli-)
    site_in_data2["address"] = (
        "500 SCHAAD LNCPEADVA 116 PRO-H 1 FLOOR ENCLOSURE 2 SUITE/"
        "RM CELL TOWER 3 RACK LOC extra characters to make it the address long to fall out"
    )

    with pytest.raises(Exception):
        assert so.create_site_v4(site_in_data2) is None


@pytest.mark.unittest
def test_ctbh_customer_abbreviations():
    scenarios = {
        "AT&T": "ATT",
        "CAROLINA WEST WIRELESS": "CAW",
        "CARRIER UNKNOWN": "CARRIER UNKNOWN",
        "CLEARWIRE": "CLW",
        "FIBERLIGHT": "FBR",
        "PARADIGM": "PAR",
        "SPRINT": "SPR",
        "SUDDENLINK": "SDK",
        "T-MOBILE": "TMO",
        "US CELLULAR": "USC",
        "VERIZON WIRELESS": "VZW",
    }

    for k, v in scenarios.items():
        assert so.ctbh_customer_abbreviations(k) == v


@pytest.mark.unittest
def test_find_mtu_site(monkeypatch):
    res = [{"siteName": "TEST SITE", "address": "road avenue highway street", "siteType": "ACTIVE MTU"}]

    monkeypatch.setattr(so, "get_sites", lambda *args, **kwargs: res)
    assert so.find_mtu_site("ABZYHQ") is True

    monkeypatch.setattr(so, "get_sites", lambda *args, **kwargs: [{"siteName": "TEST"}])

    with pytest.raises(Exception):
        assert so.find_mtu_site("test") == (500, "No sites found for hub CLLI: test")


@pytest.mark.unittest
def test_find_or_create_a_site_v5(monkeypatch):
    res1 = {
        "siteName": "KRVLNCPS-KERNERSVILLE WESLEYAN//930 N MAIN ST",
        "clli": "KRVLNCPS",
        "latitude": "36.129297",
        "longitude": "-80.054790",
    }

    monkeypatch.setattr(so, "att_check", mock.mock_update)
    monkeypatch.setattr(so, "get_ctbh_cell_sites", mock.mock_update)
    monkeypatch.setattr(so, "get_sites_v3", mock.mock_get_sites_v3)
    monkeypatch.setattr(so, "create_site_v4", lambda *args, **kwargs: res1)
    monkeypatch.setattr(so, "find_or_create_building", mock.mock_update)
    monkeypatch.setattr(so, "get_site_by_enni", mock.mock_get_site_by_enni)
    monkeypatch.setattr(so, "get_sites", mock.mock_get_sites)
    monkeypatch.setattr(so, "update_existing_site_npaxx", mock.mock_update)

    res2 = {
        "created new site": False,
        "siteName": "KRVLNCPS-KERNERSVILLE WESLEYAN//930 N MAIN ST",
        "clli": "KRVLNCPS",
        "lat": "36.129297",
        "lon": "-80.054790",
    }
    assert so.find_or_create_a_site_v5(mock.site_in_data1) == res2

    res2["created new site"] = True
    assert so.find_or_create_a_site_v5(mock.site_in_data2) == res2

    res2["siteName"] = "KRVLNCPS"
    res2["created new site"] = False
    assert so.find_or_create_a_site_v5(mock.site_in_data_w_enni) == res2

    monkeypatch.setattr(so, "validate_site_records_v4", mock.mock_update)
    monkeypatch.setattr(so, "create_site_v4", lambda *args, **kwargs: res1)
    monkeypatch.setattr(so, "find_or_create_building", mock.mock_update)

    res2["created new site"] = True
    res2["siteName"] = "KRVLNCPS-KERNERSVILLE WESLEYAN//930 N MAIN ST"
    assert so.find_or_create_a_site_v5(mock.site_in_data1) == res2

    monkeypatch.setattr(so, "is_type_II", lambda *args, **kwargs: True)
    assert so.find_or_create_a_site_v5(mock.site_in_data1) == res2

    monkeypatch.setattr(so, "is_ctbh", lambda *args, **kwargs: True)
    assert so.find_or_create_a_site_v5(mock.site_in_data1) == res2

    monkeypatch.setattr(so, "is_ctbh", lambda *args, **kwargs: False)
    monkeypatch.setattr(so, "get_site_by_related_CID", mock.mock_get_related_cid)

    assert so.find_or_create_a_site_v5(mock.site_in_data_w_related_cid) == {
        "created new site": False,
        "siteName": "CSMSCA07-VZW/COSTA MESA",
        "clli": "CSMSCA07",
        "lat": "33.639217",
        "lon": "-117.939405",
    }


@pytest.mark.unittest
def test_find_or_create_building(monkeypatch):
    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert so.find_or_create_building("test", {"siteName": "test"}) == (
            500,
            "Something went wrong looking up the site in Granite",
        )

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [{"clli": "test", "parent_site": "test"}])
    monkeypatch.setattr(so, "validate_site_records_v4", lambda sd, sites, building_search=False: "building")
    monkeypatch.setattr(so, "update_site_with_building", lambda *args: None)
    site_data = {"parent_site": "test"}
    site = {"siteName": "test", "clli": "test"}
    assert so.find_or_create_building(site_data, site) is None

    monkeypatch.setattr(so, "validate_site_records_v4", lambda *args, **kwargs: None)
    monkeypatch.setattr(so, "get_building", lambda *args, **kwargs_: None)
    monkeypatch.setattr(so, "create_building", lambda *args, new_site=True: None)

    assert so.find_or_create_building(site_data, site, new_site=True) is None

    site = {"siteName": "test", "clli": "test", "siteType": "test", "parent_site": "test"}
    monkeypatch.setattr(so, "update_site_with_building", lambda *args, **kwargs: None)
    monkeypatch.setattr(so, "create_building", lambda *args, **kwargs: None)
    assert so.find_or_create_building(site_data, site) is None

    site["siteType"] = "LOCAL"
    assert so.find_or_create_building(site_data, site) is None

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert so.find_or_create_building(site_data, site, new_site=True) is None

    site.pop("clli")
    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [site])

    with pytest.raises(Exception):
        assert so.find_or_create_building(site_data, site, new_site=True) is None


@pytest.mark.unittest
def test_get_building(monkeypatch):
    bldg_test = [{"siteType": "BUILDING", "siteName": "test"}]
    bldg_fail = [{"siteType": "BUILDING", "siteName": "fail"}]
    local_test = [{"siteType": "LOCAL", "siteName": "test"}]

    monkeypatch.setattr(so, "get_sites", lambda *args, **kwargs: bldg_test)
    assert so.get_building("test") == {"siteType": "BUILDING", "siteName": "test"}

    monkeypatch.setattr(so, "get_sites", lambda *args, **kwargs: bldg_fail)
    assert so.get_building("test") is None

    monkeypatch.setattr(so, "get_sites", lambda *args, **kwargs: local_test)
    monkeypatch.setattr(so, "update_existing_bldg_site", lambda *args, **kwargs: None)
    assert so.get_building("test") == {"siteType": "LOCAL", "siteName": "test"}


@pytest.mark.unittest
def test_get_ctbh_cell_sites(monkeypatch):
    site = {
        "address": "689 OAK HILL RD",
        "state": "ME",
        "name": "SPRINT",
        "type": "CELL",
        "sf_id": "bad",
        "product_name_order_info": "Carrier CTBH",
        "clean_name": "SPRINT",
    }
    monkeypatch.setattr(so, "loop_through_pages", lambda *args, **kwargs: mock.loop_data)
    assert so.get_ctbh_cell_sites(site) == site


@pytest.mark.unittest
def test_get_site_by_enni(monkeypatch):
    results = [
        {"A_SITE_NAME": "test", "A_SITE_TYPE": "test", "A_CLLI": "test", "A_LATITUDE": "test", "A_LONGITUDE": "test"}
    ]

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: results)
    res = {
        "created new site": False,
        "siteName": "test",
        "siteType": "test",
        "clli": "test",
        "latitude": "test",
        "longitude": "test",
    }
    assert so.get_site_by_enni("333") == res

    results[0]["CIRCUIT_STATUS"] = "Live"
    results.append({})
    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: results)
    assert so.get_site_by_enni("333") == res

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert so.get_site_by_enni("333") is None


@pytest.mark.unittest
def test_get_site_by_enni_for_circuitpath(monkeypatch):
    test_list1 = [{"A_SITE_NAME": "test", "A_ZIP": "123456"}]
    test_list2 = [{"CIRCUIT_STATUS": "test"}, {"A_SITE_NAME": "test", "A_ZIP": "123456", "CIRCUIT_STATUS": "Live"}]
    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: test_list1)
    res = {"siteName": "test", "zipcode": "123456"}
    assert so.get_site_by_enni_for_circuitpath("enni") == res

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: test_list2)
    assert so.get_site_by_enni_for_circuitpath("enni") == res

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [])
    assert so.get_site_by_enni_for_circuitpath("enni", is_ctbh=True) is None

    with pytest.raises(Exception):
        assert so.get_site_by_enni_for_circuitpath("enni") is None


@pytest.mark.unittest
def test_get_sites_v3(monkeypatch):
    provided_site = {"address": "test", "state": "TX", "customer": "acct-123456"}
    monkeypatch.setattr(so, "loop_through_pages", lambda *args, **kwargs: None)
    assert so.get_sites_v3(provided_site) is None


@pytest.mark.unittest
def test_is_type_II():
    site = mock.test_site.copy()
    site["product_name_order_info"] = "Something (Type II)"
    assert so.is_type_II(site) is True

    site["product_name_order_info"] = "Something (Nothing)"
    assert so.is_type_II(site) is False

    site["parent"] = "OFF-NET-NY"
    assert so.is_type_II(site) is True

    site["parent"] = "CLLI"
    assert so.is_type_II(site) is False

    site["third_party_provided_circuit"] = "true"
    assert so.is_type_II(site) is True


@pytest.mark.unittest
def test_loop_through_pages(monkeypatch):
    original_site = {"address": "test", "siteType": "local", "construction_job_number": False}
    monkeypatch.setattr(so, "get_granite", lambda *args, **kwargs: [])
    assert so.loop_through_pages("url", original_site) == []

    result = {"address": "test", "siteName": "test", "siteType": "local"}
    test_mock = Mock(side_effect=[[result], []])
    monkeypatch.setattr(so, "get_granite", test_mock)
    monkeypatch.setattr(so, "check_unit_match", lambda *args, **kwargs: True)
    assert so.loop_through_pages("url", original_site) == [result]

    results2 = {"address": "test", "clean_name": None, "siteName": "test//TEST2", "siteType": "local"}
    original_site = {"address": "TEST2", "clean_name": "TEST2", "siteType": "local", "construction_job_number": False}
    test_mock = Mock(side_effect=[[results2], []])
    monkeypatch.setattr(so, "get_granite", test_mock)
    monkeypatch.setattr(so, "check_unit_match", lambda *args, **kwargs: True)
    assert so.loop_through_pages("url", original_site) == [results2]

    test_mock2 = Mock(
        side_effect=[
            [
                {"address": "celltest1", "siteName": "cell//cell1", "product_family": "test", "customerRec_id": "1234"},
                {"address": "celltest2", "siteName": "cell//cell2", "product_family": "test", "customerRec_id": "1234"},
            ],
            [],
        ]
    )
    original_site = {
        "address": "TEST2",
        "clean_name": "TEST2",
        "product_family": "TEST2",
        "construction_job_number": True,
    }
    monkeypatch.setattr(so, "get_granite", test_mock2)
    assert so.loop_through_pages("CELL", original_site) == []

    results3 = {"address": "test2", "siteName": "test", "siteType": "local"}
    test_mock = Mock(side_effect=[[results3], []])
    monkeypatch.setattr(so, "get_granite", test_mock)
    monkeypatch.setattr(so, "check_unit_match", lambda *args, **kwargs: True)
    assert so.loop_through_pages("url", original_site) == [results3]

    results3 = {"address": "test2", "siteName": "test", "siteType": "BUILDING"}
    test_mock2 = Mock(side_effect=[[results3], []])
    monkeypatch.setattr(so, "get_granite", test_mock2)
    monkeypatch.setattr(so, "check_unit_match", lambda *args, **kwargs: True)
    assert so.loop_through_pages("url", original_site) == [results3]


@pytest.mark.unittest
def test_match_on_account_id_or_name():
    site = {"siteName": "test", "clean_name": "TEST"}
    clean_name = "TEST"
    assert so.match_on_account_id_or_name("test", clean_name, site) is True

    site = {"siteName": "test_name", "clean_name": "TEST_name", "siteId": "TEST"}
    assert so.match_on_account_id_or_name("test", clean_name, site) is True

    site = {
        "siteName": "test_name",
        "clean_name": "TEST_name",
        "customerRec_id": "TEST",
        "sfUniqueCustomerId_UDA": "sf_id",
    }
    assert so.match_on_account_id_or_name("sf_id", clean_name, site) is True


@pytest.mark.unittest
def test_parse_site_error(monkeypatch):
    error = "Not a valid address. iConnective LocateIt found a similar address:"
    site = {"address": "644 US FORT", "city": "DALLAS", "state": "TX", "zip_code": "75244"}
    monkeypatch.setattr(so, "saint_cities", lambda *args, **kwargs: ("FT", "FORT"))
    monkeypatch.setattr(so, "create_site_v4", lambda *args: None)
    assert so.parse_site_error(error, site) is None

    monkeypatch.setattr(so, "saint_cities", lambda *args, **kwargs: False)
    monkeypatch.setattr(so, "find_best_match", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert so.parse_site_error(error, site) is None

    error = """Duplicate Site Address info found.\nPlease select one of the suggested sites
    and resubmit your request:\n- 13740 MIDWAY
    RD @ (BLDG 700) DALLAS 75244 -- 13740 MIDWAY RD @ (BLDG 500) DALLAS 75244"""

    with pytest.raises(Exception):
        assert so.parse_site_error(error, site) is None

    error = """Multiple site addresses matched from LocateIt, please select or copy the address below and try
    again\n1.null, INDIANHEAD RESORT *//644 US RTE 3, Planned, LOCAL, 44.083292, -71.684975,
    644 US HWY 3 S, LINCOLN, 03251, NH, USA\n-------End of Site Address-------"""

    with pytest.raises(Exception):
        assert so.parse_site_error(error, site) is None

    with pytest.raises(Exception):
        assert so.parse_site_error("", site) is None


@pytest.mark.unittest
def test_remote_dukenet_sites():
    test_sites = [
        {"siteName": "TEST SITE"},
        {"siteName": "TEST SITE 2"},
        {"siteName": "CHRONCAE-DUKENET/PF/5605 CARNEIGE BLVD"},
    ]
    sites = so.remove_dukenet_sites(test_sites)
    assert sites == [{"siteName": "TEST SITE"}, {"siteName": "TEST SITE 2"}]


@pytest.mark.unittest
def test_saint_cities():
    assert so.saint_cities("314 Mount", "314 Mount") == ("MT", "MOUNT")
    assert so.saint_cities("314 Fort", "314 FT") == ("FORT", "FT")
    assert so.saint_cities("314 Mount", "314 Mt lane") is False


@pytest.mark.unittest
def test_sort_out_multiple_candidates_v2():
    local_site = [{"siteName": "SITE1", "clean_name": "test name", "siteType": "LOCAL", "status": "Live"}]
    assert so.sort_out_multiple_candidates_v2(local_site, "clean_name", "provided_name") == local_site[0]

    scenarios = ([{"siteType": "COLO"}, {"siteType": "POP"}], [{"siteType": "test"}])

    for k in scenarios:
        assert so.sort_out_multiple_candidates_v2(k, None, None) is None

    no_hub = [
        [
            {"siteName": "SITE1", "clean_name": "test name", "siteType": "colo", "status": "Live"},
            {"siteName": "SITE1", "clean_name": "test name", "siteType": "hub", "status": "Live"},
        ]
    ]
    assert so.sort_out_multiple_candidates_v2(no_hub[0], "test name", "SITE100") == no_hub[0][0]

    for scenario in mock.scenarios:
        site = so.sort_out_multiple_candidates_v2(scenario, "test name", "SITE100")
        assert site is not None
        assert "test name" in site["clean_name"]


@pytest.mark.unittest
def test_take_room_info_from_name():
    name = "161 RIVERSIDE DR STE 1"
    assert so.take_room_info_from_name(name) == "161 RIVERSIDE DR"


@pytest.mark.unittest
def test_update_existing_bldg_site(monkeypatch):
    monkeypatch.setattr(so, "put_granite", lambda *args, **kwargs: True)
    assert so.update_existing_bldg_site({"siteName": "test"}) is None


@pytest.mark.unittest
def test_update_existing_site(monkeypatch):
    monkeypatch.setattr(so, "put_granite", lambda *args, **kwargs: True)
    provided_site = {"customer": "test", "gems_key": "123", "sf_id": "test", "product_family": "test"}
    record = {"siteName": "test2", "siteType": "LOCAL", "status": "test", "product_family": "test"}
    assert so.update_existing_site(provided_site, record) is None

    record["customerRec"] = [{"sfUniqueCustomerId_UDA": "test2"}]
    assert so.update_existing_site(provided_site, record) is None

    provided_site["product_family"] = "RingCentral"
    assert so.update_existing_site(provided_site, record) is None


@pytest.mark.unittest
def test_update_existing_site_npaxx(monkeypatch):
    site = {"siteName": "test", "siteType": "test", "zip1": "12345"}
    monkeypatch.setattr(so, "get_npa_three_digits", lambda *args, **kwargs: None)
    monkeypatch.setattr(so, "put_granite", lambda *args, **kwargs: None)
    assert so.update_existing_site_npaxx(site) is None


@pytest.mark.unittest
def test_update_site_parent(monkeypatch):
    monkeypatch.setattr(so, "put_granite", lambda *args, **kwargs: None)
    site = {"name": "test", "type": "test", "parent": "test"}
    assert so.update_site_parent(site) is None


@pytest.mark.unittest
def test_update_site_with_building(monkeypatch):
    monkeypatch.setattr(so, "update_site_parent", lambda *args, **kwargs: None)
    monkeypatch.setattr(so, "update_existing_site", lambda *args, **kwargs: None)
    assert so.update_site_with_building(mock.site_data1, mock.site1, mock.building, new_site=True) is None
    assert so.update_site_with_building(mock.site_data2, mock.site1, mock.building, new_site=True) is None
    assert so.update_site_with_building(mock.site_data1, mock.site1, mock.building) is None
    assert so.update_site_with_building(mock.site_data1, mock.site2, mock.building) is None


@pytest.mark.unittest
def test_validate_site_records_v4(monkeypatch):
    find_fuzzy_matches2 = ([{"siteName": "test1"}], 90, None)
    find_fuzzy_matches3 = ([{"siteName": "test1"}], 80, None)

    provided_site = {
        "name": "TEST",
        "product_name_order_info": "test",
        "product_family": "test",
        "type": "CELL",
        "sf_id": "test",
        "clean_name": "test",
        "construction_job_number": True,
    }

    records1 = [
        {"siteName": "test", "siteType": "COLO", "status": "Live"},
        {"siteName": "test", "siteType": "COLO", "status": "Live"},
        {"siteName": "test", "siteType": "LOCAL", "status": "Live"},
    ]
    records2 = [{"siteName": "test", "siteType": "CELL", "status": "Live"}]
    records3 = [
        {"siteType": "LOCAL", "status": "Live", "siteName": "Site B//address"},
        {"siteType": "LOCAL", "status": "Live", "siteName": "Site B/300/address"},
    ]
    records4 = [{"siteName": "test_name", "siteType": "LOCAL", "status": "Live", "siteId": "test"}]
    # testing multiple colo fallout
    with pytest.raises(Exception):
        assert so.validate_site_records_v4(provided_site, records1) is None

    # testing cell logic
    monkeypatch.setattr(so, "sort_out_multiple_candidates_v2", lambda *args, **kwargs: None)
    assert so.validate_site_records_v4(provided_site, records2) == records2[0]

    # testing carrier logic
    records1.pop(0)
    provided_site["type"] = "test"
    provided_site["product_family"] = "carrier"
    with pytest.raises(Exception):
        assert so.validate_site_records_v4(provided_site, records1) is None

    # testing carrier fallout
    provided_site["type"] = "LOCAL"
    provided_site["product_family"] = "carrier"

    with pytest.raises(Exception):
        assert so.validate_site_records_v4(provided_site, records4) is None

    # building search logic
    provided_site["product_family"] = "test"
    assert so.validate_site_records_v4(provided_site, records1, True) is None

    # fuzzy match success
    monkeypatch.setattr(so, "find_fuzzy_matches", lambda *args, **kwargs: find_fuzzy_matches2)
    assert so.validate_site_records_v4(provided_site, records1) == {"siteName": "test1"}

    # test multiple candidates logic
    monkeypatch.setattr(so, "find_fuzzy_matches", lambda *args, **kwargs: (None, None, None))
    monkeypatch.setattr(so, "sort_out_multiple_candidates_v2", lambda *args, **kwargs: "best_site")
    assert so.validate_site_records_v4(provided_site, records1) == "best_site"

    # test fuzzy abort
    monkeypatch.setattr(so, "match_on_account_id_or_name", lambda *args, **kwargs: False)
    monkeypatch.setattr(so, "find_fuzzy_matches", lambda *args, **kwargs: find_fuzzy_matches3)

    with pytest.raises(Exception):
        assert so.validate_site_records_v4(provided_site, records4) is None

    # More than one site tied as a good match with room compare
    provided_site2 = {
        "clean_name": "Site B",
        "sf_id": "3",
        "product_name_order_info": "enterprise",
        "type": "LOCAL",
        "construction_job_number": False,
        "room": "300",
    }

    monkeypatch.setattr(so, "find_fuzzy_matches", lambda *args, **kwargs: (records3, None, None))
    assert so.validate_site_records_v4(provided_site2, records3) == records3[1]


@pytest.mark.unittest
def test_get_site_by_related_CID(monkeypatch):
    results = [
        {"Z_SITE_NAME": "test", "Z_SITE_TYPE": "test", "Z_CLLI": "test", "Z_LATITUDE": "test", "Z_LONGITUDE": "test"}
    ]

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: results)
    res = {
        "created new site": False,
        "siteName": "test",
        "siteType": "test",
        "clli": "test",
        "latitude": "test",
        "longitude": "test",
    }
    assert so.get_site_by_related_CID("333") == res

    results[0]["CIRCUIT_STATUS"] = "Live"
    results.append({})
    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: results)
    assert so.get_site_by_related_CID("333") == res

    monkeypatch.setattr(so, "get_result_as_list", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert so.get_site_by_related_CID("333") is None


@pytest.mark.unittest
def test_v5_site(client, monkeypatch):
    endpoint = "/arda/v5/site"
    payload = {
        "name": "test",
        "parent": "SYRACUSE",
        "type": "local",
        "address": "123 DAWN STREET",
        "city": "mount pleasant",
        "state": "TX",
        "zip_code": "78645",
        "clli": "1234",
        "fixed_access_code": "12",
        "product_name_order_info": "COM-DIA",
        "sf_id": "ACCT-123456",
        "product_family": "CTBH Wave Services",
    }

    res = {
        "created new site": False,
        "siteName": "test",
        "siteType": "test",
        "clli": "test",
        "latitude": "test",
        "longitude": "test",
    }

    monkeypatch.setattr(se, "find_or_create_a_site_v5", lambda *args, **kwargs: res)
    resp = client.put(endpoint, json=payload)
    assert resp.status_code == 200

    resp = client.put(endpoint, json="ab1")
    assert resp.status_code == 500


@pytest.mark.unittest
def test_site_clli_check():
    # bad test 7 character clli
    with pytest.raises(Exception):
        assert so.site_clli_check("testsite", "sevencl") is None

    # good test 8 character clli
    assert so.site_clli_check("testsite", "eightcli") is None


@pytest.mark.unittest
def test_rel_site_name_main(monkeypatch):
    # no related cid
    rel_payload = {"related_circuit_id": "27.L1XX.000002.GSO.TWCC", "product_family": "Secure Dedicated Internet"}

    monkeypatch.setattr(so, "get_circuit_site_info", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert so.rel_site_name_main(rel_payload) is None

    # retstring no path updated
    response = [{"CIRC_PATH_INST_ID": "123456", "Z_SITE_NAME": "good site"}]
    monkeypatch.setattr(so, "get_circuit_site_info", lambda *args, **kwargs: response)
    monkeypatch.setattr(so, "put_granite", lambda *args, **kwargs: {"retString": "No Dice"})

    with pytest.raises(Exception):
        assert so.rel_site_name_main(rel_payload) is None

    # good test
    monkeypatch.setattr(so, "put_granite", lambda *args, **kwargs: {"retString": "Path Updated"})
    assert so.rel_site_name_main(rel_payload) == {"siteName": "good site"}
