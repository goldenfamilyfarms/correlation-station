#!/bin/bash
# TEST 3: Full Pipeline
# MDSO → OTel Gateway → Correlation Engine → Loki/Tempo

set -e

echo "=========================================="
echo "TEST 3: Full Pipeline with Correlation"
echo "=========================================="
echo ""

# Test connectivity
echo "1. Testing OTel Gateway connectivity..."
if curl -s --max-time 5 http://159.56.4.94:55681/v1/logs > /dev/null 2>&1; then
    echo "   ✓ OTel Gateway reachable"
else
    echo "   ✗ Cannot reach OTel Gateway"
    exit 1
fi

# Stop any existing test containers
echo ""
echo "2. Stopping existing containers..."
sudo docker stop alloy-test1 alloy-test2 alloy-test3 2>/dev/null || true
sudo docker rm alloy-test1 alloy-test2 alloy-test3 2>/dev/null || true

# Start test container
echo ""
echo "3. Starting Test 3 container (full pipeline)..."
CONFIG_PATH=$(realpath config-test3-full-pipeline.alloy)
sudo docker run -d \
  --name alloy-test3 \
  --restart unless-stopped \
  --network host \
  -v "${CONFIG_PATH}:/tmp/config.alloy:ro" \
  -v /var/log/ciena:/var/log/ciena:ro \
  -v /bp2/log:/bp2/log:ro \
  grafana/alloy:latest \
  run /tmp/config.alloy --server.http.listen-addr=0.0.0.0:12345

sleep 5

# Check status
echo ""
echo "4. Container status:"
sudo docker ps | grep alloy-test3

echo ""
echo "5. Alloy logs:"
sudo docker logs --tail 30 alloy-test3

echo ""
echo "=========================================="
echo "TEST 3 DEPLOYED - FULL PIPELINE"
echo "=========================================="
echo "Monitor: docker logs -f alloy-test3"
echo "Stop:    docker stop alloy-test3"
echo ""
echo "Verify on Meta:"
echo "  - OTel Gateway:        docker-compose logs otel-gateway"
echo "  - Correlation Engine:  docker-compose logs correlation-engine"
echo "  - Loki:                curl 'http://159.56.4.94:3100/loki/api/v1/query?query={service=\"mdso\"}'"
echo ""
