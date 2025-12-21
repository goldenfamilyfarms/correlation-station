import sys
sys.path.append('model-definitions')
import logging
from scripts.common_plan import CommonPlan
# Setup logger for otel import tracking
_import_logger = logging.getLogger(__name__)
_import_logger.info("multilegcircuit.py: Attempting to import OTelMixin from scripts.otel.otel_mixin")
try:
    from scripts.otel.otel_mixin import OTelMixin
    _import_logger.info("multilegcircuit.py: Successfully imported OTelMixin")
except ImportError as e:
    _import_logger.error(f"multilegcircuit.py: Failed to import OTelMixin - Error: {e}")
    raise
import scripts.networkservice.circuitdetailscollector
import scripts.scriptplan


class Activate(CommonPlan, OTelMixin):

    def process(self):
        # Initialize OTel instrumentation
        self.__init_otel__()

        # Create root span for multileg circuit
        with self.create_root_span(operation_name="multileg_circuit"):
            # Set correlation baggage
            self.set_correlation_baggage_from_instance()

            self.circuit_id = self.properties['circuit_id']

            # Create tracelog on multi-leg resource
            self.enter_exit_log(message="Multi-Leg Circuit")

            self.use_alternate_url = bool(self.properties.get('use_alternate_circuit_details_server', False))

            # Get circuit details with timing
            with self.timed_operation("multileg.get_circuit_details") if getattr(self, '_otel_initialized', False) else self._nullcontext():
                raw_details = scripts.networkservice.circuitdetailscollector.Activate.get_circuit_details_server_response(self, True)

            self.timeout_per_leg = self.properties['timeout_per_leg']

            self.legs_list = []
            for k in raw_details:
                self.legs_list.append(k)

            self.logger.info("==== Legs List: {}".format(self.legs_list))

            # Add span attributes for multileg details
            if getattr(self, '_otel_initialized', False):
                from opentelemetry import trace
                span = trace.get_current_span()
                if span and span.is_recording():
                    span.set_attribute("multileg.circuit_id", self.circuit_id)
                    span.set_attribute("multileg.leg_count", len(self.legs_list))
                    span.set_attribute("multileg.timeout_per_leg", self.timeout_per_leg)
                self.record_span_event_from_instance("multileg.legs_identified", {
                    "leg_count": len(self.legs_list),
                    "legs": self.legs_list
                })

            network_service_prod_id = self.get_products_by_type_and_domain("charter.resourceTypes.NetworkService", "built-in")[0]['id']

            for leg_name in self.legs_list:
                try:
                    cid = raw_details[leg_name]['serviceName'] + "-" + leg_name
                    self.logger.info("The CID I will send is: {}".format(cid))
                    props = {
                        "circuit_id": cid,
                        "use_alternate_circuit_details_server": self.resource['properties']['use_alternate_circuit_details_server']}
                    net_serv_body = {
                        "productId": network_service_prod_id,
                        "label": cid,
                        "properties": props}

                    # Create network service for each leg with timing
                    with self.timed_operation("multileg.create_leg", {"leg_name": leg_name, "cid": cid}) if getattr(self, '_otel_initialized', False) else self._nullcontext():
                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("multileg.leg.creation.started", {"leg_name": leg_name, "cid": cid})

                        net_serv_response = self.create_active_resource(title=cid, parent_res_id=self.resource_id, body=net_serv_body, waittime=self.timeout_per_leg)
                        self.logger.info("=&=$=%=&=$=%=&=$=% NET_SERV_RESPONSE %=$=&=%=$=&=%=$=&=%=$=&=")
                        self.logger.info(net_serv_response)

                        if getattr(self, '_otel_initialized', False):
                            self.record_span_event_from_instance("multileg.leg.creation.completed", {"leg_name": leg_name, "cid": cid})

                except Exception as e:
                    msg = "Failure in the Multileg process"
                    if getattr(self, '_otel_initialized', False):
                        self.otel_error_handler(f"Failed to create leg {leg_name}: {msg}", exception=e)
                    self.categorized_error = self.ERROR_CATEGORY['MDSO'].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                    self.exit_error("Failed during the multileg process : %s" % str(e))

            # Record completion
            if getattr(self, '_otel_initialized', False):
                self.record_span_event_from_instance("multileg.circuit.completed", {
                    "circuit_id": self.circuit_id,
                    "total_legs": len(self.legs_list)
                })

    def _nullcontext(self):
        """Return a nullcontext for when OTel is not initialized."""
        from contextlib import nullcontext
        return nullcontext()


class Terminate(CommonPlan):
    """This is the class that is called for the termination of a Multileg Circuit resource.
    """
    """
        Disable the enter_exit_log behavior to prevent creating a new instance of TraceLog that would
        not be terminated automatically after the Multileg Circuit terminates. Unless this is disabled,
        TraceLog resources will accumulate for each Multileg Circuit that we terminate.
    """
    EnableEnterExitLog = False
    all_dependencies_ids = []

    def process(self):

        self.soft_terminate_process()

        try:
            dependencies = self.bpo.resources.get_dependencies(self.resource['id'])
            # is_service_built = False

            self.logger.debug("Deleting resources. " + str(len(dependencies)))
            self.bpo.resources.delete_dependencies(self.resource['id'],
                                                   None,
                                                   dependencies,
                                                   force_delete_relationship=True)

        except Exception as ex:
            self.logger.exception(ex)
            raise Exception(ex)
        pass
