import sys
from contextlib import nullcontext
sys.path.append('model-definitions')
import logging
from scripts.common_plan import CommonPlan
# Setup logger for otel import tracking
_import_logger = logging.getLogger(__name__)
_import_logger.info("managedSecurityServices.py: Attempting to import OTelMixin from scripts.otel.otel_mixin")
try:
    from scripts.otel.otel_mixin import OTelMixin
    _import_logger.info("managedSecurityServices.py: Successfully imported OTelMixin")
except ImportError as e:
    _import_logger.error(f"managedSecurityServices.py: Failed to import OTelMixin - Error: {e}")
    raise


class Activate(CommonPlan, OTelMixin):
    def process(self):
        # Initialize OTel instrumentation
        self.__init_otel__()
        
        # Create root span for managed security services
        with self.create_root_span(operation_name="managed_security_services"):
            customer_res = self.bpo.resources.get(self.resource["properties"]["customerResourceId"])
            
            if getattr(self, '_otel_initialized', False):
                self.set_correlation_baggage_from_instance()
                self.record_span_event_from_instance("security_services.activation.started", {
                    "customer_resource_id": customer_res.get("id", "unknown")
                })
            
            fmg_payload, faz_payload, fpc_payload = self.create_payloads(customer_res)
            # create fortimanager, fortianalyzer, and fortiportal child resources
            with self.timed_operation("security_services.create_resources", {}) if getattr(self, '_otel_initialized', False) else nullcontext():
                self.bpo.resources.create(self.resource["id"], fmg_payload)
                self.bpo.resources.create(self.resource["id"], faz_payload)
                self.bpo.resources.create(self.resource["id"], fpc_payload)
                if getattr(self, '_otel_initialized', False):
                    self.record_span_event_from_instance("security_services.resources_created", {
                        "fmg": fmg_payload.get("label", "unknown"),
                        "faz": faz_payload.get("label", "unknown"),
                        "fpc": fpc_payload.get("label", "unknown")
                    })

    def create_payloads(self, customer_res):
        # get properties from customer resource and assign to local variables
        datastore = self.bpo.market.get(
            "/resources?resourceTypeId={}&p=label:{}&obfuscate=false&limit=1000".format(
                "charter.resourceTypes.datastore", "Datastore"
            )
        )
        common_properties = customer_res["properties"]["customerProps"]["common_properties"]
        customer = customer_res["properties"]["customerProps"]["customer"]
        fmg_properties = customer_res["properties"]["customerProps"]["fmg_properties"]
        datestore_faz_properties = {
            "dataPolicyKeepLogsForArchive": datastore["items"][0]["properties"]["dataPolicyKeepLogsForArchive"],
            "dataPolicyKeepLogsForAnalytics": datastore["items"][0]["properties"]["dataPolicyKeepLogsForAnalytics"],
            "diskUtilizationAllocated": datastore["items"][0]["properties"]["diskUtilizationAllocated"],
            "diskUtilizationAnalyticsArchived": datastore["items"][0]["properties"]["diskUtilizationAnalyticsArchived"],
            "diskUtilizationAnalyticsArchivedUnit": datastore["items"][0]["properties"][
                "diskUtilizationAnalyticsArchivedUnit"
            ],
        }
        # combine dicts together to create new properties dict for fmg and faz properties
        faz_properties = common_properties
        faz_properties.update({"customer": customer})

        updated_fmg_properties = {**faz_properties, **fmg_properties}

        fmg_payload = {
            "label": customer_res["label"].split(".")[0] + ".fortimanager",
            "productId": self.get_built_in_product(self.BUILT_IN_MANAGED_SERVICES_FORTIMANAGER_TYPE)["id"],
            "properties": updated_fmg_properties,
        }
        updated_faz_properties = {**faz_properties, **datestore_faz_properties}
        faz_payload = {
            "label": customer_res["label"].split(".")[0] + ".fortianalyzer",
            "productId": self.get_built_in_product(self.BUILT_IN_MANAGED_SERVICES_FORTIANALYZER_TYPE)["id"],
            "properties": updated_faz_properties,
        }

        fpc_payload = {
            "label": customer_res["label"].split(".")[0] + ".fortiportal",
            "productId": self.get_built_in_product(self.BUILT_IN_MANAGED_SERVICES_FORTIPORTAL_TYPE)["id"],
            "properties": {
                "customer": customer,
                "siteName": fmg_properties["site_clli"],
                "version": common_properties["version"],
                "tid": common_properties["tid"],
            },
        }

        return fmg_payload, faz_payload, fpc_payload


class Terminate(CommonPlan):
    def process(self):
        pass
