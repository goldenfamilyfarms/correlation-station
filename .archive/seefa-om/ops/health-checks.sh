#!/bin/bash
#
# Health Checks Script
# Comprehensive health checking for all observability components
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVER_124="${SERVER_124_IP:-localhost}"
TIMEOUT=5

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Observability PoC Health Checks${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Target: $SERVER_124"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Function to check HTTP endpoint
check_http() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo -n "  Checking $name... "

    if response=$(curl -s -w "\n%{http_code}" -m $TIMEOUT "$url" 2>/dev/null); then
        http_code=$(echo "$response" | tail -n 1)

        if [ "$http_code" = "$expected_code" ]; then
            echo -e "${GREEN}✓ OK (${http_code})${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        else
            echo -e "${RED}✗ FAIL (${http_code}, expected ${expected_code})${NC}"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        fi
    else
        echo -e "${RED}✗ TIMEOUT/ERROR${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Function to check TCP port
check_port() {
    local name="$1"
    local host="$2"
    local port="$3"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo -n "  Checking $name... "

    if timeout $TIMEOUT bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}✓ Port ${port} open${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗ Port ${port} closed/timeout${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# ============================================
# Check Core Observability Stack
# ============================================
echo -e "${YELLOW}Core Observability Stack:${NC}"

check_http "Grafana" "http://${SERVER_124}:3000/api/health"
check_http "Loki" "http://${SERVER_124}:3100/ready"
check_http "Tempo" "http://${SERVER_124}:3200/ready"
check_http "Prometheus" "http://${SERVER_124}:9090/-/healthy"

echo ""

# ============================================
# Check OTel Gateway
# ============================================
echo -e "${YELLOW}OTel Collector Gateway:${NC}"

check_http "Gateway Health" "http://${SERVER_124}:13133"
check_port "OTLP gRPC" "$SERVER_124" 4317
check_port "OTLP HTTP" "$SERVER_124" 4318
check_port "Legacy OTLP gRPC" "$SERVER_124" 55680
check_port "Legacy OTLP HTTP" "$SERVER_124" 55681
check_http "Gateway Metrics" "http://${SERVER_124}:8888/metrics"

echo ""

# ============================================
# Check Correlation Engine
# ============================================
echo -e "${YELLOW}Correlation Engine:${NC}"

check_http "Engine Health" "http://${SERVER_124}:8080/health"
check_http "Engine Metrics" "http://${SERVER_124}:8080/metrics"
check_http "Engine Root" "http://${SERVER_124}:8080/"

echo ""

# ============================================
# Check Sense Apps
# ============================================
echo -e "${YELLOW}Sense Applications:${NC}"

check_http "Beorn" "http://${SERVER_124}:5001/health"
check_http "Palantir" "http://${SERVER_124}:5002/health"
check_http "Arda" "http://${SERVER_124}:5003/health"

echo ""

# ============================================
# Check Data Flow
# ============================================
echo -e "${YELLOW}Data Flow Checks:${NC}"

# Check if metrics are being collected
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "  Checking Prometheus targets... "
if targets=$(curl -s -m $TIMEOUT "http://${SERVER_124}:9090/api/v1/targets" 2>/dev/null); then
    active=$(echo "$targets" | jq -r '.data.activeTargets | length' 2>/dev/null || echo "0")
    if [ "$active" -gt 0 ]; then
        echo -e "${GREEN}✓ ${active} active targets${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠ No active targets${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    echo -e "${RED}✗ Cannot query Prometheus${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check if logs are in Loki
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "  Checking Loki logs... "
if logs=$(curl -s -m $TIMEOUT -G "http://${SERVER_124}:3100/loki/api/v1/query" \
    --data-urlencode 'query={service=~".+"}' \
    --data-urlencode 'limit=1' 2>/dev/null); then
    count=$(echo "$logs" | jq -r '.data.result | length' 2>/dev/null || echo "0")
    if [ "$count" -gt 0 ]; then
        echo -e "${GREEN}✓ Logs present${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠ No logs found${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    echo -e "${RED}✗ Cannot query Loki${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check if traces are in Tempo
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "  Checking Tempo traces... "
if traces=$(curl -s -m $TIMEOUT "http://${SERVER_124}:3200/api/search?limit=1" 2>/dev/null); then
    count=$(echo "$traces" | jq -r '.traces | length' 2>/dev/null || echo "0")
    if [ "$count" -gt 0 ]; then
        echo -e "${GREEN}✓ Traces present${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠ No traces found${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    echo -e "${RED}✗ Cannot query Tempo${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check correlation metrics
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "  Checking correlation metrics... "
if metrics=$(curl -s -m $TIMEOUT "http://${SERVER_124}:8080/metrics" 2>/dev/null); then
    if echo "$metrics" | grep -q "correlation_events_total"; then
        count=$(echo "$metrics" | grep "correlation_events_total{" | head -1 | awk '{print $2}' || echo "0")
        echo -e "${GREEN}✓ Metrics present (${count} events)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠ No correlation metrics${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    echo -e "${RED}✗ Cannot query metrics${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# ============================================
# Check Docker Containers
# ============================================
echo -e "${YELLOW}Docker Containers:${NC}"

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "  Checking running containers... "
if command -v docker &> /dev/null; then
    running=$(docker ps --filter "status=running" | wc -l)
    running=$((running - 1))  # Subtract header line

    if [ "$running" -gt 0 ]; then
        echo -e "${GREEN}✓ ${running} containers running${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))

        # Show container names
        echo ""
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
    else
        echo -e "${RED}✗ No containers running${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
else
    echo -e "${YELLOW}⚠ Docker not available${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# ============================================
# Summary
# ============================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Health Check Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Total Checks:  $TOTAL_CHECKS"
echo -e "Passed:        ${GREEN}${PASSED_CHECKS}${NC}"
echo -e "Failed:        ${RED}${FAILED_CHECKS}${NC}"
echo ""

# Calculate percentage
if [ "$TOTAL_CHECKS" -gt 0 ]; then
    percentage=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    echo "Success Rate:  ${percentage}%"
    echo ""

    if [ "$FAILED_CHECKS" -eq 0 ]; then
        echo -e "${GREEN}✓ All health checks passed!${NC}"
        exit 0
    elif [ "$percentage" -ge 80 ]; then
        echo -e "${YELLOW}⚠ Most checks passed, but some services may need attention${NC}"
        exit 0
    else
        echo -e "${RED}✗ Multiple services failing - immediate attention required${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ No checks performed${NC}"
    exit 1
fi