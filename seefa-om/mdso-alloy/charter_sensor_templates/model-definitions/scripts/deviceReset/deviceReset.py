"""-*- coding: utf-8 -*-
deviceReset.py
Versions:
    9/5/2025
    todo list
        -
        -
"""


import sys
sys.path.append('model-definitions')
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.serviceMapper.common import Common, Device
from scripts.common_plan import CommonPlan
from scripts.otel.otel_mixin import OTelMixin
from scripts.deviceReset.advaReset import AdvaReset
from scripts.deviceReset.juniperReset import JuniperReset
from scripts.deviceReset.radReset import RadReset
from scripts.deviceReset.nokiaReset import NokiaReset


class DeviceReset:
    RESET = {
        "JUNIPER": JuniperReset,
        "RAD": RadReset,
        "ADVA": AdvaReset,
        "NOKIA": NokiaReset,
        "ALCATEL": NokiaReset,
    }

    def __init__(self, plan, device_values: Device, circuit_id, circuit_details_id):
        self.plan = plan
        self.device_values = device_values
        self.circuit_id = circuit_id
        self.circuit_details_id = circuit_details_id
        self.vendor_modeler = self.RESET[self.device_values.vendor](
            plan=self.plan,
            device_values=self.device_values,
            circuit_id=self.circuit_id,
            circuit_details_id=self.circuit_details_id,
        )

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class Activate(CommonPlan, OTelMixin):
    def process(self):
        # Initialize OTel instrumentation
        self.__init_otel__()

        # Create root span for device reset
        with self.create_root_span(operation_name="device_reset"):
            # Set correlation baggage
            self.set_correlation_baggage_from_instance()

            self.initialize()

            # Add span attributes
            if getattr(self, '_otel_initialized', False):
                from opentelemetry import trace
                span = trace.get_current_span()
                if span and span.is_recording():
                    span.set_attribute("device_reset.circuit_id", self.circuit_id)
                    span.set_attribute("device_reset.service_type", self.service_type)
                    if self.device_tid:
                        span.set_attribute("device_reset.target_device", self.device_tid)

            topology_devices = self.get_all_devices_from_topology()

            # Record device count
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance("device_reset.devices_found", {
                    "device_count": len(topology_devices),
                    "service_type": self.service_type
                })

            for device_data in topology_devices:
                device = Device(device_data)
                if self.device_tid:
                    if self.device_tid == device.tid:
                        self.logger.info(f"device: {device}")
                        # Reset specific device with timing
                        with self.timed_operation("device_reset.execute", {"vendor": device.vendor, "tid": device.tid}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                            self.device_reset_payload(device)
                            if getattr(self, '_otel_initialized', False):
                                self.record_span_event_from_instance("device_reset.completed", {"vendor": device.vendor, "tid": device.tid})
                        break
                else:
                    # Reset all devices with timing per device
                    with self.timed_operation("device_reset.execute", {"vendor": device.vendor, "tid": device.tid}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                        self.device_reset_payload(device)
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("device_reset.completed", {"vendor": device.vendor, "tid": device.tid})

    def _nullcontext(self):
        """Return a nullcontext for when OTel is not initialized."""
        from contextlib import nullcontext
        return nullcontext()

    def initialize(self):
        self.circuit_id = self.properties["circuit_id"]

        # Get circuit details with timing
        with self.timed_operation("device_reset.get_circuit_details") if getattr(self, '_otel_initialized', False) else self._nullcontext():
            self.circuit_details = self._get_circuit_details()

        self.circuit_details_id = self.circuit_details["id"]
        self.service_type = self.circuit_details["properties"]["serviceType"]
        self.device_tid = self.properties.get("device_tid")
        self.environment_safety_check()

    def get_all_devices_from_topology(self):
        topology_devices = list(self.circuit_details["properties"]["topology"][0]["data"]["node"])
        if self.service_type == "ELINE":
            topology_devices.extend(list(self.circuit_details["properties"]["topology"][1]["data"]["node"]))
        return topology_devices

    def device_reset_payload(self, device: Device):
        return DeviceReset(
            plan=self,
            device_values=device,
            circuit_id=self.circuit_id,
            circuit_details_id=self.circuit_details_id,
        )

    def _get_circuit_details(self):
        if self.properties.get("circuit_details_id"):
            return self.bpo.resources.get(self.properties["circuit_details_id"])
        else:
            # generate circuit details, handle any onboarding necessary
            handler = CircuitDetailsHandler(plan=self, circuit_id=self.circuit_id, operation="DEVICE_RESET")
            handler.device_onboarding_process()
            return handler.circuit_details

    def environment_safety_check(self):
        global_values = self.get_resources_by_type_and_label("charter.resourceTypes.BpoConstants", "Globals", no_fail=True)
        alternate_server_url = global_values[0]["properties"]["circuit_details_server_info"]["alternate_server_url"]
        if "47.43.111.73" not in alternate_server_url:
            self.logger.info('DEVICE RESET NOT ALLOWED IN PRODUCTION')
            if getattr(self, '_otel_initialized', False):
                self.otel_error_handler("Device reset not allowed in production environment")
            self.exit_error("DEVICE RESET NOT ALLOWED IN PRODUCTION")


class Terminate(Common):
    def process(self):
        resource_dependents = self.get_dependencies(self.resource["id"])
        for resource_dependent in resource_dependents:
            self.logger.info(f'existing resource_dependent id found: {resource_dependent["id"]}')
            self.bpo.resources.patch(
                resource_dependent["id"],
                {"desiredOrchState": "terminated", "orchState": "terminated"},
            )
