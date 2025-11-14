# Deployment Guide: End-to-End Tracing Implementation

## Overview

This implementation adds OpenTelemetry instrumentation to SENSE apps and integrates MDSO log collection into the correlation engine for unified observability.

## Architecture

```
SENSE Apps (arda/beorn/palantir)
    ↓ [OTLP/HTTP traces]
Correlation Engine
    ↓ [Scheduled collection]
MDSO API
    ↓ [Logs + Traces]
Grafana Stack (Loki/Tempo/Prometheus)
```

## Phase 1: Deploy Common Telemetry Module

### 1. Copy telemetry module to common_sense

```bash
cp -r implementation/common_sense_telemetry/* sense-apps/common_sense/telemetry/
```

### 2. Verify structure

```
sense-apps/common_sense/
└── telemetry/
    ├── __init__.py
    └── tracer.py
```

## Phase 2: Instrument SENSE Apps

### For each app (arda, beorn, palantir):

### 1. Update requirements.txt

```bash
cp implementation/sense_apps_instrumented/requirements.txt sense-apps/arda/requirements.txt
pip install -r sense-apps/arda/requirements.txt
```

### 2. Update main.py

```bash
cp implementation/sense_apps_instrumented/arda_main.py sense-apps/arda/arda_app/main.py
```

Repeat for beorn and palantir (change service_name in init_telemetry call).

### 3. Set environment variables

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://correlation-engine:8080/api/otlp/v1/traces"
export DEPLOYMENT_ENV="dev"
```

### 4. Restart services

```bash
cd sense-apps/arda
uvicorn arda_app.main:app --reload
```

## Phase 3: Deploy Enhanced Correlation Engine

### 1. Backup existing correlation engine

```bash
cp -r seefa-om/correlation-engine seefa-om/correlation-engine.backup
```

### 2. Copy enhanced files

```bash
# Copy new modules
cp -r implementation/correlation_engine_enhanced/app/mdso seefa-om/correlation-engine/app/

# Copy updated files
cp implementation/correlation_engine_enhanced/app/config.py seefa-om/correlation-engine/app/
cp implementation/correlation_engine_enhanced/app/main.py seefa-om/correlation-engine/app/

# Copy new routes
cp implementation/correlation_engine_enhanced/app/routes/mdso.py seefa-om/correlation-engine/app/routes/

# Copy new pipeline module
cp implementation/correlation_engine_enhanced/app/pipeline/mdso_correlator.py seefa-om/correlation-engine/app/pipeline/

# Update requirements
cp implementation/correlation_engine_enhanced/requirements.txt seefa-om/correlation-engine/
```

### 3. Install dependencies

```bash
cd seefa-om/correlation-engine
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp implementation/correlation_engine_enhanced/.env.example seefa-om/correlation-engine/.env
```

Edit `.env` with your MDSO credentials:

```bash
MDSO_ENABLED=true
MDSO_URL=https://your-mdso-server.com
MDSO_USER=your_username
MDSO_PASS=your_password
```

### 5. Start correlation engine

```bash
cd seefa-om/correlation-engine
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Phase 4: Verify End-to-End Tracing

### 1. Test SENSE app instrumentation

```bash
# Make a request to ARDA
curl http://localhost:5000/arda/api/v1/cid/some-circuit-id

# Check correlation engine received traces
curl http://localhost:8080/api/correlations
```

### 2. Test MDSO collection

```bash
# Trigger manual collection
curl -X POST http://localhost:8080/api/mdso/collect \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "service_mapper",
    "product_name": "ServiceMapper",
    "time_range_hours": 3
  }'

# Check status
curl http://localhost:8080/api/mdso/status
```

### 3. View traces in Grafana

1. Open Grafana: http://localhost:3000
2. Navigate to Explore → Tempo
3. Search for traces with:
   - Service: `arda` or `correlation-engine`
   - Tags: `mdso.circuit_id`, `mdso.product_type`

### 4. View logs in Loki

1. Grafana → Explore → Loki
2. Query: `{service="correlation-engine"} |= "mdso"`

## Phase 5: Production Deployment

### 1. Docker deployment

```bash
# Build correlation engine
cd seefa-om/correlation-engine
docker build -t correlation-engine:2.0 .

# Build SENSE apps
cd sense-apps/arda
docker build -t arda:2.0 .
```

### 2. Update docker-compose.yml

```yaml
services:
  correlation-engine:
    image: correlation-engine:2.0
    environment:
      - MDSO_ENABLED=true
      - MDSO_URL=${MDSO_URL}
      - MDSO_USER=${MDSO_USER}
      - MDSO_PASS=${MDSO_PASS}
    ports:
      - "8080:8080"
  
  arda:
    image: arda:2.0
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://correlation-engine:8080/api/otlp/v1/traces
      - DEPLOYMENT_ENV=production
    ports:
      - "5000:5000"
```

### 3. Deploy

```bash
docker-compose up -d
```

## Monitoring

### Key Metrics

- `correlation_api_requests_total` - API request count
- `log_records_received_total{source="mdso"}` - MDSO logs ingested
- `traces_received_total{source="sense"}` - SENSE traces received
- `correlation_events_total` - Correlation events created

### Dashboards

Import Grafana dashboards from `seefa-om/observability-stack/grafana/dashboards/`

## Troubleshooting

### SENSE apps not sending traces

1. Check OTLP endpoint: `echo $OTEL_EXPORTER_OTLP_ENDPOINT`
2. Verify correlation engine is reachable
3. Check logs: `docker logs arda`

### MDSO collection failing

1. Verify credentials in `.env`
2. Check MDSO connectivity: `curl -k $MDSO_URL/tron/api/v1/tokens`
3. Check correlation engine logs: `docker logs correlation-engine | grep mdso`

### No correlations appearing

1. Verify trace_id propagation in headers
2. Check correlation window settings (default 60s)
3. Query correlation history: `curl http://localhost:8080/api/correlations?limit=100`

## Rollback

If issues occur:

```bash
# Restore original correlation engine
rm -rf seefa-om/correlation-engine
mv seefa-om/correlation-engine.backup seefa-om/correlation-engine

# Restore original SENSE apps
git checkout sense-apps/arda/arda_app/main.py
git checkout sense-apps/arda/requirements.txt
```

## Next Steps

1. Add custom spans to business logic in SENSE apps
2. Create Grafana dashboards for MDSO error trends
3. Set up alerts for high error rates
4. Implement trace sampling for high-volume services
