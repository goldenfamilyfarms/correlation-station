# import json
#
# import pytest

# from palantir_app.common import validators

#
# from palantir import ipv4_check, port_check, vlan_check, validate
# from palantir import InvalidUsage
#
# # ------------------------------
# # Test validators and unit tests
# # ------------------------------

# def test_ip_check():
#     """Tests for ip_check fn doesn't raise errors
#
#     Function raises exceptions if IP address is bad, otherwise returns `None`
#     """
#     assert ipv4_check('192.168.1.1') == None
#     assert ipv4_check('0.0.0.0') == None
#
#     with pytest.raises(Exception):
#         ipv4_check('999.999.999.999')
#         ipv4_check('6a:00:01:03:3a:b0')
#
#
# def test_port_check():
#     """Test that the port description describes *physical* ports,
#     *not* TCP/UDP ports
#     """
#     assert port_check("ge-1/0/2") == "ge-1/0/2"
#     assert port_check("SE-0/0/9") == "se-0/0/9"
#     assert port_check("GE-2/7/1") == "ge-2/7/1"
#     assert port_check("GE-10/1/2") == "ge-10/1/2"
#     assert port_check("GE-10/10/101") == "ge-10/10/101"
#     assert port_check("  GE-2/9/2 ") == "ge-2/9/2"
#
#     with pytest.raises(InvalidUsage):
#         port_check('4095')
#
#
# def test_vlan_check():
#     with pytest.raises(ValueError) as err:
#         vlan_check('VLANabba')
#     assert 'vlan must be an integer or VLANXXXX' in str(err.value)
#
#     with pytest.raises(ValueError) as err2:
#         vlan_check('VLAN9000')
#     assert 'vlan must contain an integer in the range' in str(err2.value)
#
#     # Functions raise exceptions if anything is wrong, otherwise return `None`
#     assert vlan_check('VLAN2094') == '2094'
#     assert vlan_check('4094') == '4094'
#     assert vlan_check('    VLAN2094') == '2094'
#     assert vlan_check('  VLAN 801 ') == '801'
#
#
# def test_validate_returns_json_obj(single_mx_post, sample_bad_json, irregular_post):
#     """Test that the `validate` fn returns a python data structure"""
#
#     # test with good json
#     expected_dict = single_mx_post.copy()
#     expected_dict = expected_dict.pop()
#     new_zside = expected_dict.pop('zSide')
#     new_zside.update({'vlan': '1199'})
#     expected_dict.update({'zSide': new_zside})
#
#     assert validate(json.dumps(single_mx_post)) == [expected_dict]
#
#     expected_irregular = [{'transactionID': '999',
#                            'zSide': {
#                                'ip': '65.189.178.70',
#                                'port': 'ge-10/1/2',
#                                'vlan': '1300'},
#                            'aSide': {
#                                'ip': None,
#                                'port': None, 'vlan': None}
#                            }]
#
#     assert validate(irregular_post) == expected_irregular
#
#
# def test_missing_top_level_fields(single_mx_post):
#     """Test that we get the appropriate error if we leave out
#     elements from the JSON data structure
#     """
#     # list
#     no_trans_dict = single_mx_post.copy()
#     # inner dict
#     no_trans_dict = no_trans_dict.pop()
#     no_trans_dict.pop('transactionID')
#
#     with pytest.raises(InvalidUsage):
#         validate(json.dumps([no_trans_dict]))
#
#     no_zside = single_mx_post.copy()
#     no_zside = no_zside.pop()
#     no_zside.pop('zSide')
#
#     with pytest.raises(InvalidUsage):
#         validate(json.dumps([no_zside]))
#
#     no_aside = single_mx_post.copy()
#     no_aside = no_aside.pop()
#     no_aside.pop('aSide')
#
#     with pytest.raises(InvalidUsage):
#         validate(json.dumps([no_aside]))
