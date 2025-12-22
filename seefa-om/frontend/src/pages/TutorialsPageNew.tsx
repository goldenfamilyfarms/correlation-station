import { useState } from 'react'
import { CheckCircle2, Circle, ChevronDown, ChevronRight, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import CodeBlock from '@/components/CodeBlock'
import { useAuth } from '@/lib/auth'
import { useProgress } from '@/lib/progress'

interface Tutorial {
  id: string
  title: string
  category: string
  videoUrl?: string
  content: string
}

const tutorials: Tutorial[] = [
  // ============================================
  // MDSO CORE TUTORIALS
  // ============================================
  {
    id: 'mdso-product-lifecycle',
    title: 'MDSO Product Lifecycle',
    category: 'MDSO Core',
    content: `# MDSO Product Lifecycle Management

Multi-Domain Service Orchestrator (MDSO) manages the complete lifecycle of network products from creation to decommission.

## Product Lifecycle Stages

1. **Product Creation** - New service request initiated
2. **Eligibility Check** - BEORN validates service availability
3. **Design & Validation** - ARDA designs circuit and validates feasibility
4. **Provisioning** - PALANTIR executes device configuration
5. **Activation** - Service brought into production
6. **Monitoring** - Continuous health checks and compliance
7. **Modification** - Changes to existing service
8. **Decommission** - Service removal and cleanup

## Real Circuit Creation Flow

\`\`\`python
# ARDA receives product order
@app.post("/api/product/create")
async def create_product(order: ProductOrder):
    with tracer.start_as_current_span("product_lifecycle") as span:
        # Step 1: Create circuit ID
        circuit_id = generate_circuit_id(order)
        span.set_attribute("circuit.id", circuit_id)

        # Step 2: Check eligibility via BEORN
        eligibility = await beorn_client.check_eligibility(
            location_a=order.location_a,
            location_b=order.location_b,
            bandwidth=order.bandwidth
        )

        # Step 3: Design circuit
        design = await design_circuit(order, eligibility)

        # Step 4: Provision via PALANTIR
        provision_result = await palantir_client.provision(
            circuit_id=circuit_id,
            design=design
        )

        return {"circuit_id": circuit_id, "status": "provisioned"}
\`\`\`

## Query Circuit Lifecycle Events

\`\`\`logql
{service_name="arda"}
  | json
  | circuit_id="12.LAVG.123456..ABCD"
  | line_format "{{.timestamp}}: {{.event}} - {{.status}}"
\`\`\``
  },
  {
    id: 'mdso-troubleshooting',
    title: 'MDSO Troubleshooting Guide',
    category: 'MDSO Core',
    content: `# MDSO Troubleshooting Workflows

Systematic approach to diagnosing and resolving MDSO issues.

## Common Issues & Resolution

### Issue 1: Circuit Provisioning Failures

**Symptoms:**
- Circuit stuck in "PENDING" state
- PALANTIR returns 500 errors
- Device configuration timeouts

**Diagnosis:**
\`\`\`logql
# Check PALANTIR errors for circuit
{service_name="palantir"}
  |= "12.LAVG.123456..ABCD"
  | json
  | level="ERROR"
  | line_format "{{.timestamp}} {{.error_message}}"
\`\`\`

**Resolution Steps:**
1. Check device connectivity via PALANTIR health endpoint
2. Verify ScriptPlan execution logs
3. Review resource adapter status
4. Re-queue provisioning request if transient failure

### Issue 2: Eligibility Check Failures

**Symptoms:**
- BEORN returns "INELIGIBLE" status
- Missing CDNC data
- Location validation errors

**Diagnosis:**
\`\`\`logql
{service_name="beorn"}
  |= "eligibility_check"
  | json
  | eligible="false"
  | line_format "{{.circuit_id}}: {{.ineligible_reason}}"
\`\`\`

**Resolution:**
- Verify CDNC database connectivity
- Check location code validity
- Review bandwidth availability data

### Issue 3: ARDA Service Degradation

**Symptoms:**
- High latency on circuit creation
- Queue backups
- Memory/CPU saturation

**Diagnosis:**
\`\`\`bash
# Check Prometheus metrics
curl http://austx-mdso-logs-02.chtrse.com/prometheus/api/v1/query?query=arda_queue_depth

# View Pyroscope flame graph
open http://austx-mdso-logs-02.chtrse.com/pyroscope/?query=arda
\`\`\`

**Resolution:**
- Scale ARDA horizontally if queue depth > 1000
- Check for slow database queries
- Review Redis cache hit rate
- Investigate memory leaks via profiling`
  },
  {
    id: 'mdso-development-process',
    title: 'MDSO Development Process',
    category: 'MDSO Core',
    content: `# MDSO Development Best Practices

Standards for developing, testing, and deploying MDSO components.

## Development Workflow

### 1. Local Development Setup

\`\`\`bash
# Clone SENSE apps repository
git clone https://github.com/your-org/sense-apps.git
cd sense-apps/arda

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run local ARDA instance
python -m arda_app.main --port 5001
\`\`\`

### 2. Adding OpenTelemetry Instrumentation

\`\`\`python
# arda_app/common/otel/instrumentation.py
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer("arda")

def instrument_app(app):
    FastAPIInstrumentor.instrument_app(app)

    @app.middleware("http")
    async def add_circuit_context(request, call_next):
        # Extract circuit_id from request
        circuit_id = request.headers.get("X-Circuit-ID")

        if circuit_id:
            span = trace.get_current_span()
            span.set_attribute("circuit.id", circuit_id)

        response = await call_next(request)
        return response
\`\`\`

### 3. Testing Strategy

\`\`\`python
# tests/test_circuit_creation.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_circuit_creation_success():
    # Mock BEORN response
    beorn_mock = AsyncMock()
    beorn_mock.check_eligibility.return_value = {
        "eligible": True,
        "bandwidth_available": True
    }

    # Test circuit creation
    result = await create_product({
        "location_a": "LAX",
        "location_b": "NYC",
        "bandwidth": "10G"
    })

    assert result["status"] == "provisioned"
    assert result["circuit_id"].startswith("12.L")
\`\`\`

### 4. Deployment Pipeline

1. **CI/CD via GitHub Actions**
2. **Docker image build**
3. **Deploy to dev environment**
4. **Run integration tests**
5. **Promote to production**

## Code Review Checklist

- [ ] OpenTelemetry spans added for key operations
- [ ] Structured logging with circuit_id context
- [ ] Error handling with proper status codes
- [ ] Database migrations reviewed
- [ ] Performance impact assessed
- [ ] Security review completed`
  },

  // ============================================
  // MDSO COMPONENT MODULES
  // ============================================
  {
    id: 'mdso-bpo-core',
    title: 'BPO Core Container',
    category: 'MDSO Components',
    content: `# BPO Core Container Architecture

Business Process Orchestration (BPO) Core is the foundational container managing workflow execution.

## BPO Core Responsibilities

1. **Workflow Engine** - Executes business process flows
2. **State Management** - Tracks process state across steps
3. **Event Bus** - Publishes process events
4. **Error Handling** - Manages failures and retries

## BPO Core Structure

\`\`\`
bpo-core/
├── src/
│   ├── engine/          # Workflow execution engine
│   ├── state/           # State persistence layer
│   ├── events/          # Event publishing
│   └── adapters/        # External system adapters
├── config/
│   └── workflows/       # Process definitions (BPMN)
└── tests/
\`\`\`

## Example Workflow Definition

\`\`\`xml
<!-- circuit-creation-workflow.bpmn -->
<bpmn:process id="circuit_creation" name="Circuit Creation">
  <bpmn:startEvent id="start" />

  <bpmn:serviceTask id="check_eligibility" name="Check Eligibility">
    <bpmn:extensionElements>
      <camunda:connector>
        <camunda:connectorId>beorn-eligibility</camunda:connectorId>
      </camunda:connector>
    </bpmn:extensionElements>
  </bpmn:serviceTask>

  <bpmn:serviceTask id="provision" name="Provision Circuit">
    <bpmn:extensionElements>
      <camunda:connector>
        <camunda:connectorId>palantir-provision</camunda:connectorId>
      </camunda:connector>
    </bpmn:extensionElements>
  </bpmn:serviceTask>

  <bpmn:endEvent id="end" />
</bpmn:process>
\`\`\`

## Monitoring BPO Core

\`\`\`logql
# Track workflow execution
{container="bpo-core"}
  | json
  | workflow_id != ""
  | line_format "{{.workflow_id}}: {{.step}} - {{.status}}"
\`\`\``
  },
  {
    id: 'mdso-resource-adapters',
    title: 'Resource Adapters',
    category: 'MDSO Components',
    content: `# Resource Adapters - Device Integration Layer

Resource Adapters abstract device-specific protocols into a unified interface.

## Adapter Architecture

\`\`\`
Resource Adapter
    ├── Protocol Handler (NETCONF, REST, SSH)
    ├── Command Translator (Device-specific syntax)
    ├── Response Parser (Normalize device output)
    └── Error Handler (Retry logic, circuit breaker)
\`\`\`

## Supported Adapters

| **Adapter** | **Protocol** | **Devices** |
|-------------|--------------|-------------|
| Ciena Adapter | NETCONF | Ciena 6500, 8700 |
| Cisco Adapter | SSH/CLI | ASR9K, NCS |
| Juniper Adapter | NETCONF | MX, PTX |
| Infinera Adapter | REST API | XTM, DTN-X |

## Creating a Custom Adapter

\`\`\`python
# palantir/adapters/base_adapter.py
from abc import ABC, abstractmethod

class ResourceAdapter(ABC):
    @abstractmethod
    async def configure_circuit(self, circuit_config: dict) -> dict:
        """Configure circuit on device"""
        pass

    @abstractmethod
    async def validate_config(self, circuit_id: str) -> bool:
        """Validate configuration was applied"""
        pass

    @abstractmethod
    async def rollback(self, circuit_id: str) -> bool:
        """Rollback configuration"""
        pass

# palantir/adapters/ciena_adapter.py
from palantir.adapters.base_adapter import ResourceAdapter
from ncclient import manager

class CienaAdapter(ResourceAdapter):
    async def configure_circuit(self, circuit_config: dict):
        with manager.connect(
            host=circuit_config["device_ip"],
            username=self.username,
            password=self.password,
            hostkey_verify=False
        ) as m:
            # Build NETCONF RPC
            rpc = self._build_circuit_rpc(circuit_config)

            # Execute configuration
            response = m.edit_config(target="running", config=rpc)

            return {"status": "success", "device": circuit_config["device_ip"]}
\`\`\`

## Adapter Telemetry

\`\`\`logql
{service_name="palantir"}
  |= "adapter_execution"
  | json
  | line_format "{{.adapter_type}} {{.device_ip}}: {{.status}} ({{.duration_ms}}ms)"
\`\`\``
  },
  {
    id: 'mdso-scriptplan',
    title: 'ScriptPlan Execution',
    category: 'MDSO Components',
    content: `# ScriptPlan - Declarative Device Configuration

ScriptPlan is PALANTIR's execution engine for device configuration workflows.

## ScriptPlan Structure

A ScriptPlan defines:
1. **Target Devices** - Which devices to configure
2. **Configuration Steps** - Sequential or parallel tasks
3. **Validation Rules** - Post-configuration checks
4. **Rollback Strategy** - Failure recovery

## Example ScriptPlan

\`\`\`yaml
# circuit_provisioning.yaml
scriptplan:
  name: "Circuit Provisioning"
  version: "1.0"

  targets:
    - device_id: "LAX-PE01"
      device_type: "ciena_6500"
      adapter: "ciena"
    - device_id: "NYC-PE01"
      device_type: "ciena_6500"
      adapter: "ciena"

  steps:
    - name: "Configure A-End"
      target: "LAX-PE01"
      command_template: |
        configure terminal
        interface GigabitEthernet0/0/0/1
          description "Circuit {{ circuit_id }}"
          encapsulation dot1q {{ vlan_id }}
          ip address {{ ip_a }}
        commit
      validation:
        - type: "interface_status"
          expected: "up"

    - name: "Configure Z-End"
      target: "NYC-PE01"
      command_template: |
        configure terminal
        interface GigabitEthernet0/0/0/1
          description "Circuit {{ circuit_id }}"
          encapsulation dot1q {{ vlan_id }}
          ip address {{ ip_z }}
        commit
      validation:
        - type: "interface_status"
          expected: "up"

    - name: "End-to-End Ping Test"
      type: "validation"
      command: "ping {{ ip_z }} source {{ ip_a }} count 5"
      success_criteria:
        - "5 packets transmitted, 5 received"

  rollback:
    on_failure: true
    steps:
      - "no interface configuration"
\`\`\`

## ScriptPlan Execution Logs

\`\`\`logql
{service_name="palantir"}
  |= "scriptplan_execution"
  | json
  | circuit_id="12.LAVG.123456..ABCD"
  | line_format "Step {{.step_number}}: {{.step_name}} - {{.status}} ({{.device_id}})"
\`\`\`

## Monitoring ScriptPlan Health

\`\`\`traceql
# Find failed ScriptPlan executions
{ .service.name = "palantir" && .operation = "scriptplan_execute" && status = error }
\`\`\``
  },
  {
    id: 'mdso-solution-manager',
    title: 'Solution Manager Development',
    category: 'MDSO Components',
    content: `# Solution Manager - Product Template Engine

Solution Manager defines product templates and manages solution configurations.

## Solution Manager Architecture

\`\`\`
Solution Manager
    ├── Template Repository (Product definitions)
    ├── Design Engine (Circuit design automation)
    ├── Validation Engine (Feasibility checks)
    └── Configuration Generator (Device configs)
\`\`\`

## Product Template Example

\`\`\`json
{
  "solution_id": "ethernet_eline",
  "name": "Ethernet E-Line Service",
  "version": "2.0",
  "parameters": {
    "bandwidth": {
      "type": "enum",
      "values": ["10M", "100M", "1G", "10G", "100G"],
      "required": true
    },
    "protection": {
      "type": "boolean",
      "default": false
    },
    "cos": {
      "type": "enum",
      "values": ["BE", "AF", "EF"],
      "default": "BE"
    }
  },
  "design_rules": {
    "min_bandwidth": "10M",
    "max_latency_ms": 50,
    "redundancy_required": true
  },
  "scriptplan_template": "eline_provisioning.yaml",
  "validation": {
    "pre_provision": [
      "check_port_availability",
      "validate_vlan_range",
      "verify_bandwidth_capacity"
    ],
    "post_provision": [
      "verify_interface_status",
      "ping_test",
      "throughput_test"
    ]
  }
}
\`\`\`

## Solution Manager API

\`\`\`python
# solution_manager/api/design.py
@app.post("/api/solution/design")
async def design_solution(request: DesignRequest):
    with tracer.start_as_current_span("design_solution") as span:
        span.set_attribute("solution.id", request.solution_id)

        # Load solution template
        template = load_template(request.solution_id)

        # Validate parameters
        validate_parameters(request.parameters, template.parameters)

        # Run design algorithm
        design = await run_design_engine(
            template=template,
            location_a=request.location_a,
            location_b=request.location_b,
            parameters=request.parameters
        )

        # Generate ScriptPlan
        scriptplan = generate_scriptplan(design, template)

        return {
            "design_id": design.id,
            "path": design.path,
            "devices": design.devices,
            "scriptplan": scriptplan
        }
\`\`\``
  },

  // ============================================
  // MDSO ECOSYSTEM MODULES
  // ============================================
  {
    id: 'mdso-ip-control',
    title: 'IP Control Integration',
    category: 'MDSO Ecosystem',
    content: `# IP Control - IP Address Management (IPAM)

IP Control manages IP address allocation and DNS registration for MDSO circuits.

## IP Control Workflow

1. **IP Allocation Request** - ARDA requests IP block for circuit
2. **Subnet Assignment** - IP Control allocates from available pool
3. **DNS Registration** - Create A/PTR records
4. **CMDB Update** - Record allocation in asset database

## IP Control API Integration

\`\`\`python
# arda/integrations/ip_control.py
class IPControlClient:
    async def allocate_subnet(self, circuit_id: str, size: int):
        """Allocate IP subnet for circuit"""
        response = await self.client.post("/api/subnet/allocate", json={
            "circuit_id": circuit_id,
            "prefix_length": size,
            "region": "us-west"
        })

        return response.json()

    async def register_dns(self, circuit_id: str, ip_address: str):
        """Register DNS record for circuit endpoint"""
        hostname = f"{circuit_id}.circuit.example.com"

        await self.client.post("/api/dns/register", json={
            "hostname": hostname,
            "ip_address": ip_address,
            "record_type": "A",
            "ttl": 300
        })

# Usage in circuit creation
async def create_circuit(order: ProductOrder):
    # Allocate IP addresses
    ip_allocation = await ip_control.allocate_subnet(
        circuit_id=circuit_id,
        size=30  # /30 for point-to-point
    )

    # Register DNS
    await ip_control.register_dns(circuit_id, ip_allocation["ip_a"])
    await ip_control.register_dns(circuit_id, ip_allocation["ip_z"])
\`\`\`

## Query IP Allocations

\`\`\`logql
{service_name="arda"}
  |= "ip_allocation"
  | json
  | circuit_id != ""
  | line_format "{{.circuit_id}}: {{.ip_a}} <-> {{.ip_z}}"
\`\`\``
  },
  {
    id: 'mdso-granite',
    title: 'Granite CMDB Integration',
    category: 'MDSO Ecosystem',
    content: `# Granite - Configuration Management Database

Granite is the CMDB system tracking all network assets and relationships.

## Granite Data Model

\`\`\`
Circuit
  ├── Endpoints (Location A, Location Z)
  ├── Devices (PE routers, OTN equipment)
  ├── Interfaces (Physical ports)
  ├── IP Addresses
  └── Relationships (Dependencies, parent circuits)
\`\`\`

## Granite API Integration

\`\`\`python
# arda/integrations/granite.py
class GraniteClient:
    async def create_circuit_record(self, circuit: CircuitData):
        """Create circuit record in Granite CMDB"""
        payload = {
            "circuit_id": circuit.circuit_id,
            "type": "ethernet_eline",
            "bandwidth": circuit.bandwidth,
            "endpoints": [
                {
                    "location": circuit.location_a,
                    "device": circuit.device_a,
                    "interface": circuit.interface_a,
                    "ip_address": circuit.ip_a
                },
                {
                    "location": circuit.location_z,
                    "device": circuit.device_z,
                    "interface": circuit.interface_z,
                    "ip_address": circuit.ip_z
                }
            ],
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }

        response = await self.client.post("/api/circuit/create", json=payload)
        return response.json()

    async def update_circuit_status(self, circuit_id: str, status: str):
        """Update circuit operational status"""
        await self.client.patch(f"/api/circuit/{circuit_id}", json={
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        })

# Usage in ARDA
async def provision_circuit(circuit_id: str):
    # Provision via PALANTIR
    result = await palantir.provision(circuit_id)

    # Update Granite CMDB
    await granite.update_circuit_status(circuit_id, "provisioned")
\`\`\``
  },
  {
    id: 'mdso-tacacs',
    title: 'TACACS+ Authentication',
    category: 'MDSO Ecosystem',
    content: `# TACACS+ Integration for Device Access

TACACS+ provides centralized authentication for network device access.

## TACACS+ Flow

1. **User Authentication** - Verify credentials against TACACS+ server
2. **Authorization** - Check user permissions for device/command
3. **Accounting** - Log all user actions

## PALANTIR TACACS+ Integration

\`\`\`python
# palantir/auth/tacacs.py
from tacacs_plus.client import TACACSClient

class DeviceAuthenticator:
    def __init__(self, tacacs_server: str, tacacs_secret: str):
        self.client = TACACSClient(tacacs_server, 49, tacacs_secret)

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user against TACACS+"""
        try:
            auth_response = self.client.authenticate(username, password)
            return auth_response.valid
        except Exception as e:
            logger.error("tacacs_auth_failed", error=str(e))
            return False

    async def authorize_command(self, username: str, device: str, command: str) -> bool:
        """Check if user authorized to run command on device"""
        authz_response = self.client.authorize(
            username=username,
            arguments=[f"service=shell", f"cmd={command}"]
        )
        return authz_response.valid

# Usage in adapter
async def execute_device_command(device_ip: str, command: str):
    # Authenticate service account
    if not await tacacs.authenticate(username, password):
        raise AuthenticationError("TACACS+ auth failed")

    # Authorize command
    if not await tacacs.authorize_command(username, device_ip, command):
        raise AuthorizationError(f"Not authorized to run: {command}")

    # Execute command
    result = await device.execute(command)
    return result
\`\`\``
  },
  {
    id: 'mdso-end-to-end',
    title: 'End-to-End Circuit Flow',
    category: 'MDSO Ecosystem',
    content: `# Complete End-to-End Circuit Provisioning

Full trace of circuit creation from order to activation.

## Complete Flow Diagram

\`\`\`
Customer Order
    ↓
ARDA (Circuit Creation API)
    ↓ Check Eligibility
BEORN (Eligibility Service)
    ↓ Validate CDNC
CDNC Database
    ↓ Return: ELIGIBLE
ARDA (Design Circuit)
    ↓ Allocate IPs
IP Control (IPAM)
    ↓ IPs: 10.1.1.1/30
ARDA (Generate ScriptPlan)
    ↓ Provision Request
PALANTIR (Orchestrator)
    ↓ Execute ScriptPlan
Resource Adapters (Ciena, Cisco, Juniper)
    ↓ NETCONF/SSH
Network Devices
    ↓ Validation
PALANTIR (Verify Config)
    ↓ Update CMDB
Granite (Asset Database)
    ↓ Register DNS
IP Control (DNS)
    ↓ Complete
ARDA (Return Success)
\`\`\`

## Tracing Full Flow

\`\`\`traceql
# Find complete trace for circuit creation
{ .circuit.id = "12.LAVG.123456..ABCD" }
\`\`\`

\`\`\`logql
# Aggregate logs from all services
{service_name=~"arda|beorn|palantir"}
  |= "12.LAVG.123456..ABCD"
  | json
  | line_format "{{.timestamp}} [{{.service_name}}] {{.event}}: {{.status}}"
\`\`\`

## Correlation Engine View

The Correlation Engine automatically links:
- **Logs** from ARDA, BEORN, PALANTIR by circuit_id
- **Traces** across service boundaries
- **Metrics** (latency, error rate) per service

Query correlated view:
\`\`\`bash
curl "http://austx-mdso-logs-02.chtrse.com/correlation-engine/api/correlations?circuit_id=12.LAVG.123456..ABCD"
\`\`\``
  },

  // ============================================
  // OBSERVABILITY ENHANCEMENTS
  // ============================================
  {
    id: 'grafana-dashboards',
    title: 'Grafana Dashboard Design',
    category: 'Observability',
    content: `# Building Effective Grafana Dashboards

Best practices for creating MDSO observability dashboards.

## Dashboard Layout Strategy

### 1. Executive Dashboard (High-Level)
- **Circuit Success Rate** (last 24h)
- **Active Circuits** (total count)
- **Provisioning Latency** (p50, p95, p99)
- **Service Health** (ARDA, BEORN, PALANTIR status)

### 2. Service Deep-Dive Dashboards
- **ARDA Dashboard** - Queue depth, API latency, error rate
- **PALANTIR Dashboard** - ScriptPlan success rate, device failures
- **BEORN Dashboard** - Eligibility check latency, CDNC query performance

### 3. Circuit Troubleshooting Dashboard
- **Circuit Timeline** - All events for specific circuit_id
- **Related Logs** - Correlated logs from all services
- **Trace Waterfall** - Distributed trace visualization

## Example Panel Queries

### Circuit Provisioning Success Rate
\`\`\`promql
sum(rate(circuit_provisioned_total{status="success"}[5m]))
/
sum(rate(circuit_provisioned_total[5m]))
\`\`\`

### ARDA Queue Depth
\`\`\`promql
arda_queue_depth
\`\`\`

### PALANTIR Device Failures
\`\`\`logql
sum by (device_type) (
  count_over_time({service_name="palantir"} |= "device_failure" [1h])
)
\`\`\`

## Grafana Color Scheme (Brand Consistency)

\`\`\`json
{
  "colors": {
    "primary": "#FF6600",     // Grafana Orange
    "success": "#00FF00",     // Green
    "warning": "#FFFF00",     // Yellow
    "error": "#FF0000",       // Red
    "background": "#111111",  // Dark Gray
    "text": "#FFFFFF"         // White
  }
}
\`\`\``
  },
  {
    id: 'log-parsing',
    title: 'Advanced Log Parsing',
    category: 'Observability',
    content: `# Advanced LogQL Parsing Techniques

Extract structured data from unstructured logs.

## Parsing MDSO Log Formats

### Extract Circuit ID with Regex
\`\`\`logql
{service_name="arda"}
  | regexp "circuit_id=(?P<circuit_id>\\\\d{2}\\\\.L[0-9A-Z]{3,4}\\\\.\\\\d{6}\\\\.\\\\.\\\\.\\\\w{4})"
  | line_format "{{.circuit_id}}"
\`\`\`

### Parse JSON Logs
\`\`\`logql
{service_name="palantir"}
  | json
  | level="ERROR"
  | device_type != ""
  | line_format "Device {{.device_id}} ({{.device_type}}): {{.error_message}}"
\`\`\`

### Extract Duration from Logs
\`\`\`logql
{service_name="beorn"}
  |= "eligibility_check_completed"
  | regexp "duration=(?P<duration_ms>\\\\d+)ms"
  | duration_ms > 1000
\`\`\`

## Pattern Matching

\`\`\`logql
{service_name="arda"}
  | pattern "<timestamp> <level> <message>"
  | level = "ERROR"
\`\`\`

## Building Alerts from Logs

\`\`\`promql
# Alert on high error rate
sum(rate({service_name=~"arda|beorn|palantir"} |= "ERROR" [5m])) > 10
\`\`\``
  },
  {
    id: 'otel-instrumentation',
    title: 'OpenTelemetry Best Practices',
    category: 'Observability',
    content: `# OpenTelemetry Instrumentation Standards

How to properly instrument MDSO services with OTel.

## Span Naming Convention

**Format:** \`<service>.<operation>\`

Examples:
- \`arda.create_circuit\`
- \`beorn.eligibility_check\`
- \`palantir.scriptplan_execute\`

## Semantic Attributes

Always include:
\`\`\`python
span.set_attribute("circuit.id", circuit_id)
span.set_attribute("service.name", "arda")
span.set_attribute("operation.name", "create_circuit")
span.set_attribute("circuit.bandwidth", "10G")
span.set_attribute("circuit.location_a", "LAX")
span.set_attribute("circuit.location_z", "NYC")
\`\`\`

## Error Handling

\`\`\`python
try:
    result = await provision_circuit(circuit_id)
    span.set_status(StatusCode.OK)
except Exception as e:
    span.set_status(StatusCode.ERROR, str(e))
    span.record_exception(e)
    raise
\`\`\`

## Context Propagation

\`\`\`python
# ARDA propagates trace context to BEORN
headers = {}
inject(headers)  # Inject W3C trace context

response = await http.post(
    "http://beorn:5002/api/eligibility",
    headers=headers,  # Propagate trace
    json=payload
)
\`\`\`

## Sampling Strategy

\`\`\`python
# Sample 100% of errors, 10% of success
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

sampler = ParentBasedTraceIdRatioBased(0.1)
\`\`\``
  },
  {
    id: 'correlation-engine-usage',
    title: 'Using the Correlation Engine',
    category: 'Observability',
    content: `# Correlation Engine - Unified Telemetry View

Query correlated logs, traces, and metrics by circuit_id.

## Correlation Engine Architecture

\`\`\`
Alloy (MDSO)
    ↓ OTLP/gRPC
OTel Gateway (META)
    ↓ OTLP/HTTP
Correlation Engine
    ↓ (parallel)
    ├─→ Redis Cache (fast lookups)
    ├─→ Loki (logs)
    └─→ Tempo (traces)
\`\`\`

## Query Correlations API

\`\`\`bash
# Get all telemetry for a circuit
curl "http://austx-mdso-logs-02.chtrse.com/correlation-engine/api/correlations?circuit_id=12.LAVG.123456..ABCD"
\`\`\`

Response:
\`\`\`json
{
  "circuit_id": "12.LAVG.123456..ABCD",
  "traces": [
    {
      "trace_id": "abc123...",
      "service": "arda",
      "duration_ms": 1234,
      "status": "ok"
    },
    {
      "trace_id": "def456...",
      "service": "palantir",
      "duration_ms": 5678,
      "status": "error"
    }
  ],
  "logs": [
    {
      "timestamp": "2025-12-11T10:30:00Z",
      "service": "arda",
      "level": "INFO",
      "message": "Circuit creation started"
    }
  ],
  "events": [
    {
      "event": "circuit_created",
      "timestamp": "2025-12-11T10:30:05Z",
      "status": "success"
    }
  ]
}
\`\`\`

## Redis Cache Benefits

- **Fast Lookups**: < 5ms retrieval time (vs 500ms DB query)
- **Deduplication**: Prevents duplicate trace ingestion
- **TTL Management**: Auto-expire after 48 hours`
  },

  // ============================================
  // EXISTING TUTORIALS (Logs, Traces, etc.)
  // ============================================
  {
    id: 'logql-basics',
    title: 'LogQL Basics',
    category: 'Query Languages',
    videoUrl: 'https://www.youtube.com/embed/57dQwcmqkpQ',
    content: `# LogQL Query Language

LogQL is Loki's query language for querying logs. Here are real examples from MDSO:

## MDSO Circuit Creation Logs
\`\`\`logql
{service_name="arda"} |= "circuit_id" | json | circuit_id != ""
\`\`\`

## SENSE Device Errors
\`\`\`logql
{service_name="beorn"} |= "error" | json | level="ERROR"
\`\`\`

## Count Errors Over Time
\`\`\`logql
sum(count_over_time({service_name=~"arda|beorn|palantir"} |= "error" [5m]))
\`\`\``
  },
  {
    id: 'traceql-basics',
    title: 'TraceQL Basics',
    category: 'Traces',
    videoUrl: 'https://www.youtube.com/embed/bgQblHktS78',
    content: `# TraceQL Query Language

TraceQL queries distributed traces in Tempo. Real MDSO examples:

## Find Slow Circuit Operations
\`\`\`traceql
{ .service.name = "arda" && duration > 30s }
\`\`\`

## Device Connectivity Failures
\`\`\`traceql
{ .service.name = "palantir" && status = error && .operation = "device_check" }
\`\`\`

## Trace All SENSE Operations
\`\`\`traceql
{ .service.name =~ "arda|beorn|palantir" && .circuit_id != "" }
\`\`\``
  },
  {
    id: 'distributed-traces',
    title: 'Distributed Traces',
    category: 'Traces',
    videoUrl: 'https://www.youtube.com/embed/zDrA7Ly3ovU?start=2204',
    content: `# Understanding Distributed Traces

Traces show the complete journey of a request through MDSO/SENSE systems.

## MDSO Circuit Flow
1. ARDA receives circuit creation request
2. BEORN validates eligibility
3. PALANTIR checks device compliance
4. ARDA provisions circuit

Each step is a span with timing and metadata.`
  },
  {
    id: 'otel-mdso',
    title: 'MDSO Instrumentation',
    category: 'OpenTelemetry',
    content: `# MDSO OpenTelemetry Setup

Real configuration from mdso-alloy:

## Alloy Configuration
\`\`\`yaml
otelcol.receiver.otlp "mdso" {
  grpc {
    endpoint = "0.0.0.0:4317"
  }
  output {
    traces  = [otelcol.processor.batch.default.input]
    logs    = [otelcol.processor.batch.default.input]
  }
}
\`\`\`

## Python Instrumentation (ARDA)
\`\`\`python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer("arda")

@app.post("/circuit/create")
async def create_circuit(circuit_data: dict):
    with tracer.start_as_current_span("create_circuit") as span:
        span.set_attribute("circuit.id", circuit_data["circuit_id"])
        span.set_attribute("circuit.type", circuit_data["service_type"])
        # Process circuit...
\`\`\``
  },
  {
    id: 'otel-sense',
    title: 'SENSE Instrumentation',
    category: 'OpenTelemetry',
    content: `# SENSE OpenTelemetry Setup

From sense-apps/arda/arda_app/common/otel:

## SENSE OTel Configuration
\`\`\`python
# sense-apps/arda/arda_app/common/otel/otel_sense.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
otlp_exporter = OTLPSpanExporter(
    endpoint="http://austx-mdso-logs-02.chtrse.com:4317",
    insecure=True
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
\`\`\`

## MDSO Pattern Extraction
\`\`\`python
# mdso-instrumentation/otel/mdso_patterns.py
CIRCUIT_ID_PATTERN = r'\\b\\d{2}\\.L[0-9A-Z]{3,4}\\.\\d{6}\\.\\.\\w{4}\\b'
\`\`\``
  },
  {
    id: 'mdso-queries',
    title: 'MDSO Log Queries',
    category: 'MDSO',
    content: `# MDSO-Specific Queries

## Find Circuit Creation Events
\`\`\`logql
{service_name="arda"} 
  |= "circuit_id" 
  | json 
  | circuit_id =~ "\\\\d{2}\\\\.L[0-9A-Z]{3,4}\\\\.\\\\d{6}\\\\.\\\\.\\\\.\\\\w{4}"
\`\`\`

## Track Device Provisioning
\`\`\`logql
{service_name="palantir"} 
  |= "device" 
  | json 
  | operation="provision" 
  | line_format "{{.timestamp}} {{.device_id}} {{.status}}"
\`\`\`

## Error Rate by Service
\`\`\`logql
sum by (service_name) (
  rate({service_name=~"arda|beorn|palantir"} |= "error" [5m])
)
\`\`\``
  },
  {
    id: 'sense-queries',
    title: 'SENSE Log Queries',
    category: 'SENSE',
    content: `# SENSE-Specific Queries

## BEORN Eligibility Checks
\`\`\`logql
{service_name="beorn"} 
  |= "eligibility" 
  | json 
  | circuit_id != "" 
  | eligible="true"
\`\`\`

## PALANTIR Compliance Validation
\`\`\`logql
{service_name="palantir"} 
  |= "compliance" 
  | json 
  | status="FAILED"
  | line_format "Circuit: {{.circuit_id}} - {{.failure_reason}}"
\`\`\`

## ARDA Circuit Status
\`\`\`logql
{service_name="arda"} 
  | json 
  | circuit_status != "" 
  | line_format "{{.circuit_id}}: {{.circuit_status}}"
\`\`\``
  }
]

const categories = [
  'MDSO Core',
  'MDSO Components',
  'MDSO Ecosystem',
  'Observability',
  'Query Languages',
  'Traces',
  'OpenTelemetry',
  'MDSO',
  'SENSE'
]

function parseMarkdownContent(content: string) {
  const elements: JSX.Element[] = []
  const lines = content.split('\n')
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block
    if (line.startsWith('```')) {
      const language = line.replace('```', '')
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      elements.push(<CodeBlock key={key++} code={codeLines.join('\n')} language={language} />)
      i++
      continue
    }

    // H1
    if (line.startsWith('# ')) {
      elements.push(<h1 key={key++} className="text-2xl font-bold mt-8 mb-4 text-gray-900">{line.replace('# ', '')}</h1>)
      i++
      continue
    }

    // H2
    if (line.startsWith('## ')) {
      elements.push(<h2 key={key++} className="text-xl font-semibold mt-6 mb-3 text-grafana-orange">{line.replace('## ', '')}</h2>)
      i++
      continue
    }

    // Paragraph
    if (line.trim()) {
      elements.push(<p key={key++} className="mb-4 text-gray-700 leading-relaxed">{line}</p>)
    }
    i++
  }

  return elements
}

export default function TutorialsPageNew() {
  const [selectedTutorial, setSelectedTutorial] = useState(tutorials[0])
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(categories))
  const { user } = useAuth()
  const { markComplete, isComplete, getProgress } = useProgress()

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  const handleMarkComplete = () => {
    if (user) {
      markComplete(user.id, selectedTutorial.id)
    }
  }

  const progress = user ? getProgress(user.id, tutorials.length) : 0

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white overflow-y-auto">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-grafana-orange">Tutorials</h2>
          {user && (
            <div className="mt-2">
              <div className="text-xs text-gray-400">Progress</div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-grafana-orange h-2 rounded-full transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs">{progress}%</span>
              </div>
            </div>
          )}
        </div>

        {categories.map(category => {
          const categoryTutorials = tutorials.filter(t => t.category === category)
          const isExpanded = expandedCategories.has(category)

          return (
            <div key={category}>
              <button
                onClick={() => toggleCategory(category)}
                className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-800 transition-colors"
              >
                <span className="font-medium">{category}</span>
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>

              {isExpanded && (
                <div className="bg-gray-800">
                  {categoryTutorials.map(tutorial => {
                    const completed = user ? isComplete(user.id, tutorial.id) : false
                    const isActive = selectedTutorial.id === tutorial.id

                    return (
                      <button
                        key={tutorial.id}
                        onClick={() => setSelectedTutorial(tutorial)}
                        className={`w-full px-6 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-700 transition-colors ${
                          isActive ? 'bg-gray-700 border-l-2 border-grafana-orange' : ''
                        }`}
                      >
                        {completed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                        ) : (
                          <Circle className="h-4 w-4 text-gray-500 flex-shrink-0" />
                        )}
                        <span className={completed ? 'text-green-400' : ''}>{tutorial.title}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto bg-white">
        <div className="max-w-4xl mx-auto p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-900">{selectedTutorial.title}</h1>
            {user && !isComplete(user.id, selectedTutorial.id) && (
              <Button onClick={handleMarkComplete} className="bg-grafana-orange hover:bg-grafana-orange/90">
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Mark Complete
              </Button>
            )}
          </div>

          {/* Video */}
          {selectedTutorial.videoUrl ? (
            <div className="mb-8 rounded-lg overflow-hidden shadow-lg">
              <iframe
                width="100%"
                height="450"
                src={selectedTutorial.videoUrl}
                title={selectedTutorial.title}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                loading="lazy"
              />
            </div>
          ) : (
            <div className="mb-8 bg-gray-100 rounded-lg p-12 text-center">
              <Play className="h-16 w-16 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 font-medium">Video coming soon</p>
            </div>
          )}

          {/* Content */}
          <div className="space-y-2">
            {parseMarkdownContent(selectedTutorial.content)}
          </div>
        </div>
      </div>
    </div>
  )
}
