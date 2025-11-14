import time
from scripts.common_plan import CommonPlan
from scripts.fabricator.common import FactoryBase


class Activate(FactoryBase):
    """Provisioning factory for activation operations."""

    def process(self):
        """Process provisioning activation for all circuit legs."""
        self.circuit_id = self.properties["circuit_id"]
        operation_type = self.properties["operation_type"]  # CREATE | UPDATE | DELETE
        factory = {
            "CREATE": {
                "process": self._network_service_create,
                "product": self.BUILT_IN_NETWORK_SERVICE_TYPE,
                "operation": "NETWORK_SERVICE_ACTIVATION",
            },
            "UPDATE": {
                "process": self._network_service_update,
                "product": self.BUILT_IN_NETWORK_SERVICE_UPDATE_TYPE,
                "operation": "NETWORK_SERVICE_UPDATE",
            },
        }
        self.product = factory[operation_type]["product"]
        self.operation = factory[operation_type]["operation"]
        self.alternate_cd = self.properties.get("use_alternate_circuit_details_server", False)
        self._set_circuit_details()
        # create network service product appropriate for operation type
        factory[operation_type]["process"]()

    def _network_service_create(self) -> None:
        # Iterate over all circuit details comprising circuit and create network services
        for circuit_details_id in self.leg_details_ids:
            cd = self.bpo.resources.get(circuit_details_id)
            label = cd["label"].strip(".cd")
            payload = {
                "use_alternate_circuit_details_server": self.alternate_cd,
                "circuit_id": label,
                "circuit_details_id": circuit_details_id,
            }
            if "SECONDARY" in label:
                time.sleep(60)  # prevent race condition on Juniper commits
            service = self._create_resource(label=label, properties=payload)
            self.child_resources.update({label: service["id"]})
        # create concurrently and then wait until active
        try:
            self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=1200)
        except RuntimeError:
            self.logger.warning("Unable to create Network Service Update resource")
            error = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Network Service Update"
            )
            self.exit_error(error)

    def _network_service_update(self):
        for circuit_details_id in self.leg_details_ids:
            cd = self.bpo.resources.get(circuit_details_id)
            label = cd["label"].strip(".cd")
            payload = {
                "ip": self.properties.get("ip", False),
                "description": self.properties.get("description", False),
                "bandwidth": self.properties.get("bandwidth", False),
                "use_alternate_circuit_details_server": self.alternate_cd,
                "serviceStateenable": self.properties.get("serviceStateenable", False),
                "circuit_id": label.split("-")[0],
                "serviceStatedisable": self.properties.get("serviceStatedisable", False),
                "circuit_details_id": circuit_details_id,
            }
            if "SECONDARY" in label:
                time.sleep(60)  # prevent race condition on Juniper commits
            service = self._create_resource(label=label, properties=payload)
            self.child_resources.update({label: service["id"]})
        # create concurrently and then wait until active
        try:
            self.bpo.resources.await_active(list(self.child_resources.values()), interval=60, max=1200)
        except RuntimeError:
            self.logger.warning("Unable to create Network Service Update resource")
            error = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Network Service Update"
            )
            self.exit_error(error)

    def _network_service_delete(self):
        pass


class Terminate(CommonPlan):
    pass
