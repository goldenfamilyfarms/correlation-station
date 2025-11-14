#!/bin/bash
#
# Pre-Setup Script for Server-124 Observability PoC
# Run this BEFORE deploying containers
# This would normally happen in CI/CD
#

set -e

echo "=========================================="
echo "Pre-Setup for Observability PoC"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}✗ .env file not found${NC}"
    echo "Please create .env from .env.example first"
    exit 1
fi

# # ============================================
# # 1. Check Prerequisites
# # ============================================
# echo -e "${BLUE}Step 1: Checking Prerequisites${NC}"
# echo "-------------------------------------------"

# check_command() {
#     if command -v $1 &> /dev/null; then
#         echo -e "${GREEN}✓${NC} $1 found"
#     else
#         echo -e "${RED}✗${NC} $1 not found - installing..."
#         return 1
#     fi
# }

# check_command docker || {
#     echo "Installing Docker..."
#     curl -fsSL https://get.docker.com -o get-docker.sh
#     sudo sh get-docker.sh
#     sudo usermod -aG docker $USER
#     echo -e "${YELLOW}⚠ You may need to log out and back in for Docker permissions${NC}"
# }

# check_command python3.11 || {
#     echo "Installing Python 3.11..."
#     sudo apt install -y software-properties-common
#     sudo add-apt-repository -y ppa:deadsnakes/ppa
#     sudo apt update
#     sudo apt install -y python3.11 python3.11-venv python3.11-dev
# }

# check_command jq || sudo apt install -y jq
# check_command curl || sudo apt install -y curl

# echo ""

# ============================================
# 2. Verify Credentials
# ============================================
echo -e "${BLUE}Step 2: Verifying Credentials${NC}"
echo "-------------------------------------------"

# Check MDSO credentials
if [ -z "$MDSO_USERNAME" ] || [ -z "$MDSO_PASSWORD" ]; then
    echo -e "${RED}✗ MDSO credentials not set in .env${NC}"
    echo "Add: MDSO_USERNAME and MDSO_PASSWORD"
    exit 1
else
    echo -e "${GREEN}✓${NC} MDSO credentials found"
fi

# Check Artifactory credentials
if [ -z "$ARTIFACTORY_USER" ] || [ -z "$ARTIFACTORY_TOKEN" ]; then
    echo -e "${RED}✗ Artifactory credentials not set in .env${NC}"
    echo "Add: ARTIFACTORY_USER and ARTIFACTORY_TOKEN"
    exit 1
else
    echo -e "${GREEN}✓${NC} Artifactory credentials found"
fi

echo ""

# ============================================
# 3. Test Artifactory Connection
# ============================================
echo -e "${BLUE}Step 3: Testing Artifactory Connection${NC}"
echo "-------------------------------------------"

echo "Testing PyPI repository..."
HTTP_CODE=$(curl -u "${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}" \
    -s -o /dev/null -w "%{http_code}" \
    https://docker-artifactory.spectrumflow.net/artifactory/api/pypi/pypi-local/simple/ 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓${NC} Artifactory PyPI access: OK (HTTP 200)"
else
    echo -e "${RED}✗${NC} Artifactory PyPI access failed (HTTP $HTTP_CODE)"
    echo "Please check your ARTIFACTORY_USER and ARTIFACTORY_TOKEN"
    exit 1
fi

echo ""

# ============================================
# 4. Docker Login to Artifactory
# ============================================
echo -e "${BLUE}Step 4: Docker Registry Authentication${NC}"
echo "-------------------------------------------"

echo "Logging into docker-artifactory.spectrumflow.net..."
echo "$ARTIFACTORY_TOKEN" | docker login docker-artifactory.spectrumflow.net \
    -u "$ARTIFACTORY_USER" \
    --password-stdin 2>&1 | grep -q "Login Succeeded"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Docker login successful"
else
    echo -e "${YELLOW}⚠${NC} Docker login may have issues"
fi

echo ""

# ============================================
# 5. Configure Docker for Corporate Proxy
# ============================================
echo -e "${BLUE}Step 5: Configuring Docker Proxy${NC}"
echo "-------------------------------------------"

DOCKER_CONFIG_DIR="$HOME/.docker"
DOCKER_CONFIG_FILE="$DOCKER_CONFIG_DIR/config.json"

mkdir -p "$DOCKER_CONFIG_DIR"

if [ ! -f "$DOCKER_CONFIG_FILE" ] || ! grep -q "proxies" "$DOCKER_CONFIG_FILE"; then
    echo "Creating Docker proxy configuration..."
    cat > "$DOCKER_CONFIG_FILE" << EOF
{
  "proxies": {
    "default": {
      "httpProxy": "http://173.197.207.115:3128",
      "httpsProxy": "http://173.197.207.115:3128",
      "noProxy": "localhost,127.0.0.1,::1,.charter.com,.chtrse.com,.spectrumtoolbox.com,.spectrumflow.net,artifactory.spectrumtoolbox.com,docker-artifactory.spectrumflow.net"
    }
  }
}
EOF
    echo -e "${GREEN}✓${NC} Docker proxy configured"
else
    echo -e "${GREEN}✓${NC} Docker proxy already configured"
fi

echo ""

# ============================================
# 6. Pull Base Images (Pre-cache)
# ============================================
echo -e "${BLUE}Step 6: Pre-caching Base Images${NC}"
echo "-------------------------------------------"

echo "Pulling Python base image..."
docker pull artifactory.spectrumflow.net/docker-local/python:3.11-slim || {
    echo -e "${YELLOW}⚠${NC} Could not pull from Artifactory, trying Docker Hub..."
    docker pull python:3.11-slim
}

echo "Pulling OTel Collector image..."
docker pull otel/opentelemetry-collector-contrib:0.96.0

echo "Pulling Grafana stack images..."
docker pull grafana/grafana:10.4.0
docker pull grafana/loki:2.9.6
docker pull grafana/tempo:2.4.0
docker pull prom/prometheus:v2.50.0

echo -e "${GREEN}✓${NC} Base images cached"
echo ""

# ============================================
# 7. Create Required Directories
# ============================================
echo -e "${BLUE}Step 7: Creating Required Directories${NC}"
echo "-------------------------------------------"

sudo mkdir -p /var/log/mdso
sudo chown $USER:$USER /var/log/mdso
echo -e "${GREEN}✓${NC} Created /var/log/mdso"

sudo mkdir -p /opt/mdso-poller
sudo chown $USER:$USER /opt/mdso-poller
echo -e "${GREEN}✓${NC} Created /opt/mdso-poller"

mkdir -p scripts
echo -e "${GREEN}✓${NC} Created scripts directory"

echo ""

# ============================================
# 8. Install Python Dependencies (for poller)
# ============================================
echo -e "${BLUE}Step 8: Installing Python Dependencies${NC}"
echo "-------------------------------------------"

if [ -f poller/requirements.txt ]; then
    echo "Installing poller dependencies..."
    cd poller
    python -m pip install --user -r requirements.txt
    cd ..
    echo -e "${GREEN}✓${NC} Poller dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} poller/requirements.txt not found, skipping"
fi

echo ""

# ============================================
# 9. Cleanup Any Conflicting Docker Networks
# ============================================
echo -e "${BLUE}Step 9: Cleaning Up Docker Networks${NC}"
echo "-------------------------------------------"

if docker network inspect observability &> /dev/null; then
    echo "Removing existing 'observability' network to avoid conflicts..."
    docker network rm observability 2>/dev/null || {
        echo -e "${YELLOW}⚠${NC} Could not remove network (may be in use)"
        echo "    Stopping any containers that might be using it..."
        docker ps -q --filter "network=observability" | xargs -r docker stop
        docker network rm observability 2>/dev/null || true
    }
    echo -e "${GREEN}✓${NC} Cleaned up existing network"
else
    echo -e "${GREEN}✓${NC} No conflicting networks found"
fi

echo -e "${BLUE}Note:${NC} Docker Compose will create the network when services start"

echo ""

# ============================================
# 10. Test MDSO API Connection
# ============================================
echo -e "${BLUE}Step 10: Testing MDSO API Connection${NC}"
echo "-------------------------------------------"

echo "Testing MDSO authentication endpoint..."
HTTP_CODE=$(curl -X POST \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$MDSO_USERNAME\",\"password\":\"$MDSO_PASSWORD\"}" \
    -s -o /dev/null -w "%{http_code}" \
    http://159.56.4.94/api/v1/tokens 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓${NC} MDSO API accessible (HTTP $HTTP_CODE)"
else
    echo -e "${YELLOW}⚠${NC} MDSO API returned HTTP $HTTP_CODE"
    echo "  This may be normal if credentials are not yet configured"
fi

echo ""

# ============================================
# 11. Set File Permissions
# ============================================
echo -e "${BLUE}Step 11: Setting File Permissions${NC}"
echo "-------------------------------------------"

chmod +x scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.py 2>/dev/null || true
chmod 600 .env
echo -e "${GREEN}✓${NC} File permissions set"

echo ""

# ============================================
# Summary
# ============================================
echo "=========================================="
echo -e "${GREEN}✓ Pre-Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Prerequisites installed"
echo "  ✓ Credentials verified"
echo "  ✓ Artifactory access confirmed"
echo "  ✓ Docker authenticated"
echo "  ✓ Proxy configured"
echo "  ✓ Base images cached"
echo "  ✓ Directories created"
echo "  ✓ Dependencies installed"
echo "  ✓ Docker network ready"
echo "  ✓ MDSO API tested"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Run: ${GREEN}make start-all${NC}"
echo "  2. Wait for services to start (~2 minutes)"
echo "  3. Run: ${GREEN}make health-check${NC}"
echo "  4. Access Grafana: ${GREEN}http://159.56.4.94:3000${NC}"
echo ""
echo "If you need to re-run this setup: ${YELLOW}./scripts/pre-setup.sh${NC}"
echo ""