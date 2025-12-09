class MockResponseJson:
    def __init__(self, response_data, status_code=200):
        self.status_code = status_code
        self.response_data = response_data

    def json(self):
        return self.response_data


def mock_auth_response(*args, **kwargs):
    status_code = 200
    return MockResponseJson(mdso_auth_token, status_code)


def mock_proc_response(*args, **kwargs):
    status_code = 200
    return MockResponseJson(mdso_session_req_orchstate, status_code)


def mock_good_response(*args, **kwargs):
    status_code = 200
    return MockResponseJson(mdso_session_good_orchstate, status_code)


def mock_bad_response(*args, **kwargs):
    status_code = 200
    return MockResponseJson(mdso_session_bad_orchstate, status_code)


def mock_delete_response(*args, **kwargs):
    status_code = 200
    return MockResponseJson({}, status_code)


def mock_resync_mdso_device(*args, **kwargs):
    return None


""" MDSO Mock Responses """


mdso_auth_token = {
    "user": "106bbca9-309f-42c4-b441-22ffefc11883",
    "loginDetail": {
        "time": "2020-10-12T17:00:35Z",
        "ipAddress": "142.136.4.146",
        "userAgent": "PostmanRuntime/7.26.5",
        "sessionId": "f4e43e78-cc49-413f-8d4c-2f51d832dcac",
        "sessionType": "Machine",
    },
    "expiresIn": 86400,
    "accessToken": "1732f9394cf20b0efaa0",
    "tokenType": "bearer",
    "createdTime": "2020-10-12T17:00:35Z",
    "expirationTime": "2020-10-13T17:00:35Z",
    "inactiveExpirationTime": "null",
    "isSuccessful": True,
    "sessionId": "f4e43e78-cc49-413f-8d4c-2f51d832dcac",
    "userTenantUuid": "-1",
    "failedLoginAttempts": 0,
    "lastSuccessIpAddress": "142.136.4.114",
    "lastSuccessLogin": "2020-10-12 16:41:55+00:00",
}

mdso_session_bad_orchstate = {
    "items": [
        {
            "id": "609d679b-e7fc-4e9f-ae7b-9822c98fce10",
            "label": "WHWECAIZ1AW",
            "resourceTypeId": "junipereq.resourceTypes.NetworkFunction",
            "productId": "5c043a14-f61f-4d62-856b-ac4cb7aadcb5",
            "tenantId": "c2ce28a0-eab7-46a3-97fc-ddfacf8c4d67",
            "shared": False,
            "subDomainId": "5c043a11-b7be-4979-b53a-df8995709a5a",
            "properties": {
                "sessionProfile": "5dc05e21-9731-4315-a5b0-be9bb4ad84d1",
                "typeGroup": "/typeGroups/Juniper",
                "authentication": {"netconf": {"username": "sorceror", "password": "secrets!"}},
                "communicationState": "UNAVAILABLE",
                "ipAddress": "WHWECAIZ1AW.CHTRSE.COM",
                "connection": {
                    "netconf": {"configMode": "private", "hostport": 22},
                    "hostname": "WHWECAIZ1AW.CHTRSE.COM",
                },
                "timeout": 0,
            },
            "providerResourceId": "bpo_5c043a11-b7be-4979-b53a-df8995709a5a_609d679b-e7fc-4e9f-ae7b-9822c98fce10",
            "discovered": False,
            "differences": [],
            "desiredOrchState": "active",
            "orchState": "unknown",
            "reason": "",
            "tags": {},
            "providerData": {},
            "updatedAt": "2021-05-13T17:53:40.432Z",
            "createdAt": "2021-05-13T17:53:31.101Z",
            "revision": 13194231446544,
            "autoClean": False,
            "updateState": "unset",
            "updateReason": "",
            "updateCount": 0,
        }
    ],
    "total": 1,
    "offset": 0,
    "limit": 1000,
}

mdso_session_good_orchstate = {
    "items": [
        {
            "id": "5ef49d03-ae41-4f05-bb22-1cf0c52f7b5a",
            "label": "AUSDTXIR2CW",
            "resourceTypeId": "junipereq.resourceTypes.NetworkFunction",
            "productId": "5d25169c-8d4c-487b-ad32-a41206b830aa",
            "tenantId": "22aba2b0-ccdc-4b8e-a2e2-517176b15d4b",
            "shared": False,
            "subDomainId": "5d25169b-0d41-4f88-b478-17e29329b1eb",
            "properties": {
                "serialNumber": "JN111D794AFB",
                "sessionProfile": "5d251753-00f1-45bf-87e4-cc0099e9719a",
                "typeGroup": "/typeGroups/Juniper",
                "deviceVersion": "JuniperMX480",
                "resourceType": "JuniperMX480",
                "swImage": "JUNOS 16.1R6-S2.3",
                "authentication": {"netconf": {"username": "magician", "password": "obscurities"}},
                "communicationState": "AVAILABLE",
                "ipAddress": "AUSDTXIR2CW.DEV.CHTRSE.COM",
                "swVersion": "JUNOS 16.1R6-S2.3",
                "swType": "JUNOS",
                "connection": {
                    "netconf": {"configMode": "private", "hostport": 830},
                    "hostname": "AUSDTXIR2CW.DEV.CHTRSE.COM",
                },
                "type": "JuniperMX480",
                "timeout": 120,
            },
            "providerResourceId": "bpo_5d25169b-0d41-4f88-b478-17e29329b1eb_5ef49d03-ae41-4f05-bb22-1cf0c52f7b5a",
            "discovered": False,
            "differences": [],
            "desiredOrchState": "active",
            "orchState": "active",
            "reason": "",
            "tags": {},
            "providerData": {},
            "updatedAt": "2020-10-08T16:18:21.675Z",
            "createdAt": "2020-06-25T12:48:03.736Z",
            "revision": 13194142604955,
            "autoClean": False,
            "updateState": "unset",
            "updateReason": "",
            "updateCount": 0,
        }
    ],
    "total": 1,
    "offset": 0,
    "limit": 1000,
}

mdso_session_req_orchstate = {
    "items": [
        {
            "id": "5ef49d03-ae41-4f05-bb22-1cf0c52f7b5a",
            "label": "AUSDTXIR2CW",
            "resourceTypeId": "junipereq.resourceTypes.NetworkFunction",
            "productId": "5d25169c-8d4c-487b-ad32-a41206b830aa",
            "tenantId": "22aba2b0-ccdc-4b8e-a2e2-517176b15d4b",
            "shared": False,
            "subDomainId": "5d25169b-0d41-4f88-b478-17e29329b1eb",
            "properties": {
                "serialNumber": "JN111D794AFB",
                "sessionProfile": "5d251753-00f1-45bf-87e4-cc0099e9719a",
                "typeGroup": "/typeGroups/Juniper",
                "deviceVersion": "JuniperMX480",
                "resourceType": "JuniperMX480",
                "swImage": "JUNOS 16.1R6-S2.3",
                "authentication": {"netconf": {"username": "magician", "password": "obscurities"}},
                "communicationState": "AVAILABLE",
                "ipAddress": "AUSDTXIR2CW.DEV.CHTRSE.COM",
                "swVersion": "JUNOS 16.1R6-S2.3",
                "swType": "JUNOS",
                "connection": {
                    "netconf": {"configMode": "private", "hostport": 830},
                    "hostname": "AUSDTXIR2CW.DEV.CHTRSE.COM",
                },
                "type": "JuniperMX480",
                "timeout": 120,
            },
            "providerResourceId": "bpo_5d25169b-0d41-4f88-b478-17e29329b1eb_5ef49d03-ae41-4f05-bb22-1cf0c52f7b5a",
            "discovered": False,
            "differences": [],
            "desiredOrchState": "active",
            "orchState": "active",
            "reason": "",
            "tags": {},
            "providerData": {},
            "updatedAt": "2020-10-08T16:18:21.675Z",
            "createdAt": "2020-06-25T12:48:03.736Z",
            "revision": 13194142604955,
            "autoClean": False,
            "updateState": "unset",
            "updateReason": "",
            "updateCount": 0,
        }
    ],
    "total": 1,
    "offset": 0,
    "limit": 1000,
}
