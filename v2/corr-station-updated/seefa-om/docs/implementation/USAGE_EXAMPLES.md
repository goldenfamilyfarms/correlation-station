# Usage Examples: End-to-End Tracing

## Example 1: Manual Span Creation in SENSE Apps

Add custom spans to track specific operations:

```python
# In any SENSE app endpoint (arda/beorn/palantir)
from common_sense.telemetry import get_tracer, add_span_attributes, set_baggage_context

tracer = get_tracer(__name__)

@router.post("/api/v1/design")
async def create_design(request: DesignRequest):
    # Create a span for the entire operation
    with tracer.start_as_current_span(
        "design.create",
        attributes={
            "circuit_id": request.circuit_id,
            "design_type": request.design_type,
        }
    ) as span:
        # Set baggage for cross-service propagation
        ctx = set_baggage_context(
            circuit_id=request.circuit_id,
            product_type="design"
        )
        
        # Child span for MDSO (Multi-Domain Service Orchestrator) call
        with tracer.start_as_current_span(
            "mdso.create_resource",
            context=ctx
        ):
            result = await mdso_client.create_resource(request)
            add_span_attributes(
                resource_id=result.id,
                orch_state=result.state
            )
        
        # Child span for database operation
        with tracer.start_as_current_span("db.save_design"):
            await db.save(result)
        
        span.set_attribute("design.status", "success")
        return result
```

## Example 2: Trace Propagation Between Services

ARDA calls BEORN with automatic trace propagation:

```python
# In ARDA
import httpx
from common_sense.telemetry import get_tracer

tracer = get_tracer(__name__)

async def call_beorn(circuit_id: str):
    with tracer.start_as_current_span("arda.call_beorn") as span:
        # httpx is auto-instrumented, trace context propagated automatically
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://beorn:5002/api/circuit/{circuit_id}"
            )
            span.set_attribute("beorn.response_code", response.status_code)
            return response.json()
```

In BEORN, the trace continues automatically:

```python
# In BEORN - no changes needed, FastAPI auto-instrumentation handles it
@router.get("/api/circuit/{circuit_id}")
async def get_circuit(circuit_id: str):
    # This span is automatically linked to ARDA's trace
    with tracer.start_as_current_span("beorn.get_circuit"):
        return await fetch_circuit(circuit_id)
```

## Example 3: Query Correlations by Circuit ID

```bash
# Get all correlations for a circuit
curl "http://localhost:8080/api/correlations?circuit_id=80.L1XX.005054..CHTR&limit=50"

# Response:
{
  "correlations": [
    {
      "correlation_id": "uuid",
      "trace_id": "abc123",
      "circuit_id": "80.L1XX.005054..CHTR",
      "service": "arda",
      "log_count": 15,
      "span_count": 8,
      "timestamp": "2024-01-15T10:30:00Z",
      "mdso_context": {
        "resource_id": "res-123",
        "product_type": "service_mapper",
        "orch_state": "FAILED"
      }
    }
  ]
}
```

## Example 4: Trigger MDSO Collection On-Demand

```bash
# Collect ServiceMapper logs from last 6 hours
curl -X POST http://localhost:8080/api/mdso/collect \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "service_mapper",
    "product_name": "ServiceMapper",
    "time_range_hours": 6
  }'

# Response:
{
  "status": "success",
  "message": "Collected logs for ServiceMapper",
  "logs_collected": 142,
  "errors_found": 23
}
```

## Example 5: Add Span Events for Key Milestones

```python
from common_sense.telemetry import get_current_span, add_span_event

async def process_order(order_id: str):
    span = get_current_span()
    
    # Add event when order validated
    add_span_event("order.validated", {
        "order_id": order_id,
        "validation_time_ms": 45
    })
    
    # Process...
    
    # Add event when sent to MDSO
    add_span_event("mdso.request_sent", {
        "endpoint": "/api/resources",
        "payload_size": 1024
    })
    
    # Add event on completion
    add_span_event("order.completed", {
        "duration_ms": 1250,
        "status": "success"
    })
```

## Example 6: Baggage for Cross-Service Context

```python
from common_sense.telemetry import set_baggage_context, get_tracer
from opentelemetry import baggage

tracer = get_tracer(__name__)

async def handle_request(circuit_id: str, customer_id: str):
    # Set baggage that will propagate to all downstream services
    ctx = set_baggage_context(
        circuit_id=circuit_id,
        customer_id=customer_id,
        request_source="arda"
    )
    
    with tracer.start_as_current_span("handle_request", context=ctx):
        # Call another service - baggage propagates automatically
        await call_downstream_service()

# In downstream service, retrieve baggage
def get_circuit_from_context():
    circuit_id = baggage.get_baggage("circuit_id")
    return circuit_id
```

## Example 7: Query Traces in Grafana Tempo

### TraceQL Queries:

```traceql
# Find all traces for a circuit
{ resource.service.name="arda" && mdso.circuit_id="80.L1XX.005054..CHTR" }

# Find failed MDSO operations
{ mdso.orch_state="FAILED" }

# Find slow operations (>5s)
{ duration > 5s && resource.service.namespace="sense" }

# Find traces with specific error
{ mdso.defect_code="DE-1000" }
```

## Example 8: Query Logs in Grafana Loki

### LogQL Queries:

```logql
# All MDSO-related logs
{service="correlation-engine"} |= "mdso"

# Errors for specific circuit
{service="arda"} | json | circuit_id="80.L1XX.005054..CHTR" | level="error"

# MDSO collection events
{service="correlation-engine"} | json | msg="mdso_resources_fetched"

# Correlation events
{service="correlation-engine"} | json | msg="correlation_window_closed"
```

## Example 9: Create Grafana Dashboard

Example dashboard JSON for MDSO metrics:

```json
{
  "panels": [
    {
      "title": "MDSO Logs Collected",
      "targets": [
        {
          "expr": "rate(log_records_received_total{source=\"mdso\"}[5m])"
        }
      ]
    },
    {
      "title": "Errors by Defect Code",
      "targets": [
        {
          "expr": "sum by (defect_code) (mdso_errors_total)"
        }
      ]
    },
    {
      "title": "Correlation Events",
      "targets": [
        {
          "expr": "rate(correlation_events_total[5m])"
        }
      ]
    }
  ]
}
```

## Example 10: Error Handling with Spans

```python
from opentelemetry.trace import Status, StatusCode

async def risky_operation():
    with tracer.start_as_current_span("risky_operation") as span:
        try:
            result = await perform_operation()
            span.set_status(Status(StatusCode.OK))
            return result
        except ConnectionError as e:
            span.set_status(Status(StatusCode.ERROR, "Connection failed"))
            span.record_exception(e)
            span.set_attribute("error.type", "connection")
            raise
        except ValueError as e:
            span.set_status(Status(StatusCode.ERROR, "Invalid data"))
            span.record_exception(e)
            span.set_attribute("error.type", "validation")
            raise
```

## Example 11: Scheduled MDSO Collection Configuration

Configure multiple products for scheduled collection:

```python
# In correlation engine config or environment
MDSO_PRODUCTS = [
    {
        "product_type": "service_mapper",
        "product_name": "ServiceMapper",
        "time_range_hours": 3
    },
    {
        "product_type": "network_service",
        "product_name": "NetworkService",
        "time_range_hours": 6
    },
    {
        "product_type": "disconnect_mapper",
        "product_name": "DisconnectMapper",
        "time_range_hours": 3
    }
]
```

## Example 12: Custom Metrics from Spans

Export custom metrics based on span attributes:

```python
from prometheus_client import Counter, Histogram

# Define metrics
mdso_operations = Counter(
    'mdso_operations_total',
    'MDSO operations',
    ['product_type', 'status']
)

mdso_duration = Histogram(
    'mdso_operation_duration_seconds',
    'MDSO operation duration',
    ['product_type']
)

# Use in code
async def collect_logs(product_type: str):
    with tracer.start_as_current_span("mdso.collect") as span:
        start = time.time()
        try:
            result = await mdso_client.get_resources(product_type)
            mdso_operations.labels(product_type=product_type, status="success").inc()
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            mdso_operations.labels(product_type=product_type, status="error").inc()
            span.set_status(Status(StatusCode.ERROR))
            raise
        finally:
            duration = time.time() - start
            mdso_duration.labels(product_type=product_type).observe(duration)
```
