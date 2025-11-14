""" -*- coding: utf-8 -*-

Device Onboarder Plans

Versions:
   0.1 Jan 02, 2018
       Initial check in of DeviceOnboarder plans

"""

import json
import re
import time
import os.path
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class DeviceOnboarder(CompleteAndTerminatePlan):
    """this is the class that is called for activation of a device On-boarding"""
    def process(self):
        device_ip = self.properties["device_ip"]
        device_vendor = self.properties["device_vendor"]
        device_model = self.properties.get("device_model")
        session_profile_name = self.properties.get("session_profile")
        device_name = self.properties.get("device_name")
        operation = self.properties["operation"]
        self.old_dependent_count = 0

        # Set the device resource type
        vendor_resource_types = self.COMMON_TYPE_LOOKUP.get(device_vendor)
        if not vendor_resource_types:
            raise Exception(f"Device vendor '{device_vendor}' is not defined in common_plan.py")
        device_resource_type = vendor_resource_types["DEVICE_TYPE"]

        # Determine if the device already exists
        existing_devices = self.mget(
            f"/resources?resourceTypeId={device_resource_type}&q=properties.ipAddress:{device_ip}"
        ).json()
        if len(existing_devices["items"]) > 0:
            self.logger.debug(f"There's already a device with IP {device_ip}. Skipping creation.")
            return

        # check for duplicate FQDN
        short_fqdn = device_ip
        if device_ip.find(".") > 0:
            short_fqdn = device_ip.split(".")[0]
            devs = self.mget(
                f"/resources?resourceTypeId={device_resource_type}&q=properties.ipAddress:{short_fqdn}"
            ).json()
            if devs:
                if len(devs["items"]) > 0:
                    self.logger.warning(f"duplicate IP address for IP pair {device_ip} and {short_fqdn}. Skipping creation.")
                    return
                else:
                    self.logger.info(f"ipAddress not found in marketplace {devs}.")
            else:
                raise Exception("critical error, mget() function returns None value")
        else:
            # unable to use partial query query on not top-level properties,
            # use label instead of searching through all resources
            devs = self.mget(f"/resources?resourceTypeId={device_resource_type}&q=label:{short_fqdn}").json()
            if devs:
                if len(devs["items"]) > 0:
                    self.logger.warning(f"duplicate IP address for IP {short_fqdn}*. Skipping creation.")
                    return
                else:
                    self.logger.info(f"ipAddress not found in marketplace {devs}.")
            else:
                raise Exception("critical error, mget() function returns None value")

        # Get best available domain for the device
        domain = self.get_next_domain(device_vendor, device_model, session_profile_name, operation)
        if domain is None:
            raise Exception("Unable to find an available domain, please check session profiles.")

        domain_id = domain["id"]

        # Get the session profile for the domain
        # session_profile = self.get_session_profile(device_vendor, domain_id, session_profile_name)
        session_profile = self.get_session_profile_by_vendor(
            domain_id, device_vendor, device_model, session_profile_name, operation
        )
        session_profile_id = session_profile["id"]

        # Get the product id associated with the domain
        product = self.get_products_by_type_and_domain(device_resource_type, domain_id)[0]
        product_id = product["id"]

        # Enroll the device
        if not device_name:
            match = re.match(r"^(\d{0,3})\.(\d{0,3})\.(\d{0,3})\.(\d{0,3})$", device_ip)
            if match is not None:
                device_name = device_vendor + "_" + device_ip
            else:
                device_name = device_ip

        device_data = {
            "label": device_name,
            "productId": product_id,
            "properties": {"ipAddress": device_ip, "sessionProfile": session_profile_id},
        }

        self.logger.debug(f"Adding new device {device_name}")

        try:
            new_device = self.create_active_resource(
                device_name,
                self.params["resourceId"],
                device_data,
                wait_active=True,
                waittime=300,
                interval=5,
                create_relationship=False,
            ).resource
        except Exception as e:
            msg = f"Unable to add device {device_name} caused by{e}, please check connectivity state."
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg)
            self.exit_error(msg)

        if device_vendor == "JUNIPER":
            self.bpo.resources.resync(new_device["id"])

        # Wait for relationships to be built
        if operation != "MANAGED_SERVICES_ACTIVATION":
            try:
                self.await_till_collect_timing(
                    f"device onboarding {device_name}",
                    lambda: self.is_sync_done_on_device(new_device["id"]),
                    interval=10,
                    tmax=300,
                )
            except Exception:
                msg = (
                    f"""Device sync timeout to device{device_name}, NetworkConstruct resource type is not synced,
                    please check RA logs."""
                )
                self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg)
                self.exit_error(msg)

    def is_sync_done_on_device(self, device_id):
        """returns True if there are more than 5 dependents (NetworkConstruct must be one) on the device,
        or if network constructs is one of the device dependents"""

        def network_construct_present(dependents):
            if dependents is None:
                return False
            else:
                dependent_count = len(dependents)
            return "tosca.resourceTypes.NetworkConstruct" in [
                dependents[i].get("resourceTypeId") for i in range(dependent_count)
            ]

        dependents = self.get_dependents(device_id, recursive=True, exception_on_failure=False)

        return_value = False

        if dependents is None:
            dependent_count = 0
        else:
            dependent_count = len(dependents)
        if dependent_count > 5 and dependent_count <= self.old_dependent_count:
            return_value = network_construct_present(dependents)
        elif (dependent_count >= 1) and network_construct_present(dependents):
            return_value = True

        self.old_dependent_count = dependent_count

        return return_value

    def get_next_domain(self, device_vendor, model, session_profile_name, operation):
        """returns the next domain that the device should be enrolled as
        This will find the least used domain and return it.
        :param device_vendor: Name of device vendor to match the CommonPlan.COMMON_TYPE_LOOKUP
        :type device_vendor: str
        :return: Domain resource
        :rtype: dict
        """

        domain_lookup = self.COMMON_TYPE_LOOKUP.get(device_vendor)

        next_domain_index = 10000
        return_value = None
        for domain in self.mget(f"/domains?q=domainType:{domain_lookup['DOMAIN_TYPE']}").json()["items"]:
            domain_id = domain["id"]
            session_profile = None

            try:
                session_profile = self.get_session_profile_by_vendor(
                    domain_id, device_vendor, model, session_profile_name, operation
                )

            except Exception:
                self.logger.warning(f"Domain {domain['title']} does not have a valid session profile")
                continue

            if session_profile is not None:
                device_response = self.mget(
                    f"/resources?domainId={domain_id}&resourceTypeId={domain_lookup['DEVICE_TYPE']}&limit=0"
                ).json()

                if len(device_response["items"]) < next_domain_index:
                    return_value = domain
                    next_domain_index = len(device_response["items"])

        self.logger.debug("Returning domain: " + str(return_value))
        return return_value

    def get_session_profile_by_vendor(self, domain_id, device_vendor, model, session_profile_name, operation):
        session_profile = None
        if operation == "CPE_ACTIVATION":
            if device_vendor == "ADVA":
                profile_type = "netconf" if "116PRO" in model.replace(" ", "").upper() else "cli"
                self.logger.info(f"This is the profile type for Adva {profile_type}")
                session_profile = self.get_session_profile_by_type_and_label(
                    device_vendor, domain_id, profile_type, operation
                )
            else:
                session_profile = self.get_session_profile_by_label(
                    device_vendor, domain_id, operation, session_profile_name
                )
        else:
            if device_vendor == "ADVA":
                normalized_model = model.replace(" ", "").upper()
                profile_type = (
                    "netconf"
                    if "116PRO" in normalized_model or "120PRO" in normalized_model or "118" in normalized_model
                    else "cli"
                )
                session_profile = self.get_session_profile_by_type_and_label(
                    device_vendor, domain_id, profile_type, operation
                )
            else:
                session_profile = self.get_session_profile_by_label(
                    device_vendor, domain_id, operation, session_profile_name
                )
        return session_profile

    def resource_test_loop(self, action, info, interval=5, rmax=20):
        t0 = time.time()
        while True:
            if action == "post":
                resource = self.mpost("/resources", info)
                if resource.status_code < 210:
                    break
            elif action == "get":
                resource = self.mget(info)
                if resource.status_code < 210:
                    break
            elif action == "delete":
                self.mdelete(f"/resources/{info}")
                return "Gone"

            remaining = (t0 + rmax) - time.time()
            if remaining < 0:
                self.logger.debug(f"Timeout waiting for {action}.")
            self.logger.debug("Failed. Trying again.")
            time.sleep(interval)

        return resource.json()


class DeviceFileOnboarder(CommonPlan):
    """this is the class that is called for checking the state of a device list"""

    def process(self):
        file_path = "/bp2/data/" + self.properties["file_name"]
        batch_completion_percentage = self.properties.get("batch_completion_size_percentage", 70) / 100
        batch_size = self.properties.get("batch_size", 10)

        # CHECK FILE PATH
        if not os.path.exists(file_path):
            msg = f"File name {file_path} not found."
            self.categorized_error = self.ERROR_CATEGORY["MDSO"].format(msg)
            self.exit_error(msg)

        # Get the product id associated with the domain
        product = self.get_products_by_type_and_domain(self.BUILT_IN_DEVICE_ONBOARDER_TYPE, self.BUILT_IN_DOMAIN_ID)[0]
        product_id = product["id"]

        executed_onboard_list = []
        successfull_completion = []
        with open(file_path) as lines:
            for line in lines:
                line = line.strip()
                line = line.replace("\n", "")
                comp = line.split(",")
                self.logger.debug("Device file line: " + str(comp))
                device_name = comp[0]
                device_vendor = "JUNIPER"
                if len(comp) > 1 and len(comp[1]) > 3:
                    device_vendor = comp[1].upper()
                self.logger.debug(f"Device name: {device_name}, type: {device_vendor}")

                resource = {
                    "label": device_name + ".dev_onboard",
                    "productId": product_id,
                    "properties": {"device_ip": device_name, "device_vendor": device_vendor},
                }

                try:
                    executed_onboard_list.append(
                        self.create_active_resource(
                            device_name,
                            self.params["resourceId"],
                            resource,
                            wait_active=False,
                            create_relationship=False,
                        ).resource
                    )
                except Exception as ex:
                    self.logger.warning("Error attempting to create device on-boarder: " + str(ex))

                if len(executed_onboard_list) >= batch_size:
                    successfull_completion = successfull_completion + self.wait_for_batch(
                        executed_onboard_list, batch_completion_percentage
                    )
                    executed_onboard_list = []

        successfull_completion = successfull_completion + self.wait_for_batch(
            executed_onboard_list, batch_completion_percentage
        )
        if len(successfull_completion) == 0:
            raise Exception("Unable to on-board any devices.")

    def wait_for_batch(self, executed_onboard_list, batch_completion_percentage):
        """this method will watch for a certain number of resources to complete their execution

        It will return the number of resources ids that were successful.

        :param executed_onboard_list: List of onboarding resquests
        :param batch_completion_percentage: % completioon to return on
        :type executed_onboard_list: List of DeviceOnboarder
        :type batch_completion_percentage: Float (.70 == 70%)

        :return: list of successful ids
        :rtype: list
        """
        self.logger.debug("Waiting for batch with size: " + str(len(executed_onboard_list)))
        completion_list = []
        successfull_completion = []
        min_size = 1
        max_size = int(batch_completion_percentage * len(executed_onboard_list))
        if max_size > min_size:
            min_size = max_size

        self.logger.debug("Size to return: " + str(min_size))
        while len(completion_list) < min_size:
            self.logger.debug(
                "Sleeping 10 seconds before checking on-boarder state.  Completed list: " + str(completion_list)
            )
            time.sleep(10)
            for device_ob in executed_onboard_list:
                time.sleep(1)
                if device_ob is None or device_ob["id"] in completion_list:
                    continue
                try:
                    resource = self.bpo.resources.get(device_ob["id"])
                    state = resource["orchState"]
                    self.logger.debug(f"Checking on-boarder {resource['label']}, state: {resource['orchState']}")
                    if state == "active":
                        successfull_completion.append(device_ob["label"])
                        completion_list.append(device_ob["id"])
                    elif state == "failed":
                        completion_list.append(device_ob["id"])
                except Exception:
                    completion_list.append(device_ob["id"])
                    self.logger.warning("Device sync timeout." + device_ob["label"])

        self.logger.debug("Completed check.  Completed list: " + str(completion_list))
        return successfull_completion

    def enter_exit_log(self, message, state="STARTED"):
        pass


class Device:
    def __init__(self, device: dict):
        self.ip = device["device_host"]
        self.vendor = device["device_vendor"]
        self.name = device["device_name"]
        self.fqdn = device["device_fqdn"]
        self.role = device["device_role"]
        self.model = device["device_model"]
        self.resource_id = None
        self.reachable = False
        self.reachable_via = "NA"
        self.state = ""
        self.connectivity_checked = []

    def update_reachable_attributes(self, network_function_reachable_via: str):
        self.state = "AVAILABLE"
        self.reachable = True
        self.reachable_via = "FQDN" if network_function_reachable_via == self.fqdn else "IP"


class DeviceStateChecker(CommonPlan):
    """this is the class that is called for checking the state of a device list"""
    def process(self):
        device_states = []
        self.logger.debug(f"{self.properties['devices'] = }")
        for device_details in self.properties["devices"]:
            device = Device(device_details)
            # get the first available state network function or process for onboarding if none found
            network_function = self.get_network_function_by_host_or_ip(device.fqdn, device.ip, require_active=True)
            if network_function:
                device.resource_id = network_function["id"]
                device.update_reachable_attributes(network_function["properties"]["ipAddress"])
            else:
                self.logger.info("Active Network Function not found.")
                device.state = "NOT_ONBOARD"
                # IF THE DEVICE IS NOT ON-BOARDED VERIFY THAT WE CAN CONNECT TO THE DEVICE
                self.process_connectivity_check(device)

            device_details = {
                "device": device.name,
                "state": device.state,
                "reachable_ip": device.reachable,
                "device_id": device.name,
                "reachable_via": device.reachable_via,
            }

            if device.resource_id is not None:
                device_details["device_id"] = device.resource_id
            if not device.reachable:
                device_details["connectivity_checked"] = device.connectivity_checked

            device_states.append(device_details)

        # Output the Device State Details so other templates can use
        output = {"device_state": device_states}
        self.logger.debug("Output: " + json.dumps(output))

        return output

    def process_connectivity_check(self, device: Device):
        connection_check_details = self.get_connection_check_details(device)
        try:
            self.logger.info("Checking connectivity to " + device.fqdn)
            device.connectivity_checked.append(device.fqdn)
            self.bpo.resources.create(self.resource["id"], connection_check_details)
            device.reachable = True
            device.reachable_via = "FQDN"
        except Exception as ex:  # ConnectivityCheck resource raises exception if device is not reachable
            # retry connectivity with mgmt IP for CPE devices
            if device.role == "CPE":
                if device.ip.upper() == "DHCP":
                    # we can't check connectivity without a static IP address
                    device.reachable_via = "NA"
                    self.logger.info(f"CPE {device.fqdn} is not reachable via FQDN and has no static IP address. Declaring unreachable.")
                    return
                try:
                    connection_check_details["properties"]["device_ip"] = device.ip
                    self.logger.info("Checking connectivity to " + device.ip)
                    self.bpo.resources.create(self.resource["id"], connection_check_details)
                    device.reachable = True
                    device.reachable_via = "IP"
                    return
                except Exception as ex:  # ConnectivityCheck resource raises exception if device is not reachable
                    self.logger.info(f"Exception {ex} raised when checking connection to {device.ip}")
                    return
            self.logger.info(f"Exception {ex} raised when checking connection to {device.fqdn}")

    def get_connection_check_details(self, device: Device) -> dict:
        connection_product = self.get_built_in_product(self.BUILT_IN_CONNECTIVITY_CHECK_TYPE)
        return {
            "label": device.fqdn + ".connection_check",
            "productId": connection_product["id"],
            "properties": {
                "device_ip": device.fqdn,
                "device_port": self.get_device_connection_port_for_vendor(device.vendor, device.model),
                "timeout": 60,
                "method": "SSH",
                "return_delay": 1,
            },
        }

    def get_device_connection_port_for_vendor(self, vendor: str, model: str):
        """returns the port that will be tested based on the vendor"""
        if vendor == "ADVA" and self.is_netconf_model(model):
            self.logger.debug(f"Returning netconf port {self.DEFAULT_NETCONF_PORT}")
            return self.DEFAULT_NETCONF_PORT

        self.logger.debug(f"Returning CLI port {self.DEFAULT_CLI_PORT} for vendor {vendor}")
        return self.DEFAULT_CLI_PORT

    def is_netconf_model(self, model):
        return "116PRO" in model or "120PRO" in model or "118" in model
