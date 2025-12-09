#!/bin/bash
# Fix config file and run Test 2

set -e

echo "=========================================="
echo "Fixing and Running TEST 2"
echo "=========================================="

# Remove directory if it exists
echo "1. Cleaning up old config..."
sudo rm -rf config-test2-loki-components.alloy

# Create proper config file
echo "2. Creating Test 2 config..."
sudo tee config-test2-loki-components.alloy > /dev/null << 'EOF'
// TEST 2: Loki Components Pipeline
// MDSO Dev → Loki components → OTel Gateway

// Discover syslog files
local.file_match "syslog_files" {
  path_targets = [
    {"__path__" = "/var/log/ciena/blueplanet.log"},
  ]
}

// Tail syslog files (only new logs)
loki.source.file "syslog" {
  targets    = local.file_match.syslog_files.targets
  forward_to = [loki.process.add_labels.receiver]
  
  // Start at end - only tail new logs
  tail_from_end = true
}

// Parse and extract fields
loki.process "add_labels" {
  forward_to = [otelcol.receiver.loki.default.receiver]

  // Parse JSON from syslog message
  stage.json {
    expressions = {
      timestamp   = "timestamp",
      app         = "app",
      app_instance = "app_instance",
      container   = "container",
      msg         = "msg",
      priority    = "priority",
      namespace   = "namespace",
      pid         = "pid",
    }
  }

  // Add low-cardinality labels only
  stage.labels {
    values = {
      service = "mdso",
      env     = "dev",
      app     = "",  // Extracted from JSON
    }
  }
}

// Convert Loki logs to OTLP
otelcol.receiver.loki "default" {
  output {
    logs = [otelcol.exporter.otlphttp.gateway.input]
  }
}

// Export to OTel Gateway on Meta
otelcol.exporter.otlphttp "gateway" {
  client {
    endpoint = "http://159.56.4.94:55681"
    timeout  = "10s"
  }
}
EOF

echo "   ✓ Config created"

# Test connectivity
echo ""
echo "3. Testing OTel Gateway connectivity..."
if curl -s --max-time 5 http://159.56.4.94:55681/v1/logs > /dev/null 2>&1; then
    echo "   ✓ OTel Gateway reachable"
else
    echo "   ✗ Cannot reach OTel Gateway"
    exit 1
fi

# Stop any existing test containers
echo ""
echo "4. Stopping existing containers..."
sudo docker stop alloy-test1 alloy-test2 2>/dev/null || true
sudo docker rm alloy-test1 alloy-test2 2>/dev/null || true

# Start test container
echo ""
echo "5. Starting Test 2 container..."
CONFIG_PATH=$(realpath config-test2-loki-components.alloy)
sudo docker run -d \
  --name alloy-test2 \
  --restart unless-stopped \
  --network host \
  -v "${CONFIG_PATH}:/tmp/config.alloy:ro" \
  -v /var/log/ciena:/var/log/ciena:ro \
  grafana/alloy:latest \
  run /tmp/config.alloy --server.http.listen-addr=0.0.0.0:12345

sleep 5

# Check status
echo ""
echo "6. Container status:"
sudo docker ps | grep alloy-test2

echo ""
echo "7. Alloy logs:"
sudo docker logs --tail 30 alloy-test2

echo ""
echo "=========================================="
echo "TEST 2 DEPLOYED"
echo "=========================================="
echo "Monitor: sudo docker logs -f alloy-test2"
echo "Stop:    sudo docker stop alloy-test2"
echo ""
