import pytest

from arda_app.common import utils as ut


@pytest.mark.unittest
def test_find_best_match():
    # opk == original
    options = [{"primary_key": "primary_key"}]

    with pytest.raises(Exception):
        assert ut.find_best_match(options, "primary_key", "primary_key") is None

    # 92 < distance > best_match[0]
    with pytest.raises(Exception):
        assert ut.find_best_match(options, "primary_key2", "primary_key") is None

    # no close match
    with pytest.raises(Exception):
        assert ut.find_best_match(options, "primary_key22", "primary_key") is None


@pytest.mark.unittest
def test_find_fuzzy_matches(monkeypatch):
    # best partial
    options = [{"clean_name": "clean name original"}, {"clean_name": "clean name original"}]
    assert ut.find_fuzzy_matches(options, "clean name original", "clean_name") == (
        [{"clean_name": "clean name original"}, {"clean_name": "clean name original"}],
        100,
        "best_partial",
    )

    # best set
    options = [{"clean_name": "cleans names originals"}]
    assert ut.find_fuzzy_matches(options, "clean name original", "clean_name") == (
        [{"clean_name": "cleans names originals"}],
        93,
        "best_set",
    )

    # maurice ratio
    options = [{"clean_name": "a maurice ratio"}]
    monkeypatch.setattr(ut, "words_alone", lambda *args: 3)
    assert ut.find_fuzzy_matches(options, "clean name original", "clean_name") == (
        [{"clean_name": "a maurice ratio"}],
        3,
        "maurice_ratio",
    )

    # None
    assert ut.find_fuzzy_matches([], "clean name original", "clean_name") == (None, 0, "CJ")


@pytest.mark.unittest
def test_find_similar_names():
    options = [{"clean_name": "clean_name"}]
    assert ut.find_similar_names(options, "clean_name")


@pytest.mark.unittest
def test_words_alone():
    assert ut.words_alone("original", "this is original")


@pytest.mark.unittest
def test_validate_required_parameters():
    # missing_site_data
    with pytest.raises(Exception):
        assert ut.validate_required_parameters(["required_parameters"], {"given_data": None}) is None


@pytest.mark.unittest
def test_get_bandwidth_in_mbps():
    # mbps
    assert ut.get_bandwidth_in_mbps("mbps", 10) == 10.0

    # gbps
    assert ut.get_bandwidth_in_mbps("gbps", 10) == 10000.0

    # bad bw_type
    with pytest.raises(Exception):
        assert ut.get_bandwidth_in_mbps("error", 10) is None


@pytest.mark.unittest
def test_convert_bandwidth():
    # bandwidth_in_mbps <= 1000 and not mtu and SC
    assert ut.convert_bandwidth("Gbps", 1, None, ct="SC") == ("1 Gbps", "GE", "GENERIC SFP LEVEL 1 SC")

    # bandwidth_in_mbps <= 1000 and not mtu and LC
    assert ut.convert_bandwidth("Gbps", 1, None, ct="LC") == ("1 Gbps", "GE", "GENERIC SFP LEVEL 1")

    # other
    assert ut.convert_bandwidth("Gbps", 10, None) == ("10 Gbps", "XE", "GENERIC SFP+ LEVEL 1")


@pytest.mark.unittest
def test_create_bw_string():
    # gbps
    assert ut.create_bw_string("gbps", 2) == "10 Gbps"
    assert ut.create_bw_string("gbps", 1) == "1 Gbps"

    # mbps
    assert ut.create_bw_string("mbps", 1001) == "10 Gbps"
    assert ut.create_bw_string("mbps", 1) == "1 Gbps"


@pytest.mark.unittest
def test_qpath_regex_match():
    # cid
    assert ut.path_regex_match("70.L1XX.005033..TWCC", "cid") == ["70.L1XX.005033..TWCC"]

    # path_name
    assert ut.path_regex_match("31001.GE40L.LSAICAEV1CW.LSAICAEV0QW", "path_name") == [
        "31001.GE40L.LSAICAEV1CW.LSAICAEV0QW"
    ]
