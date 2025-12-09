from copy import deepcopy

import pytest
from pytest import raises

import arda_app.bll.circuit_design.bandwidth_change.normal_bw_upgrade as nbu

from arda_app.dll import granite
from mock_data.circuit_design.circuit_upgrade import normal_upgrade, pathid

from common_sense.common.errors import AbortException

EC_MSG = "Customer coordination is required for CPE shelf swap."


@pytest.mark.unittest
def test_bw_upgrade_main(monkeypatch):
    # PRISM ID
    with raises(AbortException):
        assert nbu.bw_upgrade_main({"pid": "test"}) is None

    # wrong product
    nu1 = normal_upgrade.copy()
    nu1["product_name"] = "wrong product"

    with raises(AbortException):
        assert nbu.bw_upgrade_main(nu1) is None

    # ctbh connector/ uni_type abort
    nu3 = normal_upgrade.copy()
    nu3["product_name"] = "Carrier CTBH"
    nu3["spectrum_primary_enni"] = "71.TEST.000000..TWCC"
    nu3["uni_type"] = "routed"

    with raises(AbortException):
        assert nbu.bw_upgrade_main(nu3) is None

    # ctbh No ENNI path elements found trunked unitype
    nu3["uni_type"] = "Trunked"

    monkeypatch.setattr(nbu, "check_enni", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "check_vlan", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "get_path_elements_l1", lambda *args, **kwargs: None)

    with raises(AbortException):
        assert nbu.bw_upgrade_main(nu3) is None

    # ctbh cpe_upgrade_needed
    cpe_upgrade_needed = {"PORT_ACCESS_ID": "PORT_ACCESS_ID", "TID": "TID"}

    monkeypatch.setattr(nbu, "get_path_elements_l1", lambda *args, **kwargs: [])
    monkeypatch.setattr(nbu, "enni_oversub_check", lambda *args, **kwargs: "enni_list")
    monkeypatch.setattr(
        nbu, "_validate_payload", lambda *args, **kwargs: ("req_bw_val", "req_bw_unit", "mbps_req_bw_val")
    )

    monkeypatch.setattr(nbu, "_check_granite_bandwidth", lambda *args, **kwargs: ("500", "Mbps", 400, "12345", "1"))
    monkeypatch.setattr(nbu, "upgrade_bw_compare", lambda *args, **kwargs: "mbps_delta_bw_val")
    monkeypatch.setattr(nbu, "carrier_transport_paths", lambda *args, **kwargs: ("transport_paths", "all_paths"))

    monkeypatch.setattr(nbu, "_check_handoff_port", lambda *args, **kwargs: cpe_upgrade_needed)
    monkeypatch.setattr(nbu, "check_transport_paths_ctbh", lambda *args, **kwargs: (None, "trans_name"))
    monkeypatch.setattr(nbu, "edna_check_ctbh", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "sforce_granite_compare", lambda *args, **kwargs: None)

    with raises(AbortException):
        assert nbu.bw_upgrade_main(nu3) is None

    # Fiber Internet Access NO rev_result
    nu3["product_name"] = "Fiber Internet Access"

    monkeypatch.setattr(
        nbu, "_granite_transport_devices_network_checks", lambda *args, **kwargs: ("transport_paths", "all_paths")
    )
    monkeypatch.setattr(nbu, "_check_transport_paths", lambda *args, **kwargs: ("trans_id", "trans_name.ZW"))
    monkeypatch.setattr(nbu, "hub_transport_check", lambda *args, **kwargs: False)
    monkeypatch.setattr(nbu, "trans_path_upgrade", lambda *args, **kwargs: ("trans_data", "new_shelf", "resp_data"))
    monkeypatch.setattr(nbu, "device_check", lambda *args, **kwargs: "ec_msg")

    monkeypatch.setattr(
        nbu, "_granite_create_circuit_revision", lambda *args, **kwargs: (None, "rev_instance", "rev_path")
    )

    with raises(AbortException):
        assert nbu.bw_upgrade_main(nu3) is None

    # rev_instance == main_inst
    monkeypatch.setattr(
        nbu, "_granite_create_circuit_revision", lambda *args, **kwargs: ("rev_result", "12345", "rev_path")
    )

    with raises(AbortException):
        assert nbu.bw_upgrade_main(nu3) is None

    # EP-LAN (Fiber)
    nu3["product_name"] = "EP-LAN (Fiber)"

    monkeypatch.setattr(
        nbu, "_granite_create_circuit_revision", lambda *args, **kwargs: ("rev_result", "54321", "rev_path")
    )

    monkeypatch.setattr(nbu, "evc_assoc_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "cpe_10g_swap", lambda *args, **kwargs: ("ec_msg", True))
    monkeypatch.setattr(nbu, "remove_1G_transport", lambda *args, **kwargs: None)

    monkeypatch.setattr(nbu, "express_update_circuit_bw", lambda *args, **kwargs: {})
    monkeypatch.setattr(nbu, "update_circuit_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "bw_upgrade_assign_gsip", lambda *args, **kwargs: None)

    result = {
        "cpe_installer": True,
        "mw_needed": "Yes - No Hub Impacted - Inflight Customer Only Impacted",
        "hub_work_required": False,
        "circuit_design_notes": "ec_msg",
    }

    assert nbu.bw_upgrade_main(nu3) == result

    # Fiber Internet Access
    nu3["product_name"] = "Fiber Internet Access"

    monkeypatch.setattr(nbu, "fia_ipv6_check", lambda *args, **kwargs: None)

    assert nbu.bw_upgrade_main(nu3) == result

    # Carrier E Access
    nu3["product_name"] = "Carrier E-Access (Fiber)"
    monkeypatch.setattr(nbu, "enni_oversub_check", lambda *args, **kwargs: [{"ELEMENT_NAME": "trans_name"}])
    monkeypatch.setattr(nbu, "_check_handoff_port", lambda *args, **kwargs: None)

    result = {
        "cpe_installer": True,
        "mw_needed": "Yes - No Hub Impacted - Inflight Customer Only Impacted",
        "hub_work_required": False,
        "circuit_design_notes": "ec_msg",
    }
    assert nbu.bw_upgrade_main(nu3) == result


@pytest.mark.unittest
def test_cross_duplex_bw_threshold():
    assert nbu._cross_duplex_bw_threshold([100], 70, 100) is False
    assert nbu._cross_duplex_bw_threshold([100], 70, 120) is True
    assert nbu._cross_duplex_bw_threshold([], 70, 120) is False


@pytest.mark.unittest
def test_fia_ipv6_check(monkeypatch):
    data_resp = {
        "IPV4_ASSIGNED_SUBNETS": "/29",
        "IPV6_ASSIGNED_SUBNETS": "/48",
        "IPV4_GLUE_SUBNET": "",
        "IPV6_GLUE_SUBNET": "2605:E000:0:8::F:262E/64",
    }
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: [data_resp])
    assert nbu.fia_ipv6_check("pathid", False) is None

    data_resp["IPV6_GLUE_SUBNET"] = "2605:E000:0:8::F:262E/127"
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: [data_resp])

    with pytest.raises(AbortException):
        assert nbu.fia_ipv6_check("pathid", True) is None


@pytest.mark.unittest
def test_add_uplink_port(monkeypatch):
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: _exception())
    uplinkport = {"PORT_INST_ID": 1234}

    with pytest.raises(AbortException):
        assert nbu.add_uplink_port("path_name", "path_instid", uplinkport, "leg_inst_id") is None


def _exception():
    raise Exception


@pytest.mark.unittest
def test_remove_1G_transport(monkeypatch):
    # Exception test
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: _exception())

    with pytest.raises(AbortException):
        assert nbu.remove_1G_transport("path_name", "path_instid") is None

    # Retstring test
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: "retString")

    with pytest.raises(AbortException):
        assert nbu.remove_1G_transport("path_name", "path_instid") is None

    # No data test
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(AbortException):
        assert nbu.remove_1G_transport("path_name", "path_instid") is None

    # paths to delete len 2
    data = [
        {"ELEMENT_BANDWIDTH": "1 Gbps", "ELEMENT_CATEGORY": "ETHERNET TRANSPORT"},
        {"ELEMENT_BANDWIDTH": "1 Gbps", "ELEMENT_CATEGORY": "ETHERNET TRANSPORT"},
    ]
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: data)

    with pytest.raises(AbortException):
        assert nbu.remove_1G_transport("path_name", "path_instid") is None

    # No paths to delete
    data = [{"ELEMENT_BANDWIDTH": "10 Gbps", "ELEMENT_CATEGORY": "Bad"}]
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: data)

    with pytest.raises(AbortException):
        assert nbu.remove_1G_transport("path_name", "path_instid") is None

    # put granite exception
    data = [
        {"ELEMENT_BANDWIDTH": "1 Gbps", "ELEMENT_CATEGORY": "ETHERNET TRANSPORT", "LEG_INST_ID": "1234", "SEQUENCE": "1"}
    ]
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: data)
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: _exception())

    with pytest.raises(AbortException):
        assert nbu.remove_1G_transport("path_name", "path_instid") is None

    # all good test
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: None)
    assert nbu.remove_1G_transport("path_name", "path_instid") is None


@pytest.mark.unittest
def test_remove_uplink(monkeypatch):
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: _exception())
    uplinkport = {"LEG_INST_ID": 1234}

    with pytest.raises(AbortException):
        assert nbu.remove_uplink("path_name", "path_instid", uplinkport) is None


@pytest.mark.unittest
def test_port_check_10G(monkeypatch):
    data = [{"BANDWIDTH": "10 Gbps"}]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: data)
    assert nbu.port_check_10G("uplinkdevice") == data[0]

    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(AbortException):
        assert nbu.port_check_10G("uplinkdevice") is None


@pytest.mark.unittest
def test_granite_port_info(monkeypatch):
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: _exception())

    with pytest.raises(AbortException):
        assert nbu.granite_port_info(pathid, "path_instid") is None

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: "retString")

    with pytest.raises(AbortException):
        assert nbu.granite_port_info(pathid, "path_instid") is None

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [{"TID": "AUSWTXMA2AW"}])
    assert nbu.granite_port_info("51001.GE1.AUSWTXMA2AW.AUSWTXMADZW", "path_instid") == {"TID": "AUSWTXMA2AW"}

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(AbortException):
        assert nbu.granite_port_info("AUSWTXMA2AW", "path_instid") is None


@pytest.mark.unittest
def test_check_handoff_port(monkeypatch):
    # No paths found
    with pytest.raises(AbortException):
        assert nbu._check_handoff_port([], 100, "", "LAN") is None

    # Handoff port not found"
    with pytest.raises(AbortException):
        assert nbu._check_handoff_port([{"ELEMENT_TYPE": "test"}], 100, "", "LAN") is None

    # connector not in port_connector
    port = [
        {
            "A_SITE_NAME": "A_SITE_NAME",
            "ELEMENT_NAME": "ELEMENT_NAME",
            "ELEMENT_TYPE": "PORT",
            "PORT_ACCESS_ID": "PORT_ACCESS_ID",
            "ELEMENT_REFERENCE": "ELEMENT_REFERENCE",
            "ELEMENT_STATUS": "ELEMENT_STATUS",
            "ELEMENT_BANDWIDTH": "100 Gbps",
            "BANDWIDTH": "BANDWIDTH",
            "TID": "TID",
            "VENDOR": "VENDOR",
            "MODEL": "MODEL",
        }
    ]

    with pytest.raises(AbortException):
        assert nbu._check_handoff_port(port, 100, "RJ-45", "LAN") is None

    # all good
    assert nbu._check_handoff_port(port, 100, "", "LAN") is False

    # normal bw process
    port_100001 = port[0].copy()
    port_100001["Z_SIDE_SITE"] = "A_SITE_NAME"
    del port_100001["A_SITE_NAME"]
    assert nbu._check_handoff_port(port, 100001, "", "LAN") == port_100001

    # CTBH handoff port can not support bandwidth upgrade
    monkeypatch.setattr(nbu, "ctbh_cpe_check", lambda *args, **kwargs: 1000)

    with pytest.raises(AbortException):
        assert nbu._check_handoff_port(port, 100001, "", "LAN", ctbh=True) == port_100001

    # all good
    port[0]["ELEMENT_BANDWIDTH"] = "10/100/1000 BASET"
    assert nbu._check_handoff_port(port, 100, "", "LAN") is False

    # Exception while obtaining max bw value
    port[0]["ELEMENT_BANDWIDTH"] = "10/BASET"

    with pytest.raises(AbortException):
        assert nbu._check_handoff_port(port, 100, "", "LAN") is None

    # uni type / connector type granite mismatch abort
    port[0]["ELEMENT_BANDWIDTH"] = "10/100/1000 BASET"

    with pytest.raises(AbortException):
        assert nbu._check_handoff_port(port, 100, "", "Trunked") is None


@pytest.mark.unittest
def test_retrieve_transport_paths(monkeypatch):
    # bad exception test
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: _exception())

    with pytest.raises(AbortException):
        assert nbu._retrieve_transport_paths("99.L3XX.000001..TWCC") is None

    # normal all good
    gdata1 = [
        {
            "BANDWIDTH": "100 GBPS",
            "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
            "ELEMENT_NAME": "ELEMENT_NAME",
            "ELEMENT_REFERENCE": "ELEMENT_REFERENCE",
            "ELEMENT_STATUS": "ELEMENT_STATUS",
            "ELEMENT_BANDWIDTH": "ELEMENT_BANDWIDTH",
        }
    ]
    glist = iter([gdata1, gdata1, "retString", ""])
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: next(glist))

    gdata2 = gdata1[0].copy()
    gdata2.pop("ELEMENT_CATEGORY")
    assert nbu._retrieve_transport_paths("99.L3XX.000001..TWCC") == ([gdata2], gdata1)

    # no transport paths
    gdata1[0]["BANDWIDTH"] = "AGGREGATE"

    with pytest.raises(AbortException):
        assert nbu._retrieve_transport_paths("99.L3XX.000001..TWCC") is None

    # retstring error
    with pytest.raises(AbortException):
        assert nbu._retrieve_transport_paths("99.L3XX.000001..TWCC") is None

    # no data error
    with pytest.raises(AbortException):
        assert nbu._retrieve_transport_paths("99.L3XX.000001..TWCC") is None


@pytest.mark.unittest
def test_check_handoff_port_duplex_settings_ADVA(monkeypatch):
    cid = "21.L1XX.006991..TWCC"
    devices = {
        "ROCHNYXA1ZW": "GE-0/3/4",
        "BFLONYGO6ZW": "ETH PORT 5",
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/55",
        "BFLONYGO1AW": "ETH PORT 0/5",
    }
    monkeypatch.setattr(nbu, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, "", "", ""))
    monkeypatch.setattr(nbu, "get_device_vendor", lambda *args, **kwargs: "ADVA")
    monkeypatch.setattr(nbu, "_get_handoff_port_duplex_settings_ADVA", lambda *args, **kwargs: 100)

    maintenance_window_required = nbu._check_handoff_port_duplex_settings(cid, 50, 100, "FIA")
    assert maintenance_window_required is False


@pytest.mark.unittest
def test_check_handoff_port_duplex_settings_RAD(monkeypatch):
    cid = "21.L1XX.006991..TWCC"
    devices = {
        "ROCHNYXA1ZW": "GE-0/3/4",
        "BFLONYGO6ZW": "ETH PORT 5",
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/55",
        "BFLONYGO1AW": "ETH PORT 0/5",
    }
    monkeypatch.setattr(nbu, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, "", "", ""))
    monkeypatch.setattr(nbu, "get_device_vendor", lambda *args, **kwargs: "RAD")
    monkeypatch.setattr(nbu, "_get_handoff_port_duplex_settings_RAD", lambda *args, **kwargs: 100)
    maintenance_window_required = nbu._check_handoff_port_duplex_settings(cid, 50, 1000, "FIA")
    assert maintenance_window_required is True


@pytest.mark.unittest
def test_check_handoff_port_duplex_settings_Device_Unsupported(monkeypatch):
    cid = "21.L1XX.006991..TWCC"
    devices = {
        "ROCHNYXA1ZW": "GE-0/3/4",
        "BFLONYGO6ZW": "ETH PORT 5",
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/55",
        "BFLONYGO1AW": "ETH PORT 0/5",
    }
    monkeypatch.setattr(nbu, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, "", "", ""))
    monkeypatch.setattr(nbu, "get_device_vendor", lambda *args, **kwargs: "ALCATEL")

    with raises(AbortException):
        assert nbu._check_handoff_port_duplex_settings(cid, 50, 1000, "FIA") is None


@pytest.mark.unittest
def test_check_handoff_port_duplex_settings_upgrade_over_threshold(monkeypatch):
    cid = "21.L1XX.006991..TWCC"
    devices = {
        "ROCHNYXA1ZW": "GE-0/3/4",
        "BFLONYGO6ZW": "ETH PORT 5",
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/55",
        "BFLONYGO1AW": "ETH PORT 0/5",
    }
    monkeypatch.setattr(nbu, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, "", "", ""))
    monkeypatch.setattr(nbu, "get_device_vendor", lambda *args, **kwargs: "ADVA")
    monkeypatch.setattr(nbu, "_get_handoff_port_duplex_settings_ADVA", lambda *args, **kwargs: 100)
    maintenance_window_required = nbu._check_handoff_port_duplex_settings(cid, 100, 500, "FIA")
    assert maintenance_window_required is True


@pytest.mark.unittest
def test_check_handoff_port_duplex_settings_upgrade_over_1G_threshold(monkeypatch):
    cid = "21.L1XX.006991..TWCC"
    devices = {
        "ROCHNYXA1ZW": "GE-0/3/4",
        "BFLONYGO6ZW": "ETH PORT 5",
        "BFLONYKK1CW": "AE17",
        "BFLONYKK0QW": "XE-0/0/55",
        "BFLONYGO1AW": "ETH PORT 0/5",
    }
    monkeypatch.setattr(nbu, "get_circuit_tid_ports", lambda *args, **kwargs: (devices, "", "", ""))
    monkeypatch.setattr(nbu, "get_device_vendor", lambda *args, **kwargs: "RAD")
    monkeypatch.setattr(nbu, "_get_handoff_port_duplex_settings_RAD", lambda *args, **kwargs: 1000)
    maintenance_window_required = nbu._check_handoff_port_duplex_settings(cid, 500, 1500, "FIA")
    assert maintenance_window_required is False


@pytest.mark.unittest
def test_get_handoff_port_duplex_settings_ADVA(monkeypatch):
    zw_device = {"tid": "SNAUTXLW3ZW", "port_id": "ACCESS-1-1-1-3", "vendor": "ADVA"}
    network_data = {
        "command": "list_access_ports.json",
        "result": [
            {
                "orchState": "active",
                "properties": {
                    "sfp_media_type": "Not Available",
                    "tx_dei_action": "set-to-zero",
                    "rx_dei_outer_tag_type": "ctag-or-stag",
                    "mtu": 9600,
                    "llf_local_link_id": 3,
                    "sfp_laser_wave_length": "Not Available",
                    "configured_port_speed": "auto",
                    "rx_dei_action": "ignore",
                    "service_type": "evpl",
                    "media_type": "copper",
                    "secondary_states": "act",
                    "afp": "all-afp",
                    "port_vlan_id": "3-0",
                    "max_port_speed": 1000000000,
                    "admin_state": "in-service",
                    "negotiated_port_speed": "auto-1000-full",
                    "sfp_link_length": "Not Available",
                    "n2a_pop_port_vid": "disabled",
                    "a2n_push_port_vid": "disabled",
                    "name": "access-1-1-1-3",
                    "operational_state": "normal",
                    "alias": "EP-UNI:FIA:TASKUS,  INC.@300 E SONTERRA BLVD:21.L1XX.018627..CHTR:",
                    "auto_diagnostic": "disabled",
                    "tx_dei_outer_tag_type": "ctag-or-stag",
                    "n2a_vlan_trunking": "enabled",
                    "port_mode": "co",
                },
                "label": "access-1-1-1-3",
            }
        ],
        "parameters": {},
    }
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: network_data)
    assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) == 1000

    # Exceptions
    nd1 = deepcopy(network_data)
    nd2 = deepcopy(network_data)
    nd3 = deepcopy(network_data)
    nd4 = deepcopy(network_data)
    nd5 = deepcopy(network_data)
    nd6 = deepcopy(network_data)

    # missing negotiated_port_speed from result(list)
    del nd1["result"][0]["properties"]["negotiated_port_speed"]
    assert nd1["result"][0]["properties"].get("negotiated_port_speed") is None

    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd1)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None

    # missing negotiated_port_speed from result(dict)
    nd2["result"] = nd2["result"][0]
    assert isinstance(nd2["result"], dict)

    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd2)

    with raises(Exception):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None

    # missing zw_device
    zw_device = {}
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: network_data)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None

    # reset test data
    zw_device = {"tid": "SNAUTXLW3ZW", "port_id": "ACCESS-1-1-1-3", "vendor": "ADVA"}

    # missing network_data result value
    del nd3["result"]

    with raises(Exception):
        assert nd3["result"] is None

    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd3)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None

    # network_data(list) element "label" is different than port_access_id
    nd4["result"][0]["label"] = "access-1-1-1-4"
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd4)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None

    # network_data(dict) "label" is different than port_access_id
    nd5["result"] = nd5["result"][0]
    nd5["result"]["label"] = "access-1-1-1-5"
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd5)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None

    # duplex setting is not FULL
    nd6["result"][0]["properties"]["negotiated_port_speed"] = "auto-1000-half"
    nd6["result"][0]["label"] = "access-1-1-1-3"
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd6)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_ADVA(zw_device) is None


@pytest.mark.unittest
def test_get_handoff_port_duplex_settings_RAD(monkeypatch):
    zw_device = {"tid": "BRHMALFZ1ZW", "port_id": "ETH PORT 5", "vendor": "RAD"}
    network_data = {
        "command": "get-port-info-details.json",
        "result": {"speed-duplex": "1000-x-full-duplex", "name": ":EP-UNI:35242:VERIZON ENTERPRISE VES FEDERAL:"},
        "parameters": {"type": "ETHERNET", "id": "5"},
    }
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: network_data)
    assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) == 1000

    # Exceptions
    nd1 = deepcopy(network_data)
    nd2 = deepcopy(network_data)
    nd3 = deepcopy(network_data)
    nd4 = deepcopy(network_data)

    # missing ZW device
    zw_device = {}
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: network_data)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) is None

    # reset ZW device
    zw_device = {"tid": "BRHMALFZ1ZW", "port_id": "ETH PORT 5", "vendor": "RAD"}

    # missing network data parameters
    del nd1["parameters"]
    assert nd1.get("parameters") is None

    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd1)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) is None

    # network port id doesn't match
    nd2["parameters"]["id"] = "6"
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd2)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) is None

    # missing speed duplex value
    del nd3["result"]["speed-duplex"]
    assert nd3["result"].get("speed-duplex") is None
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd3)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) is None

    # unexpected format for network data
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: [network_data])

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) is None

    # unexpected value for duplex setting
    nd4["result"]["speed-duplex"] = "1000-x-half-duplex"
    monkeypatch.setattr(nbu, "onboard_and_exe_cmd", lambda *args, **kwargs: nd4)

    with raises(AbortException):
        assert nbu._get_handoff_port_duplex_settings_RAD(zw_device) is None


@pytest.mark.unittest
def test_new_cpe():
    cpe_swap = {"new_vendor": "ADVA"}
    result = {"new_vendor": "ADVA", "new_model": "FSP 150-XG108"}
    assert nbu.new_cpe(cpe_swap) == result

    cpe_swap = {"new_vendor": "RAD"}
    result = {"new_vendor": "RAD", "new_model": "ETX-2I-10G-B/8.5/8SFPP"}
    assert nbu.new_cpe(cpe_swap) == result

    cpe_swap = {"new_vendor": "CISCO"}
    with raises(AbortException):
        assert nbu.new_cpe(cpe_swap) is None


@pytest.mark.unittest
def test_multiple_paths_check(monkeypatch):
    transport_path_id = "71001.GE10.BFLRNYZV1AW.BFLRNYZV4ZW"
    cpe_swap_payload = {"cid": "21.L1XX.123456..TWCC"}

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [1])
    assert nbu.multiple_paths_check(transport_path_id, cpe_swap_payload) is None

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [1, 2])

    with raises(Exception):
        assert nbu.multiple_paths_check(transport_path_id, cpe_swap_payload) is None


@pytest.mark.unittest
def test_multiple_paths_check_with_multi_channels(monkeypatch):
    transport_path_id = "71001.GE10.BFLRNYZV1AW.BFLRNYZV4ZW"
    cpe_swap_payload = {"cid": "21.L1XX.123456..TWCC"}

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [{"MEMBER_PATH": 1}, 2])
    monkeypatch.setattr(nbu, "remove_1G_transport", lambda *args, **kwargs: None)

    with raises(Exception):
        assert nbu.multiple_paths_check(transport_path_id, cpe_swap_payload) is None


@pytest.mark.unittest
def test_check_transport_paths(monkeypatch):
    # clean test for check transport paths
    transport_paths = [
        {
            "ELEMENT_NAME": "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW",
            "CIRC_PATH_INST_ID": "125689",
            "ELEMENT_REFERENCE": "125689",
        }
    ]
    data = [{"BANDWIDTH": "1 Gbps", "AVAILABLE_BW": "600"}]

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: data)
    monkeypatch.setattr(nbu, "_validate_payload", lambda *args, **kwargs: (600, "Mbps", 600))
    assert nbu._check_transport_paths(transport_paths, 2000) == ("125689", "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW")

    # testing continue in for loop None, None
    data = [{"BANDWIDTH": "10 Gbps", "AVAILABLE_BW": "6000"}]
    monkeypatch.setattr(nbu, "_validate_payload", lambda *args, **kwargs: (600, "Mbps", 6000))
    assert nbu._check_transport_paths(transport_paths, 2000) == (None, None)

    # get_granite exception test
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: _exception())

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000) is None

    # testing 2nd exception error no available bandwidth
    data = [{"BANDWIDTH": "1 Gbps"}]
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: data)

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000) is None

    # testing len of data > 1 multi utilization fallout
    transport_paths.append(
        {
            "ELEMENT_NAME": "71001.GE1.BFLRNYZV1QW.BFLRNYZV3AW",
            "CIRC_PATH_INST_ID": "125669",
            "ELEMENT_REFERENCE": "125669",
        }
    )

    transport_paths.append(
        {
            "ELEMENT_NAME": "71001.GE1.BFLRNYZV1CW.BFLRNYZV3QW",
            "CIRC_PATH_INST_ID": "125632",
            "ELEMENT_REFERENCE": "125632",
        }
    )

    data = [{"BANDWIDTH": "AGGREGATE", "AVAILABLE_BW": "600"}]
    data1 = [{"BANDWIDTH": "AGGREGATE", "AVAILABLE_BW": "600"}, {"BANDWIDTH": "1 Gbps", "AVAILABLE_BW": "600"}]
    data2 = [{"BANDWIDTH": "10 Gbps", "AVAILABLE_BW": "600"}, {"BANDWIDTH": "1 Gbps", "AVAILABLE_BW": "600"}]

    iter_data = iter([data, data1, data2])
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: next(iter_data))

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000) is None

    # bad test abort no data dict
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: {})

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000) is None

    # testing element name ending in QW or CW
    transport_paths = [
        {
            "ELEMENT_NAME": "71001.GE1.BFLRNYZV1CW.BFLRNYZV3QW",
            "CIRC_PATH_INST_ID": "125689",
            "ELEMENT_REFERENCE": "125689",
        },
        {
            "ELEMENT_NAME": "71001.GE1.BFLRNYZV1QW.BFLRNYZV3ZW",
            "CIRC_PATH_INST_ID": "125690",
            "ELEMENT_REFERENCE": "125690",
        },
    ]
    data1 = [{"BANDWIDTH": "1 Gbps", "AVAILABLE_BW": "600", "OVERSUBSCRIPTION": "10"}]

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: data1)
    monkeypatch.setattr(nbu, "_validate_payload", lambda *args, **kwargs: (600, "Mbps", 600))

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000) is None

    # testing no transport path data
    with raises(AbortException):
        assert nbu._check_transport_paths([], 2000) is None

    # ctbh all good
    channel_availability_resp = [{"MEMBER_PATH": 1}, {"MEMBER_PATH": 1}]
    data3 = iter([data1, channel_availability_resp])

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: next(data3))
    monkeypatch.setattr(nbu, "_calculate_oversubscription", lambda *args, **kwargs: "1")
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: None)

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000, True) is None

    # VLAN channel CIDs do not match
    channel_availability_resp = [{"MEMBER_PATH": 1}, {"MEMBER_PATH": 2}]
    data3 = iter([data1, channel_availability_resp])

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: next(data3))

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000, True) is None

    # More than 2 VLAN channels
    channel_availability_resp = [{"MEMBER_PATH": 1}, {"MEMBER_PATH": 2}, {"MEMBER_PATH": 3}]
    data3 = iter([data1, channel_availability_resp])

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: next(data3))

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000, True) is None

    # Less than 2 VLAN channels
    channel_availability_resp = [{"MEMBER_PATH": 1}]
    data3 = iter([data1, channel_availability_resp])

    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: next(data3))

    with raises(AbortException):
        assert nbu._check_transport_paths(transport_paths, 2000, True) is None


@pytest.mark.unittest
def test_sforce_granite_compare():
    # usable_ip failure
    body = {"usable_ip_addresses_requested": "/30"}
    all_paths = [{"IPV4_ASSIGNED_SUBNETS": "127.0.0.1/28"}]

    with raises(AbortException):
        assert nbu.sforce_granite_compare(all_paths, body) is None

    # service type failure
    body["usable_ip_addresses_requested"] = "/28"
    body["primary_fia_service_type"] = "BAD_SERVICE_TYPE"
    all_paths[0]["IPV4_SERVICE_TYPE"] = "SERVICE_TYPE"

    with raises(AbortException):
        assert nbu.sforce_granite_compare(all_paths, body) is None

    # ip address failure
    body["primary_fia_service_type"] = "SERVICE_TYPE"
    body["ip_address"] = "127.0.0.2/29"

    with raises(AbortException):
        assert nbu.sforce_granite_compare(all_paths, body) is None

    # all comparisons good
    body["ip_address"] = "127.0.0.1/28"
    assert nbu.sforce_granite_compare(all_paths, body) is None


@pytest.mark.unittest
def test_remove_ip_bad_stuff():
    assert nbu.remove_ip_bad_stuff("ip: 127.0.0.1/20") == "127.0.0.1/20"


@pytest.mark.unittest
def test_enni_oversub_check(monkeypatch):
    # all good
    body = {"bw_speed": "500", "bw_unit": "Gbps", "product_name": "Carrier CTBH"}
    carrier_resp = [
        {"ELEMENT_TYPE": "PATH", "ELEMENT_NAME": "CHTR", "ELEMENT_REFERENCE": "ELEMENT_REFERENCE"},
        {"ELEMENT_TYPE": "PATH", "ELEMENT_NAME": "xx.xx.AW.AW", "ELEMENT_REFERENCE": "ELEMENT_REFERENCE"},
        {"ELEMENT_TYPE": "PORT", "ELEMENT_NAME": "AW", "ELEMENT_REFERENCE": "ELEMENT_REFERENCE", "PORT_ROLE": "ENNI"},
    ]
    monkeypatch.setattr(nbu, "_calculate_oversubscription", lambda *args, **kwargs: "1")
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: None)

    assert nbu.enni_oversub_check(carrier_resp, "pathid", body) == carrier_resp[:2]

    # more than 2
    carrier_resp.append(carrier_resp[0])

    with raises(AbortException):
        assert nbu.enni_oversub_check(carrier_resp, "pathid", body) is None

    # less than 2
    with raises(AbortException):
        assert nbu.enni_oversub_check([], "pathid", body) is None


@pytest.mark.unittest
def test_carrier_transport_paths(monkeypatch):
    # all good
    all_paths = [{"ELEMENT_NAME": "ELEMENT_NAME"}]

    monkeypatch.setattr(nbu, "_retrieve_transport_paths", lambda *args, **kwargs: ("transport_paths", all_paths))

    assert nbu.carrier_transport_paths(pathid) == ("transport_paths", all_paths)

    # AW-DSW0 found
    all_paths = [{"ELEMENT_NAME": "AW-DSW0"}]

    with raises(AbortException):
        assert nbu.carrier_transport_paths(pathid, ctbh=True) is None


@pytest.mark.unittest
def test_check_transport_paths_ctbh(monkeypatch):
    # all good
    transport_paths = [{"ELEMENT_NAME": "ELEMENT_NAME71W"}]
    enni_list = [{"ELEMENT_NAME": "ELEMENT_NAME"}, {"ELEMENT_NAME": "ELEMENT_NAME"}]

    monkeypatch.setattr(nbu, "_check_transport_paths", lambda *args, **kwargs: None)

    assert nbu.check_transport_paths_ctbh(transport_paths, enni_list, "mbps_delta_bw_val", "pathid") is None

    # No CPE transport found
    enni_list = [{"ELEMENT_NAME": "ELEMENT_NAME71W"}, {"ELEMENT_NAME": "ELEMENT_NAME"}]

    with raises(AbortException):
        assert nbu.check_transport_paths_ctbh(transport_paths, enni_list, "mbps_delta_bw_val", "pathid") is None


@pytest.mark.unittest
def test_ctbh_cpe_check(monkeypatch):
    # Cisco
    current_port = {"VENDOR": "CISCO", "MODEL": "3400", "TID": "", "ELEMENT_NAME": "TID/99.99.SWT"}

    with raises(AbortException):
        assert nbu.ctbh_cpe_check(current_port, 501, "all_paths") is None

    # Alcatel
    current_port = {"VENDOR": "ALCATEL", "MODEL": "7705", "TID": "", "ELEMENT_NAME": "TID/99.99.SWT"}

    with raises(AbortException):
        assert nbu.ctbh_cpe_check(current_port, 500, "all_paths") is None

    # All good
    all_paths = [{"ELEMENT_TYPE": "PATH", "ELEMENT_NAME": "TID", "ELEMENT_BANDWIDTH": "1 Gbps"}]
    current_port = {"VENDOR": "CISCO", "MODEL": "7705", "TID": "TID", "ELEMENT_NAME": "TID/99.99.SWT"}

    assert nbu.ctbh_cpe_check(current_port, 500, all_paths) == 1000

    # OTHER
    all_paths[0]["ELEMENT_BANDWIDTH"] = "10 Gbps"
    assert nbu.ctbh_cpe_check(current_port, 500, all_paths) == 10000


@pytest.mark.unittest
def test_upgrade_bw_compare():
    # all good
    assert nbu.upgrade_bw_compare(500, 100, 500, 100) == 400

    # No change required
    with raises(Exception):
        assert nbu.upgrade_bw_compare(500, 500, 500, 100) is None

    # bandwidth less than current bandwidth
    with raises(Exception):
        assert nbu.upgrade_bw_compare(100, 500, 500, 100) is None


@pytest.mark.unittest
def test_trans_path_upgrade(monkeypatch):
    cpe_upgrade_needed = {"Z_SIDE_SITE": "Z_SIDE_SITE"}
    trans_data = {"pathInstanceId": "12345", "pathId": "pathId"}
    uplink_port = {"ELEMENT_NAME": "ELEMENT_NAME", "LEG_INST_ID": "LEG_INST_ID"}

    monkeypatch.setattr(nbu, "create_transport_revision", lambda *args, **kwargs: trans_data)
    monkeypatch.setattr(nbu, "granite_port_info", lambda *args, **kwargs: uplink_port)
    monkeypatch.setattr(nbu, "port_check_10G", lambda *args, **kwargs: "ten_gig_port")

    monkeypatch.setattr(nbu, "remove_uplink", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "add_uplink_port", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "get_next_zw_shelf", lambda *args, **kwargs: "new_shelf")

    monkeypatch.setattr(nbu, "update_transport_bw", lambda *args, **kwargs: "resp_data")

    assert nbu.trans_path_upgrade("trans_name", "trans_id", cpe_upgrade_needed, False) == (
        trans_data,
        "new_shelf",
        "resp_data",
    )

    monkeypatch.setattr(nbu, "card_swap", lambda *args, **kwargs: "10_gig_port")
    assert nbu.trans_path_upgrade("trans_name", "trans_id", cpe_upgrade_needed, True) == (
        trans_data,
        "new_shelf",
        "resp_data",
    )


@pytest.mark.unittest
def test_device_check(monkeypatch):
    # bad vendor
    monkeypatch.setattr(nbu, "get_cpe_info", lambda *args, **kwargs: ("tid", "bad vendor", "model"))

    with raises(AbortException):
        assert nbu.device_check(pathid, "mbps_main_bw_val", "mbps_req_bw_val", "FIA") is None

    # Unable to login into the device
    monkeypatch.setattr(nbu, "get_cpe_info", lambda *args, **kwargs: ("tid", "ADVA", "model"))
    monkeypatch.setattr(nbu, "get_active_device", lambda *args, **kwargs: AbortException)

    with raises(AbortException):
        assert nbu.device_check(pathid, "mbps_main_bw_val", "mbps_req_bw_val", "FIA") is None

    # check_network_data
    monkeypatch.setattr(nbu, "get_active_device", lambda *args, **kwargs: (None, None))

    monkeypatch.setattr(nbu, "get_zsite", lambda *args, **kwargs: "z_site_info")
    monkeypatch.setattr(nbu, "get_cpe_transport_paths", lambda *args, **kwargs: "shelf_dict")
    monkeypatch.setattr(nbu, "get_cpe_services", lambda *args, **kwargs: ("shelf_info", "cids"))

    monkeypatch.setattr(nbu, "cpe_service_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "_cross_duplex_bw_threshold", lambda *args, **kwargs: "check_network_data")
    monkeypatch.setattr(nbu, "_check_handoff_port_duplex_settings", lambda *args, **kwargs: "mw_needed")

    assert (
        nbu.device_check(pathid, "mbps_main_bw_val", "mbps_req_bw_val", "FIA")
        == "Customer coordination is required for Port Speed/Duplex change on handoff."
    )

    # NOT check_network_data
    monkeypatch.setattr(nbu, "_check_handoff_port_duplex_settings", lambda *args, **kwargs: None)
    assert nbu.device_check(pathid, "mbps_main_bw_val", "mbps_req_bw_val", "FIA") is None


@pytest.mark.unittest
def test_evc_assoc_check(monkeypatch):
    all_paths = [{"EVC_ID": "123456"}]

    # Missing association in granite
    monkeypatch.setattr(nbu, "get_path_association", lambda *args, **kwargs: {"retString": "retString"})

    with raises(AbortException):
        assert nbu.evc_assoc_check("main_inst", "rev_instance", "pathid", "prod_name", all_paths) is None

    # evcid greater than 6 digits abort
    all_paths = [{"EVC_ID": "1234567"}]
    assert nbu.evc_assoc_check("main_inst", "rev_instance", "pathid", "prod_name", all_paths) is None

    # Unable to add path association
    association = [
        {
            "associationValue": "associationValue",
            "associationName": "associationName",
            "numberRangeName": "numberRangeName",
        }
    ]

    monkeypatch.setattr(nbu, "get_path_association", lambda *args, **kwargs: association)
    monkeypatch.setattr(nbu, "assign_association", lambda *args, **kwargs: None)

    with raises(Exception):
        assert nbu.evc_assoc_check("main_inst", "rev_instance", "pathid", "prod_name", all_paths) is None

    # EP-LAN (Fiber)"
    monkeypatch.setattr(nbu, "assign_association", lambda *args, **kwargs: "assoc_result")
    monkeypatch.setattr(nbu, "add_vrfid_link", lambda *args, **kwargs: None)

    assert nbu.evc_assoc_check("main_inst", "rev_instance", "pathid", "EP-LAN (Fiber)", all_paths) is None


@pytest.mark.unittest
def test_cpe_10g_swap(monkeypatch):
    cpe_upgrade_needed = {"TID": "TID", "VENDOR": "VENDOR"}
    trans_data = {"pathInstanceId": "pathInstanceId", "pathId": "pathId"}
    resp_data = {"pathId": "pathId"}

    monkeypatch.setattr(nbu, "new_cpe", lambda *args, **kwargs: "cpe_swap")
    monkeypatch.setattr(nbu, "cpe_swap_main", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "multiple_paths_check", lambda *args, **kwargs: None)

    assert nbu.cpe_10g_swap("rev_instance", cpe_upgrade_needed, trans_data, resp_data, "pathid") == (EC_MSG, True)


@pytest.mark.unittest
def test_edna_check_ctbh(monkeypatch):
    # _is_relevant_router True and _edna_check False
    all_paths = [{"PATH_NAME": "21.L1XX.006991..TWCC"}]
    cid_info = [
        {"LVL": "1", "ELEMENT_NAME": "hub_device", "PORT_ROLE": "ENNI", "DEVICE_INFO_NETWORK": "not_edna", "TID": "tid"},
        {"LVL": "1", "ELEMENT_NAME": "hub_device", "PORT_ROLE": "ENNI", "DEVICE_INFO_NETWORK": "EDNA", "TID": "tid"},
    ]

    monkeypatch.setattr(nbu, "get_path_elements", lambda *args, **kwargs: cid_info)
    monkeypatch.setattr(nbu, "_is_relevant_router", lambda *args, **kwargs: True)
    monkeypatch.setattr(nbu, "_edna_check", lambda *args, **kwargs: True)

    with raises(Exception):
        assert nbu.edna_check_ctbh(5000, all_paths) is None

    # _is_relevant_router False and port_role == "ENNI"
    monkeypatch.setattr(nbu, "_is_relevant_router", lambda *args, **kwargs: False)

    with raises(Exception):
        assert nbu.edna_check_ctbh(5000, all_paths) is None


@pytest.mark.unittest
def test_hub_transport_check(monkeypatch):
    # return False - no hub transport
    assert nbu.hub_transport_check("1234", "trans_name.ZW") is False

    # abort - MTU hub transport
    with raises(Exception):
        nbu.hub_transport_check("1234", "trans_nameQW.AW")

    # abort - len(channel_availability_resp) != 1
    monkeypatch.setattr(
        nbu, "get_granite", lambda *args, **kwargs: [{"CHAN_NAME": "VLAN1100"}, {"CHAN_NAME": "VLAN1300"}]
    )
    with raises(Exception):
        nbu.hub_transport_check("1234", "trans_nameQW.ZW")

    # abort - get_path_elements_inst_l1 response is not a list
    monkeypatch.setattr(nbu, "get_granite", lambda *args, **kwargs: [{"CHAN_NAME": "VLAN1100"}])
    monkeypatch.setattr(nbu, "get_path_elements_inst_l1", lambda *args, **kwargs: {})
    with raises(Exception):
        nbu.hub_transport_check("1234", "trans_nameQW.ZW")

    # abort - wavelength in ("1430", "1450", "1430.00", "1450.00")
    monkeypatch.setattr(nbu, "get_path_elements_inst_l1", lambda *args, **kwargs: [{"PORT_ACCESS_ID": "GE-0/0/15"}])
    monkeypatch.setattr(
        nbu,
        "get_optic_info",
        lambda *args, **kwargs: {"wavelength": "1430", "vendor": "CHAMPION", "receive_power": "-22"},
    )
    with raises(Exception):
        nbu.hub_transport_check("1234", "trans_nameQW.ZW")

    # abort - "CHAMPION" in vendor_name.upper()
    monkeypatch.setattr(
        nbu,
        "get_optic_info",
        lambda *args, **kwargs: {"wavelength": "1470", "vendor": "CHAMPION", "receive_power": "-22"},
    )
    with raises(Exception):
        nbu.hub_transport_check("1234", "trans_nameQW.ZW")

    # abort - receive_power <= -21
    monkeypatch.setattr(
        nbu,
        "get_optic_info",
        lambda *args, **kwargs: {"wavelength": "1470", "vendor": "PROLAPS", "receive_power": "-22"},
    )
    with raises(Exception):
        nbu.hub_transport_check("1234", "trans_nameQW.ZW")

    # good test
    monkeypatch.setattr(
        nbu,
        "get_optic_info",
        lambda *args, **kwargs: {"wavelength": "1470", "vendor": "PROLAPS", "receive_power": "-19"},
    )
    assert nbu.hub_transport_check("1234", "trans_nameQW.ZW") is True


@pytest.mark.unittest
def test_card_swap(monkeypatch):
    uplink_port = {"ELEMENT_NAME": "TESTQWSWT#0", "PORT_ACCESS_ID": "GE-0/0/15", "SLOT": "15"}

    # abort - len(resp) != 1
    monkeypatch.setattr(
        nbu,
        "get_equipment_buildout_slot",
        lambda *args, **kwargs: [{"EQUIP_NAME": "TESTQWSWT#0"}, {"EQUIP_NAME": "TESTQWSWT#1"}],
    )
    with raises(Exception):
        nbu.card_swap(uplink_port)

    # good test
    port = {"EQUIP_NAME": "TESTQWSWT#0", "SLOT_INST_ID": "1234", "PORT_INST_ID": "5678"}
    monkeypatch.setattr(nbu, "get_equipment_buildout_slot", lambda *args, **kwargs: [port])
    monkeypatch.setattr(nbu, "delete_granite", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "insert_card_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(nbu, "put_granite", lambda *args, **kwargs: None)
    assert nbu.card_swap(uplink_port) == port
