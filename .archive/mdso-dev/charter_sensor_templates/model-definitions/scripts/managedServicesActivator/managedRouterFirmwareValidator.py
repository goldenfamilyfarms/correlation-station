import json
import time
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    def process(self):
        """Validate Firmware

        1) Create Network Function
        2) Get running firmware
        3) Compare to approved firmware
        """
        self.label = self.resource["label"]
        props = self.resource["properties"]
        self.ipAddress = props["ipAddress"]
        self.firmware_version = props["firmwareVersion"]
        fqdn = self.ipAddress

        # Create connection to CPE
        try:
            msg = "1. Onboard Network Function"
            self.logger.info(msg)
            nf = self.onboard_network_function(fqdn)
            self.logger.info("Device Onboarded: " + str(nf))
        except Exception as err:
            err_msg = "Failed Device Onboard: {}".format(err)
            self.exit_error(err_msg)

        # Run show version command
        try:
            msg = "2. Run `show version` command."
            self.logger.info(msg)
            result = self.create_cli_manager()
            self.logger.info("Result: {}".format(result))
        except Exception as err:
            err_msg = "Failed Sending Command: {}".format(err)
            self.exit_error(err_msg)

        # Verify if current firmware is approved
        try:
            msg = "3. Verify firmware."
            self.logger.info(msg)
            firmware_current = result["properties"]["output_results"]["command_results"][0]["result"]
            self.logger.info("Current Firmware: {}".format(firmware_current))
        except Exception as err:
            err_msg = "Failed: {}".format(err)
            self.exit_error(err_msg)

        if self.firmware_version in firmware_current:
            self.logger.info("Firmware is approved!  Patching Observed")
            props["approved"] = True
            self.bpo.resources.patch_observed(self.resource["id"], {"properties": props})

    def onboard_network_function(self, fqdn):
        """Attempt to onboard a Network Function resource.

        PARAMETERS
        ----------
        fqdn : str
            FQDN of resource

        RETURNS
        -------
        NetworkFunction : dict
            Resource data for new Network Function resource.
        """
        nf = self.get_network_function_by_host_or_ip(fqdn, self.ipAddress)

        if nf is not None and nf["orchState"].lower() != "active":
            # Attempt to delete resource if not already active
            nf_id = nf["id"]
            self.logger.info("Attempting to delete resource: " + nf_id)
            self.delete_resource(nf_id)

            attempts = 0
            while nf is not None and attempts < 5:
                time.sleep(1)
                nf = self.get_network_function_by_host_or_ip(fqdn, self.ipAddress)
                attempts += 1
            if nf is not None:
                raise Exception("Failed to delete resource.")
            else:
                self.logger.info("Resource deleted successfully.")
        elif nf is not None:
            self.logger.info("Found active Network Function: " + str(nf))

        if nf is None:
            # Onboard new Network Function
            device_onboard = self.add_device()
            self.logger.info("device_onboard {}".format(device_onboard))

        return self.get_network_function_by_host_or_ip(fqdn, self.ipAddress)

    def add_device(self):
        onboard_product = self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)
        label = self.label + ".device_onboarder"
        created_onboarded_res = []
        devices_deployed = {}
        devices_deployed[self.label] = False
        onboard_details = {
            "label": label,
            "productId": onboard_product["id"],
            "properties": {
                "device_ip": self.ipAddress,
                "device_vendor": "CISCO",
                "operation": "MANAGED_SERVICES_ACTIVATION",
            },
        }

        self.logger.debug("On-boarding device: " + self.ipAddress)
        device_res = self.bpo.resources.create(self.params["resourceId"], onboard_details)
        self.logger.debug("Resource Created: {}".format(device_res))
        created_onboarded_res.append(device_res.resource)
        # NOW WAIT FOR THEM ALL TO FINISH
        for resp in created_onboarded_res:
            resp_id = resp["id"]
            # Wait for relationships to be built
            try:
                self.await_resource_states_collect_timing("Waiting for " + resp_id, resp_id, interval=5, tmax=300)
                devices_deployed[resp["properties"]["device_ip"]] = True
            except Exception:
                try:
                    r = self.bpo.resources.get(resp_id)
                    if r is not None:
                        devices_deployed[resp["properties"]["device_ip"]] = r["orchState"] == "active"
                except Exception as ex:
                    devices_deployed[resp["properties"]["device_ip"]] = True
                    self.logger.debug("On-boarder {} already on-boarding so no need to check.".format(resp_id))
                    self.logger.debug("Exception: " + str(ex))

            # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
            self.delete_resource(resp_id)

            if True not in devices_deployed.values():
                nf = self.get_network_function_by_host_or_ip(self.fqdn or self.ipAddress, self.ipAddress)
                self.delete_resource(nf["id"])
                raise Exception("Failed to onboard device: {} ".format(self.fqdn.split(".")[0]))

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        output = {"status": "Device deployed successfully"}
        self.logger.info("Output: " + json.dumps(output))

        return output

    def create_cli_manager(self):
        cli_manager_product = self.get_built_in_product(self.BUILT_IN_CLI_MANAGER_TYPE)
        label = self.label + ".cli_manager"
        config = ["show version | i image"]
        cli_manager_details = {
            "label": label,
            "productId": cli_manager_product["id"],
            "properties": {
                "configuration": config,
                "ipAddress": self.ipAddress,
                "operation": "MANAGED_SERVICES_ACTIVATION",
            },
        }

        self.logger.debug("Sending following commands: " + str(config))
        created_cli_manager = self.bpo.resources.create(self.params["resourceId"], cli_manager_details)
        return created_cli_manager.resource


class Terminate(CommonPlan):
    pass
