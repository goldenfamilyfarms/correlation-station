""" -*- coding: utf-8 -*-

UpdateObservedProperty Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of UpdateObservedProperty plans

"""
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    RESOURCE_TYPES_TO_DISCARD = [
        CommonPlan.BUILT_IN_DEVICE_STATE_CHECK_TYPE,
        CommonPlan.BUILT_IN_DEVICE_ONBOARDER_TYPE,
        CommonPlan.BUILT_IN_CIRCUIT_DATA_COLLECTOR_TYPE,
        CommonPlan.BUILT_IN_SERVICE_DEVICE_VALIDATORY_TYPE,
        CommonPlan.BUILT_IN_SERVICE_FRE_ONBOARDER_TYPE,
        CommonPlan.BUILT_IN_UPDATE_OBSERVED_PROP_TYPE,
    ]

    def process(self):
        network_service_id = self.properties["resource_id"]
        """ this is get the resource id of the network service """
        dependencies = self.bpo.resources.get_dependencies(network_service_id)
        for resource_type in self.RESOURCE_TYPES_TO_DISCARD:
            self.logger.info("Deleting resources with type: " + resource_type)

            try:
                self.bpo.resources.delete_dependencies(
                    network_service_id, resource_type, dependencies, force_delete_relationship=True
                )
            except Exception:
                self.logger.info(
                    "Failed to delete dependencies for network service {} \
                    and resource type {}".format(
                        network_service_id, resource_type
                    )
                )


class Terminate(CommonPlan):
    """this is the class that is called for the termination of the NetworkServiceCleaner"""

    def process(self):
        pass
