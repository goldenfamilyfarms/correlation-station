##!/bin/bash
# #
# # Grafana Alloy Installation Script for MDSO Dev
# # Installs and configures Alloy to tail syslogs and send to Server-124
# #

# set -e

# # Colors
# RED='\033[0;31m'
# GREEN='\033[0;32m'
# YELLOW='\033[1;33m'
# BLUE='\033[0;34m'
# NC='\033[0m'

# echo -e "${BLUE}========================================${NC}"
# echo -e "${GREEN}Grafana Alloy Installation (MDSO Dev)${NC}"
# echo -e "${BLUE}========================================${NC}"
# echo ""

# # Check if running as root
# if [ "$EUID" -ne 0 ]; then
#     echo -e "${RED}ERROR: This script must be run as root${NC}"
#     echo "Please run: sudo $0"
#     exit 1
# fi

# # Configuration
# ALLOY_VERSION="1.0.0"
# SERVER_124_HOST="${SERVER_124_HOST:-159.56.4.94}"
# SERVER_124_PORT="${SERVER_124_PORT:-4318}"
# ALLOY_CONFIG_DIR="/etc/alloy"
# ALLOY_BIN="/usr/local/bin/alloy"

# # ============================================
# # Step 1: Install Alloy Binary
# # ============================================
# echo -e "${YELLOW}Step 1: Installing Grafana Alloy...${NC}"

# # Download Alloy
# if [ ! -f "$ALLOY_BIN" ]; then
#     echo "Downloading Alloy binary..."
#     curl -L -o /tmp/alloy-linux-amd64 \
#         "https://github.com/grafana/alloy/releases/download/v${ALLOY_VERSION}/alloy-linux-amd64"

#     # Install binary
#     mv /tmp/alloy-linux-amd64 $ALLOY_BIN
#     chmod +x $ALLOY_BIN

#     echo -e "${GREEN}✓ Alloy binary installed${NC}"
# else
#     echo -e "${GREEN}✓ Alloy binary already installed${NC}"
# fi

# # Verify installation
# if $ALLOY_BIN --version > /dev/null 2>&1; then
#     echo -e "${GREEN}✓ Alloy version: $($ALLOY_BIN --version | head -1)${NC}"
# else
#     echo -e "${RED}✗ Alloy installation failed${NC}"
#     exit 1
# fi

# echo ""

# # ============================================
# # Step 2: Create Configuration Directory
# # ============================================
# echo -e "${YELLOW}Step 2: Creating configuration directory...${NC}"

# mkdir -p $ALLOY_CONFIG_DIR
# mkdir -p $ALLOY_CONFIG_DIR/certs
# mkdir -p /var/log/alloy

# echo -e "${GREEN}✓ Configuration directory created${NC}"
# echo ""

# # ============================================
# # Step 3: Install Configuration
# # ============================================
# echo -e "${YELLOW}Step 3: Installing Alloy configuration...${NC}"

# # Check if config.alloy exists in current directory
# if [ -f "$(dirname $0)/config.alloy" ]; then
#     cp "$(dirname $0)/config.alloy" $ALLOY_CONFIG_DIR/config.alloy

#     # Update Server-124 endpoint in config
#     sed -i "s|endpoint = \"http://159.56.4.94:4318\"|endpoint = \"http://${SERVER_124_HOST}:${SERVER_124_PORT}\"|g" \
#         $ALLOY_CONFIG_DIR/config.alloy

#     echo -e "${GREEN}✓ Configuration installed${NC}"
# else
#     echo -e "${YELLOW}⚠ config.alloy not found in current directory${NC}"
#     echo "Creating minimal configuration..."

#     cat > $ALLOY_CONFIG_DIR/config.alloy <<'EOF'
# // Grafana Alloy Configuration for MDSO Dev
# logging {
#   level  = "info"
#   format = "json"
# }

# local.file_match "mdso_syslogs" {
#   path_targets = [
#     {
#       __path__ = "/var/log/ciena/blueplanet.log",
#       service  = "blueplanet",
#       env      = "dev",
#       host     = "mdso-dev",
#     },
#   ]
# }

# loki.source.file "mdso_logs" {
#   targets    = local.file_match.mdso_syslogs.targets
#   forward_to = [loki.process.parse_logs.receiver]
# }

# loki.process "parse_logs" {
#   forward_to = [otelcol.receiver.loki.default]

#   stage.json {
#     expressions = {
#       timestamp = "timestamp",
#       severity  = "severity",
#       message   = "message",
#       trace_id  = "trace_id",
#     }
#   }
# }

# otelcol.receiver.loki "default" {
#   output {
#     logs = [otelcol.processor.batch.default.input]
#   }
# }

# otelcol.processor.batch "default" {
#   output {
#     logs = [otelcol.exporter.otlphttp.server124.input]
#   }
# }

# otelcol.exporter.otlphttp "server124" {
#   client {
#     endpoint = "http://PLACEHOLDER_HOST:PLACEHOLDER_PORT"
#     compression = "gzip"
#     timeout     = "30s"
#   }
# }
# EOF

#     # Replace placeholder
#     sed -i "s|PLACEHOLDER_HOST:PLACEHOLDER_PORT|${SERVER_124_HOST}:${SERVER_124_PORT}|g" \
#         $ALLOY_CONFIG_DIR/config.alloy

#     echo -e "${GREEN}✓ Minimal configuration created${NC}"
# fi

# echo ""

# # ============================================
# # Step 4: Verify Log Paths
# # ============================================
# echo -e "${YELLOW}Step 4: Verifying syslog paths...${NC}"

# LOG_PATHS=(
#     "/var/log/ciena/blueplanet.log"
#     "/bp2/log"
# )

# for path in "${LOG_PATHS[@]}"; do
#     if [ -e "$path" ]; then
#         echo -e "${GREEN}✓ Found: $path${NC}"
#     else
#         echo -e "${YELLOW}⚠ Not found: $path${NC}"
#     fi
# done

# echo ""

# # ============================================
# # Step 5: Test Connectivity to Server-124
# # ============================================
# echo -e "${YELLOW}Step 5: Testing connectivity to Server-124...${NC}"

# if curl -f -s -X POST http://${SERVER_124_HOST}:${SERVER_124_PORT}/v1/logs \
#     -H "Content-Type: application/json" \
#     -d '{"resourceLogs":[]}' > /dev/null; then
#     echo -e "${GREEN}✓ Server-124 is reachable at ${SERVER_124_HOST}:${SERVER_124_PORT}${NC}"
# else
#     echo -e "${RED}✗ Cannot reach Server-124 at ${SERVER_124_HOST}:${SERVER_124_PORT}${NC}"
#     echo "  Please verify:"
#     echo "  1. Server-124 is running"
#     echo "  2. OTel Gateway is started (port ${SERVER_124_PORT})"
#     echo "  3. Firewall allows outbound connections"
#     echo ""
#     read -p "Continue anyway? (y/n): " CONTINUE
#     if [ "$CONTINUE" != "y" ]; then
#         exit 1
#     fi
# fi

# echo ""

# # ============================================
# # Step 6: Create Systemd Service
# # ============================================
# echo -e "${YELLOW}Step 6: Creating systemd service...${NC}"

# # Check if service file exists in current directory
# if [ -f "$(dirname $0)/systemd/alloy.service" ]; then
#     cp "$(dirname $0)/systemd/alloy.service" /etc/systemd/system/alloy.service
# else
#     # Create service file
#     cat > /etc/systemd/system/alloy.service <<EOF
# [Unit]
# Description=Grafana Alloy
# Documentation=https://grafana.com/docs/alloy/
# After=network-online.target
# Wants=network-online.target

# [Service]
# Type=simple
# User=root
# Group=root
# ExecStart=$ALLOY_BIN run --config.file=$ALLOY_CONFIG_DIR/config.alloy --server.http.listen-addr=0.0.0.0:12345
# Restart=always
# RestartSec=10
# StandardOutput=journal
# StandardError=journal
# SyslogIdentifier=alloy

# [Install]
# WantedBy=multi-user.target
# EOF
# fi

# # Reload systemd
# systemctl daemon-reload

# echo -e "${GREEN}✓ Systemd service created${NC}"
# echo ""

# # ============================================
# # Step 7: Validate Configuration
# # ============================================
# echo -e "${YELLOW}Step 7: Validating Alloy configuration...${NC}"

# if $ALLOY_BIN run --config.file=$ALLOY_CONFIG_DIR/config.alloy --stability.level=experimental --dry-run 2>&1 | grep -q "dry run complete"; then
#     echo -e "${GREEN}✓ Configuration is valid${NC}"
# else
#     echo -e "${RED}✗ Configuration validation failed${NC}"
#     echo "Please check $ALLOY_CONFIG_DIR/config.alloy"
#     exit 1
# fi

# echo ""

# # ============================================
# # Step 8: Start Alloy Service
# # ============================================
# echo -e "${YELLOW}Step 8: Starting Alloy service...${NC}"

# # Enable service
# systemctl enable alloy.service

# # Start service
# systemctl start alloy.service

# # Wait a moment
# sleep 3

# # Check status
# if systemctl is-active --quiet alloy.service; then
#     echo -e "${GREEN}✓ Alloy service is running${NC}"
# else
#     echo -e "${RED}✗ Alloy service failed to start${NC}"
#     echo "Check logs: journalctl -u alloy -f"
#     exit 1
# fi

# echo ""

# # ============================================
# # Step 9: Create Logrotate Configuration
# # ============================================
# echo -e "${YELLOW}Step 9: Creating logrotate configuration...${NC}"

# cat > /etc/logrotate.d/alloy <<EOF
# /var/log/alloy/*.log {
#     daily
#     rotate 7
#     compress
#     delaycompress
#     notifempty
#     missingok
#     create 0644 root root
# }
# EOF

# echo -e "${GREEN}✓ Logrotate configuration created${NC}"
# echo ""

# # ============================================
# # Summary
# # ============================================
# echo -e "${BLUE}========================================${NC}"
# echo -e "${GREEN}Alloy Installation Complete!${NC}"
# echo -e "${BLUE}========================================${NC}"
# echo ""
# echo -e "${YELLOW}Service Status:${NC}"
# systemctl status alloy.service --no-pager | head -5
# echo ""
# echo -e "${YELLOW}Configuration:${NC}"
# echo "  Config file: $ALLOY_CONFIG_DIR/config.alloy"
# echo "  Target: http://${SERVER_124_HOST}:${SERVER_124_PORT}"
# echo ""
# echo -e "${YELLOW}Useful Commands:${NC}"
# echo "  View logs:    sudo journalctl -u alloy -f"
# echo "  Restart:      sudo systemctl restart alloy"
# echo "  Stop:         sudo systemctl stop alloy"
# echo "  Status:       sudo systemctl status alloy"
# echo "  Edit config:  sudo vim $ALLOY_CONFIG_DIR/config.alloy"
# echo "  Reload config: sudo systemctl restart alloy"
# echo ""
# echo -e "${YELLOW}Verification:${NC}"
# echo "  1. Check Alloy logs: sudo journalctl -u alloy -f"
# echo "  2. Verify logs in Grafana: http://${SERVER_124_HOST}:3000"
# echo "  3. Query Loki for service 'blueplanet'"
# echo ""
# echo -e "${GREEN}Alloy is now tailing syslogs and sending to Server-124!${NC}"
# echo ""

#!/usr/bin/env bash
#
# Grafana Alloy Docker Setup Script for MDSO Dev
# Runs Alloy in a Docker container, auto-started by systemd
#

set -euo pipefail

# ─── Colors ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Grafana Alloy Docker Setup (MDSO Dev)${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ─── Configurable Variables ───────────────────────────────
ALLOY_VERSION="latest"
SERVER_124_HOST="${SERVER_124_HOST:-159.56.4.94}"
SERVER_124_PORT="${SERVER_124_PORT:-4318}"
ALLOY_HTTP_PORT="${ALLOY_HTTP_PORT:-8088}"
ALLOY_CONFIG_DIR="/etc/alloy"
ALLOY_DOCKER_IMAGE="grafana/alloy:${ALLOY_VERSION}"
SERVICE_NAME="alloy-docker"
COMPOSE_FILE="${ALLOY_CONFIG_DIR}/docker-compose.yml"

# ─── Root Check ───────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}ERROR: Must be run as root.${NC}"
  echo "Run: sudo $0"
  exit 1
fi

# ─── Step 1: Ensure Docker Installed ──────────────────────
echo -e "${YELLOW}Step 1: Checking Docker installation...${NC}"
if ! command -v docker &>/dev/null; then
  echo "Installing Docker..."
  dnf install -y docker || yum install -y docker
  systemctl enable --now docker
fi
if ! systemctl is-active --quiet docker; then
  echo "Starting Docker..."
  systemctl start docker
fi
echo -e "${GREEN}✓ Docker is running${NC}\n"

# ─── Step 2: Create Directories ───────────────────────────
echo -e "${YELLOW}Step 2: Creating directories...${NC}"
mkdir -p "${ALLOY_CONFIG_DIR}" /var/log/alloy
echo -e "${GREEN}✓ Created ${ALLOY_CONFIG_DIR} and /var/log/alloy${NC}\n"

# ─── Step 3: Write Config ─────────────────────────────────
echo -e "${YELLOW}Step 3: Writing Alloy configuration...${NC}"
CONFIG_FILE="${ALLOY_CONFIG_DIR}/config.alloy"

if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" <<EOF
// Grafana Alloy Configuration for MDSO Dev
logging {
  level  = "info"
  format = "json"
}

server "alloy" {
  http { listen_addr = "0.0.0.0:${ALLOY_HTTP_PORT}" }
}

otelcol.receiver.loki "default" {
  output { logs = [otelcol.processor.batch.default.input] }
}

otelcol.processor.batch "default" {
  timeout             = "10s"
  send_batch_size     = 512
  send_batch_max_size = 1024
  output { logs = [otelcol.processor.resource.default.input] }
}

otelcol.processor.resource "default" {
  attributes {
    action = "upsert"
    key    = "service.name"
    value  = "blueplanet"
  }
  attributes {
    action = "upsert"
    key    = "deployment.environment"
    value  = "dev"
  }
  output { logs = [otelcol.exporter.otlphttp.server124.input] }
}

otelcol.exporter.otlphttp "server124" {
  client {
    endpoint    = "http://${SERVER_124_HOST}:${SERVER_124_PORT}"
    compression = "gzip"
    timeout     = "30s"
  }
}
EOF
  echo -e "${GREEN}✓ Created base config: ${CONFIG_FILE}${NC}"
else
  echo -e "${GREEN}✓ Existing config detected${NC}"
fi
echo ""

# ─── Step 4: Generate docker-compose.yml ──────────────────
echo -e "${YELLOW}Step 4: Creating docker-compose.yml...${NC}"
cat > "$COMPOSE_FILE" <<EOF
version: "3.9"
services:
  alloy:
    image: ${ALLOY_DOCKER_IMAGE}
    container_name: alloy
    restart: unless-stopped
    ports:
      - "${ALLOY_HTTP_PORT}:${ALLOY_HTTP_PORT}"
    volumes:
      - ${ALLOY_CONFIG_DIR}/config.alloy:/etc/alloy/config.alloy:ro,Z
      - /var/log/alloy:/var/log/alloy:Z
    command: >
      run
      --server.http.listen-addr=0.0.0.0:${ALLOY_HTTP_PORT}
      --storage.path=/var/lib/alloy/data
      /etc/alloy/config.alloy
EOF
echo -e "${GREEN}✓ docker-compose.yml created${NC}\n"

# ─── Step 5: Validate Config ──────────────────────────────
echo -e "${YELLOW}Step 5: Validating Alloy config...${NC}"
docker run --rm \
  -v "${CONFIG_FILE}:/etc/alloy/config.alloy" \
  "${ALLOY_DOCKER_IMAGE}" lint /etc/alloy/config.alloy || {
  echo -e "${RED}✗ Config validation failed${NC}"
  exit 1
}
echo -e "${GREEN}✓ Configuration valid${NC}\n"

# ─── Step 6: Check Server-124 Connectivity ────────────────
echo -e "${YELLOW}Step 6: Checking connectivity to Server-124...${NC}"
if curl -fs -X POST "http://${SERVER_124_HOST}:${SERVER_124_PORT}/v1/logs" \
  -H "Content-Type: application/json" \
  -d '{"resourceLogs":[]}' >/dev/null; then
  echo -e "${GREEN}✓ Server-124 reachable${NC}"
else
  echo -e "${RED}⚠ Server-124 not reachable${NC}"
  read -p "Continue anyway? (y/n): " ans
  [[ "$ans" != "y" ]] && exit 1
fi
echo ""

# ─── Step 7: Start Alloy Container ────────────────────────
echo -e "${YELLOW}Step 7: Starting Alloy container...${NC}"
cd "${ALLOY_CONFIG_DIR}"
docker compose up -d
sleep 3
if docker ps --filter "name=alloy" --filter "status=running" | grep -q alloy; then
  echo -e "${GREEN}✓ Alloy container running${NC}\n"
else
  echo -e "${RED}✗ Alloy container failed to start${NC}"
  echo "Run: docker logs alloy"
  exit 1
fi

# ─── Step 8: Create systemd Service ───────────────────────
echo -e "${YELLOW}Step 8: Setting up systemd auto-start...${NC}"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Grafana Alloy (Docker)
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${ALLOY_CONFIG_DIR}
ExecStart=/usr/bin/docker compose -f ${COMPOSE_FILE} up -d
ExecStop=/usr/bin/docker compose -f ${COMPOSE_FILE} down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl start "${SERVICE_NAME}.service"
sleep 2

if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
  echo -e "${GREEN}✓ systemd service active: ${SERVICE_NAME}${NC}\n"
else
  echo -e "${RED}✗ Failed to start ${SERVICE_NAME}${NC}"
  exit 1
fi

# ─── Summary ──────────────────────────────────────────────
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Alloy Docker Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Config:     ${CONFIG_FILE}"
echo "  Compose:    ${COMPOSE_FILE}"
echo "  Endpoint:   http://${SERVER_124_HOST}:${SERVER_124_PORT}"
echo ""
echo -e "${YELLOW}Alloy Web UI:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):${ALLOY_HTTP_PORT}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  sudo systemctl stop ${SERVICE_NAME}"
echo "  sudo docker logs alloy -f"
echo ""
echo -e "${GREEN}Alloy is now running in Docker and will start automatically on boot.${NC}\n"
