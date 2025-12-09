import logging

import pytest
from werkzeug import exceptions

from palantir_app.common import ise_operations

logger = logging.getLogger(__name__)


class MockResponse:
    def __init__(self, data_set, status_code=200):
        self.status_code = status_code
        self.content = data_set

    def json(self):
        return self.content


"""Unit tests for methods in ise_operations.py"""


@pytest.mark.unittest
def test_id_lookup_with_missing_parameter(monkeypatch):
    """Testing id_lookup with a missing paramter"""
    try:
        ids, results = ise_operations.id_lookup("94.L1XX.025950..TWCC")
        assert ids is None
        assert results is None
    except TypeError as e:
        logger.debug("= response =")
        logger.debug(e)
        assert e


@pytest.mark.unittest
def test_id_lookup_with_incorrect_parameter(monkeypatch):
    """Testing id_lookup with an incorrect paramter"""
    try:
        ids, results = ise_operations.id_lookup("cid", "94.L1XX.025950..TWCC")
        logger.debug(ids)
        logger.debug(results)
        assert ids is None
        assert results is None
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(e.code)
        assert e.code == 400


@pytest.mark.unittest
def test_id_lookup_with_connection_aborted_error(monkeypatch):
    """Testing id_lookup with a connection aborted error"""

    def mocked_requests_get(*args, **kwargs):
        raise ConnectionAbortedError

    monkeypatch.setattr(ise_operations.requests, "get", mocked_requests_get)
    logger.debug("UNIT TEST: test_id_lookup_with_connection_aborted_error")
    try:
        ise_operations.id_lookup("ipaddress", "10.20.107.32")
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(e.code)
        assert e.code == 500


@pytest.mark.unittest
def test_ise_calls_with_connection_aborted_error(monkeypatch):
    """Testing ise_calls with a connection aborted error"""

    def mocked_requests_get(*args, **kwargs):
        raise ConnectionAbortedError

    monkeypatch.setattr(ise_operations.requests, "get", mocked_requests_get)
    logger.debug("UNIT TEST: test_ise_calls_with_connection_aborted_error")
    try:
        ise_operations.ise_calls(
            "https://austx-ise-pan-s01.chtrse.com:9060", "/ers/config/networkdevice", "ipaddress", "10.27.155.43"
        )
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(e.code)
        assert e.code == 500


@pytest.mark.unittest
def test_ise_calls_with_successful_response(monkeypatch):
    """
    Test the ise_calls function with a successful connection and 200 code
    """

    def mocked_requests_get(*args, **kwargs):
        with open("tests/samples/test_ise_calls_successful_return.json", "r") as f:
            data = f.read()
        result = MockResponse(data_set=data, status_code=200)
        return result

    monkeypatch.setattr(ise_operations.requests, "get", mocked_requests_get)
    logger.debug("UNIT TEST: test_ise_calls_with_successful_response")
    try:
        ise_call = ise_operations.ise_calls(
            "https://austx-ise-pan-s01.chtrse.com:9060", "/ers/config/networkdevice", "ipaddress", "10.27.155.43"
        )
        assert ise_call
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(e.code)


@pytest.mark.unittest
def test_id_lookup_with_invalid_device_list(monkeypatch):
    """
    Testing id_lookup with invalid device list and causes an abort 400
    """

    def mocked_requests_get(*args, **kwargs):
        input = MockResponse("{}", 400)
        return input

    monkeypatch.setattr(ise_operations.requests, "get", mocked_requests_get)
    logger.debug("UNIT TEST: test_id_lookup_with_invalid_device_list")
    try:
        ise_operations.id_lookup("ipaddress", None)
    except Exception as e:
        logger.debug("= response status code =")
        logger.debug(e.code)
        assert e.code == 400


@pytest.mark.unittest
def test_id_lookup_ise_call_with_none_results(monkeypatch):
    """Testing id_lookup and ise_calls with none data but successfull execution"""

    def mocked_requests_get(*args, **kwargs):
        with open("tests/samples/test_id_lookup_ise_call_none_results.json", "r") as f:
            data = f.read()
        result = MockResponse(data_set=data, status_code=200)
        return result

    monkeypatch.setattr(ise_operations.requests, "get", mocked_requests_get)
    logger.debug("UNIT TEST: test_id_lookup_ise_call_with_none_results")
    try:
        ids, results = ise_operations.id_lookup("ipaddress", "94.L1XX.025950..TWCC")
        assert results["west_result"] == "none"
        assert results["east_result"] == "none"
        assert results["south_result"] == "none"
    except TypeError as e:
        logger.debug("= response =")
        logger.debug(e)
        assert e


@pytest.mark.unittest
def test_id_lookup_ise_call_with_with_results(monkeypatch):
    """Testing id_lookup and ise_calls with none data but successfull execution"""

    def mocked_requests_get(*args, **kwargs):
        with open("tests/samples/test_id_lookup_ise_call_with_results.json", "r") as f:
            data = f.read()
        result = MockResponse(data_set=data, status_code=200)
        return result

    monkeypatch.setattr(ise_operations.requests, "get", mocked_requests_get)
    logger.debug("UNIT TEST: test_id_lookup_ise_call_with_with_results")
    try:
        ids, results = ise_operations.id_lookup("ipaddress", "94.L1XX.025950..TWCC")
        assert results["west_result"]["id"] == 1234
        assert results["east_result"]["id"] == 1234
        assert results["south_result"]["id"] == 1234
    except TypeError as e:
        logger.debug("= response =")
        logger.debug(e)
        assert e
