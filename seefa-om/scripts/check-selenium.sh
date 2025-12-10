#!/bin/bash
# Check Selenium container status

echo "Checking Selenium container..."
docker ps --filter "name=selenium" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Checking Selenium health..."
curl -s http://localhost:4444/wd/hub/status | jq '.value.ready' 2>/dev/null || echo "Selenium not responding"

echo ""
echo "To start Selenium:"
echo "  docker-compose -f docker-compose.selenium.yml up -d"
echo ""
echo "To view Selenium UI (VNC):"
echo "  Open browser to: http://localhost:7900"
echo "  Password: secret (if prompted)"
