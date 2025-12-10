# Quick Fix Guide

## Issue 1: Correlation Engine 502 Error (Container Restarting)

The correlation-engine container is restarting because of missing dependencies for the new SECA routes.

### Fix:
```bash
cd ~/seefa-om
git pull origin main
docker-compose down correlation-engine
docker-compose build correlation-engine
docker-compose up -d correlation-engine
docker logs -f correlation-engine
```

## Issue 2: Pyroscope 404 Error

Pyroscope is returning HTML instead of JSON for the API endpoint.

### Check:
```bash
# Check if Pyroscope is running
docker ps | grep pyroscope

# Check Pyroscope logs
docker logs pyroscope

# Test Pyroscope endpoint
curl http://localhost:4040/api/apps
```

### Fix:
```bash
# Restart Pyroscope
docker-compose restart pyroscope

# If still failing, rebuild
docker-compose down pyroscope
docker-compose up -d pyroscope
```

## Issue 3: Datadog Modal Image

The image has been replaced with an emoji-based design that doesn't require external assets.

### Rebuild Frontend:
```bash
cd ~/seefa-om/frontend
npm run build
cd ~/seefa-om
docker-compose build correlation-station-ui
docker-compose up -d correlation-station-ui
```

## Issue 4: Check Selenium Container

Selenium is in a testing profile and needs to be started separately.

### Start Selenium:
```bash
cd ~/seefa-om
docker-compose -f docker-compose.selenium.yml up -d

# Check status
docker ps | grep selenium

# Check health
curl http://localhost:4444/wd/hub/status

# View Selenium UI (for debugging)
# Open browser to: http://localhost:7900
```

## All-in-One Fix Script

```bash
#!/bin/bash
cd ~/seefa-om

echo "Pulling latest code..."
git pull origin main

echo "Rebuilding correlation-engine..."
docker-compose down correlation-engine
docker-compose build --no-cache correlation-engine
docker-compose up -d correlation-engine

echo "Restarting Pyroscope..."
docker-compose restart pyroscope

echo "Rebuilding frontend..."
docker-compose build --no-cache correlation-station-ui
docker-compose up -d correlation-station-ui

echo "Starting Selenium..."
docker-compose -f docker-compose.selenium.yml up -d

echo ""
echo "Waiting for services to start..."
sleep 10

echo ""
echo "Checking service status..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "correlation-engine|pyroscope|correlation-station-ui|selenium"

echo ""
echo "Testing endpoints..."
echo "Correlation Engine: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/health)"
echo "Pyroscope: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:4040/healthz)"
echo "Frontend: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:3002)"
echo "Selenium: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:4444/wd/hub/status)"

echo ""
echo "Done! Check logs with:"
echo "  docker logs -f correlation-engine"
echo "  docker logs -f pyroscope"
echo "  docker logs -f correlation-station-ui"
```

## Verify Fixes

### 1. Correlation Engine Docs
```bash
curl http://austx-mdso-logs-02.chtrse.com/correlation-engine/docs
# Should return HTML page, not 502
```

### 2. Pyroscope API
```bash
curl http://austx-mdso-logs-02.chtrse.com/pyroscope/api/apps
# Should return JSON, not 404 HTML
```

### 3. Frontend
```bash
# Open browser to:
http://austx-mdso-logs-02.chtrse.com/correlation-station/
# Datadog modal should show emoji design
```

### 4. Selenium
```bash
curl http://localhost:4444/wd/hub/status | jq '.value.ready'
# Should return: true
```

## Troubleshooting

### If correlation-engine still fails:
```bash
# Check logs for specific error
docker logs correlation-engine 2>&1 | tail -50

# Check if dependencies are installed
docker exec correlation-engine pip list | grep -E "pandas|selenium|openpyxl"

# If missing, rebuild with no cache
docker-compose build --no-cache correlation-engine
```

### If Pyroscope still returns 404:
```bash
# Check Pyroscope config
docker exec pyroscope cat /etc/pyroscope/config.yaml

# Check if base URL is set correctly
docker exec pyroscope env | grep PYROSCOPE

# Restart with fresh data
docker-compose down pyroscope
docker volume rm seefa-om_pyroscope-data
docker-compose up -d pyroscope
```

### If frontend doesn't show changes:
```bash
# Clear browser cache
# Or use incognito mode

# Check if new files are in container
docker exec correlation-station-ui ls -la /usr/share/nginx/html/assets

# Rebuild from scratch
docker-compose down correlation-station-ui
docker rmi seefa-om-correlation-station-ui
docker-compose build --no-cache correlation-station-ui
docker-compose up -d correlation-station-ui
```
