#!/bin/bash
#
# Simple Setup Script - Create New Directory Structure
# Run this in your existing seefa-om directory
#

set -e

echo "================================================"
echo "Creating New Observability PoC Structure"
echo "================================================"
echo ""

# Get the current directory
REPO_ROOT=$(pwd)
echo "Working in: $REPO_ROOT"
echo ""

# ============================================
# STEP 1: Rename Existing Directories
# ============================================
echo "Step 1: Renaming existing directories..."

# Rename correlation-engine to correlation-engine
if [ -d "correlation-engine" ]; then
    echo "  Renaming: correlation-engine → correlation-engine"
    mv correlation-engine correlation-engine
fi

# Rename otel-gateway to gateway
if [ -d "otel-gateway" ]; then
    echo "  Renaming: otel-gateway → gateway"
    mv otel-gateway gateway
fi

# Rename observability to observability-stack
if [ -d "observability" ]; then
    echo "  Renaming: observability → observability-stack"
    mv observability observability-stack
fi

# Rename apps to sense-apps
if [ -d "apps" ]; then
    echo "  Renaming: apps → sense-apps"
    mv apps sense-apps
fi

# Move poller to archive
if [ -d "poller" ]; then
    echo "  Archiving: poller → .archive/poller_deprecated"
    mkdir -p .archive
    mv poller .archive/poller_deprecated
fi

echo "✓ Done"
echo ""

# ============================================
# STEP 2: Create All New Directories
# ============================================
echo "Step 2: Creating new directories..."

# Create all directories at once
mkdir -p \
    .github/workflows \
    correlation-engine/app/pipeline \
    correlation-engine/app/routes \
    correlation-engine/tests \
    gateway \
    observability-stack/grafana/provisioning/datasources \
    observability-stack/grafana/provisioning/dashboards \
    observability-stack/prometheus \
    observability-stack/loki \
    observability-stack/tempo \
    sense-apps/beorn/common \
    sense-apps/palantir/common \
    sense-apps/arda/common \
    sense-apps/common \
    mdso-alloy/systemd \
    ops \
    scripts \
    dashboards \
    certs \
    docs \
    .archive

echo "✓ Created all directories"
echo ""

# ============================================
# STEP 3: Create All Files
# ============================================
echo "Step 3: Creating empty files..."

# Root files
touch .gitignore
touch .env.example
touch README.md
touch LICENSE
touch Makefile
touch docker-compose.yml

# Correlation Engine
touch correlation-engine/app/__init__.py
touch correlation-engine/app/main.py
touch correlation-engine/app/config.py
touch correlation-engine/app/models.py
touch correlation-engine/app/pipeline/__init__.py
touch correlation-engine/app/pipeline/normalizer.py
touch correlation-engine/app/pipeline/correlator.py
touch correlation-engine/app/pipeline/exporters.py
touch correlation-engine/app/routes/__init__.py
touch correlation-engine/app/routes/health.py
touch correlation-engine/app/routes/logs.py
touch correlation-engine/app/routes/otlp.py
touch correlation-engine/app/routes/correlations.py
touch correlation-engine/app/routes/auth.py
touch correlation-engine/tests/__init__.py
touch correlation-engine/tests/test_api.py
touch correlation-engine/tests/test_pipeline.py
touch correlation-engine/tests/test_exporters.py
touch correlation-engine/Dockerfile
touch correlation-engine/requirements.txt
touch correlation-engine/.env.example
touch correlation-engine/docker-compose.yml
touch correlation-engine/README.md
touch correlation-engine/.dockerignore
touch correlation-engine/pytest.ini

# Gateway
touch gateway/otel-config.yaml
touch gateway/Dockerfile
touch gateway/docker-compose.yml
touch gateway/README.md

# Observability Stack
touch observability-stack/grafana/grafana.ini
touch observability-stack/grafana/provisioning/datasources/datasources.yml
touch observability-stack/grafana/provisioning/dashboards/dashboards.yml
touch observability-stack/grafana/provisioning/dashboards/correlation-overview.json
touch observability-stack/prometheus/prometheus.yml
touch observability-stack/loki/loki-config.yaml
touch observability-stack/tempo/tempo-config.yaml
touch observability-stack/docker-compose.yml
touch observability-stack/README.md

# Sense Apps - Common
touch sense-apps/common/__init__.py
touch sense-apps/common/otel_config.py

# Sense Apps - Beorn
touch sense-apps/beorn/common/__init__.py
touch sense-apps/beorn/app.py
touch sense-apps/beorn/middleware.py
touch sense-apps/beorn/requirements.txt
touch sense-apps/beorn/Dockerfile
touch sense-apps/beorn/.env.example
touch sense-apps/beorn/README.md

# Sense Apps - Palantir
touch sense-apps/palantir/common/__init__.py
touch sense-apps/palantir/app.py
touch sense-apps/palantir/middleware.py
touch sense-apps/palantir/requirements.txt
touch sense-apps/palantir/Dockerfile
touch sense-apps/palantir/.env.example
touch sense-apps/palantir/README.md

# Sense Apps - Arda
touch sense-apps/arda/common/__init__.py
touch sense-apps/arda/app.py
touch sense-apps/arda/requirements.txt
touch sense-apps/arda/Dockerfile
touch sense-apps/arda/.env.example
touch sense-apps/arda/uvicorn_disable_logging.json
touch sense-apps/arda/README.md

# Sense Apps compose
touch sense-apps/docker-compose.yml
touch sense-apps/README.md

# MDSO Alloy
touch mdso-alloy/config.alloy
touch mdso-alloy/systemd/alloy.service
touch mdso-alloy/install.sh
touch mdso-alloy/README.md

# Ops
touch ops/runbook.md
touch ops/health-checks.sh
touch ops/test-traffic.sh
touch ops/stress-test.sh
touch ops/logrotate.conf

# Scripts
touch scripts/bootstrap.sh
touch scripts/setup-server-124.sh
touch scripts/cleanup.sh
touch scripts/generate-certs.sh

# CI/CD
touch .github/workflows/ci-cd.yml
touch .github/workflows/docker-publish.yml
touch .github/workflows/security-scan.yml
touch .github/CODEOWNERS
touch .github/pull_request_template.md

# Docs
touch docs/architecture.md
touch docs/deployment.md
touch docs/troubleshooting.md
touch docs/api.md

# Dashboards
touch dashboards/correlation-overview.json

echo "✓ Created all files"
echo ""

# ============================================
# STEP 4: Make Scripts Executable
# ============================================
echo "Step 4: Making scripts executable..."

chmod +x scripts/*.sh 2>/dev/null || true
chmod +x ops/*.sh 2>/dev/null || true
chmod +x mdso-alloy/install.sh 2>/dev/null || true

echo "✓ Done"
echo ""

# ============================================
# STEP 5: Create symlinks for shared files
# ============================================
echo "Step 5: Creating symlinks for shared OTel config..."

# Create symlinks in beorn, palantir, arda to use the common otel_config.py
cd sense-apps/beorn/common
ln -sf ../../common/otel_config.py otel_config.py 2>/dev/null || true
cd ../../..

cd sense-apps/palantir/common
ln -sf ../../common/otel_config.py otel_config.py 2>/dev/null || true
cd ../../..

cd sense-apps/arda/common
ln -sf ../../common/otel_config.py otel_config.py 2>/dev/null || true
cd ../../..

echo "✓ Done"
echo ""

# ============================================
# Summary
# ============================================
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Directory structure created at: $REPO_ROOT"
echo ""
echo "Summary:"
echo "  - Renamed existing directories"
echo "  - Created all new directories"
echo "  - Created 80+ empty files"
echo "  - Made scripts executable"
echo "  - Created symlinks for shared configs"
echo ""
echo "Next Steps:"
echo "  1. Copy content from Claude artifacts into the files"
echo "  2. Update .env with your configuration"
echo "  3. Run: docker-compose config"
echo "  4. Run: make build"
echo ""
echo "File Structure:"
find . -maxdepth 2 -type d | sort
echo ""
echo "Total files created:"
find . -type f | wc -l
echo ""
