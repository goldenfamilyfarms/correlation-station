# Fixing CFFI Build Error in MDSO Environment

## Problem

When running pip install with `requirements_cst.txt`, you may encounter this error:

```
Building wheel for cffi (setup.py): finished with status 'error'
...
c/_cffi_backend.c:2:10: fatal error: Python.h: No such file or directory
    2 | #include <Python.h>
      |          ^~~~~~~~~~
compilation terminated.
error: command '/usr/bin/x86_64-linux-gnu-gcc' failed with exit code 1
```

**Root Cause**: The `cffi` package (required by `pyroscope-io==0.8.14`) needs to be compiled from source, which requires Python development headers (`Python.h`). These headers are provided by the `python3-dev` or `python3.10-dev` system package.

## Solution Options

### Option 1: Install Python Development Headers (Recommended)

This is the standard solution and ensures all native extensions can be built.

#### For Python 3.10:
```bash
sudo apt update
sudo apt install -y python3.10-dev
```

#### For Python 3.11:
```bash
sudo apt update
sudo apt install -y python3.11-dev
```

#### Then retry the pip install:
```bash
/bp2/data/contexts/15/venv/bin/python3.10 -m pip install \
  -r /bp2/data/contexts/15/model-definitions/requirements_cst.txt
```

### Option 2: Use Pre-built Wheels

If you cannot install system packages, you can try to use pre-built wheels for `cffi`.

#### Add these packages to your PYPI repository:

1. Navigate to the charter-pypi repository
2. Add to `requirements-mkpypi-py3.txt`:
   ```
   cffi==1.15.1
   pycparser==2.21
   ```

3. Ensure the PYPI repository has pre-built wheels for cffi

#### Update the index URLs in requirements_cst.txt:

Make sure your requirements file includes the PYPI index that has the pre-built wheels:

```txt
--index-url http://blueplanet/vfirewall-templates-pypi/simple/
--extra-index-url http://blueplanet/mdsocharter-pypi/simple/
--extra-index-url http://blueplanet/charter-pypi/simple/
```

### Option 3: Upgrade to a Newer Version of pyroscope-io

The `pyroscope-io` package may have newer versions that use pre-built wheels or have different dependencies.

#### Check for newer versions:
```bash
pip index versions pyroscope-io
```

#### Update requirements_cst.txt:
```txt
# Instead of:
pyroscope-io==0.8.14

# Try:
pyroscope-io>=0.8.14
```

### Option 4: Make pyroscope-io Optional

If profiling is not critical for your use case, you can make `pyroscope-io` an optional dependency.

#### Update requirements_cst.txt:
```txt
# Comment out or remove:
# pyroscope-io==0.8.14
```

#### Update your code to handle missing pyroscope:
```python
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    PYROSCOPE_AVAILABLE = False

# Only use pyroscope if available
if PYROSCOPE_AVAILABLE:
    # Configure pyroscope
    pass
```

## Verification

After applying the fix, verify the installation:

```bash
# 1. Check cffi installed correctly
/bp2/data/contexts/15/venv/bin/python3.10 -c "import cffi; print(cffi.__version__)"

# 2. Check pyroscope-io installed correctly
/bp2/data/contexts/15/venv/bin/python3.10 -c "import pyroscope; print('pyroscope-io installed')"

# 3. List all installed packages
/bp2/data/contexts/15/venv/bin/python3.10 -m pip list
```

## Additional Information

### Why cffi Requires Python.h

The `cffi` (C Foreign Function Interface) package provides a way to call C code from Python. When installed, it needs to compile native C extensions, which require:

1. **Python.h** - Python's C API header files
2. **gcc** - C compiler (already installed in your environment)
3. **libffi-dev** - Foreign Function Interface library headers

### What Packages Depend on cffi

In your requirements:
```
pyroscope-io==0.8.14
  └── cffi>=1.6.0
      └── pycparser
```

### System Packages Required for Building Python Extensions

For a complete Python development environment on Ubuntu/Debian:

```bash
sudo apt install -y \
  python3.10-dev \
  python3-pip \
  gcc \
  g++ \
  make \
  libffi-dev \
  libssl-dev \
  zlib1g-dev
```

## MDSO Environment Specifics

### Virtual Environment Location
```
/bp2/data/contexts/15/venv/
```

### Python Version
```
Python 3.10
```

### Requirements File Location
```
/bp2/data/contexts/15/model-definitions/requirements_cst.txt
```

### PYPI Indexes Used
1. `http://blueplanet/vfirewall-templates-pypi/simple/` (has cffi-1.15.1.tar.gz)
2. `http://blueplanet/mdsocharter-pypi/simple/`
3. `http://blueplanet/charter-pypi/simple/`
4. `http://127.0.0.1/plansdk-pypi/simple/` (local)

## Recommended Solution

**For MDSO Production Environments:**

1. Install `python3.10-dev` on all MDSO servers (one-time setup)
2. Keep `pyroscope-io==0.8.14` in requirements as-is
3. Document the system requirement in deployment docs

**For MDSO Development Environments:**

1. Install `python3.10-dev` locally
2. Or use a Docker container with Python dev headers pre-installed

## Quick Fix Command

```bash
# Install Python dev headers and retry
sudo apt update && sudo apt install -y python3.10-dev && \
/bp2/data/contexts/15/venv/bin/python3.10 -m pip --isolated \
  --disable-pip-version-check \
  --cache-dir /bp2/data/cache install \
  --pypi-url https://pypi.org/simple \
  -r /bp2/data/contexts/15/model-definitions/requirements_cst.txt \
  --trusted-host blueplanet \
  --cert /etc/ssl/certs/ca-certificates.crt
```

## Prevention

To prevent this issue in new environments:

### 1. Update Dockerfile (if using containers):
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

### 2. Update setup scripts:
Add to your pre-setup or environment setup script:

```bash
# Install Python development headers
if ! dpkg -l | grep -q python3.10-dev; then
    echo "Installing python3.10-dev..."
    sudo apt update
    sudo apt install -y python3.10-dev
fi
```

### 3. Document in requirements:
Add to the top of `requirements_cst.txt`:

```txt
# System Requirements (install before pip install):
# - python3.10-dev (for cffi compilation)
# - gcc/g++ (for native extensions)
# - libffi-dev (for cffi)
#
# Install with: sudo apt install -y python3.10-dev gcc g++ libffi-dev
```

## Related Issues

- If you see similar errors for other packages (like `cryptography`, `lxml`, `psycopg2`), they also require dev headers
- The same solution (install `python3.10-dev`) will fix those issues too

## References

- cffi documentation: https://cffi.readthedocs.io/
- pyroscope-io: https://pyroscope.io/docs/python/
- Python C API: https://docs.python.org/3/c-api/
