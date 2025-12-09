"""Repository pattern for MDSO access

This module implements the Repository Pattern for MDSO data access,
abstracting away the underlying HTTP client and enabling:
- Easy testing with mock repositories
- Centralized rate limiting
- Caching capabilities
- Simplified dependency injection
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import MDSOResource, MDSOOrchTrace


class MDSORepository(ABC):
    """Abstract base class for MDSO data access

    This repository pattern abstracts MDSO operations, allowing for:
    - Multiple implementations (HTTP, cached, mock)
    - Easier unit testing
    - Centralized rate limiting and retry logic
    - Future support for different MDSO backends
    """

    @abstractmethod
    async def get_resources(
        self,
        product_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MDSOResource]:
        """Get resources for a product

        Args:
            product_name: Name of the product (e.g., "ServiceMapper")
            filters: Optional filters to apply

        Returns:
            List of MDSOResource objects

        Raises:
            MDSOConnectionError: If connection to MDSO fails
            MDSOAuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def get_resource_by_id(
        self,
        resource_id: str
    ) -> Optional[MDSOResource]:
        """Get a single resource by ID

        Args:
            resource_id: The resource ID

        Returns:
            MDSOResource if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_orch_trace(
        self,
        circuit_id: str,
        resource_id: str
    ) -> Optional[MDSOOrchTrace]:
        """Get orchestration trace for a circuit

        Args:
            circuit_id: Circuit identifier
            resource_id: Resource identifier

        Returns:
            MDSOOrchTrace if found, None otherwise
        """
        pass

    @abstractmethod
    async def search_resources_by_date(
        self,
        product_name: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[MDSOResource]:
        """Search resources by date range

        Args:
            product_name: Product to search
            start_date: Start of date range
            end_date: End of date range (defaults to now)

        Returns:
            List of matching resources
        """
        pass

    @abstractmethod
    async def get_errors_for_resource(
        self,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """Get all errors for a resource

        Args:
            resource_id: Resource identifier

        Returns:
            List of error dictionaries
        """
        pass

    @abstractmethod
    async def close(self):
        """Close any connections and cleanup resources"""
        pass


class HTTPMDSORepository(MDSORepository):
    """HTTP-based MDSO repository using MDSOClient

    This is the production implementation that uses the
    existing MDSOClient for HTTP communication with MDSO.
    """

    def __init__(self, mdso_client):
        """Initialize with an MDSOClient instance

        Args:
            mdso_client: Configured MDSOClient instance
        """
        self.client = mdso_client

    async def get_resources(
        self,
        product_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MDSOResource]:
        """Get resources via HTTP client"""
        # Delegate to existing client
        return await self.client.get_resources(product_name)

    async def get_resource_by_id(
        self,
        resource_id: str
    ) -> Optional[MDSOResource]:
        """Get single resource by ID"""
        # This would need to be implemented in MDSOClient if not exists
        # For now, we can search through all resources
        # TODO: Add dedicated endpoint in MDSOClient
        return await self.client.get_resource_by_id(resource_id)

    async def get_orch_trace(
        self,
        circuit_id: str,
        resource_id: str
    ) -> Optional[MDSOOrchTrace]:
        """Get orchestration trace via HTTP"""
        return await self.client.get_orch_trace(circuit_id, resource_id)

    async def search_resources_by_date(
        self,
        product_name: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[MDSOResource]:
        """Search resources by date range"""
        # Get all resources and filter by date
        all_resources = await self.get_resources(product_name)

        end_date = end_date or datetime.now()

        return [
            r for r in all_resources
            if start_date <= datetime.fromisoformat(r.created_at) <= end_date
        ]

    async def get_errors_for_resource(
        self,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """Get errors for a resource"""
        # Get resource first to find circuit_id
        resource = await self.get_resource_by_id(resource_id)
        if not resource:
            return []

        circuit_id = resource.circuit_id or resource.label
        if not circuit_id:
            return []

        # Get orchestration trace
        orch_trace = await self.get_orch_trace(circuit_id, resource_id)
        if not orch_trace:
            return []

        return orch_trace.get_errors()

    async def close(self):
        """Close HTTP client connection"""
        await self.client.close()


class InMemoryMDSORepository(MDSORepository):
    """In-memory MDSO repository for testing

    This implementation stores data in memory and is useful for:
    - Unit testing without external dependencies
    - Integration testing with predictable data
    - Local development without MDSO access
    """

    def __init__(self):
        """Initialize with empty in-memory storage"""
        self.resources: Dict[str, MDSOResource] = {}
        self.orch_traces: Dict[str, MDSOOrchTrace] = {}

    def add_resource(self, resource: MDSOResource):
        """Add a resource to in-memory storage (for testing)"""
        self.resources[resource.id] = resource

    def add_orch_trace(self, circuit_id: str, resource_id: str, trace: MDSOOrchTrace):
        """Add an orch trace to in-memory storage (for testing)"""
        key = f"{circuit_id}:{resource_id}"
        self.orch_traces[key] = trace

    async def get_resources(
        self,
        product_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MDSOResource]:
        """Get resources from memory"""
        # Filter by product name if available
        results = [
            r for r in self.resources.values()
            if hasattr(r, 'product_name') and r.product_name == product_name
        ]

        # Apply additional filters if provided
        if filters:
            for key, value in filters.items():
                results = [r for r in results if getattr(r, key, None) == value]

        return results

    async def get_resource_by_id(
        self,
        resource_id: str
    ) -> Optional[MDSOResource]:
        """Get resource from memory"""
        return self.resources.get(resource_id)

    async def get_orch_trace(
        self,
        circuit_id: str,
        resource_id: str
    ) -> Optional[MDSOOrchTrace]:
        """Get orch trace from memory"""
        key = f"{circuit_id}:{resource_id}"
        return self.orch_traces.get(key)

    async def search_resources_by_date(
        self,
        product_name: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[MDSOResource]:
        """Search resources by date in memory"""
        all_resources = await self.get_resources(product_name)

        end_date = end_date or datetime.now()

        return [
            r for r in all_resources
            if start_date <= datetime.fromisoformat(r.created_at) <= end_date
        ]

    async def get_errors_for_resource(
        self,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """Get errors from in-memory trace"""
        resource = await self.get_resource_by_id(resource_id)
        if not resource:
            return []

        circuit_id = resource.circuit_id or resource.label
        if not circuit_id:
            return []

        orch_trace = await self.get_orch_trace(circuit_id, resource_id)
        if not orch_trace:
            return []

        return orch_trace.get_errors()

    async def close(self):
        """Nothing to close for in-memory storage"""
        pass

    def clear(self):
        """Clear all in-memory data (for testing)"""
        self.resources.clear()
        self.orch_traces.clear()


class CachedMDSORepository(MDSORepository):
    """Cached MDSO repository with TTL-based caching

    Wraps another repository (typically HTTPMDSORepository) and adds
    caching to reduce load on MDSO and improve response times.
    """

    def __init__(self, underlying_repo: MDSORepository, ttl_seconds: int = 300):
        """Initialize with underlying repository and cache TTL

        Args:
            underlying_repo: The actual repository to cache
            ttl_seconds: Cache time-to-live in seconds (default 5 minutes)
        """
        self.repo = underlying_repo
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple[Any, datetime]] = {}

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]
        age = (datetime.now() - timestamp).total_seconds()

        if age > self.ttl_seconds:
            del self.cache[key]
            return None

        return value

    def _set_cache(self, key: str, value: Any):
        """Set value in cache with current timestamp"""
        self.cache[key] = (value, datetime.now())

    async def get_resources(
        self,
        product_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MDSOResource]:
        """Get resources with caching"""
        cache_key = f"resources:{product_name}:{filters}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = await self.repo.get_resources(product_name, filters)
        self._set_cache(cache_key, result)
        return result

    async def get_resource_by_id(
        self,
        resource_id: str
    ) -> Optional[MDSOResource]:
        """Get resource with caching"""
        cache_key = f"resource:{resource_id}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = await self.repo.get_resource_by_id(resource_id)
        if result:
            self._set_cache(cache_key, result)
        return result

    async def get_orch_trace(
        self,
        circuit_id: str,
        resource_id: str
    ) -> Optional[MDSOOrchTrace]:
        """Get orch trace with caching"""
        cache_key = f"orch:{circuit_id}:{resource_id}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = await self.repo.get_orch_trace(circuit_id, resource_id)
        if result:
            self._set_cache(cache_key, result)
        return result

    async def search_resources_by_date(
        self,
        product_name: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[MDSOResource]:
        """Search with caching (short TTL for date queries)"""
        # Don't cache date queries as aggressively
        return await self.repo.search_resources_by_date(product_name, start_date, end_date)

    async def get_errors_for_resource(
        self,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """Get errors with caching"""
        cache_key = f"errors:{resource_id}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = await self.repo.get_errors_for_resource(resource_id)
        self._set_cache(cache_key, result)
        return result

    async def close(self):
        """Close underlying repository"""
        await self.repo.close()

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
