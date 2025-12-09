import pytest

from common.network_devices import ADVA, CISCO, JUNIPER, RAD, SUMITOMO
from dll.device_snmp import DeviceSNMP


@pytest.mark.unittest
@pytest.mark.parametrize(
    "sysDescr, description",
    [
        ("FSP150CC-825:3.3.3", {"vendor": ADVA, "model": "FSP150CC-825:3.3.3"}),
        ("FSP 150-XG108", {"vendor": ADVA, "model": "FSP 150-XG108"}),
        ("FSP150CC-GE114", {"vendor": ADVA, "model": "FSP150CC-GE114"}),
        ("FSP 150-GE114Pro", {"vendor": ADVA, "model": "FSP 150-GE114Pro"}),
        ("FSP150CC-XG116PRO", {"vendor": ADVA, "model": "FSP150CC-XG116PRO"}),
        ("FSP150CC-XG116PRO (H)", {"vendor": ADVA, "model": "FSP150CC-XG116PRO (H)"}),
        ("FSP150-XG118PRO (SH)", {"vendor": ADVA, "model": "FSP150-XG118PRO (SH)"}),
        ("FSP150CC-XG120PRO", {"vendor": ADVA, "model": "FSP150CC-XG120PRO"}),
        (
            (
                "Cisco IOS Software, ASR920 Software (PPC_LINUX_IOSD-UNIVERSALK9_NPE-M), Version 15.6(2)SP1, RELEASE"
                " SOFTWARE (fc3)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2016 by"
                " Cisco Systems, Inc.\r\nCompiled Wed 23-Nov-16 16:25 by mcpre"
            ),
            {"vendor": CISCO, "model": "ASR920", "software_version": "15.6(2)SP1"},
        ),
        (
            (
                "Cisco IOS XR Software (Cisco ASR9K Series),  Version 6.4.2[Default]\r\nCopyright (c) 2021 by Cisco"
                " Systems, Inc."
            ),
            {"vendor": CISCO, "model": "ASR9K Series", "software_version": "6.4.2"},
        ),
        (
            (
                "Juniper Networks, Inc. ex4200-24f Ethernet Switch, kernel JUNOS 12.3R12-S3.1, Build date: 2016-07-23"
                " 13:35:17 UTC Copyright (c) 1996-2016 Juniper Networks, Inc."
            ),
            {"vendor": JUNIPER, "model": "ex4200-24f", "software_version": "JUNOS 12.3R12-S3.1"},
        ),
        (
            (
                "Juniper Networks, Inc. qfx5100-96s-8q Ethernet Switch, kernel JUNOS 21.2X4.1, Build date: 2023-02-01"
                " 09:52:49 UTC Copyright (c) 1996-2023 Juniper Networks, Inc."
            ),
            {"vendor": JUNIPER, "model": "qfx5100-96s-8q", "software_version": "JUNOS 21.2X4.1"},
        ),
        (
            (
                "Juniper Networks, Inc. mx240 internet router, kernel JUNOS 19.4X12.1, Build date: 2022-04-18 22:17:54"
                " UTC Copyright (c) 1996-2022 Juniper Networks, Inc."
            ),
            {"vendor": JUNIPER, "model": "mx240", "software_version": "JUNOS 19.4X12.1"},
        ),
        (
            (
                "Juniper Networks, Inc. mx480 internet router, kernel JUNOS 19.4X12.1, Build date: 2022-04-18 22:17:54"
                " UTC Copyright (c) 1996-2022 Juniper Networks, Inc."
            ),
            {"vendor": JUNIPER, "model": "mx480", "software_version": "JUNOS 19.4X12.1"},
        ),
        (
            (
                "Juniper Networks, Inc. mx960 internet router, kernel JUNOS 19.4R2-S3.2, Build date: 2020-11-12"
                " 20:58:06 UTC Copyright (c) 1996-2020 Juniper Networks, Inc."
            ),
            {"vendor": JUNIPER, "model": "mx960", "software_version": "JUNOS 19.4R2-S3.2"},
        ),
        (
            (
                "Juniper Networks, Inc. mx960 internet router, kernel JUNOS 19.4X12.1, Build date: 2022-04-18 22:17:54"
                " UTC Copyright (c) 1996-2022 Juniper Networks, Inc."
            ),
            {"vendor": JUNIPER, "model": "mx960", "software_version": "JUNOS 19.4X12.1"},
        ),
        ("5171 Packetwave Platform", {"vendor": SUMITOMO, "model": "5171 Packetwave Platform"}),
        (
            (
                "SUMITOMO ELECTRIC FSU7100, HWType=FSU7100, HWVersion=B0, FWVersion=R4.1.2.3.1.13500,"
                " SystemSerial=3681200050\u0000"
            ),
            {"vendor": SUMITOMO, "model": "FSU7100", "hardware_revision": "B0", "software_version": "R4.1.2.3.1.13500"},
        ),  # Granite marked this model as FSU7101 EPON OLT
        (
            "ETX-203AX Hw: 2.2/F, Sw: 6.4.0(0.94)",
            {"vendor": RAD, "model": "ETX-203AX", "hardware_revision": "2.2/F", "software_version": "6.4.0(0.94)"},
        ),
        (
            "ETX-220A Hw: 0.0/E, Sw: 6.4.0(0.52)",
            {"vendor": RAD, "model": "ETX-220A", "hardware_revision": "0.0/E", "software_version": "6.4.0(0.52)"},
        ),
        (
            "ETX-2I-10G-LC Hw: 0.2/A, Sw: 5.7.0(0.87.9)",
            {
                "vendor": RAD,
                "model": "ETX-2I-10G-LC",
                "hardware_revision": "0.2/A",
                "software_version": "5.7.0(0.87.9)",
            },
        ),
        (
            "ETX-2i-10G-B-8SFPP Hw: 0.3/A, Sw: 6.8.2(4.77)",
            {
                "vendor": RAD,
                "model": "ETX-2i-10G-B-8SFPP",
                "hardware_revision": "0.3/A",
                "software_version": "6.8.2(4.77)",
            },
        ),
    ],
)
def test_normalize_model(sysDescr, description):
    assert description == DeviceSNMP("", "").parse_description(sysDescr)
