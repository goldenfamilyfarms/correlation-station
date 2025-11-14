# Three-Phase Testing Guide

## Overview

Progressive testing approach to validate the full observability pipeline:

1. **Test 1**: Pure OTel components (simplest)
2. **Test 2**: Loki components pipeline (comparison)
3. **Test 3**: Full pipeline with correlation (production-ready)

## Test Architecture

### Test 1: Pure OTel
```
MDSO Dev                           Meta
┌─────────────────┐               ┌──────────────┐
│ Alloy           │               │ OTel Gateway │
│ • filelog       │─────OTLP─────▶│ • Receives   │
│ • resource      │               │ • Logs       │
│ • otlphttp      │               └──────────────┘
└─────────────────┘
```

### Test 2: Loki Components
```
MDSO Dev                           Meta
┌─────────────────┐               ┌──────────────┐
│ Alloy           │               │ OTel Gateway │
│ • loki.source   │               │ • Receives   │
│ • loki.process  │─────OTLP─────▶│ • Logs       │
│ • otelcol.recv  │               └──────────────┘
│ • otlphttp      │
└─────────────────┘
```

### Test 3: Full Pipeline
```
MDSO Dev                           Meta
┌─────────────────┐               ┌──────────────────────────────────┐
│ Alloy           │               │ OTel Gateway                     │
│ • loki.source   │               │   ↓                              │
│ • loki.process  │─────OTLP─────▶│ Correlation Engine               │
│ • normalize     │               │   ↓                              │
│ • otlphttp      │               │ OTel Gateway (enriched)          │
└─────────────────┘               │   ↓         ↓                    │
                                  │ Loki      Tempo                  │
                                  └──────────────────────────────────┘
```

## Prerequisites

### On MDSO Dev (159.56.4.37)
- Docker installed
- Access to `/var/log/ciena/` and `/bp2/log/`
- Network access to Meta on port 55681

### On Meta (159.56.4.94)
- All services running: `docker-compose ps`
- OTel Gateway listening on port 55681
- Loki, Tempo, Correlation Engine running (for Test 3)

## Test 1: Pure OTel Components

### Deploy
```bash
# On MDSO Dev
cd ~/alloy-agent
chmod +x test1-pure-otel.sh
./test1-pure-otel.sh
```

### Monitor
```bash
# Watch Alloy logs
docker logs -f alloy-test1

# Look for:
# - "component started" - Alloy initialized
# - "Reading file" - Found log files
# - No errors
```

### Verify on Meta
```bash
# SSH to Meta
ssh user@159.56.4.94

# Check OTel Gateway logs
docker-compose logs --tail 50 otel-gateway | grep -i "log"

# Check metrics
curl -s http://localhost:8888/metrics | grep "otelcol_receiver_accepted_log_records"
```

### Success Criteria
- ✅ Container running on MDSO
- ✅ Alloy reading log files
- ✅ OTel Gateway receiving logs
- ✅ Metrics show `otelcol_receiver_accepted_log_records > 0`

### Stop Test 1
```bash
docker stop alloy-test1
docker rm alloy-test1
```

## Test 2: Loki Components Pipeline

### Deploy
```bash
# On MDSO Dev
cd ~/alloy-agent
chmod +x test2-loki-components.sh
./test2-loki-components.sh
```

### Monitor
```bash
# Watch Alloy logs
docker logs -f alloy-test2

# Look for:
# - "tailing file" - Loki source active
# - "processing" - Loki pipeline working
# - No errors
```

### Verify on Meta
```bash
# Same as Test 1
docker-compose logs --tail 50 otel-gateway | grep -i "log"
curl -s http://localhost:8888/metrics | grep "otelcol_receiver_accepted_log_records"
```

### Compare with Test 1
- Are logs formatted differently?
- Is throughput similar?
- Any performance differences?

### Success Criteria
- ✅ Container running on MDSO
- ✅ Loki components processing logs
- ✅ OTel Gateway receiving logs
- ✅ Similar or better performance than Test 1

### Stop Test 2
```bash
docker stop alloy-test2
docker rm alloy-test2
```

## Test 3: Full Pipeline with Correlation

### Ensure Meta Services Running
```bash
# On Meta
cd ~/seefa-om
docker-compose ps

# Should show all services running:
# - otel-gateway
# - correlation-engine
# - loki
# - tempo
# - prometheus
# - grafana

# If not, start them:
make start-all
```

### Deploy
```bash
# On MDSO Dev
cd ~/alloy-agent
chmod +x test3-full-pipeline.sh
./test3-full-pipeline.sh
```

### Monitor
```bash
# Watch Alloy logs
docker logs -f alloy-test3

# Look for:
# - "tailing file" - Reading logs
# - "parsing" - Syslog normalization
# - "exporting" - Sending to OTel Gateway
```

### Verify Full Pipeline on Meta

#### 1. OTel Gateway
```bash
docker-compose logs --tail 50 otel-gateway | grep -i "mdso"
```

#### 2. Correlation Engine
```bash
docker-compose logs --tail 50 correlation-engine | grep -i "mdso"

# Check correlation metrics
curl http://localhost:8080/metrics | grep "log_records_received"
```

#### 3. Loki
```bash
# Query for MDSO logs
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=10' | jq
```

#### 4. Grafana
```bash
# Open browser
http://159.56.4.94:3000

# Navigate to Explore → Loki
# Query: {service="mdso"}
```

### Success Criteria
- ✅ Alloy reading and parsing logs
- ✅ OTel Gateway receiving logs
- ✅ Correlation Engine processing logs
- ✅ Logs visible in Loki
- ✅ Logs visible in Grafana
- ✅ Correlation metrics increasing

### Keep Running
```bash
# Test 3 can stay running for production use
docker logs -f alloy-test3
```

## Troubleshooting

### No logs in OTel Gateway

**Check Alloy:**
```bash
docker logs alloy-test3 | grep -i "error\|warn"
docker exec alloy-test3 ls -la /var/log/ciena/
```

**Check connectivity:**
```bash
docker exec alloy-test3 curl -v http://159.56.4.94:55681/v1/logs
```

### Logs in Gateway but not in Loki

**Check Loki:**
```bash
docker-compose logs loki | grep -i "error"
curl http://localhost:3100/ready
```

**Check Gateway → Loki export:**
```bash
docker-compose logs otel-gateway | grep -i "loki"
```

### Correlation Engine not receiving

**Check Gateway config:**
```bash
cat gateway/otel-config.yaml | grep -A 10 "correlation"
```

**Check Correlation Engine:**
```bash
docker-compose logs correlation-engine
curl http://localhost:8080/health
```

## Cleanup

### Stop specific test
```bash
docker stop alloy-test1  # or test2, test3
docker rm alloy-test1
```

### Stop all tests
```bash
docker stop alloy-test1 alloy-test2 alloy-test3 2>/dev/null || true
docker rm alloy-test1 alloy-test2 alloy-test3 2>/dev/null || true
```

## Files Reference

| File | Purpose |
|------|---------|
| `config-test1-pure-otel.alloy` | Test 1 config |
| `config-test2-loki-components.alloy` | Test 2 config |
| `config-test3-full-pipeline.alloy` | Test 3 config |
| `test1-pure-otel.sh` | Deploy Test 1 |
| `test2-loki-components.sh` | Deploy Test 2 |
| `test3-full-pipeline.sh` | Deploy Test 3 |
| `verify-test.sh` | Verification helper |

## Next Steps

After successful Test 3:
1. Rename `alloy-test3` to `alloy-mdso` for production
2. Add to systemd or docker-compose for auto-start
3. Set up log rotation
4. Configure alerts in Grafana
5. Document operational procedures
