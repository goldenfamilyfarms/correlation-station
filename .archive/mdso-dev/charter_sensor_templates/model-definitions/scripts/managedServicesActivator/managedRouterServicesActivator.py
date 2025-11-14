import json
import re
import time
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough


class MRSA_Exception(Exception):
    pass


class Activate(CommonPlan, CliCutthrough):
    """
    Checking Operation Type
    Validate Supported Device Model
    Checking Existing Resources
    Onboard device
    Validate Firmware
    Update Firmware
    Validate Firmware after update
    Get Banner configuration
    Send configuration
    Send Banner configuration
    Deleting Network Function
    """

    def process(self):
        self.label = self.resource["label"]
        props = self.resource["properties"]
        self.ipAddress = props["ipAddress"]
        self.firmwareVersion = props.get("firmwareVersion")
        self.device_whitelist_cisco = ["C1111", "4431", "4451"]
        self.fqdn = props["fqdn"]
        self.configuration = props["configuration"]
        self.vendor = props["vendor"]
        self.model = props["model"]
        self.ignore_errors = bool(props.get("ignore_errors", False))
        self.operationType = props["operationType"]

        # Check operation type
        msg = "Checking Operation Type"
        self.status_messages(msg, parent="mrs_activation")
        if self.operationType != "New":
            err = "Operation " + self.operationType + " is not supported."
            err_msg = "Failed Step {}: {}".format(msg, err)
            self.update_status_and_exit(err_msg)

        # Validate Supported Device Model
        msg = "Validating Supported Device Model"
        self.status_messages(msg, parent="mrs_activation")
        valid = False
        try:
            for model in self.device_whitelist_cisco:
                if model in self.model.upper():
                    valid = True
                    break
            if not valid:
                raise MRSA_Exception("Unsupported Device Model - Do Not Reattempt!")
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.update_status_and_exit(err_msg)
        except Exception as err:
            err_msg = "Failed: {} - Reason: Platform error; Please manually " "provision".format(msg)
            self.logger.error(err)
            self.update_status_and_exit(err_msg)

        # Check Existing Resources
        msg = "Checking Existing Resources"
        self.status_messages(msg, parent="mrs_activation")
        try:
            self.check_existing_resource()
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.update_status_and_exit(err_msg)
        except Exception as err:
            err_msg = "Failed: {} - Reason: Failed onboard prechecks. Provision " "manually.".format(msg)
            self.logger.error(err)
            self.update_status_and_exit(err_msg)

        # Onboard device
        msg = "Onboarding Device"
        self.status_messages(msg, parent="mrs_activation")
        fqdn = self.fqdn or self.ipAddress
        try:
            nf = self.onboard_network_function(fqdn)
            self.logger.info("Device Onboarded: " + str(nf))
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.update_status_and_exit(err_msg)
        except Exception as err:
            err_msg = (
                "Failed: {} - Reason: Unable to onboard device. "
                "Please confirm router connectivity before retrying "
                "automation.".format(msg)
            )
            self.logger.error(err)
            self.update_status_and_exit(err_msg)

        """(1/5/22)Pending mgmt tunnel BWU from customer. Est 1/27/22"""
        # # Validate Firmware
        # msg = "Validate Firmware"
        # self.status_messages(msg, parent="mrs_activation")
        # firmware_validated = True
        # try:
        #     if self.firmwareVersion:
        #         validator_product = self.get_built_in_product(
        #             self.BUILT_IN_MANAGED_ROUTER_FIRMWARE_VALIDATOR_TYPE)
        #         validator_details = {
        #             "label": self.label + ".firmware_validator",
        #             "productId": validator_product['id'],
        #             "properties": {
        #                 "ipAddress": self.ipAddress,
        #                 "firmwareVersion": self.firmwareVersion
        #             }
        #         }
        #         validator = self.bpo.resources.create(
        #                         self.params['resourceId'],
        #                         validator_details).resource
        #         self.logger.info("validator: {}".format(validator))
        #         firmware_validated = validator['properties']['approved']
        #         self.logger.info("Valid: {}".format(firmware_validated))
        #         if not firmware_validated:
        #             raise MRSA_Exception(
        #                 "Invalid Firmware version found on router. Please "
        #                 "manually update firmware before running automation.")
        # except MRSA_Exception as err:
        #     err_msg = "Failed: {} - Reason: {}".format(msg, err)
        #     self.update_status_and_exit(err_msg)
        # except Exception as err:
        #     err_msg = ("Failed: {} - Reason: Unable to Validate Firmware. "
        #                "Please confirm router connectivity before retrying "
        #                "automation.".format(msg))
        #     self.logger.error(err)
        #     self.update_status_and_exit(err_msg)

        # # Update Firmware
        # msg = "Update Firmware"
        # try:
        #     updater = None
        #     if not firmware_validated:
        #         self.status_messages(msg, parent="mrs_activation")
        #         updater_product = self.get_built_in_product(
        #             self.BUILT_IN_MANAGED_ROUTER_FIRMWARE_UPDATER_TYPE)
        #         updater_details = {
        #             "label": self.label + ".firmware_updater",
        #             "productId": updater_product['id'],
        #             "properties": {
        #                 "ipAddress": self.ipAddress,
        #                 "firmwareVersion": self.firmwareVersion
        #             }
        #         }
        #         updater = self.bpo.resources.create(
        #                         self.params['resourceId'],
        #                         updater_details,
        #                         wait_time=2700).resource
        #         if updater['orchState'] != 'active':
        #             reason = updater.get('reason') or 'Unknown Error'
        #             raise MRSA_Exception(reason)
        # except MRSA_Exception as err:
        #     err_msg = "Failed: {} - Reason: {}".format(msg, err)
        #     self.update_status_and_exit(err_msg)
        # except Exception as err:
        #     err_msg = ("Failed: {} - Reason: Unable to Update Firmware. "
        #     "Please confirm router connectivity before retrying automation.".format(msg))
        #     self.logger.error(err)
        #     self.update_status_and_exit(err_msg)

        # # Wait for router to recover from reload and verify firmware
        # msg = "Verify Firmware After Router Recovery."
        # try:
        #     if updater is not None:
        #         self.status_messages(msg, parent="mrs_activation")

        #         # Restart session
        #         session_id = nf.get('providerResourceId')
        #         self.logger.info('Restarting session: {}'.format(session_id))
        #         requests.post(self.SESSION_URL.format(session_id) + '/restart',
        #                       headers={'Content-Type': 'application/json'})

        #         # Wait for router recovery from reload.  Checks session status
        #         # every 20s for 10 minutes.  If status is not `CONNECTED` after
        #         # 10 minutes, then exception is raised.
        #         attempts = 0
        #         status = "DISCONNECTED"
        #         while attempts < 30:
        #             time.sleep(20)
        #             attempts += 1
        #             session = requests.get(
        #                     self.SESSION_URL.format(session_id),
        #                     headers={'Content-Type': 'application/json'}
        #                 ).json()
        #             self.logger.info("get session: {}".format(session))
        #             status = session.get("connectState").upper()
        #             if status == "CONNECTED":
        #                 self.logger.info("Session reconnected!")
        #                 break
        #             self.logger.info("Check {}: {}".format(attempts, status))
        #         if attempts == 30 and status != "CONNECTED":
        #             raise MRSA_Exception('10-minute recovery timer exceeded. Manually provision services.')

        #         # Validate firmware again. Raise exception if still invalid.
        #         validator = self.bpo.resources.create(
        #                     self.params['resourceId'],
        #                     validator_details).resource
        #         self.logger.info("validator: {}".format(validator))
        #         firmware_validated = validator['properties']['approved']
        #         self.logger.info("Valid: {}".format(firmware_validated))
        #         if not firmware_validated:
        #             raise MRSA_Exception("Firmware Failed to Update. Manually provision services.")
        # except MRSA_Exception as err:
        #     err_msg = "Failed: {} - Reason: {}".format(msg, err)
        #     self.update_status_and_exit(err_msg)
        # except Exception as err:
        #     err_msg = ("Failed: {} - Reason: Unable to Verify Firmware After Router Recovery. "
        #     "Manually provision services.".format(msg))
        #     self.logger.error(err)
        #     self.update_status_and_exit(err_msg)

        # Get Banner Configuration
        msg = "Get Banner Configuration"
        self.status_messages(msg, parent="mrs_activation")
        try:
            config, banner_config, delimiter = self.get_banner()
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.update_status_and_exit(err_msg)
        except Exception as err:
            err_msg = (
                "Failed: {} - Reason: Unable to get banner "
                "configuration. Verify partial configuration sent. "
                "Manually provision services.".format(msg)
            )
            self.logger.error(err)
            self.update_status_and_exit(err_msg)

        # Sending configuration
        msg = "Sending Configuration"
        self.status_messages(msg, parent="mrs_activation")
        try:
            cli_mngr_result = self.create_cli_manager(config)
            self.logger.info("Configuration Result: " + str(cli_mngr_result))
            self.verify_config_delivery(cli_mngr_result, nf["id"])
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.update_status_and_exit(err_msg)
        except Exception as err:
            err_msg = (
                "Failed: {} - Reason: Unable to send configuration. "
                "Verify partial configuration sent. Manually provision "
                "services.".format(msg)
            )
            self.logger.error(err)
            self.update_status_and_exit(err_msg)

        # Sending Banner configuration
        msg = "Sending Banner Configuration"
        self.status_messages(msg, parent="mrs_activation")
        try:
            if banner_config:
                banner_result = self.create_cli_manager(banner_config, banner=True, delimiter=delimiter)
                self.logger.info("Banner Result: " + str(banner_result))
                self.verify_config_delivery(banner_result, nf["id"])
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.update_status_and_exit(err_msg)
        except Exception as err:
            err_msg = (
                "Failed: {} - Reason: Unable to send banner "
                "configuration. Verify partial configuration sent. "
                "Manually provision services.".format(msg)
            )
            self.logger.error(err)
            self.update_status_and_exit(err_msg)

        # Deleting Network Function
        msg = "Deleting Network Function"
        self.status_messages(msg, parent="mrs_activation")
        try:
            if nf is not None:
                self.delete_resource(nf["id"])
        except MRSA_Exception as err:
            err_msg = "Failed: {} - Reason: {}".format(msg, err)
            self.logger.error(err)
        except Exception as err:
            err_msg = "Failed: {} - Reason: Unable to delete Network " "Function".format(msg)
            self.logger.error(err)

    def check_existing_resource(self):
        """Verify no MSA resources exist with provided fqdn.

        Raises Exception if MSA resource found in active or activating state.
        Deletes resource if one is found in `failed` state.
        """
        activators = self.get_resources_by_type_and_label(
            self.BUILT_IN_MANAGED_ROUTER_SERVICE_ACTIVATOR_TYPE, self.label
        )

        for activator in activators:
            state = activator["orchState"]
            activator_id = activator["id"]
            if state == "failed":
                # terminate this one
                dep = self.bpo.resources.get_dependents(activator_id)
                if dep:
                    self.bpo.resources.delete(dep[0]["id"])
                self.bpo.resources.delete(activator_id)
            elif state == "active":
                # prevent activating this self.site again
                raise MRSA_Exception(
                    "Managed Service Activation is complete - " "DO NOT REATTEMPT {}".format(self.label)
                )
            elif state == "activating" and activator_id != self.resource_id:
                # prevent activating this self.site again
                raise MRSA_Exception(
                    "Managed Service Activation is in progress - " "DO NOT REATTEMPT {}".format(self.label)
                )

    def update_status_and_exit(self, msg):
        """Update status_message and exit_error message.

        PARAMETERS
        ----------
            msg : str
                Message to deliver
        """
        self.status_messages(msg, error=True, parent="mrs_activation")
        self.exit_error(msg)

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
            # Network Function resource found but not in active state.
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
            # Active NetworkFunction Resource found.
            self.logger.info("Found active Network Function: " + str(nf))
            return nf

        # Onboard new Network Function
        onboard_product = self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)
        device_name = fqdn.split(".")[0]
        label = device_name + ".device_onboarder"
        created_onboarded_res = []
        devices_deployed = {}
        devices_deployed[self.label] = False
        onboard_details = {
            "label": label,
            "productId": onboard_product["id"],
            "properties": {
                "device_ip": self.ipAddress,
                "device_name": device_name,
                "device_vendor": self.vendor.upper(),
                "device_model": self.model.upper(),
                "device_already_active": True,
                "operation": "MANAGED_SERVICES_ACTIVATION",
            },
        }

        self.logger.debug("On-boarding device: " + device_name)
        device_res = self.bpo.resources.create(self.params["resourceId"], onboard_details)
        self.logger.debug("Resource Created: {}".format(device_res))
        created_onboarded_res.append(device_res.resource)

        # NOW WAIT FOR ONBOARDER TO FINISH
        resp = device_res.resource
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
                    devices_deployed[device_ip] = r["orchState"] == "active"
            except Exception as ex:
                devices_deployed[device_ip] = True
                self.logger.debug("On-boarder {} already on-boarding so no" " need to check.".format(resp_id))
                self.logger.debug("Exception: " + str(ex))

        # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
        self.delete_resource(resp_id)

        # Get created NetworkFunction resource
        nf = self.get_network_function_by_host_or_ip(fqdn, self.ipAddress)

        if True not in devices_deployed.values():
            # Delete Network Function and raise Exception if resource failed.
            self.delete_resource(nf["id"])
            raise Exception("Failed to onboard device: {}".format(fqdn))

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        output = {"status": "Device deployed successfully"}
        self.logger.info("Output: " + json.dumps(output))

        return nf

    def get_banner(self):
        """Parse configuration for banner.

        RETURNS
        -------
        configuration : List[str]
            Original configuration with banner removed.
        banner_config : List[str]
            Banner configuration parsed from original.
        delimiter : str
            Character indicating beginning and end of banner.
        """
        banner_config = []
        delimiter = None

        banner_re = re.compile(r"(banner\s+\S+)\s*(\S{1})([\W\w]*)\2")
        configuration = "\n".join(self.configuration)
        result = banner_re.search(configuration)
        if result:
            banner_config = result.group(0)
            delimiter = result.group(2)

            if banner_config.count(delimiter) > 2:
                # Make sure we only use first two delimiters in config.
                _i = banner_config.index(delimiter, banner_config.index(delimiter) + 1)
                banner_config = banner_config[:_i]

            banner_index = configuration.find(banner_config)
            configuration = configuration[:banner_index] + configuration[banner_index + len(banner_config):]
            banner_config = banner_config.split("\n")

        return configuration.split("\n"), banner_config, delimiter

    def create_cli_manager(self, config, banner=False, delimiter=None):
        """Build CLIManager resource to send configuration.

        PARAMS
        ------
        config : List[str]
            configuration lines to be sent
        banner : bool (Optional)
            True if sending banner configuration
        delimiter : str (Optional)
            delimiter for banner configuration

        RETURNS
        -------
        output_results:  dict
            status and command results

        Sample of output_results:
        {
            "status": "full",
            "command_results": [
                {
                    "command": "command1",
                    "result": "result1"
                },
                {
                    "command": "command2",
                    "result": "result2"
                }
            ]
        }
        """
        cli_manager_product = self.get_built_in_product(self.BUILT_IN_CLI_MANAGER_TYPE)
        label = self.fqdn.split(".")[0] + ".cli_manager"
        cli_manager_details = {
            "label": label,
            "productId": cli_manager_product["id"],
            "properties": {
                "configuration": config,
                "ipAddress": self.ipAddress,
                "operation": "MANAGED_SERVICES_ACTIVATION",
                "ignore_errors": self.ignore_errors,
                "banner": banner,
            },
        }

        if banner:
            cli_manager_details["properties"]["additionalAttributes"] = {"delimiter": delimiter, "config_mode": True}
        if self.fqdn is not None:
            cli_manager_details["fqdn"] = self.fqdn
        self.logger.debug("Sending following commands: " + str(config))
        created_cli_manager = self.bpo.resources.create(self.params["resourceId"], cli_manager_details)

        return created_cli_manager.resource["properties"]["output_results"]

    def verify_config_delivery(self, output_results, nf_id):
        """Verify success of configuration delivery.

        Attempts to delete Network Function resource on unsuccessful config
        delivery and raises an Exception.

        PARAMETERS
        ----------
        output_results : dict
            CLIManager resource data
        nf_id : str
            Network Function ID
        """
        output_status = output_results["status"]
        command_results = output_results["command_results"]

        # If configuration did not complete, then display the last 5
        # configuration lines and exit the configuration.
        if output_status != "full":
            self.logger.debug("Config Error: " + str(command_results))
            if len(command_results) == 0:
                err_msg = "No configuration sent."
            else:
                line_num = len(command_results)
                last_command = command_results[-1].get("command")
                last_result = command_results[-1].get("result")
                err_msg = "Error encountered on line {}. ".format(line_num)
                err_msg += "Command: {} Result: {} ".format(last_command, last_result)

            self.logger.info("Deleting Network Function: " + nf_id)
            try:
                self.delete_resource(nf_id)
            except Exception as err:
                self.logger.error("Failed to delete Network Function: {}".format(err))
            else:
                self.logger.info("Network Function deleted.")
            finally:
                raise MRSA_Exception(err_msg)


class Terminate(CommonPlan):
    pass
