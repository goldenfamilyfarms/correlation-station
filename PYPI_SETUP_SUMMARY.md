# OpenTelemetry PYPI Setup - Complete Summary

## What You Need to Do

### Step 1: Add Packages to PYPI Repository

1. Navigate to the PYPI repository (likely `mdsocharter-pypi`)
2. Open `./model-definitions/requirements_python38.txt`
3. Add all packages from `PYPI_PACKAGES_TO_ADD.txt` at the end of the file
4. **DO NOT** modify existing package versions
5. **DO NOT** add packages that already exist (check first!)

### Step 2: Handle Version Conflicts

Before adding, check if these packages already exist:
- `certifi` (may be 2021.10.8, new is 2025.4.26)
- `cffi` (already 1.15.1 - matches)
- `charset-normalizer` (may be 2.0.7, new is 2.0.12)
- `idna` (may be 2.10, new is 3.10) ⚠️ **Major version change**
- `pycparser` (already 2.21 - matches)
- `requests` (may be 2.26, new is 2.27.1)
- `typing-extensions` (may be 3.10.0.2, new is 4.1.1) ⚠️ **Major version change**
- `urllib3` (may be 1.26.7, new is 1.26.20)

**Action**: If they exist, test OpenTelemetry with existing versions first. Only update if OpenTelemetry requires the newer version.

### Step 3: Build PYPI Server

**Option A: Development Build (Recommended)**
1. Create a merge request from your branch
2. Manually trigger build in MR or GitLab Build > Pipelines
3. Deploys to: `artifactory.spectrumtoolbox.com/docker/solution-mdsocharterpypi`

**Option B: Manual Build**
```bash
# Update version.json with new version and gitlab_token
make pypi-image
make pypi-tag
make pypi-push
make pypi-solution-image
make pypi-solution-push
```

### Step 4: Update MDSO Solution Requirements

After PYPI is deployed, update your solution requirements files:

**Example: Update `requirements_cst.txt`**
```txt
--index-url http://blueplanet/vfirewall-templates-pypi/simple/
--extra-index-url http://blueplanet/mdsocharter-pypi/simple
--extra-index-url http://blueplanet/charter-pypi/simple/

# Existing packages
jsonpath
requests
plansdk
ipaddress

# OpenTelemetry (add these)
opentelemetry-api==1.12.0
opentelemetry-sdk==1.12.0
opentelemetry-exporter-otlp-proto-http==1.12.0
opentelemetry-semantic-conventions==0.33b0
structlog==21.5.0
opentelemetry-instrumentation-requests==0.33b0
opentelemetry-instrumentation-urllib3==0.33b0
pyroscope-io==0.8.14
```

See `requirements_cst_with_otel_updated.txt` for complete example.

## Package List (Copy-Paste Ready)

```
aiocontextvars==0.2.2
backoff==1.11.1
contextvars==2.4
dataclasses==0.8
deprecated==1.3.1
googleapis-common-protos==1.56.3
immutables==0.19
opentelemetry-api==1.12.0
opentelemetry-exporter-otlp-proto-http==1.12.0
opentelemetry-exporter-prometheus==0.33b0
opentelemetry-instrumentation==0.33b0
opentelemetry-instrumentation-requests==0.33b0
opentelemetry-instrumentation-urllib3==0.33b0
opentelemetry-proto==1.12.0
opentelemetry-sdk==1.12.0
opentelemetry-semantic-conventions==0.33b0
opentelemetry-util-http==0.33b0
prometheus-client==0.17.1
protobuf==3.19.6
pyroscope-io==0.8.14
structlog==21.5.0
wrapt==1.16.0
```

## Files Reference

- **`PYPI_PACKAGES_TO_ADD.txt`** - Exact list of packages with versions
- **`PYPI_SETUP_INSTRUCTIONS.md`** - Detailed step-by-step guide
- **`PYPI_QUICK_REFERENCE.md`** - Quick reference card
- **`parse_pip_compile.py`** - Script to parse pip-compile output
- **`requirements_cst_with_otel_updated.txt`** - Example updated requirements file

## Verification

After deployment, verify packages are available:

```bash
# In a Python environment with access to PYPI
python3 -c "import opentelemetry; print('✓ OpenTelemetry available')"
python3 -c "from opentelemetry import trace; print('✓ Trace module available')"
python3 -c "import structlog; print('✓ Structlog available')"
```

## Important Reminders

⚠️ **Never modify existing package versions** unless coordinated with the team  
⚠️ **Always lock versions** in solution requirements files  
⚠️ **Test thoroughly** before deploying to production  
⚠️ **Check for deprecated plansdk calls** that might conflict

## Troubleshooting

- **Build fails**: Check GitLab token expiration
- **Import errors**: Verify packages are in PYPI and index URLs are correct
- **Version conflicts**: Test with existing versions first, update only if necessary

