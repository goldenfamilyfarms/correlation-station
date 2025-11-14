"""Test logging"""

import logging

import pytest
from testfixtures import LogCapture

from palantir_app.common.errors import InvalidUsage
from palantir_app.common.logging_setup import format_api_call, format_connection_error
from palantir_app.common.validators import port_check


@pytest.fixture
def function_logs():
    """Capture log output from a function to pass to test"""
    with LogCapture(level=logging.DEBUG) as logs:
        with pytest.raises(InvalidUsage):
            port_check("4095")
    return logs


def test_logging_works(function_logs):
    """Use LogCapture's 'check' function to validate log output from a function"""
    # TODO test logging configuration

    function_logs.check(("palantir_app.common.errors", "ERROR", "Connection to endpoint failed - 400: Incorrect port"))


def test_format_api_call():
    """String is formatted correctly for api call log messages"""
    assert format_api_call("endpoint", "get", "test message") == "GET to endpoint - test message"


def test_format_connection_error():
    """String is formatted correctly for connection error messages"""
    assert format_connection_error("endpoint", "error", 500) == "Connection to endpoint failed - 500: error"
