# """Tests for Juniper-specific devices and code paths"""
#
# from lxml import etree
# import pytest
#
# from palantir import (_get_description, _get_admin_status,
#                       _get_oper_status, _get_last, _get_last_flapped,
#                       _get_bandwidth)
#
#
# @pytest.fixture
# def single_vlan_xml():
#     """Return sample XML from router"""
#
#     tree = etree.parse('tests/samples/single-vlan.xml')
#     return tree
#
#
# @pytest.fixture
# def multi_vlan_xml():
#     """Return sample XML containing multiple VLANs"""
#
#     tree = etree.parse('tests/samples/multi-vlan.xml')
#     return tree
#
#
# @pytest.fixture
# def multi_vlan_xml2():
#     """Return sample XML containing multip VLANs - from real MX"""
#
#     tree = etree.parse('tests/samples/multi-vlan2.xml')
#     return tree
#
#
# @pytest.fixture
# def single_vlan_0_xml():
#     """Return XML that has a single logical interface with VLAN of 0,
#     representing an interface that cannot be taken down.
#
#     `_get_last` test should return `False`
#
#     *Note* that in the future, we can delete a .0 VLAN if the physical port
#     type is NOT a CORE or REMCORE, or is marked as EP-UNI or EVP-UNI, which
#     are new.
#     """
#     tree = etree.parse('tests/samples/true_0.xml')
#     return tree
#
#
# # ----------------------
# # XML parsing unit tests
# # ----------------------
#
#
# def test__get_bandwidth(single_vlan_xml, single_vlan_0_xml, multi_vlan_xml,
#                         multi_vlan_xml2):
#     """Test that we can extract bandwidth settings for a vlan from xml"""
#
#     assert _get_bandwidth(single_vlan_xml, "1101") == "10mbps"
#     assert _get_bandwidth(single_vlan_0_xml, "0") == None
#     assert _get_bandwidth(multi_vlan_xml, "1008") == None
#     assert _get_bandwidth(multi_vlan_xml2, "59") == "1000mbps"
#     assert _get_bandwidth(multi_vlan_xml2, "71") == "10mbps"
#     assert _get_bandwidth(multi_vlan_xml2, "100") == "1000mbps"
#
#
# def test__get_last_flapped(single_vlan_xml, single_vlan_0_xml, multi_vlan_xml):
#     """Test that we can pull out a timestamp from xml"""
#
#     assert _get_last_flapped(single_vlan_xml) == "13426"
#     assert _get_last_flapped(single_vlan_0_xml) == "597940"
#     assert _get_last_flapped(multi_vlan_xml) == "1232663"
#
#
# def test__get_last(single_vlan_xml, multi_vlan_xml, single_vlan_0_xml):
#     """Test we can determine whether there's only one configured VLAN
#
#     The file 'single-vlan' should only have 3 'logical-interface' sections
#     """
#     assert _get_last(single_vlan_xml)
#
#     assert _get_last(multi_vlan_xml) is False
#
#     assert _get_last(single_vlan_0_xml) is False
#
#
# def test__get_oper_status(single_vlan_xml, single_mx_post):
#     """Test we can get the oper-status for a given port
#
#     `oper-status` for `sample_xml` is down
#     """
#     assert _get_oper_status(single_vlan_xml) == "down"
#
#
# def test__get_admin_status(single_vlan_xml):
#     """Test we can get the admin-status for a given port
#
#     `admin-status` for `sample_xml` is up
#     """
#     assert _get_admin_status(single_vlan_xml) == 'up'
#
#
# def test__get_description(single_vlan_xml, multi_vlan_xml, single_vlan_0_xml):
#     """Test we can get the description from a configured port"""
#
#     # expect responses for a good ports
#     assert _get_description(multi_vlan_xml, '1008') == 'CUST:ELINE::testing-etx220:v1008;'
#     assert _get_description(multi_vlan_xml, '1200') == 'CUST:ELINE::testing-etx220:v1200'
#     # Wrong port
#     assert _get_description(multi_vlan_xml, '1300') == None
#
#     # .0s have no description - test case where we don't know it's a .0
#     assert _get_description(single_vlan_0_xml, '1201') == None
#
#     expected_1101_desc = 'CUST:DIA:Mark Test@123 main:Quick_Retression:'
#     assert _get_description(single_vlan_xml, '1101') == expected_1101_desc
