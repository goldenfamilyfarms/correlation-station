def test_status_with_missing_param(client):
    """Test not providing a resource_id results in a 400"""
    response = client.get("/palantir/v1/resourcestatus")
    assert response.status_code == 400


def test_status_with_bad_resource(client):
    """Test providing an invalid resource_id results in correct error message"""
    response = client.get("palantir/v1/resourcestatus?resourceId=3")
    assert response.status_code == 500
    assert response.json["message"] == "Resource not found"
