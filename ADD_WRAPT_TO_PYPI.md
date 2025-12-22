# Adding `wrapt` to MDSO PYPI Server

## Problem

`opentelemetry-instrumentation-urllib3==0.33b0` requires `wrapt<2.0.0,>=1.0.0`, but `wrapt` is not available in the PYPI server.

**Error**:
```
ERROR: Could not find a version that satisfies the requirement wrapt<2.0.0,>=1.0.0 (from opentelemetry-instrumentation-urllib3) (from versions: none)
```

## Solution: Add `wrapt==1.17.3` to PYPI Server

### Step 1: Add to PYPI Requirements File

1. Navigate to the PYPI repository: https://git.blueplanet.com/Charter/charter-pypi/-/tree/develop

2. Edit the appropriate requirements file:
   - For Python 3.8: `requirements-mkpypi-py3.txt`
   - For Python 3.10: Check if there's a separate file or use the same one

3. Add `wrapt==1.17.3` to the file:
   ```txt
   wrapt==1.17.3
   ```

### Step 2: Build and Deploy PYPI

Follow the same process you used for adding OpenTelemetry packages:

1. Update `version.json` with a new version number
2. Update `gitlab_token` if needed
3. Push the commit to trigger the CI/CD build
4. Wait for the build to complete

### Step 3: Verify `wrapt` is Available

After deployment, verify `wrapt` is in the PYPI server:

```bash
curl http://blueplanet/mdsocharter-pypi/simple/wrapt/
```

You should see HTML with links to `wrapt` packages.

## Alternative: Check if `wrapt` Already Exists

Before adding, check if `wrapt` might already be in the PYPI server under a different name or in a different index:

```bash
# Check mdsocharter-pypi
curl http://blueplanet/mdsocharter-pypi/simple/wrapt/

# Check charter-pypi
curl http://blueplanet/charter-pypi/simple/wrapt/
```

## Why This is Needed

From the PYPI build log, we can see that `wrapt-1.17.3` was downloaded during the build process, but it appears it wasn't added to the PYPI server's package list. The build process downloads packages, but they need to be explicitly listed in the requirements file to be included in the PYPI server.

## Quick Reference

**Package to add**: `wrapt==1.17.3`

**Why**: Required by `opentelemetry-instrumentation-urllib3==0.33b0`

**Constraint**: `wrapt<2.0.0,>=1.0.0` (version 1.17.3 satisfies this)

**File to edit**: `requirements-mkpypi-py3.txt` in charter-pypi repository

