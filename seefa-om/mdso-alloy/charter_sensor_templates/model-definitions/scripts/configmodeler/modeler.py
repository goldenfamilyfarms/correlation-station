import sys
sys.path.append('model-definitions')
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.common_plan import CommonPlan
from scripts.otel.otel_mixin import OTelMixin
from scripts.configmodeler.adva import Adva
from scripts.configmodeler.juniper import Juniper
from scripts.configmodeler.rad import RAD
from scripts.configmodeler.cisco import Cisco
from scripts.configmodeler.nokia import Nokia


class ConfigModeler:
    MODELERS = {
        "JUNIPER": Juniper,
        "RAD": RAD,
        "ADVA": Adva,
        "CISCO": Cisco,
        "NOKIA": Nokia,
        "ALCATEL": Nokia,
    }

    def __init__(self, plan, vendor, device_tid, location, circuit_id, circuit_details_id):
        self.plan = plan
        self.vendor = vendor
        self.device_tid = device_tid
        self.location = location
        self.circuit_id = circuit_id
        self.circuit_details_id = circuit_details_id
        self.vendor_modeler = self.MODELERS[self.vendor](
            plan=self.plan,
            circuit_id=self.circuit_id,
            device=self.device_tid,
            location=self.location,
            circuit_details_id=self.circuit_details_id,
        )

    def model_config(self, model_type):
        creators = {
            "network_config": self.vendor_modeler.generate_network_model,
            "designed_config": self.vendor_modeler.generate_design_model,
        }
        generate_model = creators[model_type]
        self.logger.debug(f"{generate_model = }")
        return generate_model()

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class Activate(CommonPlan, OTelMixin):
    def process(self):
        # Initialize OTel instrumentation
        self.__init_otel__()

        # Create root span for config modeling
        with self.create_root_span(operation_name="config_modeler"):
            # Set correlation baggage
            self.set_correlation_baggage_from_instance()

            self.circuit_id = self.properties["circuit_id"]
            self.device = self.properties["device"].upper()
            self.vendor = self.properties["vendor"]
            self.location = self.properties["location"]

            # Add vendor and device attributes to span
            if getattr(self, '_otel_initialized', False):
                from opentelemetry import trace
                span = trace.get_current_span()
                if span and span.is_recording():
                    span.set_attribute("config_modeler.vendor", self.vendor.upper())
                    span.set_attribute("config_modeler.device", self.device)
                    span.set_attribute("config_modeler.location", self.location)
                    span.set_attribute("config_modeler.circuit_id", self.circuit_id)

            # Get circuit details with timing
            with self.timed_operation("config_modeler.get_circuit_details") if getattr(self, '_otel_initialized', False) else self._nullcontext():
                self.circuit_details = self._get_circuit_details()
                self.circuit_details_id = self.circuit_details["id"]

            self.config_modeler = ConfigModeler(
                plan=self,
                vendor=self.vendor,
                device_tid=self.device,
                location=self.location,
                circuit_id=self.circuit_id,
                circuit_details_id=self.circuit_details_id,
            )

            # Build config with timing
            config = self._build_resource_data()
            self.bpo.resources.patch_observed(self.resource["id"], data=config)

            # Record completion event
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance("config_modeler.completed", {
                    "vendor": self.vendor,
                    "device": self.device
                })

    def _nullcontext(self):
        """Return a nullcontext for when OTel is not initialized."""
        from contextlib import nullcontext
        return nullcontext()

    def _get_circuit_details(self):
        if self.properties.get("circuit_details_id"):
            return self.bpo.resources.get(self.properties["circuit_details_id"])
        else:
            # generate circuit details, handle any onboarding necessary
            handler = CircuitDetailsHandler(plan=self, circuit_id=self.circuit_id, operation="CONFIG_MODELER")
            handler.device_onboarding_process()
            return handler.circuit_details

    def _build_resource_data(self):
        """
        dynamically build resource data for network config or designed config
        """
        model_type = "network_config" if self.properties.get("network_config") else "designed_config"

        # Time the model generation with model type attribute
        with self.timed_operation("config_modeler.generate_model", {
            "model_type": model_type,
            "vendor": self.vendor,
            "device": self.device
        }) if getattr(self, '_otel_initialized', False) else self._nullcontext():
            model = self.config_modeler.model_config(model_type)

            # Record model generation event
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance("config_modeler.model_generated", {
                    "model_type": model_type,
                    "vendor": self.vendor,
                    "device": self.device
                })

        data = {
            "properties": {
                "modeled_config": {
                    "device": self.properties["device"],
                    model_type: model
                }
            }
        }
        return data


class Terminate(CommonPlan):
    def process(self):
        pass
