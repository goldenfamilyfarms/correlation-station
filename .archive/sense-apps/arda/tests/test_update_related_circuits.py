import pytest

from arda_app.bll import all_products
from tests.data import update_related_circuits_data


@pytest.mark.unittest
def test_update_related_circuits_epl_evpl_no_address_match(monkeypatch):
    body = update_related_circuits_data.mock_payload_epl_no_address_match()
    monkeypatch.setattr(
        all_products, "add_path_to_granite", lambda x, y, z: {"circuit_id": "51.L1XX.008342..CHTR", "status": "success"}
    )
    monkeypatch.setattr(
        all_products, "get_transport_path_data", update_related_circuits_data.mock_get_transport_path_data
    )
    monkeypatch.setattr(all_products, "create_circuit_path_data", update_related_circuits_data.mock_circuit_path_data)
    monkeypatch.setattr(all_products, "get_existing_path_elements", update_related_circuits_data.mock_path_elements)

    response = all_products.update_related_circuits(
        body["related_circuit_ids"], body["transport_path"], body["service_location_address"]
    )
    assert response == [{"circuit_id": "51.L1XX.008342..CHTR", "status": "failure"}]


@pytest.mark.unittest
def test_update_related_circuits_epl_a_address_match(monkeypatch):
    body = update_related_circuits_data.mock_payload_epl_a_address()
    monkeypatch.setattr(
        all_products,
        "add_path_to_granite",
        lambda x, y, z, m: {"circuit_id": "51.L1XX.008342..CHTR", "status": "success"},
    )
    monkeypatch.setattr(
        all_products, "get_transport_path_data", update_related_circuits_data.mock_get_transport_path_data
    )
    monkeypatch.setattr(all_products, "create_circuit_path_data", update_related_circuits_data.mock_circuit_path_data)
    monkeypatch.setattr(all_products, "get_existing_path_elements", update_related_circuits_data.mock_path_elements)

    response = all_products.update_related_circuits(
        body["related_circuit_ids"], body["transport_path"], body["service_location_address"]
    )
    assert all_products.sequence == "1"
    assert response == [{"circuit_id": "51.L1XX.008342..CHTR", "status": "success"}]


@pytest.mark.unittest
def test_update_related_circuits_evpl_z_address_match(monkeypatch):
    body = update_related_circuits_data.mock_payload_evpl_z_addresss()
    monkeypatch.setattr(
        all_products,
        "add_path_to_granite",
        lambda x, y, z, m: {"circuit_id": "51.L1XX.008342..CHTR", "status": "success"},
    )
    monkeypatch.setattr(
        all_products, "get_transport_path_data", update_related_circuits_data.mock_get_transport_path_data
    )
    monkeypatch.setattr(all_products, "create_circuit_path_data", update_related_circuits_data.mock_circuit_path_data)
    monkeypatch.setattr(all_products, "get_existing_path_elements", update_related_circuits_data.mock_path_elements)

    response = all_products.update_related_circuits(
        body["related_circuit_ids"], body["transport_path"], body["service_location_address"]
    )
    assert all_products.sequence == "2"
    assert response == [{"circuit_id": "51.L1XX.008342..CHTR", "status": "success"}]
