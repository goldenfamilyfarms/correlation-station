# MDSO Product Location Analysis

**Date:** 2025-01-27  
**Status:** Products Not Found in This Repository

---

## Executive Summary

After comprehensive codebase analysis, **MDSO scriptplan products (ServiceMapper, Fabricator, ConfigModeler, etc.) are NOT located in this repository**. The products appear to be in a separate location, likely on the MDSO server or in a different repository.

---

## Search Results

### ❌ Not Found in This Repository

1. **CommonPlan class** - Not found
2. **ServiceMapper product code** - Not found
3. **Fabricator product code** - Not found
4. **ConfigModeler product code** - Not found
5. **scripts/common_plan.py** - Not found
6. **scripts/serviceMapper/** - Not found
7. **scripts/fabricator/** - Not found
8. **.archive/mdso-dev/** - Not found

### ✅ What IS in This Repository

1. **OTel Instrumentation Classes** ✅
   - `seefa-om/mdso-alloy/mdso-instrumentation/otel_instrumentation/`
   - `instrumentation.py` - OTel setup functions
   - `otel_mdso_utils.py` - MDSO-specific helpers
   - `otel_mixin.py` - Mixin class (just created)

2. **Sense Apps** ✅
   - `seefa-om/sense-apps/palantir/` - Creates MDSO resources
   - `seefa-om/sense-apps/arda/` - Creates MDSO resources
   - `seefa-om/sense-apps/beorn/` - Creates MDSO resources
   - These apps **call** MDSO products via API, but don't contain product code

3. **Correlation Engine** ✅
   - `seefa-om/correlation-engine/` - Processes MDSO telemetry
   - API endpoints that reference MDSO products

4. **Test Scripts** ✅
   - `seefa-om/scripts/send-test-span.py` - Test telemetry sender

---

## Where Products Likely Are

Based on the strategy document and codebase analysis:

### Option 1: MDSO Server (Most Likely)
**Location:** On the MDSO server itself (e.g., `159.56.4.37` or similar)

**Evidence:**
- Strategy mentions `.archive/mdso-dev/charter_sensor_templates/model-definitions/scripts/`
- Products execute on MDSO servers
- OTel instrumentation needs to be deployed to where products run

**Path Structure (Likely):**
```
/mdso-dev/charter_sensor_templates/model-definitions/scripts/
├── common_plan.py          # Base class for all products
├── serviceMapper/
│   └── common.py           # ServiceMapper product
├── fabricator/
│   └── common.py           # Fabricator product
├── configmodeler/
│   └── common.py           # ConfigModeler product
└── ...
```

### Option 2: Separate Repository
**Location:** Different Git repository (possibly private/internal)

**Evidence:**
- Products are referenced but not present
- Strategy document references `.archive/` which suggests archived/moved code
- May be in a separate "mdso-dev" or "charter-sensor-templates" repo

### Option 3: Archive Directory (Not in This Repo)
**Location:** `.archive/mdso-dev/` (mentioned in strategy but not in this repo)

**Evidence:**
- Strategy explicitly mentions this path
- May have been moved or excluded from this repository

---

## How Products Are Referenced

### 1. Via Resource Types
Products are referenced by resource type IDs:
- `charter.resourceTypes.ServiceMapper`
- `charter.resourceTypes.NetworkService`
- `charter.resourceTypes.DisconnectMapper`
- `charter.resourceTypes.ConfigModeler`
- `charter.resourceTypes.Fabricator`

### 2. Via API Calls
Sense apps create MDSO resources via API:

```python
# From sense-apps/palantir/palantir_app/bll/compliance_provisioning.py
resource = mdso_post(
    "/bpocore/market/api/v1/resources?validate=false&obfuscate=true",
    payload
)
# Returns resource with resourceTypeId: "charter.resourceTypes.ServiceMapper"
```

### 3. Via Product Queries
Products are queried by name:

```python
# From sense-apps/palantir/palantir_app/dll/mdso.py
product_id = product_query("ServiceMapper")
```

---

## Implementation Strategy

Since products are not in this repository, here's how to proceed:

### Phase 1: Locate Products

1. **Check MDSO Server**
   ```bash
   # SSH to MDSO server
   ssh user@mdso-server-ip
   
   # Search for products
   find /opt -name "common_plan.py" 2>/dev/null
   find /opt -name "*serviceMapper*" -type d 2>/dev/null
   find /opt -name "*fabricator*" -type d 2>/dev/null
   ```

2. **Check for Archive Directory**
   ```bash
   # In this repository
   find . -name ".archive" -type d
   find . -name "*mdso-dev*" -type d
   ```

3. **Check Separate Repository**
   - Look for "mdso-dev" repository
   - Look for "charter-sensor-templates" repository
   - Check internal GitLab/GitHub for MDSO-related repos

### Phase 2: Deploy OTel Instrumentation

Once products are located:

1. **Copy OTel Classes to Product Location**
   ```bash
   # Copy instrumentation classes
   cp -r mdso-alloy/mdso-instrumentation/otel_instrumentation/ \
        /path/to/products/otel_instrumentation/
   ```

2. **Install Dependencies**
   ```bash
   # On MDSO server, in product directory
   pip install -r otel_instrumentation/requirements.txt
   ```

3. **Update Product Code**
   - Add mixin to product classes
   - Follow implementation guide

### Phase 3: Alternative Approach (If Products Unavailable)

If products cannot be located or modified directly:

1. **Instrument at API Level**
   - Add OTel to Sense apps that call MDSO
   - Track MDSO resource creation/status
   - Correlate via resource IDs

2. **Instrument MDSO Client**
   - Add OTel to MDSO API client calls
   - Track product execution via API responses
   - Use resource status endpoints

3. **Log-Based Instrumentation**
   - Parse MDSO product logs
   - Extract trace context from logs
   - Correlate via circuit_id/resource_id

---

## Recommended Next Steps

### Immediate Actions

1. **Contact MDSO Team**
   - Ask for product code location
   - Request access to product repository
   - Get deployment process documentation

2. **Check MDSO Server**
   - SSH to MDSO server (if accessible)
   - Locate product directories
   - Identify deployment structure

3. **Review Deployment Docs**
   - Check `seefa-om/mdso-alloy/DEPLOYMENT-GUIDE-ENHANCED.md`
   - Review MDSO instrumentation deployment process
   - Understand product execution environment

### If Products Are Found

1. **Follow Implementation Guide**
   - Use `IMPLEMENTATION_GUIDE.md`
   - Add OTel mixin to products
   - Test in dev environment

2. **Deploy OTel Classes**
   - Copy instrumentation to product location
   - Update product imports
   - Test integration

### If Products Cannot Be Modified

1. **Instrument at Integration Points**
   - Add OTel to Sense apps
   - Track MDSO API calls
   - Correlate via resource IDs

2. **Use Log-Based Correlation**
   - Parse MDSO logs
   - Extract correlation context
   - Link to traces

---

## Product Reference Map

Based on codebase analysis, here are the products referenced:

| Product Name | Resource Type ID | Referenced In |
|-------------|------------------|---------------|
| ServiceMapper | `charter.resourceTypes.ServiceMapper` | `palantir_app/bll/compliance_provisioning.py` |
| NetworkService | `charter.resourceTypes.NetworkService` | `correlation-engine/app/routes/mdso.py` |
| DisconnectMapper | `charter.resourceTypes.DisconnectMapper` | `correlation-engine/app/routes/mdso.py` |
| NetworkServiceUpdate | `charter.resourceTypes.NetworkServiceUpdate` | `correlation-engine/app/routes/mdso.py` |
| PortActivation | `charter.resourceTypes.PortActivation` | `palantir_app/bll/port.py` |
| Compliance | `charter.resourceTypes.Compliance` | Multiple files |
| DeviceOnboarder | `charter.resourceTypes.DeviceOnboarder` | `palantir_app/dll/mdso.py` |
| CircuitDetails | `charter.resourceTypes.CircuitDetails` | `palantir_app/common/mdso_operations.py` |

---

## Questions to Answer

1. **Where are MDSO products actually located?**
   - On MDSO server?
   - In separate repository?
   - In archive directory?

2. **How are products deployed?**
   - Git-based deployment?
   - Manual file copy?
   - Container-based?

3. **Can products be modified?**
   - Do we have write access?
   - What's the deployment process?
   - Are there change controls?

4. **What's the product execution environment?**
   - Python version?
   - Dependencies?
   - Execution context?

---

## Conclusion

**MDSO scriptplan products are not in this repository.** They need to be located before OTel instrumentation can be implemented. The OTel mixin and instrumentation classes are ready - they just need to be integrated with the actual product code.

**Next Action:** Locate product code location and deployment process.

---

## References

- [Implementation Guide](./IMPLEMENTATION_GUIDE.md) - Ready to use once products are found
- [Strategy Review](./STRATEGY_REVIEW.md) - Original strategy assessment
- [OTel Mixin](./otel_instrumentation/otel_mixin.py) - Implementation ready
- [Original Strategy](https://raw.githubusercontent.com/goldenfamilyfarms/correlation-station/claude/analyze-logging-otel-strategy-01UwuAJMKz9NoJgubNbA1Qsf/OTEL_IMPLEMENTATION_STRATEGY.md)

