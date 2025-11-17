# Sense Common - Shared Library

Shared functionality for SEEFA Sense applications (Palantir, Arda, Beorn).

## Overview

This library provides common functionality to eliminate code duplication across the three Sense applications:
- **Palantir**: Data aggregation service
- **Arda**: Inventory SEEFA design service
- **Beorn**: Authentication & identity service

## Features

- ✅ **Standardized Configuration** - Pydantic Settings-based configuration
- ✅ **HTTP Client** - Async HTTP client with retry, circuit breaker, and SSL support
- ✅ **Observability** - OpenTelemetry instrumentation setup
- ✅ **Type Safety** - Full type hints and validation
- ✅ **Testability** - Easy to mock and test

## Installation

```bash
# From source
cd shared-libs
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

## Usage

### Configuration

```python
from sense_common.config import BaseServiceConfig

class PalantirConfig(BaseServiceConfig):
    service_name: str = "palantir"
    port: int = 5002

    # Add Palantir-specific config here
    enable_circuit_testing: bool = True

# Load from environment
config = PalantirConfig()

# Access MDSO (Multi-Domain Service Orchestrator) config
mdso_config = config.get_mdso_config()
print(mdso_config.mdso_base_url)

# Access OTEL config
otel_config = config.get_otel_config()
print(otel_config.otel_endpoint)
```

### HTTP Client

```python
from sense_common.http import AsyncHTTPClient, RetryConfig

# Create client
async with AsyncHTTPClient(
    base_url="https://api.example.com",
    timeout=30.0,
    verify_ssl=True,
    retry_config=RetryConfig(max_attempts=3),
    enable_circuit_breaker=True
) as client:
    # Make requests with automatic retry
    response = await client.get("/endpoint", retry=True)
    data = response.json()

    # POST with retry
    response = await client.post(
        "/endpoint",
        json={"key": "value"},
        retry=True
    )
```

### Observability

```python
from sense_common.observability import setup_observability, get_tracer, get_meter

# Setup OTEL instrumentation
setup_observability(
    service_name="palantir",
    service_version="1.0.0",
    environment="prod",
    endpoint="http://gateway:4318",
    protocol="http"
)

# Get tracer for instrumentation
tracer = get_tracer(__name__)

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("custom.attr", "value")
    # Your code here

# Get meter for custom metrics
meter = get_meter(__name__)
counter = meter.create_counter("requests_total")
counter.add(1, {"endpoint": "/api/health"})
```

## Architecture

```
sense_common/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── base.py          # Base configuration classes
├── http/
│   ├── __init__.py
│   └── client.py        # HTTP client with retry/circuit breaker
└── observability/
    ├── __init__.py
    └── otel.py          # OTEL setup utilities
```

## Benefits

### Before (Duplicated Code)

```
sense-apps/
├── palantir/common_sense/    # ~3,100 lines
├── arda/common_sense/        # ~3,100 lines (duplicate!)
└── beorn/common_sense/       # ~3,100 lines (duplicate!)

Total: ~9,300 lines of duplicated code!
```

### After (Shared Library)

```
shared-libs/sense_common/     # ~1,500 lines (single source of truth)
sense-apps/
├── palantir/ → uses sense_common
├── arda/ → uses sense_common
└── beorn/ → uses sense_common

Eliminated: ~7,800 lines of duplication!
```

## Migration Guide

### Step 1: Install shared library

```bash
cd shared-libs
pip install -e .
```

### Step 2: Update configuration

```python
# Old (hardcoded)
class Config:
    def __init__(self):
        self.MDSO_IP = "50.84.225.107"  # Hardcoded!

# New (environment-based)
from sense_common.config import BaseServiceConfig

class PalantirConfig(BaseServiceConfig):
    service_name: str = "palantir"
    # Config loaded from environment automatically
```

### Step 3: Replace HTTP client

```python
# Old (manual retry logic)
import requests
response = requests.get(url, verify=False)

# New (automatic retry + circuit breaker)
from sense_common.http import AsyncHTTPClient

async with AsyncHTTPClient(base_url=url) as client:
    response = await client.get("/endpoint", retry=True)
```

### Step 4: Setup observability

```python
# Old (duplicated setup code)
# ... 50+ lines of OTEL setup in each app ...

# New (one line)
from sense_common.observability import setup_observability

setup_observability(service_name="palantir")
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=sense_common --cov-report=html

# Type checking
mypy sense_common
```

## Contributing

1. Add new shared functionality to appropriate module
2. Add tests to `tests/` directory
3. Update version in `setup.py`
4. Update this README with usage examples

## License

MIT License - See LICENSE file for details
