import json
import time
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


SFTP_SERVER_LABEL = "MRSA_SCP_ENDPOINT"


class Activate(CommonPlan):
    def process(self):
        """Update Firmware

        1) Create Network Function
        2) Check for existing valid firmware file
        3) if step 2 = False, Run command to download file from remote server
        4) Configure router to boot from approved firmware
        5) Reload router
        """
        self.label = self.resource["label"]
        props = self.resource["properties"]
        self.ipAddress = props["ipAddress"]
        self.firmware_version = props["firmwareVersion"]

        # Create connection to CPE
        try:
            msg = "1. Create Network Function"
            self.logger.info(msg)
            nf = self.onboard_network_function()
            self.nf_res_id = nf["providerResourceId"]
            self.logger.info("Device Onboarded: " + str(nf))
        except Exception as err:
            err_msg = "Failed Device Onboard: {}".format(err)
            self.exit_error(err_msg)

        # Check for file on router and download file if not present
        try:
            msg = "2. Check for and download firmware file on router."
            self.logger.info(msg)
            if not self.check_for_firmware_file():
                sftp_props = self.get_sftp_constants(SFTP_SERVER_LABEL)
                if sftp_props is None:
                    raise Exception("No SFTP Server Resource Found")
                sftp_props["dirpath"] += self.firmware_version
                self.logger.info("Executing file-transfer.json: {}".format(sftp_props))
                self.execute_ra_command_file(self.nf_res_id, "file-transfer.json", parameters=sftp_props)
                # Check again for file and raise exception if still not found.
                if not self.check_for_firmware_file():
                    raise Exception("File not found")
        except Exception as err:
            err_msg = "Failed File Download: {}".format(err)
            self.exit_error(err_msg)

        # Configure router to reload into new firmware
        try:
            msg = "3. Configure router to reload into new firmware"
            self.logger.info(msg)
            if "test" in self.firmware_version:
                raise Exception("test file")
            commands = [
                "configure terminal",
                "boot system flash bootflash:{}".format(self.firmware_version),
                "no service private-config-encryption",
                "end",
                "write memory",
                "show run | include boot",
            ]
            result = self.create_cli_manager(commands, ignore_errors=True)
            bootconf = result[-1]["result"]
            self.logger.info("bootconf: {}".format(bootconf))
            if self.firmware_version not in bootconf:
                raise Exception(bootconf)
            self.logger.info("Sending Reload command.")
            self.execute_ra_command_file(self.nf_res_id, "reload.json")
            self.logger.info("Reload command sent, sleep 10s.")
            time.sleep(10)
        except Exception as err:
            err_msg = "Failed to update boot config: {}".format(err)
            self.exit_error(err_msg)

    def get_sftp_constants(self, label):
        """Returns the Blue Planet Constants resource properties.

        If none found it will return None.

        :return: Blue Planet Constants object
        :rtype: dict
        """
        resources = self.get_active_resources(self.BUILT_IN_SFTP_FIRMWARE_CONSTANTS_TYPE, obfuscate=False)
        for res in resources:
            if res["label"].lower() == label.lower():
                return res["properties"]
        return None

    def check_for_firmware_file(self):
        """Check for firmware file on router

        Returns
        bool : True if file exists on router
        """
        self.logger.info("Checking router files")
        dir = self.create_cli_manager(["dir"])[0]["result"]
        self.logger.info("router files: {}".format(dir))

        found = self.firmware_version in dir
        self.logger.info("File Found: {}".format(found))
        return found

    def onboard_network_function(self):
        """Attempt to onboard a Network Function resource.

        RETURNS
        -------
        NetworkFunction : dict
            Resource data for new Network Function resource.
        """
        nf = self.get_network_function_by_host(self.ipAddress)

        if nf is not None and nf["orchState"].lower() != "active":
            # Attempt to delete resource if not already active
            nf_id = nf["id"]
            self.logger.info("Attempting to delete resource: " + nf_id)
            self.delete_resource(nf_id)

            attempts = 0
            while nf is not None and attempts < 5:
                time.sleep(1)
                nf = self.get_network_function_by_host(self.ipAddress)
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

        return self.get_network_function_by_host(self.ipAddress)

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
            device_ip = resp["properties"]["device_ip"]
            # Wait for relationships to be built
            try:
                self.await_resource_states_collect_timing("Waiting for " + resp_id, resp_id, interval=5, tmax=300)
                devices_deployed[device_ip] = True
            except Exception:
                try:
                    r = self.bpo.resources.get(resp_id)
                    if r is not None:
                        is_active = r["orchState"] == "active"
                        devices_deployed[device_ip] = is_active
                except Exception as ex:
                    devices_deployed[resp["properties"]["device_ip"]] = True
                    self.logger.debug("On-boarder {} already on-boarding so" " no need to check.".format(resp_id))
                    self.logger.debug("Exception: " + str(ex))

            # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
            self.delete_resource(resp_id)

            if True not in devices_deployed.values():
                nf = self.get_network_function_by_host(self.ipAddress)
                self.delete_resource(nf["id"])
                raise Exception("Failed to onboard device: {} ".format(self.ipAddress))

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        output = {"status": "Device deployed successfully"}
        self.logger.info("Output: " + json.dumps(output))

        return output

    def create_cli_manager(self, config, ignore_errors=False):
        cli_manager_product = self.get_built_in_product(self.BUILT_IN_CLI_MANAGER_TYPE)
        label = self.label + ".cli_manager"
        cli_manager_details = {
            "label": label,
            "productId": cli_manager_product["id"],
            "properties": {
                "configuration": config,
                "ipAddress": self.ipAddress,
                "ignore_errors": ignore_errors,
                "operation": "MANAGED_SERVICES_ACTIVATION",
            },
        }

        self.logger.debug("Sending following commands: " + str(config))
        res_id = self.params["resourceId"]
        clim = self.bpo.resources.create(res_id, cli_manager_details).resource
        return clim["properties"]["output_results"]["command_results"]


class Terminate(CommonPlan):
    def process(self):
        pass
