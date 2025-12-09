# Template Names
ADVA_FSP_XG108 = "ADVA FSP 150-XG108"
ADVA_114PRO_1G = "FSP 150-GE114PRO-C"  # Chassis ports
ADVA_116PRO_10G = "ADVA FSP 150-XG116PRO"
ADVA_116PROH_10G = "ADVA FSP 150-XG116PROH"
ADVA_120PRO_10G = "ADVA FSP 150-XG120PRO"
ADVA_LEGACY_114_1G = "FSP 150CC-GE114/114S"  # Chassis ports
AUDIOCODES_M500B = "MEDIANT 500B SBC"
# TODO: Get different 1000B for the standard pri
AUDIOCODES_MEDIANT_1000B_4D38FXS = "MEDIANT 1000B 4-D3/8-FXS GATEWAY"
AUDIOCODES_MEDIANT_1000B_824FXS = "MEDIANT 1000B 8-24 FXS GATEWAY"
AUDIOCODES_MEDIANT_MP_52424FXS = "MEDIANT MP-524/24 FXS"
AUDIOCODES_MEDIANT_800B = "MEDIANT 800B-V-1ET4S-4L"
AUDIOCODES_MEDIANT_800C_200_SIP = "MEDIANT 800C 200-SIP/8-FXS GATEWAY"
AUDIOCODES_MEDIANT_800C_60_SIP = "MEDIANT 800C 60-SIP/8-FXS GATEWAY"
CRADLEPOINT_ARC = "ARC CBA850"
CRADLEPOINT_E100 = "CRADLEPOINT E100 C4D/C7C"
CRADLEPOINT_W1850 = "CRADLEPOINT W1850"
MERAKI_MX_68 = "MERAKI MX68"
MERAKI_MX_85 = "MERAKI MX85"
MERAKI_MX_105 = "MERAKI MX105"
MERAKI_MX_250 = "MERAKI MX250"
MERAKI_MX_450 = "MERAKI MX450"
RAD_203AX_1G = "ETX203AX/2SFP/2UTP2SFP"  # Chassis ports
RAD_220A_10G = "ETX-220A"
RAD_2I_10G_HALF = "RAD ETX-2I-10G/4SFPP/4SFP4UTP"
RAD_2I_10G_FULL = "RAD ETX-2I-10G/4SFPP/24SFP"
RAD_2I_10G_B_HALF = "RAD ETX-2I-10G-B/8.5/8SFPP"
RAD_2I_10G_B_FULL = "RAD ETX-2I-10G-B/19/8SFPP"
JUNIPER_AGG = "EX4200-24F 24-PORT SWITCH"  # not approved for new customer orders

# model names
MODEL_NAMES = {
    ADVA_FSP_XG108: "FSP 150-XG108",
    ADVA_114PRO_1G: "FSP 150-GE114PRO-C",
    ADVA_116PRO_10G: "FSP 150-XG116PRO",
    ADVA_116PROH_10G: "FSP 150-XG116PROH",
    ADVA_120PRO_10G: "FSP 150-XG120PRO",
    ADVA_LEGACY_114_1G: "FSP 150CC-GE114/114S",
    AUDIOCODES_M500B: "M500B",
    AUDIOCODES_MEDIANT_1000B_4D38FXS: "MEDIANT 1000B 4-D3/8-FXS GATEWAY",
    AUDIOCODES_MEDIANT_1000B_824FXS: "M1KB/8S/CH/ALU",
    AUDIOCODES_MEDIANT_MP_52424FXS: "MEDIANT MP-524/24 FXS",
    AUDIOCODES_MEDIANT_800B: "M800B-V-1ET4S-4L",
    AUDIOCODES_MEDIANT_800C_200_SIP: "M800C/8S/200SIP/ALU",
    AUDIOCODES_MEDIANT_800C_60_SIP: "M800C/8S/60SIP/ALU",
    CRADLEPOINT_ARC: "ARC CBA850",
    CRADLEPOINT_E100: "E100 C4D/C7C",
    CRADLEPOINT_W1850: "W1850",
    RAD_203AX_1G: "ETX203AX/2SFP/2UTP2SFP",
    RAD_220A_10G: "ETX-220A",
    RAD_2I_10G_HALF: "ETX-2I-10G/4SFPP/4SFP4UTP",
    RAD_2I_10G_FULL: "ETX-2I-10G/4SFPP/24SFP",
    RAD_2I_10G_B_HALF: "ETX-2I-10G-B/8.5/8SFPP",
    RAD_2I_10G_B_FULL: "ETX-2I-10G-B/19/8SFPP",
    JUNIPER_AGG: "EX4200-24F",
    MERAKI_MX_68: "MERAKI MX68",
    MERAKI_MX_85: "MERAKI MX85",
    MERAKI_MX_105: "MERAKI MX105",
    MERAKI_MX_250: "MERAKI MX250",
    MERAKI_MX_450: "MERAKI MX450",
}

TEMPLATE_NAMES = {v: k for k, v in MODEL_NAMES.items()}

# card templates
LC_1G = "GENERIC SFP LEVEL 1"
LC_10G = "GENERIC SFP+ LEVEL 1"
RJ45_1G = "GENERIC COPPER SFP LEVEL 1"
SC_1G = "GENERIC SFP LEVEL 1 SC"
SC_10G = "GENERIC SFP+ LEVEL 1 SC"
ADVA_1G = "ADVA GENERIC SFP LEVEL 1"
ADVA_SC_1G = "ADVA GENERIC SFP LEVEL 1 SC"
XFP_10G = "GENERIC XFP LEVEL 1"
XFP_10G_SC = "GENERIC XFP LEVEL 1 SC"
M500_PORT = "M500 FIXED ETHERNET PORTS"
MEDIANT_M1K_MODULE = "MEDIANT M1K CRMX-C MODULE"
MEDIANT_M1K_QUAD_TRUNKS = "MEDIANT M1K-TMX-1A1V1 QUAD TRUNKS"
AUDIOCODES_M800B_FXS = "AUDIOCODES M800B FXS"
AUDIOCODES_M800B_GE_LAN = "AUDIOCODES M800B GE LAN PORTS"
AUDIOCODES_M800B_ISDN_PRI = "AUDIOCODES M800B ISDN PRI (E1/T1) TRUNKS"
AUDIOCODES_FIXED_CHASSIS_PORTS = "AUDIOCODES FIXED CHASSIS PORTS"
AUDIOCODES_24_PORT_FXS_CARD = "AUDIOCODES 24 PORT FXS CARD"
GENERIC_SFP = "GENERIC SFP"
AUDIOCODES_4_PORT_FXS = "AUDIOCODES 4 PORT FXS CARD"
MEDIANT_800C_CHASSIS_PORTS = "MEDIANT 800C CHASSIS PORTS"
CRADLEPOINT_ARC_CBA850_CHASSIS_PORTS = "CRADLEPOINT ARC CBA850 CHASSIS PORTS"
CRADLEPOINT_E100_FIXED_CHASSIS_PORTS = "CRADLEPOINT E100 FIXED CHASSIS PORTS"
CRADLEPOINT_W1850_FIXED_CHASSIS_PORTS = "W1850 CHASSIS PORTS"
MERAKI_MX68_FIREWALL_CHASSIS_PORTS = "CISCO_MERAKI_MX68_FIREWALL_CHASSIS_PORTS"
MERAKI_MX85_FIREWALL_CHASSIS_PORTS = "CISCO_MERAKI_MX85_FIREWALL_CHASSIS_PORTS"
MERAKI_MX105_FIREWALL_CHASSIS_PORTS = "CISCO_MERAKI_MX105_FIREWALL_CHASSIS_PORTS"
MERAKI_MX250_FIREWALL_CHASSIS_PORTS = "CISCO_MERAKI_MX250_FIREWALL_CHASSIS_PORTS"
MERAKI_MX450_FIREWALL_CHASSIS_PORTS = "CISCO_MERAKI_MX450_FIREWALL_CHASSIS_PORTS"

# returns primary slot, port access id, and card template
#  (in that order)
PRIMARY_SLOT_PAID_TEMPLATE = {
    ADVA_FSP_XG108: {
        "uplink": {"LC": ("NETWORK 1", "NETWORK-1-1-1-1", LC_10G)},
        "handoff": {
            "1 Gbps": {
                "RJ-45": ("3", "ACCESS-1-1-1-3", RJ45_1G),
                "SC": ("3", "ACCESS-1-1-1-3", SC_1G),
                "LC": ("3", "ACCESS-1-1-1-3", LC_1G),
            },
            "10 Gbps": {"RJ-45": None, "SC": ("7", "ACCESS-1-1-1-7", SC_10G), "LC": ("7", "ACCESS-1-1-1-7", LC_10G)},
        },
    },
    ADVA_114PRO_1G: {
        "uplink": {"LC": ("01", "NETWORK-1-1-1-1", LC_1G)},
        "handoff": {
            "1 Gbps": {
                "RJ-45": ("CHASSIS PORTS", "ACCESS-1-1-1-3", ADVA_1G),
                "SC": ("03", "ACCESS-1-1-1-3", SC_1G),
                "LC": ("03", "ACCESS-1-1-1-3", ADVA_1G),
            }
        },
    },
    ADVA_116PRO_10G: {
        "uplink": {"LC": ("8-1/10GBE", "ETH_PORT-1-1-1-8", LC_10G)},
        "handoff": {
            "1 Gbps": {
                "RJ-45": ("1-100FX/1GBE", "ETH_PORT-1-1-1-1", RJ45_1G),
                "SC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", SC_1G),
                "LC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", LC_1G),
            },
            "10 Gbps": {
                "RJ-45": None,
                "SC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", SC_10G),
                "LC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", LC_10G),
            },
        },
    },
    ADVA_116PROH_10G: {
        "uplink": {"LC": ("8-1/10GBE", "ETH_PORT-1-1-1-8", LC_10G)},
        "handoff": {
            "1 Gbps": {
                "RJ-45": ("1-100FX/1GBE", "ETH_PORT-1-1-1-1", RJ45_1G),
                "SC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", SC_1G),
                "LC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", LC_1G),
            },
            "10 Gbps": {
                "RJ-45": None,
                "SC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", SC_10G),
                "LC": ("3-1/10GBE", "ETH_PORT-1-1-1-3", LC_10G),
            },
        },
    },
    ADVA_120PRO_10G: {
        "uplink": {"LC": ("26", "ETH_PORT-1-1-1-26", LC_10G)},
        "handoff": {
            "1 Gbps": {"RJ-45": None, "SC": None, "LC": ("01", "ETH_PORT-1-1-1-1", LC_1G)},
            "10 Gbps": {"RJ-45": None, "SC": None, "LC": ("23", "ETH_PORT-1-1-1-23", LC_10G)},
        },
    },
    RAD_203AX_1G: {
        "uplink": {"LC": ("NET 1", "ETH PORT 1", LC_1G)},
        "handoff": {
            "1 Gbps": {
                "RJ-45": ("FIXED PORTS", "ETH PORT 3", RJ45_1G),
                "SC": ("USER 5", "ETH PORT 5", SC_1G),
                "LC": ("USER 5", "ETH PORT 5", LC_1G),
            }
        },
    },
    RAD_220A_10G: {
        "uplink": {"LC": ("4/1", "4/1", XFP_10G)},
        "handoff": {"1 Gbps": {"LC": ("1/1", "1/1", LC_1G)}, "10 Gbps": {"LC": ("3/1", "3/1", XFP_10G)}},
    },
    RAD_2I_10G_HALF: {
        "uplink": {"LC": ("0/1", "ETH PORT 0/1", LC_10G)},
        "handoff": {
            "1 Gbps": {"RJ-45": ("CHASSIS", "ETH PORT 0/9", None), "SC": None, "LC": ("0/5", "ETH PORT 0/5", LC_1G)},
            "10 Gbps": {"RJ-45": None, "SC": None, "LC": ("0/3", "ETH PORT 0/3", LC_10G)},
        },
    },
    RAD_2I_10G_FULL: {
        "uplink": {"LC": ("0/1", "ETH PORT 0/1", LC_10G)},
        "handoff": {
            "1 Gbps": {"RJ-45": ("0/5", "ETH PORT 0/5", RJ45_1G), "SC": None, "LC": ("0/5", "ETH PORT 0/5", LC_1G)},
            "10 Gbps": {"RJ-45": None, "SC": None, "LC": ("0/3", "ETH PORT 0/3", LC_10G)},
        },
    },
    RAD_2I_10G_B_HALF: {
        "uplink": {"LC": ("0/8", "0/8", LC_10G)},
        "handoff": {
            "1 Gbps": {"RJ-45": ("0/1", "0/1", RJ45_1G), "SC": ("0/1", "0/1", SC_1G), "LC": ("0/1", "0/1", LC_1G)},
            "10 Gbps": {"RJ-45": None, "SC": ("0/1", "0/1", SC_10G), "LC": ("0/1", "0/1", LC_10G)},
        },
    },
    RAD_2I_10G_B_FULL: {
        "uplink": {"LC": ("0/8", "0/8", LC_10G)},
        "handoff": {
            "1 Gbps": {"RJ-45": ("0/1", "0/1", RJ45_1G), "SC": ("0/1", "0/1", SC_1G), "LC": ("0/1", "0/1", LC_1G)},
            "10 Gbps": {"RJ-45": None, "SC": ("0/1", "0/1", SC_10G), "LC": ("0/1", "0/1", LC_10G)},
        },
    },
    CRADLEPOINT_ARC: {
        "uplink": {"RF": ("WAN - ANTENNA", "WAN-1", CRADLEPOINT_ARC_CBA850_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN 1", "LAN 1", CRADLEPOINT_ARC_CBA850_CHASSIS_PORTS)}},
    },
    CRADLEPOINT_E100: {
        "uplink": {"RF": ("WAN - ANTENNA", "WAN 1", CRADLEPOINT_E100_FIXED_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN 01", "LAN 1", CRADLEPOINT_E100_FIXED_CHASSIS_PORTS)}},
    },
    CRADLEPOINT_W1850: {
        "uplink": {"RF": ("WAN 01", "WAN 01", CRADLEPOINT_W1850_FIXED_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN 01", "LAN 01", CRADLEPOINT_W1850_FIXED_CHASSIS_PORTS)}},
    },
    JUNIPER_AGG: {
        "uplink": {"LC": ("", "", "")},
        "handoff": {
            "1 Gbps": {"RJ-45": None, "SC": None, "LC": ("00", "GE-0/0/0", LC_1G)},
            "10 Gbps": {"RJ-45": None, "SC": None, "LC": ("00", "XE-0/1/0", LC_10G)},
        },
    },
    MERAKI_MX_68: {
        "uplink": {"RJ-45": ("WAN01", "WAN01", MERAKI_MX68_FIREWALL_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN03", "LAN03", MERAKI_MX68_FIREWALL_CHASSIS_PORTS)}},
    },
    MERAKI_MX_85: {
        "uplink": {"RJ-45": ("WAN03", "WAN03", MERAKI_MX85_FIREWALL_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN05", "LAN05", MERAKI_MX85_FIREWALL_CHASSIS_PORTS)}},
    },
    MERAKI_MX_105: {
        "uplink": {"RJ-45": ("WAN03", "WAN03", MERAKI_MX105_FIREWALL_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN05", "LAN05", MERAKI_MX105_FIREWALL_CHASSIS_PORTS)}},
    },
    MERAKI_MX_250: {
        "uplink": {"LC": ("WAN01", "WAN01", MERAKI_MX250_FIREWALL_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("LAN03", "LAN03", MERAKI_MX250_FIREWALL_CHASSIS_PORTS)}},
    },
    MERAKI_MX_450: {
        "uplink": {"RJ-45": ("08", "08", MERAKI_MX450_FIREWALL_CHASSIS_PORTS)},
        "handoff": {"1 Gbps": {"RJ-45": ("01", "01", MERAKI_MX450_FIREWALL_CHASSIS_PORTS)}},
    },
    ADVA_LEGACY_114_1G: {
        "uplink": {"LC": ("", "", "")},
        "handoff": {
            "1 Gbps": {"RJ-45": None, "SC": None, "LC": None},
            "10 Gbps": {"RJ-45": None, "SC": None, "LC": None},
        },
    },
}

# returns secondary slot, port access id, and card template
# for PAID: dict indicates dual purpose port (either secondary uplink or access handoff)
#           str indicates dedicated secondary uplink port
SECONDARY_SLOT_PAID_TEMPLATE = {
    ADVA_FSP_XG108: {"secondary": {"LC": ("NETWORK 2", "NETWORK-1-1-1-2", LC_10G)}},
    ADVA_114PRO_1G: {"secondary": {"LC": ("02", "NETWORK-1-1-1-2", LC_1G)}},
    ADVA_116PRO_10G: {"secondary": {"LC": ("7-1/10GBE", "ETH_PORT-1-1-1-7", LC_10G)}},
    ADVA_116PROH_10G: {"secondary": {"LC": ("7-1/10GBE", "ETH_PORT-1-1-1-7", LC_10G)}},
    ADVA_120PRO_10G: {"secondary": {"LC": ("", "", "")}},
    RAD_203AX_1G: {"secondary": {"LC": ("NET 2/USER", "ETH PORT 2", LC_1G)}},
    RAD_220A_10G: {"secondary": {"LC": ("4/2", "4/2", XFP_10G)}},
    RAD_2I_10G_HALF: {"secondary": {"LC": ("0/2", "ETH PORT 0/2", LC_10G)}},
    RAD_2I_10G_FULL: {"secondary": {"LC": ("0/2", "ETH PORT 0/2", LC_10G)}},
    RAD_2I_10G_B_HALF: {"secondary": {"LC": ("0/7", "0/7", LC_10G)}},
    RAD_2I_10G_B_FULL: {"secondary": {"LC": ("0/7", "0/7", LC_10G)}},
    ADVA_LEGACY_114_1G: {"secondary": {"LC": ("", "", "")}},
    JUNIPER_AGG: {"secondary": {"LC": ("", "", "")}},
    CRADLEPOINT_ARC: {"secondary": {"RF": ("", "", "")}},
    CRADLEPOINT_E100: {"secondary": {"RF": ("", "", "")}},
    CRADLEPOINT_W1850: {"secondary": {"RF": ("", "", "")}},
}

AVAILABLE_HANDOFF_PORTS = {
    ADVA_FSP_XG108: {
        "1 Gbps": {
            "LC": [(f"{i}", f"ACCESS-1-1-1-{i}", LC_1G) for i in range(3, 9)],
            "SC": [(f"{i}", f"ACCESS-1-1-1-{i}", SC_1G) for i in range(3, 9)],
            "RJ-45": [(f"{i}", f"ACCESS-1-1-1-{i}", RJ45_1G) for i in range(3, 9)],
        },
        "10 Gbps": {
            "LC": [(f"{i}", f"ACCESS-1-1-1-{i}", LC_10G) for i in range(7, 9)],
            "SC": [(f"{i}", f"ACCESS-1-1-1-{i}", SC_10G) for i in range(7, 9)],
            "RJ-45": [],
        },
    },
    ADVA_114PRO_1G: {
        "1 Gbps": {
            "LC": [(f"0{i}", f"ACCESS-1-1-1-{i}", ADVA_1G) for i in range(3, 7)],
            "SC": [(f"0{i}", f"ACCESS-1-1-1-{i}", ADVA_SC_1G) for i in range(3, 7)],
            "RJ-45": [("CHASSIS PORTS", f"ACCESS-1-1-1-{i}", ADVA_1G) for i in range(3, 7)],
        },
        "10 Gbps": {"LC": [], "SC": [], "RJ-45": []},
    },
    ADVA_116PRO_10G: {
        "1 Gbps": {
            "LC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", LC_1G) for i in range(3, 7)],
            "SC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", SC_1G) for i in range(3, 7)],
            "RJ-45": [("1-100FX/1GBE", "ETH_PORT-1-1-1-1", RJ45_1G), ("2-100FX/1GBE", "ETH_PORT-1-1-1-2", RJ45_1G)]
            + [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", RJ45_1G) for i in range(3, 7)],
        },
        "10 Gbps": {
            "LC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", LC_10G) for i in range(3, 7)],
            "SC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", SC_10G) for i in range(3, 7)],
            "RJ-45": [],
        },
    },
    ADVA_116PROH_10G: {
        "1 Gbps": {
            "LC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", LC_1G) for i in range(3, 7)],
            "SC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", SC_1G) for i in range(3, 7)],
            "RJ-45": [("1-100FX/1GBE", "ETH_PORT-1-1-1-1", RJ45_1G), ("2-100FX/1GBE", "ETH_PORT-1-1-1-2", RJ45_1G)]
            + [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", RJ45_1G) for i in range(3, 7)],
        },
        "10 Gbps": {
            "LC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", LC_10G) for i in range(3, 7)],
            "SC": [(f"{i}-1/10GBE", f"ETH_PORT-1-1-1-{i}", SC_10G) for i in range(3, 7)],
        },
    },
    ADVA_120PRO_10G: {
        "1 Gbps": {
            "LC": [(f"{i:02d}", f"ETH_PORT-1-1-1-{i}", LC_1G) for i in range(1, 25)],
            "SC": [(f"{i:02d}", f"ETH_PORT-1-1-1-{i}", SC_1G) for i in range(1, 25)],
            "RJ-45": [(f"{i:02d}", f"ETH_PORT-1-1-1-{i}", RJ45_1G) for i in range(1, 25)],
        },
        "10 Gbps": {
            "LC": [(f"{i:02d}", f"ETH_PORT-1-1-1-{i}", LC_10G) for i in range(23, 25)],
            "SC": [(f"{i:02d}", f"ETH_PORT-1-1-1-{i}", SC_10G) for i in range(23, 25)],
            "RJ-45": [],
        },
    },
    RAD_203AX_1G: {
        "1 Gbps": {
            "LC": [("USER 5", "ETH PORT 5", LC_1G), ("USER 6", "ETH PORT 6", LC_1G)],
            "SC": [("USER 5", "ETH PORT 5", SC_1G), ("USER 6", "ETH PORT 6", SC_1G)],
            "RJ-45": [
                ("FIXED PORTS", "ETH PORT 3", RJ45_1G),
                ("FIXED PORTS", "ETH PORT 4", RJ45_1G),
                ("USER 5", "ETH PORT 5", RJ45_1G),
                ("USER 6", "ETH PORT 6", RJ45_1G),
            ],
        },
        "10 Gbps": {"LC": [], "SC": [], "RJ-45": []},
    },
    RAD_220A_10G: {
        "1 Gbps": {
            "LC": [(f"1/{i}", f"1/{i}", LC_1G) for i in range(1, 10)],
            "SC": [(f"1/{i}", f"1/{i}", SC_1G) for i in range(1, 10)],
            "RJ-45": [(f"1/{i}", f"1/{i}", RJ45_1G) for i in range(1, 10)],
        },
        "10 Gbps": {
            "LC": [("3/1", "3/1", XFP_10G), ("3/2", "3/2", XFP_10G)],
            "SC": [("3/1", "3/1", XFP_10G_SC), ("3/2", "3/2", XFP_10G_SC)],
            "RJ-45": [],
        },
    },
    RAD_2I_10G_HALF: {
        "1 Gbps": {
            "LC": [(f"0/{i}", f"ETH PORT 0/{i}", LC_1G) for i in range(5, 9)],
            "SC": [(f"0/{i}", f"ETH PORT 0/{i}", SC_1G) for i in range(5, 9)],
            "RJ-45": [("CHASSIS", f"ETH PORT 0/{i}", RJ45_1G) for i in range(9, 13)],
        },
        "10 Gbps": {
            "LC": [(f"0/{i}", f"ETH PORT 0/{i}", LC_10G) for i in range(3, 5)],
            "SC": [(f"0/{i}", f"ETH PORT 0/{i}", SC_10G) for i in range(3, 5)],
            "RJ-45": [],
        },
    },
    RAD_2I_10G_FULL: {
        "1 Gbps": {
            "LC": [(f"0/{i}", f"ETH PORT 0/{i}", LC_1G) for i in range(5, 29)],
            "SC": [(f"0/{i}", f"ETH PORT 0/{i}", SC_1G) for i in range(5, 29)],
            "RJ-45": [(f"0/{i}", f"ETH PORT 0/{i}", RJ45_1G) for i in range(5, 29)],
        },
        "10 Gbps": {
            "LC": [(f"0/{i}", f"ETH PORT 0/{i}", LC_10G) for i in range(3, 5)],
            "SC": [(f"0/{i}", f"ETH PORT 0/{i}", SC_10G) for i in range(3, 5)],
            "RJ-45": [],
        },
    },
    RAD_2I_10G_B_HALF: {
        "1 Gbps": {
            "LC": [(f"0/{i}", f"0/{i}", LC_1G) for i in range(1, 5)],
            "SC": [(f"0/{i}", f"0/{i}", SC_1G) for i in range(1, 5)],
            "RJ-45": [(f"0/{i}", f"0/{i}", RJ45_1G) for i in range(1, 5)],
        },
        "10 Gbps": {
            "LC": [(f"0/{i}", f"0/{i}", LC_10G) for i in range(1, 5)],
            "SC": [(f"0/{i}", f"0/{i}", SC_10G) for i in range(1, 5)],
            "RJ-45": [],
        },
    },
    RAD_2I_10G_B_FULL: {
        "1 Gbps": {
            "LC": [(f"0/{i}", f"0/{i}", LC_1G) for i in range(1, 5)],
            "SC": [(f"0/{i}", f"0/{i}", SC_1G) for i in range(1, 5)],
            "RJ-45": [(f"0/{i}", f"0/{i}", RJ45_1G) for i in range(1, 5)],
        },
        "10 Gbps": {
            "LC": [(f"0/{i}", f"0/{i}", LC_10G) for i in range(1, 5)],
            "SC": [(f"0/{i}", f"0/{i}", SC_10G) for i in range(1, 5)],
            "RJ-45": [],
        },
    },
    CRADLEPOINT_ARC: {
        "1 Gbps": {"LC": [("WAN - ANTENNA", "WAN-1", "")], "RJ-45": []},
        "10 Gbps": {"LC": [], "RJ-45": [("LAN 1", "LAN 1", RJ45_1G)]},
    },
    CRADLEPOINT_E100: {
        "1 Gbps": {"LC": [("WAN 01", "WAN 1", "")], "RJ-45": []},
        "10 Gbps": {"LC": [], "RJ-45": [("LAN 1", "LAN 1", RJ45_1G)]},
    },
    JUNIPER_AGG: {
        "1 Gbps": {"LC": [(f"{i:02d}", f"GE-0/0/{i}", LC_1G) for i in range(0, 24)], "RJ-45": []},
        "10 Gbps": {"LC": [(f"{i:02d}", f"XE-0/1/{i}", LC_10G) for i in range(0, 2)], "RJ-45": []},
    },
    ADVA_LEGACY_114_1G: {
        "1 Gbps": {
            "LC": [("CHASSIS", f"ACCESS-1-1-1-{i}", LC_1G) for i in range(3, 7)],
            "SC": [("CHASSIS", f"ACCESS-1-1-1-{i}", SC_1G) for i in range(3, 7)],
            "RJ-45": [("CHASSIS", f"ACCESS-1-1-1-{i}", RJ45_1G) for i in range(3, 7)],
        },
        "10 Gbps": {"LC": [], "SC": [], "RJ-45": []},
    },
}

OVERLAY_PRIMARY_SLOT_PAID_TEMPLATE = {
    AUDIOCODES_M500B: {"uplink": ("WAN", "2/1", M500_PORT), "handoff": ("LAN 1", "GE1/1", M500_PORT)},
    AUDIOCODES_MEDIANT_1000B_4D38FXS: {
        "uplink": ("0/0(WAN)", "GE0/0", MEDIANT_M1K_MODULE),
        "handoff": ("ET/T1-1", "ET-T1 [MOD#]/[PORT#]", MEDIANT_M1K_QUAD_TRUNKS),
    },
    AUDIOCODES_MEDIANT_1000B_824FXS: {
        "uplink": ("0/0(WAN)", "GE0/0", MEDIANT_M1K_MODULE),
        "handoff": ("ET/T1-1", "ET-T1 [MOD#]/[PORT#]", MEDIANT_M1K_QUAD_TRUNKS),
    },
    AUDIOCODES_MEDIANT_800B: {
        "uplink": ("1", "WAN", GENERIC_SFP),
        "handoff": ("GE-4/1", "GE-4/1", AUDIOCODES_M800B_GE_LAN),
    },
    AUDIOCODES_MEDIANT_800C_200_SIP: {
        "uplink": ("WAN", "WAN", MEDIANT_800C_CHASSIS_PORTS),
        "handoff": ("1", "1/1", AUDIOCODES_4_PORT_FXS),
    },
    AUDIOCODES_MEDIANT_800C_60_SIP: {
        "uplink": ("WAN", "WAN", MEDIANT_800C_CHASSIS_PORTS),
        "handoff": ("1", "1/1", AUDIOCODES_4_PORT_FXS),
    },
    AUDIOCODES_MEDIANT_MP_52424FXS: {
        "uplink": ("GIGABIT ETHERNET 1 (WAN)", "GE0/1", AUDIOCODES_FIXED_CHASSIS_PORTS),
        "handoff": ("01", "FXS-1", AUDIOCODES_24_PORT_FXS_CARD),
    },
    MERAKI_MX_68: {
        "uplink": ("WAN01", "WAN01", MERAKI_MX68_FIREWALL_CHASSIS_PORTS),
        "handoff": ("LAN03", "LAN03", MERAKI_MX68_FIREWALL_CHASSIS_PORTS),
    },
    MERAKI_MX_85: {
        "uplink": ("WAN03", "WAN03", MERAKI_MX85_FIREWALL_CHASSIS_PORTS),
        "handoff": ("LAN05", "LAN05", MERAKI_MX85_FIREWALL_CHASSIS_PORTS),
    },
    MERAKI_MX_105: {
        "uplink": ("WAN03", "WAN03", MERAKI_MX105_FIREWALL_CHASSIS_PORTS),
        "handoff": ("LAN05", "LAN05", MERAKI_MX105_FIREWALL_CHASSIS_PORTS),
    },
    MERAKI_MX_250: {
        "uplink": ("WAN01", "WAN01", MERAKI_MX250_FIREWALL_CHASSIS_PORTS),
        "handoff": ("LAN03", "LAN03", MERAKI_MX250_FIREWALL_CHASSIS_PORTS),
    },
    MERAKI_MX_450: {
        "uplink": ("08", "08", MERAKI_MX450_FIREWALL_CHASSIS_PORTS),
        "handoff": ("01", "01", MERAKI_MX450_FIREWALL_CHASSIS_PORTS),
    },
}

OVERLAY_AVAILABLE_HANDOFF_PORTS = {
    AUDIOCODES_M500B: [(f"LAN {i}", f"GE1/{i}", M500_PORT) for i in range(1, 5)],
    AUDIOCODES_MEDIANT_1000B_824FXS: [
        (f"ET/T1-{i}", "ET-T1 [MOD#]/[PORT#]", MEDIANT_M1K_QUAD_TRUNKS) for i in range(1, 5)
    ],
    AUDIOCODES_MEDIANT_800B: [(f"3/{i}", f"3/{i}", AUDIOCODES_M800B_FXS) for i in range(1, 5)]
    + [(f"GE-4/{i}", f"GE-4/{i}", AUDIOCODES_M800B_GE_LAN) for i in range(1, 5)],
    AUDIOCODES_MEDIANT_800C_200_SIP: [(f"{i}", f"(slot)/{i}", AUDIOCODES_4_PORT_FXS) for i in range(1, 5)],
    AUDIOCODES_MEDIANT_800C_60_SIP: [(f"{i}", f"{i}", AUDIOCODES_4_PORT_FXS) for i in range(1, 5)],
    AUDIOCODES_MEDIANT_MP_52424FXS: [(f"0{i}", f"FXS-{i}", AUDIOCODES_24_PORT_FXS_CARD) for i in range(1, 5)],
    MERAKI_MX_68: [(f"{i}", f"{i}", MERAKI_MX68_FIREWALL_CHASSIS_PORTS) for i in range(3, 12)],
    MERAKI_MX_85: [(f"{i}", f"{i}", MERAKI_MX85_FIREWALL_CHASSIS_PORTS) for i in range(5, 12)],
    MERAKI_MX_105: [(f"{i}", f"{i}", MERAKI_MX105_FIREWALL_CHASSIS_PORTS) for i in range(5, 8)],
    MERAKI_MX_250: [(f"{i}", f"{i}", MERAKI_MX250_FIREWALL_CHASSIS_PORTS) for i in range(3, 26)],
    MERAKI_MX_450: [(f"{i}", f"{i}", MERAKI_MX450_FIREWALL_CHASSIS_PORTS) for i in range(1, 5)],
}
