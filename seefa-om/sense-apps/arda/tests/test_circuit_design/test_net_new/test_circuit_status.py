from copy import deepcopy
import pytest
from thefuzz import fuzz
from pytest import raises
from unittest.mock import Mock
from arda_app.bll import circuit_status as cs
from common_sense.common.errors import AbortException

pathid = "20.L4XX.%..CHRT"

data = [{"pathInstanceId": "2", "pathRev": "2"}, {"pathInstanceId": "1", "pathRev": "1"}]

paths_data = [
    {
        "aSideSiteName": "SMRCTX51_TWC/HUB U-SAN MARCOS",
        "bandwidth": "10 Gbps",
        "category": "ETHERNET TRANSPORT",
        "gia_UDA": "NO",
        "off_NetFacility_UDA": "NO",
        "pathId": "51001.GE10.SMRCTX510QW.SMRCTXFI1ZW",
        "pathRev": "1",
        "product_Service_UDA": "INT-ACCESS TO PREM TRANSPORT",
        "servicePriority": "NO",
        "status": "Designed",
        "topology": "P",
        "tspChildPresent_UDA": "NO",
        "zSideSiteName": "SMRCTXFI-THE GRAND AT STONECREEK UAN//450 BARNES DR",
        "instanceProtocol": "9999",
        "pathInstanceId": "1919315",
        "startChanNbr": "1",
        "virtualChans": "D",
    }
]

mock_get_L1_good = [
    {
        "CIRC_PATH_INST_ID": "1842455",
        "PATH_NAME": "51.L1XX.816620..CHTR",
        "PATH_REV": "1",
        "PATH_CATEGORY": "ETHERNET",
        "PATH_A_SITE": "AUSDTXIR_TWC/HE-AUSTIN MDC",
        "PATH_Z_SITE": "AUSXTXZR-SEEFA_TESTING//11921 N MO PAC EXPY",
        "A_CLLI": "AUSDTXIR",
        "Z_CLLI": "AUSXTXZR",
        "PATH_A_SITE_TYPE": "HEAD END",
        "PATH_Z_SITE_TYPE": "LOCAL",
        "TOPOLOGY": "Point-to-point",
        "PATH_STATUS": "Planned",
        "CLASS_OF_SERVICE": None,
        "EVC_ID": None,
        "SERVICE_TYPE": "COM-DIA",
        "BANDWIDTH": "100 Mbps",
        "CUSTOMER_ID": "SEEFA TESTING",
        "CUSTOMER_TYPE": "ENTERPRISE",
        "SEQUENCE": "2",
        "LEG_NAME": "1",
        "LEG_INST_ID": "2088416",
        "A_SITE_NAME": "AUSDTXIR_TWC/HE-AUSTIN MDC",
        "Z_SITE_NAME": "AUSXTXZR-SEEFA_TESTING//11921 N MO PAC EXPY",
        "A_SITE_TYPE": "HEAD END",
        "Z_SITE_TYPE": "LOCAL",
        "ELEMENT_TYPE": "PATH",
        "ELEMENT_NAME": "51001.GE1.AUSDTXIR8CW.AUSXTXZR5ZW",
        "ELEMENT_REFERENCE": "269283",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "ELEMENT_STATUS": "Live",
        "CHAN_NAME": "1",
        "SLOT": None,
        "PORT_NAME": None,
        "PORT_ACCESS_ID": None,
        "FQDN": None,
        "MODEL": None,
        "VENDOR": None,
        "TID": None,
        "MANAGEMENT_IP": None,
        "C-VLAN": None,
        "S-VLAN": None,
        "VLAN_OPERATION": None,
        "INITIAL_PATH_NAME": "51.L1XX.816620..CHTR",
        "INITIAL_CIRCUIT_ID": "1842455",
        "LVL": "1",
        "PORT_INST_ID": "109197749",
    }
]

path_elements = [
    {"TID": "", "PATH_Z_SITE": "zsite_name", "ELEMENT_NAME": "ELEMENT_NAME", "ELEMENT_REFERENCE": "ELEMENT_REFERENCE"}
]

get_zsite_voice_response = [
    {
        "CIRC_PATH_INST_ID": "2582905",
        "CIRCUIT_NAME": "21.L1XX.010107..TWCC",
        "CIRCUIT_STATUS": "Pending Decommission",
        "CIRCUIT_BANDWIDTH": "30 Mbps",
        "CIRCUIT_CATEGORY": "ETHERNET",
        "PREV_PATH_INST_ID": "1814913",
        "SERVICE_TYPE": "COM-DIA",
        "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
        "ORDER_NUM": "D-ENG-04714583,D-ENG-04714583,D-ENG-04714583",
        "A_SITE_NAME": "NYCLNYRG-TWC/HUB C-MANHATTAN",
        "A_SITE_TYPE": "HUB",
        "A_SITE_MARKET": "SOUTHERN MANHATTAN",
        "A_SITE_REGION": "NYC",
        "A_ADDRESS": "409 E 60TH ST",
        "Z_SITE_NAME": "NYCMNYVU-ARTHUR CHERNICK COMPANY INC/1400/370 LEXINGTON AVE",
    }
]
paths_from_site_response = [
    {
        "SITE_INST_ID": "423556",
        "SITE_NAME": "NYCMNYVU-ARTHUR CHERNICK COMPANY INC/1400/370 LEXINGTON AVE",
        "SITE_TYPE": "LOCAL",
        "SITE_STATUS": "Pending Decommission",
        "CIRC_PATH_INST_ID": "2582905",
        "PATH_NAME": "21.L1XX.010107..TWCC",
        "PATH_REV": "3",
        "A_SITE_INST_ID": "80099",
        "A_SITE_NAME": "NYCLNYRG-TWC/HUB C-MANHATTAN",
        "A_SITE_TYPE": "HUB",
        "Z_SITE_INST_ID": "423556",
        "Z_SITE_NAME": "NYCMNYVU-ARTHUR CHERNICK COMPANY INC/1400/370 LEXINGTON AVE",
        "Z_SITE_TYPE": "LOCAL",
        "PATH_TYPE": "ETHERNET",
        "PATH_BW": "30 Mbps",
        "CUSTOMER_ID": "ARTHUR CHERNICK COMPANY INC",
        "PATH_STATUS": "Pending Decommission",
        "SERVICE_TYPE": "COM-DIA",
    },
    {
        "SITE_INST_ID": "423556",
        "SITE_NAME": "NYCMNYVU-ARTHUR CHERNICK COMPANY INC/1400/370 LEXINGTON AVE",
        "SITE_TYPE": "LOCAL",
        "SITE_STATUS": "Pending Decommission",
        "CIRC_PATH_INST_ID": "1814912",
        "PATH_NAME": "21001.GE1.NYCLNYRG4QW.NYCMNYVU1ZW",
        "PATH_REV": "2",
        "A_SITE_INST_ID": "80099",
        "A_SITE_NAME": "NYCLNYRG-TWC/HUB C-MANHATTAN",
        "A_SITE_TYPE": "HUB",
        "Z_SITE_INST_ID": "423556",
        "Z_SITE_NAME": "NYCMNYVU-ARTHUR CHERNICK COMPANY INC/1400/370 LEXINGTON AVE",
        "Z_SITE_TYPE": "LOCAL",
        "PATH_TYPE": "ETHERNET TRANSPORT",
        "PATH_BW": "1 Gbps",
        "PATH_STATUS": "Pending Decommission",
        "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
    },
]


class MockResponse:
    def __init__(self, json_data, status_code=401):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


response = {
    "instId": "0",
    "rev": "1",
    "pathId": f"{pathid}",
    "retCode": 0,
    "retString": "Path Updated",
    "status": "Auto-Designed",
}


@pytest.mark.unittest
def test_update_circuit_status(monkeypatch):
    # path_instance is None
    # "retString" in get_data
    monkeypatch.setattr(cs, "get_granite", lambda _: "retString")

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid) is None

    # Empty Granite response
    monkeypatch.setattr(cs, "get_granite", lambda _: [None, None])

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid, service="bw_change") is None

    # len(get_data) > 1
    # service not in ("bw_change", "change_logical")
    monkeypatch.setattr(cs, "get_granite", lambda _: [1, 2])

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid) is None

    # len(get_data) > 2
    # service in ("bw_change", "change_logical")
    monkeypatch.setattr(cs, "get_granite", lambda _: [1, 2, 3])

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid, service="bw_change") is None

    # len(get_data) > 1
    # "pathRev"[0] and validate values missing
    monkeypatch.setattr(cs, "get_granite", lambda _: [{"pathRev": 1}, {"pathRev": 2}])
    monkeypatch.setattr(cs, "validate_values", lambda *args: True)

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid, service="bw_change") is None

    # "pathRev"[1] and validate first entry values not missing, data values missing
    monkeypatch.setattr(cs, "get_granite", lambda _: data)
    monkeypatch.setattr(cs, "put_granite", lambda *args: response)
    vv = iter([False, True])
    monkeypatch.setattr(cs, "validate_values", lambda *args: next(vv))

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid, service="bw_change") is None

    # uda and not leg
    vv = iter([False, False])
    monkeypatch.setattr(cs, "validate_values", lambda *args: next(vv))

    assert cs.update_circuit_status(pathid, path_instance=True, service="quick_connect", leg=False, uda=True) == {
        "cid": "20.L4XX.%..CHRT",
        "status": "Auto-Designed",
    }

    # "retString" in circuit_info_data
    monkeypatch.setattr(cs, "get_granite", lambda _: "retString")

    with pytest.raises(Exception):
        assert (
            cs.update_circuit_status(
                pathid, "Bright House", path_instance=True, service="quick_connect", leg=True, uda=True
            )
            is None
        )

    # ["ELEMENT_STATUS"] == "Live"
    monkeypatch.setattr(cs, "get_granite", lambda _: mock_get_L1_good)
    monkeypatch.setattr(cs, "validate_values", lambda *args: False)

    assert cs.update_circuit_status(pathid, path_instance=True, leg=True) == {
        "cid": "20.L4XX.%..CHRT",
        "status": "Auto-Designed",
    }

    # ["ELEMENT_STATUS"] == "Designed" and no path
    mock_get_L1_good[0]["ELEMENT_STATUS"] = "Designed"
    mock_get_L1_good[0]["ELEMENT_NAME"] = "51001.GE1.AUSDTXIR8CW.AUSXTXZR5AW"

    assert cs.update_circuit_status(pathid, path_instance=True, leg=True) == {
        "cid": "20.L4XX.%..CHRT",
        "status": "Auto-Designed",
    }

    # no second data pathid
    mock_get_L1_good[0]["ELEMENT_NAME"] = "51001.GE1.AUSDTXIR8CW.AUSXTXZR5ZW"
    res = iter([response, {}])
    monkeypatch.setattr(cs, "put_granite", lambda *args: next(res))

    with pytest.raises(Exception):
        assert cs.update_circuit_status(pathid, path_instance=True, leg=True) is None

    # second data pathid
    monkeypatch.setattr(cs, "put_granite", lambda *args: response)

    assert cs.update_circuit_status(pathid, path_instance=True, leg=True) == {
        "cid": "20.L4XX.%..CHRT",
        "ethernet_transport": "20.L4XX.%..CHRT",
        "status": "Auto-Designed",
    }


@pytest.mark.unittest
def test_update_path_status(monkeypatch):
    body = {
        "cid": "86.L1XX.001113..TWCC",
        "product_name": "EP-LAN (Fiber)",
        "status": "Pending Decommission",
        "service_type": "disconnect",
        "due_date": "2024-01-31",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-04178112",
    }

    response = {
        "message": "Full Disconnect complete",
        "cid_disconnect_data": {
            "pathId": "81.L1XX.912924..CHTR",
            "pathRev": "1",
            "status": "Pending Decommission",
            "pathInstanceId": "1958644",
            "retString": "Path Updated",
        },
        "site_disconnect_data": True,
        "transport_disconnect_data": {
            "pathId": "81001.GE1.HDSNFLJDO99.HDSNFL481ZW",
            "pathRev": "1",
            "status": "Pending Decommission",
            "pathInstanceId": "1963833",
            "retString": "Path Updated",
        },
        "cpe_disconnect_data": {
            "id": "HDSNFL481ZW/999.9999.999.99/SWT",
            "status": "Pending Decommission",
            "equipInstId": "1431442",
            "retString": "Shelf Updated",
        },
        "status": "Pending Decommission",
    }

    get_granite_response = [
        {
            "aSideSiteName": "HDSNFLJD-BHN/HUB TAMP82-HUDSON",
            "bandwidth": "50 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-23992550",
            "orderNumber": "D-ENG-04178112,D-ENG-04178112,D-ENG-04178112",
            "pathId": "81.L1XX.912924..CHTR",
            "pathInService": "2021-02-26 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "COM-EPLAN",
            "servicePriority": "NO",
            "status": "Pending Decommission",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-23992550",
            "zSideSiteName": "HDSNFL48-MCR HEALTH INC//14730 COBRA WAY",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "0",
            "pathInstanceId": "1958644",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ]
    put_granite_response = {
        "pathId": "81.L1XX.912924..CHTR",
        "pathRev": "1",
        "status": "Pending Decommission",
        "pathInstanceId": "1958644",
        "retString": "Path Updated",
    }
    get_path_elements_response = [
        {
            "CIRC_PATH_INST_ID": "1958644",
            "PATH_NAME": "81.L1XX.912924..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "HDSNFLJD-BHN/HUB TAMP82-HUDSON",
            "PATH_Z_SITE": "HDSNFL48-MCR HEALTH INC//14730 COBRA WAY",
            "A_CLLI": "HDSNFLJD",
            "Z_CLLI": "HDSNFL48",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "90937",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "50 Mbps",
            "BW_SIZE": "50000000",
            "CUSTOMER_ID": "ACCT-23992550",
            "CUSTOMER_NAME": "MCR HEALTH INC-NAT",
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
            "LEG_INST_ID": "2220433",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "ELEMENT_REFERENCE": "1405593",
            "ELEMENT_CATEGORY": "VPLS SVC",
            "ELEMENT_STATUS": "Pending Decommission",
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
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "81.L1XX.912924..CHTR",
            "INITIAL_CIRCUIT_ID": "1958644",
            "LVL": "1",
        }
    ]
    get_network_elements_response = [
        {
            "CIRC_PATH_INST_ID": "1405593",
            "PATH_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Pending Decommission",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-BHN",
            "L_NAME": "DAC-MCRH.ELAN",
            "L_ID": "937",
            "SEQUENCE": "10",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1610938",
            "A_SITE_NAME": "BRTNFLUF-BHN/HE TAMP54/TAMP55-MANATEE",
            "Z_SITE_NAME": "BRTOFLBJ-MANATEE COUNTY RURAL/A/712 39TH ST W",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "94.IPXN.000091..TWCC",
            "ELEMENT_REFERENCE": "1502066",
            "ELEMENT_CATEGORY": "PRI TRUNKS",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "10 Mbps",
        },
        {
            "CIRC_PATH_INST_ID": "1405593",
            "PATH_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Pending Decommission",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-BHN",
            "L_NAME": "DAC-MCRH.ELAN",
            "L_ID": "937",
            "SEQUENCE": "11",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1610938",
            "A_SITE_NAME": "BRTNFLUF-BHN/HE TAMP54/TAMP55-MANATEE",
            "Z_SITE_NAME": "BRTOFLCJ-MANATEE COUNTY RURAL HEALTH//2318 MANATEE",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "94.IPXN.000092..TWCC",
            "ELEMENT_REFERENCE": "1502407",
            "ELEMENT_CATEGORY": "PRI TRUNKS",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "10 Mbps",
            "NEXT_PATH_INST_ID": "2352805",
        },
        {
            "CIRC_PATH_INST_ID": "1405593",
            "PATH_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Pending Decommission",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-BHN",
            "L_NAME": "DAC-MCRH.ELAN",
            "L_ID": "937",
            "SEQUENCE": "15",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1610938",
            "A_SITE_NAME": "BRTNFLUF-BHN/HE TAMP54/TAMP55-MANATEE",
            "Z_SITE_NAME": "BRTNFLQX-MANATEE COUNTY RURAL HEALTH SERVICES//1312 MANATEE AVE E",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "94.L1XX.015677..TWCC",
            "ELEMENT_REFERENCE": "1538004",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Canceled",
            "ELEMENT_BANDWIDTH": "40 Mbps",
        },
    ]
    update_network_status_response = {
        "NetworkName": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
        "rev": "1",
        "status": "Pending Decommission",
        "ntwkInstanceId": "1405593",
        "retString": "Network Updated",
    }
    disco_site_update_response = True
    get_path_elements_l1_response = [
        {
            "CIRC_PATH_INST_ID": "1958644",
            "PATH_NAME": "81.L1XX.912924..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "HDSNFLJD-BHN/HUB TAMP82-HUDSON",
            "PATH_Z_SITE": "HDSNFL48-MCR HEALTH INC//14730 COBRA WAY",
            "A_CLLI": "HDSNFLJD",
            "Z_CLLI": "HDSNFL48",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "90937",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "50 Mbps",
            "BW_SIZE": "50000000",
            "CUSTOMER_ID": "ACCT-23992550",
            "CUSTOMER_NAME": "MCR HEALTH INC-NAT",
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
            "LEG_INST_ID": "2220433",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "ELEMENT_REFERENCE": "1405593",
            "ELEMENT_CATEGORY": "VPLS SVC",
            "ELEMENT_STATUS": "Pending Decommission",
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
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "81.L1XX.912924..CHTR",
            "INITIAL_CIRCUIT_ID": "1958644",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "1958644",
            "PATH_NAME": "81.L1XX.912924..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "HDSNFLJD-BHN/HUB TAMP82-HUDSON",
            "PATH_Z_SITE": "HDSNFL48-MCR HEALTH INC//14730 COBRA WAY",
            "A_CLLI": "HDSNFLJD",
            "Z_CLLI": "HDSNFL48",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "90937",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "50 Mbps",
            "BW_SIZE": "50000000",
            "CUSTOMER_ID": "ACCT-23992550",
            "CUSTOMER_NAME": "MCR HEALTH INC-NAT",
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
            "LEG_INST_ID": "2220433",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK",
            "ELEMENT_NAME": "CHTRSE.CEN.FLORIDA.MPLS",
            "ELEMENT_REFERENCE": "1175889",
            "ELEMENT_CATEGORY": "SE MPLS CORE",
            "ELEMENT_STATUS": "Auto-Designed",
            "ELEMENT_BANDWIDTH": "MPLS_CORE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "24481",
            "CHAN_INST_ID": "9186535",
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
            "INITIAL_PATH_NAME": "81.L1XX.912924..CHTR",
            "INITIAL_CIRCUIT_ID": "1958644",
            "LVL": "1",
        },
    ]
    disco_transport_update_response = {
        "pathId": "81001.GE1.HDSNFLJDO99.HDSNFL481ZW",
        "pathRev": "1",
        "status": "Pending Decommission",
        "pathInstanceId": "1963833",
        "retString": "Path Updated",
    }
    disco_cpe_update_response = {
        "id": "HDSNFL481ZW/999.9999.999.99/SWT",
        "status": "Pending Decommission",
        "equipInstId": "1431442",
        "retString": "Shelf Updated",
    }

    second_response = {
        "message": "Full Disconnect complete",
        "cid_disconnect_data": {
            "pathId": "81.L1XX.912924..CHTR",
            "pathRev": "1",
            "status": "Pending Decommission",
            "pathInstanceId": "1958644",
            "retString": "Path Updated",
        },
        "site_disconnect_data": "Multiple live paths found. Did not disconnect site",
        "transport_disconnect_data": {
            "pathId": "81001.GE1.HDSNFLJDO99.HDSNFL481ZW",
            "pathRev": "1",
            "status": "Pending Decommission",
            "pathInstanceId": "1963833",
            "retString": "Path Updated",
        },
        "cpe_disconnect_data": {
            "id": "HDSNFL481ZW/999.9999.999.99/SWT",
            "status": "Pending Decommission",
            "equipInstId": "1431442",
            "retString": "Shelf Updated",
        },
        "status": "Pending Decommission",
    }

    monkeypatch.setattr(cs, "get_granite", lambda _: get_granite_response)
    monkeypatch.setattr(cs, "put_granite", lambda *args: put_granite_response)
    monkeypatch.setattr(cs, "get_path_elements", lambda _: get_path_elements_response)
    monkeypatch.setattr(cs, "get_network_elements", lambda _: get_network_elements_response)
    monkeypatch.setattr(cs, "update_network_status", lambda *args: update_network_status_response)
    monkeypatch.setattr(cs, "disco_site_update", lambda *args: disco_site_update_response)
    monkeypatch.setattr(cs, "get_path_elements_l1", lambda _: get_path_elements_l1_response)
    monkeypatch.setattr(cs, "disco_transport_update", lambda *args, **kwargs: disco_transport_update_response)
    monkeypatch.setattr(cs, "disco_cpe_update", lambda *args, **kwargs: disco_cpe_update_response)
    monkeypatch.setattr(cs, "get_zsite_voice", lambda *args: get_zsite_voice_response)
    monkeypatch.setattr(cs, "paths_from_site", lambda *args: paths_from_site_response)
    assert cs.disco_path_update("86.L1XX.001113..TWCC", body) == response

    paths_from_site_response_copy = deepcopy(paths_from_site_response)
    paths_from_site_response_copy[0]["SITE_STATUS"] = "Live"
    paths_from_site_response_copy[0]["PATH_NAME"] = "22.L1XX.010107..TWCC"
    monkeypatch.setattr(cs, "paths_from_site", lambda *args: paths_from_site_response_copy)
    assert cs.disco_path_update("86.L1XX.001113..TWCC", body) == second_response


@pytest.mark.unittest
def test_update_path_status_elan_exceptions(monkeypatch):
    body = {
        "cid": "86.L1XX.001113..TWCC",
        "product_name": "EP-LAN (Fiber)",
        "status": "Pending Decommission",
        "service_type": "disconnect",
        "due_date": "2024-01-31",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-04178112",
    }

    get_granite_response = [
        {
            "aSideSiteName": "HDSNFLJD-BHN/HUB TAMP82-HUDSON",
            "bandwidth": "50 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-23992550",
            "orderNumber": "D-ENG-04178112,D-ENG-04178112,D-ENG-04178112",
            "pathId": "81.L1XX.912924..CHTR",
            "pathInService": "2021-02-26 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "COM-EPLAN",
            "servicePriority": "NO",
            "status": "Pending Decommission",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-23992550",
            "zSideSiteName": "HDSNFL48-MCR HEALTH INC//14730 COBRA WAY",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "0",
            "pathInstanceId": "1958644",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ]

    put_granite_response = {
        "pathId": "81.L1XX.912924..CHTR",
        "pathRev": "1",
        "status": "Pending Decommission",
        "pathInstanceId": "1958644",
        "retString": "Path Updated",
    }

    get_path_elements_response = [
        {
            "CIRC_PATH_INST_ID": "1958644",
            "PATH_NAME": "81.L1XX.912924..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "HDSNFLJD-BHN/HUB TAMP82-HUDSON",
            "PATH_Z_SITE": "HDSNFL48-MCR HEALTH INC//14730 COBRA WAY",
            "A_CLLI": "HDSNFLJD",
            "Z_CLLI": "HDSNFL48",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": "90937",
            "SERVICE_TYPE": "COM-EPLAN",
            "BANDWIDTH": "50 Mbps",
            "BW_SIZE": "50000000",
            "CUSTOMER_ID": "ACCT-23992550",
            "CUSTOMER_NAME": "MCR HEALTH INC-NAT",
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
            "LEG_INST_ID": "2220433",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "ELEMENT_REFERENCE": "1405593",
            "ELEMENT_CATEGORY": "VPLS SVC",
            "ELEMENT_STATUS": "Pending Decommission",
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
            "PURCHASING_GROUP": None,
            "IPV4_ADDRESS": None,
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "81.L1XX.912924..CHTR",
            "INITIAL_CIRCUIT_ID": "1958644",
            "LVL": "1",
        }
    ]

    get_path_elements_response_invalid_element_category = deepcopy(get_path_elements_response)
    get_path_elements_response_invalid_element_category[0]["ELEMENT_CATEGORY"] = "MPLS CORE"
    monkeypatch.setattr(cs, "get_granite", lambda _: get_granite_response)
    monkeypatch.setattr(cs, "put_granite", lambda *args: put_granite_response)
    monkeypatch.setattr(cs, "get_path_elements", lambda _: get_path_elements_response_invalid_element_category)
    with pytest.raises(Exception):
        assert cs.disco_path_update("86.L1XX.001113..TWCC", body) is None

    missing_element_category = deepcopy(get_path_elements_response)
    missing_element_category[0].pop("ELEMENT_CATEGORY")
    monkeypatch.setattr(cs, "get_granite", lambda _: get_granite_response)
    monkeypatch.setattr(cs, "put_granite", lambda *args: put_granite_response)
    monkeypatch.setattr(cs, "get_path_elements", lambda _: missing_element_category)
    with pytest.raises(Exception):
        assert cs.disco_path_update("86.L1XX.001113..TWCC", body) is None


@pytest.mark.unittest
def test_disco_path_update(monkeypatch):
    disco_data = [
        {
            "pathInstanceId": "0",
            "pathRev": "1",
            "zSideSiteName": "BFLONYJZ-PRATT COLLARD BUCK ADVISORY GROUP/205/120 W TUPPER ST",
            "orderNumber": "ENG-02933980",
        }
    ]

    body = {
        "service_type": "disconnect",
        "product_name": "Fiber Internet Access",
        "status": "Pending Decommission",
        "due_date": "2023-06-30",
        "engineering_job_type": "Partial Disconnect",
        "engineering_name": "ENG-02933980, ENG-02933980, ENG-02933980",
    }

    # No path info found for CID
    monkeypatch.setattr(cs, "get_granite", lambda _: [])

    with pytest.raises(Exception):
        assert cs.disco_path_update("71.L1XX.910595..CHTR", body) is None

    # len(discodata) > 50 and partial disconnect
    monkeypatch.setattr(cs, "get_granite", lambda _: disco_data)
    monkeypatch.setattr(cs, "put_granite", lambda *args: "disco_cid_data")
    assert cs.disco_path_update("71.L1XX.910595..CHTR", body) == {
        "data": "disco_cid_data",
        "message": "Partial Disconnect complete",
        "status": "Pending Decommission",
    }

    # len(discodata) < 50 and full disconnect and No elements found for pathid
    body["engineering_name"] = "ENG-02933980"
    body["engineering_job_type"] = "full disconnect"
    monkeypatch.setattr(cs, "disco_site_update", lambda *args: "disco_site_data")
    monkeypatch.setattr(cs, "get_path_elements_l1", lambda *args: [])
    monkeypatch.setattr(cs, "get_zsite_voice", lambda *args: get_zsite_voice_response)
    monkeypatch.setattr(cs, "paths_from_site", lambda *args: paths_from_site_response)

    with pytest.raises(Exception):
        assert cs.disco_path_update("71.L1XX.910595..CHTR", body) is None

    # all good
    monkeypatch.setattr(cs, "get_path_elements_l1", lambda *args: [1, 2])
    monkeypatch.setattr(cs, "disco_transport_update", lambda *args, **kwargs: {"pathId": "20.L4XX.%..CHRT"})
    monkeypatch.setattr(cs, "disco_cpe_update", lambda *args, **kwargs: "disco_cpe_data")
    assert cs.disco_path_update("71.L1XX.910595..CHTR", body) == {
        "cid_disconnect_data": "disco_cid_data",
        "cpe_disconnect_data": "disco_cpe_data",
        "message": "Full Disconnect complete",
        "site_disconnect_data": "disco_site_data",
        "status": "Pending Decommission",
        "transport_disconnect_data": {"pathId": "20.L4XX.%..CHRT"},
    }


@pytest.mark.unittest
def test_disco_path_update_epl(monkeypatch):
    pathid = "50.L1XX.000518..TWCC"
    body = {
        "product_name": "EPL (Fiber)",
        "service_location_address": "1140 LEXINGTON RD",
        "status": "Pending Decommission",
        "legacy_company": "TWC",
        "service_type": "disconnect",
        "due_date": "2023-04-03",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-8675309",
    }
    paths_resp = [
        {
            "aSideCustomer": "ACCT-28314450",
            "aSideSiteName": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "bandwidth": "50 Mbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-28314450",
            "orderNumber": "D-ENG-8675309,D-ENG-8675309,D-ENG-8675309",
            "pathId": "50.L1XX.000518..TWCC",
            "pathInService": "2023-12-05 12:00:00.0",
            "pathRev": "4",
            "pathScheduled": "2024-01-03 12:00:00.0",
            "product_Service_UDA": "COM-EPL",
            "servicePriority": "NO",
            "status": "Pending Decommission",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-28314450",
            "zSideSiteName": "GRTWKY20-GEORGETOWN COMMUNITY HOSPITAL//1002 LEXINGTON RD",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "0",
            "pathInstanceId": "2623480",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ]
    circuit_data = {
        "cid": "50.L1XX.000518..TWCC",
        "status": "Live",
        "aSideSiteName": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
        "zSideSiteName": "GRTWKY20-GEORGETOWN COMMUNITY HOSPITAL//1002 LEXINGTON RD",
    }
    """
    data = [
        {
            "SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "SITE_INST_ID": "59210",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "GRTWKYAL",
            "EQUIP_NAME": "GRTWKYAL2ZW/999.9999.999.99/SWT",
            "EQUIP_INST_ID": "839040",
            "EQUIP_CATEGORY": "SWITCH",
            "EQUIP_STATUS": "Live",
            "EQUIP_VENDOR": "JUNIPER",
            "EQUIP_MODEL": "EX4200-24T",
            "FQDN": "GRTWKYAL2ZW.CHTRSE.COM",
            "TARGET_ID": "GRTWKYAL2ZW",
            "IPV4_ADDRESS": "10.9.56.15/24",
            "OBJECT_TYPE": "SHELF",
        },
        {
            "SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "SITE_INST_ID": "59210",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "GRTWKYAL",
            "EQUIP_NAME": "GRTWKYAL4ZW/999.9999.999.99/NIU",
            "EQUIP_INST_ID": "1842111",
            "EQUIP_CATEGORY": "NIU",
            "EQUIP_STATUS": "Planned",
            "EQUIP_VENDOR": "RAD",
            "EQUIP_MODEL": "ETX-2I-10G-B/8.5/8SFPP",
            "FQDN": "GRTWKYAL4ZW.CML.CHTRSE.COM",
            "TARGET_ID": "GRTWKYAL4ZW",
            "IPV4_ADDRESS": "DHCP",
            "OBJECT_TYPE": "SHELF",
        },
    ]
    job_type = "partial"
    """
    disco_cid_data = {
        "pathId": "50.L1XX.000518..TWCC",
        "pathRev": "4",
        "status": "Pending Decommission",
        "pathInstanceId": "2623480",
        "retString": "Path Updated",
    }
    site_info = [
        {
            "CIRC_PATH_INST_ID": "2623480",
            "CIRCUIT_NAME": "50.L1XX.000518..TWCC",
            "CIRCUIT_STATUS": "Pending Decommission",
            "CIRCUIT_BANDWIDTH": "50 Mbps",
            "CIRCUIT_CATEGORY": "ETHERNET",
            "PREV_PATH_INST_ID": "1254095",
            "SERVICE_TYPE": "COM-EPL",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "ORDER_NUM": "D-ENG-8675309,D-ENG-8675309,D-ENG-8675309",
            "ORDERED": "DEC 04, 2023",
            "DUE": "JUN 13, 2025",
            "IN_SERVICE": "DEC 05, 2023",
            "SCHEDULED": "JAN 03, 2024",
            "DECOMMISSION": "APR 03, 2023",
            "A_SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_MARKET": "KENTUCKY-SOUTHERN INDIANA",
            "A_SITE_REGION": "SO OHIO",
            "A_ADDRESS": "1140 LEXINGTON RD",
            "A_CITY": "GEORGETOWN",
            "A_STATE": "KY",
            "A_ZIP": "40324",
            "A_COMMENTS": "Tech ID: 150 Date: 9/1/2022  CPE: M800C 1. Floor: 1st 2. Suite/Room: Rm 1700",
            "A_CLLI": "GRTWKYAL",
            "A_NPA": "502",
            "A_LONGITUDE": "-84.562225",
            "A_LATITUDE": "38.190556",
            "Z_SITE_NAME": "GRTWKY20-GEORGETOWN COMMUNITY HOSPITAL//1002 LEXINGTON RD",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_MARKET": "KENTUCKY-SOUTHERN INDIANA",
            "Z_SITE_REGION": "SO OHIO",
            "Z_ADDRESS": "1002 LEXINGTON RD",
            "Z_CITY": "GEORGETOWN",
            "Z_STATE": "KY",
            "Z_ZIP": "40324",
            "Z_CLLI": "GRTWKY20",
            "Z_NPA": "502",
            "Z_LONGITUDE": "-84.559387",
            "Z_LATITUDE": "38.190673",
            "LEG_NAME": "1",
            "LEG_INST_ID": "3049384",
            "ORDERING_CUSTOMER": "ACCT-28314450",
            "CUSTOMER_NAME": "GEORGETOWN COMMUNITY HOSPITAL",
            "COMMENTS": "ENG-01161945 ENG-01118127",
        }
    ]
    paths = [
        {
            "SITE_INST_ID": "59210",
            "SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "2623480",
            "PATH_NAME": "50.L1XX.000518..TWCC",
            "PATH_REV": "4",
            "A_SITE_INST_ID": "59210",
            "A_SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "A_SITE_TYPE": "LOCAL",
            "Z_SITE_INST_ID": "331098",
            "Z_SITE_NAME": "GRTWKY20-GEORGETOWN COMMUNITY HOSPITAL//1002 LEXINGTON RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET",
            "PATH_BW": "50 Mbps",
            "CUSTOMER_ID": "ACCT-28314450",
            "PATH_STATUS": "Pending Decommission",
            "SERVICE_TYPE": "COM-EPL",
        },
        {
            "SITE_INST_ID": "59210",
            "SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "1918335",
            "PATH_NAME": "50001.GE1.GRTWKYBN1QW.GRTWKYAL2ZW",
            "PATH_REV": "4",
            "A_SITE_INST_ID": "12463",
            "A_SITE_NAME": "GRTWKYBN-TWC/HUB G-GEORGETOWN",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_INST_ID": "59210",
            "Z_SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET TRANSPORT",
            "PATH_BW": "1 Gbps",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        },
        {
            "SITE_INST_ID": "59210",
            "SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "2217534",
            "PATH_NAME": "85.L1XX.001073..TWCC",
            "PATH_REV": "4",
            "A_SITE_INST_ID": "347727",
            "A_SITE_NAME": "WNCHKYHL-CLARK REGIONAL HOSPITAL//175 HOSPITAL DR",
            "A_SITE_TYPE": "LOCAL",
            "Z_SITE_INST_ID": "59210",
            "Z_SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET",
            "PATH_BW": "10 Mbps",
            "CUSTOMER_ID": "ACCT-12838770",
            "PATH_STATUS": "Designed",
            "SERVICE_TYPE": "COM-EPL",
        },
    ]
    truncated_path_elements = [
        {
            "CIRC_PATH_INST_ID": "2623480",
            "PATH_NAME": "50.L1XX.000518..TWCC",
            "PATH_REV": "4",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "PATH_Z_SITE": "GRTWKY20-GEORGETOWN COMMUNITY HOSPITAL//1002 LEXINGTON RD",
            "A_CLLI": "GRTWKYAL",
            "Z_CLLI": "GRTWKY20",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": "SILVER METRO",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "50 Mbps",
            "BW_SIZE": "50000000",
            "CUSTOMER_ID": "ACCT-28314450",
            "CUSTOMER_NAME": "GEORGETOWN COMMUNITY HOSPITAL",
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
            "LEG_INST_ID": "3049384",
            "A_SITE_NAME": "GRTWKYAL-GEORGETOWN COMMUNITY HOSPITAL//1140 LEXINGTON RD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "GRTWKYAL2ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "839040",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FPC0/0",
            "PORT_NAME": "02",
            "PORT_INST_ID": "100044321",
            "PORT_ACCESS_ID": "GE-0/0/2",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "GRTWKYAL2ZW.CHTRSE.COM",
            "MODEL": "EX4200-24T",
            "VENDOR": "JUNIPER",
            "TID": "GRTWKYAL2ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "DEVICE_INFO_NETWORK": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.9.56.15/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1213",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "50.L1XX.000518..TWCC",
            "INITIAL_CIRCUIT_ID": "2623480",
            "LVL": "1",
        }
    ]
    disco_transport_data = {
        "pathId": "50001.GE1.GRTWKYBN1QW.GRTWKYAL2ZW",
        "pathRev": "4",
        "status": "Pending Decommission",
        "pathInstanceId": "1918335",
        "retString": "Path Updated",
    }
    disco_cpe_data = {
        "id": "GRTWKYAL2ZW/999.9999.999.99/SWT",
        "status": "Pending Decommission",
        "equipInstId": "839040",
        "retString": "Shelf Updated",
    }
    expected = {
        "message": "Full Disconnect complete",
        "cid_disconnect_data": {
            "pathId": "50.L1XX.000518..TWCC",
            "pathRev": "4",
            "status": "Pending Decommission",
            "pathInstanceId": "2623480",
            "retString": "Path Updated",
        },
        "site_disconnect_data": "Multiple live paths found. Did not disconnect site",
        "transport_disconnect_data": {
            "pathId": "50001.GE1.GRTWKYBN1QW.GRTWKYAL2ZW",
            "pathRev": "4",
            "status": "Pending Decommission",
            "pathInstanceId": "1918335",
            "retString": "Path Updated",
        },
        "cpe_disconnect_data": {
            "id": "GRTWKYAL2ZW/999.9999.999.99/SWT",
            "status": "Pending Decommission",
            "equipInstId": "839040",
            "retString": "Shelf Updated",
        },
        "status": "Pending Decommission",
    }
    """
    expected = {
        "message": "Partial Disconnect complete",
        "data": {
            "pathId": "50.L1XX.000518..TWCC",
            "pathRev": "4",
            "status": "Pending Decommission",
            "pathInstanceId": "2623480",
            "retString": "Path Updated",
        },
        "status": "Pending Decommission",
    }
    """
    monkeypatch.setattr(cs, "get_granite", lambda *args, **kwargs: paths_resp)
    monkeypatch.setattr(cs, "get_circuit_side_info", lambda *args, **kwargs: circuit_data)
    """
    monkeypatch.setattr(cs, "get_existing_shelf", lambda *args, **kwargs: data)
    monkeypatch.setattr(cs, "get_job_type", lambda *args, **kwargs: job_type)
    """
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: disco_cid_data)
    monkeypatch.setattr(cs, "get_zsite_voice", lambda *args, **kwargs: site_info)
    monkeypatch.setattr(cs, "paths_from_site", lambda *args, **kwargs: paths)
    monkeypatch.setattr(cs, "get_path_elements_l1", lambda *args, **kwargs: truncated_path_elements)
    monkeypatch.setattr(cs, "disco_transport_update", lambda *args, **kwargs: disco_transport_data)
    monkeypatch.setattr(cs, "disco_cpe_update", lambda *args, **kwargs: disco_cpe_data)
    assert cs.disco_path_update(pathid, body) == expected

    # generate fall-out conditions
    body_missing_service_location = {
        "product_name": "EPL (Fiber)",
        "status": "Pending Decommission",
        "legacy_company": "TWC",
        "service_type": "disconnect",
        "due_date": "2023-04-03",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-8675309",
    }
    try:
        cs.disco_path_update(pathid, body_missing_service_location)
    except AbortException as e:
        assert "Service location address is missing" in e.data["message"]

    body_with_blank_space_service_location = {
        "product_name": "EPL (Fiber)",
        "service_location_address": " ",
        "status": "Pending Decommission",
        "legacy_company": "TWC",
        "service_type": "disconnect",
        "due_date": "2023-04-03",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-8675309",
    }
    try:
        cs.disco_path_update(pathid, body_with_blank_space_service_location)
    except AbortException as e:
        assert "Missing service location address" in e.data["message"]

    body_with_unexpected_service_location = {
        "product_name": "EPL (Fiber)",
        "service_location_address": "11921 N. Mopac Expressway",
        "status": "Pending Decommission",
        "legacy_company": "TWC",
        "service_type": "disconnect",
        "due_date": "2023-04-03",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-8675309",
    }
    try:
        cs.disco_path_update(pathid, body_with_unexpected_service_location)
    except AbortException as e:
        assert "Service location matching threshold unmet" in e.data["message"]

    ratio = iter([65, 70, 85, 85])
    monkeypatch.setattr(cs.fuzz, "partial_ratio", lambda *args, **kwargs: next(ratio))
    try:
        cs.disco_path_update(pathid, body)
    except AbortException as e:
        assert "Service location matching threshold unmet" in e.data["message"]
    try:
        cs.disco_path_update(pathid, body)
    except AbortException as e:
        assert "Unable to designate which ZW device services" in e.data["message"]


@pytest.mark.unittest
def test_disco_site_update(monkeypatch):
    # No site data found for site
    monkeypatch.setattr(cs, "get_site_data", lambda *args: [])

    with pytest.raises(Exception):
        assert cs.disco_site_update("site_name", "status") is None

    def _exception():
        raise Exception

    # Issue updating site in granite. Update parameters
    monkeypatch.setattr(cs, "get_site_data", lambda *args: [{"siteType": "siteType"}])
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: _exception())

    with pytest.raises(Exception):
        assert cs.disco_site_update("site_name", "status") is None

    # all good
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: "data")
    assert cs.disco_site_update("site_name", "status") == "data"


@pytest.mark.unittest
def test_disco_transport_update(monkeypatch):
    path_elementst = path_elements.copy()
    path_elementst[0]["LEG_NAME"] = "LEG_NAME"

    # No elements found for CID
    with pytest.raises(Exception):
        assert cs.disco_transport_update([{}], "zsite_name", "status") is None

    # No path elements ending in ZW found
    with pytest.raises(Exception):
        assert cs.disco_transport_update(path_elementst, "zsite_name", "status") is None

    # More than 1 element ending in ZW found
    path_elementst[0]["ELEMENT_NAME"] = "ELEMENT_NAMEZW"
    path_elementst.append(path_elements[0])

    with pytest.raises(Exception):
        assert cs.disco_transport_update(path_elementst, "zsite_name", "status") is None

    # No path info found for transport path
    path_elementst.pop()
    monkeypatch.setattr(cs, "get_granite", lambda *args: [])

    with pytest.raises(Exception):
        assert cs.disco_transport_update(path_elementst, "zsite_name", "status") is None

    # Issue updating transport path in granite
    monkeypatch.setattr(cs, "get_granite", lambda *args: [{"pathInstanceId": "pathInstanceId", "pathRev": 1}])
    monkeypatch.setattr(cs, "put_granite", lambda *args: {})

    with pytest.raises(Exception):
        assert cs.disco_transport_update(path_elementst, "zsite_name", "status") is None

    # data["pathId"] is None
    monkeypatch.setattr(cs, "put_granite", lambda *args: {"pathId": None})

    with pytest.raises(Exception):
        assert cs.disco_transport_update(path_elementst, "zsite_name", "status") is None

    # all good
    monkeypatch.setattr(cs, "put_granite", lambda *args: {"pathId": "pathId"})
    assert cs.disco_transport_update(path_elementst, "zsite_name", "status") == {"pathId": "pathId"}


@pytest.mark.unittest
def test_disco_cpe_update(monkeypatch):
    path_elementsc = path_elements.copy()

    # NO CPE found
    with pytest.raises(Exception):
        assert cs.disco_cpe_update(path_elementsc, "tid", "zsite_name", "status") is None

    # More than 1 CPE found
    path_elementsc[0]["TID"] = "tid"
    path_elementsc.append(path_elementsc[0])

    with pytest.raises(Exception):
        assert cs.disco_cpe_update(path_elementsc, "tid", "zsite_name", "status") is None

    # Issue updating cpe in granite
    path_elementsc.pop()
    monkeypatch.setattr(cs, "put_granite", lambda *args: {})

    with pytest.raises(Exception):
        assert cs.disco_cpe_update(path_elementsc, "tid", "zsite_name", "status") is None

    # no Shelf Updated
    monkeypatch.setattr(cs, "put_granite", lambda *args: {"retString": False})

    with pytest.raises(Exception):
        assert cs.disco_cpe_update(path_elementsc, "tid", "zsite_name", "status") is None

    # all good
    monkeypatch.setattr(cs, "put_granite", lambda *args: {"retString": "Shelf Updated"})
    assert cs.disco_cpe_update(path_elementsc, "tid", "zsite_name", "status") == {"retString": "Shelf Updated"}


@pytest.mark.unittest
def test_get_decom_status():
    get_network_elements_response = [
        {
            "CIRC_PATH_INST_ID": "1405593",
            "PATH_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Pending Decommission",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-BHN",
            "L_NAME": "DAC-MCRH.ELAN",
            "L_ID": "937",
            "SEQUENCE": "10",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1610938",
            "A_SITE_NAME": "BRTNFLUF-BHN/HE TAMP54/TAMP55-MANATEE",
            "Z_SITE_NAME": "BRTOFLBJ-MANATEE COUNTY RURAL/A/712 39TH ST W",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "94.IPXN.000091..TWCC",
            "ELEMENT_REFERENCE": "1502066",
            "ELEMENT_CATEGORY": "PRI TRUNKS",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "10 Mbps",
        },
        {
            "CIRC_PATH_INST_ID": "1405593",
            "PATH_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Pending Decommission",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-BHN",
            "L_NAME": "DAC-MCRH.ELAN",
            "L_ID": "937",
            "SEQUENCE": "11",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1610938",
            "A_SITE_NAME": "BRTNFLUF-BHN/HE TAMP54/TAMP55-MANATEE",
            "Z_SITE_NAME": "BRTOFLCJ-MANATEE COUNTY RURAL HEALTH//2318 MANATEE",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "94.IPXN.000092..TWCC",
            "ELEMENT_REFERENCE": "1502407",
            "ELEMENT_CATEGORY": "PRI TRUNKS",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "10 Mbps",
            "NEXT_PATH_INST_ID": "2352805",
        },
        {
            "CIRC_PATH_INST_ID": "1405593",
            "PATH_NAME": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Pending Decommission",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-BHN",
            "L_NAME": "DAC-MCRH.ELAN",
            "L_ID": "937",
            "SEQUENCE": "15",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1610938",
            "A_SITE_NAME": "BRTNFLUF-BHN/HE TAMP54/TAMP55-MANATEE",
            "Z_SITE_NAME": "BRTNFLQX-MANATEE COUNTY RURAL HEALTH SERVICES//1312 MANATEE AVE E",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "94.L1XX.015677..TWCC",
            "ELEMENT_REFERENCE": "1538004",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Decommissioned",
            "ELEMENT_BANDWIDTH": "40 Mbps",
        },
    ]

    network_elements = deepcopy(get_network_elements_response)
    assert cs.get_decom_status(network_elements) is True

    network_elements2 = deepcopy(get_network_elements_response)
    network_elements2[-1]["ELEMENT_STATUS"] = "Live"
    assert cs.get_decom_status(network_elements2) is False


@pytest.mark.unittest
def test_disco_hosted_voice_update(monkeypatch):
    pathid = "42.HNXN.000046..CHTR"

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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
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
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "INTERNET",
            "LEG_INST_ID": "2659728",
            "A_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "Z_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "31001.GE40L.LSAICAEV2CW.LSAICAEV4QW",
            "ELEMENT_REFERENCE": "1895264",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1309",
            "CHAN_INST_ID": "10667343",
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
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "INTERNET",
            "LEG_INST_ID": "2659728",
            "A_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "Z_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "42001.GE1.LSAICAEV4QW.LSEHCA251ZW",
            "ELEMENT_REFERENCE": "2345238",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": "VLAN1309",
            "CHAN_INST_ID": "10293191",
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
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "INTERNET",
            "LEG_INST_ID": "2659728",
            "A_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "LSEHCA251ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1850105",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED PORTS",
            "PORT_NAME": "USER 4",
            "PORT_INST_ID": "116053172",
            "PORT_ACCESS_ID": "ETH PORT 4",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "LSEHCA251ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "LSEHCA251ZW",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.0.238.115/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1309",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "42.HNXN.000046..CHTR",
            "INITIAL_CIRCUIT_ID": "2326337",
            "LVL": "1",
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "5.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "5",
            "MEMBER_NBR": None,
            "LEG_NAME": "INTERNET",
            "LEG_INST_ID": "2659728",
            "A_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "LSEHCA2501W/999.999.999.999/RTR",
            "ELEMENT_REFERENCE": "1773746",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED ETHERNET PORTS",
            "PORT_NAME": "WAN",
            "PORT_INST_ID": "115196084",
            "PORT_ACCESS_ID": "WAN",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": "DYNAMIC",
            "FQDN": "LSEHCA2501W .CHTRSE.COM",
            "MODEL": "M500",
            "VENDOR": "AUDIOCODES",
            "TID": "LSEHCA2501W",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "MANAGED SERVICES - IP",
            "IPV4_ADDRESS": "76.53.81.194",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "42.HNXN.000046..CHTR",
            "INITIAL_CIRCUIT_ID": "2326337",
            "LVL": "1",
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "6.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "6",
            "MEMBER_NBR": None,
            "LEG_NAME": "INTERNET",
            "LEG_INST_ID": "2659728",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_NAME": "MANAGED VOICE/LSEHCA25-MATTIE MUSIC GROUP",
            "ELEMENT_REFERENCE": "2497380",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
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
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "MGMT VLAN88",
            "LEG_INST_ID": "2881799",
            "A_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "Z_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "31001.GE40L.LSAICAEV2CW.LSAICAEV4QW",
            "ELEMENT_REFERENCE": "1895264",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "AGGREGATE",
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
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "MGMT VLAN88",
            "LEG_INST_ID": "2881799",
            "A_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "Z_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "42001.GE1.LSAICAEV4QW.LSEHCA251ZW",
            "ELEMENT_REFERENCE": "2345238",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
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
        },
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
            "PATH_STATUS": "Pending Decommission",
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
            "IPV6_SERVICE_TYPE": "None",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "3.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "3",
            "MEMBER_NBR": None,
            "LEG_NAME": "MGMT VLAN88",
            "LEG_INST_ID": "2881799",
            "A_SITE_NAME": None,
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "NETWORK LINK",
            "ELEMENT_NAME": "MANAGED VOICE/LSEHCA25-MATTIE MUSIC GROUP",
            "ELEMENT_REFERENCE": "2497380",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
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
        },
    ]

    body = {
        "service_type": "disconnect",
        "product_name": "Hosted Voice - (Fiber)",
        "status": "Pending Decommission",
        "due_date": "2024-06-08",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-04178112",
    }

    network_elements = [
        {
            "CIRC_PATH_INST_ID": "2497380",
            "PATH_NAME": "MANAGED VOICE/LSEHCA25-MATTIE MUSIC GROUP",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SEQUENCE": "1",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2881794",
            "A_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "Z_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "ELEMENT_TYPE": "PATH",
            "ELEMENT_NAME": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
            "ELEMENT_REFERENCE": "2497374",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "CHAN_NAME": "1",
            "CHAN_INST_ID": "10674902",
        },
        {
            "CIRC_PATH_INST_ID": "2497380",
            "PATH_NAME": "MANAGED VOICE/LSEHCA25-MATTIE MUSIC GROUP",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SEQUENCE": "2",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2881794",
            "A_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "LSEHCA2501W/999.999.999.999/RTR",
            "ELEMENT_REFERENCE": "1773746",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "SLOT": "FIXED ETHERNET PORTS",
            "PORT_NAME": "LAN 1-1",
            "PORT_INST_ID": "115196220",
            "CONNECTOR_TYPE": "RJ-45",
            "FQDN": "LSEHCA2501W .CHTRSE.COM",
            "MODEL": "M500",
            "VENDOR": "AUDIOCODES",
            "TID": "LSEHCA2501W",
            "PURCHASING_GROUP": "MANAGED SERVICES - IP",
            "IPV4_ADDRESS": "76.53.81.194",
        },
        {
            "CIRC_PATH_INST_ID": "2497380",
            "PATH_NAME": "MANAGED VOICE/LSEHCA25-MATTIE MUSIC GROUP",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "TOPOLOGY": "Mesh",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SEQUENCE": "3",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2881794",
            "A_SITE_NAME": "LSAICAEV-TWC/HE BO-BOWCROFT MDC (BWLACA1)",
            "Z_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "42.HNXN.000046..CHTR",
            "ELEMENT_REFERENCE": "2326337",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "5 Mbps",
        },
    ]

    hosted_voice_path_elements = [
        {
            "CIRC_PATH_INST_ID": "2497374",
            "PATH_NAME": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "PATH_Z_SITE": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "A_CLLI": "LSEHCA25",
            "Z_CLLI": "LSEHCA25",
            "PATH_A_SITE_TYPE": "LOCAL",
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
            "ORDER_REFERENCE": "1.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "1",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2881788",
            "A_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "LSEHCA2501W/999.999.999.999/RTR",
            "ELEMENT_REFERENCE": "1773746",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Pending Decommission",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED ETHERNET PORTS",
            "PORT_NAME": "LAN 1",
            "PORT_INST_ID": "115196080",
            "PORT_ACCESS_ID": "LAN 1",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": "DYNAMIC",
            "FQDN": "LSEHCA2501W .CHTRSE.COM",
            "MODEL": "M500",
            "VENDOR": "AUDIOCODES",
            "TID": "LSEHCA2501W",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "MANAGED SERVICES - IP",
            "IPV4_ADDRESS": "76.53.81.194",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
            "INITIAL_CIRCUIT_ID": "2497374",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2497374",
            "PATH_NAME": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
            "PATH_REV": "1",
            "PATH_CATEGORY": "ETHERNET TRANSPORT",
            "PATH_A_SITE": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "PATH_Z_SITE": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "A_CLLI": "LSEHCA25",
            "Z_CLLI": "LSEHCA25",
            "PATH_A_SITE_TYPE": "LOCAL",
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
            "ORDER_REFERENCE": "2.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "2",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2881788",
            "A_SITE_NAME": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "LSEHCA2502W/999.999.999.999/SWT",
            "ELEMENT_REFERENCE": "1773753",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "ADTRAN NETVANTA 1560-24P PORTS",
            "PORT_NAME": "24",
            "PORT_INST_ID": "115196157",
            "PORT_ACCESS_ID": None,
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "LSEHCA2502W.CHTRSE.COM",
            "MODEL": "NETVANTA 1560-24P",
            "VENDOR": "ADTRAN",
            "TID": "LSEHCA2502W",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "MANAGED SERVICES - IP",
            "IPV4_ADDRESS": "10.12.0.5/23",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
            "INITIAL_CIRCUIT_ID": "2497374",
            "LVL": "1",
        },
    ]

    update_voice_switch_status = {
        "id": "LSEHCA2502W/999.999.999.999/SWT",
        "status": "Pending Decommission",
        "equipInstId": "1773753",
        "retString": "Shelf Updated",
    }

    update_transport_path_status = {
        "pathId": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
        "pathRev": "1",
        "status": "Pending Decommission",
        "pathInstanceId": "2497374",
        "retString": "Path Updated",
    }

    responses_put = iter([update_voice_switch_status, update_transport_path_status])

    response_get = [
        {
            "aSideSiteName": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "bandwidth": "1 Gbps",
            "category": "ETHERNET TRANSPORT",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "pathId": "42001.GE1.LSEHCA2501W.LSEHCA2502W",
            "pathInService": "2023-12-15 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "INT-ACCESS TO PREM TRANSPORT",
            "servicePriority": "NO",
            "status": "Live",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideSiteName": "LSEHCA25-MATTIE MUSIC GROUP//8556 VENICE BLVD",
            "instanceProtocol": "9999",
            "pathInstanceId": "2497374",
            "serviceMedia": "COPPER",
            "startChanNbr": "1",
            "virtualChans": "D",
        }
    ]

    update_network_status_resp = {
        "NetworkName": "MANAGED VOICE/LSEHCA25-MATTIE MUSIC GROUP",
        "rev": "1",
        "status": "Pending Decommission",
        "ntwkInstanceId": "2497380",
        "retString": "Network Updated",
    }

    monkeypatch.setattr(cs, "get_network_elements", lambda *args, **kwargs: network_elements)
    monkeypatch.setattr(cs, "get_path_elements_l1", lambda *args, **kwargs: hosted_voice_path_elements)
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kargs: next(responses_put))
    monkeypatch.setattr(cs, "get_granite", lambda *args, **kwargs: response_get)
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: next(responses_put))
    monkeypatch.setattr(cs, "update_network_status", lambda *args, **kwargs: update_network_status_resp)

    assert cs.disco_hosted_voice_update(pathid, path_elements, body) is None


@pytest.mark.unittest
def test_disco_vgw_update(monkeypatch):
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2570846",
            "PATH_NAME": "31.IPXN.001093..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "PRI TRUNKS",
            "PATH_A_SITE": "GENVNYAA-TWC/HUB GE-GENEVA (NY) (ROCHNYGNV)",
            "PATH_Z_SITE": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "A_CLLI": "GENVNYAA",
            "Z_CLLI": "GENVNYEA",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-PRI",
            "BANDWIDTH": "10 Mbps",
            "BW_SIZE": "10000000",
            "CUSTOMER_ID": "ACCT-00596242",
            "CUSTOMER_NAME": "LYONS NATIONAL BANK",
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
            "LEG_INST_ID": "2979075",
            "A_SITE_NAME": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "GENVNYEA1ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "715729",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "CHASSIS PORTS",
            "PORT_NAME": "NETWORK PORT-1-1-1-2",
            "PORT_INST_ID": "97164933",
            "PORT_ACCESS_ID": "ACCESS-1-1-1-2",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "GENVNYEA1ZW.CML.CHTRSE.COM",
            "MODEL": "FSP 150CC-GE114/114S",
            "VENDOR": "ADVA",
            "TID": "GENVNYEA1ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.12.91.133/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1309",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "31.IPXN.001093..CHTR",
            "INITIAL_CIRCUIT_ID": "2570846",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2570846",
            "PATH_NAME": "31.IPXN.001093..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "PRI TRUNKS",
            "PATH_A_SITE": "GENVNYAA-TWC/HUB GE-GENEVA (NY) (ROCHNYGNV)",
            "PATH_Z_SITE": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "A_CLLI": "GENVNYAA",
            "Z_CLLI": "GENVNYEA",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-PRI",
            "BANDWIDTH": "10 Mbps",
            "BW_SIZE": "10000000",
            "CUSTOMER_ID": "ACCT-00596242",
            "CUSTOMER_NAME": "LYONS NATIONAL BANK",
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
            "LEG_INST_ID": "2979075",
            "A_SITE_NAME": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "GENVNYEAG2W/999.9999.999.99/RTR",
            "ELEMENT_REFERENCE": "1817687",
            "ELEMENT_CATEGORY": "ROUTER",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "FIXED ETHERNET PORTS",
            "PORT_NAME": "WAN",
            "PORT_INST_ID": "115715982",
            "PORT_ACCESS_ID": "WAN",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": "DYNAMIC",
            "FQDN": "GENVNYEAG2W.CHTRSE.COM",
            "MODEL": "M500",
            "VENDOR": "AUDIOCODES",
            "TID": "GENVNYEAG2W",
            "LEGACY_EQUIP_SOURCE": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "50.75.87.154/30",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": None,
            "VLAN_OPERATION": None,
            "PORT_ROLE": None,
            "INITIAL_PATH_NAME": "31.IPXN.001093..CHTR",
            "INITIAL_CIRCUIT_ID": "2570846",
            "LVL": "1",
        },
    ]

    tid = "GENVNYEAG2W"

    zsite_name = "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST"

    status = "Pending Decommission"

    data = {
        "id": "GENVNYEAG2W/999.9999.999.99/RTR",
        "status": "Pending Decommission",
        "equipInstId": "1817687",
        "retString": "Shelf Updated",
    }

    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: data)

    assert cs.disco_vgw_update(path_elements, tid, zsite_name, status) == data


@pytest.mark.unittest
def test_is_supported_vgw_shelf(monkeypatch):
    shelf_name = "GENVNYEAG2W"

    data = [
        {
            "SITE_NAME": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "SITE_INST_ID": "346279",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Pending Decommission",
            "SITE_CLLI": "GENVNYEA",
            "EQUIP_NAME": "GENVNYEAG2W/999.9999.999.99/RTR",
            "EQUIP_INST_ID": "1817687",
            "EQUIP_CATEGORY": "ROUTER",
            "EQUIP_STATUS": "Pending Decommission",
            "EQUIP_VENDOR": "AUDIOCODES",
            "EQUIP_MODEL": "M500",
            "FQDN": "GENVNYEAG2W.CHTRSE.COM",
            "TARGET_ID": "GENVNYEAG2W",
            "IPV4_ADDRESS": "50.75.87.154/30",
            "OBJECT_TYPE": "SHELF",
        }
    ]

    monkeypatch.setattr(cs, "get_equipid", lambda *args, **kwargs: data)

    assert cs.is_supported_vgw_shelf(shelf_name) is False


@pytest.mark.unittest
def test_set_circuit_status(monkeypatch):
    circ_name = "31.IPXN.001093..CHTR.001"

    body = {
        "service_type": "disconnect",
        "product_name": "PRI Trunk (Fiber)",
        "status": "Pending Decommission",
        "due_date": "2024-06-08",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-04178112",
    }

    granite_resp = [
        {
            "aSideSiteName": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "bandwidth": "DS1",
            "category": "TDM",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-00596242",
            "orderNumber": "CUS-VO-PRI-00001851,ENG-04152150",
            "pathId": "31.IPXN.001093..CHTR.001",
            "pathInService": "2024-03-18 12:00:00.0",
            "pathRev": "1",
            "product_Service_UDA": "CUS-VOICE-PRI",
            "servicePriority": "NO",
            "status": "Live",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-00596242",
            "zSideSiteName": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "pathInstanceId": "2570847",
            "serviceMedia": "FIBER",
            "virtualChans": "N",
        }
    ]

    disco_cid_data = {
        "pathId": "31.IPXN.001093..CHTR.001",
        "pathRev": "1",
        "status": "Pending Decommission",
        "pathInstanceId": "2570847",
        "retString": "Path Updated",
    }

    monkeypatch.setattr(cs, "get_granite", lambda *args, **kwargs: granite_resp)
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: disco_cid_data)

    assert cs.set_circuit_status(circ_name, body) is None


@pytest.mark.unittest
def test_is_pri_service(monkeypatch):
    cid = "31.IPXN.001093..CHTR"

    resp = [
        {
            "CIRC_PATH_INST_ID": "2570846",
            "CIRCUIT_NAME": "31.IPXN.001093..CHTR",
            "CIRCUIT_STATUS": "Pending Decommission",
            "CIRCUIT_BANDWIDTH": "10 Mbps",
            "CIRCUIT_CATEGORY": "PRI TRUNKS",
            "SERVICE_TYPE": "CUS-VOICE-PRI",
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "ORDER_NUM": "CUS-VO-PRI-00001851,ENG-04152150,D-ENG-04178112",
            "ORDERED": "SEP 27, 2023",
            "DUE": "MAR 18, 2024",
            "IN_SERVICE": "OCT 24, 2023",
            "DECOMMISSION": "JUN 08, 2024",
            "A_SITE_NAME": "GENVNYAA-TWC/HUB GE-GENEVA (NY) (ROCHNYGNV)",
            "A_SITE_TYPE": "HUB",
            "A_SITE_MARKET": "WESTERN NEW YORK",
            "A_SITE_REGION": "NORTHEAST",
            "A_ADDRESS": "3518 SUTTON RD",
            "A_CITY": "GENEVA",
            "A_STATE": "NY",
            "A_ZIP": "14456",
            "A_CLLI": "GENVNYAA",
            "A_NPA": "315",
            "A_LONGITUDE": "-77.040222",
            "A_LATITUDE": "42.863506",
            "Z_SITE_NAME": "GENVNYEA-LYONS NATIONAL BANK//399 EXCHANGE ST",
            "Z_SITE_TYPE": "LOCAL",
            "Z_SITE_MARKET": "WESTERN NEW YORK",
            "Z_SITE_REGION": "NORTHEAST",
            "Z_ADDRESS": "399 EXCHANGE ST",
            "Z_CITY": "GENEVA",
            "Z_STATE": "NY",
            "Z_ZIP": "14456",
            "Z_CLLI": "GENVNYEA",
            "Z_NPA": "315",
            "Z_LONGITUDE": "-76.981194",
            "Z_LATITUDE": "42.868515",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2979075",
        }
    ]

    resp2 = deepcopy(resp)
    resp2[0]["SERVICE_TYPE"] = "CUS-VOICE"

    monkeypatch.setattr(cs, "get_circuit_site_info", lambda *args, **kwargs: resp)
    assert cs.is_pri_service(cid) is True

    monkeypatch.setattr(cs, "get_circuit_site_info", lambda *args, **kwargs: resp2)
    assert cs.is_pri_service(cid) is False


@pytest.mark.unittest
def test_is_voice_product():
    product_name1 = "PRI Trunk (Fiber)"
    product_name2 = "PRI Trunk"

    assert cs.is_voice_product(product_name1) is True
    assert cs.is_voice_product(product_name2) is False


@pytest.mark.unittest
def test_check_thor(monkeypatch):
    # all good
    monkeypatch.setattr(cs, "thor_gsip_check", lambda *args, **kwargs: ("compliant", "data"))
    assert cs.check_thor("pathid", "prod_name", "N") is None

    # GSIP compliance check failed
    monkeypatch.setattr(cs, "thor_gsip_check", lambda *args, **kwargs: (None, "data"))

    with raises(AbortException):
        assert cs.check_thor("pathid", "prod_name", "Y") is None


@pytest.fixture
def disco_epl_data():
    resp1 = {
        "message": "Full Disconnect complete",
        "cid_disconnect_data": {
            "pathId": "93.L1XX.003635..CHTR",
            "pathRev": "2",
            "status": "Pending Decommission",
            "pathInstanceId": "2313452",
            "retString": "Path Updated",
        },
        "site_disconnect_data": "Multiple live paths found. Did not disconnect site",
        "transport_disconnect_data": {
            "pathId": "93001.GE1.TROYOH090QW.PIQUOHAD2ZW",
            "pathRev": "2",
            "status": "Pending Decommission",
            "pathInstanceId": "2258486",
            "retString": "Path Updated",
        },
        "cpe_disconnect_data": {
            "id": "PIQUOHAD2ZW/999.9999.999.99/SWT",
            "status": "Pending Decommission",
            "equipInstId": "1225653",
            "retString": "Shelf Updated",
        },
        "status": "Pending Decommission",
    }
    resp2 = {
        "message": "Full Disconnect complete",
        "cid_disconnect_data": {
            "pathId": "93.L1XX.003635..CHTR",
            "pathRev": "2",
            "status": "Pending Decommission",
            "pathInstanceId": "2313452",
        },
        "site_disconnect_data": "Multiple live paths found. Did not disconnect site",
        "transport_disconnect_data": {
            "pathId": "93001.GE10.TROYOH090QW.TROYOHAA2ZW",
            "pathRev": "2",
            "status": "Pending Decommission",
            "pathInstanceId": "2274049",
            "retString": "Path Updated",
        },
        "cpe_disconnect_data": {
            "id": "TROYOHAA2ZW/999.9999.999.99/SWT",
            "status": "Pending Decommission",
            "equipInstId": "1626093",
            "retString": "Shelf Updated",
        },
        "status": "Pending Decommission",
    }
    return resp1, resp2


@pytest.mark.unittest
def test_disco_epl(disco_epl_data, monkeypatch):
    cid = "93.L1XX.003635..CHTR"
    body = {
        "service_type": "disconnect",
        "product_name": "EPL (Fiber)",
        "status": "Pending Decommission",
        "due_date": "2023-04-03",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-052",
        "service_location_address": "308 LOONEY RD",
    }
    circuit_info_resp = {
        "cid": "93.L1XX.003635..CHTR",
        "status": "Pending Decommission",
        "aSideSiteName": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
        "zSideSiteName": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
    }
    zw = iter(["PIQUOHAD2ZW", "TROYOHAA2ZW"])
    a_z_side_ratio = iter([35, 100])
    job_type = "full"
    resp1, resp2 = disco_epl_data
    resp = iter([resp1, resp2])
    responses = [resp1, resp2]

    monkeypatch.setattr(cs, "get_circuit_side_info", lambda *args, **kwargs: circuit_info_resp)
    monkeypatch.setattr(cs, "get_zw_device_tid", lambda *args: next(zw))
    monkeypatch.setattr(cs, "get_job_type", lambda *args, **kwargs: job_type)
    monkeypatch.setattr(fuzz, "partial_ratio", lambda *args: next(a_z_side_ratio))
    monkeypatch.setattr(cs, "disco_path_update", lambda *args, **kwargs: next(resp))
    assert cs.disco_epl(cid, body) == responses


@pytest.fixture
def disco_path_update_epl_fiber_data():
    granite_paths_url_resp = [
        {
            "aSideCustomer": "ACCT-01574543",
            "aSideSiteName": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "bandwidth": "1 Gbps",
            "category": "ETHERNET",
            "gia_UDA": "NO",
            "off_NetFacility_UDA": "NO",
            "orderingCustomer": "ACCT-01574543",
            "orderNumber": "D-ENG-8675309,D-ENG-8675309,D-ENG-8675309",
            "pathId": "93.L1XX.003635..CHTR",
            "pathInService": "2022-06-14 12:00:00.0",
            "pathRev": "2",
            "pathScheduled": "2022-06-29 12:00:00.0",
            "product_Service_UDA": "COM-EPL",
            "protectedFlag_UDA": "YES",
            "servicePriority": "NO",
            "status": "Live",
            "topology": "P",
            "tspChildPresent_UDA": "NO",
            "zSideCustomer": "ACCT-01574543",
            "zSideSiteName": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "instanceProtocol": "9999",
            "managedService": "NO",
            "ofEnnis": "0",
            "pathInstanceId": "2313452",
            "serviceMedia": "FIBER",
            "slmEligibility": "ELIGIBLE DESIGN",
            "startChanNbr": "1",
            "vcClass": "TYPE 1",
            "virtualChans": "D",
        }
    ]
    get_circuit_side_info_resp = {
        "cid": "93.L1XX.003635..CHTR",
        "status": "Live",
        "aSideSiteName": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
        "zSideSiteName": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
    }
    put_granite_resp = {
        "pathId": "93.L1XX.003635..CHTR",
        "pathRev": "2",
        "status": "Pending Decommission",
        "pathInstanceId": "2313452",
        "retString": "Path Updated",
    }
    get_zsite_voice_resp = [
        {
            "CIRC_PATH_INST_ID": "2313452",
            "CIRCUIT_NAME": "93.L1XX.003635..CHTR",
            "CIRCUIT_STATUS": "Pending Decommission",
            "CIRCUIT_BANDWIDTH": "1 Gbps",
            "CIRCUIT_CATEGORY": "ETHERNET",
            "PREV_PATH_INST_ID": "2270253",
            "SERVICE_TYPE": "COM-EPL",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "ORDER_NUM": "D-ENG-8675309,D-ENG-8675309,D-ENG-052",
            "ORDERED": "JUN 01, 2022",
            "DUE": "SEP 03, 2025",
            "IN_SERVICE": "JUN 14, 2022",
            "SCHEDULED": "JUN 29, 2022",
            "DECOMMISSION": "APR 03, 2023",
            "A_SITE_NAME": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "A_SITE_TYPE": "LOCAL",
            "A_SITE_MARKET": "CENTRAL OHIO",
            "A_SITE_REGION": "SO OHIO",
            "A_ADDRESS": "600 W MAIN ST",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
        }
    ]
    paths_from_site_resp = [
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "1849989",
            "PATH_NAME": "93.IPXN.100466..CHTR",
            "PATH_REV": "1",
            "A_SITE_INST_ID": "3169",
            "A_SITE_NAME": "PIQUOH07-TWC/HUB PQ-PIQUA (PQUAOH01)",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "PRI TRUNKS",
            "PATH_BW": "10 Mbps",
            "CUSTOMER_ID": "KETTERING HEALTH NETWORK",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "CUS-VOICE-PRI",
        },
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "1849990",
            "PATH_NAME": "93.IPXN.100466..CHTR.001",
            "PATH_REV": "1",
            "A_SITE_INST_ID": "3169",
            "A_SITE_NAME": "PIQUOH07-TWC/HUB PQ-PIQUA (PQUAOH01)",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "TDM",
            "PATH_BW": "DS1",
            "CUSTOMER_ID": "KETTERING HEALTH NETWORK",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "CUS-VOICE-PRI",
        },
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "A_SITE_INST_ID": "561465",
            "A_SITE_NAME": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "A_SITE_TYPE": "LOCAL",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET",
            "PATH_BW": "1 Gbps",
            "CUSTOMER_ID": "ACCT-01574543",
            "PATH_STATUS": "Pending Decommission",
            "SERVICE_TYPE": "COM-EPL",
        },
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "2270265",
            "PATH_NAME": "93.L1XX.003636..CHTR",
            "PATH_REV": "1",
            "A_SITE_INST_ID": "19192",
            "A_SITE_NAME": "KTNGOHAI-KETTERING HEALTH NETWORK//3535 SOUTHERN BLVD",
            "A_SITE_TYPE": "LOCAL",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET",
            "PATH_BW": "1 Gbps",
            "CUSTOMER_ID": "ACCT-01574543",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "COM-EPL",
        },
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "1784811",
            "PATH_NAME": "93.VSXX.002065..CHTR",
            "PATH_REV": "1",
            "A_SITE_INST_ID": "3169",
            "A_SITE_NAME": "PIQUOH07-TWC/HUB PQ-PIQUA (PQUAOH01)",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "RF",
            "PATH_BW": "RF",
            "CUSTOMER_ID": "KETTERING HEALTH NETWORK",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "CUS-VIDEO-FIBER CONNECT PLUS",
        },
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "2258486",
            "PATH_NAME": "93001.GE1.TROYOH090QW.PIQUOHAD2ZW",
            "PATH_REV": "2",
            "A_SITE_INST_ID": "3174",
            "A_SITE_NAME": "TROYOH09-TWC/HUB TR-TROY (TROYOH01)",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET TRANSPORT",
            "PATH_BW": "1 Gbps",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        },
        {
            "SITE_INST_ID": "568427",
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_TYPE": "LOCAL",
            "SITE_STATUS": "Live",
            "CIRC_PATH_INST_ID": "2277758",
            "PATH_NAME": "93001.GE10.PIQUOH070QW.PIQUOHAD1ZW",
            "PATH_REV": "1",
            "A_SITE_INST_ID": "3169",
            "A_SITE_NAME": "PIQUOH07-TWC/HUB PQ-PIQUA (PQUAOH01)",
            "A_SITE_TYPE": "HUB",
            "Z_SITE_INST_ID": "568427",
            "Z_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_TYPE": "LOCAL",
            "PATH_TYPE": "ETHERNET TRANSPORT",
            "PATH_BW": "10 Gbps",
            "PATH_STATUS": "Live",
            "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        },
    ]
    get_path_elements_l1_resp = [
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
        },
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
        },
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
        },
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
        },
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
        },
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Pending Decommission",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
        },
    ]
    disco_transport_update_resp = {
        "pathId": "93001.GE1.TROYOH090QW.PIQUOHAD2ZW",
        "pathRev": "2",
        "status": "Pending Decommission",
        "pathInstanceId": "2258486",
        "retString": "Path Updated",
    }
    disco_cpe_update_resp = {
        "id": "PIQUOHAD2ZW/999.9999.999.99/SWT",
        "status": "Pending Decommission",
        "equipInstId": "1225653",
        "retString": "Shelf Updated",
    }
    return (
        granite_paths_url_resp,
        get_circuit_side_info_resp,
        put_granite_resp,
        get_zsite_voice_resp,
        paths_from_site_resp,
        get_path_elements_l1_resp,
        disco_transport_update_resp,
        disco_cpe_update_resp,
    )


@pytest.mark.unittest
def test_disco_path_update_epl_fiber(disco_path_update_epl_fiber_data, monkeypatch):
    cid = "93.L1XX.003635..CHTR"
    body = {
        "service_type": "disconnect",
        "product_name": "EPL (Fiber)",
        "status": "Pending Decommission",
        "due_date": "2023-04-03",
        "engineering_job_type": "Full Disconnect",
        "engineering_name": "ENG-052",
        "service_location_address": "308 LOONEY RD",
    }
    response = {
        "message": "Full Disconnect complete",
        "cid_disconnect_data": {
            "pathId": "93.L1XX.003635..CHTR",
            "pathRev": "2",
            "status": "Pending Decommission",
            "pathInstanceId": "2313452",
            "retString": "Path Updated",
        },
        "site_disconnect_data": "Multiple live paths found. Did not disconnect site",
        "transport_disconnect_data": {
            "pathId": "93001.GE1.TROYOH090QW.PIQUOHAD2ZW",
            "pathRev": "2",
            "status": "Pending Decommission",
            "pathInstanceId": "2258486",
            "retString": "Path Updated",
        },
        "cpe_disconnect_data": {
            "id": "PIQUOHAD2ZW/999.9999.999.99/SWT",
            "status": "Pending Decommission",
            "equipInstId": "1225653",
            "retString": "Shelf Updated",
        },
        "status": "Pending Decommission",
    }

    (
        granite_paths_url_resp,
        get_circuit_side_info_resp,
        put_granite_resp,
        get_zsite_voice_resp,
        paths_from_site_resp,
        get_path_elements_l1_resp,
        disco_transport_update_resp,
        disco_cpe_update_resp,
    ) = disco_path_update_epl_fiber_data

    monkeypatch.setattr(cs, "get_granite", lambda *args, **kwargs: granite_paths_url_resp)
    monkeypatch.setattr(cs, "get_circuit_side_info", lambda *args, **kwargs: get_circuit_side_info_resp)
    monkeypatch.setattr(cs, "put_granite", lambda *args, **kwargs: put_granite_resp)
    monkeypatch.setattr(cs, "get_zsite_voice", lambda *args, **kwargs: get_zsite_voice_resp)
    monkeypatch.setattr(cs, "paths_from_site", lambda *args, **kwargs: paths_from_site_resp)
    monkeypatch.setattr(cs, "get_path_elements_l1", lambda *args, **kwargs: get_path_elements_l1_resp)
    monkeypatch.setattr(cs, "disco_transport_update", lambda *args, **kwargs: disco_transport_update_resp)
    monkeypatch.setattr(cs, "disco_cpe_update", lambda *args, **kwargs: disco_cpe_update_resp)
    assert cs.disco_path_update(cid, body) == response


@pytest.fixture
def get_zw_device_tid_data():
    single_shelf_data = {
        "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
        "SITE_INST_ID": "568427",
        "SITE_CATEGORY": "LOCAL",
        "SITE_STATUS": "Live",
        "SITE_CLLI": "PIQUOHAD",
        "EQUIP_NAME": "PIQUOHAD2ZW/999.9999.999.99/SWT",
        "EQUIP_INST_ID": "1225653",
        "EQUIP_CATEGORY": "SWITCH",
        "EQUIP_STATUS": "Live",
        "EQUIP_VENDOR": "ADVA",
        "EQUIP_MODEL": "FSP 150-GE114PRO-C",
        "FQDN": "PIQUOHAD2ZW.MW.TWCBIZ.COM",
        "TARGET_ID": "PIQUOHAD2ZW",
        "IPV4_ADDRESS": "10.10.29.248/24",
        "OBJECT_TYPE": "SHELF",
    }
    multi_shelf_data = [
        {
            "SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "SITE_INST_ID": "568427",
            "SITE_CATEGORY": "LOCAL",
            "SITE_STATUS": "Live",
            "SITE_CLLI": "PIQUOHAD",
            "EQUIP_NAME": "PIQUOHAD1ZW/999.9999.999.99/SWT",
            "EQUIP_INST_ID": "1371960",
            "EQUIP_CATEGORY": "SWITCH",
            "EQUIP_STATUS": "Live",
            "EQUIP_VENDOR": "ADVA",
            "EQUIP_MODEL": "FSP 150-XG116PRO",
            "FQDN": "PIQUOHAD1ZW.CML.CHTRSE.COM",
            "TARGET_ID": "PIQUOHAD1ZW",
            "IPV4_ADDRESS": "10.9.31.181/24",
            "OBJECT_TYPE": "SHELF",
        },
        single_shelf_data,
    ]

    elements_data = [
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
            "CUSTOMER_NAME": "KETTERING HEALTH NETWORK",
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
            "LEG_INST_ID": "2643163",
            "A_SITE_NAME": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "TROYOHAA2ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "1626093",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "4-1/10GBE",
            "PORT_NAME": "1",
            "PORT_INST_ID": "113268753",
            "PORT_ACCESS_ID": "ETH_PORT-1-1-1-4",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "TROYOHAA2ZW.CML.CHTRSE.COM",
            "MODEL": "FSP 150-XG116PRO",
            "VENDOR": "ADVA",
            "TID": "TROYOHAA2ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "DEVICE_INFO_NETWORK": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "DHCP",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1201",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "93.L1XX.003635..CHTR",
            "INITIAL_CIRCUIT_ID": "2313452",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2313452",
            "PATH_NAME": "93.L1XX.003635..CHTR",
            "PATH_REV": "2",
            "PATH_CATEGORY": "ETHERNET",
            "PATH_A_SITE": "TROYOHAA-KETTERING HEALTH NETWORK//600 W MAIN ST",
            "PATH_Z_SITE": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "A_CLLI": "TROYOHAA",
            "Z_CLLI": "PIQUOHAD",
            "PATH_A_SITE_TYPE": "LOCAL",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "EVC_ID": None,
            "SERVICE_TYPE": "COM-EPL",
            "BANDWIDTH": "1 Gbps",
            "BW_SIZE": "1000000000",
            "CUSTOMER_ID": "ACCT-01574543",
            "CUSTOMER_NAME": "KETTERING HEALTH NETWORK",
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
            "LEG_INST_ID": "2643163",
            "A_SITE_NAME": "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "PIQUOHAD2ZW/999.9999.999.99/SWT",
            "ELEMENT_REFERENCE": "1225653",
            "ELEMENT_CATEGORY": "SWITCH",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "04",
            "PORT_NAME": "1",
            "PORT_INST_ID": "106860430",
            "PORT_ACCESS_ID": "ACCESS-1-1-1-4",
            "CONNECTOR_TYPE": "LC",
            "PORT_CHANNELIZATION": None,
            "FQDN": "PIQUOHAD2ZW.MW.TWCBIZ.COM",
            "MODEL": "FSP 150-GE114PRO-C",
            "VENDOR": "ADVA",
            "TID": "PIQUOHAD2ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "DEVICE_INFO_NETWORK": None,
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.10.29.248/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1204",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "93.L1XX.003635..CHTR",
            "INITIAL_CIRCUIT_ID": "2313452",
            "LVL": "1",
        },
    ]

    return single_shelf_data, multi_shelf_data, elements_data


@pytest.mark.unittest
def test_get_zw_device_tid(get_zw_device_tid_data, monkeypatch):
    pathid = "93.L1XX.003635..CHTR"
    clli = "PIQUOHAD"
    site_name = "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD"
    zw = "PIQUOHAD2ZW"

    single_shelf_data, multi_shelf_data, elements_data = get_zw_device_tid_data
    existing_shelf_data = iter([[single_shelf_data], multi_shelf_data, "not a list", multi_shelf_data, multi_shelf_data])
    incorrect_site_name = deepcopy(elements_data)
    incorrect_site_name[1]["A_SITE_NAME"] = "PIQUOHA-KETTERING HEALTH NETWORK//308 LOONEY RD"
    missing_tid = deepcopy(elements_data)
    missing_tid[1].pop("TID")
    path_elements_data = iter([elements_data, incorrect_site_name, missing_tid])

    # mock helper method calls
    monkeypatch.setattr(cs, "get_existing_shelf", lambda *args, **kwargs: next(existing_shelf_data))
    monkeypatch.setattr(cs, "get_path_elements", lambda *args, **kwargs: next(path_elements_data))

    # single ZW device shelf
    assert cs.get_zw_device_tid(pathid, clli, site_name) == zw

    # multiple ZW device shelves
    assert cs.get_zw_device_tid(pathid, clli, site_name) == zw

    # fall-out conditions
    try:
        cs.get_zw_device_tid(pathid, clli, site_name)
    except AbortException as e:
        assert "Unable to retrieve ZW device of circuit at" in e.data["message"]

    try:
        cs.get_zw_device_tid(pathid, clli, site_name)
    except AbortException as e:
        assert "Unable to retrieve tid of ZW device at" in e.data["message"]

    try:
        cs.get_zw_device_tid(pathid, clli, site_name)
    except AbortException as e:
        assert "Missing TID of ZW device at" in e.data["message"]


@pytest.mark.unittest
def test_get_zw_device_tid_no_shelves(monkeypatch):
    pathid = "93.L1XX.003635..CHTR"
    clli = "PIQUOHAD"
    site_name = "PIQUOHAD-KETTERING HEALTH NETWORK//308 LOONEY RD"
    mock_get_existing_shelf = Mock(return_value=[{}])
    monkeypatch.setattr(cs, "get_existing_shelf", mock_get_existing_shelf)
    try:
        cs.get_zw_device_tid(pathid, clli, site_name)
    except AbortException as e:
        assert "No existing ZW shelf at" in e.data["message"]
