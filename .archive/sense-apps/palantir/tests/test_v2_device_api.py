import json
import logging

import pytest
from werkzeug import exceptions

logger = logging.getLogger(__name__)


class MockResponse:
    def __init__(self, data_set, status_code=200):
        self.status_code = status_code
        self.content = data_set

    def json(self):
        return self.content


@pytest.mark.unittest
def test_validate_endpoint_no_arguments(client):
    """
    Test and validate arguments
    """
    logger.debug("UNIT TEST: test_validate_endpoint_no_arguments")
    try:
        resp = client.get("/palantir/v2/device?")
        resp_data = json.loads(resp.data.decode("utf-8"))
        logger.debug("{} - {}".format(resp.status_code, resp_data["message"]))
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug("{} - {}".format(e.code, e.data["message"]))
    assert resp.status_code == 400


@pytest.mark.unittest
def test_validate_endpoint_mult_arguments(client):
    """
    Test and validate arguments
    """
    logger.debug("UNIT TEST: test_validate_endpoint_mult_arguments")
    try:
        resp = client.get("/palantir/v2/device?cid=27.L1XX.004893..CHTR&ip=10.16.10.220")
        resp_data = json.loads(resp.data.decode("utf-8"))
        logger.debug("{} - {}".format(resp.status_code, resp_data["message"]))
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug("{} - {}".format(e.code, e.data["message"]))
    assert resp.status_code == 500
