# Correlation Engine Enhanced

Enhanced version of the Correlation Engine with MDSO (Multi-Domain Service Orchestrator) integration for automated log collection and error analysis.

## New Features

### MDSO Integration
- **Automated Log Collection**: Scheduled collection of MDSO product logs
- **Error Analysis**: Pattern-based error categorization with defect codes
- **Circuit Correlation**: Links logs and traces by circuit_id when trace_id is unavailable
- **Resource Tracking**: Correlates by MDSO resource_id and product_id

### Enhanced Correlation
- **Multi-Key Correlation**: Supports trace_id, circuit_id, resource_id, product_id
- **MDSO Context Enrichment**: Adds device_tid, orch_state, management_ip to correlations
- **Flexible Querying**: Query by any correlation key

## Quick Start

```bash
# Build and start
make build
make up

# View logs
make logs

# Test endpoints
make test

# Stop
make down
```

## Configuration

### MDSO Settings

Add to `.env`:

```env
# Enable MDSO integration
MDSO_ENABLED=true
MDSO_URL=https://mdso.example.com
MDSO_USER=your_username
MDSO_PASS=your_password

# Collection settings
MDSO_COLLECTION_INTERVAL=3600  # 1 hour
MDSO_TIME_RANGE_HOURS=3        # Look back 3 hours
```

## API Endpoints

### MDSO Endpoints

#### Trigger Manual Collection
```bash
POST /api/mdso/collect
{
  "product_type": "service_mapper",
  "product_name": "ServiceMapper",
  "time_range_hours": 3
}
```

#### List Available Products
```bash
GET /api/mdso/products
```

#### Check MDSO Status
```bash
GET /api/mdso/status
```

### Standard Endpoints

All standard correlation engine endpoints are available:
- `POST /api/logs` - Ingest logs
- `POST /api/otlp/v1/logs` - OTLP logs
- `POST /api/otlp/v1/traces` - OTLP traces
- `GET /api/correlations` - Query correlations
- `POST /api/events` - Inject synthetic events
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Correlation Engine Enhanced                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────────┐            │
│  │ OTLP Ingest  │      │  MDSO Collector  │            │
│  │ (logs/traces)│      │  (scheduled)     │            │
│  └──────┬───────┘      └────────┬─────────┘            │
│         │                       │                        │
│         └───────┬───────────────┘                        │
│                 │                                        │
│         ┌───────▼────────┐                              │
│         │  Correlator    │                              │
│         │  - trace_id    │                              │
│         │  - circuit_id  │                              │
│         │  - resource_id │                              │
│         └───────┬────────┘                              │
│                 │                                        │
│         ┌───────▼────────┐                              │
│         │   Exporters    │                              │
│         │ Loki/Tempo/DD  │                              │
│         └────────────────┘                              │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## MDSO Error Analysis

The engine automatically categorizes MDSO errors:

- **DE-1000**: Device connection failures
- **DE-1001**: Authentication failures
- **DE-1002**: Device timeouts
- **DE-1003**: Configuration commit failures
- **DE-1004**: Invalid configuration
- **DE-1005**: Resource not found
- **DE-1006**: Network unreachable
- **DE-1007**: Permission denied
- **DE-1008**: Syntax errors
- **DE-1009**: Duplicate entries
- **DE-1010**: Constraint violations

## Deployment

### Docker Compose

```yaml
services:
  correlation-engine-enhanced:
    image: correlation-engine-enhanced:latest
    ports:
      - "8080:8080"
    environment:
      - MDSO_ENABLED=true
      - MDSO_URL=https://mdso.example.com
      - MDSO_USER=user
      - MDSO_PASS=pass
    networks:
      - observability
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: correlation-engine-enhanced
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: correlation-engine
        image: correlation-engine-enhanced:latest
        env:
        - name: MDSO_ENABLED
          value: "true"
        - name: MDSO_URL
          valueFrom:
            secretKeyRef:
              name: mdso-credentials
              key: url
        - name: MDSO_USER
          valueFrom:
            secretKeyRef:
              name: mdso-credentials
              key: username
        - name: MDSO_PASS
          valueFrom:
            secretKeyRef:
              name: mdso-credentials
              key: password
```

## Differences from Base Version

| Feature | Base | Enhanced |
|---------|------|----------|
| OTLP Ingestion | ✓ | ✓ |
| Trace Correlation | ✓ | ✓ |
| MDSO Integration | ✗ | ✓ |
| Circuit ID Correlation | ✗ | ✓ |
| Error Categorization | ✗ | ✓ |
| Scheduled Collection | ✗ | ✓ |
| Resource Tracking | ✗ | ✓ |

## Troubleshooting

### MDSO Connection Issues

Check MDSO status:
```bash
curl http://localhost:8080/api/mdso/status
```

Enable debug logging:
```env
LOG_LEVEL=debug
```

### Missing Correlations

1. Verify circuit_id is present in logs/traces
2. Check MDSO collection is running
3. Query by circuit_id: `GET /api/correlations?circuit_id=CIRCUIT-123`

## License

MIT
