#!/bin/bash
# Test syslog → OTel Collector pipeline only

set -e

echo "=== Testing Alloy → OTel Collector Pipeline ==="

# Test Meta OTel Gateway connectivity
echo "1. Testing OTel Gateway connectivity..."
if curl -s --max-time 5 http://159.56.4.94:55681/v1/logs > /dev/null 2>&1; then
    echo "   ✓ OTel Gateway reachable at 159.56.4.94:55681"
else
    echo "   ✗ Cannot reach OTel Gateway"
    exit 1
fi

# Check log files exist
echo ""
echo "2. Checking log files..."
if [ -f "/var/log/ciena/blueplanet.log" ]; then
    echo "   ✓ /var/log/ciena/blueplanet.log exists"
    echo "   Last 3 lines:"
    tail -3 /var/log/ciena/blueplanet.log | sed 's/^/     /'
else
    echo "   ✗ /var/log/ciena/blueplanet.log not found"
fi

if [ -d "/bp2/log" ]; then
    echo "   ✓ /bp2/log directory exists"
    ls -1 /bp2/log/*.log 2>/dev/null | head -3 | sed 's/^/     /'
else
    echo "   ✗ /bp2/log directory not found"
fi

# Stop existing test container
echo ""
echo "3. Stopping existing test container..."
docker-compose -f docker-compose-test.yml down 2>/dev/null || true

# Start test container
echo ""
echo "4. Starting Alloy test container..."
docker-compose -f docker-compose-test.yml up -d

# Wait for startup
echo "   Waiting 5 seconds for startup..."
sleep 5

# Check container status
echo ""
echo "5. Container status:"
docker ps | grep alloy-test || echo "   ✗ Container not running!"

# Show logs
echo ""
echo "6. Alloy logs (last 30 lines):"
docker logs --tail 30 alloy-test

echo ""
echo "=== Test Deployment Complete ==="
echo ""
echo "Next steps:"
echo "  1. Monitor logs:    docker logs -f alloy-test"
echo "  2. Check OTel Gateway on Meta (159.56.4.94):"
echo "     docker-compose logs otel-gateway | grep -i mdso"
echo "  3. Stop test:       docker-compose -f docker-compose-test.yml down"
