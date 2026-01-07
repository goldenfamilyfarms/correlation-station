# OpenTelemetry Deployment Checklist

## Changes Made

### 1. Code Fix (commit 2fcd483)
- **File:** `scripts/fabricator/compliance.py`
- **Fix:** Removed non-existent method `_delete_existing_resource_and_dependencies()`
- **Impact:** Eliminates AttributeError that caused job failures

### 2. Dependencies Fix (commit 0bf00b9)
- **File:** `requirements_cst.txt`
- **Changes:**
  - Added public PyPI fallback: `--extra-index-url https://pypi.org/simple/`
  - Updated OpenTelemetry from 1.12.0 → 1.20.0
  - Updated structlog from 21.5.0 → 23.2.0
  - Updated semantic-conventions from 0.33b0 → 0.41b0
- **Impact:** Enables OpenTelemetry instrumentation when virtualenv rebuilds

## Deployment Steps

### Prerequisites
- [x] Code changes committed to `claude/fix-opentelemetry-imports-uwQF5`
- [x] Changes pushed to remote repository

### To Activate Changes

**Choose ONE of the following:**

#### Option A: Onboard to BluePlanet (Recommended)
1. Merge PR to main branch
2. Navigate to BluePlanet UI → Model Definitions
3. Click "Onboard" or trigger onboarding via API
4. Wait for onboarding to complete (virtualenv will be recreated)

#### Option B: Restart Scriptplan App
1. Identify scriptplan container/pod:
   ```bash
   kubectl get pods | grep scriptplan
   # OR
   docker ps | grep scriptplan
   ```
2. Restart the scriptplan app:
   ```bash
   kubectl rollout restart deployment/scriptplan
   # OR
   docker restart <scriptplan-container-id>
   ```
3. Virtualenv will be recreated on next script execution

#### Option C: Wait for Next Deployment
- Changes will take effect during next regular deployment cycle
- Virtualenv automatically recreated during deployment

## Verification Steps

### 1. Check Virtualenv Recreation
Look for these log messages in scriptplan logs:
```
Creating virtualenv for scripts...
Installing packages from requirements_cst.txt...
Successfully installed opentelemetry-api-1.20.0 opentelemetry-sdk-1.20.0...
```

### 2. Verify OpenTelemetry Import
The script should now log:
```
✅ instrumentation.py: Successfully imported OpenTelemetry modules - OTEL_AVAILABLE=True
✅ instrumentation.py: Successfully imported structlog - STRUCTLOG_AVAILABLE=True
✅ instrumentation.py: Successfully imported pyroscope - PYROSCOPE_AVAILABLE=True
```

Instead of:
```
❌ instrumentation.py: Failed to import OpenTelemetry modules - OTEL_AVAILABLE=False - Error: No module named 'opentelemetry'
```

### 3. Check Job Execution
- Re-run the failed job (ID: c89e1bfd-eb3e-11f0-8bc4-6df956d7cef3)
- Should complete successfully without AttributeError
- Should have OpenTelemetry traces exported

### 4. Verify Telemetry Data
Check for traces in your observability backend:
- Service name: `mdso-scriptplan`
- Span names: `compliance_activate`, `compliance.get_circuit_details`, etc.
- Trace files: `/opt/ciena/bp2/alloy-collector/traces.ndjson` (if using file export)

## Troubleshooting

### If OpenTelemetry still not available after onboarding:

1. **Check virtualenv location:**
   ```bash
   # On scriptplan container
   ls -la /tmp/scriptplan-venvs/
   # or wherever virtualenvs are cached
   ```

2. **Check pip install logs:**
   ```bash
   # Look for errors installing OpenTelemetry packages
   grep -i "opentelemetry" /var/log/scriptplan/*.log
   ```

3. **Verify PyPI connectivity:**
   ```bash
   # Test if scriptplan can reach public PyPI
   curl -I https://pypi.org/simple/opentelemetry-api/
   ```

4. **Manual verification:**
   ```bash
   # Inside scriptplan container
   /path/to/venv/bin/pip list | grep opentelemetry
   ```

### If AttributeError persists:

- Verify that `compliance.py:49` does NOT have the line:
  ```python
  self._delete_existing_resource_and_dependencies()  # Should be removed!
  ```

## Expected Timeline

| Action | Timeline |
|--------|----------|
| Merge PR | ~5 minutes |
| Trigger onboarding | ~1 minute |
| Virtualenv rebuild | ~2-5 minutes (first time, includes package installation) |
| Script execution | Normal runtime |
| **Total** | **~10-15 minutes from merge to working instrumentation** |

## Success Criteria

- ✅ No AttributeError in compliance.py
- ✅ No "No module named 'opentelemetry'" errors
- ✅ `OTEL_AVAILABLE=True` in logs
- ✅ Telemetry data flowing to observability backend
- ✅ Job completes successfully

## Contact

If issues persist after onboarding:
1. Check BluePlanet scriptplan logs
2. Verify requirements_cst.txt was deployed correctly
3. Confirm virtualenv was actually recreated (check timestamps)
