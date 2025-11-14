"""-*- coding: utf-8 -*-

WIA Mapper

Versions:
    9/4/24 - Initial version - robert.j.saunders@charter.com
"""

import requests
import sys
import re
from scripts.configmodeler.utils import NetworkCheckUtils
from scripts.serviceMapper.common import Common


class Activate(Common):
    def process(self):
        self.utils = NetworkCheckUtils()
        self.initialize()
        self.sentinel_jwt = self.auth_sentinel()

        sentinel_data = self.get_sentinel_data()
        cradlepoint_data = self.get_cradlepoint_data()

        self.logger.info(f"Sentinel Data: {sentinel_data}")
        self.logger.info(f"Cradlepoint Data: {cradlepoint_data}")

        sentinel_model = self.create_sentinel_model(sentinel_data)
        cradlepoint_model = self.create_cradlepoint_model(cradlepoint_data)

        self.sentinel_diffs, self.cradelpoint_diffs = self.compliance_process(
            sentinel_data, sentinel_model, cradlepoint_data, cradlepoint_model
        )

        if self.sentinel_diffs or self.cradelpoint_diffs:
            self.post_to_resource()

    def initialize(self):
        props = self.resource["properties"]
        self.cid = props["circuit_id"]
        self.device_properties = props["device_properties"]
        self.tid = self.device_properties["tid"]
        # Model cleanup from granite
        self.model = self.device_properties["device_model"]
        for model in ["E100", "CBA850", "CB850", "W1850", "W1855"]:
            if self.model.find(model) != -1:
                self.model = model
                break
        self.wia_constants = self.get_wia_contants_resource()

    def stop_report_fail(self, failure_status):
        # Stop Resource, add a report to the failure_status message on resource and then fail with exit_error
        self.bpo.resources.patch_observed(
            self.resource_id,
            data={"properties": {"failure_status": failure_status}},
        )
        self.exit_error(failure_status)

    def stop_report_exit(self, failure_status):
        # Lets you halt the process & send info to the resource about the error without causing it to outright fail
        self.bpo.resources.patch_observed(
            self.resource_id,
            data={"properties": {"failure_status": failure_status}},
        )
        sys.exit(0)

    def post_to_resource(self):
        self.bpo.resources.patch_observed(
            self.resource_id,
            data={
                "properties": {
                    "service_differences": {
                        "sentinel": self.sentinel_diffs,
                        "cradlepoint": self.cradelpoint_diffs,
                    }
                }
            },
        )

    def post_serial_number_to_resource(self, serial_number):
        self.bpo.resources.patch_observed(
            self.resource_id,
            data={
                "properties": {
                    "device_properties": {
                        "serial_number": serial_number,
                    }
                }
            },
        )

    def get_wia_contants_resource(self):
        return_value = None

        resources = self.get_active_resources(
            self.BUILT_IN_WIA_CONSTANT_TYPE, obfuscate=False
        )
        if len(resources) > 0:
            return_value = resources[0]

        return return_value["properties"]

    def gather_values_to_compare(self, devices):
        def get_model_type(device_name):
            delimiters = ["Cradlepoint ", "Cisco Meraki ", "Kajeet ENT-"]
            regex_pattern = "|".join(map(re.escape, delimiters))
            return re.split(regex_pattern, device_name)[-1]

        new_device_list = []
        for device in devices:
            new_device_list.append(
                {
                    "rate_plan": device.get("ratePlanDescription"),
                    "model": get_model_type(device.get("deviceName")),
                    "name": get_model_type(device.get("deviceName")),
                    "service_code": device.get("ratePlan"),
                }
            )
        return new_device_list

    def confirm_sentinel_devices_match(self, devices):
        devices = self.gather_values_to_compare(devices)
        self.logger.info(f"Sentinel devices being compared: {devices}")
        first_device = devices[0]
        for device in devices[1:]:
            if device != first_device:
                device_differences = self.get_dictionary_differences(
                    device, first_device
                )
                self.logger.info(
                    f"Mismatch found between devices: {device_differences}"
                )
                return device_differences
        return None

    def sentinel_get(self, endpoint, payload=None):
        SENTINEL_URL = "https://sentinel-api.kajeet.com"
        url = f"{SENTINEL_URL}/{endpoint}"

        retry_max = 2
        retry = 0

        while retry <= retry_max:
            try:
                retry += 1
                headers = {"Authorization": f"Bearer {self.sentinel_jwt}"}
                r = requests.get(url, headers=headers, params=payload, verify=False)

                if r.status_code == 200:
                    return r.json()
                else:
                    msg = "Sentinel API Error: Invalid Response: {} - {}".format(
                        r.status_code, r.text
                    )
                    if "NO DEVICES FOUND" in r.text.upper():
                        self.stop_report_exit(msg)
                    self.stop_report_fail(msg)

            except requests.ConnectTimeout:
                self.stop_report_fail("Sentinel API Error: Connection Timeout")
            except (ConnectionError, requests.ConnectionError):
                self.stop_report_fail("Sentinel API Error: Connection Error")
            except requests.ReadTimeout:
                self.stop_report_fail("Sentinel API Error: Read Timeout")

    def cradlepoint_get(self, endpoint, payload=None):
        CRADLEPOINT_URL = "https://www.cradlepointecm.com/api"
        url = f"{CRADLEPOINT_URL}/{endpoint}"
        headers = {
            "X-ECM-API-ID": self.wia_constants["cradlepoint_api_keys"]["ecm_api_id"],
            "X-ECM-API-KEY": self.wia_constants["cradlepoint_api_keys"]["ecm_api_key"],
            "X-CP-API-ID": self.wia_constants["cradlepoint_api_keys"]["cp_api_id"],
            "X-CP-API-KEY": self.wia_constants["cradlepoint_api_keys"]["cp_api_key"],
        }

        retry_max = 2
        retry = 0

        while retry <= retry_max:
            try:
                retry += 1
                r = requests.get(url, headers=headers, params=payload, verify=False)

                if r.status_code == 200:
                    return r.json()
                else:
                    self.stop_report_fail(
                        "Cradlepoint API Error: Invalid Response: {} - {}".format(
                            r.status_code, r.text
                        )
                    )
            except requests.ConnectTimeout:
                self.stop_report_fail("Cradlepoint API Error: Connection Timeout")
            except (ConnectionError, requests.ConnectionError):
                self.stop_report_fail("Cradlepoint API Error: Connection Error")
            except requests.ReadTimeout:
                self.stop_report_fail("Cradlepoint API Error: Read Timeout")

    def get_sentinel_data(self):
        # Gather Data with token as auth

        SENTINEL_DEVICE = "sentinel/api/v1.0/devices/CHARTERENT"
        SENTINEL_MANAGED_WIRELESS = (
            "sentinel/api/v1.0/managedwireless/devices/CHARTERENT/"
        )

        querystring = {
            "sort": "CIRCUIT_ID",
            "sortDir": "ASC",
            "searchValue": self.cid.split("..")[0],
            "offset": "0",
            "limit": "10",
        }

        sentinel_device_data = self.sentinel_get(SENTINEL_DEVICE, querystring)

        if sentinel_device_data["totalCount"] > 1:
            self.logger.info(f"Multiple devices found: {sentinel_device_data}")
            # If there are multiple devices, we must confirm that they all have the same values
            device_mismatches = self.confirm_sentinel_devices_match(
                sentinel_device_data["devices"]
            )
            if device_mismatches:
                msg = f"Sentinel API Error: Multiple Devices Found With Mismatched Data: {device_mismatches}"
                self.stop_report_exit(msg)
        sentinel_device_data = sentinel_device_data["devices"][0]

        mdn = sentinel_device_data["mdn"]
        managed_device_data = self.sentinel_get(SENTINEL_MANAGED_WIRELESS + mdn)

        self.post_serial_number_to_resource(sentinel_device_data["oemSerialNumber"])

        try:
            data_from_sentinel = {
                "rate_plan": sentinel_device_data["ratePlan"],
                "rate_plan_desc": sentinel_device_data["ratePlanDescription"],
                "ncm_group_name": managed_device_data["ncmGroup"]["name"].replace(
                    " ", ""
                ),
            }
        except KeyError as ke:
            msg = f"Device information missing from Sentinel: {ke}"
            self.stop_report_fail(msg)

        return data_from_sentinel

    def get_cradlepoint_data(self):
        # Grab the CID and strip it to match the chaos of the cradlepoint api
        CRADELPOINT_ROUTERS = "v2/routers/"
        CRADLEPOINT_NET_DEVICES = "v2/net_devices/"
        clean_cid = self.cid.split("..")[0]

        cradlepoint_data = {
            "asset_id": "",
            "lte_connection_status": {
                "verizon": "",
                "att": "",
            },
        }

        router_data = self.cradlepoint_get(CRADELPOINT_ROUTERS, {"name": clean_cid})[
            "data"
        ]

        if router_data == []:
            msg = "No Routers Found in Cradlepoint"
            self.stop_report_exit(msg)
        elif len(router_data) > 1:
            msg = "Cradlepoint API Error: Multiple Routers Found"
            self.stop_report_exit(msg)
        else:
            router_data = router_data[0]

        cradlepoint_data["asset_id"] = router_data["asset_id"]

        # Use this to get the router specifics
        router_id = router_data["id"]

        net_device_data = self.cradlepoint_get(
            CRADLEPOINT_NET_DEVICES, {"router": router_id}
        )["data"]

        for device in net_device_data:
            if isinstance(device, dict):
                carrier = device.get("carrier")
                if carrier is not None:
                    cradlepoint_data["lte_connection_status"][carrier] = device[
                        "connection_state"
                    ]
        return cradlepoint_data

    def auth_sentinel(self):
        url = "https://sentinel-api.kajeet.com/sentinel/api/v1.0/auth/token"

        payload = {
            "username": self.wia_constants["sentinel_auth"]["username"],
            "password": self.wia_constants["sentinel_auth"]["password"],
        }

        response = requests.get(url, json=payload, verify=False)

        return response.json()["token"]

    def create_sentinel_model(self, sentinel_data):
        ncm_group_name = None
        rate_plan_desc = None
        legacy = False
        rate_plan = self.device_properties["service_code"]
        if rate_plan in self.wia_constants["unsupported_service_codes"]:
            self.logger.info(f"Service Code: {rate_plan} is Unsupported")
            self.stop_report_fail(f"Unsupported Service Code: {rate_plan}")

        elif rate_plan in self.wia_constants["legacy_service_codes"]:
            self.logger.info(f"Service Code: {rate_plan} is Legacy")
            legacy = True

        elif rate_plan in self.wia_constants["supported_device_service_codes"]:
            self.logger.info(
                f"Service Code: {rate_plan} is Device Specific and Not Applicable"
            )
            self.stop_report_fail(f"Legacy Service Code: {rate_plan}")

        elif rate_plan in self.wia_constants["active_service_codes"]:
            self.logger.info(f"Service Code: {rate_plan} is supported")
        else:
            self.logger.info(f"Service Code: {rate_plan} is not documented")
            self.stop_report_fail(f"Service Code: {rate_plan} is not documented")

        if legacy:
            rate_plan_details = self.wia_constants["legacy_service_codes"][rate_plan]
        else:
            rate_plan_details = self.wia_constants["active_service_codes"][rate_plan]

        for ncm in rate_plan_details["ncm_group"]:
            if self.model.split()[0] in ncm:
                ncm_group_name = ncm.replace(" ", "")
        if ncm_group_name is None:
            self.stop_report_fail(
                f"Model: {self.model} and NCM Group: {ncm} not supported for Rate Plan: {rate_plan}"
            )

        for desc in rate_plan_details["desc"]:
            if sentinel_data["rate_plan_desc"] in desc:
                rate_plan_desc = desc
        if rate_plan_desc is None:
            self.stop_report_fail(
                f"Rate Plan Desc: {sentinel_data['rate_plan_desc']} is not supported for Rate Plan: {rate_plan}"
            )

        sentinel_model = {
            "rate_plan": rate_plan,
            "rate_plan_desc": rate_plan_desc,
            "ncm_group_name": ncm_group_name,
        }
        return sentinel_model

    def create_cradlepoint_model(self, cradlepoint_data):
        connected_carrier = False
        for carrier in cradlepoint_data["lte_connection_status"]:
            if cradlepoint_data["lte_connection_status"][carrier] == "connected":
                self.logger.info(f"{carrier} is connected")
                connected_carrier = True
                break
            connected_carrier = False

        # If model is made the service code is valid and supported with valid desc and ncm group for rate code
        cradlepoint_model = {
            "asset_id": self.tid,
            "connected_carrier": connected_carrier,
        }

        return cradlepoint_model

    def compliance_process(
        self, sentinel_data, sentinel_model, cradlepoint_data, cradlepoint_model
    ):
        sentinel_diffs = None
        cradlepoint_diffs = None

        sentinel_net_diffs, sentinel_model_diffs = self.utils.compare_complex_dicts(
            sentinel_data, sentinel_model
        )

        cradelpoint_net_diffs, cradlepoint_model_diffs = (
            self.utils.compare_complex_dicts(cradlepoint_data, cradlepoint_model)
        )

        if sentinel_net_diffs:
            sentinel_diffs = {
                "network": sentinel_net_diffs,
                "model": sentinel_model_diffs,
            }
        if cradelpoint_net_diffs:
            cradlepoint_diffs = {
                "network": cradelpoint_net_diffs,
                "model": cradlepoint_model_diffs,
            }

        return sentinel_diffs, cradlepoint_diffs


class Terminate(Common):
    def process(self):
        resource_dependents = self.get_dependencies(self.resource["id"])
        for resource_dependent in resource_dependents:
            self.logger.info(
                "existing resource_dependent id found: {}".format(
                    resource_dependent["id"]
                )
            )
            self.bpo.resources.patch(
                resource_dependent["id"],
                {"desiredOrchState": "terminated", "orchState": "terminated"},
            )
