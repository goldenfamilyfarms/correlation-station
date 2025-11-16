# SEEFA Observability Implementation

This folder contains the enhanced implementation for end-to-end tracing across SENSE apps and MDSO (Multi-Domain Service Orchestrator).

## Structure

```
implementation/
├── common_sense_telemetry/     # Shared OpenTelemetry instrumentation for SENSE apps
├── sense_apps_instrumented/    # Updated SENSE app files with OTel
├── correlation_engine_enhanced/ # Enhanced correlation engine with MDSO integration
└── README.md
```

## Implementation Phases

### Phase 1: SENSE Apps Instrumentation
- Add OpenTelemetry to arda, beorn, palantir
- Shared telemetry module in common_sense
- Auto-instrumentation for FastAPI, httpx, requests

### Phase 2: MDSO Integration into Correlation Engine
- MDSO API client
- Log collector with OTel spans
- Error analyzer with trace context
- MDSO-specific correlation logic

### Phase 3: End-to-End Tracing
- Trace propagation SENSE → MDSO → SENSE
- Circuit ID correlation
- Baggage propagation for context

## Deployment Steps

1. **Deploy common_sense_telemetry module:**
   ```bash
   cp -r common_sense_telemetry/* /path/to/sense-apps/common_sense/telemetry/
   ```

2. **Update SENSE apps:**
   ```bash
   # For each app (arda, beorn, palantir)
   cp sense_apps_instrumented/requirements.txt /path/to/sense-apps/arda/
   cp sense_apps_instrumented/arda_main.py /path/to/sense-apps/arda/arda_app/main.py
   ```

3. **Deploy enhanced correlation engine:**
   ```bash
   cp -r correlation_engine_enhanced/app/* /path/to/seefa-om/correlation-engine/app/
   cp correlation_engine_enhanced/requirements.txt /path/to/seefa-om/correlation-engine/
   ```

4. **Set environment variables:**
   ```bash
   # SENSE apps
   export OTEL_EXPORTER_OTLP_ENDPOINT="http://correlation-engine:8080"
   export OTEL_SERVICE_NAME="arda"  # or beorn, palantir
   
   # Correlation engine
   export MDSO_URL="https://mdso.example.com"
   export MDSO_USER="user"
   export MDSO_PASS="pass"
   ```

## Key Features

- **Automatic trace propagation** via W3C Trace Context headers
- **Circuit ID correlation** for MDSO operations without trace_id
- **Baggage propagation** for cross-service context
- **Real-time error detection** replacing batch jobs
- **Unified observability** in Grafana/Tempo/Loki
