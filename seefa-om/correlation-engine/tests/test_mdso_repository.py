"""Tests for MDSO Repository Pattern"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from app.mdso.repository import (
    MDSORepository,
    HTTPMDSORepository,
    InMemoryMDSORepository,
    CachedMDSORepository,
)
from app.mdso.models import MDSOResource, MDSOOrchTrace


class TestInMemoryMDSORepository:
    """Test in-memory repository implementation"""

    @pytest.fixture
    def repo(self):
        """Create fresh repository for each test"""
        return InMemoryMDSORepository()

    @pytest.fixture
    def sample_resource(self):
        """Create sample resource"""
        return MDSOResource(
            id="resource-123",
            label="test-circuit",
            circuit_id="CIRCUIT-123",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="device-456",
            created_at=datetime.now().isoformat()
        )

    @pytest.mark.asyncio
    async def test_add_and_get_resource(self, repo, sample_resource):
        """Should store and retrieve resource"""
        repo.add_resource(sample_resource)

        result = await repo.get_resource_by_id("resource-123")

        assert result is not None
        assert result.id == "resource-123"
        assert result.circuit_id == "CIRCUIT-123"

    @pytest.mark.asyncio
    async def test_get_nonexistent_resource_returns_none(self, repo):
        """Should return None for non-existent resource"""
        result = await repo.get_resource_by_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_resources_by_product(self, repo):
        """Should filter resources by product name"""
        resource1 = MDSOResource(
            id="res-1",
            label="circuit-1",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-1",
            created_at=datetime.now().isoformat()
        )
        resource2 = MDSOResource(
            id="res-2",
            label="circuit-2",
            product_name="NetworkService",
            orch_state="completed",
            device_tid="dev-2",
            created_at=datetime.now().isoformat()
        )

        repo.add_resource(resource1)
        repo.add_resource(resource2)

        results = await repo.get_resources("ServiceMapper")

        assert len(results) == 1
        assert results[0].id == "res-1"

    @pytest.mark.asyncio
    async def test_get_resources_with_filters(self, repo):
        """Should apply additional filters"""
        resource1 = MDSOResource(
            id="res-1",
            label="circuit-1",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-1",
            created_at=datetime.now().isoformat()
        )
        resource2 = MDSOResource(
            id="res-2",
            label="circuit-2",
            product_name="ServiceMapper",
            orch_state="failed",
            device_tid="dev-2",
            created_at=datetime.now().isoformat()
        )

        repo.add_resource(resource1)
        repo.add_resource(resource2)

        results = await repo.get_resources("ServiceMapper", filters={"orch_state": "completed"})

        assert len(results) == 1
        assert results[0].id == "res-1"

    @pytest.mark.asyncio
    async def test_search_resources_by_date(self, repo):
        """Should filter resources by date range"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        resource_old = MDSOResource(
            id="res-old",
            label="old",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-1",
            created_at=week_ago.isoformat()
        )
        resource_new = MDSOResource(
            id="res-new",
            label="new",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-2",
            created_at=now.isoformat()
        )

        repo.add_resource(resource_old)
        repo.add_resource(resource_new)

        results = await repo.search_resources_by_date("ServiceMapper", yesterday)

        assert len(results) == 1
        assert results[0].id == "res-new"

    @pytest.mark.asyncio
    async def test_get_orch_trace(self, repo):
        """Should retrieve orchestration trace"""
        trace = MDSOOrchTrace(
            circuit_id="CIRCUIT-123",
            resource_id="resource-123",
            trace_data=[{"step": "1", "status": "completed"}],
            timestamp="2025-10-15T10:30:45Z"
        )

        repo.add_orch_trace("CIRCUIT-123", "resource-123", trace)

        result = await repo.get_orch_trace("CIRCUIT-123", "resource-123")

        assert result is not None
        assert result.circuit_id == "CIRCUIT-123"
        assert len(result.trace_data) == 1

    @pytest.mark.asyncio
    async def test_get_errors_for_resource(self, repo):
        """Should extract errors from orch trace"""
        resource = MDSOResource(
            id="resource-123",
            label="test-circuit",
            circuit_id="CIRCUIT-123",
            product_name="ServiceMapper",
            orch_state="failed",
            device_tid="device-456",
            created_at=datetime.now().isoformat()
        )

        trace = MDSOOrchTrace(
            circuit_id="CIRCUIT-123",
            resource_id="resource-123",
            trace_data=[
                {"process": "validate", "status": "error", "error": "Validation failed"},
                {"process": "provision", "status": "completed"},
            ],
            timestamp="2025-10-15T10:30:45Z"
        )

        repo.add_resource(resource)
        repo.add_orch_trace("CIRCUIT-123", "resource-123", trace)

        errors = await repo.get_errors_for_resource("resource-123")

        assert len(errors) == 1
        assert errors[0]["error"] == "Validation failed"

    @pytest.mark.asyncio
    async def test_clear(self, repo, sample_resource):
        """Should clear all data"""
        repo.add_resource(sample_resource)

        repo.clear()

        result = await repo.get_resource_by_id("resource-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_close_does_not_error(self, repo):
        """close() should not error for in-memory repo"""
        await repo.close()  # Should not raise


class TestHTTPMDSORepository:
    """Test HTTP repository implementation"""

    @pytest.fixture
    def mock_client(self):
        """Create mock MDSO client"""
        client = Mock()
        client.get_resources = AsyncMock()
        client.get_resource_by_id = AsyncMock()
        client.get_orch_trace = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def repo(self, mock_client):
        """Create HTTP repository with mock client"""
        return HTTPMDSORepository(mock_client)

    @pytest.mark.asyncio
    async def test_get_resources_delegates_to_client(self, repo, mock_client):
        """Should delegate to underlying client"""
        expected = [Mock(spec=MDSOResource)]
        mock_client.get_resources.return_value = expected

        result = await repo.get_resources("ServiceMapper")

        assert result == expected
        mock_client.get_resources.assert_called_once_with("ServiceMapper")

    @pytest.mark.asyncio
    async def test_get_resource_by_id_delegates_to_client(self, repo, mock_client):
        """Should delegate to client"""
        expected = Mock(spec=MDSOResource)
        mock_client.get_resource_by_id.return_value = expected

        result = await repo.get_resource_by_id("resource-123")

        assert result == expected
        mock_client.get_resource_by_id.assert_called_once_with("resource-123")

    @pytest.mark.asyncio
    async def test_get_orch_trace_delegates_to_client(self, repo, mock_client):
        """Should delegate to client"""
        expected = Mock(spec=MDSOOrchTrace)
        mock_client.get_orch_trace.return_value = expected

        result = await repo.get_orch_trace("CIRCUIT-123", "resource-123")

        assert result == expected
        mock_client.get_orch_trace.assert_called_once_with("CIRCUIT-123", "resource-123")

    @pytest.mark.asyncio
    async def test_search_resources_by_date(self, repo, mock_client):
        """Should filter resources by date"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        old_resource = MDSOResource(
            id="old",
            label="old",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-1",
            created_at=week_ago.isoformat()
        )
        new_resource = MDSOResource(
            id="new",
            label="new",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-2",
            created_at=now.isoformat()
        )

        mock_client.get_resources.return_value = [old_resource, new_resource]

        results = await repo.search_resources_by_date("ServiceMapper", yesterday)

        assert len(results) == 1
        assert results[0].id == "new"

    @pytest.mark.asyncio
    async def test_close_delegates_to_client(self, repo, mock_client):
        """Should close underlying client"""
        await repo.close()

        mock_client.close.assert_called_once()


class TestCachedMDSORepository:
    """Test cached repository implementation"""

    @pytest.fixture
    def underlying_repo(self):
        """Create underlying repository"""
        repo = Mock(spec=MDSORepository)
        repo.get_resources = AsyncMock()
        repo.get_resource_by_id = AsyncMock()
        repo.get_orch_trace = AsyncMock()
        repo.search_resources_by_date = AsyncMock()
        repo.get_errors_for_resource = AsyncMock()
        repo.close = AsyncMock()
        return repo

    @pytest.fixture
    def cached_repo(self, underlying_repo):
        """Create cached repository with 1 second TTL"""
        return CachedMDSORepository(underlying_repo, ttl_seconds=1)

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_call(self, cached_repo, underlying_repo):
        """Should use cache on second call"""
        expected = [Mock(spec=MDSOResource)]
        underlying_repo.get_resources.return_value = expected

        # First call - cache miss
        result1 = await cached_repo.get_resources("ServiceMapper")

        # Second call - cache hit
        result2 = await cached_repo.get_resources("ServiceMapper")

        assert result1 == expected
        assert result2 == expected
        # Underlying should only be called once
        assert underlying_repo.get_resources.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_after_ttl(self, underlying_repo):
        """Should fetch fresh data after TTL expires"""
        import asyncio

        # Use very short TTL for testing
        cached_repo = CachedMDSORepository(underlying_repo, ttl_seconds=0.1)

        expected = [Mock(spec=MDSOResource)]
        underlying_repo.get_resources.return_value = expected

        # First call
        await cached_repo.get_resources("ServiceMapper")

        # Wait for TTL to expire
        await asyncio.sleep(0.2)

        # Second call - should fetch fresh data
        await cached_repo.get_resources("ServiceMapper")

        # Underlying should be called twice
        assert underlying_repo.get_resources.call_count == 2

    @pytest.mark.asyncio
    async def test_different_keys_cache_separately(self, cached_repo, underlying_repo):
        """Should cache different products separately"""
        underlying_repo.get_resources.side_effect = [
            [Mock(id="service-1")],
            [Mock(id="network-1")],
        ]

        # Call with different products
        result1 = await cached_repo.get_resources("ServiceMapper")
        result2 = await cached_repo.get_resources("NetworkService")

        # Both should call underlying (different cache keys)
        assert underlying_repo.get_resources.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_resource_by_id(self, cached_repo, underlying_repo):
        """Should cache individual resources"""
        expected = Mock(spec=MDSOResource)
        underlying_repo.get_resource_by_id.return_value = expected

        # First call
        result1 = await cached_repo.get_resource_by_id("resource-123")

        # Second call - cached
        result2 = await cached_repo.get_resource_by_id("resource-123")

        assert result1 == expected
        assert result2 == expected
        assert underlying_repo.get_resource_by_id.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_orch_trace(self, cached_repo, underlying_repo):
        """Should cache orchestration traces"""
        expected = Mock(spec=MDSOOrchTrace)
        underlying_repo.get_orch_trace.return_value = expected

        # First call
        result1 = await cached_repo.get_orch_trace("CIRCUIT-123", "resource-123")

        # Second call - cached
        result2 = await cached_repo.get_orch_trace("CIRCUIT-123", "resource-123")

        assert result1 == expected
        assert result2 == expected
        assert underlying_repo.get_orch_trace.call_count == 1

    @pytest.mark.asyncio
    async def test_clear_cache(self, cached_repo, underlying_repo):
        """Should clear all cached data"""
        underlying_repo.get_resources.return_value = [Mock(spec=MDSOResource)]

        # First call - cache miss
        await cached_repo.get_resources("ServiceMapper")

        # Clear cache
        cached_repo.clear_cache()

        # Second call - should call underlying again
        await cached_repo.get_resources("ServiceMapper")

        assert underlying_repo.get_resources.call_count == 2

    @pytest.mark.asyncio
    async def test_close_delegates_to_underlying(self, cached_repo, underlying_repo):
        """Should close underlying repository"""
        await cached_repo.close()

        underlying_repo.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_does_not_store_none_values(self, cached_repo, underlying_repo):
        """Should not cache None values"""
        underlying_repo.get_resource_by_id.return_value = None

        # First call - returns None
        result1 = await cached_repo.get_resource_by_id("nonexistent")

        # Second call - should call underlying again (None not cached)
        result2 = await cached_repo.get_resource_by_id("nonexistent")

        assert result1 is None
        assert result2 is None
        # Should call underlying each time for None values
        assert underlying_repo.get_resource_by_id.call_count == 2


class TestRepositoryIntegration:
    """Integration tests for repository pattern"""

    @pytest.mark.asyncio
    async def test_repository_abstraction_allows_swapping(self):
        """Should be able to swap repository implementations"""
        # Create both implementations
        in_memory = InMemoryMDSORepository()
        resource = MDSOResource(
            id="test-123",
            label="test",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-1",
            created_at=datetime.now().isoformat()
        )
        in_memory.add_resource(resource)

        # Both should work with the same interface
        async def fetch_resources(repo: MDSORepository):
            return await repo.get_resources("ServiceMapper")

        # In-memory
        results = await fetch_resources(in_memory)
        assert len(results) == 1

        # HTTP would work too (with mock client)
        mock_client = Mock()
        mock_client.get_resources = AsyncMock(return_value=[resource])
        http_repo = HTTPMDSORepository(mock_client)

        results = await fetch_resources(http_repo)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_cached_repo_wraps_in_memory(self):
        """Should be able to wrap in-memory repo with caching"""
        in_memory = InMemoryMDSORepository()
        resource = MDSOResource(
            id="test-123",
            label="test",
            product_name="ServiceMapper",
            orch_state="completed",
            device_tid="dev-1",
            created_at=datetime.now().isoformat()
        )
        in_memory.add_resource(resource)

        cached = CachedMDSORepository(in_memory, ttl_seconds=300)

        # Should work through cache
        results = await cached.get_resources("ServiceMapper")
        assert len(results) == 1
