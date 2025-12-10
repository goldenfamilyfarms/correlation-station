# Manual Fix Steps for Server

Run these commands on `austx-mdso-logs-02.chtrse.com`:

## 1. Check Correlation Engine Error

```bash
cd /opt/seefa-om
sudo docker logs correlation-engine 2>&1 | tail -50
```

Look for import errors related to `pandas`, `selenium`, or `openpyxl`.

## 2. Fix Correlation Engine

The container needs to rebuild with new dependencies:

```bash
cd /opt/seefa-om
sudo docker compose down correlation-engine
sudo docker compose build --no-cache correlation-engine
sudo docker compose up -d correlation-engine

# Wait and check
sleep 10
sudo docker ps | grep correlation-engine
sudo docker logs correlation-engine | tail -20
```

## 3. Fix Pyroscope 404

The Pyroscope API endpoint might have changed. Test different endpoints:

```bash
# Test health
curl http://localhost:4040/healthz

# Test different API paths
curl http://localhost:4040/api/apps
curl http://localhost:4040/pyroscope/api/apps
curl http://localhost:4040/

# Check Pyroscope logs
sudo docker logs pyroscope | tail -30
```

If Pyroscope is unhealthy, restart it:

```bash
sudo docker compose restart pyroscope
sleep 5
sudo docker logs pyroscope | tail -20
```

## 4. Verify All Services

```bash
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
```

All services should show "Up" and "(healthy)".

## 5. Test Endpoints

```bash
# Correlation Engine
curl http://localhost:8080/health
curl http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs

# Pyroscope
curl http://localhost:4040/healthz

# Frontend
curl http://localhost:3002
```

## 6. If Correlation Engine Still Fails

Check if it's a dependency issue:

```bash
# Enter the container
sudo docker exec -it correlation-engine bash

# Check if packages are installed
pip list | grep -E "pandas|selenium|openpyxl|reportlab"

# If missing, exit and rebuild
exit
sudo docker compose build --no-cache correlation-engine
sudo docker compose up -d correlation-engine
```

## 7. Alternative: Disable SECA Routes Temporarily

If you need the correlation engine working NOW without SECA features:

The code already has a try/except to make SECA routes optional. The issue is likely the import failing before that check.

Check the error in logs - if it's an import error at the top level, we need to make those imports conditional too.

## Quick Status Check Script

```bash
#!/bin/bash
echo "=== Service Status ==="
sudo docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "correlation-engine|pyroscope|correlation-station-ui"

echo ""
echo "=== Health Checks ==="
echo -n "Correlation Engine: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health

echo -n "Pyroscope: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4040/healthz

echo -n "Frontend: "
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3002

echo ""
echo "=== Recent Errors ==="
echo "Correlation Engine:"
sudo docker logs correlation-engine 2>&1 | grep -i error | tail -5

echo ""
echo "Pyroscope:"
sudo docker logs pyroscope 2>&1 | grep -i error | tail -5
```

Save this as `check-status.sh`, make it executable, and run it:

```bash
chmod +x check-status.sh
./check-status.sh
```
