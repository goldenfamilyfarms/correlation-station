import sys
from abc import ABC
from typing import Any, Dict

sys.path.append("model-definitions")
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.common_plan import CommonPlan


class FactoryBase(CommonPlan, ABC):
    """Base factory class for provisioning and compliance factories."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._circuit_id: str = ""
        self._operation: str = "NoOperationSet"
        self._product: str = "NoProductSet"
        self.child_resources: Dict[str, str] = {}  # {label: resource id}

    @property
    def circuit_id(self) -> str:
        """Get the circuit ID."""
        return self._circuit_id

    @circuit_id.setter
    def circuit_id(self, circuit_id: str) -> None:
        """Set the circuit ID with validation."""
        if not isinstance(circuit_id, str):
            raise ValueError("circuit_id must be a string")
        if not circuit_id.strip():
            raise ValueError("circuit_id cannot be empty")
        self._circuit_id = circuit_id.strip()

    @property
    def operation(self) -> str:
        """Get the current operation."""
        return self._operation

    @operation.setter
    def operation(self, operation: str) -> None:
        """Set the operation."""
        if not isinstance(operation, str):
            raise ValueError("operation must be a string")
        self._operation = operation

    @property
    def product(self) -> str:
        """Get the current product."""
        return self._product

    @product.setter
    def product(self, product: str) -> None:
        """Set the product."""
        if not isinstance(product, str):
            raise ValueError("product must be a string")
        self._product = product

    def _set_circuit_details(self):
        # create circuit details collector resource, set circuit details, circuit details id, and leg details ids attrs
        handler = CircuitDetailsHandler(self, self.circuit_id, self.operation)
        self.circuit_details = handler.circuit_details
        self.circuit_details_id = handler.circuit_details_id
        self.leg_details_ids = handler.leg_details_ids

    def _delete_existing_resource_and_dependencies(self):
        """Delete existing child resources and their dependencies for this factory resource.

        This method cleans up any existing child resources of the factory before creating new ones.
        It's particularly useful for re-activation scenarios where old resources need to be removed.
        """
        try:
            # Get existing children of this factory resource
            existing_children = self.bpo.resources.get(self.resource_id).get("children", [])

            if existing_children:
                self.logger.info(f"Deleting {len(existing_children)} existing child resources and dependencies")

                for child_id in existing_children:
                    try:
                        # Get dependencies of the child resource
                        child_resource = self.bpo.resources.get(child_id)
                        resource_dependents = self.get_dependencies(child_id)

                        # Terminate dependencies first
                        for dependent in resource_dependents:
                            self.logger.info(f"Terminating dependent resource: {dependent['id']}")
                            self.bpo.resources.patch(
                                dependent["id"],
                                {"desiredOrchState": "terminated", "orchState": "terminated"},
                            )

                        # Then terminate the child resource itself
                        self.logger.info(f"Terminating child resource: {child_id}")
                        self.bpo.resources.patch(
                            child_id,
                            {"desiredOrchState": "terminated", "orchState": "terminated"},
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to delete child resource {child_id}: {e}")
                        # Continue with other children even if one fails

            else:
                self.logger.info("No existing child resources to delete")

        except Exception as e:
            self.logger.warning(f"Error during cleanup of existing resources: {e}")
            # Don't fail the entire operation if cleanup fails

    def _create_resource(self, label: str, properties: dict, wait_active=False) -> Dict[str, Any]:
        """Create a child resource and associate it with the factory."""
        product = self.bpo.market.get_products_by_resource_type(self.product)[0]
        try:
            return self.bpo.resources.create(
                self.resource_id,
                {
                    "productId": product["id"],
                    "label": label,
                    "properties": properties,
                },
                wait_active=wait_active,
            ).resource
        except RuntimeError:
            self.logger.warning(f"Unable to create {self.product} from Fabricator")
            error = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Service Device Validator"
            )
            self.exit_error(error)
