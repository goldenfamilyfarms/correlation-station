import json
import requests

from palantir_app.apis.v3 import ise
from palantir_app.common.ise_operations import find_location

# logger = logging.getLogger(__name__)

root_url = "/palantir/v1/ise/"
record = "device_record"
lookup = "id_lookup"


"""General tests for endpoints"""


def test_api_no_endpoints(client):
    """Test ise api with no endpoint specified"""
    url = f"{root_url}"
    resp = client.get(url)
    assert resp.status_code == 500


def test_api_invalid_endpoint(client):
    """Test ise api with invalid endpoint 'iserecords' specified"""
    url = f"{root_url}iserecords"
    resp = client.get(url)
    assert resp.status_code == 500


def test_lookup_invalid_param(client):
    """Test id_lookup with invalid param 'devicetype'"""
    device_type = "devicetype"
    device = "SNMNCAFJ2ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 500
    assert resp_data is not None


def test_lookup_no_params(client):
    """Test id_lookup without any params"""
    url = f"{root_url}{lookup}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 500
    assert resp_data is not None


def test_record_invalid_param(client):
    """Test device_record with invalid param 'deviceid'"""
    ise_id = "123123123"
    url = f"{root_url}{record}?deviceid={ise_id}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 500
    assert resp_data is not None


def test_record_no_params(client):
    """Test device_record without any params"""
    url = f"{root_url}{record}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 500
    assert resp_data is not None


"""Tests for id_lookup endpoint"""


# INVALID HOSTNAME TESTS


def test_lookup_invalid_type(client):
    """Test id_lookup with invalid type 'host'"""
    # NOTE: 'type' value MUST match either "name" or "ipaddress" (case insensitive)
    device_type = "host"
    device = "SNMNCAFJ2ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 500
    assert resp_data is not None


def test_lookup_not_found_host(client):
    """Test id_lookup with a hostname not in ISE"""
    device_type = "name"
    device = "ZZZZZZZZZZZ"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp_data["west_result"] == "none"
    assert resp_data["east_result"] == "none"
    assert resp_data["south_result"] == "none"
    assert resp_data is not None


# VALID HOSTNAME TESTS


def test_lookup_valid_type_hostname(client):
    """Test id_lookup with valid type 'hostname'"""
    # NOTE: 'type' value MUST match either "name" or "ipaddress" (case insensitive)
    device_type = "name"
    device = "SNMNCAFJ2ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_lookup_valid_host(client):
    """Test id_lookup with valid hostname"""
    device_type = "name"
    device = "SNMNCAFJ2ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_lookup_valid_host_west(client):
    """Test id_lookup with valid hostname for WEST ISE"""
    device_type = "name"
    device = "SNMNCAFJ2ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["west_result"] is not None


def test_lookup_valid_host_east(client):
    """Test id_lookup with valid hostname for EAST ISE"""
    device_type = "name"
    device = "AKRNOHKJ1ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["east_result"] is not None


def test_lookup_valid_host_south(client):
    """Test id_lookup with valid hostname for SOUTH ISE"""
    device_type = "name"
    device = "snaxtx431cw"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["south_result"] is not None


def test_lookup_valid_host_east_and_south(client):
    """Test id_lookup with valid hostname for both EAST and SOUTH ISE"""
    device_type = "name"
    device = "JHCYTN831ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["east_result"] is not None
    assert resp_data["south_result"] is not None


def test_lookup_valid_host_east_and_west(client):
    """Test id_lookup with valid hostname for both EAST and WEST ISE"""
    device_type = "name"
    device = "JFTWKYBC1ZW"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["east_result"] is not None
    assert resp_data["west_result"] is not None


# INVALID IP TESTS


def test_lookup_invalid_type_ipaddress(client):
    """Test id_lookup with invalid type 'ipaddr'"""
    # NOTE: 'type' value MUST match either "name" or "ipaddress" (case insensitive)
    device_type = "ipaddr"
    device = "0.0.0.0"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    assert resp.status_code == 500


def test_lookup_invalid_ip(client):
    """Test id_lookup with an IP that isnt in ISE"""
    device_type = "ipaddress"
    device = "0.0.0.0"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp_data["west_result"] == "none"
    assert resp_data["east_result"] == "none"
    assert resp_data["south_result"] == "none"


# VALID IP TESTS


def test_lookup_valid_type_ipaddress(client):
    """Test id_lookup with valid type 'ipaddress'"""
    # NOTE: 'type' value MUST match either "name" or "ipaddress" (case insensitive)
    device_type = "ipaddress"
    device = "10.0.248.111"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_lookup_valid_ip(client):
    """Test id_lookup with valid IP"""
    device_type = "ipaddress"
    device = "10.0.248.111"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_lookup_valid_ip_east(client):
    """Test id_lookup with valid IP for EAST ISE"""
    device_type = "ipaddress"
    device = "10.8.71.167"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["east_result"] is not None


def test_lookup_valid_ip_west(client):
    """Test id_lookup with valid IP for WEST ISE"""
    device_type = "ipaddress"
    device = "10.0.248.111"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["west_result"] is not None


def test_lookup_valid_ip_south(client):
    """Test id_lookup with valid IP for SOUTH ISE"""
    device_type = "ipaddress"
    device = "24.73.242.51"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["south_result"] is not None


def test_lookup_valid_ip_east_and_west(client):
    """Test id_lookup with valid IP for both EAST and WEST ISE"""
    device_type = "ipaddress"
    device = "10.9.92.66"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["east_result"] is not None
    assert resp_data["west_result"] is not None


def test_lookup_valid_ip_east_and_south(client):
    """Test id_lookup with valid IP for both EAST and SOUTH ISE"""
    device_type = "ipaddress"
    device = "10.27.155.43"
    url = f"{root_url}{lookup}?type={device_type}&device={device}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))["results"]
    assert resp.status_code == 200
    assert resp_data["east_result"] is not None
    assert resp_data["south_result"] is not None


"""Tests for device_record endpoint"""


def test_record_invalid_id(client):
    """Test device_record with an invalid ID"""
    ise_id = "1"
    url = f"{root_url}{record}?id={ise_id}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp_data["west_record"] == "none"
    assert resp_data["east_record"] == "none"
    assert resp_data["south_record"] == "none"


def test_record_valid_id(client):
    """Test device_record with valid ID"""
    ise_id = "08250aa0-0f5a-11ea-a794-5abe77267629"
    url = f"{root_url}{record}?id={ise_id}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data is not None


def test_record_valid_id_east(client):
    """Test device_record with valid ID for EAST ISE"""
    ise_id = "ca604350-e007-11e9-beb2-62c9a4cad2c2"
    url = f"{root_url}{record}?id={ise_id}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data["east_record"] is not None


def test_record_valid_id_west(client):
    """Test device_record with valid ID for WEST ISE"""
    ise_id = "08250aa0-0f5a-11ea-a794-5abe77267629"
    url = f"{root_url}{record}?id={ise_id}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data["west_record"] is not None


def test_record_valid_id_south(client):
    """Test device_record with valid ID for SOUTH ISE"""
    ise_id = "f4901cc0-0c00-11ea-9013-a640979a5290"
    url = f"{root_url}{record}?id={ise_id}"
    resp = client.get(url)
    resp_data = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert resp_data["south_record"] is not None


# Tests for device creates


def test_location_translation():
    """Test market and extended market logic is translated correctly into
    the location string"""
    locations = {
        "BYFDWIBL1ZW": ["MWM", "F-CHTR-C", "CHTR-Central"],
        "NYMSNYRF1ZW": ["NEM", "EastRegion", "TWC:New York City"],
        "CLMTFLLJ2ZW": ["SEM", "F-BHN-SE", "BHN-Florida-SE"],
        "EDBHTXFFG1W": ["SWM", None, "Southwest"],
        "HNBJCAEF1ZW": ["PWM", "WestRegion", "Pacwest"],
    }
    for host, i in locations.items():
        assert find_location(i[0], i[1], host) == i[2]


class MockResponseObject:
    status_code = 201

    @staticmethod
    def json():
        return ""


def test_create_device_in_ise(client, monkeypatch):
    """Test the data is formatted correctly when creating a device in ise"""

    # mock incoming data from cedr
    def mock_cedr(*_):
        return [("10.10.10.10", "AMDAOH031ZW", "Adva", "MWM", "EDGE", "WestRegion")]

    monkeypatch.setattr(ise, "query_by_tid_or_ip", mock_cedr)

    # mock outgoing call to ise, assert data is correct
    def mock_ise(*args, **kwargs):
        device_group = ["Access#TWC#EDGE", "Location#All Locations#Midwest", "Device Type#All Device Types#Adva"]
        assert kwargs["json"]["NetworkDevice"]["NetworkDeviceGroupList"] == device_group
        return MockResponseObject

    monkeypatch.setattr(requests, "post", mock_ise)

    r = client.post("/palantir/v1/ise/device_record?ip=10.10.10.10")
    assert r.status_code == 201
