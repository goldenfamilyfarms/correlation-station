import time
import pytest
import requests
from arda_app.bll.net_new import ip_swip
from arda_app.dll import arin
from arda_app.dll.arin import (
    format_arin_field,
    has_special_chars,
    remove_special_chars,
    create_arin_record,
    delete_arin_record,
    whois_check,
    whois_record,
)
from arda_app.bll.net_new.ip_swip import ip_swip_main
from common_sense.common.errors import AbortException
from mock_data.circuit_design.net_new.ip_swip.data import (
    arin_error_codes,
    mock_create_200,
    mock_create_error,
    mock_create_error_from_arin,
    mock_create_fail,
    mock_create_ticket,
    mock_whois_good,
    mock_whois_not_200,
    mock_whois_wrong_org,
    # mock_arin_whois_good,
    success_payload,
    success_payload_v2,
)

ipv4_lan = "72.128.143.88/29"
ipv4_lan_30 = "72.128.143.88/30"
ipv6_route = "64:ff9b:1::/48"
customer_info = {
    "customer_id": "HELENA AGRI ENTERPRISES, LLC some other logic that makes this over 50 char",
    "z_address": "8756 TEEL PKWY",
    "z_city": "FRISCO",
    "z_state": "TX",
    "z_zip": "75034",
}

customer_info_bad_info = {
    "customer_id": "HELENA AGRI ENTERPRISES, LLC some other logic that makes this over 50 char",
    "z_address": "8756 TEEL PKWY",
    "z_city": "(FRISCO)",
    "z_state": "TX",
    "z_zip": "75034",
}

handle = "NET-72-128-143-88-1"


@pytest.mark.unittest
def test_whois_record_correct_org(monkeypatch):
    monkeypatch.setattr(requests, "get", mock_whois_good)

    assert whois_record(ipv4_lan)[0] is None
    assert whois_record(ipv4_lan)[1] == "NET6-2001-1998-1"
    assert whois_record(ipv4_lan)[2]


@pytest.mark.unittest
def test_whois_check_200(monkeypatch):
    monkeypatch.setattr(requests, "get", mock_whois_good)

    assert whois_check(ipv4_lan)


@pytest.mark.unittest
def test_whois_record_wrong_org(monkeypatch):
    monkeypatch.setattr(requests, "get", mock_whois_wrong_org)

    assert whois_record(ipv4_lan)[0] == "C07585356"
    assert whois_record(ipv4_lan)[1] == "NET6-2001-1998-1"
    assert not whois_record(ipv4_lan)[2]


@pytest.mark.unittest
def test_whois_record_not_200(monkeypatch):
    monkeypatch.setattr(requests, "get", mock_whois_not_200)
    monkeypatch.setattr(arin, "sleep", lambda *args, **kwargs: None)

    try:
        whois_record(ipv4_lan)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.skip
@pytest.mark.unittest
def test_create_arin_record_customer_name_length(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_create_200)
    monkeypatch.setattr(requests, "put", mock_create_200)

    assert not create_arin_record(ipv4_lan, customer_info, handle)[0]
    assert create_arin_record(ipv4_lan, customer_info, handle)[1] is None


@pytest.mark.skip
@pytest.mark.unittest
def test_create_arin_record_char_length_ipv6(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_create_200)
    monkeypatch.setattr(requests, "put", mock_create_200)

    assert not create_arin_record(ipv6_route, customer_info, handle)[0]
    assert create_arin_record(ipv6_route, customer_info, handle)[1] is None


@pytest.mark.skip
@pytest.mark.unittest
def test_create_arin_record_customer_ticket(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_create_200)
    monkeypatch.setattr(requests, "put", mock_create_ticket)

    assert not create_arin_record(ipv4_lan, customer_info, handle)[0]
    assert create_arin_record(ipv4_lan, customer_info, handle)[1] == "1234"


@pytest.mark.skip
@pytest.mark.unittest
def test_create_arin_record_customer_error(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_create_200)
    monkeypatch.setattr(requests, "put", mock_create_error)

    assert create_arin_record(ipv4_lan, customer_info, handle)[0]
    assert create_arin_record(ipv4_lan, customer_info, handle)[1] is None


@pytest.mark.skip
@pytest.mark.unittest
def test_create_arin_record_arin_decode_error(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_create_200)
    monkeypatch.setattr(requests, "put", mock_create_error_from_arin)

    try:
        create_arin_record(ipv4_lan, customer_info, handle)
        assert False  # noqa: B011
    except AbortException as e:
        assert e.code == 500


@pytest.mark.skip
@pytest.mark.unittest
def test_create_arin_record_fail_create(monkeypatch):
    monkeypatch.setattr(requests, "post", mock_create_fail)

    assert create_arin_record(ipv4_lan, customer_info, handle)[0]
    assert create_arin_record(ipv4_lan, customer_info, handle)[1] is None


@pytest.mark.skip
@pytest.mark.unittest
def test_delete_arin_record_success(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"

    monkeypatch.setattr(requests, "delete", mock_create_200)

    assert delete_arin_record(customer_id, handle4)


@pytest.mark.skip
@pytest.mark.unittest
def test_ip_swip_main_delete_records(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"
    handle6 = "NET6-2001-0db8-1"
    whois_res = iter([(customer_id, handle4, False), (customer_id, handle6, False)])

    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "delete_arin_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(ip_swip, "delete_arin_record", lambda *args, **kwargs: True)
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: (customer_id, handle4, True))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: (customer_id, handle6, True))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    assert ip_swip_main(ipv4_lan, ipv6_route, customer_info)


@pytest.mark.unittest
def test_ip_swip_main_ticket(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"
    handle6 = "NET6-2001-0db8-1"
    whois_res = iter([(customer_id, handle4, True), (customer_id, handle6, True)])
    create_res = iter([(False, "1234", None), (False, None, None)])
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    assert ip_swip_main(ipv4_lan, ipv6_route, customer_info) == {
        "message": "IP SWIP operation completed",
        "IPs Assigned": "[{'ip': '72.128.143.88/29', 'ticket': '1234', 'status': 'pending'}, {'ip': '64:ff9b:1::/48', 'status': 'success'}]",
    }


@pytest.mark.unittest
def test_ip_swip_main_bad_cidr(monkeypatch):
    ipv4 = "72.128.143.88/32"
    ipv6 = "64:ff9b:1::/32"

    try:
        ip_swip_main(ipv4, ipv6, customer_info)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.skip
def test_ip_swip_main_no_whois_response(monkeypatch):
    # customer_id = 'C07585356'
    # handle4 = 'NET-72-128-143-88-1'
    # handle6 = "NET6-2001-0db8-1"

    monkeypatch.setattr(requests, "get", mock_whois_not_200)

    assert ip_swip_main(ipv4_lan, ipv6_route, customer_info)


@pytest.mark.unittest
def test_ip_swip_main_4_success(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"
    handle6 = "NET6-2001-0db8-1"

    whois_res = iter([(customer_id, handle4, True), (customer_id, handle6, True)])
    create_res = iter([(False, None, None), (True, None, arin_error_codes["E_SCHEMA_VALIDATION"])])

    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    assert ip_swip_main(ipv4_lan, ipv6_route, customer_info)


@pytest.mark.unittest
def test_ip_swip_main_6_success(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"
    handle6 = "NET6-2001-0db8-1"

    whois_res = iter([(customer_id, handle4, True), (customer_id, handle6, True)])
    create_res = iter([(True, None, arin_error_codes["E_SCHEMA_VALIDATION"]), (False, None, None)])

    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    assert ip_swip_main(ipv4_lan, ipv6_route, customer_info)


@pytest.mark.unittest
def test_ip_swip_main_both_success(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"
    handle6 = "NET6-2001-0db8-1"

    whois_res = iter([(customer_id, handle4, True), (customer_id, handle6, True)])
    create_res = iter([(False, None, None), (False, None, None)])

    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    assert ip_swip_main(ipv4_lan, ipv6_route, customer_info) == success_payload


@pytest.mark.unittest
def test_ip_swip_main_with_ipv4_30cidr(monkeypatch):
    customer_id = "C07585356"
    handle4 = "NET-72-128-143-88-1"
    handle6 = "NET6-2001-0db8-1"

    whois_res = iter([(customer_id, handle4, True), (customer_id, handle6, True)])
    create_res = iter([(False, None, None), (False, None, None)])

    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(ip_swip, "whois_record", lambda _: next(whois_res))
    monkeypatch.setattr(ip_swip, "create_arin_record", lambda *args, **kwargs: next(create_res))
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    assert ip_swip_main(ipv4_lan_30, ipv6_route, customer_info) == success_payload_v2


@pytest.mark.unittest
def test_special_char_functions():
    """Are we handling known special characters scenarios?"""
    # Predictably remove special characters, but not spaces or numbers
    assert remove_special_chars("Normal #^(#$^*&Enterprise 12") == "Normal Enterprise 12"
    assert remove_special_chars("Normal Enterprise 12") == "Normal Enterprise 12"

    # Transform special cases
    assert format_arin_field("Mom & Pop") == "Mom and Pop"
    # Added by Russell to add spaces if there are not already spaces
    assert format_arin_field("Proctor&Gamble") == "Proctor and Gamble"
    assert format_arin_field("Mom_Pop") == "Mom Pop"
    assert format_arin_field("Mom-Pop") == "Mom Pop"
    # Scenarios from Spec
    assert format_arin_field("H-E-B") == "H E B"
    assert format_arin_field("PLEASANT TOWNSHIP (HARDIN)") == "PLEASANT TOWNSHIP HARDIN"

    # The "double duty" the regex was doing previously
    assert has_special_chars("%@#$*&(")
    assert not has_special_chars("Normal Enterprise 12")

    # trim trailng space
    assert format_arin_field("Fri-") == "Fri"
    assert format_arin_field("Fri ") == "Fri"
