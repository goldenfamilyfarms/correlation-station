from flask_restx import fields
from beorn_app.dll.sense import sense_get
import logging

logger = logging.getLogger(__name__)


def validate_rphy_payload(rphy_payload):
    missing_fields = []

    required_fields = [
        "channels",
        "zone_num",
        "zone_name",
        "rpd_des",
        "signal_type",
        "device_type",
        "cid",
        "mac_address",
        "rpd",
        "cmtsipAddress",
        "service_group_data",
        "ptp_ips",
    ]

    for field in required_fields:
        if field == "channels":
            if len(rphy_payload["properties"][field]) < 1:
                missing_fields.append(field)
        elif field == "service_group_data":
            missing_service_group_fields = validate_service_group(rphy_payload)
            missing_fields += missing_service_group_fields
        else:
            if rphy_payload["properties"].get(field, None) is None:
                missing_fields.append(field)

    return missing_fields


def check_for_mac_arping(payload, mac_address):
    """
    Check PE for Pebble MAC address being in arp table
    """
    endpoint = "v1/device/" + payload["hostname"]
    params = {"args": "4063", "cmd": "show_arp_irb", "attempt_onboarding": False}
    mac_result = sense_get("arda", endpoint, params=params)
    logger.info(f"MAC: {mac_result} FROM DEVICE:{payload['hostname']}")
    if mac_result.get("result"):
        for entry in mac_result["result"]["properties"]["result"]:
            if mac_address == entry["mac-address"]:
                return True
    return False


def validate_service_group(rphy_payload):
    service_group_required = ["name", "dst_address", "session_port", "src_address"]

    service_groups = rphy_payload["properties"]["service_group_data"]

    missing_fields = set(service_group_required) - {field for service_group in service_groups for field in service_group}

    return list(missing_fields)


def validate_ptp_data(rphy_payload):
    ptp_required = ["PTP", "PTP_GW"]

    ptp_ips = rphy_payload["properties"]["ptp_ips"]

    missing_fields = set(ptp_required) - {field for ptp_ip in ptp_ips for field in ptp_ip}

    return missing_fields


def expected_payloads(api):
    models = {"rphy": rphy_expected_payload(api)}
    return models


def rphy_expected_payload(api):
    """
    Creates the expected payload template for Managed RPHY endpoint
    :param api: api
    :return: api.model
    """

    service_group_data = api.model(
        "service_group_data",
        {
            "name": fields.String(),
            "dst_address": fields.String(),
            "session_port": fields.String(),
            "src_address": fields.String(),
        },
    )

    ptp_ip_data = api.model("ptp_ips", {"PTP": fields.String(), "PTP_GW": fields.String()})

    properties = api.model(
        "properties",
        {
            "operationType": fields.String(),
            "cmtsipAddress": fields.String(),
            "cmtsTid": fields.String(),
            "cid": fields.String(),
            "mac_address": fields.String(),
            "device_type": fields.String(),
            "channels": fields.List(fields.Integer),
            "signal_type": fields.String(),
            "rpd": fields.String(),
            "rpd_des": fields.String(),
            "zone_name": fields.String(),
            "zone_num": fields.String(),
            "service_group_data": fields.List(fields.Nested(service_group_data)),
            "ptp_ips": fields.List(fields.Nested(ptp_ip_data)),
        },
    )

    payload = api.model("payload", {"resourceTypeId": fields.String(), "properties": fields.Nested(properties)})

    return payload


def response_models(api):
    models = {}
    models["bad_request"] = api.model("bad_request", {"message": fields.String(example="Brief failure description")})

    models["server_error"] = api.model(
        "app_error", {"message": fields.String(example="MDSO failed to process the request")}
    )

    models["rphy_get_ok"] = api.model(
        "Successfully retrieved data",
        {
            "rphy_resource_id": fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"),
            "operation_ids": fields.List(cls_or_instance=fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")),
        },
    )

    models["created"] = api.model(
        "Successfully Initiated Provisioning",
        {"rphy_resource_id": fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")},
    )

    return models
