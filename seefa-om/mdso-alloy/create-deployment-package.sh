#!/bin/bash
# Create deployment package for MDSO instrumentation

set -e

echo "=== Creating MDSO Instrumentation Deployment Package ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="mdso-instrumentation-deploy"
BUILD_DIR="/tmp/${PACKAGE_NAME}"

# Clean previous builds
rm -rf "$BUILD_DIR"
rm -f "${SCRIPT_DIR}/${PACKAGE_NAME}.tar.gz"

# Create build directory
mkdir -p "$BUILD_DIR"

echo "→ Copying files to build directory..."

# Copy Alloy configuration
cp "$SCRIPT_DIR/config.alloy" "$BUILD_DIR/"
cp "$SCRIPT_DIR/docker-compose.yml" "$BUILD_DIR/"

# Copy deployment scripts
cp "$SCRIPT_DIR/deploy-container.sh" "$BUILD_DIR/"
chmod +x "$BUILD_DIR/deploy-container.sh"

# Copy verification scripts
cp "$SCRIPT_DIR/verify-deployment.sh" "$BUILD_DIR/"
chmod +x "$BUILD_DIR/verify-deployment.sh"

# Copy OTel instrumentation code
echo "→ Copying OTel instrumentation..."
cp -r "$SCRIPT_DIR/mdso-instrumentation" "$BUILD_DIR/"

# Copy documentation
echo "→ Copying documentation..."
cp "$SCRIPT_DIR/DEPLOY_TO_REMOTE.md" "$BUILD_DIR/README.md"
cp "$SCRIPT_DIR/DEPLOYMENT-GUIDE-ENHANCED.md" "$BUILD_DIR/"
cp "$SCRIPT_DIR/TESTING-GUIDE-ENHANCED.md" "$BUILD_DIR/"

# Create installation script
cat > "$BUILD_DIR/install.sh" <<'EOF'
#!/bin/bash
# Install MDSO instrumentation on remote server

set -e

echo "=== MDSO Instrumentation Installation ==="
echo ""

# Check if running on remote server
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Current host IP: $CURRENT_IP"
echo ""

# Verify prerequisites
echo "→ Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found. Please install Docker first."
    exit 1
fi
echo "  ✓ Docker installed"

# Check Docker Compose
if ! docker-compose --version &> /dev/null; then
    if ! docker compose version &> /dev/null; then
        echo "ERROR: Docker Compose not found"
        exit 1
    fi
fi
echo "  ✓ Docker Compose installed"

# Check log directories
if [ ! -d "/var/log/ciena" ]; then
    echo "WARNING: /var/log/ciena not found"
    echo "  Creating directory..."
    sudo mkdir -p /var/log/ciena
fi
echo "  ✓ Log directory exists"

if [ ! -d "/bp2/log" ]; then
    echo "WARNING: /bp2/log not found"
    echo "  You may need to update config.alloy with correct log paths"
fi

# Test connectivity to Meta
echo ""
echo "→ Testing connectivity to Meta server (159.56.4.94:55681)..."
if curl -s --max-time 5 http://159.56.4.94:55681 > /dev/null 2>&1; then
    echo "  ✓ Meta server reachable"
else
    echo "WARNING: Cannot reach Meta server"
    echo "  Check network connectivity and firewall rules"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "  1. Review config.alloy and update paths if needed"
echo "  2. Run: ./deploy-container.sh"
echo "  3. Verify deployment: ./verify-deployment.sh"
echo ""
EOF

chmod +x "$BUILD_DIR/install.sh"

# Create README for deployment
cat > "$BUILD_DIR/QUICK_DEPLOY.md" <<'EOF'
# Quick Deployment Guide

## On Your Local Machine

```bash
# Deploy to remote server
scp mdso-instrumentation-deploy.tar.gz bpadmin@159.56.4.37:~/
```

## On Remote MDSO Server

```bash
# SSH to server
ssh bpadmin@159.56.4.37

# Extract package
tar -xzf mdso-instrumentation-deploy.tar.gz
cd mdso-instrumentation-deploy

# Run installation
./install.sh

# Deploy Alloy container
./deploy-container.sh

# Verify deployment
./verify-deployment.sh
```

## Deploying OTel to Products

```bash
# Copy instrumentation to product directory
PRODUCT_DIR="/opt/ciena/bp2/your-product/scripts"
sudo cp -r mdso-instrumentation/otel_instrumentation $PRODUCT_DIR/

# Install dependencies
cd $PRODUCT_DIR
pip install -r otel_instrumentation/requirements.txt
```

See README.md for detailed instructions.
EOF

# Create tarball
echo ""
echo "→ Creating tarball..."
cd /tmp
tar -czf "${SCRIPT_DIR}/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"

# Cleanup
rm -rf "$BUILD_DIR"

echo ""
echo "=== Package Created ==="
echo "Location: ${SCRIPT_DIR}/${PACKAGE_NAME}.tar.gz"
echo "Size: $(du -h "${SCRIPT_DIR}/${PACKAGE_NAME}.tar.gz" | cut -f1)"
echo ""
echo "Deploy with:"
echo "  scp ${PACKAGE_NAME}.tar.gz user@<mdso-server>:~/"
echo "  ssh user@<mdso-server>"
echo "  tar -xzf ${PACKAGE_NAME}.tar.gz && cd ${PACKAGE_NAME}"
echo "  ./install.sh"
echo ""
