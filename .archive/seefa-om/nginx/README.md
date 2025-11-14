# Nginx Reverse Proxy Configuration

This directory contains the Nginx reverse proxy configuration for the Correlation Station and SENSE apps.

## Overview

Nginx acts as a reverse proxy providing unified access to all services through a single entry point (port 80/443).

## Proxied Services

### Observability Stack
- **Grafana**: `/grafana/` → http://localhost:8443
- **Charter Toolbox**: `/charter-toolbox/` → http://localhost:3001

### SENSE Apps
- **Arda**: `/arda/` → http://arda-fastapi:5001
- **Beorn**: `/beorn/` → http://beorn-flask:5002
- **Palantir**: `/palantir/` → http://palantir-flask:5003

## Files

- **nginx.conf** - Main Nginx configuration with location blocks
- **nginx-docker-compose.yml** - Docker Compose service definition
- **ssl/** - SSL certificates directory (self-signed certs)

## Deployment

### Start Nginx

```bash
cd seefa-om/nginx
docker-compose -f nginx-docker-compose.yml up -d
```

### Reload Configuration

After editing nginx.conf:

```bash
# Test configuration
docker exec sbnoe-nginx nginx -t

# Reload (no downtime)
docker exec sbnoe-nginx nginx -s reload

# Or restart container
docker-compose -f nginx-docker-compose.yml restart
```

### View Logs

```bash
docker-compose -f nginx-docker-compose.yml logs -f
```

## Network Configuration

Nginx connects to three Docker networks:

1. **nginx-ingress** (172.16.100.0/23) - Nginx internal network
2. **observability** - Connects to Grafana, Correlation Engine, etc.
3. **sense-network** - Connects to SENSE apps (Arda, Beorn, Palantir)

This allows Nginx to route traffic to services across different networks.

## Access URLs

Once deployed, access services via:

- http://159.56.4.94/arda/
- http://159.56.4.94/beorn/
- http://159.56.4.94/palantir/
- http://159.56.4.94/grafana/
- http://159.56.4.94/charter-toolbox/

## Prerequisites

Before starting Nginx, ensure:

1. **Observability stack is running**:
   ```bash
   cd seefa-om
   docker-compose up -d
   ```

2. **SENSE apps are running**:
   ```bash
   cd sense-apps
   docker-compose up -d
   ```

3. **Networks exist**:
   ```bash
   docker network ls | grep -E 'observability|sense-network'
   ```

If networks are missing, they'll be created automatically by the respective docker-compose files.

## Troubleshooting

### 502 Bad Gateway

If you get 502 errors:

```bash
# Check target service is running
docker ps | grep -E 'arda|beorn|palantir'

# Check Nginx can reach the service
docker exec sbnoe-nginx ping arda-fastapi
docker exec sbnoe-nginx wget -qO- http://arda-fastapi:5001/health

# Check Nginx logs
docker-compose -f nginx-docker-compose.yml logs
```

### Network Issues

```bash
# Verify Nginx is connected to all networks
docker inspect sbnoe-nginx | grep -A 20 Networks

# Reconnect to network if needed
docker network connect observability sbnoe-nginx
docker network connect sense-apps_sense-network sbnoe-nginx
```

### Configuration Errors

```bash
# Test configuration syntax
docker exec sbnoe-nginx nginx -t

# View full error log
docker exec sbnoe-nginx cat /var/log/nginx/error.log
```

## SSL/HTTPS

SSL is configured for port 443 using self-signed certificates in the `ssl/` directory.

To use custom certificates:
1. Replace `ssl/certs/nginx-selfsigned.crt`
2. Replace `ssl/private/nginx-selfsigned.key`
3. Reload Nginx: `docker exec sbnoe-nginx nginx -s reload`

## Adding New Services

To proxy a new service:

1. Edit `nginx.conf`:
   ```nginx
   location /newservice/ {
       proxy_pass http://newservice-container:port/;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   ```

2. Reload configuration:
   ```bash
   docker exec sbnoe-nginx nginx -t
   docker exec sbnoe-nginx nginx -s reload
   ```

3. Test:
   ```bash
   curl http://159.56.4.94/newservice/
   ```

---

**Author**: Derrick Golden (derrick.golden@charter.com)
**Last Updated**: 2025-11-13
