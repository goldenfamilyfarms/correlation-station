# Observability End-to-End Correlation System

> **Real-time log and trace correlation using OpenTelemetry, Grafana Stack, and a custom FastAPI correlation engine**

[![CI/CD](https://github.com/your-org/observability-poc/workflows/CI%2FCD/badge.svg)](https://github.com/your-org/observability-poc/actions)

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [Components](#components)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

This observability platform provides:

- **Real-time log streaming** from MDSO Dev via Grafana Alloy
- **Distributed tracing** for Sense applications (Beorn, Palantir, Arda)
- **Windowed correlation** of logs and traces by `trace_id`
- **Multi-backend export** to Loki, Tempo, Prometheus, and optional Datadog
- **Low-cardinality labels** to prevent metric/log explosion
- **Production-ready** architecture with health checks, retries, and monitoring

### Why This Solution?

**Problem:** Debugging distributed systems requires correlating logs, traces, and metrics across multiple services. Traditional approaches either:
- Lack correlation capabilities
- Require expensive proprietary solutions
- Don't handle high cardinality well

**Solution:** Our correlation engine:
- Uses OpenTelemetry standard for vendor-neutral telemetry
- Implements windowed correlation (60s default) to link related events
- Maintains low cardinality with only 3 Loki labels: `service`, `env`, `trace_id`
- Scales efficiently with batch processing and async pipelines
- Provides both internal correlation and optional Datadog dual-write

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MDSO Dev (159.56.4.37)                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Grafana Alloy                                                    │  │
│  │  • Tails: /var/log/ciena/blueplanet.log, /bp2/log/*.log           │  │
│  │  • Normalizes syslog → structured logs                            │  │
│  │  • Exports: OTLP/HTTP → META:4318                                 │  │
│  └─────────────────────────────┬─────────────────────────────────────┘  │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │ TLS/BasicAuth (optional)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      META (159.56.4.94)                                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  OTel Collector Gateway (:4317, :4318, :55680, :55681)            │  │
│  │  • Receives: OTLP logs/traces/metrics from Alloy & Sense apps     │  │
│  │  • Adds: Resource attributes (env, service, trace context)        │  │
│  │  • Routes to: Correlation Engine, Loki, Tempo                     │  │
│  └────────────┬──────────────────────────────────────────────────────┘  │
│               │                                                         │
│               ├─────────────────┬──────────────────┬──────────────┐     │
│               ▼                 ▼                  ▼              ▼     │
│  ┌─────────────────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Correlation Engine  │  │  Loki   │  │  Tempo   │  │Prometheus│       │
│  │ • Normalize logs    │  │  :3100  │  │  :3200   │  │  :9090   │       │
│  │ • 60s windows       │  └─────────┘  └──────────┘  └──────────┘       │
│  │ • Match by trace_id │       ▲            ▲              ▲            │
│  │ • Export: Loki,     │       │            │              │            │
│  │   Tempo, Prom, DD   │       │            │              │            │
│  └──────────┬──────────┘       │            │              │            │
│             └──────────────────┴────────────┴──────────────┘            │
│                                      │                                  │
│                            ┌─────────▼─────────┐                        │
│                            │  Grafana :3000    │                        │
│                            │  • Dashboards     │                        │
│                            │  • Trace → Logs   │                        │
│                            │  • Correlation UI │                        │
│                            └───────────────────┘                        │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Sense Apps (OTel Instrumented)                                   │  │
│  │  • beorn:5001 (Flask)  • palantir:5002 (Flask)  • arda:5003       │  │
│  │  • Custom attributes: circuit_id, product_id, resource_id, etc.   │  │
│  │  • Export traces/logs → Gateway:4318                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## ✨ Features

### Core Capabilities

- ✅ **Real-time Log Streaming**: Grafana Alloy tails syslog files and ships via OTLP
- ✅ **Distributed Tracing**: Full OpenTelemetry instrumentation for Sense apps
- ✅ **Windowed Correlation**: Links logs and traces within configurable time windows
- ✅ **Low-Cardinality Labels**: Only 3 Loki labels prevent metric explosion
- ✅ **Multi-Backend Export**: Loki, Tempo, Prometheus, optional Datadog
- ✅ **Custom Attributes**: circuit_id, product_id, resource_id, resource_type_id, request_id
- ✅ **Health Checks**: All services expose health and metrics endpoints
- ✅ **Retry Logic**: Automatic retries for transient failures
- ✅ **Batch Processing**: Efficient batch ingestion and export

### Observability Features

- 📊 **Grafana Dashboards**: Pre-configured correlation overview dashboard
- 🔍 **Trace → Logs Navigation**: Click trace ID to see related logs
- 📈 **Prometheus Metrics**: Pipeline health, export counts, latencies
- 🚨 **Alerting Ready**: Metrics exposed for Prometheus alerting
- 📝 **Structured Logging**: JSON logs with trace context injection
- 🔄 **Zero-Downtime Restarts**: Health checks enable rolling updates

### Security Features

- 🔐 **Optional BasicAuth**: Configurable authentication for correlation engine
- 🔒 **TLS Support**: Documented mTLS setup for Alloy → Gateway
- 🛡️ **Non-Root Containers**: All containers run as non-root users
- 🔑 **Secret Management**: Environment-based configuration

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose
- Python 3.11+ (for local development)
- 100GB+ disk space
- Network access between MDSO Dev and META

### 1. Clone and Configure

```bash
# Clone repository
git clone <repo-url>
cd observability-poc

# Copy environment template
cp .env.example .env

# Edit configuration (optional)
vim .env
```

### 2. Deploy on META

```bash
# Build all images
make build

# Start all services
make up

# Wait 30 seconds for services to initialize
sleep 30

# Verify health
make health
```

Expected output:
```
✓ Grafana: Healthy
✓ Loki: Ready
✓ Tempo: Ready
✓ Prometheus: Healthy
✓ OTel Gateway: Healthy
✓ Correlation Engine: Healthy
✓ Beorn: Healthy
✓ Palantir: Healthy
✓ Arda: Healthy
```

### 3. Configure Alloy on MDSO Dev

```bash
# SSH to MDSO Dev
ssh user@159.56.4.37

# Install Alloy
cd /path/to/observability-poc/mdso-alloy
sudo ./install.sh

# Verify Alloy is running
sudo systemctl status alloy
sudo journalctl -u alloy -f
```

### 4. Access Grafana

```bash
# Open browser
open http://austx-mdso-logs-02.chtrse.com/grafana


# Login credentials
Username: admin
Password: admin

# Navigate to: Dashboards → Correlation Overview (DEV)
```

### 5. Generate Test Traffic

```bash
# Generate test traces and logs
make test-traffic

# View correlations
make correlations

# Check metrics
make metrics
```

## 📦 Components

### Correlation Engine (FastAPI)

**Purpose:** Normalizes, correlates, and exports telemetry

**Endpoints:**
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /api/logs` - Ingest log batch from Gateway
- `POST /api/otlp/v1/logs` - OTLP logs ingestion
- `POST /api/otlp/v1/traces` - OTLP traces ingestion
- `GET /api/correlations` - Query correlation events
- `POST /api/events` - Inject synthetic correlation event

**Configuration:** See `correlation-engine/.env.example`

### OTel Collector Gateway

**Purpose:** Routes telemetry between sources and backends

**Receivers:**
- OTLP gRPC: `:4317`
- OTLP HTTP: `:4318`
- Legacy OTLP gRPC: `:55680`
- Legacy OTLP HTTP: `:55681`

**Exporters:**
- Correlation Engine (HTTP)
- Loki (Loki push API)
- Tempo (OTLP)
- Prometheus (scrape endpoint)

**Configuration:** `gateway/otel-config.yaml`

### Observability Stack

| Service | Purpose | Port | Retention |
|---------|---------|------|-----------|
| Grafana | Visualization | 3000 | N/A |
| Loki | Log aggregation | 3100 | 7 days |
| Tempo | Distributed tracing | 3200 | 7 days |
| Prometheus | Metrics storage | 9090 | 15 days |

### Sense Apps

**Beorn** (Flask, Port 5001)
- Authentication & identity service
- OTel instrumented with custom attributes

**Palantir** (Flask, Port 5002)
- Data aggregation service
- OTel instrumented with request tracing

**Arda** (FastAPI, Port 5003)
- Inventory SEEFA design service
- OTel instrumented with async tracing

All apps include: `circuit_id`, `product_id`, `resource_id`, `resource_type_id`, `request_id`

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Correlation window (seconds)
CORR_WINDOW_SECONDS=60

# Max batch size
MAX_BATCH_SIZE=5000

# Log level
LOG_LEVEL=info

# Enable BasicAuth (optional)
ENABLE_BASIC_AUTH=false

# Datadog dual-write (optional)
DATADOG_API_KEY=your_key_here
```

### Low-Cardinality Labels

**CRITICAL:** Loki labels determine cardinality. We use only 3:

```yaml
labels:
  service: "beorn"        # Service name
  env: "dev"              # Environment
  trace_id: "abc123..."   # For correlation queries
```

All other fields (severity, host, message, custom attributes) are stored as JSON in the log line.

### Retention Policies

Adjust retention in respective configs:

- **Loki**: `observability-stack/loki/loki-config.yaml` → `retention_period: 168h`
- **Tempo**: `observability-stack/tempo/tempo-config.yaml` → `block_retention: 168h`
- **Prometheus**: `docker-compose.yml` → `--storage.tsdb.retention.time=15d`

## 📖 Usage

### Query Logs in Loki

```bash
# All logs for a service
{service="beorn"}

# Logs with specific trace_id
{trace_id="abc123def456..."}

# Logs with severity ERROR
{service="beorn"} |= "ERROR"

# JSON field filter
{service="beorn"} | json | circuit_id="CIRCUIT-123"
```

### Query Traces in Tempo

Via Grafana Explore → Tempo:
- Search by service name
- Search by trace ID
- Search by duration
- Search by custom attributes: `circuit_id`, `product_id`

### Query Correlations

```bash
# Get recent correlations
curl http://localhost:8080/api/correlations?limit=10

# Filter by trace_id
curl http://localhost:8080/api/correlations?trace_id=abc123...

# Filter by service
curl http://localhost:8080/api/correlations?service=beorn

# Filter by time range
curl http://localhost:8080/api/correlations?start_time=2025-10-15T00:00:00Z&end_time=2025-10-15T23:59:59Z
```

### Send Custom Logs

```bash
curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "service": "my-service",
      "host": "my-host",
      "env": "dev"
    },
    "records": [
      {
        "timestamp": "2025-10-15T10:30:00.000Z",
        "severity": "INFO",
        "message": "Operation started",
        "trace_id": "abc123def456...",
        "circuit_id": "CIRCUIT-123",
        "product_id": "PROD-456",
        "labels": {"operation": "start"}
      }
    ]
  }'
```

## 🔧 Troubleshooting

### Services Won't Start

```bash
# Check logs
make logs

# Check specific service
docker-compose logs correlation-engine

# Verify ports are available
sudo ss -tulpn | grep -E ':(3000|3100|4317|4318|8080)'

# Check disk space
df -h

# Restart everything
make restart
```

### No Logs in Loki

```bash
# Test log ingestion
make test-logs

# Query Loki directly
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="test"}' \
  --data-urlencode 'limit=10'

# Check Gateway → Loki connectivity
docker-compose exec otel-gateway wget -qO- http://loki:3100/ready

# Check Loki logs for errors
docker-compose logs loki | grep -i error
```

### No Traces in Tempo

```bash
# Generate test traces
make test-trace

# Search Tempo
curl 'http://localhost:3200/api/search?tags=service.name=beorn&limit=10'

# Check Gateway → Tempo connectivity
docker-compose exec otel-gateway wget -qO- http://tempo:3200/ready

# Verify sense apps are exporting
docker-compose logs beorn | grep -i otlp
```

### Alloy Not Sending from MDSO

```bash
# On MDSO Dev host
sudo systemctl status alloy
sudo journalctl -u alloy -f

# Test connectivity
curl -X POST http://159.56.4.94:4318/v1/logs \
  -H "Content-Type: application/json" \
  -d '{"resourceLogs":[]}'

# Check firewall rules
sudo iptables -L | grep 4318

# Verify log files exist
ls -la /var/log/ciena/blueplanet.log
```

For more troubleshooting, see [ops/runbook.md](ops/runbook.md)

## 🧪 Testing

### Unit Tests

```bash
# Correlation engine tests
cd correlation-engine
pytest tests/ -v --cov=app
```

### Integration Tests

```bash
# Full integration test
make ci-test

# Manual testing
make up
make test-traffic
make health
```

### Load Testing

```bash
# Stress test (generates 1000 logs/sec for 60s)
./ops/stress-test.sh

# Monitor during load
watch -n 1 'make metrics'
```

## 📊 Monitoring

### Key Metrics

**Correlation Engine:**
- `correlation_events_total` - Total correlations created
- `log_records_received_total` - Logs ingested
- `traces_received_total` - Traces ingested
- `export_attempts_total` - Export successes/failures
- `export_duration_seconds` - Export latency

**Query Metrics:**
```bash
# In Prometheus
correlation_events_total
rate(log_records_received_total[5m])
histogram_quantile(0.95, export_duration_seconds_bucket)
```

### Health Checks

All services expose health endpoints:

```bash
make health  # Check all services
```

Or individually:
```bash
curl http://localhost:8080/health  # Correlation Engine
curl http://localhost:3100/ready   # Loki
curl http://localhost:3200/ready   # Tempo
curl http://localhost:9090/-/healthy  # Prometheus
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install pre-commit hooks
pre-commit install

# Run tests
make test

# Lint code
make lint

# Format code
make format
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Documentation**: [ops/runbook.md](ops/runbook.md)
- **API Docs**: http://159.56.4.94:8080/docs
- **Issues**: GitHub Issues
- **Slack**: #observability-support

## 🙏 Acknowledgments

- OpenTelemetry Community
- Grafana Labs
- FastAPI Framework
- The SECA Engineering Team

---

**Built with ❤️ by the Derrick Golden**