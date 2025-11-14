import pytest
from arda_app.bll import scrape_ip as si
from copy import deepcopy


@pytest.mark.unittest
def test_scrape_ip_main(monkeypatch):
    class MockSalesforceConnection:
        def get_epr_fields(self, *args, **kwargs):
            return ["good"]

    mockcall = MockSalesforceConnection()
    monkeypatch.setattr(si, "SalesforceConnection", lambda *args, **kwargs: mockcall)
    monkeypatch.setattr(si, "reformat_fields", lambda *args, **kwargs: "good")

    assert si.scrape_ip_main("epr") == "good"


sample_sf_resp = {
    "Engineering_Job_Type__c": "New",
    "PRISM_Id__c": "5338077",
    "CJ_Sub_Status__c": None,
    "Fiber_Building_Serviceability_Status__c": "Other Addressable",
    "SR_Order_Type__c": "New Install",
}


@pytest.mark.unittest
def test_get_service_type():
    # testing net_new_cj
    net_new_cj_sf_resp = deepcopy(sample_sf_resp)
    assert si.get_service_type(net_new_cj_sf_resp) == "net_new_cj"

    # testing net_new_qc
    net_new_qc_sf_resp = deepcopy(sample_sf_resp)
    net_new_qc_sf_resp["Fiber_Building_Serviceability_Status__c"] = "Quick Connect On-Net"
    net_new_qc_sf_resp["PRISM_Id__c"] = None
    assert si.get_service_type(net_new_qc_sf_resp) == "net_new_qc"

    # net_new_serviceable
    net_new_serviceable_sf_resp = deepcopy(sample_sf_resp)
    net_new_serviceable_sf_resp["PRISM_Id__c"] = None
    net_new_serviceable_sf_resp["Fiber_Building_Serviceability_Status__c"] = None
    assert si.get_service_type(net_new_serviceable_sf_resp) == "net_new_serviceable"

    net_new_serviceable_sf_resp["PRISM_Id__c"] = "5338077"
    net_new_serviceable_sf_resp["CJ_Sub_Status__c"] = "Not Required: Location Serviceable"
    assert si.get_service_type(net_new_serviceable_sf_resp) == "net_new_serviceable"

    # disconnect
    disconnect_sf_resp = deepcopy(sample_sf_resp)
    disconnect_sf_resp["Engineering_Job_Type__c"] = None
    disconnect_sf_resp["SR_Order_Type__c"] = "Disconnect"
    assert si.get_service_type(disconnect_sf_resp) == "disconnect"

    disconnect_sf_resp["Engineering_Job_Type__c"] = "blah"
    with pytest.raises(Exception) as excinfo:
        si.get_service_type(disconnect_sf_resp)
    assert 500 == excinfo.value.code

    # bw_change
    bw_change_sf_resp = deepcopy(sample_sf_resp)
    bw_change_sf_resp["Engineering_Job_Type__c"] = "Upgrade"
    assert si.get_service_type(bw_change_sf_resp) == "bw_change"

    bw_change_sf_resp["Engineering_Job_Type__c"] = "Downgrade"
    assert si.get_service_type(bw_change_sf_resp) == "bw_change"

    # change_logical
    change_logical_sf_resp = deepcopy(sample_sf_resp)
    change_logical_sf_resp["Engineering_Job_Type__c"] = "Logical Change"
    assert si.get_service_type(change_logical_sf_resp) == "change_logical"


@pytest.mark.unittest
def test_sf_connection(monkeypatch):
    # purposefully pass incorrect output to test failure check
    monkeypatch.setattr(si, "SalesforceConnection", lambda *args, **kwargs: None)
    with pytest.raises(Exception) as excinfo:
        si.scrape_ip_main("nonsense!!")
    assert 500 == excinfo.value.code


@pytest.mark.unittest
def test_get_epr_fields(monkeypatch):
    class MockSalesforceConnectionBad1:
        def get_epr_fields(self, *args, **kwargs):
            return None

    class MockSalesforceConnectionBad2:
        def get_epr_fields(self, *args, **kwargs):
            return ["non", "sense"]

    mockcall1 = MockSalesforceConnectionBad1()
    mockcall2 = MockSalesforceConnectionBad2()

    monkeypatch.setattr(si, "SalesforceConnection", lambda *args, **kwargs: mockcall1)
    with pytest.raises(Exception) as excinfo:
        si.scrape_ip_main("a")
    assert 500 == excinfo.value.code

    monkeypatch.setattr(si, "SalesforceConnection", lambda *args, **kwargs: mockcall2)
    with pytest.raises(Exception) as excinfo:
        si.scrape_ip_main("b")
    assert 500 == excinfo.value.code


@pytest.mark.unittest
def test_reformat_fields(monkeypatch):
    # patch over get_service_type, test standard output with assert and real inputs
    bad_sf_resp = {
        "attributes": {
            "type": "Engineering__c",
            "url": "/services/data/v52.0/sobjects/Engineering__c/a2g4000000452SLAAY",
        },
        "Name": "ENG-00600673",
        "Id": "a2g4000000452SLAAY",
        "Circuit_ID2__c": "57.L1XX.000002.713.TWCC",
        "Product_Family__c": "Enterprise Metro Ethernet",
        "Product_Name_order_info__c": "MetroE",
        "Service_Location_Address__c": "1 Guthrie Sq Sayre PA 18840",
        "SR_Order_Type__c": "Disconnect",
        "Engineering_Job_Type__c": "Partial Disconnect",
        "Legacy_Company__c": "TWC",
        "DIA_Type__c": None,
        "IP_Address_Requested__c": None,
        "BuildType__c": None,
        "PRISM_Id__c": None,
        "Fiber_Building_Serviceability_Status__c": "On-Net",
        "CJ_Sub_Status__c": None,
    }
    expected_reformatted_resp = {
        "z_side_info": {
            "service_type": "disconnect",
            "engineering_id": "ENG-00600673",
            "cid": "57.L1XX.000002.713.TWCC",
            "product_name": "MetroE",
            "legacy_company": "TWC",
            "ipv4_type": None,
            "block_size": None,
            "build_type": None,
        },
        "notes": "No Sales Engineering notes found",
    }
    monkeypatch.setattr(si, "get_service_type", lambda *args, **kwargs: "disconnect")
    assert si.reformat_fields(bad_sf_resp) == expected_reformatted_resp
