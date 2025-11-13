# Implementation Guide - End-to-End Observability for MDSO ↔ Sense

## Overview

This guide provides step-by-step instructions for implementing complete observability across the MDSO and Sense ecosystem.

**Architecture**: See `ARCHITECTURE.md` for detailed flow diagrams
**Signals**: See `SIGNAL_DESIGN.md` for complete signal specifications
**Container Matrix**: See `CONTAINER_MATRIX.md` for instrumentation decisions

---

## Prerequisites

### Infrastructure
- [x] Meta Server (159.56.4.94) - Running Docker Compose
- [x] MDSO Server (47.43.111.107) - Running Blue Planet 24.08
- [ ] Network connectivity: MDSO → Meta on ports 55681 (OTLP HTTP), 3100 (Loki), 9090 (Prometheus)

### Access Requirements
- [ ] SSH access to MDSO server
- [ ] Docker access on Meta server
- [ ] GitLab CI/CD runner configured
- [ ] MDSO admin credentials (for manual product deployment)

### Environment Variables Required

Create `/home/user/correlation-station/seefa-om/.env`:

```bash
# Correlation Engine
CORR_WINDOW_SECONDS=60
MAX_BATCH_SIZE=5000
LOG_LEVEL=info

# Loki/Tempo/Prometheus endpoints
LOKI_URL=http://loki:3100/loki/api/v1/push
TEMPO_GRPC_ENDPOINT=tempo:4317
TEMPO_HTTP_ENDPOINT=http://tempo:4318
PROMETHEUS_PUSHGATEWAY=

# DataDog dual export (optional)
DATADOG_API_KEY=${DATADOG_API_KEY}
DATADOG_SITE=datadoghq.com

# Deployment
DEPLOYMENT_ENV=dev

# MDSO Connection
MDSO_URL=http://47.43.111.107:8181
MDSO_USER=${MDSO_USER}
MDSO_PASS=${MDSO_PASS}
```

---

## Phase 1: MDSO Instrumentation (Week 1)

### Step 1.1: Deploy otel_instrumentation Product to MDSO

**Objective**: Install OTel SDK library in MDSO scriptplan containers

**Files Created**:
- ✅ `/mdso-dev/charter_sensor_templates/model-definitions/scripts/otel_instrumentation/`
  - `__init__.py`
  - `common_otel.py` (OTelPlan class)
  - `instrumentation.py` (utilities - **TO BE CREATED**)
  - `otel_instrumentation.tosca` (product definition)

**Implementation**:

1. **Create Missing File**: `instrumentation.py`

```python
# File: mdso-dev/charter_sensor_templates/model-definitions/scripts/otel_instrumentation/instrumentation.py

"""
Utility functions for OTel instrumentation
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

def setup_otel(
    service_name: str = "mdso-scriptplan",
    endpoint: str = None,
    environment: str = "dev"
) -> trace.Tracer:
    """
    Setup OpenTelemetry tracer

    Args:
        service_name: Service name for resource attributes
        endpoint: OTLP exporter endpoint
        environment: Deployment environment

    Returns:
        Configured tracer instance
    """
    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://159.56.4.94:55681")

    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    })

    provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        timeout=30,
    )

    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)

    logger.info(f"OTel initialized: service={service_name}, endpoint={endpoint}")

    return trace.get_tracer(__name__)

def get_otel_logger():
    """Get structured logger for OTel"""
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
    )

    return structlog.get_logger()

def otel_enter_exit_log(message: str, state: str = "STARTED", **kwargs):
    """
    Standalone enter_exit_log function for products that don't inherit OTelPlan
    """
    logger = get_otel_logger()

    if state == "FAILED":
        logger.error(message, state=state, **kwargs)
    else:
        logger.info(message, state=state, **kwargs)
```

2. **Install Dependencies in MDSO Scriptplan Container**

Create `requirements-otel.txt`:

```
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-http==1.20.0
structlog==23.2.0
```

**Deployment Commands** (run on MDSO server):

```bash
# SSH to MDSO server
ssh user@47.43.111.107

# Copy otel_instrumentation directory to MDSO
scp -r /path/to/correlation-station/mdso-dev/charter_sensor_templates/model-definitions/scripts/otel_instrumentation user@47.43.111.107:/tmp/

# On MDSO server, install in scriptplan container
docker exec -it scriptplan bash
cd /opt/mdso/model-definitions/scripts/
mv /tmp/otel_instrumentation ./
pip install -r otel_instrumentation/requirements-otel.txt
exit
```

3. **Update Existing Products to Use OTelPlan**

Example: Modify `CircuitDetailsCollectorPlan`:

```python
# File: model-definitions/scripts/circuitDetailsHandler.py

# OLD:
from scripts.common_plan import CommonPlan

class CircuitDetailsCollectorPlan(CommonPlan):
    def process(self):
        self.enter_exit_log("Starting circuit details collection")
        # ...
        self.enter_exit_log("Completed", "COMPLETED")

# NEW:
from otel_instrumentation.common_otel import OTelPlan

class CircuitDetailsCollectorPlan(OTelPlan):
    def process(self):
        # Start parent workflow span
        self.start_workflow_span()

        self.enter_exit_log("Starting circuit details collection")
        # ... existing logic ...
        self.enter_exit_log("Completed", "COMPLETED")

        # End workflow span
        self.end_workflow_span(success=True)
```

**Validation**:

```bash
# Check logs are being emitted
docker exec scriptplan tail -f /bp2/log/splunk-logs/sensor-templates-otel.log

# Verify OTel export (should see HTTP POST to Meta server)
docker exec scriptplan tcpdump -i any -nn port 55681
```

---

### Step 1.2: Deploy Grafana Alloy Agent to MDSO

**Objective**: Collect MDSO logs and forward to Meta server

**Files Created**:
- ✅ `/mdso-instrumentation/alloy/mdso-config.alloy`

**Implementation**:

1. **Create Installation Script**

```bash
# File: mdso-instrumentation/alloy/install-alloy.sh

#!/bin/bash
set -euo pipefail

echo "Installing Grafana Alloy on MDSO server..."

# Download Alloy
ALLOY_VERSION="v1.0.0"
wget https://github.com/grafana/alloy/releases/download/${ALLOY_VERSION}/alloy-linux-amd64
chmod +x alloy-linux-amd64
sudo mv alloy-linux-amd64 /usr/local/bin/alloy

# Create config directory
sudo mkdir -p /etc/alloy

# Copy configuration
sudo cp mdso-config.alloy /etc/alloy/config.alloy

# Create systemd service
sudo tee /etc/systemd/system/alloy.service > /dev/null <<EOF
[Unit]
Description=Grafana Alloy
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/alloy run /etc/alloy/config.alloy
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable alloy
sudo systemctl start alloy

echo "✓ Alloy installed and started"
echo "Check status: sudo systemctl status alloy"
echo "View logs: sudo journalctl -u alloy -f"
```

2. **Deploy to MDSO Server**

```bash
# From your local machine
cd /home/user/correlation-station/mdso-instrumentation/alloy

# Copy to MDSO server
scp install-alloy.sh mdso-config.alloy user@47.43.111.107:/tmp/

# SSH to MDSO and run installer
ssh user@47.43.111.107
cd /tmp
chmod +x install-alloy.sh
sudo ./install-alloy.sh
```

3. **Validation**

```bash
# Check Alloy is running
sudo systemctl status alloy

# View Alloy logs
sudo journalctl -u alloy -f

# Test log forwarding
echo "TEST LOG resource_id=550e8400-e29b-41d4-a716-446655440000 circuit_id=test-123" | \
  sudo tee -a /opt/ciena/bp2/scriptplan/logs/test.log

# Verify in Loki (on Meta server)
curl -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={container="scriptplan"}' \
  --data-urlencode 'limit=10'
```

---

## Phase 2: Correlation Station Enhancement (Week 2)

### Step 2.1: Enhance Correlation Station with Trace Synthesis

**Objective**: Add trace stitching and synthetic span injection

**Files to Create**:

1. **Trace Synthesizer**

```python
# File: seefa-om/correlation-engine/app/correlation/trace_synthesizer.py

"""
Trace Synthesizer - Creates synthetic parent spans to link disconnected traces
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

@dataclass
class TraceSegment:
    """Represents a segment of a distributed trace"""
    trace_id: str
    span_id: str
    service: str
    timestamp: datetime
    circuit_id: Optional[str] = None
    resource_id: Optional[str] = None
    product_id: Optional[str] = None

class TraceSynthesizer:
    """
    Links disconnected trace segments using correlation keys

    Example: MDSO creates resource (trace A) → calls Sense app (trace B)
    Since MDSO doesn't propagate trace context, we create synthetic bridge span.
    """

    def __init__(self, correlation_window_seconds: int = 60):
        self.window = timedelta(seconds=correlation_window_seconds)
        self.segments: List[TraceSegment] = []

    def add_segment(self, segment: TraceSegment):
        """Add trace segment for correlation"""
        self.segments.append(segment)
        self._cleanup_old_segments()

    def find_parent_trace(self, segment: TraceSegment) -> Optional[TraceSegment]:
        """
        Find parent trace segment based on:
        1. circuit_id match
        2. Temporal proximity (within correlation window)
        3. Service flow pattern (MDSO → Sense)
        """
        candidates = []

        for parent in self.segments:
            # Skip same service
            if parent.service == segment.service:
                continue

            # Check correlation keys match
            if segment.circuit_id and parent.circuit_id == segment.circuit_id:
                # Check temporal proximity
                time_diff = abs((segment.timestamp - parent.timestamp).total_seconds())
                if time_diff <= self.window.total_seconds():
                    candidates.append((parent, time_diff))

        # Return closest temporal match
        if candidates:
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]

        return None

    def create_bridge_span(
        self,
        parent: TraceSegment,
        child: TraceSegment
    ) -> Dict:
        """
        Create synthetic bridge span linking parent and child
        """
        # Generate deterministic span_id based on parent+child
        span_id_str = f"{parent.span_id}-{child.span_id}"
        span_id = hashlib.md5(span_id_str.encode()).hexdigest()[:16]

        return {
            "trace_id": parent.trace_id,  # Inherit parent's trace
            "span_id": span_id,
            "parent_span_id": parent.span_id,
            "name": f"{parent.service}_to_{child.service}_bridge",
            "kind": "INTERNAL",
            "start_time_unix_nano": int(parent.timestamp.timestamp() * 1e9),
            "end_time_unix_nano": int(child.timestamp.timestamp() * 1e9),
            "attributes": {
                "bridge.type": "synthetic",
                "bridge.parent_service": parent.service,
                "bridge.child_service": child.service,
                "circuit_id": parent.circuit_id,
                "resource_id": parent.resource_id,
                "correlation.method": "circuit_id_match",
                "correlation.confidence": 0.95,
            },
            "links": [
                {"trace_id": child.trace_id, "span_id": child.span_id}
            ],
        }

    def _cleanup_old_segments(self):
        """Remove segments outside correlation window"""
        now = datetime.utcnow()
        self.segments = [
            s for s in self.segments
            if (now - s.timestamp) <= self.window
        ]
```

2. **Update Correlation Engine Main App**

```python
# File: seefa-om/correlation-engine/app/main.py
# Add to existing file

from app.correlation.trace_synthesizer import TraceSynthesizer, TraceSegment

# In lifespan function:
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global trace_synthesizer

    # Initialize trace synthesizer
    trace_synthesizer = TraceSynthesizer(
        correlation_window_seconds=settings.corr_window_seconds
    )

    app.state.trace_synthesizer = trace_synthesizer

    # ... rest of existing code
```

3. **Add OTLP Trace Processing Route**

```python
# File: seefa-om/correlation-engine/app/routes/otlp.py
# Add to existing file

@router.post("/api/otlp/v1/traces")
async def ingest_otlp_traces(request: Request):
    """
    Receive OTLP traces from OTel SDK (Sense apps, MDSO otel_instrumentation)
    """
    body = await request.body()

    # Parse OTLP protobuf
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    trace_request = ExportTraceServiceRequest()
    trace_request.ParseFromString(body)

    # Extract trace segments for correlation
    for resource_span in trace_request.resource_spans:
        for scope_span in resource_span.scope_spans:
            for span in scope_span.spans:
                # Extract attributes
                circuit_id = None
                resource_id = None
                service = None

                for attr in span.attributes:
                    if attr.key == "circuit_id":
                        circuit_id = attr.value.string_value
                    elif attr.key == "resource_id":
                        resource_id = attr.value.string_value
                    elif attr.key == "service.name":
                        service = attr.value.string_value

                # Create trace segment
                segment = TraceSegment(
                    trace_id=span.trace_id.hex(),
                    span_id=span.span_id.hex(),
                    service=service or "unknown",
                    timestamp=datetime.utcfromtimestamp(span.start_time_unix_nano / 1e9),
                    circuit_id=circuit_id,
                    resource_id=resource_id,
                )

                # Add to synthesizer
                request.app.state.trace_synthesizer.add_segment(segment)

                # Check if we need to create bridge span
                parent = request.app.state.trace_synthesizer.find_parent_trace(segment)
                if parent:
                    bridge_span = request.app.state.trace_synthesizer.create_bridge_span(parent, segment)

                    # Export bridge span to Tempo
                    await export_synthetic_span_to_tempo(bridge_span)

    # Forward original traces to Tempo
    await forward_to_tempo(body)

    return {"status": "success"}
```

**Deployment**:

```bash
cd /home/user/correlation-station/seefa-om
docker-compose build correlation-engine
docker-compose up -d correlation-engine
```

---

## Phase 3: Sense Apps Instrumentation (Week 3)

### Step 3.1: Create Common OTel Instrumentation Library

```python
# File: sense-apps/common/otel_utils.py

"""
Common OpenTelemetry instrumentation for Sense apps
Provides dual export to Correlation Station and DataDog
"""

import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# DataDog exporter (optional)
try:
    from ddtrace.opentelemetry import TracerProvider as DDTracerProvider
    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False

def setup_otel_sense(
    service_name: str,
    service_version: str,
    environment: str = "dev",
    correlation_gateway: str = None,
    datadog_enabled: bool = True,
):
    """
    Setup OpenTelemetry for Sense apps with dual export

    Args:
        service_name: Service name (beorn, arda, palantir)
        service_version: Version string
        environment: Environment (dev/staging/prod)
        correlation_gateway: Correlation gateway endpoint
        datadog_enabled: Enable DataDog dual export
    """
    correlation_gateway = correlation_gateway or os.getenv("CORRELATION_GATEWAY_URL", "http://159.56.4.94:55681")

    # Resource attributes
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter (Correlation Gateway)
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{correlation_gateway}/v1/traces",
        timeout=30,
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Add DataDog exporter (optional)
    if datadog_enabled and DATADOG_AVAILABLE and os.getenv("DD_API_KEY"):
        from ddtrace.opentelemetry import DatadogSpanExporter
        dd_exporter = DatadogSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(dd_exporter))

    # Set global provider
    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    return trace.get_tracer(service_name)

def instrument_flask_app(app, service_name: str):
    """Instrument Flask app with OTel"""
    FlaskInstrumentor().instrument_app(app)

    # Add middleware to inject correlation keys
    @app.before_request
    def inject_correlation_keys():
        from flask import request, g
        from opentelemetry import baggage, context

        # Extract correlation keys from request
        circuit_id = request.headers.get("X-Circuit-Id") or request.json.get("circuit_id") if request.is_json else None
        product_id = request.headers.get("X-Product-Id") or request.json.get("product_id") if request.is_json else None
        resource_id = request.headers.get("X-Resource-Id") or request.json.get("resource_id") if request.is_json else None

        # Set baggage
        ctx = context.get_current()
        if circuit_id:
            ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
        if product_id:
            ctx = baggage.set_baggage("product_id", product_id, context=ctx)
        if resource_id:
            ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

        context.attach(ctx)

        # Add to span attributes
        span = trace.get_current_span()
        if span:
            if circuit_id:
                span.set_attribute("circuit_id", circuit_id)
            if product_id:
                span.set_attribute("product_id", product_id)
            if resource_id:
                span.set_attribute("resource_id", resource_id)

def instrument_fastapi_app(app, service_name: str):
    """Instrument FastAPI app with OTel"""
    FastAPIInstrumentor.instrument_app(app)

    # Add middleware for correlation keys
    from fastapi import Request
    from opentelemetry import baggage, context

    @app.middleware("http")
    async def inject_correlation_keys(request: Request, call_next):
        # Extract correlation keys
        circuit_id = request.headers.get("x-circuit-id")
        product_id = request.headers.get("x-product-id")
        resource_id = request.headers.get("x-resource-id")

        # Set baggage
        ctx = context.get_current()
        if circuit_id:
            ctx = baggage.set_baggage("circuit_id", circuit_id, context=ctx)
        if product_id:
            ctx = baggage.set_baggage("product_id", product_id, context=ctx)
        if resource_id:
            ctx = baggage.set_baggage("resource_id", resource_id, context=ctx)

        context.attach(ctx)

        # Add to span
        span = trace.get_current_span()
        if span:
            if circuit_id:
                span.set_attribute("circuit_id", circuit_id)
            if product_id:
                span.set_attribute("product_id", product_id)
            if resource_id:
                span.set_attribute("resource_id", resource_id)

        response = await call_next(request)
        return response
```

### Step 3.2: Update Beorn (Flask)

```python
# File: sense-apps/beorn/beorn_app/__init__.py
# Add to existing file after app creation

from common.otel_utils import setup_otel_sense, instrument_flask_app

# Setup OTel
tracer = setup_otel_sense(
    service_name="beorn",
    service_version=__version__,
    environment=os.getenv("DEPLOYMENT_ENV", "dev"),
)

# Instrument Flask app
instrument_flask_app(app, "beorn")
```

### Step 3.3: Update Arda (FastAPI)

```python
# File: sense-apps/arda/arda_app/main.py
# Add after app creation

from common.otel_utils import setup_otel_sense, instrument_fastapi_app

# Setup OTel
tracer = setup_otel_sense(
    service_name="arda",
    service_version="1.0.0",
    environment=os.getenv("DEPLOYMENT_ENV", "dev"),
)

# Instrument FastAPI app
instrument_fastapi_app(app, "arda")
```

---

## Phase 4: GitLab CI/CD Pipeline (Week 4)

### Create `.gitlab-ci.yml`

```yaml
# File: .gitlab-ci.yml

stages:
  - test
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"

# ============================================
# Test Stage
# ============================================

test:correlation-engine:
  stage: test
  image: python:3.11
  script:
    - cd seefa-om/correlation-engine
    - pip install -r requirements.txt
    - pytest tests/ -v --cov=app
  coverage: '/TOTAL.*\s+(\d+%)$/'

test:sense-apps:
  stage: test
  image: python:3.11
  parallel:
    matrix:
      - APP: [beorn, palantir, arda]
  script:
    - cd sense-apps/$APP
    - pip install -r requirements.txt
    - pytest tests/ -v

# ============================================
# Build Stage
# ============================================

build:correlation-engine:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd seefa-om
    - docker build -t correlation-engine:$CI_COMMIT_SHA ./correlation-engine
    - docker tag correlation-engine:$CI_COMMIT_SHA correlation-engine:latest
    - docker push correlation-engine:$CI_COMMIT_SHA
    - docker push correlation-engine:latest
  only:
    - main
    - develop

build:sense-apps:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  parallel:
    matrix:
      - APP: [beorn, palantir, arda]
  script:
    - cd sense-apps/$APP
    - docker build -t sense-$APP:$CI_COMMIT_SHA .
    - docker tag sense-$APP:$CI_COMMIT_SHA sense-$APP:latest
    - docker push sense-$APP:$CI_COMMIT_SHA
    - docker push sense-$APP:latest
  only:
    - main
    - develop

# ============================================
# Deploy Stage
# ============================================

deploy:meta-server:
  stage: deploy
  image: docker:latest
  script:
    - cd seefa-om
    - docker-compose pull
    - docker-compose up -d
    - docker-compose ps
  environment:
    name: production
    url: http://159.56.4.94:8443
  only:
    - main
  when: manual
```

---

## Validation Steps

### End-to-End Trace Validation

1. **Trigger MDSO Workflow**:
```bash
# Create network service via Beorn API
curl -X POST http://beorn:5001/beorn/api/v1/service/create \
  -H "Content-Type: application/json" \
  -H "X-Circuit-Id: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
    "circuit_id": "123e4567-e89b-12d3-a456-426614174000",
    "service_type": "FIA",
    "topology_id": "001461"
  }'
```

2. **Verify in Tempo** (Grafana → Explore → Tempo):
- Search by `circuit_id=123e4567-e89b-12d3-a456-426614174000`
- Should see:
  - Beorn span (create_network_service)
  - Synthetic bridge span (beorn_to_mdso_bridge)
  - MDSO scriptplan span (mdso.product.CircuitDetailsCollector)
  - Arda span (get_topology)

3. **Verify in Loki** (Grafana → Explore → Loki):
```logql
{circuit_id="123e4567-e89b-12d3-a456-426614174000"}
```

Should see logs from: Beorn → API-GW → Bpocore → Scriptplan → Arda

4. **Check Correlation Station Metrics**:
```bash
curl http://159.56.4.94:8080/metrics | grep correlation_events_total
```

---

## Troubleshooting

### MDSO Not Sending Telemetry

```bash
# Check OTel SDK initialized
docker exec scriptplan cat /bp2/log/splunk-logs/sensor-templates-otel.log | grep "OTel initialized"

# Check network connectivity
docker exec scriptplan curl -v http://159.56.4.94:55681/health

# Check Alloy is running
ssh user@47.43.111.107 "sudo systemctl status alloy"
```

### Sense Apps Not Propagating Context

```bash
# Check OTel instrumentation loaded
docker logs beorn | grep "OpenTelemetry initialized"

# Check trace headers in requests
docker exec beorn tcpdump -i any -A -s 0 'tcp port 4318' | grep traceparent
```

### Correlation Station Not Linking Traces

```bash
# Check trace synthesizer logs
docker logs correlation-engine | grep "bridge_span"

# Check correlation window
curl http://159.56.4.94:8080/api/correlations?circuit_id=<UUID>
```

---

## Next Steps

1. ✅ Phase 1: MDSO instrumentation complete
2. ✅ Phase 2: Correlation Station enhanced
3. ⬜ Phase 3: Sense apps instrumented (in progress)
4. ⬜ Phase 4: CI/CD pipeline deployed
5. ⬜ Phase 5: Grafana dashboards created (see dashboard JSON in repo)
6. ⬜ Phase 6: Production rollout

---

## Additional Resources

- **Architecture Diagrams**: See `ARCHITECTURE.md`
- **Signal Specifications**: See `SIGNAL_DESIGN.md`
- **Container Matrix**: See `CONTAINER_MATRIX.md`
- **Grafana Dashboards**: `seefa-om/observability-stack/grafana/provisioning/dashboards/`
- **Runbook**: `seefa-om/ops/runbook.md`

**Contact**: Derrick Golden (derrick.golden@charter.com)
