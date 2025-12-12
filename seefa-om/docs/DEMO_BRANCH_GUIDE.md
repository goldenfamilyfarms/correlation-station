# Demo Branch Setup Guide

**Blueprint Feature 7:** Public Demo Branch with Sanitized Data & Mocked Dependencies

---

## Objective

Create a public-facing demo deployment that:
1. **Sanitizes all proprietary information** (no Charter/Spectrum data)
2. **Mocks all external dependencies** with hardcoded JSON responses
3. **Deploys to AWS EKS** via GitHub Actions
4. **Showcases functionality** without exposing internal systems

---

## Architecture

```
GitHub Repo (public demo branch)
    ↓
GitHub Actions CI/CD
    ↓
AWS ECR (Docker images)
    ↓
AWS EKS (Kubernetes cluster)
    ├─ sense-demo-apps (ARDA, BEORN, PALANTIR with mocks)
    ├─ correlation-engine-demo
    ├─ correlation-gateway-demo
    ├─ redis-demo
    └─ grafana-stack-demo (reduced footprint)
```

---

## Step 1: Create Demo Branch

```bash
# Create demo branch from main
git checkout -b demo
git push -u origin demo

# Remove sensitive files
rm -rf seefa-om/ops/secrets/
rm seefa-om/.env.prod
rm seefa-om/correlation-engine/.env

# Update README for demo
cat > README.md << 'EOF'
# Correlation Station Demo

**Public demonstration** of observability correlation engine for telecom service orchestration.

**⚠️ DEMO ONLY:** This branch uses mocked dependencies and sanitized data. Not for production use.

## Features
- OpenTelemetry instrumentation for microservices
- Distributed tracing correlation
- Redis caching for high-throughput telemetry
- SECA review automation
- Grafana dashboards

## Quick Start
```bash
# Deploy to AWS EKS
kubectl apply -f k8s/demo/
```

## Documentation
See [docs/](docs/) for architecture, setup, and usage guides.
EOF

git add README.md
git commit -m "docs: Update README for demo branch"
```

---

## Step 2: Create Mock Client Library

**File:** `seefa-om/shared-libs/demo_mocks/external_clients.py`

```python
"""
Mock clients for external dependencies

Blueprint Feature 7: Demo branch with mocked responses
Provides 20-30 hardcoded JSON variants per dependency
"""
import random
from typing import Dict, Any, List


class MockIPControlClient:
    """Mock IP Control (IPAM) client"""

    RESPONSES = [
        # Successful IP allocation
        {
            "status": "success",
            "allocated_ips": ["10.100.1.10", "10.100.1.11"],
            "subnet": "10.100.1.0/24",
            "vlan": 100,
            "dns_records": ["circuit-001.example.com"]
        },
        # IP pool exhaustion
        {
            "status": "error",
            "error": "No available IPs in pool",
            "subnet": "10.100.2.0/24"
        },
        # Successful IPv6 allocation
        {
            "status": "success",
            "allocated_ips": ["2001:db8:100::10", "2001:db8:100::11"],
            "subnet": "2001:db8:100::/64",
            "vlan": 200
        },
        # ... (add 17 more variants)
    ]

    def allocate_ips(self, circuit_id: str, count: int = 2) -> Dict:
        """Allocate IP addresses (mocked)"""
        return random.choice(self.RESPONSES)


class MockGraniteClient:
    """Mock Granite (CMDB) client"""

    RESPONSES = [
        # Successful circuit creation
        {
            "status": "success",
            "circuit_id": "DEMO.CIRCUIT.001..MOCK",
            "product_id": "prod-12345",
            "device_a": "router-a.example.com",
            "device_z": "router-z.example.com",
            "bandwidth": "10G"
        },
        # Circuit already exists
        {
            "status": "error",
            "error": "Circuit already exists",
            "existing_circuit_id": "DEMO.CIRCUIT.002..MOCK"
        },
        # Device not found
        {
            "status": "error",
            "error": "Device not found in CMDB",
            "device": "router-invalid.example.com"
        },
        # ... (add 17 more variants)
    ]

    def create_circuit(self, circuit_data: Dict) -> Dict:
        """Create circuit in CMDB (mocked)"""
        return random.choice(self.RESPONSES)


class MockKongClient:
    """Mock Kong (API Gateway) client"""

    RESPONSES = [
        # Successful auth
        {
            "status": "success",
            "authenticated": True,
            "user": "demo-user",
            "permissions": ["read", "write"]
        },
        # Invalid credentials
        {
            "status": "error",
            "authenticated": False,
            "error": "Invalid credentials"
        },
        # ... (add 18 more variants)
    ]

    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate user (mocked)"""
        return random.choice(self.RESPONSES)


class MockMDSOClient:
    """Mock MDSO (orchestrator) client"""

    # 30 different RA telemetry configurations
    RA_TELEMETRY_RESPONSES = [
        {
            "status": "success",
            "operation": "provision_eline",
            "device": "ciena-saos-01.example.com",
            "commands_executed": 15,
            "elapsed_time_ms": 3500,
            "telemetry": {
                "pre_check": "PASSED",
                "config_applied": True,
                "post_check": "PASSED"
            }
        },
        {
            "status": "error",
            "operation": "provision_eline",
            "device": "ciena-saos-02.example.com",
            "error": "Device timeout after 30s",
            "commands_executed": 5,
            "elapsed_time_ms": 30000
        },
        # ... (add 28 more variants)
    ]

    def execute_scriptplan(self, plan_name: str, params: Dict) -> Dict:
        """Execute MDSO ScriptPlan (mocked)"""
        return random.choice(self.RA_TELEMETRY_RESPONSES)


class MockTACACSClient:
    """Mock TACACS+ authentication client"""

    RESPONSES = [
        {"status": "success", "authenticated": True},
        {"status": "error", "authenticated": False, "error": "Invalid password"},
        {"status": "error", "authenticated": False, "error": "User not found"},
        # ... (add 17 more variants)
    ]

    def authenticate_device(self, device: str, username: str, password: str) -> Dict:
        """Authenticate device access (mocked)"""
        return random.choice(self.RESPONSES)


class MockSNMPClient:
    """Mock SNMP client for device polling"""

    RESPONSES = [
        # Router metrics
        {
            "device": "router-a.example.com",
            "uptime": "45 days, 12:30:00",
            "cpu_usage": 35.2,
            "memory_usage": 62.5,
            "interfaces": [
                {"name": "GigabitEthernet0/0/0", "status": "up", "speed": "1000Mbps"},
                {"name": "GigabitEthernet0/0/1", "status": "down", "speed": "1000Mbps"}
            ]
        },
        # Switch metrics
        {
            "device": "switch-b.example.com",
            "uptime": "120 days, 05:15:22",
            "cpu_usage": 12.8,
            "memory_usage": 45.1,
            "interfaces": [
                {"name": "Port1", "status": "up", "speed": "10000Mbps"},
                {"name": "Port2", "status": "up", "speed": "10000Mbps"}
            ]
        },
        # ... (add 18 more variants)
    ]

    def poll_device(self, device: str) -> Dict:
        """Poll device via SNMP (mocked)"""
        return random.choice(self.RESPONSES)


# Factory function to get mock clients
def get_mock_client(client_type: str):
    """Get mock client instance"""
    clients = {
        "ip_control": MockIPControlClient,
        "granite": MockGraniteClient,
        "kong": MockKongClient,
        "mdso": MockMDSOClient,
        "tacacs": MockTACACSClient,
        "snmp": MockSNMPClient
    }

    if client_type not in clients:
        raise ValueError(f"Unknown client type: {client_type}")

    return clients[client_type]()
```

---

## Step 3: Update Sense Apps to Use Mocks

**File:** `seefa-om/sense-apps/arda/arda_app/config_demo.py`

```python
"""Demo configuration with mocked dependencies"""
import os
from demo_mocks.external_clients import get_mock_client

# Feature flag for demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Mock clients (used when DEMO_MODE=true)
if DEMO_MODE:
    ip_control_client = get_mock_client("ip_control")
    granite_client = get_mock_client("granite")
    kong_client = get_mock_client("kong")
else:
    # Real clients (production)
    from arda_app.clients import IPControlClient, GraniteClient, KongClient
    ip_control_client = IPControlClient()
    granite_client = GraniteClient()
    kong_client = KongClient()
```

**Update ARDA routes:**
```python
# arda_app/api/v1/circuit.py
from arda_app.config_demo import ip_control_client, granite_client

@router.post("/api/v1/circuit")
def create_circuit(circuit_data: CircuitCreateRequest):
    """Create circuit (uses mock client in demo mode)"""
    # Allocate IPs (mocked in demo)
    ip_allocation = ip_control_client.allocate_ips(circuit_data.circuit_id)

    # Create circuit in CMDB (mocked in demo)
    circuit = granite_client.create_circuit(circuit_data.dict())

    return {"circuit_id": circuit["circuit_id"], "status": circuit["status"]}
```

---

## Step 4: Sanitize Data

**Script:** `scripts/sanitize_demo_data.sh`

```bash
#!/bin/bash
# Sanitize all sensitive data for demo branch

set -e

echo "Sanitizing demo data..."

# Remove real customer circuit IDs
find . -type f -name "*.py" -exec sed -i 's/[0-9]\{2\}\.L[0-9]XX\.[0-9]\{6\}\.\.[A-Z]\{4\}/DEMO.CIRCUIT.XXX..MOCK/g' {} \;

# Remove real hostnames
find . -type f -name "*.py" -exec sed -i 's/159\.56\.4\.94/demo.example.com/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/austx-mdso-logs-02\.chtrse\.com/demo.example.com/g' {} \;

# Remove internal URLs
find . -type f -name "*.md" -exec sed -i 's/http:\/\/159\.56\.4\.94/http:\/\/demo.example.com/g' {} \;

# Replace company names
find . -type f \( -name "*.py" -o -name "*.md" \) -exec sed -i 's/Charter/DemoTelco/g' {} \;
find . -type f \( -name "*.py" -o -name "*.md" \) -exec sed -i 's/Spectrum/DemoNet/g' {} \;

echo "Sanitization complete"
```

---

## Step 5: GitHub Actions Workflow

**File:** `.github/workflows/deploy-demo.yml`

```yaml
name: Deploy Demo to AWS EKS

on:
  push:
    branches:
      - demo
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  EKS_CLUSTER_NAME: correlation-station-demo
  ECR_REPOSITORY: correlation-station-demo

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - correlation-engine
          - correlation-gateway
          - arda-demo
          - beorn-demo
          - palantir-demo
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build \
            -t $ECR_REGISTRY/$ECR_REPOSITORY/${{ matrix.service }}:$IMAGE_TAG \
            -t $ECR_REGISTRY/$ECR_REPOSITORY/${{ matrix.service }}:latest \
            -f seefa-om/${{ matrix.service }}/Dockerfile \
            seefa-om/${{ matrix.service }}

          docker push $ECR_REGISTRY/$ECR_REPOSITORY/${{ matrix.service }}:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY/${{ matrix.service }}:latest

  deploy-to-eks:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --region $AWS_REGION \
            --name $EKS_CLUSTER_NAME

      - name: Deploy to EKS
        run: |
          kubectl apply -f k8s/demo/
          kubectl rollout status deployment/correlation-engine -n demo
          kubectl rollout status deployment/correlation-gateway -n demo

      - name: Verify deployment
        run: |
          kubectl get pods -n demo
          kubectl get svc -n demo
```

---

## Step 6: Kubernetes Manifests

**File:** `k8s/demo/correlation-engine-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: correlation-engine
  namespace: demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: correlation-engine
  template:
    metadata:
      labels:
        app: correlation-engine
    spec:
      containers:
      - name: correlation-engine
        image: <ECR_REGISTRY>/correlation-station-demo/correlation-engine:latest
        ports:
        - containerPort: 8080
        env:
        - name: DEMO_MODE
          value: "true"
        - name: REDIS_HOST
          value: redis-demo
        - name: LOKI_URL
          value: http://loki:3100
        - name: TEMPO_GRPC_ENDPOINT
          value: tempo:4317
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: correlation-engine
  namespace: demo
spec:
  selector:
    app: correlation-engine
  ports:
  - port: 8080
    targetPort: 8080
  type: LoadBalancer
```

---

## Summary

**Demo branch includes:**
1. ✅ Sanitized data (no Charter/Spectrum/real customer info)
2. ✅ Mock clients with 20-30 response variants per dependency
3. ✅ Feature flag (`DEMO_MODE=true`) to enable mocks
4. ✅ GitHub Actions CI/CD to AWS EKS
5. ✅ Kubernetes manifests for deployment
6. ✅ Updated README for public consumption

**Next steps:**
1. Create demo branch: `git checkout -b demo`
2. Run sanitization script: `./scripts/sanitize_demo_data.sh`
3. Implement mock clients in `demo_mocks/`
4. Update Sense apps to use mocks when `DEMO_MODE=true`
5. Create Kubernetes manifests in `k8s/demo/`
6. Set up GitHub Actions workflow
7. Deploy to AWS EKS
8. Test demo deployment
9. Document demo URL in README

**Demo URL (after deployment):**
`http://demo.correlation-station.example.com`
