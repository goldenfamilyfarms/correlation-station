import json
import pytest

from palantir_app.common import compliance_utils
from palantir_app.common.constants import (
    CHANGE_ORDER_TYPE,
    DOCSIS_NEW_ORDER_TYPE,
    DOCSIS_CHANGE_ORDER_TYPE,
    FIBER_INTERNET_ACCESS,
)


class DataResp:
    def __init__(self, status_code, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        try:
            with open(self.file_name) as f:
                data = json.load(f)
        except TypeError:
            data = self.file_name
        return data


@pytest.mark.unittest
def test_translate_sf_order_type():
    sf_order = CHANGE_ORDER_TYPE
    product_name = FIBER_INTERNET_ACCESS
    order = compliance_utils.translate_sf_order_type(sf_order, product_name)
    assert order == CHANGE_ORDER_TYPE


@pytest.mark.unittest
def test_translate_sf_order_type_docsis_new():
    sf_order = "NEW INSTALL"
    product_name = "PRI Trunk (DOCSIS)"
    order = compliance_utils.translate_sf_order_type(sf_order, product_name)
    assert order == DOCSIS_NEW_ORDER_TYPE


@pytest.mark.unittest
def test_translate_sf_order_type_docsis_change():
    sf_order = "ADD"
    product_name = "PRI Trunk (DOCSIS)"
    order = compliance_utils.translate_sf_order_type(sf_order, product_name)
    assert order == DOCSIS_CHANGE_ORDER_TYPE


@pytest.mark.unittest
def test_check_multiple_cids():
    cid = "46.IPXN.000203.DAL.TWCC 46.IPXN.000203.DAL.TWCC.001"
    intended_result = "46.IPXN.000203.DAL.TWCC"
    result = compliance_utils.NetworkCompliance.check_multiple_cids(None, cid)

    assert result == intended_result


@pytest.mark.unittest
def test_check_multiple_cids_chc():
    cid = "54.L1XX.000386..TWCC /CHC00323242,CHC00271839"
    intended_result = "54.L1XX.000386..TWCC"
    result = compliance_utils.NetworkCompliance.check_multiple_cids(None, cid)

    assert result == intended_result


@pytest.mark.unittest
def test_check_multiple_cids_none():
    cid = "54.L1XX.000386..TWCC"
    intended_result = "54.L1XX.000386..TWCC"
    result = compliance_utils.NetworkCompliance.check_multiple_cids(None, cid)

    assert result == intended_result


@pytest.mark.unittest
def test_check_multiple_cids_chc_first():
    cid = "CHC00282636 50.L1XX.990316..CHTR"
    intended_result = "50.L1XX.990316..CHTR"
    result = compliance_utils.NetworkCompliance.check_multiple_cids(None, cid)

    assert result == intended_result


@pytest.mark.unittest
def test_check_multiple_cids_none_valid():
    cid = "CHC00323242 CHC00271839123"
    intended_result = "CHC00323242 CHC00271839123"
    result = compliance_utils.NetworkCompliance.check_multiple_cids(None, cid)

    assert result == intended_result
