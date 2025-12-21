# Setting Up OpenTelemetry in MDSO PYPI Server

## Overview

This guide walks through adding OpenTelemetry packages to the MDSO PYPI server based on the pip-compile output you provided.

## Step 1: Locate the PYPI Repository

The `requirements_python38.txt` file is in the PYPI server repository, not in the MDSO solution repository. You'll need to:

1. Navigate to the PYPI repository (likely `mdsocharter-pypi` or similar)
2. Find `./model-definitions/requirements_python38.txt`

## Step 2: Add OpenTelemetry Packages

Open `requirements_python38.txt` and add the following packages at the **end** of the file:

### Core OpenTelemetry Packages (Add these)

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

## Step 3: Handle Existing Package Conflicts

Some packages from the pip-compile output may already exist in `requirements_python38.txt` with different versions. **DO NOT** modify existing versions unless you've coordinated with the team.

### Potentially Conflicting Packages:

| Package | Existing Version | New Version | Action |
|---------|-----------------|-------------|--------|
| `certifi` | 2021.10.8 | 2025.4.26 | **Check with team** - may need to update |
| `cffi` | 1.15.1 | 1.15.1 | ✅ Already matches |
| `charset-normalizer` | 2.0.7 | 2.0.12 | **Check with team** - minor update |
| `idna` | 2.10 | 3.10 | **Check with team** - major version change |
| `pycparser` | 2.21 | 2.21 | ✅ Already matches |
| `requests` | 2.26 | 2.27.1 | **Check with team** - patch update |
| `typing-extensions` | 3.10.0.2 | 4.1.1 | **Check with team** - major version change |
| `urllib3` | 1.26.7 | 1.26.20 | **Check with team** - patch update |

### Recommended Approach:

1. **For packages that already exist**: 
   - Check if OpenTelemetry will work with the existing version
   - If yes, keep the existing version (don't add the new one)
   - If no, coordinate with the team about updating

2. **For new packages**: 
   - Add them with the exact versions shown above

## Step 4: Build and Deploy PYPI Server

After adding the packages:

1. **For Development Build:**
   - Open a merge request from your branch
   - Manually trigger a build in the merge request or in GitLab's Build > Pipelines view
   - Once built, it will be deployed to `artifactory.spectrumtoolbox.com/docker/solution-mdsocharterpypi`

2. **For Manual Build** (if needed):
   ```bash
   # Update version.json with new version number and gitlab_token
   # Then run:
   make pypi-image
   make pypi-tag
   make pypi-push
   make pypi-solution-image
   make pypi-solution-push
   ```

## Step 5: Update MDSO Solution Requirements

After the PYPI server is built and deployed, update your MDSO solution requirements files:

### Option A: Add to Existing Requirements File

Add OpenTelemetry packages to an existing requirements file (e.g., `requirements_cst.txt`):

```txt
--index-url http://blueplanet/mdsocharter-pypi/simple
--extra-index-url http://blueplanet/charter-pypi/simple/
--extra-index-url http://blueplanet/openapi-pypi/simple/

# ... existing packages ...

# OpenTelemetry packages (after PYPI deployment)
opentelemetry-api==1.12.0
opentelemetry-sdk==1.12.0
opentelemetry-exporter-otlp-proto-http==1.12.0
opentelemetry-semantic-conventions==0.33b0
opentelemetry-instrumentation-requests==0.33b0
opentelemetry-instrumentation-urllib3==0.33b0
structlog==21.5.0
pyroscope-io==0.8.14
```

### Option B: Create New Requirements File

Create `requirements_otel.txt` and reference it in your TOML files:

```toml
[virtualenv]
python = "py38"
requirements = "requirements_otel.txt"
```

## Step 6: Verify Installation

After deployment, verify the packages are available:

```bash
# Test in a Python environment
python3 -c "import opentelemetry; print('OpenTelemetry available')"
python3 -c "from opentelemetry import trace; print('Trace module available')"
```

## Important Notes

⚠️ **Version Locking**: Always lock package versions in MDSO solution requirements files to prevent regressions when new packages are added to PYPI.

⚠️ **Backward Compatibility**: The instructions warn about deprecated calls in plansdk. Make sure OpenTelemetry packages don't conflict with existing plansdk dependencies.

⚠️ **Testing**: Test thoroughly in a development environment before deploying to production.

## Troubleshooting

- **Build fails**: Check if GitLab token is expired - get new token at: https://git.blueplanet.com/profile/personal_access_tokens
- **Import errors**: Verify packages are in PYPI and requirements file is updated
- **Version conflicts**: Use `pip freeze` to lock versions in your virtual environment

