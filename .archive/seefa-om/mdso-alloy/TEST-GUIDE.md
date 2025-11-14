# Test Guide: MDSO → OTel Collector Only

## Overview

This test sends syslog from MDSO Dev directly to the OTel Collector on Meta, bypassing Loki initially. This validates the pipeline before adding complexity.

## Architecture (Test Phase)

```
MDSO Dev (159.56.4.37)                Meta (159.56.4.94)
┌─────────────────────┐              ┌──────────────────────┐
│  Alloy Container    │              │  OTel Gateway        │
│  • Tail syslog      │─────OTLP────▶│  :55681 (HTTP)       │
│  • Convert to OTLP  │   HTTP       │  • Receives logs     │
│  • Export           │              │  • Logs to console   │
└─────────────────────┘              └──────────────────────┘
```

## Step 1: Deploy on MDSO Dev

```bash
# SSH to MDSO Dev
ssh bpadmin@159.56.4.37

# Navigate to alloy directory
cd ~/alloy-agent

# Make script executable
chmod +x test-otel-only.sh

# Run test deployment
./test-otel-only.sh
```

**Expected Output:**
```
✓ OTel Gateway reachable at 159.56.4.94:55681
✓ /var/log/ciena/blueplanet.log exists
✓ Container running
```

## Step 2: Monitor Alloy Logs

```bash
# On MDSO Dev - watch Alloy logs
docker logs -f alloy-test

# Look for:
# - "component started" - Alloy initialized
# - "tailing file" - Found log files
# - "exporting" - Sending to OTel Gateway
```

## Step 3: Verify on Meta Server

```bash
# SSH to Meta
ssh user@159.56.4.94

# Navigate to project
cd ~/seefa-om

# Make verification script executable
chmod +x mdso-alloy/verify-on-meta.sh

# Run verification
./mdso-alloy/verify-on-meta.sh
```

**What to Look For:**
- OTel Gateway logs showing received logs
- Metrics showing `otelcol_receiver_accepted_log_records`
- Correlation engine receiving logs (if enabled)

## Step 4: Manual Verification

### On MDSO Dev:
```bash
# Check container is running
docker ps | grep alloy-test

# Check Alloy is reading files
docker exec alloy-test ls -la /var/log/ciena/
docker exec alloy-test tail -5 /var/log/ciena/blueplanet.log

# Test Meta connectivity from container
docker exec alloy-test wget -qO- http://159.56.4.94:55681/v1/logs
```

### On Meta:
```bash
# Check OTel Gateway logs
docker-compose logs --tail 100 otel-gateway | grep -i "log"

# Check OTel Gateway metrics
curl -s http://localhost:8888/metrics | grep "otelcol_receiver_accepted_log_records"

# Check correlation engine (if logs are forwarded)
docker-compose logs --tail 50 correlation-engine
```

## Troubleshooting

### No logs in OTel Gateway

**Check Alloy is sending:**
```bash
# On MDSO Dev
docker logs alloy-test | grep -i "export\|error"
```

**Check network:**
```bash
# From MDSO Dev container
docker exec alloy-test ping -c 2 159.56.4.94
docker exec alloy-test curl -v http://159.56.4.94:55681/v1/logs
```

### Alloy not reading files

**Check file permissions:**
```bash
# On MDSO Dev
ls -la /var/log/ciena/blueplanet.log
ls -la /bp2/log/

# Check container can access
docker exec alloy-test ls -la /var/log/ciena/
```

**Check file has content:**
```bash
tail -10 /var/log/ciena/blueplanet.log
```

### Container won't start

**Check logs:**
```bash
docker logs alloy-test
```

**Check config syntax:**
```bash
docker run --rm -v $(pwd)/config-test-otel-only.alloy:/config.alloy \
  grafana/alloy:latest \
  run --dry-run /config.alloy
```

## Success Criteria

✅ Alloy container running on MDSO Dev  
✅ Alloy logs show "tailing file"  
✅ OTel Gateway logs show received log records  
✅ OTel Gateway metrics show `otelcol_receiver_accepted_log_records > 0`  

## Next Steps (After Test Success)

Once logs are flowing to OTel Gateway:

1. **Add Loki**: OTel Gateway already exports to Loki (configured)
2. **Verify in Grafana**: Query `{service="mdso"}` in Loki
3. **Add Tempo**: For trace correlation (if needed)
4. **Switch to full config**: Use `config.alloy` instead of `config-test-otel-only.alloy`

## Cleanup

```bash
# Stop test container
docker-compose -f docker-compose-test.yml down

# Remove test container and volumes
docker-compose -f docker-compose-test.yml down -v
```

## Files Reference

- `config-test-otel-only.alloy` - Minimal test config (OTel only)
- `docker-compose-test.yml` - Test container setup
- `test-otel-only.sh` - Automated test deployment
- `verify-on-meta.sh` - Verification script for Meta server
- `config.alloy` - Full production config (use after test)
- `docker-compose.yml` - Production container setup
