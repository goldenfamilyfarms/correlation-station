#!/bin/bash
# Deploy Grafana Alloy as container on MDSO Dev (159.56.4.37)

set -e

echo "=== Deploying Alloy Container on MDSO Dev ==="

# Check if running on MDSO Dev
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Current host IP: $CURRENT_IP"

# Verify log directories exist
echo "Checking log directories..."
if [ ! -d "/var/log/ciena" ]; then
    echo "WARNING: /var/log/ciena not found"
fi
if [ ! -d "/bp2/log" ]; then
    echo "WARNING: /bp2/log not found"
fi

# Test connectivity to Meta
echo "Testing connectivity to Meta (159.56.4.94:55681)..."
if curl -s --max-time 5 http://159.56.4.94:55681/v1/logs > /dev/null 2>&1; then
    echo "✓ Meta server reachable"
else
    echo "✗ Cannot reach Meta server - check network/firewall"
    exit 1
fi

# Stop existing container if running
if docker ps -a | grep -q alloy-mdso; then
    echo "Stopping existing Alloy container..."
    docker stop alloy-mdso || true
    docker rm alloy-mdso || true
fi

# Start Alloy container
echo "Starting Alloy container..."
docker-compose up -d

# Wait for startup
echo "Waiting for Alloy to start..."
sleep 5

# Check status
echo ""
echo "=== Container Status ==="
docker ps | grep alloy-mdso

echo ""
echo "=== Alloy Logs (last 20 lines) ==="
docker logs --tail 20 alloy-mdso

echo ""
echo "=== Deployment Complete ==="
echo "Alloy UI: http://$(hostname -I | awk '{print $1}'):12345"
echo "View logs: docker logs -f alloy-mdso"
echo "Stop: docker-compose down"
