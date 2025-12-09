import pytest

from arda_app.bll.cid.pathid import generate_cid_v3, get_pathid_v4

site = {"bw_unit": "Mbps", "bw_value": "100", "site_zip_code": "78758", "product_service": "COM-DIA"}


@pytest.mark.unittest
def _test_raises_abort(site, npa, error_code, error_message):
    with pytest.raises(Exception) as exception:
        generate_cid_v3(site, npa)
        assert exception.code == error_code
        assert exception.value == error_message

    error, message = get_pathid_v4(site, "CAR-CTBH 4G", "51")
    assert error == error_code
    assert f"Couldn't create a CID - {message}" == error_message


@pytest.mark.unittest
def test_generate_cid_fails_with_invalid_bw_unit():
    message = "Couldn't create a CID - BW Unit must be in the formats of - 'GBPS' or 'MBPS'"
    invalid_bw_site = site.copy()
    invalid_bw_site["bw_unit"] = ""
    _test_raises_abort(invalid_bw_site, "51", error_code=500, error_message=message)


@pytest.mark.unittest
def test_generate_cid_fails_with_invalid_unit_kbps():
    message = "Couldn't create a CID - BW Unit must be in the formats of - 'GBPS' or 'MBPS'"
    invalid_bw_site = site.copy()
    invalid_bw_site["bw_unit"] = "Kbps"
    _test_raises_abort(invalid_bw_site, "51", error_code=500, error_message=message)


@pytest.mark.unittest
def test_generate_cid_fails_with_invalid_zip():
    message = "Couldn't create a CID - Invalid value '1234' for query parameter zip_code. Expected length to be 5"
    invalid_zip_site = site.copy()
    invalid_zip_site["site_zip_code"] = "1234"
    _test_raises_abort(invalid_zip_site, "51", error_code=500, error_message=message)


@pytest.mark.unittest
def test_generate_cid_fails_with_negative_bw_value():
    message = "Couldn't create a CID - BW must be greater than 0Gbps or 0Mbps"
    invalid_bw_value_site = site.copy()
    invalid_bw_value_site["bw_value"] = "-1234"
    _test_raises_abort(invalid_bw_value_site, "51", error_code=500, error_message=message)


@pytest.mark.unittest
def test_generate_cid_fails_with_non_numeric_bw_value():
    message = "Couldn't create a CID - bw_val: asdfjkl should be in integer form"
    invalid_bw_value_site = site.copy()
    invalid_bw_value_site["bw_value"] = "asdfjkl"
    _test_raises_abort(invalid_bw_value_site, "51", error_code=500, error_message=message)


def _test_raises_abort_v3(site, service_type, npa_val, company, error_code, error_message):
    with pytest.raises(Exception) as exception:
        generate_cid_v3(site, npa_val, service_type, company)
        assert exception.code == error_code
        assert exception.value == error_message

    error, message = get_pathid_v4(site, service_type, npa_val, company)
    assert error == error_code
    assert message == error_message


@pytest.mark.unittest
def test_generate_cid_fails_with_invalid_service_type():
    message = "Service type of CIA not supported"
    invalid_site = site.copy()
    _test_raises_abort_v3(invalid_site, "CIA", "123", "CHTR", error_code=500, error_message=message)


@pytest.mark.unittest
def test_generate_cid_fails_with_wrong_company():
    message = "Invalid value 'CHR' for query parameter company. Expected min length 4"
    invalid_site = site.copy()
    invalid_site["company"] = "CHR"
    _test_raises_abort_v3(invalid_site, "FIA", "123", "CHR", error_code=500, error_message=message)


@pytest.mark.unittest
def test_generate_cid_v3_success():
    assert generate_cid_v3(site, "51", "CAR-EPL") == "51.L1XX.%..CHTR"

    site["product_service"] = "CUS-VOICE-SIP"
    site["bw_val"] = "20"
    assert generate_cid_v3(site, "51", "CAR-EPL") == "51.IPXN.%..CHTR"
