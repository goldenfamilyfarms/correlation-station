class MockResponseText:
    def __init__(self, text, status_code=200):
        self.status_code = status_code
        self.text = text


class MockResponseJson:
    def __init__(self, response_data, status_code=200):
        self.status_code = status_code
        self.response_data = response_data

    def json(self):
        return self.response_data


def mock_correlation_id_good(*args, **kwargs):
    res_data = " d9eeeeb3-8e00-4c01-a065-008f60f0de95 "

    return MockResponseText(res_data, 200)


def mock_correlation_id_bad_status(*args, **kwargs):
    res_data = " d9eeeeb3-8e00-4c01-a065-008f60f0de95 "

    return MockResponseText(res_data, 500)


def mock_correlation_id_bad(*args, **kwargs):
    raise ConnectionError


def mock_auth_token_good(*args, **kwargs):
    data = {
        "message": None,
        "status": "OK",
        "code": 200,
        "jsonResponse": '{"nice-authentication-token":"eyJhbGciOiJBMTI4S1ciLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0.S1baD1EuSd9lYyVp79Eq2hBR6fLoOn3Jo0LDDjnJhCEax1uBq78rEg.Atyb6PzKQ9joRODUXhGZtA.0pAe4NMaWzXPYETWe-DshzDj0bAMlMrEyR4swbB9kDhJC2hofnN2B8nb3Gmom46IhovCQFsHg8TbGr-6Re5xOvnwGCPu77ltKskmOSl-rft2s9yjm-f6IqJm0R74QzZB4dqPSEsK9ng2mYwpkPe21x5LeWMoQdvU3ls0fWOjDdzkfgGkbePHGf73LphBLUum2iTbd60EJuMvMaFqqP5Jdg.oZvj-UyzB0rUpz0zIO718w"}',
    }
    return MockResponseJson(data, 200)


def mock_auth_token_bad_status(*args, **kwargs):
    data = {"jsonResponse": {"nice-authentication-token": "3454353543"}}
    return MockResponseJson(data, 500)


def mock_execute_rule_check_200(*args, **kwargs):
    data = {
        "message": None,
        "status": "OK",
        "code": 200,
        "jsonResponse": '{"RESPONSE":{"TOTAL":41,"RECORDS":[],"FIELDS":["RULE##","RULE_VALUE##","RULE_STATUS##","RESULT_COMMENT##","GRANITE_OBJ_TYPE","OPERATION","PATH_CIRC_INST_ID","PATH_NAME","CUR/REV","PATH_REVISION","OBJECT_VALUE","PATH_STATUS","PATH_BANDWIDTH","PATH_CATEGORY","PATH_TOPOLOGY","PATH_NBR_MEMBERS","PATH_NBR_CHANNELS","PATH_CUSTOMER_ID","PATH_A_SIDE_CUSTOMER_ID","PATH_Z_SIDE_CUSTOMER_ID","PATH_ORDER_NUM","PATH_A_SIDE_SITE_NAME","PATH_Z_SIDE_SITE_NAME","PATH_CH_RANGE_START","PATH_CH_RANGE_END","CHANNEL_ASSIGNMENTS","CURRENT/REVISION","REV_NBR","CIRC_PATH_INST_ID","GROUP_NAME","VAL_ATTR_NAME","ATTR_VALUE","REL_ORDER","REVISION","INST_VERSION","PATH_LEG_A_SITE","PATH_LEG_NAME","PATH_LEG_Z_SITE","PATH_INST_ID","LEG_INST_ID","RENAME","SEQUENCE","SUB_SEQUENCE","MEMBER_NUMBER","ELEMENT_TYPE","CONNECTOR_TYPE","E_ELEMENT_INST_ID","E_SITE","E_EQUIPMENT","E_SLOT","E_PARENT_SLOT","E_GRANDPARENT_SLOT","E_PORT","E_CABLE","E_PAIR_STRAND","E_SEGMENT","E_PATH","E_PATH_REVISION","E_PATH_CURRENT/REVISION","E_PATH_LEG_NAME","E_CHANNEL_NAME","E_NETWORK","E_NETWORK_REVISION","E_NETWORK_CURRENT/REVISION","E_SUBRATE","SITE_NAME","EQUIP_NAME","SLOT","PORT_NAME","PORT_INST_ID","PARENT_PATH_NAME","PARENT_PATH_INST_ID","PARENT_PATH_REVISION","PARENT_PATH_CURRENT/REV","PATH_CH_INST_ID","PATH_CH_CHANNEL_NAME"]}}',
    }
    return MockResponseJson(data, 200)


def mock_execute_rule_check_500(*args, **kwargs):
    data = "test error"
    return MockResponseText(data, 500)


def mock_execute_rule_check_502(*args, **kwargs):
    raise Exception("testing")


bad_return = [
    {
        "REVISION": 1,
        "RULE##": "Z-Side Customer is required.",
        "GRANITE_OBJ_TYPE": "PATH",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Z-Side Customer is missing.",
        "RULE_STATUS##": "FAIL",
        "PATH_Z_SIDE_CUSTOMER_ID": "*ERROR*",
    },
    {
        "REVISION": 1,
        "RULE##": "Order Number is required.",
        "GRANITE_OBJ_TYPE": "PATH",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Order Number is missing.",
        "RULE_STATUS##": "FAIL",
        "PATH_ORDER_NUM": "*ERROR*",
    },
    {
        "REVISION": 1,
        "RULE##": "Path Leg A-Side Site must match Path A-Side Site.",
        "GRANITE_OBJ_TYPE": "PATH_LEG",
        "PATH_LEG_NAME": "1",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "PATH_LEG_A_SITE": "AUSDTXIR-NSM DEV TESTING/CUSTOMER SITE/11921 N MO PAC EXPY",
        "OBJECT_VALUE": "AUSDTXIR-CHARTER LAB/3F/11921 N MOPAC EXPY",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "LEG_INST_ID": 2059492,
        "RESULT_COMMENT##": "Path Leg  (1) A-Side Site does not match Path A-Side Site.",
        "RULE_STATUS##": "FAIL",
    },
    {
        "REVISION": 1,
        "RULE##": "Valid IPv4 Service Type required.",
        "GRANITE_OBJ_TYPE": "PATH_UDA",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "GROUP_NAME": "INTERNET SERVICE ATTRIBUTES",
        "RULE_VALUE##": "'LAN', 'ROUTED', 'BGP', 'LEGACY-MULTI'",
        "ATTR_VALUE": "*ERROR*",
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Invalid IPv4 Service Type 'NULL'.",
        "VAL_ATTR_NAME": "IPv4 SERVICE TYPE",
        "RULE_STATUS##": "FAIL",
    },
    {
        "REVISION": 1,
        "RULE##": "Valid IPv6 Service Type required.",
        "GRANITE_OBJ_TYPE": "PATH_UDA",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "GROUP_NAME": "INTERNET SERVICE ATTRIBUTES",
        "RULE_VALUE##": "'NONE', 'ROUTED', 'BGP', 'LEGACY-MULTI'",
        "ATTR_VALUE": "*ERROR*",
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Invalid IPv6 Service Type 'NULL'.",
        "VAL_ATTR_NAME": "IPv6 SERVICE TYPE",
        "RULE_STATUS##": "FAIL",
    },
    {
        "REVISION": 1,
        "RULE##": "Valid LEGACY_PATH/SOURCE UDA value required.",
        "GRANITE_OBJ_TYPE": "PATH_UDA",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "GROUP_NAME": "LEGACY_PATH",
        "ATTR_VALUE": "*ERROR*",
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Invalid LEGACY_PATH/SOURCE value 'NULL' entered.",
        "VAL_ATTR_NAME": "SOURCE",
        "RULE_STATUS##": "FAIL",
    },
    {
        "REVISION": 1,
        "RULE##": "Valid SLM Eligibility value required.",
        "GRANITE_OBJ_TYPE": "PATH_UDA",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "GROUP_NAME": "CIRCUIT SOAM PM",
        "RULE_VALUE##": "'ELIGIBLE DESIGN', 'unsupported DESIGN', 'INELIGIBLE SERVICE'",
        "ATTR_VALUE": "*ERROR*",
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Invalid SLM Eligibility value 'NULL'.",
        "VAL_ATTR_NAME": "SLM ELIGIBILITY",
        "RULE_STATUS##": "FAIL",
    },
    {
        "REVISION": 1,
        "RULE##": "Port UDA INCOMING VLAN OPERATION must be set to PUSH.",
        "GRANITE_OBJ_TYPE": "PORT_UDA",
        "REV_NBR": 1,
        "PATH_CIRC_INST_ID": 1816227,
        "PATH_REVISION": 1,
        "PATH_INST_ID": 1816227,
        "SITE_NAME": "AUSDTXIR-CHARTER LAB/3F/11921 N MOPAC EXPY",
        "PORT_INST_ID": 103978562,
        "GROUP_NAME": "VLAN INFO",
        "RULE_VALUE##": "PUSH",
        "ATTR_VALUE": "*ERROR*",
        "PATH_NAME": "51.L1XX.802896..CHTR",
        "OPERATION": "UPDATE",
        "CIRC_PATH_INST_ID": 1816227,
        "RESULT_COMMENT##": "Invalid Port UDA value INCOMING VLAN OPERATION 'SWAP'.",
        "SLOT": "CHASSIS PORTS",
        "EQUIP_NAME": "AUSDTXIRJZW/999.9999.999.99/SWT",
        "VAL_ATTR_NAME": "INCOMING VLAN OPERATION",
        "RULE_STATUS##": "FAIL",
        "PORT_NAME": "03",
    },
]
