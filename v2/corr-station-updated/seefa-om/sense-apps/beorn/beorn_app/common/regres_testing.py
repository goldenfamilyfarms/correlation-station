import logging

logger = logging.getLogger(__name__)


RESPONSES = {
    "/v1/granite_status": {"put": "Circuit status updated to Auto-Provisioned"},
    "/v3/service": {
        "post": {"resource_id": "79797979-7979-7979-7979-797979797979"},
        "put": {
            "New Install": {"resource_id": "test_new_mac_success"},
            "Change Request": {"resource_id": "test_new_mac_success"},
            "Partial Disconnect": {"resource_id": "test_partial_disconnect_success"},
            "Full Disconnect": {"resource_id": "test_full_disconnect_success_single"},
            "Double Full Disconnect": {"resource_id": "test_full_disconnect_success_double"},
        },
    },
}


def regression_testing_check(endpoint, cid, request="post", validate_cid=True, order_type=None):
    if validate_cid:
        return _valid_cid_regression_testing_check(endpoint, cid, request)
    return _get_mock_response(endpoint, request, order_type)


def _valid_cid_regression_testing_check(endpoint, cid, request):
    result = "pass"

    if not all((cid.startswith("51.L1XX.9999"), cid.endswith(".CHTR"))):
        return result

    # try to extract last 2 digits from CID
    try:
        num = int(cid.split(".")[-2][-2:])
    except Exception:
        logger.error(f"Wrong CID format: {cid}")
        return result

    if 69 < num < 80:
        result = _get_mock_response(endpoint, request)
    else:
        pass

    return result


def _get_mock_response(endpoint, request, order_type=None):
    result = "pass"
    endpoint_responses = RESPONSES.get(endpoint)
    if not endpoint_responses:
        return result
    if not order_type:
        return endpoint_responses.get(request, result)
    if not endpoint_responses.get(request):
        return result
    return endpoint_responses[request].get(order_type, result)
