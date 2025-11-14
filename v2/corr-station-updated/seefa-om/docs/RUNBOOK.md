# Observability PoC - Operations Runbook

## Table of Contents
1. [Service Overview](#service-overview)
2. [Common Operations](#common-operations)
3. [Troubleshooting Guide](#troubleshooting-guide)
4. [Alert Response](#alert-response)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Disaster Recovery](#disaster-recovery)

---

## Service Overview

### Architecture Components

| Component | Purpose | Port | Health Check |
|-----------|---------|------|--------------|
| Grafana | Visualization & dashboards | 3000 | `http://localhost:3000/api/health` |
| Loki | Log aggregation | 3100 | `http://localhost:3100/ready` |
| Tempo | Distributed tracing | 3200 | `http://localhost:3200/ready` |
| Prometheus | Metrics storage | 9090 | `http://localhost:9090/-/healthy` |
| OTel Gateway | Telemetry router | 4317, 4318 | `http://localhost:13133` |
| Correlation Engine | Log/trace correlation | 8080 | `http://localhost:8080/health` |
| Beorn | Sense app (Flask) | 5001 | `http://localhost:5001/health` |
| Palantir | Sense app (Flask) | 5002 | `http://localhost:5002/health` |
| Arda | Sense app (FastAPI) | 5003 | `http://localhost:5003/health` |

### Data Flow

```
MDSO Alloy → OTel Gateway → Correlation Engine → Loki/Tempo
Sense Apps → OTel Gateway → Correlation Engine → Loki/Tempo
```

---

## Common Operations

### Starting Services

```bash
# Start all services
make up

# Start specific service
docker-compose up -d correlation-engine

# Start with rebuild
docker-compose up -d --build
```

### Stopping Services

```bash
# Stop all services
make down

# Stop specific service
docker-compose stop correlation-engine

# Stop and remove volumes (DESTRUCTIVE)
make clean
```

### Checking Status

```bash
# Check all services
make health

# Check specific service
curl http://localhost:8080/health

# View running containers
docker-compose ps

# View resource usage
docker stats
```

### Viewing Logs

```bash
# All logs
make logs

# Specific service
docker-compose logs -f correlation-engine

# Last 100 lines
docker-compose logs --tail=100 correlation-engine

# Since timestamp
docker-compose logs --since 2025-10-15T10:00:00 correlation-engine
```

### Restarting Services

```bash
# Restart all
make restart

# Restart specific service
docker-compose restart correlation-engine

# Restart with config reload
docker-compose up -d --force-recreate correlation-engine
```

---

## Troubleshooting Guide

### Issue: Correlation Engine Not Starting

**Symptoms:**
- Container keeps restarting
- Health check fails

**Diagnosis:**
```bash
# Check logs
docker-compose logs correlation-engine

# Check container status
docker-compose ps correlation-engine

# Inspect container
docker inspect observability-poc_correlation-engine
```

**Common Causes & Solutions:**

1. **Port already in use:**
   ```bash
   # Find process using port 8080
   sudo lsof -i :8080
   # Kill process or change port in docker-compose.yml
   ```

2. **Missing environment variables:**
   ```bash
   # Check .env file exists
   ls -la .env
   # Verify required variables
   docker-compose config
   ```

3. **Loki/Tempo not reachable:**
   ```bash
   # Check backend services are running
   docker-compose ps loki tempo
   # Test connectivity
   docker-compose exec correlation-engine curl http://loki:3100/ready
   ```

### Issue: No Logs in Loki

**Symptoms:**
- Loki is running but no logs appear in Grafana
- Empty query results

**Diagnosis:**
```bash
# Check Loki status
curl http://localhost:3100/ready

# Query Loki directly
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service=~".+"}' \
  --data-urlencode 'limit=10'

# Check OTel Gateway logs
docker-compose logs otel-gateway | grep loki
```

**Solutions:**

1. **Verify log ingestion:**
   ```bash
   # Send test log
   make test-logs
   # Check if it appears
   curl -G 'http://localhost:3100/loki/api/v1/query' \
     --data-urlencode 'query={service="test"}'
   ```

2. **Check label cardinality:**
   ```bash
   # High cardinality causes ingestion failures
   make check-cardinality
   # If too many unique label combinations, review label usage
   ```

3. **Verify disk space:**
   ```bash
   df -h
   du -sh /var/lib/docker/volumes/*loki*
   ```

### Issue: Traces Not Appearing in Tempo

**Symptoms:**
- No traces in Tempo search
- Grafana can't find traces

**Diagnosis:**
```bash
# Check Tempo status
curl http://localhost:3200/ready

# Search for traces
curl 'http://localhost:3200/api/search?tags=service.name=beorn&limit=10'

# Check Gateway logs
docker-compose logs otel-gateway | grep tempo
```

**Solutions:**

1. **Verify OTLP exporter:**
   ```bash
   # Test trace ingestion
   make test-trace

   # Check sense app logs for OTLP export errors
   docker-compose logs beorn | grep -i error
   ```

2. **Check Tempo storage:**
   ```bash
   # Verify blocks are being created
   docker-compose exec tempo ls -la /var/tempo/blocks
   ```

3. **Validate trace ID format:**
   - Trace IDs must be 32 hex characters
   - Check logs for malformed trace IDs

### Issue: High Disk Usage

**Symptoms:**
- Disk full alerts
- Services failing due to no space

**Diagnosis:**
```bash
# Check overall disk usage
make check-disk

# Check Docker volumes
docker system df -v

# Check specific volumes
du -sh /var/lib/docker/volumes/observability-stack_loki-data
du -sh /var/lib/docker/volumes/observability-stack_tempo-data
```

**Solutions:**

1. **Immediate relief:**
   ```bash
   # Prune unused resources
   make prune

   # Remove old logs (CAREFUL)
   docker-compose exec loki rm -rf /loki/chunks/fake/*
   ```

2. **Long-term fixes:**
   - Reduce retention periods (default: 7 days)
   - Implement log sampling
   - Set up remote storage
   - Add disk monitoring alerts

### Issue: Correlation Events Not Being Created

**Symptoms:**
- `/api/correlations` returns empty
- `correlation_events_total` metric is 0

**Diagnosis:**
```bash
# Check correlation engine is receiving logs
docker-compose logs correlation-engine | grep logs_ingested

# Check correlation metrics
curl http://localhost:8080/metrics | grep correlation

# Verify correlation window setting
docker-compose exec correlation-engine env | grep CORR_WINDOW
```

**Solutions:**

1. **Verify logs have trace_id:**
   ```bash
   # Logs need trace_id to be correlated
   curl 'http://localhost:3100/loki/api/v1/query' \
     --data-urlencode 'query={trace_id=~".+"}' \
     --data-urlencode 'limit=10'
   ```

2. **Check correlation window:**
   - Default is 60s - traces/logs must arrive within this window
   - Increase if needed: `CORR_WINDOW_SECONDS=120`

3. **Review correlation engine logs:**
   ```bash
   docker-compose logs correlation-engine | grep correlation_window_closed
   ```

### Issue: Alloy Not Sending Logs from MDSO

**Symptoms:**
- No logs from MDSO in Loki
- No `blueplanet` service logs

**Diagnosis:**
```bash
# On MDSO Dev host
sudo systemctl status alloy
sudo journalctl -u alloy -f

# Check connectivity to Server-124
curl -X POST http://159.56.4.94:4318/v1/logs \
  -H "Content-Type: application/json" \
  -d '{"resourceLogs":[]}'
```

**Solutions:**

1. **Verify Alloy is running:**
   ```bash
   # On MDSO Dev
   sudo systemctl start alloy
   sudo systemctl enable alloy
   ```

2. **Check log file paths:**
   ```bash
   # Verify syslog files exist
   ls -la /var/log/ciena/blueplanet.log
   ls -la /bp2/log/*.log
   ```

3. **Test Alloy config:**
   ```bash
   alloy run --config /etc/alloy/config.alloy --dry-run
   ```

4. **Check network connectivity:**
   ```bash
   # Firewall rules
   sudo iptables -L | grep 4318
   # Test port
   telnet 159.56.4.94 4318
   ```

### Issue: High Memory Usage

**Symptoms:**
- OOM killer terminating containers
- Slow performance

**Diagnosis:**
```bash
# Check memory usage
docker stats

# Check memory limits
docker inspect correlation-engine | grep -i memory
```

**Solutions:**

1. **Add memory limits to docker-compose.yml:**
   ```yaml
   services:
     correlation-engine:
       mem_limit: 512m
       memswap_limit: 1g
   ```

2. **Tune correlation engine:**
   ```bash
   # Reduce batch sizes
   MAX_BATCH_SIZE=1000
   CORR_WINDOW_SECONDS=30
   ```

3. **Add more RAM or scale horizontally**

---

## Alert Response

### Critical Alerts

#### Alert: Service Down

**Impact:** High - Service unavailable

**Response:**
1. Check service status: `docker-compose ps`
2. Review logs: `docker-compose logs [service]`
3. Restart service: `docker-compose restart [service]`
4. If restart fails, check disk space and memory
5. Escalate if not resolved in 10 minutes

#### Alert: Disk Usage >90%

**Impact:** High - Risk of service failure

**Response:**
1. Check disk usage: `df -h`
2. Identify large volumes: `du -sh /var/lib/docker/volumes/*`
3. Prune unused resources: `make prune`
4. If Loki/Tempo data is large, consider reducing retention
5. Plan for storage expansion

#### Alert: High Error Rate

**Impact:** Medium - Data loss possible

**Response:**
1. Check correlation engine metrics: `make metrics`
2. Review error logs: `docker-compose logs | grep ERROR`
3. Identify failing component
4. Check backend connectivity (Loki, Tempo)
5. Review recent changes

### Warning Alerts

#### Alert: Memory Usage >80%

**Impact:** Medium - Performance degradation

**Response:**
1. Check memory usage: `docker stats`
2. Identify memory-intensive container
3. Consider adding memory limits
4. Plan for scaling

#### Alert: Slow Queries

**Impact:** Low - User experience degraded

**Response:**
1. Check Grafana query performance
2. Review Loki label cardinality: `make check-cardinality`
3. Optimize dashboard queries
4. Consider adding indexes

---

## Maintenance Procedures

### Rolling Restart

```bash
# Restart services one by one with zero downtime
docker-compose up -d --no-deps --scale correlation-engine=2 correlation-engine
sleep 30
docker-compose up -d --no-deps --scale correlation-engine=1 correlation-engine
```

### Updating Configuration

```bash
# 1. Update config file
vim observability-stack/loki/loki-config.yaml

# 2. Validate
docker-compose config

# 3. Restart service
docker-compose up -d --force-recreate loki

# 4. Verify
curl http://localhost:3100/ready
```

### Database Compaction

```bash
# Loki compaction (automatic, but can be triggered)
docker-compose exec loki wget -qO- http://localhost:3100/loki/api/v1/delete

# Tempo compaction (automatic via config)
# Check compactor logs
docker-compose logs tempo | grep compactor
```

### Backup Dashboards

```bash
# Backup all Grafana dashboards
make backup-dashboards

# Backup to remote
scp -r backups/ backup-server:/backups/observability-poc/
```

### Update Images

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Verify versions
docker-compose images
```

---

## Disaster Recovery

### Complete System Failure

**Recovery Steps:**

1. **Verify Server-124 is accessible:**
   ```bash
   ssh user@159.56.4.94
   ```

2. **Check Docker daemon:**
   ```bash
   sudo systemctl status docker
   sudo systemctl start docker
   ```

3. **Restore from backup:**
   ```bash
   cd /opt/observability-poc
   git pull origin main
   docker-compose up -d
   ```

4. **Verify all services:**
   ```bash
   make health
   ```

5. **Restore dashboards:**
   ```bash
   make restore-dashboards
   ```

### Data Loss

**Prevention:**
- Daily backups of Grafana dashboards
- Prometheus remote write to long-term storage
- Loki compaction enabled
- Regular volume snapshots

**Recovery:**
- Restore from most recent backup
- Accept data loss for time-series (not recoverable)
- Recreate dashboards from code

### Network Partition

**Symptoms:**
- Alloy can't reach Server-124
- Sense apps can't reach Gateway

**Response:**
1. Verify network connectivity
2. Check security group rules
3. Test ports: `telnet 159.56.4.94 4318`
4. Review firewall logs
5. Coordinate with network team

---

## Appendix

### Useful Commands

```bash
# Enter container shell
docker-compose exec correlation-engine /bin/bash

# Copy files from container
docker cp observability-poc_correlation-engine:/app/logs/error.log ./

# View container resource limits
docker inspect correlation-engine | grep -i resources -A 20

# Force container restart
docker-compose kill correlation-engine && docker-compose up -d correlation-engine

# Export logs to file
docker-compose logs --no-color > debug.log
```

### Emergency Contacts

- **SRE On-Call:** #observability-oncall
- **Development Team:** #sense-dev
- **Network Team:** #network-ops
- **Security Team:** #security

### Related Documentation

- [Architecture Overview](../README.md)
- [API Documentation](http://159.56.4.94:8080/docs)
- [Grafana Dashboards](http://159.56.4.94:3000)
- [OpenTelemetry Docs](https://opentelemetry.io/docs/)