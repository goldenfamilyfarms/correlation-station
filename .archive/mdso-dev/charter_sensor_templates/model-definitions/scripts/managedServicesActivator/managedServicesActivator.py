import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough


class Activate(CommonPlan, CliCutthrough):
    """This is the activation plan for the MSA Activator
    Select Service and create child resource
    Managed Service Activator Complete
    """

    def process(self):
        props = self.resource["properties"]
        label = self.resource["label"]
        service_type = props.get("service_type", "MRS")
        self.resource_properties = props.get("resource_properties")
        if not self.resource_properties:
            self.resource_properties = {
                "ipAddress": props.get("ipAddress"),
                "configuration": props.get("configuration"),
                "vendor": props.get("vendor").upper(),
                "model": props.get("model"),
                "fqdn": props.get("fqdn"),
                "operationType": props.get("operationType"),
                "ignore_errors": props.get("ignore_errors"),
                "firmwareVersion": props.get("firmwareVersion", ""),
            }

        #  Service selector
        msg = "Building {} Resource".format(service_type)
        self.status_messages(msg, parent="msa_activation")
        try:
            if service_type == "MRS":
                self.invoke_activator(
                    self.get_built_in_product(self.BUILT_IN_MANAGED_ROUTER_SERVICE_ACTIVATOR_TYPE)["id"],
                    label + ".managed_router_services",
                )
            elif service_type == "MSS":
                self.invoke_activator(
                    self.get_built_in_product(self.BUILT_IN_MANAGED_SECURITY_SERVICES_TYPE)["id"],
                    label + ".managed_security_services",
                )
            elif service_type == "MNE":
                if self.resource_properties["circuitId"]:
                    self.invoke_activator(
                        self.get_built_in_product(self.BUILT_IN_MANAGED_NETWORK_EDGE_TYPE)["id"], label
                    )
        except Exception as err:
            err_msg = "Failed Step {}: {}".format(msg, err)
            self.logger.error(err)
            self.status_messages(err_msg, error=True, parent="msa_activation")
            self.exit_error(err_msg)

        # Managed Service Activator Complete
        msg = "Managed Services Activator Completed"
        self.status_messages(msg, parent="msa_activation")

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
