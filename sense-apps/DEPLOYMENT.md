# SENSE Apps Deployment Guide

This guide covers deploying the SENSE microservices (Arda, Beorn, Palantir) on the Meta server (159.56.4.94).

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Manual Deployment](#manual-deployment)
4. [GitLab CI/CD Deployment](#gitlab-cicd-deployment)
5. [Service Configuration](#service-configuration)
6. [Health Checks](#health-checks)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+ installed on Meta server
- SSH access to Meta server (159.56.4.94)
- Observability stack running on Meta server (seefa-om)
- Network connectivity between services

---

## Quick Start

### Deploy All SENSE Apps Together

```bash
# SSH to Meta server
ssh root@159.56.4.94

# Navigate to sense-apps directory
cd /opt/correlation-station/sense-apps

# Create environment configuration
cp .env.example .env
nano .env  # Edit as needed

# Create individual app .env files
cp .env.example arda/.env
cp .env.example beorn/.env
cp .env.example palantir/.env

# Start all three services
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check logs
docker-compose logs -f

# Test health endpoints
curl http://localhost:5001/health  # Arda
curl http://localhost:5002/health  # Beorn
curl http://localhost:5003/health  # Palantir
```

---

## Manual Deployment

### Option 1: Deploy All Apps (Recommended)

Use the unified `docker-compose.yml` in the `sense-apps/` root directory:

```bash
cd /opt/correlation-station/sense-apps

# Start all services
docker-compose up -d

# View status
docker-compose ps

# View logs for specific service
docker-compose logs -f beorn

# Restart specific service
docker-compose restart arda

# Stop all services
docker-compose down
```

### Option 2: Deploy Individual Apps

Deploy each app separately:

#### Arda (FastAPI - Inventory SEEFA Design)

```bash
cd /opt/correlation-station/sense-apps/arda

# Create environment file
cp dev.env.example dev.env
nano dev.env

# Start service
docker-compose up -d

# Check logs
docker-compose logs -f

# Test endpoint
curl http://localhost:5001/health
```

#### Beorn (Flask - Auth & Identity)

```bash
cd /opt/correlation-station/sense-apps/beorn

# Create environment file
cat > .env << 'EOF'
OTEL_SERVICE_NAME=beorn
OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:4318
DEPLOYMENT_ENV=production
LOG_LEVEL=info
EOF

# Build image
docker build -t beorn:latest .

# Run container
docker run -d \
  --name beorn-flask \
  --restart unless-stopped \
  -p 5002:5002 \
  --env-file .env \
  --network observability \
  beorn:latest

# Check logs
docker logs -f beorn-flask

# Test endpoint
curl http://localhost:5002/health
```

#### Palantir (Flask - Data Aggregation)

```bash
cd /opt/correlation-station/sense-apps/palantir

# Create environment file
cat > .env << 'EOF'
OTEL_SERVICE_NAME=palantir
OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:4318
DEPLOYMENT_ENV=production
LOG_LEVEL=info
EOF

# Build image
docker build -t palantir:latest .

# Run container
docker run -d \
  --name palantir-flask \
  --restart unless-stopped \
  -p 5003:5003 \
  --env-file .env \
  --network observability \
  palantir:latest

# Check logs
docker logs -f palantir-flask

# Test endpoint
curl http://localhost:5003/health
```

---

## GitLab CI/CD Deployment

The GitLab pipeline in `.gitlab-ci.yml` handles automated building and deployment.

### Pipeline Stages

1. **Test**: Run pytest for each app
2. **Build**: Build Docker images with cache
3. **Deploy**: SSH deploy to Meta server (manual trigger)
4. **Validate**: Health checks

### Trigger Deployment

1. Push code to `develop` or `main` branch
2. Go to **GitLab → CI/CD → Pipelines**
3. Find your pipeline
4. Click ▶️ on **deploy:meta-server:staging** or **deploy:meta-server:production**
5. Pipeline will SSH to Meta server and run:
   ```bash
   cd /opt/correlation-station/sense-apps
   docker-compose pull
   docker-compose up -d
   ```

### Required GitLab Variables

Configure in **GitLab → Settings → CI/CD → Variables**:

- `SSH_PRIVATE_KEY`: SSH key for root@159.56.4.94
- `DATADOG_API_KEY` (optional): For dual export

---

## Service Configuration

### Environment Variables

Each service supports these OpenTelemetry variables:

```bash
# OpenTelemetry
OTEL_SERVICE_NAME=<service-name>          # arda, beorn, or palantir
OTEL_SERVICE_VERSION=1.0.0
OTEL_DEPLOYMENT_ENV=production            # production, staging, dev
OTEL_EXPORTER_OTLP_ENDPOINT=http://159.56.4.94:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1               # 10% sampling rate

# DataDog (optional)
DD_AGENT_HOST=<datadog-agent-ip>
DD_ENV=production
DD_SERVICE=<service-name>
DD_VERSION=1.0.0

# Application
LOG_LEVEL=info                            # debug, info, warning, error
```

### Network Configuration

Services connect to two networks:

1. **sense-network** (172.21.0.0/24): Internal communication between SENSE apps
2. **observability** (external): Connection to Correlation Gateway, Loki, Tempo

### Port Mapping

| Service  | Port | Protocol | Purpose                    |
|----------|------|----------|----------------------------|
| Arda     | 5001 | HTTP     | FastAPI REST API           |
| Beorn    | 5002 | HTTP     | Flask REST API             |
| Palantir | 5003 | HTTP     | Flask REST API             |

---

## Health Checks

### Check Service Health

```bash
# Individual health checks
curl http://159.56.4.94:5001/health  # Arda
curl http://159.56.4.94:5002/health  # Beorn
curl http://159.56.4.94:5003/health  # Palantir

# All services status
docker-compose ps

# Detailed container inspection
docker inspect arda-fastapi
docker inspect beorn-flask
docker inspect palantir-flask
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f beorn

# Last 100 lines
docker-compose logs --tail=100 arda

# Follow logs with timestamps
docker-compose logs -f -t palantir
```

### Check OpenTelemetry Export

Verify traces are being sent to Correlation Gateway:

```bash
# Check service logs for OTLP export
docker-compose logs beorn | grep -i otlp

# Check Correlation Gateway received traces
curl http://159.56.4.94:8080/metrics | grep traces_received

# Query Tempo for recent traces
curl 'http://159.56.4.94:3200/api/search?tags=service.name=beorn&limit=10'

# View in Grafana
# Navigate to: http://159.56.4.94:8443
# Explore → Tempo → Search by service name
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
docker-compose logs <service-name>

# Check if port is already in use
sudo ss -tulpn | grep -E ':(5001|5002|5003)'

# Restart service
docker-compose restart <service-name>

# Rebuild and restart
docker-compose up -d --build <service-name>
```

### Network Issues

```bash
# Check networks exist
docker network ls | grep -E 'sense|observability'

# Create observability network if missing
docker network create \
  --driver bridge \
  --subnet 172.20.0.0/23 \
  observability

# Reconnect service to network
docker network connect observability <container-name>
```

### No Traces in Tempo

```bash
# 1. Check service is exporting traces
docker-compose logs beorn | grep -i "trace"

# 2. Check Correlation Gateway is reachable
docker-compose exec beorn curl -v http://159.56.4.94:4318/v1/traces

# 3. Check Gateway logs
cd /opt/correlation-station/seefa-om
docker-compose logs otel-gateway | grep -i beorn

# 4. Verify Tempo is receiving traces
docker-compose logs tempo | tail -50
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Limit resources in docker-compose.yml
services:
  beorn:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Missing Environment Variables

```bash
# Check container environment
docker exec arda-fastapi env | grep OTEL

# Verify .env files exist
ls -la arda/.env beorn/.env palantir/.env

# Recreate with correct variables
docker-compose down
docker-compose up -d
```

---

## Service URLs

After deployment, services are available at:

- **Arda API**: http://159.56.4.94:5001/docs (FastAPI auto-docs)
- **Beorn API**: http://159.56.4.94:5002/health
- **Palantir API**: http://159.56.4.94:5003/health
- **Grafana**: http://159.56.4.94:8443 (view traces/logs)
- **Correlation Engine**: http://159.56.4.94:8080/docs

---

## Common Operations

### Update Services

```bash
# Pull latest code
cd /opt/correlation-station
git pull origin main

# Rebuild and restart
cd sense-apps
docker-compose up -d --build

# Or update specific service
docker-compose up -d --build beorn
```

### Scale Services

```bash
# Run multiple instances (example: 3 Beorn instances)
docker-compose up -d --scale beorn=3

# Note: You'll need a load balancer for multiple instances
```

### Backup Data

```bash
# Backup volumes
docker run --rm \
  -v sense-apps_arda-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/arda-data-backup.tar.gz /data

# Repeat for beorn-data and palantir-data
```

### Clean Up

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker rmi arda:latest beorn:latest palantir:latest

# Complete cleanup
docker-compose down -v --rmi all
```

---

## Next Steps

1. **Configure Monitoring**: Set up Grafana dashboards for SENSE apps
2. **Set Up Alerts**: Configure Prometheus alerting rules
3. **Enable DataDog**: Add DD_AGENT_HOST for dual export
4. **Instrument Code**: Add OTel instrumentation using `sense-apps/common/otel_utils.py`
5. **Load Testing**: Test with production-like traffic

---

**Author**: Derrick Golden (derrick.golden@charter.com)
**Last Updated**: 2025-11-13
**Version**: 1.0.0
