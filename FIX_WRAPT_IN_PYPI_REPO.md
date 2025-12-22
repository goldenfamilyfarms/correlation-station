# Fix: Add `wrapt` to PYPI Repository Requirements File

## Problem

Even though the PYPI Docker image was built and pushed, `wrapt==1.17.3` is still not available because it wasn't in the requirements file used to build the PYPI image.

## Solution: Add `wrapt` to PYPI Repository

### Step 1: Go to PYPI Repository

Navigate to: **https://git.blueplanet.com/Charter/charter-pypi/-/tree/develop**

### Step 2: Edit Requirements File

Edit the file: **`requirements-mkpypi-py3.txt`**

(Or check if there's a Python 3.10 specific file if your MDSO uses Python 3.10)

### Step 3: Add `wrapt==1.17.3`

Add this line to the requirements file:

```txt
wrapt==1.17.3
```

**Important**: Add it in the appropriate section (probably near other OpenTelemetry dependencies if they're grouped together).

### Step 4: Commit and Push

1. Commit the change
2. Push to trigger the CI/CD build
3. Wait for the build to complete (you'll see the same build output as before)

### Step 5: Deploy the New Image

After the build completes, deploy the new PYPI image:
- Image: `mdsocharter-pypi:21.10.12.MR.XX.<new-commit-hash>`

### Step 6: Verify `wrapt` is Available

After deployment, verify:

```bash
curl http://blueplanet/mdsocharter-pypi/simple/wrapt/
```

Should return HTML with links to `wrapt` packages.

## Why This is Needed

The PYPI Docker image is built from a requirements file in the PYPI repository. Packages need to be:
1. ✅ Listed in that requirements file (this step)
2. ✅ Built into the Docker image (happens automatically via CI/CD)
3. ✅ Deployed to the server (manual step)

## Current Status

- ✅ `wrapt==1.17.3` is in `requirements_cst.txt` (MDSO requirements)
- ❌ `wrapt==1.17.3` is NOT in PYPI repository requirements file
- ❌ PYPI image doesn't contain `wrapt` package
- ❌ MDSO can't install `wrapt` because it's not in PYPI server

## After Fix

- ✅ `wrapt==1.17.3` in PYPI repository requirements file
- ✅ PYPI image contains `wrapt` package
- ✅ MDSO can download and install `wrapt`
- ✅ OpenTelemetry installation succeeds

