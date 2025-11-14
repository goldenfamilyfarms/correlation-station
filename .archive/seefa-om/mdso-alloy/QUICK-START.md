# Quick Start - Three-Phase Testing

## Test 1: Pure OTel (Simplest)
```bash
cd ~/alloy-agent
./test1-pure-otel.sh
docker logs -f alloy-test1
```

## Test 2: Loki Components
```bash
cd ~/alloy-agent
./test2-loki-components.sh
docker logs -f alloy-test2
```

## Test 3: Full Pipeline (Production)
```bash
cd ~/alloy-agent
./test3-full-pipeline.sh
docker logs -f alloy-test3
```

## Verify on Meta (159.56.4.94)
```bash
# OTel Gateway
docker-compose logs --tail 50 otel-gateway | grep -i mdso

# Correlation Engine
docker-compose logs --tail 50 correlation-engine | grep -i mdso

# Loki
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=10' | jq

# Grafana
http://159.56.4.94:3000
```

## Stop Tests
```bash
docker stop alloy-test1 alloy-test2 alloy-test3
docker rm alloy-test1 alloy-test2 alloy-test3
```

## Files
- `config-test1-pure-otel.alloy` - Pure OTel
- `config-test2-loki-components.alloy` - Loki pipeline
- `config-test3-full-pipeline.alloy` - Full correlation
- `TESTING-GUIDE.md` - Detailed instructions
