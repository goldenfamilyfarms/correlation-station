import sys

sys.path.append("model-definitions")
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.common_plan import CommonPlan
from scripts.slm.data_models.juniper import Juniper
from scripts.slm.data_models.rad import RAD
from scripts.slm.data_models.adva import Adva


class Modeler(object):
    VENDOR_MODELERS = {
        "JUNIPER": Juniper,
        "ADVA": Adva,
        "RAD": RAD,
    }

    def __init__(
        self,
        plan,
        circuit_id,
        model_type,
        circuit_details_id=None,
        onboarding_complete=False,
        core_only=False,
        slm_details=None,
    ):
        self.plan = plan
        self.circuit_id = circuit_id
        self.model_type = model_type
        self.core_only = core_only
        self._set_circuit_details_properties(circuit_details_id, onboarding_complete)
        if slm_details:
            self.slm_details = slm_details
        else:
            self._set_slm_details_collector()
            self._set_slm_details()

    def _set_circuit_details_properties(self, circuit_details_id, onboarding_complete):
        if circuit_details_id:
            self.circuit_details_id = circuit_details_id
            self.circuit_details = self.bpo.resources.get(self.circuit_details_id)
        else:
            circuit_details = CircuitDetailsHandler(plan=self, circuit_id=self.circuit_id, operation="SLM")
            if not onboarding_complete:
                circuit_details.device_onboarding_process()
            self.circuit_details_id = circuit_details.circuit_details_id
            self.circuit_details = circuit_details.circuit_details

    def _set_slm_details_collector(self):
        slm_details_collectors = {
            "network_config": self.BUILT_IN_SLM_SERVICE_FINDER_TYPE,
            "designed_config": self.BUILT_IN_SLM_CONFIG_VARIABLES_TYPE,
        }
        self.slm_details_collector = slm_details_collectors[self.model_type]
        self.logger.info(f"SLM Details will be created from {self.slm_details_collector}")

    def _set_slm_details(self):
        name = "slm_configuration_variables" if self.model_type == "designed_config" else "slm_configuration"
        payload = {
            "label": f"{self.circuit_id}.slmModeler",
            "productId": self.get_built_in_product(self.slm_details_collector)["id"],
            "properties": {
                "circuit_id": self.circuit_id,
                "circuit_details_id": self.circuit_details_id,
                "onboarding_complete": True,
            },
        }
        if self.core_only:
            payload["core_only"] = self.core_only
        slm_details = self.bpo.resources.create(self.resource_id, payload)
        if slm_details:
            self.slm_details = self.bpo.resources.get(slm_details.resource["id"])["properties"][name]
            self.logger.info(f"SLM Details:\n{self.slm_details}")
        else:
            self.logger.error(f"Unable to get SLM details. Failed to create {self.slm_details_collector} resource.")
            raise Exception

    def model_probe(self):
        probe = self.slm_details["probe"]
        vendor = probe["vendor"]
        return self.VENDOR_MODELERS[vendor](probe=True).model_slm_config(probe, self.model_type)

    def model_reflector(self):
        reflector = self.slm_details["reflector"]
        vendor = reflector["vendor"]
        self.logger.info(f"\nDELETE ME\n{reflector}")
        return self.VENDOR_MODELERS[vendor]().model_slm_config(reflector, self.model_type)

    def model_y1731(self):
        return {"probe": self.model_probe(), "reflector": self.model_reflector()}

    def __getattr__(self, attr):
        if hasattr(self.plan, attr):
            return getattr(self.plan, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, attr))


class Activate(CommonPlan):
    def process(self):
        circuit_id = self.properties["circuit_id"]
        model_type = self.properties["model_type"]
        circuit_details_id = self.properties.get("circuit_details_id")
        onboarding_complete = self.properties.get("onboarding_complete", False)
        core_only = self.properties.get("core_only", False)
        slm_details = self.properties.get("slm_details")
        self.requested_model = self.properties.get("requested_model", "y1731")
        self.modeler = Modeler(
            self, circuit_id, model_type, circuit_details_id, onboarding_complete, core_only, slm_details
        )
        model = self.set_model()
        modeled_slm = model()

        self.bpo.resources.patch_observed(self.resource["id"], data={"properties": {"y1731_model": modeled_slm}})

    def set_model(self):
        models = {
            "probe": self.modeler.model_probe,
            "reflector": self.modeler.model_reflector,
            "y1731": self.modeler.model_y1731,
        }
        return models[self.requested_model]


class Terminate(CommonPlan):
    def process(self):
        pass
