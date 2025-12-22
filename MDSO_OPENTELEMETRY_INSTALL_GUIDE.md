# MDSO OpenTelemetry Installation Troubleshooting Guide

## Problems Identified

### 1. ❌ Wrong Import Paths in `otel_mixin.py`

**Problem**: `otel_mixin.py` was using `from otel.instrumentation` instead of `from scripts.otel.instrumentation`

**Error**: `No module named 'otel'`

**Fix Applied**: Changed all imports to use `scripts.otel.*` prefix

### 2. ❌ Missing OpenTelemetry Packages in `requirements_cst.txt`

**Problem**: The TOML file `scripts.toml` points to `requirements_cst.txt`, but it didn't have OpenTelemetry packages

**Fix Applied**: Added OpenTelemetry packages to `requirements_cst.txt`

## What Was Fixed

### Fixed Import Paths in `otel_mixin.py`

Changed:
- `from otel.instrumentation` → `from scripts.otel.instrumentation`
- `from otel.otel_mdso_utils` → `from scripts.otel.otel_mdso_utils`
- `from otel.feature_flags` → `from scripts.otel.feature_flags`
- `from otel.metrics` → `from scripts.otel.metrics`

### Added OpenTelemetry to `requirements_cst.txt`

Added:
- PYPI index URLs for `mdsocharter-pypi` and `charter-pypi`
- All OpenTelemetry packages with pinned versions

## How MDSO Virtual Environments Work

MDSO creates virtual environments based on TOML files:

1. **TOML file** (e.g., `scripts.toml`) specifies:
   - Python version: `python = "py310"`
   - Requirements file: `requirements = "requirements_cst.txt"`

2. **MDSO creates venv** and installs packages from the requirements file

3. **Scripts run** in that venv

## Why Your Manual Installation Didn't Work

If you SSH'd into the server and installed packages manually:

1. **Wrong venv**: You might have installed to a different venv than MDSO uses
2. **MDSO recreates venvs**: MDSO may recreate venvs on each run, wiping your manual installs
3. **Requirements file**: MDSO uses the requirements file specified in TOML, not manual installs

## Solution: Update Requirements File

The fix is to ensure `requirements_cst.txt` has OpenTelemetry packages (which I've done).

## Verification Steps

### 1. Check TOML File Points to Correct Requirements

```bash
# On MDSO server
cat /path/to/model-definitions/scripts.d/scripts.toml
```

Should show:
```toml
[virtualenv]
python = "py310"
requirements = "requirements_cst.txt"  # This file now has OpenTelemetry
```

### 2. Check Requirements File Has OpenTelemetry

```bash
# On MDSO server
cat /path/to/model-definitions/requirements_cst.txt | grep opentelemetry
```

Should show:
```
opentelemetry-api==1.12.0
opentelemetry-sdk==1.12.0
...
```

### 3. Check PYPI Index URLs

```bash
# On MDSO server
cat /path/to/model-definitions/requirements_cst.txt | head -5
```

Should show:
```
--index-url http://blueplanet/vfirewall-templates-pypi/simple/
--extra-index-url http://blueplanet/mdsocharter-pypi/simple/
--extra-index-url http://blueplanet/charter-pypi/simple/
```

### 4. Verify PYPI Server Has Packages

```bash
# Test if you can access the PYPI server
curl http://blueplanet/mdsocharter-pypi/simple/opentelemetry-api/
```

Should return HTML with package links.

### 5. Check Virtual Environment Location

MDSO creates venvs in a specific location. Find it:

```bash
# Find where MDSO creates venvs
find /opt -name "venv" -type d 2>/dev/null | grep -i mdso
find /opt -path "*/vfirewallplan/venv" 2>/dev/null
```

### 6. Check if Packages Are Installed in Venv

```bash
# If you find the venv location
/path/to/venv/bin/pip list | grep opentelemetry
```

## Common Issues and Solutions

### Issue: "No module named 'opentelemetry'"

**Causes**:
1. Packages not in requirements file ✅ **FIXED**
2. Wrong PYPI index URLs ✅ **FIXED**
3. PYPI server not accessible
4. Virtual environment not using correct requirements file

**Solutions**:
- ✅ Verify `requirements_cst.txt` has OpenTelemetry packages
- ✅ Verify PYPI index URLs are correct
- ✅ Test PYPI server connectivity
- ✅ Check TOML file points to correct requirements file

### Issue: "No module named 'otel'"

**Cause**: Wrong import paths in `otel_mixin.py` ✅ **FIXED**

**Solution**: All imports now use `scripts.otel.*` prefix

### Issue: "ERROR: Could not find a version that satisfies the requirement wrapt<2.0.0,>=1.0.0"

**Error Message**:
```
ERROR: Could not find a version that satisfies the requirement wrapt<2.0.0,>=1.0.0 (from opentelemetry-instrumentation-urllib3) (from versions: none)
ERROR: No matching distribution found for wrapt<2.0.0,>=1.0.0
```

**Cause**: 
- `opentelemetry-instrumentation-urllib3==0.33b0` requires `wrapt<2.0.0,>=1.0.0`
- The `wrapt` package is not available in the PYPI server, or not in a compatible version

**Fix Applied**: 
- Added `wrapt==1.17.3` explicitly to `requirements_cst.txt`
- This version satisfies the constraint `wrapt<2.0.0,>=1.0.0`

**If Still Failing**:
- Verify `wrapt==1.17.3` is in the PYPI server (`mdsocharter-pypi` or `charter-pypi`)
- If not, add `wrapt==1.17.3` to the PYPI server's requirements file
- Check for version conflicts with other packages that might require `wrapt>=2.0.0`

### Issue: Packages installed manually but not found

**Cause**: MDSO recreates venvs or uses different venv

**Solution**: 
- Don't install manually
- Update requirements file (which I've done)
- Let MDSO install from requirements file

## Next Steps

1. **Deploy the fixes**:
   - Updated `otel_mixin.py` with correct import paths
   - Updated `requirements_cst.txt` with OpenTelemetry packages

2. **Verify on MDSO server**:
   - Check requirements file has OpenTelemetry
   - Check TOML points to correct requirements
   - Test PYPI connectivity

3. **Trigger MDSO job**:
   - MDSO will create venv with updated requirements
   - Packages should install automatically

4. **Check logs**:
   - Look for "Successfully imported" messages
   - Verify no "No module named" errors

## Diagnostic Script

Create this script to test on MDSO server:

```python
#!/usr/bin/env python
# test_otel_install.py
import sys
import os

print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("\nsys.path:")
for i, path in enumerate(sys.path[:10]):
    print(f"  {i}. {path}")

print("\nTesting imports...")
try:
    from opentelemetry import trace
    print("✅ opentelemetry.trace imported")
except ImportError as e:
    print(f"❌ opentelemetry.trace failed: {e}")

try:
    import structlog
    print("✅ structlog imported")
except ImportError as e:
    print(f"❌ structlog failed: {e}")

try:
    from scripts.otel.otel_mixin import OTelMixin
    print("✅ scripts.otel.otel_mixin imported")
except ImportError as e:
    print(f"❌ scripts.otel.otel_mixin failed: {e}")
```

Run it in the MDSO venv to see what's happening.

