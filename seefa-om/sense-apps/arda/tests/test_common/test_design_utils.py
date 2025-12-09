import pytest

import arda_app.common.cd_utils as du

""" Validate values """


@pytest.mark.unittest
def test_validate_values_list_none_in_none_expected():
    x = du.validate_values([], [])
    assert not x


@pytest.mark.unittest
def test_validate_values_list_none_in_one_expected():
    x = du.validate_values([], ["one"])
    assert x == ["one"]


@pytest.mark.unittest
def test_validate_values_dict_none_in_one_expected():
    x = du.validate_values({}, ["one"])
    assert x == ["one"]


@pytest.mark.unittest
def test_validate_values_dict_one_in_one_expected_none_value():
    x = du.validate_values({"one": None}, ["one"])
    assert x is None


@pytest.mark.unittest
def test_validate_values_dict_one_in_one_expected_with_value():
    x = du.validate_values({"one": "two"}, ["one"])
    assert x is None


@pytest.mark.unittest
def test_validate_values_dict_bad_one_in_one_expected():
    x = du.validate_values({"two": "two"}, ["one"])
    assert x == ["one"]


@pytest.mark.unittest
def test_validate_hub_clli_empty():
    v, t = du.validate_hub_clli("")
    assert v is False and "empty" in t


@pytest.mark.unittest
def test_validate_hub_clli_short():
    v, t = du.validate_hub_clli("small")
    assert v is False and "8 characters" in t


@pytest.mark.unittest
def test_validate_hub_clli_not_in_either_list():
    v, t = du.validate_hub_clli("8CHARCLI")
    assert v is True


@pytest.mark.unittest
def test_validate_hub_clli_stripped():
    v, t = du.validate_hub_clli("ELPWTX02_TWC/HU")
    assert v is True


@pytest.mark.unittest
def test_validate_hub_clli_in_map():
    v, t = du.validate_hub_clli("OPLSLA")
    assert v is True
