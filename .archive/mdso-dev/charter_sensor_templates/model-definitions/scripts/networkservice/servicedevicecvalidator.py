""" -*- coding: utf-8 -*-

ServiceDeviceValidator Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of ServiceDeviceValidator plans

    0.2 Feb 10, 2018
        - Removed the assumption that the PE routers are on-boarded already into BPO and
        treat them the same as the CPEs and dynamically on-board them.

"""

import sys

sys.path.append("model-definitions")
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    ServiceDeviceConfigurator.
    """
    def process(self):
        circuit_details_id = self.properties["circuit_details_id"]
        self.operation = self.properties["operation"]

        # Get the circuit details and network service
        self.circuit_details = self.get_resource(circuit_details_id)
        self.circuit_id = self.circuit_details["properties"]["circuit_id"]

        # Get device details
        affected_devices = self.get_affected_devices_from_circuit(
            self.resource["id"], self.circuit_details, self.operation
        )
        devices = self.get_affected_devices_attributes(affected_devices)

        # GET THE COMMUNICATION STATE OF THE RESOURCES by using the DeviceStateChecker resource
        device_check_product_res = self.create_and_cleanup_device_state_checker(devices)

        # REFRESH CIRCUIT DETAILS, and NOW CHECK THE STATE RETURNED.  IF NOT AVAILABLE EXCEPTION OUT
        devices_to_add = []
        self.logger.debug(f"{device_check_product_res = }")
        self.circuit_details = self.bpo.resources.get(circuit_details_id)

        for device in device_check_product_res["properties"]["device_state"]:
            name = device["device"]
            state = device["state"]
            reachable = device["reachable_ip"]
            reachable_via = device["reachable_via"]
            device_role = self.get_node_role(self.circuit_details, name)
            device_equipment_status = self.get_device_equipment_status(name, device_role)

            if self.skip_device(device_role, device_equipment_status):
                self.logger.info(f"Device connectivity not required for {name}")
                continue

            if not reachable:  # no available network function, connectivity check failed with FQDN and IP - fall out
                self.device_connectivity_error_process(reachable, device_role, name, state, device_equipment_status)

            if reachable and state == "NOT_ONBOARD":  # connectivity checks out, just need to onboard
                devices_to_add.append(name)

            # if reachable and onboard, hooray! carry on.

            node_prop_names = ["Ip Reachable", "Bpo State", "Reachable Via"]
            node_prop_values = [str(reachable), self.BPO_STATES[state]["state"], reachable_via]
            self.update_node_prop_value(name, circuit_details_id, node_prop_names, node_prop_values)

        # NOW FETCH UPDATED CIRCUIT DETAILS AND PATCH WITH THE DEVICES THAT WILL NEED TO BE ADDED TO BPO
        self.circuit_details = self.get_resource(circuit_details_id)
        self.circuit_details["properties"]["devices_to_onboard"] = devices_to_add

        self.bpo.resources.patch(circuit_details_id, {"properties": self.circuit_details["properties"]})

    def get_affected_devices_attributes(self, affected_devices):
        devices = []
        for device in affected_devices:
            devices.append(
                {
                    "device_name": device,
                    "device_vendor": self.get_node_vendor(self.circuit_details, device),
                    "device_host": self.get_node_management_ip(self.circuit_details, device),
                    "device_fqdn": self.get_node_fqdn(self.circuit_details, device),
                    "device_role": self.get_node_role(self.circuit_details, device),
                    "device_model": self.get_node_model(self.circuit_details, device),
                }
            )
        return devices

    def create_and_cleanup_device_state_checker(self, devices):
        device_check_product = self.get_built_in_product(self.BUILT_IN_DEVICE_STATE_CHECK_TYPE)

        label = self.circuit_id + ".device_check"
        device_check_params = {
            "label": label,
            "productId": device_check_product["id"],
            "properties": {"devices": devices, "property_path": "properties.ipAddress"},
        }

        device_check = self.create_active_resource(
            label,
            self.params["resourceId"],
            device_check_params,
            wait_active=True,
            waittime=360,
            interval=5,
            create_relationship=False,
        )

        device_check_id = device_check.resource["id"]
        device_check_product_res = self.get_resource(device_check_id)
        self.delete_resource(device_check_id)
        return device_check_product_res

    def get_device_equipment_status(self, name, device_role):
        device_equipment_status = self.get_node_property(self.circuit_details, name, "Equipment Status")
        if device_equipment_status is None:
            if self.operation == "CPE_ACTIVATION":
                device_equipment_status = "PLANNED" if device_role == "CPE" else "LIVE"
            else:
                device_equipment_status = "UNKNOWN"
        return device_equipment_status

    def skip_device(self, device_role, device_equipment_status):
        return (
            device_role == "CPE"
            and self.operation == "DISCONNECT_MAPPER"
            and device_equipment_status == "PENDING DECOMMISSION"
        )

    def device_connectivity_error_process(self, reachable, device_role, name, state, device_equipment_status):
        self.logger.debug(f"Device reachability error. {name} reachable: {reachable} state: {state} status: {device_equipment_status}")
        # if failed connectivity checks, we'll assess based on device role
        self.failed_connectivity_checks_error(device_role, name, state)
        # MTU, CPE can have failed connectivity checks and not be onboarded, unless live
        if self.is_unavailable_live_device(state, device_equipment_status):
            msg = self.error_formatter(
                self.CONNECTIVITY_ERROR_TYPE,
                "Unreachable Live Device",
                f"device: {name} communication state: {state} equipment status: {device_equipment_status}",
            )
            self.categorized_error = msg
            raise Exception(msg)

        if self.is_available_invalid_equipment_status_device(state, device_equipment_status):
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Reachable Invalid Equipment Status Device",
                f"device: {name} communication_state: AVAILABLE equipment status: {device_equipment_status}"
            )
            self.categorized_error = msg
            self.exit_error(msg)

    def failed_connectivity_checks_error(self, device_role, name, state):
        msg = self.error_formatter(
            self.CONNECTIVITY_ERROR_TYPE,
            "Pre-Onboarding Failed Connectivity Checks",
            f"device: {name} role: {device_role} state: {state} connectivity check: failed",
        )
        self.categorized_error = msg
        if device_role in ["PE", "AGG"]:
            raise Exception(msg)
        elif device_role in ["CPE", "MTU"] and state == "NOT_ONBOARD":
            if self.operation_requires_all_devices_reachable():
                self.exit_error(msg)
        # if CPE, MTU and other state, we'll continue to check for other issues

    def operation_requires_all_devices_reachable(self):
        # it's ok for network service to not have the last device in line installed
        all_devices_operations = [
            "NETWORK_SERVICE_UPDATE",
            "NETWORK_SERVICE_DELETION",
            "CPE_ACTIVATION",
            "SERVICE_MAPPER",
            "TRANSPORT",
        ]
        return self.operation in all_devices_operations

    def is_unavailable_live_device(self, state, device_equipment_status):
        return state != "AVAILABLE" and device_equipment_status == "LIVE"

    def is_available_invalid_equipment_status_device(self, state, device_equipment_status):
        invalid_statuses = ["PLANNED", "DESIGNED"]
        any_equipment_status_operations = ["CPE_ACTIVATION", "SERVICE_MAPPER", "SLM"]
        return (
            state == "AVAILABLE"
            and device_equipment_status.split("-")[-1] in invalid_statuses
            and self.operation not in any_equipment_status_operations
        )
