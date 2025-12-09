# Complete Manual Implementation Guide
## Correlation Station - Full Stack Observability Platform

**Version:** 2.0.0
**Last Updated:** 2025-11-16
**Author:** Derrick Golden

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Quick Start (Automated)](#quick-start-automated)
5. [Manual Setup (Step-by-Step)](#manual-setup-step-by-step)
6. [Component Details](#component-details)
7. [Horizontal Scaling with Redis](#horizontal-scaling-with-redis)
8. [Load Testing with K6](#load-testing-with-k6)
9. [Operations & Maintenance](#operations--maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Rollback Procedures](#rollback-procedures)
12. [Advanced Topics](#advanced-topics)

---

## Overview

This guide provides complete instructions for manually setting up the Correlation Station observability platform. You can choose between an automated setup (one command) or manual step-by-step deployment.

### What You'll Deploy

- **Observability Stack:** Grafana, Loki, Tempo, Prometheus, Pyroscope
- **OTel Gateway:** OpenTelemetry Collector for telemetry ingestion
- **Correlation Engine:** FastAPI-based correlation service
- **Redis:** State management for horizontal scaling
- **Sense Apps:** Three sample instrumented applications (Beorn, Palantir, Arda)
- **Frontend UI:** React-based training and documentation portal
- **K6:** Load testing framework

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND TIER                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Frontend UI (React + Nginx)        :3000               │   │
│  │ • Training portal                                       │   │
│  │ • Documentation (TraceQL, PromQL, OTel)                │   │
│  │ • SECA error reviews                                   │   │
│  └──────────────────┬──────────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────────┘
                     │ Proxy /api/* to :8080
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CORRELATION TIER                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Correlation Engine (FastAPI)       :8080               │   │
│  │ • OTLP ingestion                                       │   │
│  │ • Windowed correlation (60s)                           │   │
│  │ • Redis-backed state (optional)                        │   │
│  │ • Horizontal scaling ready                             │   │
│  └──────────────────┬──────────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GATEWAY TIER                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ OTel Collector Gateway             :55681 :4317        │   │
│  │ • Receives OTLP logs/traces/metrics                    │   │
│  │ • Routes to correlation engine & backends              │   │
│  └──────────────────┬──────────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY BACKENDS                         │
│                                                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │  Grafana   │ │   Loki     │ │   Tempo    │ │ Prometheus │  │
│  │   :8443    │ │   :3100    │ │   :9000    │ │   :9090    │  │
│  │ Dashboards │ │   Logs     │ │  Traces    │ │  Metrics   │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
│                                                                 │
│  ┌────────────┐ ┌────────────┐                                 │
│  │ Pyroscope  │ │   Redis    │                                 │
│  │   :4040    │ │   :6379    │                                 │
│  │ Profiling  │ │   State    │                                 │
│  └────────────┘ └────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
                     ▲
                     │
┌─────────────────────────────────────────────────────────────────┐
│                      SENSE APPS (Test)                          │
│                                                                 │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐                 │
│  │  Beorn   │    │ Palantir  │    │   Arda   │                 │
│  │  :5001   │    │   :5002   │    │   :5003  │                 │
│  └──────────┘    └───────────┘    └──────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 1.29+ or 2.0+ | Orchestration |
| Make | Any | Automation |
| Git | Any | Version control |

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB | 50+ GB |
| OS | Linux/macOS | Ubuntu 20.04+ |

### Network Ports

Ensure these ports are available:

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | Frontend UI | React app |
| 3100 | Loki | Log storage |
| 4040 | Pyroscope | Profiling UI |
| 5001 | Beorn | Test app |
| 5002 | Palantir | Test app |
| 5003 | Arda | Test app |
| 6379 | Redis | State store |
| 8080 | Correlation Engine | API |
| 8443 | Grafana | Dashboards |
| 9000 | Tempo | Traces UI |
| 9090 | Prometheus | Metrics |
| 13133 | OTel Gateway | Health check |
| 55681 | OTel Gateway | OTLP HTTP |

### Validation

```bash
# Validate prerequisites
cd /path/to/correlation-station/v2/corr-station-updated/seefa-om
make setup-validate
```

---

## Quick Start (Automated)

For a fully automated setup:

```bash
# 1. Validate environment
make setup-validate

# 2. Complete automated setup (all components)
make setup-all

# 3. Wait 2-3 minutes for all services to stabilize

# 4. Verify health
make health-full

# 5. Generate test traffic
make test-traffic

# 6. Access UIs
make show-urls
```

**That's it!** Skip to [Operations & Maintenance](#operations--maintenance) section.

---

## Manual Setup (Step-by-Step)

For granular control or learning purposes, follow these steps.

### Step 1: Validate Environment

```bash
make setup-validate
```

**What it checks:**
- Docker installation and version
- Docker Compose availability
- Disk space (need 20GB+)
- Memory availability
- Port conflicts

**Expected output:**
```
========================================
Validating Prerequisites
========================================

→ Checking Docker...
  ✓ Docker installed: Docker version 24.0.7
→ Checking Docker Compose...
  ✓ Docker Compose installed
→ Checking disk space...
  ✓ Disk space OK: 45G available
→ Checking memory...
  ✓ Memory available: 16Gi total
→ Checking required ports...
  ✓ Port 3000 available
  ✓ Port 3100 available
  ...

✓ Validation complete!
```

### Step 2: Create Docker Network

```bash
make setup-network
```

**What it does:**
- Creates `observability` bridge network
- Configures subnet: 172.20.0.0/23

**Verification:**
```bash
docker network ls | grep observability
docker network inspect observability
```

### Step 3: Setup Observability Stack

```bash
make setup-observability
```

**What it deploys:**
- Grafana (port 8443)
- Loki (port 3100)
- Tempo (port 9000)
- Prometheus (port 9090)
- Pyroscope (port 4040)

**Timeline:**
- Total time: ~2 minutes
- Each service gets 3-5 seconds to start
- Automated health check after 30 seconds

**Verification:**
```bash
make health-observability
```

**Access:**
- Grafana: http://159.56.4.94:8443 (admin/admin)
- Prometheus: http://159.56.4.94:9090
- Pyroscope: http://localhost:4040

### Step 4: Setup OTel Gateway

```bash
make setup-gateway
```

**What it deploys:**
- OpenTelemetry Collector (contrib distribution)
- OTLP HTTP endpoint (port 55681)
- OTLP gRPC endpoint (port 4317, internal)
- Health check endpoint (port 13133)
- Metrics endpoint (port 8888)

**Configuration:** `gateway/otel-config.yaml`

**Verification:**
```bash
make health-gateway
curl http://localhost:13133
```

### Step 5: Setup Redis

```bash
make setup-redis
```

**What it deploys:**
- Redis 7 Alpine
- Persistent storage with AOF
- Max memory: 2GB
- Eviction policy: allkeys-lru

**Verification:**
```bash
make health-redis
make test-redis-connection
```

**Advanced verification:**
```bash
make debug-redis-info
```

### Step 6: Setup Correlation Engine

```bash
make setup-correlation
```

**What it deploys:**
- FastAPI-based correlation service
- OTLP log/trace ingestion
- 60-second correlation window
- Exports to Loki, Tempo, Prometheus
- REST API for queries

**Configuration:**
- Environment: `correlation-engine/.env` (optional)
- Dockerfile: `correlation-engine/Dockerfile`

**Verification:**
```bash
make health-correlation
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

### Step 7: Setup Sense Apps

```bash
make setup-sense-apps
```

**What it deploys:**
- **Beorn** (port 5001): Sample app with OTel instrumentation
- **Palantir** (port 5002): Sample app with OTel instrumentation
- **Arda** (port 5003): Sample app with OTel instrumentation

**Verification:**
```bash
make health-sense-apps
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
```

### Step 8: Setup Frontend UI

```bash
make setup-frontend
```

**What it deploys:**
- React application
- Nginx web server
- Proxies `/api/*` to correlation engine

**Verification:**
```bash
make health-frontend
curl http://localhost:3000
```

**Access:** http://localhost:3000

### Step 9: Final Verification

```bash
# Complete health check
make health-full

# Show all service URLs
make show-urls

# View service status
make status
```

---

## Component Details

### 1. Observability Stack

#### Grafana

**Purpose:** Visualization and dashboards
**Port:** 8443
**Login:** admin/admin
**Config:** `observability-stack/grafana/provisioning/`

**Operations:**
```bash
# Logs
make logs-grafana

# Restart
docker-compose restart grafana

# Shell access
make shell-grafana
```

**Datasources (pre-configured):**
- Loki: http://loki:3100
- Tempo: http://tempo:3200
- Prometheus: http://prometheus:9090

#### Loki

**Purpose:** Log aggregation
**Port:** 3100
**Config:** `observability-stack/loki/loki-config.yaml`

**Operations:**
```bash
# Query logs
make tail-loki

# Check cardinality
make check-cardinality

# Test ingestion
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H "Content-Type: application/json" \
  -d '{"streams":[{"stream":{"service":"test"},"values":[["'$(date +%s)000000000'","test message"]]}]}'
```

#### Tempo

**Purpose:** Distributed tracing
**Port:** 9000 (HTTP), 4317 (gRPC internal)
**Config:** `observability-stack/tempo/tempo-config.yaml`

**Operations:**
```bash
# Query traces
make tail-tempo

# Health check
curl http://localhost:9000/ready
```

#### Prometheus

**Purpose:** Metrics storage
**Port:** 9090
**Config:** `observability-stack/prometheus/prometheus.yml`

**Operations:**
```bash
# Query metrics
make prometheus-query

# Scrape targets
curl http://localhost:9090/api/v1/targets
```

#### Pyroscope

**Purpose:** Continuous profiling
**Port:** 4040
**UI:** http://localhost:4040

**Operations:**
```bash
# Check health
curl http://localhost:4040/healthz
```

### 2. OTel Gateway

**Purpose:** Central telemetry collection point
**Config:** `gateway/otel-config.yaml`

**Endpoints:**
- OTLP HTTP: http://localhost:55681
- OTLP gRPC: localhost:4317 (internal)
- Health: http://localhost:13133
- Metrics: http://localhost:8888/metrics

**Operations:**
```bash
# Debug logs
make debug-logs-gateway

# Test OTLP ingestion
curl -X POST http://localhost:55681/v1/logs \
  -H "Content-Type: application/json" \
  -d '{...OTLP payload...}'
```

### 3. Correlation Engine

**Purpose:** Log/trace correlation and enrichment
**Port:** 8080
**API Docs:** http://localhost:8080/docs

**Key Features:**
- 60-second correlation window
- Trace ID-based correlation
- Batch processing (max 5000 records)
- Redis-backed state (optional)
- Horizontal scaling ready

**Environment Variables:**

Create `correlation-engine/.env`:
```bash
# Core settings
PORT=8080
LOG_LEVEL=info
DEPLOYMENT_ENV=dev

# Correlation settings
CORR_WINDOW_SECONDS=60
MAX_BATCH_SIZE=5000

# Backend URLs
LOKI_URL=http://loki:3100/loki/api/v1/push
TEMPO_GRPC_ENDPOINT=tempo:4317
TEMPO_HTTP_ENDPOINT=http://tempo:4318
PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040

# Redis (optional for scaling)
USE_REDIS_STATE=false
REDIS_URL=redis://redis:6379
```

**API Endpoints:**
```bash
# Health
curl http://localhost:8080/health

# Metrics
curl http://localhost:8080/metrics

# Send logs
curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {"service": "test", "host": "localhost"},
    "records": [{
      "timestamp": "2025-11-16T10:00:00Z",
      "severity": "INFO",
      "message": "Test message",
      "trace_id": "abc123"
    }]
  }'

# Query correlations
curl http://localhost:8080/api/correlations?limit=10
```

**Operations:**
```bash
# Logs
make logs-correlation

# Restart
docker-compose restart correlation-engine

# Debug
make troubleshoot-correlation
make debug-env-correlation
```

### 4. Redis

**Purpose:** Shared state for horizontal scaling
**Port:** 6379
**Version:** Redis 7 Alpine

**Configuration:**
- Persistence: AOF (Append-Only File)
- Max memory: 2GB
- Eviction policy: allkeys-lru

**Operations:**
```bash
# CLI access
make debug-redis-cli

# Monitor commands
make debug-redis-monitor

# Info
make debug-redis-info

# Test connection
make test-redis-connection
```

**Key patterns:**
```
corr:trace:<trace_id>         # Correlation by trace ID
corr:time_index               # Time-based index
corr:correlation:<corr_id>    # Full correlation data
```

### 5. Sense Apps

Three sample applications demonstrating OTel instrumentation:

**Beorn** (port 5001)
- Python Flask application
- Auto-instrumented with OpenTelemetry
- Sends logs and traces to OTel Gateway

**Palantir** (port 5002)
- Python Flask application
- Manual OTel instrumentation examples
- Custom span attributes

**Arda** (port 5003)
- Python Flask application
- Error injection for testing
- Demonstrates trace correlation

**Operations:**
```bash
# View logs
make logs-sense

# Generate test traffic
make test-traces

# Health checks
make health-sense-apps
```

### 6. Frontend UI

**Purpose:** Training portal and documentation
**Port:** 3000
**Tech:** React + Nginx

**Features:**
- Quick links to all tools
- TraceQL and PromQL documentation
- OTel instrumentation guides
- SECA error reviews
- Architecture diagrams

**Operations:**
```bash
# Logs
docker-compose logs -f correlation-station-ui

# Restart
docker-compose restart correlation-station-ui

# Rebuild
docker-compose build correlation-station-ui
```

---

## Horizontal Scaling with Redis

### Enable Redis State Management

#### Option 1: Using Make Commands

```bash
# 1. Ensure Redis is running
make setup-redis

# 2. Create environment file
make scale-create-env

# 3. Enable Redis state
make scale-enable-redis

# 4. Verify
make debug-env-correlation | grep REDIS
```

#### Option 2: Manual Configuration

```bash
# 1. Create/edit correlation-engine/.env
cat > correlation-engine/.env <<EOF
USE_REDIS_STATE=true
REDIS_URL=redis://redis:6379
REDIS_MAX_CONNECTIONS=50
REDIS_KEY_PREFIX=corr:
CORRELATION_TTL_SECONDS=3600
MAX_CORRELATION_AGE_HOURS=24
EOF

# 2. Restart correlation engine
docker-compose restart correlation-engine

# 3. Watch logs for Redis connection
docker-compose logs -f correlation-engine | grep -i redis
```

**Expected log output:**
```
INFO | redis_connected | url=redis://redis:6379
INFO | correlation_state_backend | backend=redis
```

### Scale to Multiple Instances

```bash
# Scale to 3 instances
make scale-up N=3

# Verify
docker-compose ps correlation-engine

# Should see:
# correlation-engine_1
# correlation-engine_2
# correlation-engine_3
```

### Test Scaling

```bash
# Run scaling test (1000 requests)
make scale-test

# Monitor Redis
make debug-redis-monitor

# Check Redis size
docker exec redis redis-cli DBSIZE

# Check instance distribution
docker stats
```

### Scale Down

```bash
# Back to 1 instance
make scale-down
```

### Disable Redis (Rollback)

```bash
make rollback-redis-disable
```

---

## Load Testing with K6

### Install K6 (Optional)

If not using Docker:

```bash
make k6-install
```

### Basic Load Test

```bash
# Run basic test
make k6-test-basic

# Run log ingestion test
make k6-test-logs
```

### Stress Test

```bash
# High load (100 VUs for 5 minutes)
make k6-test-stress
```

### K6 in Docker

```bash
# Run K6 test in container
make k6-test-docker
```

### Custom K6 Tests

Create test in `k6/my-test.js`:

```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  let res = http.get('http://correlation-engine:8080/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
```

Run:
```bash
docker run --rm -i --network observability \
  -v $(PWD)/k6:/scripts \
  grafana/k6:latest run /scripts/my-test.js
```

---

## Operations & Maintenance

### Daily Operations

```bash
# Check health
make health-full

# View status
make status

# View logs
make logs-all
```

### Service Management

```bash
# Restart all
make restart

# Restart specific service
docker-compose restart correlation-engine
docker-compose restart redis
docker-compose restart grafana
```

### Monitoring

```bash
# Container stats
make debug-container-stats

# Disk usage
make debug-disk-usage

# Network info
make debug-network

# Port mappings
make debug-ports
```

### Log Management

```bash
# Export logs
make logs-export

# View errors only
make logs-errors

# Clean old logs
make clean-logs
```

### Backups

```bash
# Create backup
make rollback-backup

# Lists backups
ls -la backups/
```

**Backup includes:**
- docker-compose.yml
- Makefile
- correlation-engine/.env
- Service status
- Volume list
- Network list

### Grafana Dashboard Backup

```bash
# Backup dashboards
make backup-dashboards

# Restore dashboards
make restore-dashboards
```

---

## Troubleshooting

### General Troubleshooting

```bash
# Full health check
make health-full

# View all logs
make debug-logs-all

# Check disk space
make debug-disk-usage

# Check network
make troubleshoot-network
```

### Correlation Engine Issues

```bash
# Automated troubleshooting
make troubleshoot-correlation

# Manual checks
docker ps -a | grep correlation
curl http://localhost:8080/health
make debug-logs-correlation
make debug-env-correlation
```

**Common issues:**

1. **Cannot connect to Redis**
   ```bash
   # Check Redis
   make troubleshoot-redis

   # Restart Redis
   make fix-redis
   ```

2. **High memory usage**
   ```bash
   # Check stats
   docker stats correlation-engine

   # Reduce batch size in .env
   MAX_BATCH_SIZE=1000
   ```

3. **Slow response times**
   ```bash
   # Check Pyroscope for profiling
   open http://localhost:4040

   # Check correlation window
   # Reduce in .env:
   CORR_WINDOW_SECONDS=30
   ```

### Redis Issues

```bash
# Automated troubleshooting
make troubleshoot-redis

# Check connection
make test-redis-connection

# View info
make debug-redis-info

# Monitor activity
make debug-redis-monitor
```

**Common issues:**

1. **Out of memory**
   ```bash
   # Check memory
   docker exec redis redis-cli INFO memory

   # Flush if needed (⚠️ deletes data)
   docker exec redis redis-cli FLUSHDB
   ```

2. **Slow queries**
   ```bash
   # Check slow log
   docker exec redis redis-cli SLOWLOG GET 10
   ```

### Network Issues

```bash
# Automated troubleshooting
make troubleshoot-network

# Fix network
make fix-network

# Recreate manually
make teardown-network
make setup-network
```

### Port Conflicts

```bash
# Check port usage
lsof -i :8080
lsof -i :6379

# Kill conflicting processes
make fix-ports
```

### Service Won't Start

```bash
# Check logs
make debug-logs-<service>

# Rebuild
docker-compose build --no-cache <service>

# Recreate
docker-compose up -d --force-recreate <service>
```

---

## Rollback Procedures

### Create Backup Before Changes

```bash
make rollback-backup
```

### Rollback Correlation Engine

```bash
make rollback-correlation
```

### Disable Redis State

```bash
make rollback-redis-disable
```

### Restore from Backup

```bash
# List backups
ls -la backups/

# Restore (interactive)
make rollback-restore-volumes
# Enter timestamp when prompted: YYYYMMDD_HHMMSS
```

### Manual Rollback

```bash
# 1. Stop services
make teardown-all

# 2. Restore configs
cp backups/TIMESTAMP/docker-compose.yml .
cp backups/TIMESTAMP/.env correlation-engine/

# 3. Restart
make setup-all
```

---

## Advanced Topics

### Custom Environment Variables

Edit `correlation-engine/.env`:

```bash
# Performance tuning
CORR_WINDOW_SECONDS=30        # Faster correlation
MAX_BATCH_SIZE=10000          # Larger batches
WORKER_THREADS=4              # More concurrency

# Security
ENABLE_BASIC_AUTH=true
BASIC_AUTH_USER=admin
BASIC_AUTH_PASS=secret123

# DataDog integration
DATADOG_API_KEY=your_key
DATADOG_SITE=datadoghq.com
```

### Custom OTel Gateway Config

Edit `gateway/otel-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024

exporters:
  otlphttp:
    endpoint: http://correlation-engine:8080
```

### Loki Retention Policy

Edit `observability-stack/loki/loki-config.yaml`:

```yaml
limits_config:
  retention_period: 168h  # 7 days

compactor:
  retention_enabled: true
  delete_request_cancel_period: 24h
```

### Tempo Retention

Edit `observability-stack/tempo/tempo-config.yaml`:

```yaml
storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    block:
      retention: 48h  # 2 days
```

### Prometheus Scrape Intervals

Edit `observability-stack/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'correlation-engine'
    static_configs:
      - targets: ['correlation-engine:8080']
```

### Multi-Instance Load Balancing

Add Nginx as load balancer:

```yaml
# docker-compose.yml
nginx-lb:
  image: nginx:alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx-lb.conf:/etc/nginx/nginx.conf
  depends_on:
    - correlation-engine
```

Create `nginx-lb.conf`:

```nginx
upstream correlation_backend {
    least_conn;
    server correlation-engine_1:8080;
    server correlation-engine_2:8080;
    server correlation-engine_3:8080;
}

server {
    listen 80;

    location / {
        proxy_pass http://correlation_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Production Hardening

1. **Enable authentication:**
   ```bash
   # In correlation-engine/.env
   ENABLE_BASIC_AUTH=true
   BASIC_AUTH_USER=admin
   BASIC_AUTH_PASS=your_secure_password
   ```

2. **Use secrets management:**
   ```bash
   # Use Docker secrets
   echo "admin" | docker secret create corr_user -
   echo "password" | docker secret create corr_pass -
   ```

3. **Enable TLS:**
   - Configure Nginx with SSL certificates
   - Use Let's Encrypt for free certs

4. **Resource limits:**
   ```yaml
   # docker-compose.yml
   correlation-engine:
     deploy:
       resources:
         limits:
           cpus: '2'
           memory: 4G
         reservations:
           cpus: '1'
           memory: 2G
   ```

5. **Monitoring alerts:**
   - Configure Prometheus AlertManager
   - Set up PagerDuty/Slack notifications

---

## Makefile Command Reference

### Setup Commands

| Command | Description |
|---------|-------------|
| `make setup-validate` | Validate prerequisites |
| `make setup-network` | Create Docker network |
| `make setup-observability` | Setup Grafana, Loki, etc |
| `make setup-gateway` | Setup OTel Gateway |
| `make setup-redis` | Setup Redis |
| `make setup-correlation` | Setup Correlation Engine |
| `make setup-sense-apps` | Setup test apps |
| `make setup-frontend` | Setup UI |
| `make setup-all` | Complete automated setup |

### Teardown Commands

| Command | Description |
|---------|-------------|
| `make teardown-observability` | Stop observability stack |
| `make teardown-gateway` | Stop OTel Gateway |
| `make teardown-redis` | Stop Redis |
| `make teardown-correlation` | Stop Correlation Engine |
| `make teardown-sense-apps` | Stop test apps |
| `make teardown-frontend` | Stop UI |
| `make teardown-all` | Complete teardown (keeps data) |
| `make teardown-purge` | Teardown + remove volumes |

### Health Check Commands

| Command | Description |
|---------|-------------|
| `make health-observability` | Check observability stack |
| `make health-gateway` | Check OTel Gateway |
| `make health-redis` | Check Redis |
| `make health-correlation` | Check Correlation Engine |
| `make health-sense-apps` | Check test apps |
| `make health-frontend` | Check UI |
| `make health-full` | Complete health check |

### Scaling Commands

| Command | Description |
|---------|-------------|
| `make scale-create-env` | Create .env for scaling |
| `make scale-enable-redis` | Enable Redis state |
| `make scale-up N=3` | Scale to N instances |
| `make scale-down` | Scale to 1 instance |
| `make scale-test` | Test with load |

### K6 Commands

| Command | Description |
|---------|-------------|
| `make k6-install` | Install K6 locally |
| `make k6-test-basic` | Basic load test |
| `make k6-test-logs` | Log ingestion test |
| `make k6-test-stress` | Stress test |
| `make k6-test-docker` | Run in Docker |

### Debug Commands

| Command | Description |
|---------|-------------|
| `make debug-logs-all` | All container logs |
| `make debug-logs-correlation` | Correlation engine logs |
| `make debug-logs-redis` | Redis logs |
| `make debug-redis-info` | Redis stats |
| `make debug-redis-monitor` | Monitor Redis |
| `make debug-redis-cli` | Redis CLI |
| `make debug-network` | Network info |
| `make debug-ports` | Port mappings |
| `make debug-disk-usage` | Disk usage |
| `make debug-container-stats` | Resource usage |

### Troubleshooting Commands

| Command | Description |
|---------|-------------|
| `make troubleshoot-correlation` | Diagnose correlation issues |
| `make troubleshoot-redis` | Diagnose Redis issues |
| `make troubleshoot-network` | Diagnose network issues |
| `make fix-permissions` | Fix file permissions |
| `make fix-network` | Recreate network |
| `make fix-redis` | Restart Redis |

### Logging Commands

| Command | Description |
|---------|-------------|
| `make logs-all` | Tail all logs |
| `make logs-correlation` | Correlation engine logs |
| `make logs-redis` | Redis logs |
| `make logs-gateway` | OTel Gateway logs |
| `make logs-grafana` | Grafana logs |
| `make logs-sense` | Sense apps logs |
| `make logs-errors` | Error logs only |
| `make logs-export` | Export to files |

### Testing Commands

| Command | Description |
|---------|-------------|
| `make test-traffic` | Generate test traffic |
| `make test-logs` | Send test logs |
| `make test-traces` | Generate test traces |
| `make test-correlation-api` | Test API |
| `make test-redis-connection` | Test Redis |

### Utility Commands

| Command | Description |
|---------|-------------|
| `make status` | Service status |
| `make show-urls` | Show all URLs |
| `make version` | Show versions |
| `make shell-correlation` | Shell in correlation engine |
| `make shell-redis` | Shell in Redis |
| `make shell-grafana` | Shell in Grafana |
| `make open-grafana` | Open Grafana browser |
| `make open-frontend` | Open UI in browser |
| `make prune` | Clean Docker resources |

### Rollback Commands

| Command | Description |
|---------|-------------|
| `make rollback-backup` | Create backup |
| `make rollback-correlation` | Rollback correlation engine |
| `make rollback-redis-disable` | Disable Redis |
| `make rollback-restore-volumes` | Restore from backup |

### Quick Aliases

| Command | Alias For |
|---------|-----------|
| `make up` | `make setup-all` |
| `make down` | `make teardown-all` |
| `make restart` | `make teardown-all setup-all` |
| `make health` | `make health-full` |
| `make logs` | `make logs-all` |

---

## Service URLs Quick Reference

### User Interfaces

- **Frontend:** http://localhost:3000
- **Grafana:** http://159.56.4.94:8443 (admin/admin)
- **Prometheus:** http://159.56.4.94:9090
- **Pyroscope:** http://localhost:4040

### APIs

- **Correlation API:** http://159.56.4.94:8080
- **API Docs:** http://159.56.4.94:8080/docs
- **Health:** http://159.56.4.94:8080/health
- **Metrics:** http://159.56.4.94:8080/metrics

### Test Applications

- **Beorn:** http://localhost:5001
- **Palantir:** http://localhost:5002
- **Arda:** http://localhost:5003

### Backends

- **Loki:** http://localhost:3100
- **Tempo:** http://localhost:9000
- **Redis:** localhost:6379
- **OTLP HTTP:** http://localhost:55681

---

## Support & Resources

### Documentation

- **Main README:** `README.md`
- **Makefile Guide:** `MAKEFILE_SETUP_GUIDE.md`
- **Horizontal Scaling:** `HORIZONTAL_SCALING_SETUP_GUIDE.md`
- **Master Setup:** `MASTER_SETUP_GUIDE.md`

### Getting Help

1. Run `make help` for command reference
2. Check logs: `make debug-logs-all`
3. Run troubleshooting: `make troubleshoot-<component>`
4. Review this guide's troubleshooting section

### Common Tasks

```bash
# I need to...

# ...start everything
make setup-all

# ...check if it's working
make health-full

# ...see what's running
make status

# ...view logs
make logs-all

# ...test the system
make test-traffic

# ...scale up
make scale-up N=3

# ...troubleshoot
make troubleshoot-correlation
make troubleshoot-redis

# ...stop everything
make teardown-all

# ...remove all data
make teardown-purge
```

---

## Conclusion

You now have a complete observability platform with:

✅ Full telemetry pipeline (logs, traces, metrics)
✅ Correlation engine with horizontal scaling
✅ Production-ready monitoring stack
✅ Load testing capabilities
✅ Comprehensive operational tools
✅ Rollback and recovery procedures

**Next Steps:**

1. Instrument your applications with OpenTelemetry
2. Configure custom dashboards in Grafana
3. Set up alerts in Prometheus
4. Enable horizontal scaling for production
5. Implement backup procedures

**Happy Observing! 🚀**

---

*For questions or issues, refer to the troubleshooting section or review service logs.*

**Version:** 2.0.0
**Last Updated:** 2025-11-16
**Maintained by:** Derrick Golden
