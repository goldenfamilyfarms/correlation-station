#!/bin/bash
# Comprehensive Alloy Deployment Verification Script
# Tests if Alloy is deployed, running, and sending data to correlation engine

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MDSO_DEV_HOST="159.56.4.37"
META_SERVER="159.56.4.94"
CORRELATION_ENGINE_PORT="8080"
OTEL_GATEWAY_PORT="55681"
OTEL_METRICS_PORT="8888"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Alloy Deployment Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
    else
        echo -e "${RED}✗${NC} $message"
    fi
}

# ========================================
# 1. Check Alloy Container on MDSO Dev
# ========================================
echo -e "\n${BLUE}[1/6] Checking Alloy Container${NC}"
echo "Target: $MDSO_DEV_HOST"

# Note: This script assumes it's run from the Meta server
# For local testing, skip the SSH checks
if command -v docker &> /dev/null; then
    # Running locally with Docker
    if docker ps | grep -q "alloy"; then
        ALLOY_CONTAINER=$(docker ps --filter "name=alloy" --format "{{.Names}}" | head -1)
        print_status "OK" "Alloy container running: $ALLOY_CONTAINER"

        # Check Alloy version
        ALLOY_VERSION=$(docker exec $ALLOY_CONTAINER /bin/alloy --version 2>&1 | head -1 || echo "unknown")
        echo "  Version: $ALLOY_VERSION"

        # Check Alloy config
        echo "  Config loaded: checking..."
        docker exec $ALLOY_CONTAINER /bin/alloy fmt /etc/alloy/config.alloy > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            print_status "OK" "Configuration syntax valid"
        else
            print_status "FAIL" "Configuration syntax invalid"
        fi

        # Check if reading log files
        echo ""
        echo -e "${BLUE}  Checking log file access:${NC}"
        LOG_FILES_FOUND=$(docker exec $ALLOY_CONTAINER ls -l /var/log/ciena/*.log 2>/dev/null | wc -l || echo "0")
        if [ "$LOG_FILES_FOUND" -gt 0 ]; then
            print_status "OK" "Found $LOG_FILES_FOUND log file(s) in /var/log/ciena/"
            docker exec $ALLOY_CONTAINER ls -lh /var/log/ciena/*.log | head -3
        else
            print_status "WARN" "No log files found in /var/log/ciena/"
        fi

        BP2_LOG_FILES=$(docker exec $ALLOY_CONTAINER ls -l /bp2/log/*.log 2>/dev/null | wc -l || echo "0")
        if [ "$BP2_LOG_FILES" -gt 0 ]; then
            print_status "OK" "Found $BP2_LOG_FILES log file(s) in /bp2/log/"
        else
            print_status "WARN" "No log files found in /bp2/log/"
        fi
    else
        print_status "FAIL" "Alloy container not running"
        echo "  Run: ./deploy-container.sh or docker-compose up -d"
    fi
else
    print_status "WARN" "Docker not available (test from MDSO Dev or Meta server)"
fi

# ========================================
# 2. Check OTel Gateway on Meta
# ========================================
echo -e "\n${BLUE}[2/6] Checking OTel Gateway${NC}"
echo "Target: $META_SERVER:$OTEL_GATEWAY_PORT"

# Test if OTel Gateway is reachable
if timeout 3 bash -c "cat < /dev/null > /dev/tcp/$META_SERVER/$OTEL_GATEWAY_PORT" 2>/dev/null; then
    print_status "OK" "OTel Gateway port $OTEL_GATEWAY_PORT is open"
else
    print_status "FAIL" "Cannot connect to OTel Gateway on $META_SERVER:$OTEL_GATEWAY_PORT"
fi

# Check OTel Gateway metrics (if accessible)
if curl -sf "http://$META_SERVER:$OTEL_METRICS_PORT/metrics" > /dev/null 2>&1; then
    print_status "OK" "OTel Gateway metrics endpoint accessible"

    # Get log reception metrics
    LOGS_RECEIVED=$(curl -s "http://$META_SERVER:$OTEL_METRICS_PORT/metrics" | grep "otelcol_receiver_accepted_log_records" | grep -v "#" | tail -1 | awk '{print $2}')
    if [ -n "$LOGS_RECEIVED" ] && [ "$LOGS_RECEIVED" != "0" ]; then
        print_status "OK" "Log records received: $LOGS_RECEIVED"
    else
        print_status "WARN" "No log records received yet (or metrics not available)"
    fi
else
    print_status "WARN" "Cannot access OTel Gateway metrics endpoint"
fi

# ========================================
# 3. Check Correlation Engine
# ========================================
echo -e "\n${BLUE}[3/6] Checking Correlation Engine${NC}"
echo "Target: $META_SERVER:$CORRELATION_ENGINE_PORT"

# Test correlation engine health
if curl -sf "http://$META_SERVER:$CORRELATION_ENGINE_PORT/health" > /dev/null 2>&1; then
    HEALTH_STATUS=$(curl -s "http://$META_SERVER:$CORRELATION_ENGINE_PORT/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_status "OK" "Correlation Engine is healthy"
    else
        print_status "WARN" "Correlation Engine status: $HEALTH_STATUS"
    fi

    # Check if receiving logs
    LOG_COUNT=$(curl -s "http://$META_SERVER:$CORRELATION_ENGINE_PORT/metrics" | grep "log_records_received_total" | grep -v "#" | tail -1 | awk '{print $2}' || echo "0")
    TRACE_COUNT=$(curl -s "http://$META_SERVER:$CORRELATION_ENGINE_PORT/metrics" | grep "traces_received_total" | grep -v "#" | tail -1 | awk '{print $2}' || echo "0")

    if [ -n "$LOG_COUNT" ] && [ "$LOG_COUNT" != "0" ]; then
        print_status "OK" "Logs received: $LOG_COUNT"
    else
        print_status "WARN" "No logs received by correlation engine"
    fi

    if [ -n "$TRACE_COUNT" ] && [ "$TRACE_COUNT" != "0" ]; then
        print_status "OK" "Traces received: $TRACE_COUNT"
    else
        print_status "WARN" "No traces received (expected if only MDSO logs flowing)"
    fi
else
    print_status "FAIL" "Cannot connect to Correlation Engine on $META_SERVER:$CORRELATION_ENGINE_PORT"
fi

# ========================================
# 4. Test Field Extraction
# ========================================
echo -e "\n${BLUE}[4/6] Testing Field Extraction${NC}"

# Create a test log entry with known patterns
TEST_LOG_ENTRY="Nov 16 10:30:00 mdso-host: Creating circuit: 80.L1XX.005054..CHTR for device JFVLINBJ2CW.CHTRSE.COM (vendor: juniper) resource: 550e8400-e29b-41d4-a716-446655440000 service type: ELAN"

echo "Test log entry:"
echo "  $TEST_LOG_ENTRY"
echo ""
echo "Expected extractions:"
echo "  • circuit_id: 80.L1XX.005054..CHTR"
echo "  • device_fqdn: JFVLINBJ2CW.CHTRSE.COM"
echo "  • device_tid: JFVLINBJ2CW"
echo "  • vendor: juniper"
echo "  • resource_id: 550e8400-e29b-41d4-a716-446655440000"
echo "  • service_type: ELAN"
echo ""

# If Alloy is running locally, we can test the regex patterns
if command -v docker &> /dev/null && docker ps | grep -q "alloy"; then
    ALLOY_CONTAINER=$(docker ps --filter "name=alloy" --format "{{.Names}}" | head -1)

    # Verify config has extraction stages
    EXTRACTION_STAGES=$(docker exec $ALLOY_CONTAINER cat /etc/alloy/config.alloy | grep -c "stage.regex" || echo "0")
    if [ "$EXTRACTION_STAGES" -gt 10 ]; then
        print_status "OK" "Found $EXTRACTION_STAGES regex extraction stages in config"
    else
        print_status "WARN" "Only found $EXTRACTION_STAGES extraction stages (expected ~16)"
    fi
else
    print_status "WARN" "Cannot test extraction locally (run from MDSO Dev with Alloy container)"
fi

# ========================================
# 5. Check Recent Log Activity
# ========================================
echo -e "\n${BLUE}[5/6] Checking Recent Log Activity${NC}"

if command -v docker &> /dev/null && docker ps | grep -q "alloy"; then
    ALLOY_CONTAINER=$(docker ps --filter "name=alloy" --format "{{.Names}}" | head -1)

    echo "Recent Alloy logs (last 20 lines):"
    docker logs --tail 20 $ALLOY_CONTAINER 2>&1 | grep -E "(error|warn|component|reading|export)" || echo "  No recent activity"

    # Check for errors
    ERROR_COUNT=$(docker logs --tail 100 $ALLOY_CONTAINER 2>&1 | grep -ci "error" || echo "0")
    if [ "$ERROR_COUNT" -eq 0 ]; then
        print_status "OK" "No errors in recent logs"
    else
        print_status "WARN" "Found $ERROR_COUNT error messages in recent logs"
    fi
else
    print_status "WARN" "Cannot check logs (Alloy container not running locally)"
fi

# ========================================
# 6. End-to-End Verification
# ========================================
echo -e "\n${BLUE}[6/6] End-to-End Verification${NC}"

# Check if data is flowing through the entire pipeline
if curl -sf "http://$META_SERVER:$CORRELATION_ENGINE_PORT/api/correlations" > /dev/null 2>&1; then
    CORRELATIONS=$(curl -s "http://$META_SERVER:$CORRELATION_ENGINE_PORT/api/correlations?limit=1" | grep -c "correlation_id" || echo "0")
    if [ "$CORRELATIONS" -gt 0 ]; then
        print_status "OK" "Correlation events are being created"
    else
        print_status "WARN" "No correlation events found (may take 60s for first window)"
    fi
else
    print_status "WARN" "Cannot query correlation events"
fi

# ========================================
# Summary
# ========================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. If Alloy is not running:"
echo "   cd /path/to/mdso-alloy && ./deploy-container.sh"
echo ""
echo "2. To monitor live logs:"
echo "   docker logs -f <alloy-container>"
echo ""
echo "3. To view field extractions in Grafana:"
echo "   http://$META_SERVER:3000 → Explore → Loki"
echo "   Query: {service=\"mdso\"} | json"
echo ""
echo "4. To test pattern extraction locally:"
echo "   cd test-samples && ./validate-extractions.sh"
echo ""
echo "5. For detailed testing guide:"
echo "   cat TESTING-GUIDE-ENHANCED.md"

echo -e "\n${BLUE}========================================${NC}"
