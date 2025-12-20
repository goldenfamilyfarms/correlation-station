import time
from scripts.common_plan import CommonPlan
from scripts.fabricator.common import FactoryBase
from scripts.otel.otel_mixin import OTelMixin


class Activate(FactoryBase, OTelMixin):
    """Provisioning factory for activation operations."""

    def process(self):
        """Process provisioning activation for all circuit legs."""
        # Initialize OTel instrumentation
        self.__init_otel__()

        # Create root span for provisioning operation
        with self.create_root_span(operation_name="provisioning_activate"):
            self.circuit_id = self.properties["circuit_id"]
            operation_type = self.properties["operation_type"]  # CREATE | UPDATE | DELETE

            # Set correlation baggage
            self.set_correlation_baggage_from_instance()

            factory = {
                "CREATE": {
                    "process": self._network_service_create,
                    "product": self.BUILT_IN_NETWORK_SERVICE_TYPE,
                    "operation": "NETWORK_SERVICE_ACTIVATION",
                },
                "UPDATE": {
                    "process": self._network_service_update,
                    "product": self.BUILT_IN_NETWORK_SERVICE_UPDATE_TYPE,
                    "operation": "NETWORK_SERVICE_UPDATE",
                },
            }
            self.product = factory[operation_type]["product"]
            self.operation = factory[operation_type]["operation"]
            self.alternate_cd = self.properties.get("use_alternate_circuit_details_server", False)

            # Record span event for operation start
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance(
                    "provisioning.started",
                    {
                        "circuit_id": self.circuit_id,
                        "operation_type": operation_type,
                        "alternate_cd_server": self.alternate_cd
                    }
                )

            self._set_circuit_details()

            # create network service product appropriate for operation type
            factory[operation_type]["process"]()

    def _network_service_create(self) -> None:
        # Iterate over all circuit details comprising circuit and create network services
        with self.timed_operation("provisioning.create_network_services", {"leg_count": len(self.leg_details_ids)}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
            for circuit_details_id in self.leg_details_ids:
                cd = self.bpo.resources.get(circuit_details_id)
                label = cd["label"].strip(".cd")
                payload = {
                    "use_alternate_circuit_details_server": self.alternate_cd,
                    "circuit_id": label,
                    "circuit_details_id": circuit_details_id,
                }
                if "SECONDARY" in label:
                    time.sleep(60)  # prevent race condition on Juniper commits

                # Create network service with timing
                if getattr(self, '_otel_initialized', False):
                    with self.timed_operation("provisioning.create_leg", {"label": label, "is_secondary": "SECONDARY" in label}):
                        self.record_span_event_from_instance("provisioning.leg.creation.started", {"label": label})
                        service = self._create_resource(label=label, properties=payload)
                        self.child_resources.update({label: service["id"]})
                        self.record_span_event_from_instance("provisioning.leg.creation.completed", {"label": label, "service_id": service["id"]})
                else:
                    service = self._create_resource(label=label, properties=payload)
                    self.child_resources.update({label: service["id"]})

            # create concurrently and then wait until active
            try:
                if getattr(self, '_otel_initialized', False):
                    with self.timed_operation("provisioning.await_active", {"resource_count": len(self.child_resources)}):
                        self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=1200)
                        self.record_span_event_from_instance("provisioning.all_legs_active", {"resource_ids": list(self.child_resources.values())})
                else:
                    self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=1200)
            except RuntimeError as err:
                self.logger.warning("Unable to create Network Service Update resource")
                error = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Network Service Update"
                )
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler("Network service creation failed", exception=err)
                self.exit_error(error)

    def _nullcontext(self):
        """Return a nullcontext for when OTel is not initialized."""
        from contextlib import nullcontext
        return nullcontext()

    def _network_service_update(self):
        # Determine update types for span attributes
        update_types = []
        if self.properties.get("ip", False):
            update_types.append("ip")
        if self.properties.get("description", False):
            update_types.append("description")
        if self.properties.get("bandwidth", False):
            update_types.append("bandwidth")
        if self.properties.get("serviceStateenable", False):
            update_types.append("enable")
        if self.properties.get("serviceStatedisable", False):
            update_types.append("disable")

        with self.timed_operation("provisioning.update_network_services", {"leg_count": len(self.leg_details_ids), "update_types": update_types}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
            for circuit_details_id in self.leg_details_ids:
                cd = self.bpo.resources.get(circuit_details_id)
                label = cd["label"].strip(".cd")
                payload = {
                    "ip": self.properties.get("ip", False),
                    "description": self.properties.get("description", False),
                    "bandwidth": self.properties.get("bandwidth", False),
                    "use_alternate_circuit_details_server": self.alternate_cd,
                    "serviceStateenable": self.properties.get("serviceStateenable", False),
                    "circuit_id": label.split("-")[0],
                    "serviceStatedisable": self.properties.get("serviceStatedisable", False),
                    "circuit_details_id": circuit_details_id,
                }
                if "SECONDARY" in label:
                    time.sleep(60)  # prevent race condition on Juniper commits

                # Update network service with timing
                if getattr(self, '_otel_initialized', False):
                    with self.timed_operation("provisioning.update_leg", {"label": label, "is_secondary": "SECONDARY" in label, "update_types": update_types}):
                        self.record_span_event_from_instance("provisioning.leg.update.started", {"label": label})
                        service = self._create_resource(label=label, properties=payload)
                        self.child_resources.update({label: service["id"]})
                        self.record_span_event_from_instance("provisioning.leg.update.completed", {"label": label, "service_id": service["id"]})
                else:
                    service = self._create_resource(label=label, properties=payload)
                    self.child_resources.update({label: service["id"]})

            # create concurrently and then wait until active
            try:
                if getattr(self, '_otel_initialized', False):
                    with self.timed_operation("provisioning.await_active", {"resource_count": len(self.child_resources)}):
                        self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=1200)
                        self.record_span_event_from_instance("provisioning.all_legs_active", {"resource_ids": list(self.child_resources.values())})
                else:
                    self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=1200)
            except RuntimeError as err:
                self.logger.warning("Unable to create Network Service Update resource")
                error = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Network Service Update"
                )
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler("Network service update failed", exception=err)
                self.exit_error(error)

    def _network_service_delete(self):
        pass


class Terminate(CommonPlan):
    pass
