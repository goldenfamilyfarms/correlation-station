import pytest

from pytest import raises
import requests

import arda_app.bll.logical_change as lc

from common_sense.common.errors import AbortException


# Raise an error
def do_raise(ex):
    raise ex


@pytest.mark.unittest
def test_logical_change_main(monkeypatch):
    payload = {
        "service_type": "net_new_cj",
        "product_name": "Fiber Internet Access",
        "cid": "cid",
        "engineering_id": "engineering_id",
        "engineering_name": "engineering_name",
        "class_of_service_needed": "yes",
        "class_of_service_type": "GOLD",
        "change_reason": "Upgrading Service",
        "3rd_party_provided_circuit": "Y",
        "spectrum_primary_enni": "test_enni_primary",
        "spectrum_secondary_enni": "test_enni_secondary",
    }

    result = {
        "circ_path_inst_id": "circ_path_inst_id",
        "engineering_job_type": "Logical Change",
        "maintenance_window_needed": "No",
        "message": "Logical Change updated successfully",
    }

    payload_model = lc.LogicalChangePayloadModel(**payload)

    # bad service type abort
    with raises(AbortException):
        assert lc.logical_change_main(payload_model) is None

    # bad product name abort
    payload_model.service_type = "change_logical"

    with raises(AbortException):
        assert lc.logical_change_main(payload_model) is None

    # bad 3rd party provided circuit value abort
    payload_model.product_name = "Carrier E-Access (Fiber)"

    with raises(AbortException):
        assert lc.logical_change_main(payload_model) is None

    # bad change reason abort
    payload_model.third_party_provided_circuit = "N"
    payload_model.change_reason = "no clue"

    with raises(AbortException):
        assert lc.logical_change_main(payload_model) is None

    # good test carrier e access
    payload_model.change_reason = "Upgrading Service"

    monkeypatch.setattr(lc, "check_enni", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "logical_change_process", lambda *args, **kwargs: "circ_path_inst_id")

    assert lc.logical_change_main(payload_model) == result

    # good test nni_rehome and product_name != "Carrier CTBH"
    monkeypatch.setattr(lc, "check_enni", lambda *args, **kwargs: "rehome")
    monkeypatch.setattr(lc, "bw_upgrade_assign_gsip", lambda *args, **kwargs: None)
    payload_model.class_of_service_type = None
    result["maintenance_window_needed"] = "Yes - No Hub Impact - Inflight Customer Only Impacted"

    assert lc.logical_change_main(payload_model) == result

    # good test check_vlan
    monkeypatch.setattr(lc, "check_vlan", lambda *args, **kwargs: "vlan")

    assert lc.logical_change_main(payload_model) == result

    # bad test nni_rehome and product_name == "Carrier CTBH"
    payload_model.product_name = "Carrier CTBH"

    with raises(AbortException):
        assert lc.logical_change_main(payload_model) is None

    # good test hosted voice
    payload_model.product_name = "Hosted Voice - (Fiber)"
    monkeypatch.setattr(lc, "hosted_voice_upgrade", lambda *args, **kwargs: "circ_path_inst_id")
    result["maintenance_window_needed"] = "No"

    assert lc.logical_change_main(payload_model) == result


@pytest.mark.unittest
def test_get_circuit_path_inst_id(monkeypatch):
    # good test
    monkeypatch.setattr(lc, "get_circuit_site_info", lambda *args, **kwargs: [{"CIRC_PATH_INST_ID": "123456"}])

    assert lc.get_circuit_path_inst_id("test_cid") == "123456"

    # bad test abort keyerror/ index error
    monkeypatch.setattr(lc, "get_circuit_site_info", lambda *args, **kwargs: {})

    with raises(AbortException):
        assert lc.get_circuit_path_inst_id("test_cid") is None


@pytest.mark.unittest
def test_get_granite_data(monkeypatch):
    # good test
    monkeypatch.setattr(
        lc,
        "get_granite",
        lambda *args, **kwargs: [{"ATTR_NAME": "CLASS OF SERVICE", "ATTR_VALUE": "attr", "REV_NBR": "1"}],
    )

    assert lc.get_granite_data("test_cid", "123456") == ("attr", "1")

    # bad test abort no class of service found
    monkeypatch.setattr(
        lc, "get_granite", lambda *args, **kwargs: [{"ATTR_NAME": "TEST_UDA", "ATTR_VALUE": "attr", "REV_NBR": "1"}]
    )

    with raises(AbortException):
        assert lc.get_granite_data("test_cid", "123456") is None


@pytest.mark.unittest
def test_update_class_of_service_type(monkeypatch):
    # good test
    monkeypatch.setattr(lc, "put_granite", lambda *args, **kwargs: None)

    assert lc.update_class_of_service_type("cid", "rev_instance", "class_of_service_type", "engineering_name") is None


@pytest.mark.unittest
def test_logical_change_process(monkeypatch):
    # bad test abort salesforce cos is None
    body = {
        "product_name": "EP-LAN (Fiber)",
        "cid": "cid",
        "engineering_name": "engineering_name",
        "class_of_service_needed": "yes",
    }

    monkeypatch.setattr(lc, "get_circuit_path_inst_id", lambda *args, **kwargs: "45678")
    monkeypatch.setattr(lc, "get_granite_data", lambda *args, **kwargs: ("GOLD METRO", "1"))

    with raises(AbortException):
        assert lc.logical_change_process(body, None, None, "", "") is None

    # bad test abort granite cos and salesfoce cos are the same value
    body["class_of_service_type"] = "GOLD"

    with raises(AbortException):
        assert lc.logical_change_process(body, None, None, "", "") is None

    # good test
    rev_instance = "09876"
    monkeypatch.setattr(lc, "get_granite_data", lambda *args, **kwargs: ("SILVER METRO", "1"))
    monkeypatch.setattr(lc, "_granite_create_circuit_revision", lambda *args, **kwargs: (None, rev_instance, None))
    monkeypatch.setattr(lc, "nni_rehome_change", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "change_vlan", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "add_association", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "update_class_of_service_type", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "bw_upgrade_assign_gsip", lambda *args, **kwargs: None)

    assert lc.logical_change_process(body, "nni_rehome", "vlan_change", "enni", "vlan") == rev_instance


@pytest.mark.unittest
def test_hosted_voice_upgrade(monkeypatch):
    # bad test abort no IPV4_ASSIGNED_SUBNETS and IPV4_ASSIGNED_GATEWAY
    body = {
        "product_name": "Hosted Voice - (Fiber)",
        "cid": "cid",
        "engineering_name": "engineering_name",
        "class_of_service_needed": "yes",
    }

    monkeypatch.setattr(lc, "get_circuit_path_inst_id", lambda *args, **kwargs: "45678")
    monkeypatch.setattr(lc, "bw_upgrade_assign_gsip", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        lc,
        "get_path_elements_l1",
        lambda *args, **kwargs: [{"IPV4_ASSIGNED_SUBNETS": None, "IPV4_ASSIGNED_GATEWAY": None}],
    )

    with raises(AbortException):
        assert lc.hosted_voice_upgrade(body) is None

    # good test
    monkeypatch.setattr(
        lc,
        "get_path_elements_l1",
        lambda *args, **kwargs: [
            {"IPV4_ASSIGNED_SUBNETS": "12.22.11.245/31", "IPV4_ASSIGNED_GATEWAY": "12.22.11.246/31"}
        ],
    )
    monkeypatch.setattr(lc, "granite_assignment", lambda *args, **kwargs: None)

    assert lc.hosted_voice_upgrade(body) == "45678"

    # bad test - get_path_elements_l1 returns an empty dict
    monkeypatch.setattr(lc, "get_path_elements_l1", lambda *args, **kwargs: {})

    with raises(AbortException):
        assert lc.hosted_voice_upgrade(body) is None


@pytest.mark.unittest
def test_check_enni(monkeypatch):
    # bad test primary enni does not match granite
    enni_list = iter(["primary_enni", "secondary_enni"])

    monkeypatch.setattr(lc, "_validate_enni", lambda *args, **kwargs: next(enni_list))
    monkeypatch.setattr(
        lc, "get_path_elements_l1", lambda *args, **kwargs: [{"ELEMENT_NAME": "enni1"}, {"ELEMENT_NAME": "enni2"}]
    )

    assert (
        lc.check_enni("cid", "primary_enni", "sesondary_enni")
        == "Spectrum Primary E-NNI provided on EPR does not match Granite"
    )

    # bad test secondary enni does not match granite
    enni_list = iter(["primary_enni", "secondary_enni"])

    monkeypatch.setattr(lc, "_validate_enni", lambda *args, **kwargs: next(enni_list))
    monkeypatch.setattr(
        lc, "get_path_elements_l1", lambda *args, **kwargs: [{"ELEMENT_NAME": "primary_enni"}, {"ELEMENT_NAME": "enni2"}]
    )

    assert (
        lc.check_enni("cid", "primary_enni", "sesondary_enni")
        == "Spectrum Secondary E-NNI provided on EPR does not match Granite"
    )

    # good test
    enni_list = iter(["primary_enni", "secondary_enni"])

    monkeypatch.setattr(lc, "_validate_enni", lambda *args, **kwargs: next(enni_list))
    monkeypatch.setattr(
        lc,
        "get_path_elements_l1",
        lambda *args, **kwargs: [{"ELEMENT_NAME": "primary_enni"}, {"ELEMENT_NAME": "secondary_enni"}],
    )
    assert lc.check_enni("cid", "primary_enni", "sesondary_enni") is None


@pytest.mark.unittest
def test_validate_enni():
    # bad test E-NNI does not match CID or Path format
    with raises(AbortException):
        assert lc._validate_enni("primary_enni", False) is None

    # good test return enni with bad enni replaced/removed
    assert lc._validate_enni("21.KGFD.123456..CHTR na", False) == "21.KGFD.123456..CHTR"

    # good test return "" found bad enni
    assert lc._validate_enni("na", False) == ""


@pytest.mark.unittest
def test_check_vlan(monkeypatch):
    # bad test abort primary vlan does not match granite
    monkeypatch.setattr(lc, "get_path_elements_l1", lambda *args, **kwargs: [{"CHAN_NAME": "1"}, {"CHAN_NAME": "2"}])

    assert lc.check_vlan("cid", "VLAN3", "VLAN4") == "Spectrum Primary VLAN provided on EPR does not match Granite"

    # bad test abort secondary vlan does not match granite
    assert lc.check_vlan("cid", "VLAN1", "VLAN4") == "Spectrum Secondary VLAN provided on EPR does not match Granite"

    # good test
    assert lc.check_vlan("cid", "VLAN1", "VLAN2") is None


@pytest.mark.unittest
def test_nni_rehome_change(monkeypatch):
    # good test
    monkeypatch.setattr(lc, "find_and_remove_enni", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "assign_enni_main", lambda *args, **kwargs: None)
    monkeypatch.setattr(lc, "update_enni_vlan", lambda *args, **kwargs: None)

    assert lc.nni_rehome_change("cid", "test_nni", "123456") is None


@pytest.mark.unittest
def test_update_enni_vlan(monkeypatch):
    # bad test - get_path_elements_inst_l1 does not return a list
    elements = {}
    monkeypatch.setattr(lc, "get_path_elements_inst_l1", lambda *args, **kwargs: elements)

    with raises(AbortException):
        assert lc.update_enni_vlan("enni", "rev_inst", "test_cid") is None

    # bad test - elements does not contain an element with ELEMENT_TYPE == PATH
    elements = [
        {"ELEMENT_NAME": "enni", "ELEMENT_REFERENCE": "5678", "CHAN_INST_ID": "4321"},
        {"ELEMENT_NAME": "port", "ELEMENT_TYPE": "PORT", "PORT_ROLE": "ENNI", "PORT_INST_ID": "1234"},
    ]
    monkeypatch.setattr(lc, "put_granite", lambda *args, **kwargs: None)

    with raises(AbortException):
        assert lc.update_enni_vlan("enni", "rev_inst", "test_cid") is None

    # good test
    elements.append({"ELEMENT_NAME": "vlan", "ELEMENT_TYPE": "PATH", "CHAN_NAME": "VLAN1100"})

    assert lc.update_enni_vlan("enni", "rev_inst", "test_cid") is None


@pytest.mark.unittest
def test_find_and_remove_enni(monkeypatch):
    # bad test - len(enni_list) == 1 and len(tid_sequence) != 1
    elements = [
        {"ELEMENT_NAME": "20001.ge10.test_cid.test_cid", "ELEMENT_TYPE": "PATH", "LEG_INST_ID": "1234", "SEQUENCE": "2"},
        {"ELEMENT_NAME": "port/99.999.999", "ELEMENT_TYPE": "PORT", "PORT_ROLE": "ENNI", "SEQUENCE": "1234"},
    ]
    monkeypatch.setattr(lc, "get_path_elements_inst_l1", lambda *args, **kwargs: elements)

    with raises(AbortException):
        assert lc.find_and_remove_enni("path", "path_instid") is None

    # bad test - try and except abort ConnectionError
    elements[0]["ELEMENT_NAME"] = "test_cid.CHTR"
    monkeypatch.setattr(lc, "put_granite", lambda *args, **kwargs: do_raise(requests.exceptions.ConnectionError()))

    with raises(AbortException):
        assert lc.find_and_remove_enni("path", "path_instid") is None

    # good test
    elements[0]["ELEMENT_NAME"] = "20001.ge10.test_cid.test_cid"
    elements[1]["ELEMENT_NAME"] = "test_cid/99.999.999"
    monkeypatch.setattr(lc, "put_granite", lambda *args, **kwargs: None)

    assert lc.find_and_remove_enni("path", "path_instid") is None


@pytest.mark.unittest
def test_add_association(monkeypatch):
    # bad test - abort for dict with retString
    monkeypatch.setattr(lc, "get_path_association", lambda *args, **kwargs: {"retString": "Unable to do the thing"})

    with raises(AbortException):
        assert lc.add_association("cid", "path_instid", "Carrier E-Access (Fiber)", "123456") is None

    # bad test - abort no assoc_result
    association = [{"associationValue": "Value", "associationName": "Name", "numberRangeName": "Rangename"}]
    monkeypatch.setattr(lc, "get_path_association", lambda *args, **kwargs: association)
    monkeypatch.setattr(lc, "assign_association", lambda *args, **kwargs: None)

    with raises(AbortException):
        assert lc.add_association("cid", "path_instid", "Carrier E-Access (Fiber)", "123456") is None

    # good test
    monkeypatch.setattr(lc, "assign_association", lambda *args, **kwargs: "assoc_result")
    monkeypatch.setattr(lc, "add_vrfid_link", lambda *args, **kwargs: None)

    assert lc.add_association("cid", "path_instid", "EP-LAN (Fiber)", "123456") is None


@pytest.mark.unittest
def test_change_vlan(monkeypatch):
    # good test
    monkeypatch.setattr(lc, "vlan_reservation_main", lambda *args, **kwargs: None)
    assert lc.change_vlan("cid", "prod_name", "vlan", "path_instid") is None


@pytest.mark.unittest
def test_check_circuit_revisions():
    # bad test - abort no path_elements
    path_elements = {}
    with raises(AbortException):
        assert lc.check_circuit_revisions(path_elements)

    # bad test - abort multiple revisions found
    path_elements = [{"CIRC_PATH_INST_ID": "12345"}, {"CIRC_PATH_INST_ID": "67890"}]
    with raises(AbortException):
        assert lc.check_circuit_revisions(path_elements)

    # good test
    path_elements = [{"CIRC_PATH_INST_ID": "12345"}, {"CIRC_PATH_INST_ID": "12345"}, {"CIRC_PATH_INST_ID": "12345"}]
    assert lc.check_circuit_revisions(path_elements) is None
