# Correlation Station - Complete Setup Guide

**Master manual for setting up Pyroscope profiling and Redis-based horizontal scaling from scratch**

This guide walks you through the complete setup of the Correlation Station observability platform, including:
- ✅ Pyroscope continuous profiling
- ✅ Redis-based horizontal scaling (multi-instance deployment)
- ✅ Complete monitoring stack (Grafana, Prometheus, Loki, Tempo)
- ✅ Health checks and production readiness

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Phase 1: Single Instance Deployment](#phase-1-single-instance-deployment)
4. [Phase 2: Enable Pyroscope Profiling](#phase-2-enable-pyroscope-profiling)
5. [Phase 3: Enable Redis State Management](#phase-3-enable-redis-state-management)
6. [Phase 4: Horizontal Scaling (Multi-Instance)](#phase-4-horizontal-scaling-multi-instance)
7. [Phase 5: Production Hardening](#phase-5-production-hardening)
8. [Monitoring & Dashboards](#monitoring--dashboards)
9. [Testing & Verification](#testing--verification)
10. [Troubleshooting](#troubleshooting)
11. [Rollback Procedures](#rollback-procedures)
12. [Tear Down](#tear-down)
13. [Maintenance](#maintenance)

---

## Prerequisites

### Required Software

```bash
# Check Docker
docker --version
# Required: Docker 20.10+

# Check Docker Compose
docker-compose --version
# Required: Docker Compose 1.29+ or 2.0+

# Check available disk space (need ~20GB)
df -h

# Check available memory (need ~8GB)
free -h

# Check Git
git --version
```

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB | 50+ GB |
| OS | Linux/macOS | Ubuntu 20.04+ |

### Network Ports

Ensure these ports are available:

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | Grafana | Dashboards |
| 3100 | Loki | Log aggregation |
| 4040 | Pyroscope | Profiling UI |
| 4317 | Tempo (gRPC) | Trace ingestion |
| 4318 | Tempo (HTTP) | Trace ingestion |
| 6379 | Redis | State management |
| 8080 | Correlation Engine | API |
| 9090 | Prometheus | Metrics |

**Check ports are free:**
```bash
# Check if ports are in use
netstat -tuln | grep -E ':(3000|3100|4040|4317|4318|6379|8080|9090)'

# If any ports are in use, either:
# 1. Stop the conflicting service, OR
# 2. Change the port in docker-compose.yml
```

---

## Environment Setup

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/goldenfamilyfarms/correlation-station.git
cd correlation-station/v2/corr-station-updated/seefa-om

# Verify directory structure
ls -la
# Expected: correlation-engine/, sense-apps/, observability-stack/, docker-compose.yml
```

### Step 2: Create Environment Files

**Create `.env` files for all services:**

```bash
# Correlation Engine .env
cat > correlation-engine/.env <<'EOF'
# === Server Configuration ===
PORT=8080
LOG_LEVEL=info
DEPLOYMENT_ENV=dev

# === Correlation Settings ===
CORR_WINDOW_SECONDS=60
MAX_BATCH_SIZE=5000
MAX_QUEUE_SIZE=10000
MAX_CORRELATION_HISTORY=10000

# === Backend URLs ===
LOKI_URL=http://loki:3100/loki/api/v1/push
TEMPO_GRPC_ENDPOINT=tempo:4317
TEMPO_HTTP_ENDPOINT=http://tempo:4318

# === Export Settings ===
EXPORT_RETRY_ATTEMPTS=3
EXPORT_RETRY_DELAY=1.0
EXPORT_TIMEOUT=10.0
ENABLE_CIRCUIT_BREAKER=true

# === Pyroscope Profiling (disabled initially) ===
ENABLE_PYROSCOPE=false
PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
PYROSCOPE_SAMPLE_RATE=100

# === Redis State Management (disabled initially) ===
USE_REDIS_STATE=false
REDIS_URL=redis://redis:6379
REDIS_MAX_CONNECTIONS=50
CORRELATION_TTL_SECONDS=3600

# === Self-Observability ===
ENABLE_SELF_OBSERVABILITY=true
EOF

# Set permissions
chmod 600 correlation-engine/.env

# Verify .env was created
cat correlation-engine/.env
```

### Step 3: Verify Docker Compose Configuration

```bash
# Validate docker-compose.yml syntax
docker-compose config

# Check which services are defined
docker-compose config --services

# Expected services:
# - grafana
# - loki
# - tempo
# - prometheus
# - pyroscope
# - redis
# - correlation-engine
# - otel-gateway
```

---

## Phase 1: Single Instance Deployment

**Goal:** Get the basic correlation engine running with all observability components.

### Step 1.1: Start Core Services

```bash
# Start observability stack first
docker-compose up -d \
  grafana \
  loki \
  tempo \
  prometheus \
  pyroscope \
  redis

# Wait for services to be healthy (30 seconds)
echo "Waiting for services to start..."
sleep 30

# Check service status
docker-compose ps

# All services should show "Up (healthy)"
```

### Step 1.2: Verify Core Services

**Check each service is running:**

```bash
# Grafana
curl -s http://localhost:3000/api/health | jq
# Expected: {"commit": "...", "database": "ok", "version": "..."}

# Loki
curl -s http://localhost:3100/ready
# Expected: ready

# Tempo
curl -s http://localhost:4318/health
# Expected: (empty response with 200 OK)

# Prometheus
curl -s http://localhost:9090/-/healthy
# Expected: Prometheus is Healthy.

# Pyroscope
curl -s http://localhost:4040/healthz
# Expected: OK

# Redis
docker exec redis redis-cli ping
# Expected: PONG
```

**If any service fails, check logs:**
```bash
# View logs for specific service
docker-compose logs <service-name>

# Example: Check Grafana logs
docker-compose logs grafana

# Follow logs in real-time
docker-compose logs -f grafana
```

### Step 1.3: Start Correlation Engine

```bash
# Build correlation engine image
docker-compose build correlation-engine

# Start correlation engine
docker-compose up -d correlation-engine

# Wait for startup (10 seconds)
sleep 10

# Check status
docker-compose ps correlation-engine

# View logs
docker-compose logs -f correlation-engine
```

**Look for success messages in logs:**
```
INFO  | Correlation Engine started
INFO  | Starting Correlation Engine
INFO  | Self-observability disabled or unavailable
INFO  | Exporters initialized
```

### Step 1.4: Verify Correlation Engine

```bash
# Health check
curl http://localhost:8080/health
# Expected: {"status":"healthy","version":"1.0.0",...}

# Liveness probe
curl http://localhost:8080/health/live
# Expected: {"status":"alive",...}

# Readiness probe
curl http://localhost:8080/health/ready
# Expected: {"status":"ready","checks":{...}}

# Metrics endpoint
curl http://localhost:8080/metrics | head -20
# Expected: Prometheus metrics

# API root
curl http://localhost:8080/
# Expected: {"service":"correlation-engine","status":"running",...}
```

### Step 1.5: Send Test Traffic

```bash
# Send test log batch
curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "service": "test-app",
      "host": "localhost",
      "env": "dev"
    },
    "records": [{
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "severity": "INFO",
      "message": "Test log message from setup guide",
      "trace_id": "test123456789abcdef"
    }]
  }'

# Expected: {"status":"accepted"}
```

**Verify in logs:**
```bash
docker-compose logs correlation-engine | grep "test-app"
# Should see log ingestion messages
```

### ✅ Phase 1 Complete Checklist

- [ ] All 6 core services running (Grafana, Loki, Tempo, Prometheus, Pyroscope, Redis)
- [ ] Correlation engine running and healthy
- [ ] Health endpoints return 200 OK
- [ ] Test traffic accepted successfully
- [ ] No errors in logs

---

## Phase 2: Enable Pyroscope Profiling

**Goal:** Enable continuous profiling to identify performance bottlenecks.

### Step 2.1: Update Environment Configuration

```bash
# Enable Pyroscope in .env
cd correlation-engine/

# Update ENABLE_PYROSCOPE
sed -i 's/ENABLE_PYROSCOPE=false/ENABLE_PYROSCOPE=true/' .env

# Verify change
grep PYROSCOPE .env

# Expected output:
# ENABLE_PYROSCOPE=true
# PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
# PYROSCOPE_SAMPLE_RATE=100
```

### Step 2.2: Restart Correlation Engine

```bash
# Go back to project root
cd ..

# Restart to pick up new env vars
docker-compose restart correlation-engine

# Watch logs for Pyroscope initialization
docker-compose logs -f correlation-engine
```

**Look for success message:**
```
INFO  | Pyroscope profiling enabled | server=http://pyroscope:4040 | sample_rate=100
```

**If you see an error:**
```
WARNING | Failed to configure Pyroscope: ...
```
→ See [Troubleshooting - Pyroscope Issues](#pyroscope-issues)

### Step 2.3: Verify Profiling is Active

**Check metrics:**
```bash
# Pyroscope should be collecting profiles
curl http://localhost:8080/metrics | grep pyroscope

# Check active profiling (should be empty initially, profiles collect over time)
curl -s http://localhost:4040/api/apps | jq
```

**Access Pyroscope UI:**
```bash
# Open in browser
open http://localhost:4040

# Or use curl to check
curl -s http://localhost:4040/ | grep "Pyroscope"
```

### Step 2.4: Generate Load for Profiling

**Send traffic to generate profile data:**

```bash
# Send 1000 requests to create profiling data
for i in {1..1000}; do
  curl -s -X POST http://localhost:8080/api/logs \
    -H "Content-Type: application/json" \
    -d '{
      "resource": {"service": "load-test", "host": "localhost", "env": "dev"},
      "records": [{
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "severity": "INFO",
        "message": "Load test message '$i'",
        "trace_id": "load'$RANDOM'"
      }]
    }' > /dev/null

  # Print progress every 100 requests
  if [ $((i % 100)) -eq 0 ]; then
    echo "Sent $i requests..."
  fi
done

echo "Load test complete!"
```

### Step 2.5: View Flame Graphs

**Wait 30 seconds for profiles to upload, then:**

```bash
# Open Pyroscope UI
open http://localhost:4040
```

**In Pyroscope UI:**
1. Select application: `correlation-engine`
2. Select profile type: `cpu` (CPU time)
3. View flame graph
4. Look for hot paths:
   - `create_correlations` (correlation logic)
   - `export_logs` (Loki export)
   - `export_traces` (Tempo export)
   - `ingest_otlp_logs` (OTLP ingestion)

**Check profiling tags:**
```bash
# Profiles should have tags
curl -s "http://localhost:4040/api/render?query=correlation-engine.cpu{}" | jq '.metadata.labels'

# Expected tags:
# - environment: dev
# - version: 1.0.0
# - service: correlation-engine
# - function: (varies)
# - operation: (varies)
```

### ✅ Phase 2 Complete Checklist

- [ ] Pyroscope enabled in .env
- [ ] Correlation engine restarted successfully
- [ ] Pyroscope UI accessible (http://localhost:4040)
- [ ] Flame graphs visible after load test
- [ ] CPU hotspots identified in flame graphs
- [ ] Profile tags include function/operation names

---

## Phase 3: Enable Redis State Management

**Goal:** Switch from in-memory state to Redis to prepare for horizontal scaling.

### Step 3.1: Enable Redis State

```bash
cd correlation-engine/

# Enable Redis state management
sed -i 's/USE_REDIS_STATE=false/USE_REDIS_STATE=true/' .env

# Verify
grep REDIS .env

# Expected:
# USE_REDIS_STATE=true
# REDIS_URL=redis://redis:6379
# REDIS_MAX_CONNECTIONS=50
# CORRELATION_TTL_SECONDS=3600
```

### Step 3.2: Restart and Verify

```bash
cd ..

# Restart correlation engine
docker-compose restart correlation-engine

# Watch logs for Redis connection
docker-compose logs -f correlation-engine | grep -i redis
```

**Success messages to look for:**
```
INFO  | redis_connected | url=redis://redis:6379
INFO  | Correlation Engine started
```

**Check state backend metric:**
```bash
# Should show 1.0 (Redis enabled)
curl -s http://localhost:8080/metrics | grep correlation_state_backend

# Expected:
# correlation_state_backend 1.0
```

### Step 3.3: Test Redis State Storage

**Send test correlation:**
```bash
# Send log + trace with same trace_id
TRACE_ID="redis-test-$(date +%s)"

# Send log
curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {"service": "redis-test", "host": "localhost", "env": "dev"},
    "records": [{
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "severity": "INFO",
      "message": "Redis state test log",
      "trace_id": "'$TRACE_ID'"
    }]
  }'

echo "Sent log with trace_id: $TRACE_ID"
```

**Check Redis for stored data:**
```bash
# Connect to Redis
docker exec -it redis redis-cli

# Inside Redis CLI:
KEYS corr:*
# Should see keys like:
# corr:time_index
# corr:trace:<trace_id>
# corr:<correlation_id>

# View time index (sorted set of correlation IDs)
ZRANGE corr:time_index 0 -1 WITHSCORES

# Get a correlation entry
GET corr:<correlation-id-from-above>

# Count total correlations
ZCARD corr:time_index

# Exit
exit
```

### Step 3.4: Monitor Redis Metrics

```bash
# Check Redis operation metrics
curl -s http://localhost:8080/metrics | grep redis

# Expected metrics:
# redis_operations_total{operation="set",status="success"}
# redis_operations_total{operation="get",status="success"}
# redis_operation_duration_seconds_bucket

# Check Redis memory usage
docker exec redis redis-cli INFO memory | grep used_memory_human
```

### Step 3.5: 24-Hour Stability Test

**Before scaling to multiple instances, monitor for 24 hours:**

```bash
# Create monitoring script
cat > monitor_redis.sh <<'EOF'
#!/bin/bash
while true; do
  echo "=== $(date) ==="

  # Check correlation count
  echo -n "Correlations in Redis: "
  docker exec redis redis-cli ZCARD corr:time_index

  # Check Redis memory
  docker exec redis redis-cli INFO memory | grep used_memory_human

  # Check error rate
  echo -n "Redis errors: "
  curl -s http://localhost:8080/metrics | grep 'redis_errors_total' | tail -1

  # Check state backend
  echo -n "State backend: "
  curl -s http://localhost:8080/metrics | grep correlation_state_backend | awk '{print $2}'

  echo ""
  sleep 300  # Every 5 minutes
done
EOF

chmod +x monitor_redis.sh

# Run in background
nohup ./monitor_redis.sh > redis_monitor.log 2>&1 &

echo "Monitoring started. Check redis_monitor.log for updates."
```

**What to watch for:**
- ✅ No Redis connection errors
- ✅ Memory usage stable (not constantly growing)
- ✅ `redis_errors_total` stays at 0
- ✅ `correlation_state_backend` stays at 1.0

### ✅ Phase 3 Complete Checklist

- [ ] Redis state enabled in .env
- [ ] Correlation engine connects to Redis successfully
- [ ] `correlation_state_backend` metric shows 1.0
- [ ] Correlations stored in Redis (check with `KEYS corr:*`)
- [ ] No Redis errors in logs for 24 hours
- [ ] Redis memory usage is stable

---

## Phase 4: Horizontal Scaling (Multi-Instance)

**Goal:** Run 3 correlation engine instances sharing state via Redis.

### Step 4.1: Create Load Balancer Configuration

**Create nginx config for load balancing:**

```bash
# Create nginx config file
cat > correlation-lb-nginx.conf <<'EOF'
events {
    worker_connections 2048;
}

http {
    # Logging
    log_format detailed '$remote_addr - $remote_user [$time_local] '
                       '"$request" $status $body_bytes_sent '
                       '"$http_referer" "$http_user_agent" '
                       'upstream: $upstream_addr '
                       'response_time: $upstream_response_time';

    access_log /var/log/nginx/correlation-access.log detailed;
    error_log /var/log/nginx/correlation-error.log warn;

    # Upstream pool of correlation engines
    upstream correlation_backend {
        least_conn;  # Route to instance with fewest connections

        server correlation-engine-1:8080 max_fails=3 fail_timeout=30s;
        server correlation-engine-2:8080 max_fails=3 fail_timeout=30s;
        server correlation-engine-3:8080 max_fails=3 fail_timeout=30s;

        keepalive 64;
    }

    server {
        listen 80;
        server_name localhost;

        # Increase buffer sizes for large requests
        client_body_buffer_size 1M;
        client_max_body_size 10M;

        # Proxy to correlation engines
        location / {
            proxy_pass http://correlation_backend;

            # Headers
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 10s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;

            # Buffering
            proxy_buffering on;
            proxy_buffer_size 8k;
            proxy_buffers 8 8k;

            # Health checks
            proxy_next_upstream error timeout http_500 http_502 http_503;
        }

        # Health check endpoint (no logging)
        location /health {
            access_log off;
            proxy_pass http://correlation_backend/health;
        }

        # Nginx status
        location /nginx-status {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            deny all;
        }
    }
}
EOF

echo "nginx config created: correlation-lb-nginx.conf"
```

### Step 4.2: Update docker-compose.yml for Multiple Instances

**Add to docker-compose.yml:**

```bash
# Create backup first
cp docker-compose.yml docker-compose.yml.backup

# Add the following services to docker-compose.yml
cat >> docker-compose.yml <<'EOF'

  # ============================================
  # Load Balancer
  # ============================================
  correlation-lb:
    image: nginx:alpine
    container_name: correlation-lb
    restart: unless-stopped
    ports:
      - "8080:80"  # Override correlation-engine port
    volumes:
      - ./correlation-lb-nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - observability
    depends_on:
      - correlation-engine-1
      - correlation-engine-2
      - correlation-engine-3
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============================================
  # Correlation Engine Instances
  # ============================================
  correlation-engine-1:
    build: ./correlation-engine
    container_name: correlation-engine-1
    restart: unless-stopped
    environment:
      - PORT=8080
      - INSTANCE_ID=1
      - USE_REDIS_STATE=true
      - REDIS_URL=redis://redis:6379
      - ENABLE_PYROSCOPE=true
      - PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
      - LOKI_URL=http://loki:3100/loki/api/v1/push
      - TEMPO_GRPC_ENDPOINT=tempo:4317
      - TEMPO_HTTP_ENDPOINT=http://tempo:4318
      - DEPLOYMENT_ENV=dev
    volumes:
      - ./correlation-engine/app:/app/app
    networks:
      - observability
    depends_on:
      - redis
      - loki
      - tempo
      - pyroscope
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 5

  correlation-engine-2:
    build: ./correlation-engine
    container_name: correlation-engine-2
    restart: unless-stopped
    environment:
      - PORT=8080
      - INSTANCE_ID=2
      - USE_REDIS_STATE=true
      - REDIS_URL=redis://redis:6379
      - ENABLE_PYROSCOPE=true
      - PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
      - LOKI_URL=http://loki:3100/loki/api/v1/push
      - TEMPO_GRPC_ENDPOINT=tempo:4317
      - TEMPO_HTTP_ENDPOINT=http://tempo:4318
      - DEPLOYMENT_ENV=dev
    volumes:
      - ./correlation-engine/app:/app/app
    networks:
      - observability
    depends_on:
      - redis
      - loki
      - tempo
      - pyroscope
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 5

  correlation-engine-3:
    build: ./correlation-engine
    container_name: correlation-engine-3
    restart: unless-stopped
    environment:
      - PORT=8080
      - INSTANCE_ID=3
      - USE_REDIS_STATE=true
      - REDIS_URL=redis://redis:6379
      - ENABLE_PYROSCOPE=true
      - PYROSCOPE_SERVER_ADDRESS=http://pyroscope:4040
      - LOKI_URL=http://loki:3100/loki/api/v1/push
      - TEMPO_GRPC_ENDPOINT=tempo:4317
      - TEMPO_HTTP_ENDPOINT=http://tempo:4318
      - DEPLOYMENT_ENV=dev
    volumes:
      - ./correlation-engine/app:/app/app
    networks:
      - observability
    depends_on:
      - redis
      - loki
      - tempo
      - pyroscope
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 5
EOF

echo "docker-compose.yml updated with 3 instances + load balancer"
```

**Important:** Comment out or remove the original `correlation-engine` service since we now have 3 instances.

### Step 4.3: Stop Single Instance and Start Multi-Instance

```bash
# Stop old single instance
docker-compose stop correlation-engine
docker-compose rm -f correlation-engine

# Start 3 new instances + load balancer
docker-compose up -d \
  correlation-engine-1 \
  correlation-engine-2 \
  correlation-engine-3 \
  correlation-lb

# Wait for startup (30 seconds)
sleep 30

# Check all instances are running
docker-compose ps | grep correlation

# Expected output (all healthy):
# correlation-engine-1    Up    healthy
# correlation-engine-2    Up    healthy
# correlation-engine-3    Up    healthy
# correlation-lb          Up    healthy
```

### Step 4.4: Verify Load Distribution

**Test load balancer:**

```bash
# Send 30 requests and track which instance handles each
echo "Sending 30 requests to track load distribution..."

for i in {1..30}; do
  curl -s http://localhost:8080/health/live > /dev/null
  sleep 0.1
done

echo "Checking request distribution..."

# Count requests per instance
echo "Instance 1 requests:"
docker logs correlation-engine-1 2>&1 | grep -c "request_completed"

echo "Instance 2 requests:"
docker logs correlation-engine-2 2>&1 | grep -c "request_completed"

echo "Instance 3 requests:"
docker logs correlation-engine-3 2>&1 | grep -c "request_completed"

echo ""
echo "Expected: Each instance should have ~10 requests (even distribution)"
```

**Check nginx stats:**
```bash
# View nginx access log
docker exec correlation-lb cat /var/log/nginx/correlation-access.log | tail -20

# Check nginx upstream status
docker exec correlation-lb cat /etc/nginx/nginx.conf | grep -A 10 "upstream correlation_backend"
```

### Step 4.5: Test Failover

**Kill one instance and verify traffic continues:**

```bash
echo "Testing failover - killing instance 2..."

# Kill instance 2
docker kill correlation-engine-2

# Immediately send traffic
for i in {1..10}; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
  echo "Request $i: HTTP $RESPONSE"
  sleep 0.5
done

# All should be 200 OK (routed to instances 1 and 3)

# Check nginx error log
docker exec correlation-lb tail -20 /var/log/nginx/correlation-error.log

# Restart instance 2
echo "Restarting instance 2..."
docker-compose up -d correlation-engine-2

# Wait for health check
sleep 15

# Verify it's back in rotation
docker-compose ps correlation-engine-2
```

### Step 4.6: Test Shared State

**Verify all instances share Redis state:**

```bash
# Send correlation to instance 1 via direct connection
TRACE_ID="shared-state-test-$(date +%s)"

# Force traffic to instance 1
docker exec correlation-engine-1 curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {"service": "shared-test", "host": "localhost", "env": "dev"},
    "records": [{
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "severity": "INFO",
      "message": "Shared state test",
      "trace_id": "'$TRACE_ID'"
    }]
  }'

# Wait for correlation to be created
sleep 5

# Check if instance 2 can see it (via Redis)
docker exec correlation-engine-2 curl -s "http://localhost:8080/api/correlations?trace_id=$TRACE_ID" | jq

# Should return the correlation event
```

### ✅ Phase 4 Complete Checklist

- [ ] 3 correlation engine instances running
- [ ] Load balancer distributes traffic evenly (~33% each)
- [ ] Failover works (kill instance, traffic continues)
- [ ] All instances share Redis state
- [ ] nginx access logs show distribution
- [ ] No errors in nginx error log

---

## Phase 5: Production Hardening

### Step 5.1: Configure Redis Persistence

**Update docker-compose.yml Redis service:**

```yaml
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: |
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
    volumes:
      - redis-data:/data
    networks:
      - observability
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Restart Redis:**
```bash
docker-compose up -d redis

# Wait for restart
sleep 10

# Verify persistence is enabled
docker exec redis redis-cli CONFIG GET appendonly
# Expected: 1) "appendonly" 2) "yes"

docker exec redis redis-cli CONFIG GET save
# Expected: RDB save points configured
```

### Step 5.2: Set Up Prometheus Alerts

**Create `prometheus-alerts.yml`:**

```bash
cat > observability-stack/prometheus/alerts.yml <<'EOF'
groups:
  - name: correlation_engine_alerts
    interval: 30s
    rules:
      # Instance health
      - alert: CorrelationEngineDown
        expr: up{job="correlation-engine"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Correlation Engine instance is down"
          description: "Instance {{ $labels.instance }} has been down for more than 1 minute"

      # Redis connection issues
      - alert: RedisConnectionErrors
        expr: rate(redis_errors_total{error_type="ConnectionError"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Redis connection errors detected"
          description: "{{ $value }} Redis connection errors/sec on {{ $labels.instance }}"

      # High Redis latency
      - alert: HighRedisLatency
        expr: histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis operations are slow"
          description: "p95 Redis latency is {{ $value }}s (threshold: 0.1s)"

      # Queue saturation
      - alert: CorrelationQueueNearlyFull
        expr: correlation_queue_depth{queue_type="logs"} > 8000
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Correlation queue nearly full"
          description: "Log queue depth is {{ $value }}/10000 on {{ $labels.instance }}"

      # Export failures
      - alert: HighExportFailureRate
        expr: rate(export_attempts_total{status="error"}[5m]) / rate(export_attempts_total[5m]) > 0.05
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High export failure rate"
          description: "{{ $value | humanizePercentage }} of exports failing to {{ $labels.backend }}"

      # Circuit breaker open
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{backend=~"loki|tempo"} == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker is open"
          description: "Circuit breaker for {{ $labels.backend }} has been open for >1min"

      # Redis memory usage
      - alert: RedisHighMemory
        expr: redis_used_memory_bytes / redis_max_memory_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage high"
          description: "Redis is using {{ $value | humanizePercentage }} of max memory"

      # No correlations being created
      - alert: NoCorrelationsCreated
        expr: rate(correlation_events_total[5m]) == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "No correlations being created"
          description: "No correlation events created in last 10 minutes"
EOF
```

**Update Prometheus config to load alerts:**

```bash
# Add to prometheus.yml
cat >> observability-stack/prometheus/prometheus.yml <<'EOF'

rule_files:
  - /etc/prometheus/alerts.yml
EOF

# Restart Prometheus
docker-compose restart prometheus
```

### Step 5.3: Create Grafana Dashboard

**Import correlation engine dashboard JSON:**

```bash
cat > correlation-dashboard.json <<'EOF'
{
  "dashboard": {
    "title": "Correlation Engine - Production",
    "tags": ["correlation", "observability"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Instances Status",
        "targets": [{"expr": "up{job=\"correlation-engine\"}"}],
        "type": "stat"
      },
      {
        "title": "Request Rate",
        "targets": [{"expr": "rate(correlation_api_requests_total[5m])"}],
        "type": "graph"
      },
      {
        "title": "Redis Operations",
        "targets": [{"expr": "rate(redis_operations_total[5m])"}],
        "type": "graph"
      },
      {
        "title": "Redis Latency (p95)",
        "targets": [{"expr": "histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket[5m]))"}],
        "type": "graph"
      },
      {
        "title": "Queue Depth",
        "targets": [{"expr": "correlation_queue_depth"}],
        "type": "graph"
      },
      {
        "title": "Export Success Rate",
        "targets": [{"expr": "rate(export_attempts_total{status=\"success\"}[5m]) / rate(export_attempts_total[5m])"}],
        "type": "graph"
      }
    ]
  }
}
EOF

# Import to Grafana
curl -X POST \
  -H "Content-Type: application/json" \
  -d @correlation-dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

### ✅ Phase 5 Complete Checklist

- [ ] Redis persistence enabled (AOF + RDB)
- [ ] Prometheus alerts configured
- [ ] Grafana dashboard created
- [ ] All health endpoints working
- [ ] Monitoring alerts test successfully

---

## Monitoring & Dashboards

### Access Web UIs

```bash
# Grafana
open http://localhost:3000
# Default login: admin / admin

# Pyroscope
open http://localhost:4040

# Prometheus
open http://localhost:9090
```

### Key Prometheus Queries

```promql
# Redis state backend (0=memory, 1=redis)
correlation_state_backend

# Request rate
rate(correlation_api_requests_total[5m])

# Redis operations rate
rate(redis_operations_total[5m])

# Redis p95 latency
histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket[5m]))

# Export success rate
rate(export_attempts_total{status="success"}[5m]) / rate(export_attempts_total[5m])

# Queue depth
correlation_queue_depth

# Error rate
rate(redis_errors_total[5m])

# Circuit breaker state
circuit_breaker_state
```

---

## Testing & Verification

### Load Test Script

```bash
cat > load_test.sh <<'EOF'
#!/bin/bash

REQUESTS=${1:-1000}
CONCURRENCY=${2:-10}

echo "Running load test: $REQUESTS requests with $CONCURRENCY concurrency"

START_TIME=$(date +%s)

for i in $(seq 1 $REQUESTS); do
  (
    curl -s -X POST http://localhost:8080/api/logs \
      -H "Content-Type: application/json" \
      -d '{
        "resource": {"service": "load-test", "host": "localhost", "env": "dev"},
        "records": [{
          "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
          "severity": "INFO",
          "message": "Load test message '$i'",
          "trace_id": "load-'$RANDOM'"
        }]
      }' > /dev/null
  ) &

  # Limit concurrency
  if [ $((i % CONCURRENCY)) -eq 0 ]; then
    wait
    echo "Progress: $i/$REQUESTS requests sent..."
  fi
done

wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "Load test complete!"
echo "Total requests: $REQUESTS"
echo "Duration: ${DURATION}s"
echo "Requests/sec: $((REQUESTS / DURATION))"
EOF

chmod +x load_test.sh

# Run load test
./load_test.sh 1000 20
```

### Chaos Test (Instance Failures)

```bash
cat > chaos_test.sh <<'EOF'
#!/bin/bash

echo "Starting chaos test - will randomly kill instances every 30-90 seconds"
echo "Press Ctrl+C to stop"

while true; do
  # Random sleep between 30-90 seconds
  SLEEP=$((30 + RANDOM % 60))
  echo "Waiting ${SLEEP}s before next chaos event..."
  sleep $SLEEP

  # Pick random instance (1-3)
  INSTANCE=$((1 + RANDOM % 3))

  echo "[$(date)] Killing correlation-engine-$INSTANCE"
  docker kill correlation-engine-$INSTANCE

  # Wait 10 seconds
  sleep 10

  # Restart
  echo "[$(date)] Restarting correlation-engine-$INSTANCE"
  docker-compose up -d correlation-engine-$INSTANCE

  # Wait for health check
  sleep 20
done
EOF

chmod +x chaos_test.sh

# Run chaos test in background
nohup ./chaos_test.sh > chaos.log 2>&1 &

# Monitor while chaos test runs
watch -n 5 'docker-compose ps | grep correlation'

# Stop chaos test
pkill -f chaos_test.sh
```

---

## Troubleshooting

### Common Issues

#### Issue: "redis library not installed"

**Symptoms:**
```
ImportError: redis library required for RedisStateManager
```

**Solution:**
```bash
# Rebuild Docker image with dependencies
docker-compose build correlation-engine

# Verify redis is in requirements.txt
grep redis correlation-engine/requirements.txt
# Should show: redis==5.0.1

# Restart
docker-compose up -d correlation-engine-1 correlation-engine-2 correlation-engine-3
```

#### Issue: "Failed to connect to Redis"

**Symptoms:**
```
ERROR | Failed to connect to Redis | error=...
```

**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker exec redis redis-cli ping
# Expected: PONG

# Check network
docker exec correlation-engine-1 ping -c 3 redis

# Check Redis URL in env
docker exec correlation-engine-1 env | grep REDIS_URL
# Should be: redis://redis:6379

# Restart Redis and correlation engines
docker-compose restart redis
sleep 10
docker-compose restart correlation-engine-1 correlation-engine-2 correlation-engine-3
```

#### Issue: Pyroscope not collecting profiles

**Symptoms:**
- No profiles in Pyroscope UI
- Flame graphs empty

**Solution:**
```bash
# Check Pyroscope is enabled
docker exec correlation-engine-1 env | grep ENABLE_PYROSCOPE
# Should be: ENABLE_PYROSCOPE=true

# Check logs for Pyroscope init
docker logs correlation-engine-1 | grep -i pyroscope

# Restart with fresh environment
docker-compose restart correlation-engine-1 correlation-engine-2 correlation-engine-3

# Generate traffic to create profiles
./load_test.sh 500 10

# Wait 60 seconds, then check Pyroscope
open http://localhost:4040
```

#### Issue: Uneven load distribution

**Symptoms:**
- One instance gets 90% of traffic
- Others idle

**Solution:**
```bash
# Check nginx upstream config
docker exec correlation-lb cat /etc/nginx/nginx.conf | grep -A 10 "upstream"

# Verify all instances are healthy
docker-compose ps | grep correlation-engine

# Restart nginx
docker-compose restart correlation-lb

# Test distribution again
for i in {1..30}; do curl -s http://localhost:8080/health > /dev/null; done
docker logs correlation-engine-1 2>&1 | grep -c "request_completed"
docker logs correlation-engine-2 2>&1 | grep -c "request_completed"
docker logs correlation-engine-3 2>&1 | grep -c "request_completed"
```

#### Issue: High Redis latency

**Symptoms:**
```
redis_operation_duration_seconds p95 > 100ms
```

**Solution:**
```bash
# Check Redis memory
docker exec redis redis-cli INFO memory

# Check Redis CPU
docker stats redis

# Check slow queries
docker exec redis redis-cli SLOWLOG GET 10

# Increase Redis memory limit
# Edit docker-compose.yml, change:
# --maxmemory 4gb  (from 2gb)

# Restart Redis
docker-compose up -d redis
```

#### Issue: correlations not persisting across restarts

**Symptoms:**
- Restart container, correlations disappear

**Solution:**
```bash
# Check Redis persistence is enabled
docker exec redis redis-cli CONFIG GET appendonly
# Expected: "yes"

# Check AOF file exists
docker exec redis ls -lh /data/
# Should see: appendonly.aof

# Check RDB dump exists
docker exec redis redis-cli CONFIG GET save
# Should have save points

# If persistence not enabled, update docker-compose.yml
# (See Phase 5.1)
```

---

## Rollback Procedures

### Rollback: Disable Multi-Instance (Back to Single)

```bash
# Stop multi-instance setup
docker-compose stop \
  correlation-lb \
  correlation-engine-1 \
  correlation-engine-2 \
  correlation-engine-3

# Restore original docker-compose.yml
cp docker-compose.yml.backup docker-compose.yml

# Start single instance
docker-compose up -d correlation-engine

# Verify
docker-compose ps correlation-engine
```

### Rollback: Disable Redis State (Back to In-Memory)

```bash
cd correlation-engine/

# Disable Redis
sed -i 's/USE_REDIS_STATE=true/USE_REDIS_STATE=false/' .env

cd ..

# Restart
docker-compose restart correlation-engine

# Verify in-memory mode
curl -s http://localhost:8080/metrics | grep correlation_state_backend
# Expected: correlation_state_backend 0.0
```

### Rollback: Disable Pyroscope

```bash
cd correlation-engine/

# Disable Pyroscope
sed -i 's/ENABLE_PYROSCOPE=true/ENABLE_PYROSCOPE=false/' .env

cd ..

# Restart
docker-compose restart correlation-engine

# Verify
docker logs correlation-engine | grep -i pyroscope
# Should not see "Pyroscope profiling enabled"
```

---

## Tear Down

### Stop All Services

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Clean up everything
docker system prune -a --volumes
```

### Partial Tear Down (Keep Data)

```bash
# Stop containers but keep volumes
docker-compose down

# Data persists in:
# - redis-data
# - loki-data
# - tempo-data
# - prometheus-data
# - grafana-data

# Restart later with data intact
docker-compose up -d
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Check service health: `docker-compose ps`
- Review logs: `docker-compose logs --tail=100`
- Check disk space: `df -h`

**Weekly:**
- Review Grafana dashboards
- Check Prometheus alerts
- Review Pyroscope flame graphs
- Clean up old Docker images: `docker image prune -a`

**Monthly:**
- Update Docker images: `docker-compose pull`
- Review Redis memory usage
- Backup configuration files
- Test failover procedures

### Backup Procedure

```bash
# Backup Redis data
docker exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb

# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  correlation-engine/.env \
  correlation-lb-nginx.conf \
  observability-stack/

# Backup Grafana dashboards
curl -H "Authorization: Bearer <admin-api-key>" \
  http://localhost:3000/api/search?type=dash-db | \
  jq -r '.[].uid' | \
  xargs -I {} curl -H "Authorization: Bearer <admin-api-key>" \
    http://localhost:3000/api/dashboards/uid/{} > dashboards-backup.json
```

### Upgrade Procedure

```bash
# 1. Backup current state
./backup.sh

# 2. Pull latest code
git pull origin main

# 3. Stop services
docker-compose down

# 4. Rebuild images
docker-compose build

# 5. Start services
docker-compose up -d

# 6. Verify health
./health_check.sh
```

---

## Quick Reference Commands

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Restart correlation engines
docker-compose restart correlation-engine-1 correlation-engine-2 correlation-engine-3

# Check Redis
docker exec redis redis-cli INFO

# Check metrics
curl http://localhost:8080/metrics

# Health check
curl http://localhost:8080/health/ready

# Load test
./load_test.sh 1000 20

# Chaos test
./chaos_test.sh

# Stop everything
docker-compose down

# Full cleanup
docker-compose down -v && docker system prune -af
```

---

## Support & Resources

**Documentation:**
- Architecture: `HORIZONTAL_SCALING.md`
- This guide: `MASTER_SETUP_GUIDE.md`
- API docs: http://localhost:8080/docs

**Monitoring:**
- Grafana: http://localhost:3000 (admin/admin)
- Pyroscope: http://localhost:4040
- Prometheus: http://localhost:9090

**Logs:**
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs correlation-engine-1

# Follow logs
docker-compose logs -f --tail=100
```

---

**Version:** 1.0.0
**Last Updated:** $(date +%Y-%m-%d)
**Status:** Production Ready
