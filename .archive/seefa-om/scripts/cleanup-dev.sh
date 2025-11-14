#!/bin/bash
# Full cleanup script for dev environment (DELETES ALL DATA)

set -e

echo "=========================================="
echo "  DEV ENVIRONMENT CLEANUP (DESTRUCTIVE)"
echo "=========================================="
echo ""
echo "This will:"
echo "  - Stop all containers"
echo "  - Remove all Docker volumes (logs, traces, metrics)"
echo "  - Stop MDSO poller"
echo "  - Remove MDSO log files"
echo "  - Stop Sense apps"
echo ""
read -p "Are you sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "Starting cleanup..."

# Stop Sense apps
echo "→ Stopping Sense apps..."
cd sense-apps 2>/dev/null && make stop-all 2>/dev/null || true
cd ..

# Stop MDSO poller
echo "→ Stopping MDSO poller..."
sudo systemctl stop mdso-poller 2>/dev/null || true

# Stop Correlation API
echo "→ Stopping Correlation API..."
cd correlation-engine && docker compose down 2>/dev/null || true
cd ..

# Stop OTel Gateway
echo "→ Stopping OTel Gateway..."
cd gateway && docker compose down 2>/dev/null || true
cd ..

# Stop Observability Stack
echo "→ Stopping Observability Stack..."
cd observability-stack && docker compose down 2>/dev/null || true
cd ..

# Remove Docker volumes
echo "→ Removing Docker volumes..."
docker volume rm observability-stack_grafana-data 2>/dev/null || true
docker volume rm observability-stack_loki-data 2>/dev/null || true
docker volume rm observability-stack_tempo-data 2>/dev/null || true
docker volume rm observability-stack_prometheus-data 2>/dev/null || true

# Remove MDSO logs
echo "→ Removing MDSO logs..."
sudo rm -rf /var/log/mdso/*.ndjson 2>/dev/null || true
sudo rm -f /var/log/mdso-poller.log 2>/dev/null || true

# Remove Sense app logs
echo "→ Removing Sense app logs..."
rm -rf sense-apps/*/logs 2>/dev/null || true
rm -f sense-apps/*/*.pid 2>/dev/null || true

# Prune Docker system (optional - commented by default)
# echo "→ Pruning Docker system..."
# docker system prune -f

echo ""
echo "=========================================="
echo "✓ Cleanup complete!"
echo "=========================================="
echo ""
echo "To restart the environment:"
echo "  1. make stack-up"
echo "  2. make gateway-up"
echo "  3. make corr-up"
echo "  4. make poller-start"
echo ""
echo "Or use: make start-all"