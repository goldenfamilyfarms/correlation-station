import json
import logging
import unittest

import pytest
from _pytest.monkeypatch import MonkeyPatch
from werkzeug import exceptions

# from palantir_app.dll import granite
from palantir_app.dll import denodo

logger = logging.getLogger(__name__)


class MockResponse:
    def __init__(self, data_set, status_code=200):
        self.status_code = status_code
        self.content = data_set

    def json(self):
        return self.content


"""Unit tests for methods in dll/denodo.py"""


class TestGetPathIdByCid(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        self.headers_info = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        self.no_cid = None
        self.cid = "94.L1XX.025950..TWCC"
        self.monkeypatch = MonkeyPatch()

    @pytest.mark.unittest
    def test_denodo_get_with_conn_error(self):
        """
        Tests denodo_get with a connection
        error thrown
        """

        def mocked_requests_get(*args, **kwargs):
            raise ConnectionError

        self.monkeypatch.setattr(denodo.requests, "get", mocked_requests_get)
        logger.debug("UNIT TEST: test_denodo_get_with_conn_error")
        try:
            endpoint = f"/server/app_int/dv_mdso_model_v20200605_1/views/dv_mdso_model_v20200605_1?cid={self.cid}"
            denodo.denodo_get(endpoint)
        except exceptions.HTTPException as e:
            logger.debug("= response status code =")
            logger.debug(f"{e.code} - {e.data['message']}")
            assert e.code == 500

    @pytest.mark.unittest
    def test_denodo_get_with_404_status_code(self):
        """
        Tests denodo_get_for_circuit_devices with 404 status code which causes
        abort 502 on line 102 of denodo.py
        """

        def mocked_requests_get(*args, **kwargs):
            return MockResponse(None, 404)

        self.monkeypatch.setattr(denodo.requests, "get", mocked_requests_get)
        logger.debug("UNIT TEST: test_denodo_get_with_404_status_code")
        try:
            endpoint = f"/server/app_int/dv_mdso_model_v20200605_1/views/dv_mdso_model_v20200605_1?cid={self.cid}"
            denodo.denodo_get(endpoint)
        except exceptions.HTTPException as e:
            logger.debug("= response status code =")
            logger.debug(f"{e.code} - {e.data['message']}")
            assert e.code == 500

    @pytest.mark.unittest
    def test_denodo_get_with_504_status_code(self):
        """
        Tests denodo_get_for_circuit_devices with 503 status code which causes
        abort 504 on line 17 of denodo.py
        """

        def mocked_requests_get(*args, **kwargs):
            return MockResponse(None, 502)

        self.monkeypatch.setattr(denodo.requests, "get", mocked_requests_get)
        logger.debug("UNIT TEST: test_denodo_get_with_502_status_code")
        try:
            endpoint = f"/server/app_int/dv_mdso_model_v20200605_1/views/dv_mdso_model_v20200605_1?cid={self.cid}"
            denodo.denodo_get(endpoint)
        except exceptions.HTTPException as e:
            logger.debug("= response status code =")
            logger.debug(f"{e.code} - {e.data['message']}")
            assert e.code == 500

    @pytest.mark.unittest
    def test_denodo_get_with_none_denodo_elements(self):
        """
        executes denodo_get with no result and ends in
        abort statement in line 109 of denodo.py
        """

        def mocked_requests_get(*args, **kwargs):
            data = []
            return MockResponse(data, 200)

        self.monkeypatch.setattr(denodo.requests, "get", mocked_requests_get)
        logger.debug("UNIT TEST: test_denodo_get_with_none_denodo_elements")
        try:
            endpoint = f"/server/app_int/dv_mdso_model_v20200605_1/views/dv_mdso_model_v20200605_1?cid={self.cid}"
            r = denodo.denodo_get(endpoint)
            logger.debug(r)
            assert r == []
        except exceptions.HTTPException as e:
            logger.debug("= response status code =")
            logger.debug(f"{e.code} - {e.data['message']}")
            assert e.code == 200

    @pytest.mark.unittest
    def test_denodo_get_with_success(self):
        """
        Calls denodo_get with successful execution
        """

        def mocked_requests_get(*args, **kwargs):
            with open("tests/samples/test_call_denodo_for_circuit_devices_successful.json", "r") as f:
                data = f.read()
                data = json.loads(data)
            return MockResponse(data)

        self.monkeypatch.setattr(denodo.requests, "get", mocked_requests_get)
        logger.debug("UNIT TEST: test_denodo_get_with_success")
        try:
            endpoint = f"/server/app_int/dv_mdso_model_v20200605_1/views/dv_mdso_model_v20200605_1?cid={self.cid}"
            r = denodo.denodo_get(endpoint)
            logger.debug("successful call to denodo")
            assert r["elements"][0]["cid"] == self.cid
        except exceptions.HTTPException as e:
            logger.debug("= response status code =")
            logger.debug(f"{e.code} - {e.data['message']}")
            assert e.code == 500
