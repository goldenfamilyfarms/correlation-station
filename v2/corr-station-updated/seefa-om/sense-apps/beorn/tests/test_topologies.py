import json
import logging
import pytest
import requests

from unittest.mock import MagicMock
from werkzeug.exceptions import InternalServerError, NotImplemented

from beorn_app.bll.topologies import Topologies
from beorn_app.bll import granite


logger = logging.getLogger(__name__)


class DataResp:
    def __init__(self, status_code, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        with open(self.file_name) as f:
            data = json.load(f)
        return data


def mock_denodo_uda(*args, **kwargs):
    data = DataResp(200, "tests/mock_data/topologies/elan_dv_circ_path_attr_settings.json")
    logger.debug("= mock_denodo_uda =")
    logger.debug(data.json()["elements"][0])
    return data.json()["elements"]


def mock_granite_uda(*args, **kwargs):
    data = DataResp(200, "tests/mock_data/topologies/granite_uda_1509654.json")
    logger.debug("= mock_granite_uda =")
    logger.debug(data.json()[0])
    return data.json()


def mock_granite_type_2(*args, **kwargs):
    return [
        {
            "CIRC_PATH_INST_ID": "2631041",
            "PATH_NAME": "51.L2XX.001307..CHTR",
            "REV_NBR": "1",
            "PATH_CLASS": "P",
            "GROUP_NAME": "ADDITIONAL CIRCUIT INFORMATION",
            "ATTR_NAME": "VC CLASS",
            "ATTR_VALUE": "TYPE 2",
        }
    ]


def mock_granite_type_1(*args, **kwargs):
    return [
        {
            "CIRC_PATH_INST_ID": "2631041",
            "PATH_NAME": "51.L2XX.001307..CHTR",
            "REV_NBR": "1",
            "PATH_CLASS": "P",
            "GROUP_NAME": "ADDITIONAL CIRCUIT INFORMATION",
            "ATTR_NAME": "VC CLASS",
            "ATTR_VALUE": "TYPE 1",
        }
    ]


@pytest.mark.unittest
def test_denodo_404(monkeypatch):
    def bad_denodo_get(*args, **kwargs):
        return DataResp(404)

    monkeypatch.setattr(requests, "get", bad_denodo_get)
    with pytest.raises(InternalServerError):
        _ = Topologies("cid").create_topology()


@pytest.mark.unittest
def test_denodo_500(monkeypatch):
    def bad_denodo_get(*args, **kwargs):
        return DataResp(500)

    monkeypatch.setattr(requests, "get", bad_denodo_get)
    with pytest.raises(InternalServerError):
        _ = Topologies("cid").create_topology()


@pytest.mark.unittest
def test_create_topology_fia(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/fia_dv_mdso_model_v20220413_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_uda)

    topology = Topologies("cid").create_topology()
    assert topology["serviceName"] == "41.LOXX.000187.CMH.TWCC"
    assert topology["serviceType"] == "FIA"
    assert topology["serviceMedia"] == "FIBER"
    topo = topology["topology"][0]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 2
    assert topo["data"]["node"][0]["name"][-1]["value"] == "LIVE"
    service = topology["service"][0]
    assert service["model"] == "MEF-LEGATO-EVC"
    assert service["data"]["evc"]
    assert service["data"]["fia"]
    assert topo["data"]["node"][0]["name"][4]["value"] == "65.189.176.21"
    assert service["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"][0] == "24.142.154.48/28"


@pytest.mark.skip(reason="No Valid Circuit for this Test")
@pytest.mark.unittest
def test_create_topology_l_c_fia(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/l-c-fia_dv_mdso_model_v20220413_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("cid").create_topology()
    assert topology["serviceName"] == "86.L1XX.990761..CHTR"
    assert topology["serviceType"] == "FIA"
    assert topology["serviceMedia"] == "FIBER"
    topo = topology["topology"][0]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 3
    assert len(topo["data"]["node"][0]["ownedNodeEdgePoint"][0]["name"]) == 4
    assert topo["data"]["node"][0]["name"][-1]["value"] == "LIVE"
    assert topo["data"]["node"][1]["name"][-1]["value"] == "LIVE"
    assert topo["data"]["node"][-1]["name"][-1]["value"] == "PLANNED"
    assert topo["data"]["link"][0]["nodeEdgePoint"][0] == "SVVLTNKA3CW-TE0/0/0/18"
    assert topo["data"]["link"][0]["uuid"] == "SVVLTNKA3CW-TE0/0/0/18_SVVLTNKA0QW-XE-0/0/0"
    service = topology["service"][0]
    assert service["model"] == "MEF-LEGATO-EVC"
    assert service["data"]["evc"]
    assert service["data"]["fia"]


@pytest.mark.unittest
def test_create_topology_epl(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/epl_dv_mdso_model_v20220413_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("cid").create_topology()
    assert topology["serviceName"] == "51.L1XX.814265..TWCC"
    assert topology["serviceType"] == "ELINE"
    assert topology["serviceMedia"] == "FIBER"
    topo = topology["topology"][0]
    topo1 = topology["topology"][1]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 1
    assert len(topo1["data"]["node"]) == 2
    assert len(topo["data"]["link"]) == 0
    assert len(topo1["data"]["link"]) == 1
    assert topo["data"]["node"][0]["name"][4]["value"] == "71.42.150.66"  # side a
    assert topo1["data"]["node"][0]["name"][4]["value"] == "71.42.150.68"  # side z (cidr notation)
    assert topo["data"]["node"][0]["name"][-1]["value"] == "LIVE"
    assert topo1["data"]["node"][0]["name"][-1]["value"] == "LIVE"
    assert topo1["data"]["node"][-1]["name"][-1]["value"] == "LIVE"
    service = topology["service"][0]
    assert service["model"] == "MEF-LEGATO-EVC"
    assert service["data"]["evc"]
    assert service["data"]["evc"][0]["serviceType"] == "EPL"


@pytest.mark.skip(reason="No Valid Circuit for this Test")
@pytest.mark.unittest
def test_create_topology_evpl(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/evpl_dv_mdso_model_v20210209_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.IAMEVP..TWCC").create_topology()
    onep_value = "51001.GE1.CNI4TXR37ZW.CNI4TXR37ZW"
    assert topology["serviceName"] == "51.L1XX.IAMEVP..TWCC"
    assert topology["serviceType"] == "ELINE"
    assert topology["serviceMedia"] == "FIBER"
    topo = topology["topology"][0]
    topo1 = topology["topology"][1]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 2
    assert len(topo1["data"]["node"]) == 2
    assert len(topo["data"]["link"]) == 1
    assert len(topo1["data"]["link"]) == 1
    onep_value = "51001.GE1.CNI4TXR37ZW.CNI4TXR37ZW"
    assert topo["data"]["node"][0]["ownedNodeEdgePoint"][0]["name"][-1]["value"] == "51.KGFD.000078..TWCC"
    assert topo1["data"]["node"][-1]["ownedNodeEdgePoint"][-1]["name"][-1]["value"] == onep_value
    service = topology["service"][0]
    assert service["model"] == "MEF-LEGATO-EVC"
    assert service["data"]["evc"]
    assert service["data"]["evc"][0]["serviceType"] == "EVPL"


@pytest.mark.unittest
def test_create_topology_dia(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/dia_dv_mdso_model_v20220413_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("cid").create_topology()
    assert topology["serviceName"] == "51.L1XX.008488..TWCC"
    assert topology["serviceType"] == "FIA"  # because DIA/FIA are marked the same in create_topology
    assert topology["serviceMedia"] == "FIBER"
    topo = topology["topology"][0]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 4
    assert len(topo["data"]["link"]) == 4
    service = topology["service"][0]
    assert service["model"] == "MEF-LEGATO-EVC"
    assert service["data"]["evc"]
    # extra lanIpv4 added to Denodo Mock Data to test handling multiple IP blocks - cidr separate
    assert service["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"][0] == "192.168.14.0/30"
    assert service["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"][1] == "192.168.14.8/29"


@pytest.mark.unittest
def test_create_topology_fia_multi_routed(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/multi_routed_fia_dv_mdso_model_v20220413_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("cid").create_topology()
    assert topology["serviceName"] == "51.L1XX.008480..TWCC"
    assert topology["serviceType"] == "FIA"
    assert topology["serviceMedia"] == "FIBER"
    topo = topology["topology"][0]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 2
    assert len(topo["data"]["link"]) == 1
    service = topology["service"][0]
    assert service["model"] == "MEF-LEGATO-EVC"
    assert service["data"]["evc"][0]["cosNames"][0]["name"] == "BRONZE"
    assert service["data"]["fia"][0]["type"] == "STATIC"
    assert service["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"][0] == "192.168.1.0/24"
    assert service["data"]["fia"][0]["endPoints"][0]["lanIpv4Addresses"][1] == "192.168.2.0/30"
    assert service["data"]["fia"][0]["endPoints"][0]["wanIpv4Address"] == "192.168.56.0/30"


@pytest.mark.unittest
def test_create_topology_elan(monkeypatch, client):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/elan_dv_mdso_model_v20220413_1.json")

    def mock_vpls_vlan_id_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/granite_uda_1509654.json")

    def mock_elan_slm_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/elan3_slm_granite.json")

    granite_get_mock = MagicMock()
    granite_get_mock.side_effect = [
        mock_denodo_get(),
        mock_vpls_vlan_id_get(),
        mock_vpls_vlan_id_get(),
        mock_elan_slm_get(),
    ]
    monkeypatch.setattr(requests, "get", granite_get_mock)
    topology = Topologies("cid").create_topology()

    assert topology["serviceName"] == "51.L1XX.802228..TWCC"
    assert topology["serviceType"] == "ELAN"
    assert topology["serviceMedia"] == "FIBER"
    assert topology["service"][0]["data"]["evc"][0]["vplsVlanId"] == "400"
    topo = topology["topology"][0]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 2
    assert len(topo["data"]["link"]) == 1
    service = topology["service"][0]
    assert service["data"]["evc"][0]["serviceType"] == "EP-LAN"


@pytest.mark.skip(reason="No Valid Circuit for this Test")
@pytest.mark.unittest
def test_create_topology_evplan(monkeypatch, client):
    def mock_denodo_get(*args, **kwargs):
        logger.debug("= mock_denodo_get =")
        return DataResp(200, "tests/mock_data/topologies/evplan_dv_mdso_model_v20210209_1.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_uda)

    topology = Topologies("55.L5XX.EVPLAN..TWCC").create_topology()
    assert topology["serviceName"] == "55.L5XX.EVPLAN..TWCC"
    assert topology["serviceType"] == "ELAN"
    assert topology["serviceMedia"] == "FIBER"
    assert topology["service"][0]["data"]["evc"][0]["vplsVlanId"] == "400"
    topo = topology["topology"][0]
    assert topo["model"] == "ONF_TAPI"
    assert len(topo["data"]["node"]) == 2
    assert len(topo["data"]["link"]) == 1
    service = topology["service"][0]
    assert service["data"]["evc"][0]["serviceType"] == "EVP-LAN"
    t = [[list(node["name"]) for node in onep["ownedNodeEdgePoint"]][0] for onep in topo["data"]["node"]][0]
    for i in t:
        if i["name"] == "name":
            assert i["value"] == "GE-1/1/0"
        if i["name"] == "portRole":
            assert i["value"] == "INNI"
        if i["name"] == "transportId":
            assert i["value"] == "51001.GE1.AUSDTXIR2CW.AUSDTXIRHZW"


@pytest.mark.unittest
def test_create_topology_ctbh(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/ctbh_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/ctbh_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L4XX.000246..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_eline_one(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/eline1_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/eline1_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.802200..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_eline_two(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/eline2_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/eline2_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.817141..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_eline_local_switch(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/eline_local_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/eline_local_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.011290..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_fia_multiple_ipv4_lan(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/fia_multiple_ipv4_lan_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/fia_multiple_ipv4_lan_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.008480..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_fia_multiple_ipv4_wan(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/fia_multiple_ipv4_wan_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/fia_multiple_ipv4_wan_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.009485..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_fia_routed_ipv4_routed_ipv6(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/fia_routed_ipv4_routed_ipv6_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/fia_routed_ipv4_routed_ipv6_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.991069..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_fia_typical(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/fia_typical_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/fia_typical_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.L1XX.008486..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_elan_one(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/elan1_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/elan1_topologies.json").json()

    def mock_vpls_vlan_id_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/elan1_vpls_vlan_id_granite.json")

    def mock_elan_slm_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/elan1_slm_granite.json")

    granite_get_mock = MagicMock()
    granite_get_mock.side_effect = [
        mock_denodo_get(),
        mock_vpls_vlan_id_get(),
        mock_vpls_vlan_id_get(),
        mock_elan_slm_get(),
    ]

    monkeypatch.setattr(requests, "get", granite_get_mock)
    topology = Topologies("51.L1XX.802226..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_elan_two(monkeypatch):
    def mock_denodo_get():
        return DataResp(200, "tests/mock_data/topologies/elan2_denodo.json")

    def mock_vpls_vlan_id_get():
        return DataResp(200, "tests/mock_data/topologies/elan2_vpls_vlan_id_granite.json")

    def mock_elan_slm_get():
        return DataResp(200, "tests/mock_data/topologies/elan2_slm_granite.json")

    def mock_circuit_uda_get():
        return DataResp(200, "tests/mock_data/topologies/elan2_slm_granite_uda.json")

    granite_get_mock = MagicMock()
    granite_get_mock.side_effect = [
        mock_denodo_get(),
        mock_circuit_uda_get(),
        mock_vpls_vlan_id_get(),
        mock_elan_slm_get(),
        mock_circuit_uda_get(),
    ]

    mock_topology = DataResp(200, "tests/mock_data/topologies/elan2_topologies.json").json()
    monkeypatch.setattr(requests, "get", granite_get_mock)
    topology = Topologies("51.L1XX.802235..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_voice_one(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/voice1_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/voice1_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("60.TGXX.000335..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_voice_two(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/voice2_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/voice2_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.IPXN.002284..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_voice_three(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/voice3_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/voice3_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("51.IPXN.002287..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_video_rphy(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/video_rphy_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/video_rphy_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("42.VSXX.000096..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_linked_port(monkeypatch):
    # Raises NotImplemented exception with denodo data containing multiple linked ports
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/linked_port.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    with pytest.raises(NotImplemented):
        _ = Topologies("44.L1XX.003392..CHTR").create_topology()


@pytest.mark.unittest
def test_create_topology_linked_lag_port(monkeypatch):
    # Raises NotImplemented exception with denodo data containing multiple linked lag ports
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/linked_lag_ports.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    with pytest.raises(NotImplemented):
        _ = Topologies("86.L1XX.003039..CHTR").create_topology()


@pytest.mark.unittest
def test_create_topology_3_letter_city_tid(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/3_letter_city_tid_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/3_letter_city_tid_topologies.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("41.L1XX.008581..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_type_2_fia_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/typeII_fia_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/typeII_fia_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("51.L2XX.001307..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_type_2_eline_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/typeII_eline_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/typeII_eline_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("51.L2XX.001308..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_topology_elan_type2(monkeypatch, client):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/typeII_elan_denodo.json")

    def mock_type2_uda_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/type2_elan_uda_granite.json")

    def mock_vpls_vlan_id_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/granite_uda_1509654.json")

    def mock_elan_slm_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/elan3_slm_granite.json")

    granite_get_mock = MagicMock()
    granite_get_mock.side_effect = [
        mock_denodo_get(),
        mock_type2_uda_get(),
        mock_vpls_vlan_id_get(),
        mock_elan_slm_get(),
    ]
    monkeypatch.setattr(requests, "get", granite_get_mock)
    topology = Topologies("cid").create_topology()
    mock_topology = DataResp(200, "tests/mock_data/topologies/typeII_elan_topology.json").json()

    assert topology == mock_topology


@pytest.mark.unittest
def test_create_mrs_eline_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/mrs_eline_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/mrs_eline_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("33.L1XX.000196..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.skip(reason="Temporarily Disabled until Trunked is supported on EXPO")
@pytest.mark.unittest
def test_create_mss_dia_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/mss_dia_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/mss_dia_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("20.L1XX.902787..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_mrs_mss_dia_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/mrs_mss_dia_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/mrs_mss_dia_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("86.L1XX.802115..TWCC").create_topology()
    assert topology == mock_topology


@pytest.mark.skip(reason="Temporarily Disabled until Trunked is supported on EXPO")
@pytest.mark.unittest
def test_create_mrs_internet_dia_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/mrs_internet_dia_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/mrs_internet_dia_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("83.L1XX.002704..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_mrs_eplan_topology(monkeypatch, client):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/mrs_eplan_denodo.json")

    def mock_circuit_uda_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/granite_uda_2680125.json")

    def mock_vpls_vlan_id_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/granite_uda_2683417.json")

    def mock_elan_slm_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/mrs_eplan_slm_granite.json")

    granite_get_mock = MagicMock()
    granite_get_mock.side_effect = [
        mock_denodo_get(),
        mock_circuit_uda_get(),
        mock_vpls_vlan_id_get(),
        mock_elan_slm_get(),
    ]
    monkeypatch.setattr(requests, "get", granite_get_mock)
    topology = Topologies("40.L1XX.007911..CHTR").create_topology()
    mock_topology = DataResp(200, "tests/mock_data/topologies/mrs_eplan_topology.json").json()

    assert topology == mock_topology


@pytest.mark.unittest
def test_create_nni_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/nni_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/nni_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_1)
    topology = Topologies("46002.GE1.DLLUTXJR2CW.DLLUTXJR2CW").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_secure_fia_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/secure_fia_denodo.json")

    mock_topology = DataResp(200, "tests/mock_data/topologies/secure_fia_topology.json").json()

    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_granite_type_2)
    topology = Topologies("91.L1XX.017448..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_hosted_voice_rad_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/hosted_voice_denodo.json")

    def mock_hosted_voice_uda(*args, **kwargs):
        uda = DataResp(200, "tests/mock_data/topologies/hosted_voice_uda.json")
        return uda.json()

    mock_topology = DataResp(200, "tests/mock_data/topologies/hosted_voice_topologies.json").json()
    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_hosted_voice_uda)
    topology = Topologies("70.HNXN.000932..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_hosted_voice_rad_user_pattern_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/hosted_voice_rad_user_pattern_denodo.json")

    def mock_hosted_voice_uda(*args, **kwargs):
        uda = DataResp(200, "tests/mock_data/topologies/hosted_voice_rad_user_pattern_uda.json")
        return uda.json()

    mock_topology = DataResp(200, "tests/mock_data/topologies/hosted_voice_rad_user_pattern_topologies.json").json()
    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_hosted_voice_uda)
    topology = Topologies("84.HNXN.000430..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_create_hosted_voice_adva_topology(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/hosted_voice_adva_denodo.json")

    def mock_hosted_voice_uda(*args, **kwargs):
        uda = DataResp(200, "tests/mock_data/topologies/hosted_voice_adva_uda.json")
        return uda.json()

    mock_topology = DataResp(200, "tests/mock_data/topologies/hosted_voice_adva_topologies.json").json()
    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_hosted_voice_uda)
    topology = Topologies("58.HNXN.000294..CHTR").create_topology()
    assert topology == mock_topology


@pytest.mark.unittest
def test_alcatel_ctbh(monkeypatch):
    def mock_denodo_get(*args, **kwargs):
        return DataResp(200, "tests/mock_data/topologies/alcatel_ctbh_denodo.json")

    def mock_hosted_voice_uda(*args, **kwargs):
        uda = DataResp(200, "tests/mock_data/topologies/alcatel_ctbh_uda.json")
        return uda.json()

    mock_topology = DataResp(200, "tests/mock_data/topologies/alcatel_ctbh_topology.json").json()
    monkeypatch.setattr(requests, "get", mock_denodo_get)
    monkeypatch.setattr(granite, "call_granite_for_uda", mock_hosted_voice_uda)
    topology = Topologies("21.L2XX.001157..TWCC").create_topology()
    assert topology == mock_topology
