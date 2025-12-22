# Fixing the `cffi` Build Error

## Current Error

```
Building wheel for cffi (setup.py): finished with status 'error'
...
c/_cffi_backend.c:2:10: fatal error: Python.h: No such file or directory
    2 | #include <Python.h>
      |          ^~~~~~~~~~
compilation terminated.
error: command '/usr/bin/x86_64-linux-gnu-gcc' failed with exit code 1
ERROR: Failed building wheel for cffi
ERROR: Could not build wheels for cffi, which is required to install pyproject.toml-based projects
```

## Root Cause

`pyroscope-io==0.8.14` requires `cffi>=1.6.0`, which needs to be compiled from source. The compilation requires:

1. ❌ **Missing**: Python development headers (`Python.h`) - provided by `python3.10-dev` package
2. ✅ **Present**: C compiler (`gcc`) - already installed
3. ✅ **Present**: Source distribution - available in PYPI (`cffi-1.15.1.tar.gz`)

## Solution

Install Python development headers on the system where pip install is running.

### For Python 3.10 (Current MDSO Environment)

```bash
sudo apt update
sudo apt install -y python3.10-dev
```

### For Python 3.11 (Future Versions)

```bash
sudo apt update
sudo apt install -y python3.11-dev
```

### Complete Build Dependencies (Recommended)

For a complete Python build environment:

```bash
sudo apt update
sudo apt install -y \
  python3.10-dev \
  gcc \
  g++ \
  make \
  libffi-dev \
  libssl-dev \
  zlib1g-dev
```

## Quick Fix Command

Install the dev headers and retry the pip install in one command:

```bash
sudo apt update && sudo apt install -y python3.10-dev && \
/bp2/data/contexts/15/venv/bin/python3.10 -m pip --isolated \
  --disable-pip-version-check \
  --cache-dir /bp2/data/cache install \
  --pypi-url https://pypi.org/simple \
  -r /bp2/data/contexts/15/model-definitions/requirements_cst.txt \
  --trusted-host blueplanet \
  --cert /etc/ssl/certs/ca-certificates.crt
```

## Verification

After installing `python3.10-dev`, verify the installation:

```bash
# 1. Check Python.h is available
dpkg -L python3.10-dev | grep Python.h

# 2. Retry pip install
/bp2/data/contexts/15/venv/bin/python3.10 -m pip install cffi

# 3. Verify cffi installed
/bp2/data/contexts/15/venv/bin/python3.10 -c "import cffi; print(cffi.__version__)"

# 4. Verify pyroscope-io can be installed
/bp2/data/contexts/15/venv/bin/python3.10 -m pip install pyroscope-io==0.8.14
```

## Dependency Chain

```
requirements_cst.txt
  └── pyroscope-io==0.8.14
      └── cffi>=1.6.0  ← Requires compilation
          └── pycparser
```

## Why This Happens

The `cffi` package provides a C Foreign Function Interface for Python. When installed:

1. pip downloads the source distribution (`cffi-1.15.1.tar.gz`)
2. pip runs `setup.py` to build the native extension
3. The build process compiles C code that includes `<Python.h>`
4. **Build fails** if `Python.h` is not available

**Solution**: Install `python3.10-dev` to provide `Python.h`

## Alternative Solutions

### Option 1: Use Pre-built Wheels (If Available)

If your PYPI repository has pre-built wheels for `cffi`:

```bash
# Check if wheel is available
curl http://blueplanet/mdsocharter-pypi/simple/cffi/ | grep -i "\.whl"

# If wheel exists, pip will use it automatically (no compilation needed)
```

### Option 2: Make pyroscope-io Optional

If profiling is not critical:

```python
# In your code, make pyroscope import optional
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    PYROSCOPE_AVAILABLE = False

# Use only if available
if PYROSCOPE_AVAILABLE:
    # Configure pyroscope
    pass
```

And comment out in `requirements_cst.txt`:
```txt
# pyroscope-io==0.8.14  # Optional: continuous profiling
```

### Option 3: Upgrade pyroscope-io

Newer versions might have different dependencies:

```bash
# Check available versions
pip index versions pyroscope-io

# Try newer version (if compatible)
# Update requirements_cst.txt:
# pyroscope-io>=0.8.14
```

## For Docker/Container Deployments

If installing in a container, add to your `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements_cst.txt .
RUN pip install -r requirements_cst.txt
```

## For MDSO Server Deployments

Add to your server setup script or documentation:

```bash
# Install Python dev headers (one-time setup)
sudo apt update
sudo apt install -y python3.10-dev gcc g++ libffi-dev

# Verify installation
dpkg -l | grep python3.10-dev
```

## Prevention

### 1. Document in requirements file

Add to the top of `requirements_cst.txt`:

```txt
# System Requirements (install before pip install):
#
# Ubuntu/Debian:
#   sudo apt install -y python3.10-dev gcc g++ libffi-dev
#
# RHEL/CentOS:
#   sudo yum install -y python3-devel gcc gcc-c++ libffi-devel
```

### 2. Add to setup documentation

Update setup guides to include:

```markdown
## Prerequisites

Before running pip install, ensure development headers are installed:

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3.10-dev gcc g++ libffi-dev
```

### 3. Automate in setup scripts

Add to your environment setup script:

```bash
#!/bin/bash

# Check if python3.10-dev is installed
if ! dpkg -l | grep -q python3.10-dev; then
    echo "Installing python3.10-dev..."
    sudo apt update
    sudo apt install -y python3.10-dev gcc g++ libffi-dev
else
    echo "✓ python3.10-dev already installed"
fi
```

## Related Issues

This same error can occur with other packages that require compilation:

- `cryptography` - Requires `libssl-dev`
- `lxml` - Requires `libxml2-dev`, `libxslt-dev`
- `psycopg2` - Requires `libpq-dev`
- `mysqlclient` - Requires `libmysqlclient-dev`
- `Pillow` - Requires image library headers

**Solution for all**: Install the relevant `-dev` packages before running pip install.

## MDSO Environment Specifics

### Current Configuration

- **Python Version**: 3.10
- **Virtual Environment**: `/bp2/data/contexts/15/venv/`
- **Requirements File**: `/bp2/data/contexts/15/model-definitions/requirements_cst.txt`
- **PYPI Indexes**:
  - `http://blueplanet/vfirewall-templates-pypi/simple/`
  - `http://blueplanet/mdsocharter-pypi/simple/`
  - `http://blueplanet/charter-pypi/simple/`

### Installation Command Used

```bash
/bp2/data/contexts/15/venv/bin/python3.10 -m pip \
  --isolated \
  --disable-pip-version-check \
  --cache-dir /bp2/data/cache install \
  --pypi-url https://pypi.org/simple \
  -r /bp2/data/contexts/15/model-definitions/requirements_cst.txt \
  --trusted-host blueplanet \
  --cert /etc/ssl/certs/ca-certificates.crt
```

## Expected Result

After installing `python3.10-dev`:

- ✅ `cffi` compiles successfully
- ✅ `pyroscope-io==0.8.14` installs successfully
- ✅ All OpenTelemetry instrumentation packages install
- ✅ No build errors

## References

- cffi documentation: https://cffi.readthedocs.io/
- Python C API: https://docs.python.org/3/c-api/
- pyroscope-io: https://pyroscope.io/docs/python/
- Related fix: See `WRAPT_DEPENDENCY_FIX.md` for similar dependency resolution
