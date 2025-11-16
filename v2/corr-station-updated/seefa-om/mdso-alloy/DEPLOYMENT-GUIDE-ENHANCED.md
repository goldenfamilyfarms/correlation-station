# Enhanced Alloy Configuration Deployment Guide

## Overview

This guide covers deploying the **enhanced** Alloy configuration with comprehensive structured field extraction for improved correlation performance.

## What's New in Enhanced Config

The enhanced `config.alloy` now extracts **13 structured fields** from MDSO (Multi-Domain Service Orchestrator) log messages:

### Business Identifiers
- **circuit_id** - Circuit IDs like `80.L1XX.005054..CHTR`
- **resource_id** - UUIDs for resources
- **product_id** - UUIDs for products

### Device Context
- **device_fqdn** - Fully qualified domain names (e.g., `JFVLINBJ2CW.CHTRSE.COM`)
- **device_tid** - 10-character device identifiers
- **vendor** - Network vendor (juniper, adva, cisco, rad)
- **management_ip** - Device management IPs

### Operational Context
- **orch_state** - Orchestration states (CREATE_IN_PROGRESS, etc.)
- **service_type** - Service types (ELAN, ELINE, FIA, VOICE, VIDEO)
- **product_type** - Product types (service_mapper, network_service, etc.)

### Error Tracking
- **error_code** - Error/defect codes (DE-1000, DEF-123, etc.)
- **severity** - Normalized severity levels (INFO, WARN, ERROR, FATAL, DEBUG)
- **management_ip** - Device management IP addresses

## Prerequisites

### On MDSO Dev Server (159.56.4.37)
- Docker installed and running
- Access to log directories:
  - `/var/log/ciena/blueplanet.log`
  - `/bp2/log/*.log`
- Network connectivity to Meta server (159.56.4.94) on port 55681
- User: `bpadmin` (or appropriate user with Docker permissions)

### On Meta Server (159.56.4.94)
- OTel Gateway running on port 55681
- Correlation Engine running (for full pipeline testing)
- Loki, Tempo, Prometheus (for end-to-end verification)

## Deployment Steps

### Step 1: Copy Files to MDSO Server

From your workstation:

```bash
# Navigate to the mdso-alloy directory
cd /path/to/correlation-station/v2/corr-station-updated/seefa-om/mdso-alloy

# Copy entire directory to MDSO server
scp -r . bpadmin@159.56.4.37:~/alloy-agent/

# Or use rsync for updates
rsync -avz --exclude='*.log' . bpadmin@159.56.4.37:~/alloy-agent/
```

### Step 2: SSH to MDSO Server

```bash
ssh bpadmin@159.56.4.37
cd ~/alloy-agent
```

### Step 3: Verify Prerequisites

```bash
# Check Docker is running
docker ps

# Verify log directories exist and have content
ls -lh /var/log/ciena/blueplanet.log
ls -lh /bp2/log/

# Test connectivity to Meta server
curl -v http://159.56.4.94:55681/v1/logs
# Should return 404 or 405 (endpoint exists but wrong method is OK)
```

### Step 4: Review Configuration

```bash
# View the enhanced config
cat config.alloy | less

# Check for your specific log patterns
grep "circuit" config.alloy
grep "resource" config.alloy
grep "vendor" config.alloy
```

### Step 5: Deploy Alloy Container

#### Option A: Using Deployment Script (Recommended)

```bash
# Make script executable
chmod +x deploy-container.sh

# Deploy
./deploy-container.sh
```

The script will:
1. Check connectivity to Meta server
2. Stop existing Alloy container (if running)
3. Start new container with enhanced config
4. Show container status and logs

#### Option B: Manual Deployment

```bash
# Stop and remove existing container
docker stop alloy-mdso 2>/dev/null || true
docker rm alloy-mdso 2>/dev/null || true

# Pull latest Alloy image
docker pull grafana/alloy:latest

# Start with docker-compose
docker-compose up -d

# Or start manually
docker run -d \
  --name alloy-mdso \
  --restart unless-stopped \
  --network host \
  -v $(pwd)/config.alloy:/etc/alloy/config.alloy:ro \
  -v /var/log/ciena:/var/log/ciena:ro \
  -v /bp2/log:/bp2/log:ro \
  -p 12345:12345 \
  grafana/alloy:latest \
  run /etc/alloy/config.alloy \
  --server.http.listen-addr=0.0.0.0:12345 \
  --storage.path=/var/lib/alloy/data
```

### Step 6: Verify Deployment

```bash
# Check container is running
docker ps | grep alloy-mdso

# View logs (should see initialization messages)
docker logs alloy-mdso

# Look for successful startup indicators:
# - "component started"
# - "tailing file"
# - No errors

# Follow logs in real-time
docker logs -f alloy-mdso
```

### Step 7: Access Alloy UI

Open browser to:
```
http://159.56.4.37:12345
```

You should see:
- Alloy dashboard with component status
- Graph showing pipeline flow
- All components showing "healthy" status

## Verification Steps

### On MDSO Server

#### 1. Check Log File Access

```bash
# Verify Alloy can access log files
docker exec alloy-mdso ls -la /var/log/ciena/
docker exec alloy-mdso ls -la /bp2/log/

# Test reading a log file
docker exec alloy-mdso head -n 5 /var/log/ciena/blueplanet.log
```

#### 2. Monitor Processing

```bash
# Watch for field extraction in logs
docker logs -f alloy-mdso | grep -E "circuit|resource|vendor"

# Check for export activity
docker logs alloy-mdso | grep -i "export"

# Look for errors
docker logs alloy-mdso | grep -i "error"
```

#### 3. Test Network Connectivity

```bash
# Test OTLP endpoint from container
docker exec alloy-mdso wget -qO- http://159.56.4.94:55681/v1/logs || echo "Endpoint reachable"
```

### On Meta Server (159.56.4.94)

#### 1. Check OTel Gateway Reception

```bash
# SSH to Meta server
ssh user@159.56.4.94

# Check gateway logs for MDSO logs
docker-compose logs --tail 100 otel-gateway | grep -i "mdso"

# Check metrics
curl -s http://localhost:8888/metrics | grep "otelcol_receiver_accepted_log_records"
```

#### 2. Verify Field Extraction in Loki

```bash
# Query Loki for MDSO logs with circuit_id
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=10' | jq '.data.result[].values[]'

# Check if structured fields are present
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso", circuit_id!=""}' \
  --data-urlencode 'limit=5' | jq
```

#### 3. Check Correlation Engine

```bash
# View correlation engine logs
docker-compose logs --tail 50 correlation-engine | grep -i "mdso"

# Check correlation metrics
curl http://localhost:8080/metrics | grep "mdso"

# Check health endpoint
curl http://localhost:8080/health | jq
```

#### 4. Verify in Grafana

1. Open browser: `http://159.56.4.94:8443`
2. Login (default: admin/admin)
3. Go to **Explore** → **Loki**
4. Query: `{service="mdso"}`
5. Click on a log entry to see **extracted fields**:
   - circuit_id
   - resource_id
   - device_tid
   - vendor
   - orch_state
   - etc.

## Field Extraction Validation

To test if fields are being extracted correctly, generate test log entries:

```bash
# On MDSO server, create a test log entry
echo "$(date '+%b %d %H:%M:%S') mdso-host ServiceMapper: Creating circuit 80.L1XX.005054..CHTR with resource 550e8400-e29b-41d4-a716-446655440000 on device JFVLINBJ2CW.CHTRSE.COM (vendor: juniper)" >> /var/log/ciena/blueplanet.log

# Wait 10 seconds, then check in Grafana
# You should see:
# - circuit_id = "80.L1XX.005054..CHTR"
# - resource_id = "550e8400-e29b-41d4-a716-446655440000"
# - device_fqdn = "JFVLINBJ2CW.CHTRSE.COM"
# - device_tid = "JFVLINBJ2CW"
# - vendor = "juniper"
# - product_type = "service_mapper"
```

## Operational Commands

### Start/Stop/Restart

```bash
# Stop Alloy
docker-compose down
# Or
docker stop alloy-mdso

# Start Alloy
docker-compose up -d
# Or
docker start alloy-mdso

# Restart Alloy (reload config)
docker-compose restart
# Or
docker restart alloy-mdso
```

### Configuration Updates

After modifying `config.alloy`:

```bash
# Validate syntax (optional, if alloy CLI available)
alloy fmt --check config.alloy

# Restart to apply changes
docker-compose restart

# Verify new config loaded
docker logs --tail 50 alloy-mdso | grep "config"
```

### Log Management

```bash
# View real-time logs
docker logs -f alloy-mdso

# View last 100 lines
docker logs --tail 100 alloy-mdso

# Search for errors
docker logs alloy-mdso | grep -i error

# Search for specific field extractions
docker logs alloy-mdso | grep -i "circuit_id"

# Export logs to file
docker logs alloy-mdso > alloy-debug.log
```

### Health Checks

```bash
# Check container health
docker inspect alloy-mdso | jq '.[0].State.Health'

# Check Alloy HTTP endpoint
curl http://159.56.4.37:12345/ready
curl http://159.56.4.37:12345/metrics

# Check specific component status
curl http://159.56.4.37:12345/api/v1/components | jq
```

## Troubleshooting

### Container Won't Start

```bash
# Check Docker daemon
sudo systemctl status docker

# Check for port conflicts
netstat -tuln | grep 12345

# Check config syntax
docker run --rm -v $(pwd)/config.alloy:/config.alloy grafana/alloy:latest fmt --check /config.alloy

# View startup errors
docker logs alloy-mdso 2>&1 | head -50
```

### No Logs Being Collected

```bash
# Verify file permissions
ls -la /var/log/ciena/blueplanet.log
ls -la /bp2/log/

# Check if files exist in container
docker exec alloy-mdso ls -la /var/log/ciena/
docker exec alloy-mdso ls -la /bp2/log/

# Check if Alloy is tailing files
docker logs alloy-mdso | grep -i "tailing"

# Verify file match component
curl http://159.56.4.37:12345/api/v1/components | jq '.components[] | select(.name | contains("file_match"))'
```

### Logs Not Reaching Meta Server

```bash
# Test connectivity from container
docker exec alloy-mdso curl -v http://159.56.4.94:55681/v1/logs

# Check for network issues
docker exec alloy-mdso ping -c 3 159.56.4.94

# Check export logs
docker logs alloy-mdso | grep -i "export\|send\|otlp"

# Verify OTLP exporter config
curl http://159.56.4.37:12345/api/v1/components | jq '.components[] | select(.name | contains("otlphttp"))'
```

### Fields Not Being Extracted

```bash
# Check if regex patterns are working
docker logs alloy-mdso | grep -i "regex\|stage"

# View processed logs with debug
# (Add --log.level=debug to docker run command)

# Test regex patterns manually (see TESTING-GUIDE-ENHANCED.md)

# Check structured_metadata configuration
curl http://159.56.4.37:12345/api/v1/components | jq '.components[] | select(.name | contains("normalize"))'
```

### High CPU/Memory Usage

```bash
# Check resource usage
docker stats alloy-mdso

# Reduce processing if needed (config.alloy):
# - Limit file paths
# - Reduce regex complexity
# - Add sampling

# Restart with resource limits
docker run -d \
  --name alloy-mdso \
  --cpus="1.0" \
  --memory="512m" \
  ... (rest of docker run command)
```

## Rollback Procedure

If the enhanced config causes issues:

### Option 1: Revert to Previous Config

```bash
# Copy backup (if you made one)
cp config.alloy.backup config.alloy

# Restart
docker-compose restart
```

### Option 2: Use Simplified Config

```bash
# Use one of the test configs
cp config-test1-pure-otel.alloy config.alloy

# Restart
docker-compose restart
```

### Option 3: Complete Removal

```bash
# Stop and remove container
docker-compose down

# Remove image (optional)
docker rmi grafana/alloy:latest
```

## Performance Tuning

### Optimize for High Volume

If processing many logs per second:

```bash
# Edit docker-compose.yml to add resources
services:
  alloy:
    ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '1.0'
          memory: 512M
```

### Batch Configuration

Add to `config.alloy` in the exporter section:

```hcl
otelcol.exporter.otlphttp "meta" {
  client {
    endpoint = "http://159.56.4.94:55681"
    timeout = "30s"  # Increase timeout
  }

  sending_queue {
    enabled = true
    num_consumers = 10
    queue_size = 1000
  }
}
```

## Monitoring and Alerting

### Key Metrics to Monitor

```bash
# On Alloy (http://159.56.4.37:12345/metrics)
- alloy_loki_source_file_read_bytes_total
- alloy_loki_source_file_read_lines_total
- otelcol_exporter_sent_log_records
- otelcol_exporter_send_failed_log_records

# On Meta Gateway (http://159.56.4.94:8888/metrics)
- otelcol_receiver_accepted_log_records
- otelcol_processor_batch_batch_send_size
```

### Set Up Grafana Dashboard

Import dashboard from: `correlation-station/grafana/dashboards/alloy-monitoring.json` (if available)

Or create custom dashboard with panels for:
- Log ingestion rate
- Field extraction success rate
- Export success/failure rate
- Container resource usage

## Production Checklist

Before going to production:

- [ ] Config tested with real MDSO logs
- [ ] All expected fields being extracted
- [ ] Logs visible in Loki
- [ ] Logs visible in Grafana
- [ ] Correlation engine receiving structured fields
- [ ] Circuit IDs correlating with traces
- [ ] Container auto-restart configured (`restart: unless-stopped`)
- [ ] Monitoring dashboard created
- [ ] Alerts configured for failures
- [ ] Backup of config.alloy created
- [ ] Rollback procedure tested
- [ ] Documentation updated for team

## Next Steps

After successful deployment:

1. **Monitor for 24 hours** - Watch for any errors or performance issues
2. **Validate field extraction** - Check that all expected fields are being captured
3. **Tune regex patterns** - Adjust patterns based on actual log formats
4. **Configure alerts** - Set up alerts for export failures or field extraction issues
5. **Document edge cases** - Note any log formats that don't match patterns
6. **Update correlation rules** - Ensure correlation engine uses new fields
7. **Train team** - Share knowledge about new capabilities

## Support

For issues or questions:
- Check logs: `docker logs alloy-mdso`
- Review documentation in this directory
- Check Alloy docs: https://grafana.com/docs/alloy/
- See TESTING-GUIDE-ENHANCED.md for detailed testing procedures
