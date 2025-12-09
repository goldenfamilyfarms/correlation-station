import pytest
from pytest import raises
from arda_app.bll.circuit_design.common import normalize_bandwidth_values


@pytest.mark.unittest
def test_normalize_bw_values_wrong_unit():
    """Tests normalize_bandwidth_values func"""
    """Returns 500 because unit character is not M or G """

    with raises(Exception) as excinfo:
        normalize_bandwidth_values("100", "L")

    assert 500 == excinfo.value.code


@pytest.mark.unittest
def test_normalize_bw_values_not_int():
    """Tests normalize_bandwidth_values func"""
    """Returns 500 because unit character is not M or G """

    with pytest.raises(Exception) as excinfo:
        normalize_bandwidth_values("1r0", "M")

    assert 500 == excinfo.value.code
