# Horizontal Scaling Strategy for Sense Platform

This document outlines the horizontal scaling strategy for the Sense observability platform, including the Correlation Engine and Sense applications (Palantir, Arda, Beorn).

## Table of Contents
- [Overview](#overview)
- [Current Architecture](#current-architecture)
- [Scaling Constraints](#scaling-constraints)
- [Scaling Strategy by Component](#scaling-strategy-by-component)
- [Implementation Roadmap](#implementation-roadmap)
- [Monitoring and Metrics](#monitoring-and-metrics)
- [Deployment Patterns](#deployment-patterns)

---

## Overview

The Sense platform consists of multiple components with different scaling characteristics:

| Component | Type | Current State | Scaling Complexity |
|-----------|------|---------------|-------------------|
| **Correlation Engine** | Stateful | Single instance | **High** - Requires state externalization |
| **Palantir** | Stateless | Multi-instance capable | **Low** - Ready for horizontal scaling |
| **Arda** | Stateless | Multi-instance capable | **Low** - Ready for horizontal scaling |
| **Beorn** | Stateless | Multi-instance capable | **Low** - Ready for horizontal scaling |
| **Gateway** | Stateless | Multi-instance capable | **Medium** - Requires load balancer config |

---

## Current Architecture

### Correlation Engine (FastAPI + AsyncIO)
```
┌─────────────────────────────────────────────────┐
│          Correlation Engine (Single)            │
│  ┌─────────────┐  ┌──────────────┐             │
│  │ OTLP Traces │  │  OTLP Logs   │             │
│  └──────┬──────┘  └──────┬───────┘             │
│         │                │                      │
│         └────────┬───────┘                      │
│                  ▼                               │
│         ┌────────────────┐                      │
│         │ In-Memory      │                      │
│         │ Correlation    │ ◄─ BOTTLENECK       │
│         │ Index          │                      │
│         └────────┬───────┘                      │
│                  ▼                               │
│         ┌────────────────┐                      │
│         │  Export to     │                      │
│         │ Loki/Tempo     │                      │
│         └────────────────┘                      │
└─────────────────────────────────────────────────┘
```

**Limitations:**
- ❌ Correlation state stored in-memory (non-shareable)
- ❌ Single point of failure
- ❌ Vertical scaling only
- ❌ Limited by single machine resources

### Sense Apps (Flask + Gunicorn)
```
┌──────────────────────────────────────┐
│     Load Balancer (nginx/HAProxy)    │
└───────┬──────────┬───────────────┬───┘
        │          │               │
   ┌────▼───┐ ┌───▼────┐    ┌────▼───┐
   │Palantir│ │Palantir│    │Palantir│
   │   #1   │ │   #2   │ ...│   #N   │
   └────────┘ └────────┘    └────────┘
```

**Current State:**
- ✅ Stateless design (ready for horizontal scaling)
- ✅ Gunicorn multi-worker support
- ⚠️ Shared database connections (needs pooling optimization)
- ⚠️ External service rate limiting (MDSO, ODIN, etc.)

---

## Scaling Constraints

### 1. Correlation State Management ⚠️ **CRITICAL BLOCKER**

**Problem:** Correlation index is stored in-memory and cannot be shared across instances.

**Current Implementation:**
```python
# correlation-engine/app/pipeline/correlator.py
class CorrelationEngine:
    def __init__(self):
        self.correlation_index: Dict[str, CorrelationEntry] = {}  # ❌ In-memory only
```

**Impact:**
- Cannot run multiple correlation engine instances
- All traces/logs must route to same instance
- No failover capability

**Solution:** See [Priority 3 Roadmap Item](#priority-3-this-month---externalize-correlation-state)

### 2. Queue Management

**Current:** AsyncIO queues (in-memory, per-instance)
```python
self.trace_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
```

**Scaling Impact:**
- ✅ Each instance has independent queues
- ❌ No work distribution across instances
- ⚠️ Backpressure is per-instance (could overwhelm single node)

**Recommendation:**
- **Short-term:** Vertical scaling (increase MAX_QUEUE_SIZE, add more CPU/memory)
- **Long-term:** Distributed message queue (RabbitMQ, Kafka, Redis Streams)

### 3. External Service Rate Limits

**Services with Rate Limits:**
- MDSO (MetaData Service Orchestrator)
- ODIN (Orchestration/Data Interface)
- Hydra, ISE, Remedy, etc.

**Scaling Considerations:**
- Multiple instances = multiplied request rate
- Need centralized rate limiting or token bucket
- Circuit breaker patterns already implemented in `sense_common`

**Solution:**
- Implement distributed rate limiter (Redis-based)
- Centralized API gateway with rate limiting
- Service mesh (Istio, Linkerd) for traffic management

### 4. Database Connection Pooling

**Current State:** Each app instance creates own DB connections

**Scaling Impact:**
- Linear growth: N instances × M connections per instance
- Database connection exhaustion risk

**Solution:**
```python
# Use connection pooling in sense_common
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,           # Max connections per instance
    max_overflow=10,       # Burst capacity
    pool_timeout=30,
    pool_recycle=3600,     # Recycle connections hourly
)
```

---

## Scaling Strategy by Component

### Correlation Engine - Stateful Service

#### Phase 1: Vertical Scaling (Immediate - Weeks 1-2) ✅
**Current capacity can be increased by:**
1. Increase queue sizes:
   ```python
   # app/config.py
   MAX_QUEUE_SIZE=10000  # Up from 1000
   ```
2. Add more CPU cores for AsyncIO workers
3. Increase memory for larger correlation index
4. Optimize correlation window trimming

**Expected Capacity:** 2-5x current throughput

#### Phase 2: Active-Passive HA (Weeks 3-4)
**Setup:**
```yaml
# docker-compose.yml
services:
  correlation-engine-primary:
    image: correlation-engine:latest
    environment:
      - ROLE=primary

  correlation-engine-standby:
    image: correlation-engine:latest
    environment:
      - ROLE=standby
      - WATCH_PRIMARY=correlation-engine-primary:8000
```

**Failover Logic:**
- Health check primary every 5s
- Promote standby on 3 consecutive failures
- Use shared storage for periodic state snapshots

**Expected Uptime:** 99.9% (3 nines)

#### Phase 3: Horizontal Scaling with Shared State (Month 2) 🎯

**Architecture:**
```
┌────────────────────────────────────────────────────────┐
│                   Load Balancer                        │
│              (Sticky sessions by trace_id)             │
└─────┬──────────────────┬──────────────────┬───────────┘
      │                  │                  │
┌─────▼──────┐    ┌─────▼──────┐    ┌─────▼──────┐
│ Corr Eng#1 │    │ Corr Eng#2 │    │ Corr Eng#3 │
└─────┬──────┘    └─────┬──────┘    └─────┬──────┘
      │                  │                  │
      └──────────────────┴──────────────────┘
                         │
                    ┌────▼─────┐
                    │  Redis   │
                    │ Cluster  │
                    │ (Shared  │
                    │  State)  │
                    └──────────┘
```

**Implementation:**
```python
# New: app/pipeline/state_manager.py
import redis.asyncio as redis
from typing import Dict, Optional

class RedisStateManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def get_correlation(self, correlation_id: str) -> Optional[CorrelationEntry]:
        """Retrieve correlation from Redis"""
        data = await self.redis.get(f"corr:{correlation_id}")
        if data:
            return CorrelationEntry.parse_raw(data)
        return None

    async def set_correlation(
        self,
        correlation_id: str,
        entry: CorrelationEntry,
        ttl_seconds: int = 3600
    ):
        """Store correlation in Redis with TTL"""
        await self.redis.setex(
            f"corr:{correlation_id}",
            ttl_seconds,
            entry.json()
        )

    async def add_to_time_index(self, timestamp: datetime, correlation_id: str):
        """Add to sorted set for time-based queries"""
        await self.redis.zadd(
            "corr:time_index",
            {correlation_id: timestamp.timestamp()}
        )

    async def cleanup_old_correlations(self, cutoff_time: datetime):
        """Remove correlations older than cutoff"""
        cutoff_ts = cutoff_time.timestamp()
        old_ids = await self.redis.zrangebyscore(
            "corr:time_index",
            0,
            cutoff_ts
        )

        if old_ids:
            # Remove from time index
            await self.redis.zremrangebyscore("corr:time_index", 0, cutoff_ts)
            # Remove correlation data
            await self.redis.delete(*[f"corr:{id}" for id in old_ids])
```

**Configuration:**
```python
# app/config.py
class Settings(BaseSettings):
    # Redis Configuration
    redis_url: str = "redis://redis-cluster:6379"
    redis_max_connections: int = 50
    correlation_ttl_seconds: int = 3600
    use_redis_state: bool = True  # Feature flag
```

**Load Balancing Strategy:**
- **Option 1:** Sticky sessions by trace_id hash (simple, works immediately)
- **Option 2:** Consistent hashing ring (better distribution)
- **Option 3:** Full shared state (all instances access Redis for every correlation)

**Expected Capacity:** 10-50x current throughput

### Sense Apps (Palantir, Arda, Beorn) - Stateless Services

#### Current Capability: Horizontally Scalable ✅

**Deployment:**
```yaml
# docker-compose.yml
services:
  palantir:
    image: palantir:latest
    deploy:
      replicas: 3  # ✅ Already supported
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  nginx-lb:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
```

**Nginx Load Balancer Config:**
```nginx
# nginx.conf
upstream palantir_backend {
    least_conn;  # Route to instance with fewest connections

    server palantir-1:8000 max_fails=3 fail_timeout=30s;
    server palantir-2:8000 max_fails=3 fail_timeout=30s;
    server palantir-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;

    location / {
        proxy_pass http://palantir_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Health check
        proxy_next_upstream error timeout http_500 http_502 http_503;
        proxy_connect_timeout 5s;
    }
}
```

**Health Checks:**
```python
# Add to each app: palantir_app/routes/health.py
from flask import Blueprint

health_bp = Blueprint('health', __name__)

@health_bp.route('/health/live')
def liveness():
    """Kubernetes liveness probe"""
    return {'status': 'healthy'}, 200

@health_bp.route('/health/ready')
def readiness():
    """Kubernetes readiness probe"""
    # Check database connectivity
    try:
        db.session.execute('SELECT 1')
        return {'status': 'ready'}, 200
    except Exception as e:
        return {'status': 'not_ready', 'error': str(e)}, 503
```

**Kubernetes Deployment:**
```yaml
# k8s/palantir-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: palantir
spec:
  replicas: 3
  selector:
    matchLabels:
      app: palantir
  template:
    metadata:
      labels:
        app: palantir
    spec:
      containers:
      - name: palantir
        image: palantir:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: USAGE_DESIGNATION
          value: "PRODUCTION"
        - name: WORKERS
          value: "4"
---
apiVersion: v1
kind: Service
metadata:
  name: palantir
spec:
  selector:
    app: palantir
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Auto-scaling Configuration:**
```yaml
# k8s/palantir-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: palantir-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: palantir
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

---

## Implementation Roadmap

### Priority 1 (This Week) ✅ COMPLETED
- [x] Fix SSL certificate verification
- [x] Add queue backpressure metrics and retry logic
- [x] Create .env.example files for all services
- [x] Fix correlation index corruption bug

### Priority 2 (Next 2 Weeks)
- [x] Extract duplicated common_sense to shared library
- [ ] **Implement Repository Pattern for MDSO access**
  - Abstract MDSO client behind repository interface
  - Enable mocking and testing
  - Prepare for distributed rate limiting
- [x] Add comprehensive integration tests
- [x] Document horizontal scaling strategy *(this document)*

### Priority 3 (This Month) - Externalize Correlation State

**Goal:** Enable horizontal scaling of Correlation Engine

**Tasks:**
1. **Set up Redis Cluster** (Week 3)
   ```bash
   # docker-compose.yml
   services:
     redis-master:
       image: redis:7-alpine
       command: redis-server --appendonly yes
     redis-replica-1:
       image: redis:7-alpine
       command: redis-server --slaveof redis-master 6379
   ```

2. **Implement RedisStateManager** (Week 3)
   - Create `app/pipeline/state_manager.py`
   - Implement async Redis operations
   - Add feature flag for gradual rollout

3. **Refactor CorrelationEngine** (Week 4)
   ```python
   # Before
   self.correlation_index: Dict[str, CorrelationEntry] = {}

   # After
   if settings.use_redis_state:
       self.state = RedisStateManager(settings.redis_url)
   else:
       self.state = InMemoryStateManager()  # Fallback
   ```

4. **Testing** (Week 4)
   - Unit tests with fake Redis
   - Integration tests with real Redis
   - Load testing with multiple instances
   - Chaos testing (kill random instances)

5. **Deploy with Feature Flag** (Week 4)
   ```python
   # Gradual rollout
   use_redis_state=False  # Week 4 - testing
   use_redis_state=True   # Week 5 - production
   ```

**Success Criteria:**
- [ ] 3+ correlation engine instances running simultaneously
- [ ] 99.9% uptime during instance failures
- [ ] 10x throughput improvement
- [ ] Zero correlation data loss

### Priority 4 (Month 2) - Production Hardening

**Tasks:**
1. **Implement Distributed Rate Limiting**
   - Redis-based token bucket
   - Per-service rate limits for MDSO, ODIN, etc.

2. **Add Circuit Breakers to All External Calls**
   - Already implemented in `sense_common.http.client`
   - Migrate all apps to use sense_common

3. **Database Connection Pooling**
   - Configure SQLAlchemy pool settings
   - Monitor connection usage

4. **Observability Improvements**
   - Distributed tracing across all components
   - Centralized logging aggregation
   - Custom Grafana dashboards for scaling metrics

---

## Monitoring and Metrics

### Key Metrics for Scaling Decisions

#### Correlation Engine
```python
# Existing metrics to monitor
correlation_index_size = Gauge('correlation_index_size', 'Number of active correlations')
queue_size = Gauge('queue_size', 'Current queue depth', ['type'])
processing_time = Histogram('correlation_processing_seconds', 'Time to correlate')
dropped_batches = Counter('dropped_batches_total', 'Batches dropped due to backpressure', ['type'])

# New metrics needed
redis_operation_duration = Histogram('redis_operation_seconds', 'Redis operation latency', ['operation'])
redis_errors = Counter('redis_errors_total', 'Redis operation errors', ['operation'])
instance_correlation_count = Counter('instance_correlations_total', 'Correlations per instance')
```

#### Sense Apps
```python
# Add to sense_common.observability
request_duration = Histogram('http_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_requests = Gauge('http_active_requests', 'Currently processing requests')
error_rate = Counter('http_errors_total', 'HTTP errors', ['status_code'])
external_api_calls = Counter('external_api_calls_total', 'External API calls', ['service', 'status'])
```

### Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU > 70% (sustained 5min) | 70% | Scale up +1 instance |
| Memory > 80% | 80% | Scale up +1 instance |
| Queue depth > 80% capacity | 8000/10000 | Scale up or increase queue size |
| Request latency p95 > 500ms | 500ms | Investigate, consider scaling |
| Error rate > 1% | 1% | Alert, investigate before scaling |
| Redis latency p99 > 50ms | 50ms | Check Redis cluster health |

### Grafana Dashboard Queries

```promql
# CPU utilization across all instances
rate(container_cpu_usage_seconds_total{container="correlation-engine"}[5m])

# Queue depth trend
correlation_queue_size

# Correlation throughput
rate(instance_correlations_total[1m])

# Redis operation latency p95
histogram_quantile(0.95, sum(rate(redis_operation_duration_bucket[5m])) by (le, operation))

# Error rate
sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m]))
```

---

## Deployment Patterns

### Pattern 1: Docker Compose (Development/Small Prod)

```yaml
# docker-compose.scaling.yml
version: '3.8'

services:
  # Load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - palantir-1
      - palantir-2
      - palantir-3

  # Sense Apps (3 replicas each)
  palantir-1:
    image: palantir:latest
    environment:
      - INSTANCE_ID=1
  palantir-2:
    image: palantir:latest
    environment:
      - INSTANCE_ID=2
  palantir-3:
    image: palantir:latest
    environment:
      - INSTANCE_ID=3

  # Correlation Engine (initially 1, then scale to 3)
  correlation-engine-1:
    image: correlation-engine:latest
    environment:
      - INSTANCE_ID=1
      - REDIS_URL=redis://redis-cluster:6379

  # Redis Cluster
  redis-cluster:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

### Pattern 2: Kubernetes (Production)

```bash
# Deploy all components
kubectl apply -f k8s/redis-cluster.yaml
kubectl apply -f k8s/correlation-engine-deployment.yaml
kubectl apply -f k8s/palantir-deployment.yaml
kubectl apply -f k8s/arda-deployment.yaml
kubectl apply -f k8s/beorn-deployment.yaml

# Apply auto-scaling
kubectl apply -f k8s/palantir-hpa.yaml
kubectl apply -f k8s/correlation-engine-hpa.yaml

# Monitor scaling
kubectl get hpa -w
```

---

## Testing Horizontal Scaling

### Load Testing Script

```python
# tests/load_test.py
import asyncio
import httpx
from opentelemetry.proto.trace.v1.trace_pb2 import TracesData

async def send_trace(client: httpx.AsyncClient, trace_id: str):
    """Send a trace to correlation engine"""
    response = await client.post(
        "http://localhost:8000/v1/traces",
        content=create_trace_protobuf(trace_id),
        headers={"Content-Type": "application/x-protobuf"}
    )
    return response.status_code

async def load_test(num_traces: int, concurrency: int):
    """Send num_traces with concurrency level"""
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(num_traces):
            tasks.append(send_trace(client, f"trace-{i}"))

            if len(tasks) >= concurrency:
                results = await asyncio.gather(*tasks)
                print(f"Batch {i//concurrency}: {sum(1 for r in results if r == 200)}/{concurrency} success")
                tasks = []

        if tasks:
            await asyncio.gather(*tasks)

# Run test
asyncio.run(load_test(num_traces=10000, concurrency=100))
```

### Chaos Testing

```bash
# Kill random instances during load test
while true; do
    sleep $((RANDOM % 60 + 30))  # 30-90 seconds
    instance=$(docker ps --filter "name=correlation-engine" --format "{{.Names}}" | shuf -n 1)
    echo "Killing $instance"
    docker kill $instance
    docker-compose up -d  # Restart
done
```

---

## Summary

### Current State
- ✅ **Sense Apps (Palantir, Arda, Beorn):** Ready for horizontal scaling
- ⚠️ **Correlation Engine:** Limited to vertical scaling (state externalization needed)

### Immediate Actions (Weeks 1-2)
1. ✅ Increase queue sizes and optimize vertical scaling
2. ✅ Add health check endpoints to all services
3. Set up load balancer for Sense apps

### Short-term Goals (Month 1)
1. Implement Repository Pattern for MDSO
2. Deploy Redis cluster
3. Implement RedisStateManager
4. Test correlation engine with 3+ instances

### Long-term Goals (Month 2+)
1. Achieve 10x throughput improvement
2. 99.9% uptime with instance failures
3. Full Kubernetes deployment with auto-scaling
4. Comprehensive monitoring and alerting

### Success Metrics
- **Throughput:** 10,000+ traces/second (10x improvement)
- **Latency:** p95 < 100ms for correlation
- **Availability:** 99.9% uptime
- **Scalability:** Linear scaling with instance count
- **Cost:** 50% reduction per-request with horizontal scaling

---

## References

- [Correlation Engine Code](./correlation-engine/)
- [Shared Library](./shared-libs/sense_common/)
- [Test Suite](./correlation-engine/tests/)
- [OpenTelemetry Collector Scaling](https://opentelemetry.io/docs/collector/scaling/)
- [Redis Cluster Tutorial](https://redis.io/topics/cluster-tutorial)
- [Kubernetes HPA Best Practices](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
