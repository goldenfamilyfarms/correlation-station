from copy import deepcopy

import pytest

from arda_app.api import pick_sova_wo as psw

from arda_app.bll import nova_to_sova as nts

PAYLOAD = {
    "prism_id": "4453191",
    "related_eprs": [
        {
            "engineering_name": "ENG-03806752",
            "WO": "WO000001192857",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
        {
            "engineering_name": "ENG-03806765",
            "WO": "WO000001192858",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
        {
            "engineering_name": "ENG-03802265",
            "WO": "WO000001192859",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
        {
            "engineering_name": "ENG-02512265",
            "WO": "WO000001192860",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
    ],
}

EPR = {
    "engineering_name": "ENG-03806752",
    "WO": "WO0000011928603",
    "submitted_date": "",
    "submitted_by": "0051W000004cV9LQAU",
    "complete_date": "",
    "status": "Open",
}

RESULT = {
    "prism_id": "4453191",
    "main_epr": {
        "engineering_name": "ENG-03806752",
        "WO": "WO000001192857",
        "submitted_date": "",
        "submitted_by": "0051W000004cV9LQAU",
        "complete_date": "",
        "status": "Open",
    },
    "related_eprs": [
        {
            "engineering_name": "ENG-03806765",
            "WO": "WO000001192857",
            "circuit_design_notes": "WO000001192858 has a status of Open & was not chosen. Please close out in remedy.",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
        {
            "engineering_name": "ENG-03802265",
            "WO": "WO000001192857",
            "circuit_design_notes": "WO000001192859 has a status of Open & was not chosen. Please close out in remedy.",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
        {
            "engineering_name": "ENG-02512265",
            "WO": "WO000001192857",
            "circuit_design_notes": "WO000001192860 has a status of Open & was not chosen. Please close out in remedy.",
            "submitted_date": "",
            "submitted_by": "0051W000004cV9LQAU",
            "complete_date": "",
            "status": "Open",
        },
    ],
}


@pytest.mark.unittest
def test_v1_pick_sova_wo(client, monkeypatch):
    endpoint = "/arda/v1/pick_sova_wo"

    # all good
    monkeypatch.setattr(psw, "wo_main", lambda *args, **kwargs: EPR)
    resp = client.post(endpoint, json=PAYLOAD)
    assert resp.status_code == 200

    # missing field
    test_payload = deepcopy(PAYLOAD)
    test_payload.pop("prism_id")
    resp = client.post(endpoint, json=test_payload)
    assert resp.status_code == 500

    resp = client.post(endpoint, json="ab1")
    assert resp.status_code == 500


@pytest.mark.unittest
def test_wo_main(monkeypatch):
    payload = deepcopy(PAYLOAD)

    # all compare_wo match
    monkeypatch.setattr(nts, "compare_wo", lambda *args, **kwargs: (payload["related_eprs"][0], None))
    assert nts.wo_main(payload) == RESULT

    # no compare_wo match
    # len(wo_info) == 1
    monkeypatch.setattr(nts, "compare_wo", lambda *args, **kwargs: (None, payload["related_eprs"]))
    monkeypatch.setattr(nts, "get_wo_info", lambda *args, **kwargs: [payload["related_eprs"][0]])
    assert nts.wo_main(payload) == RESULT

    # compare_date not Bool
    monkeypatch.setattr(nts, "get_wo_info", lambda *args, **kwargs: [])
    monkeypatch.setattr(nts, "compare_date", lambda *args, **kwargs: payload["related_eprs"][0])
    assert nts.wo_main(payload) == RESULT

    # compare_date True
    # 1 rejected
    payload = deepcopy(PAYLOAD)
    payload["related_eprs"][1]["status"] = "rejected"

    monkeypatch.setattr(nts, "get_wo_info", lambda *args, **kwargs: payload["related_eprs"])
    monkeypatch.setattr(nts, "compare_date", lambda *args, **kwargs: True)

    payload = deepcopy(PAYLOAD)
    payload["related_eprs"] = payload["related_eprs"][:3]
    payload["related_eprs"][0]["status"] = "rejected"

    res = deepcopy(RESULT)
    res["related_eprs"] = res["related_eprs"][:2]

    note2 = "Automation: Unsupported Scenario - Investigation Required"
    note3 = "Main EPR that was chosen has a status of rejected. Please investigate"

    res["main_epr"]["status"] = "rejected"
    res["main_epr"]["circuit_design_notes"] = note3
    res["main_epr"]["isp_request_issue_flags"] = note2

    res["related_eprs"][0]["status"] = "rejected"
    res["related_eprs"][0]["circuit_design_notes"] = note3
    res["related_eprs"][0]["isp_request_issue_flags"] = note2

    res["related_eprs"][1]["status"] = "rejected"
    res["related_eprs"][1]["circuit_design_notes"] = note3
    res["related_eprs"][1]["isp_request_issue_flags"] = note2

    assert nts.wo_main(payload) == res


@pytest.mark.unittest
def test_compare_wo():
    # good match
    wo_match_payload = deepcopy(PAYLOAD)

    for epr in wo_match_payload["related_eprs"]:
        epr["WO"] = "WO000001192860"

    assert nts.compare_wo(wo_match_payload["related_eprs"]) == (wo_match_payload["related_eprs"][0], None)

    # bad match
    wo_mismatch_payload = deepcopy(PAYLOAD)
    wo_mismatch_payload["related_eprs"][0]["WO"] = "different"
    related_eprs = wo_mismatch_payload["related_eprs"]
    assert nts.compare_wo(related_eprs) == (None, wo_mismatch_payload["related_eprs"])


@pytest.mark.unittest
def test_compare_date():
    # good match
    assert nts.compare_date(PAYLOAD["related_eprs"]) is True

    # bad match
    date_mismatch_payload = deepcopy(PAYLOAD)
    date_mismatch_payload["related_eprs"][0]["submitted_date"] = "2023-10-31"
    related_eprs = date_mismatch_payload["related_eprs"]
    assert nts.compare_date(related_eprs) == date_mismatch_payload["related_eprs"][0]

    # good match submitted date extended(H:M:S)
    date_mismatch_payload = deepcopy(PAYLOAD)
    date_mismatch_payload["related_eprs"][0]["submitted_date"] = "2023-10-31T10:20:33"
    related_eprs = date_mismatch_payload["related_eprs"]
    assert nts.compare_date(related_eprs) == date_mismatch_payload["related_eprs"][0]


@pytest.mark.unittest
def test_get_wo_info(monkeypatch):
    # abort
    with pytest.raises(Exception):
        assert nts.get_wo_info([]) is None

    # all good
    monkeypatch.setattr(nts, "get_remedy_wo", lambda *args, **kwargs: "test")
    assert nts.get_wo_info([EPR]) == ["test"]


@pytest.mark.unittest
def test_get_remedy_wo(monkeypatch):
    response = """<ns0:WO_Target_Wavelength>1561.42</ns0:WO_Target_Wavelength>\\n
        <ns0:WO_Status>Closed</ns0:WO_Status>\\n
        <ns0:WO_PE_Device>NYCLNYRG5QW/000.0000.000.00/SWT#1</ns0:WO_PE_Device>\\n
        <ns0:WO_Completed_Date>2022-11-26T13:36:06-06:00</ns0:WO_Completed_Date>\\n"""

    class MockRemedyTicket:
        def __init__(self, resp):
            self.resp = resp

        def get_wo_info(self, *args):
            return self.resp

    # all good
    payload = deepcopy(PAYLOAD)
    mockremedy = MockRemedyTicket(response)
    monkeypatch.setattr(nts, "RemedyTicket", lambda *args, **kwargs: mockremedy)

    assert nts.get_remedy_wo(payload["related_eprs"][0]) == {
        "WO": "WO000001192857",
        "engineering_name": "ENG-03806752",
        "ftp_assignment": "",
        "hub_clli": "NYCLNYRG",
        "status": "Closed",
        "submitted_by": "0051W000004cV9LQAU",
        "submitted_date": "",
        "complete_date": "2022-11-26T13:36:06-06:00",
        "wavelength": "1561.42",
    }

    # not good
    mockremedy1 = MockRemedyTicket(None)
    monkeypatch.setattr(nts, "RemedyTicket", lambda *args, **kwargs: mockremedy1)
    assert nts.get_remedy_wo(payload["related_eprs"][0]) is None


@pytest.mark.unittest
def test_compare_fields():
    epr = {"ftp_assignment": "ftp_assignment", "hub_clli": "hub_clli", "wavelength": "wavelength"}
    epr1 = {"ftp_assignment": "ftp_assignment", "hub_clli": "hub_clli", "wavelength": "wavelength2"}

    # good match
    wo_info = [epr, epr]
    assert nts.compare_fields(wo_info) == epr

    # bad match
    wo_info1 = [epr, epr1]
    assert nts.compare_fields(wo_info1) is None


@pytest.mark.unittest
def test_update_eprs():
    # epr_status == "Open" and epr["WO"]
    payload = deepcopy(PAYLOAD)
    payload["related_eprs"][0]["engineering_name"]
    related_eprs = [
        x for x in payload["related_eprs"] if x["engineering_name"] != payload["related_eprs"][0]["engineering_name"]
    ]
    result = {"prism_id": "4453191", "main_epr": payload["related_eprs"][0], "related_eprs": related_eprs}
    assert nts.update_eprs(payload["related_eprs"][0], related_eprs, "4453191") == result


@pytest.mark.unittest
def test_remove_epr_fields():
    # with the keys
    epr = {"hub_clli": "", "wavelength": "", "ftp_assignment": ""}
    assert nts.remove_epr_fields(epr) == {}

    # without the keys
    assert nts.remove_epr_fields({}) == {}
