# Testing Guide: OTel Gateway & Correlation Engine

## Quick Test Methods

### 1. Unit Tests (Correlation Engine)
```bash
cd correlation-engine
pytest tests/ -v
```

### 2. Send Test Telemetry
```bash
# From Meta server (159.56.4.94)
python3 scripts/send-test-span.py
```

### 3. Load Testing with k6
```bash
# Basic load test
k6 run k6/load-test-basic.js

# Log ingestion test
k6 run k6/load-test-logs.js
```

### 4. Manual API Testing
```bash
# Health check
curl http://159.56.4.94:8080/health

# Stats
curl http://159.56.4.94:8080/stats

# Metrics
curl http://159.56.4.94:9090/metrics
```

---

## Detailed Testing Scenarios

### Test 1: Gateway Receives OTLP Data

**Test the OTel Gateway is receiving data from Alloy:**

```bash
# On Meta server
sudo docker logs gateway --tail 100 -f

# Look for:
# - "LogsExporter" entries showing log ingestion
# - "TracesExporter" entries showing trace ingestion
# - No error messages
```

**Send test data:**
```bash
# From MDSO server
curl -X POST http://159.56.4.94:55681/v1/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resourceLogs": [{
      "resource": {
        "attributes": [
          {"key": "service.name", "value": {"stringValue": "test-service"}}
        ]
      },
      "scopeLogs": [{
        "logRecords": [{
          "timeUnixNano": "'$(date +%s)000000000'",
          "severityText": "INFO",
          "body": {"stringValue": "Test log from MDSO"}
        }]
      }]
    }]
  }'
```

**Expected Result:**
- Gateway logs show: `LogsExporter {"#logs": 1}`
- HTTP 200 response

---

### Test 2: Correlation Engine Logic

**Test correlation between logs and traces:**

```bash
# Run integration tests
cd correlation-engine
pytest tests/test_integration.py -v

# Specific correlation test
pytest tests/test_integration.py::TestEndToEndCorrelation::test_logs_and_traces_correlation -v
```

**Manual correlation test:**
```python
# Create test_correlation_manual.py
import requests
import time
import secrets

GATEWAY_URL = "http://159.56.4.94:55681"
trace_id = secrets.token_hex(16)

# 1. Send trace
trace_payload = {
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "test-app"}}
            ]
        },
        "scopeSpans": [{
            "spans": [{
                "traceId": trace_id,
                "spanId": secrets.token_hex(8),
                "name": "test-operation",
                "startTimeUnixNano": str(int(time.time() * 1e9)),
                "endTimeUnixNano": str(int(time.time() * 1e9) + 100000000)
            }]
        }]
    }]
}

response = requests.post(f"{GATEWAY_URL}/v1/traces", json=trace_payload)
print(f"Trace sent: {response.status_code}")

# 2. Send correlated log
log_payload = {
    "resourceLogs": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "test-app"}}
            ]
        },
        "scopeLogs": [{
            "logRecords": [{
                "timeUnixNano": str(int(time.time() * 1e9)),
                "severityText": "INFO",
                "body": {"stringValue": "Correlated test log"},
                "attributes": [
                    {"key": "trace_id", "value": {"stringValue": trace_id}}
                ],
                "traceId": trace_id,
                "spanId": secrets.token_hex(8)
            }]
        }]
    }]
}

response = requests.post(f"{GATEWAY_URL}/v1/logs", json=log_payload)
print(f"Log sent: {response.status_code}")
print(f"\nTrace ID: {trace_id}")
print(f"Search in Grafana Tempo for this trace_id")
```

**Run it:**
```bash
python3 test_correlation_manual.py
```

**Verify in Grafana:**
1. Go to http://159.56.4.94:8443
2. Navigate to Explore → Tempo
3. Search for the trace_id
4. Click on trace → should see correlated logs

---

### Test 3: MDSO Log Extraction

**Test Alloy regex extraction logic:**

```bash
cd mdso-alloy/test-samples

# Run validation script
bash validate-extractions.sh

# Test specific log file
alloy run --config ../config.alloy --dry-run < 01-circuit-creation.log
```

**Manual regex test:**
```bash
# Test a single log line
echo '2024-01-15 10:30:45 INFO [circuit:61.TGXX.000860..CHTR] Creating circuit on device austx-pe01.chtrse.com' | \
  grep -oP 'circuit:\K[^\]]+' 

# Expected: 61.TGXX.000860..CHTR
```

**Verify extraction in Loki:**
```bash
# Query Loki for extracted fields
curl -G http://159.56.4.94:3100/loki/api/v1/query \
  --data-urlencode 'query={service_name="mdso-dev"} | json | circuit_id != ""' \
  --data-urlencode 'limit=10'
```

---

### Test 4: End-to-End Pipeline

**Full pipeline test from MDSO → Meta → Grafana:**

```bash
# 1. Generate test log on MDSO
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO [circuit:99.TEST.999999..CHTR] [resource:RES-TEST-001] Test circuit creation on device test-pe01.chtrse.com [vendor:ciena] [service_type:ELAN]" | \
  sudo tee -a /var/log/ciena/test.log

# 2. Check Alloy processed it (on MDSO)
sudo docker logs alloy-mdso --tail 20

# 3. Check Gateway received it (on Meta)
sudo docker logs gateway --tail 20 | grep -i test

# 4. Query in Loki (on Meta)
curl -G http://159.56.4.94:3100/loki/api/v1/query \
  --data-urlencode 'query={service_name="mdso-dev"} |= "TEST.999999"' \
  --data-urlencode 'limit=1'

# 5. View in Grafana
# Navigate to: http://159.56.4.94:8443
# Explore → Loki → Query: {service_name="mdso-dev"} |= "TEST.999999"
```

---

### Test 5: Load Testing

**Test system under load:**

```bash
# Install k6 (if not installed)
# Windows: choco install k6
# Linux: sudo apt install k6

# Run basic load test
cd k6
k6 run load-test-basic.js

# Run log ingestion load test
k6 run load-test-logs.js

# Custom load test
k6 run -e BASE_URL=http://159.56.4.94:8080 \
       --vus 50 \
       --duration 5m \
       load-test-logs.js
```

**Monitor during load test:**
```bash
# Terminal 1: Gateway logs
sudo docker logs gateway -f

# Terminal 2: Correlation engine logs
sudo docker logs correlation-engine -f

# Terminal 3: System resources
watch -n 1 'docker stats --no-stream'
```

---

### Test 6: Correlation Engine API

**Test all API endpoints:**

```bash
# Health check
curl http://159.56.4.94:8080/health | jq

# Stats
curl http://159.56.4.94:8080/stats | jq

# Metrics (Prometheus format)
curl http://159.56.4.94:8080/metrics

# Query correlations
curl "http://159.56.4.94:8080/api/correlations?service=test-service&limit=10" | jq

# API docs
curl http://159.56.4.94:8080/docs
```

---

### Test 7: Error Scenarios

**Test error handling:**

```bash
# 1. Invalid OTLP payload
curl -X POST http://159.56.4.94:55681/v1/logs \
  -H "Content-Type: application/json" \
  -d '{"invalid": "payload"}'

# Expected: 400 Bad Request

# 2. Missing trace_id
curl -X POST http://159.56.4.94:55681/v1/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resourceLogs": [{
      "scopeLogs": [{
        "logRecords": [{
          "timeUnixNano": "'$(date +%s)000000000'",
          "body": {"stringValue": "Log without trace_id"}
        }]
      }]
    }]
  }'

# Expected: 200 (should still accept, just won't correlate)

# 3. Oversized payload
dd if=/dev/zero bs=1M count=10 | base64 | \
  curl -X POST http://159.56.4.94:55681/v1/logs \
       -H "Content-Type: application/json" \
       -d @-

# Expected: 413 Payload Too Large or timeout
```

---

### Test 8: Performance Benchmarks

**Measure throughput:**

```bash
# Create benchmark script
cat > benchmark.sh << 'EOF'
#!/bin/bash
ENDPOINT="http://159.56.4.94:55681/v1/logs"
COUNT=1000

echo "Sending $COUNT log batches..."
start=$(date +%s)

for i in $(seq 1 $COUNT); do
  curl -s -X POST $ENDPOINT \
    -H "Content-Type: application/json" \
    -d '{
      "resourceLogs": [{
        "scopeLogs": [{
          "logRecords": [{
            "timeUnixNano": "'$(date +%s)000000000'",
            "body": {"stringValue": "Benchmark log '$i'"}
          }]
        }]
      }]
    }' > /dev/null
done

end=$(date +%s)
duration=$((end - start))
rate=$((COUNT / duration))

echo "Completed in ${duration}s"
echo "Rate: ${rate} batches/sec"
EOF

chmod +x benchmark.sh
./benchmark.sh
```

---

## Automated Test Suite

**Run all tests:**

```bash
# Create comprehensive test script
cat > run_all_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Running All Tests ==="
echo

echo "1. Unit Tests..."
cd correlation-engine && pytest tests/ -v --tb=short
cd ..

echo
echo "2. Health Checks..."
curl -f http://159.56.4.94:8080/health || exit 1
curl -f http://159.56.4.94:55681/ || exit 1

echo
echo "3. Send Test Telemetry..."
python3 scripts/send-test-span.py

echo
echo "4. Load Test (light)..."
k6 run --vus 10 --duration 30s k6/load-test-basic.js

echo
echo "=== All Tests Passed ==="
EOF

chmod +x run_all_tests.sh
./run_all_tests.sh
```

---

## Troubleshooting Tests

### Gateway Not Receiving Data
```bash
# Check gateway is running
sudo docker ps | grep gateway

# Check gateway config
sudo docker exec gateway cat /etc/otel-collector-config.yaml

# Check network connectivity
curl -v http://159.56.4.94:55681/

# Check firewall
sudo netstat -tlnp | grep 55681
```

### Correlation Not Working
```bash
# Check correlation engine logs
sudo docker logs correlation-engine --tail 100

# Check Redis connection
sudo docker exec correlation-engine redis-cli -h redis ping

# Verify trace_id format (32 hex chars)
echo "abc123" | wc -c  # Should be 32
```

### Logs Not Appearing in Loki
```bash
# Check Loki is running
curl http://159.56.4.94:3100/ready

# Check Loki logs
sudo docker logs loki --tail 50

# Query all recent logs
curl -G http://159.56.4.94:3100/loki/api/v1/query \
  --data-urlencode 'query={service_name=~".+"}' \
  --data-urlencode 'limit=10'
```

---

## CI/CD Integration

**GitLab CI example:**

```yaml
test:
  stage: test
  script:
    - cd correlation-engine
    - pip install -r requirements.txt
    - pytest tests/ -v --junitxml=report.xml
  artifacts:
    reports:
      junit: correlation-engine/report.xml

integration-test:
  stage: test
  script:
    - python3 scripts/send-test-span.py
    - sleep 5
    - curl -f http://correlation-engine:8080/health
```

---

## Monitoring Test Results

**View in Grafana:**
1. Navigate to http://159.56.4.94:8443
2. Go to Dashboards → Correlation Engine
3. Check panels:
   - Request Rate
   - Error Rate
   - Latency (p95, p99)
   - Correlation Count

**Prometheus Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Latency p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```
