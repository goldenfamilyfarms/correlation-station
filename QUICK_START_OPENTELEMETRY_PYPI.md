# Quick Start: Adding OpenTelemetry to MDSO PYPI

## TL;DR Steps

1. **Create requirements file for pip-compile** (already created: `requirements-opentelemetry-pypi.txt`)
2. **Run pip-compile** on a server with the target Python version
3. **Add compiled dependencies** to `charter-pypi` repository
4. **Update MDSO requirements files** to include OpenTelemetry packages
5. **Update TOML files** if needed

## Detailed Steps

### Step 1: Run pip-compile

On a server with Python 3.8 or 3.10 (matching your MDSO environment):

```bash
# Install pip-tools if not already installed
pip install pip-tools

# Compile requirements (this will resolve all dependencies)
pip-compile requirements-opentelemetry-pypi.txt
```

This creates `requirements-opentelemetry-pypi.txt` with all dependencies pinned.

### Step 2: Add to charter-pypi

1. Go to: https://git.blueplanet.com/Charter/charter-pypi/-/tree/develop
2. Edit `requirements-mkpypi-py3.txt` (for Python 3)
3. Add all packages from the compiled requirements file
4. Commit and push

### Step 3: Update MDSO Requirements

**Option A**: Add to existing `requirements_cst.txt`:

```txt
--index-url http://blueplanet/mdsocharter-pypi/simple
--extra-index-url http://blueplanet/charter-pypi/simple/
--extra-index-url http://blueplanet/openapi-pypi/simple/

# ... existing packages ...

# OpenTelemetry (after PYPI deployment)
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-http
opentelemetry-semantic-conventions
structlog
```

**Option B**: Use the new `requirements_otel.txt` file and update TOML:

```toml
[virtualenv]
python = "py38"
requirements = "requirements_otel.txt"
```

## Files Created

- ✅ `requirements-opentelemetry-pypi.txt` - For pip-compile (has index-url)
- ✅ `requirements_otel.txt` - For MDSO (after PYPI deployment)
- ✅ `ADD_OPENTELEMETRY_TO_PYPI.md` - Full documentation

## Next Steps

1. Run `pip-compile` on a server
2. Add compiled packages to charter-pypi
3. Wait for PYPI deployment
4. Update MDSO requirements files
5. Test with `python quick_otel_test.py`

