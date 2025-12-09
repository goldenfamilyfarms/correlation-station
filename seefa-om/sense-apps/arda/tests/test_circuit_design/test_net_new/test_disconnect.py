from copy import deepcopy

import pytest
from pytest import raises

from arda_app.bll import disconnect as dsco
from arda_app.bll import disconnect_utils as dscoutils
from arda_app.dll import blacklist as blkck
from arda_app.bll.disconnect_utils import get_db_data_for_cid, get_db_data_for_e_access, is_vgw_installer_needed
from arda_app.bll.models.payloads.disconnect import DisconnectPayloadModel
from arda_app.bll.utils import compare_ipv6_addresses
from arda_app.dll import mdso
from mock_data.circuit_design.net_new.vlan import data as vld
from tests.test_common import test_disconnect_globals as tdg
from common_sense.common.errors import AbortException


@pytest.mark.unittest
def test_blacklist_check(monkeypatch):
    ip_address = "50.75.87.154/30"
    get_ip_status_value = (False, None)
    result = {
        "blacklist_ip's": [],
        "blacklist_status": False,
        "blacklist_reason": None,
        "ip's_checked": ["50.75.87.152", "50.75.87.153", "50.75.87.154", "50.75.87.155"],
    }

    monkeypatch.setattr(blkck, "get_temp_auth_key", lambda *args, **kwargs: "temp_auth_key")
    monkeypatch.setattr(blkck, "get_ip_status", lambda *args, **kwargs: get_ip_status_value)
    assert dsco.is_blacklisted(ip_address) == result


@pytest.mark.unittest
def test_comparison_db_and_network_data(monkeypatch):
    result = True
    cid = "31.TGXX.000473..TWCC"
    product_name = "SIP - Trunk (Fiber)"
    devices = {"WTTWNYSR1ZW": "ACCESS-1-1-1-4", "WTTWNYCF1CW": "AE17", "WTTWNYCF0QW": "GE-0/0/3"}
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.NORTHEAST.MPLS",
            "ELEMENT_REFERENCE": "686665",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": "0",
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "4380",
            "CHAN_INST_ID": "7667975",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "31001.GE40L.WTTWNYCF1CW.WTTWNYCF0QW",
            "ELEMENT_REFERENCE": "1207156",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667974",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "31001.GE1.WTTWNYCF0QW.WTTWNYSR1ZW",
            "ELEMENT_REFERENCE": "1510495",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667973",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYSR1ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "1155097",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "CHASSIS PORTS",
            "PORT_NAME": "ACCESS PORT-1-1-1-4",
            "PORT_INST_ID": "105448475",
            "PORT_ACCESS_ID": "ACCESS-1-1-1-4",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYSR1ZW.CML.CHTRSE.COM",
            "MODEL": "FSP 150CC-GE114/114S",
            "VENDOR": "ADVA",
            "TID": "WTTWNYSR1ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.48.226/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1306",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "5.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "5",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYSRG01/999.9999.999.99/LSTG",
            "ELEMENT_REFERENCE": "1144437",
            "ELEMENT_CATEGORY": "LINE/ACCESS GATEWAY",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "1",
            "PORT_NAME": "WAN-01",
            "PORT_INST_ID": "105227163",
            "PORT_ACCESS_ID": "WAN-01",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYSRG01.NE.TWCBIZ.COM",
            "MODEL": "ESBC 9378-4B",
            "VENDOR": "INNOMEDIA",
            "TID": "WTTWNYSRG01",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "24.169.81.58/30",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "6.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "6",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYSRG01/999.9999.999.99/LSTG",
            "ELEMENT_REFERENCE": "1144437",
            "ELEMENT_CATEGORY": "LINE/ACCESS GATEWAY",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "1",
            "PORT_NAME": "LAN-02",
            "PORT_INST_ID": "105227156",
            "PORT_ACCESS_ID": "LAN-02",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYSRG01.NE.TWCBIZ.COM",
            "MODEL": "ESBC 9378-4B",
            "VENDOR": "INNOMEDIA",
            "TID": "WTTWNYSRG01",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "24.169.81.58/30",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1207156",
            "PATH_NAME": "31001.GE40L.WTTWNYCF1CW.WTTWNYCF0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYCF",
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
            "LEG_INST_ID": "1397824",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYCF1CW/000.0000.000.00/RTR",
            "ELEMENT_REFERENCE": "534722",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667974",
            "SLOT": "3/0",
            "PORT_NAME": "1",
            "PORT_INST_ID": "102122520",
            "PORT_ACCESS_ID": "ET-1/3/0",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYCF1CW.CHTRSE.COM",
            "MODEL": "MX480",
            "VENDOR": "JUNIPER",
            "TID": "WTTWNYCF1CW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "24.58.26.33/32",
            "IPV6_ADDRESS": "2604:6000::F:21/128",
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1207156",
            "PATH_NAME": "31001.GE40L.WTTWNYCF1CW.WTTWNYCF0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYCF",
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
            "LEG_INST_ID": "1397824",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYCF1CW/000.0000.000.00/RTR",
            "ELEMENT_REFERENCE": "534722",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667974",
            "SLOT": "3/0",
            "PORT_NAME": "1",
            "PORT_INST_ID": "102122515",
            "PORT_ACCESS_ID": "ET-3/3/0",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYCF1CW.CHTRSE.COM",
            "MODEL": "MX480",
            "VENDOR": "JUNIPER",
            "TID": "WTTWNYCF1CW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "24.58.26.33/32",
            "IPV6_ADDRESS": "2604:6000::F:21/128",
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1207156",
            "PATH_NAME": "31001.GE40L.WTTWNYCF1CW.WTTWNYCF0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYCF",
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
            "LEG_INST_ID": "1397824",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYCF0QW/001.0100.002.15/SWT#0",
            "ELEMENT_REFERENCE": "943241",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667974",
            "SLOT": "96",
            "PORT_NAME": "1",
            "PORT_INST_ID": "102122322",
            "PORT_ACCESS_ID": "ET-0/0/96",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYCF0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "WTTWNYCF0QW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.48.4/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1207156",
            "PATH_NAME": "31001.GE40L.WTTWNYCF1CW.WTTWNYCF0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYCF",
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
            "LEG_INST_ID": "1397824",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYCF0QW/001.0100.002.17/SWT#1",
            "ELEMENT_REFERENCE": "943247",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667974",
            "SLOT": "96",
            "PORT_NAME": "1",
            "PORT_INST_ID": "102122418",
            "PORT_ACCESS_ID": "ET-1/0/96",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYCF0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "WTTWNYCF0QW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.48.4/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1510495",
            "PATH_NAME": "31001.GE1.WTTWNYCF0QW.WTTWNYSR1ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "1721367",
            "A_SITE_NAME": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYCF0QW/001.0100.002.15/SWT#0",
            "ELEMENT_REFERENCE": "943241",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667973",
            "SLOT": "3",
            "PORT_NAME": "1",
            "PORT_INST_ID": "102167855",
            "PORT_ACCESS_ID": "GE-0/0/3",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYCF0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "WTTWNYCF0QW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.48.4/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1510495",
            "PATH_NAME": "31001.GE1.WTTWNYCF0QW.WTTWNYSR1ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "1721367",
            "A_SITE_NAME": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "WTTWNYSR1ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "1155097",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1306",
            "CHAN_INST_ID": "7667973",
            "SLOT": "1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "105448468",
            "PORT_ACCESS_ID": "NETWORK-1-1-1-1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "WTTWNYSR1ZW.CML.CHTRSE.COM",
            "MODEL": "FSP 150CC-GE114/114S",
            "VENDOR": "ADVA",
            "TID": "WTTWNYSR1ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.48.226/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "2",
        },
    ]
    zw = "WTTWNYSR1ZW"
    skip_cpe_check = False
    vgw_ipv4 = "24.169.81.58/30"
    db_dev_list = [
        {
            "tid": "WTTWNYCF1CW",
            "port_id": "AE17",
            "vendor": "JUNIPER",
            "vlan_id": "1306",
            "description": True,
            "model": "MX480",
            "ipv4": None,
            "ipv6": None,
        },
        {
            "tid": "WTTWNYCF0QW",
            "port_id": "GE-0/0/3",
            "vendor": "JUNIPER",
            "vlan_id": "1306",
            "description": True,
            "model": "QFX5100-96S",
        },
        {
            "tid": "WTTWNYSR1ZW",
            "port_id": "ACCESS-1-1-1-4",
            "vendor": "ADVA",
            "vlan_id": "1306",
            "description": True,
            "model": "FSP 150CC-GE114/114S",
        },
    ]

    get_network_data = [
        {
            "tid": "WTTWNYCF1CW",
            "vendor": "JUNIPER",
            "model": "MX480",
            "vlan_id": "1306",
            "port_id": "AE17",
            "description": True,
            "ipv4": "24.169.81.57/30",
        },
        {
            "tid": "WTTWNYCF0QW",
            "vendor": "JUNIPER",
            "model": "QFX5100-96S",
            "vlan_id": "1306",
            "port_id": "GE-0/0/3",
            "description": True,
        },
        {
            "tid": "WTTWNYSR1ZW",
            "vendor": "ADVA",
            "model": "FSP 150CC-GE114/114S",
            "vlan_id": "1306",
            "port_id": "ACCESS-1-1-1-4",
            "description": True,
        },
    ]

    inactive_devices = []
    ipv4_service_type = ""

    z_side_cpe_model = "fsp 150cc-ge114/114s"
    ipv4 = [None, "24.169.81.57/30"]
    iv4_service_type = ""
    ipv4_assigned_subnet = None
    ipv4_glue_subnet = None

    monkeypatch.setattr(
        dsco,
        "get_circuit_device_data_from_db",
        lambda *args, **kwargs: (db_dev_list, ipv4[0], ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet),
    )
    monkeypatch.setattr(dsco, "get_network_data", lambda *args, **kwargs: get_network_data)
    monkeypatch.setattr(dsco, "check_active_devices", lambda *args, **kwargs: inactive_devices)
    assert dsco.get_comparison_db_and_network_data(
        cid, product_name, devices, path_elements, zw, skip_cpe_check, vgw_ipv4
    ) == (result, z_side_cpe_model, ipv4[1], iv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet)


@pytest.mark.unittest
def test_sip_fiber(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect", product_name="SIP - Trunk (Fiber)", cid="31.TGXX.000473..TWCC"
    )

    response = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "ESBC 9378-4B",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "1508042",
        "engineering_job_type": "partial",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "No",
    }

    vgw_shelf_data = {
        "SHELF_NAME": "WTTWNYSRG01",
        "VENDOR": "INNOMEDIA",
        "MODEL": "ESBC 9378-4B",
        "CIRC_PATH_INST_ID": "1508042",
        "IPV4_ADDRESS": "24.169.81.58/30",
    }
    devices = {"WTTWNYSR1ZW": "ACCESS-1-1-1-4", "WTTWNYCF1CW": "AE17", "WTTWNYCF0QW": "GE-0/0/3"}
    zw = "WTTWNYSR1ZW"
    circ_path_inst_id = "1508042"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "1508042",
            "PATH_NAME": "31.TGXX.000473..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "WTTWNYCF-TWC/HUB WV-WATERTOWN (SYRCNYWTN)",
            "PATH_Z_SITE": "WTTWNYSR-WAITE MOTOR SALES INC//18406 US ROUTE 11",
            "A_CLLI": "WTTWNYCF",
            "Z_CLLI": "WTTWNYSR",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-00197630",
            "CUSTOMER_NAME": "WAITE MOTOR SALES INC",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1718760",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.NORTHEAST.MPLS",
            "ELEMENT_REFERENCE": "686665",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": "0",
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "4380",
            "CHAN_INST_ID": "7667975",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.TGXX.000473..TWCC",
            "INITIAL_CIRCUIT_ID": "1508042",
            "LVL": "1",
        }
    ]

    result = True
    z_side_cpe_model = "fsp 150cc-ge114/114s"
    ipv4 = "24.169.81.57/30"
    ipv4_service_type = None
    ipv4_assigned_subnet = None
    ipv4_glue_subnet = None

    hub_work_required = "Yes"
    cpe_installer_needed = "No"

    monkeypatch.setattr(dsco, "get_vgw_shelf_info", lambda *args, **kwargs: vgw_shelf_data)
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )

    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "partial")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (
            result,
            z_side_cpe_model,
            ipv4,
            ipv4_service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )

    monkeypatch.setattr(dsco, "full_disco_check", lambda *args, **kwargs: (hub_work_required, cpe_installer_needed))
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **__: {"blacklist_ip's": []})

    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_voice_hosted_fiber(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect", product_name="Hosted Voice - (Fiber)", cid="42.HNXN.000046..CHTR"
    )

    response = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "2326337",
        "engineering_job_type": "partial",
        "cpe_model": "M500",
        "hub_work_required": "No",
        "cpe_installer_needed": "Yes",
    }

    vgw_shelf_info = {
        "SHELF_NAME": "BCLKOHAG01W",
        "VENDOR": "AUDIOCODES",
        "MODEL": "M500",
        "CIRC_PATH_INST_ID": "2586920",
        "IPV4_ADDRESS": "DHCP",
    }
    devices = {"LSEHCA251ZW": "ETH PORT 4", "LSEHCA2501W": "WAN", "LSAICAEV2CW": "AE18", "LSAICAEV4QW": "GE-1/0/1"}
    zw = "LSEHCA251ZW"
    circ_path_inst_id = "2326337"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2326337",
            "PATH_NAME": "42.HNXN.000046..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "PATH_Z_SITE": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "A_CLLI": "LSAICAEV",
            "Z_CLLI": "LSEHCA25",
            "PATH_A_SITE_TYPE": "HEAD END",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-HOSTED",
            "BANDWIDTH": "5 Mbps",
            "BW_SIZE": "5000000",
            "CUSTOMER_ID": "ACCT-26819509",
            "CUSTOMER_NAME": "MATTIE MUSIC GROUP",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "76.53.81.192/30",
            "IPV4_ASSIGNED_GATEWAY": "76.53.81.193/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": "NONE",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "INTERNET",
            "LEG_INST_ID": "2659728",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.WEST.MPLS",
            "ELEMENT_REFERENCE": "602608",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "34617",
            "CHAN_INST_ID": "10667344",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "42.HNXN.000046..CHTR",
            "INITIAL_CIRCUIT_ID": "2326337",
            "LVL": "1",
        }
    ]

    result = True
    z_side_cpe_model = "FSP 150 114/114S"
    ipv4 = "76.53.81.193/30"
    ipv4_service_type = "LAN"
    ipv4_assigned_subnet = "76.53.81.192/30"
    ipv4_glue_subnet = None

    monkeypatch.setattr(dsco, "get_vgw_shelf_info", lambda *args, **kwargs: vgw_shelf_info)
    monkeypatch.setattr(dsco, "is_vgw_installer_needed", lambda *args, **kwargs: "Yes")
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "partial")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (
            result,
            z_side_cpe_model,
            ipv4,
            ipv4_service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **__: {"blacklist_ip's": []})
    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_voice_hosted_docsis(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect", product_name="Hosted Voice - (DOCSIS)", cid="74.HNXN.000267..CHTR"
    )

    response = {
        "networkcheck": {"passed": True},
        "circ_path_inst_id": "2586920",
        "engineering_job_type": "full",
        "cpe_model": "M500",
        "blacklist": {"passed": True, "ips": []},
        "hub_work_required": "No",
        "cpe_installer_needed": "Yes",
    }

    vgw_shelf_info = {
        "SHELF_NAME": "BCLKOHAG01W",
        "VENDOR": "AUDIOCODES",
        "MODEL": "M500",
        "CIRC_PATH_INST_ID": "2586920",
        "IPV4_ADDRESS": "DHCP",
    }

    devices = {}
    zw = ""
    circ_path_inst_id = "2586920"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2586920",
            "PATH_NAME": "74.HNXN.000267..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "BCLKOHAG-LICKING COUNTY//4455 WALNUT RD",
            "PATH_Z_SITE": "BCLKOHAG-LICKING COUNTY//4455 WALNUT RD",
            "A_CLLI": "BCLKOHAG",
            "Z_CLLI": "BCLKOHAG",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-HOSTED",
            "BANDWIDTH": "5 Mbps",
            "BW_SIZE": "5000000",
            "CUSTOMER_ID": "ACCT-28034392",
            "CUSTOMER_NAME": "LICKING COUNTY",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "3000708",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "LTWC.HFC.MID WEST.MPLS",
            "ELEMENT_REFERENCE": "650319",
            "ELEMENT_CATEGORY": "HFC CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "VPLS",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "739",
            "CHAN_INST_ID": "10893639",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "74.HNXN.000267..CHTR",
            "INITIAL_CIRCUIT_ID": "2586920",
            "LVL": "1",
        }
    ]

    monkeypatch.setattr(dsco, "get_vgw_shelf_info", lambda *args, **kwargs: vgw_shelf_info)
    monkeypatch.setattr(dsco, "is_vgw_installer_needed", lambda *args, **kwargs: "Yes")
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "full")
    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_voice_pri_docsis(monkeypatch):
    param = DisconnectPayloadModel(
        cid="31.IPXN.000993..CHTR", service_type="disconnect", product_name="PRI Trunk (DOCSIS)"
    )
    response = {
        "networkcheck": {"passed": True},
        "circ_path_inst_id": "2424714",
        "engineering_job_type": "full",
        "cpe_model": "M500",
        "blacklist": {"passed": True, "ips": []},
        "hub_work_required": "No",
        "cpe_installer_needed": "Yes",
    }
    vgw_shelf_info = {
        "SHELF_NAME": "ELSGCADBG1W",
        "VENDOR": "AUDIOCODES",
        "MODEL": "M500",
        "CIRC_PATH_INST_ID": "2424714",
        "IPV4_ADDRESS": "DHCP",
    }
    devices = {}
    zw = ""
    circ_path_inst_id = "2424714"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2424714",
            "PATH_NAME": "31.IPXN.000993..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "PRI TRUNKS",
            "PATH_A_SITE": "ELSGCADB-LAN AIRLINES SA/303/2101 E EL SEGUNDO BLVD",
            "PATH_Z_SITE": "ELSGCADB-LAN AIRLINES SA/303/2101 E EL SEGUNDO BLVD",
            "A_CLLI": "ELSGCADB",
            "Z_CLLI": "ELSGCADB",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-PRI",
            "BANDWIDTH": "10 Mbps",
            "BW_SIZE": "10000000",
            "CUSTOMER_ID": "ACCT-27444569",
            "CUSTOMER_NAME": "STARLUX AIRLINES CO., LTD.",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2786760",
            "A_SITE_NAME": "ELSGCADB-LAN AIRLINES SA/303/2101 E EL SEGUNDO BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "ELSGCADBG1W/999.9999.999.99/RTR",
            "ELEMENT_REFERENCE": "1724441",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED ETHERNET PORTS",
            "PORT_NAME": "WAN",
            "PORT_INST_ID": "114617031",
            "PORT_ACCESS_ID": "WAN",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": "DYNAMIC",
            "FQDN": "ELSGCADBG1W.CML.CHTRSE.COM",
            "MODEL": "M500",
            "VENDOR": "AUDIOCODES",
            "TID": "ELSGCADBG1W",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "DHCP",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.IPXN.000993..CHTR",
            "INITIAL_CIRCUIT_ID": "2424714",
            "LVL": "1",
        }
    ]
    monkeypatch.setattr(dsco, "get_vgw_shelf_info", lambda *args, **kwargs: vgw_shelf_info)
    monkeypatch.setattr(dsco, "is_vgw_installer_needed", lambda *args, **kwargs: "Yes")
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "full")
    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_get_circuit_device_data_from_db():
    # get_circuit_device_data_from_db_mocked
    payload = {
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/21",
        "BFLONYJZ3AW": "ETH PORT 0/5",
        "BFLONYJZ1ZW": "ACCESS PORT-1-1-1-4",
    }
    response = [
        {
            "tid": "BFLONYKK1CW",
            "vendor": "JUNIPER",
            "model": "MX960",
            "vlan_id": "1153",
            "ipv4": "208.125.204.185/30",
            "ipv6": "2604:6000:0:8::F:80B8/127",
            "port_id": "AE17",
            "description": True,
        },
        {
            "tid": "BFLONYKK0QW",
            "vendor": "JUNIPER",
            "model": "QFX5100-96S",
            "vlan_id": "1153",
            "port_id": "XE-0/0/21",
            "description": True,
        },
        {
            "tid": "BFLONYJZ3AW",
            "vendor": "RAD",
            "vlan_id": "1153",
            "port_id": "ETH PORT 0/5",
            "description": True,
            "model": "ETX-2I-10G/4SFPP/4SFP4UTP",
        },
        {
            "tid": "BFLONYJZ1ZW",
            "vendor": "ADVA",
            "vlan_id": "1153",
            "port_id": "ACCESS PORT-1-1-1-4",
            "description": True,
            "model": "FSP 150CC-GE114/114S",
        },
    ]
    assert (
        response,
        "208.125.204.185/30",
        vld.granite_l1_cid_data[1].get("IPV4_SERVICE_TYPE"),
        vld.granite_l1_cid_data[1].get("IPV4_ASSIGNED_SUBNETS"),
        vld.granite_l1_cid_data[1].get("IPV4_GLUE_SUBNET"),
    ) == dsco.get_circuit_device_data_from_db("71.L1XX.910595..CHTR", payload, vld.granite_cid_data)

    # get_circuit_device_data_from_db_missing_cid
    with raises(Exception):
        assert dsco.get_circuit_device_data_from_db("", payload, vld.granite_cid_data) is None

    # get_circuit_device_data_from_db_missing_payload
    with raises(Exception):
        assert dsco.get_circuit_device_data_from_db("71.L1XX.910595..CHTR", None, vld.granite_cid_data) is None

    # get_circuit_device_data_from_db_missing_input
    with raises(Exception):
        assert dsco.get_circuit_device_data_from_db(None, {}, vld.granite_cid_data) is None


@pytest.mark.unittest
def test_get_circuit_tid_ports(monkeypatch):
    cid = "71.L1XX.910595..CHTR"
    product = "Fiber Internet Access"
    expected = {
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/21",
        "BFLONYJZ3AW": "ETH PORT 0/5",
        "BFLONYJZ1ZW": "ACCESS-1-1-1-4",
    }
    monkeypatch.setattr(dsco, "get_path_elements", lambda *_: vld.granite_cid_data)
    monkeypatch.setattr(dsco, "get_granite", lambda _: vld.get_granite_paths)

    response, _, _, _ = dsco.get_circuit_tid_ports(cid, product)
    assert response == expected


@pytest.mark.unittest
def test_get_circuit_tid_ports_evpl(monkeypatch):
    cid = "40.L1XX.005155..CHTR"
    product = "EVPL (Fiber)"
    get_granite_data = [
        {
            "aSideCustomer": "ACCT-01692242",
            "aSideSiteName": "DLLSTX97-TWC/COLO-EQUINIX-DA2:02:002220 DALLAS (NBB) (ENT) (DFW10)",
            "bandwidth": "10 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-01692242",
            "orderNumber": "COM-EVPL-00001376,ENG-03509217",
            "pathId": "40.L1XX.005155..CHTR",
            "pathInService": "2023-03-28 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "COM-EVPL",
            "servicePriority": "YES",
            "status": "Live",
            "topology": "P",
            "tspAuthorizationCode_UDA": "TSP0L6P48-02",
            "tspChildPresent_UDA": "NO",
            "tspExpirationDate_UDA": "25-FEB-2026",
            "zSideCustomer": "ACCT-01692242",
        }
    ]
    path_elements_data = [
        {
            "CIRC_PATH_INST_ID": "2405753",
            "PATH_NAME": "40.L1XX.005155..CHTR",
            "ELEMENT_CATEGORY": "ROUTER",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "DLLSTX976CW",
            "PORT_ROLE": "UNI-EVP",
            "PORT_ACCESS_ID": "GE-0/2/1",
            "A_SITE_NAME": "DLLSTX97-TWC/COLO-EQUINIX-DA2:02:002220 DALLAS (NBB) (ENT) (DFW10)",
            "LEG_NAME": "1",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2405753",
            "PATH_NAME": "40.L1XX.005155..CHTR",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "None",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "None",
            "A_SITE_NAME": "DLLSTX97-TWC/COLO-EQUINIX-DA2:02:002220 DALLAS (NBB) (ENT) (DFW10)",
            "LEG_NAME": "1",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2405753",
            "PATH_NAME": "40.L1XX.005155..CHTR",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "None",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "None",
            "A_SITE_NAME": "None",
            "LEG_NAME": "1",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2405753",
            "PATH_NAME": "40.L1XX.005155..CHTR",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "None",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "None",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "1",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2405753",
            "PATH_NAME": "40.L1XX.005155..CHTR",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "None",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "None",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "1",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2405753",
            "PATH_NAME": "40.L1XX.005155..CHTR",
            "ELEMENT_CATEGORY": "NIU",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "BUMUTXCZ1ZW",
            "PORT_ROLE": "UNI-EP",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "A_SITE_NAME": "BUMUTXCZ-HARRIS CORPORATION//5040 AIRLINE DR",
            "LEG_NAME": "1",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2190772",
            "PATH_NAME": "91001.GE1.DLLSTX976CW.DLLSTX976CW",
            "ELEMENT_CATEGORY": "ROUTER",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "DLLSTX976CW",
            "PORT_ROLE": "UNI-EVP",
            "PORT_ACCESS_ID": "GE-0/2/1",
            "A_SITE_NAME": "DLLSTX97-TWC/COLO-EQUINIX-DA2:02:002220 DALLAS (NBB) (ENT) (DFW10)",
            "LEG_NAME": "1",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "2190772",
            "PATH_NAME": "91001.GE1.DLLSTX976CW.DLLSTX976CW",
            "ELEMENT_CATEGORY": "FDP",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "None",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "PORT 17 TX",
            "A_SITE_NAME": "DLLSTX97-TWC/COLO-EQUINIX-DA2:02:002220 DALLAS (NBB) (ENT) (DFW10)",
            "LEG_NAME": "1",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "2190772",
            "PATH_NAME": "91001.GE1.DLLSTX976CW.DLLSTX976CW",
            "ELEMENT_CATEGORY": "FDP",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "None",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "PORT 18 RX",
            "A_SITE_NAME": "DLLSTX97-TWC/COLO-EQUINIX-DA2:02:002220 DALLAS (NBB) (ENT) (DFW10)",
            "LEG_NAME": "1",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1701341",
            "PATH_NAME": "40001.GE10L.NDLDTX051CW.NDLDTX050QW",
            "ELEMENT_CATEGORY": "ROUTER",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "NDLDTX051CW",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "XE-0/3/1",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "AE17/AE17 10G",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1701341",
            "PATH_NAME": "40001.GE10L.NDLDTX051CW.NDLDTX050QW",
            "ELEMENT_CATEGORY": "ROUTER",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "NDLDTX051CW",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "XE-3/3/1",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "AE17/AE17 10G",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1701341",
            "PATH_NAME": "40001.GE10L.NDLDTX051CW.NDLDTX050QW",
            "ELEMENT_CATEGORY": "SWITCH",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "NDLDTX050QW",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "XE-0/0/95",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "AE17/AE17 10G",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "1701341",
            "PATH_NAME": "40001.GE10L.NDLDTX051CW.NDLDTX050QW",
            "ELEMENT_CATEGORY": "SWITCH",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "NDLDTX050QW",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "XE-1/0/95",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "AE17/AE17 10G",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "2429667",
            "PATH_NAME": "40001.GE1.NDLDTX050QW.BUMUTXCZ1ZW",
            "ELEMENT_CATEGORY": "SWITCH",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "NDLDTX050QW",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "GE-0/0/61",
            "A_SITE_NAME": "NDLDTX05-TWC/HUB 2-NEDERLAND",
            "LEG_NAME": "1",
            "LVL": "2",
        },
        {
            "CIRC_PATH_INST_ID": "2429667",
            "PATH_NAME": "40001.GE1.NDLDTX050QW.BUMUTXCZ1ZW",
            "ELEMENT_CATEGORY": "NIU",
            "PATH_STATUS": "Live",
            "ELEMENT_STATUS": "Live",
            "TID": "BUMUTXCZ1ZW",
            "PORT_ROLE": "None",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "A_SITE_NAME": "BUMUTXCZ-HARRIS CORPORATION//5040 AIRLINE DR",
            "LEG_NAME": "1",
            "LVL": "2",
        },
    ]
    devices = {"BUMUTXCZ1ZW": "ETH PORT 3", "DLLSTX976CW": "GE-0/2/1", "NDLDTX051CW": "AE17", "NDLDTX050QW": "GE-0/0/61"}
    zw_device = "BUMUTXCZ1ZW"
    circ_path_inst_id = "2405753"

    monkeypatch.setattr(dsco, "get_path_elements", lambda *_: path_elements_data)
    monkeypatch.setattr(dsco, "get_granite", lambda _: get_granite_data)
    response_device, response_zw, response_inst_id, response_path_elements = dsco.get_circuit_tid_ports(cid, product)
    assert response_device == devices
    assert response_zw == zw_device
    assert response_inst_id == circ_path_inst_id
    assert response_path_elements == path_elements_data


@pytest.mark.unittest
def test_get_db_data_for_e_access():
    assert vld.granite_l1_e_access[-1:][0].get("LVL") == "1"
    assert vld.granite_l2_e_access[-1:][0].get("LVL") == "2"
    expected_evc_id = vld.granite_l1_e_access[0].get("EVC_ID")
    expected_router_connection_ips = {"DLLATX371CW": "24.73.241.25", "MCKNTXWF1CW": "67.79.252.145"}
    evc_id, router_connection_ips = get_db_data_for_e_access(vld.granite_l1_e_access, vld.granite_l2_e_access)

    assert evc_id == expected_evc_id
    assert router_connection_ips == expected_router_connection_ips


@pytest.mark.unittest
def test_get_db_data_for_cid():
    cid = "97.L1XX.001936..TWCC"
    expected_ordered_dev_list = [
        ["DLLATX371CW", "XE-3/0/2"],
        ["MCKNTXWF1CW", "AE17"],
        ["MCKNTXWF0QW", "XE-0/0/75"],
        ["MCKYTXUH2AW", "GE-0/0/4"],
        ["MCKYTXUH5ZW", "ETH PORT 5"],
    ]
    expected_vlan_id = "3030"
    expected_ipv4 = None
    expected_ipv4_service_type = None
    expected_ipv6 = None
    expected_service_type = "CAR-E-ACCESS FIBER/FIBER EPL"

    expected_ipv4_assigned_subnet = None
    expected_ipv4_glue_subnet = None
    (
        ordered_dev_list,
        vlan_id,
        ipv4,
        ipv4_service_type,
        ipv6,
        granite_l1_data,
        granite_l2_data,
        service_type,
        ipv4_assigned_subnet,
        ipv4_glue_subnet,
    ) = get_db_data_for_cid(cid, tdg.devices, vld.granite_path_elements_e_access)
    assert ordered_dev_list == expected_ordered_dev_list
    assert vlan_id == expected_vlan_id
    assert ipv4 == expected_ipv4
    assert ipv4_service_type == expected_ipv4_service_type
    assert ipv6 == expected_ipv6
    assert granite_l1_data == vld.granite_l1_e_access
    assert granite_l2_data == vld.granite_l2_e_access
    assert service_type == expected_service_type
    assert ipv4_assigned_subnet == expected_ipv4_assigned_subnet
    assert ipv4_glue_subnet == expected_ipv4_glue_subnet


@pytest.mark.unittest
def test_compare_network_and_granite():
    # compare_network_and_granite_with_no_mismatch
    network_dev_list = [
        tdg.juniper_paired_router1_network_data,
        tdg.juniper_paired_router2_network_data,
        tdg.juniper_qw_network_data,
        tdg.juniper_aw_network_data,
        tdg.rad_zw_network_data,
    ]
    assert dsco.compare_network_and_granite(tdg.db_dev_list, network_dev_list) is True

    # compare_network_and_granite_with_mismatches
    juniper_paired_router1_network_data = {
        "tid": "DLLATX371CW",
        "vendor": "JUNIPER",
        "model": "MX480",
        "vlan_id": "3030",
        "port_id": "XE-3/0/2",
        "description": True,
        "e_access_ip": "24.73.241.25",
        "evc_id": "407294",
    }
    juniper_paired_router1_network_data["vendor"] = "JUPITER"
    juniper_paired_router1_network_data["e_access_ip"] = "127.0.0.1"
    juniper_paired_router1_network_data["evc_id"] = None
    juniper_paired_router2_network_data = {
        "tid": "MCKNTXWF1CW",
        "vendor": "JUNIPER",
        "model": "MX480",
        "vlan_id": "3030",
        "port_id": "AE17",
        "description": True,
        "e_access_ip": "67.79.252.145",
        "evc_id": "407294",
    }
    juniper_paired_router2_network_data["model"] = "MX490"
    juniper_paired_router2_network_data["vlan_id"] = "3031"
    juniper_paired_router2_network_data["port_id"] = "A&E17"
    juniper_qw_network_data = {
        "tid": "MCKNTXWF0QW",
        "vendor": "JUNIPER",
        "model": "QFX5100-96S",
        "vlan_id": "3030",
        "port_id": "XE-0/0/75",
        "description": True,
    }
    juniper_qw_network_data["description"] = False
    juniper_aw_network_data = {
        "tid": "MCKYTXUH2AW",
        "vendor": "JUNIPER",
        "model": "EX4200-24F",
        "vlan_id": "3030",
        "port_id": "GE-0/0/4",
        "description": True,
    }
    juniper_aw_network_data["port_id"] = "XE-0/0/4"
    rad_zw_network_data = {
        "tid": "MCKYTXUH5ZW",
        "vendor": "RAD",
        "model": "ETX203AX/2SFP/2UTP2SFP",
        "vlan_id": "3030",
        "port_id": "ETH PORT 5",
        "description": True,
    }
    rad_zw_network_data["vendor"] = "ADVA"
    network_dev_list = [
        juniper_paired_router1_network_data,
        juniper_paired_router2_network_data,
        juniper_qw_network_data,
        juniper_aw_network_data,
        rad_zw_network_data,
    ]

    response = dsco.compare_network_and_granite(tdg.db_dev_list, network_dev_list)
    assert len(tdg.db_dev_list) == len(network_dev_list)
    assert response.get("Granite Data")
    assert response.get("Network Data")
    assert response.get("Granite Data") != response.get("Network Data")


@pytest.mark.unittest
def test_get_aw_device():
    tid = "BFLONYJZ3AW"
    db_dev_list = [
        {
            "tid": "BFLONYKK1CW",
            "port_id": "AE17",
            "vendor": "JUNIPER",
            "vlan_id": "1153",
            "description": True,
            "ipv4": "208.125.204.185/30",
            "ipv6": "2604:6000:0:8::F:80B8/127",
        },
        {"tid": "BFLONYKK0QW", "port_id": "XE-0/0/21", "vendor": "JUNIPER", "vlan_id": "1153", "description": True},
        {
            "tid": "BFLONYJZ3AW",
            "port_id": "ETH PORT 0/5",
            "vendor": "RAD",
            "vlan_id": "1153",
            "description": True,
            "model": "ETX-2I-10G/4SFPP/4SFP4UTP",
        },
        {
            "tid": "BFLONYJZ1ZW",
            "port_id": "ACCESS-1-1-1-4",
            "vendor": "ADVA",
            "vlan_id": "1153",
            "description": True,
            "model": "FSP 150CC-GE114/114S",
        },
    ]
    expected_aw_device = {
        "tid": "BFLONYJZ3AW",
        "port_id": "ETH PORT 0/5",
        "vendor": "RAD",
        "vlan_id": "1153",
        "description": True,
        "model": "ETX-2I-10G/4SFPP/4SFP4UTP",
    }
    assert [expected_aw_device] == dsco.get_aw_device(tid, db_dev_list)


@pytest.mark.unittest
def test_get_zw_device():
    tid = "MCKYTXUH5ZW"
    expected_zw_device = {
        "tid": "MCKYTXUH5ZW",
        "port_id": "ETH PORT 5",
        "vendor": "RAD",
        "vlan_id": "3030",
        "description": True,
        "model": "ETX203AX/2SFP/2UTP2SFP",
    }
    assert [expected_zw_device] == dsco.get_zw_device(tid, tdg.db_dev_list)


@pytest.mark.unittest
def test_disconnect_with_fia(monkeypatch):
    devices = {
        "BFLONYKK0QW": "XE-0/0/21",
        "BFLONYKK1CW": "AE17",
        "BFLONYJZ1ZW": "ACCESS-1-1-1-4",
        "BFLONYJZ3AW": "ETH PORT 0/5",
    }
    monkeypatch.setattr(
        dsco,
        "get_circuit_tid_ports",
        lambda *args: (devices, "BFLONYJZ1ZW", vld.granite_cid_data[0]["CIRC_PATH_INST_ID"], vld.granite_cid_data),
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "partial")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (True, "fsp 150cc-gE114/114S", "208.125.204.185/30", "LAN", None, None),
    )
    param = DisconnectPayloadModel(
        cid="71.L1XX.910595..CHTR", service_type="disconnect", product_name="Carrier E-Access (Fiber)"
    )
    expected = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "fsp 150cc-gE114/114S",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "1831957",
        "engineering_job_type": "partial",
        "hub_work_required": "No",
        "cpe_installer_needed": "No",
    }
    assert dsco.disconnect(param) == expected


@pytest.mark.unittest
def test_disconnect_cisco_fia(monkeypatch):
    devices = {"HTSPSDAJ1ZW": "ACCESS-1-1-1-3", "CHCGILDT5CW": "TE0/1/0/2"}
    monkeypatch.setattr(
        dsco,
        "get_circuit_tid_ports",
        lambda *args: (
            devices,
            "HTSPSDAJ1ZW",
            vld.granite_cid_data_disconnect[0]["CIRC_PATH_INST_ID"],
            vld.granite_cid_data_disconnect,
        ),
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "full")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (True, "fsp 150-ge114pro-c", "35.134.133.25/29", "LAN", None, None),
    )
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **kwargs: {"blacklist_ip's": []})
    param = DisconnectPayloadModel(
        cid="60.L1XX.993969..CHTR", service_type="disconnect", product_name="Fiber Internet Access"
    )
    expected = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "fsp 150-ge114pro-c",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "1978708",
        "engineering_job_type": "full",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "No",
    }
    assert dsco.disconnect(param) == expected


@pytest.mark.unittest
def test_disconnect_with_e_access_full_disconnect_unsupported(monkeypatch):
    payload = {"service_type": "disconnect", "product_name": "Carrier E-Access (Fiber)", "cid": "97.L1XX.001936..TWCC"}
    ipv4 = ""
    ipv4_service_type = vld.granite_path_elements_e_access[1].get("IPV4_SERVICE_TYPE")
    zw = tdg.rad_zw_network_data.get("tid")
    ipv4_assigned_subnet = None
    ipv4_glue_subnet = None

    monkeypatch.setattr(
        dsco,
        "get_circuit_tid_ports",
        lambda *args: (
            tdg.devices,
            zw,
            vld.granite_path_elements_e_access[0]["CIRC_PATH_INST_ID"],
            vld.granite_path_elements_e_access,
        ),
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: ("partial"))
    monkeypatch.setattr(
        dsco,
        "get_circuit_device_data_from_db",
        lambda *args, **kwargs: (tdg.db_dev_list, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet),
    )
    responses_get = iter(
        [
            tdg.juniper_paired_router1_network_data,
            tdg.juniper_paired_router2_network_data,
            tdg.juniper_qw_network_data,
            tdg.juniper_aw_network_data,
            tdg.rad_zw_network_data,
        ]
    )
    monkeypatch.setattr(dsco, "get_juniper_network_configuration_e_access", lambda *_: next(responses_get))
    monkeypatch.setattr(dsco, "get_juniper_network_configuration", lambda *_: next(responses_get))
    monkeypatch.setattr(dsco, "get_rad_network_configs", lambda *_: next(responses_get))
    monkeypatch.setattr(dsco, "get_adva_network_configs", lambda *_: next(responses_get))
    monkeypatch.setattr(dsco, "check_active_devices", lambda *_: [])
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **__: {"blacklist_ip's": []})
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (
            True,
            "z_side_cpe_model",
            ipv4,
            ipv4_service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )
    param = DisconnectPayloadModel(
        cid=payload.get("cid"), service_type=payload.get("service_type"), product_name=payload.get("product_name")
    )

    try:
        dsco.disconnect(param)
    except AbortException as e:
        assert e.code == 500


@pytest.mark.unittest
def test_disconnect_with_e_access_full_disconnect(monkeypatch):
    devices = {
        "MCKYTXUH5ZW": "ETH PORT 5",
        "DLLATX371CW": "XE-3/0/2",
        "MCKNTXWF1CW": "AE17",
        "MCKNTXWF0QW": "XE-0/0/75",
        "MCKYTXUH2AW": "GE-0/0/4",
    }
    monkeypatch.setattr(
        dsco,
        "get_circuit_tid_ports",
        lambda *args: (devices, "MCKYTXUH5ZW", "1978604", vld.granite_path_elements_e_access),
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "partial")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (True, "etx203ax/2sfp/2utp2sfp", None, None, None, None),
    )
    monkeypatch.setattr(
        dsco, "get_circuit_device_data_from_db", lambda *args, **kwargs: (tdg.db_dev_list, None, None, None, None)
    )
    param = DisconnectPayloadModel(
        cid="97.L1XX.001936..TWCC", service_type="disconnect", product_name="Carrier E-Access (Fiber)"
    )
    expected = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "etx203ax/2sfp/2utp2sfp",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "1978604",
        "engineering_job_type": "partial",
        "hub_work_required": "No",
        "cpe_installer_needed": "No",
    }
    assert dsco.disconnect(param) == expected


@pytest.mark.unittest
def test_full_disco_check():
    # full_disco_check_no_match
    hub_work_required, cpe_installer_needed = dsco.full_disco_check("full", [{"PATH_Z_SITE_TYPE": "Local"}], "None")
    assert hub_work_required == "Yes"
    assert cpe_installer_needed == "No"

    # full_disco_check_match
    hub_work_required, cpe_installer_needed = dsco.full_disco_check(
        "full", [{"PATH_Z_SITE_TYPE": "Active MTU"}], "ADVA FSP 150-XG404"
    )
    assert hub_work_required == "No"
    assert cpe_installer_needed == "Yes"


@pytest.mark.unittest
def test_filter_devices():
    devices = [
        {"vendor": "JUNIPER", "model": "MX480"},
        {"vendor": "CISCO", "model": ""},
        {"vendor": "ADVA", "model": "MUX"},
        {"vendor": "GENERIC", "model": ""},
        {"vendor": "GENERIC", "model": "MUX"},
        {"vendor": "CISCO", "model": ""},
    ]
    result = dsco.filter_devices(devices)
    assert len(result) == 3


@pytest.mark.unittest
def test_check_vendor():
    db_dev_list = [
        {"vendor": "JUNIPER"},
        {"vendor": "CISCO"},
        {"vendor": "ADVA"},
        {"vendor": "RAD"},
        {"vendor": "UNKNOWNVENDOR"},
        {"vendor": ""},
    ]

    try:
        dsco.check_vendor(db_dev_list)
    except AbortException as e:
        assert "Unsupported Vendor" in e.data["message"]


@pytest.mark.unittest
def test_skip_CPE_check(monkeypatch):
    db_dev_elements = iter([None, None, {"id": "MCKNTXWF0QW"}, None, {"id": "MCKYTXUH5ZW"}])
    resource_result = iter(["MCKNTXWF0QW", "MCKYTXUH5ZW"])
    device_payload = iter(
        {
            "MCKNTXWF0QW": {"FQDN_RESOLVES": True, "PING_CHECK": {"IP": "FAKE_IP"}},
            "MCKYTXUH5ZW": {"FQDN_RESOLVES": True, "PING_CHECK": {"IP": "FAKE_IP"}},
        }
    )

    monkeypatch.setattr(mdso, "create_onboard_payload", lambda *_: None)
    monkeypatch.setattr(mdso, "mdso_post", lambda *_: None)

    monkeypatch.setattr(mdso, "get_device_fqdn", lambda *_: None)
    monkeypatch.setattr(mdso, "_check_device", lambda *_: None)
    monkeypatch.setattr(mdso, "verify_device_connectivity", lambda *_: next(device_payload))
    monkeypatch.setattr(mdso, "_get_network_device", lambda *_: next(db_dev_elements))
    monkeypatch.setattr(dsco, "get_resource_result", lambda *_, tries: next(resource_result))

    skip_cpe_check = True
    inactive_devices = dsco.check_active_devices(tdg.db_dev_list, skip_cpe_check)
    assert len(inactive_devices) == 3


@pytest.mark.unittest
def test_compare_ipv6_addresses():
    # ipv6_comparison_true
    ipv6_first = "FE80:0:0:0:903A:1C1A:E802:11E4"
    ipv6_second = "FE80:0:0:0:903A:1C1A:E802:11E4"
    result = compare_ipv6_addresses(ipv6_first, ipv6_second)
    assert result is True

    # ipv6_comparison_type_true
    ipv6_first = "fcef:b0e7:7d20::3b95:565"
    ipv6_second = "fcef:b0e7:7d20:0000:0000:0000:3b95:0565"
    result = compare_ipv6_addresses(ipv6_first, ipv6_second)
    assert result is True

    # ipv6_comparison_false
    ipv6_first = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    ipv6_second = "2001:0db8:85a3:0000:0000:8a2e:0370:7333"
    result = compare_ipv6_addresses(ipv6_first, ipv6_second)
    assert result is False

    # ipv6_comparison_None_false
    ipv6_first = None
    ipv6_second = "FE80::903A:1C1A:E802:11E4"
    result = compare_ipv6_addresses(ipv6_first, ipv6_second)
    assert result is False


@pytest.mark.unittest
def test_get_cisco_network_configuration(monkeypatch):
    cid = "60.L1XX.993969..CHTR"
    ipv4_service_type = "LAN"
    circ_path_inst_id = "1978708"
    expected = {
        "tid": "CHCGILDT5CW",
        "vendor": "CISCO",
        "model": "ASR 9010",
        "vlan_id": "11002:OV-553//IV-1101",
        "port_id": "TE0/1/0/2",
        "description": True,
        "ipv6": "2600:6C3A::48/127",
        "ipv4": "35.134.133.25/29",
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.device_config)
    cisco_device = dsco.get_cisco_network_configuration(tdg.device_info, cid, circ_path_inst_id, ipv4_service_type)
    assert cisco_device == expected


@pytest.mark.unittest
def test_get_cisco_network_configuration_vlan_id_mismatch(monkeypatch):
    cid = "60.L1XX.993969..CHTR"
    ipv4_service_type = "LAN"
    circ_path_inst_id = "1978708"
    device_info1 = tdg.device_info.copy()
    device_info1["vlan_id"] = "mismatch"
    expected = {
        "tid": "CHCGILDT5CW",
        "vendor": "",
        "model": "",
        "vlan_id": "mismatch",
        "port_id": "",
        "description": None,
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.device_config)
    cisco_device = dsco.get_cisco_network_configuration(device_info1, cid, circ_path_inst_id, ipv4_service_type)
    assert cisco_device == expected


@pytest.mark.unittest
def test_get_cisco_network_configuration_routed(monkeypatch):
    cid = "60.L1XX.993969..CHTR"
    ipv4_service_type = "ROUTED"
    circ_path_inst_id = "1978708"
    expected = {
        "tid": "CHCGILDT5CW",
        "vendor": "CISCO",
        "model": "ASR 9010",
        "vlan_id": "11002:OV-553//IV-1101",
        "port_id": "TE0/1/0/2",
        "description": True,
        "ipv6": "2600:6C3A::48/127",
        "ipv4": "35.134.133.25/29",
        "IPV4_ASSIGNED_SUBNETS": None,
        "IPV4_GLUE_SUBNET": None,
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.device_config)
    cisco_device = dsco.get_cisco_network_configuration(tdg.device_info, cid, circ_path_inst_id, ipv4_service_type)
    assert cisco_device == expected


@pytest.mark.unittest
def test_get_cisco_network_configuration_e_access(monkeypatch):
    device_info = {
        "tid": "ATLNGAMQ4CW",
        "port_id": "TE0/0/0/8",
        "vendor": "CISCO",
        "vlan_id": "2282",
        "description": True,
        "model": "ASR 9010",
        "evc_id": "100426956",
        "e_access_ip": "96.34.246.2",
    }
    cid = "47.L1XX.800167..CHTR"
    circ_path_inst_id = "2477675"
    ipv4_service_type = "LAN"
    cisco_data1 = {
        "command": "seefa-l2vpn-xconnect.json",
        "parameters": {"interface": "TE0/0/0/8.2282"},
        "result": {"evcid": "100426956"},
    }
    cisco_data2 = {
        "command": "seefa-cd-show-interface-config.json",
        "parameters": {"interface": "TE0/0/0/8.2282"},
        "result": [
            {
                "interface": "TenGigE0/0/0/8.2282 l2transport",
                "description": "chc00135680,chc00426956,l3,l2epl,acr05sghlga_0/1/0/7.2282,50m",
            }
        ],
    }
    network_data = iter([cisco_data1, cisco_data2])
    expected = {
        "tid": "ATLNGAMQ4CW",
        "vendor": "CISCO",
        "model": "ASR 9010",
        "vlan_id": "2282",
        "port_id": "TE0/0/0/8",
        "description": True,
        "evc_id": "100426956",
        "e_access_ip": "96.34.246.2",
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: next(network_data))
    monkeypatch.setattr(dsco, "uda_legacy_id_matches_cid", lambda *args, **kwargs: True)
    assert (
        dsco.get_cisco_network_configuration_e_access(device_info, cid, circ_path_inst_id, ipv4_service_type) == expected
    )


@pytest.mark.unittest
def test_get_cisco_network_configuration_e_access_unpaired_router(monkeypatch):
    device_info = {
        "tid": "ATLNGAMQ4CW",
        "port_id": "TE0/0/0/8",
        "vendor": "CISCO",
        "vlan_id": "2282",
        "description": True,
        "model": "ASR 9010",
        "ipv4": "35.134.133.25/29",
        "ipv6": "2600:6C3A::48/127",
    }
    cid = "47.L1XX.800167..CHTR"
    circ_path_inst_id = "2477675"
    ipv4_service_type = "LAN"

    expected = {
        "tid": "ATLNGAMQ4CW",
        "vendor": "CISCO",
        "model": "ASR 9010",
        "vlan_id": "2282",
        "port_id": "TE0/0/0/8",
        "description": True,
        "ipv4": "35.134.133.25/29",
        "ipv6": "2600:6C3A::48/127",
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.device_config4)
    monkeypatch.setattr(dsco, "uda_legacy_id_matches_cid", lambda *args, **kwargs: True)
    assert (
        dsco.get_cisco_network_configuration_e_access(device_info, cid, circ_path_inst_id, ipv4_service_type) == expected
    )


@pytest.mark.unittest
def test_get_cisco_network_configuration_e_access_missing_router_info():
    device_info = {
        "tid": "ATLNGAMQ4CW",
        "port_id": "TE0/0/0/8",
        "vendor": "CISCO",
        "vlan_id": "2282",
        "description": True,
        "model": "ASR 9010",
        "ipv6": "2600:6C3A::48/127",
    }
    cid = "47.L1XX.800167..CHTR"
    circ_path_inst_id = "2477675"
    ipv4_service_type = "LAN"
    expected = {"tid": "ATLNGAMQ4CW", "vendor": "", "model": "", "vlan_id": "", "port_id": "", "description": None}
    assert (
        dsco.get_cisco_network_configuration_e_access(device_info, cid, circ_path_inst_id, ipv4_service_type) == expected
    )


@pytest.mark.unittest
def test_get_cisco_network_configuration_e_access_non_router():
    device_info = {
        "tid": "ATLNGAMQ4AW",
        "port_id": "TE0/0/0/8",
        "vendor": "CISCO",
        "vlan_id": "2282",
        "description": True,
        "model": "ASR 9010",
        "ipv4": "35.134.133.25/29",
        "ipv6": "2600:6C3A::48/127",
    }
    cid = "47.L1XX.800167..CHTR"
    circ_path_inst_id = "2477675"
    ipv4_service_type = "LAN"
    expected = {"tid": "ATLNGAMQ4AW", "vendor": "", "model": "", "vlan_id": "", "port_id": "", "description": None}
    assert (
        dsco.get_cisco_network_configuration_e_access(device_info, cid, circ_path_inst_id, ipv4_service_type) == expected
    )


@pytest.mark.unittest
def test_get_cisco_network_configuration_e_access_missing_port_id():
    device_info = {
        "tid": "ATLNGAMQ4CW",
        "port_id": "",
        "vendor": "CISCO",
        "vlan_id": "2282",
        "description": True,
        "model": "ASR 9010",
        "ipv4": "35.134.133.25/29",
        "ipv6": "2600:6C3A::48/127",
    }
    cid = "47.L1XX.800167..CHTR"
    circ_path_inst_id = "2477675"
    ipv4_service_type = "LAN"
    expected = {"tid": "ATLNGAMQ4CW", "vendor": "", "model": "", "vlan_id": "", "port_id": "", "description": None}
    assert (
        dsco.get_cisco_network_configuration_e_access(device_info, cid, circ_path_inst_id, ipv4_service_type) == expected
    )


@pytest.mark.unittest
def test_get_juniper_network_configuration_elan_cw(monkeypatch):
    device_info = {
        "tid": "MNTVALAP1CW",
        "port_id": "AE18",
        "vendor": "JUNIPER",
        "vlan_id": "1228",
        "description": True,
        "model": "MX960",
        "evc_id": "454706",
        "encapsulation": "vlan-vpls",
    }
    cid = "20.L1XX.902572..TWCC"
    expected = {
        "tid": "MNTVALAP1CW",
        "vendor": "JUNIPER",
        "model": "MX960",
        "vlan_id": "1228",
        "port_id": "AE18",
        "description": True,
        "encapsulation": "vlan-vpls",
        "evc_id": "454706",
    }
    network_data = iter([tdg.juniper_data1, tdg.juniper_data2])
    network_association_id = [
        {
            "networkInstId": "1663821",
            "networkHumId": "CHTRSE.VRFID.454706.CHC00427069.CITY OF CALERA",
            "networkRevNbr": "1",
            "networkStatus": "Live",
            "assocInstId": "156914",
            "associationName": "EVC ID NUMBER/NETWORK",
            "associationType": "NETWORK TO EVC ID",
            "associationValue": "454706",
            "associationObjectType": "Number",
            "numberRangeName": "MANUAL ASSIGNMENT RETAIL/CARRIER RANGE 0055",
        }
    ]
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: tdg.path_elements)
    monkeypatch.setattr(dsco, "get_network_association", lambda *_: network_association_id)
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: next(network_data))
    assert dsco.get_juniper_network_configuration_elan(device_info, tdg.db_dev_list, cid) == expected


@pytest.mark.unittest
def test_get_juniper_network_configuration_elan_qw(monkeypatch):
    expected = {
        "tid": "MNTVALAP1QW",
        "vendor": "JUNIPER",
        "model": "QFX5100-96S",
        "vlan_id": "1228",
        "port_id": "GE-0/0/18",
        "description": True,
    }
    cid = "20.L1XX.902572..TWCC"
    device_info = {
        "tid": "MNTVALAP1QW",
        "port_id": "GE-0/0/18",
        "vendor": "JUNIPER",
        "vlan_id": "1228",
        "description": True,
        "model": "QFX5100-96S",
    }
    device_config = {
        "command": "get-interface-config.json",
        "parameters": {"name": "ge-0/0/18"},
        "result": {
            "configuration": {
                "interfaces": {
                    "ge-0/0/18": {
                        "name": "ge-0/0/18",
                        "apply-groups": "SERVICEPORT",
                        "description": "20001.GE1.MNTVALAP1QW.CALRAL771ZW:CPE:CALRAL771ZW:TE0/0/5:DHCP",
                        "unit": [
                            {
                                "name": "0",
                                "family": {"ethernet-switching": {"vlan": {"members": ["ELAN1228", "CHTR-CPE-MGMT"]}}},
                            }
                        ],
                    }
                }
            }
        },
    }
    device_config2 = {
        "command": "get-vlanidentifier-full.json",
        "parameters": {},
        "result": {
            "CHTR-CPE-MGMT": {
                "name": "CHTR-CPE-MGMT",
                "description": "MGMT::L-CHTR CPE Management::",
                "vlan-id": "1000",
            },
            "ELAN1225": {
                "name": "ELAN1225",
                "description": "CUST:ELAN:HPT SUNBELT PORTFOLIO LLC@31 INVERNESS CENTER PKWY:20.L1XX.002309..TWCC:",
                "vlan-id": "1225",
            },
            "ELAN1228": {
                "name": "ELAN1228",
                "description": "CUST:ELAN:CITY OF CALERA - FIRE ST@360 GEORGE ROY PKWY:20.L1XX.902572..TWCC:",
                "vlan-id": "1228",
            },
            "VOICE921": {
                "name": "VOICE921",
                "description": "CUST:VOICE:JOHNSON STERLING, INC.@820 SHADES CREEK PKWY:20.IPXN.003281..CHTR:",
                "vlan-id": "921",
            },
        },
    }
    device_data = iter([device_config, device_config2])
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: next(device_data))
    assert dsco.get_juniper_network_configuration_elan(device_info, tdg.db_dev_list, cid) == expected


@pytest.mark.unittest
def test_get_juniper_elan_vpls_cw(monkeypatch):
    expected = {
        "tid": "MNTVALAP1CW",
        "vendor": "JUNIPER",
        "model": "MX960",
        "vlan_id": "1228",
        "port_id": "AE18",
        "description": True,
        "encapsulation": "vlan-vpls",
        "evc_id": "454706",
    }
    cid = "20.L1XX.902572..TWCC"
    device_info = {
        "tid": "MNTVALAP1CW",
        "port_id": "AE18",
        "vendor": "JUNIPER",
        "vlan_id": "1228",
        "description": True,
        "model": "MX960",
        "evc_id": "454706",
        "encapsulation": "vlan-vpls",
    }
    device_config = iter([tdg.device_config1, tdg.device_config2])
    network_association_id = [
        {
            "networkInstId": "1663821",
            "networkHumId": "CHTRSE.VRFID.454706.CHC00427069.CITY OF CALERA",
            "networkRevNbr": "1",
            "networkStatus": "Live",
            "assocInstId": "156914",
            "associationName": "EVC ID NUMBER/NETWORK",
            "associationType": "NETWORK TO EVC ID",
            "associationValue": "454706",
            "associationObjectType": "Number",
            "numberRangeName": "MANUAL ASSIGNMENT RETAIL/CARRIER RANGE 0055",
        }
    ]
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: tdg.path_elements)
    monkeypatch.setattr(dsco, "get_network_association", lambda *_: network_association_id)
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: next(device_config))
    assert dsco.get_juniper_network_configuration_elan(device_info, tdg.db_dev_list, cid) == expected


@pytest.mark.unittest
def test_get_juniper_network_configuration_elan_premature_return(monkeypatch):
    device_info = {
        "tid": "MNTVALAP1CW",
        "port_id": "AE18",
        "vendor": "JUNIPER",
        "vlan_id": "1228",
        "description": True,
        "model": "MX960",
        "evc_id": "454706",
        "encapsulation": "vlan-vpls",
    }
    juniper_dev = {
        "tid": "MNTVALAP1CW",
        "vendor": "",
        "model": "",
        "vlan_id": "1228",
        "port_id": "",
        "description": False,
    }
    cid = "20.L1XX.902572..TWCC"
    path_elements = [
        {
            "EVC_ID": "454706",
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_REFERENCE": "1663821",
            "ELEMENT_CATEGORY": "VPLS SVC",
        },
        {
            "EVC_ID": "454706",
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_REFERENCE": "1307124",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
        },
    ]

    # invalid element category value
    invalid_element_category = deepcopy(path_elements)
    invalid_element_category[0]["ELEMENT_CATEGORY"] = "VPLS SVE"
    evc_id_error = deepcopy(juniper_dev)
    evc_id_error["evc_id"] = ""
    evc_id_error["Error"] = "Can't find correct path element to process"
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: invalid_element_category)
    assert dsco.get_juniper_network_configuration_elan(device_info, "granite_data", cid) == evc_id_error

    # missing port id
    missing_port_id = deepcopy(device_info)
    del missing_port_id["port_id"]
    assert dsco.get_juniper_network_configuration_elan(missing_port_id, "granite_data", cid) == juniper_dev

    # network association id mismatch with evc id
    net_assoc = deepcopy(tdg.network_associations)
    net_assoc[0]["associationValue"] = "fake_id"
    mismatch_id = deepcopy(juniper_dev)
    mismatch_id["evc_id"] = ""
    mismatch_id["Error"] = "Granite network associate ID fake_id did not match Granite EVC ID 454706"
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: path_elements)
    monkeypatch.setattr(dsco, "get_network_association", lambda *args, **kwargs: net_assoc)
    assert dsco.get_juniper_network_configuration_elan(device_info, "granite_data", cid) == mismatch_id

    # network association id unavailable
    net_assoc = deepcopy(tdg.network_associations)[0]
    mismatch_id = deepcopy(juniper_dev)
    mismatch_id["evc_id"] = ""
    mismatch_id["Error"] = "Granite network association ID is not available"
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: path_elements)
    monkeypatch.setattr(dsco, "get_network_association", lambda *args, **kwargs: net_assoc)
    assert dsco.get_juniper_network_configuration_elan(device_info, "granite_data", cid) == mismatch_id

    # missing element reference
    missing_element_reference = deepcopy(path_elements)
    missing_element_reference[0]["ELEMENT_REFERENCE"] = ""
    with_evc_id = deepcopy(juniper_dev)
    with_evc_id["evc_id"] = ""
    with_evc_id["Error"] = "Granite network instance ID is unavailable"
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: missing_element_reference)
    assert dsco.get_juniper_network_configuration_elan(device_info, "granite_data", cid) == with_evc_id

    # fail encapsulation check
    net_assoc = deepcopy(tdg.network_associations)
    net_assoc[0]["associationValue"] = "454706"
    device_profile = deepcopy(juniper_dev)
    device_profile["Error"] = "EVC ID 454706 was not found in the config route target of MNTVALAP1CW:AE18.1228"
    monkeypatch.setattr(dsco, "get_path_elements", lambda *args, **kwargs: path_elements)
    monkeypatch.setattr(dsco, "get_network_association", lambda *args, **kwargs: net_assoc)
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.show_interfaces)
    resp = dsco.get_juniper_network_configuration_elan(device_info, "granite_data", cid)
    assert resp["Error"] == device_profile["Error"]


@pytest.mark.unittest
def test_uda_legacy_id_matches_cid(monkeypatch):
    # no circ_path_inst_id
    with pytest.raises(Exception):
        assert dsco.uda_legacy_id_matches_cid(None, "device_desc") is None

    # no circuit_uda_info
    monkeypatch.setattr(dsco, "get_circuit_uda_info", lambda *args: None)
    assert dsco.uda_legacy_id_matches_cid("circ_path_inst_id", "device_desc") is False

    # no "ATTR_NAME" == "L-ID"
    monkeypatch.setattr(dsco, "get_circuit_uda_info", lambda *args: [{"ATTR_NAME": "test"}])
    assert dsco.uda_legacy_id_matches_cid("circ_path_inst_id", "device_desc") is False

    # "ATTR_NAME" == "L-ID"
    monkeypatch.setattr(
        dsco, "get_circuit_uda_info", lambda *args: [{"ATTR_NAME": "L-ID", "ATTR_VALUE": "CHC00246523,CHC00246525"}]
    )
    assert dsco.uda_legacy_id_matches_cid("circ_path_inst_id", "CHC00246523") is True


@pytest.mark.unittest
def test_path_match():
    assert dscoutils._path_match("cid", "zw", "CHTR") is True
    assert dscoutils._path_match("cid", "zw", "pathname") is False


@pytest.mark.unittest
def test_get_job_type(monkeypatch):
    # yes vc_class
    monkeypatch.setattr(
        dscoutils,
        "get_circuit_site_info",
        lambda *args, **kwargs: [
            {"CIRC_PATH_INST_ID": "123", "CIRCUIT_STATUS": "Pending Decommission", "Z_SITE_NAME": "test_site"}
        ],
    )
    monkeypatch.setattr(dscoutils, "get_circuit_uda_info", lambda *args, **kwargs: [{"ATTR_VALUE": "TYPE 2"}])

    with pytest.raises(Exception):
        assert dsco.get_job_type("cid", "zw") is None

    # no vc_class and no zw
    monkeypatch.setattr(dscoutils, "get_circuit_uda_info", lambda *args, **kwargs: [{"ATTR_VALUE": "TYPE 1"}])

    with pytest.raises(Exception):
        assert dsco.get_job_type("cid", None) is None

    # full
    monkeypatch.setattr(
        dscoutils,
        "get_used_equipment_ports",
        lambda _: [{"CURRENT_PATH_NAME": "CURRENT_PATH_NAME", "Z_SITE_NAME": "test_site"}],
    )
    monkeypatch.setattr(dscoutils, "_path_match", lambda *args: True)
    assert dsco.get_job_type("cid", "zw") == "full"

    # partial
    monkeypatch.setattr(
        dscoutils,
        "get_circuit_site_info",
        lambda *args, **kwargs: [{"CIRC_PATH_INST_ID": "123", "CIRCUIT_STATUS": None, "Z_SITE_NAME": "test_site"}],
    )
    assert dsco.get_job_type("cid", "zw") == "partial"


@pytest.mark.unittest
def test_get_comparison_db_and_network_data(monkeypatch):
    monkeypatch.setattr(
        dsco,
        "get_circuit_device_data_from_db",
        lambda *args, **kwargs: ("db_dev_list", "ipv4", "ipv4_service_type", "ipv4_assigned_subnet", "ipv4_glue_subnet"),
    )
    monkeypatch.setattr(dsco, "filter_devices", lambda *args: [])
    monkeypatch.setattr(dsco, "check_vendor", lambda *args: None)
    monkeypatch.setattr(dsco, "check_active_devices", lambda *args: "inactive_devices")
    monkeypatch.setattr(dsco, "get_z_side_cpe", lambda *args: {"model": "model"})
    monkeypatch.setattr(dsco, "get_network_data", lambda *args: "network_dev_list")
    monkeypatch.setattr(dsco, "compare_network_and_granite", lambda *args, **kwargs: "result")
    assert dsco.get_comparison_db_and_network_data("cid", "product_name", "devices", "path_elements", "zw", False) == (
        "result",
        "model",
        "ipv4",
        "ipv4_service_type",
        "ipv4_assigned_subnet",
        "ipv4_glue_subnet",
    )


@pytest.mark.unittest
def test_get_z_side_cpe():
    assert dsco.get_z_side_cpe([{"tid": "zw"}], "zw") == {"tid": "zw"}


@pytest.mark.unittest
def test_get_network_data(monkeypatch):
    # Juniper and Carrier E-Access (Fiber)
    monkeypatch.setattr(dsco, "get_circuit_path_inst_id", lambda _: "circ_path_inst_id")
    monkeypatch.setattr(dsco, "get_juniper_network_configuration", lambda *args: "network_data")
    monkeypatch.setattr(dsco, "get_juniper_network_configuration_e_access", lambda *args: "e_access")
    db_dev_list = [{"vendor": "JUNIPER", "tid": "AW"}, {"vendor": "JUNIPER", "tid": "AA"}]
    assert dsco.get_network_data(db_dev_list, "cid", "Carrier E-Access (Fiber)", "ipv4_service_type") == [
        "network_data",
        "e_access",
    ]

    # Juniper and EP-LAN (Fiber)
    monkeypatch.setattr(dsco, "get_juniper_network_configuration_elan", lambda *args: "elan")
    assert dsco.get_network_data(db_dev_list, "cid", "EP-LAN (Fiber)", "ipv4_service_type") == ["elan", "elan"]

    # Juniper
    assert dsco.get_network_data(db_dev_list, "cid", "test", "ipv4_service_type") == ["network_data", "network_data"]

    # Cisco and Carrier E-Access (Fiber)
    db_dev_list[0]["vendor"] = "CISCO"
    db_dev_list[1]["vendor"] = "CISCO"
    db_dev_list[0]["model"] = "ASR 9010"
    db_dev_list[1]["model"] = "ASR 9006"
    monkeypatch.setattr(dsco, "get_cisco_network_configuration_e_access", lambda *args: "e_access")
    assert dsco.get_network_data(db_dev_list, "cid", "Carrier E-Access (Fiber)", "ipv4_service_type") == [
        "e_access",
        "e_access",
    ]

    # Cisco
    monkeypatch.setattr(dsco, "get_cisco_network_configuration", lambda *args: "cisco")
    assert dsco.get_network_data(db_dev_list, "cid", "test", "ipv4_service_type") == ["cisco", "cisco"]
    del (db_dev_list[0]["model"], db_dev_list[1]["model"])

    # Adva or Rad
    db_dev_list[0]["vendor"] = "ADVA"
    db_dev_list[1]["vendor"] = "RAD"
    monkeypatch.setattr(dsco, "get_adva_network_configs", lambda *args: "ADVA")
    monkeypatch.setattr(dsco, "get_rad_network_configs", lambda *args: "RAD")
    assert dsco.get_network_data(db_dev_list, "cid", "test", "ipv4_service_type") == ["ADVA", "RAD"]


@pytest.mark.unittest
def test_get_adva_network_configs(monkeypatch):
    # GE114Pro
    zw_devices = [{"tid": "MNTVALAP1AW"}]
    monkeypatch.setattr(dsco, "get_zw_device", lambda *args: zw_devices)
    network_resp = {
        "result": [
            {
                "properties": {
                    "epAccessFlowEVCName": "cid",
                    "epAccessFlowAccessInterface": "epAccessFlowAccessInterface",
                },
                "flow_point": [{"properties": {"interface": "", "alias": "cid"}}],
                "eth": [{"properties": {"name": "1", "alias": "MNTVALAP1AW"}}],
            }
        ]
    }
    device_info = {"properties": {"type": "GE114Pro"}}
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: network_resp)
    monkeypatch.setattr(dsco, "_get_network_device", lambda *args, **kwargs: device_info)
    device = {"tid": "MNTVALAP1AW", "model": "114", "vendor": "vendor", "vlan_id": "vlan_id", "port_id": "port_id"}
    result = {
        "description": True,
        "model": "FSP 150-GE114PRO-C",
        "port_id": "EPACCESSFLOWACCESSINTERFACE",
        "tid": "MNTVALAP1AW",
        "vendor": "vendor",
        "vlan_id": "vlan_id",
    }
    assert dsco.get_adva_network_configs(device, "device_list", "cid") == result

    # different model, different MDSO command
    device["model"] = "116"
    assert dsco.get_adva_network_configs(device, "device_list", "cid") == result

    # GE114
    device_info = {"properties": {"type": "GE114"}}
    result["model"] = "FSP 150CC-GE114/114S"
    assert dsco.get_adva_network_configs(device, "device_list", "cid") == result

    # XG116PRO
    device_info = {"properties": {"type": "XG116PRO"}}
    result["model"] = "FSP150CC-XG116PRO"
    result["description"] = False
    result["port_id"] = ""
    assert dsco.get_adva_network_configs(device, "device_list", "cid") == result

    # XG120PRO
    device_info = {"properties": {"type": "XG120PRO"}}
    network_resp["result"][0]["flow_point"][0]["properties"]["interface"] = "eth_port-1-1-1-7"
    network_resp["result"][0]["eth"][0]["properties"]["name"] = "eth_port-1-1-1-7"
    result["model"] = "FSP 150-XG120PRO"
    result["description"] = True
    result["port_id"] = "ETH_PORT-1-1-1-7"
    assert dsco.get_adva_network_configs(device, "device_list", "cid") == result

    # Exception
    device.pop("vendor")

    with pytest.raises(Exception):
        assert dsco.get_adva_network_configs(device, "device_list", "cid") is None


def _exception():
    raise Exception


@pytest.mark.unittest
def test_get_juniper_network_configuration_e_access(monkeypatch):
    # no port_id
    device_infoj = tdg.device_info.copy()
    device_infoj["port_id"] = None
    res = {
        "description": True,
        "model": "",
        "port_id": "",
        "tid": "CHCGILDT5CW",
        "vendor": "",
        "vlan_id": "11002:OV-553//IV-1101",
    }
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") == res

    # paired_router = True KeyError
    device_infoj["port_id"] = "TE0/1/0/2"
    device_infoj["evc_id"] = "1234"
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.device_config2)
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") == res

    # paired_router = True
    res2 = {
        "tid": "CHCGILDT5CW",
        "vendor": "JUNIPER",
        "model": "ASR 9010",
        "vlan_id": "11002:OV-553//IV-1101",
        "port_id": "TE0/1/0/2",
        "description": True,
        "e_access_ip": "",
        "evc_id": "1234",
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: tdg.device_config3)
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") == res2

    # paired_router = False singleton router
    device_infoj.pop("evc_id")
    monkeypatch.setattr(dsco, "get_juniper_network_configuration", lambda *args, **kwargs: None)
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") is None

    # paired_router = False
    device_infoj["tid"] = "CHCGILDT5ZW"
    res2["tid"] = "CHCGILDT5ZW"
    res2["model"] = ""
    res2["description"] = True
    res2["vendor"] = ""
    res2["port_id"] = ""
    res2.pop("e_access_ip")
    res2.pop("evc_id")
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") == res2

    # paired_router = False is_cpe
    device_infoj.pop("ipv4")
    device_infoj["tid"] = "CHCGILDT5ZW"
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") is None

    # onboard error
    device_infoj["evc_id"] = "407294"
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: _exception())
    res2["Error"] = "Device communication: get-l2-circuits-full"
    assert dsco.get_juniper_network_configuration_e_access(device_infoj, "granite_data", "cid") == res2


@pytest.mark.unittest
def test_is_vgw_installer_needed():
    audiocodes_truckroll_model = "M500"
    audiocodes_not_truckroll_model = "M3000B"
    assert is_vgw_installer_needed(audiocodes_truckroll_model) == "Yes"
    assert is_vgw_installer_needed(audiocodes_not_truckroll_model) == "No"


@pytest.mark.unittest
def test_juniper_acx_disconnect(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect", product_name="Fiber Internet Access", cid="60.L1XX.003937..CHTR"
    )

    response = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "etx203ax/2sfp/2utp2sfp",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "2292543",
        "engineering_job_type": "full",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "Yes",
    }

    devices = {"MDSPWIUY4ZW": "ETH PORT 3", "SNPRWIEV1CW": "AE19", "SNPRWIEV2QW": "XE-0/0/22"}
    zw = "MDSPWIUY4ZW"
    circ_path_inst_id = "2292543"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": None,
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": None,
        },
    ]
    ipv4 = "47.225.245.205/30"
    ipv4_service_type = "LAN"
    ipv4_assigned_subnet = "47.225.245.204/30"
    ipv4_glue_subnet = None
    ipv4 = "47.225.245.205/30"
    ipv4_service_type = "LAN"
    ipv4_assigned_subnet = "76.53.81.192/30"
    ipv4_glue_subnet = None
    inactive_devices = []
    ordered_dev_list = [["SNPRWIEV1CW", "AE19"], ["SNPRWIEV2QW", "XE-0/0/22"], ["MDSPWIUY4ZW", "ETH PORT 3"]]
    ipv6 = "2600:6C08::2156/127"
    granite_l1_data = [
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.CENTRAL STATES.MPLS",
            "ELEMENT_REFERENCE": "1175885",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "7420",
            "CHAN_INST_ID": "10176697",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "ELEMENT_REFERENCE": "2478356",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "ELEMENT_REFERENCE": "2547166",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": "2296975",
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MDSPWIUY4ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1639619",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED PORTS",
            "PORT_NAME": "USER 3",
            "PORT_INST_ID": "113440454",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MDSPWIUY4ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "MDSPWIUY4ZW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": None,
        },
    ]
    granite_l2_data = [
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV1CW/01.001.011.01/RTR",
            "ELEMENT_REFERENCE": "923171",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "3/1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101704251",
            "PORT_ACCESS_ID": "ET-1/3/1",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV1CW/01.001.011.01/RTR",
            "ELEMENT_REFERENCE": "923171",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "3/1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101704261",
            "PORT_ACCESS_ID": "ET-10/3/1",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "48",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115029149",
            "PORT_ACCESS_ID": "ET-0/1/0",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "49",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115029150",
            "PORT_ACCESS_ID": "ET-0/1/1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "2946916",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": "22",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115556718",
            "PORT_ACCESS_ID": "XE-0/0/22",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "2946916",
            "A_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MDSPWIUY4ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1639619",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": "NET 1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "113440451",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MDSPWIUY4ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "MDSPWIUY4ZW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": None,
        },
    ]
    service_type = "COM-DIA"
    vlan_id = "1154"
    network_data = iter(
        [
            {
                "tid": "SNPRWIEV1CW",
                "vendor": "JUNIPER",
                "model": "MX960",
                "vlan_id": "1154",
                "port_id": "AE19",
                "description": True,
                "ipv4": "47.225.245.205/30",
                "ipv6": "2600:6C08::2156/127",
            },
            {
                "tid": "SNPRWIEV2QW",
                "vendor": "JUNIPER",
                "model": "ACX5448",
                "vlan_id": "1154",
                "port_id": "XE-0/0/22",
                "description": True,
            },
        ]
    )
    network_data_rad = {
        "tid": "MDSPWIUY4ZW",
        "vendor": "RAD",
        "model": "ETX203AX/2SFP/2UTP2SFP",
        "vlan_id": "1154",
        "port_id": "ETH PORT 3",
        "description": True,
    }

    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "full")
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(
        dscoutils,
        "get_db_data_for_cid",
        lambda *args, **kwargs: (
            ordered_dev_list,
            vlan_id,
            ipv4,
            ipv4_service_type,
            ipv6,
            granite_l1_data,
            granite_l2_data,
            service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )
    monkeypatch.setattr(dsco, "check_active_devices", lambda *args, **kwargs: inactive_devices)
    monkeypatch.setattr(dsco, "get_circuit_path_inst_id", lambda _: circ_path_inst_id)
    monkeypatch.setattr(dsco, "get_juniper_network_configuration", lambda *args: next(network_data))
    monkeypatch.setattr(dsco, "get_rad_network_configs", lambda *args: network_data_rad)
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **__: {"blacklist_ip's": []})
    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_rad_203acx_disconnect(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect", product_name="Fiber Internet Access", cid="60.L1XX.003937..CHTR"
    )

    response = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "etx203ax/2sfp/2utp2sfp",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "2292543",
        "engineering_job_type": "full",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "Yes",
    }

    devices = {"MDSPWIUY4ZW": "ETH PORT 3", "SNPRWIEV1CW": "AE19", "SNPRWIEV2QW": "XE-0/0/22"}
    zw = "MDSPWIUY4ZW"
    circ_path_inst_id = "2292543"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.CENTRAL STATES.MPLS",
            "ELEMENT_REFERENCE": "1175885",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "7420",
            "CHAN_INST_ID": "10176697",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "ELEMENT_REFERENCE": "2478356",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "ELEMENT_REFERENCE": "2547166",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": "2296975",
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MDSPWIUY4ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1639619",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED PORTS",
            "PORT_NAME": "USER 3",
            "PORT_INST_ID": "113440454",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MDSPWIUY4ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "MDSPWIUY4ZW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV1CW/01.001.011.01/RTR",
            "ELEMENT_REFERENCE": "923171",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "3/1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101704251",
            "PORT_ACCESS_ID": "ET-1/3/1",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV1CW/01.001.011.01/RTR",
            "ELEMENT_REFERENCE": "923171",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "3/1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101704261",
            "PORT_ACCESS_ID": "ET-10/3/1",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "48",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115029149",
            "PORT_ACCESS_ID": "ET-0/1/0",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "49",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115029150",
            "PORT_ACCESS_ID": "ET-0/1/1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "2946916",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": "22",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115556718",
            "PORT_ACCESS_ID": "XE-0/0/22",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "2946916",
            "A_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MDSPWIUY4ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1639619",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": "NET 1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "113440451",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MDSPWIUY4ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "MDSPWIUY4ZW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": None,
        },
    ]
    result = True
    z_side_cpe_model = "etx203ax/2sfp/2utp2sfp"
    ipv4 = "47.225.245.205/30"
    ipv4_service_type = ("LAN",)
    ipv4_assigned_subnet = "47.225.245.204/30"
    ipv4_glue_subnet = None
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "full")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (
            result,
            z_side_cpe_model,
            ipv4,
            ipv4_service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **__: {"blacklist_ip's": []})
    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_cisco_asr_920_disconnect(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect", product_name="Fiber Internet Access", cid="67.L1XX.800134..TWCC"
    )

    response = {
        "networkcheck": {
            "passed": False,
            "granite": [{"tid": "STBRGADP1CW", "evc_id": "421669", "encapsulation": "vlan-vpls"}],
            "network": [{"tid": "STBRGADP1CW"}],
        },
        "cpe_model": "asr-920-4sz-a",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "1557536",
        "engineering_job_type": "full",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "No",
    }
    devices = {"MCDNGA931ZW": "GI0/0/0", "STBRGADP1CW": "AE17", "STBRGADP0QW": "GE-1/0/20"}
    zw = "MCDNGA931ZW"
    circ_path_inst_id = "1557536"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "1557536",
            "PATH_NAME": "67.L1XX.800134..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "421669",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "HENRY COUNTY GOVERNMENT",
            "CUSTOMER_NAME": "HENRY COUNTY GOVERNMENT",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770874",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_NAME": "CHTRSE.VRFID.421669.HENRY COUNTY GOVERNMENT CHC00018547",
            "ELEMENT_REFERENCE": "1556285",
            "ELEMENT_CATEGORY": "VPLS SVC",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "VPLS",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "1557536",
            "PATH_NAME": "67.L1XX.800134..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "421669",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "HENRY COUNTY GOVERNMENT",
            "CUSTOMER_NAME": "HENRY COUNTY GOVERNMENT",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770874",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "LEGACY_CHARTER.GEORGIA.MPLS",
            "ELEMENT_REFERENCE": "1222313",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "873",
            "CHAN_INST_ID": "7862059",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "1557536",
            "PATH_NAME": "67.L1XX.800134..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "421669",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "HENRY COUNTY GOVERNMENT",
            "CUSTOMER_NAME": "HENRY COUNTY GOVERNMENT",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770874",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "67001.GE40L.STBRGADP1CW.STBRGADP0QW",
            "ELEMENT_REFERENCE": "1168432",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862058",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "1557536",
            "PATH_NAME": "67.L1XX.800134..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "421669",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "HENRY COUNTY GOVERNMENT",
            "CUSTOMER_NAME": "HENRY COUNTY GOVERNMENT",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770874",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "67001.GE1.STBRGADP0QW.MCDNGA931ZW",
            "ELEMENT_REFERENCE": "1556881",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862057",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "1557536",
            "PATH_NAME": "67.L1XX.800134..TWCC",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "421669",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "HENRY COUNTY GOVERNMENT",
            "CUSTOMER_NAME": "HENRY COUNTY GOVERNMENT",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": None,
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": None,
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "5.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "5",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770874",
            "A_SITE_NAME": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MCDNGA931ZW/999.9999.999.99/RTR",
            "ELEMENT_REFERENCE": "1177059",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "CHASSIS",
            "PORT_NAME": "0",
            "PORT_INST_ID": "105875709",
            "PORT_ACCESS_ID": "GI0/0/0",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MCDNGA931ZW.CHTRSE.COM",
            "MODEL": "ASR-920-4SZ-A",
            "VENDOR": "CISCO",
            "TID": "MCDNGA931ZW",
            "LEGACY_EQUIP_SOURCE": "L-BHN",
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "1168432",
            "PATH_NAME": "67001.GE40L.STBRGADP1CW.STBRGADP0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "STBRGADP",
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
            "ORDER_REFERENCE": "3.1.1.",
            "PARENT_SEQUENCE": "3",
            "PARENT_MEMBER_NBR": "1",
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1356876",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "STBRGADP1CW/001.0004.017.01/RTR",
            "ELEMENT_REFERENCE": "917941",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862058",
            "SLOT": "3/2",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101619153",
            "PORT_ACCESS_ID": "ET-1/3/2",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "STBRGADP1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "STBRGADP1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "L-C CEN 20115",
        },
        {
            "CIRC_PATH_INST_ID": "1168432",
            "PATH_NAME": "67001.GE40L.STBRGADP1CW.STBRGADP0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "STBRGADP",
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
            "ORDER_REFERENCE": "3.1.2.",
            "PARENT_SEQUENCE": "3",
            "PARENT_MEMBER_NBR": "1",
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1356876",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "STBRGADP1CW/001.0004.017.01/RTR",
            "ELEMENT_REFERENCE": "917941",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862058",
            "SLOT": "3/2",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101619163",
            "PORT_ACCESS_ID": "ET-10/3/2",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "STBRGADP1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "STBRGADP1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "L-C CEN 20115",
        },
        {
            "CIRC_PATH_INST_ID": "1168432",
            "PATH_NAME": "67001.GE40L.STBRGADP1CW.STBRGADP0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "STBRGADP",
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
            "ORDER_REFERENCE": "3.2.1.",
            "PARENT_SEQUENCE": "3",
            "PARENT_MEMBER_NBR": "2",
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1356876",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "STBRGADP0QW/001.0004.017.19/SWT#0",
            "ELEMENT_REFERENCE": "917942",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862058",
            "SLOT": "96",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101619176",
            "PORT_ACCESS_ID": "ET-0/0/96",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "STBRGADP0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "STBRGADP0QW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "L-C CEN 20115",
        },
        {
            "CIRC_PATH_INST_ID": "1168432",
            "PATH_NAME": "67001.GE40L.STBRGADP1CW.STBRGADP0QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "STBRGADP",
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
            "ORDER_REFERENCE": "3.2.2.",
            "PARENT_SEQUENCE": "3",
            "PARENT_MEMBER_NBR": "2",
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "AE17/AE17 80G",
            "LEG_INST_ID": "1356876",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "STBRGADP0QW/001.0004.017.22/SWT#1",
            "ELEMENT_REFERENCE": "917943",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862058",
            "SLOT": "96",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101619185",
            "PORT_ACCESS_ID": "ET-1/0/96",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "STBRGADP0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "STBRGADP0QW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "L-C CEN 20115",
        },
        {
            "CIRC_PATH_INST_ID": "1556881",
            "PATH_NAME": "67001.GE1.STBRGADP0QW.MCDNGA931ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "ORDER_REFERENCE": "4..1.",
            "PARENT_SEQUENCE": "4",
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770172",
            "A_SITE_NAME": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "STBRGADP0QW/001.0004.017.22/SWT#1",
            "ELEMENT_REFERENCE": "917943",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862057",
            "SLOT": "20",
            "PORT_NAME": "1",
            "PORT_INST_ID": "105857353",
            "PORT_ACCESS_ID": "GE-1/0/20",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "STBRGADP0QW.CHTRSE.COM",
            "MODEL": "QFX5100-96S",
            "VENDOR": "JUNIPER",
            "TID": "STBRGADP0QW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "L-C CEN 20115",
        },
        {
            "CIRC_PATH_INST_ID": "1556881",
            "PATH_NAME": "67001.GE1.STBRGADP0QW.MCDNGA931ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "STBRGADP-CHTR/HUB-STOCKBRIDGE (13216) - GA (STBRGA01566)",
            "PATH_Z_SITE": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "A_CLLI": "STBRGADP",
            "Z_CLLI": "MCDNGA93",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "ORDER_REFERENCE": "4..2.",
            "PARENT_SEQUENCE": "4",
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "1770172",
            "A_SITE_NAME": "MCDNGA93-HENRY COUNTY GOVERNMENT /1092 KEYS FERRY RD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MCDNGA931ZW/999.9999.999.99/RTR",
            "ELEMENT_REFERENCE": "1177059",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN2065",
            "CHAN_INST_ID": "7862057",
            "SLOT": "5",
            "PORT_NAME": "1",
            "PORT_INST_ID": "105875711",
            "PORT_ACCESS_ID": "TE0/0/5",
            "CONNECTOR_TYPE": "LC-UPC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MCDNGA931ZW.CHTRSE.COM",
            "MODEL": "ASR-920-4SZ-A",
            "VENDOR": "CISCO",
            "TID": "MCDNGA931ZW",
            "LEGACY_EQUIP_SOURCE": "L-BHN",
            "DEVICE_INFO_NETWORK": None,
        },
    ]
    result = {
        "Granite Data": [{"tid": "STBRGADP1CW", "evc_id": "421669", "encapsulation": "vlan-vpls"}],
        "Network Data": [{"tid": "STBRGADP1CW"}],
    }
    z_side_cpe_model = "asr-920-4sz-a"
    ipv4 = None
    ipv4_service_type = None
    ipv4_assigned_subnet = None
    ipv4_glue_subnet = None
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "full")
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (
            result,
            z_side_cpe_model,
            ipv4,
            ipv4_service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )
    monkeypatch.setattr(dsco, "is_blacklisted", lambda **__: {"blacklist_ip's": []})
    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_cisco_asr_920_configuration(monkeypatch):
    result = {
        "tid": "HTCYTXRJ1ZW",
        "vendor": "CISCO",
        "model": "ASR-920-4SZ-A",
        "vlan_id": "1177",
        "port_id": "GI0/0/1",
        "description": True,
    }
    device_info = {
        "tid": "HTCYTXRJ1ZW",
        "port_id": "GI0/0/1",
        "vendor": "CISCO",
        "vlan_id": "1177",
        "description": True,
        "model": "ASR-920-4SZ-A",
    }
    cid = "81.L1XX.005906..TWCC"
    circ_path_inst_id = "2502500"
    network_result = {
        "command": "me3400/show-running-config-interface.json",
        "parameters": {"interface": "gi0/0/1"},
        "result": {
            "interface": "GigabitEthernet0/0/1",
            "description": "EP-UNI:FIA:DISCOUNT MOTORS@5801 E BELKNAP ST:81.L1XX.005906..TWCC:",
            "port_type": "",
            "mgmt_ip": "",
            "mgmt_subnet": "",
            "load_interval": "30",
            "service_policy_input": "",
            "service_policy_output": "QSP-ANY-CFP-OUT-MAP",
            "switchport": {
                "mode": "access",
                "vlan": {"access_vlan": "", "trunk": {"allowed_vlans": [], "native_vlan": ""}},
            },
        },
    }
    vlan_data = {"pass": "1177"}
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: network_result)
    monkeypatch.setattr(dsco, "get_asr920_vlan", lambda *args, **kwargs: vlan_data)
    assert (dsco.get_cisco_asr920_configuration(device_info, cid, circ_path_inst_id)) == result


@pytest.mark.unittest
def test_get_comparison_db_and_network_data_rad_203ax(monkeypatch):
    db_dev_list = [
        {
            "tid": "YNTWOHNX3CW",
            "port_id": "AE18",
            "vendor": "JUNIPER",
            "vlan_id": "1117",
            "description": True,
            "model": "MX960",
            "ipv4": "162.155.99.97/27,70.60.44.225/29",
            "ipv6": "2605:A000:0:8::F:CAA2/127",
        },
        {
            "tid": "YNTWOHNX1QW",
            "port_id": "GE-0/0/16",
            "vendor": "JUNIPER",
            "vlan_id": "1117",
            "description": True,
            "model": "QFX5100-96S",
        },
        {
            "tid": "YNTWOHET1ZW",
            "port_id": "ETH PORT 4",
            "vendor": "RAD",
            "vlan_id": "1117",
            "description": True,
            "model": "ETX-203AX/GE30/2SFP/4UTP",
        },
    ]
    ipv4 = "162.155.99.97/27,70.60.44.225/29"
    ipv4_service_type = "LAN"
    ipv4_assigned_subnet = "162.155.99.96/27,70.60.44.224/29"
    ipv4_glue_subnet = None

    devices = {"YNTWOHET1ZW": "ETH PORT 4", "YNTWOHNX3CW": "AE18", "YNTWOHNX1QW": "GE-0/0/16"}
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.CENTRAL STATES.MPLS",
            "ELEMENT_REFERENCE": "1175885",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "7420",
            "CHAN_INST_ID": "10176697",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "ELEMENT_REFERENCE": "2478356",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "ELEMENT_REFERENCE": "2547166",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": "2296975",
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": None,
            "PORT_NAME": None,
            "PORT_INST_ID": None,
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": None,
            "PORT_CHANNELIZATION": None,
            "FQDN": None,
            "MODEL": None,
            "VENDOR": None,
            "TID": None,
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2292543",
            "PATH_NAME": "60.L1XX.003937..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "100 Mbps",
            "BW_SIZE": "100000000",
            "CUSTOMER_ID": "ACCT-22020725",
            "CUSTOMER_NAME": "LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": "47.225.245.204/30",
            "IPV4_ASSIGNED_GATEWAY": "47.225.245.205/30",
            "IPV4_SERVICE_TYPE": "LAN",
            "IPV6_GLUE_SUBNET": "2600:6C08::2156/127",
            "IPV6_ASSIGNED_SUBNETS": "2600:6C08:18D::/48",
            "IPV6_SERVICE_TYPE": "ROUTED",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2616746",
            "A_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MDSPWIUY4ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1639619",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED PORTS",
            "PORT_NAME": "USER 3",
            "PORT_INST_ID": "113440454",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MDSPWIUY4ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "MDSPWIUY4ZW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": None,
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV1CW/01.001.011.01/RTR",
            "ELEMENT_REFERENCE": "923171",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "3/1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101704251",
            "PORT_ACCESS_ID": "ET-1/3/1",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV1CW/01.001.011.01/RTR",
            "ELEMENT_REFERENCE": "923171",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "3/1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "101704261",
            "PORT_ACCESS_ID": "ET-10/3/1",
            "CONNECTOR_TYPE": "OTHER",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV1CW.CHTRSE.COM",
            "MODEL": "MX960",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV1CW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "48",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115029149",
            "PORT_ACCESS_ID": "ET-0/1/0",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2478356",
            "PATH_NAME": "60001.GE40L.SNPRWIEV1CW.SNPRWIEV2QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "SNPRWIEV",
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
            "LEG_NAME": "AE19/AE19 80G",
            "LEG_INST_ID": "2857445",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "40 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790241",
            "SLOT": "49",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115029150",
            "PORT_ACCESS_ID": "ET-0/1/1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "2946916",
            "A_SITE_NAME": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "SNPRWIEV2QW/000.0000.000.00/SWT",
            "ELEMENT_REFERENCE": "1761362",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": "22",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115556718",
            "PORT_ACCESS_ID": "XE-0/0/22",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "SNPRWIEV2QW.CHTRSE.COM",
            "MODEL": "ACX5448",
            "VENDOR": "JUNIPER",
            "TID": "SNPRWIEV2QW",
            "LEGACY_EQUIP_SOURCE": None,
            "DEVICE_INFO_NETWORK": "EDNA",
        },
        {
            "CIRC_PATH_INST_ID": "2547166",
            "PATH_NAME": "60001.GE1.SNPRWIEV2QW.MDSPWIUY4ZW",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "SNPRWIEV-CHTR/HUB-SUN PRAIRIE (2639) - WI (SNPRWI00049)",
            "PATH_Z_SITE": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "A_CLLI": "SNPRWIEV",
            "Z_CLLI": "MDSPWIUY",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
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
            "LEG_INST_ID": "2946916",
            "A_SITE_NAME": "MDSPWIUY-LAKELAND UNIVERSITY [ NATIONAL ACCOUNT]//2310 CROSSROADS DR",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "MDSPWIUY4ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1639619",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1154",
            "CHAN_INST_ID": "10790228",
            "SLOT": "NET 1",
            "PORT_NAME": "1",
            "PORT_INST_ID": "113440451",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "MDSPWIUY4ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "MDSPWIUY4ZW",
            "LEGACY_EQUIP_SOURCE": "L-CHTR",
            "DEVICE_INFO_NETWORK": None,
        },
    ]
    network_dev_list = [
        {
            "tid": "YNTWOHNX3CW",
            "vendor": "JUNIPER",
            "model": "MX960",
            "vlan_id": "1117",
            "port_id": "AE18",
            "description": True,
        },
        {
            "tid": "YNTWOHNX1QW",
            "vendor": "JUNIPER",
            "model": "QFX5100-96S",
            "vlan_id": "1117",
            "port_id": "GE-0/0/16",
            "description": True,
        },
        {
            "tid": "YNTWOHET1ZW",
            "vendor": "RAD",
            "model": "ETX203AX/2SFP/2UTP2SFP",
            "vlan_id": "1117",
            "port_id": "ETH PORT 4",
            "description": False,
        },
    ]
    result = (
        {
            "Granite Data": [
                {"tid": "YNTWOHNX3CW", "ipv4": "162.155.99.97/27,70.60.44.225/29", "ipv6": "2605:A000:0:8::F:CAA2/127"},
                {"tid": "YNTWOHET1ZW", "description": True},
            ],
            "Network Data": [{"tid": "YNTWOHNX3CW"}, {"tid": "YNTWOHET1ZW", "description": False}],
        },
        "etx-203ax/ge30/2sfp/4utp",
        "162.155.99.97/27,70.60.44.225/29",
        "LAN",
        "162.155.99.96/27,70.60.44.224/29",
        None,
    )
    monkeypatch.setattr(
        dsco,
        "get_circuit_device_data_from_db",
        lambda *args, **kwargs: ("db_dev_list", "ipv4", "ipv4_service_type", "ipv4_assigned_subnet", "ipv4_glue_subnet"),
    )
    monkeypatch.setattr(dsco, "check_active_devices", lambda *args: [])
    monkeypatch.setattr(
        dsco,
        "get_circuit_device_data_from_db",
        lambda *args: (db_dev_list, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet),
    )
    monkeypatch.setattr(dsco, "get_network_data", lambda *args: network_dev_list)
    assert (
        dsco.get_comparison_db_and_network_data(
            "33.L1XX.005823..TWCC", "Fiber Internet Access", devices, path_elements, "YNTWOHET1ZW", False
        )
        == result
    )


@pytest.mark.unittest
def get_juniper_network_configuration_qfx(monkeypatch):
    juniper_dev = {"tid": "AUSUTXLA3QW", "vendor": "", "model": "", "vlan_id": "", "port_id": "", "description": True}
    device_info = {
        "tid": "AUSUTXLA3QW",
        "port_id": "GE-1/0/36",
        "vendor": "JUNIPER",
        "vlan_id": "1231",
        "description": True,
        "model": "QFX5100-96S",
    }
    cid = "51.L1XX.020938..CHTR"
    onboard_and_exe_cmd = {
        "command": "get-vlanidentifier-full.json",
        "parameters": {},
        "result": {
            "DIA101": {"name": "DIA101", "description": "51.LUXX.000070..TWCC:CUST:FIA::", "vlan-id": "101"},
            "ELINE1228": {
                "name": "ELINE1228",
                "description": "51.L1XX.020939..CHTR:CUST:ELINE:78753:",
                "vlan-id": "1228",
            },
            "ELINE1231": {
                "name": "ELINE1231",
                "description": "51.L1XX.020938..CHTR:CUST:ELINE:78753:",
                "vlan-id": "1231",
            },
            "ELINE1236": {
                "name": "ELINE1236",
                "description": "21.LOXX.000452..TWCC:CUST:ELINE:78660:",
                "vlan-id": "1236",
            },
            "VOICE2401": {
                "name": "VOICE2401",
                "description": "51.IPXN.000215.AUS.TWCC:CUST:VOICE:78758:",
                "vlan-id": "2401",
            },
        },
    }
    expected = {
        "tid": "AUSUTXLA3QW",
        "vendor": "JUNIPER",
        "model": "QFX5100-96S",
        "vlan_id": "1231",
        "port_id": "GE-1/0/36",
        "description": True,
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: onboard_and_exe_cmd)
    assert dsco.get_juniper_network_configuration_qfx(juniper_dev, device_info, cid) == expected


@pytest.mark.unittest
def test_get_juniper_network_configuration_acx(monkeypatch):
    cid = "81.L1XX.011517..CHTR"
    juniper_dev = {
        "tid": "FTWOTXGZ1QW",
        "vendor": "JUNIPER",
        "model": "ACX5448",
        "vlan_id": "",
        "port_id": "XE-0/0/0",
        "description": True,
    }
    device_info = {
        "tid": "FTWOTXGZ1QW",
        "port_id": "XE-0/0/0",
        "vendor": "JUNIPER",
        "vlan_id": "1101",
        "description": True,
        "model": "ACX5448",
    }
    result = {
        "tid": "FTWOTXGZ1QW",
        "vendor": "JUNIPER",
        "model": "ACX5448",
        "vlan_id": "1101",
        "port_id": "XE-0/0/0",
        "description": True,
    }
    dev_config = {
        "result": {
            "data": {
                "configuration": {
                    "@xmlns": "http://xml.juniper.net/xnm/1.1/xnm",
                    "@junos:commit-seconds": "1746635198",
                    "@junos:commit-localtime": "2025-05-07 16:26:38 UTC",
                    "@junos:commit-user": "sensor",
                    "interfaces": {
                        "interface": {
                            "name": "xe-0/0/0",
                            "apply-groups": "SERVICEPORT",
                            "description": "81001.GE10.FTWOTXGZ1QW.FTWRTXBP1AW:MTU:FTWRTXBP1AW:ETH PORT 1:DHCP",
                            "unit": {
                                "name": "1101",
                                "description": "81.L1XX.011517..CHTR:CUST:FIA:76115:",
                                "encapsulation": "vlan-bridge",
                                "vlan-id": "1101",
                            },
                        }
                    },
                }
            }
        }
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: dev_config)
    assert dsco.get_juniper_network_configuration_acx(juniper_dev, device_info, cid) == result


@pytest.mark.unittest
def test_get_rad_network_configs_etx_2i_10g(monkeypatch):
    device = {
        "tid": "TAYLTXAW2AW",
        "port_id": "ETH PORT 0/2",
        "vendor": "RAD",
        "vlan_id": "547",
        "description": True,
        "model": "ETX-2I-10G/4SFPP/24SFP",
    }
    network_info = {
        "tid": "TAYLTXAW2AW",
        "vendor": "RAD",
        "model": "",
        "vlan_id": "547",
        "port_id": "",
        "description": True,
    }
    cid = "51.L1XX.992149..CHTR"
    network_resp = {
        "command": "list-classifiers.json",
        "parameters": {},
        "result": [
            {
                "label": "CP-51.L1XX.012025..CHTR-IN",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.012025..CHTR-IN", "match": ["match vlan 201"]},
            },
            {
                "label": "CP-51.L1XX.012025..CHTR-OUT",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.012025..CHTR-OUT", "match": ["match vlan 201"]},
            },
            {
                "label": "CP-51.L1XX.022979..CHTR-IN",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.022979..CHTR-IN", "match": ["match vlan 1100"]},
            },
            {
                "label": "CP-51.L1XX.022979..CHTR-OUT",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.022979..CHTR-OUT", "match": ["match vlan 1100"]},
            },
            {
                "label": "CP-51.L1XX.992149..CHTR-IN",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992149..CHTR-IN", "match": ["match vlan 547"]},
            },
            {
                "label": "CP-51.L1XX.992149..CHTR-OUT",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992149..CHTR-OUT", "match": ["match vlan 547"]},
            },
            {
                "label": "CP-51.L1XX.992150..CHTR-IN",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992150..CHTR-IN", "match": ["match vlan 2547"]},
            },
            {
                "label": "CP-51.L1XX.992150..CHTR-OUT",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992150..CHTR-OUT", "match": ["match vlan 2547"]},
            },
            {
                "label": "CP-51.L1XX.992151..CHTR-IN",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992151..CHTR-IN", "match": ["match vlan 3547"]},
            },
            {
                "label": "CP-51.L1XX.992151..CHTR-OUT",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992151..CHTR-OUT", "match": ["match vlan 3547"]},
            },
            {
                "label": "CP-51.L1XX.992152..CHTR-IN",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992152..CHTR-IN", "match": ["match vlan 1547"]},
            },
            {
                "label": "CP-51.L1XX.992152..CHTR-OUT",
                "orchState": "active",
                "properties": {"name": "CP-51.L1XX.992152..CHTR-OUT", "match": ["match vlan 1547"]},
            },
            {"label": "mgmt", "orchState": "active", "properties": {"name": "mgmt", "match": ["match untagged"]}},
            {"label": "mgmt-99", "orchState": "active", "properties": {"name": "mgmt-99", "match": ["match vlan 99"]}},
            {"label": "mng_all", "orchState": "active", "properties": {"name": "mng_all", "match": ["match all"]}},
            {
                "label": "mng_untagged",
                "orchState": "active",
                "properties": {"name": "mng_untagged", "match": ["match untagged"]},
            },
        ],
    }
    device_info = {
        "id": "8fc89851-2f81-11f0-b4fc-a3d493e8798b",
        "label": "TAYLTXAW2AW",
        "resourceTypeId": "radra.resourceTypes.NetworkFunction",
        "productId": "6c519a1f-ea5d-11ef-b4fc-e98a99406438",
        "domainId": "6c2affe6-ea5d-11ef-ae36-5b2797ea3f47",
        "tenantId": "181bb2ec-e8e4-11ef-b841-cff8e8e633d6",
        "shared": False,
        "subDomainId": "83d7a4a9-9067-369e-a528-ed6afb4287c5",
        "properties": {
            "serialNumber": "00-20-D2-5E-CB-9D",
            "sessionProfile": "187073ad-ea5f-11ef-ae36-51da9667bd73",
            "typeGroup": "/typeGroups/RAD-CPE",
            "deviceVersion": "2I",
            "resourceType": "ETX-2I",
            "swImage": "6.4.0(0.94)",
            "authentication": {"cli": {"password": "uyTxQ6!GN4P2sb", "username": "sensor"}},
            "communicationState": "AVAILABLE",
            "ipAddress": "TAYLTXAW2AW.CML.CHTRSE.COM",
            "swVersion": "6.4.0",
            "swType": "",
            "connection": {
                "cli": {"hostport": 22, "transport": "bpprov.components.cli_transport.SshTransport"},
                "hostname": "TAYLTXAW2AW.CML.CHTRSE.COM",
            },
            "type": "ETX-2I",
            "timeout": 120,
        },
        "providerResourceId": "bpo_6c2affe6-ea5d-11ef-ae36-5b2797ea3f47_8fc89851-2f81-11f0-b4fc-a3d493e8798b",
        "discovered": False,
        "differences": [],
        "desiredOrchState": "active",
        "orchState": "active",
        "reason": "",
        "tags": {},
        "providerData": {},
        "updatedAt": "2025-05-12T22:36:39.435Z",
        "createdAt": "2025-05-12T22:36:35.833Z",
        "revision": 5048179,
        "autoClean": False,
        "updateState": "unset",
        "updateReason": "",
        "updateCount": 0,
    }
    expected = {
        "tid": "TAYLTXAW2AW",
        "vendor": "RAD",
        "model": "ETX-2I-10G/4SFPP/24SFP",
        "vlan_id": "547",
        "port_id": "ETH PORT 0/2",
        "description": True,
    }
    monkeypatch.setattr(dsco, "onboard_and_exe_cmd", lambda *args, **kwargs: network_resp)
    monkeypatch.setattr(dsco, "_get_network_device", lambda *args, **kwargs: device_info)
    assert dsco.get_rad_network_configs_etx_2i_10g(device, network_info, cid) == expected


@pytest.mark.unittest
def test_evpl_disconnect_main(monkeypatch):
    param = DisconnectPayloadModel(service_type="disconnect", product_name="EVPL (Fiber)", cid="81.L1XX.011517..CHTR")
    devices = {
        "FTWRTXBP1ZW": "ETH PORT 3",
        "FTWOTXGZ1CW": "AE18",
        "FTWOTXGZ1QW": "XE-0/0/0",
        "FTWRTXBP1AW": "ETH_PORT-1-1-1-1",
    }
    zw = "FTWRTXBP1ZW"
    circ_path_inst_id = "2421444"
    path_elements = ""
    job_type = "full"
    result = True
    z_side_cpe_model = "etx203ax/2sfp/2utp2sfp"
    ipv4 = "97.94.215.13/30"
    ipv4_service_type = "LAN"
    ipv4_assigned_subnet = "97.94.215.12/30"
    ipv4_glue_subnet = None
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, path_elements)
    )
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: job_type)
    monkeypatch.setattr(
        dsco,
        "get_comparison_db_and_network_data",
        lambda *args, **kwargs: (
            result,
            z_side_cpe_model,
            ipv4,
            ipv4_service_type,
            ipv4_assigned_subnet,
            ipv4_glue_subnet,
        ),
    )
    resp = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "etx203ax/2sfp/2utp2sfp",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "2421444",
        "engineering_job_type": "full",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "Yes",
    }
    assert dsco.disconnect(param) == resp


@pytest.mark.unittest
def test_epl_disconnect_main(monkeypatch):
    input = DisconnectPayloadModel(
        cid="77.L1XX.002735..CHTR",
        product_name="EPL (Fiber)",
        service_type="disconnect",
        service_location_address="4615 ECHO AVE",
    )
    devices = {
        "RENRNVYB1ZW": "ETH PORT 4",
        "STEDNVRR3ZW": "ETH PORT 3",
        "RENQNVLX1QW": "GE-0/0/49",
        "RENQNVLX1CW": "AE17",
        "RENQNVLX0QW": "GE-0/0/34",
    }
    circ_path_inst_id = "2564904"
    truncated_path_elements = [
        {
            "PATH_NAME": "77.L1XX.002735..CHTR",
            "A_SITE_NAME": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
            "ELEMENT_NAME": "RENRNVYB1ZW/999.9999.999.99/NIU",
            "PORT_ACCESS_ID": "ETH PORT 4",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "TID": "RENRNVYB1ZW",
        },
        {
            "PATH_NAME": "77.L1XX.002735..CHTR",
            "A_SITE_NAME": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
            "ELEMENT_NAME": "STEDNVRR3ZW/999.9999.999.99/NIU",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "TID": "STEDNVRR3ZW",
        },
    ]
    circuit_data = {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
    }
    cpe_per_side = {
        "a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP"),
        "z_side_cpe": ("STEDNVRR3ZW", "ETX203AX/2SFP/2UTP2SFP"),
    }
    cpe = {"a_side_cpe": ("RENRNVYB1ZW", "ETX203AX/2SFP/2UTP2SFP")}
    zw = "RENRNVYB1ZW"
    job_type = "partial"
    hub_work_required = "Yes"
    cpe_installer_needed = "No"
    expected = {
        "networkcheck": {"passed": True, "granite": [], "network": []},
        "cpe_model": "ETX203AX/2SFP/2UTP2SFP",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "2564904",
        "engineering_job_type": "partial",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "No",
    }
    monkeypatch.setattr(
        dsco, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, zw, circ_path_inst_id, truncated_path_elements)
    )
    monkeypatch.setattr(dsco, "get_circuit_side_info", lambda *args, **kwargs: circuit_data)
    monkeypatch.setattr(dsco, "get_cpe_side_info", lambda *args, **kwargs: cpe_per_side)
    monkeypatch.setattr(dsco, "get_cpe_at_service_location", lambda *args, **kwargs: cpe)
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: job_type)
    monkeypatch.setattr(dsco, "full_disco_check", lambda *args, **kwargs: (hub_work_required, cpe_installer_needed))
    assert dsco.disconnect(input) == expected

    # generate fall-out conditions
    payload_missing_service_location = DisconnectPayloadModel(
        cid="77.L1XX.002735..CHTR", product_name="EPL (Fiber)", service_type="disconnect"
    )
    try:
        dsco.disconnect(payload_missing_service_location)
    except AbortException as e:
        assert "Service location address is undefined" in e.data["message"]

    payload_with_None_service_location = DisconnectPayloadModel(
        cid="77.L1XX.002735..CHTR", product_name="EPL (Fiber)", service_type="disconnect", service_location_address=None
    )
    try:
        dsco.disconnect(payload_with_None_service_location)
    except AbortException as e:
        assert "Service location address is undefined" in e.data["message"]

    payload_with_empty_string_service_location = DisconnectPayloadModel(
        cid="77.L1XX.002735..CHTR", product_name="EPL (Fiber)", service_type="disconnect", service_location_address=""
    )
    try:
        dsco.disconnect(payload_with_empty_string_service_location)
    except AbortException as e:
        assert "Service location address is undefined" in e.data["message"]

    payload_with_blank_space_service_location = DisconnectPayloadModel(
        cid="77.L1XX.002735..CHTR", product_name="EPL (Fiber)", service_type="disconnect", service_location_address=" "
    )
    try:
        dsco.disconnect(payload_with_blank_space_service_location)
    except AbortException as e:
        assert "Undefined service location address" in e.data["message"]

    cpe_missing_tid = {"a_side_cpe": ("", "ETX203AX/2SFP/2UTP2SFP")}
    monkeypatch.setattr(dsco, "get_cpe_at_service_location", lambda *args, **kwargs: cpe_missing_tid)
    try:
        dsco.disconnect(input)
    except AbortException as e:
        assert "Unable to retrieve necessary ZW device info" in e.data["message"]

    cpe_missing_model = {"a_side_cpe": ("RENRNVYB1ZW", None)}
    monkeypatch.setattr(dsco, "get_cpe_at_service_location", lambda *args, **kwargs: cpe_missing_model)
    try:
        dsco.disconnect(input)
    except AbortException as e:
        assert "Unable to retrieve necessary ZW device info" in e.data["message"]

    circuit_data_unsupported_status = {
        "cid": "77.L1XX.002735..CHTR",
        "status": "Planned",
        "aSideSiteName": "RENRNVYB-CONTINENTAL CORPORATION MSA UMBRELLA//4615 ECHO AVE",
        "zSideSiteName": "STEDNVRR-CONTINENTAL TIRE THE AMERICAS LLC//14100 LEAR BLVD",
    }
    monkeypatch.setattr(dsco, "get_circuit_side_info", lambda *args, **kwargs: circuit_data_unsupported_status)
    monkeypatch.setattr(dsco, "get_cpe_at_service_location", lambda *args, **kwargs: cpe)
    try:
        dsco.disconnect(input)
    except AbortException as e:
        assert "circuit status: Planned" in e.data["message"]


@pytest.mark.unittest
def test_mne_disco(monkeypatch):
    param = DisconnectPayloadModel(
        service_type="disconnect",
        product_name="Managed Network Edge - Spectrum Provided",
        cid="31.L1XX.000473..TWCC",
        product_family="Managed Network Edge",
    )

    response = {
        "networkcheck": {"passed": True},
        "cpe_model": "MERAKI MX68",
        "blacklist": {"passed": True, "ips": []},
        "circ_path_inst_id": "1508042",
        "engineering_job_type": "partial",
        "hub_work_required": "No",
        "cpe_installer_needed": "Yes",
    }

    monkeypatch.setattr(dsco, "get_circuit_tid_ports", lambda *args, **kwargs: ("", "", "1508042", [{}]))
    monkeypatch.setattr(dsco, "update_mne_status", lambda *args, **kwargs: ("Yes", "MERAKI MX68"))
    monkeypatch.setattr(dsco, "get_job_type", lambda *args, **kwargs: "partial")

    assert dsco.disconnect(param) == response


@pytest.mark.unittest
def test_update_mne_status(monkeypatch):
    # bad test - granite response is not instance of list
    monkeypatch.setattr(dsco, "get_granite", lambda *args, **kwargs: "granite_resp")
    with pytest.raises(Exception):
        dsco.update_mne_status("1234", [{}], "Managed Network Edge")

    # bad test - product family does not match any MNE parent services
    monkeypatch.setattr(
        dsco, "get_granite", lambda *args, **kwargs: [{"CATEGORY": "Meraki Network-Switch", "NAME": "test_name"}]
    )
    with pytest.raises(Exception):
        dsco.update_mne_status("1234", [{}], "Managed Network Edge")

    # good test
    mock_granite_respone = [
        {"CATEGORY": "Meraki Network-Edge", "NAME": "test_name_edge", "STATUS": "LIVE"},
        {"CATEGORY": "Meraki Network-Switch", "NAME": "test_name_switch", "STATUS": "Pending Decommission"},
        {"CATEGORY": "Meraki Service Org Parent", "NAME": "test_name_parent", "STATUS": "LIVE"},
    ]
    path_elements = [{"ELEMENT_NAME": "MNE_DEVICE", "ELEMENT_TYPE": "PORT", "MODEL": "MERAKI MX68", "TID": "MNE_DEVICE"}]
    monkeypatch.setattr(dsco, "get_granite", lambda *args, **kwargs: mock_granite_respone)
    monkeypatch.setattr(dsco, "update_meraki_status", lambda *args, **kwargs: None)

    assert dsco.update_mne_status("1234", path_elements, "Managed Network Edge") == ("Yes", "MERAKI MX68")
