#!/bin/bash
#
# Repository Migration Script
# Migrates existing SEEFA-OM repo to new Observability PoC structure
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${REPO_ROOT}_backup_$(date +%Y%m%d_%H%M%S)"
DRY_RUN=${DRY_RUN:-false}

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Observability PoC - Repository Migration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${CYAN}Repository: $REPO_ROOT${NC}"
echo -e "${CYAN}Backup will be created at: $BACKUP_DIR${NC}"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to create directory
create_dir() {
    local dir="$1"
    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Would create: $dir"
    else
        mkdir -p "$dir"
        echo -e "${GREEN}✓${NC} Created: $dir"
    fi
}

# Function to create empty file
create_file() {
    local file="$1"
    local content="$2"
    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}[DRY-RUN]${NC} Would create: $file"
    else
        local dir=$(dirname "$file")
        mkdir -p "$dir"
        if [ -n "$content" ]; then
            echo "$content" > "$file"
        else
            touch "$file"
        fi
        echo -e "${GREEN}✓${NC} Created: $file"
    fi
}

# Function to move/rename directory
move_dir() {
    local src="$1"
    local dst="$2"
    if [ -d "$src" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${CYAN}[DRY-RUN]${NC} Would move: $src → $dst"
        else
            mkdir -p "$(dirname "$dst")"
            mv "$src" "$dst"
            echo -e "${GREEN}✓${NC} Moved: $src → $dst"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Source not found: $src"
    fi
}

# Function to copy file if exists
copy_file() {
    local src="$1"
    local dst="$2"
    if [ -f "$src" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${CYAN}[DRY-RUN]${NC} Would copy: $src → $dst"
        else
            mkdir -p "$(dirname "$dst")"
            cp "$src" "$dst"
            echo -e "${GREEN}✓${NC} Copied: $src → $dst"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Source not found: $src"
    fi
}

# Confirmation prompt
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Create a backup of your current repository"
echo "  2. Rename existing directories to match new structure"
echo "  3. Create new directories and placeholder files"
echo "  4. Preserve all existing code and configurations"
echo ""
echo -e "${RED}WARNING: This will modify your repository structure!${NC}"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

# ============================================
# STEP 1: Create Backup
# ============================================
print_section "Step 1: Creating Backup"

if [ "$DRY_RUN" = true ]; then
    echo -e "${CYAN}[DRY-RUN]${NC} Would create backup at: $BACKUP_DIR"
else
    echo "Creating full backup..."
    cp -r "$REPO_ROOT" "$BACKUP_DIR"
    echo -e "${GREEN}✓${NC} Backup created at: $BACKUP_DIR"
    echo "You can restore with: rm -rf $REPO_ROOT && mv $BACKUP_DIR $REPO_ROOT"
fi

cd "$REPO_ROOT"

# ============================================
# STEP 2: Rename/Move Existing Directories
# ============================================
print_section "Step 2: Migrating Existing Directories"

# Move correlation-engine to correlation-engine
move_dir "correlation-engine" "correlation-engine"

# Move otel-gateway to gateway
if [ -d "otel-gateway" ]; then
    move_dir "otel-gateway" "gateway/temp"
    if [ "$DRY_RUN" = false ]; then
        if [ -f "gateway/temp/config.yaml" ]; then
            mv "gateway/temp/config.yaml" "gateway/otel-config.yaml"
        fi
        rm -rf "gateway/temp"
        echo -e "${GREEN}✓${NC} Migrated otel-gateway config"
    fi
fi

# Move observability-stack if it exists under different name
if [ -d "observability" ]; then
    move_dir "observability" "observability-stack"
fi

# Move sense apps if they exist
if [ -d "apps" ]; then
    move_dir "apps" "sense-apps"
fi

# Move poller to archive (since it's deprecated)
if [ -d "poller" ]; then
    move_dir "poller" ".archive/poller_deprecated"
    echo -e "${YELLOW}⚠${NC} Poller moved to .archive (deprecated feature)"
fi

# ============================================
# STEP 3: Create New Directory Structure
# ============================================
print_section "Step 3: Creating New Directory Structure"

# Root directories
create_dir ".github/workflows"
create_dir "correlation-engine/app/pipeline"
create_dir "correlation-engine/app/routes"
create_dir "correlation-engine/tests"
create_dir "gateway"
create_dir "observability-stack/grafana/provisioning/datasources"
create_dir "observability-stack/grafana/provisioning/dashboards"
create_dir "observability-stack/prometheus"
create_dir "observability-stack/loki"
create_dir "observability-stack/tempo"
create_dir "sense-apps/beorn/common"
create_dir "sense-apps/palantir/common"
create_dir "sense-apps/arda/common"
create_dir "sense-apps/common"
create_dir "mdso-alloy/systemd"
create_dir "ops"
create_dir "scripts"
create_dir "dashboards"
create_dir "certs"
create_dir ".archive"

# ============================================
# STEP 4: Create Correlation Engine Files
# ============================================
print_section "Step 4: Creating Correlation Engine Files"

# App files
create_file "correlation-engine/app/__init__.py" ""
create_file "correlation-engine/app/main.py" "# FastAPI main application - see artifacts"
create_file "correlation-engine/app/config.py" "# Configuration settings - see artifacts"
create_file "correlation-engine/app/models.py" "# Pydantic models - see artifacts"

# Pipeline files
create_file "correlation-engine/app/pipeline/__init__.py" ""
create_file "correlation-engine/app/pipeline/normalizer.py" "# Log normalization - see artifacts"
create_file "correlation-engine/app/pipeline/correlator.py" "# Windowed correlation - see artifacts"
create_file "correlation-engine/app/pipeline/exporters.py" "# Multi-backend exporters - see artifacts"

# Routes files
create_file "correlation-engine/app/routes/__init__.py" ""
create_file "correlation-engine/app/routes/health.py" "# Health check endpoint - see artifacts"
create_file "correlation-engine/app/routes/logs.py" "# Logs ingestion - see artifacts"
create_file "correlation-engine/app/routes/otlp.py" "# OTLP ingestion - see artifacts"
create_file "correlation-engine/app/routes/correlations.py" "# Correlation queries - see artifacts"
create_file "correlation-engine/app/routes/auth.py" "# BasicAuth - see artifacts"

# Test files
create_file "correlation-engine/tests/__init__.py" ""
create_file "correlation-engine/tests/test_api.py" "# API tests"
create_file "correlation-engine/tests/test_pipeline.py" "# Pipeline tests"
create_file "correlation-engine/tests/test_exporters.py" "# Exporter tests"

# Config files
create_file "correlation-engine/Dockerfile" "# Multi-stage Dockerfile - see artifacts"
create_file "correlation-engine/requirements.txt" "# Python dependencies - see artifacts"
create_file "correlation-engine/.env.example" "# Environment template - see artifacts"
create_file "correlation-engine/docker-compose.yml" "# Standalone compose - see artifacts"
create_file "correlation-engine/README.md" "# Correlation Engine Documentation"
create_file "correlation-engine/.dockerignore" "*.pyc\n__pycache__\n.pytest_cache\n.env"
create_file "correlation-engine/pytest.ini" "[pytest]\ntestpaths = tests\npython_files = test_*.py"

# ============================================
# STEP 5: Create Gateway Files
# ============================================
print_section "Step 5: Creating Gateway Files"

create_file "gateway/otel-config.yaml" "# OTel Collector config - see artifacts"
create_file "gateway/Dockerfile" "FROM otel/opentelemetry-collector-contrib:0.96.0"
create_file "gateway/docker-compose.yml" "# Standalone compose - see artifacts"
create_file "gateway/README.md" "# OTel Gateway Documentation"

# ============================================
# STEP 6: Create Observability Stack Files
# ============================================
print_section "Step 6: Creating Observability Stack Files"

# Grafana
create_file "observability-stack/grafana/grafana.ini" "# Grafana config - see artifacts"
create_file "observability-stack/grafana/provisioning/datasources/datasources.yml" "# Datasources - see artifacts"
create_file "observability-stack/grafana/provisioning/dashboards/dashboards.yml" "# Dashboard provisioning"
create_file "observability-stack/grafana/provisioning/dashboards/correlation-overview.json" "# Dashboard JSON - see artifacts"

# Prometheus
create_file "observability-stack/prometheus/prometheus.yml" "# Prometheus config - see artifacts"

# Loki
create_file "observability-stack/loki/loki-config.yaml" "# Loki config - see artifacts"

# Tempo
create_file "observability-stack/tempo/tempo-config.yaml" "# Tempo config - see artifacts"

# Docker Compose
create_file "observability-stack/docker-compose.yml" "# Observability stack compose - see artifacts"
create_file "observability-stack/README.md" "# Observability Stack Documentation"

# ============================================
# STEP 7: Create Sense Apps Files
# ============================================
print_section "Step 7: Creating Sense Apps Files"

# Common OTel configuration (shared)
create_file "sense-apps/common/__init__.py" ""
create_file "sense-apps/common/otel_config.py" "# Shared OTel configuration - see artifacts"

# Beorn
create_file "sense-apps/beorn/common/__init__.py" ""
create_file "sense-apps/beorn/common/otel_config.py" "# Link to ../common/otel_config.py"
create_file "sense-apps/beorn/app.py" "# Beorn Flask app with OTel - see artifacts"
create_file "sense-apps/beorn/middleware.py" "# Flask middleware - see artifacts"
create_file "sense-apps/beorn/requirements.txt" "# Python dependencies"
create_file "sense-apps/beorn/Dockerfile" "# Multi-stage Dockerfile"
create_file "sense-apps/beorn/.env.example" "SERVICE_NAME=beorn\nSERVICE_PORT=5002"
create_file "sense-apps/beorn/README.md" "# Beorn - Authentication & Identity Service"

# Palantir
create_file "sense-apps/palantir/common/__init__.py" ""
create_file "sense-apps/palantir/common/otel_config.py" "# Link to ../common/otel_config.py"
create_file "sense-apps/palantir/app.py" "# Palantir Flask app with OTel - see artifacts"
create_file "sense-apps/palantir/middleware.py" "# Flask middleware - see artifacts"
create_file "sense-apps/palantir/requirements.txt" "# Python dependencies"
create_file "sense-apps/palantir/Dockerfile" "# Multi-stage Dockerfile"
create_file "sense-apps/palantir/.env.example" "SERVICE_NAME=palantir\nSERVICE_PORT=5003"
create_file "sense-apps/palantir/README.md" "# Palantir - Data Aggregation Service"

# Arda
create_file "sense-apps/arda/common/__init__.py" ""
create_file "sense-apps/arda/common/otel_config.py" "# Link to ../common/otel_config.py"
create_file "sense-apps/arda/app.py" "# Arda FastAPI app with OTel - see artifacts"
create_file "sense-apps/arda/requirements.txt" "# Python dependencies"
create_file "sense-apps/arda/Dockerfile" "# Multi-stage Dockerfile"
create_file "sense-apps/arda/.env.example" "SERVICE_NAME=arda\nSERVICE_PORT=5001"
create_file "sense-apps/arda/uvicorn_disable_logging.json" "# Uvicorn logging config"
create_file "sense-apps/arda/README.md" "# Arda - Inventory SEEFA Design Service"

# Sense apps compose
create_file "sense-apps/docker-compose.yml" "# Sense apps compose - see artifacts"
create_file "sense-apps/README.md" "# Sense Apps - OTel Instrumented Microservices"

# ============================================
# STEP 8: Create MDSO Alloy Files
# ============================================
print_section "Step 8: Creating MDSO Alloy Files"

create_file "mdso-alloy/config.alloy" "# Alloy configuration - see artifacts"
create_file "mdso-alloy/systemd/alloy.service" "# Systemd service - see artifacts"
create_file "mdso-alloy/install.sh" "#!/bin/bash\n# Alloy installation script - see artifacts"
create_file "mdso-alloy/README.md" "# Grafana Alloy Setup for MDSO Dev"

if [ "$DRY_RUN" = false ]; then
    chmod +x "mdso-alloy/install.sh"
fi

# ============================================
# STEP 9: Create Ops Files
# ============================================
print_section "Step 9: Creating Ops Files"

create_file "ops/runbook.md" "# Operations Runbook - see artifacts"
create_file "ops/health-checks.sh" "#!/bin/bash\n# Health check script - see artifacts"
create_file "ops/test-traffic.sh" "#!/bin/bash\n# Test traffic generator - see artifacts"
create_file "ops/stress-test.sh" "#!/bin/bash\n# Stress testing script"
create_file "ops/logrotate.conf" "# Logrotate configuration"

if [ "$DRY_RUN" = false ]; then
    chmod +x ops/*.sh 2>/dev/null || true
fi

# ============================================
# STEP 10: Create Scripts Files
# ============================================
print_section "Step 10: Creating Scripts Files"

create_file "scripts/bootstrap.sh" "#!/bin/bash\n# Bootstrap script"
create_file "scripts/setup-server-124.sh" "#!/bin/bash\n# Server-124 setup - see artifacts"
create_file "scripts/cleanup.sh" "#!/bin/bash\n# Cleanup script"
create_file "scripts/generate-certs.sh" "#!/bin/bash\n# mTLS cert generation"

if [ "$DRY_RUN" = false ]; then
    chmod +x scripts/*.sh
fi

# ============================================
# STEP 11: Create Root Files
# ============================================
print_section "Step 11: Creating Root Files"

create_file "docker-compose.yml" "# Root orchestrator - see artifacts"
create_file "Makefile" "# Make commands - see artifacts"
create_file ".env.example" "# Environment template - see artifacts"
create_file "README.md" "# Observability PoC Documentation - see artifacts"
create_file "LICENSE" "MIT License"
create_file ".gitignore" "# Python
__pycache__/
*.py[cod]
*\$py.class
*.so
.Python
.env
.venv
env/
venv/

# Docker
docker-compose.override.yml

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Backup
*.backup
_backup_*/

# Secrets
*.key
*.crt
*.pem
secrets/
"

# ============================================
# STEP 12: Create CI/CD Files
# ============================================
print_section "Step 12: Creating CI/CD Files"

create_file ".github/workflows/ci-cd.yml" "# CI/CD workflow - see artifacts"
create_file ".github/workflows/docker-publish.yml" "# Docker publish workflow"
create_file ".github/workflows/security-scan.yml" "# Security scanning workflow"
create_file ".github/CODEOWNERS" "# Code owners
* @your-team
/correlation-engine/ @sre-team
/observability-stack/ @sre-team
"
create_file ".github/pull_request_template.md" "## Description

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
"

# ============================================
# STEP 13: Copy/Update .env File
# ============================================
print_section "Step 13: Updating Environment Configuration"

# Backup existing .env if present
if [ -f ".env" ] && [ "$DRY_RUN" = false ]; then
    cp ".env" ".env.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓${NC} Backed up existing .env"
fi

echo -e "${YELLOW}⚠${NC} You need to manually update .env with the recommended structure"
echo "  See the provided .env structure in the artifacts"
echo "  Key changes needed:"
echo "    - Remove CORRELATION_API_AUTH_TOKEN"
echo "    - Remove all POLLER_* variables"
echo "    - Add CORR_WINDOW_SECONDS, MAX_BATCH_SIZE"
echo "    - Fix OTEL_EXPORTER_OTLP_ENDPOINT"
echo "    - Add ENABLE_BASIC_AUTH, DATADOG_API_KEY"

# ============================================
# STEP 14: Create Documentation Links
# ============================================
print_section "Step 14: Creating Documentation"

create_file "docs/architecture.md" "# Architecture Documentation"
create_file "docs/deployment.md" "# Deployment Guide"
create_file "docs/troubleshooting.md" "# Troubleshooting Guide"
create_file "docs/api.md" "# API Documentation"

# ============================================
# STEP 15: Archive Old Files
# ============================================
print_section "Step 15: Archiving Deprecated Files"

# Move deprecated files to archive
DEPRECATED_FILES=(
    "poller"
    "correlation_auth.py"
    "zip_poller.py"
)

for file in "${DEPRECATED_FILES[@]}"; do
    if [ -e "$file" ] && [ "$DRY_RUN" = false ]; then
        mv "$file" ".archive/" 2>/dev/null || true
        echo -e "${YELLOW}⚠${NC} Archived: $file"
    fi
done

# ============================================
# SUMMARY
# ============================================
print_section "Migration Complete!"

echo ""
echo -e "${GREEN}✓ Repository structure updated successfully!${NC}"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo "  - Backup created: $BACKUP_DIR"
echo "  - New directory structure created"
echo "  - Placeholder files generated"
echo "  - Deprecated features archived in .archive/"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "  1. Review the migration:"
echo "     ${CYAN}git status${NC}"
echo ""
echo "  2. Update .env with recommended structure:"
echo "     ${CYAN}vim .env${NC}"
echo "     (See provided .env structure in artifacts)"
echo ""
echo "  3. Copy artifact contents to placeholder files:"
echo "     ${CYAN}# For each file marked '# see artifacts', copy the content"
echo "     # from the Claude artifacts into the file${NC}"
echo ""
echo "  4. Test the new structure:"
echo "     ${CYAN}docker-compose config${NC}"
echo "     ${CYAN}make build${NC}"
echo ""
echo "  5. Commit changes:"
echo "     ${CYAN}git add .${NC}"
echo "     ${CYAN}git commit -m \"Migrate to observability PoC structure\"${NC}"
echo ""
echo -e "${GREEN}Migration script completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Pro Tip:${NC} Run with DRY_RUN=true first to preview changes:"
echo "  ${CYAN}DRY_RUN=true ./scripts/migrate-repo-structure.sh${NC}"
echo ""