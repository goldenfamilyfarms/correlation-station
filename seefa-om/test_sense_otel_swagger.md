# Testing SENSE OTel Configuration via Swagger

## Prerequisites
1. SSH to server: `ssh p3128232@austx-mdso-logs-02.chtrse.com`
2. Ensure SENSE apps are running (arda, beorn, palantir)
3. Correlation engine is running

## Swagger Endpoints

### ARDA (Circuit Design)
- **URL**: `http://austx-mdso-logs-02.chtrse.com/arda/docs`
- **Test Endpoint**: `POST /api/v1/circuit/design`

### BEORN (Eligibility)
- **URL**: `http://austx-mdso-logs-02.chtrse.com/beorn/docs`
- **Test Endpoint**: `POST /api/v1/eligibility/check`

### PALANTIR (Device Compliance)
- **URL**: `http://austx-mdso-logs-02.chtrse.com/palantir/docs`
- **Test Endpoint**: `POST /api/v1/device/validate`

## Test Steps

### 1. Check SENSE App Status
```bash
cd /opt/correlation-station-test/seefa-om/seefa-om
sudo docker compose ps | grep -E "arda|beorn|palantir"
```

### 2. Check Correlation Engine Status
```bash
sudo docker compose ps correlation-engine
sudo docker compose logs -f correlation-engine
```

### 3. Test ARDA with OTel Headers

**Using curl:**
```bash
curl -X POST "http://austx-mdso-logs-02.chtrse.com/arda/api/v1/health" \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: 80.L1XX.005054..CHTR" \
  -H "X-Resource-Id: test-resource-123" \
  -v
```

**Expected Response Headers:**
- `X-Trace-Id`: OpenTelemetry trace ID
- `X-Request-Id`: Request correlation ID

### 4. Test BEORN with Circuit ID

```bash
curl -X POST "http://austx-mdso-logs-02.chtrse.com/beorn/api/v1/health" \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: 33.L1XX.801233..TWCC" \
  -H "X-Product-Id: FIA-12345" \
  -v
```

### 5. Test PALANTIR with Device Info

```bash
curl -X POST "http://austx-mdso-logs-02.chtrse.com/palantir/api/v1/health" \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: 44.L1YY.882190..ABC" \
  -H "X-Resource-Id: device-resource-456" \
  -v
```

## Verify Traces in Grafana

### 1. Open Grafana Tempo
```
http://austx-mdso-logs-02.chtrse.com/grafana/explore
```

### 2. Select Tempo Data Source

### 3. Query by Service Name
```traceql
{ .service.name = "arda" }
```

```traceql
{ .service.name = "beorn" }
```

```traceql
{ .service.name = "palantir" }
```

### 4. Query by Circuit ID
```traceql
{ .mdso.circuit_id = "80.L1XX.005054..CHTR" }
```

### 5. Query Recent Traces (Last 5 minutes)
```traceql
{ .service.name =~ "arda|beorn|palantir" && duration > 0ms }
```

## Verify Logs in Loki

### 1. Open Grafana Loki
```
http://austx-mdso-logs-02.chtrse.com/grafana/explore
```

### 2. Select Loki Data Source

### 3. Query ARDA Logs
```logql
{service_name="arda"} | json | circuit_id != ""
```

### 4. Query BEORN Logs
```logql
{service_name="beorn"} | json | level="INFO"
```

### 5. Query PALANTIR Logs
```logql
{service_name="palantir"} | json | resource_id != ""
```

### 6. Find Logs by Trace ID
```logql
{service_name=~"arda|beorn|palantir"} | json | trace_id="<TRACE_ID_FROM_TEMPO>"
```

## Verify Correlation Engine

### 1. Check Correlation Engine Logs
```bash
sudo docker compose logs -f correlation-engine | grep -E "circuit_id|trace_id"
```

### 2. Check Redis Keys
```bash
sudo docker compose exec redis redis-cli KEYS "circuit:*"
sudo docker compose exec redis redis-cli KEYS "trace:*"
```

### 3. Query Correlation API
```bash
curl "http://austx-mdso-logs-02.chtrse.com:8080/api/correlations?circuit_id=80.L1XX.005054..CHTR"
```

## Expected Results

### ✅ Successful OTel Configuration
1. **Response Headers**: Contains `X-Trace-Id` and `X-Request-Id`
2. **Tempo**: Traces appear with service name (arda/beorn/palantir)
3. **Loki**: Logs contain `trace_id` field matching Tempo traces
4. **Span Attributes**: 
   - `mdso.circuit_id`
   - `mdso.resource_id`
   - `mdso.product_id`
   - `sense.service`
5. **Correlation Engine**: Links logs and traces by trace_id

### ❌ Common Issues

**No traces in Tempo:**
- Check correlation-engine is running
- Verify OTLP endpoint: `http://austx-mdso-logs-02.chtrse.com:8080/api/otlp/v1/traces`
- Check SENSE app logs for OTel errors

**No X-Trace-Id header:**
- OTel not initialized in SENSE app
- Check `otel_sense.py` is imported in `main.py`

**Traces not correlated:**
- Check trace_id in logs matches Tempo
- Verify correlation-engine is processing spans

## Quick Test Script

Save as `test_otel.sh`:
```bash
#!/bin/bash

echo "Testing SENSE OTel Configuration..."
echo "===================================="

CIRCUIT_ID="80.L1XX.TEST.$(date +%s)..CHTR"

echo ""
echo "1. Testing ARDA..."
ARDA_RESPONSE=$(curl -s -i -X POST "http://austx-mdso-logs-02.chtrse.com/arda/api/v1/health" \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: $CIRCUIT_ID")

TRACE_ID=$(echo "$ARDA_RESPONSE" | grep -i "x-trace-id" | cut -d: -f2 | tr -d ' \r')

if [ -n "$TRACE_ID" ]; then
  echo "✅ ARDA Trace ID: $TRACE_ID"
else
  echo "❌ ARDA: No trace ID found"
fi

echo ""
echo "2. Testing BEORN..."
BEORN_RESPONSE=$(curl -s -i -X POST "http://austx-mdso-logs-02.chtrse.com/beorn/api/v1/health" \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: $CIRCUIT_ID")

BEORN_TRACE=$(echo "$BEORN_RESPONSE" | grep -i "x-trace-id" | cut -d: -f2 | tr -d ' \r')

if [ -n "$BEORN_TRACE" ]; then
  echo "✅ BEORN Trace ID: $BEORN_TRACE"
else
  echo "❌ BEORN: No trace ID found"
fi

echo ""
echo "3. Testing PALANTIR..."
PALANTIR_RESPONSE=$(curl -s -i -X POST "http://austx-mdso-logs-02.chtrse.com/palantir/api/v1/health" \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: $CIRCUIT_ID")

PALANTIR_TRACE=$(echo "$PALANTIR_RESPONSE" | grep -i "x-trace-id" | cut -d: -f2 | tr -d ' \r')

if [ -n "$PALANTIR_TRACE" ]; then
  echo "✅ PALANTIR Trace ID: $PALANTIR_TRACE"
else
  echo "❌ PALANTIR: No trace ID found"
fi

echo ""
echo "===================================="
echo "Test Circuit ID: $CIRCUIT_ID"
echo ""
echo "View traces in Grafana:"
echo "http://austx-mdso-logs-02.chtrse.com/grafana/explore"
echo ""
echo "TraceQL Query:"
echo "{ .mdso.circuit_id = \"$CIRCUIT_ID\" }"
```

**Run the test:**
```bash
chmod +x test_otel.sh
./test_otel.sh
```
