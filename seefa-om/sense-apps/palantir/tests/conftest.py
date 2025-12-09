import json

import pytest

import palantir_app


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Remove requests.sessions.Session.request for all tests."""
    monkeypatch.delattr("requests.sessions.Session.request")


@pytest.fixture
def client(request):
    palantir_app.app.config["TESTING"] = True
    client = palantir_app.app.test_client()

    return client


@pytest.fixture
def irregular_post():
    json = """
    [
        {"transactionID": "999",
         "zSide": {
             "ip": "65.189.178.70",
             "port": "GE-10/1/2",
             "vlan": "1300"
         },
         "aSide": {
             "ip": null,
             "port": null,
             "vlan": null
         }
        }
    ]"""
    return json


@pytest.fixture
def single_mx_post():
    """Generate sample JSON input like we would receive from Mulesoft

    Returns Python data structure of JSON data, NOT raw JSON
    """
    with open("tests/samples/single_mx_post.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def single_mx_post2():
    """Generate a second set of sample JSON input

    Returns a Python data structure
    """
    with open("tests/samples/single_mx_post2.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def double_mx_post():
    """Generate sample JSON input like we would receive from Mulesoft
    or another external caller

    Returns Python data structure of JSON data, NOT raw JSON
    """
    with open("tests/samples/dbl_mx_post.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def double_mx_resp():
    """Generate expected JSON response from `double_mx_post`"""
    with open("tests/samples/dbl_mx_resp.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def sample_bad_json():
    """Generate some bad JSON"""
    # Uses the wrong kind of quotes
    return b"[{'bad': 'quotes'}]"


@pytest.fixture
def single_mx_expected():
    """Generate expected JSON, given the file `samples/sample_post.json`

    Returns a Python data structure representing the JSON
    """
    with open("tests/samples/single_mx_resp.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def lab_test_1():
    with open("tests/samples/lab_test_1.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def lab_test_2():
    with open("tests/samples/lab_test_2.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def lab_test_3():
    with open("tests/samples/lab_test_3.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)


@pytest.fixture
def lab_test_4():
    with open("tests/samples/lab_test_4.json", "r") as f:
        json_data = f.read()
    return json.loads(json_data)
