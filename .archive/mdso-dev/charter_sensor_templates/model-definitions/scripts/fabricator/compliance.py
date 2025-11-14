from scripts.fabricator.common import FactoryBase
import time


class Activate(FactoryBase):
    def _get_child_resource_type(self) -> str:
        """Return the resource type for child resources."""
        return ""

    def process(self):
        self.operation = "SERVICE_MAPPER"
        self.product = self.BUILT_IN_SERVICE_MAPPER_TYPE
        self.circuit_id = self.properties["circuit_id"]
        self.remediation_flag = self.properties["remediation_flag"]
        self.alternate_cd = self.properties.get("use_alternate_circuit_details_server", False)
        self.device_properties = self.properties.get("device_properties", {})
        self.order_type = self.properties.get("order_type", "")
        self.slm_eligible = self.properties.get("slm_eligible", False)

        self._delete_existing_resource_and_dependencies()

        # MAIN PROCESS (SERVICE MAPPER)
        # Step 1: Get circuit details
        self._set_circuit_details()
        # Step 2: Iterator Over all in CD
        for circuit_details_id in self.leg_details_ids:
            cd = self.bpo.resources.get(circuit_details_id)
            label = cd["label"].strip(".cd")
            payload = {
                "remediation_flag": self.remediation_flag,
                "use_alternate_circuit_details_server": self.alternate_cd,
                "device_properties": self.device_properties,
                "circuit_id": self.circuit_id,
                "circuit_details_id": circuit_details_id,
                "order_type": self.order_type,
                "slm_eligible": self.slm_eligible,
            }
            if "SECONDARY" in label:
                time.sleep(60)  # allow time for any duplicate devices in PRIMARY to onboard
            mapper = self._create_resource(label, payload)
            self.child_resources.update({label: mapper["id"]})

        # we created all children at once, now let's wait for them to complete
        self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=600)

        # Step 3: Harvest any child resource data the parent will need
        service_differences, slm_issues = self._get_child_compliance_issues()

        # Step 4: Patch the resource with any data from the children required at parent level
        if service_differences:
            for leg in service_differences:
                self._patch_property("service_differences", service_differences[leg], leg)
        if slm_issues:
            for leg in slm_issues:
                self._patch_property("slm_traffic_passing", slm_issues[leg])
                break

    def _get_child_compliance_issues(self):
        # service differences and slm traffic not passing are compliance issues that need to be recorded
        service_differences = {}
        slm_issues = {}
        for child in self.child_resources:
            resource = self.bpo.resources.get(self.child_resources[child])
            differences = resource["properties"].get("service_differences", {})
            slm_passing = resource["properties"].get("slm_traffic_passing", True)
            if differences:
                service_differences.update({child: differences})
            if slm_passing is False:
                slm_issues.update({child: False})
        return service_differences, slm_issues

    def _patch_property(self, property_name, new_value, label=""):
        if isinstance(new_value, bool):
            self.bpo.resources.patch_observed(
                self.resource_id, data={"properties": {property_name: new_value}}
            )
        else:
            if self.resource["properties"].get(property_name):
                value = self.resource["properties"][property_name]
                value.update({label: new_value})
            else:
                value = {label: new_value}
            self.bpo.resources.patch_observed(
                self.resource_id, data={"properties": {property_name: value}}
            )


class Terminate(FactoryBase):
    def process(self):
        pass
