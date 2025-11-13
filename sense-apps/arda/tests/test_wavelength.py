import pytest

from arda_app.bll import light_test_check, optic_check
from arda_app.dll import sense
from tests.data import wavelength_data


@pytest.mark.unittest
def test_check_port(monkeypatch):
    body = wavelength_data.mock_tid()

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "adminstate": "up",
                "operstate": "down",
                "transmitting_optical_power": "1.61 dBm",
                "receiving_optical_power": "- Inf dBm",
                "portSFPvendorPartNumber": "SFP-6141-120-X",
                "portSFPwavelength": "1561 nm",
                "portSFPvendorName": "CISCO-PR6141-120",
                "status_info": "Successfully able to retrieve port state",
            }

    moxie = MockResponse()

    monkeypatch.setattr(light_test_check, "get_sense", lambda _, return_resp=True: moxie)
    monkeypatch.setattr(sense, "_handle_sense_resp", lambda *args, **kwargs: moxie.json)
    response = light_test_check.check_port(body["tid"], body["port_id"])
    assert response["portSFPvendorPartNumber"] == "SFP-6141-120-X"


"""
@pytest.mark.unittest
def test_check_port_fail(monkeypatch):
    body = wavelength_data.mock_tid()
    planatir_response = {
    }
    monkeypatch.setattr(light_test_check, 'get_sense', lambda _: planatir_response)
    response = light_test_check.check_port(body['tid'], body['port_id'])
    result = response['portSFPvendorPartNumber']
    assert response['portSFPvendorPartNumber'] == KeyError
"""


@pytest.mark.unittest
def test_wavelength_cwdm0():
    wavelength = "1310/1330"
    palantir_wavelength = "1310"
    match = optic_check.get_wavelengths(palantir_wavelength, wavelength)
    assert match


@pytest.mark.unittest
def test_wavelength_cwdm1():
    wavelength = "1310/1330"
    palantir_wavelength = "1330"
    match = optic_check.get_wavelengths(palantir_wavelength, wavelength)
    assert match


@pytest.mark.unittest
def test_wavelength_cwdm2():
    wavelength = "1370/1450"
    palantir_wavelength = "1371"
    match = optic_check.get_wavelengths(palantir_wavelength, wavelength)
    assert match


@pytest.mark.unittest
def test_wavelength_cwdm3():
    wavelength = "1370/1450"
    palantir_wavelength = "1449"
    match = optic_check.get_wavelengths(palantir_wavelength, wavelength)
    assert match


@pytest.mark.unittest
def test_wavelength_dwdm():
    wavelength = "1533.47"
    palantir_wavelength = "1533"
    match = optic_check.get_wavelengths(palantir_wavelength, wavelength)
    assert match
