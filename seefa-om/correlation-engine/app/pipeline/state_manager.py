"""State management for correlation engine

This module provides abstraction for correlation state storage,
enabling both in-memory (single instance) and Redis-based (multi-instance)
deployments.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import json
import structlog

logger = structlog.get_logger()


class CorrelationEntry:
    """Represents a correlation entry in the state store

    This is a lightweight data class that can be serialized to/from JSON
    for storage in Redis or kept in-memory.
    """

    def __init__(
        self,
        correlation_id: str,
        trace_id: Optional[str] = None,
        service: str = "unknown",
        env: str = "unknown",
        first_seen: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
        spans: Optional[List[Dict[str, Any]]] = None,
        logs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.service = service
        self.env = env
        self.first_seen = first_seen or datetime.now(timezone.utc)
        self.last_updated = last_updated or datetime.now(timezone.utc)
        self.spans = spans or []
        self.logs = logs or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "service": self.service,
            "env": self.env,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "spans": self.spans,
            "logs": self.logs,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrelationEntry":
        """Create from dictionary (deserialization)"""
        return cls(
            correlation_id=data["correlation_id"],
            trace_id=data.get("trace_id"),
            service=data.get("service", "unknown"),
            env=data.get("env", "unknown"),
            first_seen=datetime.fromisoformat(data["first_seen"]) if data.get("first_seen") else None,
            last_updated=datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else None,
            spans=data.get("spans", []),
            logs=data.get("logs", []),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "CorrelationEntry":
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


class StateManager(ABC):
    """Abstract base class for correlation state management

    Provides interface for storing and retrieving correlation state.
    Implementations can use in-memory storage (single instance) or
    Redis (multi-instance horizontal scaling).
    """

    @abstractmethod
    async def get_correlation(self, correlation_id: str) -> Optional[CorrelationEntry]:
        """Retrieve a correlation by ID

        Args:
            correlation_id: The correlation identifier

        Returns:
            CorrelationEntry if found, None otherwise
        """
        pass

    @abstractmethod
    async def set_correlation(
        self,
        correlation_id: str,
        entry: CorrelationEntry,
        ttl_seconds: Optional[int] = None
    ):
        """Store or update a correlation

        Args:
            correlation_id: The correlation identifier
            entry: The correlation entry to store
            ttl_seconds: Optional time-to-live in seconds
        """
        pass

    @abstractmethod
    async def delete_correlation(self, correlation_id: str):
        """Delete a correlation

        Args:
            correlation_id: The correlation identifier to delete
        """
        pass

    @abstractmethod
    async def get_correlations_by_time_range(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[CorrelationEntry]:
        """Get all correlations within a time range

        Args:
            start_time: Start of time range
            end_time: End of time range (defaults to now)

        Returns:
            List of correlation entries
        """
        pass

    @abstractmethod
    async def cleanup_old_correlations(self, cutoff_time: datetime) -> int:
        """Remove correlations older than cutoff time

        Args:
            cutoff_time: Delete correlations last updated before this time

        Returns:
            Number of correlations deleted
        """
        pass

    @abstractmethod
    async def get_correlation_count(self) -> int:
        """Get total number of active correlations

        Returns:
            Count of correlations in storage
        """
        pass

    @abstractmethod
    async def close(self):
        """Close connections and cleanup resources"""
        pass


class InMemoryStateManager(StateManager):
    """In-memory state manager for single-instance deployments

    Stores correlation state in Python dictionaries. Fast and simple,
    but limited to single instance (no horizontal scaling).
    """

    def __init__(self):
        """Initialize in-memory storage"""
        self.correlations: Dict[str, CorrelationEntry] = {}
        self.time_index: List[tuple[datetime, str]] = []  # (timestamp, correlation_id)

    async def get_correlation(self, correlation_id: str) -> Optional[CorrelationEntry]:
        """Get correlation from memory"""
        return self.correlations.get(correlation_id)

    async def set_correlation(
        self,
        correlation_id: str,
        entry: CorrelationEntry,
        ttl_seconds: Optional[int] = None
    ):
        """Store correlation in memory"""
        self.correlations[correlation_id] = entry

        # Update time index
        self.time_index.append((entry.last_updated, correlation_id))

        # Note: TTL is handled by periodic cleanup, not enforced here
        if ttl_seconds:
            logger.debug(
                "in_memory_ttl_note",
                correlation_id=correlation_id,
                ttl_seconds=ttl_seconds,
                note="TTL will be enforced during cleanup"
            )

    async def delete_correlation(self, correlation_id: str):
        """Delete correlation from memory"""
        if correlation_id in self.correlations:
            del self.correlations[correlation_id]

        # Remove from time index
        self.time_index = [
            (ts, cid) for ts, cid in self.time_index
            if cid != correlation_id
        ]

    async def get_correlations_by_time_range(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[CorrelationEntry]:
        """Get correlations from time index"""
        end_time = end_time or datetime.now(timezone.utc)

        return [
            self.correlations[cid]
            for ts, cid in self.time_index
            if start_time <= ts <= end_time and cid in self.correlations
        ]

    async def cleanup_old_correlations(self, cutoff_time: datetime) -> int:
        """Remove old correlations from memory"""
        to_delete = [
            correlation_id
            for correlation_id, entry in self.correlations.items()
            if entry.last_updated < cutoff_time
        ]

        for correlation_id in to_delete:
            await self.delete_correlation(correlation_id)

        logger.info("in_memory_cleanup", deleted_count=len(to_delete))
        return len(to_delete)

    async def get_correlation_count(self) -> int:
        """Get count from memory"""
        return len(self.correlations)

    async def close(self):
        """Nothing to close for in-memory storage"""
        pass


class RedisStateManager(StateManager):
    """Redis-based state manager for horizontal scaling

    Stores correlation state in Redis, enabling multiple correlation engine
    instances to share state. This is the key to horizontal scaling.

    Requires: redis-py (pip install redis)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "corr:",
        max_connections: int = 50
    ):
        """Initialize Redis state manager

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
            max_connections: Max connections in pool
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_connections = max_connections
        self.redis = None
        self._initialized = False

    async def _ensure_connected(self):
        """Lazy initialization of Redis connection"""
        if self._initialized:
            return

        try:
            import redis.asyncio as redis
        except ImportError:
            logger.error(
                "redis_not_installed",
                message="redis library not installed. Run: pip install redis"
            )
            raise ImportError("redis library required for RedisStateManager")

        self.redis = redis.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            decode_responses=True  # Get strings instead of bytes
        )

        # Test connection
        await self.redis.ping()
        self._initialized = True
        logger.info("redis_connected", url=self.redis_url)

    def _make_key(self, correlation_id: str) -> str:
        """Create Redis key for correlation"""
        return f"{self.key_prefix}{correlation_id}"

    async def get_correlation(self, correlation_id: str) -> Optional[CorrelationEntry]:
        """Retrieve correlation from Redis"""
        await self._ensure_connected()

        key = self._make_key(correlation_id)
        data = await self.redis.get(key)

        if not data:
            return None

        try:
            return CorrelationEntry.from_json(data)
        except Exception as e:
            logger.error(
                "redis_deserialize_error",
                correlation_id=correlation_id,
                error=str(e)
            )
            return None

    async def set_correlation(
        self,
        correlation_id: str,
        entry: CorrelationEntry,
        ttl_seconds: Optional[int] = None
    ):
        """Store correlation in Redis with optional TTL"""
        await self._ensure_connected()

        key = self._make_key(correlation_id)
        value = entry.to_json()

        if ttl_seconds:
            # Set with expiration
            await self.redis.setex(key, ttl_seconds, value)
        else:
            # Set without expiration
            await self.redis.set(key, value)

        # Add to time-sorted index
        await self.redis.zadd(
            f"{self.key_prefix}time_index",
            {correlation_id: entry.last_updated.timestamp()}
        )

        logger.debug(
            "redis_correlation_stored",
            correlation_id=correlation_id,
            ttl_seconds=ttl_seconds
        )

    async def delete_correlation(self, correlation_id: str):
        """Delete correlation from Redis"""
        await self._ensure_connected()

        key = self._make_key(correlation_id)

        # Delete from main storage
        await self.redis.delete(key)

        # Remove from time index
        await self.redis.zrem(f"{self.key_prefix}time_index", correlation_id)

        logger.debug("redis_correlation_deleted", correlation_id=correlation_id)

    async def get_correlations_by_time_range(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[CorrelationEntry]:
        """Get correlations from Redis time index"""
        await self._ensure_connected()

        end_time = end_time or datetime.now(timezone.utc)

        # Query sorted set by score (timestamp)
        correlation_ids = await self.redis.zrangebyscore(
            f"{self.key_prefix}time_index",
            start_time.timestamp(),
            end_time.timestamp()
        )

        # Fetch all correlations
        correlations = []
        for correlation_id in correlation_ids:
            entry = await self.get_correlation(correlation_id)
            if entry:
                correlations.append(entry)

        return correlations

    async def cleanup_old_correlations(self, cutoff_time: datetime) -> int:
        """Remove old correlations from Redis"""
        await self._ensure_connected()

        # Find old correlation IDs from time index
        old_ids = await self.redis.zrangebyscore(
            f"{self.key_prefix}time_index",
            0,
            cutoff_time.timestamp()
        )

        if not old_ids:
            return 0

        # Delete correlations
        keys_to_delete = [self._make_key(cid) for cid in old_ids]
        await self.redis.delete(*keys_to_delete)

        # Remove from time index
        await self.redis.zremrangebyscore(
            f"{self.key_prefix}time_index",
            0,
            cutoff_time.timestamp()
        )

        logger.info("redis_cleanup", deleted_count=len(old_ids))
        return len(old_ids)

    async def get_correlation_count(self) -> int:
        """Get count of correlations in Redis"""
        await self._ensure_connected()

        count = await self.redis.zcard(f"{self.key_prefix}time_index")
        return count

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("redis_closed")
