# End-to-End Testing Guide for Sense/MDSO/Correlation Station

**Features 2 & 3:** Testing MDSO OTel and Redis Caching

---

## Feature 2: MDSO OTel End-to-End Testing

### Objective
Validate the complete telemetry pipeline from MDSO → Alloy → OTEL Collector → Correlation Engine → Loki/Tempo/Grafana

### Prerequisites
- MDSO-Otel Instrumentation product installed
- Alloy agent running on MDSO server
- OTEL Collector running on META server
- Correlation Engine running
- Grafana stack (Loki, Tempo, Prometheus) available

### Test Scenarios

#### 1. MDSO Trace Generation Test

**Steps:**
1. Trigger a MDSO operation using the MDSO-Otel Instrumentation product
   ```bash
   # Use MDSO product to provision a circuit (example)
   curl -X POST http://mdso-server/api/products/provision \
     -H "Content-Type: application/json" \
     -d '{"circuit_id": "TEST.CIRCUIT.001", "product_type": "eline"}'
   ```

2. Wait 10-15 seconds for telemetry to propagate

3. **Verify in Alloy (MDSO server):**
   ```bash
   # Check Alloy logs
   journalctl -u grafana-alloy -f | grep "traces exported"
   ```

4. **Verify in OTEL Collector (META server):**
   ```bash
   # Check OTEL Collector logs
   docker logs otel-collector | grep "TracesExporter"
   ```

5. **Verify in Correlation Engine:**
   ```bash
   curl http://159.56.4.94:8080/health
   docker logs correlation-engine | grep "TEST.CIRCUIT.001"
   ```

6. **Verify in Tempo:**
   - Open Grafana: `http://austx-mdso-logs-02.chtrse.com/grafana`
   - Navigate to Explore → Tempo
   - Run TraceQL query:
     ```traceql
     { .circuit_id = "TEST.CIRCUIT.001" }
     ```
   - **Expected:** Trace with MDSO spans, attributes include `circuit_id`, `product_type`, `service.name=mdso`

7. **Verify in Loki:**
   - Navigate to Explore → Loki
   - Run LogQL query:
     ```logql
     {job="mdso-otel"} |= "TEST.CIRCUIT.001"
     ```
   - **Expected:** Logs with circuit_id, linked trace_id

#### 2. MDSO Attribute Validation Test

**Verify these attributes are present in MDSO traces:**
- `service.name`: "mdso" or "mdso-otel"
- `service.version`: version string
- `deployment.environment`: "dev", "staging", or "prod"
- `circuit.id`: circuit ID
- `product.type`: "eline", "elan", etc.
- `resource.id`: resource identifier

**Query:**
```traceql
{ .service.name = "mdso" }
| select(.circuit_id, .product_type, .resource_id)
```

#### 3. MDSO → Correlation Engine Integration Test

**Verify correlation engine processes MDSO telemetry:**

```bash
# Check correlation engine Redis cache
docker exec -it correlation-engine-redis redis-cli

# Query for test circuit
> HGETALL trace:TEST.CIRCUIT.001
> LRANGE circuit:TEST.CIRCUIT.001:spans 0 -1
```

**Expected:**
- TraceIndex stored in Redis
- Circuit events indexed by circuit_id
- Spans linked to circuit

### Test Checklist

- [ ] MDSO operation triggers trace generation
- [ ] Alloy receives and exports traces
- [ ] OTEL Collector forwards traces to Correlation Engine
- [ ] Correlation Engine ingests traces successfully
- [ ] Traces appear in Tempo with correct attributes
- [ ] Logs appear in Loki with trace correlation
- [ ] Redis cache contains trace metadata

### Troubleshooting

**Problem:** No traces in Tempo
- Check Alloy logs: `journalctl -u grafana-alloy -f`
- Verify OTEL Collector is reachable: `telnet otel-collector-host 4317`
- Check Correlation Engine health: `curl http://159.56.4.94:8080/health`

**Problem:** Traces missing attributes
- Review MDSO-Otel Instrumentation configuration
- Check attribute propagation in Alloy config
- Verify OTEL SDK version compatibility

---

## Feature 3: Redis Caching Load Testing & Scaling

### Objective
Determine Redis performance characteristics and scaling requirements

### Prerequisites
- Correlation Engine running with Redis integration
- Access to generate OTEL traffic
- Monitoring tools (redis-cli, docker stats, Prometheus)

### Load Test Scenarios

#### 1. Baseline Performance Test

**Test parameters:**
- Rate: 100 spans/second
- Duration: 5 minutes
- Circuit IDs: 100 unique circuits
- Trace depth: 5-10 spans per trace

**Load generator script:**
```bash
#!/bin/bash
# load_test_redis.sh

ENDPOINT="http://159.56.4.94:8080/api/otlp/v1/traces"
RATE=100  # spans/second
DURATION=300  # 5 minutes

python3 << 'EOF'
import requests
import time
import random
import json
from datetime import datetime

endpoint = "http://159.56.4.94:8080/api/otlp/v1/traces"
rate = 100
duration = 300

start_time = time.time()
span_count = 0

while time.time() - start_time < duration:
    circuit_id = f"TEST.CIRCUIT.{random.randint(1, 100):03d}"
    trace_id = f"{random.randint(0, 2**64-1):016x}"

    # Generate OTLP JSON payload
    payload = {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "test-service"}},
                    {"key": "circuit.id", "value": {"stringValue": circuit_id}}
                ]
            },
            "scopeSpans": [{
                "spans": [{
                    "traceId": trace_id,
                    "spanId": f"{random.randint(0, 2**64-1):016x}",
                    "name": "test-operation",
                    "startTimeUnixNano": int(time.time() * 1e9),
                    "endTimeUnixNano": int((time.time() + 0.1) * 1e9),
                    "attributes": [
                        {"key": "circuit.id", "value": {"stringValue": circuit_id}}
                    ]
                }]
            }]
        }]
    }

    requests.post(endpoint, json=payload)
    span_count += 1

    # Rate limiting
    time.sleep(1.0 / rate)

    if span_count % 1000 == 0:
        print(f"Sent {span_count} spans...")

print(f"Load test complete. Sent {span_count} spans in {duration}s")
EOF
```

**Metrics to collect:**
```bash
# During test, monitor:
docker stats correlation-engine-redis

# Redis memory usage
redis-cli INFO MEMORY | grep used_memory_human

# Redis hit/miss rate
redis-cli INFO STATS | grep keyspace

# Queue depth (in Correlation Engine)
curl http://159.56.4.94:8080/metrics | grep queue_depth
```

#### 2. Burst Load Test

**Test parameters:**
- Burst rate: 1000 spans/second for 30 seconds
- Idle: 5 seconds
- Repeat: 10 times

**Observe:**
- Redis memory spikes
- Queue depth changes
- Correlation Engine latency

#### 3. Memory Saturation Test

**Goal:** Determine Redis memory limits

**Steps:**
1. Start with empty Redis
2. Generate traffic until Redis reaches memory limit
3. Monitor eviction count

```bash
# Monitor evictions
watch -n 1 "redis-cli INFO STATS | grep evicted_keys"

# Monitor memory usage
watch -n 1 "redis-cli INFO MEMORY | grep used_memory_human"
```

### Scaling Recommendations Template

Based on test results, document:

```markdown
# Redis Scaling Recommendations

## Test Results Summary
- Baseline load: 100 spans/s sustained ✅/❌
- Burst load: 1000 spans/s peaks ✅/❌
- Memory usage at steady state: X MB
- Memory usage at peak: Y MB
- Hit rate: Z%
- Queue depth max: N spans

## Current Configuration
- Redis instance: Single node
- Memory limit: X GB
- Eviction policy: allkeys-lru
- TTL: 48 hours

## Scaling Decision

### Option 1: Single Instance (if current is sufficient)
**Recommendation:** Keep single Redis instance
**Reason:** Test results show adequate performance
**Resource requirements:**
- Memory: X GB
- CPU: Y cores
- Network: Z Gbps

### Option 2: Redis Cluster (if scaling needed)
**Recommendation:** Implement Redis Cluster with N nodes
**Reason:** Test results show memory/throughput constraints
**Architecture:**
```
Redis Cluster (3 masters, 3 replicas)
  ├─ Master 1 (shards: circuit_id hash 0-5460)
  ├─ Master 2 (shards: circuit_id hash 5461-10922)
  └─ Master 3 (shards: circuit_id hash 10923-16383)
```
**Resource requirements per node:**
- Memory: X GB
- CPU: Y cores
- Network: Z Gbps

### Option 3: Redis Sentinel (if HA needed)
**Recommendation:** Redis Sentinel for high availability
**Architecture:**
```
Redis Primary + 2 Replicas
  └─ Sentinel quorum: 3 nodes
```

## Configuration Recommendations
```yaml
# Redis configuration
maxmemory: 8gb
maxmemory-policy: allkeys-lru
save: ""  # Disable RDB snapshots for cache-only use
appendonly: no  # Disable AOF for performance

# Correlation Engine configuration
REDIS_MAX_CONNECTIONS: 50
REDIS_POOL_SIZE: 20
REDIS_TIMEOUT_MS: 5000
```

## Monitoring Alerts
```promql
# Alert if Redis memory >80%
redis_memory_used_bytes / redis_memory_max_bytes > 0.8

# Alert if eviction rate >100/min
rate(redis_evicted_keys_total[1m]) > 100

# Alert if queue depth >5000
correlation_engine_queue_depth > 5000
```
```

---

## Test Execution Checklist

### Pre-Test
- [ ] Document baseline metrics (CPU, memory, queue depth)
- [ ] Clear Redis cache: `redis-cli FLUSHALL`
- [ ] Ensure Correlation Engine is healthy
- [ ] Set up monitoring dashboards

### During Test
- [ ] Monitor Redis memory usage
- [ ] Monitor queue depth
- [ ] Check for errors in Correlation Engine logs
- [ ] Observe hit/miss ratio

### Post-Test
- [ ] Export Prometheus metrics
- [ ] Analyze peak memory usage
- [ ] Calculate average latency
- [ ] Document scaling decision

---

## Automated Test Script

```bash
#!/bin/bash
# run_redis_scaling_test.sh

set -e

echo "=== Redis Scaling Test ==="
echo "Starting baseline test..."

# Clear Redis
redis-cli FLUSHALL

# Run load test
./load_test_redis.sh

# Collect metrics
echo "Collecting metrics..."
redis-cli INFO MEMORY > redis_memory.txt
redis-cli INFO STATS > redis_stats.txt
curl http://159.56.4.94:8080/metrics > correlation_metrics.txt

# Analyze results
echo "=== Test Results ==="
echo "Redis memory usage:"
cat redis_memory.txt | grep used_memory_human

echo "Redis hit rate:"
cat redis_stats.txt | grep keyspace_hits

echo "Correlation Engine queue depth:"
cat correlation_metrics.txt | grep queue_depth

echo "Test complete. Review results and update REDIS_SCALING_RECOMMENDATIONS.md"
```

---

## Next Steps

1. Run baseline performance test
2. Run burst load test
3. Analyze results
4. Create `REDIS_SCALING_RECOMMENDATIONS.md` with decision
5. Implement scaling changes if needed
6. Re-test to validate improvements
