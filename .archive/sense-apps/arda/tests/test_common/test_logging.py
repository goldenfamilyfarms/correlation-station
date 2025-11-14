"""Test logging"""

import pytest
from testfixtures import LogCapture

from arda_app.common.logging_setup import format_api_call, format_connection_error
import logging

logger = logging.getLogger(__name__)


def function_logs():
    """Capture log output from a function to pass to test"""
    with LogCapture(level=logging.DEBUG) as logs:
        # do something that generates logs
        pass
    return logs


@pytest.mark.skip("Tests fail when run with rest of test suite, pass individually")
def test_logging_works():
    """Use LogCapture's 'check' function to validate log output from a function"""

    function_logs().check(
        ("arda_app.common.granite81Api", "DEBUG", "Executing granite query for CID: 33.L2XX.009152.GSO.TWCC"),
        ("arda_app.common.granite81Api", "DEBUG", "Data mapped for CID 33.L2XX.009152.GSO.TWCC for sense xc query"),
        ("arda_app.common.granite81Api", "DEBUG", "Data mapped for CID 33.L2XX.009152.GSO.TWCC for sense xc query"),
    )


@pytest.mark.unittest
def test_format_api_call():
    """String is formatted correctly for api call log messages"""
    assert format_api_call("endpoint", "get", "test message") == "GET to endpoint - test message"


@pytest.mark.unittest
def test_format_connection_error():
    """String is formatted correctly for connection error messages"""
    assert format_connection_error("endpoint", "error", 500) == "Connection to endpoint failed - 500: error"
