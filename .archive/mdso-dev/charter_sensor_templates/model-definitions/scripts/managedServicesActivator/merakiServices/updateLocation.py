from scripts.managedServicesActivator.merakiServices.merakidashboard import (
    MerakiDashboard,
)
from scripts.common_plan import CommonPlan
import json


class Activate(CommonPlan):
    def process(self):
        """
        MNE per room location update
        """
        # Log the payload and get data
        self.logger.info(f"properties: {json.dumps(self.properties, indent=4)}")
        default_data_resource = self.get_resources_by_type_and_label(
            "charter.resourceTypes.MNEData",
            "default",
            no_fail=True
        )[0]["id"]
        defaults = self.bpo.resources.get(
            default_data_resource,
            obfuscate=False
        )

        self.api = defaults["properties"]["apiKey"]
        self.meraki = MerakiDashboard(
            self.api,
            self.logger,
            self.exit_error,
            self.bpo,
            self.resource["id"],
        )
        self.meraki.record_to_resource = False
        self.meraki.ignore_warnings = True

        # ------------- customer info-------------
        # first get organization info and confirm that we have access to the organization
        self.nw_id = self.properties.get("networkID")
        if self.nw_id:
            # check the provided net id exists
            net_info = self.meraki.getNetInfo(nwid=self.nw_id)
            if not net_info:
                self.nw_id = None
            else:
                self.nw_id = net_info["id"]
                self.org_id = net_info["organizationId"]

        if not self.nw_id:
            # if that was not a valid network, or the net id was not provided, do a search by name
            if "orgName" not in self.properties or "networkName" not in self.properties:
                self.meraki.log_issue(
                    external_message="Please provide an organization and network name or a valid networkID",
                    internal_message="Please provide an organization and network name or a valid networkID",
                    api_response="",
                    code=3012,
                    details="",
                    category=1
                )

            self.org_id = self.meraki.getOrganizationId(
                organizationName=self.properties["orgName"]
            )
            if not self.org_id:
                self.meraki.log_issue(
                    external_message=f"Unable to find an organization with name: '{self.properties['orgName']}'"
                                     f"Please make sure the organization and network first have been created first",
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
        # -----------------

        self.devices = self.properties.get("devices", None)
        # self.devices = {"serial": {"location": "room 123", "tags": "11osTag"}}

        failed_devices = []
        error_messages = []
        for serial, device_info in self.devices.items():
            success, error_message = self.meraki.update_device_location(
                serial=serial,
                notes=device_info.get("notes"),
                tags=device_info.get("tags")
            )
            if not success:
                failed_devices.append(serial)
                error_messages.append(error_message)
        if len(failed_devices) != 0:
            failed_devices = ", ".join(failed_devices)
            self.meraki.log_issue(
                external_message=f"Failed to update location or tags for device(s): {failed_devices}",
                internal_message="Failed to update location or tags for device(s)",
                api_response=f"{error_messages}",
                code=2081,
                details=f"org name={self.properties['orgName']} | network name = {self.properties['networkName']}",
                category=1
            )
        self.meraki.finish()


class Terminate(Activate):
    def process(self):
        return
