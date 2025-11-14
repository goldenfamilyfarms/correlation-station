# Changelog

## [2.0.0] - 2025-01-XX

### Added
- **MDSO Integration**: Automated log collection from MDSO products
  - Scheduled collection with configurable intervals
  - Support for ServiceMapper, NetworkService, DisconnectMapper products
  - Orchestration trace retrieval and error extraction
  
- **Enhanced Correlation**:
  - Multi-key correlation (trace_id, circuit_id, resource_id, product_id)
  - MDSO context enrichment (device_tid, orch_state, management_ip)
  - Circuit-based correlation when trace_id is unavailable
  
- **Error Analysis**:
  - Pattern-based error categorization
  - Defect code assignment (DE-1000 through DE-1010)
  - Error summary and statistics
  
- **New API Endpoints**:
  - `POST /api/mdso/collect` - Trigger manual MDSO collection
  - `GET /api/mdso/products` - List available MDSO products
  - `GET /api/mdso/status` - Check MDSO integration status

### Changed
- Version bumped to 2.0.0
- Enhanced health check to include MDSO component status
- Updated documentation with MDSO integration guide

### Dependencies
- Added pandas==2.0.3
- Added pendulum==2.0.5
- Added configparser==5.3.0
- Added requests==2.31.0
- Added openpyxl==3.1.2

## [1.0.0] - 2025-01-XX

### Initial Release
- Real-time log and trace correlation
- OTLP ingestion support (JSON and Protobuf)
- Trace synthesis with bridge spans
- Multi-backend export (Loki, Tempo, Prometheus, Datadog)
- Circuit breaker pattern for export resilience
- Prometheus metrics exposure
- OpenTelemetry self-monitoring
