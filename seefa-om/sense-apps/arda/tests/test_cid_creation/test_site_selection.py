import pytest

from arda_app.bll.cid import site as so
from arda_app.bll.cid.site import get_site_by_enni, validate_site_records_v4


@pytest.mark.unittest
def test_site_by_enni_not_found(monkeypatch):
    monkeypatch.setattr(so, "get_result_as_list", lambda *args: [])

    with pytest.raises(Exception):
        assert get_site_by_enni("111") is None


@pytest.mark.unittest
def test_site_validation_aborts(monkeypatch):
    provided_site = {
        "clean_name": "TEST SITE",
        "sf_id": "3",
        "product_name_order_info": "enterprise",
        "type": "LOCAL",
        "construction_job_number": False,
    }
    multiple_colo_records = [
        {"siteType": "COLO", "status": "Live", "siteName": "Site A"},
        {"siteType": "COLO", "status": "Live", "siteName": "Site B"},
    ]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_colo_records) is None

    # Found multiple similarly named sites
    multiple_local_records = [
        {"siteType": "LOCAL", "status": "Live", "clean_name": "TEST SITE A", "siteName": "TEST SITE A"},
        {"siteType": "LOCAL", "status": "Live", "clean_name": "TEST SITE B", "siteName": "TEST SITE B"},
    ]
    monkeypatch.setattr(so, "is_ctbh", lambda *args: True)
    monkeypatch.setattr(so, "find_similar_names", lambda *args: multiple_local_records)

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_local_records) is None

    # Multiple potential matches (buildings)
    multiple_local_buildings = [
        {"siteType": "BUILDING", "status": "Live", "clean_name": "TEST SITE A", "siteName": "TEST SITE A"},
        {"siteType": "BUILDING", "status": "Live", "clean_name": "TEST SITE B", "siteName": "TEST SITE B"},
    ]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_local_buildings, building_search=True) is None

    # More than one site tied as a good match
    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_local_records) is None

    # Instead of creating a new site, found potential match
    one_obvious_match = [
        {
            "siteType": "LOCAL",
            "status": "Live",
            "clean_name": "TEST SITE A",
            "siteName": "TEST SITE A",
            "customerRec": [{"sfUniqueCustomerId_UDA": "3"}],
        },
        {
            "siteType": "LOCAL",
            "status": "Live",
            "clean_name": "XYZ",
            "siteName": "XYZ",
            "customerRec": [{"sfUniqueCustomerId_UDA": "3"}],
        },
    ]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, one_obvious_match) is None


@pytest.mark.unittest
def test_site_validation_v4_aborts(monkeypatch):
    provided_site = {
        "name": "TESTSITE10",
        "clean_name": "TEST SITE",
        "sf_id": "3",
        "product_name_order_info": "enterprise",
        "type": "LOCAL",
        "product_family": "blah",
        "construction_job_number": False,
    }

    # Multiple COLO/HUB/POP records at this address
    multiple_colo_records = [
        {"siteType": "COLO", "status": "Live", "siteName": "Site A"},
        {"siteType": "COLO", "status": "Live", "siteName": "Site B"},
    ]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_colo_records) is None

    # Found multiple similarly named sites
    multiple_local_records = [
        {"siteType": "LOCAL", "status": "Live", "clean_name": "TEST SITE A", "siteName": "TEST SITE A"},
        {"siteType": "LOCAL", "status": "Live", "clean_name": "TEST SITE B", "siteName": "TEST SITE B"},
    ]

    # Multiple potential matches (buildings)
    multiple_local_buildings = [
        {"siteType": "BUILDING", "status": "Live", "clean_name": "TEST SITE A", "siteName": "TEST SITE A"},
        {"siteType": "BUILDING", "status": "Live", "clean_name": "TEST SITE B", "siteName": "TEST SITE B"},
    ]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_local_buildings, building_search=True) is None

    # More than one site tied as a good match
    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_local_records) is None

    monkeypatch.setattr(so, "is_ctbh", lambda *args: True)

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, multiple_local_records) is None

    # Instead of creating a new site, found potential match
    monkeypatch.setattr(so, "is_ctbh", lambda *args: False)

    one_obvious_match = [
        {
            "siteType": "LOCAL",
            "status": "Live",
            "clean_name": "TEST SITE A",
            "siteName": "TEST SITE A",
            "customerRec": [{"sfUniqueCustomerId_UDA": "3"}],
        },
        {
            "siteType": "LOCAL",
            "status": "Live",
            "clean_name": "XYZ",
            "siteName": "XYZ",
            "customerRec": [{"sfUniqueCustomerId_UDA": "3"}],
        },
    ]

    assert validate_site_records_v4(provided_site, one_obvious_match) == one_obvious_match[0]


@pytest.mark.unittest
def test_site_validation_v4_selections():
    provided_site = {
        "name": "TEST SITE 10",
        "sf_id": "3",
        "clean_name": "TEST SITE 10",
        "product_family": "stuff",
        "product_name_order_info": "enterprise",
        "type": "LOCAL",
        "clli": "12345",
        "construction_job_number": False,
    }
    two_close_match_local_records = [
        {"siteType": "Local", "status": "Live", "siteName": "TEST SITES A 11"},
        {"siteType": "Local", "status": "Live", "siteName": "TEST SITE B 12"},
    ]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, two_close_match_local_records, False) is None

    no_matches_local_records = [{"siteType": "Local", "status": "Live", "siteName": "TEST NO MATCH"}]

    with pytest.raises(Exception):
        assert validate_site_records_v4(provided_site, no_matches_local_records, False) is None
