#!/bin/bash
# Deploy MDSO instrumentation to remote server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="mdso-instrumentation-deploy.tar.gz"

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <remote-server> [remote-user]"
    echo ""
    echo "Example:"
    echo "  $0 159.56.4.37"
    echo "  $0 159.56.4.37 bpadmin"
    echo ""
    exit 1
fi

REMOTE_SERVER="$1"
REMOTE_USER="${2:-bpadmin}"
REMOTE_PATH="~/alloy-agent"

echo "=== Deploying MDSO Instrumentation to Remote Server ==="
echo ""
echo "Remote server: ${REMOTE_USER}@${REMOTE_SERVER}"
echo "Remote path: ${REMOTE_PATH}"
echo ""

# Check if package exists
if [ ! -f "${SCRIPT_DIR}/${PACKAGE_NAME}" ]; then
    echo "Package not found. Creating deployment package..."
    "${SCRIPT_DIR}/create-deployment-package.sh"
fi

# Test SSH connectivity
echo "→ Testing SSH connectivity..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${REMOTE_USER}@${REMOTE_SERVER}" echo "SSH OK" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to ${REMOTE_USER}@${REMOTE_SERVER}"
    echo "Make sure:"
    echo "  1. Server is reachable"
    echo "  2. SSH keys are configured"
    echo "  3. User has correct permissions"
    exit 1
fi
echo "  ✓ SSH connection OK"

# Create remote directory
echo ""
echo "→ Creating remote directory..."
ssh "${REMOTE_USER}@${REMOTE_SERVER}" "mkdir -p ${REMOTE_PATH}"

# Copy package
echo ""
echo "→ Copying deployment package..."
scp "${SCRIPT_DIR}/${PACKAGE_NAME}" "${REMOTE_USER}@${REMOTE_SERVER}:${REMOTE_PATH}/"

# Extract and install
echo ""
echo "→ Extracting package on remote server..."
ssh "${REMOTE_USER}@${REMOTE_SERVER}" << EOF
cd ${REMOTE_PATH}
tar -xzf ${PACKAGE_NAME}
cd mdso-instrumentation-deploy

echo ""
echo "=== Running installation on remote server ==="
./install.sh
EOF

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. SSH to remote server:"
echo "   ssh ${REMOTE_USER}@${REMOTE_SERVER}"
echo ""
echo "2. Navigate to deployment directory:"
echo "   cd ${REMOTE_PATH}/mdso-instrumentation-deploy"
echo ""
echo "3. Deploy Alloy container:"
echo "   ./deploy-container.sh"
echo ""
echo "4. Verify deployment:"
echo "   ./verify-deployment.sh"
echo ""
echo "5. Deploy OTel to products:"
echo "   See DEPLOY_TO_REMOTE.md Step 4"
echo ""
