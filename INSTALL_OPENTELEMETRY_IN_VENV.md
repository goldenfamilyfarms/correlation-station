# Installing OpenTelemetry in Virtual Environment

## Problem

OpenTelemetry packages are not being installed in your virtual environment because they're not listed in the requirements file.

## Solution

I've updated `requirements_cst.txt` to include OpenTelemetry packages. Now you need to reinstall the requirements.

## Steps to Install

### 1. Activate Your Virtual Environment

```bash
# Navigate to your vfirewallplan directory
cd /path/to/vfirewallplan

# Activate the virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 2. Install/Update Requirements

```bash
# Install the updated requirements
pip install -r requirements_cst.txt

# OR if you want to upgrade existing packages
pip install --upgrade -r requirements_cst.txt
```

### 3. Verify Installation

```bash
# Test that OpenTelemetry is installed
python -c "from opentelemetry import trace; print('OpenTelemetry installed!')"

# Check installed packages
pip list | grep opentelemetry
```

## What Was Changed

The `requirements_cst.txt` file was updated to include:

1. **Added extra index URLs** to access the PYPI servers:
   - `--extra-index-url http://blueplanet/mdsocharter-pypi/simple/`
   - `--extra-index-url http://blueplanet/charter-pypi/simple/`

2. **Added OpenTelemetry packages**:
   - `opentelemetry-api==1.12.0`
   - `opentelemetry-sdk==1.12.0`
   - `opentelemetry-exporter-otlp-proto-http==1.12.0`
   - `opentelemetry-semantic-conventions==0.33b0`
   - `structlog==21.5.0`
   - `opentelemetry-instrumentation-requests==0.33b0`
   - `opentelemetry-instrumentation-urllib3==0.33b0`
   - `pyroscope-io==0.8.14`

## Troubleshooting

### If installation fails with "Could not find a version":

1. **Check PYPI server access:**
   ```bash
   # Test if you can access the PYPI server
   curl http://blueplanet/mdsocharter-pypi/simple/
   ```

2. **Verify the PYPI build was successful:**
   - Check that the PYPI server was built and deployed
   - The build should have created: `artifactory.spectrumtoolbox.com/docker/solution-mdsocharterpypi:21.10.12.MR.18.b801e7b8`

3. **Check network connectivity:**
   - Ensure you can reach `blueplanet` from your environment
   - Check if you need VPN or special network access

### If you get version conflicts:

The requirements file pins specific versions. If you encounter conflicts:

1. Check what versions are already installed:
   ```bash
   pip list
   ```

2. You may need to uninstall conflicting packages first:
   ```bash
   pip uninstall opentelemetry-api opentelemetry-sdk
   pip install -r requirements_cst.txt
   ```

## After Installation

Once OpenTelemetry is installed, you can verify it works:

```python
# Test script
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

print("OpenTelemetry is working!")
```

## Next Steps

After installing OpenTelemetry:

1. Test your scripts to ensure they work with OpenTelemetry
2. Verify that `common_plan.py` can now use `create_root_span` without errors
3. Run your verification script: `python quick_otel_test.py`

