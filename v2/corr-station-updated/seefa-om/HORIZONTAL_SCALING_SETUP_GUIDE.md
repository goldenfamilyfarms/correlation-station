# Horizontal Scaling - Manual Setup Guide

**Complete step-by-step guide to implement Redis-based horizontal scaling for the Correlation Engine**

This guide will walk you through manually setting up horizontal scaling to run multiple Correlation Engine instances that share state via Redis.

---

## =Ë Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Enable Redis State (Single Instance)](#phase-1-enable-redis-state-single-instance)
3. [Phase 2: Scale to Multiple Instances](#phase-2-scale-to-multiple-instances)
4. [Phase 3: Production Hardening](#phase-3-production-hardening)
5. [Monitoring & Verification](#monitoring--verification)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Instructions](#rollback-instructions)

---

## Prerequisites

 **Before you begin, ensure you have:**

- [ ] Docker and Docker Compose installed
- [ ] This repository cloned locally
- [ ] Basic understanding of Redis
- [ ] Access to view Grafana dashboards (optional but recommended)

**Check current setup:**
```bash
cd /path/to/correlation-station/v2/corr-station-updated/seefa-om

# Verify services are running
docker-compose ps

# Check Redis is available in requirements
grep redis correlation-engine/requirements.txt

# Verify Redis config exists
grep -A 5 "use_redis_state" correlation-engine/app/config.py
```

---

## Phase 1: Enable Redis State (Single Instance)

**Goal:** Switch from in-memory state to Redis while still running a single instance. This validates Redis works before scaling.

### Step 1.1: Start Redis

```bash
# Navigate to project root
cd /path/to/correlation-station/v2/corr-station-updated/seefa-om

# Check if Redis is already in docker-compose.yml
grep -A 10 "redis" docker-compose.yml
```

**If Redis is NOT in docker-compose.yml, add it:**

```yaml
# Add to docker-compose.yml under services:
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - observability
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

# Add to volumes section at top level:
volumes:
  redis-data: {}
```

**Start Redis:**
```bash
# If you added Redis to docker-compose.yml
docker-compose up -d redis

# Wait for Redis to be healthy
docker-compose ps redis

# Test Redis connection
docker exec -it redis redis-cli ping
# Expected output: PONG
```

### Step 1.2: Configure Environment Variables

Create or update `.env` file in `/correlation-engine/`:

```bash
cd correlation-engine/

# Create .env if it doesn't exist
cat > .env <<'EOF'
# === Horizontal Scaling Configuration ===

# Enable Redis state management (FEATURE FLAG)
USE_REDIS_STATE=true

# Redis connection
REDIS_URL=redis://redis:6379
REDIS_MAX_CONNECTIONS=50
REDIS_KEY_PREFIX=corr:

# Correlation TTL (1 hour)
CORRELATION_TTL_SECONDS=3600

# Cleanup old correlations after 24 hours
MAX_CORRELATION_AGE_HOURS=24

# === Existing Configuration (keep as-is) ===
LOG_LEVEL=info
DEPLOYMENT_ENV=dev
# ... rest of your existing env vars ...
EOF

# Verify .env was created
cat .env | grep -A 5 "REDIS"
```

### Step 1.3: Stop and Restart Correlation Engine

```bash
# Go back to project root
cd ..

# Stop correlation engine
docker-compose stop correlation-engine

# Rebuild with new dependencies (if needed)
docker-compose build correlation-engine

# Start with new Redis configuration
docker-compose up -d correlation-engine

# Watch logs to verify Redis connection
docker-compose logs -f correlation-engine
```

** Look for these log messages:**
```
INFO  | redis_connected | url=redis://redis:6379
INFO  | Correlation Engine started
INFO  | correlation_state_backend | backend=redis
```

**L If you see errors:**
```
ERROR | redis_not_installed | Install: pip install redis
ERROR | Failed to connect to Redis
```
’ See [Troubleshooting](#troubleshooting) section

### Step 1.4: Verify Redis is Working

**Send test traffic:**
```bash
# Send a test log batch
curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "service": "test-service",
      "host": "localhost",
      "env": "dev"
    },
    "records": [{
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "severity": "INFO",
      "message": "Test log message",
      "trace_id": "abc123def456"
    }]
  }'
```

**Check Redis for stored correlations:**
```bash
# Connect to Redis
docker exec -it redis redis-cli

# Inside Redis CLI:
KEYS corr:*
# Should see keys like: corr:time_index, corr:trace:abc123def456, etc.

# Check a correlation
GET corr:<correlation-id-from-KEYS-command>

# Check time index
ZRANGE corr:time_index 0 -1 WITHSCORES

# Exit Redis CLI
exit
```

**Check Prometheus metrics:**
```bash
# View Redis metrics
curl http://localhost:8080/metrics | grep redis

# Expected metrics:
# redis_operations_total
# redis_operation_duration_seconds
# correlation_state_backend 1.0  # 1.0 = Redis enabled
```

### Step 1.5: Monitor for 24 Hours

**Before scaling to multiple instances, run with Redis for 24 hours to ensure stability.**

**Monitoring checklist:**
- [ ] No Redis connection errors in logs
- [ ] Correlations are being stored (check `redis_operations_total{operation="set"}`)
- [ ] Correlations are being retrieved (check `redis_operations_total{operation="get"}`)
- [ ] Redis memory usage is stable (check `docker stats redis`)
- [ ] Application performance is acceptable (p95 latency < 200ms)

**View real-time metrics in Grafana:**
```bash
# Access Grafana
open http://localhost:8443

# Create dashboard with these queries:
# - redis_operations_total
# - redis_operation_duration_seconds
# - correlation_state_backend
```

---

## Phase 2: Scale to Multiple Instances

**Goal:** Run 3 correlation engine instances sharing state via Redis.

### Step 2.1: Update docker-compose.yml for Scaling

**Option A: Using docker-compose scale (simplest)**

```bash
# Scale to 3 instances
docker-compose up -d --scale correlation-engine=3

# Verify 3 instances are running
docker-compose ps correlation-engine
```

**Option B: Explicit instance definitions (more control)**

Edit `docker-compose.yml`:

```yaml
services:
  # Load balancer for correlation engines
  correlation-lb:
    image: nginx:alpine
    container_name: correlation-lb
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./correlation-lb-nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - observability
    depends_on:
      - correlation-engine-1
      - correlation-engine-2
      - correlation-engine-3

  # Correlation Engine Instance 1
  correlation-engine-1:
    image: correlation-engine:latest
    build: ./correlation-engine
    container_name: correlation-engine-1
    restart: unless-stopped
    environment:
      - PORT=8080
      - USE_REDIS_STATE=true
      - REDIS_URL=redis://redis:6379
      - INSTANCE_ID=1  # For logging/metrics
    volumes:
      - ./correlation-engine/app:/app/app
    networks:
      - observability
    depends_on:
      - redis
      - loki
      - tempo

  # Correlation Engine Instance 2
  correlation-engine-2:
    image: correlation-engine:latest
    build: ./correlation-engine
    container_name: correlation-engine-2
    restart: unless-stopped
    environment:
      - PORT=8080
      - USE_REDIS_STATE=true
      - REDIS_URL=redis://redis:6379
      - INSTANCE_ID=2
    volumes:
      - ./correlation-engine/app:/app/app
    networks:
      - observability
    depends_on:
      - redis
      - loki
      - tempo

  # Correlation Engine Instance 3
  correlation-engine-3:
    image: correlation-engine:latest
    build: ./correlation-engine
    container_name: correlation-engine-3
    restart: unless-stopped
    environment:
      - PORT=8080
      - USE_REDIS_STATE=true
      - REDIS_URL=redis://redis:6379
      - INSTANCE_ID=3
    volumes:
      - ./correlation-engine/app:/app/app
    networks:
      - observability
    depends_on:
      - redis
      - loki
      - tempo
```

### Step 2.2: Create nginx Load Balancer Config

**Create `correlation-lb-nginx.conf`:**

```bash
cat > correlation-lb-nginx.conf <<'EOF'
events {
    worker_connections 1024;
}

http {
    # Upstream pool of correlation engines
    upstream correlation_backend {
        least_conn;  # Route to instance with fewest connections

        server correlation-engine-1:8080 max_fails=3 fail_timeout=30s;
        server correlation-engine-2:8080 max_fails=3 fail_timeout=30s;
        server correlation-engine-3:8080 max_fails=3 fail_timeout=30s;

        # Health check
        keepalive 32;
    }

    server {
        listen 80;
        server_name localhost;

        # Logging
        access_log /var/log/nginx/correlation-access.log;
        error_log /var/log/nginx/correlation-error.log;

        # Proxy to correlation engines
        location / {
            proxy_pass http://correlation_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;

            # Retry on failure
            proxy_next_upstream error timeout http_500 http_502 http_503;
        }

        # Health check endpoint
        location /health {
            access_log off;
            proxy_pass http://correlation_backend/health;
        }

        # Metrics endpoint
        location /metrics {
            proxy_pass http://correlation_backend/metrics;
        }
    }
}
EOF
```

### Step 2.3: Start All Instances

```bash
# Stop existing single instance
docker-compose down correlation-engine

# Start all 3 instances + load balancer
docker-compose up -d correlation-engine-1 correlation-engine-2 correlation-engine-3 correlation-lb

# Verify all instances are healthy
docker-compose ps

# Expected output:
# correlation-engine-1    Up      healthy
# correlation-engine-2    Up      healthy
# correlation-engine-3    Up      healthy
# correlation-lb          Up      healthy
```

### Step 2.4: Verify Load Distribution

**Send test traffic:**
```bash
# Send 100 requests
for i in {1..100}; do
  curl -s http://localhost:8080/health > /dev/null
  echo "Request $i sent"
done

# Check logs to see which instance handled each request
docker-compose logs correlation-engine-1 | grep "request_completed" | wc -l
docker-compose logs correlation-engine-2 | grep "request_completed" | wc -l
docker-compose logs correlation-engine-3 | grep "request_completed" | wc -l

# All three should have ~33 requests each
```

**Check nginx load balancer stats:**
```bash
# View nginx access logs
docker exec correlation-lb cat /var/log/nginx/correlation-access.log | tail -20

# Check nginx stats
docker exec correlation-lb nginx -T
```

### Step 2.5: Test Failover

**Kill one instance and verify traffic continues:**

```bash
# Kill instance 2
docker kill correlation-engine-2

# Send traffic
curl http://localhost:8080/health
# Should still work (routed to instance 1 or 3)

# Check nginx errors
docker exec correlation-lb cat /var/log/nginx/correlation-error.log | tail

# Restart instance 2
docker-compose up -d correlation-engine-2

# Wait for health check
sleep 10

# Verify it rejoined the pool
docker-compose ps correlation-engine-2
```

---

## Phase 3: Production Hardening

### Step 3.1: Add Health Check Endpoints

**Add to `correlation-engine/app/routes/health.py` (if not exists):**

```python
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import structlog

router = APIRouter()
logger = structlog.get_logger()

@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the app running?"""
    return {"status": "healthy", "checks": {"app": "running"}}

@router.get("/health/ready")
async def readiness(request):
    """Kubernetes readiness probe - can the app serve traffic?"""
    checks = {}

    # Check Redis connection
    try:
        correlation_engine = request.app.state.correlation_engine
        if hasattr(correlation_engine, 'state') and hasattr(correlation_engine.state, 'redis'):
            await correlation_engine.state.redis.ping()
            checks["redis"] = "connected"
        else:
            checks["redis"] = "in-memory"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks, "error": str(e)}
        )

    # Check exporters
    checks["exporters"] = "ready"

    return {"status": "ready", "checks": checks}
```

**Update `main.py` to include health router:**
```python
from app.routes import health

app.include_router(health.router, prefix="/health", tags=["health"])
```

### Step 3.2: Configure Redis Persistence

**Update docker-compose.yml Redis service:**

```yaml
  redis:
    image: redis:7-alpine
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
```

**Explanation:**
- `--appendonly yes`: Enable AOF (Append Only File) persistence
- `--appendfsync everysec`: Sync to disk every second
- `--maxmemory 4gb`: Limit Redis memory
- `--maxmemory-policy allkeys-lru`: Evict least recently used keys when full
- `--save`: Create RDB snapshots periodically

### Step 3.3: Set Up Monitoring Alerts

**Create `prometheus-alerts.yml`:**

```yaml
groups:
  - name: correlation_engine_alerts
    interval: 30s
    rules:
      - alert: CorrelationEngineDown
        expr: up{job="correlation-engine"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Correlation Engine instance down"
          description: "Instance {{ $labels.instance }} is down"

      - alert: RedisConnectionErrors
        expr: rate(redis_errors_total[5m]) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Redis connection errors detected"
          description: "{{ $value }} errors/sec on {{ $labels.instance }}"

      - alert: HighRedisLatency
        expr: histogram_quantile(0.95, redis_operation_duration_seconds_bucket) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis operations slow"
          description: "p95 latency is {{ $value }}s"

      - alert: CorrelationQueueFull
        expr: correlation_queue_depth > 8000
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Correlation queue nearly full"
          description: "Queue depth: {{ $value }}/10000"
```

---

## Monitoring & Verification

### Check System Status

```bash
# View all services
docker-compose ps

# Check Redis memory usage
docker exec redis redis-cli INFO memory | grep used_memory_human

# Check correlation count in Redis
docker exec redis redis-cli ZCARD corr:time_index

# View logs from all instances
docker-compose logs -f correlation-engine-1 correlation-engine-2 correlation-engine-3
```

### Key Metrics to Monitor

**Access Prometheus:**
```bash
open http://localhost:9090
```

**Run these queries:**

1. **Redis Operations Rate:**
   ```promql
   rate(redis_operations_total[5m])
   ```

2. **Redis Latency (p95):**
   ```promql
   histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket[5m]))
   ```

3. **Correlations Per Instance:**
   ```promql
   rate(instance_correlations_total[5m])
   ```

4. **Error Rate:**
   ```promql
   sum(rate(redis_errors_total[5m])) by (operation, error_type)
   ```

5. **State Backend:**
   ```promql
   correlation_state_backend
   # 0 = in-memory, 1 = redis
   ```

### Grafana Dashboard

**Create a new dashboard with these panels:**

1. **Redis Operations** (Graph)
   ```promql
   sum(rate(redis_operations_total[5m])) by (operation, status)
   ```

2. **Correlation Engine Instances** (Stat)
   ```promql
   count(up{job="correlation-engine"} == 1)
   ```

3. **Redis Latency** (Heatmap)
   ```promql
   redis_operation_duration_seconds_bucket
   ```

4. **Queue Depth** (Graph)
   ```promql
   correlation_queue_depth
   ```

---

## Troubleshooting

### Problem: "redis library not installed"

**Solution:**
```bash
cd correlation-engine/
pip install redis==5.0.1

# Or rebuild Docker image
docker-compose build correlation-engine
```

### Problem: "Failed to connect to Redis"

**Check Redis is running:**
```bash
docker-compose ps redis

# Should show: Up (healthy)
```

**Check Redis logs:**
```bash
docker-compose logs redis

# Look for errors
```

**Test Redis manually:**
```bash
docker exec -it redis redis-cli ping
# Expected: PONG
```

**Check network:**
```bash
# Ensure correlation-engine can reach Redis
docker exec correlation-engine-1 ping -c 3 redis
```

### Problem: High Redis Latency

**Check Redis memory:**
```bash
docker exec redis redis-cli INFO memory
```

**If memory is high, increase maxmemory:**
```yaml
# In docker-compose.yml
redis:
  command: redis-server --maxmemory 8gb
```

**Check slow queries:**
```bash
docker exec redis redis-cli SLOWLOG GET 10
```

### Problem: Correlations Not Being Created

**Check logs:**
```bash
docker-compose logs correlation-engine-1 | grep -i error
```

**Verify Redis state:**
```bash
docker exec redis redis-cli KEYS "corr:*" | wc -l
# Should be > 0 if correlations exist
```

**Check feature flag:**
```bash
docker exec correlation-engine-1 env | grep USE_REDIS_STATE
# Should show: USE_REDIS_STATE=true
```

### Problem: Uneven Load Distribution

**Check nginx upstream status:**
```bash
docker exec correlation-lb nginx -T | grep -A 20 "upstream correlation_backend"
```

**View nginx access log:**
```bash
docker exec correlation-lb tail -100 /var/log/nginx/correlation-access.log | awk '{print $3}' | sort | uniq -c
```

**Restart nginx:**
```bash
docker-compose restart correlation-lb
```

---

## Rollback Instructions

### Rollback to In-Memory State (Single Instance)

If you need to rollback to the original in-memory state:

**Step 1: Update .env**
```bash
cd correlation-engine/

# Disable Redis
sed -i 's/USE_REDIS_STATE=true/USE_REDIS_STATE=false/' .env

# Or manually edit .env and set:
# USE_REDIS_STATE=false
```

**Step 2: Restart with single instance**
```bash
cd ..

# Stop all instances
docker-compose down correlation-engine-1 correlation-engine-2 correlation-engine-3 correlation-lb

# Start single instance
docker-compose up -d correlation-engine

# Verify
docker-compose logs correlation-engine | grep "correlation_state_backend"
# Should see: backend=in-memory
```

**Step 3: Verify in-memory mode**
```bash
curl http://localhost:8080/metrics | grep correlation_state_backend
# Expected: correlation_state_backend 0.0  (0 = in-memory)
```

---

## Success Criteria

 **Phase 1 Complete When:**
- [ ] Redis is running and healthy
- [ ] Correlation engine connects to Redis successfully
- [ ] Correlations are stored in Redis (check with `KEYS corr:*`)
- [ ] No Redis errors in logs for 24 hours
- [ ] Metrics show `correlation_state_backend 1.0`

 **Phase 2 Complete When:**
- [ ] 3+ correlation engine instances running
- [ ] Load balancer distributes traffic evenly
- [ ] Failover works (kill one instance, traffic continues)
- [ ] All instances share same Redis state
- [ ] No correlation data loss during failover

 **Phase 3 Complete When:**
- [ ] Health endpoints return 200 OK
- [ ] Redis persistence enabled (AOF + RDB)
- [ ] Monitoring alerts configured
- [ ] Grafana dashboards created
- [ ] Runbook documented

---

## Next Steps

After completing horizontal scaling:

1. **Load Testing**: Run load tests with 10k+ traces/second
2. **Chaos Testing**: Randomly kill instances during load
3. **Redis Cluster**: Upgrade to Redis Cluster for HA
4. **Kubernetes**: Deploy on K8s with HPA (Horizontal Pod Autoscaler)
5. **Distributed Rate Limiting**: Implement Redis-based rate limiter
6. **Connection Pooling**: Optimize database connection pools

---

## Support

**Issues?**
- Check [Troubleshooting](#troubleshooting) section
- Review logs: `docker-compose logs`
- Check metrics: http://localhost:8080/metrics
- View Grafana: http://localhost:8443

**Questions?**
- See main [HORIZONTAL_SCALING.md](./HORIZONTAL_SCALING.md) for architecture details
- Review Redis documentation: https://redis.io/docs/

**Need help?**
- Create an issue in the repository
- Check existing issues for similar problems

---

**Last Updated:** 2025-01-XX
**Version:** 1.0.0
