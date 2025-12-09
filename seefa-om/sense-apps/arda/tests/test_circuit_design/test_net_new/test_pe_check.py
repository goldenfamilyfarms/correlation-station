import pytest

import arda_app.bll.net_new.pe_check as pe
from common_sense.common.errors import AbortException

""" MOCK DATA """

l1_good = [
    {"ELEMENT_NAME": "CEN_TEXAS_CLOUD (TEXAS.CEN.SPECTRUM.MPLS.000001)"},
    {"ELEMENT_NAME": "51001.GE40L.AUSDTXIR9CW.AUSDTXIR0QW"},
    {"ELEMENT_NAME": "51001.GE10.AUSDTXIR0QW.AUSXTXZR6ZW"},
]

l1_good_all_nones = [{"ELEMENT_NAME": None}, {"ELEMENT_NAME": None}, {"ELEMENT_NAME": None}]


@pytest.mark.unittest
def test_pe_check_main_success(monkeypatch):
    monkeypatch.setattr(pe, "get_granite", lambda _: l1_good)
    result = pe.pe_check_main("cid")
    expected = (
        [
            "CEN_TEXAS_CLOUD (TEXAS.CEN.SPECTRUM.MPLS.000001)",
            "51001.GE40L.AUSDTXIR9CW.AUSDTXIR0QW",
            "51001.GE10.AUSDTXIR0QW.AUSXTXZR6ZW",
        ],
        200,
    )
    assert result == expected


@pytest.mark.unittest
def test_pe_check_main_no_res(monkeypatch):
    monkeypatch.setattr(pe, "get_granite", lambda _: [])
    try:
        pe.pe_check_main("cid")
    except AbortException as e:
        assert e.code == 500 and "No data in response from Granite for Path" in e.data["message"]


@pytest.mark.unittest
def test_pe_check_main_res_but_all_nones(monkeypatch):
    monkeypatch.setattr(pe, "get_granite", lambda _: l1_good_all_nones)
    result = pe.pe_check_main("cid")
    assert result == ([], 200)
