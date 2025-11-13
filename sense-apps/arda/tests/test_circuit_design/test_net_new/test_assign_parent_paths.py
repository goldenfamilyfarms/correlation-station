import pytest

from copy import deepcopy
from arda_app.bll.net_new import assign_parent_paths as app
from arda_app.api import assign_parent_paths


CID = "51.L1XX.008342..CHTR"
PRODUCT_NAME = "Wireless Internet Access"

L1_RESP = [
    {
        "PATH_NAME": "test_path_name",
        "PATH_REV": "test_path_rev",
        "CIRC_PATH_INST_ID": "test_circ_path_inst_id",
        "LEG_NAME": "test_leg_name",
        "LEG_INST_ID": "test_leg_inst_id",
        "ELEMENT_NAME": "test.element.QW.ZW",
        "PATH_Z_SITE": "test_path_z_site",
        "A_CLLI": "LBRTNY15",
        "Z_CLLI": "LBRTNY15",
        "A_SITE_REGION": "test_site_region",
        "A_STATE": "test_a_state",
        "A_SITE_NAME": "test_site_name",
        "Z_ADDRESS": "test_z_address",
        "Z_CITY": "test_z_city",
        "Z_STATE": "test_z_state",
        "Z_SITE_NAME": "test_site_name",
        "Z_ZIP": "test_z_zip",
        "Z_SITE_REGION": "test_site_region",
        "CIRCUIT_BANDWIDTH": "100 Mbps",
        "ELEMENT_CATEGORY": "ROUTER",
        "TID": "CW",
        "LEGACY_EQUIP_SOURCE": "",
        "CIRCUIT_NAME": "CIRCUIT_NAME",
    }
]

GCI_RESP = {"AW_CIRCUIT_NAME": "AW_CIRCUIT_NAME", "CW_CID": "CW_CID", "ELEMENT_NAME": "ELEMENT_NAME"}


@pytest.mark.unittest
def test_v1_assign_parent_paths(monkeypatch, client):
    endpoint = "/arda/v1/assign_parent_paths"
    payload = {"service_type": "net_new_no_cj", "product_name": "Carrier E-Access (Fiber)", "cid": CID, "side": "z_side"}

    # normal
    monkeypatch.setattr(
        assign_parent_paths,
        "assign_parent_paths_main",
        lambda payload: {"message": "Parent Paths & Cloud has been successfully added."},
    )
    resp = client.put(endpoint, json=payload)
    assert resp.status_code == 201

    # regression test
    payload["service_type"] = "net_new_cj"
    monkeypatch.setattr(assign_parent_paths, "regression_testing_check", lambda *args, **kwargs: None)
    resp = client.put(endpoint, json=payload)
    assert resp.status_code == 201


@pytest.mark.unittest
def test_add_parent_for_each_child(monkeypatch):
    # bad get_granite
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert app._add_parent_for_each_child(CID, "parent_path_inst_id", 2) is None

    # all good
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: L1_RESP)
    monkeypatch.setattr(app, "_add_parent_path_element", lambda *args, **kwargs: None)
    assert app._add_parent_for_each_child(CID, "parent_path_inst_id", 2) is None


@pytest.mark.unittest
def test_clli_check(monkeypatch):
    # valid
    monkeypatch.setattr(app, "validate_hub_clli", lambda *args, **kwargs: (True, None))
    assert app.clli_check(L1_RESP) is None

    # not valid
    monkeypatch.setattr(app, "validate_hub_clli", lambda *args, **kwargs: (False, None))

    with pytest.raises(Exception):
        assert app.clli_check(L1_RESP) is None


@pytest.mark.unittest
def test_assign_parent_paths_main(monkeypatch):
    # "Wireless Internet Access" or type2 == "Y"
    # get granite error
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        payload = {
            "cid": CID,
            "product_name": PRODUCT_NAME,
            "service_type": "net_new_cj",
            "side": "z_side",
            "path_inst_id": 0,
            "third_party_provided_circuit": "Y",
        }
        assert app.assign_parent_paths_main(payload) is None

    # get granite good
    csip_resp = [{"Z_SITE_REGION": "OFF-NET", "A_SITE_REGION": "OFF-NET"}]
    expected = {"message": "Parent Paths & Cloud has been successfully added."}

    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: L1_RESP)
    monkeypatch.setattr(app, "circuit_site_info_path", lambda *args, **kwargs: csip_resp)
    monkeypatch.setattr(app, "_validate_and_add_parent_paths", lambda *args, **kwargs: None)

    payload = {
        "cid": CID,
        "product_name": PRODUCT_NAME,
        "service_type": "net_new_cj",
        "side": "z_side",
        "path_inst_id": 0,
        "third_party_provided_circuit": "Y",
    }
    assert app.assign_parent_paths_main(payload) == expected

    # Carrier E-Access (Fiber) w/CW_CID
    monkeypatch.setattr(app, "_add_serviceable_shelf_uplink_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "_get_circuit_info", lambda *args, **kwargs: GCI_RESP)
    payload = {
        "cid": CID,
        "product_name": "Carrier E-Access (Fiber)",
        "service_type": "net_new_cj",
        "side": "z_side",
        "path_inst_id": 0,
    }
    assert app.assign_parent_paths_main(payload) == expected

    # Carrier E-Access (Fiber) wo/CW_CID
    gci_resp = deepcopy(GCI_RESP)
    gci_resp.pop("CW_CID")

    monkeypatch.setattr(app, "_get_circuit_info", lambda *args, **kwargs: gci_resp)
    assert app.assign_parent_paths_main(payload) == expected


@pytest.mark.unittest
def test_validate_and_add_parent_paths(monkeypatch):
    # len(csip) > 1 clli good and number of circuits > 1 and is_aw_cid
    # PRI Trunk (Fiber)
    monkeypatch.setattr(app, "_add_parent_path_element", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "_add_parent_for_each_child", lambda *args, **kwargs: None)
    assert (
        app._validate_and_add_parent_paths(
            CID,
            [L1_RESP[0], L1_RESP[0]],
            L1_RESP[0],
            "PRI Trunk (Fiber)",
            is_cw_cid=True,
            is_aw_cid=True,
            num_of_circuits=1,
        )
        is None
    )

    # len(csip) == 1 clli good and number of circuits > 1 and is_aw_cid
    # Wireless Internet Access
    monkeypatch.setattr(app, "_add_parent_network_element", lambda *args, **kwargs: None)
    assert app._validate_and_add_parent_paths(CID, L1_RESP, L1_RESP[0], PRODUCT_NAME, is_aw_cid=True) is None

    # Carrier E-Access and get_path_elements failure
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: L1_RESP)
    monkeypatch.setattr(app, "get_path_elements", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert app._validate_and_add_parent_paths(CID, L1_RESP, L1_RESP[0], "Carrier E-Access") is None

    # not hub_clli and not edna_mpls_in_path and not is_aw_cid
    get_granite = deepcopy(GCI_RESP)
    get_granite["ELEMENT_CATEGORY"] = "ROUTER"
    path_elements = [{"TID": "CW", "VENDOR": "JUNIPER", "ELEMENT_REFERENCE": "10293846", "LEGACY_EQUIP_SOURCE": ""}]

    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: [get_granite])
    monkeypatch.setattr(app, "get_path_elements", lambda *args, **kwargs: path_elements)
    monkeypatch.setattr(app, "edna_mpls_in_path", lambda *args, **kwargs: None)

    monkeypatch.setattr(app, "_edna_check", lambda *args, **kwargs: None)
    monkeypatch.setattr(app, "onboard_and_exe_cmd", lambda *args, **kwargs: {"result": None})
    monkeypatch.setattr(app, "region_network_mapping", lambda *args, **kwargs: "cloud_address")

    monkeypatch.setattr(app, "region_network_mapping", lambda *args, **kwargs: "cloud_address")
    monkeypatch.setattr(app, "circuit_site_info_network", lambda *args, **kwargs: "parent_network_inst_id")
    get_granite["TID"] = "CW"
    get_granite["A_CLLI"] = "hub_clli"
    get_granite["LEGACY_EQUIP_SOURCE"] = "legacy_region"
    L1_RESP[0]["SEQUENCE"] = "2"
    assert (
        app._validate_and_add_parent_paths(CID, L1_RESP, L1_RESP[0], "Carrier E-Access (Fiber)", side="a_side") is None
    )
    del L1_RESP[0]["SEQUENCE"]

    # not hub_clli and not edna_mpls_in_path and is_aw_cid and edna_device
    # Carrier E-Access (Fiber)
    monkeypatch.setattr(app, "onboard_and_exe_cmd", lambda *args, **kwargs: {"result": True})
    assert (
        app._validate_and_add_parent_paths(CID, L1_RESP, L1_RESP[0], "Carrier E-Access (Fiber)", is_aw_cid=True) is None
    )

    # Carrier E-Access
    assert app._validate_and_add_parent_paths(CID, L1_RESP, L1_RESP[0], "Carrier E-Access") is None

    # not hub_clli and not edna_mpls_in_path and is_aw_cid and edna_device
    # Wireless Internet Access
    L1_RESP[0]["MODEL"] = "W1850"
    monkeypatch.setattr(app, "onboard_and_exe_cmd", lambda *args, **kwargs: {"result": True})
    assert app._validate_and_add_parent_paths(CID, L1_RESP, L1_RESP[0], PRODUCT_NAME) is None


@pytest.mark.unittest
def test_get_circuit_info(monkeypatch):
    # bad test missing keys from l1_resp
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: None)

    # bad test - no data in Granite response
    with pytest.raises(Exception):
        assert app._get_circuit_info(CID, side="a_side") is None

    # bad test missing values from l1_resp
    l1_resp = deepcopy(L1_RESP)

    l1_resp[0].pop("PATH_Z_SITE")
    l1_resp[0]["ELEMENT_CATEGORY"] = "ETHERNET TRANSPORT"
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: l1_resp)

    with pytest.raises(Exception):
        assert app._get_circuit_info(CID, side="z_side") is None

    # bad test element name no split()
    l1_resp[0]["ELEMENT_NAME"] = None
    l1_resp[0]["PATH_Z_SITE"] = "VLLJCADF-00813 EMPLOYMENT DEVELOPMENT DEPARTMENT//1440 MARIN ST"

    with pytest.raises(Exception):
        assert app._get_circuit_info(CID, side="z_side") is None

    # bad test element name no in AW, CW, QW, ZW
    l1_resp[0]["ELEMENT_NAME"] = "40001.GE1.SNJUCACL1TW.VLLJCADF1TW"

    with pytest.raises(Exception):
        assert app._get_circuit_info(CID, side="z_side") is None

    # bad test AW multiple paths found
    l1_resp[0]["ELEMENT_NAME"] = "40001.GE1.SNJUCACL1AW.VLLJCADF1ZW"
    granite = iter([l1_resp, [{}, {}]])

    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: next(granite))

    with pytest.raises(Exception):
        assert app._get_circuit_info(CID, side="z_side") is None

    # bad test AW live path single list
    granite = iter([l1_resp, [{"CIRCUIT_STATUS": "Live", "CIRCUIT_NAME": "Test"}]])
    l1_data = {
        "PATH_NAME": "test_path_name",
        "PATH_REV": "test_path_rev",
        "CIRC_PATH_INST_ID": "test_circ_path_inst_id",
        "LEG_NAME": "test_leg_name",
        "LEG_INST_ID": "test_leg_inst_id",
        "ELEMENT_NAME": "40001.GE1.SNJUCACL1AW.VLLJCADF1ZW",
        "A_CLLI": "test",
        "Z_CLLI": "test",
        "A_SITE_REGION": "test_site_region",
        "A_STATE": "test_a_state",
        "A_SITE_NAME": "test_site_name",
        "Z_ADDRESS": "test_z_address",
        "Z_CITY": "test_z_city",
        "Z_STATE": "test_z_state",
        "Z_SITE_NAME": "test-test_site_name",
        "Z_ZIP": "test_z_zip",
        "Z_SITE_REGION": "test_site_region",
        "CIRCUIT_BANDWIDTH": "100 Mbps",
        "ELEMENT_CATEGORY": "ETHERNET TRANSPORT",
        "TID": "CW",
        "LEGACY_EQUIP_SOURCE": "",
        "CIRCUIT_NAME": "CIRCUIT_NAME",
        "MODEL": "W1850",
        "PATH_Z_SITE": "VLLJCADF-00813 EMPLOYMENT DEVELOPMENT DEPARTMENT//1440 MARIN ST",
        "CW_CID": "CW.SNJUCACL1QW",
    }

    with pytest.raises(Exception):
        assert app._get_circuit_info(CID, side="z_side") == l1_data

    # good test QW
    l1_resp[0]["ELEMENT_NAME"] = "40001.GE1.SNJUCACL1QW.VLLJCADF1ZW"
    l1_resp[0]["A_CLLI"] = "test"
    l1_resp[0]["Z_CLLI"] = "test"
    l1_resp[0]["Z_SITE_NAME"] = "test-test_site_name"
    l1_data["ELEMENT_NAME"] = "40001.GE1.SNJUCACL1QW.VLLJCADF1ZW"
    l1_data["CW_CID"] = "CW.SNJUCACL1QW"
    granite = iter([l1_resp, [{}]])

    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: next(granite))

    assert app._get_circuit_info(CID, side="a_side") == l1_data


@pytest.mark.unittest
def test_circuit_site_info_path(monkeypatch):
    # bad test index error granite res
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert app.circuit_site_info_path(CID, True) is None

    # bad test full info = False and length res > 2
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: [{}, {}, {}])

    with pytest.raises(Exception):
        assert app.circuit_site_info_path(CID, False) is None

    # bad test bW RF missing expected values
    res = [
        {
            "PATH_NAME": "test_path_name",
            "PATH_REV": "test_path_rev",
            "CIRC_PATH_INST_ID": "test_circ_path_inst_id",
            "LEG_NAME": "test_leg_name",
            "LEG_INST_ID": "test_leg_inst_id",
            "ELEMENT_NAME": "40001.GE1.SNJUCACL1AW.VLLJCADF1ZW",
            "A_CLLI": "LBRTNY15",
            "Z_CLLI": "LBRTNY15",
            "A_SITE_REGION": "test_site_region",
            "A_STATE": "test_a_state",
            "A_SITE_NAME": "test_site_name",
            "Z_ADDRESS": "test_z_address",
            "Z_CITY": "test_z_city",
            "Z_STATE": "test_z_state",
            "Z_SITE_NAME": "test_site_name",
            "Z_ZIP": "test_z_zip",
            "Z_SITE_REGION": "test_site_region",
            "CIRCUIT_BANDWIDTH": "RF",
            "CIRCUIT_STATUS": "Live",
        }
    ]

    res[0].pop("CIRC_PATH_INST_ID")

    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: res)

    with pytest.raises(Exception):
        assert app.circuit_site_info_path(CID, True) is None

    # good test
    res[0]["CIRC_PATH_INST_ID"] = "test_circ_path_inst_id"

    csip = [
        {
            "CIRC_PATH_INST_ID": "test_circ_path_inst_id",
            "A_SITE_REGION": "test_site_region",
            "Z_SITE_REGION": "test_site_region",
            "Z_ADDRESS": "test_z_address",
            "Z_CITY": "test_z_city",
            "Z_STATE": "test_z_state",
            "Z_ZIP": "test_z_zip",
            "A_STATE": "test_z_state",
            "A_SITE_NAME": "test_site_name",
            "A_CLLI": "LBRTNY15",
            "Z_CLLI": "LBRTNY15",
        }
    ]
    assert app.circuit_site_info_path(CID, True) == csip


@pytest.mark.unittest
def test_add_parent_path_element(monkeypatch):
    # bad test put granite data equal None
    appe_params = deepcopy(L1_RESP[0])
    appe_params["PARENT_PATH_INST_ID"] = "1234567"
    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: [{}])

    with pytest.raises(Exception):
        assert app._add_parent_path_element(appe_params) is None

    # bad test retstring not equal to path updated
    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: {"retString": "NOT UPDATED"})

    with pytest.raises(Exception):
        assert app._add_parent_path_element(appe_params) is None

    # good test
    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: {"retString": "Path Updated"})
    assert app._add_parent_path_element(appe_params) is None


@pytest.mark.unittest
def test_circuit_site_info_network(monkeypatch):
    # bad test granite res equal None
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert app.circuit_site_info_network("1128") is None

    # bad test missing key circuit_path_inst_id
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: [{"NO_CIRC_PATH_INST_ID": ""}])

    with pytest.raises(Exception):
        assert app.circuit_site_info_network("1128") is None

    # good test
    res = [{"CIRC_PATH_INST_ID": "123890"}]
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: res)

    assert app.circuit_site_info_network("1128") == res[0]["CIRC_PATH_INST_ID"]


@pytest.mark.unittest
def test_add_parent_network_element(monkeypatch):
    # bad test data not a dictionary type
    apne_params = deepcopy(L1_RESP[0])
    apne_params["PARENT_NETWORK_INST_ID"] = "1234567"

    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: [{}])

    with pytest.raises(Exception):
        assert app._add_parent_network_element(apne_params, a_site=False) is None

    # bad test retString not equal to path updated
    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: {"retString": "NOT UPDATED"})

    with pytest.raises(Exception):
        assert app._add_parent_network_element(apne_params, a_site=True) is None

    # good test
    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: {"retString": "Path Updated"})
    assert app._add_parent_network_element(apne_params, a_site=True) is None


@pytest.mark.unittest
def test_put_parent_path(monkeypatch):
    # good test
    monkeypatch.setattr(app, "put_granite", lambda *args, **kwargs: None)
    assert app._put_parent_path("cid", "path_rev", "path_leg", "parent_path_id", "1") is None


@pytest.mark.unittest
def test_add_serviceable_shelf_uplink_path(monkeypatch):
    # bad test No parent path found for TID
    element = {"TID": "TID", "PATH_REV": "PATH_REV", "LEG_NAME": "1", "SEQUENCE": "2"}
    path_elements = [element]

    monkeypatch.setattr(app, "get_path_elements", lambda *args, **kwargs: path_elements)
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert app._add_serviceable_shelf_uplink_path(CID, epl=True, side="z_side") is None

    # error len(parent_paths) > 2
    path = {
        "CIRCUIT_STATUS": "Live",
        "CIRC_PATH_INST_ID": "12345",
        "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        "CIRCUIT_NAME": "CIRCUIT_NAME_TID",
    }
    parent_paths = [path, path, path]

    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: parent_paths)
    monkeypatch.setattr(app, "_put_parent_path", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        assert app._add_serviceable_shelf_uplink_path(CID, epl=True, side="a_side") is None

    # error no parent_paths
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: [])

    with pytest.raises(Exception):
        assert app._add_serviceable_shelf_uplink_path(CID, epl=False, side="z_side") is None

    # good test parent paths == 1
    parent_paths = [path]
    monkeypatch.setattr(app, "get_granite", lambda *args, **kwargs: parent_paths)
    monkeypatch.setattr(app, "_put_parent_path", lambda *args, **kwargs: None)

    assert app._add_serviceable_shelf_uplink_path(CID, epl=False, side="z_side") is None

    # len(parent_paths) == 2 0-Live 1-Designed
    path1 = {
        "CIRCUIT_STATUS": "Designed",
        "CIRC_PATH_INST_ID": "12345",
        "SERVICE_TYPE": "INT-ACCESS TO PREM TRANSPORT",
        "CIRCUIT_NAME": "CIRCUIT_NAME_TID",
    }
    parent_paths = [path, path1]

    assert app._add_serviceable_shelf_uplink_path(CID, epl=False, side="z_side") is None

    # len(parent_paths) == 2 0-Designed 1-Live
    parent_paths = [path1, path]

    assert app._add_serviceable_shelf_uplink_path(CID, epl=False, side="z_side") is None

    # error Parent path for TID: {shelf_tid} is not in Live or Designed status
    path["CIRCUIT_STATUS"] = "Planned"
    path1 = path

    with pytest.raises(Exception):
        assert app._add_serviceable_shelf_uplink_path(CID, epl=False, side="z_side") is None
