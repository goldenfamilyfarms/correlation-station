import logging

import pytest
from werkzeug import exceptions

from palantir_app.common import auth

logger = logging.getLogger(__name__)


class MockResponse:
    def __init__(self, data_set, status_code=200):
        self.status_code = status_code
        self.content = data_set

    def json(self):
        return self.content


"""Unit tests for methods in auth.py"""


@pytest.mark.skip
def test_create_token_with_success(monkeypatch):
    """Testing create_token with success"""

    def mocked_requests_post(*args, **kwargs):
        data = {"access_token": "eyJhb", "token_type": "bearer", "expires_in": 3600}
        logger.debug("= mocked_requests_post =")
        logger.debug(data)
        return MockResponse(data)

    monkeypatch.setattr(auth.requests, "post", mocked_requests_post)

    logger.debug("UNIT TEST: test_create_token_with_success")
    try:
        response = auth.create_token()
        logger.debug(f"response - {response}")
        assert response
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(e.code)


@pytest.mark.skip
def test_create_token_generates_400(monkeypatch):
    """Testing create_token returns a 400"""

    def mocked_requests_post(*args, **kwargs):
        data = {}
        logger.debug("= mocked_requests_post =")
        logger.debug(data)
        return MockResponse(data, 400)

    monkeypatch.setattr(auth.requests, "post", mocked_requests_post)

    logger.debug("UNIT TEST: test_create_token_generates_400")
    try:
        auth.create_token()
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(f"{e.code} - {e.description}")
        assert e.code == 400


@pytest.mark.skip
def test_create_token_encounters_connection_error(monkeypatch):
    """Testing create_token encounters a connection error"""

    def mocked_requests_post(*args, **kwargs):
        raise ConnectionError

    monkeypatch.setattr(auth.requests, "post", mocked_requests_post)

    logger.debug("UNIT TEST: test_create_token_encounters_connection_error")
    try:
        auth.create_token()
    except exceptions.HTTPException as e:
        logger.debug("= response status code =")
        logger.debug(f"{e.code} - {e.description}")
        assert e.code == 500
