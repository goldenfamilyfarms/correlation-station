""" -*- coding: utf-8 -*-

SLM Configurator Plans

Versions:
   0.1 May 11, 2022
       Initial check in of SLM Configurator plans

"""
import sys

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.circuitDetailsHandler import CircuitDetailsHandler


class Activate(CommonPlan):
    def process(self):
        self.properties = self.resource["properties"]
        self.circuit_id = self.properties["circuit_id"]
        self.circuit_details_id = self.properties.get("circuit_details_id")
        self.onboarding_complete = self.properties.get("onboarding_complete", False)
        self.origin_cid = self.properties.get("origin_cid", "")
        self.origin_circuit_details_id = self.properties.get("origin_cd_id", "")

        # if we already have circuit details resource id, get circuit details from it
        if self.circuit_details_id:
            self.circuit_details = self.bpo.resources.get(self.circuit_details_id)
        # if we don't already have circuit details resource id or if we need to onboard additional devices into circuit details
        # we need to generate our own circuit details
        elif not self.circuit_details_id or not self.onboarding_complete:
            handler = CircuitDetailsHandler(plan=self, circuit_id=self.circuit_id, operation="SLM")
            handler.device_onboarding_process()
            self.circuit_details = handler.circuit_details
            self.onboarding_complete = True

        self.cutthrough = RaCutThrough()

        slm_config_variables_payload = {
            "label": "{}.slmConfigVariables".format(self.circuit_id),
            "productId": self.get_built_in_product(self.BUILT_IN_SLM_CONFIG_VARIABLES_TYPE)["id"],
            "properties": {
                "use_alternate_circuit_details_server": self.properties.get(
                    "use_alternate_circuit_details_server", False
                ),
                "circuit_id": self.circuit_id,
                "circuit_details_id": self.circuit_details_id,
                "origin_cid": self.origin_cid,
                "origin_cd_id": self.origin_circuit_details_id,
                "onboarding_complete": self.onboarding_complete,
                "core_only": self.properties.get("core_only", False),
            },
        }
        slm_config_variables_resource_id = self.bpo.resources.create(
            self.resource_id, data=slm_config_variables_payload
        ).resource_id
        slm_config_variables = self.get_resource(slm_config_variables_resource_id)
        self.logger.info("SLM Config Variables: {}".format(slm_config_variables))
        mdso_configured_slm = {}
        for slm_role in slm_config_variables["properties"]["slm_configuration_variables"]:
            already_configured = False
            if slm_config_variables["properties"]["slm_configuration_variables"][slm_role].get(
                "existing_configuration_details"
            ):
                already_configured = True
                self.logger.info(
                    "SLM configuration already applied to device: {}".format(
                        slm_config_variables["properties"]["slm_configuration_variables"][slm_role]
                    )
                )
            if not already_configured:
                try:
                    self.configure_slm_device(slm_config_variables, slm_role)
                    # TODO adva ra will respond with 201 + all the errors and we'll say we did a good job because no exception raised
                except Exception as error:
                    self.logger.info("Error attempting to configure device: {}".format(error))
                    raise Exception(error)
            mdso_configured_slm[slm_role] = False if already_configured else True
        self.bpo.resources.patch_observed(
            self.resource["id"], data={"properties": {"mdso_configured_slm": mdso_configured_slm}}
        )

    def configure_slm_device(self, slm_config_variables, slm_role):
        network_function = self.bpo.resources.get(
            slm_config_variables["properties"]["slm_configuration_variables"][slm_role]["network_function_resource_id"]
        )
        command_file = (
            "create-slm.json"
            if self.get_network_function_connection_type(network_function) == "cli"
            else "netconf-create-slm.json"
        )
        self.logger.info("Sending SLM configuration to network function {}".format(network_function))
        RaCutThrough().execute_ra_command_file(
            network_function["providerResourceId"],
            command_file,
            slm_config_variables["properties"]["slm_configuration_variables"][slm_role],
        )


class Terminate(CommonPlan):
    def process(self):
        pass
