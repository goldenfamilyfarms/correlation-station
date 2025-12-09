"""Dependency injection container for Correlation Engine

This module implements a lightweight dependency injection system using
FastAPI's built-in dependency injection alongside a service registry
for managing application-wide singletons.
"""

from typing import Optional, Dict, Any, Callable, TypeVar, Type
from functools import lru_cache
import structlog

from app.config import settings
from app.mdso import MDSOClient, MDSORepository, HTTPMDSORepository, CachedMDSORepository
from app.pipeline.state_manager import StateManager, InMemoryStateManager, RedisStateManager

logger = structlog.get_logger()

T = TypeVar('T')


class ServiceRegistry:
    """Central registry for application services (singletons)

    Provides a centralized way to manage service lifecycle and dependencies.
    Services are lazily initialized and cached.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    def register_factory(self, name: str, factory: Callable):
        """Register a factory function for a service

        Args:
            name: Service identifier
            factory: Function that creates the service instance
        """
        self._factories[name] = factory
        logger.debug("service_factory_registered", service=name)

    def register_instance(self, name: str, instance: Any):
        """Register a pre-created service instance

        Args:
            name: Service identifier
            instance: Service instance
        """
        self._services[name] = instance
        logger.debug("service_instance_registered", service=name)

    def get(self, name: str) -> Any:
        """Get a service instance, creating it if necessary

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Return existing instance if available
        if name in self._services:
            return self._services[name]

        # Create from factory if available
        if name in self._factories:
            logger.info("service_creating", service=name)
            instance = self._factories[name]()
            self._services[name] = instance
            return instance

        raise KeyError(f"Service '{name}' not registered")

    def get_optional(self, name: str) -> Optional[Any]:
        """Get a service if it exists, None otherwise

        Args:
            name: Service identifier

        Returns:
            Service instance or None
        """
        try:
            return self.get(name)
        except KeyError:
            return None

    def has(self, name: str) -> bool:
        """Check if a service is registered

        Args:
            name: Service identifier

        Returns:
            True if service exists
        """
        return name in self._services or name in self._factories

    async def cleanup(self):
        """Cleanup all services with close() methods"""
        for name, service in self._services.items():
            if hasattr(service, 'close'):
                try:
                    logger.info("service_closing", service=name)
                    await service.close()
                except Exception as e:
                    logger.error("service_close_error", service=name, error=str(e))

        self._services.clear()
        logger.info("service_registry_cleaned")


# Global service registry instance
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """Get the global service registry"""
    return _registry


# Service factory functions

def create_mdso_client() -> Optional[MDSOClient]:
    """Create MDSO client if configured"""
    if not settings.mdso_base_url:
        logger.warning("mdso_client_not_configured")
        return None

    client = MDSOClient(
        base_url=settings.mdso_base_url,
        username=settings.mdso_username,
        password=settings.mdso_password,
        verify_ssl=settings.mdso_verify_ssl,
        ssl_ca_bundle=settings.mdso_ssl_ca_bundle,
        timeout=settings.mdso_timeout,
        token_expiry_seconds=settings.mdso_token_expiry_seconds,
    )

    logger.info(
        "mdso_client_created",
        base_url=settings.mdso_base_url,
        verify_ssl=settings.mdso_verify_ssl
    )
    return client


def create_mdso_repository() -> Optional[MDSORepository]:
    """Create MDSO repository (with optional caching)"""
    client = get_registry().get_optional("mdso_client")

    if not client:
        logger.warning("mdso_repository_skipped_no_client")
        return None

    # Create HTTP repository
    repo = HTTPMDSORepository(client)

    # Optionally wrap with caching
    # TODO: Add cache TTL configuration
    # repo = CachedMDSORepository(repo, ttl_seconds=300)

    logger.info("mdso_repository_created")
    return repo


def create_state_manager() -> StateManager:
    """Create state manager based on configuration"""
    if settings.use_redis_state:
        logger.info(
            "state_manager_creating_redis",
            redis_url=settings.redis_url,
            max_connections=settings.redis_max_connections
        )
        return RedisStateManager(
            redis_url=settings.redis_url,
            key_prefix=settings.redis_key_prefix,
            max_connections=settings.redis_max_connections,
        )
    else:
        logger.info("state_manager_creating_in_memory")
        return InMemoryStateManager()


# FastAPI dependency functions (use with Depends())

async def get_mdso_client() -> Optional[MDSOClient]:
    """FastAPI dependency: Get MDSO client"""
    return get_registry().get_optional("mdso_client")


async def get_mdso_repository() -> Optional[MDSORepository]:
    """FastAPI dependency: Get MDSO repository"""
    return get_registry().get_optional("mdso_repository")


async def get_state_manager() -> StateManager:
    """FastAPI dependency: Get state manager"""
    return get_registry().get("state_manager")


# Initialization function

def initialize_services():
    """Initialize all application services

    Call this during application startup to register all services.
    """
    registry = get_registry()

    # Register factories for lazy initialization
    registry.register_factory("mdso_client", create_mdso_client)
    registry.register_factory("mdso_repository", create_mdso_repository)
    registry.register_factory("state_manager", create_state_manager)

    logger.info("services_initialized")


async def cleanup_services():
    """Cleanup all services

    Call this during application shutdown.
    """
    await get_registry().cleanup()
    logger.info("services_cleaned_up")


# Context manager for testing

class ServiceContext:
    """Context manager for testing with custom service implementations

    Example:
        with ServiceContext() as ctx:
            ctx.register("mdso_repository", InMemoryMDSORepository())
            # Test code here
    """

    def __init__(self):
        self._original_services = {}
        self._original_factories = {}

    def __enter__(self):
        """Save current state"""
        registry = get_registry()
        self._original_services = registry._services.copy()
        self._original_factories = registry._factories.copy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original state"""
        registry = get_registry()
        registry._services = self._original_services
        registry._factories = self._original_factories

    def register(self, name: str, instance: Any):
        """Register a service for testing"""
        get_registry().register_instance(name, instance)

    def register_factory(self, name: str, factory: Callable):
        """Register a factory for testing"""
        get_registry().register_factory(name, factory)


# Alternative: Class-based approach for more complex scenarios

class Container:
    """Alternative DI container using property-based lazy loading

    This provides a more explicit approach compared to the registry.
    Use this when you prefer type hints and IDE autocomplete.
    """

    def __init__(self):
        self._mdso_client: Optional[MDSOClient] = None
        self._mdso_repository: Optional[MDSORepository] = None
        self._state_manager: Optional[StateManager] = None

    @property
    def mdso_client(self) -> Optional[MDSOClient]:
        """Lazily create MDSO client"""
        if self._mdso_client is None:
            self._mdso_client = create_mdso_client()
        return self._mdso_client

    @property
    def mdso_repository(self) -> Optional[MDSORepository]:
        """Lazily create MDSO repository"""
        if self._mdso_repository is None:
            self._mdso_repository = create_mdso_repository()
        return self._mdso_repository

    @property
    def state_manager(self) -> StateManager:
        """Lazily create state manager"""
        if self._state_manager is None:
            self._state_manager = create_state_manager()
        return self._state_manager

    async def cleanup(self):
        """Cleanup all services"""
        if self._mdso_client:
            await self._mdso_client.close()
        if self._state_manager:
            await self._state_manager.close()

        self._mdso_client = None
        self._mdso_repository = None
        self._state_manager = None


# Global container instance (alternative to registry)
_container: Optional[Container] = None


def get_container() -> Container:
    """Get or create the global container"""
    global _container
    if _container is None:
        _container = Container()
    return _container
