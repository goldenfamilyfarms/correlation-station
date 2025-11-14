#!/bin/bash
# Health check script for all observability components

set -e

echo "============================================"
echo "Health Check - Server-124 Observability PoC"
echo "============================================"
echo ""

FAILED=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    echo -n "Checking $name... "

    if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_code" ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        else
            echo -e "${YELLOW}⚠ WARNING${NC} (HTTP $response, expected $expected_code)"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "${RED}✗ FAILED${NC} (unreachable)"
        FAILED=$((FAILED + 1))
    fi
}

check_port() {
    local name=$1
    local host=$2
    local port=$3

    echo -n "Checking $name port... "

    if timeout 2 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC} (port $port open)"
    else
        echo -e "${RED}✗ FAILED${NC} (port $port closed)"
        FAILED=$((FAILED + 1))
    fi
}

check_systemd() {
    local name=$1
    local service=$2

    echo -n "Checking $name... "

    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓ OK${NC} (running)"
    else
        echo -e "${RED}✗ FAILED${NC} (not running)"
        FAILED=$((FAILED + 1))
    fi
}

# Core Observability Stack
echo "=== Core Observability Stack ==="
check_service "Grafana" "http://47:43:111:124:3000/api/health"
check_service "Loki" "http://localhost:3100/ready"
check_service "Tempo" "http://localhost:3200/ready"
check_service "Prometheus" "http://localhost:9090/-/healthy"
echo ""

# OTel Collector Gateway
echo "=== OTel Collector Gateway ==="
check_service "Gateway Metrics" "http://localhost:18888/metrics"
check_port "OTLP gRPC" "localhost" "55680"
check_port "OTLP HTTP" "localhost" "55681"
check_port "OTLP gRPC (legacy)" "localhost" "14317"
check_port "OTLP HTTP (legacy)" "localhost" "14318"
check_port "OTLP gRPC (legacy)" "localhost" "4317"
check_port "OTLP HTTP (legacy)" "localhost" "4318"
echo ""

# Correlation Engine
echo "=== Correlation Engine ==="
check_service "Correlation API" "http://localhost:8080/health"
echo ""

# MDSO Poller
echo "=== MDSO Syslog Poller ==="
check_systemd "MDSO Poller" "mdso-poller.service"
if [ -d "/var/log/mdso" ]; then
    log_count=$(find /var/log/mdso -name "*.ndjson" 2>/dev/null | wc -l)
    echo "  Log files: $log_count"
    if [ "$log_count" -gt 0 ]; then
        latest=$(find /var/log/mdso -name "*.ndjson" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
        if [ -n "$latest" ]; then
            line_count=$(wc -l < "$latest" 2>/dev/null || echo "0")
            echo "  Latest file: $(basename "$latest") ($line_count lines)"
        fi
    fi
fi
echo ""

# Sense Apps (optional)
echo "=== Sense Apps (optional) ==="
check_service "Beorn" "http://localhost:5001/" 000
check_service "Palantir" "http://localhost:5002/" 000
check_service "Arda" "http://localhost:5003/" 000
echo ""

# Docker containers
echo "=== Docker Containers ==="
echo "Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(grafana|loki|tempo|prometheus|otel-gateway|correlation-engine)" || echo "  No observability containers running"
echo ""

# Disk space
echo "=== Disk Space ==="
df -h / | tail -1 | awk '{print "  Root: " $3 " used / " $2 " total (" $5 " used)"}'
if [ -d "/var/lib/docker" ]; then
    docker_size=$(du -sh /var/lib/docker 2>/dev/null | cut -f1)
    echo "  Docker: $docker_size"
fi
echo ""

# Summary
echo "============================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED check(s) failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check logs: make logs SERVICE=<service>"
    echo "  - Restart services: make restart-all"
    echo "  - View detailed status: docker compose ps"
    exit 1
fi