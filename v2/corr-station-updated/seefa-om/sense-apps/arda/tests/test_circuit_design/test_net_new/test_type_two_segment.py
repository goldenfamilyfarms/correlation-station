import logging
import pytest

from arda_app.bll import type_two_segment_ops as seg
from arda_app.bll.models.payloads.type_2_hub_work import Type2HubWorkPayloadModel
from common_sense.common.errors import AbortException
from copy import deepcopy

logger = logging.getLogger(__name__)


@pytest.mark.unittest
def test_get_existing_segment_inst_id_returns_empty_str(monkeypatch: pytest.MonkeyPatch):
    test_type_two_payload = Type2HubWorkPayloadModel(
        cid="95.L1XX.004370..CHTR",
        third_party_provided_circuit="Y",
        service_provider="COMCAST / Comcast",
        service_provider_uni_cid="70.KGGS.021142..TESTA19..",
        service_provider_cid="70.VLXP.019925.ON.TESTA19..",
        service_provider_vlan="3991",
        spectrum_buy_nni_circuit_id="60.KGFD.000001..TWCC",
    )
    # mock data
    segments_found = iter([0, 0])
    segment_inst_id = ""

    monkeypatch.setattr(seg, "get_number_of_segments", lambda *args, **kwargs: next(segments_found))

    assert seg.get_existing_segment_inst_id(test_type_two_payload.model_dump()) == segment_inst_id


@pytest.mark.unittest
def test_get_existing_segment_inst_id_AbortExceptions(monkeypatch: pytest.MonkeyPatch):
    test_type_two_payload = Type2HubWorkPayloadModel(
        cid="95.L1XX.004370..CHTR",
        third_party_provided_circuit="Y",
        service_provider="COMCAST / Comcast",
        service_provider_uni_cid="70.KGGS.021142..TESTA19..",
        service_provider_cid="70.VLXP.019925.ON.TESTA19..",
        service_provider_vlan="3991",
        spectrum_buy_nni_circuit_id="60.KGFD.000001..TWCC",
    )
    segment_inst_id = "12345"
    a_side_site_name = "a-side site name"
    z_side_site_name = "z-side site name"
    update_resp = {
        "CIRC_INST_ID": segment_inst_id,
        "SEGMENT_NAME": "70.KGGS.021142..TESTA19..",
        "STATUS": "Auto-Designed",
        "retString": "AbortException testing",
    }

    monkeypatch.setattr(seg, "get_number_of_segments", lambda *args, **kwargs: next(segments_found))
    monkeypatch.setattr(seg, "get_segment_inst_id", lambda *args, **kwargs: segment_inst_id)
    monkeypatch.setattr(seg, "get_a_side_site_name_for_segment", lambda *args, **kwargs: a_side_site_name)
    monkeypatch.setattr(seg, "get_z_side_site_name_for_segment", lambda *args, **kwargs: z_side_site_name)
    monkeypatch.setattr(seg, "put_granite", lambda *args, **kwargs: update_resp)

    # more than 1 segment was found with service provider CID

    segments_found = iter([2])
    try:
        seg.get_existing_segment_inst_id(test_type_two_payload.model_dump())
    except AbortException as e:
        assert e.code == 500
        assert f"More than 1 segment was found for {test_type_two_payload.service_provider_cid}" in e.data["message"]

    # more than 1 segment was found with service provider UNI CID
    segments_found = iter([0, 2])
    try:
        seg.get_existing_segment_inst_id(test_type_two_payload.model_dump())
    except AbortException as e:
        assert e.code == 500
        assert f"More than 1 segment was found for {test_type_two_payload.service_provider_uni_cid}" in e.data["message"]

    # unable to update segment
    segments_found = iter([1])
    try:
        seg.get_existing_segment_inst_id(test_type_two_payload.model_dump())
    except AbortException as e:
        assert e.code == 500
        assert "Unable to update segment" in e.data["message"]


@pytest.mark.unittest
def test_get_new_segment_inst_id(monkeypatch: pytest.MonkeyPatch):
    test_type_two_payload = Type2HubWorkPayloadModel(
        cid="95.L1XX.004370..CHTR",
        third_party_provided_circuit="Y",
        service_provider="COMCAST / Comcast",
        service_provider_uni_cid="70.KGGS.021142..TESTA19..",
        service_provider_cid="70.VLXP.019925.ON.TESTA19..",
        service_provider_vlan="3991",
        spectrum_buy_nni_circuit_id="60.KGFD.000001..TWCC",
    )
    # mock data
    bandwidth_string = "1 Gbps"
    payloads = [
        {
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "SEGMENT_BANDWIDTH": "1 Gbps",
            "SEGMENT_TYPE": "CUSTOMER",
            "SEGMENT_VENDOR": "COMCAST",
            "SEGMENT_STATUS": "Auto-Designed",
        },
        {
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "A_SIDE_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "Z_SIDE_SITE_NAME": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
        },
    ]
    resp = iter(
        [
            {
                "CIRC_INST_ID": "73559",
                "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
                "STATUS": "Auto-Designed",
                "retString": "Segment Added",
            },
            {
                "CIRC_INST_ID": "73559",
                "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
                "STATUS": "Auto-Designed",
                "retString": "Segment Updated",
            },
        ]
    )
    segments = [
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "BANDWIDTH": "1 Gbps",
            "NBR_CHANNELS": "0",
            "VENDOR": "COMCAST",
            "CATEGORY": "CUSTOMER",
        }
    ]
    segment_inst_id = "73559"

    monkeypatch.setattr(seg, "payload_constructor_for_create_segment", lambda *args, **kwargs: payloads)
    monkeypatch.setattr(seg, "post_granite", lambda *args, **kwargs: next(resp))
    monkeypatch.setattr(seg, "get_segments", lambda *args, **kwargs: segments)
    monkeypatch.setattr(seg, "put_granite", lambda *args, **kwargs: next(resp))

    assert seg.get_new_segment_inst_id(test_type_two_payload.model_dump(), bandwidth_string) == segment_inst_id


@pytest.mark.unittest
def test_get_new_segment_inst_id_AbortExceptions(monkeypatch: pytest.MonkeyPatch):
    test_type_two_payload = Type2HubWorkPayloadModel(
        cid="95.L1XX.004370..CHTR",
        third_party_provided_circuit="Y",
        service_provider="COMCAST / Comcast",
        service_provider_uni_cid="70.KGGS.021142..TESTA19..",
        service_provider_cid="70.VLXP.019925.ON.TESTA19..",
        service_provider_vlan="3991",
        spectrum_buy_nni_circuit_id="60.KGFD.000001..TWCC",
    )
    # mock data
    bandwidth_string = "1 Gbps"
    payloads = [
        {
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "SEGMENT_BANDWIDTH": "1 Gbps",
            "SEGMENT_TYPE": "CUSTOMER",
            "SEGMENT_VENDOR": "COMCAST",
            "SEGMENT_STATUS": "Auto-Designed",
        },
        {
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "A_SIDE_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "Z_SIDE_SITE_NAME": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
        },
    ]
    resp = [
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "retString": "Segment Added",
        },
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "retString": "Segment Updated",
        },
    ]

    segments = [
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "BANDWIDTH": "1 Gbps",
            "NBR_CHANNELS": "0",
            "VENDOR": "COMCAST",
            "CATEGORY": "CUSTOMER",
        }
    ]

    monkeypatch.setattr(seg, "payload_constructor_for_create_segment", lambda *args, **kwargs: p1)
    monkeypatch.setattr(seg, "post_granite", lambda *args, **kwargs: r1)
    monkeypatch.setattr(seg, "get_segments", lambda *args, **kwargs: s1)
    monkeypatch.setattr(seg, "put_granite", lambda *args, **kwargs: r2)

    # required data to create segment unavailable
    p1 = deepcopy(payloads)
    p1 = []
    try:
        seg.get_new_segment_inst_id(test_type_two_payload.model_dump(), bandwidth_string)
    except AbortException as e:
        assert e.code == 500
        assert "Required data to create segment unavailable" in e.data["message"]

    # segment not created
    p1 = deepcopy(payloads)
    r1 = deepcopy(resp)
    r1 = r1[0]
    r1["retString"] = "Segment Not Added"
    try:
        seg.get_new_segment_inst_id(test_type_two_payload.model_dump(), bandwidth_string)
    except AbortException as e:
        assert e.code == 500
        assert "Unable to create segment" in e.data["message"]

    # unable to update segment
    p1 = deepcopy(payloads)
    r1 = deepcopy(resp)
    r1 = r1[0]
    s1 = deepcopy(segments)
    r2 = deepcopy(resp)
    r2 = r2[0]
    r2["retString"] = "Segment Not Updated"
    try:
        seg.get_new_segment_inst_id(test_type_two_payload.model_dump(), bandwidth_string)
    except AbortException as e:
        assert e.code == 500
        assert "Unable to update segment" in e.data["message"]

    # unable to obtain an instance ID for the new segment
    p1 = deepcopy(payloads)
    r1 = deepcopy(resp)
    r1 = r1[0]
    s1 = deepcopy(segments)
    r2 = deepcopy(resp)
    r2 = r2[1]
    r2.pop("CIRC_INST_ID")
    try:
        seg.get_new_segment_inst_id(test_type_two_payload.model_dump(), bandwidth_string)
    except AbortException as e:
        assert e.code == 500
        assert "Unable to obtain an instance ID for the new segment" in e.data["message"]


@pytest.mark.unittest
def test_get_number_of_segments(monkeypatch: pytest.MonkeyPatch):
    # mock data
    cid = "92.L1XX.004050..CHTR"
    segments_data = [
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "BANDWIDTH": "1 Gbps",
            "NBR_CHANNELS": "0",
            "VENDOR": "COMCAST",
            "CATEGORY": "CUSTOMER",
            "A_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "A_CLLI": "PHNHAZVA",
            "Z_SITE": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
        }
    ]

    monkeypatch.setattr(seg, "get_segments", lambda *args, **kwargs: segments_data)

    assert seg.get_number_of_segments(cid) == 1


@pytest.mark.unittest
def test_get_segment_inst_id(monkeypatch: pytest.MonkeyPatch):
    # mock data
    cid = "92.L1XX.004050..CHTR"
    segments_data = [
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "BANDWIDTH": "1 Gbps",
            "NBR_CHANNELS": "0",
            "VENDOR": "COMCAST",
            "CATEGORY": "CUSTOMER",
            "A_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "A_CLLI": "PHNHAZVA",
            "Z_SITE": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
        }
    ]

    monkeypatch.setattr(seg, "get_segments", lambda *args, **kwargs: segments_data)

    assert seg.get_segment_inst_id(cid) == segments_data[0]["CIRC_INST_ID"]


@pytest.mark.unittest
def test_get_segment_inst_id_AbortExceptions(monkeypatch: pytest.MonkeyPatch):
    # mock data
    cid = "92.L1XX.004050..CHTR"
    segments_data = [
        {
            "CIRC_INST_ID": "73559",
            "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
            "STATUS": "Auto-Designed",
            "BANDWIDTH": "1 Gbps",
            "NBR_CHANNELS": "0",
            "VENDOR": "COMCAST",
            "CATEGORY": "CUSTOMER",
            "A_SITE": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "A_CLLI": "PHNHAZVA",
            "Z_SITE": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
        }
    ]

    monkeypatch.setattr(seg, "get_segments", lambda *args, **kwargs: sd1)

    # Unable to obtain segment instance ID
    sd1 = deepcopy(segments_data)
    sd1[0].pop("CIRC_INST_ID")
    try:
        seg.get_segment_inst_id(cid)
    except AbortException as e:
        assert e.code == 500
        assert f"Unable to obtain segment instance ID for {cid}" in e.data["message"]

    # Unexpected data format of segments data
    sd1 = deepcopy(segments_data)
    sd1 = sd1[0]
    try:
        seg.get_segment_inst_id(cid)
    except AbortException as e:
        assert e.code == 500
        assert f"Unable to obtain segment instance ID for {cid}" in e.data["message"]


@pytest.mark.unittest
def test_payload_constructor_for_create_segment(monkeypatch: pytest.MonkeyPatch):
    test_type_two_payload = Type2HubWorkPayloadModel(
        cid="95.L1XX.004370..CHTR",
        third_party_provided_circuit="Y",
        service_provider="COMCAST / Comcast",
        service_provider_uni_cid="70.KGGS.021142..TESTA19..",
        service_provider_cid="70.VLXP.019925.ON.TESTA19..",
        service_provider_vlan="3991",
        spectrum_buy_nni_circuit_id="60.KGFD.000001..TWCC",
    )
    # mock data
    bandwidth_string = "1 Gbps"
    a_side_site_name = "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)"
    z_side_site_name = "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR"

    monkeypatch.setattr(seg, "get_a_side_site_name_for_segment", lambda *args, **kwargs: a_side_site_name)
    monkeypatch.setattr(seg, "get_z_side_site_name_for_segment", lambda *args, **kwargs: z_side_site_name)
    monkeypatch.setattr(seg, "vendor_check", lambda *_: "COMCAST")

    post_payload = {
        "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
        "SEGMENT_BANDWIDTH": "1 Gbps",
        "SEGMENT_TYPE": "CUSTOMER",
        "SEGMENT_VENDOR": "COMCAST",
        "SEGMENT_STATUS": "Designed",
    }
    put_payload = {
        "SEGMENT_NAME": "70.VLXP.019925.ON.TESTA19..",
        "A_SIDE_SITE_NAME": a_side_site_name,
        "Z_SIDE_SITE_NAME": z_side_site_name,
    }
    expected_resp = [post_payload, put_payload]

    assert (
        seg.payload_constructor_for_create_segment(test_type_two_payload.model_dump(), bandwidth_string) == expected_resp
    )


@pytest.mark.unittest
def test_payload_constructor_for_create_segment_AbortExceptions(monkeypatch: pytest.MonkeyPatch):
    # mock data
    bandwidth_string = "1 Gbps"
    a_side_site_name = "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)"
    z_side_site_name = "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR"

    monkeypatch.setattr(seg, "vendor_check", lambda *args, **kwargs: "AT&T")
    monkeypatch.setattr(seg, "get_a_side_site_name_for_segment", lambda *args, **kwargs: a_side_site_name)
    monkeypatch.setattr(seg, "get_z_side_site_name_for_segment", lambda *args, **kwargs: z_side_site_name)

    # missing values when creating segment
    payload_missing_values = Type2HubWorkPayloadModel(
        cid="95.L1XX.004370..CHTR",
        third_party_provided_circuit="Y",
        service_provider="",
        service_provider_uni_cid="70.KGGS.021142..TESTA19..",
        service_provider_cid="",
        service_provider_vlan="3991",
        spectrum_buy_nni_circuit_id="60.KGFD.000001..TWCC",
    )

    with pytest.raises(Exception):
        assert seg.payload_constructor_for_create_segment(payload_missing_values.model_dump(), bandwidth_string) is None


@pytest.mark.unittest
def test_get_a_side_site_name_for_segment(monkeypatch: pytest.MonkeyPatch):
    # mock data
    buy_nni_cid = "60.KGFD.000001..TWCC"
    data = [
        {
            "CIRC_PATH_INST_ID": "2511364",
            "CIRCUIT_NAME": "60.KGFD.000001..TWCC",
            "CIRCUIT_STATUS": "Live",
            "CIRCUIT_BANDWIDTH": "10 Gbps",
            "CIRCUIT_CATEGORY": "ETHERNET TRANSPORT",
            "PREV_PATH_INST_ID": "2190296",
            "SERVICE_TYPE": "CUS-ENNI-BUY",
            "SLM_ELIGIBILITY": "INELIGIBLE DESIGN",
            "ORDER_NUM": "ENG-01250944",
            "ORDERED": "MAY 19, 2023",
            "IN_SERVICE": "MAY 22, 2023",
            "SCHEDULED": "MAY 22, 2023",
            "A_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "A_SITE_TYPE": "COLO",
            "A_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "A_SITE_REGION": "WEST",
            "A_ADDRESS": "615 N 48TH ST",
            "A_CITY": "PHOENIX",
            "A_STATE": "AZ",
            "A_ZIP": "85008",
            "A_FLOOR": "1",
            "A_ROOM": "D",
            "A_CLLI": "PHNHAZVA",
            "A_NPA": "602",
            "A_LONGITUDE": "-111.977644",
            "A_LATITUDE": "33.455597",
            "Z_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "Z_SITE_TYPE": "COLO",
            "Z_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "Z_SITE_REGION": "WEST",
            "Z_ADDRESS": "615 N 48TH ST",
            "Z_CITY": "PHOENIX",
            "Z_STATE": "AZ",
            "Z_ZIP": "85008",
            "Z_FLOOR": "1",
            "Z_ROOM": "D",
            "Z_CLLI": "PHNHAZVA",
            "Z_NPA": "602",
            "Z_LONGITUDE": "-111.977644",
            "Z_LATITUDE": "33.455597",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2899815",
        }
    ]

    monkeypatch.setattr(seg, "get_circuit_site_info", lambda *args, **kwargs: data)

    assert seg.get_a_side_site_name_for_segment(buy_nni_cid) == data[0]["A_SITE_NAME"]


@pytest.mark.unittest
def test_get_a_side_site_name_for_segment_AbortExceptions(monkeypatch: pytest.MonkeyPatch):
    # mock data
    buy_nni_cid = "60.KGFD.000001..TWCC"
    data = [
        {
            "CIRC_PATH_INST_ID": "2511364",
            "CIRCUIT_NAME": "60.KGFD.000001..TWCC",
            "CIRCUIT_STATUS": "Live",
            "CIRCUIT_BANDWIDTH": "10 Gbps",
            "CIRCUIT_CATEGORY": "ETHERNET TRANSPORT",
            "PREV_PATH_INST_ID": "2190296",
            "SERVICE_TYPE": "CUS-ENNI-BUY",
            "SLM_ELIGIBILITY": "INELIGIBLE DESIGN",
            "ORDER_NUM": "ENG-01250944",
            "ORDERED": "MAY 19, 2023",
            "IN_SERVICE": "MAY 22, 2023",
            "SCHEDULED": "MAY 22, 2023",
            "A_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "A_SITE_TYPE": "COLO",
            "A_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "A_SITE_REGION": "WEST",
            "A_ADDRESS": "615 N 48TH ST",
            "A_CITY": "PHOENIX",
            "A_STATE": "AZ",
            "A_ZIP": "85008",
            "A_FLOOR": "1",
            "A_ROOM": "D",
            "A_CLLI": "PHNHAZVA",
            "A_NPA": "602",
            "A_LONGITUDE": "-111.977644",
            "A_LATITUDE": "33.455597",
            "Z_SITE_NAME": "PHNHAZVA-TWC/COLO-IRON MOUNTAIN/PHOENIX-615 N 48TH ST (ENT/ENT LEC)",
            "Z_SITE_TYPE": "COLO",
            "Z_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "Z_SITE_REGION": "WEST",
            "Z_ADDRESS": "615 N 48TH ST",
            "Z_CITY": "PHOENIX",
            "Z_STATE": "AZ",
            "Z_ZIP": "85008",
            "Z_FLOOR": "1",
            "Z_ROOM": "D",
            "Z_CLLI": "PHNHAZVA",
            "Z_NPA": "602",
            "Z_LONGITUDE": "-111.977644",
            "Z_LATITUDE": "33.455597",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2899815",
        }
    ]
    expected = ""

    monkeypatch.setattr(seg, "get_circuit_site_info", lambda *args, **kwargs: d1)

    # can't find A-side site name for segment
    d1 = deepcopy(data)
    d1[0].pop("A_SITE_NAME")
    resp = seg.get_a_side_site_name_for_segment(buy_nni_cid)
    assert resp == expected

    # unable to retrieve circuit site info
    d1 = pytest.raises(AbortException)
    resp = seg.get_a_side_site_name_for_segment(buy_nni_cid)
    assert resp == expected


@pytest.mark.unittest
def test_get_z_side_site_name_for_segment(monkeypatch: pytest.MonkeyPatch):
    # mock data
    service_path_cid = "95.L1XX.004370..CHTR"
    data = [
        {
            "CIRC_PATH_INST_ID": "2412881",
            "CIRCUIT_NAME": "95.L1XX.004370..CHTR",
            "CIRCUIT_STATUS": "Auto-Planned",
            "CIRCUIT_BANDWIDTH": "500 Mbps",
            "CIRCUIT_CATEGORY": "ETHERNET",
            "SERVICE_TYPE": "COM-DIA",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "ORDER_NUM": "COM-FIA-114121,ENG-03637653",
            "ORDERED": "MAR 09, 2023",
            "IN_SERVICE": "MAR 23, 2023",
            "A_SITE_NAME": "SNDACAHC-TWC/COLO-AIS DATA CENTER-9305 LIGHTWAVE AVE (ENT/ENT LEC)",
            "A_SITE_TYPE": "COLO",
            "A_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "A_SITE_REGION": "WEST",
            "A_ADDRESS": "9305 LIGHTWAVE AVE",
            "A_CITY": "SAN DIEGO",
            "A_STATE": "CA",
            "A_ZIP": "92123",
            "A_FLOOR": "1",
            "A_CLLI": "SNDACAHC",
            "A_NPA": "858",
            "A_LONGITUDE": "-117.129683",
            "A_LATITUDE": "32.827850",
            "Z_SITE_NAME": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
            "Z_SITE_TYPE": "CUST_OFFNET",
            "Z_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "Z_SITE_REGION": "WEST",
            "Z_ADDRESS": "3591 DE FOREST CIR",
            "Z_CITY": "MIRA LOMA",
            "Z_STATE": "CA",
            "Z_ZIP": "91752",
            "Z_COMMENTS": "== Inserted via REST Web Service ==",
            "Z_CLLI": "MRLMCAHC",
            "Z_NPA": "951",
            "Z_LONGITUDE": "-117.521384",
            "Z_LATITUDE": "34.022932",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2771111",
        }
    ]

    monkeypatch.setattr(seg, "get_circuit_site_info", lambda *args, **kwargs: data)

    assert seg.get_z_side_site_name_for_segment(service_path_cid) == data[0]["Z_SITE_NAME"]


@pytest.mark.unittest
def test_get_z_side_site_name_for_segment_AbortExceptions(monkeypatch: pytest.MonkeyPatch):
    # mock data
    service_path_cid = "95.L1XX.004370..CHTR"
    data = [
        {
            "CIRC_PATH_INST_ID": "2412881",
            "CIRCUIT_NAME": "95.L1XX.004370..CHTR",
            "CIRCUIT_STATUS": "Auto-Planned",
            "CIRCUIT_BANDWIDTH": "500 Mbps",
            "CIRCUIT_CATEGORY": "ETHERNET",
            "SERVICE_TYPE": "COM-DIA",
            "SLM_ELIGIBILITY": "ELIGIBLE DESIGN",
            "ORDER_NUM": "COM-FIA-114121,ENG-03637653",
            "ORDERED": "MAR 09, 2023",
            "IN_SERVICE": "MAR 23, 2023",
            "A_SITE_NAME": "SNDACAHC-TWC/COLO-AIS DATA CENTER-9305 LIGHTWAVE AVE (ENT/ENT LEC)",
            "A_SITE_TYPE": "COLO",
            "A_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "A_SITE_REGION": "WEST",
            "A_ADDRESS": "9305 LIGHTWAVE AVE",
            "A_CITY": "SAN DIEGO",
            "A_STATE": "CA",
            "A_ZIP": "92123",
            "A_FLOOR": "1",
            "A_CLLI": "SNDACAHC",
            "A_NPA": "858",
            "A_LONGITUDE": "-117.129683",
            "A_LATITUDE": "32.827850",
            "Z_SITE_NAME": "MRLMCAHC-MARTIN BROS//3591 DE FOREST CIR",
            "Z_SITE_TYPE": "CUST_OFFNET",
            "Z_SITE_MARKET": "SOUTHERN CALIFORNIA SOUTH",
            "Z_SITE_REGION": "WEST",
            "Z_ADDRESS": "3591 DE FOREST CIR",
            "Z_CITY": "MIRA LOMA",
            "Z_STATE": "CA",
            "Z_ZIP": "91752",
            "Z_COMMENTS": "== Inserted via REST Web Service ==",
            "Z_CLLI": "MRLMCAHC",
            "Z_NPA": "951",
            "Z_LONGITUDE": "-117.521384",
            "Z_LATITUDE": "34.022932",
            "LEG_NAME": "1",
            "LEG_INST_ID": "2771111",
        }
    ]
    expected = ""

    monkeypatch.setattr(seg, "get_circuit_site_info", lambda *args, **kwargs: d1)

    # can't find Z-side site name for segment
    d1 = deepcopy(data)
    d1[0].pop("Z_SITE_NAME")
    resp = seg.get_z_side_site_name_for_segment(service_path_cid)
    assert resp == expected

    # unable to retrieve circuit site info
    d1 = pytest.raises(AbortException)
    resp = seg.get_z_side_site_name_for_segment(service_path_cid)
    assert resp == expected


@pytest.mark.unittest
def test_vendor_check(monkeypatch):
    # bad test abort consolidated vendor multiple results
    service_provider = "Consolidated"

    with pytest.raises(Exception):
        assert seg.vendor_check(service_provider) is None

    # bad test abort no results from granite
    service_provider = "ATT"

    monkeypatch.setattr(seg, "get_vendor", lambda *args, **kwargs: {})

    with pytest.raises(Exception):
        assert seg.vendor_check(service_provider) is None

    # good test C SPIRE conversion to CSPIRE
    service_provider = "C SPIRE"

    monkeypatch.setattr(seg, "get_vendor", lambda *args, **kwargs: [{"VENDOR_NAME": "CSPIRE"}])

    assert seg.vendor_check(service_provider) == "CSPIRE"

    # good test AT&T / AT&T slash coverage and ampersand to %26
    service_provider = "AT&T / AT&T"

    monkeypatch.setattr(seg, "get_vendor", lambda *args, **kwargs: [{"VENDOR_NAME": "AT&T"}])

    assert seg.vendor_check(service_provider) == "AT&T"
