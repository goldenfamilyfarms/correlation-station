import pytest
from copy import deepcopy
from pytest import raises
import json

from arda_app.bll.net_new.vlan_reservation import vlan_utils as vu
from arda_app.api import type_2_outer_vlan_request as outer_vlan
from arda_app.bll.models.payloads.vlan_reservation import Type2OuterVLANRequestPayloadModel
from arda_app.bll.net_new.vlan_reservation import vlan_reservation_main as vbcd
from arda_app.bll.net_new.vlan_reservation import collect_vlans as cv


path_elements_data = [
    {
        "CIRC_PATH_INST_ID": "2511364",
        "PATH_NAME": "60.KGFD.000001..TWCC",
        "PATH_REV": "3",
        "PATH_CATEGORY": "ETHERNET TRANSPORT",
        "PATH_A_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
        "PATH_Z_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
        "A_CLLI": "PHNHAZVA",
        "Z_CLLI": "PHNHAZVA",
        "PATH_A_SITE_TYPE": "COLO",
        "PATH_Z_SITE_TYPE": "COLO",
        "TOPOLOGY": "Point-to-point",
        "PATH_STATUS": "Live",
        "CLASS_OF_SERVICE": None,
        "SLM_ELIGIBILITY": "INELIGIBLE DESIGN",
        "EVC_ID": None,
        "SERVICE_TYPE": "CUS-ENNI-BUY",
        "BANDWIDTH": "10 Gbps",
        "BW_SIZE": "10000000000",
        "CUSTOMER_ID": "ACCT-04797547",
        "CUSTOMER_NAME": "BUY NNI",
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
        "LEG_INST_ID": "2899815",
        "A_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
        "Z_SITE_NAME": None,
        "ELEMENT_TYPE": "PORT",
        "ELEMENT_NAME": "PHNHAZVA1CW/001.00D.004.01/RTR",
        "ELEMENT_REFERENCE": "503601",
        "ELEMENT_CATEGORY": "ROUTER",
        "ELEMENT_STATUS": "Live",
        "ELEMENT_BANDWIDTH": "10 Gbps",
        "NEXT_PATH_INST_ID": None,
        "PREV_PATH_INST_ID": None,
        "CHAN_NAME": None,
        "CHAN_INST_ID": None,
        "SLOT": "[0/2]/1",
        "PORT_NAME": "1",
        "PORT_INST_ID": "114433805",
        "PORT_ACCESS_ID": "XE-1/2/1",
        "CONNECTOR_TYPE": "LC",
        "PORT_CHANNELIZATION": "DYNAMIC",
        "FQDN": "PHNHAZVA1CW.CHTRSE.COM",
        "MODEL": "MX240",
        "VENDOR": "JUNIPER",
        "TID": "PHNHAZVA1CW",
        "LEGACY_EQUIP_SOURCE": "L-TWC",
        "DEVICE_INFO_NETWORK": None,
        "LVL": "1",
    }
]
device = {"PHNHAZVA1CW": "XE-1/2/1"}

payload = Type2OuterVLANRequestPayloadModel(
    nni="60.KGFD.000001..TWCC", exclusion_list=[1100, 1101, 1103], product_name="Fiber Internet Access"
)
response = {"vlan": 5}
get_granite_data = [
    {
        "CIRC_PATH_INST_ID": "2511364",
        "PATH_NAME": "60.KGFD.000001..TWCC",
        "PATH_REV": "3",
        "PATH_CATEGORY": "ETHERNET TRANSPORT",
        "PATH_A_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
        "PATH_Z_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
        "A_CLLI": "PHNHAZVA",
        "Z_CLLI": "PHNHAZVA",
        "PATH_A_SITE_TYPE": "COLO",
        "PATH_Z_SITE_TYPE": "COLO",
        "TOPOLOGY": "Point-to-point",
        "PATH_STATUS": "Live",
        "CLASS_OF_SERVICE": None,
        "SLM_ELIGIBILITY": "INELIGIBLE DESIGN",
        "EVC_ID": None,
        "SERVICE_TYPE": "CUS-ENNI-BUY",
        "BANDWIDTH": "10 Gbps",
        "BW_SIZE": "10000000000",
        "CUSTOMER_ID": "ACCT-04797547",
        "CUSTOMER_NAME": "BUY NNI",
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
        "LEG_INST_ID": "2899815",
        "A_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
        "Z_SITE_NAME": None,
        "ELEMENT_TYPE": "PORT",
        "ELEMENT_NAME": "PHNHAZVA1CW/001.00D.004.01/RTR",
        "ELEMENT_REFERENCE": "503601",
        "ELEMENT_CATEGORY": "ROUTER",
        "ELEMENT_STATUS": "Live",
        "ELEMENT_BANDWIDTH": "10 Gbps",
        "NEXT_PATH_INST_ID": None,
        "PREV_PATH_INST_ID": None,
        "CHAN_NAME": None,
        "CHAN_INST_ID": None,
        "SLOT": "[0/2]/1",
        "PORT_NAME": "1",
        "PORT_INST_ID": "114433805",
        "PORT_ACCESS_ID": "XE-1/2/1",
        "CONNECTOR_TYPE": "LC",
        "PORT_CHANNELIZATION": "DYNAMIC",
        "FQDN": "PHNHAZVA1CW.CHTRSE.COM",
        "MODEL": "MX240",
        "VENDOR": "JUNIPER",
        "TID": "PHNHAZVA1CW",
        "LEGACY_EQUIP_SOURCE": "L-TWC",
        "DEVICE_INFO_NETWORK": None,
        "LVL": "1",
    }
]
get_granite_no_records_found = {
    "instId": "0",
    "retCode": 2,
    "httpCode": 200,
    "retString": "No records found with the specified search criteria...",
}
network_outer_vlans_data = {
    "1623",
    "749",
    "108",
    "613",
    "624",
    "609",
    "120",
    "219",
    "1232",
    "636",
    "2345",
    "248",
    "215",
    "3443",
    "223",
    "167",
    "243",
    "229",
    "225",
    "1265",
    "249",
    "125",
    "121",
}
get_granite_vlans_data = "12"
get_nni_tid_port_data = {"PHNHAZVA1CW": "XE-1/2/1"}
get_device_vendor_data = "JUNIPER"
get_device_model_data = "MX240"
onboard_and_exe_cmd_data = {
    "result": {
        "data": {
            "configuration": {
                "interfaces": {
                    "interface": {
                        "unit": [
                            {
                                "name": "11000",
                                "description": "60.L1XX.006270..CHTR:CUST:FIA:85008:",
                                "bandwidth": "50m",
                                "vlan-tags": {"outer": "225", "inner": "1100"},
                            },
                            {
                                "name": "11001",
                                "description": "92.L1XX.990714..CHTR:CUST:FIA:86336:",
                                "bandwidth": "100m",
                                "vlan-tags": {"outer": "120", "inner": "1101"},
                            },
                            {
                                "name": "11002",
                                "description": "80.L1XX.995263..CHTR:CUST:FIA:84660:",
                                "bandwidth": "100m",
                                "vlan-tags": {"outer": "108", "inner": "1102"},
                            },
                        ]
                    }
                }
            }
        }
    }
}
vlans = {"225", "120", "108"}
vlans_outer_false = {"11000", "11001", "11002"}
attempt_onboarding = False
path_chan_availability = [
    {
        "CIRC_PATH_INST_ID": "2511364",
        "PATH_NAME": "60.KGFD.000001..TWCC",
        "PATH_REV": "3",
        "PATH_STATUS": "Live",
        "PATH_CATEGORY": "ETHERNET TRANSPORT",
        "PATH_BANDWIDTH": "10 Gbps",
        "CHAN_NAME": "11018:OV-2345//IV-1118",
        "VLAN_NBR": "1101823451118",
        "CHAN_INST_ID": "10789527",
        "CHANNEL_USED": "41",
        "CHAN_BANDWIDTH": "1 Gbps",
        "MEMBER_PATH": "52.L1XX.000061..CHTR",
        "MEMBER_INST_ID": "2477324",
        "MEMBER_BANDWIDTH": "1 Gbps",
        "MEMBER_CUSTOMER": "ACCT-02581909",
        "MEMBER_CUSTOMER_NAME": "CATERPILLAR, INC.",
        "CHAN_AVAILABILITY": "IN USE",
    }
]


@pytest.mark.unittest
def test_get_network_outer_vlans(monkeypatch):
    monkeypatch.setattr(cv, "get_nni_tid_port", lambda *args, **kwargs: get_nni_tid_port_data)
    monkeypatch.setattr(cv, "get_device_vendor", lambda *args, **kwargs: get_device_vendor_data)
    monkeypatch.setattr(cv, "get_device_model", lambda *args, **kwargs: get_device_model_data)
    monkeypatch.setattr(cv, "onboard_and_exe_cmd", lambda *args, **kwargs: onboard_and_exe_cmd_data)
    assert vbcd.get_network_outer_vlans("60.KGFD.000001..TWCC", attempt_onboarding, type2=True) == vlans


@pytest.mark.unittest
def test_get_device_vlans(monkeypatch):
    monkeypatch.setattr(cv, "onboard_and_exe_cmd", lambda *args, **kwargs: onboard_and_exe_cmd_data)
    monkeypatch.setattr(cv, "get_device_vendor", lambda *args, **kwargs: get_device_vendor_data)
    monkeypatch.setattr(cv, "get_device_model", lambda *args, **kwargs: get_device_model_data)

    # not an outer vlan scenario
    assert cv._get_device_vlans(get_nni_tid_port_data, type2=True, attempt_onboarding=False) == vlans_outer_false

    # outer vlan scenario
    assert cv._get_device_vlans(get_nni_tid_port_data, type2=True, attempt_onboarding=False, outer_vlan=True) == vlans

    # good test - RAD device
    monkeypatch.setattr(cv, "get_device_vendor", lambda *args, **kwargs: "RAD")
    monkeypatch.setattr(cv, "_filter_mdso_response", lambda *args, **kwargs: vlans)
    assert cv._get_device_vlans(get_nni_tid_port_data, type2=True, attempt_onboarding=False) == vlans

    # bad test - CIENA device, abort unsupported
    monkeypatch.setattr(cv, "get_device_vendor", lambda *args, **kwargs: "CIENA")
    with pytest.raises(Exception):
        assert cv._get_device_vlans(get_nni_tid_port_data, type2=True, attempt_onboarding=False) is None


@pytest.mark.unittest
def test_outer_vlan(monkeypatch):
    monkeypatch.setattr(vu, "get_path_elements", lambda *args, **kwargs: path_elements_data)
    monkeypatch.setattr(vbcd, "get_granite", lambda *args, **kwargs: get_granite_data)
    monkeypatch.setattr(vbcd, "get_network_outer_vlans", lambda *args, **kwargs: network_outer_vlans_data)
    monkeypatch.setattr(vbcd, "get_granite_vlans", lambda *args, **kwargs: get_granite_vlans_data)
    result = outer_vlan.vlan_request(payload).body.decode("utf-8")
    assert result == json.dumps(response).replace(" ", "")


@pytest.mark.unittest
def test_get_nni_tid_port(monkeypatch):
    # happy path
    monkeypatch.setattr(vu, "get_path_elements", lambda *args, **kwargs: path_elements_data)
    assert vu.get_nni_tid_port("60.KGFD.000001..TWCC") == device

    # no record found in Granite
    monkeypatch.setattr(vu, "get_path_elements", lambda *args, **kwargs: {})
    assert vu.get_nni_tid_port("nni") == {}

    # update lvl to 2 so that device will be empty
    path_elements_data_copy = deepcopy(path_elements_data)
    path_elements_data_copy[0]["LVL"] = "2"
    monkeypatch.setattr(vu, "get_path_elements", lambda *args, **kwargs: path_elements_data_copy)
    assert vu.get_nni_tid_port("60.KGFD.000001..TWCC") == {}

    # update element_category to other than Router
    path_elements_data_copy = deepcopy(path_elements_data)
    path_elements_data_copy[0]["ELEMENT_CATEGORY"] = "NON ROUTER"
    monkeypatch.setattr(vu, "get_path_elements", lambda *args, **kwargs: path_elements_data_copy)
    assert vu.get_nni_tid_port("60.KGFD.000001..TWCC") == {}


@pytest.mark.unittest
def test_get_outer_vlan(monkeypatch: pytest.MonkeyPatch):
    # mock data section
    network_outer_vlans = {"8", "9", "7"}
    granite_outer_vlans = {"5", "6", "10"}
    expected = 14
    payload = Type2OuterVLANRequestPayloadModel(
        nni="60.KGFD.000001..TWCC", exclusion_list=[11, 12, 13], product_name="Carrier Fiber Internet Access"
    )
    transports = [{"CIRC_PATH_INST_ID": "2511364", "PATH_NAME": "60.KGFD.000001..TWCC", "LVL": "1"}]
    attempt_onboarding = False
    type2 = True

    # monkeypatch code section
    monkeypatch.setattr(vbcd, "get_network_outer_vlans", lambda *args, **kwargs: network_outer_vlans)
    monkeypatch.setattr(vbcd, "get_granite_vlans", lambda *args, **kwargs: granite_outer_vlans)
    monkeypatch.setattr(vbcd, "get_next_available_vlan_or_subinterface", lambda *args, **kwargs: expected)

    # assert the response from the call to get_outer_vlan
    assert vbcd.get_outer_vlan(payload, transports, attempt_onboarding, type2) == expected


@pytest.mark.unittest
def test_type_2_outer_vlan_request(monkeypatch: pytest.MonkeyPatch):
    # granite records found
    monkeypatch.setattr(vbcd, "get_granite", lambda *args, **kwargs: path_elements_data)
    monkeypatch.setattr(vbcd, "get_outer_vlan", lambda *args, **kwargs: response["vlan"])
    assert vbcd.type_2_outer_vlan_request(payload) == response

    # no granite records found
    monkeypatch.setattr(vbcd, "get_granite", lambda *args, **kwargs: get_granite_no_records_found)
    with raises(Exception):
        assert vbcd.type_2_outer_vlan_request(payload) is None


@pytest.mark.unittest
def test_get_granite_vlans(monkeypatch: pytest.MonkeyPatch):
    # mock data
    expected = {"2345"}

    # outer vlan tag with '-'
    path_chan_availability_copy = deepcopy(path_chan_availability)
    monkeypatch.setattr(cv, "get_granite", lambda *args, **kwargs: path_chan_availability_copy)
    assert vbcd.get_granite_vlans(get_granite_data, outer_vlan=True) == expected

    # outer vlan tag without '-'
    path_chan_availability_copy = deepcopy(path_chan_availability)
    path_chan_availability_copy[0]["CHAN_NAME"] = path_chan_availability_copy[0]["CHAN_NAME"].replace("OV-", "OV")
    monkeypatch.setattr(cv, "get_granite", lambda *args, **kwargs: path_chan_availability_copy)
    assert vbcd.get_granite_vlans(get_granite_data, outer_vlan=True) == expected


@pytest.mark.unittest
def test_filter_mdso_response():
    # mock data
    is_cw = True
    host = list(get_nni_tid_port_data.keys())[0]
    port = list(get_nni_tid_port_data.values())[0]
    type2 = True
    outer_vlan = True
    expected = ["225", "120", "108"]

    # outer vlan tag present
    assert (
        cv._filter_mdso_response(get_device_vendor_data, onboard_and_exe_cmd_data, is_cw, host, port, type2, outer_vlan)
        == expected
    )

    # missing outer vlan tag
    onboard_and_exe_cmd_data_copy = deepcopy(onboard_and_exe_cmd_data)
    onboard_and_exe_cmd_data_copy["result"]["data"]["configuration"]["interfaces"]["interface"]["unit"][0][
        "vlan-tags"
    ].pop("outer")
    with raises(Exception):
        assert (
            cv._filter_mdso_response(
                get_device_vendor_data, onboard_and_exe_cmd_data_copy, is_cw, host, port, type2, outer_vlan
            )
            is None
        )

    # Good test - dict missing vlan-id
    response = {
        "result": {
            "data": {
                "configuration": {
                    "interfaces": {
                        "interface": {
                            "unit": {
                                "name": "11000",
                                "description": "60.L1XX.006270..CHTR:CUST:FIA:85008:",
                                "bandwidth": "50m",
                                "vlan-tags": {"outer": "225", "inner": "1100"},
                            }
                        }
                    }
                }
            }
        }
    }

    assert cv._filter_mdso_response(get_device_vendor_data, response, is_cw, host, port, False, False) == [""]
