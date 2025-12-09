import json
import logging

import pytest
import requests

from beorn_app.bll.topologies import Topologies
from beorn_app.common import utils
from beorn_app.common.utils import clean_data, ipv4_block_processor, ipv4_length_validator, ipv4_str_processor

logger = logging.getLogger(__name__)


class DenodoResp:
    def __init__(self, status_code, file_name=None):
        self.status_code = status_code
        self.file_name = file_name

    def json(self):
        with open(self.file_name) as f:
            data = json.load(f)
        return data


@pytest.mark.unittest
def test_ipv4_clean_data(client):
    mandatory_fields = ["network_ip", "gateway_ip", "customer_ips"]

    # IPv4 Test Case 0 -- no subnet
    ip4_address = "173.197.217.160, 2ND 173.197.217.120"
    process_ipv4 = ipv4_str_processor(ipv4_address=ip4_address)
    assert "ipv4_list" in list(process_ipv4.keys())
    assert len(process_ipv4["ipv4_list"][0]) == 15  # simple ip address
    assert "ipv4_subnet_list" in list(process_ipv4.keys())
    assert len(process_ipv4["ipv4_subnet_list"]) == 0  # ip + subnet
    # Length Validator
    len_ipv4 = ipv4_length_validator(ipv4_dict=process_ipv4)
    assert len_ipv4["ipv4_len_check"] == "No subnet on 2 IP Addresses"
    # Block Validator
    block_ipv4 = ipv4_block_processor(ipv4_dict=len_ipv4)
    for ipv4_assign in block_ipv4["ipv4_assignments"]:
        assert mandatory_fields == list(ipv4_assign.keys())
    # call from clean_data
    clean_ipv4 = clean_data(ipv4=ip4_address)
    assert clean_ipv4["ipv4"]["ipv4_list"] == ["173.197.217.160", "173.197.217.120"]
    for ip in clean_ipv4["ipv4"]["ipv4_list"]:
        assert len(ip) == 15  # standard ipv4 length
    assert len(clean_ipv4["ipv4"]["ipv4_subnet_list"]) == 0
    assert clean_ipv4["ipv4"]["ipv4_len_check"] == "No subnet on 2 IP Addresses"
    for ipv4_assign in clean_ipv4["ipv4"]["ipv4_assignments"]:
        assert mandatory_fields == list(ipv4_assign.keys())

    # IPv4 Test Case 1 -- junk in the string
    ip4_addresses = [
        "173.197.217.160/29, 2ND 173.197.217.120/30",
        "173.197.217.160/29 (local), 2ND 173.197.217.120/30 (routed)",
    ]
    for addr in ip4_addresses:
        process_ipv4 = ipv4_str_processor(ipv4_address=addr)
        assert "ipv4_list" in process_ipv4.keys()
        assert len(process_ipv4["ipv4_list"][0]) == 15  # simple ip address
        assert "ipv4_subnet_list" in process_ipv4.keys()
        assert len(process_ipv4["ipv4_subnet_list"][0]) == 18  # ip + subnet
        # Length Validator
        len_ipv4 = ipv4_length_validator(ipv4_dict=process_ipv4)
        assert len_ipv4["ipv4_len_check"] == "2 Valid IP Addresses"
        # Block Validator
        block_ipv4 = ipv4_block_processor(ipv4_dict=len_ipv4)
        assert "ipv4_list" in process_ipv4.keys()
        for ipv4_assign in block_ipv4["ipv4_assignments"]:
            assert mandatory_fields == list(ipv4_assign.keys())
        # call from clean_data
        clean_ipv4 = clean_data(ipv4=addr)
        assert clean_ipv4["ipv4"]["ipv4_list"] == ["173.197.217.160", "173.197.217.120"]
        for ip in clean_ipv4["ipv4"]["ipv4_list"]:
            assert len(ip) == 15  # standard ipv4 length
        assert len(clean_ipv4["ipv4"]["ipv4_subnet_list"]) == 2
        assert clean_ipv4["ipv4"]["ipv4_len_check"] == "2 Valid IP Addresses"
        for ipv4_assign in clean_ipv4["ipv4"]["ipv4_assignments"]:
            assert mandatory_fields == list(ipv4_assign.keys())


@pytest.mark.xfail
def test_ipv4_clean_data_fail(client):
    # Bad IPs: the numbers are too high to be valid
    # mandatory_fields = ['network_ip', 'gateway_ip', 'customer_ips']
    ip4_addresses = [
        "888.197.217.160/29/29, 2ND 777.197.217.120/30",
        "888.197.217.160/29 (local), 2ND 777.197.217.120/30 (routed)",
    ]
    for addr in ip4_addresses:
        process_ipv4 = ipv4_str_processor(ipv4_address=addr)
        len_ipv4 = ipv4_length_validator(ipv4_dict=process_ipv4)
        # Block Validator
        ipv4_block_processor(ipv4_dict=len_ipv4)


@pytest.mark.skip
# @pytest.mark.unittest
def test_connect_denodo_uda(monkeypatch, client):
    def mock_denodo_get(_, timeout):
        logger.debug("= mock_denodo_get =")
        return DenodoResp(200, "tests/mock_data/topologies/elan_dv_mdso_model_v20200925_2.json")

    monkeypatch.setattr(requests, "get", mock_denodo_get)

    def mock_denodo_uda(*args, **kwargs):
        data = DenodoResp(200, "tests/mock_data/topologies/elan_dv_circ_path_attr_settings.json")
        logger.debug("= mock_denodo_uda =")
        logger.debug(data.json()["elements"][0])
        return data.json()["elements"]

    monkeypatch.setattr(utils, "call_denodo_for_uda", mock_denodo_uda)

    topology = Topologies("cid").create_topology()
    assert topology["service"][0]["data"]["evc"][0]["vplsVlanId"] == "400"
