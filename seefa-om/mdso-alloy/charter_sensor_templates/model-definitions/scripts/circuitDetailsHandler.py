""" -*- coding: utf-8 -*-

Circuit Details Handler Plans

Versions:
   0.1 May 18, 2022
       Initial check in of Circuit Details Handler plans

"""


class CircuitDetailsHandler:
    """
    Helper class to handle creating circuit details resource and subsequent onboarding processes
    """

    def __init__(self, plan: object, circuit_id: str, operation: str, circuit_details_id: str = ""):
        self.plan = plan  # plansdk handed over on instantiation by passing "self" as plan
        self.circuit_id = circuit_id
        self.operation = operation
        # generate circuit details resource or get circuit details resource if id provided
        if circuit_details_id:
            self.circuit_details_id = circuit_details_id
            self.circuit_details = self.bpo.resources.get(circuit_details_id)
            self.leg_details_ids = []  # allow caller to update with leg details ids prop from its own circuit details collector
        else:
            circuit_details_collector = self.create_circuit_details_collector_resource()
            self.circuit_details_id = circuit_details_collector["properties"]["circuit_details_id"]
            self.circuit_details = self.bpo.resources.get(self.circuit_details_id)
            self.leg_details_ids = circuit_details_collector["properties"]["leg_details_ids"]

    def create_circuit_details_collector_resource(self):
        self.logger.info("Creating circuit details collector resource")
        payload = self._create_payload_base(self.BUILT_IN_CIRCUIT_DATA_COLLECTOR_TYPE)
        try:
            # Use parent plan's OTel if available
            if getattr(self.plan, '_otel_initialized', False):
                with self.plan.timed_operation("circuit_details.create_collector", {"circuit_id": self.circuit_id, "operation": self.operation}):
                    resource = self.bpo.resources.create(self.resource_id, payload).resource
                    self.plan.record_span_event_from_instance("circuit_details.collector.created", {"circuit_id": self.circuit_id})
            else:
                resource = self.bpo.resources.create(self.resource_id, payload).resource
        except RuntimeError as err:
            self.logger.warning("Unable to create Circuit Details Collector resource")
            error = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Circuit Details Collector"
            )
            if getattr(self.plan, '_otel_initialized', False):
                self.plan.otel_error_handler("Failed to create circuit details collector", exception=err)
            self.exit_error(error)
        self.logger.info(f"Circuit details resource: {resource}")
        return resource

    def create_service_device_validator_resource(self, circuit_details_id=None):
        if not circuit_details_id:
            circuit_details_id = self.circuit_details_id
        payload = self._create_payload_base(self.BUILT_IN_SERVICE_DEVICE_VALIDATORY_TYPE)
        payload["properties"]["circuit_details_id"] = circuit_details_id
        try:
            # Use parent plan's OTel if available
            if getattr(self.plan, '_otel_initialized', False):
                with self.plan.timed_operation("circuit_details.create_validator", {"circuit_id": self.circuit_id}):
                    resource = self.bpo.resources.create(self.resource_id, payload).resource
                    self.plan.record_span_event_from_instance("circuit_details.validator.created", {"circuit_id": self.circuit_id})
            else:
                resource = self.bpo.resources.create(self.resource_id, payload).resource
        except RuntimeError as err:
            self.logger.warning("Unable to create Service Device Validator resource")
            error = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Service Device Validator"
            )
            if getattr(self.plan, '_otel_initialized', False):
                self.plan.otel_error_handler("Failed to create service device validator", exception=err)
            self.exit_error(error)
        self.logger.info(f"Circuit details resource: {resource}")
        return resource

    def _create_payload_base(self, product):
        return {
            "label": f"{self.circuit_id}.CircuitDetailsHandler.{product.split('.')[-1]}",
            "productId": self.get_built_in_product(product)["id"],
            "properties": {
                "circuit_id": self.circuit_id,
                "use_alternate_circuit_details_server": self.properties.get("use_alternate_circuit_details_server", False),
                "operation": self.operation,
            },
        }

    def device_onboarding_process(self, circuit_details_id=None, onboarding_context="ALL"):
        # Use parent plan's OTel if available
        if getattr(self.plan, '_otel_initialized', False):
            with self.plan.timed_operation("circuit_details.onboarding_process", {"circuit_id": self.circuit_id, "context": onboarding_context}):
                # update circuit details with devices to onboard, call service device onboarder
                self.create_service_device_validator_resource()
                self.onboard_devices(circuit_details_id, onboarding_context)
                # grab updated circuit details
                self.circuit_details = self.bpo.resources.get(self.circuit_details_id)
                self.plan.record_span_event_from_instance("circuit_details.onboarding.completed", {"circuit_id": self.circuit_id})
        else:
            # update circuit details with devices to onboard, call service device onboarder
            self.create_service_device_validator_resource()
            self.onboard_devices(circuit_details_id, onboarding_context)
            # grab updated circuit details
            self.circuit_details = self.bpo.resources.get(self.circuit_details_id)

    def onboard_devices(self, circuit_details_id=None, onboarding_context="ALL"):
        if not circuit_details_id:
            circuit_details_id = self.circuit_details_id
        self.logger.info("Onboarding devices!")
        try:
            # Use parent plan's OTel if available
            if getattr(self.plan, '_otel_initialized', False):
                with self.plan.timed_operation("circuit_details.onboard_devices", {"circuit_id": self.circuit_id, "context": onboarding_context}):
                    onboarder = self.bpo.resources.create(
                        self.resource_id,
                        {
                            "label": f"{self.circuit_id}.ServiceDeviceOnboarder",
                            "productId": self.get_built_in_product(self.BUILT_IN_SERVICE_DEVICE_ONBOARDER_TYPE)["id"],
                            "properties": {
                                "circuit_details_id": circuit_details_id,
                                "circuit_id": self.circuit_id,
                                "context": onboarding_context,
                                "operation": self.operation,
                            },
                        },
                    )
                    self.plan.record_span_event_from_instance("circuit_details.devices_onboarded", {"circuit_id": self.circuit_id, "context": onboarding_context})
            else:
                onboarder = self.bpo.resources.create(
                    self.resource_id,
                    {
                        "label": f"{self.circuit_id}.ServiceDeviceOnboarder",
                        "productId": self.get_built_in_product(self.BUILT_IN_SERVICE_DEVICE_ONBOARDER_TYPE)["id"],
                        "properties": {
                            "circuit_details_id": circuit_details_id,
                            "circuit_id": self.circuit_id,
                            "context": onboarding_context,
                            "operation": self.operation,
                        },
                    },
                )
        except RuntimeError as err:
            self.logger.warning("Unable to create Service Device Onboarder resource")
            error = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Service Device Onboarder"
            )
            if getattr(self.plan, '_otel_initialized', False):
                self.plan.otel_error_handler("Failed to onboard devices", exception=err)
            self.exit_error(error)
        self.logger.info(f"Onboarding circuit details resource: {onboarder}")
        return self.bpo.resources.get(onboarder.resource["properties"]["circuit_details_id"])

    def set_leg_details_ids(self, leg_details_ids: list):
        self.leg_details_ids = leg_details_ids

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))
