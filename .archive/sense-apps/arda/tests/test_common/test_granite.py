import logging

from pytest import mark, raises
import requests
from types import SimpleNamespace

from arda_app.common.cd_utils import granite_paths_get_url
from arda_app.dll import granite
from arda_app.dll.granite import get_network_association

logger = logging.getLogger(__name__)


valid_path_id = "99.L3XX.000001..TWCC"
valid_granite_url = granite_paths_get_url(valid_path_id)


### Mock Tests ###  # noqa: E266


class MockResponse:
    __slots__ = ("url", "status_code", "response_json", "text")

    def __init__(self, url, status_code=401, response_object=None, text=""):
        self.url = url
        self.status_code = status_code
        self.response_json = response_object
        self.text = text

    def json(self):
        return self.response_json if self.response_json else {}


def mock_get_granite_empty_response(url, timeout=30, verify=False):
    status_code = 200
    json_response = {"retString": f"no records found for {valid_path_id}", "retCode": 1}
    return MockResponse(url, status_code, json_response)


def mock_get_granite_failure_message(url, timeout=30, verify=False):
    status_code = 200
    error_message = "Internal Server Error Occurred"
    json_response = {"retCode": 2, "retString": error_message}
    return MockResponse(url, status_code, json_response)


def mock_get_granite_404(url, timeout=30, verify=False):
    return MockResponse(url, 404)


def mock_get_granite_returns_unexpected_status_code(url, timeout=30, verify=False):
    return MockResponse(url, 401)


def mock_granite_connection_error(url, **kwargs):
    raise ConnectionError(f"Connection Error occurred connecting to {url}")


def mock_granite_requests_connection_error(url, **kwargs):
    raise requests.exceptions.ConnectionError(f"Connection Error occured connecting to {url}")


def mock_granite_connect_timeout(url, **kwargs):
    raise requests.exceptions.ConnectTimeout(f"Connection Timed out connecting to {url}")


def mock_get_granite_read_timeout(url, timeout=30, verify=False):
    raise requests.exceptions.ReadTimeout(f"ReadTimeout occurred connecting to {url}")


# Raise an error
def do_raise(ex):
    raise ex


### Unit Tests ###  # noqa: E266


@mark.unittest
def test_handle_granite_resp(monkeypatch):
    # Test success
    mock_resp = MockResponse("URL", 200, "response_obj", "DOCTYPE")
    monkeypatch.setattr(granite, "sleep", lambda *args, **kwargs: None)
    assert granite._handle_granite_resp(mock_resp.url, "POST", mock_resp) == mock_resp.json()

    # Test failure - timeout
    with raises(Exception):
        assert granite._handle_granite_resp("URL", "POST", None, None, timeout=5) is None

    # Test failure - "<!DOCTYPE" in resp.text
    mock_resp = SimpleNamespace(text="<!DOCTYPE", status_code=200)
    with raises(Exception):
        assert granite._handle_granite_resp("URL", "POST", mock_resp) is None

    # Test failure - mock_resp not able to be converted to json
    mock_resp.text = "TEST"
    with raises(Exception):
        assert granite._handle_granite_resp("URL", "POST", mock_resp) is None

    # Test failure - status code not 200
    mock_resp.status_code = 300
    with raises(Exception):
        assert granite._handle_granite_resp("URL", "POST", mock_resp) is None


@mark.unittest
def test_get_granite(monkeypatch):
    mock_resp = SimpleNamespace(text="<!DOCTYPE")
    monkeypatch.setattr(granite, "sleep", lambda *args, **kwargs: None)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)
    monkeypatch.setattr(granite, "_handle_granite_resp", lambda *args, **kwargs: mock_resp)

    # Test success - No return
    assert granite.get_granite("endpoint") is None

    # Test success - return_resp = True
    mock_resp.text = ""
    assert granite.get_granite("endpoint", return_resp=True) == mock_resp

    # Test success - return_resp = False
    assert granite.get_granite("endpoint", return_resp=False) == mock_resp

    # Test failure - try except ConnectionError
    monkeypatch.setattr(
        requests, "get", lambda *args, **kwargs: do_raise(requests.exceptions.ConnectionError("Failed to connect"))
    )
    assert granite.get_granite("endpoint", return_resp=True) is None


@mark.unittest
def test_post_granite(monkeypatch):
    mock_resp = SimpleNamespace(text="<!NO_DOCTYPE")
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: mock_resp)
    monkeypatch.setattr(granite, "_handle_granite_resp", lambda *args, **kwargs: None)

    # Test success - return_resp = True
    assert granite.post_granite("endpoint", "payload", return_resp=True) == mock_resp

    # Test success - return_resp = False
    assert granite.post_granite("endpoint", "payload", return_resp=False) is None

    # Test failure - try except ConnectionError
    monkeypatch.setattr(
        requests, "post", lambda *args, **kwargs: do_raise(requests.exceptions.ConnectionError("Failed to connect"))
    )
    assert granite.post_granite("endpoint", "payload") is None


@mark.unittest
def test_put_granite(monkeypatch):
    mock_resp = SimpleNamespace(text="<!NO_DOCTYPE")
    payload = {"BREAK_LOCK": "FALSE"}
    monkeypatch.setattr(requests, "put", lambda *args, **kwargs: mock_resp)
    monkeypatch.setattr(granite, "_handle_granite_resp", lambda *args, **kwargs: None)

    # Test success - return_resp = True
    assert granite.put_granite("endpoint", payload, return_resp=True) == mock_resp

    # Test success - return_resp = False
    assert granite.put_granite("endpoint", payload, return_resp=False) is None

    # Test failure - try except ConnectionError
    monkeypatch.setattr(
        requests, "put", lambda *args, **kwargs: do_raise(requests.exceptions.ConnectionError("Failed to connect"))
    )
    assert granite.put_granite("endpoint", payload) is None


@mark.unittest
def test_delete_granite(monkeypatch):
    mock_resp = SimpleNamespace(text="<!NO_DOCTYPE")
    monkeypatch.setattr(requests, "delete", lambda *args, **kwargs: mock_resp)
    monkeypatch.setattr(granite, "_handle_granite_resp", lambda *args, **kwargs: None)

    # Test success - return_resp=True
    assert granite.delete_granite("endpoint", "payload", return_resp=True) == mock_resp

    # Test success - return_resp=False
    assert granite.delete_granite("endpoint", "payload", return_resp=False) is None

    # Test failure - try except ConnectionError
    monkeypatch.setattr(
        requests, "delete", lambda *args, **kwargs: do_raise(requests.exceptions.ConnectionError("Failed to connect"))
    )
    assert granite.delete_granite("endpoint", "payload") is None


@mark.unittest
def test_get_equipment_buildout(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["equipment_build_data"])
    assert granite.get_equipment_buildout("ELPSTXIG1ZW") == ["equipment_build_data"]

    # Test failure - retString
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["equipment_build_data", "retString"])
    with raises(Exception):
        assert granite.get_equipment_buildout("ELPSTXIG1ZW") is None


@mark.unittest
def test_get_device_vendor(monkeypatch):
    # Test success
    response = [{"EQUIP_VENDOR": "RAD"}]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: response)
    assert granite.get_device_vendor("ELPSTXGG-TWC/HUB") == "RAD"

    # Test failure - IndexError
    response = []
    with raises(Exception):
        assert granite.get_device_vendor("ELPSTXIG1ZW") is None


@mark.unittest
def test_get_selected_vendor(monkeypatch):
    mock_response = ["400"]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: mock_response)

    # Test success - source == "internal"
    assert granite.get_selected_vendor(source="internal") == mock_response[0]

    # Test success - source != "internal"
    assert granite.get_selected_vendor(source="external") == mock_response[0]

    # Test failure - ConnectionError
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: do_raise(requests.exceptions.ConnectionError()))
    assert granite.get_selected_vendor(source="internal") == {"VENDOR": "RAD"}


@mark.unittest
def test_get_device_fqdn(monkeypatch):
    # Test success
    response = [{"FQDN": "RAD"}]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: response)
    assert granite.get_device_fqdn("ELPSTXGG-TWC/HUB") == "RAD"

    # Test failure - host is None
    response[0]["FQDN"] = None
    with raises(Exception):
        assert granite.get_device_fqdn("ELPSTXGG-TWC/HUB") is None

    # Test failure - empty response
    response = []
    with raises(Exception):
        assert granite.get_device_fqdn("ELPSTXGG-TWC/HUB") is None


@mark.unittest
def test_get_device_model(monkeypatch):
    # Test success
    response = [{"EQUIP_MODEL": "ETX203AX"}]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: response)
    assert granite.get_device_model("ELPSTXGG-TWC/HUB") == "ETX203AX"

    # Test failure - model is None
    response[0]["EQUIP_MODEL"] = None
    with raises(Exception):
        assert granite.get_device_model("ELPSTXGG-TWC/HUB") is None

    # Test failure - IndexError
    response = []
    with raises(Exception):
        assert granite.get_device_model("ELPSTXGG-TWC/HUB") is None


@mark.unittest
def test_insert_card_template(monkeypatch):
    # Test success
    uplink_port = {"EQUIP_NAME": "MDFDORQM2ZW/999", "SLOT_INST_ID": "2766833"}
    card_template = "TEMP"
    response = "MOCK_RESP"
    monkeypatch.setattr(granite, "post_granite", lambda *args, **kwargs: response)
    assert granite.insert_card_template(uplink_port, card_template) == "MOCK_RESP"


@mark.unittest
def test_get_available_uplink_ports(monkeypatch):
    clli = "ELPSTXGG"
    bandwidth_string = "20Mbps"
    response = {"NOretString": "MOCK_RESP"}
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: response)
    monkeypatch.setattr(granite, "filter_out_ports", lambda *args, **kwargs: response["NOretString"])

    # Test success
    assert granite.get_available_uplink_ports(clli, bandwidth_string) == "MOCK_RESP"

    # Test failure - retString and JUNIPER in resonse
    response["retString"] = "JUNIPER"
    with raises(Exception):
        assert granite.get_available_uplink_ports(clli, bandwidth_string) is None

    # Test failure - JUNIPER not in response
    response["retString"] = "NONE"
    with raises(Exception):
        assert granite.get_available_uplink_ports(clli, bandwidth_string) is None


@mark.unittest
def test_filter_out_ports(monkeypatch):
    # Test success - empty return list
    ports = [{"SLOT": "POWER"}]
    assert granite.filter_out_ports(ports) == []

    # Test success - populated return list
    ports = [{"SLOT": "EMPTY", "MODEL": "EMPTY"}]
    assert granite.filter_out_ports(ports) == [{"SLOT": "EMPTY", "MODEL": "EMPTY"}]


@mark.unittest
def test_get_qc_available_uplink_ports(monkeypatch):
    # Test success
    response = [{"EQUIP_NAME": "MDFDORQM2ZW/999", "MODEL": "ETX-220A", "EXPECTED_PAID": "ETH PORT "}]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: response)
    assert granite.get_qc_available_uplink_ports("ELPSTXIG", "VPLS") == [
        {"EQUIP_NAME": "MDFDORQM2ZW/999", "MODEL": "ETX-220A", "EXPECTED_PAID": ""}
    ]

    # Test failure - multiple equipment names in granite response
    response = [{"EQUIP_NAME": "MDFDORQM2ZW/999", "MODEL": "ETX203AX/2SFP"}, {"EQUIP_NAME": "ZFXOPQM2ZY/788"}]
    with raises(Exception):
        assert granite.get_qc_available_uplink_ports("ELPSTXIG", "VPLS") is None

    # Test failure - response is instance of dict
    response = {"EQUIP_NAME": "MDFDORQM2ZW/999", "MODEL": "ETX-220A"}
    with raises(Exception):
        assert granite.get_qc_available_uplink_ports("ELPSTXIG", "VPLS") is None


@mark.unittest
def test_put_port_access_id(monkeypatch):
    # Test success
    granite_rsp = "MOCK_RESP"
    monkeypatch.setattr(granite, "put_granite", lambda *args, **kwargs: granite_rsp)
    assert granite.put_port_access_id("115032919", "ETH PORT 5") == granite_rsp


@mark.unittest
def test_get_available_equipment_ports(monkeypatch):
    # Test success
    granite_rsp = {"retString": "Records found"}
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: granite_rsp)
    assert granite.get_available_equipment_ports("MDFDORQM2ZW/999") == granite_rsp

    # Test failure - granite_resp is a dict and no records found
    granite_rsp = {"retString": "No records found"}
    with raises(Exception):
        assert granite.get_available_equipment_ports("MDFDORQM2ZW/999") is None


@mark.unittest
def test_get_used_equipment_ports(monkeypatch):
    # Test success
    granite_rsp = {"retString": "Records found"}
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: granite_rsp)
    assert granite.get_used_equipment_ports("MDFDORQM2ZW/999") == granite_rsp

    # Test failure - granite_resp is a dict and no records found
    granite_rsp = {"retString": "No records found"}
    with raises(Exception):
        assert granite.get_used_equipment_ports("MDFDORQM2ZW/999") is None


@mark.unittest
def test_get_existing_shelf(monkeypatch):
    # Test success
    granite_rsp = "MOCK_RESP"
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: granite_rsp)
    assert granite.get_existing_shelf("MDFDORQM", "MDFDORQM-PROVIDENCE") == "MOCK_RESP"

    # Test failure - IndexError
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: do_raise(IndexError))
    assert granite.get_existing_shelf("MDFDORQM", "MDFDORQM-PROVIDENCE") is None


@mark.unittest
def test_get_network_association(monkeypatch):
    data = [
        {
            "networkInstId": "2276164",
            "networkHumId": "CHTRSE.VRFID.477776.MCNC NCTN",
            "networkRevNbr": "1",
            "networkStatus": "Live",
            "assocInstId": "303095",
            "associationName": "EVC ID NUMBER/NETWORK",
            "associationType": "NETWORK TO EVC ID",
            "associationValue": "477776",
            "associationObjectType": "Number",
            "numberRangeName": "MANUAL ASSIGNMENT RETAIL/CARRIER RANGE 0078",
        }
    ]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: data)
    network_inst_id = "2276164"
    response = get_network_association(network_inst_id)
    if isinstance(response, list):
        assert response[0]["associationValue"] == "477776"


@mark.unittest
def test_get_network_elements(monkeypatch):
    network_inst_id = "1343777"
    expected = [
        {
            "CIRC_PATH_INST_ID": "1343777",
            "PATH_NAME": "CHTRSE.VRFID.400093185.YOUNG OFFICE SUPPLY",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Cloud",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-CHTR",
            "L_ID": "CHC00093185_YOSRIDGERD",
            "SEQUENCE": "10",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543958",
            "A_SITE_NAME": "CHRNNCKT-TWC/COLO-DIGITAL REALTY-CHR1 CHARLOTTE//113 N MYERS ST (ENT/ENT LEC)",
            "Z_SITE_NAME": "CLMASCFS-YOUNG OFFICE ENVIRONMENTS//1104 SHOP RD",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "80.L1XX.007793..CHTR",
            "ELEMENT_REFERENCE": "2577956",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "100 Mbps",
        },
        {
            "CIRC_PATH_INST_ID": "1343777",
            "PATH_NAME": "CHTRSE.VRFID.400093185.YOUNG OFFICE SUPPLY",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Cloud",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-CHTR",
            "L_ID": "CHC00093185_YOSRIDGERD",
            "SEQUENCE": "11",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543958",
            "A_SITE_NAME": "GNVLSCZV-CHTR/HUB-GREENVILLE PRIMARY (GNVLSC21280)",
            "Z_SITE_NAME": "GNVMSCHF-YOUNG OFFICE SUPPLY//1280 RIDGE RD",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "86.L1XX.001113..TWCC",
            "ELEMENT_REFERENCE": "2621885",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Designed",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "PREV_PATH_INST_ID": "1948981",
        },
        {
            "CIRC_PATH_INST_ID": "1343777",
            "PATH_NAME": "CHTRSE.VRFID.400093185.YOUNG OFFICE SUPPLY",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Cloud",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-CHTR",
            "L_ID": "CHC00093185_YOSRIDGERD",
            "SEQUENCE": "5",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543958",
            "A_SITE_NAME": "GNVLSCZV-CHTR/HUB-GREENVILLE PRIMARY (GNVLSC21280)",
            "Z_SITE_NAME": "GNVMSCHF-YOUNG OFFICE SUPPLY//1280 RIDGE RD",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "86.L1XX.001113..TWCC",
            "ELEMENT_REFERENCE": "1948981",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "200 Mbps",
            "NEXT_PATH_INST_ID": "2621885",
            "PREV_PATH_INST_ID": "1343305",
        },
        {
            "CIRC_PATH_INST_ID": "1343777",
            "PATH_NAME": "CHTRSE.VRFID.400093185.YOUNG OFFICE SUPPLY",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Cloud",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-CHTR",
            "L_ID": "CHC00093185_YOSRIDGERD",
            "SEQUENCE": "6",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543958",
            "A_SITE_NAME": "AHVLNCDG-CHTR/HUB-ASHEVILLE PRIMARY (AHVLNC06362)",
            "Z_SITE_NAME": "AHVLNCQO-YOUNG OFFICE SUPPLY//71 THOMPSON ST",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "82.L1XX.000507..TWCC",
            "ELEMENT_REFERENCE": "1949929",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "100 Mbps",
            "PREV_PATH_INST_ID": "1343204",
        },
        {
            "CIRC_PATH_INST_ID": "1343777",
            "PATH_NAME": "CHTRSE.VRFID.400093185.YOUNG OFFICE SUPPLY",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Cloud",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-CHTR",
            "L_ID": "CHC00093185_YOSRIDGERD",
            "SEQUENCE": "8",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543958",
            "A_SITE_NAME": "SPBGSCFI-CHTR/HE-SPARTANBURG (SPBGSC21279)",
            "Z_SITE_NAME": "SPBGSCNZ-YOUNG OFFICE ENVIRONMENTS//103 N PINE ST",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "86.L1XX.003690..CHTR",
            "ELEMENT_REFERENCE": "2369495",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "100 Mbps",
        },
        {
            "CIRC_PATH_INST_ID": "1343777",
            "PATH_NAME": "CHTRSE.VRFID.400093185.YOUNG OFFICE SUPPLY",
            "PATH_REV": "1",
            "PATH_CATEGORY": "VPLS SVC",
            "TOPOLOGY": "Cloud",
            "PATH_STATUS": "Live",
            "BANDWIDTH": "VPLS",
            "BW_SIZE": "0",
            "SOURCE": "L-CHTR",
            "L_ID": "CHC00093185_YOSRIDGERD",
            "SEQUENCE": "9",
            "LEG_NAME": "1",
            "LEG_INST_ID": "1543958",
            "A_SITE_NAME": "CHRNNCKT-TWC/COLO-DIGITAL REALTY-CHR1 CHARLOTTE//113 N MYERS ST (ENT/ENT LEC)",
            "Z_SITE_NAME": "LDSNSCDP-YOUNG OFFICE ENVIRONMENTS//3841 COMMERCIAL CENTER DR",
            "ELEMENT_TYPE": "PATH LINK",
            "ELEMENT_NAME": "84.L1XX.003653..CHTR",
            "ELEMENT_REFERENCE": "2577959",
            "ELEMENT_CATEGORY": "ETHERNET",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "100 Mbps",
        },
    ]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: expected)
    assert granite.get_network_elements(network_inst_id) == expected


@mark.unittest
def test_get_vgw_id(monkeypatch):
    cid = "91.TGXX.001266..CHTR"
    path_elements = [
        {
            "CIRC_PATH_INST_ID": "2409769",
            "PATH_NAME": "91.TGXX.001266..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "ELPSTXGG-TWC/HUB E-HUNTER (5)",
            "PATH_Z_SITE": "ELPSTXIG-FOX TOYOTA LEXUS//7750 GATEWAY BLVD E",
            "A_CLLI": "ELPSTXGG",
            "Z_CLLI": "ELPSTXIG",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-04786270",
            "CUSTOMER_NAME": "FOX TOYOTA LEXUS",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": "NONE",
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": "NONE",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "4.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "4",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2766833",
            "A_SITE_NAME": "ELPSTXIG-FOX TOYOTA LEXUS//7750 GATEWAY BLVD E",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "ELPSTXIG1ZW/999.9999.999.99/NIU",
            "ELEMENT_REFERENCE": "1758434",
            "ELEMENT_CATEGORY": "NIU",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "1 Gbps",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "USER 5",
            "PORT_NAME": "1",
            "PORT_INST_ID": "115032919",
            "PORT_ACCESS_ID": "ETH PORT 5",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": None,
            "FQDN": "ELPSTXIG1ZW.CML.CHTRSE.COM",
            "MODEL": "ETX203AX/2SFP/2UTP2SFP",
            "VENDOR": "RAD",
            "TID": "ELPSTXIG1ZW",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "ENTERPRISE",
            "IPV4_ADDRESS": "10.4.100.211/24",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1313",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "91.TGXX.001266..CHTR",
            "INITIAL_CIRCUIT_ID": "2409769",
            "LVL": "1",
        },
        {
            "CIRC_PATH_INST_ID": "2409769",
            "PATH_NAME": "91.TGXX.001266..CHTR",
            "PATH_REV": "1",
            "PATH_CATEGORY": "CUSTOMER SIP TRUNKS",
            "PATH_A_SITE": "ELPSTXGG-TWC/HUB E-HUNTER (5)",
            "PATH_Z_SITE": "ELPSTXIG-FOX TOYOTA LEXUS//7750 GATEWAY BLVD E",
            "A_CLLI": "ELPSTXGG",
            "Z_CLLI": "ELPSTXIG",
            "PATH_A_SITE_TYPE": "HUB",
            "PATH_Z_SITE_TYPE": "LOCAL",
            "TOPOLOGY": "Point-to-point",
            "PATH_STATUS": "Live",
            "CLASS_OF_SERVICE": None,
            "SLM_ELIGIBILITY": "INELIGIBLE SERVICE",
            "EVC_ID": None,
            "SERVICE_TYPE": "CUS-VOICE-SIP",
            "BANDWIDTH": "20 Mbps",
            "BW_SIZE": "20000000",
            "CUSTOMER_ID": "ACCT-04786270",
            "CUSTOMER_NAME": "FOX TOYOTA LEXUS",
            "IPV4_GLUE_SUBNET": None,
            "IPV4_ASSIGNED_SUBNETS": None,
            "IPV4_ASSIGNED_GATEWAY": None,
            "IPV4_SERVICE_TYPE": "NONE",
            "IPV6_GLUE_SUBNET": None,
            "IPV6_ASSIGNED_SUBNETS": None,
            "IPV6_SERVICE_TYPE": "NONE",
            "CUSTOMER_TYPE": "ENTERPRISE",
            "ORDER_REFERENCE": "5.",
            "PARENT_SEQUENCE": None,
            "PARENT_MEMBER_NBR": None,
            "SEQUENCE": "5",
            "MEMBER_NBR": None,
            "LEG_NAME": "1",
            "LEG_INST_ID": "2766833",
            "A_SITE_NAME": "ELPSTXIG-FOX TOYOTA LEXUS//7750 GATEWAY BLVD E",
            "Z_SITE_NAME": None,
            "ELEMENT_TYPE": "PORT",
            "ELEMENT_NAME": "ELPSTXIGG01/999.9999.999.99/LAG",
            "ELEMENT_REFERENCE": "1761734",
            "ELEMENT_CATEGORY": "LINE/ACCESS GATEWAY",
            "ELEMENT_STATUS": "Live",
            "ELEMENT_BANDWIDTH": "10/100/1000 BASET",
            "NEXT_PATH_INST_ID": None,
            "PREV_PATH_INST_ID": None,
            "CHAN_NAME": None,
            "CHAN_INST_ID": None,
            "SLOT": "CHASSIS PORTS",
            "PORT_NAME": "WAN",
            "PORT_INST_ID": "115033062",
            "PORT_ACCESS_ID": "WAN",
            "CONNECTOR_TYPE": "RJ-45",
            "PORT_CHANNELIZATION": "FIXED",
            "FQDN": "ELPSTXIGG01.CML.CHTRSE.COM",
            "MODEL": "M800C/8S/60SIP/ALU",
            "VENDOR": "AUDIOCODES",
            "TID": "ELPSTXIGG01",
            "LEGACY_EQUIP_SOURCE": "L-TWC",
            "PURCHASING_GROUP": "MANAGED SERVICES - IP",
            "IPV4_ADDRESS": "98.6.191.107/30",
            "IPV6_ADDRESS": None,
            "C_VLAN": None,
            "CUST_S_VLAN": None,
            "S_VLAN": "1313",
            "VLAN_OPERATION": "PUSH",
            "PORT_ROLE": "UNI-EP",
            "INITIAL_PATH_NAME": "91.TGXX.001266..CHTR",
            "INITIAL_CIRCUIT_ID": "2409769",
            "LVL": "1",
        },
    ]

    monkeypatch.setattr(granite, "get_path_elements_l1", lambda *args: path_elements)
    result = granite.get_vgw_id(cid)
    assert result == "1761734"

    path_elements[1]["TID"] = "ELPSTXIGG71"
    monkeypatch.setattr(granite, "get_path_elements_l1", lambda *args: path_elements)
    result = granite.get_vgw_id(cid)
    assert result == "1761734"

    path_elements[0]["TID"] = "ELPSTXIGG1W"
    monkeypatch.setattr(granite, "get_path_elements_l1", lambda *args: path_elements)
    result = granite.get_vgw_id(cid)
    assert result == "1758434"


@mark.unittest
def test_get_next_available_zw_shelf(monkeypatch):
    z_clli = "MDFDORQM"
    z_site_name = "MDFDORQM-PROVIDENCE ST JOSEPH HEALTH//2780 E BARNETT RD"
    zw_candidate = iter(["MDFDORQM3ZW", "MDFDORQM1ZW"])
    available_zw = "MDFDORQM3ZW"
    resp = iter(
        [
            {
                "instId": "0",
                "retCode": 2,
                "httpCode": 200,
                "retString": "No records found with the specified search criteria...",
            },
            [
                {
                    "SITE_NAME": "MDFDORQM-SOUTHERN OREGON ORHOPEDICS//2780 E BARNETT RD",
                    "SITE_INST_ID": "641440",
                    "SITE_CATEGORY": "LOCAL",
                    "SITE_STATUS": "Live",
                    "SITE_CLLI": "MDFDORQM",
                    "EQUIP_NAME": "MDFDORQM2ZW/999.9999.999.99/SWT",
                    "EQUIP_INST_ID": "1406739",
                    "EQUIP_CATEGORY": "SWITCH",
                    "EQUIP_STATUS": "Live",
                    "EQUIP_VENDOR": "CISCO",
                    "EQUIP_MODEL": "ME-3400-EG-12CS-M",
                    "FQDN": "MDFDORQM2ZW.CML.CHTRSE.COM",
                    "TARGET_ID": "MDFDORQM2ZW",
                    "IPV4_ADDRESS": "DHCP",
                    "OBJECT_TYPE": "SHELF",
                }
            ],
            {
                "instId": "0",
                "retCode": 2,
                "httpCode": 200,
                "retString": "No records found with the specified search criteria...",
            },
        ]
    )

    monkeypatch.setattr(granite, "get_next_zw_shelf", lambda *args, **kwargs: next(zw_candidate))
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: next(resp))
    monkeypatch.setattr(granite, "identify_available_zw_shelf", lambda *args, **kwargs: available_zw)

    assert granite.get_next_available_zw_shelf(z_clli, z_site_name) == available_zw
    assert granite.get_next_available_zw_shelf(z_clli, z_site_name) == available_zw


@mark.unittest
def test_identify_available_zw_shelf(monkeypatch):
    z_clli = "MDFDORQM"
    zw_candidate = "MDFDORQM1ZW"
    resp = iter(
        [
            [
                {
                    "SITE_NAME": "MDFDORQM-SOUTHERN OREGON ORHOPEDICS//2780 E BARNETT RD",
                    "SITE_INST_ID": "641440",
                    "SITE_CATEGORY": "LOCAL",
                    "SITE_STATUS": "Live",
                    "SITE_CLLI": "MDFDORQM",
                    "EQUIP_NAME": "MDFDORQM2ZW/999.9999.999.99/SWT",
                    "EQUIP_INST_ID": "1406739",
                    "EQUIP_CATEGORY": "SWITCH",
                    "EQUIP_STATUS": "Live",
                    "EQUIP_VENDOR": "CISCO",
                    "EQUIP_MODEL": "ME-3400-EG-12CS-M",
                    "FQDN": "MDFDORQM2ZW.CML.CHTRSE.COM",
                    "TARGET_ID": "MDFDORQM2ZW",
                    "IPV4_ADDRESS": "DHCP",
                    "OBJECT_TYPE": "SHELF",
                }
            ],
            {
                "instId": "0",
                "retCode": 2,
                "httpCode": 200,
                "retString": "No records found with the specified search criteria...",
            },
        ]
    )
    next_zw = "MDFDORQM3ZW"

    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: next(resp))

    assert granite.identify_available_zw_shelf(z_clli, zw_candidate) == next_zw


@mark.unittest
def test_update_network_status(monkeypatch):
    # Test success
    network_inst_id = "1405593"
    status = "Pending Decommission"
    expected = {
        "NetworkName": "CHTRSE.VRFID.90937.MANATEE RURAL HEALTH SVCS",
        "rev": "1",
        "status": "Pending Decommission",
        "ntwkInstanceId": "1405593",
        "retString": "Network Updated",
    }
    monkeypatch.setattr(granite, "put_granite", lambda *args, **kwargs: expected)
    assert granite.update_network_status(network_inst_id, status) == expected


@mark.unittest
def test_get_attributes_for_path(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: {"retString": "Records found"})
    assert granite.get_attributes_for_path("2409769") == {"retString": "Records found"}

    # Test failure - "No records found" in granite_resp
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: {"retString": "No records found"})
    with raises(Exception):
        assert granite.get_attributes_for_path("2409769") is None


@mark.unittest
def test_get_source_mep(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.get_source_mep("91.TGXX.001266..CHTR") == ["resp"]


@mark.unittest
def test_get_network_path(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.get_network_path("Spectrum") == ["resp"]


@mark.unittest
def test_update_vgw_shelf_ipv4_address(monkeypatch):
    # Test success
    cid = "91.TGXX.001266..CHTR"
    shelf_ipv4 = "98.6.191.106/32"
    vgw_id = "1761734"
    put_granite_resp = {
        "id": "ELPSTXIGG01/999.9999.999.99/LAG",
        "status": "Live",
        "equipInstId": "1761734",
        "retString": "Shelf Updated",
    }

    monkeypatch.setattr(granite, "get_vgw_id", lambda *args: vgw_id)
    monkeypatch.setattr(granite, "put_granite", lambda *args: put_granite_resp)
    result = granite.update_vgw_shelf_ipv4_address(cid, shelf_ipv4)
    assert result == put_granite_resp


@mark.unittest
def test_get_segments(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.get_segments("1543958", "PUSH") == ["resp"]


@mark.unittest
def test_get_transport_channels(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.get_transport_channels("CHAN_NAME") == ["resp"]

    # Test failure - "No records found" in resp
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: {"retString": "No records found"})
    with raises(Exception):
        assert granite.get_transport_channels("CHAN_NAME") is None


@mark.unittest
def test_paths_from_site(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.paths_from_site("SITE_NAME") == ["resp"]

    # Test failure - if isinstance(data, dict)
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: {"resp1": "resp2"})
    with raises(Exception):
        assert granite.paths_from_site("SITE_NAME") is None


@mark.unittest
def test_find_nni_device(monkeypatch):
    # Able to find A-side router
    resp = [{"ELEMENT_TYPE": "PORT", "TID": "ELPSTXIG1ZW"}]
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: resp)
    assert granite.find_nni_device("NNI") == "ELPSTXIG1ZW"

    # Unable to find A-side router
    resp[0]["ELEMENT_TYPE"] = "ELM"
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: resp)
    with raises(Exception):
        assert granite.find_nni_device("NNI") is None


@mark.unittest
def test_get_vendor(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.get_vendor("Salesforce") == ["resp"]


@mark.unittest
def test_get_paths_from_ip(monkeypatch):
    # Test success
    monkeypatch.setattr(granite, "get_granite", lambda *args, **kwargs: ["resp"])
    assert granite.get_paths_from_ip("127.0.0.1") == ["resp"]
