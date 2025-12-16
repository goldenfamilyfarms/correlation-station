""" -*- coding: utf-8 -*-

ServiceDeviceOnboarder Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of ServiceDeviceOnboarder plans

"""
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
from scripts.otel_instrumentation.otel_mixin import OTelMixin
import json
import sys
sys.path.append('model-definitions')


class Activate(CompleteAndTerminatePlan, OTelMixin):
    """this is the class that is called for the initial activation of the
    ServiceDeviceConfigurator.
    """

    def process(self):
        # Initialize OTel instrumentation
        self.__init_otel__()
        
        # Create root span for the entire process
        with self.create_root_span(operation_name="service_device_onboarder"):
            circuit_details_id = self.properties["circuit_details_id"]
            context = self.properties["context"]
            operation = self.properties["operation"]
            
            # Set correlation baggage from instance attributes
            if getattr(self, '_otel_initialized', False):
                self.set_correlation_baggage_from_instance()

            # Get the circuit details and network service
            circuit_details = self.get_resource(circuit_details_id)
        circuit_details_props = circuit_details["properties"]

        devices_to_onboard = circuit_details_props.get("devices_to_onboard", [])
        if len(devices_to_onboard) == 0:
            self.logger.debug("No devices to onboard found")
            return
            
        # Extract and set topology context from circuit details
        if getattr(self, '_otel_initialized', False):
            self.extract_and_set_topology_context(circuit_details_props)
            
        # Build the lookup and add the device if it is not there
        # GET THE COMMUNICATION STATE OF THE RESOURCES by using the DeviceStateChecker resource
        onboard_product = self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)

        affected_devices = self.get_affected_devices_from_circuit(self.resource["id"], circuit_details, operation)
        self.logger.info(f"affected_devices are {affected_devices}")

        created_onboarded_res = []
        devices_deployed = {}
        for device in devices_to_onboard:
            device_actual_role = self.get_node_role(circuit_details, device)
            device_role = "PE" if device_actual_role in ["PE", "AGG", "MTU"] else "CPE"
            device_hostname = self.get_node_hostname(circuit_details, device)
            device_fqdn = self.get_node_fqdn(circuit_details, device)
            device_ip = self.get_node_management_ip(circuit_details, device)
            reachable_via = self.get_node_reachability(circuit_details, device)
            if device_role.upper() == context:
                devices_deployed[device_hostname] = False

            network_service = self.get_associated_network_service_for_resource(self.params["resourceId"])
            self.logger.info(f"Network service in service device onboarder {network_service}")

            connection_param = device_ip if reachable_via == "IP" else device_fqdn
            use_ip_always = ["CPE_ACTIVATION"]
            if operation in use_ip_always and device_ip.upper() != "DHCP":
                connection_param = device_ip

            if device_hostname in devices_to_onboard and (context == "ALL" or device_role.upper() == context):
                # Create network function span for device onboarding
                tid = device_hostname
                from contextlib import nullcontext
                span_ctx = self.create_network_function_span_context(tid, device_fqdn, "onboard") if getattr(self, '_otel_initialized', False) else nullcontext()
                with span_ctx:
                    nf = self.get_network_function_by_host(device_fqdn)
                    # Network function was created during provisioning of primary leg but Bpo State on secondary leg incorrectly shows "NOT-ONBOARD"
                    if nf and self.get_node_bpo_state(circuit_details, device) == "NOT-ONBOARD":
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("device.onboard.retry", {"device": device_hostname, "reason": "bpo_state_not_onboard"})
                        _, onboard_details = self.generate_onboard_details(device_hostname, circuit_details, onboard_product, connection_param, device)
                        device_res = self.add("Resource", "/resources", onboard_details)
                        created_onboarded_res.append(device_res)

                    if not nf and device_role.upper() != "PE":
                        nf = self.get_network_function_by_host(device_ip)

                    if not nf:
                        devices_deployed[device_hostname] = False
                        label, onboard_details = self.generate_onboard_details(device_hostname, circuit_details, onboard_product, connection_param, device)

                        if operation == "CPE_ACTIVATION":
                            onboard_details["properties"]["operation"] = "CPE_ACTIVATION"

                        # check market for resource already existing with identical label
                        self.logger.debug("***********")
                        try:
                            check_label = self.bpo.resources.get_one_by_filters(
                                resource_type="charter.resourceTypes.DeviceOnboarder",
                                q_params={"label": label},
                            )
                            self.logger.debug("Checking for device onboarder for resource:", check_label)
                            if check_label["label"] == label:
                                self.logger.debug("On-boarding already processing for device: " + device_hostname)
                                if getattr(self, '_otel_initialized', False):
                                    self.record_span_event_from_instance("device.onboard.already_processing", {"device": device_hostname})
                                created_onboarded_res.append(check_label)
                        except Exception as ex:
                            self.logger.debug("On-boarding device: " + device_hostname)
                            if getattr(self, '_otel_initialized', False):
                                self.record_span_event_from_instance("device.onboard.start", {"device": device_hostname, "vendor": onboard_details["properties"].get("device_vendor"), "model": onboard_details["properties"].get("device_model")})
                            device_res = self.add("Resource", "/resources", onboard_details)
                            created_onboarded_res.append(device_res)

        # NOW WAIT FOR THEM ALL TO FINISH
        for resp in created_onboarded_res:
            resp_id = resp["id"]
            device_name = resp["properties"]["device_name"]
            # Wait for relationships to be built
            try:
                from contextlib import nullcontext
                timed_ctx = self.timed_operation("device_onboard_wait", {"device": device_name}) if getattr(self, '_otel_initialized', False) else nullcontext()
                with timed_ctx:
                    self.await_resource_states_collect_timing("Waiting for " + resp_id, resp_id, interval=5, tmax=300)
                    devices_deployed[device_name] = True
                    if getattr(self, '_otel_initialized', False):
                        self.record_span_event_from_instance("device.onboard.completed", {"device": device_name})
            except Exception as ex:
                try:
                    r = self.bpo.resources.get(resp_id)
                    if r is not None:
                        devices_deployed[device_name] = r["orchState"] == "active"
                except Exception:
                    devices_deployed[device_name] = False
                    if getattr(self, '_otel_initialized', False):
                        self.otel_error_handler(f"On-boarder {resp_id} failed for device {device_name}", ex)
                    self.logger.debug(f"On-boarder {resp_id} already on-boarding so no need to check.")
                    self.logger.debug(f"Exception: {ex}")

                # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
                self.delete_resource(resp_id)

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        # NOW UPDATE THE CIRCUIT DETAILS
        for device, deployed in devices_deployed.items():
            if deployed is True:
                bpo_state = self.BPO_STATES["AVAILABLE"]["state"]
                self.update_node_prop_value(device, circuit_details_id, "Bpo State", bpo_state)
                if device in devices_to_onboard:
                    new_onboard = "TRUE"
                else:
                    new_onboard = "FALSE"
                self.update_node_prop_value(device, circuit_details_id, "Newly Onboard", new_onboard)
            else:
                bpo_state = self.BPO_STATES["UNKNOWN"]["state"]
                self.update_node_prop_value(device, circuit_details_id, "Bpo State", bpo_state)
            if deployed is True and device in devices_to_onboard:
                devices_to_onboard.remove(device)

        # Fetch circuit details resource again after all the patches
        circuit_details = self.get_resource(circuit_details_id)
        circuit_details["properties"]["devices_to_onboard"] = devices_to_onboard

        self.logger.debug("Updated circuit details: " + json.dumps(circuit_details, indent=4))
        self.bpo.resources.patch(circuit_details["id"], {"properties": circuit_details["properties"]})

    def generate_onboard_details(self, device_hostname, circuit_details, onboard_product, connection_param, device):
        label = device_hostname + ".device_onboarder"
        vendor = self.get_node_vendor(circuit_details, device)
        model = self.get_node_model(circuit_details, device)
        onboard_details = {
            "label": label,
            "productId": onboard_product["id"],
            "properties": {
                "device_ip": connection_param,
                "device_name": device,
                "device_vendor": vendor,
                "device_model": model,
                "resource_name": "device_onboarder",
                "device_already_active": True,
            },
        }
        return label, onboard_details
