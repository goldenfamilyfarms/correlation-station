# End-to-End Test Suite for Sense OTel Instrumentation

**Blueprint Feature 1:** Comprehensive testing of OpenTelemetry instrumentation across Sense apps (ARDA, BEORN, PALANTIR) and the complete observability stack.

---

## Overview

This E2E test suite validates the complete telemetry pipeline:

```
Sense Apps (ARDA, BEORN, PALANTIR)
    ↓ (OpenTelemetry SDK)
Correlation Gateway
    ↓ (OTLP)
Correlation Engine
    ↓
Grafana Stack (Loki, Tempo, Prometheus)
```

---

## Prerequisites

### 1. Running Services

Ensure all services are running before executing tests:

```bash
# Check service health
curl http://localhost:8000/health  # ARDA
curl http://localhost:8001/health  # BEORN
curl http://localhost:8002/health  # PALANTIR
curl http://localhost:8080/health  # Correlation Engine
curl http://localhost:3100/ready   # Loki
curl http://localhost:3200/ready   # Tempo
curl http://localhost:9090/-/ready # Prometheus
```

### 2. Python Dependencies

Install test dependencies:

```bash
pip install pytest requests
```

---

## Running Tests

### Run All E2E Tests

```bash
# From repository root
pytest seefa-om/tests/e2e/test_sense_otel_e2e.py -v
```

### Run Specific Test Class

```bash
# Test ARDA instrumentation only
pytest seefa-om/tests/e2e/test_sense_otel_e2e.py::TestARDAOTelInstrumentation -v

# Test BEORN instrumentation only
pytest seefa-om/tests/e2e/test_sense_otel_e2e.py::TestBEORNOTelInstrumentation -v

# Test metrics cardinality
pytest seefa-om/tests/e2e/test_sense_otel_e2e.py::TestMetricsCardinality -v
```

### Run with Verbose Output

```bash
pytest seefa-om/tests/e2e/test_sense_otel_e2e.py -v -s
```

### Run as Standalone Script

```bash
python seefa-om/tests/e2e/test_sense_otel_e2e.py
```

---

## Test Cases

### 1. ARDA OTel Instrumentation

**Test:** `test_arda_circuit_creation_generates_trace`
- Triggers circuit creation via ARDA API
- Verifies trace appears in Tempo
- Validates trace attributes (circuit_id, service.name, etc.)
- Confirms span count and structure

**Test:** `test_arda_logs_correlated_with_traces`
- Queries Loki for ARDA logs
- Verifies logs contain trace_id for correlation
- Validates log-trace linkage

### 2. BEORN OTel Instrumentation

**Test:** `test_beorn_scriptplan_execution_generates_trace`
- Triggers MDSO scriptplan execution
- Verifies BEORN trace in Tempo
- Validates service.name = "beorn"

### 3. PALANTIR Metrics

**Test:** `test_palantir_request_metrics_recorded`
- Sends multiple requests to PALANTIR
- Queries Prometheus for sense_requests_total
- Validates metric existence and values

### 4. Metrics Cardinality Safety

**Test:** `test_request_counter_has_safe_cardinality`
- Checks all sense_requests_total metrics
- Ensures only safe labels are used (service_name, endpoint_group, product_type)
- Flags unsafe labels (circuit_id, user_id, session_id)

### 5. End-to-End Pipeline

**Test:** `test_full_pipeline_arda_to_grafana`
- Triggers ARDA operation with unique test ID
- Verifies telemetry in:
  - Tempo (traces)
  - Loki (logs)
  - Prometheus (metrics)
- Confirms complete pipeline functionality

---

## Configuration

### Endpoint Configuration

Edit `test_sense_otel_e2e.py` to adjust service endpoints:

```python
# Sense app endpoints
ARDA_URL = "http://localhost:8000"
BEORN_URL = "http://localhost:8001"
PALANTIR_URL = "http://localhost:8002"

# Correlation Engine/Gateway
CORRELATION_ENGINE_URL = "http://localhost:8080"
CORRELATION_GATEWAY_URL = "http://localhost:8081"

# Grafana stack endpoints
LOKI_URL = "http://localhost:3100"
TEMPO_URL = "http://localhost:3200"
PROMETHEUS_URL = "http://localhost:9090"
```

### Test Timeout

Adjust telemetry propagation wait time:

```python
TEST_TIMEOUT = 30  # seconds

def wait_for_telemetry(seconds: int = 10):
    """Wait for telemetry to propagate"""
    time.sleep(seconds)
```

---

## Expected Output

### Successful Test Run

```
===== VERIFYING SERVICES =====
✓ ARDA: http://localhost:8000 - UP
✓ BEORN: http://localhost:8001 - UP
✓ PALANTIR: http://localhost:8002 - UP
✓ Correlation Engine: http://localhost:8080 - UP
✓ Loki: http://localhost:3100 - UP
✓ Tempo: http://localhost:3200 - UP
✓ Prometheus: http://localhost:9090 - UP

===== TEST: ARDA Circuit Creation Trace =====
→ Creating circuit: TEST.CIRCUIT.1234567890..E2E
✓ Circuit created: 201
→ Searching Tempo for circuit_id=TEST.CIRCUIT.1234567890..E2E
✓ Found 1 trace(s) in Tempo
✓ Trace ID: abc123def456
✓ Trace contains 5 span(s)
  - Service: arda

===== TEST: Full E2E Telemetry Pipeline =====
→ Test ID: E2E.TEST.1234567890
→ Step 1: Triggering ARDA operation
  ✓ ARDA operation triggered
→ Step 2: Verifying trace in Tempo
  ✓ Trace found in Tempo: xyz789
→ Step 3: Verifying logs in Loki
  ✓ Logs found in Loki: 3 stream(s)
→ Step 4: Verifying metrics in Prometheus
  ✓ Metrics found in Prometheus: 8 series

✅ E2E PIPELINE TEST PASSED
Test ID: E2E.TEST.1234567890
Trace ID: xyz789
Logs: 3 streams
Metrics: 8 series

===== 5 passed in 45.23s =====
```

---

## Troubleshooting

### No traces found in Tempo

**Possible causes:**
- Telemetry propagation delay (increase `wait_for_telemetry()` duration)
- Correlation Gateway not forwarding to Correlation Engine
- Tempo not receiving spans from Correlation Engine

**Debug:**
```bash
# Check Correlation Gateway logs
docker logs correlation-gateway | grep "traces exported"

# Check Correlation Engine logs
docker logs correlation-engine | grep "trace_id"

# Query Tempo directly
curl http://localhost:3200/api/search?q='{.service.name="arda"}'
```

### No logs found in Loki

**Possible causes:**
- Logs not being sent to Loki
- LogQL query syntax error
- Loki label configuration mismatch

**Debug:**
```bash
# Check Loki for job labels
curl http://localhost:3100/loki/api/v1/labels

# Query all recent logs
curl 'http://localhost:3100/loki/api/v1/query_range?query={job=~".+"}'
```

### No metrics in Prometheus

**Possible causes:**
- Prometheus not scraping Sense apps
- Metrics endpoint not exposed
- Scrape interval not elapsed

**Debug:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query all sense metrics
curl 'http://localhost:9090/api/v1/query?query=sense_requests_total'
```

### Service health check failures

**Possible causes:**
- Service not running
- Port mismatch
- Network connectivity issues

**Debug:**
```bash
# Check running containers
docker ps | grep -E "arda|beorn|palantir|correlation"

# Check port bindings
netstat -tulpn | grep -E "8000|8001|8002|8080|3100|3200|9090"

# Test connectivity
curl -v http://localhost:8000/health
```

---

## CI/CD Integration

### GitLab CI

```yaml
test-e2e-otel:
  stage: test
  services:
    - docker:dind
  script:
    - docker-compose up -d
    - sleep 30  # Wait for services
    - pip install pytest requests
    - pytest seefa-om/tests/e2e/test_sense_otel_e2e.py -v
  after_script:
    - docker-compose logs
    - docker-compose down
```

### GitHub Actions

```yaml
- name: Run E2E Tests
  run: |
    docker-compose up -d
    sleep 30
    pip install pytest requests
    pytest seefa-om/tests/e2e/test_sense_otel_e2e.py -v
```

---

## Next Steps

1. ✅ Run E2E tests to validate Feature 1 implementation
2. Review test results and fix any failures
3. Add custom test cases for specific Sense app workflows
4. Integrate into CI/CD pipeline
5. Document findings in IMPLEMENTATION_STATUS.md
