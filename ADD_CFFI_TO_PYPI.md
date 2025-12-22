# Adding `cffi` Pre-built Wheels to PYPI Repository

## Why Add cffi to PYPI?

Adding pre-built wheels for `cffi` to your PYPI repository eliminates the need for Python development headers (`python3.10-dev`) on deployment servers.

**Benefits:**
- ✅ No need to install `python3.10-dev` on every server
- ✅ Faster pip installations (no compilation)
- ✅ More reliable deployments (no build failures)
- ✅ Smaller server footprint (no build tools needed)

## Option 1: Install python3.10-dev (Recommended)

**Easiest solution**: Install Python development headers on your servers:

```bash
sudo apt update
sudo apt install -y python3.10-dev
```

This allows `cffi` to compile from source and works for all future packages that need compilation.

See `CFFI_BUILD_ERROR_FIX.md` for complete instructions.

## Option 2: Add Pre-built Wheels to PYPI

If you cannot install system packages, add pre-built wheels to your PYPI repository.

### Step 1: Download Pre-built Wheels

Download the appropriate wheel for your platform:

```bash
# For Ubuntu 22.04 / Debian 11 with Python 3.10 (x86_64)
pip download --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --python-version 310 \
  --abi cp310 \
  cffi==1.15.1

# This downloads: cffi-1.15.1-cp310-cp310-manylinux2014_x86_64.whl
```

### Step 2: Add to charter-pypi Repository

1. Navigate to: https://git.blueplanet.com/Charter/charter-pypi/-/tree/develop

2. Upload the wheel file to the repository

3. Update `requirements-mkpypi-py3.txt`:
   ```txt
   # Add these lines:
   cffi==1.15.1
   pycparser==2.21  # Dependency of cffi
   ```

4. Commit and push to trigger PYPI build

### Step 3: Verify Wheel is Available

After the PYPI build completes:

```bash
# Check if wheel is available
curl http://blueplanet/mdsocharter-pypi/simple/cffi/

# Should show .whl file in the output
```

### Step 4: Test Installation

```bash
# Try installing - should use wheel (no compilation)
pip install --index-url http://blueplanet/mdsocharter-pypi/simple/ cffi==1.15.1

# Should complete in seconds without building
```

## Supported Platforms

You'll need wheels for each platform you deploy to:

### Linux (manylinux)
```bash
# Python 3.10 on x86_64
cffi-1.15.1-cp310-cp310-manylinux2014_x86_64.whl

# Python 3.11 on x86_64
cffi-1.15.1-cp311-cp311-manylinux2014_x86_64.whl
```

### To download all common wheels:

```bash
pip download --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --python-version 310 \
  cffi==1.15.1

pip download --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --python-version 311 \
  cffi==1.15.1
```

## Comparison: Source vs. Wheel

### Source Distribution (Current - Requires Compilation)

**File**: `cffi-1.15.1.tar.gz` (508 kB)

**Installation Process**:
1. Download source tarball
2. Extract files
3. Run `setup.py build` (requires gcc, Python.h)
4. Compile C extension
5. Install compiled extension

**Requirements**:
- gcc compiler
- python3.10-dev
- libffi-dev
- Time: ~30-60 seconds

**Error if missing**:
```
fatal error: Python.h: No such file or directory
```

### Pre-built Wheel (Proposed - No Compilation)

**File**: `cffi-1.15.1-cp310-cp310-manylinux2014_x86_64.whl`

**Installation Process**:
1. Download wheel
2. Extract files
3. Install (no compilation)

**Requirements**:
- None (just pip)
- Time: ~1-2 seconds

**Benefits**:
- No build errors
- Faster installation
- No system dependencies

## Dependencies of cffi

When adding `cffi` to PYPI, also ensure these are available:

```txt
# requirements-mkpypi-py3.txt
cffi==1.15.1
pycparser==2.21      # Required by cffi
```

## Verification After Adding to PYPI

```bash
# 1. Check package is in PYPI
curl http://blueplanet/mdsocharter-pypi/simple/cffi/

# 2. Install from PYPI
pip install --index-url http://blueplanet/mdsocharter-pypi/simple/ \
  --no-cache-dir cffi==1.15.1

# 3. Verify it works
python -c "import cffi; print(cffi.__version__)"

# 4. Install pyroscope-io (depends on cffi)
pip install --index-url http://blueplanet/mdsocharter-pypi/simple/ \
  pyroscope-io==0.8.14
```

## Which Approach to Use?

### Use Option 1 (Install python3.10-dev) if:
- ✅ You have sudo access to servers
- ✅ You want a permanent solution
- ✅ You may need to install other packages that require compilation
- ✅ You're okay with installing system packages

**Recommended for**: Most deployments, especially where you control the server environment.

### Use Option 2 (Add wheels to PYPI) if:
- ❌ You cannot install system packages
- ❌ You want minimal dependencies on servers
- ✅ You want faster, more reliable installations
- ✅ You have access to update the PYPI repository

**Recommended for**: Containerized deployments, restricted environments, or when you want maximum portability.

## Long-term Recommendation

**Best practice**: Do BOTH

1. **Add wheels to PYPI** - Provides fast, reliable installations
2. **Document system requirements** - Ensures fallback if wheels aren't available

This gives you:
- Fast installations (uses wheel if available)
- Fallback to source (compiles if wheel missing)
- Maximum compatibility

## Example: Complete PYPI Update

To add all packages needed for `requirements_cst.txt`:

```txt
# File: requirements-mkpypi-py3.txt (in charter-pypi repo)

# Add these packages:
cffi==1.15.1
pycparser==2.21
pyroscope-io==0.8.14
wrapt==1.17.3

# OpenTelemetry packages (if not already present)
opentelemetry-api==1.12.0
opentelemetry-sdk==1.12.0
opentelemetry-exporter-otlp-proto-http==1.12.0
opentelemetry-semantic-conventions==0.33b0
opentelemetry-instrumentation-requests==0.33b0
opentelemetry-instrumentation-urllib3==0.33b0
structlog==21.5.0
```

## Related Documentation

- `CFFI_BUILD_ERROR_FIX.md` - How to fix the build error with python3.10-dev
- `WRAPT_DEPENDENCY_FIX.md` - Similar fix for wrapt dependency
- `ADD_WRAPT_TO_PYPI.md` - Guide for adding wrapt to PYPI
- `ADD_OPENTELEMETRY_TO_PYPI.md` - Guide for adding all OpenTelemetry packages

## References

- cffi PyPI: https://pypi.org/project/cffi/
- cffi documentation: https://cffi.readthedocs.io/
- Python wheel format: https://pythonwheels.com/
