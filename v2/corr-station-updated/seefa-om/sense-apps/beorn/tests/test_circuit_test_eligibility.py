import json
import pytest

from beorn_app.bll.eligibility import circuit_test_eligibility
from beorn_app.bll.snmp import isolate_firmware, compare_version
from beorn_app.common.generic import FIA, ELINE, ADVA, RAD

"""
circuit_id: Any,
cpe_ip_address: bool = False,
allow_ctbh: bool = False,
cap_eline_bandwidth: bool = True,
check_ssh: str = "",
username: str = "",
fastpath_only: bool = False,
cpe_planned_ineligible: bool
"""


@pytest.mark.unittest
@pytest.mark.parametrize(
    "service_type, vendor, model, firmware_response, eligible_tests",
    [
        (FIA, ADVA, "GE114", "10.1.1", []),
        (FIA, ADVA, "GE114", "11.1.2", []),
        (FIA, ADVA, "GE114", "11.1.2-123", [circuit_test_eligibility.L3LB]),
        (FIA, ADVA, "GE114", "11.1.3", [circuit_test_eligibility.L3LB]),
        (FIA, ADVA, "GE114", "99.99.99", [circuit_test_eligibility.L3LB]),
        (FIA, ADVA, "FSP150GE114PROC", "11.6.0-99", []),
        (FIA, ADVA, "FSP150GE114PROC", "11.6.1", [circuit_test_eligibility.L3LB]),
        (FIA, ADVA, "FSP150GE114PROC", "99.99.99-999", [circuit_test_eligibility.L3LB]),
        (FIA, ADVA, "FSP150XG116PRO", "11.6.0", []),
        (FIA, ADVA, "FSP150XG116PRO", "11.6.1", [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR]),
        (FIA, ADVA, "FSP150XG116PRO", "13.1.1-223", [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR]),
        (
            FIA,
            ADVA,
            "FSP150XG116PRO",
            "13.7.1",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLG, circuit_test_eligibility.MFLR],
        ),
        (
            FIA,
            ADVA,
            "FSP150XG116PRO",
            "99.99.99-999",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLG, circuit_test_eligibility.MFLR],
        ),
        (FIA, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.3.0", []),
        (FIA, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.3.0(0.52)", []),
        (FIA, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.3.0(0.101)", []),
        (FIA, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.4.0", []),
        (FIA, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.86)", [circuit_test_eligibility.L3LB]),
        (
            FIA,
            RAD,
            "EXT220A",
            "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.91)",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR],
        ),
        (
            FIA,
            RAD,
            "EXT220A",
            "ETX-220A Hw: 0.0/E, Sw: 99.0.99",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR],
        ),
        (FIA, RAD, "ETX203AX2SFP2UTP2SFP", "ETX-203AX Hw: 2.0/F, Sw: 1.99.0(0.86)", []),
        (FIA, RAD, "ETX203AX/2SFP/2UTP2SFP", "ETX-203AX/N Hw: 2.2/F, Sw: 6.7.1(0.159)", [circuit_test_eligibility.L3LB]),
        (FIA, RAD, "ETX203AX2SFP2UTP2SFP", "ETX-203AX Hw: 2.0/F, Sw: 6.4.0(0.86)", [circuit_test_eligibility.L3LB]),
        (FIA, RAD, "ETX203AX2SFP2UTP2SFP", "ETX-203AX Hw: 2.0/F, Sw: 100.4.0(0.86)", [circuit_test_eligibility.L3LB]),
        (
            FIA,
            RAD,
            "EXT220A",
            "ETX-220A-4XFP-10x1G Hw: 0.0/E, Sw: 6.7.1(0.159)",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR],
        ),
        (FIA, RAD, "2I", "ETX-2I-10G-LC Hw: 0.2/A, Sw: 5.7.0(0.87.9)", []),
        (FIA, RAD, "2I", "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.3.0(0.49)", []),
        (FIA, RAD, "2I", "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.86)", [circuit_test_eligibility.L3LB]),
        (FIA, RAD, "2I", "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.86.9)", [circuit_test_eligibility.L3LB]),
        (
            FIA,
            RAD,
            "2I",
            "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.91)",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR],
        ),
        (
            FIA,
            RAD,
            "2I",
            "ETX-2I-10G-LC Hw: 0.2/A, Sw: 99.99.0(0.49)",
            [circuit_test_eligibility.L3LB, circuit_test_eligibility.MFLR],
        ),
        (ELINE, ADVA, "GE114", "1.1.1", []),
        (ELINE, ADVA, "GE114", "7.1.4", [circuit_test_eligibility.L2LB]),
        (ELINE, ADVA, "GE114", "10.5.1-999", [circuit_test_eligibility.L2LB]),
        (ELINE, ADVA, "GE114", "10.5.2", [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB]),
        (ELINE, ADVA, "FSP150GE114PROC", "10.5.2-99", []),
        (ELINE, ADVA, "FSP150GE114PROC", "10.5.3", [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB]),
        (ELINE, ADVA, "FSP150GE114PROC", "11.6.1", [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB]),
        (
            ELINE,
            ADVA,
            "FSP150GE116PROC",
            "11.6.1",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB, circuit_test_eligibility.MFLR],
        ),
        (
            ELINE,
            ADVA,
            "FSP150GE116PROC",
            "13.5.2-99",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB, circuit_test_eligibility.MFLR],
        ),
        (
            ELINE,
            ADVA,
            "FSP150GE116PROC",
            "13.7.1",
            [
                circuit_test_eligibility.L2YG,
                circuit_test_eligibility.L2LB,
                circuit_test_eligibility.MFLG,
                circuit_test_eligibility.MFLR,
            ],
        ),
        (
            ELINE,
            ADVA,
            "FSP150XG116PRO",
            "13.1.1-223",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB, circuit_test_eligibility.MFLR],
        ),
        (
            ELINE,
            ADVA,
            "FSP150XG116PRO",
            "13.7.1",
            [
                circuit_test_eligibility.L2YG,
                circuit_test_eligibility.L2LB,
                circuit_test_eligibility.MFLG,
                circuit_test_eligibility.MFLR,
            ],
        ),
        (
            ELINE,
            ADVA,
            "FSP150XG116PRO",
            "13.7.1-999",
            [
                circuit_test_eligibility.L2YG,
                circuit_test_eligibility.L2LB,
                circuit_test_eligibility.MFLG,
                circuit_test_eligibility.MFLR,
            ],
        ),
        (ELINE, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.3.0", []),
        (ELINE, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.3.0(0.52)", []),
        (ELINE, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.4.0", []),
        (ELINE, RAD, "EXT220A", "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.52)", []),
        (
            ELINE,
            RAD,
            "EXT220A",
            "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.86)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB],
        ),
        (
            ELINE,
            RAD,
            "EXT220A",
            "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.91)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB, circuit_test_eligibility.MFLR],
        ),
        (ELINE, RAD, "ETX203AX2SFP2UTP2SFP", "ETX-203AX Hw: 2.0/F, Sw: 6.3.0(0.86)", []),
        (
            ELINE,
            RAD,
            "ETX203AX2SFP2UTP2SFP",
            "ETX-203AX Hw: 2.0/F, Sw: 6.4.0(0.86)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB],
        ),
        (
            ELINE,
            RAD,
            "ETX203AX2SFP2UTP2SFP",
            "ETX-203AX Hw: 2.0/F, Sw: 6.4.0(0.91)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB],
        ),
        (ELINE, RAD, "2I", "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.3.0(0.49)", []),
        (
            ELINE,
            RAD,
            "2I",
            "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.86)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB],
        ),
        (
            ELINE,
            RAD,
            "2I",
            "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.91)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB, circuit_test_eligibility.MFLR],
        ),
        (
            ELINE,
            RAD,
            "EXT220A",
            "ETX-220A-4XFP-10x1G Hw: 0.0/E, Sw: 6.7.1(0.159)",
            [circuit_test_eligibility.L2YG, circuit_test_eligibility.L2LB, circuit_test_eligibility.MFLR],
        ),
    ],
)
def test_firmware(service_type, vendor, model, firmware_response, eligible_tests):
    firmware = isolate_firmware(firmware_response, vendor)
    eligible = []
    model = circuit_test_eligibility.Eligibility("CID").normalize_model(model, vendor=vendor)
    test_eligibility = circuit_test_eligibility.SUPPORTED_VISIONWORKS_DEVICES[vendor][model][
        circuit_test_eligibility.FIRMWARE
    ][service_type]
    for test, test_min_version in test_eligibility.items():
        if compare_version(firmware=firmware, minimum=test_min_version) != "LESSER":
            eligible.append(test)
    assert eligible == eligible_tests


@pytest.mark.unittest
@pytest.mark.parametrize(
    "normalize, model, vendor",
    [
        ("GE114", "GE114", ""),
        ("GE114", "GE114", ADVA),
        ("GE114PRO", "GE114PRO", ""),
        ("GE114PRO", "GE114PRO", ADVA),
        ("GE114PRO", "FSP150GE114PROC", ""),  # These are treated the same by dice circuit testing as of 01/29/24
        ("GE114PRO", "FSP150GE114PROC", ADVA),  # ||
        ("XG108", "FSP150XG108", ""),
        ("XG108", "FSP150XG108", ADVA),
        ("XG116PRO", "FSP 150-XG116PRO", ""),
        ("XG116PRO", "FSP150CC-XG116PRO", ""),
        ("XG116PRO", "FSP150XG116PRO", ""),
        ("XG116PRO", "FSP150XG116PRO", ADVA),
        ("XG116PRO", "FSP150XG116PRO (H)", ""),  # These are treated the same by dice circuit testing as of 01/29/24
        ("XG116PRO", "FSP150XG116PRO (H)", ADVA),  # ||
        ("XG118PRO", "FSP150-XG118PRO (SH)", ""),
        ("XG118PRO", "FSP150-XG118PRO (SH)", ADVA),
        ("XO106", "FSP150XO106", ""),
        ("XO106", "FSP150XO106", ADVA),
        ("203", "ETX203AX2SFP2UTP2SFP", ""),
        ("203", "ETX203AX2SFP2UTP2SFP", RAD),
        ("203", "ETX-203AX/N Hw: 2.2/F, Sw: 6.7.1(0.159)", ""),
        ("203", "ETX-203AX/N Hw: 2.2/F, Sw: 6.7.1(0.159)", RAD),
        ("220", "ETX-220A-4XFP-10x1G Hw: 0.0/E, Sw: 6.7.1(0.159)", ""),
        ("220", "ETX-220A-4XFP-10x1G Hw: 0.0/E, Sw: 6.7.1(0.159)", RAD),
        ("220", "EXT220A", ""),
        ("220", "EXT220A", RAD),
        ("2I", "2I", ""),
        ("2I", "2I", RAD),
    ],
)
def test_normalize_model(normalize, model, vendor):
    assert normalize == circuit_test_eligibility.Eligibility("CID").normalize_model(model, vendor=vendor)


class DataResp:
    def __init__(self, status_code, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        with open(self.file_name) as f:
            data = json.loads(f.read())
        return data


def mock_get_granite_dia_825(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/dia_adva_825.json")
    return response.json()


@pytest.mark.unittest
def test_dia_ineligible_adva_825(monkeypatch):
    system_info = ("GLDLWIFM1ZW", "FSP150CC-825:3.3.3", "26505200", "OLDENBURGGROUP@1717WCIVICD")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_825)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_ip_from_tid", lambda *arg, **kwargs: "")
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "3.3.3")
    eligibility = circuit_test_eligibility.Eligibility("41.L1XX.000182..TWCC").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "Device Make 'ADVA' or Model 'FSP150CCF825' Not Supported",
            "service_type": "DIA",
        },
        200,
    )


def mock_get_granite_fia_no_cpe(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/fia_no_cpe.json")
    return response.json()


@pytest.mark.unittest
def test_fia_no_cpe_ineligible(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_fia_no_cpe)
    eligibility = circuit_test_eligibility.Eligibility("86.L1XX.005676..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "No device with role ['A', 'Z']",
            "service_type": "DIA",
        },
        200,
    )


def mock_get_granite_evpl(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/evpl.json")
    return response.json()


@pytest.mark.unittest
def test_evpl_ineligible(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_evpl)
    eligibility = circuit_test_eligibility.Eligibility("66.L1XX.002126..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "Service Type 'EVPL' Not Supported",
            "service_type": "EVPL",
        },
        200,
    )


def mock_get_granite_eaccessf(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/eaccessf.json")
    return response.json()


def mock_get_granite_ctbh(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/71.L4XX.000500..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_ctbh_ineligible(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_ctbh)
    eligibility = circuit_test_eligibility.Eligibility("71.L4XX.000500..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "Service Type 'CTBH 4G' Not Supported",
            "service_type": "CTBH 4G",
        },
        200,
    )


@pytest.mark.unittest
def test_ctbh_leg_one(monkeypatch):
    elements = mock_get_granite_ctbh().get("elements")
    system_info = ("RHNLWIGS71W", "FSP150CC-XG116PRO (H)", "1748893177", "1990 S BUNDY DR LOS ANGELES CA 90025")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "get_granite_data", lambda *arg, **kwargs: elements)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.7.2-210")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_pe_ctbh_wbox", lambda *arg, **kwargs: True)
    e = circuit_test_eligibility.Eligibility("71.L4XX.000500..CHTR", allow_ctbh=True)
    eligibility = e.check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [
                "Live Circuit",
                "Topology Element '0' Live used for eligibility.",
                "Topology Element '1' Live used for eligibility.",
            ],
            "failure_reason": "",
            "service_type": "CTBH 4G",
            "tests": ["L2 Y.1564 Generator", "L2 Loopback Function", "Multi-flow Generation", "Multi-flow Reflection"],
        },
        200,
    )


def mock_get_granite_ctbh_loopback_device(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/20.L4XX.000194..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_ctbh_loopback_device(monkeypatch):
    elements = mock_get_granite_ctbh_loopback_device().get("elements")
    system_info = ("RHNLWIGS71W", "FSP150CC-XG116PRO (H)", "1748893177", "1990 S BUNDY DR LOS ANGELES CA 90025")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "get_granite_data", lambda *arg, **kwargs: elements)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.7.2-210")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_pe_ctbh_wbox", lambda *arg, **kwargs: True)
    e = circuit_test_eligibility.Eligibility("71.L4XX.000500..CHTR", allow_ctbh=True)
    eligibility = e.check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [
                "Topology Element '0' Designed used for eligibility.",
                "Topology Element '1' Designed used for eligibility.",
            ],
            "failure_reason": "",
            "service_type": "CTBH 4G",
            "tests": ["L2 Y.1564 Generator", "L2 Loopback Function", "Multi-flow Generation", "Multi-flow Reflection"],
        },
        200,
    )


@pytest.mark.unittest
def test_ctbh_no_wbox(monkeypatch):
    elements = mock_get_granite_ctbh().get("elements")
    system_info = ("RHNLWIGS71W", "FSP150CC-XG116PRO (H)", "1748893177", "1990 S BUNDY DR LOS ANGELES CA 90025")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "get_granite_data", lambda *arg, **kwargs: elements)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.7.2-210")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_pe_ctbh_wbox", lambda *arg, **kwargs: False)
    e = circuit_test_eligibility.Eligibility("71.L4XX.000500..CHTR", allow_ctbh=True)
    eligibility = e.check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "No Whitebox Discovered",
            "service_type": "CTBH 4G",
        },
        200,
    )


def mock_get_granite_managed_wi(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/managedwi.json")
    return response.json()


@pytest.mark.unittest
def test_managed_wi_ineligible(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_managed_wi)
    eligibility = circuit_test_eligibility.Eligibility("90.L1XX.003339..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "Service Type 'MANAGED WI' Not Supported",
            "service_type": "MANAGED WI",
        },
        200,
    )


def mock_get_granite_mrs_intern(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/mrsintern.json")
    return response.json()


@pytest.mark.unittest
def test_mrs_intern_ineligible(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_mrs_intern)
    eligibility = circuit_test_eligibility.Eligibility("70.L1XX.011094..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [{"element_attempts": ["Service Type 'MRS INTERN' Not Supported"]}],
            "failure_reason": "Service Type 'MRS INTERN' Not Supported",
            "service_type": "MRS INTERN",
        },
        200,
    )


def mock_get_granite_dia_single_element(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/dia_single_element.json")
    return response.json()


@pytest.mark.unittest
def test_dia_ineligible_jumphost(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_single_element)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_acr", lambda *arg, **kwargs: True)
    eligibility = circuit_test_eligibility.Eligibility("31.L1XX.016236..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "Jumphost Detected on Circuit",
            "service_type": "DIA",
        },
        200,
    )


@pytest.mark.unittest
def test_dia_device_swap_no_override(monkeypatch):
    system_info = ("LSANCAPPBZW", "FSP 150-GE114Pro", "1748893177", "1990 S BUNDY DR LOS ANGELES CA 90025")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_single_element)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.5.2-99")
    eligibility = circuit_test_eligibility.Eligibility("31.L1XX.016236..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [
                "Mismatch in device vendor/model. TID 'LSANCAPPBZW'. IP '10.1.0.133'. Discovered 'ADVA'/'FSP150GE114PRO'. Expected 'ADVA'/'FSP150XG116PRO'"
            ],
            "failure_reason": "",
            "tests": ["L3 Loopback Function"],
            "service_type": "DIA",
        },
        200,
    )


@pytest.mark.unittest
def test_dia_device_swap_cpe_override(monkeypatch):
    system_info = ("LSANCAPPBZW", "FSP 150-GE114Pro", "1748893177", "1990 S BUNDY DR LOS ANGELES CA 90025")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_single_element)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.5.2-99")
    eligibility = circuit_test_eligibility.Eligibility("31.L1XX.016236..CHTR", "1.1.1.1").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [
                "Discovered device 'LSANCAPPBZW' does not match design 'LSANCAPPLZW'.",
                "Mismatch in device vendor/model. TID 'LSANCAPPBZW'. IP '10.1.0.133'. Discovered 'ADVA'/'FSP150GE114PRO'. Expected 'ADVA'/'FSP150XG116PRO'",
            ],
            "failure_reason": "",
            "tests": ["L3 Loopback Function"],
            "service_type": "DIA",
        },
        200,
    )


def mock_get_granite_fia_multiple_elements(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/fia_multiple_elements.json")
    return response.json()


def mock_get_granite_eaccessf_no_wbox(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/eaccessf_no_wbox.json")
    return response.json()


def mock_granite_inventory_40_L1XX_008718__CHTR(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/granite_inventory/eaccessf_40.L1XX.008718..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_adva_108_no_management_ip(monkeypatch):  # TODO: Implement this test correctly
    system_info = ("DYBIFLXI1ZW", "FSP 150-XG108", "10448780", "1 INTEGRA BLVD DAYTONA BEACH FL 32117")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_no_device_id)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(
        circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.7.2-210"
    )  # TODO: Firmware version is from a 116Pro
    circuit_test_eligibility.get_ip_from_tid = lambda *arg, **kwargs: "10.72.9.205"  # TODO: IP address from 116Pro
    eligibility = circuit_test_eligibility.Eligibility("38.L4XX.000019..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [
                "Mismatch in device vendor/model. TID 'DYBIFLXI1ZW'. IP '10.72.9.205'. Discovered 'ADVA'/'FSP150XG108'. Expected 'ADVA'/'FSP150XG108'",
                "Override Management IP. TID 'DYBIFLXI1ZW'. IP '10.72.9.205'.",
            ],
            "failure_reason": "",
            "service_type": "DIA",
            "tests": ["L3 Loopback Function"],
        },
        200,
    )


@pytest.mark.unittest
def test_no_cpe_ineligible(monkeypatch):
    system_info = ("", "", "", "")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_single_element)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.5.2-99")
    eligibility = circuit_test_eligibility.Eligibility("31.L1XX.016236..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "No valid IP to SNMP for device 'LSANCAPPLZW.CML.CHTRSE.COM'",
            "service_type": "DIA",
        },
        502,
    )


def mock_get_granite_fia_secure_element(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/fia_secure_internet.json")
    return response.json()


# TODO: Make a secure internet test case
# @pytest.mark.unittest
# def test_fia_secure_element(monkeypatch):
#   pass


@pytest.mark.unittest
def test_element_status_testing(monkeypatch):
    system_info = ("AUSLTXABUZW", "FSP 150-GE114Pro", "1748893177", "11921 N MOPAC EXPY")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_fia_secure_element)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    # TODO: This firmware version was not verified.
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.5.2-99")
    eligibility = circuit_test_eligibility.Eligibility("51.L1XX.018785..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [],
            "failure_reason": "",
            "tests": ["L3 Loopback Function"],
            "service_type": "SECURE INT",
        },
        200,
    )


def mock_get_granite_fia_mss_dia(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/fia_mss_dia.json")
    return response.json()


@pytest.mark.unittest
def test_fia_mss_dia(monkeypatch):
    system_info = ("MONRNCET2ZW", "FSP150CC-XG116PRO", "1748893177", "3220 W HWY 74")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_fia_mss_dia)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    # TODO: This firmware version was not verified.
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.5.2-99")
    eligibility = circuit_test_eligibility.Eligibility("70.L1XX.002261..TWCC").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": ["Live Circuit"],
            "failure_reason": "",
            "tests": ["L3 Loopback Function", "Multi-flow Reflection"],
            "service_type": "MSS DIA",
        },
        200,
    )


def mock_get_granite_dia_no_device_id(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/dia_adva_108.json")
    return response.json()


def mock_get_granite_dia_juniper_reserved(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/dia_juniper_mx960_reserved.json")
    return response.json()


@pytest.mark.unittest
def test_pe_reserved_ineligible(monkeypatch):  # TODO: This test isnt implemented
    system_info = ("DYBIFLXI1ZW", "FSP 150-XG108", "10448780", "1 INTEGRA BLVD DAYTONA BEACH FL 32117")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_juniper_reserved)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(
        circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.7.2-210"
    )  # TODO: Firmware version is from a 116Pro
    monkeypatch.setattr(
        circuit_test_eligibility, "get_ip_from_tid", lambda *arg, **kwargs: "10.72.9.205"
    )  # TODO: IP address from 116Pro
    eligibility = circuit_test_eligibility.Eligibility("86.L1XX.005594..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "PE Reserved on Circuit",
            "service_type": "DIA",
        },
        200,
    )


def mock_get_granite_nid_enni(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/circuit_testing/e_access_f_nid_enni.json")
    return response.json()


@pytest.mark.unittest
def test_nid_enni(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_nid_enni)
    eligibility = circuit_test_eligibility.Eligibility("70.L1XX.011693..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "NID ENNI Detected",
            "service_type": "E-ACCESS F",
        },
        200,
    )


@pytest.mark.unittest
def test_eaccessf_ineligible_asidepe_unsupported(monkeypatch):
    with open("tests/mock_data/circuit_testing/eaccessf_ineligible_aside_pe.json") as file:
        topology = json.loads(file.read())
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", lambda *args, **kwargs: topology)
    eligibility = circuit_test_eligibility.Eligibility("70.L1XX.011693..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "Unsupported PE",
            "service_type": "E-ACCESS F",
        },
        200,
    )


@pytest.mark.unittest
def test_fastpath_only(monkeypatch):  # TODO: Implement this test correctly
    system_info = ("DYBIFLXI1ZW", "FSP 150-XG108", "10448780", "1 INTEGRA BLVD DAYTONA BEACH FL 32117")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_get_granite_dia_no_device_id)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(
        circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "13.7.2-210"
    )  # TODO: Firmware version is from a 116Pro
    circuit_test_eligibility.get_ip_from_tid = lambda *arg, **kwargs: ""
    eligibility = circuit_test_eligibility.Eligibility(
        "38.L4XX.000019..CHTR", fastpath_only=True
    ).check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "No valid IP to SNMP for device 'None'",  # TODO: Test with proper device id
            "service_type": "DIA",
        },
        502,
    )


def mock_ip_finder(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/95.L1XX.006470..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_no_ip_finder(monkeypatch):
    ip_finder = {
        "CPE_IP": "no ip found",
        "FAIL_REASON": "Unsupported Device in Role: ADVA as UPSTREAM DEVICE VENDOR. FSP 150-XG120PRO as UPSTREAM DEVICE MODEL. ",
        "failure_reason": "No valid IP to SNMP for device 'TMTNCA501ZW.CML.CHTRSE.COM'",
    }
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_ip_finder)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_ip_from_tid", lambda *arg, **kwargs: "")
    monkeypatch.setattr(circuit_test_eligibility, "ip_finder", lambda *arg, **kwargs: ip_finder)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: {})
    eligibility = circuit_test_eligibility.Eligibility("95.L1XX.006470..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "No valid IP to SNMP for device 'MSSOTXER1ZW.CML.CHTRSE.COM'",
            "service_type": "DIA",
        },
        502,
    )


@pytest.mark.unittest
def test_no_ip_finder_planned(monkeypatch):
    ip_finder = (
        {
            "CPE_IP": "no ip found",
            "FAIL_REASON": "Unsupported Device in Role: ADVA as UPSTREAM DEVICE VENDOR. FSP 150-XG120PRO as UPSTREAM DEVICE MODEL. ",
            "failure_reason": "No valid IP to SNMP for device 'TMTNCA501ZW.CML.CHTRSE.COM'",
        },
        500,
    )
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_ip_finder)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_ip_from_tid", lambda *arg, **kwargs: "")
    monkeypatch.setattr(circuit_test_eligibility, "ip_finder", lambda *arg, **kwargs: ip_finder)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: {})
    eligibility = circuit_test_eligibility.Eligibility(
        "95.L1XX.006470..CHTR", cpe_planned_ineligible=True
    ).check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": [],
            "failure_reason": "Element Status 'PLANNED' Not Supported",
            "service_type": "DIA",
        },
        200,
    )


def mock_mx_cpe(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/71.L1XX.017408..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_mx_cpe_ineligible(monkeypatch):
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_mx_cpe)
    eligibility = circuit_test_eligibility.Eligibility("71.L1XX.017408..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "MX CPE",
            "service_type": "E-ACCESS F",
        },
        200,
    )


def mock_ip_finder_replacement(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/80.L1XX.009524..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_dia_ip_finder_override(monkeypatch):
    ip_finder = ({"CPE_IP": "10.28.137.65"}, 200)
    system_info = ("SNLSCA541ZW", "ETX-2i-10G-B-8SFPP Hw: 0.4/A, Sw: 6.8.2(4.77)", "Junk", "More Junk")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_ip_finder_replacement)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_ip_from_tid", lambda *arg, **kwargs: "")
    monkeypatch.setattr(circuit_test_eligibility, "ip_finder", lambda *arg, **kwargs: ip_finder)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "6.8.2(4.77)")
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "palantir_ip_update", lambda *arg, **kwargs: True)
    eligibility = circuit_test_eligibility.Eligibility("80.L1XX.009524..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": True,
            "warning": [
                "Mismatch in device vendor/model. TID 'SNLSCA541ZW'. IP '10.28.137.65'. Discovered 'RAD'/'ETX2I10GB8SFPP'. Expected 'RAD'/'ETX2I10GB858SFPP'",
                "Override Management IP. TID 'SNLSCA541ZW'. IP '10.28.137.65'.",
            ],
            "failure_reason": "",
            "service_type": "DIA",
            "tests": ["L3 Loopback Function", "Multi-flow Reflection"],
        },
        200,
    )


def mock_vta_discovery(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/81.L1XX.017958..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_vta_discovery(monkeypatch):
    system_info = ("ARTPTXNL1ZW", "ETX-203AX/N Hw: 2.2/F, Sw: 6.7.1(0.159)", "Junk", "More Junk")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_vta_discovery)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "6.7.1(0.159)")
    eligibility = circuit_test_eligibility.Eligibility("81.L1XX.017958..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "No Whitebox Discovered",
            "service_type": "E-ACCESS F",
        },
        200,
    )


def mock_z_side_whitebox(*args, **kwargs) -> dict:
    response = DataResp(200, "tests/mock_data/hydra/dv_dice_topology_v5/33.L1XX.013431..CHTR.json")
    return response.json()


@pytest.mark.unittest
def test_z_side_whitebox_ineligible(monkeypatch):
    system_info = ("ARTPTXNL1ZW", "ETX-203AX/N Hw: 2.2/F, Sw: 6.7.1(0.159)", "Junk", "More Junk")
    monkeypatch.setattr(circuit_test_eligibility, "granite_get", mock_z_side_whitebox)
    monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_side_behind_jumphost", lambda *arg, **kwargs: False)
    monkeypatch.setattr(circuit_test_eligibility, "get_system_info", lambda *arg, **kwargs: system_info)
    monkeypatch.setattr(circuit_test_eligibility, "get_firmware", lambda *arg, **kwargs: "6.7.1(0.159)")
    eligibility = circuit_test_eligibility.Eligibility("33.L1XX.013431..CHTR").check_automation_eligibility()
    assert eligibility == (
        {
            "circuit_test_eligible": False,
            "warning": ["Live Circuit"],
            "failure_reason": "No Whitebox Discovered",
            "service_type": "E-ACCESS F",
        },
        200,
    )


@pytest.mark.unittest
def test_is_sidebehind_jumphost_false(monkeypatch):
    elements = mock_get_granite_eaccessf()["elements"]
    eligibility = circuit_test_eligibility.Eligibility("81.L1XX.017958..CHTR")
    eligibility._set_log_preamble("ELINE SEGMENT", "BW")
    for element in elements:
        monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_reachable_ssh", lambda *arg, **kwargs: True)
        assert eligibility.is_side_behind_jumphost(element.get("data", {})) is False


@pytest.mark.unittest
def test_is_sidebehind_jumphost_true_96dot_not_reachable(monkeypatch):
    elements = mock_get_granite_eaccessf()["elements"]
    eligibility = circuit_test_eligibility.Eligibility("81.L1XX.017958..CHTR")
    eligibility._set_log_preamble("ELINE SEGMENT", "BW")
    for element in elements:
        monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_96dot_pe", lambda *arg, **kwargs: True)
        monkeypatch.setattr(circuit_test_eligibility.Eligibility, "is_reachable_ssh", lambda *arg, **kwargs: False)
        assert eligibility.is_side_behind_jumphost(element.get("data", {})) is True
