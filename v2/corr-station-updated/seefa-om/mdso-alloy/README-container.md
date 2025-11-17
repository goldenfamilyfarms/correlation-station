# Alloy Container Deployment on MDSO (Multi-Domain Service Orchestrator) Dev

## Quick Start

### 1. Copy Files to MDSO Dev

```bash
# From your workstation
scp -r mdso-alloy/ bpadmin@159.56.4.37:~/alloy-agent/
```

### 2. Deploy Container

```bash
# SSH to MDSO Dev
ssh bpadmin@159.56.4.37

# Navigate to directory
cd ~/alloy-agent

# Make script executable
chmod +x deploy-container.sh

# Deploy
./deploy-container.sh
```

### 3. Verify

```bash
# Check container status
docker ps | grep alloy

# View logs
docker logs -f alloy-mdso

# Access Alloy UI
# Open browser: http://159.56.4.37:12345
```

## Manual Commands

### Start/Stop

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart
```

### Logs

```bash
# Follow logs
docker logs -f alloy-mdso

# Last 100 lines
docker logs --tail 100 alloy-mdso

# Search for errors
docker logs alloy-mdso | grep -i error
```

### Troubleshooting

```bash
# Check if logs are being sent
docker logs alloy-mdso | grep -i "export"

# Test Meta connectivity from container
docker exec alloy-mdso wget -qO- http://159.56.4.94:55681/v1/logs

# Check file access
docker exec alloy-mdso ls -la /var/log/ciena/
docker exec alloy-mdso ls -la /bp2/log/

# Restart with fresh logs
docker-compose down && docker-compose up -d
```

## Verify on Meta Server

```bash
# SSH to Meta (159.56.4.94)
ssh user@159.56.4.94

# Check OTel Gateway received logs
docker-compose logs otel-gateway | grep -i mdso

# Query Loki for MDSO logs
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={service="mdso"}' \
  --data-urlencode 'limit=10' | jq
```

## Configuration Changes

After modifying `config.alloy`:

```bash
# Restart to apply changes
docker-compose restart

# Or reload without restart (if supported)
docker exec alloy-mdso kill -HUP 1
```

## Cleanup

```bash
# Stop and remove container
docker-compose down

# Remove container and volumes
docker-compose down -v

# Remove image
docker rmi grafana/alloy:latest
```

## Advantages Over Systemd

- ✅ Easy updates: `docker-compose pull && docker-compose up -d`
- ✅ Isolated from host system
- ✅ Portable configuration
- ✅ Built-in health checks
- ✅ Automatic restarts
- ✅ Easy rollback: `docker-compose down && docker-compose up -d`
