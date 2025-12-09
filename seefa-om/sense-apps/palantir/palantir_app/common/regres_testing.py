from palantir_app.bll import compliance_disconnect
from palantir_app.common.constants import FIA
from common_sense.common.errors import abort
from tests.mock_data.compliance.compliance import mock_full_disco_isp_information, mock_double_full_disco_isp_information


RESOURCE_STATUS_RESPONSES = {
    "/v3/resourcestatus": {
        "79797979-7979-7979-7979-797979797979": {
            "response": {"id": "79797979-7979-7979-7979-797979797979", "status": "Completed", "message": ""}
        }
    },
    "/v4/resourcestatus": {
        "test_partial_disconnect_success": {
            "response": {
                "status": "Completed",
                "message": "",
                "id": "test_partial_disconnect_success",
                "data": {
                    "label": "85.L1XX.001568..TWCC",
                    "resourceTypeId": "charter.resourceTypes.ServiceMapper",
                    "productId": "62679989-afbb-4425-bba7-e44c226b7d5b",
                    "domainId": "built-in",
                    "tenantId": "c2ce28a0-eab7-46a3-97fc-ddfacf8c4d67",
                    "shared": False,
                    "subDomainId": "7fd5144c-552f-39a3-9464-08d3b9cfb251",
                    "properties": {
                        "mdso_provisioned": True,
                        "remediation_flag": True,
                        "remediation_attempted": True,
                        "use_alternate_circuit_details_server": False,
                        "device_properties": {"UNINOHAC1ZW": {"MediaType": "RJ-45"}},
                        "service_type": FIA,
                        "circuit_id": "85.L1XX.001568..TWCC",
                    },
                    "discovered": False,
                    "differences": [],
                    "desiredOrchState": "active",
                    "orchState": "active",
                    "reason": "",
                    "tags": {},
                    "providerData": {"templateResources": {}},
                    "updatedAt": "2023-07-05T18:08:47.503Z",
                    "createdAt": "2023-07-05T18:04:48.811Z",
                    "revision": 13194438697713,
                    "autoClean": False,
                    "updateState": "unset",
                    "updateReason": "",
                    "updateCount": 0,
                },
            }
        },
        "test_full_disconnect_success_single": {
            "response": {
                "status": "Completed",
                "message": "",
                "id": "test_full_disconnect_success_single",
                "data": {
                    "label": "85.L1XX.001568..TWCC",
                    "resourceTypeId": "charter.resourceTypes.ServiceMapper",
                    "productId": "62679989-afbb-4425-bba7-e44c226b7d5b",
                    "domainId": "built-in",
                    "tenantId": "c2ce28a0-eab7-46a3-97fc-ddfacf8c4d67",
                    "shared": False,
                    "subDomainId": "7fd5144c-552f-39a3-9464-08d3b9cfb251",
                    "properties": {
                        "mdso_provisioned": True,
                        "remediation_flag": True,
                        "remediation_attempted": True,
                        "use_alternate_circuit_details_server": False,
                        "device_properties": {"UNINOHAC1ZW": {"MediaType": "RJ-45"}},
                        "service_type": FIA,
                        "circuit_id": "85.L1XX.001568..TWCC",
                    },
                    "discovered": False,
                    "differences": [],
                    "desiredOrchState": "active",
                    "orchState": "active",
                    "reason": "",
                    "tags": {},
                    "providerData": {"templateResources": {}},
                    "updatedAt": "2023-07-05T18:08:47.503Z",
                    "createdAt": "2023-07-05T18:04:48.811Z",
                    "revision": 13194438697713,
                    "autoClean": False,
                    "updateState": "unset",
                    "updateReason": "",
                    "updateCount": 0,
                },
            }
        },
        "test_full_disconnect_success_double": {
            "response": {
                "status": "Completed",
                "message": "",
                "id": "test_full_disconnect_success_double",
                "data": {
                    "label": "85.L1XX.001568..TWCC",
                    "resourceTypeId": "charter.resourceTypes.ServiceMapper",
                    "productId": "62679989-afbb-4425-bba7-e44c226b7d5b",
                    "domainId": "built-in",
                    "tenantId": "c2ce28a0-eab7-46a3-97fc-ddfacf8c4d67",
                    "shared": False,
                    "subDomainId": "7fd5144c-552f-39a3-9464-08d3b9cfb251",
                    "properties": {
                        "mdso_provisioned": True,
                        "remediation_flag": True,
                        "remediation_attempted": True,
                        "use_alternate_circuit_details_server": False,
                        "device_properties": {
                            "UNINOHAC1ZW": {"MediaType": "RJ-45"},
                            "ABCDOHAC1ZW": {"MediaType": "RJ-45"},
                        },
                        "service_type": "ELINE",
                        "circuit_id": "85.L1XX.001568..TWCC",
                    },
                    "discovered": False,
                    "differences": [],
                    "desiredOrchState": "active",
                    "orchState": "active",
                    "reason": "",
                    "tags": {},
                    "providerData": {"templateResources": {}},
                    "updatedAt": "2023-07-05T18:08:47.503Z",
                    "createdAt": "2023-07-05T18:04:48.811Z",
                    "revision": 13194438697713,
                    "autoClean": False,
                    "updateState": "unset",
                    "updateReason": "",
                    "updateCount": 0,
                },
            }
        },
        "test_new_mac_success": {
            "response": {
                "status": "Completed",
                "message": "",
                "id": "test_new_mac_success",
                "data": {
                    "label": "94.L1XX.001657..CHTR",
                    "resourceTypeId": "charter.resourceTypes.ServiceMapper",
                    "productId": "62679989-afbb-4425-bba7-e44c226b7d5b",
                    "domainId": "built-in",
                    "tenantId": "c2ce28a0-eab7-46a3-97fc-ddfacf8c4d67",
                    "shared": False,
                    "subDomainId": "7fd5144c-552f-39a3-9464-08d3b9cfb251",
                    "properties": {
                        "mdso_provisioned": True,
                        "remediation_flag": True,
                        "cpe_swap_note": "ENC Automation CPE SHELF SWAP on PLMTFLES1ZW FROM ETX203AX/2SFP/2UTP2SFP TO FSP 150-GE114PRO-C. ",  # noqa
                        "cpe_swap": {
                            "PLMTFLES1ZW": {
                                "designed": {"model": "ETX203AX/2SFP/2UTP2SFP", "vendor": "RAD"},
                                "installed": {"model": "FSP 150-GE114PRO-C", "vendor": "ADVA"},
                            }
                        },
                        "remediation_attempted": True,
                        "slm_eligible": True,
                        "use_alternate_circuit_details_server": False,
                        "device_properties": {"PLMTFLES1ZW": {"MediaType": "RJ-45", "Management IP": "10.72.66.235"}},
                        "service_type": "ELINE",
                        "circuit_id": "94.L1XX.001657..CHTR",
                    },
                    "discovered": False,
                    "differences": [],
                    "desiredOrchState": "active",
                    "orchState": "active",
                    "reason": "",
                    "tags": {},
                    "providerData": {"templateResources": {}},
                    "updatedAt": "2023-07-14T16:33:33.023Z",
                    "createdAt": "2023-07-14T16:31:03.112Z",
                    "revision": 13194440055393,
                    "autoClean": False,
                    "updateState": "unset",
                    "updateReason": "",
                    "updateCount": 0,
                },
            }
        },
    },
}


def mock_resource_status_response(endpoint, resource_id):
    result = RESOURCE_STATUS_RESPONSES.get(endpoint, "pass")
    if result == "pass":
        return result, 200

    if result.get(resource_id):
        return result[resource_id]["response"], 200

    return "pass", 200


def mock_compliance_response(resource_id, compliance_status, site_order_data=None):
    if "fail" in resource_id:
        if site_order_data and "full" in resource_id:
            compliance_status.update(
                {
                    "ISP Information": [
                        {
                            "ispDisconnectTicket": "WO0000012266615",
                            "site": "400 BEACH DR NE 33701",
                            "engineeringPage": "ENG-04038519",
                        },
                        {
                            "ispDisconnectTicket": "WO00000999999",
                            "site": "600 PRANCING PONIES DR NE 33701",
                            "engineeringPage": "ENG-01234567",
                        },
                    ]
                }
            )
        abort(502, compliance_status)
    compliance_status = mock_success_status(compliance_status)
    if site_order_data and "full" in resource_id:
        compliance_status["ISP Information"] = (
            mock_full_disco_isp_information["ISP Information"]
            if "single" in resource_id
            else mock_double_full_disco_isp_information["ISP Information"]
        )
        compliance_status["ISP Information"] = make_mock_eng_page_dynamic(
            compliance_status["ISP Information"], site_order_data
        )
    mock_success = {
        "test_new_mac_success": plain_compliance_response,
        "test_partial_disconnect_success": compliance_disconnect.wrap_response_as_message,
        "test_full_disconnect_success_single": compliance_disconnect._full_disconnect_success_response,
        "test_full_disconnect_success_double": compliance_disconnect._full_disconnect_success_response,
    }
    return mock_success[resource_id](compliance_status), 200


def mock_success_status(compliance_status):
    for stage in compliance_status:
        compliance_status[stage] = "Successful"
    return compliance_status


def make_mock_eng_page_dynamic(mock_data, request_data):
    mock_data[0]["engineeringPage"] = request_data[0]["engineering_page"]
    if len(request_data) > 1:
        mock_data[1]["engineeringPage"] = request_data[1]["engineering_page"]
    return mock_data


def plain_compliance_response(compliance_status):
    return compliance_status
