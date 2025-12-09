import logging
import time
import unittest

import pytest
import requests

import palantir_app
from palantir_app.apis.v1.port import granite_call
from palantir_app.common.mdso_operations import (
    create_resource,
    delete_resource,
    generate_op_id,
    generate_status_op_id,
    get_existing_resource,
    get_product,
    status_call,
)

# from palantir_app.common.mdso_auth import create_token, delete_token
from palantir_app.dll.mdso import _create_token, _delete_token

logger = logging.getLogger(__name__)

RESOURCE_TYPE = "charter.resourceTypes.PortActivation"


def test_granite_call_bad_imput():
    msg, data = granite_call("xyz")
    assert msg
    assert not data


def test_granite_call_with_tid():
    msg, data = granite_call("AUSDTXIR2CW")
    assert msg is None
    assert data


def test_get_product():
    token = _create_token()
    headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}
    msg, product = get_product(headers, RESOURCE_TYPE)
    assert msg is None
    assert product
    _delete_token(token)


class TestPort(unittest.TestCase):
    def setUp(self):
        self.token = _create_token()
        self.headers = {"Accept": "application/json", "Authorization": "token {}".format(self.token)}
        self.resource_id = ""

        self.target = "AUSDTXIR5CW.ONE.TWCBIZ.COM"
        self.port_id = "ge-2/1/4"
        self.tid = "AUSDTXIR5CW"

        msg, product = get_product(self.headers, RESOURCE_TYPE)
        assert msg is None

        self.product_id = product
        self.timer = 1
        self.vendor = "JUNIPER"

        url = (
            f"{palantir_app.url_config.MDSO_BASE_URL}/bpocore/market/api/v1/resources"
            "?resourceTypeId=charter.resourceTypes.PortActivation&q=properties.deviceName:"
            f"{self.target},properties.portname:{self.port_id}&offset=0&limit=1000"
        )
        tries = 0
        resources = requests.get(url, headers=self.headers, verify=False, timeout=300)
        while resources.json()["items"] and tries <= 20:
            timeout = 0
            # make sure we're not deleting a resource in the in-between states which will hang it
            if resources.json()["items"][0]["properties"].get("orchState"):
                while (
                    resources.json()["items"][0]["properties"]["orchState"] in ("activating", "terminating")
                    and timeout <= 10
                ):
                    time.sleep(2)
                    timeout += 1
                    resources = requests.get(url, headers=self.headers, verify=False, timeout=300)
                assert resources.json()["items"][0]["properties"]["orchState"] not in (
                    "activating",
                    "terminating",
                )  # (timed out if we failed here)
            delete = delete_resource(self.headers, resources.json()["items"][0]["id"])
            assert delete is not False  # (delete timed out if we fail here)
            time.sleep(2)
            tries += 1
            resources = requests.get(url, headers=self.headers, verify=False, timeout=300)
        assert tries <= 20
        # Verify there are no resource id's for the test target and port id before beginning tests
        msg, resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert resource_id is None
        assert msg is None

    def tearDown(self):
        _delete_token(self.token)

    @pytest.mark.skip(reason="keeps timing out due to broken test port")
    def test_operation_id_generation(self):
        """Integration test without a resource"""

        # Create a resource
        msg, self.resource_id = create_resource(
            self.headers, self.tid, self.target, self.vendor, self.timer, self.port_id, self.product_id
        )
        assert msg is None
        # (In real life, the portal call ends here, and a second call to the API is made)

        # This should find that new id in existing but it won't be active yet
        msg, new_resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert new_resource_id is None or new_resource_id == "still working"

        timeout = 0
        while (new_resource_id is None or new_resource_id == "still working") and timeout <= 5:
            timeout += 1
            time.sleep(2)
            msg, new_resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert new_resource_id == self.resource_id
        assert msg is None

        # Generate OP ID with new id
        msg, operation_id = generate_op_id(self.headers, self.resource_id, "true")
        assert msg is None
        assert operation_id

    @pytest.mark.skip(reason="keeps timing out due to broken test port")
    def test_create_resource(self):
        msg, self.resource_id = create_resource(
            self.headers, self.tid, self.target, self.vendor, self.timer, self.port_id, self.product_id
        )
        assert msg is None
        assert self.resource_id

    @pytest.mark.skip(reason="keeps timing out due to broken test port")
    def test_generate_status_operation_id(self):
        # Create a resource
        msg, self.resource_id = create_resource(
            self.headers, self.tid, self.target, self.vendor, self.timer, self.port_id, self.product_id
        )
        assert msg is None

        # This should find that new id in existing but it won't be active yet
        msg, new_resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert msg is None
        timeout = 0
        while (new_resource_id is None or new_resource_id == "still working") and timeout <= 5:
            timeout += 1
            time.sleep(2)
            msg, new_resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert new_resource_id == self.resource_id
        assert msg is None

        # Generate OP ID with new id
        msg, operation_id = generate_status_op_id(self.headers, self.resource_id)
        assert msg is None
        assert operation_id

    @pytest.mark.skip(reason="keeps timing out due to broken test port")
    def test_find_existing_resource(self):
        msg, data = get_existing_resource(self.headers, self.target, self.port_id)
        assert msg is None
        assert data is None

    @pytest.mark.skip(reason="keeps timing out due to broken test port")
    def test_status_call(self):
        # generate op id and resource id
        msg, self.resource_id = create_resource(
            self.headers, self.tid, self.target, self.vendor, self.timer, self.port_id, self.product_id
        )
        assert msg is None

        # This should find that new id in existing but it won't be active yet
        msg, new_resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert msg is None
        timeout = 0
        while (new_resource_id is None or new_resource_id == "still working") and timeout <= 5:
            timeout += 1
            time.sleep(2)
            msg, new_resource_id = get_existing_resource(self.headers, self.target, self.port_id)
        assert new_resource_id == self.resource_id
        assert msg is None

        msg, operation_id = generate_status_op_id(self.headers, self.resource_id)
        assert msg is None
        assert operation_id

        # call status
        msg, data = status_call(self.headers, self.resource_id, operation_id)
        assert msg is None
        assert data
