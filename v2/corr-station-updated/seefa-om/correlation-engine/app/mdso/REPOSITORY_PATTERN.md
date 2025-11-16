# MDSO (Multi-Domain Service Orchestrator) Repository Pattern

## Overview

The Repository Pattern provides an abstraction layer between the application logic and data access for MDSO operations. This pattern enables:

- **Easy Testing**: Mock repositories for unit tests without external dependencies
- **Flexibility**: Swap implementations (HTTP, cached, in-memory) without changing business logic
- **Separation of Concerns**: Business logic doesn't depend on HTTP client details
- **Centralized Logic**: Rate limiting, caching, and retry logic in one place

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Application Logic                      │
│     (MDSOLogCollector, Routes, etc.)            │
└────────────────┬────────────────────────────────┘
                 │ depends on
                 ▼
      ┌──────────────────────┐
      │  MDSORepository      │  ◄─── Abstract Interface
      │  (ABC)               │
      └──────────────────────┘
                 △
                 │ implements
    ┌────────────┼────────────┬─────────────┐
    │            │            │             │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐   ┌────▼─────┐
│  HTTP  │  │ Cached │  │InMemory│   │ Future   │
│  Repo  │  │  Repo  │  │  Repo  │   │ Impls    │
└────────┘  └────────┘  └────────┘   └──────────┘
    │
    ▼
┌────────────┐
│ MDSOClient │
└────────────┘
```

## Available Implementations

### 1. HTTPMDSORepository (Production)

**Use Case**: Production environment with real MDSO API

```python
from app.mdso import MDSOClient, HTTPMDSORepository

# Create MDSO client
client = MDSOClient(
    base_url="https://mdso.example.com",
    username="user",
    password="pass",
    verify_ssl=True
)

# Wrap in repository
repo = HTTPMDSORepository(client)

# Use repository
resources = await repo.get_resources("ServiceMapper")
```

**Features**:
- Delegates to MDSOClient for HTTP operations
- Production-ready error handling
- OpenTelemetry tracing
- SSL verification and authentication

### 2. InMemoryMDSORepository (Testing)

**Use Case**: Unit tests, integration tests, local development

```python
from app.mdso import InMemoryMDSORepository
from app.mdso.models import MDSOResource

# Create repository
repo = InMemoryMDSORepository()

# Populate test data
resource = MDSOResource(
    id="test-123",
    label="test-circuit",
    circuit_id="CIRCUIT-123",
    product_name="ServiceMapper",
    orch_state="completed",
    device_tid="device-456",
    created_at="2025-10-15T10:30:45Z"
)
repo.add_resource(resource)

# Use like any repository
resources = await repo.get_resources("ServiceMapper")
assert len(resources) == 1
```

**Features**:
- No external dependencies
- Fast for testing
- Predictable data
- Methods to add/clear test data

### 3. CachedMDSORepository (Performance)

**Use Case**: Reduce MDSO API load, improve response times

```python
from app.mdso import HTTPMDSORepository, CachedMDSORepository

# Create underlying repository
http_repo = HTTPMDSORepository(client)

# Wrap with caching (5 minute TTL)
cached_repo = CachedMDSORepository(http_repo, ttl_seconds=300)

# First call - fetches from MDSO
resources = await cached_repo.get_resources("ServiceMapper")

# Second call within 5 minutes - returns cached data
resources = await cached_repo.get_resources("ServiceMapper")
```

**Features**:
- TTL-based caching
- Reduces API calls
- Transparent caching (same interface)
- Can wrap any repository implementation

## Interface Methods

All repository implementations must provide:

### `get_resources(product_name, filters=None)`

Get all resources for a product, optionally filtered.

```python
resources = await repo.get_resources("ServiceMapper")
resources = await repo.get_resources("ServiceMapper", filters={"orch_state": "completed"})
```

### `get_resource_by_id(resource_id)`

Get a single resource by ID.

```python
resource = await repo.get_resource_by_id("resource-123")
if resource:
    print(f"Found: {resource.circuit_id}")
```

### `get_orch_trace(circuit_id, resource_id)`

Get orchestration trace for a circuit.

```python
trace = await repo.get_orch_trace("CIRCUIT-123", "resource-123")
if trace:
    errors = trace.get_errors()
```

### `search_resources_by_date(product_name, start_date, end_date=None)`

Search resources within a date range.

```python
from datetime import datetime, timedelta

yesterday = datetime.now() - timedelta(days=1)
resources = await repo.search_resources_by_date("ServiceMapper", yesterday)
```

### `get_errors_for_resource(resource_id)`

Get all errors for a resource from its orch trace.

```python
errors = await repo.get_errors_for_resource("resource-123")
for error in errors:
    print(f"Error: {error['error']} in {error.get('process')}")
```

### `close()`

Close connections and cleanup.

```python
await repo.close()
```

## Usage in Application Code

### MDSOLogCollector (Updated)

The `MDSOLogCollector` now accepts either `MDSOClient` (legacy) or `MDSORepository` (preferred):

```python
from app.mdso import MDSOLogCollector, HTTPMDSORepository

# Using repository (preferred)
repo = HTTPMDSORepository(mdso_client)
collector = MDSOLogCollector(repo)

# Legacy (still works)
collector = MDSOLogCollector(mdso_client)  # Auto-wrapped in repository
```

### FastAPI Routes

```python
from fastapi import APIRouter, Depends
from app.mdso import MDSORepository, HTTPMDSORepository

router = APIRouter()

def get_mdso_repo() -> MDSORepository:
    """Dependency injection for MDSO repository"""
    from app.main import app
    mdso_client = app.state.mdso_client
    return HTTPMDSORepository(mdso_client)

@router.get("/products/{product_name}/resources")
async def get_product_resources(
    product_name: str,
    repo: MDSORepository = Depends(get_mdso_repo)
):
    resources = await repo.get_resources(product_name)
    return {"resources": [r.dict() for r in resources]}
```

## Testing Examples

### Unit Tests with In-Memory Repository

```python
import pytest
from app.mdso import InMemoryMDSORepository, MDSOLogCollector
from app.mdso.models import MDSOResource, MDSOOrchTrace

@pytest.fixture
def mdso_repo():
    """Create repository with test data"""
    repo = InMemoryMDSORepository()

    # Add test resource
    resource = MDSOResource(
        id="test-123",
        label="test-circuit",
        circuit_id="CIRCUIT-123",
        product_name="ServiceMapper",
        orch_state="failed",
        device_tid="device-456",
        created_at="2025-10-15T10:30:45Z"
    )
    repo.add_resource(resource)

    # Add orch trace with error
    trace = MDSOOrchTrace(
        circuit_id="CIRCUIT-123",
        resource_id="test-123",
        trace_data=[
            {"process": "validate", "status": "error", "error": "Validation failed"}
        ],
        timestamp="2025-10-15T10:30:45Z"
    )
    repo.add_orch_trace("CIRCUIT-123", "test-123", trace)

    return repo

@pytest.mark.asyncio
async def test_collect_logs_with_errors(mdso_repo):
    """Test log collection with errors"""
    collector = MDSOLogCollector(mdso_repo)

    logs = await collector.collect_product_logs(
        product_type="service_mapper",
        product_name="ServiceMapper",
        time_range_hours=24
    )

    assert len(logs) == 1
    assert logs[0]["circuit_id"] == "CIRCUIT-123"
    assert "Validation failed" in logs[0]["error"]
```

### Mocking with pytest-mock

```python
@pytest.mark.asyncio
async def test_log_collector_with_mock_repo(mocker):
    """Test with mock repository"""
    mock_repo = mocker.Mock(spec=MDSORepository)
    mock_repo.get_resources = AsyncMock(return_value=[])
    mock_repo.get_orch_trace = AsyncMock(return_value=None)

    collector = MDSOLogCollector(mock_repo)

    logs = await collector.collect_product_logs(
        product_type="service_mapper",
        product_name="ServiceMapper",
        time_range_hours=3
    )

    assert len(logs) == 0
    mock_repo.get_resources.assert_called_once()
```

## Benefits

### 1. Testability

**Before (Tightly Coupled to HTTP Client)**:
```python
# Hard to test - requires mocking HTTP client internals
async def test_collect_logs():
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value = Mock(status_code=200, json=lambda: {...})
        # Complex setup for every HTTP call
```

**After (Repository Pattern)**:
```python
# Easy to test - use in-memory repository
async def test_collect_logs():
    repo = InMemoryMDSORepository()
    repo.add_resource(test_resource)
    # Simple, fast, no mocking
```

### 2. Flexibility

Easily swap implementations:
- Development: Use `InMemoryMDSORepository` with sample data
- Testing: Use `InMemoryMDSORepository` or mocks
- Production: Use `HTTPMDSORepository` with caching
- Future: Could add database-backed repository, gRPC client, etc.

### 3. Performance

```python
# Without caching - every call hits MDSO API
resources = await client.get_resources("ServiceMapper")  # HTTP call
resources = await client.get_resources("ServiceMapper")  # HTTP call again

# With cached repository - second call uses cache
cached_repo = CachedMDSORepository(http_repo, ttl_seconds=300)
resources = await cached_repo.get_resources("ServiceMapper")  # HTTP call
resources = await cached_repo.get_resources("ServiceMapper")  # Cached!
```

### 4. Centralized Logic

Future enhancements can be added to the repository without changing callers:
- Rate limiting
- Circuit breakers
- Metrics/monitoring
- Request batching
- Background prefetching

## Migration Guide

### For Existing Code Using MDSOClient

**Old Code**:
```python
from app.mdso import MDSOClient

client = MDSOClient(...)
collector = MDSOLogCollector(client)
resources = await client.get_resources("ServiceMapper")
```

**New Code (Backward Compatible)**:
```python
from app.mdso import MDSOClient, HTTPMDSORepository

client = MDSOClient(...)

# Option 1: Direct use (auto-wrapped in repository internally)
collector = MDSOLogCollector(client)  # Still works!

# Option 2: Explicit repository (recommended)
repo = HTTPMDSORepository(client)
collector = MDSOLogCollector(repo)

# Option 3: With caching
repo = HTTPMDSORepository(client)
cached_repo = CachedMDSORepository(repo, ttl_seconds=300)
collector = MDSOLogCollector(cached_repo)
```

### Gradual Migration

1. **Phase 1**: Update `MDSOLogCollector` to accept repository (✅ Done)
2. **Phase 2**: Update routes and application code to use repositories
3. **Phase 3**: Add caching where beneficial
4. **Phase 4**: Deprecate direct `MDSOClient` usage in favor of repositories

## Best Practices

1. **Use Dependency Injection**: Pass repositories as constructor arguments
2. **Program to Interface**: Accept `MDSORepository`, not concrete types
3. **Choose Right Implementation**:
   - Production: `HTTPMDSORepository` (optionally with `CachedMDSORepository`)
   - Unit Tests: `InMemoryMDSORepository`
   - Integration Tests: `HTTPMDSORepository` with test MDSO instance
4. **Clean Up**: Always call `await repo.close()` when done
5. **TTL Configuration**: Choose cache TTL based on data freshness requirements

## Future Enhancements

Potential future repository implementations:

- **RateLimitedMDSORepository**: Automatic rate limiting wrapper
- **RetryMDSORepository**: Automatic retry with exponential backoff
- **DatabaseMDSORepository**: Cache in PostgreSQL/Redis for persistence
- **CompositeMDSORepository**: Try multiple repositories (e.g., cache → database → HTTP)
- **ReadThroughCacheRepository**: Automatically populate cache on miss

## Related Documentation

- [HORIZONTAL_SCALING.md](../../HORIZONTAL_SCALING.md) - Scaling strategies
- [TEST_IMPROVEMENTS.md](../../TEST_IMPROVEMENTS.md) - Testing enhancements
- [FIXES_SUMMARY.md](../../FIXES_SUMMARY.md) - Security and reliability fixes
