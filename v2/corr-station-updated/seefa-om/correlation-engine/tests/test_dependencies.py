"""Tests for dependency injection container"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.dependencies import (
    ServiceRegistry,
    ServiceContext,
    Container,
    get_registry,
    get_container,
    initialize_services,
    cleanup_services,
)
from app.mdso import InMemoryMDSORepository
from app.pipeline.state_manager import InMemoryStateManager


class TestServiceRegistry:
    """Test ServiceRegistry"""

    @pytest.fixture
    def registry(self):
        """Create fresh registry"""
        return ServiceRegistry()

    def test_register_and_get_instance(self, registry):
        """Should register and retrieve instance"""
        service = Mock()
        registry.register_instance("test_service", service)

        result = registry.get("test_service")

        assert result is service

    def test_register_and_get_factory(self, registry):
        """Should create instance from factory"""
        factory = Mock(return_value="created_service")
        registry.register_factory("test_service", factory)

        result = registry.get("test_service")

        assert result == "created_service"
        factory.assert_called_once()

    def test_factory_creates_singleton(self, registry):
        """Factory should only be called once (singleton)"""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return f"service_{call_count}"

        registry.register_factory("test_service", factory)

        # Get multiple times
        result1 = registry.get("test_service")
        result2 = registry.get("test_service")

        assert result1 == result2 == "service_1"
        assert call_count == 1  # Factory called only once

    def test_get_nonexistent_raises_error(self, registry):
        """Should raise KeyError for non-existent service"""
        with pytest.raises(KeyError, match="not registered"):
            registry.get("nonexistent")

    def test_get_optional_returns_none(self, registry):
        """Should return None for non-existent service"""
        result = registry.get_optional("nonexistent")

        assert result is None

    def test_get_optional_returns_service(self, registry):
        """Should return service if it exists"""
        service = Mock()
        registry.register_instance("test_service", service)

        result = registry.get_optional("test_service")

        assert result is service

    def test_has_service(self, registry):
        """Should check if service exists"""
        assert not registry.has("test_service")

        registry.register_instance("test_service", Mock())

        assert registry.has("test_service")

    def test_has_factory(self, registry):
        """Should check if factory exists"""
        assert not registry.has("test_service")

        registry.register_factory("test_service", Mock())

        assert registry.has("test_service")

    @pytest.mark.asyncio
    async def test_cleanup_calls_close(self, registry):
        """Should call close() on services that have it"""
        service_with_close = Mock()
        service_with_close.close = AsyncMock()
        service_without_close = Mock(spec=[])  # No close method

        registry.register_instance("with_close", service_with_close)
        registry.register_instance("without_close", service_without_close)

        await registry.cleanup()

        service_with_close.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_clears_services(self, registry):
        """Should clear all services after cleanup"""
        registry.register_instance("test", Mock())

        assert registry.has("test")

        await registry.cleanup()

        # Services cleared but factories remain
        assert not registry.has("test")

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors(self, registry):
        """Should handle errors during cleanup"""
        service = Mock()
        service.close = AsyncMock(side_effect=Exception("Close failed"))

        registry.register_instance("test", service)

        # Should not raise exception
        await registry.cleanup()


class TestServiceContext:
    """Test ServiceContext for testing"""

    def test_context_isolates_services(self):
        """Should isolate services within context"""
        registry = get_registry()

        # Register outside context
        registry.register_instance("global_service", "global")

        with ServiceContext() as ctx:
            # Register inside context
            ctx.register("local_service", "local")

            # Both should be available inside
            assert registry.get("global_service") == "global"
            assert registry.get("local_service") == "local"

        # Only global should exist outside
        assert registry.get_optional("global_service") == "global"
        assert registry.get_optional("local_service") is None

    def test_context_restores_overridden_services(self):
        """Should restore original services after override"""
        registry = get_registry()
        registry.register_instance("test_service", "original")

        with ServiceContext() as ctx:
            # Override service
            ctx.register("test_service", "overridden")
            assert registry.get("test_service") == "overridden"

        # Should be restored
        assert registry.get("test_service") == "original"

    def test_context_with_exception(self):
        """Should restore services even on exception"""
        registry = get_registry()
        registry.register_instance("test_service", "original")

        try:
            with ServiceContext() as ctx:
                ctx.register("test_service", "overridden")
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should be restored
        assert registry.get("test_service") == "original"


class TestContainer:
    """Test Container class"""

    @pytest.fixture
    def container(self):
        """Create fresh container"""
        return Container()

    def test_state_manager_property(self, container):
        """Should lazily create state manager"""
        # First access creates it
        manager1 = container.state_manager

        assert manager1 is not None
        assert isinstance(manager1, InMemoryStateManager)

        # Second access returns same instance
        manager2 = container.state_manager

        assert manager2 is manager1

    @pytest.mark.asyncio
    async def test_cleanup(self, container):
        """Should cleanup all services"""
        # Access services to create them
        _ = container.state_manager

        # Cleanup
        await container.cleanup()

        # Services should be reset
        assert container._state_manager is None

    def test_mdso_client_when_not_configured(self, container):
        """Should return None when MDSO not configured"""
        with patch('app.dependencies.settings') as mock_settings:
            mock_settings.mdso_base_url = None

            client = container.mdso_client

            assert client is None

    def test_mdso_repository_when_client_exists(self, container):
        """Should create repository when client exists"""
        # Mock the client
        container._mdso_client = Mock()

        repo = container.mdso_repository

        assert repo is not None


class TestInitialization:
    """Test service initialization"""

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup(self):
        """Should initialize and cleanup services"""
        # Clear registry first
        registry = get_registry()
        await registry.cleanup()

        # Initialize
        initialize_services()

        # Services should be registered (as factories)
        assert registry.has("state_manager")

        # Cleanup
        await cleanup_services()

    def test_initialize_registers_factories(self):
        """Should register service factories"""
        registry = get_registry()
        registry._services.clear()
        registry._factories.clear()

        initialize_services()

        # Check factories registered
        assert registry.has("mdso_client")
        assert registry.has("mdso_repository")
        assert registry.has("state_manager")

    @pytest.mark.asyncio
    async def test_state_manager_creation(self):
        """Should create state manager from factory"""
        registry = get_registry()
        await registry.cleanup()

        initialize_services()

        # Get state manager (triggers factory)
        manager = registry.get("state_manager")

        assert manager is not None
        assert isinstance(manager, InMemoryStateManager)


class TestDependencyInjectionIntegration:
    """Integration tests for DI system"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full service lifecycle"""
        # 1. Initialize
        initialize_services()

        # 2. Get services
        registry = get_registry()
        state_manager = registry.get("state_manager")

        assert state_manager is not None

        # 3. Use services
        from app.pipeline.state_manager import CorrelationEntry
        entry = CorrelationEntry(
            correlation_id="test-123",
            trace_id="trace-456",
            service="test",
            env="dev"
        )
        await state_manager.set_correlation("test-123", entry)

        result = await state_manager.get_correlation("test-123")
        assert result is not None

        # 4. Cleanup
        await cleanup_services()

    @pytest.mark.asyncio
    async def test_service_context_for_testing(self):
        """Test using ServiceContext for isolated testing"""
        # Setup production services
        initialize_services()

        # Test with mock services
        with ServiceContext() as ctx:
            # Use in-memory implementations for testing
            mock_repo = InMemoryMDSORepository()
            mock_state = InMemoryStateManager()

            ctx.register("mdso_repository", mock_repo)
            ctx.register("state_manager", mock_state)

            # Test code would use these mocks
            registry = get_registry()
            repo = registry.get("mdso_repository")
            state = registry.get("state_manager")

            assert repo is mock_repo
            assert state is mock_state

        # Production services restored after context

    def test_container_alternative_approach(self):
        """Test Container as alternative to registry"""
        container = get_container()

        # Access services via properties
        state_manager = container.state_manager

        assert state_manager is not None

    @pytest.mark.asyncio
    async def test_dependency_functions_for_fastapi(self):
        """Test FastAPI dependency functions"""
        from app.dependencies import get_state_manager as get_state_dep

        # Initialize services
        initialize_services()

        # Dependency functions return services
        state_manager = await get_state_dep()

        assert state_manager is not None

        # Cleanup
        await cleanup_services()


class TestServiceFactories:
    """Test individual service factory functions"""

    def test_create_state_manager_in_memory(self):
        """Should create in-memory state manager by default"""
        from app.dependencies import create_state_manager

        with patch('app.dependencies.settings') as mock_settings:
            mock_settings.use_redis_state = False

            manager = create_state_manager()

            assert isinstance(manager, InMemoryStateManager)

    def test_create_state_manager_redis(self):
        """Should create Redis state manager when configured"""
        from app.dependencies import create_state_manager
        from app.pipeline.state_manager import RedisStateManager

        with patch('app.dependencies.settings') as mock_settings:
            mock_settings.use_redis_state = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_key_prefix = "test:"
            mock_settings.redis_max_connections = 50

            manager = create_state_manager()

            assert isinstance(manager, RedisStateManager)

    def test_create_mdso_client_when_configured(self):
        """Should create MDSO client when configured"""
        from app.dependencies import create_mdso_client

        with patch('app.dependencies.settings') as mock_settings:
            mock_settings.mdso_base_url = "https://mdso.example.com"
            mock_settings.mdso_username = "user"
            mock_settings.mdso_password = "pass"
            mock_settings.mdso_verify_ssl = True
            mock_settings.mdso_ssl_ca_bundle = None
            mock_settings.mdso_timeout = 30.0
            mock_settings.mdso_token_expiry_seconds = 3600

            client = create_mdso_client()

            assert client is not None
            assert client.base_url == "https://mdso.example.com"

    def test_create_mdso_client_when_not_configured(self):
        """Should return None when MDSO not configured"""
        from app.dependencies import create_mdso_client

        with patch('app.dependencies.settings') as mock_settings:
            mock_settings.mdso_base_url = None

            client = create_mdso_client()

            assert client is None
