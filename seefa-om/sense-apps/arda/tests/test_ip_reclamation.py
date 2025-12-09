import pytest

from unittest import mock

from arda_app.bll.net_new import ip_reclamation
from common_sense.common.errors import AbortException


def mock_ip_subnets(*args):
    return {
        "IPV4_ASSIGNED_SUBNETS": "98.123.148.56/29",
        "IPV6_ASSIGNED_SUBNETS": "2600:5c01:4a27::/48",
        "IPV4_GLUE_SUBNET": None,
        "IPV6_GLUE_SUBNET": "2600:5c01:4860:5::/64",
    }


def mock_path_elements(*args, **kwargs):
    return [
        {
            "CIRC_PATH_INST_ID": "1334717",
            "PATH_NAME": "33.L1XX.006714..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCKX-KUEHNE NAGEL//3929 WESTPOINT BLVD",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCKX",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "CAR-DIA",
            "BANDWIDTH": "25 Mbps",
            "BW_SIZE": "25000000",
            "CUSTOMER_ID": "ACCT-28317054",
            "CUSTOMER_NAME": "PATH FORWARD",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "173.95.101.40",
            "IPV4_ASSIGNED_GATEWAY": "173.95.101.41",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2606:A000:0:8::F:3096/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:5800:8C6::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "CARRIER ACCESS",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1533950",
            "A_SITE_NAME": "WNSLNCKX-KUEHNE NAGEL//3929 WESTPOINT BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCKX2ZW/999.9999.999.99",
            "ELEMENT_REFERENCE": "1037108",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED PORTS",
            "PORT_NAME": "USER 3",
            "PORT_INST_ID": "103833216",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "CONNECTOR_TYPE": "RJ-45",
            "FQDN": "WNSLNCKX2ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "WNSLNCKX2ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "DHCP",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1162",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1128201",
            "PATH_NAME": "33001.GE40L.WNSLNCPV1CW.WNSLNCPV0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCPV",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "HUB",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-EDGE TRANSPORT",
            "BANDWIDTH": "AGGREGATE",
            "BW_SIZE": "0",
            "CUSTOMER_ID": None,
            "CUSTOMER_NAME": None,
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": None,
            "ORDER_REFERENCE": "2.1.1.",
            "PARENT_SEQUENCE": "2",
            "PARENT_MEMBER_NBR": "1",
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1313051",
            "A_SITE_NAME": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCPV1CW/001.0001.102.11/RTR",
            "ELEMENT_REFERENCE": "514200",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1162",
            "CHAN_INST_ID": "7163953",
            "SLOT": "3/0",
            "PORT_NAME": "1",
            "PORT_INST_ID": "103005919",
            "PORT_ACCESS_ID": "ET-4/3/0",
            "CONNECTOR_TYPE": "OTHER",
            "FQDN": "WNSLNCPV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "WNSLNCPV1CW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "24.199.192.102/32",
            "IPV6_ADDRESS": "2606:A000::F:66/128",
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1128201",
            "PATH_NAME": "33001.GE40L.WNSLNCPV1CW.WNSLNCPV0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCPV",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "HUB",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-EDGE TRANSPORT",
            "BANDWIDTH": "AGGREGATE",
            "BW_SIZE": "0",
            "CUSTOMER_ID": None,
            "CUSTOMER_NAME": None,
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": None,
            "ORDER_REFERENCE": "2.1.2.",
            "PARENT_SEQUENCE": "2",
            "PARENT_MEMBER_NBR": "1",
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1313051",
            "A_SITE_NAME": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCPV1CW/001.0001.102.11/RTR",
            "ELEMENT_REFERENCE": "514200",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1162",
            "CHAN_INST_ID": "7163953",
            "SLOT": "3/0",
            "PORT_NAME": "1",
            "PORT_INST_ID": "103005944",
            "PORT_ACCESS_ID": "ET-8/3/0",
            "CONNECTOR_TYPE": "OTHER",
            "FQDN": "WNSLNCPV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "WNSLNCPV1CW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "24.199.192.102/32",
            "IPV6_ADDRESS": "2606:A000::F:66/128",
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1128201",
            "PATH_NAME": "33001.GE40L.WNSLNCPV1CW.WNSLNCPV0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCPV",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "HUB",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-EDGE TRANSPORT",
            "BANDWIDTH": "AGGREGATE",
            "BW_SIZE": "0",
            "CUSTOMER_ID": None,
            "CUSTOMER_NAME": None,
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": None,
            "ORDER_REFERENCE": "2.2.1.",
            "PARENT_SEQUENCE": "2",
            "PARENT_MEMBER_NBR": "2",
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1313051",
            "A_SITE_NAME": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCPV0QW/001.0004.010.26/SWT#0",
            "ELEMENT_REFERENCE": "895569",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1162",
            "CHAN_INST_ID": "7163953",
            "SLOT": "96",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101202650",
            "PORT_ACCESS_ID": "ET-0/0/96",
            "CONNECTOR_TYPE": "OTHER",
            "FQDN": "WNSLNCPV0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "WNSLNCPV0QW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.20.102.126/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1128201",
            "PATH_NAME": "33001.GE40L.WNSLNCPV1CW.WNSLNCPV0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCPV",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "HUB",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-EDGE TRANSPORT",
            "BANDWIDTH": "AGGREGATE",
            "BW_SIZE": "0",
            "CUSTOMER_ID": None,
            "CUSTOMER_NAME": None,
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": None,
            "ORDER_REFERENCE": "2.2.2.",
            "PARENT_SEQUENCE": "2",
            "PARENT_MEMBER_NBR": "2",
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1313051",
            "A_SITE_NAME": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCPV0QW/001.0004.010.23/SWT#1",
            "ELEMENT_REFERENCE": "895581",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1162",
            "CHAN_INST_ID": "7163953",
            "SLOT": "96",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101202795",
            "PORT_ACCESS_ID": "ET-1/0/96",
            "CONNECTOR_TYPE": "OTHER",
            "FQDN": "WNSLNCPV0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "WNSLNCPV0QW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.20.102.126/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1343761",
            "PATH_NAME": "33001.GE1.WNSLNCPV0QW.WNSLNCKX2ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCKX-KUEHNE NAGEL//3929 WESTPOINT BLVD",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCKX",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": None,
            "CUSTOMER_NAME": None,
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": None,
            "ORDER_REFERENCE": "3..1.",
            "PARENT_SEQUENCE": "3",
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543941",
            "A_SITE_NAME": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCPV0QW/001.0004.010.26/SWT#0",
            "ELEMENT_REFERENCE": "895569",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1162",
            "CHAN_INST_ID": "7163952",
            "SLOT": "8",
            "PORT_NAME": "1",
            "PORT_INST_ID": "103833392",
            "PORT_ACCESS_ID": "GE-0/0/8",
            "CONNECTOR_TYPE": "LC",
            "FQDN": "WNSLNCPV0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "WNSLNCPV0QW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.20.102.126/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1343761",
            "PATH_NAME": "33001.GE1.WNSLNCPV0QW.WNSLNCKX2ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WNSLNCPV-TWC/HUB WS-WINSTON",
            "PATH_Z_SITE": "WNSLNCKX-KUEHNE NAGEL//3929 WESTPOINT BLVD",
            "A_CLLI": "WNSLNCPV",
            "Z_CLLI": "WNSLNCKX",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": None,
            "CUSTOMER_NAME": None,
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": None,
            "ORDER_REFERENCE": "3..2.",
            "PARENT_SEQUENCE": "3",
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543941",
            "A_SITE_NAME": "WNSLNCKX-KUEHNE NAGEL//3929 WESTPOINT BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WNSLNCKX2ZW/999.9999.999.99",
            "ELEMENT_REFERENCE": "1037108",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1162",
            "CHAN_INST_ID": "7163952",
            "SLOT": "NET 1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "103833213",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "CONNECTOR_TYPE": "LC",
            "FQDN": "WNSLNCKX2ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "WNSLNCKX2ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "DHCP",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "33.L1XX.006714..TWCC",
            "INITIAL_CIRCUIT_ID": "1334717",
            "LVL": "2",
        },
    ]


def mock_subnet_block(*args, **kwargs):
    return {
        "blockAddr": "2600:5c01:1e3b::",
        "blockName": "2600:5c01:1e3b::/48",
        "blockSize": "48",
        "blockStatus": "Deployed",
        "blockType": "RIP-DIA",
        "conckType": "RIP-DIA",
        "container": "/Commercial/LTWC/Midwest/Customer",
        "createDate": "2025-04-02 13:04:22",
        "createReverseDomains": "False",
        "description": "",
        "discoveryAgent": "InheritFromContainer",
        "excludeFromDiscovery": "False",
        "ipv6": True,
        "lastUpdateDate": "2025-04-02 13:04:22",
        "nonBroadcast": False,
        "primarySubnet": False,
        "userDefinedFields": [
            "Delete_Block=off",
            "Day=",
            "Month=",
            "Year=",
            "Midwest_Divisions=TW-MOH",
            "Company_Name=PATH FORWARD",
            "Account_Number=ACCT-28317054",
            "Notes=ENG-04962299\r\n51.L1XX.023560..CHTR\r\n8060 READING RD\r\nCINCINNATI\r\nOH\r\n45237",
            "Notes_2=",
            "Service_Type=Fiber",
        ],
    }


def mock_subnet_block_not_found(*args, ip="2605:A000:0:8::F:D8CE/127", **kwargs):
    return f"IP Block not found for blockName : {ip}"


def mock_subnet_block_customer_mismatch(*args, **kwargs):
    return {
        "blockAddr": "2600:5c01:1e3b::",
        "blockName": "2600:5c01:1e3b::/48",
        "blockSize": "48",
        "blockStatus": "Deployed",
        "blockType": "RIP-DIA",
        "conckType": "RIP-DIA",
        "container": "/Commercial/LTWC/Midwest/Customer",
        "createDate": "2025-04-02 13:04:22",
        "createReverseDomains": "False",
        "description": "",
        "discoveryAgent": "InheritFromContainer",
        "excludeFromDiscovery": "False",
        "ipv6": True,
        "lastUpdateDate": "2025-04-02 13:04:22",
        "nonBroadcast": False,
        "primarySubnet": False,
        "userDefinedFields": [
            "Delete_Block=off",
            "Day=",
            "Month=",
            "Year=",
            "Midwest_Divisions=TW-MOH",
            "Company_Name=ABSOLUTELY THE WRONG CUSTOMER",
            "Account_Number=ACCT-LOL",
            "Notes=ENG-04962299\r\n51.L1XX.023560..CHTR\r\n8060 READING RD\r\nCINCINNATI\r\nOH\r\n45237",
            "Notes_2=",
            "Service_Type=Fiber",
        ],
    }


def verification_results_all_blocks_nonexistent(*args, **kwargs):
    return {
        "status": "all_blocks_nonexistent",
        "verified": [],
        "incorrect_information": [],
        "nonexistent": ["98.123.148.56/29", "2605:A000:0:8::F:D8CE/127"],
    }


def verification_results_ready(*args, **kwargs):
    return {
        "status": "ready",
        "verified": ["98.123.148.56/29", "2600:5c01:4a27::/48", "2600:5c01:4860:5::/64"],
        "incorrect_information": [],
        "nonexistent": [],
    }


def verification_results_ready_and_incorrect(*args, **kwargs):
    return {
        "status": "ready_and_incorrect",
        "verified": ["98.123.148.56/29"],
        "incorrect_information": [{"IP": "2605:A000:0:8::F:D8CE/127", "Customer Name": "ABSOLUTELY THE WRONG CUSTOMER"}],
        "nonexistent": [],
    }


def verification_results_ready_and_nonexistent(*args, **kwargs):
    return {
        "status": "ready_and_nonexistent",
        "verified": ["98.123.148.56/29"],
        "incorrect_information": [],
        "nonexistent": ["2605:A000:0:8::F:D8CE/127"],
    }


def mock_delete_block_success(*args, **kwargs):
    return {"message": "success"}


def mock_delete_block_error(*args, **kwargs):
    return {"error": "string"}


@pytest.mark.unittest
def test_verify_disconnect_info_for_ipc_ready(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_path_elements", mock_path_elements)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_blockname", mock_subnet_block)
    cid = "33.L1XX.006714..TWCC"
    subnets_in_cid = ["98.123.148.56/29", "2600:5c01:4a27::/48", None, "2600:5c01:4860:5::/64"]
    info = ip_reclamation.verify_disconnect_info_for_ipc(cid, subnets_in_cid)
    assert info == verification_results_ready()


@pytest.mark.unittest
def test_verify_disconnect_info_for_ipc_ready_and_nonexistent(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_path_elements", mock_path_elements)
    subnets = [mock_subnet_block(), mock_subnet_block_not_found()]
    mock_subnet_responses = mock.Mock(side_effect=subnets)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_blockname", mock_subnet_responses)
    cid = "33.L1XX.006714..TWCC"
    subnets_in_cid = ["98.123.148.56/29", "2605:A000:0:8::F:D8CE/127"]
    info = ip_reclamation.verify_disconnect_info_for_ipc(cid, subnets_in_cid)
    assert info == verification_results_ready_and_nonexistent()


@pytest.mark.unittest
def test_verify_disconnect_info_for_ipc_no_ips(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_path_elements", mock_path_elements)
    subnets = [None, None]
    mock_subnet_responses = mock.Mock(side_effect=subnets)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_blockname", mock_subnet_responses)
    cid = "33.L1XX.006714..TWCC"
    subnets_in_cid = [None, None]
    with pytest.raises(AbortException):
        ip_reclamation.verify_disconnect_info_for_ipc(cid, subnets_in_cid)


@pytest.mark.unittest
def test_verify_disconnect_info_for_ipc_all_blocks_nonexistent(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_path_elements", mock_path_elements)
    subnets = [mock_subnet_block_not_found(ip="98.123.148.56/29"), mock_subnet_block_not_found()]
    mock_subnet_responses = mock.Mock(side_effect=subnets)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_blockname", mock_subnet_responses)
    cid = "33.L1XX.006714..TWCC"
    subnets_in_cid = ["98.123.148.56/29", "2605:A000:0:8::F:D8CE/127"]
    info = ip_reclamation.verify_disconnect_info_for_ipc(cid, subnets_in_cid)
    assert info == verification_results_all_blocks_nonexistent()


@pytest.mark.unittest
def test_verify_disconnect_info_for_ipc_ready_and_incorrect(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_path_elements", mock_path_elements)
    subnets = [mock_subnet_block(), mock_subnet_block_customer_mismatch()]
    mock_subnet_responses = mock.Mock(side_effect=subnets)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_blockname", mock_subnet_responses)
    cid = "33.L1XX.006714..TWCC"
    subnets_in_cid = ["98.123.148.56/29", "2605:A000:0:8::F:D8CE/127"]
    info = ip_reclamation.verify_disconnect_info_for_ipc(cid, subnets_in_cid)
    assert info == verification_results_ready_and_incorrect()


@pytest.mark.unittest
def test_verify_disconnect_info_for_ipc_incorrect_none_verifed(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_path_elements", mock_path_elements)
    subnets = [mock_subnet_block_customer_mismatch()]
    mock_subnet_responses = mock.Mock(side_effect=subnets)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_blockname", mock_subnet_responses)
    cid = "33.L1XX.006714..TWCC"
    subnets_in_cid = ["2605:A000:0:8::F:D8CE/127"]
    with pytest.raises(AbortException):
        ip_reclamation.verify_disconnect_info_for_ipc(cid, subnets_in_cid)


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_all_blocks_nonexistent(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_all_blocks_nonexistent)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    assert message == {"message": "All of the subnet blocks for the circuit's IPs have already been removed."}


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_ready_success(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_subnet_block)
    monkeypatch.setattr(ip_reclamation, "delete_block", mock_delete_block_success)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    mock_success = ["98.123.148.56/29", "2600:5c01:4a27::/48", "2600:5c01:4860:5::/64"]
    mock_message = f"Subnet blocks removed from IPControl: {mock_success} "
    assert message == {"message": mock_message}


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_ready_and_incorrect_success(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready_and_incorrect)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_subnet_block)
    monkeypatch.setattr(ip_reclamation, "delete_block", mock_delete_block_success)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    mock_success = ["98.123.148.56/29"]
    mock_incorrect = [{"IP": "2605:A000:0:8::F:D8CE/127", "Customer Name": "ABSOLUTELY THE WRONG CUSTOMER"}]
    mock_message = f"Subnet blocks removed from IPControl: {mock_success}  |  IPs without matching Granite/IPControl customer names: {mock_incorrect}"  # noqa
    assert message == {"message": mock_message}


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_ready_and_nonexistent_success(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready_and_nonexistent)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_subnet_block)
    monkeypatch.setattr(ip_reclamation, "delete_block", mock_delete_block_success)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    mock_success = ["98.123.148.56/29"]
    mock_nonexistent = ["2605:A000:0:8::F:D8CE/127"]
    mock_message = f"Subnet blocks removed from IPControl: {mock_success}  |  IPs with nonexistent subnet blocks in IPControl: {mock_nonexistent}"  # noqa
    assert message == {"message": mock_message}


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_missing_subnet_and_removed_subnet(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready)
    ips = [mock_subnet_block(), mock_subnet_block_not_found(ip="2600:5c01:4a27::/48"), mock_subnet_block_not_found()]
    mock_ips = mock.Mock(side_effect=ips)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_ips)
    monkeypatch.setattr(ip_reclamation, "delete_block", mock_delete_block_success)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    mock_success = ["98.123.148.56/29"]
    mock_message = f"Subnet blocks removed from IPControl: {mock_success} "
    assert message == {"message": mock_message}


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_missing_subnets(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready)
    ips = [
        mock_subnet_block_not_found(ip="98.123.148.56/29"),
        mock_subnet_block_not_found(ip="2600:5c01:4a27::/48"),
        mock_subnet_block_not_found(),
    ]
    mock_ips = mock.Mock(side_effect=ips)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_ips)
    cid = "33.L1XX.006714..TWCC"
    with pytest.raises(AbortException):
        ip_reclamation.delete_ip_subnet_block_by_cid(cid)


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_failed_to_remove_and_removed_subnet(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_subnet_block)
    delete_responses = [mock_delete_block_success(), mock_delete_block_error(), mock_delete_block_error()]
    mock_deletes = mock.Mock(side_effect=delete_responses)
    monkeypatch.setattr(ip_reclamation, "delete_block", mock_deletes)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    removed_subnets = ["98.123.148.56/29"]
    failed_to_remove_subnets = [
        {"2600:5c01:4a27::/48": {"error": "string"}},
        {"2600:5c01:4860:5::/64": {"error": "string"}},
    ]
    mixed_message = f"Partial success.  Subnet blocks reclaimed: {removed_subnets} | \
Subnets unable to be removed: {failed_to_remove_subnets}"
    assert message == {"message": mixed_message}


@pytest.mark.unittest
def test_delete_ip_subnet_block_by_cid_removed_all_subnets(monkeypatch):
    monkeypatch.setattr(ip_reclamation, "get_vgw_data", lambda *arg: None)
    monkeypatch.setattr(ip_reclamation, "get_ip_subnets", mock_ip_subnets)
    monkeypatch.setattr(ip_reclamation, "verify_disconnect_info_for_ipc", verification_results_ready)
    monkeypatch.setattr(ip_reclamation, "get_subnet_block_by_ip", mock_subnet_block)
    delete_responses = [mock_delete_block_success(), mock_delete_block_success(), mock_delete_block_success()]
    mock_deletes = mock.Mock(side_effect=delete_responses)
    monkeypatch.setattr(ip_reclamation, "delete_block", mock_deletes)
    cid = "33.L1XX.006714..TWCC"
    message = ip_reclamation.delete_ip_subnet_block_by_cid(cid)
    removed_subnets = ["98.123.148.56/29", "2600:5c01:4a27::/48", "2600:5c01:4860:5::/64"]
    mock_message = f"Subnet blocks removed from IPControl: {removed_subnets} "
    assert message == {"message": mock_message}
