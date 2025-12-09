import base64
import pytest

from fastapi.testclient import TestClient
from arda_app.main import app as fastapi_app
from arda_app.common import auth_config


@pytest.fixture
def client(request):
    client = TestClient(fastapi_app)

    credentials = f"{auth_config.SENSE_TEST_SWAGGER_USER}:{auth_config.SENSE_TEST_SWAGGER_PASS}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    client.headers["Authorization"] = f"Basic {encoded_credentials}"
    client.headers["Content-Type"] = "application/json"
    return client


@pytest.fixture
def lab_eline_158():
    """The expected JSON response from Arda for CID 51.L1XX.009158..TWCC"""

    resp = """
        {
            "CustomerName": "ANDROMEDA PROJECT TEST",
            "CircuitID": "51.L1XX.009158..TWCC",
            "Bandwidth": "100 Mbps",
            "ServiceLevel": null,
            "UnitType": "CARRIER",
            "ServiceVLANID": "",
            "VCID": "",
            "EtherType": "",
            "EVCType": "",
            "ASide": {
                "CustomerAddr": "",
                "PE": {
                    "Vendor": "",
                    "Model": "",
                    "Hostname": "",
                    "Interface": "",
                    "Description": "",
                    "PortType": "",
                    "VLANOperation": "",
                    "VLAN": ""
                },
                "CPE": {
                    "Vendor": "",
                    "Model": "",
                    "Hostname": "",
                    "Interface": "",
                    "Description": "",
                    "PortType": "",
                    "VLANOperation": "",
                    "VLAN": "",
                    "CFMType": "",
                    "CFMMDLevel": "",
                    "CFMMAID": "",
                    "CFMScope": "",
                    "CFMRemoteReflector": ""
                }
            },
            "ZSide": {
                "CustomerAddr": "",
                "PE": {
                    "Vendor": "",
                    "Model": "",
                    "Hostname": "",
                    "Interface": "",
                    "Description": "",
                    "PortType": "",
                    "VLANOperation": "",
                    "VLAN": ""
                },
                "CPE": {
                    "Vendor": "",
                    "Model": "",
                    "Hostname": "",
                    "Interface": "",
                    "Description": "",
                    "PortType": "",
                    "VLANOperation": "",
                    "VLAN": "",
                    "CFMType": "",
                    "CFMMDLevel": "",
                    "CFMMAID": "",
                    "CFMScope": "",
                    "CFMRemoteReflector": ""
                }
            }
        }"""

    return resp


@pytest.fixture
def real_eline_ex():
    resp = """
        {
            "CustomerName": "TEXAS LEGENDS",
            "CircuitID": "97.L1XX.003816..TWCC",
            "Bandwidth": "100 Mbps",
            "ServiceLevel": null,
            "UnitType": "COMMERCIAL",
            "ServiceVLANID": 1200,
            "VCID": 429390,
            "EtherType": "8100",
            "EVCType": "COM-EPL",
            "ASide": {
                "CustomerAddr": "2601 AVENUE OF THE STARS",
                "PE": {
                    "Vendor": null,
                    "Model": null,
                    "Hostname": null,
                    "Interface": null,
                    "Description": null,
                    "PortType": null,
                    "VLANOperation": null,
                    "VLAN": null
                },
                "CPE": {
                    "Vendor": null,
                    "Model": null,
                    "Hostname": null,
                    "Interface": null,
                    "Description": null,
                    "PortType": null,
                    "VLANOperation": null,
                    "VLAN": null,
                    "CFMType": null,
                    "CFMMDLevel": null,
                    "CFMMAID": null,
                    "CFMScope": null,
                    "CFMRemoteReflector": null
                }
            },
            "ZSide": {
                "CustomerAddr": "15455 DALLAS PKWY",
                "PE": {
                    "Vendor": null,
                    "Model": null,
                    "Hostname": null,
                    "Interface": null,
                    "Description": null,
                    "PortType": null,
                    "VLANOperation": null,
                    "VLAN": null
                },
                "CPE": {
                    "Vendor": null,
                    "Model": null,
                    "Hostname": null,
                    "Interface": null,
                    "Description": null,
                    "PortType": null,
                    "VLANOperation": null,
                    "VLAN": null,
                    "CFMType": null,
                    "CFMMDLevel": null,
                    "CFMMAID": null,
                    "CFMScope": null,
                    "CFMRemoteReflector": null
                }
            }
        }"""

    return resp
