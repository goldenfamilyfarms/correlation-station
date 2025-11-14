import json

import pytest
from werkzeug.exceptions import BadGateway

from beorn_app.dll import mdso
from beorn_app.dll.mdso import create_service, product_query


def mock_product_query(*args, **kwargs):
    mdso_prod_query_resp = "tests/mock_data/managed_services/v1products_product_query.json"
    with open(mdso_prod_query_resp) as f:
        data = json.load(f)
    return data


def mock_post_to_service(*args, **kwargs):
    mdso_service_post_resp = "tests/mock_data/managed_services/v1products_post_to_service.json"
    with open(mdso_service_post_resp) as f:
        data = json.load(f)
    return data


def mock_mdso_get_no_prod(*args, **kwargs):
    return {"bad": "data"}


def mock_mdso_get_items_no_0_elem(*args, **kwargs):
    return {"items": "data"}


def mock_mdso_get_items_no_id(*args, **kwargs):
    return {"items": [{"bad": "data"}]}


def mock_mdso_post_items_no_id(*args, **kwargs):
    return {"bad": "data"}


@pytest.mark.unittest
def test_product_query_no_product(monkeypatch):
    monkeypatch.setattr(mdso, "mdso_get", mock_mdso_get_no_prod)
    with pytest.raises(BadGateway) as http_error:
        product_query("foo")
        assert http_error.exception.code == 502


@pytest.mark.unittest
def test_product_query_no_0_elem(monkeypatch):
    monkeypatch.setattr(mdso, "mdso_get", mock_mdso_get_items_no_0_elem)
    with pytest.raises(BadGateway) as http_error:
        product_query("foo")
        assert http_error.exception.code == 502


@pytest.mark.unittest
def test_product_query_no_id(monkeypatch):
    monkeypatch.setattr(mdso, "mdso_get", mock_mdso_get_items_no_id)
    with pytest.raises(BadGateway) as http_error:
        product_query("foo")
        assert http_error.exception.code == 502


@pytest.mark.unittest
def test_product_query_success(monkeypatch):
    monkeypatch.setattr(mdso, "mdso_get", mock_product_query)
    assert product_query("foo") == "60147049-4a0c-4a36-b5a9-0910db2a9c15"


@pytest.mark.unittest
def test_create_service_no_id(monkeypatch):
    monkeypatch.setattr(mdso, "mdso_post", mock_mdso_post_items_no_id)
    with pytest.raises(BadGateway) as http_error:
        create_service("foo")
        assert http_error.exception.code == 502


@pytest.mark.unittest
def test_create_service_success(monkeypatch):
    monkeypatch.setattr(mdso, "mdso_post", mock_post_to_service)
    assert create_service("foo") == "601b18fa-711d-43cc-9ac3-bbda276e2a23"
