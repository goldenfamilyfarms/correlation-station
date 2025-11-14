from scripts.managedServicesActivator.merakiServices.merakidashboard import (
    MerakiDashboard,
)
from scripts.common_plan import CommonPlan
import time
import json


class Activate(CommonPlan):
    def process(self):
        """
        MNE DAY 1
        1) Search for, verify, or create Meraki Organization
        2) Search for, verify, or create Organization Network
        3) Verify requested licenses are not already in the Organization inventory
        4) Determine requested license ids and move them from Spectrum Clome to the customer Organization
        """

        # Log the payload and get data
        self.logger.info("properties: {}".format(json.dumps(self.properties, indent=4)))
        defaults = self.bpo.resources.get(
            self.get_resources_by_type_and_label(
                "charter.resourceTypes.MNEData", "default", no_fail=True
            )[0]["id"],
            obfuscate=False,
        )
        self.configurations = self.properties["configurations"]
        if "service_type" in self.configurations:
            self.service_type = self.configurations["service_type"]
            if not self.service_type:
                self.service_type = "Managed Network Edge"
        else:
            self.service_type = "Managed Network Edge"
        self.logger.info(f'Service type: {self.service_type}')

        self.api = defaults["properties"]["apiKey"]
        self.meraki = MerakiDashboard(
            self.api,
            self.logger,
            self.exit_error,
            self.bpo,
            self.resource["id"],
        )
        self.meraki.record_to_resource = True
        self.meraki.ignore_warnings = False
        self.license_move_successful = False

        default_orgs = self.meraki.get_template_and_inventory_orgs(defaults)
        self.template_org_id = default_orgs["template"]
        self.inventory_org_id = default_orgs["inventory"]

        # ------------- Get / Verify / Create the Organization and Network -------------
        self.org_id = self.properties.get("orgID", None)
        self.nw_id = self.properties.get("networkID", None)
        self.org_name = self.properties.get("orgName", None)
        self.netName = self.properties.get("networkName", None)
        network_exists = False
        is_vmx = False
        self.template_id = None
        if self.configurations.get("template_id"):
            self.template_id = self.configurations.get("template_id")

        network_devices = [
            x for x in self.properties["configurations"]["customer_devices"]
            if x["site_id"] == self.properties["configurations"]["site_id"]
        ]
        self.logger.info(f'vmx devices: {[x["type"].upper() == "VMX" for x in network_devices]}')
        if any([x["type"].upper() == "VMX" for x in network_devices]):
            if len(network_devices) > 1:
                self.meraki.log_issue(
                    external_message="VMX networks can only have one vmx in the network",
                    internal_message="VMX networks can only have one vmx in the network",
                    api_response="",
                    code=3009,
                    details=f"vmx devices = {len(network_devices)}",
                    category=1
                )
            else:
                is_vmx = True
                self.vmx_device = network_devices[0]

                # reset the net name to follow vmx convention
                self.netName = self.netName.split("-")[0].strip()
                self.netName = f"{self.netName} - {self.org_name} - vMX - {self.vmx_device['cloud_provider']}"

                # run checks
                sizes = {
                    "VMX-S": "small",
                    "VMX-M": "medium",
                    "VMX-L": "large",
                    "VMX-100": "100",
                }
                if self.vmx_device["model"].upper() not in sizes:
                    self.meraki.log_issue(
                        external_message="Unable to determine VMX size",
                        internal_message="Unable to determine VMX size",
                        api_response="",
                        code=3010,
                        details=f"vmx model: {self.vmx_device['model'].upper()}",
                        category=1
                    )
                else:
                    self.vmx_device["size"] = sizes[self.vmx_device['model'].upper()]

        self.logger.info(f"is_vmx = {is_vmx}")
        time_code = self.properties.get("timeZone")
        if time_code is None:
            time_code = self.properties["address"][-5:]
            if not time_code.isnumeric():
                self.meraki.log_issue(
                    external_message="Unknown timezone or address zipcode, cannot find time Zone",
                    internal_message="Unknown timezone or address zipcode, cannot find time Zone",
                    api_response="",
                    code=3011,
                    details=f"time_zone = {time_code}",
                    category=1
                )
        timeZone = self.meraki.get_timezone(code=time_code)

        # first lets check if the provided network id is correct, if so we can get the organization from it
        if self.nw_id:
            net = self.meraki.getNetInfo(nwid=self.nw_id)
            if net:
                self.logger.info("we found the org id by the network")
                self.org_id = net["organizationId"]
                network_exists = True
                if is_vmx and not(len(net["productTypes"]) == 1 and net["productTypes"][0].upper() == "APPLIANCE"):
                    self.meraki.log_issue(
                        external_message="The provided network id can not be used for vVMX",
                        internal_message="The provided network id can not be used for vVMX",
                        api_response="",
                        code=3012,
                        details="",
                        category=1
                    )
            else:
                self.nw_id = None
                self.logger.info("The provided network id could not be found")

        # we could not verify network actually exists, but we do have an org id we need to verify
        if self.org_id and not network_exists:
            org = self.meraki.get_organization_by_id(orgid=self.org_id)
            if not org:
                self.logger.info("provided organization id does not exist")
                self.org_id = None

        # Either the id was not provided or we cannot verify it.
        # Our last option is to find an existing organization is by name search
        if not self.org_id and not self.org_name:
            self.meraki.log_issue(
                external_message="Unable to find organization by id and the name was not provided",
                internal_message="Unable to find organization by id and the name was not provided",
                api_response="",
                code=3013,
                details="",
                category=1
            )
        else:
            self.org_id = self.meraki.getOrganizationId(organizationName=self.org_name)

        # we could not get the organization by name, id or through the network. We Must create it and the network
        if not self.org_id:
            # this has fail conditions built into the function, we will get an id
            self.org_id = self.meraki.cloneOrganization(
                self.template_org_id, self.org_name
            )
            time.sleep(5)

            # we know the net does not exist, so we need to create it
            self.nw_id = self.meraki.createNetwork(
                orgId=self.org_id,
                networkName=self.netName,
                timeZone=timeZone,
                notes=self.properties.get("notes", ""),
                is_vmx=is_vmx,
                template_id=self.template_id
            )
            _ = self.meraki.waitForNetwork(self.org_id, self.nw_id)
            self.meraki.updateOrganizationSamlRoles(
                self.org_id, self.properties["accountNumbers"]
            )
            time.sleep(5)

            network_exists = True

        # the org exists at this point, need to search for or create network
        if not network_exists:
            self.nw_id = None
            # we know the network id either was not provided or is incorrect and was not recently created.
            # we still cannot rule out that it exist in the organization, so we need to search for it by name
            if self.netName is None:
                self.meraki.log_issue(
                    external_message="Network name and network id was not provided",
                    internal_message="Network name and network id was not provided",
                    api_response="",
                    code=3014,
                    details="",
                    category=1
                )

            net = self.meraki.get_network_by_name(
                org_id=self.org_id, net_name=self.netName
            )
            if not net:
                # this will fail or provide the network id
                self.nw_id = self.meraki.createNetwork(
                    orgId=self.org_id,
                    networkName=self.netName,
                    timeZone=timeZone,
                    notes=self.properties.get("notes", ""),
                    is_vmx=is_vmx,
                    template_id=self.template_id
                )
            else:
                self.nw_id = net["id"]

        net = self.meraki.waitForNetwork(self.org_id, self.nw_id)
        self.logger.info(f"network is: {json.dumps(net, indent=4)}")

        if is_vmx:
            # double-check the network is an appliance only incase the net already existed
            if not (len(net["productTypes"]) == 1 and net["productTypes"][0].upper() == "APPLIANCE"):
                self.meraki.log_issue(
                    external_message="The network for a VMX most be only of product type Appliance",
                    internal_message="The network for a VMX most be only of product type Appliance",
                    api_response="",
                    code=3015,
                    details="",
                    category=1
                )

        # SAML
        time.sleep(1)
        self.meraki.updateOrganizationSamlRoles(
            self.org_id, self.properties["accountNumbers"]
        )

        if not self.template_id:
            # network alerts
            self.meraki.updateNetworkAlertSettings(self.nw_id)
            time.sleep(1)
            self.meraki.updateNetworkSnmpSettings(self.nw_id)
            time.sleep(1)

        # MDSO info
        self.logger.info(f"ORGANIZATION ID: {self.org_id}\nNETWORK ID: {self.nw_id}")
        self.bpo.resources.patch_observed(
            self.resource["id"],
            {"properties": {"networkID": self.nw_id, "orgID": self.org_id}},
        )

        if is_vmx:
            vmx_lt = self.vmx_device["license_type"]
            if vmx_lt in ["", None]:
                vmx_lt = self.vmx_device["model"].upper() + "-ENT"
            vmx_lid = ""
            licenses_in_org = self.meraki.get_licenses_from_inventory(org_id=self.org_id)

            if licenses_in_org is None:
                self.meraki.log_issue(
                    external_message="Unable to search for licenses in organization",
                    internal_message="Unable to search for licenses in organization",
                    api_response="",
                    code=3016,
                    details="",
                    category=1
                )
            for lic in licenses_in_org:
                if lic["licenseType"].upper() == vmx_lt.upper() and not lic["state"].upper() == "ACTIVE":
                    vmx_lid = lic["id"]
                    break
            if vmx_lid == "":
                # could not find an existing license, move it from the spectrum vmx org
                self.logger.info(f"getting license {vmx_lt} from org {self.inventory_org_id}")
                outside_license = self.meraki.get_license_ids(
                    org_id=self.inventory_org_id, license_types={vmx_lt: 1}
                )
                if len(outside_license) == 0:
                    self.meraki.log_issue(
                        external_message="Cannot find VMX license to bring to this organization",
                        internal_message="Cannot find VMX license to bring to this organization",
                        api_response=f"license type = {vmx_lt}",
                        code=3017,
                        details="",
                        category=1
                    )
                else:
                    vmx_lid = outside_license[0]
                    self.license_move_successful = self.meraki.move_organization_licenses(
                        orgId=self.org_id,
                        licenseIds=vmx_lid,
                        inventory_org=self.inventory_org_id
                    )

            # claim device
            claimed_vmx = self.meraki.claim_vmx(
                nwid=self.nw_id,
                size=self.vmx_device["size"]
            )
            self.vmx_device["serial"] = claimed_vmx["serial"]

            # update the device name
            self.meraki.updateDeviceName(
                org_id=self.org_id,
                nw_id=self.nw_id,
                serial=claimed_vmx["serial"],
                hostname=self.vmx_device["hostname"],
                address=self.properties["address"],
                notes=self.properties["notes"]
            )

            # assign the license
            self.meraki.updateOrganizationLicenses(
                org_id=self.org_id,
                serial=self.vmx_device["serial"],
                licenseId=vmx_lid
            )
            self.logger.info(vmx_lid)
            self.bpo.resources.patch_observed(
                self.resource["id"], {"properties": {"LicenseID": vmx_lid}}
            )
        else:
            # not a vmx
            # ------------- Search for, and move the licenses -------------
            # all of the host names we expect to exist or be claimed into the entire organization
            expected_hostnames = [
                x["hostname"] for x in self.properties["configurations"]["customer_devices"]
            ]
            expected_licenses = []  # expected for this org
            moving_for_this_site = []  # licenses we should be moving for this site
            failed_models = []
            for device in self.properties["configurations"]["customer_devices"]:
                lt = None
                belongs_to_this_site = device["site_id"] == self.properties["configurations"]["site_id"]
                if "license_type" in device:
                    # check if license type is provided in the device payload
                    lt = device.get("license_type")
                if lt is None:
                    # if it was not provided or was null in the payload, fall back to map the license type
                    lt = self.meraki.license_type(device["model"], fail_if_not_found=True)
                if lt not in ["", None]:
                    self.logger.info(f"license type for {device['hostname']} is {lt}")
                    expected_licenses.append(lt)
                    if belongs_to_this_site:
                        moving_for_this_site.append(lt)
                else:
                    # If here we still have not found the license type.
                    # Warn them if we were expecting that device in this network and skip it
                    if belongs_to_this_site:
                        failed_models.append(f"{device['hostname']} ({device['model']})")

            if len(failed_models) > 0:
                self.meraki.log_issue(
                    external_message=f"Failed to determine license types for: {failed_models}",
                    internal_message="Failed to determine license types for some devices",
                    api_response="",
                    code=2199,
                    details=f"failed_models={failed_models}",
                    category=5
                )

            # if there are no devices for this site, tell the user and leave
            if len(moving_for_this_site) == 0:
                message = "No devices for this organization appear to be assigned to this site in " \
                          "Design portal. No licenses will be moved"
                self.meraki.log_issue(
                    external_message=message,
                    internal_message=message,
                    api_response="",
                    code=1101,
                    details=f"expected_hostnames={expected_hostnames}",
                    category=1
                )

                if not self.template_id:
                    self.meraki.sensor_profiles(
                        nwid=self.nw_id,
                        profiles=self.properties["configurations"]["sensor_profiles"]
                    )
                    self.meraki.firewall_service(self.nw_id)
                self.meraki.finish()

            # requested licenses dictionary - {type: n}
            requested_licenses = {
                x: moving_for_this_site.count(x) for x in set(moving_for_this_site)
            }

            # Make sure we are not going to move more licenses into the organization than necessary
            if not self.properties["configurations"].get("ignore_existing_licenses", False):
                self.logger.info(
                    "Going through existing licenses to avoid moving unnecessary ones"
                )
                existing_licenses = self.meraki.get_licenses_from_inventory(
                    org_id=self.org_id
                )
                existing_devices = self.meraki.get_org_devices(self.org_id)
                existing_devices = {x["serial"]: x for x in existing_devices}

                self.logger.info(f"hostnames: {expected_hostnames}")
                self.logger.info(f"expected_licenses: {expected_licenses}")
                self.logger.info(f"moving_for_this_site: {requested_licenses}")
                self.logger.info(f"existing_licenses: {len(existing_licenses)}")
                self.logger.info(
                    f"existing_devices: {json.dumps(existing_devices, indent=4)}"
                )

                self.logger.info("GOING THROUGH LICENSES")
                for el in existing_licenses:
                    if el["state"].upper() == "ACTIVE":
                        if el["deviceSerial"] not in existing_devices:
                            continue
                        if (
                            existing_devices[el["deviceSerial"]].get("name")
                            in expected_hostnames
                        ):
                            if expected_licenses.__contains__(el["licenseType"]):
                                expected_licenses.remove(el["licenseType"])
                            else:
                                # This would mean that we see a device that was configured in DP, but it has an
                                # unexpected license assigment that we cannot remove from the list
                                pass
                        else:
                            # ignore other devices that are not in dp
                            pass
                    else:
                        if expected_licenses.__contains__(el["licenseType"]):
                            expected_licenses.remove(el["licenseType"])
                        else:
                            # this is a new license type that is in the inventory but not in DP
                            pass

                self.logger.info(f"requested --: {requested_licenses}")
                self.logger.info(f"expected_licenses: {expected_licenses}")
                self.logger.info(f"moving_for_this_site: {moving_for_this_site}")
                over_requesting = False
                for typ, count in requested_licenses.items():
                    this_type_licenses_needed = expected_licenses.count(typ)
                    self.logger.info(f"lt: {typ}")
                    self.logger.info(f"requested: {count}")
                    self.logger.info(
                        f"this_type_licenses_needed: {this_type_licenses_needed}"
                    )

                    if count > this_type_licenses_needed:
                        over_requesting = True
                        moving_for_this_site = [x for x in moving_for_this_site if x != typ]
                        moving_for_this_site.extend([typ] * this_type_licenses_needed)
                        self.logger.info(f"moving_for_this_site: {moving_for_this_site}")

                moving_for_this_site = {
                    x: moving_for_this_site.count(x) for x in set(moving_for_this_site)
                }
                if over_requesting:
                    if all([v == 0 for k, v in moving_for_this_site.items()]):
                        message = "All requested licenses appear to be in the organization inventory already, " \
                                  "nothing will be moved"
                        self.meraki.log_issue(
                            external_message=message,
                            internal_message=message,
                            api_response="",
                            code=1103,
                            details=f"failed_models={failed_models}",
                            category=3
                        )
                        if not self.template_id:
                            self.meraki.firewall_service(self.nw_id)

                        self.meraki.finish()
                        return
                    else:
                        message = "You are trying to move more licenses to the organization than needed, only moving needed licenses"
                        self.meraki.log_issue(
                            external_message=message,
                            internal_message=message,
                            api_response="",
                            code=1104,
                            details=f"requested_licenses={requested_licenses} | moving_for_this_site={moving_for_this_site}",
                            category=3
                        )
            else:
                self.logger.info("Ignoring existing licenses")
                moving_for_this_site = requested_licenses

            self.logger.info(f"Attempting to move licenses for: {moving_for_this_site}")
            license_ids = self.meraki.get_license_ids(
                org_id=self.inventory_org_id, license_types=moving_for_this_site
            )
            self.license_move_successful = self.meraki.move_organization_licenses(
                orgId=self.org_id,
                licenseIds=license_ids,
                inventory_org=self.inventory_org_id
            )
            self.logger.info(license_ids)
            licenseIds = ", ".join(license_ids)
            self.bpo.resources.patch_observed(
                self.resource["id"], {"properties": {"LicenseID": licenseIds}}
            )

            if not self.template_id:
                # update sensor profiles
                self.meraki.sensor_profiles(
                    nwid=self.nw_id,
                    profiles=self.properties["configurations"]["sensor_profiles"]
                )
        # this takes a while to become available after the net is created so moving it down here
        if not self.template_id:
            self.logger.info("doing logging and firewall stuff because the net is not bound to template")
            self.meraki.firewall_service(self.nw_id)
            if self.license_move_successful:
                self.meraki.logging_settings(self.nw_id, lic_types_str="MX" if is_vmx else str(requested_licenses))
        else:
            self.logger.info("net is bound to template, skipping firewall and logging")

        self.meraki.finish()


class claimDevice(CommonPlan):
    """Claim Device Operation"""

    def process(self):
        pass


class Terminate(Activate):
    def process(self):
        return
