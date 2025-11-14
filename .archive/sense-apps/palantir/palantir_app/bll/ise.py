import logging
import re

import palantir_app
from palantir_app.common.endpoints import ISE_NETWORK_DEVICE
from palantir_app.dll import granite
from palantir_app.dll.ise import ise_east_get_cluster, ise_south_get_cluster, ise_west_get_cluster, _ise_post, _ise_put
from palantir_app.dll.sense import beorn_get
import xmltodict
import json
import os
import sys
from palantir_app.common.constants import (
    ISE_ELIGIBLE_DEVICES,
    ISE_INELIGIBLE_VENDORS,
    ISE_STATE_LOCATIONS,
    ISE_STATES_EAST,
    ISE_STATES_WEST,
)

logger = logging.getLogger(__name__)


def get_device_details(hostname, ip):
    vendor, model, role = get_device_details_from_sense(ip)
    core_device = True if vendor in ISE_INELIGIBLE_VENDORS else False
    device_details = {"vendor": vendor, "model": model, "role": role, "core_device": core_device}
    if core_device:
        return device_details

    granite_device_details = granite.get_device_vendor_model_site_category(hostname)
    # use Granite data if SNMP response unusable/null
    snmp_data = ["vendor", "model"]
    for key in snmp_data:
        if not device_details[key]:
            device_details.update({key: granite_device_details[key]})

    site_category = granite_device_details["site_category"]
    for eligible_device in ISE_ELIGIBLE_DEVICES:
        if site_category and eligible_device in site_category:
            return device_details
    # default to core device if site category not in eligible devices
    device_details["core_device"] = True
    return device_details


def cluster_distribution(client_ip_str, region):
    if region in ISE_STATES_EAST:
        ise_cubes = palantir_app.url_config.ISE_CUBES_EAST
    elif region in ISE_STATES_WEST:
        ise_cubes = palantir_app.url_config.ISE_CUBES_WEST
    else:
        ise_cubes = palantir_app.url_config.ISE_CUBES_SOUTH

    client_ip = 0
    pattern = re.compile(r"(\d{1,3}).(\d{1,3}).(\d{1,3}).(\d{1,3})")
    matcher = pattern.search(client_ip_str)
    matchgroup1 = None
    matchgroup2 = None
    matchgroup3 = None
    matchgroup4 = None
    if matcher.groups():
        matchgroup1 = matcher.group(1)
        matchgroup2 = matcher.group(2)
        matchgroup3 = matcher.group(3)
        matchgroup4 = matcher.group(4)
        client_ip = (
            ((16777216) * int(matchgroup1)) + (65536 * int(matchgroup2)) + ((256) * int(matchgroup3)) + int(matchgroup4)
        )
        hashnum = len(ise_cubes) - (client_ip % len(ise_cubes))
        return ise_cubes.get(abs(hashnum))
    else:
        return "NO MATCH"


# beorn call to get ise - vendor model & role from beorn(snmp)
def get_device_details_from_sense(ip):
    beorn_device_endpoint = f"/v1/device?ip={ip}&return_ise_values=True"
    beorn_device_response = beorn_get(beorn_device_endpoint)
    if beorn_device_response:
        return (
            beorn_device_response.get("vendor"),
            beorn_device_response.get("model"),
            beorn_device_response.get("role"),
        )
    else:
        return None, None, None


def onboard_device_in_ise(hostname, ip):
    is_onboarded = False
    device_details = get_device_details(hostname, ip)
    if device_details["core_device"]:
        is_onboarded = True  # must set True to maintain existing 200 status code for v3/ise/device
        return {"message": f"Onboarding Not Attempted: {hostname} is a core device"}, is_onboarded
    create_device_response = create_device_in_ise_cluster(hostname, ip, device_details["vendor"])
    if create_device_response.status_code in (200, 201, 202):
        is_onboarded = True
        return f"Successfully onboarded {hostname} to ISE", is_onboarded
    if create_device_response.status_code == 400:
        # drill down to the str of the error response
        return create_device_response.json()["ERSResponse"]["messages"][0]["title"], is_onboarded
    logger.debug(f"Unexpected ISE response: {create_device_response.json()}")
    return "", is_onboarded


def create_device_in_ise_cluster(tid, ip, vendor):
    state_code = tid[4:6] if tid else None
    location_market = _determine_ise_location(state_code)
    secret = determine_ise_secret(vendor)
    device = {
        "NetworkDevice": {
            "name": tid,
            "description": tid,
            "tacacsSettings": {"sharedSecret": secret, "connectModeOptions": "OFF"},
            "NetworkDeviceIPList": [{"ipaddress": ip, "mask": 32}],
            "NetworkDeviceGroupList": [
                "Access#TWC#EDGE",
                f"Location#All Locations#{location_market}",
                f"Device Type#All Device Types#{vendor}",
            ],
        }
    }

    endpoint = ISE_NETWORK_DEVICE
    ise_url = cluster_distribution(ip, state_code)
    return _ise_post(ise_url, endpoint, device, timeout=60)


def delete_ise_device(hostname, ip):
    device_details = get_device_details(hostname, ip)
    if device_details["core_device"]:
        return None, None
    if ip:
        ise_ids, ise_results = id_lookup_cluster(lookup_type="ipaddress", device_id=ip, delete_device=True)
    else:
        ise_ids, ise_results = id_lookup_cluster(lookup_type="name", device_id=hostname, delete_device=True)
    return ise_ids, ise_results


def get_ise_record_by_id_cluster(ise_id):
    ise_records = {}
    endpoint = f"{ISE_NETWORK_DEVICE}/{ise_id}"
    west_resp = ise_west_get_cluster(endpoint)
    if west_resp:
        ise_records["west"] = west_resp
    else:
        ise_records["west"] = "None"

    east_resp = ise_east_get_cluster(endpoint)
    if east_resp:
        ise_records["east"] = east_resp
    else:
        ise_records["east"] = "None"

    south_resp = ise_south_get_cluster(endpoint)
    if south_resp:
        ise_records["south"] = south_resp
    else:
        ise_records["south"] = "None"
    return ise_records


def get_ise_record_by_id_cluster_specified(ise_id, cluster):
    endpoint = f"{ISE_NETWORK_DEVICE}/{ise_id}"
    cluster_gets = {"west": ise_west_get_cluster, "east": ise_east_get_cluster, "south": ise_south_get_cluster}
    return cluster_gets[cluster](endpoint)


def get_access_type_role(model):
    try:
        sys.path.append(os.path.split(os.path.dirname(__file__))[0])
        parent_dir = os.path.split(os.path.abspath(__file__))[0] + "/"
        static_files_dir = parent_dir.replace("bll", "static_files")
        mapping_file_name = os.path.join(static_files_dir, "ISE_Modeling.xml")

        with open(mapping_file_name, "r") as access_group_mapping_file:
            access_group_file_data = access_group_mapping_file.read()
        access_group_file_dict = xmltodict.parse(access_group_file_data)
        access_group_file_str = json.dumps(access_group_file_dict)
        access_group_file_json = json.loads(access_group_file_str)
        model_access_group_list = access_group_file_json["acsAppTarget"]["acsDeviceTypes"]
        model_access_group_map = next(filter(lambda mapper: mapper["deviceType"] == model, model_access_group_list))
        access_type = model_access_group_map.get("accessGroupName")
        if ":" in access_type:
            split_index = access_type.index(":")
            access_type = access_type[split_index + 1 :].strip()
        return access_type
    except Exception as excp:
        logger.warning(f"Access Type Role not found in Mapping xml for Model {model} : Exception : {excp}")
        return ""


def _determine_ise_location(state_code):
    for state_location in ISE_STATE_LOCATIONS:
        if state_code in ISE_STATE_LOCATIONS[state_location]:
            return state_location
    return None


def determine_ise_secret(vendor):
    vendor_secrets = {
        "ADVA": palantir_app.auth_config.ISE_STATIC_KEY_ADVA,
        "RAD": palantir_app.auth_config.ISE_STATIC_KEY_RAD,
        "CISCO": palantir_app.auth_config.ISE_STATIC_KEY_CISCO,
        "JUNIPER": palantir_app.auth_config.ISE_STATIC_KEY_JUNIPER,
        "ALCATEL": palantir_app.auth_config.ISE_STATIC_KEY_NOKIA,
        "NOKIA": palantir_app.auth_config.ISE_STATIC_KEY_NOKIA,
        "CIENA": palantir_app.auth_config.ISE_STATIC_KEY_CIENA,
    }

    return vendor_secrets.get(vendor.upper(), palantir_app.auth_config.ISE_STATIC_KEY)


def id_lookup_cluster(lookup_type, device_id, delete_device=False):
    endpoint = ISE_NETWORK_DEVICE
    ise_ids = {}
    results = {}
    # Run call against all three endpoints, IDs extracted to 'ise_ids', summary data
    # pulled into results, keys are built from the keys in the for call
    params = {"filter": f"{lookup_type}.EQ.{device_id}"}
    summary_data = {
        "west": ise_west_get_cluster(endpoint, params, delete_device),
        "east": ise_east_get_cluster(endpoint, params, delete_device),
        "south": ise_south_get_cluster(endpoint, params, delete_device),
    }
    region = ""
    for key, data_list in summary_data.items():
        region_result = []
        id_result = []
        for data in data_list:
            if data["SearchResult"]["total"] != 0:
                id_result.append(data["SearchResult"]["resources"][0]["id"])
                region_result.append(data["SearchResult"]["resources"][0])
                region = key
        ise_ids[f"{key}_id"] = id_result
        results[f"{key}_result"] = region_result
        results["region"] = region
    return ise_ids, results


def update_shared_secret(ise_id, shared_secret, ip, state_code):
    endpoint = f"{ISE_NETWORK_DEVICE}/{ise_id}"
    device = {"NetworkDevice": {"tacacsSettings": {"sharedSecret": shared_secret}}}
    base_url = cluster_distribution(ip, state_code)
    update = _ise_put(base_url, endpoint, device)
    # will always return Response obj
    if update.status_code in (200, 201, 202):  # it worked yay
        return True
    return False
