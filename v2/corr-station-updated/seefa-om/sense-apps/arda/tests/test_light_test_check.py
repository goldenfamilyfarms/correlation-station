import pytest
from requests import Response

import arda_app.bll.light_test_check as ltc
import arda_app.bll.optic_check as oc


@pytest.mark.unittest
def test_no_circuit_id(client):
    """Test design with a valid, defined cid"""
    url = "/arda/v1/light_test_check?wavelength=1&prism_id=1"
    resp = client.get(url)

    assert resp.status_code == 500
    assert "ARDA - Required query parameter(s) not specified: circuit_id" in resp.json().get("message")


@pytest.mark.unittest
def test_no_prism_id(client):
    """Test design with a valid, defined cid"""
    url = "/arda/v1/light_test_check?wavelength=1&circuit_id=1"
    resp = client.get(url)
    assert resp.status_code == 500
    assert "ARDA - Required query parameter(s) not specified: prism_id" in resp.json().get("message")


@pytest.mark.unittest
def test_get_port_from_mdso_juniper(monkeypatch):
    ports_info = {
        "scenario": 6,
        "optic_slotted": False,
        "optic_validation_notes": "It was unable to be determined if the optic has been slotted or not for "
        "KLLNTXCR0QW/000.0000.000.00/SWT#0/GE-0/0/70, please investigate and update the EPR per "
        "process\n\n"
        "port_activation_link: https://light-test.seek.chtrse.com/light_test/KLLNTXCR0QW/3851971/GE-0/0/70",
        "optic_check": "fail",
    }
    monkeypatch.setattr(oc, "onboard_and_exe_cmd", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert (
            oc.get_port_from_mdso_juniper(
                "KLLNTXCR0QW",
                "GE-0/0/70",
                # "KLLNTXCR0QW/000.0000.000.00/SWT#0",  # pe_device
                # "3851971",  # prism_id
            )
            == ports_info
        )


@pytest.mark.unittest
def test_get_port_from_mdso_cisco():
    with pytest.raises(Exception):
        assert oc.get_port_from_mdso_cisco("KLLNTXCR0QW", "GE-0/0/70") is None


@pytest.mark.unittest
def test_check_optic():
    ports_info = [{"port-number": "70"}]
    assert oc.check_optic("GE-0/0/70", ports_info) == ports_info[0]

    ports_info = [{"port-number": "69"}]
    with pytest.raises(Exception):
        assert oc.check_optic("GE-0/0/70", ports_info, "light_test") is None


@pytest.mark.unittest
def test_set_interface_bw():
    assert oc.set_interface_bw("GIGE 1000LH") == 1000
    assert oc.set_interface_bw("10GBASE 10000LH") == 10000
    assert oc.set_interface_bw("GIGE 100LH") == 1000

    with pytest.raises(Exception):
        assert oc.set_interface_bw("NOTVALID 100LH") is None


@pytest.mark.unittest
def test_match_optic():
    assert oc.match_optic(1000, "< 80km SFP") is True
    assert oc.match_optic(10000, "< 80km SFP") is False
    assert oc.match_optic(10000, "< 80km SFP+") is True

    with pytest.raises(Exception):
        assert oc.match_optic(None, None) is None


@pytest.mark.unittest
def test_wavelength_check():
    remedy_fields = {"construction_complete": "yes", "actual_wavelength_used": "1490", "target_wavelength": "1490"}
    assert oc.wavelength_check(remedy_fields) == ("1490", True, True, False)

    remedy_fields["target_wavelength"] = "1570"
    assert oc.wavelength_check(remedy_fields) == ("1490", True, False, True)

    remedy_fields = {"construction_complete": "no", "actual_wavelength_used": "1490", "target_wavelength": "1490"}
    assert oc.wavelength_check(remedy_fields) == ("1490", True, True, False)

    remedy_fields["actual_wavelength_used"] = "1510"
    assert oc.wavelength_check(remedy_fields) == ("1510", True, True, True)

    remedy_fields["target_wavelength"] = "1570"
    assert oc.wavelength_check(remedy_fields) == ("1510", True, True, True)

    remedy_fields["actual_wavelength_used"] = None
    assert oc.wavelength_check(remedy_fields) == ("1570", True, True, False)

    remedy_fields["construction_complete"] = "nawl"

    with pytest.raises(Exception) as e:
        assert oc.wavelength_check(remedy_fields) is None
        assert e.value.code == 400
        assert e.value == (
            "construction_complete must be either 'yes' or 'no'; value entered: "
            f"{remedy_fields.get('construction_complete')}",
        )


@pytest.mark.unittest
def test_get_wavelengths():
    assert oc.get_wavelengths("1490 nm", "1490") == ("1490", "1490")
    assert oc.get_wavelengths("1470 nm", "1470nm") == ("1470", "1470")
    assert oc.get_wavelengths("1470", "1470nm") == ("", "1470")


@pytest.mark.unittest
def test_match_wavelength():
    port_matched = {"wavelength": "1510", "sfp-vendor-pno": "prolabs"}
    assert oc.match_wavelength("1510", port_matched) == (True, "1510")
    assert oc.match_wavelength("1530", port_matched) == (False, "1510")

    port_matched = {"wavelength": "1510.40", "sfp-vendor-pno": "prolabs"}
    assert oc.match_wavelength("1510.4", port_matched) == (True, "1510.40")

    with pytest.raises(Exception) as e:
        assert oc.match_wavelength(None, None) is None
        assert e.value.code == 502
        assert e.value == ("Error occured while trying to determine wavelength match")

    port_matched = {"wavelength": None, "sfp-vendor-pno": "prolabs"}

    with pytest.raises(Exception) as e:
        assert oc.match_wavelength("1510", port_matched) is None
        assert e.value == ("Error parsing wavelength from port info")

    port_matched = {"wavelength": "1563 nm", "sfp-vendor-pno": "SFPPDTCWnm1563.42"}
    assert oc.match_wavelength("1563.42 nm", port_matched) == (True, "1563.42")

    port_matched = {"wavelength": "1563 nm", "sfp-vendor-pno": "SFPPDTCWnm1563.40"}
    assert oc.match_wavelength("1563.4 nm", port_matched) == (True, "1563.40")

    port_matched = {"wavelength": "1555 nm", "sfp-vendor-pno": "SFPPDTCWnm1555.75"}
    assert oc.match_wavelength("1555.75 nm", port_matched) == (True, "1555")

    port_matched = {"wavelength": "1554 nm", "sfp-vendor-pno": "'SFPD5494-80-JA'"}
    assert oc.match_wavelength("1554.94 nm", port_matched) == (True, "1554.94")

    port_matched = {"wavelength": "1555 nm", "sfp-vendor-pno": "'SFPD5555-80-JA'"}
    assert oc.match_wavelength("1555.55 nm", port_matched) == (True, "1555")

    port_matched = {"wavelength": "1510", "sfp-vendor-pno": None}

    with pytest.raises(Exception) as e:
        assert oc.match_wavelength("1561.42", port_matched) is None
        assert e.value == ("Error parsing sfp-vendor-pno from port info")


@pytest.mark.unittest
def test_get_path_elements_data(monkeypatch):
    granite_resp = [
        {
            "PATH_NAME": "21001.snatxa012CW.snatxa012AW",
            "TID": "snatxa012CW",
            "PATH_STATUS": "Designed",
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        }
    ]
    monkeypatch.setattr(ltc, "get_granite", lambda *args, **kwargs: granite_resp)
    assert ltc.get_path_elements_data("25.L1XX.002747..CHTR") == {
        "PATH_NAME": "21001.snatxa012CW.snatxa012AW",
        "TID": "snatxa012CW",
        "PATH_STATUS": "Designed",
        "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
    }

    monkeypatch.setattr(ltc, "get_granite", lambda *args, **kwargs: [{"retString": "No records"}])

    with pytest.raises(Exception) as e:
        assert e.value == ("No records found in Granite for cid: 25.L1XX.002747..CHTR")


def mockresponse(status):
    response = Response()
    response.status_code = status
    return response


@pytest.mark.unittest
def test_check_port(monkeypatch):
    handle_resp = {
        "adminstate": "down",
        "operstate": "down",
        "transmitting_optical_power": "- InfdBm",
        "receiving_optical_power": "- InfdBm",
        "portSFPvendorPartNumber": "ZX-SFP-CWDM-1490",
        "portSFPwavelength": "1490 nm",
        "portSFPvendorName": "PROLABS",
        "status_info": "Successfully able to retrieve port state",
    }
    monkeypatch.setattr(ltc, "get_sense", lambda *args, **kwargs: mockresponse(200))
    monkeypatch.setattr(ltc, "_handle_sense_resp", lambda *args, **kwargs: handle_resp)
    assert ltc.check_port("SNATXA012CW", "GE-0/1/2") == handle_resp

    monkeypatch.setattr(ltc, "get_sense", lambda *args, **kwargs: mockresponse(404))

    with pytest.raises(Exception) as e:
        assert ltc.check_port("SNATXA012CW", "GE-0/1/2") is None
        assert e.value.code == 404

    monkeypatch.setattr(ltc, "get_sense", lambda *args, **kwargs: None)

    with pytest.raises(Exception) as e:
        assert ltc.check_port("SNATXA012CW", "GE-0/1/2") is None
        assert e.value.code == 404
        assert e.value == ("No records found in Palantir for the tid: SNATXA012CW")
