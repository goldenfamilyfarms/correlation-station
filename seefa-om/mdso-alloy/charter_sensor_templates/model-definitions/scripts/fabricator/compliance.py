from scripts.fabricator.common import FactoryBase
from scripts.otel.otel_mixin import OTelMixin
import time
import logging

# Setup logger for otel import tracking
_import_logger = logging.getLogger(__name__)
_import_logger.info("compliance.py: Module loaded with OTelMixin")


class Activate(FactoryBase, OTelMixin):
    """Compliance factory for service mapper activation operations."""

    def _get_child_resource_type(self) -> str:
        """Return the resource type for child resources."""
        return ""

    def process(self):
        """Process compliance activation for service mapper."""
        # Initialize OTel instrumentation
        self.__init_otel__()

        # Create root span for compliance operation
        with self.create_root_span(operation_name="compliance_activate"):
            self.operation = "SERVICE_MAPPER"
            self.product = self.BUILT_IN_SERVICE_MAPPER_TYPE
            self.circuit_id = self.properties["circuit_id"]
            self.remediation_flag = self.properties["remediation_flag"]
            self.alternate_cd = self.properties.get("use_alternate_circuit_details_server", False)
            self.device_properties = self.properties.get("device_properties", {})
            self.order_type = self.properties.get("order_type", "")
            self.slm_eligible = self.properties.get("slm_eligible", False)

            # Set correlation baggage
            self.set_correlation_baggage_from_instance()

            # Record span event for operation start
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance(
                    "compliance.started",
                    {
                        "circuit_id": self.circuit_id,
                        "remediation_flag": self.remediation_flag,
                        "order_type": self.order_type,
                        "slm_eligible": self.slm_eligible
                    }
                )

            # MAIN PROCESS (SERVICE MAPPER)
            # Step 1: Get circuit details
            with self.timed_operation("compliance.get_circuit_details") if getattr(self, '_otel_initialized', False) else self._nullcontext():
                self._set_circuit_details()

            # Step 2: Iterator Over all in CD
            with self.timed_operation("compliance.create_mappers", {"leg_count": len(self.leg_details_ids)}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                for circuit_details_id in self.leg_details_ids:
                    cd = self.bpo.resources.get(circuit_details_id)
                    label = cd["label"].strip(".cd")
                    payload = {
                        "remediation_flag": self.remediation_flag,
                        "use_alternate_circuit_details_server": self.alternate_cd,
                        "device_properties": self.device_properties,
                        "circuit_id": self.circuit_id,
                        "circuit_details_id": circuit_details_id,
                        "order_type": self.order_type,
                        "slm_eligible": self.slm_eligible,
                    }
                    if "SECONDARY" in label:
                        time.sleep(60)  # allow time for any duplicate devices in PRIMARY to onboard

                    # Create mapper with instrumentation
                    if getattr(self, '_otel_initialized', False):
                        with self.timed_operation("compliance.create_mapper", {"label": label, "is_secondary": "SECONDARY" in label}):
                            self.record_span_event_from_instance("compliance.mapper.creation.started", {"label": label})
                            mapper = self._create_resource(label, payload)
                            self.child_resources.update({label: mapper["id"]})
                            self.record_span_event_from_instance("compliance.mapper.creation.completed", {"label": label, "mapper_id": mapper["id"]})
                    else:
                        mapper = self._create_resource(label, payload)
                        self.child_resources.update({label: mapper["id"]})

            # we created all children at once, now let's wait for them to complete
            try:
                if getattr(self, '_otel_initialized', False):
                    with self.timed_operation("compliance.await_active", {"resource_count": len(self.child_resources)}):
                        self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=600)
                        self.record_span_event_from_instance("compliance.all_mappers_active", {"resource_ids": list(self.child_resources.values())})
                else:
                    self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=600)
            except RuntimeError as err:
                self.logger.warning("Unable to activate Service Mapper resources")
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler("Service mapper activation failed", exception=err)
                raise

            # Step 3: Harvest any child resource data the parent will need
            with self.timed_operation("compliance.get_child_compliance_issues") if getattr(self, '_otel_initialized', False) else self._nullcontext():
                service_differences, slm_issues = self._get_child_compliance_issues()

            # Step 4: Patch the resource with any data from the children required at parent level
            if service_differences:
                for leg in service_differences:
                    self._patch_property("service_differences", service_differences[leg], leg)
            if slm_issues:
                for leg in slm_issues:
                    self._patch_property("slm_traffic_passing", slm_issues[leg])
                    break

            # Record completion event
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance(
                    "compliance.completed",
                    {
                        "circuit_id": self.circuit_id,
                        "child_count": len(self.child_resources),
                        "has_service_differences": bool(service_differences),
                        "has_slm_issues": bool(slm_issues)
                    }
                )

    def _nullcontext(self):
        """Return a nullcontext for when OTel is not initialized."""
        from contextlib import nullcontext
        return nullcontext()

    def _get_child_compliance_issues(self):
        # service differences and slm traffic not passing are compliance issues that need to be recorded
        service_differences = {}
        slm_issues = {}
        for child in self.child_resources:
            resource = self.bpo.resources.get(self.child_resources[child])
            differences = resource["properties"].get("service_differences", {})
            slm_passing = resource["properties"].get("slm_traffic_passing", True)
            if differences:
                service_differences.update({child: differences})
            if slm_passing is False:
                slm_issues.update({child: False})
        return service_differences, slm_issues

    def _patch_property(self, property_name, new_value, label=""):
        if isinstance(new_value, bool):
            self.bpo.resources.patch_observed(
                self.resource_id, data={"properties": {property_name: new_value}}
            )
        else:
            if self.resource["properties"].get(property_name):
                value = self.resource["properties"][property_name]
                value.update({label: new_value})
            else:
                value = {label: new_value}
            self.bpo.resources.patch_observed(
                self.resource_id, data={"properties": {property_name: value}}
            )


class Terminate(FactoryBase):
    def process(self):
        pass
