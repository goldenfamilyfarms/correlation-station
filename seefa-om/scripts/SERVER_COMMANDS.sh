#!/bin/bash
# Run these commands on austx-mdso-logs-02.chtrse.com

echo "========================================="
echo "SEEFA-OM Quick Fix - Run on Server"
echo "========================================="
echo ""

cd /opt/seefa-om

echo "1. Pulling latest code..."
git pull origin main

echo ""
echo "2. Stopping affected services..."
sudo docker compose down correlation-engine correlation-station-ui pyroscope

echo ""
echo "3. Rebuilding correlation-engine (with new dependencies)..."
sudo docker compose build --no-cache correlation-engine

echo ""
echo "4. Rebuilding frontend (with Datadog modal fix)..."
sudo docker compose build --no-cache correlation-station-ui

echo ""
echo "5. Starting services..."
sudo docker compose up -d correlation-engine correlation-station-ui pyroscope

echo ""
echo "6. Starting Selenium (for SECA processing)..."
sudo docker compose -f docker-compose.selenium.yml up -d

echo ""
echo "Waiting 15 seconds for services to start..."
sleep 15

echo ""
echo "========================================="
echo "Service Status Check"
echo "========================================="
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "correlation-engine|pyroscope|correlation-station-ui|selenium"

echo ""
echo "========================================="
echo "Health Checks"
echo "========================================="
echo -n "Correlation Engine: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health

echo -n "Pyroscope: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4040/healthz

echo -n "Frontend: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3002

echo -n "Selenium: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4444/wd/hub/status

echo ""
echo "========================================="
echo "Testing Endpoints"
echo "========================================="
echo "Testing Correlation Engine Docs..."
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs

echo "Testing Pyroscope API..."
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://austx-mdso-logs-02.chtrse.com/pyroscope/api/apps

echo ""
echo "========================================="
echo "View Logs (if needed)"
echo "========================================="
echo "docker logs -f correlation-engine"
echo "docker logs -f pyroscope"
echo "docker logs -f correlation-station-ui"
echo "docker logs -f selenium-standalone-chrome"

echo ""
echo "========================================="
echo "Selenium VNC Access (for debugging)"
echo "========================================="
echo "URL: http://austx-mdso-logs-02.chtrse.com:7900"
echo "Password: secret (if prompted)"

echo ""
echo "Done!"
