import json
import logging

import pytest

from beorn_app import app

logger = logging.getLogger(__name__)


class MDSOResp:
    def __init__(self, status_code, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        with open(self.file_name) as f:
            data = json.load(f)
        return data


@pytest.fixture
def fake_sf_data():
    return "Some fake data"


@pytest.fixture
def client(request):
    app.config["TESTING"] = True
    client = app.test_client()
    return client
