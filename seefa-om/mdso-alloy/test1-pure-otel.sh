#!/bin/bash
# TEST 1: Pure OTel Components
# MDSO → OTel Gateway (no Loki components)

set -e

echo "=========================================="
echo "TEST 1: Pure OTel Components"
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
sudo docker stop alloy-test1 2>/dev/null || true
sudo docker rm alloy-test1 2>/dev/null || true

# Start test container
echo ""
echo "3. Starting Test 1 container..."
CONFIG_PATH=$(realpath config-test1-pure-otel.alloy)
sudo docker run -d \
  --name alloy-test1 \
  --restart unless-stopped \
  --network host \
  -v "${CONFIG_PATH}:/tmp/config.alloy:ro" \
  -v /var/log/ciena:/var/log/ciena:ro \
  -v /bp2/log:/bp2/log:ro \
  grafana/alloy:latest \
  run /tmp/config.alloy --server.http.listen-addr=0.0.0.0:12345 --stability.level=public-preview

sleep 5

# Check status
echo ""
echo "4. Container status:"
sudo docker ps | grep alloy-test1

echo ""
echo "5. Alloy logs:"
sudo docker logs --tail 30 alloy-test1

echo ""
echo "=========================================="
echo "TEST 1 DEPLOYED"
echo "=========================================="
echo "Monitor: docker logs -f alloy-test1"
echo "Stop:    docker stop alloy-test1"
echo ""
