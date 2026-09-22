"""
Unit tests for ProviderRegistry — Core Component.

Verifies registration, retrieval, health tracking, singleton constraint,
and backward compatibility behaviors.
"""

import asyncio
import time
import pytest

from aios.core.provider import Provider
from aios.core.provider_registry import (
    ProviderRegistry,
    ProviderRegistryState,
    get_provider_registry,
    get_default_provider_registry,
    reset_provider_registry_singleton,
)
from aios.core.provider_failures import ProviderFailure, FailureCategory
from aios.core.model_router import ModelRequest, ModelResponse, ModelProvider


class TestProvider(Provider):
    """Simple provider for testing."""

    def __init__(self, content="from-test"):
        self.calls = 0
        self._content = content
        self.reload_credentials_called = False

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            content=f"{self._content}: {request.prompt[:40]}",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
        )

    async def reload_credentials(self) -> None:
        """Mock implementation of reload_credentials for testing."""
        self.reload_credentials_called = True


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before each test for isolation."""
    reset_provider_registry_singleton()
    yield
    reset_provider_registry_singleton()


class TestProviderRegistryBasic:
    """Test basic ProviderRegistry functionality."""

    def test_initial_state(self):
        """ProviderRegistry starts in UNINITIALIZED state."""
        registry = ProviderRegistry()
        assert registry.state == ProviderRegistryState.UNINITIALIZED

    def test_register_provider(self):
        """Provider can be registered and retrieved."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)
        assert registry.has_provider("test-provider")
        assert registry.get_provider("test-provider") is provider

    def test_get_nonexistent_provider(self):
        """Getting a non-existent provider returns None."""
        registry = ProviderRegistry()
        assert registry.get_provider("non-existent") is None
        assert not registry.has_provider("non-existent")

    def test_list_providers(self):
        """list_providers returns all registered provider IDs."""
        registry = ProviderRegistry()
        registry.register_provider("p1", TestProvider())
        registry.register_provider("p2", TestProvider())
        providers = registry.list_providers()
        assert set(providers) == {"p1", "p2"}

    def test_unregister_provider(self):
        """Provider can be unregistered."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)
        assert registry.unregister_provider("test-provider") is True
        assert not registry.has_provider("test-provider")

    def test_unregister_nonexistent_provider(self):
        """Unregistering a non-existent provider returns False."""
        registry = ProviderRegistry()
        assert registry.unregister_provider("non-existent") is False

    def test_register_duplicate_provider(self):
        """Registering a duplicate provider raises RuntimeError."""
        registry = ProviderRegistry()
        registry.register_provider("test", TestProvider())
        with pytest.raises(RuntimeError, match="already registered"):
            registry.register_provider("test", TestProvider())

    def test_register_empty_provider_id(self):
        """Registering with empty provider_id raises ValueError."""
        registry = ProviderRegistry()
        with pytest.raises(ValueError, match="provider_id must be a non-empty string"):
            registry.register_provider("", TestProvider())

    def test_register_none_provider(self):
        """Registering None provider raises ValueError."""
        registry = ProviderRegistry()
        with pytest.raises(ValueError, match="provider must not be None"):
            registry.register_provider("test", None)


class TestProviderRegistryIntrospection:
    """Test ProviderRegistry introspection methods."""

    def test_contains_operator(self):
        """Provider ID can be checked with 'in' operator."""
        registry = ProviderRegistry()
        registry.register_provider("test", TestProvider())
        assert "test" in registry
        assert "other" not in registry

    def test_len_operator(self):
        """len() returns the number of registered providers."""
        registry = ProviderRegistry()
        assert len(registry) == 0
        registry.register_provider("p1", TestProvider())
        assert len(registry) == 1
        registry.register_provider("p2", TestProvider())
        assert len(registry) == 2

    def test_get_stats(self):
        """get_stats returns health and count information."""
        registry = ProviderRegistry()
        registry.register_provider("p1", TestProvider())
        stats = registry.get_stats()
        assert stats["total_providers"] == 1
        assert stats["healthy_providers"] == 1
        assert stats["unhealthy_providers"] == 0
        assert stats["name"] == "ProviderRegistry"

    @pytest.mark.asyncio
    async def test_reload_provider_credentials_success(self):
        """Test that reload_provider_credentials successfully notifies providers."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Initially not called
        assert not provider.reload_credentials_called

        # Reload credentials
        result = registry.reload_provider_credentials("test-provider")

        # Should return True and mark provider as called
        assert result is True
        # Give a moment for the async task to complete
        await asyncio.sleep(0.01)
        assert provider.reload_credentials_called

    def test_reload_provider_credentials_unknown_provider(self):
        """Test that reload_provider_credentials handles unknown providers gracefully."""
        registry = ProviderRegistry()

        # Try to reload credentials for unknown provider
        result = registry.reload_provider_credentials("unknown-provider")

        # Should return False (not found)
        assert result is False

    def test_reload_provider_credentials_method_returns_false(self):
        """Test that reload_provider_credentials returns True when provider method exists (regardless of return value)."""

        class ProviderWithFailedReload(Provider):
            async def generate(self, request):
                return None

            # Override reload_credentials to return False
            # but the method still exists
            async def reload_credentials(self):
                return False

        registry = ProviderRegistry()
        provider = ProviderWithFailedReload()
        registry.register_provider("test-provider", provider)

        # Try to reload credentials
        result = registry.reload_provider_credentials("test-provider")

        # Should return True because we successfully invoked the method
        # (our implementation returns True if we could call the method,
        # regardless of what the method returns)
        assert result is True


class TestProviderRegistrySingleton:
    """Test ProviderRegistry singleton behavior."""

    def test_basic_uninitialized_instances_allowed(self):
        """Multiple basic (uninitialized) instances are allowed for backward compat."""
        reg1 = ProviderRegistry()
        reg2 = ProviderRegistry()
        assert reg1 is not reg2
        assert reg1.state == ProviderRegistryState.UNINITIALIZED
        assert reg2.state == ProviderRegistryState.UNINITIALIZED

    @pytest.mark.asyncio
    async def test_singleton_constraint_after_initialization(self):
        """After an instance is initialized, creating another raises RuntimeError."""
        reg1 = ProviderRegistry()
        await reg1.initialize()
        assert reg1.state == ProviderRegistryState.RUNNING

        with pytest.raises(RuntimeError, match="Only one ProviderRegistry instance"):
            ProviderRegistry()


class TestProviderRegistryCoreComponent:
    """Test ProviderRegistry as a Core Component."""

    def test_name(self):
        """ProviderRegistry reports correct name."""
        registry = ProviderRegistry()
        assert registry.name == "ProviderRegistry"

    def test_phase(self):
        """ProviderRegistry reports correct initialization phase."""
        registry = ProviderRegistry()
        assert registry.phase == 1

    def test_dependencies(self):
        """ProviderRegistry reports correct dependencies."""
        registry = ProviderRegistry()
        assert "EventBus" in registry.dependencies

    @pytest.mark.asyncio
    async def test_initialize_without_event_bus(self):
        """ProviderRegistry can initialize without an EventBus (deferred)."""
        registry = ProviderRegistry()
        result = await registry.initialize()
        assert result == ProviderRegistryState.RUNNING
        assert registry.state == ProviderRegistryState.RUNNING

    def test_health_check(self):
        """healthCheck returns correct health snapshot."""
        registry = ProviderRegistry()
        health = registry.healthCheck()
        assert health.state == ProviderRegistryState.UNINITIALIZED
        assert health.total_providers == 0
        assert health.healthy_providers == 0


class TestProviderRegistryProviderInteraction:
    """Test ProviderRegistry interaction with Provider interface."""

    @pytest.mark.asyncio
    async def test_registered_provider_generate(self):
        """A registered provider can be used to generate responses."""
        registry = ProviderRegistry()
        provider = TestProvider(content="test-content")
        registry.register_provider("test", provider)

        provider = registry.get_provider("test")
        request = ModelRequest(prompt="hello world")
        response = await provider.generate(request)

        assert provider.calls == 1
        assert response.content == "test-content: hello world"


class TestBackwardCompatibility:
    """Test backward compatibility behaviors."""

    def test_get_default_provider_registry(self):
        """get_default_provider_registry returns a working instance."""
        reg = get_default_provider_registry()
        assert reg is not None
        assert isinstance(reg, ProviderRegistry)

    def test_get_provider_registry_singleton(self):
        """get_provider_registry returns the same instance each time."""
        reg1 = get_provider_registry()
        reg2 = get_provider_registry()
        assert reg1 is reg2


class TestProviderRegistryLifecycle:
    """Test ProviderRegistry lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_transitions_state(self):
        """initialize transitions from UNINITIALIZED to RUNNING."""
        registry = ProviderRegistry()
        assert registry.state == ProviderRegistryState.UNINITIALIZED
        await registry.initialize()
        assert registry.state == ProviderRegistryState.RUNNING

    @pytest.mark.asyncio
    async def test_double_initialize_is_idempotent(self):
        """Initializing twice returns RUNNING both times."""
        registry = ProviderRegistry()
        state1 = await registry.initialize()
        state2 = await registry.initialize()
        assert state1 == state2 == ProviderRegistryState.RUNNING

    @pytest.mark.asyncio
    async def test_shutdown_transitions_state(self):
        """shutdown transitions to SHUTDOWN state."""
        registry = ProviderRegistry()
        await registry.initialize()
        assert registry.state == ProviderRegistryState.RUNNING

        state = await registry.shutdown()
        assert state == ProviderRegistryState.SHUTDOWN
        assert registry.state == ProviderRegistryState.SHUTDOWN


class TestProviderRegistryHealthTracking:
    """Test ProviderRegistry health tracking."""

    def test_update_health_healthy(self):
        """Updating health to healthy resets failure count."""
        registry = ProviderRegistry()
        registry.register_provider("test", TestProvider())
        registry.update_provider_health("test", healthy=True)
        stats = registry.get_stats()
        assert stats["healthy_providers"] == 1

    def test_update_health_unhealthy(self):
        """Updating health to unhealthy tracks failures correctly."""
        registry = ProviderRegistry()
        registry.register_provider("test", TestProvider())
        # A provider marked unhealthy (healthy=False) is counted as unhealthy
        # regardless of consecutive_failures count
        registry.update_provider_health("test", healthy=False, error="connection failed")
        stats = registry.get_stats()
        assert stats["unhealthy_providers"] == 1
        assert stats["healthy_providers"] == 0

        # Updating back to healthy should restore it
        registry.update_provider_health("test", healthy=True)
        stats = registry.get_stats()
        assert stats["unhealthy_providers"] == 0
        assert stats["healthy_providers"] == 1

    def test_update_health_unknown_provider(self):
        """Updating health for unknown provider is a no-op."""
        registry = ProviderRegistry()
        registry.register_provider("test", TestProvider())
        # Updating health for unknown provider should not raise
        registry.update_provider_health("unknown", healthy=False)
        assert True  # No exception raised


class TestProviderRegistryProviderInfo:
    """Test ProviderRegistry ProviderInfo functionality."""

    def test_list_provider_info_empty_registry(self):
        """list_provider_info returns empty list for empty registry."""
        registry = ProviderRegistry()
        info_list = registry.list_provider_info()
        assert info_list == []

    def test_list_provider_info_single_provider(self):
        """list_provider_info returns correct info for single provider."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        info_list = registry.list_provider_info()
        assert len(info_list) == 1

        info = info_list[0]
        assert info.id == "test-provider"
        assert info.display_name == "TEST PROVIDER"  # Derived from ID
        assert info.enabled is True
        assert info.healthy is True
        assert info.error is None
        assert info.configured is True

    def test_list_provider_info_multiple_providers(self):
        """list_provider_info returns correct info for multiple providers."""
        registry = ProviderRegistry()
        provider1 = TestProvider("provider1")
        provider2 = TestProvider("provider2")
        registry.register_provider("provider-one", provider1)
        registry.register_provider("provider_two", provider2)

        info_list = registry.list_provider_info()
        assert len(info_list) == 2

        # Check first provider
        info1 = next(info for info in info_list if info.id == "provider-one")
        assert info1.display_name == "PROVIDER ONE"
        assert info1.enabled is True
        assert info1.healthy is True
        assert info1.error is None
        assert info1.configured is True

        # Check second provider
        info2 = next(info for info in info_list if info.id == "provider_two")
        assert info2.display_name == "PROVIDER TWO"
        assert info2.enabled is True
        assert info2.healthy is True
        assert info2.error is None
        assert info2.configured is True

    def test_get_provider_info_unknown_provider(self):
        """get_provider_info returns None for unknown provider."""
        registry = ProviderRegistry()
        info = registry.get_provider_info("unknown-provider")
        assert info is None

    def test_get_provider_info_existing_provider(self):
        """get_provider_info returns correct info for existing provider."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        info = registry.get_provider_info("test-provider")
        assert info is not None
        assert info.id == "test-provider"
        assert info.display_name == "TEST PROVIDER"
        assert info.enabled is True
        assert info.healthy is True
        assert info.error is None
        assert info.configured is True

    def test_provider_info_reflects_disabled_state(self):
        """ProviderInfo correctly reflects disabled provider state."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Disable the provider
        registry.disable_provider("test-provider")

        info = registry.get_provider_info("test-provider")
        assert info is not None
        assert info.enabled is False
        assert info.healthy is True  # Health and enabled are separate
        assert info.error is None
        assert info.configured is True  # Configured is about setup, not enabled state

    def test_provider_info_reflects_health_state(self):
        """ProviderInfo correctly reflects provider health state."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Mark provider as unhealthy
        registry.update_provider_health("test-provider", healthy=False, error="Connection timeout")

        info = registry.get_provider_info("test-provider")
        assert info is not None
        assert info.enabled is True  # Enabled and health are separate
        assert info.healthy is False
        assert info.error == "Connection timeout"
        assert info.configured is True

    def test_provider_info_contains_no_secrets(self):
        """ProviderInfo does not expose any secret values."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        info = registry.get_provider_info("test-provider")
        assert info is not None

        # Verify no secret-like fields are present
        assert not hasattr(info, 'api_key')
        assert not hasattr(info, 'token')
        assert not hasattr(info, 'password')
        assert not hasattr(info, 'secret')
        assert not hasattr(info, 'authorization')
        assert not hasattr(info, 'credentials')

        # Verify the actual fields are present and appropriate types
        assert isinstance(info.id, str)
        assert isinstance(info.display_name, str)
        assert isinstance(info.enabled, bool)
        assert isinstance(info.healthy, bool)
        assert info.error is None or isinstance(info.error, str)
        assert isinstance(info.configured, bool)

    def test_list_provider_info_thread_safety(self):
        """list_provider_info is thread-safe and returns consistent results."""
        import threading
        import time

        registry = ProviderRegistry()
        # Register multiple providers
        for i in range(5):
            provider = TestProvider(f"provider-{i}")
            registry.register_provider(f"provider-{i}", provider)

        results = []

        def call_list_provider_info():
            result = registry.list_provider_info()
            results.append(len(result))

        # Call from multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=call_list_provider_info)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All calls should return the same count
        assert all(count == 5 for count in results)

    def test_get_provider_info_thread_safety(self):
        """get_provider_info is thread-safe and returns consistent results."""
        import threading
        import time

        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        results = []

        def call_get_provider_info():
            result = registry.get_provider_info("test-provider")
            results.append(result is not None)

        # Call from multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=call_get_provider_info)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All calls should return True (provider found)
        assert all(found for found in results)

    def test_provider_info_derived_display_names(self):
        """ProviderInfo generates reasonable display names from provider IDs."""
        registry = ProviderRegistry()

        test_cases = [
            ("nim", "NIM"),
            ("freellmapi", "FREELLMAPI"),
            ("test_provider", "TEST PROVIDER"),
            ("test-provider", "TEST PROVIDER"),
            ("openai-gpt", "OPENAI GPT"),
            ("anthropic_claude", "ANTHROPIC CLAUDE"),
        ]

        for provider_id, expected_display_name in test_cases:
            provider = TestProvider()
            registry.register_provider(provider_id, provider)
            info = registry.get_provider_info(provider_id)
            assert info.display_name == expected_display_name
            # Clean up for next iteration
            registry.unregister_provider(provider_id)

    def test_provider_info_configured_state(self):
        """ProviderInfo configured state behaves correctly."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Initially should be configured
        info = registry.get_provider_info("test-provider")
        assert info.configured is True

        # Disabling should not affect configured state (it's about setup, not enabled state)
        registry.disable_provider("test-provider")
        info = registry.get_provider_info("test-provider")
        assert info.configured is True  # Still configured, just disabled
        assert info.enabled is False

        # Re-enabling should work
        registry.enable_provider("test-provider")
        info = registry.get_provider_info("test-provider")
        assert info.configured is True
        assert info.enabled is True


class TestProviderRegistryCooldown:
    """Test ProviderRegistry cooldown functionality."""

    def test_cooldown_initially_inactive(self):
        """Provider cooldown is initially inactive."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Get provider info to check cooldown status
        info = registry.get_provider_info("test-provider")
        assert info.enabled is True
        assert info.healthy is True

        # Provider should be available (not in cooldown)
        retrieved = registry.get_provider("test-provider")
        assert retrieved is provider

    def test_apply_cooldown_via_failure(self):
        """Applying cooldown via failure makes provider temporarily unavailable."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Create a network failure that should trigger cooldown
        failure = ProviderFailure(
            category=FailureCategory.NETWORK,
            provider_id="test-provider",
            safe_message="Network timeout"
        )

        # Apply the failure (this should trigger cooldown)
        registry.update_provider_health_from_failure("test-provider", failure)

        # Provider should still be in registry but marked as unhealthy
        info = registry.get_provider_info("test-provider")
        assert info.enabled is True  # Enabled state unchanged
        assert info.healthy is False  # But health affected

        # Provider should not be retrievable due to cooldown/unhealthy
        retrieved = registry.get_provider("test-provider")
        assert retrieved is None  # Should return None due to cooldown/unhealthy

        # But should still be registered
        assert registry.has_provider("test-provider") is True

    def test_cooldown_expiry(self):
        """Provider cooldown expires after time passes."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Manually apply a short cooldown
        registry._apply_cooldown("test-provider", FailureCategory.NETWORK, 0.1)  # 100ms

        # Should be in cooldown initially
        assert registry.get_provider_cooldown_remaining("test-provider") > 0
        assert registry.get_provider("test-provider") is None  # Not available

        # Wait for cooldown to expire
        time.sleep(0.15)  # Wait longer than cooldown

        # Should no longer be in cooldown
        assert registry.get_provider_cooldown_remaining("test-provider") == 0
        assert registry.get_provider("test-provider") is provider  # Available again

    def test_clear_cooldown(self):
        """Manually clearing cooldown makes provider available again."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply cooldown
        registry._apply_cooldown("test-provider", FailureCategory.NETWORK, 5.0)  # 5 seconds

        # Verify in cooldown
        assert registry.get_provider_cooldown_remaining("test-provider") > 0
        assert registry.get_provider("test-provider") is None

        # Clear cooldown
        result = registry.clear_cooldown("test-provider")
        assert result is True

        # Verify cooldown cleared and provider available
        assert registry.get_provider_cooldown_remaining("test-provider") == 0
        assert registry.get_provider("test-provider") is provider

    def test_clear_cooldown_not_in_cooldown(self):
        """Clearing cooldown when not in cooldown returns False."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Try to clear cooldown when not in cooldown
        result = registry.clear_cooldown("test-provider")
        assert result is False

    def test_clear_cooldown_unknown_provider(self):
        """Clearing cooldown for unknown provider returns False."""
        registry = ProviderRegistry()

        # Try to clear cooldown for unknown provider
        result = registry.clear_cooldown("unknown-provider")
        assert result is False

    def test_different_failure_categories_have_different_cooldowns(self):
        """Different failure categories apply appropriate cooldown durations."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Test rate limit failure (should use configured duration)
        rate_limit_failure = ProviderFailure(
            category=FailureCategory.RATE_LIMIT,
            provider_id="test-provider",
            safe_message="Rate limit exceeded"
        )

        registry.update_provider_health_from_failure("test-provider", rate_limit_failure)

        # Should have cooldown applied
        cooldown_remaining = registry.get_provider_cooldown_remaining("test-provider")
        # Should be around 60 seconds (default for RATE_LIMIT)
        assert 50 <= cooldown_remaining <= 70  # Allow some timing variance

        # Clear and test another failure type
        registry.clear_cooldown("test-provider")

        # Test unknown failure (should use default)
        unknown_failure = ProviderFailure(
            category=FailureCategory.UNKNOWN,
            provider_id="test-provider",
            safe_message="Unknown error"
        )

        registry.update_provider_health_from_failure("test-provider", unknown_failure)

        # Should have cooldown applied
        cooldown_remaining = registry.get_provider_cooldown_remaining("test-provider")
        # Should be around 30 seconds (default for UNKNOWN)
        assert 25 <= cooldown_remaining <= 35  # Allow some timing variance

    def test_health_restoration_clears_cooldown(self):
        """Restoring provider health clears any active cooldown."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply cooldown
        registry._apply_cooldown("test-provider", FailureCategory.NETWORK, 5.0)

        # Verify in cooldown
        assert registry.get_provider_cooldown_remaining("test-provider") > 0

        # Restore health (should clear cooldown)
        registry.update_provider_health("test-provider", healthy=True)

        # Verify cooldown cleared
        assert registry.get_provider_cooldown_remaining("test-provider") == 0
        assert registry.get_provider("test-provider") is provider  # Available again

    def test_configuration_driven_cooldown_duration(self):
        """Cooldown durations can be configured via configuration manager."""
        # This test verifies the configuration loading mechanism works
        registry = ProviderRegistry()

        # The registry should have loaded default cooldown durations
        # We can indirectly test this by checking that cooldowns are applied
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        failure = ProviderFailure(
            category=FailureCategory.TIMEOUT,
            provider_id="test-provider",
            safe_message="Timeout"
        )

        registry.update_provider_health_from_failure("test-provider", failure)

        # Should have applied cooldown (default for TIMEOUT is 30 seconds)
        cooldown_remaining = registry.get_provider_cooldown_remaining("test-provider")
        assert cooldown_remaining > 0

        # Clean up
        registry.clear_cooldown("test-provider")
