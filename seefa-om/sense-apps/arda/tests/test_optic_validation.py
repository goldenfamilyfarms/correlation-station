import pytest

from arda_app.bll import optic_check
from tests.data import optic_validation_data


@pytest.mark.unittest
def test_match_no_decimal_scenario_1():
    body = optic_validation_data.mock_payload_no_decimal_1()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "1"


@pytest.mark.unittest
def test_match_decimal_scenario_1_xe():
    body = optic_validation_data.mock_payload_xe_optic_1()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "1"


@pytest.mark.unittest
def test_scenario_2_with_decimal_cisco():
    body = optic_validation_data.mock_payload_with_decimal_2()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "2"


@pytest.mark.unittest
def test_scenario_3_ge():
    body = optic_validation_data.mock_payload_no_decimal_3()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "3"


@pytest.mark.unittest
def test_scenario_3_xe():
    body = optic_validation_data.mock_payload_xe_optic()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "3"


@pytest.mark.unittest
def test_scenario_4_with_decimal_cisco():
    body = optic_validation_data.mock_payload_with_decimal()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "4"


@pytest.mark.unittest
def test_scenario_4_with_decimal_prolabs():
    body = optic_validation_data.mock_payload_with_decimal()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "4"


@pytest.mark.unittest
def test_scenario_4_with_decimal_prolabssfpp():
    body = optic_validation_data.mock_payload_with_decimal()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "4"


@pytest.mark.unittest
def test_scenario_4_no_decimal():
    body = optic_validation_data.mock_payload_no_decimal_4()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "4"


@pytest.mark.unittest
def test_scenario_5():
    body = optic_validation_data.mock_payload_unacceptable_change()
    response = optic_check.scenario_check(body["opticwave"], True)

    assert response["scenario"] == "5"


@pytest.mark.unittest
def test_scenario_6():
    body = optic_validation_data.mock_payload_unacceptable_change()
    response = optic_check.scenario_check(body["opticwave"], False)

    assert response["scenario"] == "6"


@pytest.mark.unittest
def test_scenario_7():
    body = optic_validation_data.mock_payload_unacceptable_change()
    body["opticwave"]["wavelength_change"] = False
    response = optic_check.scenario_check(body["opticwave"], False)

    assert response["scenario"] == "7"


@pytest.mark.unittest
def test_scenario_8():
    body = optic_validation_data.mock_payload_unacceptable_change()
    body["opticwave"]["construction_complete"] = False
    response = optic_check.scenario_check(body["opticwave"], False)

    assert response["scenario"] == "8"


@pytest.mark.unittest
def test_get_port_connection_info(monkeypatch):
    granite_resp = [{"FQDN": "SWNSILBL0QW.CHTRSE.COM", "VENDOR": "JUNIPER"}]
    monkeypatch.setattr(optic_check, "get_granite", lambda *args, **kwargs: granite_resp)
    assert optic_check.get_port_connection_info("61.L1XX.007137..CHTR", "SWNSILBL0QW/001.0001.004.24/SWT#1", "2") == (
        "SWNSILBL0QW",
        "JUNIPER",
    )

    monkeypatch.setattr(optic_check, "get_granite", lambda *args, **kwargs: [{}])

    with pytest.raises(Exception) as e:
        assert (
            optic_check.get_port_connection_info("61.L1XX.007137..CHTR", "SWNSILBL0QW/001.0001.004.24/SWT#1", "2")
            is None
        )
        assert e.value.code == 502
        assert e.value == ("Could not get the following keys for circuit id 61.L1XX.007137..CHTR: ['FQDN', 'VENDOR']")

    monkeypatch.setattr(optic_check, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(Exception) as e:
        assert (
            optic_check.get_port_connection_info("61.L1XX.007137..CHTR", "SWNSILBL0QW/001.0001.004.24/SWT#1", "2")
            is None
        )
        assert e.value.code == 404
        assert e.value == (
            "No ports found on Path Elements call to Granite for circuit id: "
            "61.L1XX.007137..CHTR and pe_device: SWNSILBL0QW/001.0001.004.24/SWT#1"
        )


@pytest.mark.unittest
def test_get_port_from_mdso_juniper(monkeypatch):
    mdso_res = {"result": {"fpc-information": {"fpc": {"pic-detail": {"port-information": {"port": "test"}}}}}}
    monkeypatch.setattr(optic_check, "onboard_and_exe_cmd", lambda *args, **kwargs: mdso_res)
    assert optic_check.get_port_from_mdso_juniper("KLLNTXCR0QW", "GE-0/0/70") == "test"

    ports_info = {
        "scenario": 4,
        "optic_slotted": False,
        "optic_validation_notes": "It was unable to be determined if the optic has been slotted or not for "
        "KLLNTXCR0QW/000.0000.000.00/SWT#0/GE-0/0/70, please investigate and update the EPR per "
        "process\n\n"
        "port_activation_link: https://light-test.seek.chtrse.com/light_test/KLLNTXCR0QW/3851971/GE-0/0/70",
        "optic_check": "fail",
    }
    monkeypatch.setattr(optic_check, "onboard_and_exe_cmd", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert optic_check.get_port_from_mdso_juniper("KLLNTXCR0QW", "GE-0/0/70") == ports_info


@pytest.mark.unittest
def test_format_wavelength():
    port = {
        "cable-type": "LC",
        "fiber-mode": "fiber-mode",
        "sfp-vendor-name": "PROLABS",
        "sfp-vendor-pno": "SFPPROLABS1490",
    }

    mdso_port_info = f"""Cable Type: {port["cable-type"]}
    Fiber Type: {port["fiber-mode"]}
    Vendor: {port["sfp-vendor-name"]}
    Model: {port["sfp-vendor-pno"]}
    Wavelength: 1490.23"""

    assert optic_check.format_wavelength(port, "1490.23") == mdso_port_info

    mdso_port_info = f"""Cable Type: {port["cable-type"]}
    Fiber Type: {port["fiber-mode"]}
    Vendor: {port["sfp-vendor-name"]}
    Model: {port["sfp-vendor-pno"]}
    Wavelength: 1490 nm"""

    assert optic_check.format_wavelength(port, "1490") == mdso_port_info
