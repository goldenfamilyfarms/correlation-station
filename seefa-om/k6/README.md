# k6 Load Testing for Correlation Station

This directory contains k6 load testing scripts for the Correlation Engine.

## Prerequisites

Install k6:
```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Windows
choco install k6
```

## Running Tests

### Basic Load Test
Tests health, metrics, and correlation query endpoints:
```bash
k6 run load-test-basic.js
```

With custom base URL:
```bash
k6 run -e BASE_URL=http://localhost:8080 load-test-basic.js
```

### Log Ingestion Load Test
Tests log ingestion endpoints with realistic payloads:
```bash
k6 run load-test-logs.js
```

## Test Scenarios

### load-test-basic.js
- **Duration**: 3.5 minutes
- **Max VUs**: 50
- **Tests**: Health, root, metrics, and correlation query endpoints
- **Thresholds**:
  - 95% of requests < 500ms
  - Error rate < 10%

### load-test-logs.js
- **Duration**: 5.5 minutes
- **Max VUs**: 30
- **Tests**: Log ingestion with batches of 3 logs per request
- **Thresholds**:
  - 95% of requests < 1000ms
  - Error rate < 5%

## Viewing Results

Results are output to:
- `summary.json` - Detailed JSON results
- `logs-summary.json` - Log ingestion test results
- stdout - Formatted text summary

## Integration with Grafana

To visualize k6 results in Grafana:

1. Use k6 with Prometheus remote write:
```bash
k6 run -o experimental-prometheus-rw load-test-basic.js
```

2. Configure k6 environment variables:
```bash
export K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write
export K6_PROMETHEUS_RW_TREND_AS_NATIVE_HISTOGRAM=true
```

3. Import k6 Grafana dashboard (ID: 18030)

## CI/CD Integration

Run tests in Docker:
```bash
docker run --rm -i --network observability \
  -v $(pwd):/scripts \
  grafana/k6:latest run \
  -e BASE_URL=http://correlation-engine:8080 \
  /scripts/load-test-basic.js
```

## Customizing Tests

### Adjusting Load
Edit the `stages` array in each test:
```javascript
stages: [
  { duration: '1m', target: 10 },   // Ramp to 10 users over 1 min
  { duration: '5m', target: 50 },   // Ramp to 50 users over 5 min
  { duration: '1m', target: 0 },    // Ramp down to 0
]
```

### Adjusting Thresholds
Edit the `thresholds` object:
```javascript
thresholds: {
  http_req_duration: ['p(95)<200'],  // Stricter: 95% < 200ms
  http_req_failed: ['rate<0.01'],     // Stricter: < 1% errors
}
```

## Monitoring During Tests

1. Watch Grafana dashboards: http://localhost:8443
2. Monitor Pyroscope: http://localhost:4040
3. Check Prometheus metrics: http://localhost:9090
4. View correlation engine logs: `docker logs -f correlation-engine`

## Best Practices

1. **Start small**: Begin with low VU counts and gradually increase
2. **Monitor resources**: Watch CPU, memory, and network during tests
3. **Analyze results**: Look for bottlenecks in the p95 and p99 percentiles
4. **Test realistic scenarios**: Use payloads that match production data
5. **Run tests regularly**: Catch performance regressions early
