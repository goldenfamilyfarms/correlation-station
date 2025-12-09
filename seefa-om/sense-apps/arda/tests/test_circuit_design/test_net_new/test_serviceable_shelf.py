import logging
import pytest

from arda_app.api import serviceable_shelf as ss

from copy import deepcopy

from arda_app.bll import serviceable_shelf
from common_sense.common.errors import AbortException
from arda_app.common import auth_config


logger = logging.getLogger(__name__)

payload = {
    "cid": "33.L1XX.007395..TWCC",
    "agg_bandwidth": "1Gbps",
    "connector_type": "LC",
    "uni_type": "Access",
    "side": "z_side",
    "product_name": "",
}

sense_usr, sense_pass = auth_config.SENSE_TEST_SWAGGER_USER, auth_config.SENSE_TEST_SWAGGER_PASS
head = {"accept": "application/json"}
auth = (sense_usr, sense_pass)

test_payload = deepcopy(payload)

serviceable_shelf_handoff_resp = {
    "cpe_shelf": "AMHRNYPA1ZW/999.9999.999.99/SWT",
    "cpe_tid": "AMHRNYPA1ZW",
    "cpe_handoff": "102681186",
    "cpe_handoff_paid": "ACCESS-1-1-1-5",
    "zw_path": "71001.GE1.WSVLNYWF1QW.AMHRNYPA1ZW",
    "circ_path_inst_id": "1878630",
}


@pytest.mark.unittest
def test_serviceable_shelf_main(monkeypatch):
    payload = {
        "cid": "51.L1XX.817074..CHTR",
        "connector_type": "LC",
        "uni_type": "Access",
        "product_name": "FC + Remote PHY",
    }

    # bad test - abort missing payload keys side
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_main(payload)

    # good test - agg bandwidth missing but changed to 10 gbps remote Phy
    payload["side"] = "z_side"
    response = {
        "cpe_shelf": "AUSNTX181ZW/999.9999.999.99/NIU",
        "cpe_tid": "AUSNTX181ZW",
        "cpe_handoff": "109711318",
        "cpe_handoff_paid": "ETH PORT 6",
        "zw_transport_path_name": "51001.GE10.AUSBTX520QW.AUSNTX181ZW",
        "zw_transport_path_inst_id": "1911263",
        "circ_path_inst_id": "1890963",
        "hub_work_required": False,
        "transport_upgrade": False,
    }
    monkeypatch.setattr(serviceable_shelf, "serviceable_shelf_handoff", lambda *args, **kwargs: response)
    assert serviceable_shelf.serviceable_shelf_main(payload) == response

    # good test - agg bandwidth "" but changed to 10 gbps remote Phy
    payload["agg_bandwidth"] = ""
    assert serviceable_shelf.serviceable_shelf_main(payload) == response

    # good test agg bandwidth 100 Mbps
    payload["agg_bandwidth"] = "100 Mbps"
    payload["product_name"] = "FIA"
    assert serviceable_shelf.serviceable_shelf_main(payload) == response


@pytest.mark.unittest
def test_serviceable_shelf_handoff(monkeypatch):
    # bad test - abort no path found for cid
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: {})
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort multiple paths found for cid
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: [{}, {}])
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort no site name found for cid
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: [{}])
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort unsuported site type of COLO
    monkeypatch.setattr(
        serviceable_shelf, "get_granite", lambda *args, **kwargs: [{"Z_SITE_NAME": "temp", "Z_SITE_TYPE": "COLO"}]
    )
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - unable to find clli and site name
    circuitSites_resp = [
        {
            "CIRC_PATH_INST_ID": "1890963",
            "CIRCUIT_NAME": "51.L1XX.817074..CHTR",
            "CIRCUIT_STATUS": "Live",
            "CIRCUIT_BANDWIDTH": "200 Mbps",
            "CIRCUIT_CATEGORY": "ETHERNET",
            "A_SITE_NAME": "AUSBTX52-TWC/HUB G-GUADALUPE",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "Z_SITE_TYPE": "LOCAL",
        }
    ]
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: circuitSites_resp)

    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "RJ45", "access", "z_side")

    # bad test - no shelves found at cid
    circuitSites_resp[0]["A_CLLI"] = "AUSBTX52"
    circuitSites_resp[0]["Z_CLLI"] = "AUSNTX18"
    monkeypatch.setattr(serviceable_shelf, "get_shelves_at_site", lambda *args, **kwargs: {})

    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort No available ports found at site
    site_shelves = [
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_INST_ID": "634763",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "AUSNTX18",
            "EQUIP_NAME": "AUSNTX1802W/999.9999.999.99/SWT",
            "EQUIP_INST_ID": "1403398",
            "EQUIP_CATEGORY": "SWITCH",
            "EQUIP_STATUS": "None",
            "EQUIP_VENDOR": "ADTRAN",
            "EQUIP_MODEL": "NETVANTA 1550-24P",
            "TARGET_ID": "AUSNTX1802W",
            "IPV4_ADDRESS": "10.12.0.5/23",
            "OBJECT_TYPE": "SHELF",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_INST_ID": "634763",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "AUSNTX18",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_CATEGORY": "NIU",
            "EQUIP_STATUS": "None",
            "EQUIP_VENDOR": "RAD",
            "EQUIP_MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "FQDN": "AUSNTX181ZW.CML.CHTRSE.COM",
            "TARGET_ID": "AUSNTX181ZW",
            "IPV4_ADDRESS": "10.5.44.184/24",
            "OBJECT_TYPE": "SHELF",
        },
    ]

    site_info = [
        {
            "SHELF_COUNT": "1",
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_STATUS": "Live",
            "EQUIP_TPLT_NAME": "ETX203AX/2SFP/2UTP2SFP",
            "PARENT_SLOT": "FIXED PORTS",
            "SLOT": "NET 2/USER",
            "SLOT_INST_ID": "11451177",
        },
        {
            "SHELF_COUNT": "1",
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_STATUS": "Live",
            "EQUIP_TPLT_NAME": "ETX203AX/2SFP/2UTP2SFP",
            "PARENT_SLOT": "FIXED PORTS",
            "SLOT": "USER 6",
            "SLOT_INST_ID": "11451179",
            "CARD_STATUS": "Live",
            "CARD_TPLT_NAME": "GENERIC SFP",
            "PORT_NAME": "1",
            "PORT_ACCESS_ID": "ETH PORT 6",
            "PORT_INST_ID": "109711318",
            "PORT_STATUS": "Ok",
            "BANDWIDTH": "1 Gbps",
        },
        {
            "SHELF_COUNT": "1",
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_STATUS": "Live",
            "EQUIP_TPLT_NAME": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_INST_ID": "11451175",
            "CARD_STATUS": "Live",
            "CARD_TPLT_NAME": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "CONSOLE PORT",
            "PORT_INST_ID": "109711313",
            "PORT_STATUS": "Ok",
            "BANDWIDTH": "10/100 BASET",
        },
        {
            "SHELF_COUNT": "1",
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_STATUS": "Live",
            "EQUIP_TPLT_NAME": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_INST_ID": "11451175",
            "CARD_STATUS": "Live",
            "CARD_TPLT_NAME": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "ETHERNET MANAGEMENT PORT",
            "PORT_INST_ID": "109711314",
            "PORT_STATUS": "Ok",
            "BANDWIDTH": "10/100 BASET",
        },
        {
            "SHELF_COUNT": "1",
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_STATUS": "Live",
            "EQUIP_TPLT_NAME": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_INST_ID": "11451175",
            "CARD_STATUS": "Live",
            "CARD_TPLT_NAME": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "USER 4",
            "PORT_ACCESS_ID": "ETH PORT 4",
            "PORT_INST_ID": "109711316",
            "PORT_STATUS": "Ok",
            "BANDWIDTH": "10/100/1000 BASET",
        },
    ]

    # bad test - no potential cpe shelves at side
    monkeypatch.setattr(serviceable_shelf, "get_shelves_at_site", lambda *args, **kwargs: site_shelves)
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    site_shelves[0]["EQUIP_STATUS"] = "Live"
    site_shelves[1]["EQUIP_STATUS"] = "Live"
    monkeypatch.setattr(serviceable_shelf, "get_site_available_ports", lambda *args, **kwargs: {})

    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort No available ports on determined shelf
    monkeypatch.setattr(serviceable_shelf, "get_site_available_ports", lambda *args, **kwargs: [{}])

    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort No available ports on the network for serviceable shelf
    monkeypatch.setattr(serviceable_shelf, "get_site_available_ports", lambda *args, **kwargs: site_info)

    shelf_ports = [
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_ORDER": "0",
            "SLOT_INST_ID": "11451175",
            "CARD_INST_ID": "7057660",
            "CARD_TYPE": "ETHERNET",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "CARD_TEMPLATE": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "CONSOLE PORT",
            "PORT_INST_ID": "109711313",
            "BANDWIDTH": "10/100 BASET",
            "PORT_STATUS": "Ok",
            "CONNECTOR_TYPE": "RJ-45",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_ORDER": "0",
            "SLOT_INST_ID": "11451175",
            "CARD_INST_ID": "7057660",
            "CARD_TYPE": "ETHERNET",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "CARD_TEMPLATE": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "ETHERNET MANAGEMENT PORT",
            "PORT_INST_ID": "109711314",
            "BANDWIDTH": "10/100 BASET",
            "PORT_STATUS": "Ok",
            "CONNECTOR_TYPE": "RJ-45",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_ORDER": "0",
            "SLOT_INST_ID": "11451175",
            "CARD_INST_ID": "7057660",
            "CARD_TYPE": "ETHERNET",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "CARD_TEMPLATE": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "USER 3",
            "PORT_ACCESS_ID": "ETH PORT 3",
            "PORT_INST_ID": "109711315",
            "BANDWIDTH": "10/100/1000 BASET",
            "PORT_STATUS": "Assigned",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_USE": "IN USE",
            "MEMBER_PATH_INST_ID": "1890963",
            "MEMBER_PATH": "51.L1XX.817074..CHTR",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "SLOT": "FIXED PORTS",
            "SLOT_ORDER": "0",
            "SLOT_INST_ID": "11451175",
            "CARD_INST_ID": "7057660",
            "CARD_TYPE": "ETHERNET",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "CARD_TEMPLATE": "RAD ETX203AX/2SFP/2UTP2SFP FIXED PORTS",
            "PORT_NAME": "USER 4",
            "PORT_ACCESS_ID": "ETH PORT 4",
            "PORT_INST_ID": "109711316",
            "BANDWIDTH": "10/100/1000 BASET",
            "PORT_STATUS": "Ok",
            "CONNECTOR_TYPE": "RJ-45",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "PARENT_SLOT": "FIXED PORTS",
            "PARENT_SLOT_ORDER": "0",
            "SLOT": "NET 1",
            "SLOT_ORDER": "0",
            "SLOT_INST_ID": "11451176",
            "CARD_INST_ID": "7057661",
            "CARD_TYPE": "SFP",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "GENERIC SFP 1GE",
            "CARD_TEMPLATE": "GENERIC SFP LEVEL 1",
            "PORT_NAME": "1",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "PORT_INST_ID": "109711312",
            "BANDWIDTH": "1 Gbps",
            "PORT_STATUS": "Ok",
            "CONNECTOR_TYPE": "LC",
            "PORT_USE": "IN USE",
            "MEMBER_PATH_INST_ID": "1911263",
            "MEMBER_PATH": "51001.GE1.AUSBTX520QW.AUSNTX181ZW",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "PARENT_SLOT": "FIXED PORTS",
            "PARENT_SLOT_ORDER": "0",
            "SLOT": "NET 2/USER",
            "SLOT_ORDER": "1",
            "SLOT_INST_ID": "11451177",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "PARENT_SLOT": "FIXED PORTS",
            "PARENT_SLOT_ORDER": "0",
            "SLOT": "USER 5",
            "SLOT_ORDER": "2",
            "SLOT_INST_ID": "11451178",
            "CARD_INST_ID": "7057662",
            "CARD_TYPE": "OPTICS",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "GENERIC SFP 1GE",
            "CARD_TEMPLATE": "GENERIC SFP",
            "PORT_NAME": "1",
            "PORT_ACCESS_ID": "ETH PORT 5",
            "PORT_INST_ID": "109711317",
            "BANDWIDTH": "1 Gbps",
            "PORT_STATUS": "Assigned",
            "CONNECTOR_TYPE": "LC",
            "PORT_USE": "IN USE",
            "MEMBER_PATH_INST_ID": "2002894",
            "MEMBER_PATH": "51.HNXN.000221..CHTR",
        },
        {
            "SITE_NAME": "AUSNTX18-USTUDIO INC//1803 WEST AVE",
            "SITE_TYPE": "LOCAL",
            "SITE_INST_ID": "634763",
            "EQUIP_NAME": "AUSNTX181ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1401732",
            "EQUIP_TYPE": "NIU",
            "EQUIP_STATUS": "Live",
            "VENDOR": "RAD",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "EQUIP_TEMPLATE": "ETX203AX/2SFP/2UTP2SFP",
            "PARENT_SLOT": "FIXED PORTS",
            "PARENT_SLOT_ORDER": "0",
            "SLOT": "USER 6",
            "SLOT_ORDER": "3",
            "SLOT_INST_ID": "11451179",
            "CARD_INST_ID": "7057663",
            "CARD_TYPE": "OPTICS",
            "CARD_STATUS": "Live",
            "CARD_DESCRIPTION": "GENERIC SFP 1GE",
            "CARD_TEMPLATE": "GENERIC SFP",
            "PORT_NAME": "1",
            "PORT_ACCESS_ID": "ETH PORT 6",
            "PORT_INST_ID": "109711318",
            "BANDWIDTH": "1 Gbps",
            "PORT_STATUS": "Ok",
            "CONNECTOR_TYPE": "LC",
        },
    ]

    network_ports = {
        "command": "seefa-cd-list-ports.json",
        "parameters": {},
        "result": [
            {
                "type": "Ethernet",
                "id": "1",
                "name": "UPLINK:AUSBTX520",
                "admin_state": "Up",
                "operational_state": "Up",
                "rate": "1000000000",
                "details": {
                    "name": "UPLINK:AUSBTX520QW:ge-0/0/57:10.4.12.6:",
                    "admin": "Up",
                    "oper": "Up",
                    "connector": "",
                    "phy_Equipped": "",
                    "auto_negotiation": "Complete",
                    "rate": "1000",
                    "duplex": "Full",
                    "mac": "00-20-D2-5D-65-58",
                    "phy_ConnectorInterface": "LC",
                    "phy_Manufacturer": "PROLABS",
                    "phy_PartNumber": "SFPC55-80-JA",
                    "opt_Range": "80000",
                    "opt_Wavelength": "1550.00",
                    "phy_FiberType": "SM",
                    "mac_egressMtu": "12000",
                    "mac_l2cp": "network",
                },
            },
            {
                "type": "Ethernet",
                "id": "2",
                "name": "ETH-2",
                "admin_state": "Down",
                "operational_state": "Down",
                "rate": "1000000000",
                "details": {
                    "name": "ETH-2",
                    "admin": "Down",
                    "oper": "Down",
                    "connector": "",
                    "phy_Equipped": "",
                    "auto_negotiation": "Other",
                    "rate": "",
                    "duplex": "",
                    "mac": "18-06-F5-EF-2C-A2",
                    "phy_ConnectorInterface": "SFP",
                    "phy_Manufacturer": "",
                    "phy_PartNumber": "",
                    "opt_Range": "",
                    "opt_Wavelength": "",
                    "phy_FiberType": "",
                },
            },
            {
                "type": "Ethernet",
                "id": "3",
                "name": "EP-UNI:FIA:USTUD",
                "admin_state": "Up",
                "operational_state": "Up",
                "rate": "1000000000",
                "details": {
                    "name": "EP-UNI:FIA:USTUDIO, INC.@1803 WEST AVEBLDG B:51.L1XX.817074..CHTR:",
                    "admin": "Up",
                    "oper": "Up",
                    "connector": "",
                    "phy_Equipped": "",
                    "auto_negotiation": "Complete",
                    "rate": "1000",
                    "duplex": "Full",
                    "mac": "18-06-F5-EF-2C-A3",
                    "phy_ConnectorInterface": "RJ45",
                    "phy_Manufacturer": "",
                    "phy_PartNumber": "",
                    "opt_Range": "",
                    "opt_Wavelength": "",
                    "phy_FiberType": "",
                    "mac_egressMtu": "12000",
                    "mac_l2cp": "EP-UNI",
                },
            },
            {
                "type": "Ethernet",
                "id": "4",
                "name": "ETH-4",
                "admin_state": "Down",
                "operational_state": "Down",
                "rate": "1000000000",
                "details": {
                    "name": "ETH-4",
                    "admin": "Down",
                    "oper": "Down",
                    "connector": "",
                    "phy_Equipped": "",
                    "auto_negotiation": "Other",
                    "rate": "",
                    "duplex": "",
                    "mac": "18-06-F5-EF-2C-A4",
                    "phy_ConnectorInterface": "RJ45",
                    "phy_Manufacturer": "",
                    "phy_PartNumber": "",
                    "opt_Range": "",
                    "opt_Wavelength": "",
                    "phy_FiberType": "",
                },
            },
            {
                "type": "Ethernet",
                "id": "5",
                "name": "EP-UNI:VOICE:UST",
                "admin_state": "Up",
                "operational_state": "Up",
                "rate": "1000000000",
                "details": {
                    "name": "EP-UNI:VOICE:USTUDIO, INC.@1803 WEST AVEBLDG B:51.HNXN.000221..CHTR:",
                    "admin": "Up",
                    "oper": "Up",
                    "connector": "",
                    "phy_Equipped": "",
                    "auto_negotiation": "Complete",
                    "rate": "1000",
                    "duplex": "Full",
                    "mac": "18-06-F5-EF-2C-A5",
                    "phy_ConnectorInterface": "RJ-45",
                    "phy_Manufacturer": "Methode Elec.",
                    "phy_PartNumber": "SFP-1GE-FE-E-T-C",
                    "opt_Range": "100",
                    "opt_Wavelength": "",
                    "phy_FiberType": "Not",
                    "mac_egressMtu": "12000",
                    "mac_l2cp": "EP-UNI",
                },
            },
            {
                "type": "Ethernet",
                "id": "6",
                "name": "ETH-6",
                "admin_state": "Down",
                "operational_state": "Down",
                "rate": "1000000000",
                "details": {
                    "name": "ETH-6",
                    "admin": "Down",
                    "oper": "Down",
                    "connector": "",
                    "phy_Equipped": "",
                    "auto_negotiation": "Other",
                    "rate": "",
                    "duplex": "",
                    "mac": "18-06-F5-EF-2C-A6",
                    "phy_ConnectorInterface": "SFP",
                    "phy_Manufacturer": "",
                    "phy_PartNumber": "",
                    "opt_Range": "",
                    "opt_Wavelength": "",
                    "phy_FiberType": "",
                },
            },
            {
                "type": "Ethernet",
                "id": "101",
                "name": "MNG-ETH",
                "admin_state": "Up",
                "operational_state": "Down",
                "rate": "100000000",
                "details": {
                    "name": "MNG-ETH",
                    "admin": "Up",
                    "oper": "Down",
                    "connector": "RJ45",
                    "phy_Equipped": "",
                    "auto_negotiation": "Other",
                    "rate": "",
                    "duplex": "",
                    "mac": "00-20-D2-5D-65-58",
                    "phy_ConnectorInterface": "",
                    "phy_Manufacturer": "",
                    "phy_PartNumber": "",
                    "opt_Range": "",
                    "opt_Wavelength": "",
                    "phy_FiberType": "",
                },
            },
            {
                "type": "SVI",
                "id": "1",
                "name": "INBAND-MGMT",
                "admin_state": "Up",
                "operational_state": "Up",
                "rate": "0",
                "details": {"mac_egressMtu": "", "mac_l2cp": "", "name": "INBAND-MGMT"},
            },
            {
                "type": "SVI",
                "id": "96",
                "name": "SVI 96",
                "admin_state": "Up",
                "operational_state": "Up",
                "rate": "0",
                "details": {},
            },
        ],
    }

    monkeypatch.setattr(serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: shelf_ports)
    monkeypatch.setattr(serviceable_shelf, "cpe_service_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        serviceable_shelf, "serviceable_shelf_port_available_on_network", lambda *args, **kwargs: network_ports
    )
    monkeypatch.setattr(serviceable_shelf, "underlay_topology_model_available_handoffs", lambda *args, **kwargs: [{}])
    monkeypatch.setattr(serviceable_shelf, "rad_admin_down_network_ports", lambda *args, **kwargs: None)

    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    # bad test - abort No usable ports after comparing Granite and the network
    monkeypatch.setattr(serviceable_shelf, "rad_admin_down_network_ports", lambda *args, **kwargs: True)
    monkeypatch.setattr(serviceable_shelf, "assign_port", lambda *args, **kwargs: None)

    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")

    #
    monkeypatch.setattr(
        serviceable_shelf, "assign_port", lambda *args, **kwargs: {"EQUIP_NAME": "CHTPMIAG2ZW/999.9999.999.99/SWT"}
    )
    monkeypatch.setattr(
        serviceable_shelf, "get_transport_path", lambda *_: ("1911263", "51001.GE1.AUSBTX520QW.AUSNTX181ZW")
    )
    monkeypatch.setattr(serviceable_shelf, "validate_transport_path", lambda *_: (True, True))
    monkeypatch.setattr(
        serviceable_shelf,
        "trans_path_upgrade",
        lambda *args, **kwargs: (
            {},
            "new_shelf",
            {"pathId": "51001.GE10.AUSBTX520QW.AUSNTX182ZW", "pathInstanceId": "1998932"},
        ),
    )
    monkeypatch.setattr(serviceable_shelf, "get_related_cid", lambda *args, **kwargs: ("cid", "1"))
    monkeypatch.setattr(
        serviceable_shelf, "_granite_create_circuit_revision", lambda *args, **kwargs: ("result", "instance", "path")
    )
    monkeypatch.setattr(serviceable_shelf, "cpe_10g_swap", lambda *args, **kwargs: None)
    monkeypatch.setattr(serviceable_shelf, "remove_1G_transport", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        serviceable_shelf,
        "get_equipment_buildout_v2",
        lambda *args, **kwargs: [{"VENDOR": "RAD", "MODEL": "FSP 150-XG108"}],
    )
    monkeypatch.setattr(
        "arda_app.bll.models.device_topology.underlay.UnderlayDeviceTopologyModel._set_uplink", lambda self: None
    )
    monkeypatch.setattr(
        "arda_app.bll.models.device_topology.underlay.UnderlayDeviceTopologyModel._set_secondary_uplink",
        lambda self: None,
    )
    monkeypatch.setattr("arda_app.bll.serviceable_shelf._build_handoff", lambda *args, **kwargs: "115022425")
    monkeypatch.setattr(
        serviceable_shelf,
        "get_port_udas",
        lambda *args, **kwargs: [{"EQUIP_NAME": "CHTPMIAG2ZW/999.9999.999.99/SWT", "PORT_ACCESS_ID": "ACCESS-1-1-1-3"}],
    )
    monkeypatch.setattr(serviceable_shelf, "_set_uni_type", lambda *args, **kwargs: None)

    response = {
        "cpe_shelf": "CHTPMIAG2ZW/999.9999.999.99/SWT",
        "cpe_tid": "CHTPMIAG2ZW",
        "cpe_handoff": "115022425",
        "cpe_handoff_paid": "ACCESS-1-1-1-3",
        "zw_transport_path_name": "51001.GE10.AUSBTX520QW.AUSNTX182ZW",
        "zw_transport_path_inst_id": "1998932",
        "circ_path_inst_id": "1890963",
        "transport_upgrade": True,
        "hub_work_required": True,
    }
    assert serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "Access", "z_side") == response

    # good test - trunked port
    response["cpe_trunked_path"] = "51001.GE10.AUSNTX182ZW.AUSNTX182ZW"
    monkeypatch.setattr(
        serviceable_shelf, "_create_trunked_handoff", lambda *args, **kwargs: "51001.GE10.AUSNTX182ZW.AUSNTX182ZW"
    )
    assert serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "Trunked", "z_side") == response

    # bad test - more than one cpe shelf found at side
    site_shelves[0]["EQUIP_MODEL"] = "FSP 150CCF-825"
    with pytest.raises(AbortException):
        serviceable_shelf.serviceable_shelf_handoff("cid", "Gbps", "1", "LC", "access", "z_side")


@pytest.mark.unittest
def test_get_related_cid(monkeypatch):
    # bad test - unable to find circuit for transport path
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: {})
    with pytest.raises(AbortException):
        serviceable_shelf.get_related_cid("51001.GE10.AUSBTX520QW.AUSNTX182ZW")

    monkeypatch.setattr(
        serviceable_shelf,
        "get_granite",
        lambda *args, **kwargs: [{"MEMBER_PATH": "51.L1XX.817074..CHTR", "pathRev": "23.L1XX.989319..CHTR"}],
    )
    assert serviceable_shelf.get_related_cid("51001.GE10.AUSBTX520QW.AUSNTX182ZW") == (
        "51.L1XX.817074..CHTR",
        "23.L1XX.989319..CHTR",
    )

    # bad test - abort Unable to retreive path information
    responses = iter([[{"MEMBER_PATH": "51.L1XX.817074..CHTR"}], {}])
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda url: next(responses))

    with pytest.raises(AbortException):
        serviceable_shelf.get_related_cid("51001.GE10.AUSBTX520QW.AUSNTX182ZW")


@pytest.mark.unittest
def test_get_transport_path(monkeypatch):
    # bad test - abort no transport path found for device
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: {})
    with pytest.raises(AbortException):
        serviceable_shelf.get_transport_path("AUSNTX182ZW/testcpe")

    # bad test - abort no live transports found for serviceable shelf
    response = [
        {
            "CIRCUIT_STATUS": "design",
            "SERVICE_TYPE": "test",
            "CIRCUIT_NAME": "51001.GE10.AUSBTX520QW.AUSNTX182ZW",
            "CIRC_PATH_INST_ID": "12345",
        },
        {
            "CIRCUIT_STATUS": "design",
            "SERVICE_TYPE": "test",
            "CIRCUIT_NAME": "51001.GE10.AUSBTX520QW.AUSNTX182ZW",
            "CIRC_PATH_INST_ID": "12345",
        },
    ]
    monkeypatch.setattr(serviceable_shelf, "get_granite", lambda *args, **kwargs: response)
    with pytest.raises(AbortException):
        serviceable_shelf.get_transport_path("AUSNTX182ZW/testcpe")

    # bad test - abort more than one live parent found to serviceable shelf
    response[0]["CIRCUIT_STATUS"] = "Live"
    response[1]["CIRCUIT_STATUS"] = "Live"
    with pytest.raises(AbortException):
        serviceable_shelf.get_transport_path("AUSNTX182ZW/testcpe")

    # good test
    response[0]["CIRCUIT_STATUS"] = "design"
    assert serviceable_shelf.get_transport_path("AUSNTX182ZW/testcpe") == ("12345", "51001.GE10.AUSBTX520QW.AUSNTX182ZW")


@pytest.mark.unittest
def test_card_template_check(monkeypatch):
    # Test case 1: FIXED PORTS slot returns unchanged
    port = {"SLOT": "FIXED PORTS", "EQUIP_NAME": "TEST_EQUIP"}
    assert serviceable_shelf.card_template_check(port, "ACCESS-1-1-1", "TEST_TEMPLATE") == port

    # Test case 4: Matching card template returns unchanged
    port = {"SLOT": "USER 1", "CARD_TEMPLATE": "SAME_TEMPLATE", "EQUIP_NAME": "TEST_EQUIP"}
    assert serviceable_shelf.card_template_check(port, "ACCESS-1-1-1", "SAME_TEMPLATE") == port

    # Test case 5: Mismatched card template deletes and updates
    port = {"SLOT": "USER 1", "CARD_TEMPLATE": "OLD_TEMPLATE", "EQUIP_NAME": "TEST_EQUIP", "SLOT_INST_ID": "12345"}
    updated_port = {"SLOT": "USER 1", "EQUIP_NAME": "TEST_EQUIP", "SLOT_INST_ID": "12345"}
    second_updated_port = {
        "SLOT": "USER 1",
        "EQUIP_NAME": "TEST_EQUIP",
        "SLOT_INST_ID": "12345",
        "PORT_INST_ID": "67890",
    }
    final_updated_port = {
        "SLOT": "USER 1",
        "EQUIP_NAME": "TEST_EQUIP",
        "SLOT_INST_ID": "12345",
        "PORT_INST_ID": "67890",
        "PORT_ACCESS_ID": "ACCESS-1-1-1",
    }
    buildout = iter([updated_port, second_updated_port, final_updated_port])
    monkeypatch.setattr(serviceable_shelf, "delete_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: [next(buildout)])
    monkeypatch.setattr(serviceable_shelf, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(serviceable_shelf, "put_port_access_id", lambda *args, **kwargs: None)

    assert serviceable_shelf.card_template_check(port, "ACCESS-1-1-1", "NEW_TEMPLATE") == final_updated_port


@pytest.mark.unittest
def test_serviceable_shelf(monkeypatch, client):
    url = "/arda/v1/serviceable_shelf"
    monkeypatch.setattr(ss, "serviceable_shelf_main", lambda *_: serviceable_shelf_handoff_resp, 201)
    logger.debug("UNIT TEST: test_serviceable_shelf")
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 201


@pytest.mark.unittest
def test_serviceable_shelf_with_mbps_bandwidth(monkeypatch, client):
    url = "/arda/v1/serviceable_shelf"
    test_payload["agg_bandwidth"] = "Mbps"

    monkeypatch.setattr(ss, "serviceable_shelf_main", lambda *_: serviceable_shelf_handoff_resp, 201)
    logger.debug("UNIT TEST: test_serviceable_shelf_with_mbps_bandwidth")
    r = client.post(url, json=test_payload, headers=head, auth=auth)
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 201


@pytest.mark.unittest
def test_serviceable_shelf_with_invalid_bandwidth(client):
    url = "/arda/v1/serviceable_shelf"
    test_payload["agg_bandwidth"] = "Kbps"

    logger.debug("UNIT TEST: test_serviceable_shelf_with_invalid_bandwidth")
    try:
        client.post(url, json=test_payload, headers=head, auth=auth)
    except AbortException as e:
        logger.debug(f"Response status code - {e.code}")
        assert e.code == 400


@pytest.mark.unittest
def test_serviceable_shelf_with_no_cid(client):
    url = "/arda/v1/serviceable_shelf"
    test_payload.pop("cid")

    logger.debug("UNIT TEST: test_serviceable_shelf_with_no_cid")
    try:
        client.post(url, json=test_payload, headers=head, auth=auth)
    except AbortException as e:
        logger.debug(f"Response status code - {e.code}")
        assert e.code == 400


@pytest.mark.unittest
def test_serviceable_shelf_with_json_decode_error(monkeypatch, client):
    url = "/arda/v1/serviceable_shelf"
    logger.debug("UNIT TEST: test_serviceable_shelf_with_json_decode_error")

    r = client.post(url, json="ab1")
    logger.debug(f"Response status code - {r.status_code}")
    assert r.status_code == 500


@pytest.mark.unittest
def test_validate_transport_path(monkeypatch):
    # bad test - parent_device name ends in "09"
    with pytest.raises(AbortException):
        serviceable_shelf.validate_transport_path("123", "test.TESTO9.device", 1000, {})

    # bad test - get_equipment_buildout returns a dict
    monkeypatch.setattr(serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: {})
    with pytest.raises(AbortException):
        serviceable_shelf.validate_transport_path("123", "test.path.name", 1000, {})

    # bad test - unsupported EPON parent device
    monkeypatch.setattr(
        serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: [{"EQUIP_TYPE": "OPTICAL LINE TERMINAL"}]
    )
    with pytest.raises(AbortException):
        serviceable_shelf.validate_transport_path("123", "test.path.name", 1000, {})

    # bad test - chosen shelf is not Live
    monkeypatch.setattr(serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: [{"EQUIP_TYPE": "SWITCH"}])
    monkeypatch.setattr(serviceable_shelf, "will_transport_be_oversubscribed", lambda *_: True)
    with pytest.raises(AbortException):
        serviceable_shelf.validate_transport_path("123", "test.path.name", 1000, {"EQUIP_STATUS": "Planned"})

    # bad test - hub_transport_check returns False
    monkeypatch.setattr(serviceable_shelf, "hub_transport_check", lambda *args, **kwargs: False)
    with pytest.raises(AbortException):
        serviceable_shelf.validate_transport_path("123", "test.path.name", 1000, {"EQUIP_STATUS": "Live"})

    # Test 6: Success case
    monkeypatch.setattr(serviceable_shelf, "hub_transport_check", lambda *args, **kwargs: True)
    assert serviceable_shelf.validate_transport_path("123", "test.path.name", 1000, {"EQUIP_STATUS": "Live"}) == (
        True,
        True,
    )


@pytest.mark.unittest
def test_delete_orphan_shelf(monkeypatch):
    # good test return resp
    resp = {"pathInstanceId": "12345", "pathId": "pathId"}
    monkeypatch.setattr(serviceable_shelf, "delete_granite", lambda *args, **kwargs: resp)

    assert serviceable_shelf.delete_orphan_shelf("123456") == resp


@pytest.mark.unittest
def test_set_uni_type(monkeypatch):
    # good test returns None
    monkeypatch.setattr(serviceable_shelf, "put_granite", lambda *args, **kwargs: None)

    assert serviceable_shelf._set_uni_type("123456", "uni-evp", True) is None


@pytest.mark.unittest
def test_assign_port(monkeypatch):
    # Test 1: Exact match - port with matching access ID and connector type
    shelf_ports = [
        {
            "SLOT": "USER 1",
            "PORT_ACCESS_ID": "ETH PORT 1",
            "CONNECTOR_TYPE": "LC",
            "PORT_INST_ID": "12345",
            "EQUIP_NAME": "TEST_EQUIP",
        }
    ]
    network_ports = [("USER 1", "ETH PORT 1", "GENERIC SFP")]

    monkeypatch.setattr(serviceable_shelf, "card_template_check", lambda *args, **kwargs: None)
    assert serviceable_shelf.assign_port(shelf_ports, network_ports, "LC") is None

    # Test 2: Port with PORT_INST_ID but no PORT_ACCESS_ID - needs access ID update
    shelf_ports = [{"SLOT": "USER 2", "PORT_INST_ID": "67890", "EQUIP_NAME": "TEST_EQUIP"}]
    network_ports = [("USER 2", "ETH PORT 2", "GENERIC SFP")]
    updated_shelf = [{"PORT_INST_ID": "67890", "PORT_ACCESS_ID": "ETH PORT 2", "CONNECTOR_TYPE": "LC"}]

    monkeypatch.setattr(serviceable_shelf, "put_port_access_id", lambda *args, **kwargs: None)
    monkeypatch.setattr(serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: updated_shelf)

    assert serviceable_shelf.assign_port(shelf_ports, network_ports, "LC") is None

    # Test 3: Port without PORT_INST_ID - needs card template insertion
    shelf_ports = [{"SLOT": "USER 3", "EQUIP_NAME": "TEST_EQUIP", "SLOT_INST_ID": "slot789"}]
    network_ports = [("USER 3", "ETH PORT 3", "GENERIC SFP")]

    first_update = [{"SLOT_INST_ID": "slot789", "PORT_INST_ID": "new_port_123"}]
    final_update = [{"PORT_INST_ID": "new_port_123", "PORT_ACCESS_ID": "ETH PORT 3"}]

    buildout_iter = iter([first_update, final_update])
    monkeypatch.setattr(serviceable_shelf, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(serviceable_shelf, "get_equipment_buildout", lambda *args, **kwargs: next(buildout_iter))

    assert serviceable_shelf.assign_port(shelf_ports, network_ports, "LC") == final_update[0]


@pytest.mark.unittest
def test_adva_admin_down_network_ports():
    # Test 1: XG108 model - uses direct network_ports structure
    network_ports_xg108 = [
        {"properties": {"name": "ETH-1", "admin_state": "unassigned"}},
        {"properties": {"name": "ETH-2", "admin_state": "assigned"}},
        {"properties": {"name": "ETH-3", "admin_state": "unassigned"}},
    ]
    handoff_ports = [("SLOT1", "ETH-1", "TEMPLATE1"), ("SLOT2", "ETH-3", "TEMPLATE2")]

    assert serviceable_shelf.adva_admin_down_network_ports(network_ports_xg108, handoff_ports, "XG108") == handoff_ports

    # Test 2: Non-XG108 model - uses network_ports[0]["eth"] structure
    network_ports_other = [
        {
            "eth": [
                {"properties": {"name": "ETH-4", "admin_state": "unassigned"}},
                {"properties": {"name": "ETH-5", "admin_state": "assigned"}},
            ]
        }
    ]
    handoff_ports = [("SLOT3", "ETH-4", "TEMPLATE3")]

    assert (
        serviceable_shelf.adva_admin_down_network_ports(network_ports_other, handoff_ports, "OTHER_MODEL")
        == handoff_ports
    )

    # Test 3: No matching ports
    network_ports_no_match = [{"properties": {"name": "ETH-6", "admin_state": "assigned"}}]
    handoff_ports = [("SLOT4", "ETH-7", "TEMPLATE4")]

    assert serviceable_shelf.adva_admin_down_network_ports(network_ports_no_match, handoff_ports, "114PRO") == []

    # Test 4: KeyError handling - missing admin_state
    network_ports_keyerror = [
        {"properties": {"name": "ETH-8"}},
        {"properties": {"name": "ETH-9", "admin_state": "unassigned"}},
    ]
    handoff_ports = [("SLOT5", "ETH-9", "TEMPLATE5")]

    assert (
        serviceable_shelf.adva_admin_down_network_ports(network_ports_keyerror, handoff_ports, "114S") == handoff_ports
    )


@pytest.mark.unittest
def test_rad_admin_down_network_ports():
    # Test 1: Matching ports with admin and oper Down
    network_ports = [
        {"name": "ETH-1", "details": {"oper": "Down", "admin": "Down"}},
        {"name": "ETH-2", "details": {"oper": "Up", "admin": "Down"}},
        {"name": "ETH-3", "details": {"oper": "Down", "admin": "Down"}},
        {"name": "MGMT-1", "details": {"oper": "Down", "admin": "Down"}},
    ]
    handoff_ports = [("SLOT1", "ETH PORT 1", "TEMPLATE1"), ("SLOT2", "ETH PORT 3", "TEMPLATE2")]

    assert serviceable_shelf.rad_admin_down_network_ports(network_ports, handoff_ports) == handoff_ports

    # Test 2: No matching ports - different admin/oper states
    network_ports_no_match = [
        {"name": "ETH-4", "details": {"oper": "Up", "admin": "Up"}},
        {"name": "ETH-5", "details": {"oper": "Down", "admin": "Up"}},
    ]
    handoff_ports = [("SLOT3", "ETH PORT 4", "TEMPLATE3")]

    assert serviceable_shelf.rad_admin_down_network_ports(network_ports_no_match, handoff_ports) == []

    # Test 3: KeyError handling - missing details
    network_ports_keyerror = [{"name": "ETH-6"}, {"name": "ETH-7", "details": {"oper": "Down", "admin": "Down"}}]
    handoff_ports = [("SLOT4", "ETH PORT 7", "TEMPLATE4")]

    assert serviceable_shelf.rad_admin_down_network_ports(network_ports_keyerror, handoff_ports) == handoff_ports

    # Test 4: Non-ETH ports filtered out
    network_ports_mixed = [
        {"name": "ETH-8", "details": {"oper": "Down", "admin": "Down"}},
        {"name": "MGMT-2", "details": {"oper": "Down", "admin": "Down"}},
    ]
    handoff_ports = [("SLOT5", "ETH PORT 8", "TEMPLATE5"), ("SLOT6", "MGMT PORT 2", "TEMPLATE6")]

    assert serviceable_shelf.rad_admin_down_network_ports(network_ports_mixed, handoff_ports) == [handoff_ports[0]]


@pytest.mark.unittest
def test_underlay_topology_model_available_handoffs(monkeypatch):
    # Mock the UnderlayDeviceTopologyModel class and its methods
    mock_handoff_ports = [("SLOT1", "ETH PORT 1", "TEMPLATE1"), ("SLOT2", "ETH PORT 2", "TEMPLATE2")]

    class MockUnderlayDeviceTopologyModel:
        def __init__(self, role, device_bw, connector_type, vendor, model):
            self.role = role
            self.device_bw = device_bw
            self.connector_type = connector_type
            self.vendor = vendor
            self.model = model

        def get_available_handoff_ports(self, circuit_bandwidth):
            return mock_handoff_ports

    monkeypatch.setattr(serviceable_shelf, "UnderlayDeviceTopologyModel", MockUnderlayDeviceTopologyModel)

    # Test function call
    assert (
        serviceable_shelf.underlay_topology_model_available_handoffs("ETX203AX/2SFP/2UTP2SFP", "1 Gbps", "RAD", "LC")
        == mock_handoff_ports
    )
