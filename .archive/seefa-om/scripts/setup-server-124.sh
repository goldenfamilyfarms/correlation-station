#!/bin/bash
#
# Server-124 Setup Script
# Prepares Server-124 for Observability PoC deployment
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Server-124 Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}ERROR: Do not run this script as root${NC}"
    echo "Run as normal user with sudo privileges"
    exit 1
fi

# ============================================
# Step 1: Install Dependencies
# ============================================
echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"

# Update package index
sudo yum update -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# Install Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "Installing Python 3.11..."
    sudo yum install -y python3.11 python3.11-pip
    echo -e "${GREEN}✓ Python 3.11 installed${NC}"
else
    echo -e "${GREEN}✓ Python 3.11 already installed${NC}"
fi

# Install Git
if ! command -v git &> /dev/null; then
    echo "Installing Git..."
    sudo yum install -y git
    echo -e "${GREEN}✓ Git installed${NC}"
else
    echo -e "${GREEN}✓ Git already installed${NC}"
fi

# Install utilities
sudo yum install -y curl wget jq htop vim

echo ""

# ============================================
# Step 2: Configure Firewall
# ============================================
echo -e "${YELLOW}Step 2: Configuring firewall...${NC}"

# Check if firewalld is running
if sudo systemctl is-active --quiet firewalld; then
    echo "Configuring firewalld..."

    # Open required ports
    PORTS=(3000 3100 3200 4317 4318 5001 5002 5003 8080 9090 14317 14318 55680 55681)

    for port in "${PORTS[@]}"; do
        sudo firewall-cmd --permanent --add-port=${port}/tcp
    done

    sudo firewall-cmd --reload
    echo -e "${GREEN}✓ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠ Firewalld not running, skipping${NC}"
fi

echo ""

# ============================================
# Step 3: Create Project Directory
# ============================================
echo -e "${YELLOW}Step 3: Creating project directory...${NC}"

PROJECT_DIR="/opt/observability-poc"

if [ ! -d "$PROJECT_DIR" ]; then
    sudo mkdir -p $PROJECT_DIR
    sudo chown $USER:$USER $PROJECT_DIR
    echo -e "${GREEN}✓ Created $PROJECT_DIR${NC}"
else
    echo -e "${GREEN}✓ $PROJECT_DIR already exists${NC}"
fi

echo ""

# ============================================
# Step 4: Clone Repository
# ============================================
echo -e "${YELLOW}Step 4: Cloning repository...${NC}"

read -p "Enter Git repository URL (or press Enter to skip): " REPO_URL

if [ -n "$REPO_URL" ]; then
    cd $PROJECT_DIR
    if [ ! -d ".git" ]; then
        git clone $REPO_URL .
        echo -e "${GREEN}✓ Repository cloned${NC}"
    else
        git pull
        echo -e "${GREEN}✓ Repository updated${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Skipping repository clone${NC}"
fi

echo ""

# ============================================
# Step 5: Create Environment File
# ============================================
echo -e "${YELLOW}Step 5: Creating environment file...${NC}"

cd $PROJECT_DIR

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from template${NC}"
        echo -e "${YELLOW}  Edit $PROJECT_DIR/.env to customize configuration${NC}"
    else
        echo -e "${YELLOW}⚠ No .env.example found, skipping${NC}"
    fi
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

echo ""

# ============================================
# Step 6: Configure Docker
# ============================================
echo -e "${YELLOW}Step 6: Configuring Docker...${NC}"

# Set Docker log rotation
DOCKER_DAEMON_CONFIG="/etc/docker/daemon.json"

if [ ! -f "$DOCKER_DAEMON_CONFIG" ]; then
    sudo tee $DOCKER_DAEMON_CONFIG > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    sudo systemctl restart docker
    echo -e "${GREEN}✓ Docker log rotation configured${NC}"
else
    echo -e "${GREEN}✓ Docker daemon.json already exists${NC}"
fi

echo ""

# ============================================
# Step 7: Verify Ports
# ============================================
echo -e "${YELLOW}Step 7: Verifying port availability...${NC}"

REQUIRED_PORTS=(3000 3100 3200 4317 4318 8080 9090)
PORTS_IN_USE=()

for port in "${REQUIRED_PORTS[@]}"; do
    if sudo ss -tulpn | grep -q ":$port "; then
        PORTS_IN_USE+=($port)
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    echo -e "${RED}⚠ Warning: The following ports are already in use:${NC}"
    for port in "${PORTS_IN_USE[@]}"; do
        echo "  Port $port: $(sudo ss -tulpn | grep ":$port " | awk '{print $7}')"
    done
    echo ""
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        echo "Exiting..."
        exit 1
    fi
else
    echo -e "${GREEN}✓ All required ports are available${NC}"
fi

echo ""

# ============================================
# Step 8: Check Disk Space
# ============================================
echo -e "${YELLOW}Step 8: Checking disk space...${NC}"

AVAILABLE_SPACE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')

if [ "$AVAILABLE_SPACE" -lt 100 ]; then
    echo -e "${RED}⚠ Warning: Less than 100GB available (${AVAILABLE_SPACE}GB free)${NC}"
    echo "  Observability stack requires significant disk space for logs/traces"
else
    echo -e "${GREEN}✓ Sufficient disk space (${AVAILABLE_SPACE}GB available)${NC}"
fi

echo ""

# ============================================
# Step 9: Create Systemd Service (Optional)
# ============================================
echo -e "${YELLOW}Step 9: Creating systemd service (optional)...${NC}"

read -p "Create systemd service for auto-start on boot? (y/n): " CREATE_SERVICE

if [ "$CREATE_SERVICE" = "y" ]; then
    sudo tee /etc/systemd/system/observability-poc.service > /dev/null <<EOF
[Unit]
Description=Observability PoC
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable observability-poc.service
    echo -e "${GREEN}✓ Systemd service created and enabled${NC}"
else
    echo -e "${YELLOW}⚠ Skipping systemd service creation${NC}"
fi

echo ""

# ============================================
# Summary
# ============================================
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Review configuration: vim $PROJECT_DIR/.env"
echo "  2. Build images: cd $PROJECT_DIR && make build"
echo "  3. Start services: make up"
echo "  4. Check health: make health"
echo "  5. Access Grafana: http://159.56.4.94:3000"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  • You may need to log out and back in for Docker group membership to take effect"
echo "  • Ensure security group rules allow required ports"
echo "  • Configure Alloy on MDSO Dev to send logs to this server"
echo ""
echo -e "${GREEN}For more information, see: $PROJECT_DIR/README.md${NC}"
echo ""