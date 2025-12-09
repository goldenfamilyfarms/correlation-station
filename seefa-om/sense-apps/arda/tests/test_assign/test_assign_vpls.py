import pytest

from arda_app.bll.assign import vpls

from arda_app.api import elan_add_vpls

ENDPOINT = "arda/v1/elan_add_vpls"
CID = "21.L1XX.123456..CHTR"


def _exception():
    raise Exception


# @pytest.mark.skip
def test_endpoint(client, monkeypatch):
    # good with Yes
    data = {"cid": CID, "product_name": "EP-LAN (Fiber)", "create_new_elan_instance": "Yes"}
    monkeypatch.setattr(elan_add_vpls, "assign_vpls", lambda *args, **kwargs: "good")
    resp = client.post(ENDPOINT, json=data)
    assert resp.status_code == 200

    # good with No
    data["create_new_elan_instance"] = "No"
    resp = client.post(ENDPOINT, json=data)
    assert resp.status_code == 200

    # missing key
    del data["create_new_elan_instance"]
    resp = client.post(ENDPOINT, json=data)
    assert resp.status_code == 500

    # JSON decode error
    resp = client.post(ENDPOINT, data=b"")
    assert resp.status_code == 500


@pytest.mark.unittest
def test_assign_vpls(monkeypatch):
    # good with existing vrfid in payload
    payload = {
        "cid": "91.L1XX.009706..CHTR",
        "product_name": "EP-LAN (Fiber)",
        "create_new_elan_instance": False,
        "customers_elan_name": "CHTRSE.VRFID.431111.NCDIT K12 RTP2",
        "granite_site_name": "PTBONC39-ITS-NC//1476 ANDREWS STORE RD",
    }

    vpls_result = [
        {"CIRC_PATH_INST_ID": "2051277", "NETWORK_NAME": "CHTRSE.VRFID.431111.NCDIT K12 RTP2", "STATUS": "Live"}
    ]

    monkeypatch.setattr(vpls, "check_vpls", lambda *args, **kwargs: vpls_result)
    monkeypatch.setattr(vpls, "get_network_elements", lambda *args, **kwargs: ["vpls_elements"])
    monkeypatch.setattr(vpls, "live_vpls_check", lambda *args, **kwargs: ["equipment_list"])
    monkeypatch.setattr(vpls, "equipment_check", lambda *args, **kwargs: None)

    network_encap = [
        {
            "properties": {
                "config": {
                    "description": "TRANS:ELAN:NC DIT SCHOOLS:CHTRSE.VRFID.431111.NCDIT K12 RTP2:VPLS431111",
                    "type": "vpls",
                },
                "vlans": [{"vlanId": "none"}],
            }
        }
    ]

    monkeypatch.setattr(vpls, "get_network_info", lambda *args, **kwargs: network_encap)
    monkeypatch.setattr(vpls, "update_network_vlan", lambda *args, **kwargs: None)

    resp = {"pathInstanceId": "2093607"}
    monkeypatch.setattr(vpls, "add_network_link", lambda *args, **kwargs: resp)

    association = [
        {
            "associationName": "EVC ID NUMBER/NETWORK",
            "associationValue": "431111",
            "numberRangeName": "MANUAL ASSIGNMENT RETAIL/CARRIER RANGE 0032",
        }
    ]

    monkeypatch.setattr(vpls, "get_network_association", lambda *args, **kwargs: association)
    monkeypatch.setattr(vpls, "assign_association", lambda *args, **kwargs: "assoc_result")
    monkeypatch.setattr(vpls, "evcid_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(vpls, "add_vrfid_link", lambda *args, **kwargs: None)

    assert vpls.assign_vpls_main(payload) == {
        "customers_elan_name": vpls_result[0]["NETWORK_NAME"],
        "create_new_elan_instance": False,
    }

    # bad without existing vrfid in payload
    payload_bad = {
        "cid": "91.L1XX.009706..CHTR",
        "product_name": "EP-LAN (Fiber)",
        "create_new_elan_instance": False,
        "granite_site_name": "PTBONC39-ITS-NC//1476 ANDREWS STORE RD",
    }

    with pytest.raises(Exception):
        assert vpls.assign_vpls_main(payload_bad) is None

    # bad encap_type not vpls
    network_encap[0]["properties"]["config"]["type"] = "not vpls"

    with pytest.raises(Exception):
        assert vpls.assign_vpls_main(payload) is None

    # bad retstring missing association
    network_encap[0]["properties"]["config"]["type"] = "vpls"
    association2 = {"retString": "retString"}
    monkeypatch.setattr(vpls, "get_network_association", lambda *args, **kwargs: association2)

    with pytest.raises(Exception):
        assert vpls.assign_vpls_main(payload) is None

    # bad no assoc_result
    monkeypatch.setattr(vpls, "get_network_association", lambda *args, **kwargs: association)
    monkeypatch.setattr(vpls, "assign_association", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert vpls.assign_vpls_main(payload) is None

    # add network link not dict
    monkeypatch.setattr(vpls, "add_network_link", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert vpls.assign_vpls_main(payload) is None

    # bad  no vpls instance
    monkeypatch.setattr(vpls, "check_vpls", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert vpls.assign_vpls_main(payload) is None

    # TODO this test logic will get added back once business logic is figured out for new elan creation
    """
    payload2 = {
        "cid": "91.L1XX.009706..CHTR",
        "product_name": "EP-LAN (Fiber)",
        "create_new_elan_instance": True,
        "granite_site_name": "PTBONC39-ITS-NC//1476 ANDREWS STORE RD",
    }

    monkeypatch.setattr(vpls, "get_sitename", lambda *args, **kwargs: None)
    monkeypatch.setattr(vpls, "assign_evc_2", lambda *args, **kwargs: "range_name")

    resp2 = [
        {
            "CIRC_PATH_INST_ID": "2093607",
            "PATH_Z_SITE": "PTBONC39-ITS-NC//1476 ANDREWS STORE RD",
            "EVC_ID": "490987",
        },
        {
            "CIRC_PATH_INST_ID": "2093607",
            "PATH_Z_SITE": "PTBONC39-ITS-NC//1476 ANDREWS STORE RD",
            "EVC_ID": "490987",
        },
    ]

    monkeypatch.setattr(vpls, "get_path_elements_l1", lambda *args, **kwargs: resp2)

    data = {"ntwkInstanceId": "2637960"}

    monkeypatch.setattr(vpls, "create_vpls_network", lambda *args, **kwargs: data)
    monkeypatch.setattr(vpls, "evcid_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(vpls, "add_network_link", lambda *args, **kwargs: {})
    monkeypatch.setattr(vpls, "assign_network_association", lambda *args, **kwargs: {})
    monkeypatch.setattr(vpls, "add_vrfid_link", lambda *args, **kwargs: None)

    assert vpls.assign_vpls(payload2) == ["CHTRSE.VRFID.490987.ITS-NC", True]

    # add_network_link not dict
    monkeypatch.setattr(vpls, "add_network_link", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert vpls.assign_vpls(payload) is None

    # assign_network_association not a dict
    monkeypatch.setattr(vpls, "assign_network_association", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert vpls.assign_vpls(payload) is None

    # create_vpls_network not dict
    # monkeypatch.setattr(vpls, "assign_network_association", lambda *args, **kwargs: {})
    monkeypatch.setattr(vpls, "create_vpls_network", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert vpls.assign_vpls(payload) is None

    # get_path_elements_l1 not a list
    monkeypatch.setattr(vpls, "get_path_elements_l1", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert vpls.assign_vpls(payload) is None

    # assign_network_association not a dict
    monkeypatch.setattr(vpls, "assign_network_association", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert vpls.assign_vpls(payload) is None
    """


@pytest.mark.unittest
def test_check_vpls(monkeypatch):
    # one network cne_instance is True and vrfid_status == "Live"
    monkeypatch.setattr(vpls, "get_network_path", lambda *args, **kwargs: [{"STATUS": "Live"}])

    assert vpls.check_vpls("existing_vrfid", True) == [{"STATUS": "Live"}]

    # one network cne_instance is False and vrfid_status == "Live" with "cust_name"
    result = [{"STATUS": "not live"}]
    monkeypatch.setattr(vpls, "get_network_path", lambda *args, **kwargs: result)
    assert vpls.check_vpls("existing_vrfid", True, "cust_name") == result

    # more than one networks
    monkeypatch.setattr(vpls, "get_network_path", lambda *args, **kwargs: [result, result])

    with pytest.raises(Exception):
        assert vpls.check_vpls("existing_vrfid", True) is None

    # result is dict cne_instance is True
    monkeypatch.setattr(vpls, "get_network_path", lambda *args, **kwargs: {})
    assert vpls.check_vpls("existing_vrfid", True) is None

    # result is dict and cne_instance not True
    with pytest.raises(Exception):
        assert vpls.check_vpls("existing_vrfid", False) is None

    # No existing VPLS instances in granite
    monkeypatch.setattr(vpls, "get_network_path", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert vpls.check_vpls("existing_vrfid", False) is None


@pytest.mark.unittest
def test_get_sitename(monkeypatch):
    # good sitename pop
    vpls_result = iter([None, ["clli-sitename"]])
    monkeypatch.setattr(vpls, "check_vpls", lambda *args, **kwargs: next(vpls_result))
    assert vpls.get_sitename(CID, True, "clli-sitename one/test1/test2") == ["clli-sitename"]

    # good
    monkeypatch.setattr(vpls, "check_vpls", lambda *args, **kwargs: ["clli-sitename"])
    assert vpls.get_sitename(CID, True, "clli-sitename/test1/test2") == ["clli-sitename"]

    # no granite_sitename
    monkeypatch.setattr(
        vpls, "get_circuit_site_info", lambda *args, **kwargs: [{"Z_SITE_NAME": "clli-sitename/test1/test2"}]
    )
    assert vpls.get_sitename(CID, True) == ["clli-sitename"]

    # no granite_sitename KEYERROR failure
    monkeypatch.setattr(vpls, "get_circuit_site_info", lambda *args, **kwargs: [{"SITE_NAME": None}])

    with pytest.raises(Exception):
        assert vpls.get_sitename(CID, True) is None

    # Unable to find VPLS in granite
    monkeypatch.setattr(vpls, "check_vpls", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert vpls.get_sitename(CID, False, "clli-sitename/test1/test2") is None

    # cne instance = true
    assert vpls.get_sitename(CID, True, "clli-sitename/test1/test2") is None


@pytest.mark.unittest
def test_live_vpls_check(monkeypatch):
    # good equipment list
    element = {"ELEMENT_STATUS": "Live", "ELEMENT_NAME": "ELEMENT_NAME"}
    vpls_elements = [element, element]
    equip = {"TID": "TIDCW", "PATH_CATEGORY": "ETHERNET TRANSPORT"}
    monkeypatch.setattr(vpls, "get_path_elements", lambda *args, **kwargs: [equip, equip])
    assert vpls.live_vpls_check(vpls_elements) == [equip, equip]

    # No equipment list
    monkeypatch.setattr(vpls, "get_path_elements", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert vpls.live_vpls_check(vpls_elements) is None


@pytest.mark.unittest
def test_equipment_check(monkeypatch):
    # good
    equipment_list = [{"VENDOR": "VENDOR", "TID": "TID", "ELEMENT_REFERENCE": "ELEMENT_REFERENCE"}]
    result = [{"ATTR_NAME": "NETWORK", "ATTR_VALUE": "ATTR_VALUE"}]
    monkeypatch.setattr(vpls, "get_shelf_udas", lambda *args, **kwargs: result)

    assert vpls.equipment_check(equipment_list) is None

    # vendor is CISCO
    equipment_list[0]["VENDOR"] = "CISCO"

    with pytest.raises(Exception):
        assert vpls.equipment_check(equipment_list) is None


@pytest.mark.unittest
def test_get_network_info(monkeypatch):
    # good
    result = {"result": [{"properties": {"interfaces": [{"config": {"interface": "ge-0/0/1.1200"}}]}}]}
    monkeypatch.setattr(vpls, "onboard_and_exe_cmd", lambda *args, **kwargs: result)

    mdso_list = [{"TID": "12345CW", "CHAN_NAME": "VLAN1200", "LEG_NAME": "LAG200/LAG200", "PORT_ACCESS_ID": "GE-0/0/1"}]
    assert vpls.get_network_info(mdso_list) == []

    mdso_list[0]["LEG_NAME"] = "1"
    assert vpls.get_network_info(mdso_list) == [result["result"][0]]

    # bad network_data
    monkeypatch.setattr(vpls, "onboard_and_exe_cmd", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert vpls.get_network_info(mdso_list) is None

    # network_data not a list
    monkeypatch.setattr(vpls, "onboard_and_exe_cmd", lambda *args, **kwargs: {"result": "bad_result"})

    with pytest.raises(Exception):
        assert vpls.get_network_info(mdso_list) is None


@pytest.mark.unittest
def test_add_network_link(monkeypatch):
    # good
    monkeypatch.setattr(vpls, "put_granite", lambda *args, **kwargs: "Good")
    assert vpls.add_network_link(CID, "234567") == "Good"

    # bad
    monkeypatch.setattr(vpls, "put_granite", lambda *args, **kwargs: _exception())

    with pytest.raises(Exception):
        assert vpls.add_network_link(CID, "234567") is None


@pytest.mark.unittest
def test_evcid_update(monkeypatch):
    # good
    monkeypatch.setattr(vpls, "get_source_mep", lambda *args, **kwargs: [{"NEXT_SOURCE_MEP_ID": "11"}])
    monkeypatch.setattr(vpls, "put_granite", lambda *args, **kwargs: None)

    assert vpls.evcid_update("21.L1XX.006991..TWCC", "evcid") is None

    # bad
    monkeypatch.setattr(vpls, "get_source_mep", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert vpls.evcid_update("21.L1XX.006991..TWCC", "evcid") is None
