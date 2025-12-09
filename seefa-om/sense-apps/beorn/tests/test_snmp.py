import pytest
from beorn_app.bll.snmp import _isolate_model, _get_vendor_by_model, isolate_firmware, normalize_firmware
from beorn_app.common.generic import ADVA, CIENA, CISCO, JUNIPER, RAD, SUMITOMO


@pytest.mark.unittest
@pytest.mark.parametrize(
    "model, snmp_response",
    [
        ("FSP150CC-825:3.3.3", "FSP150CC-825:3.3.3"),
        ("FSP 150-XG108", "FSP 150-XG108"),
        ("FSP150CC-GE114", "FSP150CC-GE114"),
        ("FSP 150-GE114Pro", "FSP 150-GE114Pro"),
        ("FSP150CC-XG116PRO", "FSP150CC-XG116PRO"),
        ("FSP150CC-XG116PRO (H)", "FSP150CC-XG116PRO (H)"),
        ("FSP150-XG118PRO (SH)", "FSP150-XG118PRO (SH)"),
        ("FSP150CC-XG120PRO", "FSP150CC-XG120PRO"),
        (
            "ASR920",
            "Cisco IOS Software, ASR920 Software (PPC_LINUX_IOSD-UNIVERSALK9_NPE-M), Version 15.6(2)SP1, RELEASE SOFTWARE (fc3)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2016 by Cisco Systems, Inc.\r\nCompiled Wed 23-Nov-16 16:25 by mcpre",
        ),
        (
            "EX4200-24F",
            "Juniper Networks, Inc. ex4200-24f Ethernet Switch, kernel JUNOS 12.3R12-S3.1, Build date: 2016-07-23 13:35:17 UTC Copyright (c) 1996-2016 Juniper Networks, Inc.",
        ),
        (
            "MX240",
            "Juniper Networks, Inc. mx240 internet router, kernel JUNOS 19.4X12.1, Build date: 2022-04-18 22:17:54 UTC Copyright (c) 1996-2022 Juniper Networks, Inc.",
        ),
        (
            "MX480",
            "Juniper Networks, Inc. mx480 internet router, kernel JUNOS 19.4X12.1, Build date: 2022-04-18 22:17:54 UTC Copyright (c) 1996-2022 Juniper Networks, Inc.",
        ),
        (
            "MX960",
            "Juniper Networks, Inc. mx960 internet router, kernel JUNOS 19.4R2-S3.2, Build date: 2020-11-12 20:58:06 UTC Copyright (c) 1996-2020 Juniper Networks, Inc.",
        ),
        ("5171 Packetwave Platform", "5171 Packetwave Platform"),
        (
            "FSU7100",
            "SUMITOMO ELECTRIC FSU7100, HWType=FSU7100, HWVersion=B0, FWVersion=R4.1.2.3.1.13500, SystemSerial=3681200050\u0000",
        ),  # Granite marked this model as FSU7101 EPON OLT
        ("ETX-203AX", "ETX-203AX Hw: 2.1/F, Sw: 6.4.0(0.94)"),
        ("ETX-203AX/N", "ETX-203AX/N Hw: 2.2/F, Sw: 6.7.1(0.159)"),
        ("ETX-2i-10G-B-8SFPP", "ETX-2i-10G-B-8SFPP Hw: 0.1/A, Sw: 6.8.0(0.34)"),
    ],
)
def test_isolate_model(model, snmp_response):
    isolated_model = _isolate_model(snmp_response)
    assert model == isolated_model


@pytest.mark.unittest
@pytest.mark.parametrize(
    "vendor, model",
    [
        (ADVA, "FSP150CC-825:3.3.3"),
        (ADVA, "FSP 150-XG108"),
        (ADVA, "FSP150CC-GE114"),
        (ADVA, "FSP 150-GE114Pro"),
        (ADVA, "FSP150CC-XG116PRO"),
        (ADVA, "FSP150CC-XG116PRO (H)"),
        (ADVA, "FSP150-XG118PRO (SH)"),
        (CIENA, "5171 Packetwave Platform"),
        (CISCO, "ASR920"),
        (JUNIPER, "MX240"),
        (JUNIPER, "MX480"),
        (RAD, "ETX-203AX"),
        (RAD, "ETX-203AX/N"),
        (RAD, "ETX-220A-4XFP-10x1G"),
        (RAD, "ETX-2i-10G-B-8SFPP"),
    ],
)
def test_get_vendor_by_model(vendor, model):
    mapped_vendor = _get_vendor_by_model(model)
    assert vendor == mapped_vendor


@pytest.mark.unittest
@pytest.mark.parametrize(
    "vendor, firmware_response, firmware",
    [
        (ADVA, "10.1.1", "10.1.1"),
        (ADVA, "11.1.2-123", "11.1.2-123"),
        (ADVA, "11.6.0-99", "11.6.0-99"),
        (ADVA, "11.6.1", "11.6.1"),
        (ADVA, "13.1.1-223", "13.1.1-223"),
        (ADVA, "13.7.1", "13.7.1"),
        (ADVA, "10.5.2-187", "10.5.2-187"),  # Taken from ADVA XG120PRO
        (RAD, "ETX-220A Hw: 0.0/E, Sw: 6.3.0(0.52)", "6.3.0(0.52)"),
        (RAD, "ETX-220A Hw: 0.0/E, Sw: 6.3.0(0.101)", "6.3.0(0.101)"),
        (RAD, "ETX-220A Hw: 0.0/E, Sw: 6.4.0", "6.4.0"),
        (RAD, "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.86)", "6.4.0(0.86)"),
        (RAD, "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.91)", "6.4.0(0.91)"),
        (RAD, "ETX-203AX Hw: 2.0/F, Sw: 6.4.0(0.86)", "6.4.0(0.86)"),
        (RAD, "ETX-2I-10G-LC Hw: 0.2/A, Sw: 5.7.0(0.87.9)", "5.7.0(0.87.9)"),
        (RAD, "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.86)", "6.4.0(0.86)"),
        (RAD, "ETX-2I-10G-LC Hw: 0.2/A, Sw: 6.4.0(0.86.9)", "6.4.0(0.86.9)"),
        (
            SUMITOMO,
            "SUMITOMO ELECTRIC FSU7100, HWType=FSU7100, HWVersion=B0, FWVersion=R4.1.2.3.1.13500, SystemSerial=3681200050\u0000",
            "R4.1.2.3.1.13500",
        ),  # Granite marked this model as FSU7101 EPON OLT
    ],
)
def test_firmware(vendor, firmware_response, firmware):
    found_firmware = isolate_firmware(firmware_response, vendor)
    assert firmware == found_firmware


@pytest.mark.unittest
@pytest.mark.parametrize(
    "firmware, normalized",
    [
        ("6.3.0", [6, 3, 0]),
        ("6.3.0(0.52)", [6, 3, 0, [0, 52]]),
        ("6.4.0(0.86)", [6, 4, 0, [0, 86]]),
        ("13.5.2", [13, 5, 2]),
        ("13.1.1-223", [13, 1, 1, [223]]),
        ("13.5.2-99", [13, 5, 2, [99]]),
        ("11.6.1+", [11, 6, 1]),  # Documentation only
        ("6.4.0 B86", [6, 4, 0, [0, 86]]),  # Documentation only
    ],
)
def test_normalize_firmware(firmware, normalized):
    assert normalized == normalize_firmware(firmware)
