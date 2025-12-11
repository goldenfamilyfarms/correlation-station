# SENSE Apps OpenTelemetry Integration Task

## Issue Summary
SENSE applications (ARDA, BEORN, PALANTIR) have OpenTelemetry packages installed and `otel_sense.py` configuration file present, but OTel is not being initialized at application startup, resulting in no trace generation.

## Current State

### ✅ What's Working
- OpenTelemetry packages installed in containers
- `otel_sense.py` exists with proper configuration at:
  - `/arda/arda_app/common/otel/otel_sense.py`
  - `/beorn/beorn_app/common/otel/` (assumed similar structure)
  - `/palantir/palantir_app/common/otel/` (assumed similar structure)
- Environment variables correctly set:
  - `OTEL_SERVICE_NAME` (arda/beorn/palantir)
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:4318`
  - `OTEL_DEPLOYMENT_ENV=dev`
  - `CORRELATION_API_URL=http://159.56.4.94:8080/ingest`
- Direct OTel imports work: `from opentelemetry import trace` succeeds

### ❌ What's Not Working
- Apps log: `"OTEL not available - running without instrumentation"`
- No `X-Trace-Id` headers in HTTP responses
- No traces appearing in Tempo
- `otel_sense.setup_otel_sense()` is never called at startup

## Root Cause
The `logging_setup.py` module checks for OTel availability but the actual initialization code (`setup_otel_sense()`) is not being called during application startup.

## Required Changes

### 1. ARDA (FastAPI) - `/arda/arda_app/main.py`

**Current Code** (from `arda_main.py`):
```python
# OpenTelemetry initialization
from common.telemetry import init_telemetry
import os

tracer = init_telemetry(
    service_name="arda",
    environment=os.getenv("DEPLOYMENT_ENV", "dev")
)
```

**Required Change**:
```python
# OpenTelemetry initialization
from arda_app.common.otel.otel_sense import setup_otel_sense, instrument_fastapi_lightweight
import os

# Initialize OTel
tracer = setup_otel_sense(
    service_name=os.getenv("OTEL_SERVICE_NAME", "arda"),
    service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
    environment=os.getenv("OTEL_DEPLOYMENT_ENV", "dev"),
    correlation_gateway=os.getenv("CORRELATION_API_URL", "http://159.56.4.94:8080")
)

# Create FastAPI app
app = FastAPI(...)

# Instrument FastAPI with lightweight middleware
instrument_fastapi_lightweight(app, "arda")
```

### 2. BEORN (Flask) - `/beorn/beorn_app/__init__.py`

**Required Change**:
```python
from flask import Flask
from beorn_app.common.otel.otel_sense import setup_otel_sense, instrument_flask_lightweight
import os

# Initialize OTel BEFORE creating Flask app
tracer = setup_otel_sense(
    service_name=os.getenv("OTEL_SERVICE_NAME", "beorn"),
    service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
    environment=os.getenv("OTEL_DEPLOYMENT_ENV", "dev"),
    correlation_gateway=os.getenv("CORRELATION_API_URL", "http://159.56.4.94:8080")
)

# Create Flask app
app = Flask(__name__)

# Instrument Flask with lightweight middleware
instrument_flask_lightweight(app, "beorn")
```

### 3. PALANTIR (Flask) - `/palantir/palantir_app/__init__.py`

**Required Change**:
```python
from flask import Flask
from palantir_app.common.otel.otel_sense import setup_otel_sense, instrument_flask_lightweight
import os

# Initialize OTel BEFORE creating Flask app
tracer = setup_otel_sense(
    service_name=os.getenv("OTEL_SERVICE_NAME", "palantir"),
    service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
    environment=os.getenv("OTEL_DEPLOYMENT_ENV", "dev"),
    correlation_gateway=os.getenv("CORRELATION_API_URL", "http://159.56.4.94:8080")
)

# Create Flask app
app = Flask(__name__)

# Instrument Flask with lightweight middleware
instrument_flask_lightweight(app, "palantir")
```

### 4. Update `logging_setup.py` (All Apps)

**Current Issue**: `logging_setup.py` has a try/except that catches import errors but doesn't provide details.

**Required Change**: Add better error handling and logging:
```python
try:
    from opentelemetry import trace
    from arda_app.common.otel.otel_sense import get_tracer
    OTEL_AVAILABLE = True
    logger.info("OTEL successfully imported and available")
except ImportError as e:
    OTEL_AVAILABLE = False
    logger.warning(f"OTEL not available - Import error: {e}")
except Exception as e:
    OTEL_AVAILABLE = False
    logger.error(f"OTEL initialization failed: {e}", exc_info=True)
```

## Testing Steps

### 1. Rebuild Containers
```bash
cd /opt/correlation-station-test/seefa-om/seefa-om
sudo docker compose build arda beorn palantir
sudo docker compose up -d arda beorn palantir
```

### 2. Check Logs for OTel Initialization
```bash
# Should see "OTEL initialized: arda v1.0.0 -> http://159.56.4.94:8080 (dev)"
sudo docker compose logs arda | grep -i "otel"
sudo docker compose logs beorn | grep -i "otel"
sudo docker compose logs palantir | grep -i "otel"
```

### 3. Test Trace Generation
```bash
# Test ARDA
curl -v "http://austx-mdso-logs-02.chtrse.com/arda/" \
  -H "X-Circuit-Id: 80.L1XX.TEST.001..CHTR" 2>&1 | grep "x-trace-id"

# Test BEORN
curl -v "http://austx-mdso-logs-02.chtrse.com/beorn/" \
  -H "X-Circuit-Id: 33.L1XX.TEST.002..TWCC" 2>&1 | grep "x-trace-id"

# Test PALANTIR
curl -v "http://austx-mdso-logs-02.chtrse.com/palantir/" \
  -H "X-Circuit-Id: 44.L1YY.TEST.003..ABC" 2>&1 | grep "x-trace-id"
```

### 4. Verify Traces in Tempo
```
http://austx-mdso-logs-02.chtrse.com/grafana/explore
```

**TraceQL Query**:
```traceql
{ .service.name =~ "arda|beorn|palantir" }
```

### 5. Verify Span Attributes
Traces should contain:
- `mdso.circuit_id`
- `mdso.resource_id`
- `sense.service`
- `request.id`
- `service.name`
- `service.version`
- `deployment.environment`

## Expected Results

### ✅ Success Criteria
1. No "OTEL not available" warnings in logs
2. Log message: `"OTEL initialized: {service} v{version} -> {gateway} ({env})"`
3. HTTP responses contain `X-Trace-Id` header
4. Traces appear in Tempo with service name
5. Spans contain MDSO correlation attributes
6. Logs contain `trace_id` field matching Tempo traces

### 📊 Performance Impact
The lightweight instrumentation should have minimal overhead:
- Batch span export every 5 seconds
- Max queue size: 1024 spans
- Max batch size: 256 spans
- No heavy middleware (optimized for production)

## Additional Notes

### Port Conflict (ARDA)
ARDA container fails to start due to port 5001 conflict with "agent" process (PID 878).

**Resolution Options**:
1. Kill the agent process: `sudo kill 878`
2. Change ARDA port in docker-compose.yml: `5005:5001`
3. Investigate what "agent" is and if it's needed

### Correlation Gateway Endpoint
The correlation gateway expects traces at:
```
POST http://159.56.4.94:8080/api/otlp/v1/traces
```

Verify this endpoint is accessible from SENSE containers:
```bash
sudo docker exec arda curl -v http://159.56.4.94:8080/health
```

### Environment Variables
All required env vars are already set in docker-compose.yml:
- `OTEL_SERVICE_NAME`
- `OTEL_SERVICE_VERSION`
- `OTEL_DEPLOYMENT_ENV`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `CORRELATION_API_URL`

## Files to Modify

1. `sense-apps/arda/arda_app/main.py` or `arda_app/common/otel/instrumentation/arda_main.py`
2. `sense-apps/beorn/beorn_app/__init__.py`
3. `sense-apps/palantir/palantir_app/__init__.py`
4. `sense-apps/arda/arda_app/common/logging_setup.py`
5. `sense-apps/beorn/beorn_app/common/logging_setup.py`
6. `sense-apps/palantir/palantir_app/common/logging_setup.py`

## Priority
**HIGH** - Required for observability and correlation features to work

## Estimated Effort
- Code changes: 2-3 hours
- Testing: 1-2 hours
- Documentation: 30 minutes

## Dependencies
- OpenTelemetry packages (already installed)
- `otel_sense.py` module (already exists)
- Correlation gateway running (already running)
- Tempo/Loki/Grafana stack (already running)

## Related Documentation
- Tutorial: `frontend/src/pages/TutorialsPageNew.tsx` (SENSE Instrumentation section)
- OTel Config: `sense-apps/*/common/otel/otel_sense.py`
- Test Guide: `test_sense_otel_swagger.md`
