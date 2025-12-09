from unittest.mock import Mock

import pytest
from pytest import raises

from arda_app.bll.models.payloads.ip_reservation import IPReservationPayloadModel, SideInfo
from arda_app.bll.net_new.ip_reservation import ip_reservation_main as ipr_main, assign_ip
from arda_app.bll.net_new.ip_reservation.utils import mdso_utils
from thefuzz import fuzz

IPR_PAYLOAD = {
    "z_side_info": SideInfo(
        service_type="net_new_cj",
        product_name="Fiber Internet Access",
        engineering_id="ENG-03413018",
        cid="51.L1XX.008342..CHTR",
        build_type="MTU New Build",
        ipv4_type="LAN",
        block_size="/30=1",
    )
}


@pytest.mark.unittest
def test_ip_delegation(monkeypatch):
    message = {"ipv4_service_type": "LAN"}
    payload = IPReservationPayloadModel(**IPR_PAYLOAD)
    monkeypatch.setattr(ipr_main, "assign_static_ip_main", Mock(return_value={"ipv4_service_type": "LAN"}))
    monkeypatch.setattr(ipr_main, "_check_ip_subnets", Mock(return_value=None))
    # Fiber Internet Access
    assert ipr_main.ip_delegation(payload) == message

    # Hosted Voice - (Fiber)
    payload.z_side_info.product_name = "Hosted Voice - (Fiber)"
    assert ipr_main.ip_delegation(payload) == message

    # SIP - Trunk (Fiber)
    payload.z_side_info.product_name = "SIP - Trunk (Fiber)"
    assert ipr_main.ip_delegation(payload) == message

    # FC + Remote PHY
    payload.z_side_info.product_name = "FC + Remote PHY"
    monkeypatch.setattr(ipr_main, "confirm_router_supports_rphy", Mock(return_value=message))
    assert ipr_main.ip_delegation(payload) == message


@pytest.mark.unittest
def test_confirm_router_supports_rphy(monkeypatch):
    monkeypatch.setattr(mdso_utils, "get_connection_info", Mock(return_value=("hostname", "leg_name")))
    monkeypatch.setattr(mdso_utils, "check_router_ip_block", Mock(return_value="10.0.0.1 /20"))
    monkeypatch.setattr(
        mdso_utils, "get_block_by_blockname", Mock(return_value={"numassignedhosts": 1, "numaddressablehosts": 1})
    )

    with pytest.raises(Exception):
        assert ipr_main.confirm_router_supports_rphy("cid") is None

    monkeypatch.setattr(mdso_utils, "get_block_by_blockname", lambda *args, **kwargs: {"badkey1": 1, "badkey2": 1})

    with pytest.raises(Exception):
        assert ipr_main.confirm_router_supports_rphy("cid") is None


@pytest.mark.unittest
def test_get_connection_info(monkeypatch):
    circuit_data = [{"ELEMENT_NAME": "test.test", "LEG_NAME": "test/test"}]
    monkeypatch.setattr(mdso_utils, "get_path_elements", Mock(return_value=circuit_data))

    with pytest.raises(Exception):
        assert mdso_utils.get_connection_info("cid") is None

    circuit_data[0]["ELEMENT_NAME"] = "test.test.CW"
    assert mdso_utils.get_connection_info("cid") == ("CW", "test")

    monkeypatch.setattr(mdso_utils, "get_path_elements", Mock(return_value=circuit_data))
    with pytest.raises(Exception):
        assert mdso_utils.get_connection_info("cid") is None

    circuit_data[0]["ELEMENT_NAME"] = "test.test.None"
    monkeypatch.setattr(mdso_utils, "get_path_elements", Mock(return_value=circuit_data))

    with pytest.raises(Exception):
        assert mdso_utils.get_connection_info("cid") is None


@pytest.mark.unittest
def test_network_gateway_ip(monkeypatch):
    ips = [
        "107.144.153.168",
        "107.144.153.169",
        "107.144.153.170",
        "107.144.153.171",
        "107.144.153.172",
        "107.144.153.173",
        "107.144.153.174",
        "107.144.153.175",
    ]
    monkeypatch.setattr(assign_ip, "get_ips_from_subnet", lambda *args, **kwargs: ips)
    test_ip = "107.144.153.168/30"
    network_ip, gateway_ip = assign_ip.get_network_and_gateway_ip(test_ip)

    assert network_ip == "107.144.153.168"
    assert gateway_ip == "107.144.153.169"

    test_ip = "107.144.153.169/30"
    network_ip, gateway_ip = assign_ip.get_network_and_gateway_ip(test_ip)

    assert network_ip == "107.144.153.168"
    assert gateway_ip == "107.144.153.169"

    test_ip = "107.144.153.900/30"
    with raises(Exception):
        assert assign_ip.get_network_and_gateway_ip(test_ip) is None


@pytest.mark.unittest
def test_check_for_retaining_address(monkeypatch):
    z_side_info = SideInfo(
        service_type="change_logical",
        product_name="Fiber Internet Access",
        engineering_id="ENG-12345689",
        cid="81.L1XX.014725..CHTR",
        build_type="Home Run",
        ipv4_type="LAN",
        block_size="/30=1",
        retain_ip_addresses="Yes",
        ip_address="107.144.153.169/29",
    )
    data = {
        "CIRC_PATH_INST_ID": "2642154",
        "PATH_NAME": "81.L1XX.014725..CHTR",
        "PATH_REV": "1",
        "PATH_CATEGORY": "ETHERNET",
        "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
        "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
        "A_CLLI": "KSCDMO14",
        "Z_CLLI": "KSCIMO98",
        "PATH_A_SITE_TYPE": "HUB",
        "PATH_Z_SITE_TYPE": "LOCAL",
        "TOPOLOGY": "Point-to-point",
        "PATH_STATUS": "Auto-Planned",
        "CLASS_OF_SERVICE": None,
        "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
        "EVC_ID": None,
        "SERVICE_TYPE": "COM-DIA",
        "BANDWIDTH": "1 Gbps",
        "BW_SIZE": "1000000000",
        "CUSTOMER_ID": "ACCT-01661556",
        "CUSTOMER_NAME": "KANSAS CITY MASTER TENANT, LLC DBA 21C MUSEUM HOTEL KANSAS C",
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
        "LEG_INST_ID": "3074460",
        "A_SITE_NAME": None,
        "Z_SITE_NAME": None,
        "ELEMENT_TYPE": "CLOUD",
        "ELEMENT_NAME": "CHTRSE.EDNA.MPLS",
        "ELEMENT_REFERENCE": "1180",
        "ELEMENT_CATEGORY": "MPLS",
        "ELEMENT_STATUS": "Live",
        "ELEMENT_BANDWIDTH": None,
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
    }
    network_ip = "107.144.153.168"
    gateway_ip = "107.144.153.169"
    ipc_resp = {
        "blockAddr": "107.144.153.168",
        "blockName": "107.144.153.168/29",
        "blockSize": "29",
        "blockStatus": "Deployed",
        "blockType": "RIP-DIA",
        "cloudObjectId": "",
        "container": "/Commercial/LBHN/TampaBay/Customer",
        "createDate": "2023-03-13 10:29:55",
        "createReverseDomains": "false",
        "description": "",
        "discoveryAgent": "InheritFromContainer",
        "excludeFromDiscovery": "false",
        "ipv6": False,
        "lastUpdateDate": "2025-03-31 15:55:45",
        "nonBroadcast": False,
        "primarySubnet": False,
        "userDefinedFields": [
            "Delete_Block=off",
            "Day=",
            "Month=",
            "Year=",
            "TampaBay_Division=TW-TampaBay",
            "Company_Name=ACCESS HEALTH CARE PHYSICIANS",
            "Account_Number=8337130121220620",
            "Notes=SEEFA_SENSE-12345689,\n35.L1XX.001005..CHTR,\n233 DELLA CT",
            "Notes_2=",
            "Service_Type=Fiber",
        ],
    }
    ipc_post_response = None
    monkeypatch.setattr(ipr_main, "get_subnet_block_by_ip", lambda *args: ipc_resp)
    monkeypatch.setattr(assign_ip, "get_network_and_gateway_ip", lambda *args, **kwargs: network_ip, gateway_ip)
    monkeypatch.setattr(ipr_main, "ipc_post", lambda *args, **kwargs: ipc_post_response)
    assert ipr_main.check_for_retaining_address(z_side_info, data) is ipc_post_response


@pytest.mark.unittest
def test_ip_reservation_main(monkeypatch):
    payload = {
        "z_side_info": {
            "service_type": "change_logical",
            "product_name": "Fiber Internet Access",
            "engineering_id": "SEEFA_SENSE",
            "cid": "81.L1XX.014725..CHTR",
            "build_type": "Home Run",
            "ipv4_type": "LAN",
            "block_size": "/30=1",
            "retain_ip_addresses": "Yes",
            "ip_address": "173.197.31.104/30",
        }
    }
    payload = IPReservationPayloadModel(
        z_side_info=SideInfo(
            service_type="change_logical",
            product_name="Fiber Internet Access",
            engineering_id="SEEFA_SENSE",
            cid="81.L1XX.014725..CHTR",
            build_type="Home Run",
            ipv4_type="LAN",
            block_size="/30=1",
            retain_ip_addresses="Yes",
            ip_address="173.197.31.104/30",
        ),
        a_side_info=None,
    )
    granite_response = [
        {
            "CIRC_PATH_INST_ID": "2642154",
            "PATH_NAME": "81.L1XX.014725..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCIMO98",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Auto-Planned",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01661556",
        },
        {
            "CIRC_PATH_INST_ID": "2642154",
            "PATH_NAME": "81.L1XX.014725..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCIMO98",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Auto-Planned",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01661556",
        },
        {
            "CIRC_PATH_INST_ID": "2642154",
            "PATH_NAME": "81.L1XX.014725..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCIMO98",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Auto-Planned",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01661556",
        },
        {
            "CIRC_PATH_INST_ID": "2642154",
            "PATH_NAME": "81.L1XX.014725..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCIMO98",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Auto-Planned",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-DIA",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01661556",
        },
        {
            "CIRC_PATH_INST_ID": "1215027",
            "PATH_NAME": "81001.GE40L.KSCDMO141CW.KSCDMO140QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCDMO14",
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
            "CIRC_PATH_INST_ID": "1215027",
            "PATH_NAME": "81001.GE40L.KSCDMO141CW.KSCDMO140QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCDMO14",
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
            "CIRC_PATH_INST_ID": "1215027",
            "PATH_NAME": "81001.GE40L.KSCDMO141CW.KSCDMO140QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCDMO14",
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
            "CIRC_PATH_INST_ID": "1215027",
            "PATH_NAME": "81001.GE40L.KSCDMO141CW.KSCDMO140QW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCDMO14",
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
            "CIRC_PATH_INST_ID": "2219868",
            "PATH_NAME": "81001.GE10.KSCDMO140QW.KSCIMO981ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCIMO98",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
            "BANDWIDTH": "10 Gbps",
            "BW_SIZE": "10000000000",
            "CUSTOMER_ID": None,
        },
        {
            "CIRC_PATH_INST_ID": "2219868",
            "PATH_NAME": "81001.GE10.KSCDMO140QW.KSCIMO981ZW",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "KSCDMO14-TWC/HUB L-PITTMAN",
            "PATH_Z_SITE": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
            "A_CLLI": "KSCDMO14",
            "Z_CLLI": "KSCIMO98",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": None,
            "EVC_ID": None,
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
            "BANDWIDTH": "10 Gbps",
            "BW_SIZE": "10000000000",
            "CUSTOMER_ID": None,
        },
    ]

    network_ip = "173.197.31.104"
    gateway_ip = "173.197.31.105"
    ipc_resp = {
        "blockAddr": "173.197.31.104",
        "blockName": "173.197.31.104/30",
        "blockSize": "30",
        "blockStatus": "Deployed",
        "blockType": "RIP-DIA",
        "cloudObjectId": "",
        "container": "/Commercial/LTWC/Texas/KansasCity/Customer",
        "createDate": "2025-04-04 14:43:20",
        "createReverseDomains": "false",
        "description": "",
        "discoveryAgent": "InheritFromContainer",
        "excludeFromDiscovery": "false",
        "ipv6": False,
        "lastUpdateDate": "2025-04-04 14:59:34",
        "nonBroadcast": False,
        "primarySubnet": False,
        "userDefinedFields": [
            "Delete_Block=off",
            "Day=",
            "Month=",
            "Year=",
            "Kansas_City_Divisions=TW-KansasCity",
            "Company_Name=KANSAS CITY MASTER TENANT, LLC",
            "Account_Number=ACCT-01661556",
            "Notes=SEEFA_SENSE,\n81.L1XX.014725..CHTR,\n219 W 9TH ST",
            "Notes_2=",
            "Service_Type=Fiber",
        ],
    }
    fuzz_ratio = 90
    modify_block_response = {"message": "IP block successfully updated"}
    resp = {
        "ipv4_service_type": "LAN",
        "ipv4_glue_subnet": "",
        "ipv4_assigned_subnets": "107.144.153.168",
        "ipv4_assigned_gateway": "107.144.153.169",
        "ipv6_service_type": "ROUTED",
        "ipv6_glue_subnet": "2605:a404:fa0:e4::/64",
        "ipv6_assigned_subnet": "2605:a404:21a6::/48",
    }
    monkeypatch.setattr(ipr_main, "get_granite", lambda *args, **kwargs: granite_response)
    monkeypatch.setattr(ipr_main, "get_network_and_gateway_ip", lambda *args, **kwargs: (network_ip, gateway_ip))
    monkeypatch.setattr(ipr_main, "get_subnet_block_by_ip", lambda *args, **kwargs: ipc_resp)
    monkeypatch.setattr(fuzz, "ratio", lambda *args, **kwargs: fuzz_ratio)
    monkeypatch.setattr(ipr_main, "get_subnet_block_by_ip", lambda *args, **kwargs: ipc_resp)
    monkeypatch.setattr(ipr_main, "modify_block", lambda *args, **kwargs: modify_block_response)
    monkeypatch.setattr(ipr_main, "assign_static_ip_main", lambda *args, **kwargs: resp)
    monkeypatch.setattr(ipr_main, "granite_assignment", lambda *args, **kwargs: None)
    assert ipr_main.ip_delegation(payload) == resp


# @pytest.mark.unittest
# def test_check_router_ip_block(monkeypatch):
#     _validate_mdso_ip_response = iter([False, "/28", False, ""])
#     monkeypatch.setattr(
#         ipr,
#         "_validate_mdso_ip_response",
#         lambda *args, **kwargs: next(_validate_mdso_ip_response),
#     )
#     assert ipr.check_router_ip_block("hostname", "leg_name") == "/28"

#     with pytest.raises(Exception):
#         assert ipr.check_router_ip_block("hostname", "leg_name") is None


# @pytest.mark.unittest
# def test_validate_mdso_ip_response(monkeypatch):
#     mdso_response = {
#         "result": {
#             "configuration": {"interfaces": {"irb": {"unit": {"family": {"inet": {"address": {"name": "name"}}}}}}}
#         }
#     }
#     monkeypatch.setattr(ipr, "onboard_and_exe_cmd", lambda *args, **kwargs: [mdso_response])
#     assert ipr._validate_mdso_ip_response("hostname", "port") == ""

#     monkeypatch.setattr(ipr, "onboard_and_exe_cmd", lambda *args, **kwargs: mdso_response)

#     with pytest.raises(Exception):
#         assert ipr._validate_mdso_ip_response("hostname", "port") is None


# @pytest.mark.unittest
# def test_assign_mtu_ip(monkeypatch):
#     path_elements_data = {
#         "PATH_A_SITE": "PATH_A_SITE",
#         "MODEL": "MODEL",
#         "TID": "TID",
#         "ELEMENT_NAME": "ELEMENT_NAME",
#     }
#     container_name = [{"TID": "container_name"}]
#     path_data = iter(
#         [
#             container_name,
#             [path_elements_data],
#             container_name,
#             [path_elements_data],
#         ]
#     )
#     mgmt_subnet_resp = [{"childBlock": {"blockAddr": "blockAddr", "container": "container"}}]
#     ipAddress = [{"ipAddress": "ipAddress"}]
#     ipc_data = iter(
#         [
#             mgmt_subnet_resp,
#             ipAddress,
#             mgmt_subnet_resp,
#             ipAddress,
#         ]
#     )
#     monkeypatch.setattr(ipr, "get_path_elements", lambda *args, **kwargs: next(path_data))
#     monkeypatch.setattr(ipr, "post_ipc", lambda *args, **kwargs: next(ipc_data))
#     monkeypatch.setattr(ipr, "can_connect", lambda *args, **kwargs: {"accessible": True})

#     with pytest.raises(Exception):
#         assert ipr.assign_mtu_ip("cid") is None

#     monkeypatch.setattr(ipr, "can_connect", lambda *args, **kwargs: {"accessible": False})
#     monkeypatch.setattr(ipr, "put_granite", lambda *args, **kwargs: None)

#     assert ipr.assign_mtu_ip("cid") == {"message": "MTU Management IP has been added successfully."}


# @pytest.mark.unittest
# def test_validate_legacy_company(monkeypatch):
#     circuit_data = [{"TID": "CW", "LEGACY_EQUIP_SOURCE": "test", "test": "test"}]
#     monkeypatch.setattr(ipr, "get_path_elements", lambda *args, **kwargs: circuit_data)
#     monkeypatch.setattr(ipr, "get_company_source_id", lambda *args, **kwargs: "1")

#     with pytest.raises(Exception):
#         assert ipr.get_tid("cid") is None

#     monkeypatch.setattr(ipr, "get_company_source_id", lambda *args, **kwargs: "test")
#     assert ipr.get_tid("cid") == "CW"
