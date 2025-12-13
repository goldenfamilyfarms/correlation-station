# Quick Start: Implementing OTel in MDSO Products

**Products Found:** Validation branch - `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/`

**Date:** 2025-01-27

---

## 🎯 Quick Implementation (5 Steps)

### Step 1: Copy OTel Classes to Product Location

```bash
# Switch to validation branch (if not already)
cd /home/derrick/dev-work/correlation-station
git checkout validation

# Navigate to scripts directory
cd .archive/mdso-dev/charter_sensor_templates/model-definitions/scripts

# Copy OTel instrumentation
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
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:55681
export MDSO_ENV=dev
```

### Step 4: Add OTel to ServiceMapper (Pilot Product)

**File:** `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/serviceMapper/common.py`

**Change:**
```python
# BEFORE (line 25)
class Common(CommonPlan):

# AFTER
from otel_instrumentation.otel_mixin import OTelMixin
from otel_instrumentation.feature_flags import is_otel_enabled

class Common(CommonPlan, OTelMixin):
```

**Add run() override:**
```python
def run(self):
    """Override run() to add OTel root span"""
    if is_otel_enabled():
        self.__init_otel__()
        with self.create_root_span():
            return super().run()
    else:
        return super().run()
```

### Step 5: Test

```bash
# Execute a ServiceMapper product
# Check Grafana Tempo for traces:
# {service.name="mdso.common"}
```

---

## 📋 Complete Example: ServiceMapper

**File:** `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/serviceMapper/common.py`

### Minimal Implementation (Just Root Span)

```python
""" -*- coding: utf-8 -*-

Common Mapper Plans WITH OpenTelemetry

Versions:
   0.1 Oct 10, 2022
       Initial check in of common plan for mapper products
   0.2 Jan 27, 2025
       Added OpenTelemetry instrumentation
"""

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
from otel_instrumentation.feature_flags import is_otel_enabled


class Common(CommonPlan, OTelMixin):
    """
    common functionalities utilized by mapper products
    WITH OpenTelemetry instrumentation
    """

    def run(self):
        """Override run() to add OTel root span"""
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()

    # All other methods remain unchanged - OTel will automatically:
    # - Track execution via root span
    # - Log via dual logging (standard + OTel)
    # - Handle errors via otel_error_handler
```

### Enhanced Implementation (With Method-Level Spans)

```python
# ... (same imports as above) ...

from otel_instrumentation.instrumentation import mdso_span


class Common(CommonPlan, OTelMixin):
    """
    common functionalities utilized by mapper products
    WITH OpenTelemetry instrumentation
    """

    def run(self):
        """Override run() to add OTel root span"""
        if is_otel_enabled():
            self.__init_otel__()
            with self.create_root_span():
                return super().run()
        else:
            return super().run()

    def get_modeled_config(self, config_request_data) -> dict:
        """Get modeled config with OTel span tracking"""
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
                    requested_model=config_request_data['requested_model'],
                    device=config_request_data.get("device", {}).get("Host Name")
                )
                
                config_modeler = self.create_modeled_config(payload)
                modeled_config = config_modeler.resource["properties"]["modeled_config"]
                
                # Record success
                span.set_attribute("success", True)
                span.set_attribute("config_modeler_id", config_modeler.resource.get("id"))
                
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

## 🧪 Testing

### Test 1: Verify OTel Initialization

```python
# In a test script or Python shell
from scripts.serviceMapper.common import Common
from scripts.common_plan import CommonPlan

# Create instance (requires proper MDSO context)
# product = Common(...)

# Check if OTel is initialized
if hasattr(product, '_otel_initialized'):
    print("✅ OTel initialized")
else:
    print("❌ OTel not initialized")
```

### Test 2: Execute Product and Check Traces

```bash
# 1. Execute a ServiceMapper product via MDSO
# 2. Wait 5+ seconds for batch export
# 3. Check Grafana Tempo:
#    {service.name="mdso.common"}
# 4. Verify spans appear with circuit_id attributes
```

### Test 3: Verify Dual Logging

```bash
# Check that both standard logs and OTel logs are generated
# Standard logs: /bp2/log/splunk-logs/sensor-templates-splunk.log
# OTel logs: Should appear in Loki with trace correlation
```

---

## 🔧 Troubleshooting

### Issue: Import Error

**Error:** `ModuleNotFoundError: No module named 'otel_instrumentation'`

**Solution:**
```bash
# Ensure OTel classes are in the right location
cd .archive/mdso-dev/charter_sensor_templates/model-definitions/scripts
ls -la otel_instrumentation/

# Check Python path
python -c "import sys; print(sys.path)"
```

### Issue: Spans Not Appearing

**Check:**
1. Feature flag enabled: `echo $OTEL_ENABLED`
2. OTel endpoint reachable: `curl http://159.56.4.94:55681/v1/traces`
3. Wait 5+ seconds after execution (batch processor delay)
4. Check OTel logs for export errors

**Solution:**
```python
# Enable debug logging
import logging
logging.getLogger('opentelemetry').setLevel(logging.DEBUG)
```

### Issue: AttributeError on circuit_id

**Error:** `AttributeError: 'Common' object has no attribute 'circuit_id'`

**Solution:**
The mixin extracts `circuit_id` from instance attributes. If it's not set, it will be None. This is OK - the span will just not have that attribute.

To ensure circuit_id is available:
```python
# In CommonPlan.run(), circuit_id is typically extracted from properties
# The mixin will automatically pick it up if it exists
```

---

## 📊 What Gets Instrumented

### Automatic (Just by adding mixin)

1. **Root Span** - Entire product execution
2. **Dual Logging** - Standard logger + OTel structured logger
3. **Error Tracking** - Automatic error span attributes
4. **Correlation Context** - circuit_id, resource_id propagation

### Optional (Method-level spans)

Add `mdso_span` context managers to key methods:
- `get_modeled_config()` - Config modeler operations
- `get_network_service()` - Network service queries
- `patch_service_diffs()` - Service difference patching
- `get_network_config()` - Network config retrieval

---

## ✅ Success Criteria

After implementation, you should see:

1. **In Grafana Tempo:**
   - Spans with `service.name="mdso.common"` (or product name)
   - Spans with `circuit_id` attribute
   - Root span for entire execution
   - Child spans for instrumented methods

2. **In Loki:**
   - Structured logs with trace_id
   - Correlation context (circuit_id, resource_id)
   - Error logs with error categories

3. **In Prometheus:**
   - Span count metrics
   - Error rate metrics
   - Duration histograms

---

## 🚀 Next Steps

1. ✅ Products found
2. ✅ Implementation examples created
3. ⏳ Copy OTel classes
4. ⏳ Implement in ServiceMapper
5. ⏳ Test in dev
6. ⏳ Validate in Grafana
7. ⏳ Roll out to other products

---

**Ready to implement!** See `IMPLEMENTATION_EXAMPLES.md` for more detailed examples.

