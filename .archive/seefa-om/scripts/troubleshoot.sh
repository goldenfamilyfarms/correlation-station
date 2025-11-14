#!/bin/bash
# Troubleshooting script for observability stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Observability Stack Troubleshooting"
echo "======================================"
echo ""

# Function to check service health
check_service() {
    local SERVICE=$1
    local PORT=$2
    local ENDPOINT=$3

    echo -n "Checking $SERVICE... "

    if curl -sf "http://localhost:$PORT$ENDPOINT" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Running on port $PORT"
        return 0
    else
        echo -e "${RED}✗${NC} Not accessible on port $PORT"
        return 1
    fi
}

# Function to check container logs for errors
check_container_logs() {
    local CONTAINER=$1
    echo ""
    echo "Recent errors in $CONTAINER:"
    echo "----------------------------"
    docker logs "$CONTAINER" 2>&1 | grep -i -E "error|exception|failed" | tail -5 || echo "No recent errors found"
}

# Check Docker
echo "1. Docker Status:"
echo "-----------------"
docker version > /dev/null 2>&1 && echo -e "${GREEN}✓${NC} Docker is running" || echo -e "${RED}✗${NC} Docker is not running"

# Check containers
echo ""
echo "2. Container Status:"
echo "--------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check correlation-engine specific files
echo ""
echo "3. Correlation Engine Files:"
echo "----------------------------"
if [ -f "correlation-engine/app/models.py" ]; then
    if grep -q "class HealthStatus" correlation-engine/app/models.py; then
        echo -e "${GREEN}✓${NC} HealthStatus model found in models.py"
    else
        echo -e "${RED}✗${NC} HealthStatus model missing in models.py"
    fi
fi

if [ -f "correlation-engine/app/routes/health.py" ]; then
    echo -e "${GREEN}✓${NC} health.py route file exists"
else
    echo -e "${RED}✗${NC} health.py route file missing"
fi

# Check service health endpoints
echo ""
echo "4. Service Health Checks:"
echo "-------------------------"
check_service "Grafana" 3000 "/api/health"
check_service "Loki" 3100 "/ready"
check_service "Tempo" 3200 "/ready"
check_service "Prometheus" 9090 "/-/healthy"
check_service "Correlation Engine" 8080 "/health"

# Check for common issues
echo ""
echo "5. Common Issues:"
echo "-----------------"

# Check Tempo config
if [ -f "configs/tempo.yaml" ]; then
    if grep -q "defaults:" configs/tempo.yaml; then
        echo -e "${YELLOW}⚠${NC} Tempo config contains 'defaults:' field - this should be removed"
    else
        echo -e "${GREEN}✓${NC} Tempo config looks correct"
    fi
fi

# Check disk space
echo ""
echo "6. Disk Space:"
echo "--------------"
df -h | grep -E "/$|/var/lib/docker"

# Container logs for failing services
echo ""
echo "7. Container Error Logs:"
echo "------------------------"
for container in correlation-engine tempo loki prometheus grafana gateway; do
    if docker ps -a --format "{{.Names}}" | grep -q "^$container$"; then
        check_container_logs "$container"
    fi
done

# Recommendations
echo ""
echo "8. Recommendations:"
echo "-------------------"
echo "If correlation-engine is failing with HealthStatus import error:"
echo "  1. Copy the fixed models.py from the artifact above"
echo "  2. Rebuild: docker-compose build correlation-engine"
echo "  3. Restart: docker-compose up -d correlation-engine"
echo ""
echo "If Tempo is failing with 'defaults' field error:"
echo "  1. Copy the fixed tempo.yaml from the artifact above"
echo "  2. Restart: docker-compose restart tempo"
echo ""
echo "To view real-time logs:"
echo "  docker-compose logs -f correlation-engine"
echo "  docker-compose logs -f tempo"
echo ""
echo "To restart all services:"
echo "  docker-compose down && docker-compose up -d"