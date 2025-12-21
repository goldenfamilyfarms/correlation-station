# Using requirements_otel.txt Instead of requirements_cst.txt

## Why Use requirements_otel.txt?

You're absolutely right! Using `requirements_otel.txt` is better because:

1. **Separation of Concerns**: Keeps OpenTelemetry requirements separate from base requirements
2. **Selective Usage**: Only products that need OpenTelemetry use it
3. **Cleaner**: Doesn't affect products that don't need OpenTelemetry
4. **Modular**: Easier to maintain and update

## What I've Done

1. ✅ **Reverted `requirements_cst.txt`** to its original state (no OpenTelemetry)
2. ✅ **Created `requirements_otel.txt`** in `model-definitions/` with OpenTelemetry packages
3. ⚠️ **You need to update TOML files** to use `requirements_otel.txt` for products that need OpenTelemetry

## How to Use requirements_otel.txt

### Option 1: Update Existing TOML File

If you want `scripts.toml` (or any other TOML) to use OpenTelemetry:

**Update `scripts.d/scripts.toml`:**
```toml
[virtualenv]
python = "py310"
requirements = "requirements_otel.txt"  # Changed from requirements_cst.txt
```

### Option 2: Create New TOML for OpenTelemetry Products

Create a new TOML file for products that need OpenTelemetry:

**Create `scripts.d/scripts.otel.toml`:**
```toml
[virtualenv]
python = "py310"
requirements = "requirements_otel.txt"
```

Then configure your products to use this TOML file.

## requirements_otel.txt Contents

The `requirements_otel.txt` file includes:

```txt
--index-url http://blueplanet/vfirewall-templates-pypi/simple/
--extra-index-url http://blueplanet/mdsocharter-pypi/simple/
--extra-index-url http://blueplanet/charter-pypi/simple/

# Base packages (shared with requirements_cst.txt)
jsonpath
requests
plansdk
ipaddress

# OpenTelemetry instrumentation packages
opentelemetry-api==1.12.0
opentelemetry-sdk==1.12.0
opentelemetry-exporter-otlp-proto-http==1.12.0
opentelemetry-semantic-conventions==0.33b0
structlog==21.5.0
opentelemetry-instrumentation-requests==0.33b0
opentelemetry-instrumentation-urllib3==0.33b0
pyroscope-io==0.8.14
```

## Which Products Should Use requirements_otel.txt?

Products that use OpenTelemetry (check if they inherit from `OTelMixin` or use `create_root_span`):

- Products using `common_plan.py` with OpenTelemetry features
- Products that explicitly use `OTelMixin`
- Products that need tracing/instrumentation

## Installation

After updating the TOML file:

1. **MDSO will automatically use the new requirements file** when creating virtual environments
2. **Or manually install** in your venv:
   ```bash
   pip install -r requirements_otel.txt
   ```

## Summary

- ✅ `requirements_cst.txt` - Base requirements (no OpenTelemetry)
- ✅ `requirements_otel.txt` - Base + OpenTelemetry (for products that need it)
- ⚠️ Update TOML files to reference `requirements_otel.txt` where needed

This approach is much cleaner and more maintainable!

