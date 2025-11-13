# CLAUDE.md - AI Assistant Guide for Correlation Station

> **Purpose:** This document provides AI assistants with comprehensive context about the correlation-station codebase structure, development workflows, and key conventions.

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Codebase Structure](#codebase-structure)
3. [Technology Stack](#technology-stack)
4. [Development Workflows](#development-workflows)
5. [Key Conventions](#key-conventions)
6. [Common Operations](#common-operations)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Guide](#deployment-guide)
9. [Troubleshooting](#troubleshooting)
10. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## Repository Overview

**Project Name:** Correlation Station
**Purpose:** End-to-end observability platform for distributed systems with real-time log and trace correlation

### What This System Does

This is an **observability platform** that:
- Collects logs and traces from distributed services (MDSO, SENSE apps)
- Correlates telemetry data by `trace_id` and circuit identifiers
- Provides unified visualization through Grafana dashboards
- Enables real-time debugging of network service provisioning workflows

### Key Components

1. **SEEFA Observability Stack** (`seefa-om/`)
   - Grafana, Loki, Tempo, Prometheus
   - Custom correlation engine (FastAPI)
   - OTel Collector Gateway

2. **SENSE Applications** (`sense-apps/`)
   - **Arda**: Inventory SEEFA design service (FastAPI)
   - **Beorn**: Authentication & identity service (Flask)
   - **Palantir**: Data aggregation service (Flask)

3. **MDSO Development Tools** (`mdso-dev/`)
   - Charter sensor templates
   - Network service orchestration scripts
   - CI/CD automation tools

4. **Implementation Guides** (`implementation/`)
   - Enhanced correlation engine with MDSO integration
   - Common telemetry modules
   - Instrumented SENSE app examples

---

## Codebase Structure

```
correlation-station/
├── seefa-om/                          # SEEFA Observability Main
│   ├── correlation-engine/            # FastAPI correlation service
│   │   ├── app/
│   │   │   ├── main.py               # FastAPI application entry
│   │   │   ├── config.py             # Settings & environment config
│   │   │   ├── routes/               # API endpoints
│   │   │   └── pipeline/             # Correlation logic & exporters
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── gateway/                       # OTel Collector configuration
│   │   ├── otel-config.yaml
│   │   └── docker-compose.yml
│   ├── observability-stack/           # Grafana, Loki, Tempo, Prometheus
│   │   ├── grafana/
│   │   │   └── provisioning/         # Dashboards & datasources
│   │   ├── loki/
│   │   │   └── loki-config.yaml
│   │   ├── tempo/
│   │   │   └── tempo-config.yaml
│   │   └── prometheus/
│   │       └── prometheus.yml
│   ├── mdso-alloy/                    # Grafana Alloy log collector
│   ├── docker-compose.yml             # Main orchestration file
│   ├── Makefile                       # Primary build/ops commands
│   └── README.md                      # Comprehensive setup guide
│
├── sense-apps/                        # SENSE microservices
│   ├── arda/                          # Inventory SEEFA design (FastAPI)
│   │   ├── arda_app/
│   │   │   └── main.py
│   │   ├── requirements.txt
│   │   └── docker-compose.yml
│   ├── beorn/                         # Auth & identity (Flask)
│   │   ├── beorn_app/
│   │   └── requirements.txt
│   └── palantir/                      # Data aggregation (Flask)
│       ├── palantir_app/
│       └── requirements.txt
│
├── mdso-dev/                          # MDSO development tools
│   ├── charter_sensor_templates/      # Network service templates
│   │   ├── model-definitions/
│   │   │   └── scripts/              # Python orchestration scripts
│   │   ├── resources/tests/
│   │   └── Makefile
│   ├── common-ci-cd-automations/      # Shared CI/CD scripts
│   ├── figmaker/                      # Figure/diagram generation
│   ├── meta/                          # Metadata management
│   └── all-product-logs-multiprocess/ # Log processing utilities
│
├── implementation/                    # Enhanced implementation examples
│   ├── common_sense_telemetry/        # Shared OTel instrumentation
│   ├── correlation_engine_enhanced/   # Enhanced engine w/ MDSO integration
│   └── sense_apps_instrumented/       # Example instrumented apps
│
├── context/                           # Architecture documentation
│   └── architecture-info/
│
├── .gitignore
├── .gitattributes
└── CLAUDE.md                          # This file
```

### Directory Purposes

| Directory | Purpose | Key Technologies |
|-----------|---------|-----------------|
| `seefa-om/` | Observability stack deployment | Docker, FastAPI, Grafana Stack |
| `sense-apps/` | Business logic microservices | Python, Flask, FastAPI, OTel |
| `mdso-dev/` | Network orchestration tools | Python, Jinja2, YAML |
| `implementation/` | Reference implementations | Python, OpenTelemetry |
| `context/` | Documentation & architecture | Markdown, diagrams |

---

## Technology Stack

### Core Technologies

- **Languages:** Python 3.11+
- **Web Frameworks:** FastAPI 0.104+, Flask
- **Observability:** OpenTelemetry, Grafana Stack (Loki, Tempo, Prometheus)
- **Containerization:** Docker, Docker Compose
- **Build Tools:** Make, Bash scripts
- **Data Validation:** Pydantic 2.10+

### Python Dependencies (Correlation Engine)

```python
# Web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Data validation
pydantic>=2.10.0
pydantic-settings>=2.7.0

# HTTP clients
httpx==0.25.2

# Observability
opentelemetry-proto>=1.20.0
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
```

### Infrastructure Components

- **Grafana:** Visualization (port 8443)
- **Loki:** Log aggregation (port 3100)
- **Tempo:** Distributed tracing (port 3200/9000)
- **Prometheus:** Metrics storage (port 9090)
- **OTel Gateway:** Telemetry routing (ports 4317, 4318, 55680, 55681)
- **Correlation Engine:** Custom FastAPI service (port 8080)

---

## Development Workflows

### Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd correlation-station

# 2. Navigate to observability stack
cd seefa-om

# 3. Run pre-setup checks (first time only)
make pre-setup

# 4. Start all services
make start-all

# 5. Verify health
make health

# 6. View logs
make logs
```

### Working with Correlation Engine

```bash
# Navigate to correlation engine
cd seefa-om/correlation-engine

# Install dependencies locally (for development)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=app

# Start in development mode
uvicorn app.main:app --reload --port 8080

# Build Docker image
docker build -t correlation-engine:latest .

# Run via Docker Compose
docker-compose up -d
```

### Working with SENSE Apps

```bash
# Navigate to specific app
cd sense-apps/arda  # or beorn, palantir

# Install dependencies
pip install -r requirements.txt

# Run locally
python -m arda_app.main  # or beorn_app.main, palantir_app.main

# Run via Docker
docker-compose up -d
```

### Working with MDSO Tools

```bash
# Navigate to charter sensor templates
cd mdso-dev/charter_sensor_templates

# View available make targets
make help

# Run tests
make test

# Build solution package
make build
```

---

## Key Conventions

### Code Style

1. **Python Code Style**
   - Follow PEP 8
   - Use type hints (Python 3.11+ syntax)
   - Docstrings for all public functions/classes
   - Max line length: 100 characters

2. **Naming Conventions**
   - Files: `snake_case.py`
   - Classes: `PascalCase`
   - Functions/variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private methods: `_leading_underscore`

3. **Import Order**
   ```python
   # Standard library
   import asyncio
   import logging

   # Third-party
   from fastapi import FastAPI
   import structlog

   # Local imports
   from app.config import settings
   from app.routes import health
   ```

### Configuration Management

1. **Environment Variables**
   - Defined in `.env` files (gitignored)
   - Loaded via `pydantic-settings`
   - Example: `seefa-om/.env`

2. **Configuration Files**
   - YAML for infrastructure (OTel, Loki, Tempo, Prometheus)
   - Python modules for application config (`config.py`)
   - Docker Compose for service orchestration

### Logging Standards

1. **Structured Logging**
   ```python
   import structlog

   logger = structlog.get_logger()
   logger.info("event_description",
               trace_id="abc123",
               circuit_id="CIRCUIT-456",
               key="value")
   ```

2. **Log Levels**
   - `DEBUG`: Detailed diagnostic info
   - `INFO`: General informational messages
   - `WARNING`: Warning messages
   - `ERROR`: Error events
   - `CRITICAL`: Critical failures

3. **Required Context**
   - Always include `trace_id` when available
   - Include business identifiers: `circuit_id`, `product_id`, `resource_id`
   - Use structured fields, not string interpolation

### OpenTelemetry Conventions

1. **Trace Context Propagation**
   - Use W3C Trace Context headers
   - Propagate via `traceparent` and `tracestate`
   - Inject/extract in all HTTP calls

2. **Custom Attributes**
   ```python
   span.set_attribute("circuit_id", "CIRCUIT-123")
   span.set_attribute("product_id", "PROD-456")
   span.set_attribute("resource_id", "RES-789")
   span.set_attribute("resource_type_id", "NetworkService")
   span.set_attribute("request_id", "REQ-111")
   ```

3. **Span Naming**
   - Format: `service.operation`
   - Examples: `beorn.authenticate`, `arda.create_topology`

### Docker Conventions

1. **Image Naming**
   - Format: `service-name:version`
   - Example: `correlation-engine:latest`

2. **Container Naming**
   - Use `container_name` in docker-compose
   - Format: lowercase, hyphenated
   - Example: `correlation-engine`, `otel-gateway`

3. **Network Configuration**
   - Single network: `observability` (bridge driver)
   - Subnet: `172.20.0.0/23`
   - Internal DNS resolution via service names

4. **Volume Management**
   - Named volumes for persistence: `grafana-data`, `loki-data`, `tempo-data`, `prometheus-data`
   - Bind mounts for configs: `./config:/etc/config`

---

## Common Operations

### Make Commands (seefa-om/)

```bash
# System Control
make start-all       # Start all core services
make stop-all        # Stop all services
make restart         # Restart all services
make status          # Show service status

# Health & Monitoring
make health          # Check health of all services
make metrics         # Show correlation engine metrics
make correlations    # Query recent correlation events

# Logging
make logs            # Tail all service logs
make logs-grafana    # Tail Grafana logs
make logs-loki       # Tail Loki logs
make logs-tempo      # Tail Tempo logs
make logs-engine     # Tail correlation engine logs
make logs-gateway    # Tail OTel gateway logs

# Testing
make test-logs       # Send test logs
make test-trace      # Generate test traces
make test-traffic    # Generate comprehensive test traffic
make stress-test     # Run stress test

# Cleanup
make clean           # Stop services and remove volumes
make purge           # Remove everything including images
make prune           # Remove unused Docker resources

# Development
make shell-engine    # Open shell in correlation engine container
make shell-gateway   # Open shell in OTel gateway container
make shell-grafana   # Open shell in Grafana container

# Validation
make validate        # Run all validations
make validate-compose # Validate Docker Compose files
make validate-env    # Validate environment variables
```

### Service URLs

```
Grafana:         http://159.56.4.94:8443
Prometheus:      http://159.56.4.94:9090
Loki:            http://159.56.4.94:3100
Tempo:           http://159.56.4.94:9000
Correlation API: http://159.56.4.94:8080
OTel Gateway:    http://159.56.4.94:55681 (HTTP)
```

### API Endpoints (Correlation Engine)

```bash
# Health check
GET http://localhost:8080/health

# Prometheus metrics
GET http://localhost:8080/metrics

# Ingest logs (custom format)
POST http://localhost:8080/api/logs

# Ingest OTLP logs
POST http://localhost:8080/api/otlp/v1/logs

# Ingest OTLP traces
POST http://localhost:8080/api/otlp/v1/traces

# Query correlations
GET http://localhost:8080/api/correlations?limit=10
GET http://localhost:8080/api/correlations?trace_id=abc123...
GET http://localhost:8080/api/correlations?service=beorn

# Inject synthetic event
POST http://localhost:8080/api/events
```

### Querying Loki

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

### Querying Tempo

Via Grafana Explore → Tempo:
- Search by service name
- Search by trace ID
- Search by duration
- Search by custom attributes: `circuit_id`, `product_id`

---

## Testing Strategy

### Unit Tests

```bash
# Correlation engine
cd seefa-om/correlation-engine
pytest tests/ -v --cov=app

# SENSE apps (example: Arda)
cd sense-apps/arda
pytest tests/ -v
```

### Integration Tests

```bash
# Full stack integration
cd seefa-om
make up
make test-traffic
make health
```

### Load Testing

```bash
# Stress test (1000 logs/sec for 60s)
cd seefa-om
./ops/stress-test.sh

# Monitor during load
watch -n 1 'make metrics'
```

### Test Data Locations

- `mdso-dev/charter_sensor_templates/resources/tests/jsons/` - MDSO test data
- `sense-apps/*/mock_data/` - Mock data for SENSE apps
- `sense-apps/*/tests/` - Unit test files

---

## Deployment Guide

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- 100GB+ disk space
- Network access between MDSO Dev (159.56.4.37) and Server-124 (159.56.4.94)

### Deployment Steps

1. **Server-124 Setup (Observability Stack)**
   ```bash
   cd seefa-om
   make pre-setup      # First time only
   make start-all
   make health
   ```

2. **MDSO Dev Setup (Grafana Alloy)**
   ```bash
   # SSH to MDSO Dev
   ssh user@159.56.4.37

   cd /path/to/correlation-station/seefa-om/mdso-alloy
   sudo ./install.sh
   sudo systemctl status alloy
   ```

3. **SENSE Apps Deployment**
   ```bash
   cd sense-apps
   # Deploy each app individually or via docker-compose
   ```

### Environment Configuration

Create `.env` in `seefa-om/`:

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
DATADOG_SITE=datadoghq.com

# Deployment environment
DEPLOYMENT_ENV=dev
```

### Health Checks

All services expose health endpoints:

```bash
# Automated health check
make health

# Manual checks
curl http://localhost:8080/health      # Correlation Engine
curl http://localhost:3100/ready       # Loki
curl http://localhost:3200/ready       # Tempo
curl http://localhost:9090/-/healthy   # Prometheus
curl http://localhost:8443/api/health  # Grafana
```

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

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

#### 2. No Logs in Loki

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

#### 3. No Traces in Tempo

```bash
# Generate test traces
make test-trace

# Search Tempo
curl 'http://localhost:3200/api/search?tags=service.name=beorn&limit=10'

# Check Gateway → Tempo connectivity
docker-compose exec otel-gateway wget -qO- http://tempo:3200/ready

# Verify SENSE apps are exporting
docker-compose logs beorn | grep -i otlp
```

#### 4. Docker Network Conflicts

```bash
# Fix network conflicts
make network-cleanup
make start-all
```

#### 5. High Cardinality Issues

```bash
# Check Loki label cardinality
make check-cardinality

# Review label usage
curl http://localhost:3100/loki/api/v1/labels
```

### Debugging Commands

```bash
# View correlation engine logs
make logs-engine

# View OTel gateway logs
make logs-gateway

# Check Prometheus metrics
make metrics

# Query recent correlations
make correlations

# Open shell in container
make shell-engine
make shell-gateway

# Check disk usage
make check-disk
```

---

## AI Assistant Guidelines

### When Working on This Codebase

1. **Always Check Context First**
   - Read relevant README files
   - Review existing code patterns
   - Check configuration files before making changes

2. **Prefer Existing Patterns**
   - Use structured logging (structlog)
   - Follow OpenTelemetry conventions
   - Maintain low-cardinality labels in Loki

3. **Testing is Required**
   - Write unit tests for new features
   - Update integration tests
   - Run `make test-traffic` before committing

4. **Documentation Updates**
   - Update README if workflows change
   - Update this CLAUDE.md if structure changes
   - Add inline comments for complex logic

5. **Don't Break Observability**
   - Always propagate trace context
   - Include business identifiers in logs/spans
   - Don't add high-cardinality labels

### File Modification Guidelines

#### NEVER Modify Directly
- Generated files (e.g., `*.pyc`, `__pycache__/`)
- Docker volumes data
- `.git/` directory

#### Modify with Caution
- `docker-compose.yml` - Check for dependent services
- `otel-config.yaml` - Verify exporter compatibility
- `prometheus.yml` - Validate scrape configs
- `loki-config.yaml` - Check retention policies
- `tempo-config.yaml` - Verify storage settings

#### Safe to Modify
- Application code (`*.py` in `app/` directories)
- Tests (`tests/` directories)
- Documentation (`*.md` files)
- Environment configs (`.env.example`, not `.env`)
- Makefile targets (add new, don't break existing)

### Making Changes

#### Adding New Features

1. **Understand the requirement**
   ```bash
   # Read relevant docs
   cat seefa-om/README.md
   cat implementation/README.md
   ```

2. **Check existing patterns**
   ```bash
   # Find similar implementations
   grep -r "similar_pattern" seefa-om/correlation-engine/
   ```

3. **Implement with tests**
   ```python
   # Add feature code
   # Add unit tests
   # Update integration tests
   ```

4. **Validate**
   ```bash
   make start-all
   make health
   make test-traffic
   ```

#### Debugging Issues

1. **Gather context**
   ```bash
   make status
   make health
   make logs
   ```

2. **Isolate the problem**
   ```bash
   # Check specific service
   make logs-engine
   docker-compose logs correlation-engine
   ```

3. **Check metrics**
   ```bash
   make metrics
   curl http://localhost:8080/metrics
   ```

4. **Verify configuration**
   ```bash
   # Validate Docker Compose
   make validate-compose

   # Check environment
   make validate-env
   ```

#### Refactoring Code

1. **Run tests before changes**
   ```bash
   pytest tests/ -v
   ```

2. **Make incremental changes**
   - One logical change per commit
   - Keep tests passing

3. **Update documentation**
   - Inline comments
   - README updates
   - CLAUDE.md updates

4. **Verify no regression**
   ```bash
   make ci-test
   ```

### Code Review Checklist

Before proposing changes, verify:

- [ ] Code follows existing patterns
- [ ] Type hints added for Python code
- [ ] Structured logging used (not print statements)
- [ ] OpenTelemetry context propagated
- [ ] Low-cardinality labels maintained
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No secrets committed
- [ ] Docker builds succeed
- [ ] `make health` passes
- [ ] `make test-traffic` works

### Useful Search Patterns

```bash
# Find all API endpoints
grep -r "@app\\.get\\|@app\\.post" seefa-om/correlation-engine/

# Find all OTel instrumentation
grep -r "set_attribute\\|tracer\\.start" sense-apps/

# Find all Loki queries
grep -r "{service=" seefa-om/

# Find all environment variables
grep -r "settings\\." seefa-om/correlation-engine/

# Find all Docker Compose services
grep "^  [a-z]" seefa-om/docker-compose.yml

# Find all Make targets
grep "^[a-z].*:.*##" seefa-om/Makefile
```

### Quick Reference Commands

```bash
# Start working
cd correlation-station/seefa-om
make start-all
make health

# Check status
make status
make logs

# Test changes
make test-logs
make test-trace
make correlations

# Debug
make logs-engine
make shell-engine
make metrics

# Stop working
make stop-all
```

---

## Additional Resources

### Documentation Files

- `seefa-om/README.md` - Comprehensive observability stack guide
- `implementation/README.md` - Enhanced implementation guide
- `implementation/DEPLOYMENT_GUIDE.md` - Deployment instructions
- `implementation/USAGE_EXAMPLES.md` - Usage examples
- `seefa-om/setupGuide.md` - Setup instructions
- `seefa-om/docs/` - Additional documentation

### API Documentation

- Correlation Engine API: http://159.56.4.94:8080/docs (FastAPI auto-generated)
- Prometheus Metrics: http://159.56.4.94:8080/metrics
- Grafana Dashboards: http://159.56.4.94:8443

### External Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Glossary

| Term | Definition |
|------|------------|
| **SEEFA** | SENSE Engineering Fabric Architecture |
| **SENSE** | Network service ecosystem (Arda, Beorn, Palantir) |
| **MDSO** | Multi-Domain Service Orchestrator (Ciena BluePlanet) |
| **OTel** | OpenTelemetry - observability framework |
| **Correlation** | Linking logs and traces by trace_id or circuit_id |
| **Cardinality** | Number of unique label combinations (keep low!) |
| **Trace Context** | W3C standard for propagating trace_id across services |
| **Baggage** | Key-value pairs propagated with trace context |
| **Span** | Single unit of work in a trace |
| **Exporter** | Component that sends telemetry to backends |
| **Gateway** | OTel Collector that routes telemetry |
| **Circuit ID** | Business identifier for network circuits |
| **Resource ID** | Identifier for MDSO resources |

---

## Contact & Support

- **Author:** Derrick Golden (derrick.golden@charter.com)
- **Documentation:** See `seefa-om/README.md`
- **API Docs:** http://159.56.4.94:8080/docs
- **Runbook:** `seefa-om/ops/runbook.md` (if exists)

---

**Last Updated:** 2025-11-13
**Repository:** correlation-station
**Branch:** develop
