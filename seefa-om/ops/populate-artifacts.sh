#!/bin/bash
#
# Populate Artifacts Script
# Helper script to guide you through copying artifact content to files
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Artifact Population Guide${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$REPO_ROOT"

# Define all artifact files and their Claude artifact IDs
declare -A ARTIFACTS=(
    # Root files
    ["docker-compose.yml"]="root_docker_compose"
    ["Makefile"]="root_makefile"
    [".env.example"]="env_example"
    ["README.md"]="root_readme"

    # Correlation Engine
    ["correlation-engine/app/main.py"]="correlation_engine_main"
    ["correlation-engine/app/config.py"]="correlation_engine_config"
    ["correlation-engine/app/models.py"]="correlation_engine_models"
    ["correlation-engine/app/routes/health.py"]="correlation_routes_health"
    ["correlation-engine/app/routes/logs.py"]="correlation_routes_logs"
    ["correlation-engine/app/routes/otlp.py"]="correlation_routes_otlp"
    ["correlation-engine/app/routes/correlations.py"]="correlation_routes_correlations"
    ["correlation-engine/app/routes/auth.py"]="correlation_routes_auth"
    ["correlation-engine/app/pipeline/normalizer.py"]="correlation_pipeline_normalizer"
    ["correlation-engine/app/pipeline/correlator.py"]="correlation_pipeline_correlator"
    ["correlation-engine/app/pipeline/exporters.py"]="correlation_pipeline_exporters"
    ["correlation-engine/Dockerfile"]="correlation_engine_dockerfile"
    ["correlation-engine/requirements.txt"]="correlation_requirements"

    # Gateway
    ["gateway/otel-config.yaml"]="gateway_otel_config"

    # Observability Stack
    ["observability-stack/loki/loki-config.yaml"]="loki_config"
    ["observability-stack/tempo/tempo-config.yaml"]="tempo_config"
    ["observability-stack/prometheus/prometheus.yml"]="prometheus_config"
    ["observability-stack/grafana/provisioning/datasources/datasources.yml"]="grafana_datasources"

    # MDSO Alloy
    ["mdso-alloy/config.alloy"]="mdso_alloy_config"
    ["mdso-alloy/install.sh"]="setup_mdso_alloy_script"

    # Sense Apps
    ["sense-apps/common/otel_config.py"]="sense_otel_common"
    ["sense-apps/beorn/app.py"]="beorn_refactored"
    ["sense-apps/palantir/app.py"]="palantir_refactored"
    ["sense-apps/arda/app.py"]="arda_refactored"

    # Scripts
    ["scripts/setup-server-124.sh"]="setup_server_124_script"

    # Ops
    ["ops/runbook.md"]="ops_runbook"
    ["ops/test-traffic.sh"]="test_traffic_script"

    # CI/CD
    [".github/workflows/ci-cd.yml"]="github_ci_workflow"
)

# Function to check if file needs content
needs_content() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return 0  # File doesn't exist, needs content
    fi

    local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    if [ "$size" -lt 100 ]; then
        return 0  # File is too small (likely placeholder)
    fi

    if grep -q "see artifacts" "$file" 2>/dev/null; then
        return 0  # File explicitly references artifacts
    fi

    return 1  # File looks complete
}

# Function to show file info
show_file_info() {
    local file="$1"
    local artifact_id="$2"

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}File: ${file}${NC}"
    echo -e "${YELLOW}Artifact ID: ${artifact_id}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -f "$file" ]; then
        local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        echo -e "Current size: ${size} bytes"
        if [ "$size" -lt 100 ]; then
            echo -e "${RED}Status: NEEDS CONTENT (placeholder file)${NC}"
        else
            echo -e "${GREEN}Status: Has content (may still need update)${NC}"
        fi
    else
        echo -e "${RED}Status: FILE MISSING${NC}"
    fi
}

# Count files that need content
total_files=0
files_needing_content=0

for file in "${!ARTIFACTS[@]}"; do
    total_files=$((total_files + 1))
    if needs_content "$file"; then
        files_needing_content=$((files_needing_content + 1))
    fi
done

echo -e "${CYAN}Repository Status:${NC}"
echo "  Total artifact files: $total_files"
echo "  Files needing content: $files_needing_content"
echo "  Files with content: $((total_files - files_needing_content))"
echo ""

if [ $files_needing_content -eq 0 ]; then
    echo -e "${GREEN}✓ All artifact files appear to have content!${NC}"
    exit 0
fi

# Menu options
echo -e "${YELLOW}What would you like to do?${NC}"
echo ""
echo "  1. Show all files needing content"
echo "  2. Show checklist by category"
echo "  3. Generate copy-paste commands"
echo "  4. Interactive file-by-file guide"
echo "  5. Exit"
echo ""
read -p "Choose option (1-5): " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}Files Needing Content:${NC}"
        echo ""
        for file in "${!ARTIFACTS[@]}"; do
            if needs_content "$file"; then
                echo "  • $file"
            fi
        done | sort
        ;;

    2)
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}Artifact Population Checklist${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        # Root files
        echo -e "${CYAN}Root Configuration Files:${NC}"
        for file in docker-compose.yml Makefile .env.example README.md; do
            if needs_content "$file"; then
                echo "  [ ] $file"
            else
                echo "  [✓] $file"
            fi
        done
        echo ""

        # Correlation Engine
        echo -e "${CYAN}Correlation Engine:${NC}"
        for file in correlation-engine/app/*.py correlation-engine/app/*/*.py correlation-engine/Dockerfile correlation-engine/requirements.txt; do
            if [ -f "$file" ] || [[ "$file" == *"*"* ]]; then
                for f in $file; do
                    if [ -f "$f" ]; then
                        if needs_content "$f"; then
                            echo "  [ ] $f"
                        else
                            echo "  [✓] $f"
                        fi
                    fi
                done
            fi
        done
        echo ""

        # Gateway
        echo -e "${CYAN}OTel Gateway:${NC}"
        for file in gateway/otel-config.yaml; do
            if needs_content "$file"; then
                echo "  [ ] $file"
            else
                echo "  [✓] $file"
            fi
        done
        echo ""

        # Observability Stack
        echo -e "${CYAN}Observability Stack:${NC}"
        for file in observability-stack/*/*; do
            if [ -f "$file" ]; then
                if needs_content "$file"; then
                    echo "  [ ] $file"
                else
                    echo "  [✓] $file"
                fi
            fi
        done
        echo ""

        # Sense Apps
        echo -e "${CYAN}Sense Apps:${NC}"
        for file in sense-apps/*/app.py sense-apps/common/otel_config.py; do
            if [ -f "$file" ]; then
                if needs_content "$file"; then
                    echo "  [ ] $file"
                else
                    echo "  [✓] $file"
                fi
            fi
        done
        echo ""

        # Scripts & Ops
        echo -e "${CYAN}Scripts & Ops:${NC}"
        for file in scripts/*.sh ops/*.sh ops/*.md; do
            if [ -f "$file" ]; then
                if needs_content "$file"; then
                    echo "  [ ] $file"
                else
                    echo "  [✓] $file"
                fi
            fi
        done
        echo ""
        ;;

    3)
        echo ""
        echo -e "${BLUE}Copy-Paste Guide:${NC}"
        echo ""
        echo "For each file, open the Claude conversation and:"
        echo "  1. Find the artifact with the matching ID"
        echo "  2. Copy the artifact content"
        echo "  3. Paste into the file"
        echo ""
        echo -e "${YELLOW}Commands to edit files:${NC}"
        echo ""

        for file in "${!ARTIFACTS[@]}"; do
            if needs_content "$file"; then
                artifact_id="${ARTIFACTS[$file]}"
                echo "# Edit: $file (Artifact: $artifact_id)"
                echo "vim $file"
                echo ""
            fi
        done | sort
        ;;

    4)
        echo ""
        echo -e "${BLUE}Interactive Guide - File by File${NC}"
        echo ""

        count=0
        for file in $(echo "${!ARTIFACTS[@]}" | tr ' ' '\n' | sort); do
            if needs_content "$file"; then
                count=$((count + 1))
                artifact_id="${ARTIFACTS[$file]}"

                show_file_info "$file" "$artifact_id"

                echo ""
                echo "Actions:"
                echo "  e - Edit this file now"
                echo "  s - Skip to next"
                echo "  d - Mark as done (already populated)"
                echo "  q - Quit"
                echo ""
                read -p "Action (e/s/d/q): " -n 1 action
                echo ""

                case $action in
                    e|E)
                        ${EDITOR:-vim} "$file"
                        echo -e "${GREEN}✓ File edited${NC}"
                        ;;
                    d|D)
                        echo -e "${GREEN}✓ Marked as done${NC}"
                        ;;
                    q|Q)
                        echo "Exiting..."
                        exit 0
                        ;;
                    *)
                        echo "Skipping..."
                        ;;
                esac

                echo ""
            fi
        done

        if [ $count -eq 0 ]; then
            echo -e "${GREEN}✓ All files have content!${NC}"
        else
            echo -e "${YELLOW}Processed $count files${NC}"
        fi
        ;;

    5)
        echo "Exiting..."
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Artifact Population Guide Complete${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Remember:${NC}"
echo "  • All artifact content is in the Claude conversation"
echo "  • Look for artifact IDs that match the file you're editing"
echo "  • Each artifact has complete, ready-to-use code"
echo "  • Don't forget to make scripts executable: chmod +x scripts/*.sh ops/*.sh"
echo ""
echo -e "${YELLOW}After populating all files:${NC}"
echo "  1. Update .env with recommended structure"
echo "  2. Run: docker-compose config"
echo "  3. Run: make build"
echo "  4. Run: make up"
echo "  5. Run: make health"
echo ""
