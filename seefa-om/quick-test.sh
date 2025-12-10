#!/bin/bash
# Quick Test Script for OTel Gateway & Correlation Engine
# Run this on Meta server (159.56.4.94)

set -e

GATEWAY_URL="http://localhost:55681"
CORRELATION_URL="http://localhost:8080"
LOKI_URL="http://localhost:3100"

echo "=========================================="
echo "Quick Test: OTel Gateway & Correlation Engine"
echo "=========================================="
echo

# Test 1: Health Checks
echo "1. Health Checks..."
echo -n "  Gateway: "
curl -sf ${GATEWAY_URL}/ > /dev/null && echo "✓ OK" || echo "✗ FAILED"

echo -n "  Correlation Engine: "
curl -sf ${CORRELATION_URL}/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"

echo -n "  Loki: "
curl -sf ${LOKI_URL}/ready > /dev/null && echo "✓ OK" || echo "✗ FAILED"
echo

# Test 2: Send Test Log
echo "2. Sending test log to Gateway..."
TRACE_ID=$(openssl rand -hex 16)
TIMESTAMP=$(date +%s)000000000

LOG_PAYLOAD=$(cat <<EOF
{
  "resourceLogs": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "quick-test"}}
      ]
    },
    "scopeLogs": [{
      "logRecords": [{
        "timeUnixNano": "${TIMESTAMP}",
        "severityText": "INFO",
        "body": {"stringValue": "Quick test log message"},
        "attributes": [
          {"key": "trace_id", "value": {"stringValue": "${TRACE_ID}"}},
          {"key": "test.type", "value": {"stringValue": "automated"}}
        ],
        "traceId": "${TRACE_ID}"
      }]
    }]
  }]
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${GATEWAY_URL}/v1/logs \
  -H "Content-Type: application/json" \
  -d "${LOG_PAYLOAD}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "  ✓ Log sent successfully (HTTP 200)"
else
  echo "  ✗ Failed to send log (HTTP $HTTP_CODE)"
  exit 1
fi
echo

# Test 3: Send Test Trace
echo "3. Sending test trace to Gateway..."
SPAN_ID=$(openssl rand -hex 8)
START_TIME=$((TIMESTAMP - 50000000))

TRACE_PAYLOAD=$(cat <<EOF
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "quick-test"}}
      ]
    },
    "scopeSpans": [{
      "spans": [{
        "traceId": "${TRACE_ID}",
        "spanId": "${SPAN_ID}",
        "name": "quick-test-operation",
        "kind": 1,
        "startTimeUnixNano": "${START_TIME}",
        "endTimeUnixNano": "${TIMESTAMP}",
        "attributes": [
          {"key": "test.type", "value": {"stringValue": "automated"}}
        ]
      }]
    }]
  }]
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${GATEWAY_URL}/v1/traces \
  -H "Content-Type: application/json" \
  -d "${TRACE_PAYLOAD}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
  echo "  ✓ Trace sent successfully (HTTP 200)"
else
  echo "  ✗ Failed to send trace (HTTP $HTTP_CODE)"
  exit 1
fi
echo

# Test 4: Verify in Loki
echo "4. Verifying log in Loki (waiting 3s for ingestion)..."
sleep 3

LOKI_QUERY='{service_name="quick-test"}'
LOKI_RESPONSE=$(curl -s -G ${LOKI_URL}/loki/api/v1/query \
  --data-urlencode "query=${LOKI_QUERY}" \
  --data-urlencode "limit=1")

LOG_COUNT=$(echo "$LOKI_RESPONSE" | jq -r '.data.result | length')
if [ "$LOG_COUNT" -gt 0 ]; then
  echo "  ✓ Log found in Loki"
else
  echo "  ✗ Log not found in Loki"
  echo "  Response: $LOKI_RESPONSE"
fi
echo

# Test 5: Check Correlation Engine Stats
echo "5. Checking Correlation Engine stats..."
STATS=$(curl -s ${CORRELATION_URL}/stats)
echo "$STATS" | jq '.'
echo

# Test 6: Check Gateway Logs
echo "6. Recent Gateway logs:"
sudo docker logs gateway --tail 5 2>&1 | grep -E "(LogsExporter|TracesExporter)" || echo "  No recent exports"
echo

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Trace ID: ${TRACE_ID}"
echo
echo "View in Grafana:"
echo "  Logs:   http://austx-mdso-logs-02.chtrse.com/grafana//explore?left=%7B%22queries%22:%5B%7B%22expr%22:%22%7Bservice_name%3D%5C%22quick-test%5C%22%7D%22%7D%5D%7D"
echo "  Traces: http://austx-mdso-logs-02.chtrse.com/grafana//explore?left=%7B%22queries%22:%5B%7B%22query%22:%22${TRACE_ID}%22%7D%5D%7D"
echo
echo "✓ Quick test completed successfully!"
