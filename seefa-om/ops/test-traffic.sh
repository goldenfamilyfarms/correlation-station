#!/bin/bash
#
# Test Traffic Generator for Observability PoC
# Generates traces, logs, and correlations for testing
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CORRELATION_ENGINE=${CORRELATION_ENGINE:-http://localhost:8080}
BEORN=${BEORN:-http://localhost:5001}
PALANTIR=${PALANTIR:-http://localhost:5002}
ARDA=${ARDA:-http://localhost:5003}

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Test Traffic Generator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to generate random trace ID (32 hex chars)
generate_trace_id() {
    echo $(openssl rand -hex 16)
}

# Function to generate random span ID (16 hex chars)
generate_span_id() {
    echo $(openssl rand -hex 8)
}

# Function to generate random circuit/product/resource IDs
generate_test_ids() {
    echo "CIRCUIT-$(openssl rand -hex 4)"
}

# ============================================
# Test 1: Simple Log Ingestion
# ============================================
echo -e "${YELLOW}Test 1: Simple Log Ingestion${NC}"
echo "Sending logs to correlation engine..."

TRACE_ID=$(generate_trace_id)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)

curl -s -X POST $CORRELATION_ENGINE/api/logs \
    -H "Content-Type: application/json" \
    -d "{
        \"resource\": {
            \"service\": \"test-script\",
            \"host\": \"localhost\",
            \"env\": \"dev\"
        },
        \"records\": [
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"INFO\",
                \"message\": \"Test log message 1\",
                \"trace_id\": \"$TRACE_ID\",
                \"labels\": {\"test\": \"true\"}
            },
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"WARN\",
                \"message\": \"Test warning message 2\",
                \"trace_id\": \"$TRACE_ID\",
                \"labels\": {\"test\": \"true\"}
            }
        ]
    }" > /dev/null

echo -e "${GREEN}✓ Sent 2 log records with trace_id: $TRACE_ID${NC}"
echo ""

# ============================================
# Test 2: Sense App Traces
# ============================================
echo -e "${YELLOW}Test 2: Sense App Traces${NC}"
echo "Generating traces from sense apps..."

# Call beorn
echo "  → Calling Beorn..."
CIRCUIT_ID=$(generate_test_ids)
PRODUCT_ID=$(generate_test_ids)
RESOURCE_ID=$(generate_test_ids)

BEORN_RESP=$(curl -s "$BEORN/api/test?circuit_id=$CIRCUIT_ID&product_id=$PRODUCT_ID&resource_id=$RESOURCE_ID")
echo -e "${GREEN}  ✓ Beorn responded${NC}"

# Call palantir
echo "  → Calling Palantir..."
PALANTIR_RESP=$(curl -s "$PALANTIR/api/test?circuit_id=$CIRCUIT_ID&product_id=$PRODUCT_ID")
echo -e "${GREEN}  ✓ Palantir responded${NC}"

# Call arda
echo "  → Calling Arda..."
ARDA_RESP=$(curl -s "$ARDA/api/test?circuit_id=$CIRCUIT_ID&product_id=$PRODUCT_ID&resource_id=$RESOURCE_ID")
echo -e "${GREEN}  ✓ Arda responded${NC}"
echo ""

# ============================================
# Test 3: Correlated Logs and Traces
# ============================================
echo -e "${YELLOW}Test 3: Correlated Logs and Traces${NC}"
echo "Creating correlated logs and traces..."

TRACE_ID=$(generate_trace_id)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
CIRCUIT_ID=$(generate_test_ids)
PRODUCT_ID="PROD-$(openssl rand -hex 3)"
RESOURCE_ID="RES-$(openssl rand -hex 3)"

# Send logs with trace context
curl -s -X POST $CORRELATION_ENGINE/api/logs \
    -H "Content-Type: application/json" \
    -d "{
        \"resource\": {
            \"service\": \"correlated-test\",
            \"host\": \"test-host\",
            \"env\": \"dev\"
        },
        \"records\": [
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"INFO\",
                \"message\": \"Starting operation for circuit $CIRCUIT_ID\",
                \"trace_id\": \"$TRACE_ID\",
                \"circuit_id\": \"$CIRCUIT_ID\",
                \"product_id\": \"$PRODUCT_ID\",
                \"resource_id\": \"$RESOURCE_ID\",
                \"request_id\": \"REQ-$(openssl rand -hex 4)\",
                \"labels\": {\"operation\": \"start\"}
            },
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"INFO\",
                \"message\": \"Operation completed successfully\",
                \"trace_id\": \"$TRACE_ID\",
                \"circuit_id\": \"$CIRCUIT_ID\",
                \"product_id\": \"$PRODUCT_ID\",
                \"resource_id\": \"$RESOURCE_ID\",
                \"labels\": {\"operation\": \"complete\", \"status\": \"success\"}
            }
        ]
    }" > /dev/null

echo -e "${GREEN}✓ Sent correlated logs with trace_id: $TRACE_ID${NC}"
echo -e "${GREEN}  Circuit ID: $CIRCUIT_ID${NC}"
echo -e "${GREEN}  Product ID: $PRODUCT_ID${NC}"
echo -e "${GREEN}  Resource ID: $RESOURCE_ID${NC}"
echo ""

# ============================================
# Test 4: High Volume Traffic
# ============================================
echo -e "${YELLOW}Test 4: High Volume Traffic${NC}"
echo "Generating high volume traffic (100 requests)..."

for i in {1..100}; do
    TRACE_ID=$(generate_trace_id)
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)

    curl -s -X POST $CORRELATION_ENGINE/api/logs \
        -H "Content-Type: application/json" \
        -d "{
            \"resource\": {
                \"service\": \"load-test\",
                \"host\": \"test-$i\",
                \"env\": \"dev\"
            },
            \"records\": [
                {
                    \"timestamp\": \"$TIMESTAMP\",
                    \"severity\": \"INFO\",
                    \"message\": \"High volume test message $i\",
                    \"trace_id\": \"$TRACE_ID\",
                    \"labels\": {\"batch\": \"$i\"}
                }
            ]
        }" > /dev/null &

    # Progress indicator
    if [ $((i % 10)) -eq 0 ]; then
        echo -n "."
    fi
done

# Wait for all background jobs
wait

echo ""
echo -e "${GREEN}✓ Sent 100 log batches${NC}"
echo ""

# ============================================
# Test 5: Error Scenarios
# ============================================
echo -e "${YELLOW}Test 5: Error Scenarios${NC}"
echo "Generating error logs..."

TRACE_ID=$(generate_trace_id)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)

curl -s -X POST $CORRELATION_ENGINE/api/logs \
    -H "Content-Type: application/json" \
    -d "{
        \"resource\": {
            \"service\": \"error-test\",
            \"host\": \"test-host\",
            \"env\": \"dev\"
        },
        \"records\": [
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"ERROR\",
                \"message\": \"Database connection failed\",
                \"trace_id\": \"$TRACE_ID\",
                \"labels\": {\"error_type\": \"connection\"}
            },
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"ERROR\",
                \"message\": \"Timeout waiting for response\",
                \"trace_id\": \"$TRACE_ID\",
                \"labels\": {\"error_type\": \"timeout\"}
            },
            {
                \"timestamp\": \"$TIMESTAMP\",
                \"severity\": \"CRITICAL\",
                \"message\": \"Service crashed unexpectedly\",
                \"trace_id\": \"$TRACE_ID\",
                \"labels\": {\"error_type\": \"crash\"}
            }
        ]
    }" > /dev/null

echo -e "${GREEN}✓ Sent error logs with trace_id: $TRACE_ID${NC}"
echo ""

# ============================================
# Verification
# ============================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Wait for correlation window to close
echo -e "${YELLOW}Waiting 65 seconds for correlation window to close...${NC}"
sleep 65

# Query recent correlations
echo -e "${YELLOW}Querying recent correlations...${NC}"
CORRELATIONS=$(curl -s "$CORRELATION_ENGINE/api/correlations?limit=10")
CORR_COUNT=$(echo $CORRELATIONS | jq '. | length')

echo -e "${GREEN}✓ Found $CORR_COUNT recent correlations${NC}"
echo ""

# Show correlation metrics
echo -e "${YELLOW}Correlation Engine Metrics:${NC}"
curl -s $CORRELATION_ENGINE/metrics | grep -E "^(correlation_events_total|log_records_received_total|export_attempts_total)" | head -10
echo ""

# ============================================
# Summary
# ============================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Test Traffic Generation Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open Grafana: http://159.56.4.94:3000"
echo "  2. View Correlation Dashboard"
echo "  3. Explore logs in Loki"
echo "  4. Search traces in Tempo"
echo "  5. Query metrics in Prometheus"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  make logs              - View all service logs"
echo "  make metrics           - Show correlation metrics"
echo "  make correlations      - Query correlations API"
echo "  make health            - Check service health"
echo ""