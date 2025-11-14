# ADR-004: Repository Pattern for MDSO Access

**Status**: Accepted
**Date**: 2025-11-14
**Authors**: Claude
**Priority**: High (Architecture)

## Context

The MDSO client was tightly coupled to HTTP implementation throughout the codebase:

```python
# BEFORE - Tight coupling
class MDSOLogCollector:
    def __init__(self, mdso_client: MDSOClient):
        self.mdso_client = mdso_client  # Direct dependency on HTTP client

    async def collect_logs(self):
        resources = await self.mdso_client.get_resources(...)  # HTTP call
```

### Problems

1. **Hard to Test**: Required complex mocking of HTTP calls
2. **No Abstraction**: Business logic coupled to HTTP implementation
3. **Limited Flexibility**: Can't swap implementations (cached, mock, etc.)
4. **No Centralized Logic**: Rate limiting, caching scattered across codebase

### Example Testing Pain
```python
# Complex test setup required
@patch('httpx.AsyncClient.get')
@patch('httpx.AsyncClient.post')
async def test_collect_logs(mock_post, mock_get):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"token": "...})
    mock_get.return_value = Mock(status_code=200, json=lambda: {"items": [...]})
    # 20+ lines of HTTP mock setup...
```

## Decision

**We will implement the Repository Pattern to abstract MDSO data access:**

1. **Define `MDSORepository` interface** (abstract base class)
2. **Create multiple implementations**:
   - `HTTPMDSORepository` - Production (wraps `MDSOClient`)
   - `InMemoryMDSORepository` - Testing (no external dependencies)
   - `CachedMDSORepository` - Performance (adds caching)
3. **Update consumers to accept repository** (backward compatible)
4. **Centralize cross-cutting concerns** (caching, rate limiting)

### Architecture

```
┌─────────────────────────────────────┐
│  Business Logic (MDSOLogCollector)  │
└────────────────┬────────────────────┘
                 │ depends on
                 ▼
      ┌──────────────────────┐
      │  MDSORepository      │  ◄─── Interface
      │  (Abstract)          │
      └──────────────────────┘
                 △
                 │ implements
    ┌────────────┼────────────┬─────────────┐
    │            │            │             │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐   ┌────▼─────┐
│  HTTP  │  │ Cached │  │InMemory│   │ Future   │
│  Repo  │  │  Repo  │  │  Repo  │   │ Impls    │
└────────┘  └────────┘  └────────┘   └──────────┘
```

### Interface Definition
```python
class MDSORepository(ABC):
    @abstractmethod
    async def get_resources(
        self,
        product_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MDSOResource]:
        pass

    @abstractmethod
    async def get_resource_by_id(self, resource_id: str) -> Optional[MDSOResource]:
        pass

    @abstractmethod
    async def get_orch_trace(
        self,
        circuit_id: str,
        resource_id: str
    ) -> Optional[MDSOOrchTrace]:
        pass
```

## Consequences

### Positive

✅ **Testability**
```python
# AFTER - Simple, fast tests
def test_collect_logs():
    repo = InMemoryMDSORepository()
    repo.add_resource(test_resource)
    collector = MDSOLogCollector(repo)
    # No mocking needed!
```

✅ **Flexibility**
- Swap implementations without changing business logic
- Easy to add caching, rate limiting, circuit breakers
- Support multiple backends (HTTP, database, gRPC)

✅ **Separation of Concerns**
- Business logic doesn't know about HTTP
- Repository handles data access details
- Single Responsibility Principle

✅ **Performance**
```python
# Add caching transparently
http_repo = HTTPMDSORepository(client)
cached_repo = CachedMDSORepository(http_repo, ttl_seconds=300)
collector = MDSOLogCollector(cached_repo)  # Automatic caching!
```

### Negative

⚠️ **Slight Complexity**: Extra abstraction layer
⚠️ **Learning Curve**: Team needs to understand pattern
⚠️ **Migration Effort**: Updating existing code

## Alternatives Considered

### Alternative 1: Direct Client Usage (Status Quo)
- **Pros**: Simple, no abstraction
- **Cons**: Hard to test, tightly coupled, inflexible
- **Why not chosen**: Testing pain outweighs simplicity

### Alternative 2: Service Layer Pattern
- **Pros**: More comprehensive than repository
- **Cons**: Heavier, more complex than needed
- **Why not chosen**: Repository sufficient for our use case

### Alternative 3: Facade Pattern
- **Pros**: Simpler than repository
- **Cons**: Less flexible, doesn't enable multiple implementations
- **Why not chosen**: Need ability to swap implementations

### Alternative 4: Use Existing DI Library
- **Pros**: Battle-tested, feature-rich
- **Cons**: Heavy dependency, overkill for our needs
- **Why not chosen**: Repository + FastAPI DI sufficient

## Implementation

### Phase 1: Create Repository Classes (✅ Complete)
```python
# app/mdso/repository.py
- MDSORepository (interface)
- HTTPMDSORepository (production)
- InMemoryMDSORepository (testing)
- CachedMDSORepository (performance)
```

### Phase 2: Update Consumers (✅ Complete)
```python
# Backward compatible
class MDSOLogCollector:
    def __init__(self, mdso_source: Union[MDSOClient, MDSORepository]):
        if isinstance(mdso_source, MDSORepository):
            self.mdso_repo = mdso_source
        else:
            # Wrap client in repository
            self.mdso_repo = HTTPMDSORepository(mdso_source)
```

### Phase 3: Add Tests (✅ Complete)
- 40+ tests in `test_mdso_repository.py`
- Test all implementations
- Verify interface compliance

### Phase 4: Documentation (✅ Complete)
- Created `REPOSITORY_PATTERN.md`
- Usage examples
- Migration guide

### Phase 5: Gradual Migration (In Progress)
- [x] `MDSOLogCollector` updated
- [ ] FastAPI routes updated
- [ ] Add caching where beneficial

## Usage Examples

### Production
```python
# Create HTTP repository
client = MDSOClient(base_url=..., username=..., password=...)
repo = HTTPMDSORepository(client)

# Optional: Add caching
cached_repo = CachedMDSORepository(repo, ttl_seconds=300)

# Use in application
collector = MDSOLogCollector(cached_repo)
```

### Testing
```python
# Create in-memory repository
repo = InMemoryMDSORepository()

# Populate test data
resource = MDSOResource(id="test-123", ...)
repo.add_resource(resource)

# Test without external dependencies
collector = MDSOLogCollector(repo)
logs = await collector.collect_product_logs(...)
```

### FastAPI Route
```python
@router.get("/resources/{product}")
async def get_resources(
    product: str,
    repo: MDSORepository = Depends(get_mdso_repository)
):
    resources = await repo.get_resources(product)
    return {"resources": resources}
```

## Benefits Realized

### Before (Lines of test code)
```python
# 30+ lines of complex mocking
@patch('httpx.AsyncClient.get')
@patch('httpx.AsyncClient.post')
async def test_collect_logs(mock_post, mock_get):
    mock_post.return_value = Mock(...)
    mock_get.return_value = Mock(...)
    # ... 20 more lines ...
```

### After (Lines of test code)
```python
# 5 lines, fast, deterministic
async def test_collect_logs():
    repo = InMemoryMDSORepository()
    repo.add_resource(test_resource)
    logs = await collector.collect_product_logs(...)
    assert len(logs) == 1
```

**Result**: 80% reduction in test complexity

## Future Enhancements

Potential future repository implementations:

1. **RateLimitedMDSORepository**: Automatic rate limiting
2. **RetryMDSORepository**: Exponential backoff retries
3. **DatabaseMDSORepository**: Cache in PostgreSQL/Redis
4. **CompositeMDSORepository**: Try cache → database → HTTP
5. **ReadThroughCacheRepository**: Auto-populate cache on miss

## Monitoring

Track repository performance:
```python
# Metrics to track
repository_calls = Counter('mdso_repository_calls_total', ['implementation', 'method'])
repository_duration = Histogram('mdso_repository_duration_seconds', ['implementation', 'method'])
cache_hits = Counter('mdso_repository_cache_hits_total')
```

## References

- [Repository Pattern - Martin Fowler](https://martinfowler.com/eaaCatalog/repository.html)
- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Documentation: REPOSITORY_PATTERN.md](../../correlation-engine/app/mdso/REPOSITORY_PATTERN.md)
- [Tests: test_mdso_repository.py](../../correlation-engine/tests/test_mdso_repository.py)

## Status History

- **2025-11-14**: Accepted and implemented
- **Future**: Consider adding more implementations (database, gRPC)
