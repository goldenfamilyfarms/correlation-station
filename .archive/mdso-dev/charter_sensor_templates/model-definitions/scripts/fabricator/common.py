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
