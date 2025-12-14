#!/bin/bash
# Sanitize all sensitive data for demo branch
# Blueprint Feature 7: Public Demo Branch Setup

set -e

echo "================================================================"
echo "  Demo Data Sanitization Script"
echo "  Blueprint Feature 7: Public Demo Branch"
echo "================================================================"
echo ""
echo "⚠️  WARNING: This script will modify files to remove proprietary data."
echo "    Only run this on the demo branch, NOT on main/production branches!"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Starting sanitization..."
echo ""

# Track changes
TOTAL_FILES_MODIFIED=0

# ===== 1. REMOVE SENSITIVE FILES =====
echo "[1/7] Removing sensitive files..."

if [ -d "seefa-om/ops/secrets/" ]; then
    rm -rf seefa-om/ops/secrets/
    echo "  ✓ Removed secrets directory"
fi

if [ -f "seefa-om/.env.prod" ]; then
    rm seefa-om/.env.prod
    echo "  ✓ Removed .env.prod"
fi

if [ -f "seefa-om/correlation-engine/.env" ]; then
    rm seefa-om/correlation-engine/.env
    echo "  ✓ Removed correlation-engine .env"
fi

# Remove any .pem, .key, .crt files
find . -type f \( -name "*.pem" -o -name "*.key" -o -name "*.crt" \) -delete 2>/dev/null || true
echo "  ✓ Removed certificate/key files"

echo ""

# ===== 2. SANITIZE CIRCUIT IDs =====
echo "[2/7] Sanitizing circuit IDs..."

# Real circuit ID pattern: XX.L1XX.XXXXXX..XXXX
# Replace with: DEMO.CIRCUIT.XXX..MOCK
CIRCUIT_COUNT=$(find . -type f -name "*.py" -exec grep -l '[0-9]\{2\}\.L[0-9]XX\.[0-9]\{6\}\.\.[A-Z]\{4\}' {} \; 2>/dev/null | wc -l)

if [ "$CIRCUIT_COUNT" -gt 0 ]; then
    find . -type f -name "*.py" -exec sed -i 's/[0-9]\{2\}\.L[0-9]XX\.[0-9]\{6\}\.\.[A-Z]\{4\}/DEMO.CIRCUIT.XXX..MOCK/g' {} \;
    echo "  ✓ Sanitized circuit IDs in $CIRCUIT_COUNT Python files"
    TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + CIRCUIT_COUNT))
fi

echo ""

# ===== 3. SANITIZE HOSTNAMES & IPS =====
echo "[3/7] Sanitizing hostnames and IP addresses..."

# Specific internal IPs and hostnames from the codebase
HOSTNAMES_TO_REPLACE=(
    "159.56.4.94:demo.example.com"
    "austx-mdso-logs-02.chtrse.com:demo.example.com"
    "austx-mdso-logs-01.chtrse.com:demo-backup.example.com"
)

for HOSTNAME_PAIR in "${HOSTNAMES_TO_REPLACE[@]}"; do
    OLD_HOST=$(echo "$HOSTNAME_PAIR" | cut -d: -f1)
    NEW_HOST=$(echo "$HOSTNAME_PAIR" | cut -d: -f2)

    # Python files
    PY_COUNT=$(find . -type f -name "*.py" -exec grep -l "$OLD_HOST" {} \; 2>/dev/null | wc -l)
    if [ "$PY_COUNT" -gt 0 ]; then
        find . -type f -name "*.py" -exec sed -i "s/$OLD_HOST/$NEW_HOST/g" {} \;
        echo "  ✓ Replaced $OLD_HOST with $NEW_HOST in $PY_COUNT Python files"
        TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + PY_COUNT))
    fi

    # Markdown files
    MD_COUNT=$(find . -type f -name "*.md" -exec grep -l "$OLD_HOST" {} \; 2>/dev/null | wc -l)
    if [ "$MD_COUNT" -gt 0 ]; then
        find . -type f -name "*.md" -exec sed -i "s/$OLD_HOST/$NEW_HOST/g" {} \;
        echo "  ✓ Replaced $OLD_HOST with $NEW_HOST in $MD_COUNT Markdown files"
        TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + MD_COUNT))
    fi

    # YAML files
    YAML_COUNT=$(find . -type f \( -name "*.yml" -o -name "*.yaml" \) -exec grep -l "$OLD_HOST" {} \; 2>/dev/null | wc -l)
    if [ "$YAML_COUNT" -gt 0 ]; then
        find . -type f \( -name "*.yml" -o -name "*.yaml" \) -exec sed -i "s/$OLD_HOST/$NEW_HOST/g" {} \;
        echo "  ✓ Replaced $OLD_HOST with $NEW_HOST in $YAML_COUNT YAML files"
        TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + YAML_COUNT))
    fi
done

echo ""

# ===== 4. SANITIZE COMPANY NAMES =====
echo "[4/7] Sanitizing company names..."

COMPANY_REPLACEMENTS=(
    "Charter:DemoTelco"
    "Spectrum:DemoNet"
    "Chtr:Demo"
    "CHTR:DEMO"
)

for COMPANY_PAIR in "${COMPANY_REPLACEMENTS[@]}"; do
    OLD_NAME=$(echo "$COMPANY_PAIR" | cut -d: -f1)
    NEW_NAME=$(echo "$COMPANY_PAIR" | cut -d: -f2)

    COMPANY_COUNT=$(find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" \) -exec grep -l "$OLD_NAME" {} \; 2>/dev/null | wc -l)
    if [ "$COMPANY_COUNT" -gt 0 ]; then
        find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" \) -exec sed -i "s/$OLD_NAME/$NEW_NAME/g" {} \;
        echo "  ✓ Replaced $OLD_NAME with $NEW_NAME in $COMPANY_COUNT files"
        TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + COMPANY_COUNT))
    fi
done

echo ""

# ===== 5. SANITIZE DEVICE NAMES =====
echo "[5/7] Sanitizing device names..."

# Replace specific device naming patterns
DEVICE_PATTERNS=(
    "ciena-saos-[0-9]\{2\}\.chtrse\.com:ciena-saos-demo-\\1.demo.com"
    "cisco-ios-[0-9]\{2\}\.chtrse\.com:cisco-ios-demo-\\1.demo.com"
    "juniper-mx-[0-9]\{2\}\.chtrse\.com:juniper-mx-demo-\\1.demo.com"
)

DEVICE_COUNT=0
for PATTERN_PAIR in "${DEVICE_PATTERNS[@]}"; do
    OLD_PATTERN=$(echo "$PATTERN_PAIR" | cut -d: -f1)
    NEW_PATTERN=$(echo "$PATTERN_PAIR" | cut -d: -f2)

    FILES_WITH_PATTERN=$(find . -type f -name "*.py" -exec grep -l "$OLD_PATTERN" {} \; 2>/dev/null | wc -l)
    if [ "$FILES_WITH_PATTERN" -gt 0 ]; then
        find . -type f -name "*.py" -exec sed -i "s/$OLD_PATTERN/$NEW_PATTERN/g" {} \;
        DEVICE_COUNT=$((DEVICE_COUNT + FILES_WITH_PATTERN))
    fi
done

if [ "$DEVICE_COUNT" -gt 0 ]; then
    echo "  ✓ Sanitized device names in $DEVICE_COUNT files"
    TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + DEVICE_COUNT))
else
    echo "  ✓ No device names found to sanitize"
fi

echo ""

# ===== 6. SANITIZE EMAIL ADDRESSES =====
echo "[6/7] Sanitizing email addresses..."

# Replace real email domains
EMAIL_COUNT=$(find . -type f \( -name "*.py" -o -name "*.md" \) -exec grep -l '@charter\.com\|@spectrum\.com' {} \; 2>/dev/null | wc -l)

if [ "$EMAIL_COUNT" -gt 0 ]; then
    find . -type f \( -name "*.py" -o -name "*.md" \) -exec sed -i 's/@charter\.com/@demo.example.com/g' {} \;
    find . -type f \( -name "*.py" -o -name "*.md" \) -exec sed -i 's/@spectrum\.com/@demo.example.com/g' {} \;
    echo "  ✓ Sanitized email addresses in $EMAIL_COUNT files"
    TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + EMAIL_COUNT))
else
    echo "  ✓ No email addresses found to sanitize"
fi

echo ""

# ===== 7. CREATE DEMO README =====
echo "[7/7] Creating demo README..."

cat > README.md << 'EOF'
# Correlation Station Demo

**Public demonstration** of observability correlation engine for telecom service orchestration.

**⚠️ DEMO ONLY:** This branch uses mocked dependencies and sanitized data. Not for production use.

## Features

- **OpenTelemetry Instrumentation** for microservices (ARDA, BEORN, PALANTIR)
- **Distributed Tracing Correlation** across service boundaries
- **Redis Caching** for high-throughput telemetry data
- **SECA Review Automation** with AI-assisted debugging prompts
- **Learning Portal** with progress tracking for NetDev101 tutorials
- **Grafana Stack** (Loki, Tempo, Prometheus) for observability

## Architecture

```
Sense Apps (ARDA, BEORN, PALANTIR)
    ↓ (OpenTelemetry)
Correlation Gateway
    ↓
Correlation Engine + Redis
    ↓
Grafana Stack (Loki, Tempo, Prometheus)
```

## Quick Start

### Deploy to AWS EKS (Demo)

```bash
# Deploy using GitHub Actions
kubectl apply -f k8s/demo/

# Verify deployment
kubectl get pods -n demo
kubectl get svc -n demo
```

### Run Locally with Docker Compose

```bash
# Set demo mode
export DEMO_MODE=true

# Start services
docker-compose -f docker-compose.demo.yml up -d

# Check health
curl http://localhost:8080/health
```

## Demo Mode

When `DEMO_MODE=true` is set, all external dependencies are mocked with realistic responses:

- **IP Control (IPAM):** 25 IP allocation response variants
- **Granite (CMDB):** 25 circuit creation response variants
- **Kong (API Gateway):** 25 authentication response variants
- **MDSO (Orchestrator):** 30 RA telemetry response variants
- **TACACS+:** 25 device authentication variants
- **SNMP:** 30 device polling variants

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Testing Guide](seefa-om/docs/TESTING_GUIDE.md)
- [Demo Branch Setup](seefa-om/docs/DEMO_BRANCH_GUIDE.md)
- [Metrics Cardinality Guide](seefa-om/docs/METRICS_CARDINALITY_GUIDE.md)

## Technology Stack

- **Backend:** Python (FastAPI), SQLite
- **Frontend:** Next.js, React, TailwindCSS
- **Observability:** OpenTelemetry, Grafana Alloy, Loki, Tempo, Prometheus
- **Caching:** Redis
- **Orchestration:** Kubernetes (AWS EKS)
- **CI/CD:** GitHub Actions

## License

Demo only - not for production use.
EOF

echo "  ✓ Created demo README.md"

echo ""
echo "================================================================"
echo "  Sanitization Complete!"
echo "================================================================"
echo ""
echo "Summary:"
echo "  - Removed sensitive files (secrets, .env, certificates)"
echo "  - Sanitized circuit IDs"
echo "  - Replaced $TOTAL_FILES_MODIFIED files with sanitized data"
echo "  - Created demo README"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Test demo mode: export DEMO_MODE=true && python -m pytest"
echo "  3. Commit changes: git add . && git commit -m 'chore: Sanitize data for demo branch'"
echo "  4. Push demo branch: git push -u origin demo"
echo ""
echo "✓ Ready for public demo deployment!"
