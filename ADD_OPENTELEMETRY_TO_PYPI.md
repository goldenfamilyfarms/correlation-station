# Adding OpenTelemetry to MDSO PYPI

This guide walks through adding OpenTelemetry packages to the MDSO PYPI repository.

## Step 1: Create Requirements File for PYPI

Create a requirements file with the index URL and OpenTelemetry packages:

```bash
# File: requirements-opentelemetry-pypi.txt
--index-url https://charter_deploy:YOUR_API_KEY_HERE@bphub.blueplanet.com

opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-http
opentelemetry-semantic-conventions
structlog
opentelemetry-instrumentation-requests
opentelemetry-instrumentation-urllib3
pyroscope-io
```

## Step 2: Run pip-compile

Run `pip-compile` on the requirements file. **Important**: Use the Python version that matches your MDSO environment (likely Python 3.8 or 3.10 based on the toml files).

```bash
# For Python 3.8
pip-compile requirements-opentelemetry-pypi.txt

# OR for Python 3.10
python3.10 -m pip install pip-tools
python3.10 -m pip_compile requirements-opentelemetry-pypi.txt
```

This will generate a compiled requirements file with all dependencies pinned.

## Step 3: Add to charter-pypi Repository

1. Navigate to: https://git.blueplanet.com/Charter/charter-pypi/-/tree/develop
2. Add the compiled dependencies to the appropriate requirements file:
   - For Python 3: `requirements-mkpypi-py3.txt`
   - For Python 2: `requirements-mkpypi.txt` (if still needed)

3. Add the OpenTelemetry packages and their dependencies from the pip-compile output.

## Step 4: Update MDSO Requirements Files

After the packages are added to PYPI and deployed, update your MDSO requirements files.

### Option A: Add to Existing Requirements File

Add OpenTelemetry packages to an existing requirements file (e.g., `requirements_cst.txt`):

```txt
--index-url http://blueplanet/mdsocharter-pypi/simple
--extra-index-url http://blueplanet/charter-pypi/simple/
--extra-index-url http://blueplanet/openapi-pypi/simple/

# ... existing packages ...

# OpenTelemetry instrumentation
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-http
opentelemetry-semantic-conventions
structlog
```

### Option B: Create New Requirements File

Create a new requirements file specifically for products using OpenTelemetry:

```txt
# File: requirements_otel.txt
--index-url http://blueplanet/mdsocharter-pypi/simple
--extra-index-url http://blueplanet/charter-pypi/simple/
--extra-index-url http://blueplanet/openapi-pypi/simple/

# OpenTelemetry packages
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-http
opentelemetry-semantic-conventions
structlog
opentelemetry-instrumentation-requests
opentelemetry-instrumentation-urllib3
pyroscope-io
```

## Step 5: Update TOML Files

Update the `.toml` files in `model-definitions/scripts.d/` to reference the requirements file.

### For products using OpenTelemetry:

```toml
[virtualenv]
python = "py38"  # or "py310" depending on your Python version
requirements = "requirements_otel.txt"  # or your existing requirements file
```

### Example: Update scripts.toml

```toml
[virtualenv]
python = "py310"
requirements = "requirements_cst.txt"  # Add opentelemetry packages to this file
```

## Required OpenTelemetry Packages

Based on the code analysis, these are the core packages needed:

### Core Packages (Required)
- `opentelemetry-api` - Core OpenTelemetry API
- `opentelemetry-sdk` - OpenTelemetry SDK implementation
- `opentelemetry-exporter-otlp-proto-http` - OTLP HTTP exporter
- `opentelemetry-semantic-conventions` - Semantic conventions

### Structured Logging (Required)
- `structlog` - Structured logging library

### Optional Packages
- `opentelemetry-instrumentation-requests` - Auto-instrumentation for requests
- `opentelemetry-instrumentation-urllib3` - Auto-instrumentation for urllib3
- `pyroscope-io` - Continuous profiling (optional)

## Version Recommendations

Based on the existing `otel/requirements.txt`:

```
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-http==1.20.0
opentelemetry-semantic-conventions==0.41b0
structlog==23.2.0
opentelemetry-instrumentation-requests==0.41b0
opentelemetry-instrumentation-urllib3==0.41b0
pyroscope-io>=0.8.7
```

**Note**: Let `pip-compile` determine the exact versions and dependencies when adding to PYPI.

## Verification

After adding to PYPI and updating requirements:

1. Test imports work:
   ```bash
   python quick_otel_test.py
   ```

2. Verify in a script:
   ```python
   from scripts.common_plan import CommonPlan, OTEL_AVAILABLE
   print(f"OTEL_AVAILABLE: {OTEL_AVAILABLE}")
   ```

## Troubleshooting

- **Import errors**: Ensure packages are in PYPI and requirements file is updated
- **Version conflicts**: Use `pip-compile` to resolve dependencies
- **Missing dependencies**: Check pip-compile output for transitive dependencies

