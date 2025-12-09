"""Tests for state managers (in-memory and Redis)"""
import pytest
from datetime import datetime, timedelta, timezone
from app.pipeline.state_manager import (
    CorrelationEntry,
    StateManager,
    InMemoryStateManager,
    RedisStateManager,
)


class TestCorrelationEntry:
    """Test CorrelationEntry serialization"""

    def test_to_dict(self):
        """Should convert to dictionary"""
        now = datetime.now(timezone.utc)
        entry = CorrelationEntry(
            correlation_id="corr-123",
            trace_id="trace-456",
            service="test-service",
            env="production",
            first_seen=now,
            last_updated=now,
            spans=[{"span_id": "span-1"}],
            logs=[{"message": "test"}],
            metadata={"key": "value"}
        )

        data = entry.to_dict()

        assert data["correlation_id"] == "corr-123"
        assert data["trace_id"] == "trace-456"
        assert data["service"] == "test-service"
        assert data["env"] == "production"
        assert len(data["spans"]) == 1
        assert len(data["logs"]) == 1
        assert data["metadata"]["key"] == "value"

    def test_from_dict(self):
        """Should create from dictionary"""
        now = datetime.now(timezone.utc)
        data = {
            "correlation_id": "corr-123",
            "trace_id": "trace-456",
            "service": "test-service",
            "env": "production",
            "first_seen": now.isoformat(),
            "last_updated": now.isoformat(),
            "spans": [{"span_id": "span-1"}],
            "logs": [{"message": "test"}],
            "metadata": {"key": "value"}
        }

        entry = CorrelationEntry.from_dict(data)

        assert entry.correlation_id == "corr-123"
        assert entry.trace_id == "trace-456"
        assert entry.service == "test-service"
        assert len(entry.spans) == 1
        assert len(entry.logs) == 1

    def test_to_json_and_back(self):
        """Should round-trip through JSON"""
        original = CorrelationEntry(
            correlation_id="corr-123",
            trace_id="trace-456",
            service="test",
            env="dev"
        )

        json_str = original.to_json()
        restored = CorrelationEntry.from_json(json_str)

        assert restored.correlation_id == original.correlation_id
        assert restored.trace_id == original.trace_id
        assert restored.service == original.service


class TestInMemoryStateManager:
    """Test in-memory state manager"""

    @pytest.fixture
    def manager(self):
        """Create fresh manager for each test"""
        return InMemoryStateManager()

    @pytest.fixture
    def sample_entry(self):
        """Create sample correlation entry"""
        return CorrelationEntry(
            correlation_id="corr-123",
            trace_id="trace-456",
            service="test-service",
            env="dev"
        )

    @pytest.mark.asyncio
    async def test_set_and_get_correlation(self, manager, sample_entry):
        """Should store and retrieve correlation"""
        await manager.set_correlation("corr-123", sample_entry)

        result = await manager.get_correlation("corr-123")

        assert result is not None
        assert result.correlation_id == "corr-123"
        assert result.trace_id == "trace-456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, manager):
        """Should return None for non-existent correlation"""
        result = await manager.get_correlation("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_correlation(self, manager, sample_entry):
        """Should delete correlation"""
        await manager.set_correlation("corr-123", sample_entry)

        await manager.delete_correlation("corr-123")

        result = await manager.get_correlation("corr-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_correlation_count(self, manager, sample_entry):
        """Should count correlations"""
        assert await manager.get_correlation_count() == 0

        await manager.set_correlation("corr-1", sample_entry)
        await manager.set_correlation("corr-2", sample_entry)

        assert await manager.get_correlation_count() == 2

    @pytest.mark.asyncio
    async def test_get_correlations_by_time_range(self, manager):
        """Should filter by time range"""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Old entry
        old_entry = CorrelationEntry(
            correlation_id="old",
            trace_id="trace-1",
            service="test",
            env="dev",
            first_seen=day_ago,
            last_updated=day_ago
        )

        # Recent entry
        new_entry = CorrelationEntry(
            correlation_id="new",
            trace_id="trace-2",
            service="test",
            env="dev",
            first_seen=now,
            last_updated=now
        )

        await manager.set_correlation("old", old_entry)
        await manager.set_correlation("new", new_entry)

        # Get only recent (last hour)
        results = await manager.get_correlations_by_time_range(hour_ago)

        assert len(results) == 1
        assert results[0].correlation_id == "new"

    @pytest.mark.asyncio
    async def test_cleanup_old_correlations(self, manager):
        """Should remove old correlations"""
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        day_ago = now - timedelta(days=1)

        # Old entry
        old_entry = CorrelationEntry(
            correlation_id="old",
            trace_id="trace-1",
            service="test",
            env="dev",
            last_updated=day_ago
        )

        # Recent entry
        new_entry = CorrelationEntry(
            correlation_id="new",
            trace_id="trace-2",
            service="test",
            env="dev",
            last_updated=now
        )

        await manager.set_correlation("old", old_entry)
        await manager.set_correlation("new", new_entry)

        # Cleanup everything older than 2 hours
        deleted = await manager.cleanup_old_correlations(two_hours_ago)

        assert deleted == 1
        assert await manager.get_correlation("old") is None
        assert await manager.get_correlation("new") is not None

    @pytest.mark.asyncio
    async def test_close_does_not_error(self, manager):
        """close() should not error"""
        await manager.close()


# Note: Redis tests require a running Redis instance
# These are integration tests and may be skipped in CI without Redis

@pytest.mark.integration
class TestRedisStateManager:
    """Test Redis state manager (requires Redis)"""

    @pytest.fixture
    async def manager(self):
        """Create manager and cleanup after test"""
        manager = RedisStateManager(
            redis_url="redis://localhost:6379",
            key_prefix="test_corr:"
        )

        try:
            # Try to connect
            await manager._ensure_connected()
        except (ImportError, Exception) as e:
            pytest.skip(f"Redis not available: {e}")

        yield manager

        # Cleanup
        if manager.redis:
            # Delete all test keys
            keys = await manager.redis.keys(f"{manager.key_prefix}*")
            if keys:
                await manager.redis.delete(*keys)
        await manager.close()

    @pytest.fixture
    def sample_entry(self):
        """Create sample correlation entry"""
        return CorrelationEntry(
            correlation_id="corr-123",
            trace_id="trace-456",
            service="test-service",
            env="dev"
        )

    @pytest.mark.asyncio
    async def test_set_and_get_correlation(self, manager, sample_entry):
        """Should store and retrieve correlation from Redis"""
        await manager.set_correlation("corr-123", sample_entry)

        result = await manager.get_correlation("corr-123")

        assert result is not None
        assert result.correlation_id == "corr-123"
        assert result.trace_id == "trace-456"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, manager, sample_entry):
        """Should set correlation with TTL"""
        await manager.set_correlation("corr-123", sample_entry, ttl_seconds=1)

        # Should exist immediately
        result = await manager.get_correlation("corr-123")
        assert result is not None

        # Wait for TTL to expire
        import asyncio
        await asyncio.sleep(2)

        # Should be gone
        result = await manager.get_correlation("corr-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_correlation(self, manager, sample_entry):
        """Should delete correlation from Redis"""
        await manager.set_correlation("corr-123", sample_entry)

        await manager.delete_correlation("corr-123")

        result = await manager.get_correlation("corr-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_correlation_count(self, manager, sample_entry):
        """Should count correlations in Redis"""
        count = await manager.get_correlation_count()
        initial_count = count

        await manager.set_correlation("corr-1", sample_entry)
        await manager.set_correlation("corr-2", sample_entry)

        count = await manager.get_correlation_count()
        assert count == initial_count + 2

    @pytest.mark.asyncio
    async def test_get_correlations_by_time_range(self, manager):
        """Should filter by time range in Redis"""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Old entry
        old_entry = CorrelationEntry(
            correlation_id="old",
            trace_id="trace-1",
            service="test",
            env="dev",
            first_seen=day_ago,
            last_updated=day_ago
        )

        # Recent entry
        new_entry = CorrelationEntry(
            correlation_id="new",
            trace_id="trace-2",
            service="test",
            env="dev",
            first_seen=now,
            last_updated=now
        )

        await manager.set_correlation("old", old_entry)
        await manager.set_correlation("new", new_entry)

        # Get only recent (last hour)
        results = await manager.get_correlations_by_time_range(hour_ago)

        assert len(results) >= 1  # At least the new one
        assert any(r.correlation_id == "new" for r in results)

    @pytest.mark.asyncio
    async def test_cleanup_old_correlations(self, manager):
        """Should remove old correlations from Redis"""
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        day_ago = now - timedelta(days=1)

        # Old entry
        old_entry = CorrelationEntry(
            correlation_id="old",
            trace_id="trace-1",
            service="test",
            env="dev",
            last_updated=day_ago
        )

        # Recent entry
        new_entry = CorrelationEntry(
            correlation_id="new",
            trace_id="trace-2",
            service="test",
            env="dev",
            last_updated=now
        )

        await manager.set_correlation("old", old_entry)
        await manager.set_correlation("new", new_entry)

        # Cleanup everything older than 2 hours
        deleted = await manager.cleanup_old_correlations(two_hours_ago)

        assert deleted >= 1
        assert await manager.get_correlation("old") is None
        assert await manager.get_correlation("new") is not None


class TestStateManagerInterface:
    """Test that both implementations follow the interface"""

    @pytest.mark.asyncio
    async def test_both_implement_same_interface(self):
        """Both managers should have same methods"""
        in_memory = InMemoryStateManager()

        # Check all required methods exist
        assert hasattr(in_memory, 'get_correlation')
        assert hasattr(in_memory, 'set_correlation')
        assert hasattr(in_memory, 'delete_correlation')
        assert hasattr(in_memory, 'get_correlations_by_time_range')
        assert hasattr(in_memory, 'cleanup_old_correlations')
        assert hasattr(in_memory, 'get_correlation_count')
        assert hasattr(in_memory, 'close')

        # Redis manager should have same methods
        redis_manager = RedisStateManager()
        assert hasattr(redis_manager, 'get_correlation')
        assert hasattr(redis_manager, 'set_correlation')
        assert hasattr(redis_manager, 'delete_correlation')
        assert hasattr(redis_manager, 'get_correlations_by_time_range')
        assert hasattr(redis_manager, 'cleanup_old_correlations')
        assert hasattr(redis_manager, 'get_correlation_count')
        assert hasattr(redis_manager, 'close')

    @pytest.mark.asyncio
    async def test_can_swap_implementations(self):
        """Should be able to swap implementations transparently"""
        async def store_and_retrieve(manager: StateManager, entry: CorrelationEntry):
            await manager.set_correlation(entry.correlation_id, entry)
            return await manager.get_correlation(entry.correlation_id)

        # Works with in-memory
        in_memory = InMemoryStateManager()
        entry = CorrelationEntry(correlation_id="test", trace_id="trace-1", service="svc", env="dev")
        result = await store_and_retrieve(in_memory, entry)
        assert result.correlation_id == "test"

        # Would work with Redis too (if available)
        # redis_mgr = RedisStateManager()
        # result = await store_and_retrieve(redis_mgr, entry)
