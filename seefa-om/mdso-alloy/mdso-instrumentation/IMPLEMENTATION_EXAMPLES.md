# MDSO OTel Implementation Examples

**Products Found:** Validation branch - `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/`

**Date:** 2025-01-27

---

## Product Locations

- **Base Class:** `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/common_plan.py`
- **ServiceMapper:** `.archive/.../scripts/serviceMapper/common.py`
- **Fabricator:** `.archive/.../scripts/fabricator/common.py`
- **ConfigModeler:** `.archive/.../scripts/configmodeler/`

---

## Example 1: ServiceMapper with OTel

**File:** `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/serviceMapper/common.py`

### Current Code (Lines 25-100)

```python
class Common(CommonPlan):
    """
    common functionalities utilized by mapper products
    """

    def create_modeled_config(self, payload) -> object:
        # ... existing code ...

    def get_modeled_config(self, config_request_data) -> dict:
        payload = self.create_config_modeler_payload(config_request_data)
        self.logger.info(f"payload: {payload}")
        self.logger.info(f"Creating {config_request_data['requested_model']} config model")
        config_modeler = self.create_modeled_config(payload)
        return config_modeler.resource["properties"]["modeled_config"]
```

### With OTel Instrumentation

```python
import sys
sys.path.append("model-definitions")

from time import sleep
from ra_plugins.ra_cutthrough import RaCutThrough
from scripts.common_plan import CommonPlan
from scripts.configmodeler.utils import NetworkCheckUtils
from scripts.serviceMapper.configDataModel import (
    REQUIRED_TPE_FRE_VALUES,
    REQUIRED_TPE_FRE_VALUES_ADVA_PRO,
)
from scripts.serviceMapper.device import Device

# Add OTel imports
from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.instrumentation import mdso_span
from otel_instrumentation.feature_flags import is_otel_enabled


class Common(CommonPlan, OTelMixin):
    """
    common functionalities utilized by mapper products
    WITH OpenTelemetry instrumentation
    """

    def run(self):
        """Override run() to add OTel root span"""
        # Check feature flag
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            # Fallback to original behavior
            return super().run()

    def create_modeled_config(self, payload) -> object:
        """Create config modeler resource with OTel span"""
        if not is_otel_enabled():
            return super().create_modeled_config(payload)
        
        with mdso_span(
            "mdso.config_modeler.create",
            circuit_id=payload.get("properties", {}).get("circuit_id"),
            device=payload.get("properties", {}).get("device"),
            vendor=payload.get("properties", {}).get("vendor"),
            model_type=payload.get("properties", {}).get("network_config", False) and "network" or "designed"
        ) as span:
            try:
                self.otel_log(
                    "Creating config modeler resource",
                    level="info",
                    device=payload.get("properties", {}).get("device"),
                    vendor=payload.get("properties", {}).get("vendor")
                )
                
                config_modeler = self.bpo.resources.create(self.resource_id, payload)
                
                # Record success
                span.set_attribute("success", True)
                span.set_attribute("config_modeler_id", config_modeler.resource.get("id"))
                
                return config_modeler
                
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise

    def get_modeled_config(self, config_request_data) -> dict:
        """Get modeled config with OTel instrumentation"""
        if not is_otel_enabled():
            return super().get_modeled_config(config_request_data)
        
        with mdso_span(
            "mdso.config_modeler.get",
            circuit_id=config_request_data.get("circuit_id"),
            device=config_request_data.get("device", {}).get("Host Name"),
            vendor=config_request_data.get("device", {}).get("Vendor"),
            requested_model=config_request_data.get("requested_model")
        ) as span:
            try:
                payload = self.create_config_modeler_payload(config_request_data)
                
                # Dual logging
                self.otel_log(
                    f"Creating {config_request_data['requested_model']} config model",
                    level="info",
                    payload=payload,
                    requested_model=config_request_data['requested_model']
                )
                
                config_modeler = self.create_modeled_config(payload)
                modeled_config = config_modeler.resource["properties"]["modeled_config"]
                
                # Record success
                span.set_attribute("success", True)
                span.set_attribute("modeled_config_created", True)
                
                return modeled_config
                
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise

    def get_network_service(self):
        """Get network service with OTel span"""
        if not is_otel_enabled():
            return super().get_network_service()
        
        with mdso_span(
            "mdso.network_service.get",
            circuit_id=self.circuit_id
        ) as span:
            try:
                network_service = self.get_resource_by_type_and_properties(
                    self.BUILT_IN_NETWORK_SERVICE_TYPE,
                    {"circuit_id": self.circuit_id},
                    no_fail=True,
                )
                
                self.otel_log(
                    f"Network Service: {network_service}",
                    level="info",
                    network_service_exists=network_service is not None,
                    orch_state=network_service.get("orchState") if network_service else None
                )
                
                if network_service is None:
                    self.logger.info("Network Service does not exist in MDSO. Proceeding as Standalone Mapper.")
                    span.set_attribute("network_service_exists", False)
                elif network_service["orchState"] != "active":
                    self.logger.info("Network Service OrchState is not active. Proceeding as Standalone Mapper.")
                    span.set_attribute("orch_state", network_service["orchState"])
                
                return network_service
                
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise
```

---

## Example 2: Fabricator with OTel

**File:** `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/fabricator/common.py`

### Current Code

```python
class FactoryBase(CommonPlan, ABC):
    """Base factory class for provisioning and compliance factories."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._circuit_id: str = ""
        self._operation: str = "NoOperationSet"
        self._product: str = "NoProductSet"
        self.child_resources: Dict[str, str] = {}
```

### With OTel Instrumentation

```python
import sys
from abc import ABC
from typing import Any, Dict

sys.path.append("model-definitions")
from scripts.circuitDetailsHandler import CircuitDetailsHandler
from scripts.common_plan import CommonPlan

# Add OTel imports
from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.instrumentation import mdso_span
from otel_instrumentation.feature_flags import is_otel_enabled


class FactoryBase(CommonPlan, OTelMixin, ABC):
    """Base factory class for provisioning and compliance factories WITH OTel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._circuit_id: str = ""
        self._operation: str = "NoOperationSet"
        self._product: str = "NoProductSet"
        self.child_resources: Dict[str, str] = {}

    def run(self):
        """Override run() to add OTel root span"""
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()

    def _set_circuit_details(self):
        """Set circuit details with OTel span"""
        if not is_otel_enabled():
            return super()._set_circuit_details()
        
        with mdso_span(
            "mdso.fabricator.set_circuit_details",
            circuit_id=self.circuit_id,
            operation=self.operation
        ) as span:
            try:
                handler = CircuitDetailsHandler(self, self.circuit_id, self.operation)
                self.circuit_details = handler.circuit_details
                self.circuit_details_id = handler.circuit_details_id
                self.leg_details_ids = handler.leg_details_ids
                
                span.set_attribute("circuit_details_id", self.circuit_details_id)
                span.set_attribute("leg_count", len(self.leg_details_ids) if self.leg_details_ids else 0)
                
                self.otel_log(
                    "Circuit details set",
                    level="info",
                    circuit_details_id=self.circuit_details_id,
                    leg_count=len(self.leg_details_ids) if self.leg_details_ids else 0
                )
                
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise

    def _create_resource(self, label: str, properties: dict, wait_active=False) -> Dict[str, Any]:
        """Create a child resource with OTel span"""
        if not is_otel_enabled():
            return super()._create_resource(label, properties, wait_active)
        
        with mdso_span(
            "mdso.fabricator.create_resource",
            circuit_id=self.circuit_id,
            product=self.product,
            label=label
        ) as span:
            try:
                product = self.bpo.market.get_products_by_resource_type(self.product)[0]
                
                self.otel_log(
                    f"Creating {self.product} resource: {label}",
                    level="info",
                    product=self.product,
                    label=label,
                    wait_active=wait_active
                )
                
                resource = self.bpo.resources.create(
                    self.resource_id,
                    {
                        "productId": product["id"],
                        "label": label,
                        "properties": properties,
                    },
                    wait_active=wait_active,
                ).resource
                
                # Record success
                span.set_attribute("resource_created", True)
                span.set_attribute("resource_id", resource.get("id"))
                span.set_attribute("resource_label", label)
                
                # Track child resource
                self.child_resources[label] = resource.get("id")
                
                self.otel_log(
                    f"Resource created: {label}",
                    level="info",
                    resource_id=resource.get("id"),
                    label=label
                )
                
                return resource
                
            except RuntimeError as e:
                self.logger.warning(f"Unable to create {self.product} from Fabricator")
                error = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE, self.RESOURCE_CREATE_SUBCATEGORY, "Service Device Validator"
                )
                self.otel_error_handler(str(e), e)
                self.exit_error(error)
```

---

## Example 3: ConfigModeler Base with OTel

**File:** `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/configmodeler/base.py`

### With OTel Instrumentation

```python
from scripts.common_plan import CommonPlan
from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.instrumentation import mdso_span
from otel_instrumentation.feature_flags import is_otel_enabled


class Base(CommonPlan, OTelMixin):
    """Base config modeler with OTel instrumentation"""

    def run(self):
        """Override run() to add OTel root span"""
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()

    def model_config(self, device_data, circuit_id):
        """Model device config with OTel span"""
        if not is_otel_enabled():
            return super().model_config(device_data, circuit_id)
        
        vendor = device_data.get("Vendor", "").lower()
        device_fqdn = device_data.get("Host Name", "")
        
        with mdso_span(
            "mdso.config_modeler.model",
            circuit_id=circuit_id,
            vendor=vendor,
            device=device_fqdn
        ) as span:
            try:
                self.otel_log(
                    f"Modeling config for {vendor} device {device_fqdn}",
                    level="info",
                    vendor=vendor,
                    device=device_fqdn,
                    circuit_id=circuit_id
                )
                
                # Call original method
                result = super().model_config(device_data, circuit_id)
                
                span.set_attribute("config_modeled", True)
                span.set_attribute("vendor", vendor)
                
                return result
                
            except Exception as e:
                self.otel_error_handler(str(e), e)
                raise
```

---

## Step-by-Step Implementation

### Step 1: Copy OTel Classes

```bash
# From repository root
cd .archive/mdso-dev/charter_sensor_templates/model-definitions/scripts

# Copy OTel instrumentation directory
cp -r ../../../../seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/ \
     ./otel_instrumentation/

# Verify
ls -la otel_instrumentation/
```

### Step 2: Install Dependencies

```bash
# In the scripts directory
pip install -r otel_instrumentation/requirements.txt
```

### Step 3: Set Environment Variables

```bash
# Enable OTel
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:55681
export MDSO_ENV=dev
```

### Step 4: Modify Product Files

1. Add imports at top of file
2. Add `OTelMixin` to class inheritance
3. Override `run()` method to add root span
4. Add spans to key methods (optional, for detailed tracking)

### Step 5: Test

```bash
# Run a test product execution
# Check Grafana Tempo for traces
# Verify logs in Loki
```

---

## Testing Checklist

- [ ] OTel classes copied to product location
- [ ] Dependencies installed
- [ ] Environment variables set
- [ ] Product modified with mixin
- [ ] Product executes without errors
- [ ] Spans appear in Tempo
- [ ] Logs appear in Loki
- [ ] Correlation context propagated
- [ ] Error handling works
- [ ] Feature flag works (can disable OTel)

---

## Rollback Plan

If issues occur:

1. **Disable OTel via feature flag:**
   ```bash
   export OTEL_ENABLED=false
   ```

2. **Remove mixin from class:**
   ```python
   # Change from:
   class Common(CommonPlan, OTelMixin):
   # To:
   class Common(CommonPlan):
   ```

3. **Revert git changes:**
   ```bash
   git checkout -- scripts/serviceMapper/common.py
   ```

---

## Next Steps

1. ✅ Products found
2. ✅ Implementation examples created
3. ⏳ Copy OTel classes to product location
4. ⏳ Implement in pilot product (ServiceMapper recommended)
5. ⏳ Test in dev environment
6. ⏳ Validate telemetry in Grafana
7. ⏳ Roll out to other products

---

**Ready to implement!** 🚀

