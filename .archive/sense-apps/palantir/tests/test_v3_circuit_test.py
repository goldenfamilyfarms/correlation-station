import json
import logging

import pytest

from palantir_app.bll import circuit_test_v3

logger = logging.getLogger(__name__)


class DataResp:
    def __init__(self, status_code=200, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        try:
            with open(self.file_name) as f:
                data = json.load(f)
        except TypeError:
            data = self.file_name
        return data


@pytest.mark.unittest
def test_model_circuit_test(monkeypatch):
    pass


def mock_device_inventory_call():
    records = DataResp(file_name="tests/mock_data/circuit_testing/device_inventory_call_records.json")
    return records.json()


@pytest.mark.unittest
def test_filter_records_by_status_live():
    records = mock_device_inventory_call()
    records[0]["status"] = "Live"
    records[1]["status"] = "Live"
    test_filtered = circuit_test_v3._filter_records_by_status(records)
    assert test_filtered == records
    assert test_filtered[0]["status"] == "Live"


@pytest.mark.unittest
def test_filter_records_by_status_designed():
    records = mock_device_inventory_call()
    test_filtered = circuit_test_v3._filter_records_by_status(records)
    assert test_filtered == records
    assert test_filtered[0]["status"] == "Designed"


@pytest.mark.unittest
def test_filter_records_by_status_live_and_designed():
    # in this case only live status should be returned, designed discared
    records = mock_device_inventory_call()
    records[0]["status"] = "Live"
    test_filtered = circuit_test_v3._filter_records_by_status(records)
    logger.debug(f"{records = }\n")
    logger.debug(f"{test_filtered = }")
    records_statuses = [record["status"] for record in records]
    assert "Live" in records_statuses and "Designed" in records_statuses
    filtered_statuses = [filtered["status"] for filtered in test_filtered]
    assert "Live" in filtered_statuses and "Designed" not in filtered_statuses


@pytest.mark.unittest
def test_filter_records_by_status_no_live_or_designed():
    records = mock_device_inventory_call()
    records[0]["status"] = "Invalid Status"
    records[1]["status"] = "Invalid Status"
    test_filtered = circuit_test_v3._filter_records_by_status(records)
    assert test_filtered == []


def mock_devices():
    records = mock_device_inventory_call()
    devices = records[0]["data"]
    return devices


def get_mock_a_side_devices():
    return [
        {
            "sequence": "0001.0000.0001.0001",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX240",
            "path_name": "51.KGFD.000154..CHTR",
            "path_inst_id": 2487216,
            "topology": "Point to Point",
            "tid": "AUSDTXIR6CW",
            "port_access_id": "ET-2/3/2",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "CAR-CTBH NNI",
            "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
            "leg_name": "1",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.82/32",
            "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0002.0000.0000.0000",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX240",
            "path_name": "51.L4XX.000246..CHTR",
            "path_inst_id": 2487178,
            "topology": "Point to Point",
            "tid": "AUSDTXIR6CW",
            "port_access_id": "ET-2/3/2",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "CAR-CTBH 4G",
            "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
            "leg_name": "3011/PRIMARY",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": "3011",
            "cevlan": None,
            "custsvlan": "3011",
            "chan_name": None,
            "management_ip": "71.42.150.82/32",
            "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
            "split_id": None,
        },
    ]


@pytest.mark.unittest
def test_get_single_side_devices_a():
    devices = mock_devices()
    a_side_devices = circuit_test_v3._get_single_side_devices(devices)
    assert a_side_devices == get_mock_a_side_devices()


def get_mock_z_side_devices():
    return [
        {
            "sequence": "0007.0000.0000.0000",
            "site_type": "CELL",
            "vendor": "CIENA",
            "eq_type": "SWITCH",
            "model": "CIENA 3931",
            "path_name": "51.L4XX.000246..CHTR",
            "path_inst_id": 2487178,
            "topology": "Point to Point",
            "tid": "AUSDTXZR72W",
            "port_access_id": "10",
            "vlan_operation": "PUSH",
            "device_role": "2",
            "path_type": "CAR-CTBH 4G",
            "owned_edge_point": "AUSDTXZR72W-10",
            "leg_name": "3011/PRIMARY",
            "full_address": "11921 N MO PAC EXPY",
            "svlan": "3011",
            "cevlan": "3011",
            "custsvlan": None,
            "chan_name": None,
            "management_ip": "DHCP",
            "device_id": "AUSDTXZR72W.CML.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0006.0000.0001.0001",
            "site_type": "CELL",
            "vendor": "CIENA",
            "eq_type": "SWITCH",
            "model": "CIENA 3931",
            "path_name": "51001.GE10.AUSDTXIR72W.AUSDTXIR72W",
            "path_inst_id": 2487183,
            "topology": "Point to Point",
            "tid": "AUSDTXZR72W",
            "port_access_id": "10",
            "vlan_operation": None,
            "device_role": "2",
            "path_type": "INT-CUSTOMER HANDOFF",
            "owned_edge_point": "AUSDTXZR72W-10",
            "leg_name": "1",
            "full_address": "11921 N MO PAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "DHCP",
            "device_id": "AUSDTXZR72W.CML.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0005.0000.0002.0002",
            "site_type": "CELL",
            "vendor": "CIENA",
            "eq_type": "SWITCH",
            "model": "CIENA 3931",
            "path_name": "51001.GE10.AUSDTXIR2QW.AUSDTXZR72W",
            "path_inst_id": 2487182,
            "topology": "Point to Point",
            "tid": "AUSDTXZR72W",
            "port_access_id": "9",
            "vlan_operation": None,
            "device_role": "2",
            "path_type": "INT-ACCESS TO PREM TRANSPORT",
            "owned_edge_point": "AUSDTXZR72W-9",
            "leg_name": "1",
            "full_address": "11921 N MO PAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "DHCP",
            "device_id": "AUSDTXZR72W.CML.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0005.0000.0001.0001",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "SWITCH",
            "model": "QFX5100-96S",
            "path_name": "51001.GE10.AUSDTXIR2QW.AUSDTXZR72W",
            "path_inst_id": 2487182,
            "topology": "Point to Point",
            "tid": "AUSDTXIR2QW",
            "port_access_id": "GE-1/0/45",
            "vlan_operation": None,
            "device_role": "Q",
            "path_type": "INT-ACCESS TO PREM TRANSPORT",
            "owned_edge_point": "AUSDTXIR2QW-GE-1/0/45",
            "leg_name": "1",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.235/29",
            "device_id": "AUSDTXIR2QW.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0004.0000.0002.0002",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "SWITCH",
            "model": "QFX5100-96S",
            "path_name": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW",
            "path_inst_id": 1204498,
            "topology": "Point to Point",
            "tid": "AUSDTXIR2QW",
            "port_access_id": "ET-1/0/99",
            "vlan_operation": None,
            "device_role": "Q",
            "path_type": "INT-EDGE TRANSPORT",
            "owned_edge_point": "AUSDTXIR2QW-ET-1/0/99",
            "leg_name": "AE0/AE0 80G",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.235/29",
            "device_id": "AUSDTXIR2QW.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0004.0000.0002.0001",
            "site_type": "LOCAL",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX480",
            "path_name": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW",
            "path_inst_id": 1204498,
            "topology": "Point to Point",
            "tid": "AUSDTXIR2CW",
            "port_access_id": "ET-2/2/1",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "INT-EDGE TRANSPORT",
            "owned_edge_point": "AUSDTXIR2CW-ET-2/2/1",
            "leg_name": "AE0/AE0 80G",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.66/32",
            "device_id": "AUSDTXIR2CW.DEV.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0004.0000.0001.0002",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "SWITCH",
            "model": "QFX5100-96S",
            "path_name": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW",
            "path_inst_id": 1204498,
            "topology": "Point to Point",
            "tid": "AUSDTXIR2QW",
            "port_access_id": "ET-0/0/99",
            "vlan_operation": None,
            "device_role": "Q",
            "path_type": "INT-EDGE TRANSPORT",
            "owned_edge_point": "AUSDTXIR2QW-ET-0/0/99",
            "leg_name": "AE0/AE0 80G",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.235/29",
            "device_id": "AUSDTXIR2QW.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0004.0000.0001.0001",
            "site_type": "LOCAL",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX480",
            "path_name": "51001.GE40L.AUSDTXIR2CW.AUSDTXIR2QW",
            "path_inst_id": 1204498,
            "topology": "Point to Point",
            "tid": "AUSDTXIR2CW",
            "port_access_id": "ET-2/2/0",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "INT-EDGE TRANSPORT",
            "owned_edge_point": "AUSDTXIR2CW-ET-2/2/0",
            "leg_name": "AE0/AE0 80G",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.66/32",
            "device_id": "AUSDTXIR2CW.DEV.CHTRSE.COM",
            "split_id": None,
        },
    ]


@pytest.mark.unittest
def test_get_single_side_devices_z():
    devices = mock_devices()
    reversed_devices = list(reversed(devices))
    z_side_devices = circuit_test_v3._get_single_side_devices(reversed_devices)
    assert z_side_devices == get_mock_z_side_devices()


def get_single_side_devices(devices):
    one_side_only = []
    for device in devices:
        if not device["split_id"]:
            one_side_only.append(device)
        if device["split_id"]:
            break
    return one_side_only


@pytest.mark.unittest
def test_single_side_devices_one_sided_circuit():
    devices = mock_devices()
    one_sided_devices = get_single_side_devices(devices)
    assert one_sided_devices == [
        {
            "sequence": "0001.0000.0001.0001",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX240",
            "path_name": "51.KGFD.000154..CHTR",
            "path_inst_id": 2487216,
            "topology": "Point to Point",
            "tid": "AUSDTXIR6CW",
            "port_access_id": "ET-2/3/2",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "CAR-CTBH NNI",
            "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
            "leg_name": "1",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.82/32",
            "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
            "split_id": None,
        },
        {
            "sequence": "0002.0000.0000.0000",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX240",
            "path_name": "51.L4XX.000246..CHTR",
            "path_inst_id": 2487178,
            "topology": "Point to Point",
            "tid": "AUSDTXIR6CW",
            "port_access_id": "ET-2/3/2",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "CAR-CTBH 4G",
            "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
            "leg_name": "3011/PRIMARY",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": "3011",
            "cevlan": None,
            "custsvlan": "3011",
            "chan_name": None,
            "management_ip": "71.42.150.82/32",
            "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
            "split_id": None,
        },
    ]


def mock_circuit_devices():
    records = DataResp(file_name="tests/mock_data/circuit_testing/circuit_devices.json")
    return records.json()


def get_mock_cpe():
    return {
        "sequence": "0001.0000.0001.0001",
        "site_type": "HUB",
        "vendor": "JUNIPER",
        "eq_type": "ROUTER",
        "model": "MX240",
        "path_name": "51.KGFD.000154..CHTR",
        "path_inst_id": 2487216,
        "topology": "Point to Point",
        "tid": "AUSDTXIR6CW",
        "port_access_id": "ET-2/3/2",
        "vlan_operation": None,
        "device_role": "C",
        "path_type": "CAR-CTBH NNI",
        "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
        "leg_name": "1",
        "full_address": "11921 N MOPAC EXPY",
        "svlan": None,
        "cevlan": None,
        "custsvlan": None,
        "chan_name": "VLAN3011",
        "management_ip": "71.42.150.82/32",
        "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
        "split_id": None,
        "status": "Designed",
    }


@pytest.mark.unittest
def test_get_cpe_device():
    devices = mock_devices()
    a_side_devices = get_single_side_devices(devices)
    circuit_devices = mock_circuit_devices()
    a_side_cpe = circuit_test_v3._get_cpe_device(a_side_devices, circuit_devices)
    assert a_side_cpe == get_mock_cpe()


@pytest.mark.unittest
def test_get_cpe_device_no_cpe():
    a_side_devices = [{}]
    circuit_devices = mock_circuit_devices()
    cpe = circuit_test_v3._get_cpe_device(a_side_devices, circuit_devices)
    assert cpe == {}


@pytest.mark.unittest
def test_add_status():
    devices = mock_devices()
    device = get_single_side_devices(devices)[0]
    # no status available in initial data
    assert device.get("status") is None
    logger.debug(f"{device}")
    circuit_devices = mock_circuit_devices()
    device_with_status = circuit_test_v3._add_status(device, circuit_devices)
    # status has been added from supplemental circuit devices data
    assert device_with_status.get("status") == "Designed"


@pytest.mark.unittest
def test_add_status_no_inst_id_match():
    devices = mock_devices()
    device = get_single_side_devices(devices)[0]
    device["path_inst_id"] = "mismatch"
    # no status available in initial data
    assert device.get("status") is None
    circuit_devices = mock_circuit_devices()
    device_status_no_match_found = circuit_test_v3._add_status(device, circuit_devices)
    assert device_status_no_match_found["status"] is None


@pytest.mark.unittest
def test_get_pe_device():
    devices = mock_devices()
    a_side_devices = get_single_side_devices(devices)
    circuit_devices = mock_circuit_devices()
    a_side_pe = circuit_test_v3._get_pe_device(a_side_devices, circuit_devices)
    assert a_side_pe == {
        "sequence": "0001.0000.0001.0001",
        "site_type": "HUB",
        "vendor": "JUNIPER",
        "eq_type": "ROUTER",
        "model": "MX240",
        "path_name": "51.KGFD.000154..CHTR",
        "path_inst_id": 2487216,
        "topology": "Point to Point",
        "tid": "AUSDTXIR6CW",
        "port_access_id": "ET-2/3/2",
        "vlan_operation": None,
        "device_role": "C",
        "path_type": "CAR-CTBH NNI",
        "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
        "leg_name": "1",
        "full_address": "11921 N MOPAC EXPY",
        "svlan": None,
        "cevlan": None,
        "custsvlan": None,
        "chan_name": "VLAN3011",
        "management_ip": "71.42.150.82/32",
        "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
        "split_id": None,
        "status": "Designed",
    }


@pytest.mark.unittest
def test_get_pe_device_no_pe():
    a_side_devices = [{}]
    circuit_devices = mock_circuit_devices()
    pe = circuit_test_v3._get_cpe_device(a_side_devices, circuit_devices)
    assert pe == {}


def get_mock_pe():
    return {
        "sequence": "0001.0000.0001.0001",
        "site_type": "HUB",
        "vendor": "JUNIPER",
        "eq_type": "ROUTER",
        "model": "MX240",
        "path_name": "51.KGFD.000154..CHTR",
        "path_inst_id": 2487216,
        "topology": "Point to Point",
        "tid": "AUSDTXIR6CW",
        "port_access_id": "ET-2/3/2",
        "vlan_operation": None,
        "device_role": "C",
        "path_type": "CAR-CTBH NNI",
        "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
        "leg_name": "1",
        "full_address": "11921 N MOPAC EXPY",
        "svlan": None,
        "cevlan": None,
        "custsvlan": None,
        "chan_name": "VLAN3011",
        "management_ip": "71.42.150.82/32",
        "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
        "split_id": None,
        "status": "Designed",
    }


def mock_get_vta_from_pe(*args, **kwargs):
    records = DataResp(file_name="tests/mock_data/circuit_testing/vta_from_pe.json")
    return records.json()


@pytest.mark.unittest
def test_get_feasible_nfx_details(monkeypatch):
    pe = get_mock_pe()
    monkeypatch.setattr(circuit_test_v3, "_get_vta_from_pe", mock_get_vta_from_pe)
    feasible_nfx = circuit_test_v3._get_feasible_nfx_details(pe)
    assert feasible_nfx == [
        {
            "test_fqdn": "CHCGILDTS6W.CHTRSE.COM",
            "test_circ_inst": 2175025,
            "test_equip_model": "NFX250-S1",
            "test_equip_status": "Live",
            "test_tid": "CHCGILDTS6W",
            "test_equip_vendor": "JUNIPER",
            "test_circ_status": "Live",
        },
        {
            "test_fqdn": "CHCGILDTS6W.CHTRSE.COM",
            "test_circ_inst": 2175027,
            "test_equip_model": "NFX250-S1",
            "test_equip_status": "Live",
            "test_tid": "CHCGILDTS6W",
            "test_equip_vendor": "JUNIPER",
            "test_circ_status": "Live",
        },
    ]


def mock_get_vta_from_pe_none_found(*args, **kwargs):
    return []


@pytest.mark.unittest
def test_get_feasible_nfx_details_none_found(monkeypatch):
    pe = get_mock_pe()
    monkeypatch.setattr(circuit_test_v3, "_get_vta_from_pe", mock_get_vta_from_pe_none_found)
    feasible_nfx = circuit_test_v3._get_feasible_nfx_details(pe)
    assert feasible_nfx == []


def mock_get_vta_from_pe_none_feasible(*args, **kwargs):
    records = DataResp(file_name="tests/mock_data/circuit_testing/vta_from_pe.json").json()
    for record in records:
        record["test_circ_status"] = "Designed"
    return records


@pytest.mark.unittest
def test_get_feasible_nfx_details_none_feasible(monkeypatch):
    pe = get_mock_pe()
    monkeypatch.setattr(circuit_test_v3, "_get_vta_from_pe", mock_get_vta_from_pe_none_feasible)
    feasible_nfx = circuit_test_v3._get_feasible_nfx_details(pe)
    assert feasible_nfx == []


PE_TID = "AUSDTXIR6CW"


@pytest.mark.unittest
def test_is_feasible_vta_available_no_live_circuit():
    vta_data = mock_get_vta_from_pe_none_feasible()[0]
    is_feasible = circuit_test_v3._is_feasible_nfx_available(vta_data, PE_TID)
    assert is_feasible is False


@pytest.mark.unittest
def test_is_feasible_vta_availalable_no_live_equip():
    vta_data = mock_get_vta_from_pe()[0]
    vta_data["test_equip_status"] = "Designed"
    is_feasible = circuit_test_v3._is_feasible_nfx_available(vta_data, PE_TID)
    assert is_feasible is False


@pytest.mark.unittest
def test_is_feasible_vta_available_no_fqdn():
    vta_data = mock_get_vta_from_pe()[0]
    vta_data["test_fqdn"] = None
    is_feasible = circuit_test_v3._is_feasible_nfx_available(vta_data, PE_TID)
    assert is_feasible is False


@pytest.mark.unittest
def test_is_feasible_vta_available_all_requirements_met():
    vta_data = mock_get_vta_from_pe()[0]
    is_feasible = circuit_test_v3._is_feasible_nfx_available(vta_data, PE_TID)
    assert is_feasible is True


def get_mock_feasible_nfx():
    return [
        {
            "test_fqdn": "CHCGILDTS6W.CHTRSE.COM",
            "test_circ_inst": 2175025,
            "test_equip_model": "NFX250-S1",
            "test_equip_status": "Live",
            "test_tid": "CHCGILDTS6W",
            "test_equip_vendor": "JUNIPER",
            "test_circ_status": "Live",
        },
        {
            "test_fqdn": "CHCGILDTS6W.CHTRSE.COM",
            "test_circ_inst": 2175027,
            "test_equip_model": "NFX250-S1",
            "test_equip_status": "Live",
            "test_tid": "CHCGILDTS6W",
            "test_equip_vendor": "JUNIPER",
            "test_circ_status": "Live",
        },
    ]


def mock_spirent_test_port(*args, **kwargs):
    records = DataResp(file_name="tests/mock_data/circuit_testing/spirent_test_port.json")
    return records.json()


def get_mock_vta_details():
    return {"port_access_id": "GE-1/0/0", "wbox_port_access_id": "GE-1/0/0"}


@pytest.mark.unittest
def test_get_base_spirent_vta_details(monkeypatch):
    pe = get_mock_pe()
    feasible_nfx = get_mock_feasible_nfx()
    monkeypatch.setattr(circuit_test_v3, "_get_spirent_port", mock_spirent_test_port)
    vta_details = circuit_test_v3._get_base_spirent_vta_details(pe, feasible_nfx)
    assert vta_details == get_mock_vta_details()


def mock_spirent_test_port_none_found(*args, **kwargs):
    return []


@pytest.mark.unittest
def test_get_base_spirent_vta_details_no_port_found(monkeypatch):
    pe = get_mock_pe()
    feasible_nfx = get_mock_feasible_nfx()
    monkeypatch.setattr(circuit_test_v3, "_get_spirent_port", mock_spirent_test_port_none_found)
    vta_details = circuit_test_v3._get_base_spirent_vta_details(pe, feasible_nfx)
    assert vta_details == {}


def get_combined_side_data():
    return {
        "pe": {
            "sequence": "0001.0000.0001.0001",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX240",
            "path_name": "51.KGFD.000154..CHTR",
            "path_inst_id": 2487216,
            "topology": "Point to Point",
            "tid": "AUSDTXIR6CW",
            "port_access_id": "ET-2/3/2",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "CAR-CTBH NNI",
            "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
            "leg_name": "1",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.82/32",
            "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
            "split_id": None,
            "status": "Designed",
        },
        "cpe": {
            "sequence": "0001.0000.0001.0001",
            "site_type": "HUB",
            "vendor": "JUNIPER",
            "eq_type": "ROUTER",
            "model": "MX240",
            "path_name": "51.KGFD.000154..CHTR",
            "path_inst_id": 2487216,
            "topology": "Point to Point",
            "tid": "AUSDTXIR6CW",
            "port_access_id": "ET-2/3/2",
            "vlan_operation": None,
            "device_role": "C",
            "path_type": "CAR-CTBH NNI",
            "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
            "leg_name": "1",
            "full_address": "11921 N MOPAC EXPY",
            "svlan": None,
            "cevlan": None,
            "custsvlan": None,
            "chan_name": "VLAN3011",
            "management_ip": "71.42.150.82/32",
            "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
            "split_id": None,
            "status": "Designed",
        },
        "nfx": [
            {
                "test_fqdn": "CHCGILDTS6W.CHTRSE.COM",
                "test_circ_inst": 2175025,
                "test_equip_model": "NFX250-S1",
                "test_equip_status": "Live",
                "test_tid": "CHCGILDTS6W",
                "test_equip_vendor": "JUNIPER",
                "test_circ_status": "Live",
            },
            {
                "test_fqdn": "CHCGILDTS6W.CHTRSE.COM",
                "test_circ_inst": 2175027,
                "test_equip_model": "NFX250-S1",
                "test_equip_status": "Live",
                "test_tid": "CHCGILDTS6W",
                "test_equip_vendor": "JUNIPER",
                "test_circ_status": "Live",
            },
        ],
        "vta": {"port_access_id": "GE-1/0/0", "wbox_port_access_id": "GE-1/0/0"},
        "devices": [
            {
                "sequence": "0001.0000.0001.0001",
                "site_type": "HUB",
                "vendor": "JUNIPER",
                "eq_type": "ROUTER",
                "model": "MX240",
                "path_name": "51.KGFD.000154..CHTR",
                "path_inst_id": 2487216,
                "topology": "Point to Point",
                "tid": "AUSDTXIR6CW",
                "port_access_id": "ET-2/3/2",
                "vlan_operation": None,
                "device_role": "C",
                "path_type": "CAR-CTBH NNI",
                "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
                "leg_name": "1",
                "full_address": "11921 N MOPAC EXPY",
                "svlan": None,
                "cevlan": None,
                "custsvlan": None,
                "chan_name": "VLAN3011",
                "management_ip": "71.42.150.82/32",
                "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
                "split_id": None,
            },
            {
                "sequence": "0002.0000.0000.0000",
                "site_type": "HUB",
                "vendor": "JUNIPER",
                "eq_type": "ROUTER",
                "model": "MX240",
                "path_name": "51.L4XX.000246..CHTR",
                "path_inst_id": 2487178,
                "topology": "Point to Point",
                "tid": "AUSDTXIR6CW",
                "port_access_id": "ET-2/3/2",
                "vlan_operation": None,
                "device_role": "C",
                "path_type": "CAR-CTBH 4G",
                "owned_edge_point": "AUSDTXIR6CW-ET-2/3/2",
                "leg_name": "3011/PRIMARY",
                "full_address": "11921 N MOPAC EXPY",
                "svlan": "3011",
                "cevlan": None,
                "custsvlan": "3011",
                "chan_name": None,
                "management_ip": "71.42.150.82/32",
                "device_id": "AUSDTXIR6CW.DEV.CHTRSE.COM",
                "split_id": None,
            },
        ],
    }


@pytest.mark.unittest
def test_combine_side_data():
    pe = get_mock_pe()
    cpe = get_mock_cpe()
    nfx = get_mock_feasible_nfx()
    vta = get_mock_vta_details()
    devices = get_mock_a_side_devices()
    side_data = circuit_test_v3._combine_side_data(pe, cpe, nfx, vta, devices)
    assert side_data == get_combined_side_data()


def mock_leg_data():
    records = DataResp(file_name="tests/mock_data/circuit_testing/circuit_test_v3_leg_data.json")
    return records.json()


def mock_a_side_pe():
    records = DataResp(file_name="tests/mock_data/circuit_testing/leg_data_a_side_pe.json")
    return records.json()


def mock_z_side_pe():
    records = DataResp(file_name="tests/mock_data/circuit_testing/leg_data_z_side_pe.json")
    return records.json()


def mock_cpe():
    records = DataResp(file_name="tests/mock_data/circuit_testing/leg_data_cpe.json")
    return records.json()


@pytest.mark.unittest
def test_build_cpe_data():
    # we don't need to monkeypatch get ip address because mock data has mgmt ip
    side_data = get_combined_side_data()
    logger.debug(f"{side_data['cpe'] = }")
    cpe_data = circuit_test_v3._build_cpe_data(side_data["cpe"])
    logger.debug(f"{cpe_data = }")
    assert cpe_data == mock_cpe()
