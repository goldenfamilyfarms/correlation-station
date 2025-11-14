"""-*- coding: utf-8 -*-

NetworkService Plans

Versions:
   0.1 Dec 06, 2017
       Initial check in of NetworkService plans

"""

import time
import sys

sys.path.append("model-definitions")
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough
from scripts.common_plan import CommonPlan
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Terminate(CommonPlan):
    """This is the class that is called for the termination of a NetworkService resource."""

    """
        Disable the enter_exit_log behavior to prevent creating a new instance of TraceLog that would
        not be terminated automatically after the NetworkService terminates. Unless this is disabled,
        TraceLog resources will accumulate for each NetworkService that we terminate.
    """
    EnableEnterExitLog = False
    all_dependencies_ids = []

    def process(self):
        self.soft_terminate_process()

        resource_types_to_delete_last = [self.BUILT_IN_CIRCUIT_DETAILS_TYPE]

        # WE WILL RUN THE SERVICE DEPENDENCY MDDIFIER LAST
        try:
            dependencies = self.bpo.resources.get_dependencies(self.resource["id"])
            first_deps = []
            last_deps = []
            circuit_details = None
            is_service_built = False
            for dep in dependencies:
                if dep["resourceTypeId"] == self.BUILT_IN_CIRCUIT_DETAILS_TYPE:
                    circuit_details = dep

                if dep["resourceTypeId"] == self.BUILT_IN_MEF_PRODUCTION_SERVICE_TYPE and dep["orchState"] == "active":
                    is_service_built = True

                if dep["resourceTypeId"] in resource_types_to_delete_last:
                    last_deps.append(dep)
                else:
                    first_deps.append(dep)

            self.logger.debug("Deleting first set of resources. " + str(len(first_deps)))
            self.bpo.resources.delete_dependencies(
                self.resource["id"], None, first_deps, force_delete_relationship=True
            )
            # WAIT FOR CLEANUP
            if is_service_built is True:
                time.sleep(15)

            # MODIFY PORTS
            self.logger.debug("Circuit details found: " + str(circuit_details))
            if circuit_details is not None:
                self.logger.debug("Updating dependent resources.")
                product = self.get_built_in_product(self.BUILT_IN_SERVICE_DEPENDENCY_MODIFIER_TYPE)
                service_modifier = {
                    "productId": product["id"],
                    "label": self.resource["label"] + ".term.service_mod",
                    "properties": {
                        "action": "TERMINATE",
                        "circuit_details_id": circuit_details["id"],
                        "circuit_id": circuit_details["properties"]["circuit_id"],
                    },
                }
                self.bpo.resources.create(self.resource["id"], service_modifier)

            self.logger.debug("Deleting second set of resources. " + str(len(last_deps)))
            self.bpo.resources.delete_dependencies(self.resource["id"], None, last_deps, force_delete_relationship=True)
        except Exception as ex:
            self.logger.exception(ex)
            raise Exception(ex)


class Update(CommonPlan):
    """This is the class that is called for the update of a NetworkService.
    This is not currently supported.
    """

    def process(self):
        self.logger.info("DONE!")


class ActivateSite(CommonPlan, CliCutthrough):
    """This is the class called for the custom operation for a NetworkService
    when activating a site (CPE).
    """

    def process(self):
        self.network_ser_res = self.mget("/resources/%s" % self.params["resourceId"]).json()
        network_props = self.network_ser_res["properties"]
        self.circuit_id = network_props["circuit_id"]
        operation = self.bpo.resources.get_operation(self.params["resourceId"], self.params["operationId"])
        if not operation:
            self.exit_error("Unable to find operation for circuit_id: " + self.circuit_id)

        site = operation["inputs"]["site"]
        port = operation["inputs"].get("port")
        try:
            cpe_ip = operation["inputs"].get("ip")
        except NameError:
            pass

        # Create an instance of a cpeActivator.
        cpe_activator_product = self.get_built_in_product(self.BUILT_IN_CPE_ACTIVATOR_TYPE)
        activator_details = {
            "label": site + ".cpe_activator",
            "productId": cpe_activator_product["id"],
            "properties": {
                "circuit_id": self.circuit_id,
                "network_service_id": self.network_ser_res["id"],
                "site": site,
                "port": port,
            },
        }
        try:
            if cpe_ip:
                activator_details["properties"]["ip"] = cpe_ip
        except NameError:
            pass
        try:
            self.logger.info("Activating site %s, port %s, IP %s ..." % (site, port, cpe_ip))
            self.bpo.resources.create(self.network_ser_res["id"], activator_details, wait_active=True, wait_time=600)
        except Exception as ex:
            self.exit_error(
                "Exception %s raised when attempting to create cpeActivator for site %s, port %s, IP %s"
                % (str(ex), site, port, cpe_ip)
            )


class Suspend(CommonPlan):
    """This is the class called for the custom operation for a NetworkService
    when suspending a service.
    """

    def process(self):
        self.logger.info("DONE!")


class Resume(CommonPlan):
    """This is the class called for the custom operation for a NetworkService
    when resuming a service (from suspend).
    """

    def process(self):
        self.logger.info("DONE!")


class SoftTerminate(CompleteAndTerminatePlan):
    """This is the class called for the custom operation for a NetworkService
    when performing a soft delete of the NetworkService.  Which is a terminate
    without affecting any of the RA resources
    """

    all_dependencies_ids = []

    def process(self):
        self.soft_terminate_process()
