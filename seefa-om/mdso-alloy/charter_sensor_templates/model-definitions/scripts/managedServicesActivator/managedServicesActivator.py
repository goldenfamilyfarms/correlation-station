import sys
import time
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough
from scripts.otel_instrumentation.otel_mixin import OTelMixin


class Activate(CommonPlan, CliCutthrough, OTelMixin):
    """This is the activation plan for the MSA Activator
    Select Service and create child resource
    Managed Service Activator Complete
    """

    def process(self):
        # Initialize OTel instrumentation
        self.__init_otel__()
        
        # Create root span for the entire process
        with self.create_root_span():
            start_time = time.time()
            
            # Set correlation baggage
            self.set_correlation_baggage_from_instance()
            props = self.resource["properties"]
            label = self.resource["label"]
            service_type = props.get("service_type", "MRS")
            self.resource_properties = props.get("resource_properties")
            if not self.resource_properties:
                self.resource_properties = {
                    "ipAddress": props.get("ipAddress"),
                    "configuration": props.get("configuration"),
                    "vendor": props.get("vendor").upper() if props.get("vendor") else None,
                    "model": props.get("model"),
                    "fqdn": props.get("fqdn"),
                    "operationType": props.get("operationType"),
                    "ignore_errors": props.get("ignore_errors"),
                    "firmwareVersion": props.get("firmwareVersion", ""),
                }

            # Record span event for MSA activation start
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance(
                    "msa.activation.started",
                    {
                        "service_type": service_type,
                        "vendor": self.resource_properties.get("vendor"),
                        "fqdn": self.resource_properties.get("fqdn")
                    }
                )
                
                # Add custom attributes based on service type
                span = trace.get_current_span()
                if span and span.is_recording():
                    span.set_attribute("msa.service_type", service_type)
                    if self.resource_properties.get("vendor"):
                        span.set_attribute("msa.vendor", self.resource_properties["vendor"])
                    if self.resource_properties.get("fqdn"):
                        span.set_attribute("msa.fqdn", self.resource_properties["fqdn"])
                    if self.resource_properties.get("ipAddress"):
                        span.set_attribute("msa.ip_address", self.resource_properties["ipAddress"])

            #  Service selector
            msg = "Building {} Resource".format(service_type)
            self.status_messages(msg, parent="msa_activation")
            
            try:
                if service_type == "MRS":
                    # Add granular span for MRS activation
                    with self.timed_operation("msa.mrs.activation", {"vendor": self.resource_properties.get("vendor")}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("msa.mrs.activation.started", {"vendor": self.resource_properties.get("vendor")})
                        self.invoke_activator(
                            self.get_built_in_product(self.BUILT_IN_MANAGED_ROUTER_SERVICE_ACTIVATOR_TYPE)["id"],
                            label + ".managed_router_services",
                        )
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("msa.mrs.activation.completed")
                            if hasattr(self, 'metrics'):
                                self.metrics.record_operation("msa.mrs.activate", {"vendor": self.resource_properties.get("vendor")})

                elif service_type == "MSS":
                    # Add granular span for MSS activation
                    with self.timed_operation("msa.mss.activation", {"vendor": self.resource_properties.get("vendor")}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("msa.mss.activation.started", {"vendor": self.resource_properties.get("vendor")})
                        self.invoke_activator(
                            self.get_built_in_product(self.BUILT_IN_MANAGED_SECURITY_SERVICES_TYPE)["id"],
                            label + ".managed_security_services",
                        )
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("msa.mss.activation.completed")
                            if hasattr(self, 'metrics'):
                                self.metrics.record_operation("msa.mss.activate", {"vendor": self.resource_properties.get("vendor")})

                elif service_type == "MNE":
                    if self.resource_properties.get("circuitId"):
                        # Add granular span for MNE activation
                        with self.timed_operation("msa.mne.activation", {"circuit_id": self.resource_properties.get("circuitId")}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                            if getattr(self, '_otel_initialized', False):
                                self.record_span_event_from_instance("msa.mne.activation.started", {"circuit_id": self.resource_properties.get("circuitId")})
                            self.invoke_activator(
                                self.get_built_in_product(self.BUILT_IN_MANAGED_NETWORK_EDGE_TYPE)["id"], label
                            )
                            if getattr(self, '_otel_initialized', False):
                                self.record_span_event_from_instance("msa.mne.activation.completed")
                                if hasattr(self, 'metrics'):
                                    self.metrics.record_operation("msa.mne.activate")
            except Exception as err:
                err_msg = "Failed Step {}: {}".format(msg, err)
                self.logger.error(err)
                self.status_messages(err_msg, error=True, parent="msa_activation")
                if getattr(self, '_otel_initialized', False):
                    self.otel_error_handler(err_msg, exception=err)
                    if hasattr(self, 'metrics'):
                        self.metrics.record_error("MSA_ACTIVATION_ERROR", {"service_type": service_type})
                self.exit_error(err_msg)

            # Managed Service Activator Complete
            msg = "Managed Services Activator Completed"
            self.status_messages(msg, parent="msa_activation")
            
            # Record completion metrics
            if getattr(self, '_otel_initialized', False):
                duration_ms = (time.time() - start_time) * 1000
                if hasattr(self, 'metrics'):
                    self.metrics.record_operation("msa.activation", {
                        "service_type": service_type,
                        "vendor": self.resource_properties.get("vendor")
                    })
                    self.metrics.record_operation_duration("msa.activation", duration_ms, {
                        "service_type": service_type
                    })
                self.record_span_event_from_instance(
                    "msa.activation.completed",
                    {
                        "service_type": service_type,
                        "duration_ms": duration_ms
                    }
                )

    def _nullcontext(self):
        """Return a nullcontext for when OTel is not initialized."""
        from contextlib import nullcontext
        return nullcontext()

    def invoke_activator(self, product_id, label):
        """Create child resource

        Params
        ------
        product_id : str
            Resource Product ID
        label : str
            Label for child resource

        Raises exception if child resource fails to reach `active` status.
        If MRS resource creation fails, then the raised exception reason will
        be the value of the MRS `mrs_activation_error` property.
        """
        details = {"label": label, "productId": product_id, "properties": self.resource_properties}
        self.logger.debug("Creating " + label + " resource")
        
        # Use network function span for device operations if applicable
        fqdn = self.resource_properties.get("fqdn")
        ip_address = self.resource_properties.get("ipAddress")
        device_id = fqdn or ip_address or label
        
        if getattr(self, '_otel_initialized', False) and (fqdn or ip_address):
            with self.create_network_function_span_context(
                device_id,
                fqdn=fqdn,
                operation="activate"
            ) as nf_span:
                if self.resource_properties.get("vendor"):
                    self.add_network_function_attributes_to_span(
                        span=nf_span,
                        vendor=self.resource_properties["vendor"],
                        ip_address=ip_address
                    )
                
                try:
                    with self.timed_operation("msa.resource.create", {"label": label}):
                        self.bpo.resources.create(self.params["resourceId"], details, wait_time=600)
                    
                    if getattr(self, '_otel_initialized', False):
                        self.record_span_event_from_instance("msa.resource.created", {"label": label})
                except Exception as ex:
                    dep = self.bpo.resources.get_dependencies(self.params["resourceId"])
                    self.logger.debug("dep: {}".format(dep))
                    reason = None
                    if dep and "mrs_activation_error" in dep[0]["properties"]:
                        reason = dep[0]["properties"]["mrs_activation_error"]
                    if not dep:
                        reason = "MDSO platform issue. Please manually provision."
                    self.logger.debug("Invoke Activator method failed****************")
                    self.logger.debug(ex)
                    if getattr(self, '_otel_initialized', False):
                        error_msg = reason or str(ex)
                        self.otel_error_handler(error_msg, exception=ex)
                    raise Exception(reason or ex)
        else:
            # Fallback if OTel not initialized
            try:
                self.bpo.resources.create(self.params["resourceId"], details, wait_time=600)
            except Exception as ex:
                dep = self.bpo.resources.get_dependencies(self.params["resourceId"])
                self.logger.debug("dep: {}".format(dep))
                reason = None
                if dep and "mrs_activation_error" in dep[0]["properties"]:
                    reason = dep[0]["properties"]["mrs_activation_error"]
                if not dep:
                    reason = "MDSO platform issue. Please manually provision."
                self.logger.debug("Invoke Activator method failed****************")
                self.logger.debug(ex)
                raise Exception(reason or ex)


class Terminate(CommonPlan):
    pass
