# Fixing the `wrapt` Dependency Issue

## Current Error

```
ERROR: Could not find a version that satisfies the requirement wrapt<2.0.0,>=1.0.0 (from opentelemetry-instrumentation-urllib3) (from versions: none)
ERROR: No matching distribution found for wrapt<2.0.0,>=1.0.0
```

## Root Cause

`opentelemetry-instrumentation-urllib3==0.33b0` requires `wrapt<2.0.0,>=1.0.0`, but:

1. ✅ **Fixed in code**: `wrapt==1.17.3` has been added to `requirements_cst.txt`
2. ❌ **Missing in PYPI**: `wrapt` is not available in the PYPI server (`mdsocharter-pypi` or `charter-pypi`)

## Two-Part Solution

### Part 1: Code Fix (Already Done) ✅

The `requirements_cst.txt` file has been updated to include:
```txt
wrapt==1.17.3
```

**Status**: ✅ Committed and pushed to repository

### Part 2: PYPI Server Fix (Needs Action) ⚠️

`wrapt==1.17.3` needs to be added to the PYPI server.

**Action Required**: Add `wrapt==1.17.3` to the PYPI server's requirements file.

See `ADD_WRAPT_TO_PYPI.md` for detailed instructions.

## Quick Fix Steps

### Option A: Add `wrapt` to PYPI Server (Recommended)

1. Go to: https://git.blueplanet.com/Charter/charter-pypi/-/tree/develop
2. Edit `requirements-mkpypi-py3.txt`
3. Add line: `wrapt==1.17.3`
4. Commit and push to trigger PYPI build
5. Wait for build to complete
6. Retry MDSO job

### Option B: Verify File is Updated on MDSO Server

If the MDSO server hasn't pulled the latest code:

1. SSH into MDSO server
2. Navigate to the model-definitions directory
3. Pull latest code: `git pull`
4. Verify `requirements_cst.txt` has `wrapt==1.17.3`:
   ```bash
   grep wrapt requirements_cst.txt
   ```
5. Retry MDSO job

## Verification

After adding `wrapt` to PYPI, verify it's available:

```bash
# Check if wrapt is in PYPI
curl http://blueplanet/mdsocharter-pypi/simple/wrapt/
```

Should return HTML with package links.

## Why Both Steps Are Needed

1. **Code fix** (`requirements_cst.txt`): Tells pip what to install
2. **PYPI fix** (add to PYPI server): Makes the package available for pip to download

Both are required for the installation to succeed.

## Expected Result

After both fixes:
- ✅ `wrapt==1.17.3` is in `requirements_cst.txt` (done)
- ✅ `wrapt==1.17.3` is in PYPI server (needs action)
- ✅ pip can download and install `wrapt`
- ✅ `opentelemetry-instrumentation-urllib3` installs successfully

