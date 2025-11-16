# 🚀 Correlation Station - Makefile Setup Guide

**Quick-start guide for deploying the complete observability solution using Makefile commands**

This guide walks you through setting up:
- ✅ Backend observability stack (Grafana, Loki, Tempo, Prometheus, Pyroscope)
- ✅ OTel Gateway for telemetry ingestion
- ✅ Correlation Engine for log/trace correlation
- ✅ Frontend UI (React-based training portal)
- ✅ Health checks and testing

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Deploy Backend Observability Stack](#deploy-backend-observability-stack)
4. [Deploy Frontend UI](#deploy-frontend-ui)
5. [Verification & Testing](#verification--testing)
6. [Access Points](#access-points)
7. [Common Operations](#common-operations)
8. [Troubleshooting](#troubleshooting)
9. [Clean Up](#clean-up)

---

## Prerequisites

### Required Software

```bash
# Check Docker (required: 20.10+)
docker --version

# Check Docker Compose (required: 1.29+ or 2.0+)
docker-compose --version

# Check Make
make --version

# Check disk space (need ~20GB)
df -h

# Check available memory (need ~8GB)
free -h
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
| 3000 | Frontend UI | React training portal |
| 3100 | Loki | Log aggregation |
| 4040 | Pyroscope | Profiling UI |
| 8080 | Correlation Engine | API |
| 8443 | Grafana | Dashboards |
| 9000 | Tempo | Trace UI/API |
| 9090 | Prometheus | Metrics |
| 55681 | OTel Gateway | OTLP HTTP |

**Check ports are free:**
```bash
# Check if ports are in use
sudo ss -tulpn | grep -E ':(3000|3100|4040|8080|8443|9000|9090|55681)'

# If any ports conflict, either:
# 1. Stop the conflicting service, OR
# 2. Modify port mappings in docker-compose.yml
```

---

## Initial Setup

### Step 1: Navigate to Project Directory

```bash
# Clone repository (if not already done)
git clone https://github.com/goldenfamilyfarms/correlation-station.git

# Navigate to the main directory
cd correlation-station/v2/corr-station-updated/seefa-om

# Verify you're in the correct directory
ls -la Makefile
# You should see the Makefile
```

### Step 2: Explore Available Commands

```bash
# View all available Makefile targets
make help
```

You'll see organized sections:
- **Setup** - Pre-setup checks
- **Observability Stack** - Grafana, Loki, Tempo, Prometheus, Pyroscope
- **OTel Gateway** - Telemetry collection
- **Correlation Engine** - Log/trace correlation
- **System Control** - Start/stop all services
- **Health & Monitoring** - Status checks
- **Testing** - Send test data
- **Cleanup** - Remove services/volumes

### Step 3: Run Pre-Setup Checks (FIRST TIME ONLY)

```bash
# Run pre-setup validation
make pre-setup
```

This script will:
- ✅ Check Docker and Docker Compose installation
- ✅ Verify network connectivity
- ✅ Check disk space
- ✅ Create necessary directories
- ✅ Validate configuration files

**Expected output:**
```
========================================
Running Pre-Setup Checks
========================================
✓ Docker installed
✓ Docker Compose installed
✓ Sufficient disk space
✓ Network configuration valid
✓ Pre-setup complete! Next: make start-all
```

---

## Deploy Backend Observability Stack

### Step 4: Start All Backend Services

This single command starts all backend observability components:

```bash
# Start entire backend stack
make start-all
```

**What happens:**
1. ✅ Cleans up old Docker networks
2. ✅ Starts **Observability Stack** (Grafana, Loki, Tempo, Prometheus, Pyroscope)
3. ✅ Starts **OTel Gateway** (telemetry collector)
4. ✅ Starts **Correlation Engine** (correlation logic)

**Expected output:**
```
→ Cleaning up Docker networks...
✓ Network cleanup complete
→ Starting observability stack...
✓ Stack running. Grafana: http://159.56.4.94:8443
→ Starting OTel Collector Gateway...
✓ Gateway running. OTLP: :55680 (gRPC), :55681 (HTTP)
→ Starting Correlation Engine API...
✓ Correlation API running: http://159.56.4.94:8080

========================================
✓ All core services started
========================================

Service URLs:
  Grafana:         http://159.56.4.94:8443
  Prometheus:      http://159.56.4.94:9090
  Loki:            http://159.56.4.94:3100
  Correlation:     http://159.56.4.94:8080

Next steps:
  make status        - Check service health
  make test-trace    - Send test telemetry
  make health        - Run full health check
```

**Wait 30-60 seconds** for all services to fully initialize.

### Step 5: Verify Backend Services

```bash
# Check all service statuses
make status
```

**Expected output:**
```
========================================
Service Status
========================================

Observability Stack:
NAME              STATUS
grafana           Up (healthy)
loki              Up (healthy)
tempo             Up (healthy)
prometheus        Up (healthy)
pyroscope         Up (healthy)

OTel Gateway:
NAME              STATUS
gateway           Up (healthy)

Correlation API:
NAME                    STATUS
correlation-engine      Up (healthy)

Docker Networks:
observability
```

All services should show `Up (healthy)`.

### Step 6: Run Health Checks

```bash
# Run comprehensive health checks
make health
```

**Expected output:**
```
========================================
Checking Health of All Services
========================================

Grafana:
  ✓ Healthy
Loki:
  ✓ Ready
Tempo:
  ✓ Ready
Prometheus:
  ✓ Healthy
OTel Gateway:
  ✓ Healthy
Correlation Engine:
  ✓ Healthy
```

All checks should show **✓ Healthy** or **✓ Ready**.

---

## Deploy Frontend UI

### Step 7: Start Frontend UI

```bash
# Start the React-based UI
docker-compose up -d correlation-station-ui
```

**Wait 10-15 seconds** for the frontend to build and start.

### Step 8: Verify Frontend

```bash
# Check UI status
docker-compose ps correlation-station-ui

# Check UI logs
docker-compose logs -f correlation-station-ui
```

**Expected status:**
```
NAME                      STATUS
correlation-station-ui    Up (healthy)
```

**Expected in logs:**
```
Server listening on port 80
```

---

## Verification & Testing

### Step 9: Send Test Telemetry

```bash
# Send test logs
make test-logs

# Send test traces
make test-trace

# Or generate combined test traffic
make test-traffic
```

**Expected output:**
```
→ Sending test logs...
✓ Test logs sent

→ Generating test traces...
✓ Test trace generation complete
```

### Step 10: Query Correlations

```bash
# View recent correlations
make correlations
```

**Expected output (JSON):**
```json
[
  {
    "correlation_id": "abc123...",
    "trace_id": "xyz789...",
    "timestamp": "2024-11-16T10:30:00Z",
    "service": "test-app",
    "log_count": 5,
    "span_count": 3
  }
]
```

### Step 11: Check Metrics

```bash
# View correlation engine metrics
make metrics
```

**Expected output:**
```
========================================
Correlation Engine Metrics
========================================
correlation_events_total 15
log_records_received_total 47
traces_received_total 12
export_attempts_total{backend="loki",status="success"} 47
export_attempts_total{backend="tempo",status="success"} 12
```

---

## Access Points

### Web UIs

Open these URLs in your browser:

| Service | URL | Login |
|---------|-----|-------|
| **Frontend UI** | http://localhost:8443 | None |
| **Grafana** | http://159.56.4.94:8443 | admin / admin |
| **Prometheus** | http://159.56.4.94:9090 | None |
| **Pyroscope** | http://localhost:4040 | None |
| **Correlation Engine API** | http://159.56.4.94:8080/docs | None (Swagger UI) |

**Open Grafana from terminal:**
```bash
make open-grafana
```

### Frontend UI Features

The UI at `http://localhost:8443` provides:

1. **Homepage**
   - Quick links to all observability tools
   - DataDog legacy modal (fun easter egg)
   - Grafana-themed color palette

2. **Documentation**
   - TraceQL query examples
   - PromQL query examples
   - OpenTelemetry instrumentation guides
   - SDK setup instructions

3. **Architecture**
   - System architecture diagrams
   - Service details and data flow
   - Network topology

4. **SECA Error Reviews**
   - Bi-weekly error analysis
   - Error cards with severity badges
   - Root cause analysis
   - Action item tracking

### API Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Metrics (Prometheus format)
curl http://localhost:8080/metrics

# List correlations
curl http://localhost:8080/api/correlations?limit=10

# SECA reviews (for frontend)
curl http://localhost:8080/api/seca-reviews

# API documentation (interactive)
open http://localhost:8080/docs
```

---

## Common Operations

### Viewing Logs

```bash
# Tail all service logs
make logs

# Tail specific service logs
make logs-grafana
make logs-loki
make logs-tempo
make logs-prometheus
make logs-engine
make logs-gateway

# Follow correlation engine logs
make corr-logs
```

### Restarting Services

```bash
# Restart all services
make restart

# Restart specific components
make stack-restart        # Restart observability stack
make gateway-restart      # Restart OTel gateway
make corr-restart         # Restart correlation engine
```

### Stopping Services

```bash
# Stop all services (keeps data)
make stop-all

# Stop specific components
make stack-down           # Stop observability stack
make gateway-down         # Stop OTel gateway
make corr-down            # Stop correlation engine

# Stop frontend UI
docker-compose stop correlation-station-ui
```

### Starting After Stop

```bash
# Start all backend services again
make start-all

# Start frontend UI
docker-compose up -d correlation-station-ui
```

### Load Testing

```bash
# Send 100 test requests
make test-load

# Run stress test (if available)
make stress-test
```

### Monitoring

```bash
# Check service status
make status

# Run health checks
make health

# View metrics
make metrics

# Query correlations
make correlations

# Check Prometheus metrics
make prometheus-query
```

---

## Troubleshooting

### Issue: Services Won't Start

**Symptoms:**
- `docker-compose up` fails
- Services show as "unhealthy"

**Solution:**
```bash
# Check logs for errors
make logs

# Check specific service
docker-compose logs correlation-engine

# Verify ports are available
sudo ss -tulpn | grep -E ':(3000|8080|8443)'

# Check disk space
df -h

# Fix Docker issues
make fix-docker

# Restart everything
make restart
```

### Issue: Port Conflicts

**Symptoms:**
```
Error: port is already allocated
```

**Solution:**
```bash
# Kill processes on conflicting ports
make fix-ports

# Or manually check and kill
sudo lsof -ti:8080
sudo kill -9 <PID>
```

### Issue: Network Errors

**Symptoms:**
```
Error: network observability not found
```

**Solution:**
```bash
# Clean up networks
make network-cleanup

# Recreate network
make network-create

# Restart services
make start-all
```

### Issue: Frontend UI Not Loading

**Symptoms:**
- http://localhost:8443 shows error
- 404 or connection refused

**Solution:**
```bash
# Check UI status
docker-compose ps correlation-station-ui

# Check UI logs
docker-compose logs correlation-station-ui

# Rebuild UI
docker-compose build correlation-station-ui

# Restart UI
docker-compose up -d correlation-station-ui
```

### Issue: API Requests Failing (404)

**Symptoms:**
- Frontend shows "Failed to fetch"
- API calls return 404

**Solution:**
```bash
# Verify correlation engine is running
docker ps | grep correlation-engine

# Check correlation engine health
curl http://localhost:8080/health

# Check nginx proxy config
docker exec correlation-station-ui cat /etc/nginx/nginx.conf

# Restart UI
docker-compose restart correlation-station-ui
```

### Issue: No Data in Grafana

**Symptoms:**
- Grafana shows no logs/traces
- Empty dashboards

**Solution:**
```bash
# Send test data
make test-logs
make test-trace

# Verify Loki has data
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="test"}' \
  --data-urlencode 'limit=10'

# Verify Tempo has data
curl 'http://localhost:9000/api/search?tags=service.name=beorn&limit=10'

# Check gateway connectivity
docker-compose logs gateway | grep -i error
```

### Issue: High Memory Usage

**Solution:**
```bash
# Check Docker stats
docker stats

# Check disk usage
make check-disk

# Prune unused resources
make prune

# If needed, reduce retention periods in configs
# Edit: observability-stack/loki/loki-config.yaml
# Edit: observability-stack/tempo/tempo-config.yaml
```

### Get Detailed Debug Info

```bash
# Show container details
make debug-inspect

# Show environment variables
make debug-env

# Show network connectivity
make debug-network

# Show exposed ports
make debug-ports

# Detailed health check
make debug-health
```

---

## Clean Up

### Partial Cleanup (Keep Data)

```bash
# Stop all services but keep volumes
make stop-all

# Later, restart with data intact
make start-all
docker-compose up -d correlation-station-ui
```

### Full Cleanup (Remove Everything)

```bash
# Stop and remove all services + volumes
make clean

# Remove Docker images too
make purge

# Clean up unused Docker resources
make prune
```

### Nuclear Option (Dev Only)

```bash
# WARNING: This deletes ALL data (logs, traces, metrics)
make cleanup-all
```

You'll be prompted to confirm:
```
⚠️  WARNING: This will DELETE all data (logs, traces, metrics)
Continue? [y/N]
```

Type `y` to proceed with full cleanup.

---

## Quick Reference

### Essential Commands

```bash
# First time setup
make pre-setup              # Run checks (first time only)
make start-all              # Start all backend services
docker-compose up -d correlation-station-ui  # Start frontend UI

# Daily operations
make status                 # Check service health
make health                 # Run health checks
make logs                   # View logs
make restart                # Restart all services

# Testing
make test-logs              # Send test logs
make test-trace             # Send test traces
make test-traffic           # Generate test traffic
make correlations           # Query correlations
make metrics                # View metrics

# Troubleshooting
make fix-docker             # Fix Docker issues
make fix-ports              # Clear port conflicts
make debug-health           # Detailed health check
make logs-engine            # View correlation engine logs

# Cleanup
make stop-all               # Stop services (keep data)
make clean                  # Stop + remove volumes
make purge                  # Remove everything including images
```

### Service URLs Quick Access

```bash
# Open in browser
open http://localhost:8443              # Frontend UI
open http://159.56.4.94:8443            # Grafana
open http://localhost:4040              # Pyroscope
open http://159.56.4.94:9090            # Prometheus
open http://159.56.4.94:8080/docs       # API docs

# Or use make commands
make open-grafana                       # Open Grafana
make open-dashboard                     # Open correlation dashboard
```

### Typical Workflow

```bash
# 1. Start everything
make start-all
docker-compose up -d correlation-station-ui

# 2. Wait for services to be ready
sleep 30

# 3. Verify health
make health

# 4. Send test data
make test-traffic

# 5. View in browser
open http://localhost:8443
open http://159.56.4.94:8443

# 6. Check correlations
make correlations

# 7. When done, stop services
make stop-all
docker-compose stop correlation-station-ui
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  FRONTEND TIER                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Correlation Station UI (React + Nginx)             │    │
│  │ Port 3000 → 80                                     │    │
│  │ • Training portal                                   │    │
│  │ • Documentation (TraceQL, PromQL, OTel)            │    │
│  │ • SECA error reviews                               │    │
│  │ • Quick links to all tools                         │    │
│  └──────────────────┬──────────────────────────────────┘    │
└────────────────────┼─────────────────────────────────────────┘
                     │ Proxy /api/* to :8080
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  CORRELATION TIER                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Correlation Engine (FastAPI)                       │    │
│  │ Port 8080                                          │    │
│  │ • OTLP ingestion                                   │    │
│  │ • Windowed correlation (60s)                       │    │
│  │ • Export to Loki, Tempo, Prometheus               │    │
│  │ • REST API for queries                             │    │
│  └──────────────────┬──────────────────────────────────┘    │
└────────────────────┼─────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  GATEWAY TIER                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ OTel Collector Gateway                             │    │
│  │ Ports: 55681 (HTTP), 4317 (gRPC internal)         │    │
│  │ • Receives OTLP logs/traces/metrics               │    │
│  │ • Routes to correlation engine & backends          │    │
│  └──────────────────┬──────────────────────────────────┘    │
└────────────────────┼─────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              OBSERVABILITY BACKENDS                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Grafana     │  │  Loki        │  │  Tempo       │      │
│  │  :8443       │  │  :3100       │  │  :9000       │      │
│  │ Dashboards   │  │ Logs         │  │ Traces       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Prometheus   │  │ Pyroscope    │                        │
│  │  :9090       │  │  :4040       │                        │
│  │ Metrics      │  │ Profiling    │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

After completing this setup:

1. **Explore the Frontend UI** at http://localhost:8443
   - Read documentation on TraceQL and PromQL
   - Review system architecture
   - Check SECA error reviews

2. **Configure Dashboards** in Grafana
   - Create custom dashboards
   - Set up alerts
   - Explore pre-configured datasources

3. **Instrument Your Applications**
   - Add OpenTelemetry to your services
   - Send traces/logs to the gateway
   - View correlations in Grafana

4. **Set Up Production**
   - Review `MASTER_SETUP_GUIDE.md` for advanced setup
   - Enable Pyroscope profiling
   - Configure Redis for horizontal scaling
   - Set up persistence and backups

5. **Load Testing**
   - Use `k6/` directory for load tests
   - Monitor with Pyroscope during load
   - Check scaling capabilities

---

## Support & Resources

**Documentation:**
- Master Setup Guide: `MASTER_SETUP_GUIDE.md`
- Frontend UI Guide: `CORRELATION_STATION_UI.md`
- Horizontal Scaling: `HORIZONTAL_SCALING.md`
- API Documentation: http://localhost:8080/docs

**Monitoring:**
- Frontend UI: http://localhost:8443
- Grafana: http://159.56.4.94:8443 (admin/admin)
- Pyroscope: http://localhost:4040
- Prometheus: http://159.56.4.94:9090

**Logs:**
```bash
# All services
make logs

# Specific service
make logs-engine
make logs-grafana

# Follow logs
docker-compose logs -f --tail=100
```

**Health Checks:**
```bash
# Quick check
make health

# Detailed check
make debug-health

# Service status
make status
```

---

## Troubleshooting Checklist

Before asking for help, try:

- [ ] `make health` - Are all services healthy?
- [ ] `make logs` - Any errors in logs?
- [ ] `docker ps` - Are all containers running?
- [ ] `df -h` - Enough disk space?
- [ ] `free -h` - Enough memory?
- [ ] `make fix-docker` - Try fixing Docker
- [ ] `make restart` - Try restarting services
- [ ] Check this guide's troubleshooting section
- [ ] Check `MASTER_SETUP_GUIDE.md` troubleshooting

---

**Version:** 1.0.0
**Last Updated:** 2024-11-16
**Status:** Production Ready ✅

Built with ❤️ by Derrick Golden
