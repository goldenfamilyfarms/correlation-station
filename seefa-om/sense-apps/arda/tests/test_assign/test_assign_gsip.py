import copy

import pytest

from arda_app.api import assign_gsip

from arda_app.bll.assign import gsip

PAYLOAD = {
    "cid": "81.L1XX.006522..TWCC",
    "product_name": "Carrier E-Access (Fiber)",
    "legacy_company": "Charter",
    "class_of_service_type": "Bronze",
}

GRANITE_RESPONSE = [{"A_LONGITUDE": "", "Z_LONGITUDE": "", "A_LATITUDE": "", "Z_LATITUDE": "", "SERVICE_LEVEL": ""}]

ENDPOINT = "arda/v1/assign_gsip"


@pytest.mark.unittest
def test_json_error(client):
    """Test design with a valid, defined cid"""
    resp = client.post(ENDPOINT, data=b"/")

    assert resp.status_code == 500
    assert "JSON decode error" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_no_cid(client):
    """Test design with a valid, defined cid"""
    data = copy.deepcopy(PAYLOAD)
    del data["cid"]

    resp = client.post(ENDPOINT, json=data)

    assert resp.status_code == 500
    assert "Required query parameter(s) not specified: cid" in str(resp.json().get("message"))


@pytest.mark.unittest
def test_wrong_cofst(client):
    """Test design with a valid, defined cid"""
    data = copy.deepcopy(PAYLOAD)
    data["class_of_service_type"] = "wrong class"

    resp = client.post(ENDPOINT, json=data)

    assert resp.status_code == 500
    assert "class_of_service_type" in str(resp.json())


@pytest.mark.unittest
def test_wrong_service_level(monkeypatch, client):
    """Test design with a valid, defined cid"""
    g_res = copy.deepcopy(GRANITE_RESPONSE)
    g_res[0]["SERVICE_LEVEL"] = "wrong SERVICE LEVEL"
    res = "Class of Service could not be determined, please investigate."

    monkeypatch.setattr(assign_gsip, "assign_gsip_main", lambda *args, **kwargs: res)

    resp = client.post(ENDPOINT, json=PAYLOAD)
    # assert resp.status_code == 500
    with pytest.raises(Exception):
        assert "Class of Service could not be determined" in resp.json().get("message")


@pytest.mark.unittest
def test_wrong_product_name(client):
    """Test design with a valid, defined cid"""
    data = copy.deepcopy(PAYLOAD)
    data["product_name"] = "wrong product name"

    resp = client.post(ENDPOINT, json=data)

    assert resp.status_code == 500
    assert "product name" in str(resp.json())


@pytest.mark.unittest
def test_success_Carrier(monkeypatch, client):
    """Test design with a valid, defined cid"""
    g_res = copy.deepcopy(GRANITE_RESPONSE)
    g_res[0]["SERVICE_LEVEL"] = "METRO"

    monkeypatch.setattr(gsip, "get_granite", lambda *_: g_res)
    monkeypatch.setattr(gsip, "put_granite", lambda *_: True)

    resp = client.post(ENDPOINT, json=PAYLOAD)

    assert resp.status_code == 201
    assert "GSIP Attributes have been added successfully" in resp.json().get("message")


@pytest.mark.unittest
def test_success_Fiber(monkeypatch, client):
    """Test design with a valid, defined cid"""
    data = copy.deepcopy(PAYLOAD)
    data["product_name"] = "Fiber Internet Access"
    cid_resp = [
        {
            "aSideCustomer": "ACCT-15081218",
            "aSideSiteName": "SRSVFL16-BHN/HUB TAMP57-WHITFIELD",
            "bandwidth": "1 Gbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-15081218",
            "orderNumber": "ENG-01374073, ENG-01374074",
            "pathId": "81.L1XX.006522..TWCC",
            "pathInService": "2020-04-03 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "CUS-SECURE INTERNET ACCESS",
            "servicePriority": "NO",
            "status": "Designed",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-15081218",
            "zSideSiteName": "CTPKFLFH-EVO MERCHANT SERVICES/300/12750 CITRUS PARK LN",
            "instanceProtocol": "9999",
        }
    ]

    monkeypatch.setattr(gsip, "get_granite", lambda *_: GRANITE_RESPONSE)
    monkeypatch.setattr(gsip, "put_granite", lambda *_: True)
    monkeypatch.setattr(gsip, "get_attributes_for_path", lambda *_: cid_resp)

    resp = client.post(ENDPOINT, json=data)

    assert resp.status_code == 201
    assert "GSIP Attributes have been added successfully" in resp.json().get("message")


@pytest.mark.unittest
def test_success_epl_fiber(monkeypatch, client):
    """Test success with EPL product name"""
    data = copy.deepcopy(PAYLOAD)
    data["product_name"] = "EPL (Fiber)"
    data["legacy_company"] = "TWC"
    data["class_of_service_type"] = "Bronze"

    monkeypatch.setattr(gsip, "get_granite", lambda *_: GRANITE_RESPONSE)
    monkeypatch.setattr(gsip, "put_granite", lambda *_: True)

    resp = client.post(ENDPOINT, json=data)

    assert resp.status_code == 201
    assert "GSIP Attributes have been added successfully" in resp.json().get("message")


@pytest.mark.unittest
def test_success_ep_lan_fiber(monkeypatch, client):
    data = copy.deepcopy(PAYLOAD)
    data["product_name"] = "EP-LAN (Fiber)"
    data["legacy_company"] = "Bright House"
    data["class_of_service_type"] = "Gold"

    monkeypatch.setattr(gsip, "get_granite", lambda *_: GRANITE_RESPONSE)
    monkeypatch.setattr(gsip, "put_granite", lambda *_: True)
    monkeypatch.setattr(gsip, "cos_check", lambda *args, **kwargs: "GOLD METRO")

    resp = client.post(ENDPOINT, json=data)

    assert resp.status_code == 201
    assert "GSIP Attributes have been added successfully" in resp.json().get("message")


@pytest.mark.unittest
def test_assign_gsip(monkeypatch):
    success = {"message": "GSIP Attributes have been added successfully."}
    payload = {
        "cid": "21.L1XX.006991..TWCC",
        "product_name": "Fiber Internet Access",
        "legacy_company": "Charter",
        "class_of_service_type": "Gold",
        "path_inst_id": "",
    }

    cid_resp = [{"product_Service_UDA": "CUS-SECURE INTERNET ACCESS"}]

    monkeypatch.setattr(gsip, "get_attributes_for_path", lambda *args, **kwargs: cid_resp)
    monkeypatch.setattr(gsip, "put_granite", lambda *args, **kwargs: None)
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = "path_inst_id"
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "SIP - Trunk (Fiber)"
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = ""
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "Hosted Voice - (DOCSIS)"
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = "path_inst_id"
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "Carrier E-Access (Fiber)"
    lat_lon = [
        {
            "A_LATITUDE": "A_LATITUDE",
            "A_LONGITUDE": "A_LONGITUDE",
            "Z_LATITUDE": "Z_LATITUDE",
            "Z_LONGITUDE": "Z_LONGITUDE",
        }
    ]
    sl = [{"SERVICE_LEVEL": "METRO"}]
    cs_res = iter([lat_lon, sl, lat_lon, sl])
    monkeypatch.setattr(gsip, "get_granite", lambda *args, **kwargs: next(cs_res))
    assert gsip.assign_gsip_main(payload) == success

    payload["class_of_service_type"] = ""
    payload["path_inst_id"] = ""
    monkeypatch.setattr(gsip, "get_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(gsip, "cos_check", lambda *args, **kwargs: "GOLD METRO")
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "Wireless Internet Access"
    payload["class_of_service_type"] = "Gold"
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = "path_inst_id"
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "FC + Remote PHY"
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = ""
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "EP-LAN (Fiber)"
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = "path_inst_id"
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "EPL (Fiber)"
    assert gsip.assign_gsip_main(payload) == success

    payload["path_inst_id"] = ""
    assert gsip.assign_gsip_main(payload) == success

    payload["product_name"] = "abort"

    with pytest.raises(Exception):
        assert gsip.assign_gsip_main(payload) == success
