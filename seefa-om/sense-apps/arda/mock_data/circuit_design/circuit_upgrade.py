from base64 import b64encode

# common vars
pathid = "21.L1XX.006991..TWCC"
credentials = b64encode(b"sense_api:$en$e_api").decode("utf-8")
arda_url = f"/arda/v1/circuitpath/{pathid}"
head = {"accept": "application/json", "Authorization": f"Basic {credentials}"}
bad_headers = {"accept": "application/json", "Authorization": "Something Wrong"}
prod_name = "EP-LAN (Fiber)"

# mock payloads
normal_upgrade = {
    "service_type": "bw_upgrade",
    "product_name": "Fiber Internet Access",
    "engineering_id": "ENG-12345689",
    "cid": "21.L1XX.006991..TWCC",
    "bw_speed": "500",
    "bw_unit": "Mbps",
    "change_reason": "change request",
    "engineering_name": "ENG-12345689",
    "engineering_job_type": "Upgrade",
    "connector_type": "N/A",
    "uni_type": "Trunked",
    "spectrum_primary_enni": "N/A",
    "spectrum_secondary_enni": "N/A",
    "primary_vlan": "N/A",
    "secondary_vlan": "N/A",
}


mock_granite_bw_check_good = [
    {
        "aSideCustomer": "TWC - LANCASTER NY",
        "bandwidth": "500 Mbps",
        "category": "ETHERNET",
        "orderingCustomer": "TWC - LANCASTER NY",
        "pathId": "99.L3XX.000001..TWCC",
        "pathInService": "2012-09-06 12:00:00.0",
        "pathRev": "1",
        "servicePriority": "YES",
        "status": "Live",
        "cloudService": "vCLOUD",
        "endChanNbr": "1000",
        "instanceProtocol": "CCC",
        "managedService": "YES",
        "ofEnnis": "5",
        "pathInstanceId": "227563",
        "serviceMedia": "FIBER",
        "slmEligibility": "ELIGIBLE DESIGN",
        "slmStatus": "PRODUCTION",
        "startChanNbr": "1",
        "vcClass": "11111",
        "virtualChans": "D",
    }
]


mock_granite_bw_check_bad = [
    {
        "instId": "0",
        "retCode": 2,
        "httpCode": 200,
        "retString": "GKRestService.getPathRecords() failed No records found with the specified search criteria...",
    }
]

mock_granite_bw_update_good = {"cid": pathid, "path_instance": "1202463", "bandwidth": "100 Mbps"}

mock_granite_bw_update_bad = {
    "instId": "0",
    "retCode": 2,
    "httpCode": 0,
    "retString": "workPath request failed while attempting to update Path "
    "com.granite.asi.exception.ServiceException: Unable to "
    "understand path-specific bitrate string for path "
    "51.L1XX.008342..CHTR. -{PATH_SPEC_BITRATE_STR=300 Bps, "
    "PATH_INST_ID=1202463, procType=update, "
    "GRANITE_USER=ws-mulesoft}",
}

mock_granite_status_update_good = {
    "instId": "1202463",
    "rev": "1",
    "pathId": "51.L1XX.008342..CHTR",
    "retCode": 0,
    "retString": "Path Updated",
    "status": "Designed",
}

mock_granite_status_update_bad = {
    "instId": "0",
    "retCode": 2,
    "httpCode": 0,
    "retString": "workPath request failed while attempting to update Path "
    "com.granite.asi.exception.ServiceException: live is not a "
    "valid path/network status for this revision. "
    "-{PATH_STATUS=live, PATH_TOPOLOGY=Point to Point, "
    "PATH_TYPE=ETHERNET, PATH_INST_ID=1202463, procType=update, "
    "GRANITE_USER=ws-mulesoft}",
}

mock_granite_rev_create_resp_good = {
    "pathId": "27.L1XX.000002.GSO.TWCC",
    "instId": "0",
    "pathRev": "2",
    "status": "Planned",
    "pathInstanceId": "1203384",
    "retString": "Revision Added",
}


mock_granite_rev_create_resp_bad = {
    "instId": "0",
    "retCode": 2,
    "httpCode": 500,
    "retString": "GKRestService.updatePath() failed FAILURE retCode = 2",
}


mock_intake_payload_good = {"operation": "bw_downgrade", "operation_payload": {"bw_unit": "M", "bw_value": "100"}}


mock_intake_payload_bad = {"operation": "invalid_command", "operation_payload": {"bw_unit": "M", "bw_value": "100"}}


class MockResponse:
    def __init__(self, json_data, status_code=401):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


# monkeypatch functions
def mock_granite_get_resp_good(_):
    return mock_granite_bw_check_good


def mock_nice_gsip_resp_good(*args, **kwargs):
    return True, []


def mock_nice_gsip_resp_bad(*args):
    return False, [1]


def mock_granite_rev_create_good(_, __):
    return mock_granite_rev_create_resp_good


def mock_granite_rev_create_bad(_, __):
    return mock_granite_rev_create_resp_bad


def mock_granite_bw_update_resp_good(url, *args, **kwargs):
    return mock_granite_bw_update_good


def mock_granite_status_resp_good(url, _):
    return mock_granite_status_update_good


def mocked_put_responses_good(*args, **kwargs):
    if "CREATE_REVISION" in str(args):
        return {
            "pathId": f"{pathid}",
            "instId": "0",
            "pathRev": "2",
            "status": "Auto-Planned",
            "pathInstanceId": "1234",
            "retString": "Revision Added",
        }
    elif "PATH_BANDWIDTH" in str(args):
        return {
            "pathId": f"{pathid}",
            "instId": "0",
            "pathRev": "2",
            "status": "Auto-Planned",
            "pathInstanceId": "1234",
            "retString": "Revision Added",
        }
    elif "Designed" in str(args):
        return {
            "instId": "0",
            "rev": "1",
            "pathId": f"{pathid}",
            "retCode": 0,
            "retString": "Path Updated",
            "status": "Designed",
        }
    else:
        return {
            "pathId": f"{pathid}",
            "instId": "0",
            "pathRev": "2",
            "status": "Auto-Planned",
            "pathInstanceId": "1234",
            "retString": "Revision Added",
        }
