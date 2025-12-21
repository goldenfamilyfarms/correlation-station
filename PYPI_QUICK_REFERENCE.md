# Quick Reference: Adding OpenTelemetry to PYPI

## TL;DR

1. **Add these packages to `requirements_python38.txt`** in the PYPI repository:
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

2. **Check for existing packages** - Don't modify existing versions:
   - `certifi`, `cffi`, `charset-normalizer`, `idna`, `pycparser`, `requests`, `typing-extensions`, `urllib3`

3. **Build PYPI** - Create MR and trigger build pipeline

4. **Update MDSO requirements** - Add OpenTelemetry packages to solution requirements files

## Files Created

- ✅ `PYPI_PACKAGES_TO_ADD.txt` - Exact list of packages to add
- ✅ `PYPI_SETUP_INSTRUCTIONS.md` - Detailed step-by-step guide
- ✅ `parse_pip_compile.py` - Script to parse pip-compile output
- ✅ `requirements_cst_with_otel_updated.txt` - Example updated requirements file

## Key Packages (Directly Requested)

These are the packages you explicitly requested in `requirements_otel.txt`:

- `opentelemetry-api==1.12.0`
- `opentelemetry-sdk==1.12.0`
- `opentelemetry-exporter-otlp-proto-http==1.12.0`
- `opentelemetry-semantic-conventions==0.33b0`
- `opentelemetry-instrumentation-requests==0.33b0`
- `opentelemetry-instrumentation-urllib3==0.33b0`
- `structlog==21.5.0`
- `pyroscope-io==0.8.14`

All other packages are dependencies that will be automatically resolved.

## Version Conflicts to Watch

| Package | Existing | New | Risk |
|---------|----------|-----|------|
| `idna` | 2.10 | 3.10 | ⚠️ Major version change |
| `typing-extensions` | 3.10.0.2 | 4.1.1 | ⚠️ Major version change |
| `certifi` | 2021.10.8 | 2025.4.26 | ⚠️ Large version jump |
| `charset-normalizer` | 2.0.7 | 2.0.12 | ✅ Minor update |
| `requests` | 2.26 | 2.27.1 | ✅ Patch update |
| `urllib3` | 1.26.7 | 1.26.20 | ✅ Patch update |

**Action**: Test OpenTelemetry with existing versions first. Only update if necessary.

