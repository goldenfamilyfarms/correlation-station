import json

from scripts.managedServicesActivator.merakiServices.merakidashboard import (
    MerakiDashboard,
)
from scripts.common_plan import CommonPlan
import traceback
import time


class Activate(CommonPlan):
    def process(self):
        wait_time = 1.0
        resource_id = self.params["resourceId"]
        resource = self.bpo.resources.get(resource_id)
        self.properties = resource["properties"]
        self.configurations = self.properties["configurations"]
        defaults = self.bpo.resources.get(
            self.get_resources_by_type_and_label(
                "charter.resourceTypes.MNEData", "default", no_fail=True
            )[0]["id"],
            obfuscate=False,
        )
        if "service_type" in self.configurations:
            self.service_type = self.configurations["service_type"]
            if not self.service_type:
                self.service_type = "Managed Network Edge"
        else:
            self.service_type = "Managed Network Edge"
        self.logger.info(f'Service type: {self.service_type}')

        serial_db_auth = None
        if "serial_db_auth_username" in defaults["properties"] and "serial_db_auth_passwd" in defaults["properties"]:
            serial_db_auth = {
                "username": defaults["properties"]["serial_db_auth_username"],
                "password": defaults["properties"]["serial_db_auth_passwd"],
            }
        else:
            self.logger.info("Failed to retrieve auth info for mso database from default resource data")

        self.devices = self.properties["devices"]
        api = defaults["properties"]["apiKey"]
        self.meraki = MerakiDashboard(
            api,
            self.logger,
            self.exit_error,
            self.bpo,
            resource_id,
            serial_db_auth=serial_db_auth
        )
        self.meraki.record_to_resource = True
        self.meraki.ignore_warnings = True
        self.nw_id = self.properties.get("network_id")
        self.org_id = None
        self.logger.info(f"nwid from payload: {self.nw_id}")

        manual_config = False
        if "dp_site_detail" in self.configurations:
            self.site_details = self.configurations["dp_site_detail"]
            self.logger.info("dp_site_detail in payload")
            manual_config = self.configurations["dp_site_detail"]["manual_provisioning_override"]
        else:
            self.site_details = None
        self.logger.info(f"manual config is set to: {manual_config}")

        if self.nw_id:
            # only try to get the org and net info by the net id if that is provided
            self.logger.debug(f"Retrieved NetID id from payload: {self.nw_id}")
            # check the provided net id exists
            net_info = self.meraki.getNetInfo(nwid=self.nw_id)
            if net_info:
                self.logger.info(f'got net info from id in payload: {net_info}')
                self.org_id = net_info["organizationId"]
            else:
                self.org_id = self.meraki.getOrganizationId(
                    organizationName=self.properties["orgName"]
                )
        if not self.org_id:
            self.org_id = self.meraki.getOrganizationId(
                organizationName=self.properties["orgName"]
            )
        if not self.org_id:
            self.meraki.log_issue(
                external_message=f"Unable to find an organization with name: '{self.properties['orgName']}'"
                                 "Please make sure the organization and network first have been created first",
                internal_message="Unable to find a organization with the provided name",
                api_response="",
                code=3007,
                details=f"org name = {self.properties['orgName']}",
                category=1
            )
        net_info = self.meraki.get_network_by_name(
            org_id=self.org_id, net_name=self.properties["networkName"]
        )
        if not net_info:
            self.meraki.log_issue(
                external_message=f"Unable to find network with name '{self.properties['networkName']}' "
                                 f"in organization '{self.properties['orgName']}' (organization id: {self.org_id})",
                internal_message="Unable to find a network with the provided name inside the organization",
                api_response="",
                code=3008,
                details=f"org name = {self.properties['orgName']} | network name = {self.properties['networkName']}",
                category=1
            )
        self.nw_id = net_info["id"]
        is_template = net_info.get("isBoundToConfigTemplate", False)
        self.logger.info(
            f"key 'isBoundToConfigTemplate' is in the net_info dict: {'isBoundToConfigTemplate' in net_info}"
        )
        self.logger.info(
            f"is_template: {is_template}"
        )
        org_id = self.org_id
        nw_id = self.nw_id
        self.bpo.resources.patch_observed(
            self.resource["id"], {"properties": {"networkID": nw_id}}
        )

        if not (is_template or manual_config):
            self.meraki.update_firmware(nw_id)
            self.meraki.applianceVlans(nw_id, True)

        self.meraki.create_webhooks(nwid=nw_id, org_id=self.org_id)

        # need to provision MX devices first
        self.devices = [d for d in self.devices if d["serial"] not in [None, ""]]
        self.logger.info(f'DEVICES: {[device["serial"] for device in self.devices]} ')

        mxs = [x for x in self.devices if "MX" in x["model"].upper()]
        non_mxs = [x for x in self.devices if "MX" not in x["model"].upper()]

        # do mxs then ha-mxs then non-mxs
        ha_mx = [x for x in mxs if x.get("is_ha", False)]
        non_ha_mx = [x for x in mxs if not x.get("is_ha", False)]
        mxs = non_ha_mx + ha_mx

        self.devices = mxs + non_mxs
        # we want to avoid further configuration for features associated with device types that already exist
        # in the meraki portal
        device_types = ["MX", "MR", "MS", "MV", "MT"]

        provided_devices = {}
        for _type in device_types:
            provided_devices[_type] = False
            for d in self.devices:
                if _type in d["model"].upper():
                    provided_devices[_type] = True

        self.logger.info(f"Device types provided:\n{json.dumps(provided_devices, indent=4)}")
        update_payload = {
            "properties": {
                "configurations": {
                    "provided_devices": provided_devices,
                }
            }
        }
        self.logger.info(f"updating the resource info with: {update_payload}")
        self.bpo.resources.patch_observed(resource_id, update_payload)

        did_configure = {dt: False for dt in device_types}
        net_devices = self.meraki.get_network_devices(nw_id)

        for device in net_devices:
            for dt in device_types:
                if dt in device.get("model", "").upper():
                    did_configure[dt] = True
                    break
        devices = {x["serial"]: x for x in net_devices}
        self.logger.info(
            "\n===============================================\n"
            f"existing devices: \n{json.dumps(devices, indent=4)}\n"
            f"did configure: \n {json.dumps(did_configure, indent=4)}\n"
            "===============================================\n"
        )

        licenses = self.meraki.get_licenses_from_inventory(org_id=org_id)
        if licenses is None:
            self.meraki.log_issue(
                external_message="Unable to search for licenses in organization",
                internal_message="Unable to search for licenses in organization",
                api_response="",
                code=3006,
                details="",
                category=2
            )
        org_licenses = {}
        self.logger.info("looking for unassigned licenses in the org inventory")
        for lic in licenses:
            self.logger.info(f"   type: {lic['licenseType'].upper()} | id: {lic['id']} | state: {lic['state'].upper()}")
            if lic["state"].upper() == "ACTIVE":
                continue
            t = lic["licenseType"].upper()
            if t not in org_licenses:
                org_licenses[t] = []
            org_licenses[t].append(lic["id"])

        self.logger.info(f"------------ DEVICES: {self.devices}")
        for device in self.devices:
            self.meraki.current_device = device["hostname"]
            self.meraki.current_device_model = device["model"]
            serial = device["serial"]
            self.logger.info(f" ===== PROVISIONING DEVICE {serial} ===== ")
            device_info = None
            try:
                if serial in devices.keys():
                    self.meraki.log_issue(
                        external_message=f"Device with serial {serial} is already claimed into network",
                        internal_message="Device with the given serial is already claimed into network",
                        api_response="",
                        code=2106,
                        details=f"serial: {serial} | device_info: {devices[serial]}",
                        category=3
                    )
                    continue
                else:
                    success, status_msg = self.meraki.claimNetworkDevice(nw_id, serial)
                    self.logger.info(f"status for claim device into network: {success} with message {status_msg}")
                    if not success:
                        continue

                for i in range(3):
                    time.sleep(wait_time)
                    net_devices = self.meraki.get_network_devices(nw_id)
                    devices = {x["serial"]: x for x in net_devices}
                    if serial in devices.keys():
                        device_info = devices[serial]
                        break
                if not device_info:
                    self.meraki.log_issue(
                        external_message="Unable to find device in Meraki after it was claimed",
                        internal_message="Unable to find device in Meraki after it was claimed",
                        api_response="",
                        code=2100,
                        details=f"serial={serial}",
                        category=2
                    )
                    continue
                else:
                    self.meraki.updateDeviceName(
                        org_id=org_id,
                        nw_id=nw_id,
                        serial=serial,
                        hostname=device["hostname"],
                        address=device["address"],
                        notes=device["notes"],
                    )
                    if not device["device_info"].get("is_ha", False):
                        if device.get("license_type", "") not in [None, ""]:
                            licType = device["license_type"]
                        else:
                            licType = self.meraki.license_type(device_info["model"], fail_if_not_found=True)
                        licenseId = None
                        if len(org_licenses.get(licType, [])) == 0:
                            self.meraki.log_missing_license(device["hostname"])
                        else:
                            licenseId = org_licenses[licType].pop()
                            self.meraki.updateOrganizationLicenses(
                                org_id, serial, licenseId
                            )
                    else:
                        self.logger.info(f"not assigining license to HA device: {device_info['serial']}")

                if is_template or manual_config:
                    continue

                elif "MX" in device_info["model"]:
                    if not did_configure["MX"]:
                        if not device["device_info"].get("is_ha", False):
                            # there will always be one non-ha mx and this needs to be done only once
                            self.meraki.failover_fallback(nwid=nw_id)

                        # VLANS
                        time.sleep(wait_time)
                        vlans = self.configurations.get("VLANS", None)
                        if vlans is not None:
                            self.meraki.create_vlans(nw_id=nw_id, vlans=vlans)

                        # STATIC ROUTES
                        time.sleep(wait_time)
                        if "static_routes" in self.configurations:
                            self.meraki.apply_static_routing(
                                nwid=nw_id,
                                static_routes=self.configurations["static_routes"],
                            )
                            time.sleep(wait_time)

                        ipsec_rules = self.configurations.get("ip_sec_rules", None)
                        self.meraki.updateNetworkApplianceSecurityIntrusion(
                            nw_id, rules=ipsec_rules
                        )

                        time.sleep(wait_time)
                        self.meraki.update_traffic_shaping_rules(nw_id)

                        time.sleep(wait_time)
                        self.meraki.updateNetworkApplianceSecurityMalware(nw_id)

                        time.sleep(wait_time)
                        self.meraki.disable_auto_vpn(nw_id)

                        time.sleep(wait_time)
                        if "one_1NAT" in self.configurations:
                            one_1_rules = self.configurations["one_1NAT"]
                            if len(one_1_rules.get("rules", [])) > 0:
                                self.meraki.apply_1to1_nat_rules(
                                    nwid=nw_id, rules=one_1_rules
                                )

                        time.sleep(wait_time)
                        if "one_manyNAT" in self.configurations:
                            one_many_rules = self.configurations["one_manyNAT"]
                            if len(one_many_rules.get("rules", [])) > 0:
                                self.meraki.apply_1to_many_nat_rules(
                                    nwid=nw_id, rules=one_many_rules
                                )

                        time.sleep(wait_time)
                        if "portforward" in self.configurations:
                            pf_rules = self.configurations["portforward"]
                            if len(pf_rules) > 0:
                                self.meraki.apply_pf_nat_rules(nwid=nw_id, rules=pf_rules)

                        time.sleep(wait_time)
                        if "L3_rules" in self.configurations:
                            l3_rules = self.configurations.get("L3_rules", None)
                            if len(l3_rules.get("rules", [])) > 0:
                                self.meraki.apply_L3_rules(nwid=nw_id, l3_rules=l3_rules)

                        time.sleep(wait_time)
                        if "L7_rules" in self.configurations:
                            l7_rules = self.configurations.get("L7_rules", None)
                            if len(l7_rules.get("rules", [])) > 0:
                                self.meraki.apply_L7_rules(nwid=nw_id, l7_rules=l7_rules)

                        time.sleep(wait_time)
                        if "bandwidth" in self.configurations and self.configurations[
                            "bandwidth"
                        ] not in [{}, None]:
                            bandwidth = self.configurations["bandwidth"]
                            self.meraki.updateNetworkApplianceTrafficShaping(
                                nw_id, bandwidth=bandwidth
                            )

                        time.sleep(wait_time)
                        # complicated content filtering settings based on service type
                        if "per room" in self.service_type.lower():
                            if not self.site_details:
                                # dp site details was not in the payload from beorn
                                self.meraki.log_issue(
                                    external_message="unable to get staff or guest content filtering settings",
                                    internal_message="unable to get staff or guest content filtering settings",
                                    api_response="",
                                    code=2101,
                                    details="",
                                    category=5
                                )
                            else:
                                # dp site details was in the payload from beorn
                                # staff
                                content_filtering_payload = self.meraki.create_content_filtering_payload(
                                    site_details=self.site_details,
                                    source="staff"
                                )
                                if content_filtering_payload:
                                    # if the above failed, it has already been logged
                                    self.meraki.create_staff_group_policy(
                                        nwid=nw_id,
                                        content_filters=content_filtering_payload
                                    )

                                # guest
                                content_filtering_payload = self.meraki.create_content_filtering_payload(
                                    site_details=self.site_details,
                                    source="guest"
                                )
                                if content_filtering_payload:
                                    # if the above failed, it has already been logged
                                    self.meraki.updateNetworkApplianceContentFiltering(
                                        nw_id, content_filtering_payload
                                    )
                        else:
                            # standard MNE, don't change the way this does content filtering
                            # eventually this will process content filtering as per room does with source="mne"
                            # when proven stable
                            if "contentFiltering" in self.configurations:
                                self.meraki.updateNetworkApplianceContentFiltering(
                                    nw_id, self.configurations["contentFiltering"]
                                )

                            if "dp_vpn_site_to_site_ipsecs" in self.configurations:
                                self.meraki.update_vpn_peers(
                                    self.org_id, self.configurations["dp_vpn_site_to_site_ipsecs"]["peers"]
                                )
                        did_configure["MX"] = True
                    if "appliancePorts" in device["device_info"]:
                        appliancePorts = device["device_info"]["appliancePorts"]
                        self.logger.info(f"appliancePorts: {appliancePorts}")
                        self.meraki.updateNetworkAppliancePorts(
                            nw_id=nw_id, ports=appliancePorts
                        )

                elif "MS" in device_info["model"]:
                    if "switchPorts" in device["device_info"]:
                        self.meraki.updateSwitchPorts(
                            serial, device["device_info"]["switchPorts"]
                        )
                    if not did_configure["MS"]:
                        default_mgmt_vlan = 88
                        switch_settings = self.configurations.get("dp_switch_settings", [{"mgmt_vlan": default_mgmt_vlan}])
                        mgmt_vlan = switch_settings[0].get("mgmt_vlan", default_mgmt_vlan)
                        self.meraki.set_switch_settings(nw_id=self.nw_id, mgmt_vlan=mgmt_vlan)
                        did_configure["MS"] = True

                elif "MR" in device_info["model"]:
                    if not did_configure["MR"]:
                        did_configure["MR"] = True
                        if "ssids" in self.configurations:
                            self.meraki.createSSIDs(
                                nw_id=nw_id,
                                ssids=self.configurations["ssids"],
                                service_type=self.service_type
                            )
                        else:
                            self.logger.info("No custom ssids to configure")
                    else:
                        self.logger.info("already configured ssids")

                elif "MV" in device_info["model"]:
                    self.meraki.setCameraSettings(
                        serial=serial, data=device["device_info"], nwid=nw_id
                    )
                    did_configure["MV"] = True

                else:
                    self.meraki.log_issue(
                        external_message=f"Unknown device model: {device_info['model']}",
                        internal_message="Unknown device model",
                        api_response="",
                        code=2103,
                        details=f"model={device_info['model']} | info: {device_info}",
                        category=5
                    )

            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(tb)
                self.meraki.log_issue(
                    external_message=f"RUNTIME ERROR when provisioning device {serial}",
                    internal_message="RUNTIME ERROR when provisioning device",
                    api_response=e.args,
                    code=2104,
                    details=f"tb: {tb}",
                    category=5
                )
        if not (is_template or manual_config):
            try:
                if "virtual_ip" in self.configurations:
                    for serial, ips in self.configurations["virtual_ip"].items():
                        self.meraki.update_ha_appliance(
                            nwid=nw_id,
                            spare_serial=serial,
                            vip1=ips[0],
                            vip2=ips[1] if len(ips) > 1 else None
                        )

                if "sensor_profiles" in self.configurations:
                    # after all devices are claimed, check if we need to update sensor profiles to include the devices
                    profile_devices = {}
                    for profile in self.configurations["sensor_profiles"]:
                        profile_device_hostnames = [x["hostname"] for x in profile["dp_devices"]]
                        profile_serials_arr = [k for k, v in devices.items() if v["name"] in profile_device_hostnames]
                        profile_devices[profile["name"]] = profile_serials_arr

                    self.meraki.add_sensor_serials(
                        dp_sensor_profiles=self.configurations["sensor_profiles"],
                        profile_serials=profile_devices,
                        nwid=nw_id
                    )
            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(tb)
                self.meraki.log_issue(
                    external_message="RUNTIME ERROR configuring general settings",
                    internal_message="RUNTIME ERROR configuring general settings",
                    api_response=e.args,
                    code=2105,
                    details=f"tb: {tb}",
                    category=5
                )

        # log any issues that occurred in provisioning
        self.meraki.finish()


class Terminate(Activate):
    def process(self):
        return
