#!/bin/bash
# Run this on Meta server (159.56.4.94) to verify logs are arriving

echo "=== Verifying MDSO Logs on Meta Server ==="

# Check OTel Gateway logs
echo "1. Checking OTel Gateway logs for MDSO traffic..."
docker-compose logs --tail 50 otel-gateway | grep -i "mdso\|blueplanet" || echo "   No MDSO logs found yet"

echo ""
echo "2. Checking OTel Gateway metrics..."
curl -s http://localhost:8888/metrics | grep -E "otelcol_receiver|otelcol_exporter" | head -10

echo ""
echo "3. Checking correlation engine logs..."
docker-compose logs --tail 20 correlation-engine | grep -i "log_records_received\|mdso" || echo "   No MDSO logs in correlation engine yet"

echo ""
echo "=== Verification Complete ==="
echo ""
echo "If no logs found, check:"
echo "  - Alloy is running on MDSO: ssh bpadmin@159.56.4.37 'docker ps | grep alloy'"
echo "  - Alloy logs: ssh bpadmin@159.56.4.37 'docker logs alloy-test'"
echo "  - Network connectivity: curl -v http://159.56.4.94:55681/v1/logs"
