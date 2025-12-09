#!/bin/bash
#
# Grafana Alloy Installation Script for MDSO Server
# Deploys Alloy agent to collect MDSO logs and forward to Meta server
#
# Usage:
#   ./install-alloy.sh
#
# Prerequisites:
#   - Root access on MDSO server
#   - Network connectivity to Meta server (159.56.4.94:55681)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ALLOY_VERSION="v1.0.0"
ALLOY_BINARY_URL="https://github.com/grafana/alloy/releases/download/${ALLOY_VERSION}/alloy-linux-amd64"
ALLOY_CONFIG_DIR="/etc/alloy"
ALLOY_DATA_DIR="/var/lib/alloy"
META_SERVER="159.56.4.94"
META_PORT="55681"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Grafana Alloy Installation for MDSO${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   exit 1
fi

# Check network connectivity to Meta server
echo -e "${YELLOW}→ Checking network connectivity to Meta server...${NC}"
if nc -z -w5 $META_SERVER $META_PORT 2>/dev/null; then
    echo -e "${GREEN}✓ Meta server reachable${NC}"
else
    echo -e "${RED}❌ Cannot reach Meta server at $META_SERVER:$META_PORT${NC}"
    echo -e "${YELLOW}Please ensure network connectivity before continuing${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Download Alloy binary
echo -e "${YELLOW}→ Downloading Grafana Alloy ${ALLOY_VERSION}...${NC}"
if command -v wget &> /dev/null; then
    wget -q --show-progress "$ALLOY_BINARY_URL" -O /tmp/alloy-linux-amd64
elif command -v curl &> /dev/null; then
    curl -L --progress-bar "$ALLOY_BINARY_URL" -o /tmp/alloy-linux-amd64
else
    echo -e "${RED}❌ Neither wget nor curl found. Please install one.${NC}"
    exit 1
fi

# Verify download
if [[ ! -f /tmp/alloy-linux-amd64 ]]; then
    echo -e "${RED}❌ Failed to download Alloy binary${NC}"
    exit 1
fi

# Install binary
echo -e "${YELLOW}→ Installing Alloy binary...${NC}"
chmod +x /tmp/alloy-linux-amd64
mv /tmp/alloy-linux-amd64 /usr/local/bin/alloy
echo -e "${GREEN}✓ Alloy binary installed to /usr/local/bin/alloy${NC}"

# Verify installation
ALLOY_INSTALLED_VERSION=$(/usr/local/bin/alloy --version 2>&1 | head -n1 || echo "unknown")
echo -e "${GREEN}  Installed version: $ALLOY_INSTALLED_VERSION${NC}"

# Create configuration directory
echo -e "${YELLOW}→ Creating configuration directory...${NC}"
mkdir -p "$ALLOY_CONFIG_DIR"
mkdir -p "$ALLOY_DATA_DIR"

# Copy configuration file
if [[ -f "$(dirname "$0")/mdso-config.alloy" ]]; then
    echo -e "${YELLOW}→ Installing Alloy configuration...${NC}"
    cp "$(dirname "$0")/mdso-config.alloy" "$ALLOY_CONFIG_DIR/config.alloy"
    echo -e "${GREEN}✓ Configuration installed to $ALLOY_CONFIG_DIR/config.alloy${NC}"
else
    echo -e "${RED}❌ Configuration file mdso-config.alloy not found${NC}"
    echo -e "${YELLOW}Please manually copy mdso-config.alloy to $ALLOY_CONFIG_DIR/config.alloy${NC}"
    exit 1
fi

# Validate configuration
echo -e "${YELLOW}→ Validating configuration...${NC}"
if /usr/local/bin/alloy fmt --check "$ALLOY_CONFIG_DIR/config.alloy" 2>/dev/null; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${YELLOW}⚠  Configuration validation failed (may be expected)${NC}"
fi

# Create Alloy user (if doesn't exist)
if ! id -u alloy &>/dev/null; then
    echo -e "${YELLOW}→ Creating alloy user...${NC}"
    useradd --system --no-create-home --shell /bin/false alloy
    echo -e "${GREEN}✓ Alloy user created${NC}"
fi

# Set ownership
chown -R alloy:alloy "$ALLOY_DATA_DIR"

# Create systemd service
echo -e "${YELLOW}→ Creating systemd service...${NC}"
cat > /etc/systemd/system/alloy.service << 'EOF'
[Unit]
Description=Grafana Alloy
Documentation=https://grafana.com/docs/alloy/latest/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/alloy run /etc/alloy/config.alloy --storage.path=/var/lib/alloy
Restart=on-failure
RestartSec=10
LimitNOFILE=65536

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=alloy

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/alloy
ReadOnlyPaths=/opt/ciena/bp2

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Systemd service created${NC}"

# Reload systemd
echo -e "${YELLOW}→ Reloading systemd...${NC}"
systemctl daemon-reload

# Enable and start service
echo -e "${YELLOW}→ Enabling Alloy service...${NC}"
systemctl enable alloy

echo -e "${YELLOW}→ Starting Alloy service...${NC}"
if systemctl start alloy; then
    echo -e "${GREEN}✓ Alloy service started${NC}"
else
    echo -e "${RED}❌ Failed to start Alloy service${NC}"
    echo -e "${YELLOW}Check logs: sudo journalctl -u alloy -f${NC}"
    exit 1
fi

# Wait for service to be ready
echo -e "${YELLOW}→ Waiting for Alloy to be ready...${NC}"
sleep 3

# Check service status
if systemctl is-active --quiet alloy; then
    echo -e "${GREEN}✓ Alloy is running${NC}"
else
    echo -e "${RED}❌ Alloy is not running${NC}"
    echo -e "${YELLOW}Check status: sudo systemctl status alloy${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Service Information:${NC}"
echo "  Service: alloy"
echo "  Config:  $ALLOY_CONFIG_DIR/config.alloy"
echo "  Data:    $ALLOY_DATA_DIR"
echo "  Target:  $META_SERVER:$META_PORT"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Status:  sudo systemctl status alloy"
echo "  Logs:    sudo journalctl -u alloy -f"
echo "  Restart: sudo systemctl restart alloy"
echo "  Stop:    sudo systemctl stop alloy"
echo "  Config:  sudo vi $ALLOY_CONFIG_DIR/config.alloy"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Verify logs are being forwarded:"
echo "     sudo journalctl -u alloy -f"
echo "  2. Check Meta server received logs:"
echo "     curl 'http://$META_SERVER:3100/loki/api/v1/query' --data-urlencode 'query={container=\"scriptplan\"}' --data-urlencode 'limit=10'"
echo "  3. Monitor Alloy metrics:"
echo "     curl http://localhost:12345/metrics"
echo ""
echo -e "${GREEN}Installation successful! 🎉${NC}"
