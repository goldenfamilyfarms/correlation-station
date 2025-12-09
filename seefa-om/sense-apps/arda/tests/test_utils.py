import unittest
import logging
import pytest

from copy import deepcopy
from arda_app.bll import utils
from arda_app.bll.utils import (
    compare_ipv4_addresses_and_cidr_notation,
    compare_ipv6_addresses,
    check_keys,
    convert_to_int,
    get_4_digits,
    get_ips_from_subnet,
    get_special_char,
)

logger = logging.getLogger(__name__)


@pytest.mark.unittest
class TestIPv6AddressComparison(unittest.TestCase):
    def test_same_ipv6_addresses(self):
        address1 = "2605:E000:0:8::F:262E/127"
        address2 = "2605:E000:0:8::F:262E/127"
        self.assertTrue(compare_ipv6_addresses(address1, address2))

    def test_same_ipv6_space_in_subnet(self):
        address1 = "2605:E000:0:8::F:262E /127"
        address2 = "2605:E000:0:8::F:262E /127"
        self.assertTrue(compare_ipv6_addresses(address1, address2))

    def test_different_spelling_ipv6_addresses(self):
        address1 = "2605:E000:0:8::F:262E/127"
        address2 = "2605:E000:0:8:0:0:F:262E/127"
        self.assertTrue(compare_ipv6_addresses(address1, address2))

    def test_different_ipv6_addresses(self):
        address1 = "2605:E000:0:9::F:262E/127"
        address2 = "2605:E000:0:8:0:0:F:262E/127"
        self.assertFalse(compare_ipv6_addresses(address1, address2))

    def test_invalid_ipv6_address(self):
        address1 = "2605:E000:0:8::F:262E/127"
        address2 = "invalid_address"
        self.assertFalse(compare_ipv6_addresses(address1, address2))

    def test_different_prefix_lengths(self):
        address1 = "2605:E000:0:8::F:262E/127"
        address2 = "2605:E000:0:8::F:262E/128"
        self.assertFalse(compare_ipv6_addresses(address1, address2))

    def test_same_network_different_hosts(self):
        address1 = "2605:E000:0:8::F:262E/127"
        address2 = "2605:E000:0:8::F:262F/127"
        self.assertTrue(compare_ipv6_addresses(address1, address2))


@pytest.mark.unittest
class TestCheckKeys(unittest.TestCase):
    def test_all_keys_present(self):
        body = {"key1": "value1", "key2": "value2", "key3": "value3"}
        keys = ["key1", "key2", "key3"]
        result = check_keys(body, keys)
        self.assertEqual(result, [])

    def test_missing_keys(self):
        body = {"key1": "value1", "key3": "value3"}
        keys = ["key1", "key2", "key3"]
        result = check_keys(body, keys)
        self.assertEqual(result, ["key2"])

    def test_empty_body(self):
        body = {}
        keys = ["key1", "key2", "key3"]
        result = check_keys(body, keys)
        self.assertEqual(result, ["key1", "key2", "key3"])

    def test_empty_keys(self):
        body = {"key1": "value1", "key2": "value2", "key3": "value3"}
        keys = []
        result = check_keys(body, keys)
        self.assertEqual(result, [])

    def test_both_empty(self):
        body = {}
        keys = []
        result = check_keys(body, keys)
        self.assertEqual(result, [])

    def test_duplicate_keys(self):
        body = {"key1": "value1", "key1": "value2", "key3": "value3"}  # noqa: F601
        keys = ["key1", "key2", "key3"]
        result = check_keys(body, keys)
        self.assertEqual(result, ["key2"])


@pytest.mark.unittest
class TestGet4Digits(unittest.TestCase):
    def test_digits_in_middle(self):
        chan = "abc1234xyz"
        result = get_4_digits(chan)
        self.assertEqual(result, "1234")

    def test_digits_at_start(self):
        chan = "5678xyz"
        result = get_4_digits(chan)
        self.assertEqual(result, "5678")

    def test_digits_at_end(self):
        chan = "abc9876"
        result = get_4_digits(chan)
        self.assertEqual(result, "9876")

    def test_no_digits(self):
        chan = "abcdef"
        result = get_4_digits(chan)
        self.assertEqual(result, "")

    def test_empty_string(self):
        chan = ""
        result = get_4_digits(chan)
        self.assertEqual(result, "")


@pytest.mark.unittest
class TestGetSpecialChar(unittest.TestCase):
    def test_special_char_present(self):
        chan = "abc$123"
        result = get_special_char(chan)
        self.assertEqual(result, "$")

    def test_no_special_char(self):
        chan = "abc123"
        result = get_special_char(chan)
        assert result == ""

    def test_empty_string(self):
        chan = ""
        result = get_special_char(chan)
        assert result == ""


@pytest.mark.unittest
class TestConvertToInt(unittest.TestCase):
    def test_valid_conversion(self):
        num = "42"
        result = convert_to_int(num)
        self.assertEqual(result, 42)

    def test_invalid_conversion(self):
        num = "abc"
        default = 99
        result = convert_to_int(num, default)
        self.assertEqual(result, default)

    def test_empty_string(self):
        num = ""
        result = convert_to_int(num)
        self.assertEqual(result, 0)


@pytest.mark.unittest
class TestGetIPsFromSubnet(unittest.TestCase):
    def test_valid_subnet(self):
        subnet = "10.0.0.0/24"
        expected_ips = [f"10.0.0.{i}" for i in range(256)]
        result = get_ips_from_subnet(subnet)
        self.assertListEqual(result, expected_ips)

    def test_invalid_subnet(self):
        subnet = "10.0.0.0/33"
        result = get_ips_from_subnet(subnet)
        self.assertListEqual(result, [])

    def test_empty_subnet(self):
        subnet = ""
        result = get_ips_from_subnet(subnet)
        self.assertListEqual(result, [])

    def test_subnet_exception(self):
        subnet = "invalid_subnet"
        result = get_ips_from_subnet(subnet)
        self.assertEqual(result, [])


@pytest.mark.unittest
class TestCompareIPv4AddressesAndCIDRNotation(unittest.TestCase):
    def setUp(self):
        self.monkeypatch = pytest.MonkeyPatch()

    def test_IPs_not_equal(self):
        db_address_CW = "98.6.191.105/31"
        net_address_CW = "98.6.191.106/31"
        cid = "91.TGXX.001266..CHTR"
        vgw_ipv4 = "98.6.191.107/31"
        result = compare_ipv4_addresses_and_cidr_notation(db_address_CW, net_address_CW, cid, vgw_ipv4)
        self.assertEqual(result, False)

    def test_IPs_and_CIDRs_equal(self):
        db_address_CW = "98.6.191.106/31"
        net_address_CW = "98.6.191.106/31"
        cid = "91.TGXX.001266..CHTR"
        vgw_ipv4 = "98.6.191.107/31"
        result = compare_ipv4_addresses_and_cidr_notation(db_address_CW, net_address_CW, cid, vgw_ipv4)
        self.assertEqual(result, True)

    def test_IPs_equal_and_CIDRs_unequal(self):
        put_granite_resp = {
            "id": "ELPSTXIGG01/999.9999.999.99/LAG",
            "status": "Live",
            "equipInstId": "1761734",
            "retString": "Shelf Updated",
        }
        db_address_CW = "98.6.191.106/31"
        net_address_CW = "98.6.191.106/30"
        cid = "91.TGXX.001266..CHTR"
        vgw_ipv4 = "98.6.191.107/31"
        self.monkeypatch.setattr(utils, "update_vgw_shelf_ipv4_address", lambda *args: put_granite_resp)
        result = compare_ipv4_addresses_and_cidr_notation(db_address_CW, net_address_CW, cid, vgw_ipv4)
        self.assertEqual(result, True)

    def test_address_value_error_exception(self):
        db_address_CW = "98.6.191."
        net_address_CW = "98.6.191.106/31"
        cid = "91.TGXX.001266..CHTR"
        vgw_ipv4 = "98.6.191.107/31"
        try:
            result = compare_ipv4_addresses_and_cidr_notation(db_address_CW, net_address_CW, cid, vgw_ipv4)
        except Exception:
            self.assertEqual(result, False)


@pytest.mark.unittest
class TestGetCIDInfoFromIP(unittest.TestCase):
    def setUp(self):
        self.monkeypatch = pytest.MonkeyPatch()

    def test_get_cid_info_from_ip(self):
        paths_from_ip_resp = [
            {
                "CIRC_PATH_INST_ID": "2207463",
                "PATH_NAME": "81.L1XX.008914..CHTR",
                "PATH_REV": "1",
                "PATH_TYPE": "ETHERNET",
                "BANDWIDTH": "1 Gbps",
                "STATUS": "Pending Decommission",
                "IPv4_ASSIGNED_SUBNETS": "173.197.31.104/30",
                "IPv4_ASSIGNED_GATEWAY": "173.197.31.105/30",
                "IPv4_SERVICE_TYPE": "LAN",
                "IPv6_GLUE_SUBNET": "2605:ED00:118:3D::/64",
                "IPv6_ASSIGNED_SUBNETS": "2605:ED00:797::/48",
                "IPv6_SERVICE_TYPE": "ROUTED",
                "SERVICE_TYPE": "COM-DIA",
            }
        ]
        ip = "173.197.31.104/30"
        cid = "81.L1XX.008914..CHTR"
        status = "Pending Decommission"
        self.monkeypatch.setattr(utils, "get_paths_from_ip", lambda *args: paths_from_ip_resp)
        result = utils.get_cid_info_from_ip(ip)
        self.assertEqual(result, (cid, status))

    def test_get_paths_from_ip_is_not_a_list(self):
        paths_from_ip_error_resp = {
            "CIRC_PATH_INST_ID": "2207463",
            "PATH_NAME": "81.L1XX.008914..CHTR",
            "PATH_REV": "1",
            "PATH_TYPE": "ETHERNET",
            "BANDWIDTH": "1 Gbps",
            "STATUS": "Pending Decommission",
            "IPv4_ASSIGNED_SUBNETS": "173.197.31.104/30",
            "IPv4_ASSIGNED_GATEWAY": "173.197.31.105/30",
            "IPv4_SERVICE_TYPE": "LAN",
            "IPv6_GLUE_SUBNET": "2605:ED00:118:3D::/64",
            "IPv6_ASSIGNED_SUBNETS": "2605:ED00:797::/48",
            "IPv6_SERVICE_TYPE": "ROUTED",
            "SERVICE_TYPE": "COM-DIA",
        }
        ip = "173.197.31.104/30"
        self.monkeypatch.setattr(utils, "get_paths_from_ip", lambda *args: paths_from_ip_error_resp)
        try:
            utils.get_cid_info_from_ip(ip)
        except Exception as e:
            assert e.data.get("message") == f"ARDA - Unable to retrieve path data from IP {ip}"

    def test_get_paths_from_ip_with_missing_cid(self):
        paths_from_ip_error_resp = [
            {
                "CIRC_PATH_INST_ID": "2207463",
                "PATH_REV": "1",
                "PATH_TYPE": "ETHERNET",
                "BANDWIDTH": "1 Gbps",
                "STATUS": "Pending Decommission",
                "IPv4_ASSIGNED_SUBNETS": "173.197.31.104/30",
                "IPv4_ASSIGNED_GATEWAY": "173.197.31.105/30",
                "IPv4_SERVICE_TYPE": "LAN",
                "IPv6_GLUE_SUBNET": "2605:ED00:118:3D::/64",
                "IPv6_ASSIGNED_SUBNETS": "2605:ED00:797::/48",
                "IPv6_SERVICE_TYPE": "ROUTED",
                "SERVICE_TYPE": "COM-DIA",
            }
        ]
        ip = "173.197.31.104/30"
        self.monkeypatch.setattr(utils, "get_paths_from_ip", lambda *args: paths_from_ip_error_resp)
        try:
            utils.get_cid_info_from_ip(ip)
        except Exception as e:
            assert e.data.get("message") == f"ARDA - Unable to determine CID info IP {ip} belongs to"

    def test_get_paths_from_ip_with_missing_status(self):
        paths_from_ip_error_resp = [
            {
                "CIRC_PATH_INST_ID": "2207463",
                "PATH_NAME": "81.L1XX.008914..CHTR",
                "PATH_REV": "1",
                "PATH_TYPE": "ETHERNET",
                "BANDWIDTH": "1 Gbps",
                "STATUS": None,
                "IPv4_ASSIGNED_SUBNETS": "173.197.31.104/30",
                "IPv4_ASSIGNED_GATEWAY": "173.197.31.105/30",
                "IPv4_SERVICE_TYPE": "LAN",
                "IPv6_GLUE_SUBNET": "2605:ED00:118:3D::/64",
                "IPv6_ASSIGNED_SUBNETS": "2605:ED00:797::/48",
                "IPv6_SERVICE_TYPE": "ROUTED",
                "SERVICE_TYPE": "COM-DIA",
            }
        ]
        ip = "173.197.31.104/30"
        self.monkeypatch.setattr(utils, "get_paths_from_ip", lambda *args: paths_from_ip_error_resp)
        try:
            utils.get_cid_info_from_ip(ip)
        except Exception as e:
            assert e.data.get("message") == f"ARDA - Unable to determine CID info IP {ip} belongs to"


@pytest.mark.unittest
class TestRetainingIPAddresses(unittest.TestCase):
    payload = {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "product_family": "Dedicated Internet Service",
        "engineering_id": "a2g8Z000009jh1LQAQ",
        "engineering_name": "ENG-04665914",
        "engineering_job_type": "New",
        "cid": "81.L1XX.014725..CHTR",
        "related_cid": None,
        "pid": "5580563",
        "legacy_company": "TWC",
        "service_location_address": "219 W 9TH ST",
        "build_type": "Home Run",
        "fiber_building_serviceability_status": "On-Net",
        "bw_speed": "1",
        "bw_unit": "Gbps",
        "agg_bandwidth": "1Gbps",
        "connector_type": "RJ45",
        "uni_type": "Access",
        "retain_ip_addresses": "Yes",
        "usable_ip_addresses_requested": "None",
        "class_of_service_needed": "false",
        "z_location": "219 W 9TH ST, KANSAS CITY, MO 64105",
        "create_new_elan_instance": "N/A",
        "billing_account_ordering_customer": "8347400183354445",
        "granite_site_name": "KSCIMO98-21C KANSAS CITY MASTER TENANT LLC//219 W 9TH ST",
        "service_code": None,
        "change_reason": "Reconnect",
        "3rd_party_provided_circuit": "N",
        "assigned_cd_team": "Retail - NE",
        "primary_fia_service_type": "LAN",
        "ip_address": "173.197.31.104/30",
        "type_II_circuit_accepted_by_spectrum": False,
        "rework": False,
    }
    exit_payload = {
        "cid": "81.L1XX.014725..CHTR",
        "circ_path_inst_id": "2642154",
        "granite_link": "https://granite-ise.chartercom.com:2269/web-access/WebAccess.html#HistoryToken,type=Path,mode=VIEW_MODE,instId=2642154",
        "maintenance_window_needed": "No",
        "ip_video_on_cen": "No",
        "ctbh_on_cen": "No",
        "cpe_model_number": "NA",
        "message": "New Install completed successfully",
        "hub_work_required": "Yes",
        "cpe_installer_needed": "Yes",
        "engineering_job_type": "New",
        "circuit_design_notes": "New construction job complete",
    }
    paths_from_ip_resp = [
        {
            "CIRC_PATH_INST_ID": "2207463",
            "PATH_NAME": "81.L1XX.008914..CHTR",
            "PATH_REV": "1",
            "PATH_TYPE": "ETHERNET",
            "BANDWIDTH": "1 Gbps",
            "STATUS": "Pending Decommission",
            "IPv4_ASSIGNED_SUBNETS": "173.197.31.104/30",
            "IPv4_ASSIGNED_GATEWAY": "173.197.31.105/30",
            "IPv4_SERVICE_TYPE": "LAN",
            "IPv6_GLUE_SUBNET": "2605:ED00:118:3D::/64",
            "IPv6_ASSIGNED_SUBNETS": "2605:ED00:797::/48",
            "IPv6_SERVICE_TYPE": "ROUTED",
            "SERVICE_TYPE": "COM-DIA",
        }
    ]

    def setUp(self):
        self.monkeypatch = pytest.MonkeyPatch()

    def test_retaining_ip_addresses(self):
        expected = {
            "cid": "81.L1XX.014725..CHTR",
            "circ_path_inst_id": "2642154",
            "granite_link": "https://granite-ise.chartercom.com:2269/web-access/WebAccess.html#HistoryToken,type=Path,mode=VIEW_MODE,instId=2642154",
            "maintenance_window_needed": "Yes - No Hub Impact - Inflight Customer Only Impacted",
            "ip_video_on_cen": "No",
            "ctbh_on_cen": "No",
            "cpe_model_number": "NA",
            "message": "New Install completed successfully",
            "hub_work_required": "Yes",
            "cpe_installer_needed": "Yes",
            "engineering_job_type": "New",
            "circuit_design_notes": "MW to migrate Customer IPs; New construction job complete",
        }
        self.monkeypatch.setattr(utils, "get_paths_from_ip", lambda *args: self.paths_from_ip_resp)
        result = utils.retaining_ip_addresses(self.payload, self.exit_payload)
        self.assertEqual(result, expected)

    def test_retaining_ip_addresses_missing_cid_error(self):
        missing_cid_payload = deepcopy(self.payload)
        missing_cid_payload["cid"] = ""
        try:
            utils.retaining_ip_addresses(missing_cid_payload, self.exit_payload)
        except Exception as e:
            logger.debug(f"e - {e}")
            assert e.data.get("message") == f"ARDA - Unable to retrieve CID from payload {missing_cid_payload}"

    def test_retaining_ip_addresses_missing_ip_error(self):
        missing_ip_payload = deepcopy(self.payload)
        missing_ip_payload.pop("ip_address")
        try:
            utils.retaining_ip_addresses(missing_ip_payload, self.exit_payload)
        except Exception as e:
            assert e.data.get("message") == f"ARDA - Unable to retrieve IP address from payload {missing_ip_payload}"

    def test_retaining_ip_addresses_missing_cidr_error(self):
        missing_cidr_payload = deepcopy(self.payload)
        missing_cidr_payload["ip_address"] = missing_cidr_payload.get("ip_address").split("/")[0]
        try:
            utils.retaining_ip_addresses(missing_cidr_payload, self.exit_payload)
        except Exception as e:
            assert (
                e.data.get("message") == f"ARDA - IP address {missing_cidr_payload['ip_address']} isn't in CIDR notation"
            )

    def test_retaining_ip_addresses_ip_value_error(self):
        ip_value_error_payload = deepcopy(self.payload)
        ip_value_error_payload["ip_address"] = " "
        try:
            utils.retaining_ip_addresses(ip_value_error_payload, self.exit_payload)
        except Exception as e:
            assert (
                e.data.get("message")
                == f"ARDA - IP address {ip_value_error_payload['ip_address']} doesn't appear to be formatted as IPv4 or IPv6"
            )

    def test_retaining_ip_addresses_usable_ip_addresses_requested_error(self):
        usable_ip_addresses_requested_error_payload = deepcopy(self.payload)
        usable_ip_addresses_requested_error_payload["usable_ip_addresses_requested"] = "/29=5"
        try:
            utils.retaining_ip_addresses(usable_ip_addresses_requested_error_payload, self.exit_payload)
        except Exception as e:
            assert (
                e.data.get("message")
                == f"ARDA - Usable IP addresses are erroneously requested when attempting to retain IP addresses for {usable_ip_addresses_requested_error_payload['cid']}"
            )

    def test_retaining_ip_addresses_cid_not_pending_decom_error(self):
        cid_to_move_ips_from = self.paths_from_ip_resp[0].get("PATH_NAME")
        cid_status = "Live"
        self.monkeypatch.setattr(utils, "get_cid_info_from_ip", lambda *args: (cid_to_move_ips_from, cid_status))
        try:
            utils.retaining_ip_addresses(self.payload, self.exit_payload)
        except Exception as e:
            assert (
                e.data.get("message")
                == f"ARDA - Not able to move IP addresses from CID {cid_to_move_ips_from} because its status is {cid_status}"
            )
