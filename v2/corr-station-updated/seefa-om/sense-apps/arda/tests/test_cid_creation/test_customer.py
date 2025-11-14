import pytest
from arda_app.api import customer as custe
from unittest.mock import Mock
from arda_app.bll.cid import customer as cust
from tests.test_cid_creation.test_cid_creation_mock_functions import MockResponse, test_customer


@pytest.mark.unittest
def test_check_value():
    assert cust.check_value(test_customer, "name") is True
    assert cust.check_value(test_customer, "site") is False
    assert cust.check_value("customer", "NOTHING WITH A VALUE") is False


@pytest.mark.unittest
def test_create_customer_v3(monkeypatch):
    data = {
        "name": "test customer",
        "sf_id": "123",
        "address": "address",
        "city": "city",
        "zip_code": "12345",
        "type": "carrier",
        "country": "USA",
    }

    # customer yes
    def mock_post_granite(*args, **kwargs):
        return MockResponse("success")

    monkeypatch.setattr(cust, "post_granite", mock_post_granite)
    assert cust.create_customer_v3(data) == "123"

    # customer no
    def mock_post_granite(*args, **kwargs):
        return MockResponse("fail", 500)

    monkeypatch.setattr(cust, "post_granite", mock_post_granite)

    with pytest.raises(Exception):
        assert cust.create_customer_v3(data) is None


@pytest.mark.unittest
def test_customer_endpoint(monkeypatch, client):
    cust_endpoint = "/arda/v4/customer"
    monkeypatch.setattr(custe, "find_or_create_a_customer_v3", lambda *arg: {"created_new_customer": False})

    r = client.put(cust_endpoint, json=test_customer)
    assert r.status_code == 200

    resp = client.put(cust_endpoint, json="ab1")
    assert resp.status_code == 500


@pytest.mark.unittest
def test_get_customer_v3(monkeypatch):
    monkeypatch.setattr(cust, "get_result_as_list", lambda *args, **kwargs: [{"id": "test"}])
    monkeypatch.setattr(cust, "update_sf_id", lambda *args, **kwargs: None)
    assert cust.get_customer_v3({"sf_id": "Test"}, True) == {"id": "test"}

    assert cust.get_customer_v3({"sf_id": "Test"}) == "test"

    test_mock = Mock(side_effect=[None, [{"id": None}], ["test"]])
    monkeypatch.setattr(cust, "update_customer_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(cust, "get_result_as_list", test_mock)
    assert cust.get_customer_v3({"sf_id": "Test"}, True) == "test"

    mock_query = iter(
        [[], [{"id": "TEST CUSTOMER", "address": "address"}], [{"SFID": "TEST CUSTOMER", "address": "address"}]]
    )
    monkeypatch.setattr(cust, "get_result_as_list", lambda *args, **kwargs: next(mock_query))
    monkeypatch.setattr(cust, "update_customer_id", lambda *args, **kwargs: None)

    assert (
        cust.get_customer_v3({"name": "name name name", "sf_id": "1234", "address": "address", "city": "city"})
        == "TEST CUSTOMER"
    )

    monkeypatch.setattr(cust, "get_result_as_list", lambda *args, **kwargs: None)
    assert cust.get_customer_v3({"sf_id": "Test"}, True) is None


@pytest.mark.unittest
def test_find_or_create_a_customer_v3(monkeypatch):
    customer_data = {"name": "nothing important here", "sf_id": "123"}
    monkeypatch.setattr(cust, "get_customer_v3", lambda *args, **kwargs: None)
    monkeypatch.setattr(cust, "create_customer_v3", lambda *args, **kwargs: "test")
    assert cust.find_or_create_a_customer_v3(customer_data) == {"customer": "test", "created new customer": True}


@pytest.mark.unittest
def test_update_customer_id(monkeypatch):
    monkeypatch.setattr(cust, "put_granite", lambda *args, **kwargs: True)
    assert (
        cust.update_customer_id(
            {"CUST_INST_ID": "test", "TYPE": "test", "SFID": "test"},
            {"CUST_INST_ID": "test2", "TYPE": "test2", "SFID": "test2", "name": "test2"},
        )
        is None
    )


@pytest.mark.unittest
def test_update_sf_id(monkeypatch):
    monkeypatch.setattr(cust, "put_granite", lambda *args, **kwargs: True)
    assert cust.update_sf_id({"id": "test", "type": "test"}, {"id": "test2", "type": "test2", "name": "test"}) is None


@pytest.mark.unittest
def test_clean_billing_name():
    # good test split on dash remove (- INDIVIDUALLY BILLED)
    customer_data = {"name": "HARVEY BAKER PLUMBING INC - INDIVIDUALLY BILLED", "sf_id": "ACCT-27032"}

    assert cust.clean_billing_name(customer_data) == "HARVEY BAKER PLUMBING INC"

    # good test split on INDIVIDUALLY BILLED remove (INDIVIDUALLY BILLED)
    customer_data = {"name": "HARVEY BAKER PLUMBING INC INDIVIDUALLY BILLED", "sf_id": "ACCT-27032"}

    assert cust.clean_billing_name(customer_data) == "HARVEY BAKER PLUMBING INC"


@pytest.mark.unittest
def test_cid_entrance_criteria():
    # bad test - colo_datacenter = Yes
    payload = {"name": "Name", "type": "ENTERPRISE", "colo_datacenter": "Yes"}
    with pytest.raises(Exception):
        assert cust.cid_entrance_criteria(payload) is None

    # good test - colo_datacenter = No
    payload["colo_datacenter"] = "No"
    assert cust.cid_entrance_criteria(payload) is None
