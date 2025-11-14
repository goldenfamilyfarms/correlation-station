#!/bin/bash
# Verify which test is running and check results on Meta

echo "=========================================="
echo "Test Verification Script"
echo "=========================================="
echo ""

# Check which test is running on MDSO
echo "Running containers on MDSO Dev:"
docker ps | grep alloy-test || echo "  No test containers running"

echo ""
echo "=========================================="
echo "Run this on Meta (159.56.4.94):"
echo "=========================================="
echo ""

cat << 'EOF'
# 1. Check OTel Gateway received logs
docker-compose logs --tail 50 otel-gateway | grep -i "log"

# 2. Check OTel Gateway metrics
curl -s http://localhost:8888/metrics | grep "otelcol_receiver_accepted_log_records"

# 3. Check Correlation Engine (Test 3 only)
docker-compose logs --tail 50 correlation-engine | grep -i "mdso"

# 4. Query Loki for MDSO logs
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=10' | jq

# 5. Check all services status
docker-compose ps
EOF

echo ""
